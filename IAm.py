# file contents adapted from AWS example
# https://docs.aws.amazon.com/code-samples/latest/catalog/python-lambda-boto_client_examples-lambda_basics.py.html

from Dynamodb import create_table
import json
import boto3
import pprint
from botocore.exceptions import ClientError
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)

iam_resource = boto3.resource("iam")
sts_client = boto3.client("sts")


def create_role(
    iam_role_name: str, assume_role_policy_json: str, policy_arns: list
) -> iam_resource.Role:  # return iam role object
    """
    TODO: write function description
    """
    try:
        role = iam_resource.create_role(
            RoleName=iam_role_name,
            AssumeRolePolicyDocument=assume_role_policy_json,
        )
        iam_resource.meta.client.get_waiter("role_exists").wait(RoleName=iam_role_name)

        for arn in policy_arns:
            role.attach_policy(PolicyArn=arn)

    except ClientError as error:
        if error.response["Error"]["Code"] == "EntityAlreadyExists":
            role = iam_resource.Role(iam_role_name)
            logging.warning("The role %s already exists. Using it.", iam_role_name)
            return role
        else:
            logging.error(error.response["Error"]["Message"])
            logging.exception(
                "Couldn't create role %s or attach policy %s.",
                iam_role_name,
                str(policy_arns),
            )
            raise
    else:
        logging.info("Created IAM role %s.", role.name)
        logging.info("Attached basic execution policy to role %s.", role.name)
        return role


def create_policy(policy_name: str, policy_json: str) -> iam_resource.Policy:
    """
    TODO: write function description
    """
    try:
        policy = iam_resource.create_policy(
            PolicyName=policy_name, PolicyDocument=policy_json
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "EntityAlreadyExists":
            policy = get_policy_by_name(policy_name)
            logging.warning("The policy %s already exists. Using it.", policy.arn)
            return policy
        else:
            logging.error(error.response["Error"]["Message"])
            logging.exception("Couldn't create policy %s", policy_name)
            raise
    else:
        logging.info("Created Policy '%s'", policy_name)
        return policy


def get_policy_by_name(policy_name: str) -> iam_resource.Policy:
    """
    TODO: write function description
    """
    account_id = sts_client.get_caller_identity()["Account"]
    policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
    policy = iam_resource.Policy(policy_arn)
    return policy


def delete_role(iam_role) -> dict:
    """
    TODO: write function description
    """
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


def delete_policy(iam_policy) -> dict:
    """
    TODO: write function description
    """
    try:
        response = iam_policy.delete()
    except ClientError as error:
        logging.error(error.response["Error"]["Message"])
        logging.error("Couldn't delete policy %s", iam_policy.arn)
    else:
        logging.info("Deleted role '%s'", iam_policy.arn)
        return response


# if __name__ == '__main__':
#     policy_json_file = '/home/matteo/repos/serverless-rock-paper-scissors/lambda_policy.json'
#     with open(policy_json_file) as file:
#         policy_json = file.read()
#     policy_name = 'test_policy'
#     policy = create_policy(policy_name,  policy_json)
#     print("dir()\n", dir(policy))
#     print("arn: ", policy.arn)
#     policy.delete()
