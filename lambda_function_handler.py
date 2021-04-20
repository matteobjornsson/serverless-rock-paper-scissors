import logging
import boto3
import re
import json
from botocore.exceptions import ClientError

db_table_name = "players"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# insert new parameters after this line:
db_table_name = "players"
# insert new parameters before this line.

sns_client = boto3.client("sns")
db_resource = boto3.resource("dynamodb")
table = db_resource.Table(db_table_name)
pinpoint_client = boto3.client("pinpoint")


def lambda_handler(event, context):

    logger.info("Event: %s", event)
    # grab the event from pinpoint
    pinpointEvent = json.loads(event["Records"][0]["Sns"]["Message"])
    msg_txt = pinpointEvent["messageBody"].lower().strip()
    fromNumber = pinpointEvent["originationNumber"]

    result = process_msg(msg_txt.lower().strip(), fromNumber)

    return {"statusCode": 200}


def process_msg(msg, number):
    """
    Process the incoming message
    :param msg: a list consisting of [message text, phone number], both strings
    """
    # first get all entries associated with phone number

    # matches on E.164 formatted phone numbers in the US
    US_phone_regex = re.compile("^(\+)(\d{11})$")
    if US_phone_regex.match(msg):
        # register player and their opponent
        # delete any old entries with different opponent
        # save (player, opponent, round) to db with round == 0
        # notify player they have been registered.
        pass
    elif msg in ["rock", "paper", "scissors"]:
        # process throw
        pass
    elif msg == "test":
        send_sms(number, "Your RPS game is up and running.")
    else:
        # log problem
        pass


def process_throw():
    # acquire lock
    #   if lock held by another process, wait?
    #   if timeout then notify player of failure
    # increment round
    # check if throw exists for same round and opponent
    #   if so, process throw and notify players of winner
    #       delete finished rounds for player and opponent
    #   if not, store throw, opponent, round
    #       notify player they are waiting for player 2
    # release lock
    pass


def put_item(item: dict):
    # item must at least have keys that match table primary keys
    try:
        response = table.put_item(Item=item)
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
    else:
        logger.info("DB entry made!")
        return response


def get_item(keys: dict) -> dict:
    # keys must have only the dict keys that match table primary keys
    try:
        item = table.get_item(Key=keys)
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
    else:
        logger.info("DB entry retrieved!")
        return item


def send_sms(phone_number: str, message: str) -> None:
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
        logger.info(str(response))
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
    else:
        logger.info("Message sent!")
