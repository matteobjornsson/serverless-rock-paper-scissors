import logging
import boto3
import uuid
import json
from botocore.exceptions import ClientError

db_table_name = "players"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# insert new parameters after this line:


# TODO: get phone number and subscribe the recipient
def lambda_handler(event, context):
    logger.info("Event: %s", event)
    # grab the event from pinpoint
    pinpointEvent = json.loads(event["Records"][0]["Sns"]["Message"])
    # extract the throw text and origination phone number
    msg_txt = pinpointEvent["messageBody"].lower().strip()
    fromNumber = pinpointEvent["originationNumber"]
    # store them together
    incoming_msg = [msg_txt, fromNumber]

    sns_client = boto3.client("sns", region_name="us-east-1")
    response = sns_client.publish(
        TargetArn="arn:aws:sns:us-east-1:802108040626:rps_outgoing_sms_test",
        Message="The lambda function was invoked",
    )
    db_resource = boto3.resource("dynamodb")
    round = str(uuid.uuid4())
    table = db_resource.Table(db_table_name)
    try:
        response = table.put_item(
            Item={
                "phone_number": fromNumber,
                "round": round,
                "bonus": {"plot": "wow", "rating": "5/5"},
            }
        )
        logger.info(str(response))
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
    else:
        logger.info("DB entry made!")

    try:
        response = table.get_item(Key={"phone_number": fromNumber, "round": round})
        logger.info(str(response["Item"]))
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
    else:
        logger.info("DB entry retrieved!")

    message = "pinpoint test your message"

    # Create a new client and specify a region.
    client = boto3.client("pinpoint")
    try:
        response = client.send_messages(
            ApplicationId=applicationId,
            MessageRequest={
                "Addresses": {fromNumber: {"ChannelType": "SMS"}},
                "MessageConfiguration": {
                    "SMSMessage": {"Body": message, "MessageType": "TRANSACTIONAL"}
                },
            },
        )
        logging.info(str(response))
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
    else:
        logging.info("Message sent!")

    return {"statusCode": 200}
