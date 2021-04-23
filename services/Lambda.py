#
# Created on Thu Apr 22 2021
# Matteo Bjornsson
#
# file contents adapted from AWS example
# https://docs.aws.amazon.com/code-samples/latest/catalog/python-lambda-boto_client_examples-lambda_basics.py.html

import time
from util import return_zipped_bytes
from services import IAm
import boto3
from botocore.exceptions import ClientError
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)

lambda_client = boto3.client("lambda")
# parameters for exponential backoff
RETRY_BACKOFF_MULTIPLIER = 1.5
INITIAL_WAIT_SECONDS = 1
MAX_WAIT_SECONDS = 18


def create_lambda_function(
    function_name: str, description: str, handler_name: str, iam_role, code_bytes: bytes
) -> dict:
    """
    Create a lambda function and publish it.
    :param function_name: function name
    :param description: function description
    :param handler_name: name of the event handler in the lambda function code
    :param iam_role: IAM role object, lambda functions need to be associated to
    a role to define access permissions
    :param code_bytes: bytes of the zipped function code to upload to Lambda
    """
    delay = INITIAL_WAIT_SECONDS
    # add in exponential backoff waiting for AWS services (iam_role) to deploy and connect
    while delay < MAX_WAIT_SECONDS:
        try:
            response = lambda_client.create_function(
                FunctionName=function_name,
                Description=description,
                Runtime="python3.8",
                Role=iam_role.arn,
                Handler=handler_name,
                Code={"ZipFile": code_bytes},
                Publish=True,
            )
        except ClientError as e:
            if "Function already exist" in e.response["Error"]["Message"]:
                logging.warning("The function %s already exists.", function_name)
                return get_function(function_name)
            else:
                print("Waiting for resources to connect...")
                time.sleep(delay)
                # exponential backoff, increase retry time
                delay = delay * RETRY_BACKOFF_MULTIPLIER
                # check if this is the last retry
                if delay >= MAX_WAIT_SECONDS:
                    # if so, max wait time has been exceeded, give up
                    logging.error(e.response["Error"]["Code"])
                    logging.error(
                        "Couldn't create function %s, max retry time exceeded.",
                        function_name,
                    )
                    raise
        else:
            logging.info(
                "Created function '%s' with ARN: '%s'.",
                function_name,
                response["FunctionArn"],
            )
            return response


def delete_lambda_function(function_name: str) -> dict:
    """
    Delete a lambda function by name
    """
    try:
        response = lambda_client.delete_function(FunctionName=function_name)
    except ClientError as error:
        logging.error(error.response["Error"]["Message"])
        logging.error("Couldn't delete function %s.", function_name)
    else:
        logging.info("Function %s Deleted.", function_name)
        return response


def update_lambda_code(
    function_name: str, code_bytes: bytes, publish=True, dryrun=False
) -> dict:
    """
    Use this function to update an existing lambda's code.
    You can change the publish flag to false to prevent deploy. 
    You can set the dryrun to True to inspect the response and confirm it would have worked. 
    :param code_bytes: bytes of zipped new code to publish. 
    """
    delay = INITIAL_WAIT_SECONDS
    # add in exponential backoff waiting for AWS services (iam_role) to deploy and connect
    while delay < MAX_WAIT_SECONDS:
        try:
            response = lambda_client.update_function_code(
                FunctionName="string",
                ZipFile=code_bytes,
                Publish=publish,
                DryRun=dryrun,
            )
        except ClientError as e:
            print("Waiting for resources to connect...")
            time.sleep(delay)
            # exponential backoff, increase retry time
            delay = delay * RETRY_BACKOFF_MULTIPLIER
            # check if this is the last retry
            if delay >= MAX_WAIT_SECONDS:
                # if so, max wait time has been exceeded, give up
                logging.error(e.response["Error"]["Code"])
                logging.error(
                    "Couldn't update function %s, max retry time exceeded.",
                    function_name,
                )
                raise
        else:
            logging.info(
                "Updated function '%s' with ARN: '%s'.",
                function_name,
                response["FunctionArn"],
            )
            return response

def add_permission(
    action: str, function_name: str, principal: str, source_arn: str, statement_id: str
) -> dict:
    """
    Add an IAM policy statement to the lambda.

    :param action: a string matching one of the many allowed AWS policy actions
    see docs here: https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_action.html
    :param function_name: function name
    :param principal: string defining the entity type the action pertains to
    :param source_arn: the arn of the source entity you are giving this permission to
    :param statement_id: a unique id, either descriptive, or uuid style. 

    example, this gives an sns topic permission to trigger the lambda
    Lambda.add_permission(
        action="lambda:InvokeFunction",
        function_name=LAMBDA_FUNCTION_NAME,
        principal="sns.amazonaws.com",
        source_arn=sns_in_topic.arn,
        statement_id="sns",
    )
    """
    try:
        response = lambda_client.add_permission(
            Action=action,
            FunctionName=function_name,
            Principal=principal,
            SourceArn=source_arn,
            StatementId=statement_id,
        )
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
        logging.error("Couldn't add permission to policy")
    else:
        logging.info("Policy Permission Added.")
        return response


def get_function(function_name: str) -> dict:
    """
    Get a function by name.

    return a response dictionary matching create_function() for interchangeability. 
    """
    try:
        response = lambda_client.get_function(FunctionName=function_name)
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
        logging.exception("Couldn't get function %s.", function_name)
        raise
    else:
        return response["Configuration"]


# "unit" test exercising the functionality in the file
if __name__ == "__main__":

    lambda_policy_name = "BasicLambdaExecutionRoleDynamoCRUD"
    lambda_policy_file_name = "lambda_policy.json"
    lambda_assume_role_policy_file_name = "lambda_assume_role_policy.json"
    lambda_function_filename = "lambda_function_handler.py"
    lambda_handler_name = "lambda_function_handler.lambda_handler"
    lambda_role_name = "rps-lambda-role_test"
    lambda_function_name = "rps-lambda-function_test"
    lamda_function_description = "Rock Paper Scissors lambda function_test"

    with open(lambda_policy_file_name) as file:
        lambda_policy_json = file.read()
    with open(lambda_assume_role_policy_file_name) as file:
        assume_role_json = file.read()

    iam_policy = IAm.create_policy(lambda_policy_name, lambda_policy_json)
    iam_role = IAm.create_role(lambda_role_name, assume_role_json, [iam_policy.arn])
    function_code = return_zipped_bytes(lambda_function_filename)

    response = create_lambda_function(
        lambda_function_name,
        lamda_function_description,
        lambda_handler_name,
        iam_role,
        function_code,
    )

    response = create_lambda_function(
        lambda_function_name,
        lamda_function_description,
        lambda_handler_name,
        iam_role,
        function_code,
    )

    delete_lambda_function(lambda_function_name)
