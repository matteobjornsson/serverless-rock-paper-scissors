import boto3
import pprint
import json
from botocore.exceptions import ClientError
import logging
logging.basicConfig(filename='sns.log', level=logging.DEBUG)

region = 'us-east-1'
sns = boto3.resource('sns')
topic_name = 'rps_incoming_sms'


# create an SNS topic 
def create_fifo_topic() -> str:
    try:
        response = sns.create_topic(
            Name=topic_name,
            Attributes={
                'FifoTopic': 'True',
                'ContentBasedDeduplication': 'True'
            },
            Tags=[]
        )
        topic_arn = response['TopicArn']
    except ClientError as e:
        logging.error(e.response['Error']['Message'])
    else:
        success_msg = "SNS Topic Created."
        logging.debug(success_msg)
        print(success_msg)
        return topic_arn

# create an SNS topic 
def create_topic() -> sns.Topic:
    try:
        topic = sns.create_topic(
            Name=topic_name,
            Attributes={},
            Tags=[]
        )
    except ClientError as e:
        logging.error(e.response['Error']['Message'])
    else:
        success_msg = "SNS Topic Created."
        logging.debug(success_msg)
        print(success_msg)
        return topic

def add_policy_statement(topic: sns.Topic, policy_statement: dict) -> None:
    # grab current policy
    policy = json.loads(topic.attributes['Policy'])
    # append new statement
    policy['Statement'].append(policy_statement)
    # set new policy
    try:
        topic.set_attributes(
            AttributeName='Policy',
            AttributeValue=json.dumps(policy)
        )
    except ClientError as e:
        logging.error(e.response['Error']['Message'])
    else:
        success_msg = "SNS Policy Updated."
        logging.debug(success_msg)
        print(success_msg)

if __name__ == '__main__':
    topic = create_topic()
    pinpoint_policy_statement = {
            "Sid": "PinpointPublish",
            "Effect": "Allow",
            "Principal": {
                "Service": "mobile.amazonaws.com"
            },
            "Action": "sns:Publish",
            "Resource": topic.arn
            }
    add_policy_statement(topic, pinpoint_policy_statement)