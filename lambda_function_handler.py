import logging
import boto3
import uuid
import time
import json
import datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# insert new parameters after this line:

# insert new parameters before this line.

sns_client = boto3.client("sns")
db_resource = boto3.resource("dynamodb")
table = db_resource.Table(GAME_STATE_TABLE_NAME)
pinpoint_client = boto3.client("pinpoint")


def lambda_handler(event, context):

    logger.info("Event: %s", event)
    # grab the event from pinpoint
    try:
        pinpointEvent = json.loads(event["Records"][0]["Sns"]["Message"])
        msg_txt = pinpointEvent["messageBody"].lower().strip()
        fromNumber = pinpointEvent["originationNumber"]

        process_msg(msg_txt, fromNumber)

    except Exception as e:
        logger.exception(str(e))
        return {"statusCode": 500}
    else:
        return {"statusCode": 200}


### Rock Paper Scissors methods ####################################
def process_msg(msg, number) -> None:
    """
    Process the incoming message
    :param msg: a list consisting of [message text, phone number], both strings
    """
    if msg in ["rock", "paper", "scissors"]:
        process_throw(msg, number)
    elif msg == "test":
        send_sms(number, "ROCK PAPER SCISSORS:\nYour RPS game is up and running.")
    else:
        send_sms(
            number, f"ROCK PAPER SCISSORS:\nUnable to process input ... try again."
        )
        logger.error(f"ROCK PAPER SCISSORS:\nUnable to process input: {msg}")

class FailedToAcquireLock(Exception):
    pass
class FailedToReleaseLock(Exception):
    pass

def process_throw(current_throw, current_number):
    self_id = str(uuid.uuid4())
    lock_acquired = exponential_change_lock_retry(acquire_lock, "throw_lock", self_id)
    if lock_acquired:

        opponent = get_item({"state": "opponent"})

        if opponent:
            winner_message = determine_winner(
                [opponent["throw"], opponent["phone_number"]],
                [current_throw, current_number],
            )

            send_sms(
                opponent["phone_number"], "ROCK PAPER SCISSORS:\n" + winner_message
            )
            send_sms(
                current_number, "ROCK PAPER SCISSORS:\n" + winner_message
            )
            delete_item({"state": "opponent"})
            logger.info("Game completed: %s", winner_message)
        else:
            put_item(
                {
                    "state": "opponent",
                    "throw": current_throw,
                    "phone_number": current_number,
                }
            )
            send_sms(current_number, "ROCK PAPER SCISSORS:\nWaiting for opponent...")

        lock_released = exponential_change_lock_retry(
            release_lock, "throw_lock", self_id
        )
        if lock_released:
            pass
        else:
            logger.error("Failed to release lock %s", self_id)
            raise FailedToReleaseLock
    else:
        logger.exception("Failed to acquire lock %s", self_id)
        raise FailedToAcquireLock

def determine_winner(first_throw, second_throw):
    """
    input parameters are each a list with contents: ["throw", "phone_number"]
    returns a string of format "phone_number wins."
    """
    t1 = first_throw[0]
    t2 = second_throw[0]

    if t1 == t2:
        response = "Tie! No winner"
    elif t1 == "paper" and t2 == "rock":
        response = first_throw[1] + " wins."
    elif t1 == "scissors" and t2 == "rock":
        response = second_throw[1] + " wins."
    elif t1 == "rock" and t2 == "scissors":
        response = first_throw[1] + " wins."
    elif t1 == "paper" and t2 == "scissors":
        response = first_throw[1] + " wins."
    elif t1 == "scissors" and t2 == "paper":
        response = first_throw[1] + " wins."
    elif t1 == "rock" and t2 == "paper":
        response = first_throw[1] + " wins."
    else:
        response = "Something went wrong..."

    return response


### DB methods #####################################################
def put_item(item: dict) -> None:
    # item must at least have keys that match table primary keys
    try:
        table.put_item(Item=item)
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
    else:
        logger.info(f"DB entry made {item}")


def get_item(keys: dict) -> dict:
    # keys must have only the dict keys that match table primary keys
    try:
        response = table.get_item(Key=keys)
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
    else:
        if "Item" in response:
            logging.info(f"DB entry retrieved {keys}")
            return response["Item"]
        else:
            logging.info(f"No entry retrieved for get: {keys}")
            return None


def delete_item(keys: dict) -> None:
    # keys must have only the dict keys that match table primary keys
    try:
        table.delete_item(Key=keys)
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
    else:
        logger.info(f"DB item deleted made {keys}")


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
            return False
        else:
            raise
    else:
        logger.info("Lock acquired %s", self_id)
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
        logger.info("Lock released %s", self_id)
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

if __name__ == "__main__":
    # this 'unit' test needs to be run after setup.py constructs the file, 
    # or you'd need to add some parameters in temporarily. 
    with open('test/lambda_test_event.json') as file:
        event_json = file.read()
    event = json.loads(event_json)
    response = lambda_handler(event, {})
    response = lambda_handler(event, {})

    print(response)