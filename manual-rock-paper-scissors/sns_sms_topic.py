import boto3
import pprint
from botocore.exceptions import ClientError
import logging
logging.basicConfig(filename='sns.log', level=logging.DEBUG)

region = 'us-east-1'

client = boto3.client('sns',region_name=region)

try:
    response = client.create_topic(
        Name='rps_incoming_sms.fifo',
        Attributes={
            'FifoTopic': 'True',
            'ContentBasedDeduplication': 'True'
        },
        Tags=[]
    )
except ClientError as e:
    logging.error(e.response['Error']['Message'])
else:
    success_msg = "SNS Topic Created."
    logging.debug(success_msg)
    print(success_msg)

pprint.pprint(response)