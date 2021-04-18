# file contents adapted from AWS example
# https://docs.aws.amazon.com/code-samples/latest/catalog/python-lambda-boto_client_examples-lambda_basics.py.html

from zipfile import ZipFile
import io
import iam
import boto3
from botocore.exceptions import ClientError
import logging
logging.basicConfig(filename='rps.log', level=logging.INFO)

lambda_client = boto3.client('lambda')

# zip a given file, return file as bytes
def zip_lambda_code(file_name: str) -> bytes:
    # buffer the zip file contents as a BytesIO object
    bytes_buffer = io.BytesIO()
    with ZipFile(bytes_buffer, 'w') as zip:
        # write the file to the buffer
        zip.write(file_name)
    # return the file position to the start (otherwise 'read()' returns nothing)
    bytes_buffer.seek(0)
    return bytes_buffer.read()


def create_lambda_function(lambda_client, function_name: str, description: str, handler_name: str, iam_role, code_bytes):
    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Description=description,
            Runtime='python3.8',
            Role=iam_role.arn,
            Handler=handler_name,
            Code={'ZipFile': code_bytes},
            Publish=True)
        function_arn = response['FunctionArn']
        logging.info("Created function '%s' with ARN: '%s'.",
                    function_name, response['FunctionArn'])
    except ClientError:
        logging.exception("Couldn't create function %s.", function_name)
        raise
    else:
        return function_arn

def add_permission(client, action: str, function_name: str, principal: str, source_arn: str, statement_id: str) -> None:
    try:
        response = client.add_permission(
            Action=action,
            FunctionName=function_name,
            Principal=principal,
            SourceArn=source_arn,
            StatementId=statement_id,
        )
    except ClientError as e:
        logging.error(e.response['Error']['Message'])
    else:
        success_msg = "Lambda Policy Permission Added."
        logging.info(success_msg)
        print(success_msg)


if __name__ == '__main__':

    lambda_function_filename = 'lambda_function_handler.py'
    lambda_handler_name = 'lambda_function_handler.lambda_handler'
    lambda_role_name = 'rps-lambda-role'
    lambda_function_name = 'rps-lambda-function'

    iam_role = iam.create_iam_role(lambda_role_name)
    function_code = zip_lambda_code(lambda_function_filename)
    description = "Rock Paper Scissors lambda function"
    create_lambda_function(lambda_client, lambda_function_name, description, lambda_handler_name, iam_role, function_code)
    add_permission(
        client=lambda_client,
        action='lambda:InvokeFunction',
        function_name=lambda_function_name,
        principal='sns.amazonaws.com',
        source_arn='arn:aws:sns:us-east-1:802108040626:rps_incoming_sms',
        statement_id='sns'
    )
    print("made it")