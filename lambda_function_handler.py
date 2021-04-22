import logging
import boto3
import re
import time
import json
import datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

db_table_name = "players"

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# insert new parameters after this line:

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


### Rock Paper Scissors methods ####################################
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


### DB methods #####################################################
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


### Pinpoint methods #####################################################
def send_sms(phone_number: str, message: str) -> None:
    try:
        response = pinpoint_client.send_messages(
            ApplicationId=PINPOINT_APP_ID,
            MessageRequest={
                "Addresses": {phone_number: {"ChannelType": "SMS"}},
                "MessageConfiguration": {
                    "SMSMessage": {"Body": message, "MessageType": "TRANSACTIONAL"}
                },
            },
        )
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
    else:
        delivery_status = response["MessageResponse"]["Result"][phone_number][
            "DeliveryStatus"
        ]
        if delivery_status == "SUCCESSFUL":
            logger.info(f"Message {message} sent to {phone_number} successfully.")
        else:
            logger.error(f"Message {message} failed to send to {phone_number}.")


### Lock methods #####################################################
def ms_timestamp() -> int:
    utc_epoch_time = datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)
    return int(utc_epoch_time.total_seconds() * 1000)


def get_lock_table(table_name: str):
    try:
        table = boto3.resource("dynamodb").Table(table_name)
    except ClientError as e:
        logger.exception("Could not get lock table.")
        raise
    else:
        return table


def acquire_lock(lock_name: str, self_id: str) -> bool:
    table = get_lock_table(LOCK_TABLE_NAME)
    try:
        table.put_item(
            Item={
                "lock_name": lock_name,
                "holder": self_id,
                "time_acquired": ms_timestamp(),  # number type
            },
            ConditionExpression=Attr("lock_name").not_exists()
            | Attr("time_acquired").lt(ms_timestamp() - LOCK_EXPIRATION_TIME_MS),
        )
    except ClientError as error:
        error_code = error.response["Error"]["Code"]
        if error_code == "ConditionalCheckFailedException":
            logger.error("Could not acquire lock.")
            return False
        else:
            raise
    else:
        logger.info("Lock acquired")
        return True


def release_lock(lock_name: str, self_id: str) -> bool:
    try:
        table = get_lock_table(LOCK_TABLE_NAME)
        table.delete_item(
            Key={"lock_name": lock_name}, ConditionExpression=Attr("holder").eq(self_id)
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        else:
            raise
    else:
        return True


def exponential_change_lock_retry(func, *func_args):
    """
    Retries acquire_lock or release_lock until lock changed or maximum desired time elapsed.
    """
    delay = INITIAL_LOCK_WAIT_SECONDS
    lock_changed = False
    while delay < MAX_LOCK_WAIT_SECONDS and not lock_changed:
        lock_changed = func(*func_args)
        if not lock_changed:
            logger.info(f"Waiting for {delay} to retry {func.__name__}.")
            time.sleep(delay)
            delay = delay * LOCK_RETRY_BACKOFF_MULTIPLIER
    return lock_changed
