#
# Created on Thu Apr 22 2021
# Matteo Bjornsson
#
###############################################################################
# This is the main deployment script for the rock-paper-scissors app.
# Find info and error logs in the log file 'rps.log'
###############################################################################

from services import IAm, Lambda, Pinpoint, SNS, Dynamodb
from util import *
import os
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)

# Logic flags
# set TEARDOWN to false if you don't want this script to automatically tear
# down deployed services after use. This script will still run with existing
# services so you can run again with True to teardown.
TEARDOWN = True
# set LOCKING to false if you wish to dismiss the use of locks to provide mutual
# exclusion to the game state.
LOCKING = True

# service names and parameters
SNS_INCOMING_SMS_TOPIC_NAME = "rps_incoming_sms"
# Lambda filenames and parameters
LAMBDA_FUNCTION_FILE_NAME = "lambda_function_handler.py"
LAMBDA_HANDLER_NAME = "lambda_function_handler.lambda_handler"
LAMBDA_FUNCTION_NAME = "rps-lambda-function"
LAMBDA_FUNCTION_DESCRIPTION = "Rock Paper Scissors lambda function"
# IAm parameters associated with the lamba
LAMBDA_ROLE_NAME = "rps-lambda-role"
LAMBDA_ASSUME_ROLE_POLICY_FILE_NAME = "policy/lambda_assume_role_policy.json"
LAMBDA_POLICY_NAME = "BasicLambdaExecutionRoleDynamoCRUD"
LAMBDA_POLICY_FILE_NAME = "policy/lambda_policy.json"
# Pinpoint app name
PINPOINT_APP_NAME = "rock_paper_scissors"
# Game state table parameters
GAME_STATE_TABLE_NAME = "game_state"
GAME_STATE_TABLE_SCHEMA = [{"AttributeName": "state", "KeyType": "HASH"}]
GAME_STATE_TABLE_ATTR_DEFINITIONS = [{"AttributeName": "state", "AttributeType": "S"}]
# Lock Table parameters
LOCK_TABLE_NAME = "lock_table"
LOCK_TABLE_SCHEMA = [{"AttributeName": "lock_name", "KeyType": "HASH"}]
LOCK_TABLE_ATTR_DEFINITIONS = [{"AttributeName": "lock_name", "AttributeType": "S"}]
# Lock configuration for retrying and expiring
LOCK_RETRY_BACKOFF_MULTIPLIER = 2
INITIAL_LOCK_WAIT_SECONDS = 0.05
MAX_LOCK_WAIT_SECONDS = 6
LOCK_EXPIRATION_TIME_MS = 5000


def deploy():
    """
    Deploys all of the services!
    """
    #######################################################################
    # Create Sns topic
    # SMS topic acts as intermediary SMS queue and trigger to the lambda function
    sns_in_topic = SNS.create_topic(SNS_INCOMING_SMS_TOPIC_NAME)
    # add a policy to allow Pinpoint to publish to this SNS topic
    pinpoint_policy_statement = {
        "Sid": "PinpointPublish",
        "Effect": "Allow",
        "Principal": {"Service": "mobile.amazonaws.com"},
        "Action": "sns:Publish",
        "Resource": sns_in_topic.arn,
    }
    SNS.add_policy_statement(sns_in_topic, pinpoint_policy_statement)

    #######################################################################
    # Create Pinpoint app
    # The Pinpoint app will handle all SMS traffic
    response = Pinpoint.create_pinpoint_app(PINPOINT_APP_NAME)
    pinpoint_app_id = response["ApplicationResponse"]["Id"]
    Pinpoint.enable_pinpoint_SMS(pinpoint_app_id)

    #######################################################################
    # Update Lambda Code
    # NOTE: The following code writes these parameters into the lambda handler file.
    # This tightly couples the files and makes it so the handler cannot run on its own.
    # this is a little hacky, feel free to improve upon it.
    lines_to_inject = [
        f'PINPOINT_APP_ID = "{pinpoint_app_id}"\n',
        f'GAME_STATE_TABLE_NAME = "{GAME_STATE_TABLE_NAME}"\n',
        f"LOCKING = {LOCKING}\n",
        f'LOCK_TABLE_NAME = "{LOCK_TABLE_NAME}"\n',
        f"LOCK_EXPIRATION_TIME_MS = {LOCK_EXPIRATION_TIME_MS}\n",
        f"LOCK_RETRY_BACKOFF_MULTIPLIER = {LOCK_RETRY_BACKOFF_MULTIPLIER}\n",
        f"INITIAL_LOCK_WAIT_SECONDS = {INITIAL_LOCK_WAIT_SECONDS}\n",
        f"MAX_LOCK_WAIT_SECONDS = {MAX_LOCK_WAIT_SECONDS}\n",
    ]
    # update the lambda file code with new parameters before deploying
    insert_lines_at_keyword(
        os.path.abspath(LAMBDA_FUNCTION_FILE_NAME),
        lines_to_inject,
        "insert new parameters after this line:",
    )

    #######################################################################
    # Create Lambda function
    # This function will handle Rock Paper Scissors logic when SMS are received
    with open(LAMBDA_POLICY_FILE_NAME) as file:
        lambda_policy_json = file.read()
    with open(LAMBDA_ASSUME_ROLE_POLICY_FILE_NAME) as file:
        assume_role_json = file.read()

    iam_policy = IAm.create_policy(LAMBDA_POLICY_NAME, lambda_policy_json)
    iam_role = IAm.create_role(LAMBDA_ROLE_NAME, assume_role_json, [iam_policy.arn])
    function_code = return_zipped_bytes(LAMBDA_FUNCTION_FILE_NAME)

    response = Lambda.create_lambda_function(
        LAMBDA_FUNCTION_NAME,
        LAMBDA_FUNCTION_DESCRIPTION,
        LAMBDA_HANDLER_NAME,
        iam_role,
        function_code,
    )
    function_arn = response["FunctionArn"]

    # Add lambda permission to allow sns topic to invoke the Lambda function
    Lambda.add_permission(
        action="lambda:InvokeFunction",
        function_name=LAMBDA_FUNCTION_NAME,
        principal="sns.amazonaws.com",
        source_arn=sns_in_topic.arn,
        statement_id="sns",
    )

    #######################################################################
    # add a lambda as a subscriber to the topic
    response = SNS.add_subscription(
        topic_arn=sns_in_topic.arn,
        protocol="lambda",
        endpoint=function_arn,
    )

    #######################################################################
    # Create the DynamoDB tables
    # Used for game state and locks
    game_table = Dynamodb.create_table(
        table_name=GAME_STATE_TABLE_NAME,
        key_schema=GAME_STATE_TABLE_SCHEMA,
        attribute_definitions=GAME_STATE_TABLE_ATTR_DEFINITIONS,
    )

    if LOCKING:
        lock_table = Dynamodb.create_table(
            table_name=LOCK_TABLE_NAME,
            key_schema=[{"AttributeName": "lock_name", "KeyType": "HASH"}],
            attribute_definitions=[
                {"AttributeName": "lock_name", "AttributeType": "S"}
            ],
        )

    print(
        "\nServices are deployed. \nYou can now text your pinpoint number 'test' to confirm.\n"
    )
    print(
        'Play rock paper scissors by texting \n"rock", "paper", or "scissors"\nto '
        + "the pinpoint number and have a friend do the same.\n"
    )

    if TEARDOWN:
        input("Press enter to begin service teardown.")
        SNS.delete_topic(sns_in_topic)
        IAm.delete_role(iam_role)
        IAm.delete_policy(iam_policy)
        Lambda.delete_lambda_function(LAMBDA_FUNCTION_NAME)
        delete_lines(os.path.abspath(LAMBDA_FUNCTION_FILE_NAME), lines_to_inject)
        Pinpoint.delete_pinpoint_app(pinpoint_app_id)
        Dynamodb.delete_table(game_table.table_name)
        if LOCKING:
            Dynamodb.delete_table(lock_table.table_name)

        print("Service teardown complete.")


if __name__ == "__main__":
    deploy()
