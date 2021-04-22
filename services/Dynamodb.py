import pprint
import time
import boto3
import logging

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

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
    TODO: write function description
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
    TODO: write function description
    """
    try:
        table = dynamodb_client.describe_table(TableName=table_name)
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
        logging.exception("Couldn't get table %s.", table_name)
        raise
    else:
        # rearrange response to match create_table() return
        return table


def delete_table(table_name: str) -> dict:
    """
    TODO: write function description
    """
    delay = INITIAL_WAIT_SECONDS
    while delay < MAX_WAIT_SECONDS:
        try:
            response = dynamodb_client.delete_table(TableName=table_name)
        except ClientError as error:
            if (
                error.response["Error"]["Code"] == "ResourceInUseException"
                and delay < MAX_WAIT_SECONDS
            ):
                logging.error("Cannot delete yet table in use ...")
                time.sleep(delay)
                delay = delay * RETRY_BACKOFF_MULTIPLIER
            else:
                logging.error(error.response["Error"]["Code"])
                logging.error("Could not delete dynamodb table %s.", table_name)
        else:
            # table_arn = response['TableDescription']['TableArn']
            logging.info("Dynamodb Table %s deleted.", table_name)
            return response


def table_exists(table_name: str) -> bool:
    try:
        dynamodb_client.describe_table(TableName=table_name)
        return True
    except ClientError as error:
        if error.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        else:
            raise

def put_item(table_name: str, item: dict):
    # item must at least have keys that match table primary keys
    try:
        table = dynamodb_resource.Table(table_name)
        response = table.put_item(Item=item)
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
    else:
        logging.info("DB entry made!")
        return response


def get_item(table_name: str, keys: dict) -> dict:
    # keys must have only the dict keys that match table primary keys
    try:
        table = dynamodb_resource.Table(table_name)
        item = table.get_item(Key=keys)
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
    else:
        logging.info("DB entry retrieved!")
        return item

def key_eq_query(table_name: str, key: str, value: str) -> dict:
    table = dynamodb_resource.Table(table_name)
    response = table.query(
        KeyConditionExpression=Key(key).eq(value)
    )
    return response['Items']


# response = create_table("test_table2", key_schema, attribute_definitions)
# # table_arn = response['TableDescription']['TableArn']
if __name__ == "__main__":

    db_key_schema = [
        {"AttributeName": "phone_number", "KeyType": "HASH"},  # Partition key
        {"AttributeName": "round", "KeyType": "RANGE"},  # Partition key
    ]

    db_attribute_definitions = [
        {"AttributeName": "phone_number", "AttributeType": "S"},
        {"AttributeName": "round", "AttributeType": "S"},
    ]

    table_name = "test_table"
    table = create_table(table_name, db_key_schema, db_attribute_definitions)
    print(table.name)
    # response = dynamodb_client.describe_table(TableName=table_name)
    # pprint.pprint(response)
    put_item(table_name, {"phone_number":"+18001234567","round":"1", "throw":"rock"})
    put_item(table_name, {"phone_number":"+18001234567","round":"1", "throw":"paper"})
    put_item(table_name, {"phone_number":"+18001234567","round":"2"})
    response = put_item(table_name, {"phone_number":"+18001234567","round":"2", "throw":"scissors"})
    print(response)

    delete_table(table_name)
