import boto3
import pprint
from botocore.exceptions import ClientError
import logging
logging.basicConfig(filename='pinpoint.log', level=logging.DEBUG)

region = "us-east-1"

client = boto3.client('pinpoint',region_name=region)

# create a pinpoint app 'rock_paper_scissors'
try:                                      
    response = client.create_app(
        CreateApplicationRequest={
            'Name': 'rock_paper_scissors',
            'tags':{}
        }
    )
except ClientError as e:
    logging.error(e.response['Error']['Message'])
else:
    success_msg = "Pinpoint App Created."
    logging.debug(success_msg)
    print(success_msg)

# grab the application ID from the 
applicationID = response['ApplicationResponse']['Id']

# enable SMS channel on Pinpoint app
try:
    response = client.update_sms_channel(
        ApplicationId=applicationID,
        SMSChannelRequest={
            'Enabled': True
            # 'SenderId': 'string',
            # 'ShortCode': 'string'
        }
    )
except ClientError as e:
    logging.error(e.response['Error']['Message'])
else:
    success_msg = "SMS Channel Enabled."
    logging.debug(success_msg)
    print(success_msg)


