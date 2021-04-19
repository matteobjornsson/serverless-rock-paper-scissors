# file contents adapted from AWS example
# https://docs.aws.amazon.com/code-samples/latest/catalog/python-lambda-boto_client_examples-lambda_basics.py.html

import json
import boto3
from botocore.exceptions import ClientError
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)

iam_resource = boto3.resource("iam")


def create_basic_lambda_execution_role(iam_role_name):  # return iam role object
    lambda_assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    try:
        role = iam_resource.create_role(
            RoleName=iam_role_name,
            AssumeRolePolicyDocument=json.dumps(lambda_assume_role_policy),
        )
        iam_resource.meta.client.get_waiter("role_exists").wait(RoleName=iam_role_name)

    except ClientError as error:
        if error.response["Error"]["Code"] == "EntityAlreadyExists":
            role = iam_resource.Role(iam_role_name)
            logging.warning("The role %s already exists. Using it.", iam_role_name)
        else:
            logging.error(error.response["Error"]["Message"])
            logging.error(
                "Couldn't create role %s or attach policy %s.",
                iam_role_name,
                policy_arn,
            )
    else:
        logging.info("Created IAM role %s.", role.name)
        role.attach_policy(PolicyArn=policy_arn)
        logging.info("Attached basic execution policy to role %s.", role.name)
    return role


def delete_role(iam_role) -> dict:
    try:
        for policy in iam_role.attached_policies.all():
            policy.detach_role(RoleName=iam_role.name)
        response = iam_role.delete()
    except ClientError as error:
        logging.error(error.response["Error"]["Message"])
        logging.error("Couldn't delete role %s", iam_role.name)
    else:
        logging.info("Deleted role '%s'", iam_role.name)
        return response


# if __name__ == '__main__':
# lambda_role_name = 'rps-lambda-role'
# new_role = create_iam_role(lambda_role_name)
