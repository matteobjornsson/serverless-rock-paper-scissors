import boto3
from botocore.exceptions import ClientError
import logging
logging.basicConfig(filename='rps.log', level=logging.DEBUG)

region = "us-east-1"

client = boto3.client('pinpoint',region_name=region)

def create_pinpoint() -> str:
    # create a pinpoint app 'rock_paper_scissors'
    try:                                      
        response = client.create_app(
            CreateApplicationRequest={
                'Name': 'rock_paper_scissors',
                'tags':{}
            }
        )
        # grab the application ID to return. 
        applicationID = response['ApplicationResponse']['Id']
    except ClientError as e:
        logging.error(e.response['Error']['Message'])
    else:
        success_msg = "Pinpoint App Created."
        logging.info(success_msg)
        # return the application ID for further modification.    
        return applicationID        

def enable_pinpoint_SMS(applicationID: str) -> None:
    # enable SMS channel on Pinpoint app
    try:
        _ = client.update_sms_channel(
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
        logging.info(success_msg)
        print(success_msg)

