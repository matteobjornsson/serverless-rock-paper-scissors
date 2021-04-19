import pprint
import time
import boto3
import json
from botocore.exceptions import ClientError
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)

dynamodb_client = boto3.client("dynamodb")
# parameters for exponential backoff
initial_wait = 1
max_wait = 9
retry_backoff = 2


def create_table(
    table_name: str, key_schema: list, attribute_definitions: list
) -> dict:
    """
    TODO: write function description
    """
    try:
        response = dynamodb_client.create_table(
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
        # table_arn = response['TableDescription']['TableArn']
        logging.info("Dynamodb Table %s Created.", table_name)
        return response


def get_table(table_name: str) -> dict:
    """
    TODO: write function description
    """
    try:
        response = dynamodb_client.describe_table(TableName=table_name)
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
        logging.exception("Couldn't get table %s.", table_name)
        raise
    else:
        # rearrange response to match create_table() return
        return {"TableDescription": response["Table"]}


def delete_table(table_name: str) -> dict:
    """
    TODO: write function description
    """
    delay = initial_wait
    while delay < max_wait:
        try:
            response = dynamodb_client.delete_table(TableName=table_name)
        except ClientError as error:
            if (
                error.response["Error"]["Code"] == "ResourceInUseException"
                and delay < max_wait
            ):
                logging.error("Cannot delete yet table in use ...")
                time.sleep(delay)
                delay = delay * retry_backoff
            else:
                logging.error(error.response["Error"]["Code"])
                logging.error("Could not delete dynamodb table %s.", table_name)
        else:
            # table_arn = response['TableDescription']['TableArn']
            logging.info("Dynamodb Table %s deleted.", table_name)
            return response


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
    response = create_table(table_name, db_key_schema, db_attribute_definitions)
    pprint.pprint(response)
    response = create_table(table_name, db_key_schema, db_attribute_definitions)
    # response = dynamodb_client.describe_table(TableName=table_name)
    # pprint.pprint(response)
    print()
    delete_table(table_name)
