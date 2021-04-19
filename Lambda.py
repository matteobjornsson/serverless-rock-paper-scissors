# file contents adapted from AWS example
# https://docs.aws.amazon.com/code-samples/latest/catalog/python-lambda-boto_client_examples-lambda_basics.py.html

import io
import time
import IAm
import boto3
from zipfile import ZipFile
from botocore.exceptions import ClientError
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)

lambda_client = boto3.client("lambda")
# parameters for exponential backoff
retry_backoff = 2
initial_wait = 1
max_wait = 9  # only wait < 9s for funciton creation before giving up.


def zip_lambda_code(file_name: str) -> bytes:
    """
    TODO: write function description
    """
    # buffer the zip file contents as a BytesIO object
    bytes_buffer = io.BytesIO()
    with ZipFile(bytes_buffer, "w") as zip:
        # write the file to the buffer
        zip.write(file_name)
    # return the file position to the start (otherwise 'read()' returns nothing)
    bytes_buffer.seek(0)
    return bytes_buffer.read()


def create_lambda_function(
    function_name: str, description: str, handler_name: str, iam_role, code_bytes: bytes
) -> dict:
    """
    TODO: write function description
    """
    delay = initial_wait
    # add in exponential backoff waiting for AWS services (iam_role) to deploy and connect
    while delay < max_wait:
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
            elif delay < max_wait:
                print("Waiting for resources to connect...")
                time.sleep(delay)
                delay = delay * retry_backoff
            else:
                logging.error(e.response["Error"]["Code"])
                logging.error("Couldn't create function %s.", function_name)
                raise
        else:
            logging.info(
                "Created function '%s' with ARN: '%s'.",
                function_name,
                response["FunctionArn"],
            )
            return response


def delete_lambda_function(function_name: str, version=None) -> dict:
    """
    TODO: write function description
    """
    try:
        if version:
            response = lambda_client.delete_function(
                FunctionName=function_name, Qualifier=version
            )
        else:
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
    TODO: write function description
    """
    delay = initial_wait
    # add in exponential backoff waiting for AWS services (iam_role) to deploy and connect
    while delay < max_wait:
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
            delay = delay * retry_backoff

            if delay >= max_wait:
                logging.error(e.response["Error"]["Message"])
                logging.error("Couldn't update function %s.", function_name)
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
    TODO: write function description
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
    TODO: write function description
    """
    try:
        response = lambda_client.get_function(FunctionName=function_name)
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
        logging.exception("Couldn't get function %s.", function_name)
        raise
    else:
        return response["Configuration"]


# "unit" test
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
    function_code = zip_lambda_code(lambda_function_filename)

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
