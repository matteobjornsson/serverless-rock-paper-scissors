import boto3
from botocore.exceptions import ClientError
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)


pinpoint_client = boto3.client("pinpoint")


def create_pinpoint_app(app_name: str) -> dict:
    # create a pinpoint app 'rock_paper_scissors'
    try:
        response = pinpoint_client.create_app(
            CreateApplicationRequest={"Name": app_name, "tags": {}}
        )
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
        logging.error("Could not create pinpoint app %s.", app_name)
    else:
        logging.info("Pinpoint App %s Created.", app_name)
        return response


def delete_pinpoint_app(application_id: str) -> dict:
    # Delete a pinpoint app
    try:
        response = pinpoint_client.delete_app(ApplicationId=application_id)
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
        logging.error("Could not delete pinpoint app %s.", application_id)
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
        logging.error("Could not enable pinpoint SMS.")
    else:
        logging.info("Pinpoint SMS Enabled.")
        return response


if __name__ == "__main__":
    app_name = "pinpoint_test_name"
    response = create_pinpoint_app(app_name)
    pinpoint_app_id = response["ApplicationResponse"]["Id"]
    response = create_pinpoint_app(app_name)
    delete_pinpoint_app(pinpoint_app_id)
