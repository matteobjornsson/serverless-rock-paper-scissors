import pprint
import time
import boto3
import logging

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.conditions import Attr

logging.basicConfig(filename="rps.log", level=logging.INFO)


# parameters for exponential backoff
RETRY_BACKOFF_MULTIPLIER = 2
INITIAL_WAIT_SECONDS = 1
MAX_WAIT_SECONDS = 9  # only wait < 9s for funciton creation before giving up.

dynamodb_client = boto3.client("dynamodb")
dynamodb_resource = boto3.resource("dynamodb")


def create_table(
    table_name: str, key_schema: list, attribute_definitions: list
) -> dynamodb_resource.Table:
    """
    Create a dynamoDB table named 'table_name.'
    Tables must have unique names within regions.
    param @key_schema and @attribute_definitions define the primary key and
    must follow the restrictions outlined here:
    https://docs.amazonaws.cn/en_us/amazondynamodb/latest/developerguide/HowItWorks.CoreComponents.html#HowItWorks.CoreComponents.PrimaryKey
    :return: Returns a boto3 dynamodb resource Table object
    """
    try:
        table = dynamodb_resource.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode="PAY_PER_REQUEST",
        )
    except ClientError as error:
        logging.error(error.response["Error"]["Code"])
        if error.response["Error"]["Code"] == "ResourceInUseException":
            logging.warning("The table %s already exists or in use.", table_name)
            return get_table(table_name)
        else:
            logging.error(error.response["Error"]["Code"])
            logging.exception("Could not create dynamodb table %s.", table_name)
            raise
    else:
        print(f"Waiting for table {table_name} to be created ...")
        table.wait_until_exists()
        logging.info("Dynamodb Table %s Created.", table_name)
        return table


def get_table(table_name: str) -> dynamodb_resource.Table:
    """
    Get a table by name and return a Table object
    """
    try:
        table = dynamodb_client.describe_table(TableName=table_name)
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
        logging.exception("Couldn't get table %s.", table_name)
        raise
    else:
        return table


def delete_table(table_name: str) -> dict:
    """
    Delete a table by name.
    Deletes must wait if the resource is in use, either because recently created
    or because another process is accessing it. Therefore delete is retried
    on an exponential backoff basis.
    """
    delay = INITIAL_WAIT_SECONDS
    while delay < MAX_WAIT_SECONDS:
        try:
            response = dynamodb_client.delete_table(TableName=table_name)
        except ClientError as error:
            if error.response["Error"]["Code"] == "ResourceInUseException":
                logging.error("Cannot delete yet, table in use ...")
                time.sleep(delay)
                # exponential backoff, increase retry time
                delay = delay * RETRY_BACKOFF_MULTIPLIER
            else:
                next_delay = delay * RETRY_BACKOFF_MULTIPLIER
                if next_delay > MAX_WAIT_SECONDS:
                    # if the max wait time was exceeded, give up and log error
                    logging.error(error.response["Error"]["Code"])
                    logging.error("Could not delete dynamodb table %s.", table_name)
        else:
            logging.info("Dynamodb Table %s deleted.", table_name)
            return response


def table_exists(table_name: str) -> bool:
    """
    Check if a table exists by name.
    """
    try:
        dynamodb_client.describe_table(TableName=table_name)
        return True
    except ClientError as error:
        if error.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        else:
            raise


def put_item(table_name: str, item: dict) -> dict:
    """
    Put an item into a table of the given name.
    Item is a dict that must at minimum contain the primary key (one or two
    parameters) but can contain arbitrary additional entries to store
    """
    try:
        table = dynamodb_resource.Table(table_name)
        response = table.put_item(Item=item)
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
    else:
        logging.info(f"DB entry made {item}")
        return response


def get_item(table_name: str, keys: dict) -> dict:
    """
    Item is a dict that must contain only the primary key (all items are
    uniquely defined by their primary key).
    :return: Returns the item in dictionary form, or None if no such item exists
    """
    try:
        table = dynamodb_resource.Table(table_name)
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


if __name__ == "__main__":
    # the following code tests the functionality of this file.
    db_key_schema = [
        {"AttributeName": "phone_number", "KeyType": "HASH"},  # Partition key
        {"AttributeName": "round", "KeyType": "SORT"},  # Sort key
    ]

    db_attribute_definitions = [
        {"AttributeName": "phone_number", "AttributeType": "S"},
        {"AttributeName": "round", "AttributeType": "N"},
    ]

    table_name = "test_table"
    table = create_table(table_name, db_key_schema, db_attribute_definitions)
    response = dynamodb_client.describe_table(TableName=table_name)
    pprint.pprint(response)
    put_item(table_name, {"phone_number": "+18001234467", "round": 1, "throw": "rock"})
    put_item(table_name, {"phone_number": "+18001234567", "round": 1, "throw": "paper"})
    put_item(table_name, {"phone_number": "+18001234467", "round": 2, "throw": "rock"})
    response = put_item(
        table_name, {"phone_number": "+18001234567", "round": 2, "throw": "scissors"}
    )
    pprint.pprint(response)
    item = get_item(table_name, {"phone_number": "+18001234567", "round": "1"})
    if item:
        print("Item retrieved: ", item)
    else:
        print("no item")
