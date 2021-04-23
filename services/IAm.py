#
# Created on Thu Apr 22 2021
# Matteo Bjornsson
#
import boto3
from botocore.exceptions import ClientError
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)

iam_resource = boto3.resource("iam")
sts_client = boto3.client("sts")


def create_role(
    iam_role_name: str, assume_role_policy_json: str, policy_arns: list
) -> iam_resource.Role:
    """
    Create an IAM role with a given policy.

    :param assume_role_policy_json: A json string that represents the assume
    role policy defining what resources are allowed to assume the role.
    :param policy_arns: a list of strings representing existing policy arns to
    also attach to the role
    :return: IAM role object

    This method was adapted from the create_iam_role_for_lambda() method found here:
    https://docs.aws.amazon.com/code-samples/latest/catalog/python-lambda-boto_client_examples-lambda_basics.py.html
    """
    try:
        role = iam_resource.create_role(
            RoleName=iam_role_name,
            AssumeRolePolicyDocument=assume_role_policy_json,
        )
        # wait for the creation to complete
        iam_resource.meta.client.get_waiter("role_exists").wait(RoleName=iam_role_name)
        # attach the additional supplied policies
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
        logging.info("Attached policies %s to role %s.", policy_arns, role.name)
        return role


def create_policy(policy_name: str, policy_json: str) -> iam_resource.Policy:
    """
    Create an IAM policy of given name and json description.
    Policies define permissions in AWS and can be associated with IAM roles.
    :param policy_json: just be a valid policy json string
    :return: IAM Policy object
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
    Get an existing policy by name.
    :return: IAM Policy object
    """
    # sts provides the account number of the current credentials
    account_id = sts_client.get_caller_identity()["Account"]
    # policy arns consist of an account id and policy name
    policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
    # policies are created in the Python SDK via their arn
    policy = iam_resource.Policy(policy_arn)
    return policy


def delete_role(iam_role) -> dict:
    """
    Delete a role.
    :param iam_role: this parameter is an IAM role object, such as returned
    by create_role()
    """
    try:
        # remove all policies before deleting role
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
    Delete a role.
    :param iam_policy: this parameter is an IAM policy object, such as returned
    by create_policy()
    """
    try:
        response = iam_policy.delete()
    except ClientError as error:
        logging.error(error.response["Error"]["Message"])
        logging.error("Couldn't delete policy %s", iam_policy.arn)
    else:
        logging.info("Deleted policy '%s'", iam_policy.arn)
        return response


if __name__ == "__main__":
    # brief functionality test with delete() cleanup at end
    policy_json_file = "./policy/lambda_policy.json"
    with open(policy_json_file) as file:
        policy_json = file.read()
    policy_name = "test_policy"
    policy = create_policy(policy_name, policy_json)
    print("new policy arn: ", policy.arn)
    policy.delete()
