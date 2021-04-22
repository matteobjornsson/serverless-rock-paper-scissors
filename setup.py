from services import IAm, Lambda, Pinpoint, SNS, Dynamodb
from util import *
import os
import logging
import pprint

logging.basicConfig(filename="rps.log", level=logging.INFO)

# Logic flags
TEARDOWN = True
LOCKING = False

# service names and parameters
SNS_INCOMING_SMS_TOPIC_NAME = "rps_incoming_sms_test"
LAMBDA_POLICY_NAME = "BasicLambdaExecutionRoleDynamoCRUD"
LAMBDA_POLICY_FILE_NAME = "policy/lambda_policy.json"
LAMBDA_ASSUME_ROLE_POLICY_FILE_NAME = "policy/lambda_assume_role_policy.json"
LAMBDA_FUNCTION_FILE_NAME = "lambda_function_handler.py"
LAMBDA_HANDLER_NAME = "lambda_function_handler.lambda_handler"
LAMBDA_ROLE_NAME = "rps-lambda-role_test"
LAMBDA_FUNCTION_NAME = "rps-lambda-function_test"
LAMBDA_FUNCTION_DESCRIPTION = "Rock Paper Scissors lambda function_test"
# parameters for exponential backoff
LOCK_RETRY_BACKOFF_MULTIPLIER = 2
INITIAL_LOCK_WAIT_SECONDS = 0.05
MAX_LOCK_WAIT_SECONDS = 3
PINPOINT_APP_NAME = "rock_paper_scissors_test"
DB_TABLE_NAME = "players"
DB_KEY_SCHEMA = [
    {"AttributeName": "phone_number", "KeyType": "HASH"},  # Partition key
    {"AttributeName": "round", "KeyType": "RANGE"},  # Partition key
]
DB_ATTRIBUTE_DEFINITION = [
    {"AttributeName": "phone_number", "AttributeType": "S"},
    {"AttributeName": "round", "AttributeType": "S"},
]
LOCK_EXPIRATION_TIME_MS = 5000
LOCK_TABLE_NAME = "lock_table"


########
# SNS  #
########
# create sns topic to handle incoming SMS messages from Pinpoint
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


#############
# PINPOINT  #
#############
# Create pinpoint app to handle incoming SMS
response = Pinpoint.create_pinpoint_app(PINPOINT_APP_NAME)
pinpoint_app_id = response["ApplicationResponse"]["Id"]

Pinpoint.enable_pinpoint_SMS(pinpoint_app_id)
print("pinpoint appID", pinpoint_app_id)

# NOTE: The following code writes these parameters into the lambda handler file.
# This tightly couples the files and makes it so the handler cannot run on its own.
# this is a little hacky, feel free to improve upon it. 
lines_to_inject = [
    f'PINPOINT_APP_ID = "{pinpoint_app_id}"\n',
    f'DB_TABLE_NAME = "{DB_TABLE_NAME}"\n',
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

###########
# LAMBDA  #
###########
# create lambda function to handle Rock Paper Scissors logic when SMS are received
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


# Give the sns topic permission to invoke the Lambda function
Lambda.add_permission(
    action="lambda:InvokeFunction",
    function_name=LAMBDA_FUNCTION_NAME,
    principal="sns.amazonaws.com",
    source_arn=sns_in_topic.arn,
    statement_id="sns",
)

# add a lambda as a subscriber to the topic
response = SNS.add_subscription(
    topic_arn=sns_in_topic.arn,
    protocol="lambda",
    endpoint=function_arn,
)

#############
# DYNAMODB  #
#############
game_table = Dynamodb.create_table(
    DB_TABLE_NAME, DB_KEY_SCHEMA, DB_ATTRIBUTE_DEFINITION
)

if LOCKING:
    lock_table = Dynamodb.create_table(
        table_name=LOCK_TABLE_NAME,
        key_schema=[{"AttributeName": "lock_name", "KeyType": "HASH"}],
        attribute_definitions=[{"AttributeName": "lock_name", "AttributeType": "S"}],
    )

print("Services are deployed. You can now text your pinpoint number 'test' to confirm.")

if TEARDOWN:
    input("Press enter to begin TEARDOWN.")
    SNS.delete_topic(sns_in_topic)
    IAm.delete_role(iam_role)
    IAm.delete_policy(iam_policy)
    Lambda.delete_lambda_function(LAMBDA_FUNCTION_NAME)
    Dynamodb.delete_table(game_table.table_name)
    Pinpoint.delete_pinpoint_app(pinpoint_app_id)
    delete_lines(os.path.abspath(LAMBDA_FUNCTION_FILE_NAME), lines_to_inject)
    if LOCKING:
        Dynamodb.delete_table(lock_table.table_name)

    print("Service TEARDOWN complete.")
