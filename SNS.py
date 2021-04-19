import boto3
import pprint
import json
from botocore.exceptions import ClientError
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)

sns = boto3.resource("sns")
sns_client = boto3.client("sns")

# create an SNS topic
def create_topic(topic_name: str) -> sns.Topic:
    try:
        # create a simple (non fifo) topic named 'topic_name'
        topic = sns.create_topic(Name=topic_name, Attributes={}, Tags=[])
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
    else:
        logging.info("SNS: Topic %s Created.", topic.name)
        return topic


def delete_topic(topic: sns.Topic) -> dict:
    try:
        response = topic.delete()
    except ClientError:
        logging.error("Couldn't delete topic %s.", topic.arn)
    else:
        logging.info("Deleted topic %s.", topic.arn)
        return response


def add_policy_statement(topic: sns.Topic, policy_statement: dict) -> dict:
    # grab current policy
    policy = json.loads(topic.attributes["Policy"])
    # append new statement
    policy["Statement"].append(policy_statement)
    # set new policy
    try:
        response = topic.set_attributes(
            AttributeName="Policy", AttributeValue=json.dumps(policy)
        )
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
    else:
        logging.info("SNS: Policy %s Updated.", str(response))
        return response


def add_subscription(
    topic_arn: str,
    protocol: str,
    endpoint: str,
    attributes={},
    return_subscription_arn=True,
) -> dict:
    try:
        response = sns_client.subscribe(
            TopicArn=topic_arn,
            Protocol=protocol,
            Endpoint=endpoint,
            Attributes=attributes,
            ReturnSubscriptionArn=return_subscription_arn,
        )
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
    else:
        logging.info("Subscription added to SNS topic. %s.", str(response))
        return response


if __name__ == "__main__":
    # topic = create_topic('rps_test')
    # pinpoint_policy_statement = {
    #         "Sid": "PinpointPublish",
    #         "Effect": "Allow",
    #         "Principal": {
    #             "Service": "mobile.amazonaws.com"
    #         },
    #         "Action": "sns:Publish",
    #         "Resource": topic.arn
    #         }
    # add_policy_statement(topic, pinpoint_policy_statement)
    response = add_subscription(
        topic_arn="arn:aws:sns:us-east-1:802108040626:rps_incoming_sms",
        protocol="lambda",
        endpoint="arn:aws:lambda:us-east-1:802108040626:function:rps-lambda-function",
    )
