import boto3
import pprint
from botocore.exceptions import ClientError
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)

dynamodb_client = boto3.resource("dynamodb")

key_schema = [
    {"AttributeName": "phone_number", "KeyType": "HASH"},  # Partition key
    {"AttributeName": "round", "KeyType": "RANGE"},  # Partition key
]

attribute_definitions = [
    {"AttributeName": "phone_number", "AttributeType": "S"},
    {"AttributeName": "round", "AttributeType": "S"},
]


def create_table(table_name: str, key_schema: list, attribute_definitions: list):
    try:
        response = dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode="PAY_PER_REQUEST",
        )
    except ClientError as error:
        logging.error(error.response["Error"]["Message"])
        logging.error("Could not create dynamodb table %s.", table_name)
    else:
        # table_arn = response['TableDescription']['TableArn']
        logging.info("Dynamodb Table %s Created.", table_name)
        return response


def delete_table(table_name: str):
    try:
        response = dynamodb_client.delete_table(TableName=table_name)
    except ClientError as error:
        logging.error(error.response["Error"]["Message"])
        logging.error("Could not delete dynamodb table %s.", table_name)
    else:
        # table_arn = response['TableDescription']['TableArn']
        logging.info("Dynamodb Table %s deleted.", table_name)
        return response


# response = create_table("test_table2", key_schema, attribute_definitions)
# # table_arn = response['TableDescription']['TableArn']
if __name__ == "__main__":
    table = dynamodb_client.Table("test_table")
    pprint.pprint(table.__dict__)
    print()
    print("dir()\n", dir(table))
