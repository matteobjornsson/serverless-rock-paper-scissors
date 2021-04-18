import boto3
from botocore.exceptions import ClientError
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)

region = "us-east-1"

pinpoint_client = boto3.client("pinpoint", region_name=region)


def create_pinpoint_app(app_name: str) -> str:
    # create a pinpoint app 'rock_paper_scissors'
    try:
        response = pinpoint_client.create_app(
            CreateApplicationRequest={"Name": app_name, "tags": {}}
        )
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
    else:
        # grab the application ID to return.
        application_id = response["ApplicationResponse"]["Id"]
        logging.info("Pinpoint App Created %s.", application_id)
        # return the application ID for further modification.
        return application_id


def delete_pinpoint_app(application_id: str) -> dict:
    # Delete a pinpoint app
    try:
        response = pinpoint_client.delete_app(ApplicationId=application_id)
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
    else:
        logging.info("Pinpoint App Deleted %s.", application_id)
        return response



def enable_pinpoint_SMS(applicationID: str) -> dict:
    # enable SMS channel on Pinpoint app
    try:
        response = pinpoint_client.update_sms_channel(
            ApplicationId=applicationID, SMSChannelRequest={"Enabled": True}
        )
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
    else:
        logging.info("Pinpoint SMS Enabled %s.", str(response))
        return response