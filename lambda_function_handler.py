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

# the following line tells the setup script where to insert relevant parameters
# such as the new pinpoint app id and all errored references below. 
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
        if LOCKING:
            process_throw_with_locking(msg, number)
        else:
            process_throw_without_locking(msg, number)
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


def process_throw_with_locking(current_throw, current_number):
    """
    Given a throw and a number it belongs to (both strings), 
    determine the winner or store throw. 
    """
    self_id = str(uuid.uuid4())
    # acquire lock to prevent other lambda functions from messing with the game
    # state while processing throw. Keep trying for exponential retry time.
    lock_acquired = exponential_retry_acquire_lock("throw_lock", self_id)
    if lock_acquired:

        opponent = get_item({"state": "opponent"})
        # if get_item returns an opponent, it means there was one stored.
        if opponent:
            # determine the winner and text players
            winner_message = determine_winner(
                [opponent["throw"], opponent["phone_number"]],
                [current_throw, current_number],
            )

            send_sms(
                opponent["phone_number"], "ROCK PAPER SCISSORS:\n" + winner_message
            )
            send_sms(current_number, "ROCK PAPER SCISSORS:\n" + winner_message)
            # delete the game state for next round. 
            delete_item({"state": "opponent"})
            logger.info("Game completed.")
        # otherwise get_item returned None, indicating no previous game state stored. 
        else:
            # therefore store the new game state. 
            put_item(
                {
                    "state": "opponent",
                    "throw": current_throw,
                    "phone_number": current_number,
                }
            )
            # notify the player the game is waiting for another throw
            send_sms(current_number, "ROCK PAPER SCISSORS:\nWaiting for opponent...")
        # release the lock. 
        lock_released = release_lock("throw_lock", self_id)
        if lock_released:
            pass
        else:
            logger.error("Failed to release lock %s", self_id)
            raise FailedToReleaseLock
    else:
        # under normal circumstances acquire lock is very unlikely to fail.
        logger.exception("Failed to acquire lock %s", self_id)
        raise FailedToAcquireLock


def process_throw_without_locking(current_throw, current_number):
    # same as above but without locking. 
    opponent = get_item({"state": "opponent"})

    if opponent:
        winner_message = determine_winner(
            [opponent["throw"], opponent["phone_number"]],
            [current_throw, current_number],
        )

        send_sms(opponent["phone_number"], "ROCK PAPER SCISSORS:\n" + winner_message)
        send_sms(current_number, "ROCK PAPER SCISSORS:\n" + winner_message)

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
    # see Dynamodb.py file for more info
    try:
        table.put_item(Item=item)
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
    else:
        logger.info(f"DB entry made {item}")


def get_item(keys: dict) -> dict:
    # keys must have only the dict keys that match table primary keys
    # see Dynamodb.py file for more info
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
    # keys must have only the dict keys that match table primary key    
    # see Dynamodb.py file for more info
    try:
        table.delete_item(Key=keys)
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
    else:
        logger.info(f"DB item deleted made {keys}")


### Pinpoint methods #####################################################
def send_sms(phone_number: str, message: str) -> None:
    # send an SMS to the given number. See Pinpoint.py file for more details.
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
    """
    Method that returns time since epoch in milliseconds. Allows for easy math
    determining passage of time at the millisecond level.
    """
    utc_epoch_time = datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)
    return int(utc_epoch_time.total_seconds() * 1000)


def get_lock_table(table_name: str):
    """
    Get the table used for acquiring and releasing named locks.
    This function assumes the existence of the table. 
    """
    try:
        table = boto3.resource("dynamodb").Table(table_name)
    except ClientError as e:
        logger.exception("Could not get lock table.")
        raise
    else:
        return table


def acquire_lock(lock_name: str, self_id: str) -> bool:
    """
    Acquire named lock from the lock table, identify self with id string.

    requesters are uniquely identified by a UUID given to each function invocation.
    """
    table = get_lock_table(LOCK_TABLE_NAME)
    try:
        # Conditional expression is used to ensure locks are acquired atomically.
        table.put_item(
            Item={
                "lock_name": lock_name,
                "holder": self_id,
                "time_acquired": ms_timestamp(),  # number type
            },
            # requester only gets the lock if it does not exist (exists if held by another function)
            # or if the lock has expired.
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
    """
    Release the named lock.

    Locks should only be releasable if acquired. UUID function ids are used to 
    uniquely differentiate holders. One cannot release a lock not held without
    guessing a UUID correctly.
    """
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


def exponential_retry_acquire_lock(lock_name: str, self_id: str):
    """
    Retries acquire_lock until lock acquired or maximum desired time elapsed.
    """
    delay = INITIAL_LOCK_WAIT_SECONDS
    lock_acquired = False
    while delay < MAX_LOCK_WAIT_SECONDS and not lock_acquired:
        lock_acquired = acquire_lock(lock_name, self_id)
        if not lock_acquired:
            logger.info(f"Waiting for {delay} to retry lock acquire.")
            time.sleep(delay)
            delay = delay * LOCK_RETRY_BACKOFF_MULTIPLIER
    return lock_acquired


if __name__ == "__main__":
    # this 'unit' test needs to be run after setup.py constructs the file,
    # or you'd need to add some parameters in temporarily.
    from threading import Thread

    with open("test/lambda_test_event.json") as file:
        event_json = file.read()
    # Start two threads at the same time to demo locking
    event = json.loads(event_json)
    t1 = Thread(
        target=lambda_handler,
        args=(
            event,
            {},
        ),
    )
    t2 = Thread(
        target=lambda_handler,
        args=(
            event,
            {},
        ),
    )
    t1.start()
    t2.start()
