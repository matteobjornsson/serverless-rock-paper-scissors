#
# Created on Thu Apr 22 2021
# Matteo Bjornsson
#
import boto3
from botocore.exceptions import ClientError
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)

pinpoint_client = boto3.client("pinpoint")


def create_pinpoint_app(app_name: str) -> dict:
    """
    Create a pinpoint app with the given name. 
    (pinpoint apps are uniquely defined by ID, not name. 
    One might create many of the same name)
    """
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
    """
    Delete pinpoint app by application ID (pinpoint apps are uniquely defined by ID, not name)
    """
    try:
        response = pinpoint_client.delete_app(ApplicationId=application_id)
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
        logging.error("Could not delete pinpoint app %s.", application_id)
    else:
        logging.info("Pinpoint App Deleted %s.", application_id)
        return response


def enable_pinpoint_SMS(applicationID: str) -> dict:
    """
    Enable SMS channel on the given pinpoint app via ID
    """
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


def send_SMS_message(phone_number: str, message: str, pinpoint_app_id: str) -> None:
    """
    Send an sms message to the given phone number using the given pinpoint app.
    :param phone_number: destination phone number
    :param message: message to send
    :param pinpoint_app_id: the id of the pinpoint app used to send the SMS
    """
    try:
        response = pinpoint_client.send_messages(
            ApplicationId=pinpoint_app_id,
            MessageRequest={
                "Addresses": {phone_number: {"ChannelType": "SMS"}},
                "MessageConfiguration": {
                    "SMSMessage": {"Body": message, "MessageType": "TRANSACTIONAL"}
                },
            },
        )
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
    else:
        result = response["MessageResponse"]["Result"][phone_number]
        if result["DeliveryStatus"] == "PERMANENT_FAILURE":
            logging.error("Message not delivered: %s", result)
        elif result["DeliveryStatus"] == "SUCCESSFUL":
            logging.info("Message sent!")
        else:
            logging.warn("Unknown delivery status of SMS message")


if __name__ == "__main__":
    # test create, enable, and text a number
    app_name = "pinpoint_test_name"
    response = create_pinpoint_app(app_name)
    pinpoint_app_id = response["ApplicationResponse"]["Id"]
    enable_pinpoint_SMS(pinpoint_app_id)
    send_SMS_message("+18001234567", "initial message", pinpoint_app_id)
    delete_pinpoint_app(pinpoint_app_id)
