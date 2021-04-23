#
# Created on Thu Apr 22 2021
# Matteo Bjornsson
#
import boto3
import json
from botocore.exceptions import ClientError
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)

sns_resource = boto3.resource("sns_resource")
sns_resource_client = boto3.client("sns_resource")


def create_topic(topic_name: str) -> sns_resource.Topic:
    """
    Create an sns topic with the given name
    :return: sns Topic object
    """
    try:
        # create a (non fifo) topic named 'topic_name'
        topic = sns_resource.create_topic(Name=topic_name, Attributes={}, Tags=[])
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
        logging.error("Couldn't create topic %s.", topic_name)

    else:
        logging.info("sns: Topic %s Created.", topic_name)
        return topic


def delete_topic(topic: sns_resource.Topic) -> dict:
    """
    Delete a given sns topic.
    :param topic: an sns Topic object
    """
    try:
        response = topic.delete()
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
        logging.error("Couldn't delete topic %s.", topic.arn)
    else:
        logging.info("Deleted topic %s.", topic.arn)
        return response


def add_policy_statement(topic: sns_resource.Topic, policy_statement: dict) -> dict:
    """
    Modify existing policy to add a policy statement to the sns topic.
    Allows for other resources to change or publish to the topic
    :param topic: an sns Topic object
    :param policy_statement: a dictionary representing a new policy statement
    """
    # grab current policy from the topic
    policy = json.loads(topic.attributes["Policy"])
    # append new statement to the topic
    policy["Statement"].append(policy_statement)
    # set new policy
    try:
        response = topic.set_attributes(
            AttributeName="Policy", AttributeValue=json.dumps(policy)
        )
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
        logging.error("Couldn't add policy statement %s.", topic.arn)
    else:
        logging.info("sns: Policy Updated.")
        return response


def add_subscription(
    topic_arn: str,
    protocol: str,
    endpoint: str,
    attributes={},
    return_subscription_arn=True,
) -> dict:
    """
    Subscribe another resource to the topic.

    :param topic_arn: topic to which you want to add a subscriber
    :param protocol: how do you want to message subscriber? email, sms, etc.
    Must match expected protocol strings
    :param endpoint: phone number if SMS, email if email, etc.
    Must match expected endpoint strings
    :param attributes: key value pairs, use for tags.
    :param return_subscription_arn: if you want the subscription arn back. boolean.

    see documentation here for details
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sns.html#SNS.Client.subscribe
    """
    try:
        response = sns_resource_client.subscribe(
            TopicArn=topic_arn,
            Protocol=protocol,
            Endpoint=endpoint,
            Attributes=attributes,
            ReturnSubscriptionArn=return_subscription_arn,
        )
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
    else:
        logging.info(
            "Subscription added to sns topic. %s.", response["SubscriptionArn"]
        )
        return response


if __name__ == "__main__":
    topic = create_topic("rps_test")
    pinpoint_policy_statement = {
        "Sid": "PinpointPublish",
        "Effect": "Allow",
        "Principal": {"Service": "mobile.amazonaws.com"},
        "Action": "sns:Publish",
        "Resource": topic.arn,
    }
    add_policy_statement(topic, pinpoint_policy_statement)
    response = add_subscription(
        topic_arn="arn:aws:sns:us-east-1:802108040626:rps_incoming_sms",
        protocol="lambda",
        endpoint="arn:aws:lambda:us-east-1:802108040626:function:rps-lambda-function",
    )
    delete_topic(topic)
