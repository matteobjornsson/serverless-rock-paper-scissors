import boto3
import json
from botocore.exceptions import ClientError
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)

dynamodb_client = boto3.client("dynamodb")

key_schema=[
    {
        'AttributeName': 'phone_number',
        'KeyType': 'HASH'  # Partition key
    },
    {
        'AttributeName': 'round',
        'KeyType': 'HASH'  # Partition key
    }

]

attribute_definitions=[
    {
        'AttributeName': 'phone_number',
        'AttributeType': 'S'
    },
    {
        'AttributeName': 'round',
        'AttributeType': 'S'
    },
    {
        'AttributeName': 'throw',
        'AttributeType': 'S'
    }
]

def create_table(table_name: str, key_schema: list, attribute_definitions: list):
    try:
        response = dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions
        )
    except ClientError as error:
        logging.error(error.response["Error"]["Message"])
        logging.error("Could not create dynamodb table %s.", table_name)
    else:
        logging.info("Dynamodb Table %s Created.", table_name)
        return response

