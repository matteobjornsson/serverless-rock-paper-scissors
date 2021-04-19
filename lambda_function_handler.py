import logging
import boto3
import uuid
from botocore.exceptions import ClientError

db_table_name = "players"

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# s3_bucket_name = "rock-paper-scissors-csci566"
# sns_outgoing_arn = "arn:aws:sns:us-east-1:802108040626:game_result"


# The AWS Region that you want to use to send the message. For a list of
# AWS Regions where the Amazon Pinpoint API is available, see
# https://docs.aws.amazon.com/pinpoint/latest/apireference/
region = "us-east-1"

# The phone number or short code to send the message from. The phone number
# or short code that you specify has to be associated with your Amazon Pinpoint
# account. For best results, specify long codes in E.164 format.

# TODO: NEED TO SET UP THIS PROGRAMMATICALLY.
originationNumber = "+18339852687"

# The recipient's phone number.  For best results, you should specify the
# phone number in E.164 format.
destinationNumber = "+18001234567"

# The content of the SMS message.
message = "got your message"

# The Amazon Pinpoint project/application ID to use when you send this message.
# Make sure that the SMS channel is enabled for the project or application
# that you choose.
# TODO: NEED TO SET UP THIS PROGRAMMATICALLY.
applicationId = "d0a40b1dbab648a189444f8808e21e1e"

# The type of SMS message that you want to send. If you plan to send
# time-sensitive content, specify TRANSACTIONAL. If you plan to send
# marketing-related content, specify PROMOTIONAL.
messageType = "TRANSACTIONAL"

# The registered keyword associated with the originating short code.
# TODO: NEED TO SET UP THIS PROGRAMMATICALLY.
registeredKeyword = "keyword_802108040626"

# The sender ID to use when sending the message. Support for sender ID
# varies by country or region. For more information, see
# https://docs.aws.amazon.com/pinpoint/latest/userguide/channels-sms-countries.html
senderId = "MySenderID"

# TODO: get phone number and subscribe the recipient
def lambda_handler(event, context):
    logger.info("Event: %s", event)
    # # grab the event from pinpoint
    # pinpointEvent = json.loads(event["Records"][0]["Sns"]["Message"])
    # # extract the throw text and origination phone number
    # msg_txt = pinpointEvent["messageBody"].lower().strip()
    # fromNumber = pinpointEvent["originationNumber"]
    # # store them together
    # incoming_msg = [msg_txt, fromNumber]
    sns_client = boto3.client("sns", region_name="us-east-1")
    response = sns_client.publish(
        TargetArn="arn:aws:sns:us-east-1:802108040626:rps_outgoing_sms_test",
        Message="The lambda function was invoked",
    )

    db_resource = boto3.resource("dynamodb")
    round = str(uuid.uuid4())
    table = db_resource.Table(db_table_name)
    try:
        response = table.put_item(
            Item={
                "phone_number": originationNumber,
                "round": round,
                "bonus": {"plot": "wow", "rating": "5/5"},
            }
        )
        logger.info(str(response))
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
    else:
        logger.info("DB entry made!")

    try:
        response = table.get_item(
            Key={"phone_number": originationNumber, "round": round}
        )
        logger.info(str(response["Item"]))
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
    else:
        logger.info("DB entry retrieved!")

    # Create a new client and specify a region.
    client = boto3.client("pinpoint", region_name=region)
    try:
        response = client.send_messages(
            ApplicationId=applicationId,
            MessageRequest={
                "Addresses": {destinationNumber: {"ChannelType": "SMS"}},
                "MessageConfiguration": {
                    "SMSMessage": {
                        "Body": message,
                        "Keyword": registeredKeyword,
                        "MessageType": messageType,
                        "OriginationNumber": originationNumber,
                        "SenderId": senderId,
                    }
                },
            },
        )
        logger.info(str(response))
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
    else:
        logger.info("Message sent!")

    return {"statusCode": 200}

    # s3 = boto3.resource("s3")
    # # an object is defined by its bucket and key, irrelevant of if it exists or not.
    # object = s3.Object(s3_bucket_name, "/throwTEST.txt")

    # # Try to get existing throw
    # try:
    #     # this will throw an exception if there is no throw already stored on the s3 bucket
    #     saved_object = object.get()
    #     # if the previous line succeeds, we have everything we need to play.

    #     # load the list object that contains throw string and phone number string
    #     saved_throw = json.loads(saved_object["Body"].read().decode("utf-8"))
    #     # debug print, view in CloudWatch logs:
    #     # print("Saved throw: ", saved_throw)
    #     # print("Incoming throw: ", incoming_throw)

    #     # determine which phone number won
    #     result = determine_winner(saved_throw, incoming_throw)
    #     # print("Result: ", result)

    #     # text back the results
    #     client = boto3.client("sns", region_name="us-east-1")
    #     response = client.publish(
    #         TargetArn=sns_outgoing_arn,
    #         Message=result,
    #     )

    #     # delete the saved throw from s3 for new match
    #     object.delete()

    # # if Try did not work, no throw exists, so store this throw for later
    # except botocore.exceptions.ClientError:
    #     # dump to json string
    #     saveThrowJSON = json.dumps([throw, fromNumber])
    #     # save to the s3 object key
    #     object.put(Body=saveThrowJSON.encode("utf-8"))
    #     # print(saveThrowJSON)

    #     # text update message
    #     client = boto3.client("sns", region_name="us-east-1")
    #     response = client.publish(
    #         TargetArn=sns_outgoing_arn,
    #         Message="Waiting for other player",
    #     )

    # return {"statusCode": 200}


# helper function
# def determine_winner(first_throw, second_throw):
#     """
#     input parameters are each a list with contents: ["throw", "phone_number"]
#     returns a string of format "phone_number wins."
#     """
#     t1 = first_throw[0]
#     t2 = second_throw[0]

#     if t1 == t2:
#         response = "tie"
#     elif t1 == "paper" and t2 == "rock":
#         response = first_throw[1] + " wins."
#     elif t1 == "scissors" and t2 == "rock":
#         response = second_throw[1] + " wins."
#     elif t1 == "rock" and t2 == "scissors":
#         response = first_throw[1] + " wins."
#     elif t1 == "paper" and t2 == "scissors":
#         response = first_throw[1] + " wins."
#     elif t1 == "scissors" and t2 == "paper":
#         response = first_throw[1] + " wins."
#     elif t1 == "rock" and t2 == "paper":
#         response = first_throw[1] + " wins."
#     else:
#         response = "Something went wrong..."

#     return response
