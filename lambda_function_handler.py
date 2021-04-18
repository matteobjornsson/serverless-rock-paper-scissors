import json
import boto3
import botocore

# TODO: get phone number and subscribe the recipient
def lambda_handler(event, context):
    # grab the event from pinpoint
    pinpointEvent = json.loads(event["Records"][0]["Sns"]["Message"])
    # extract the throw text and origination phone number
    throw = pinpointEvent["messageBody"].lower().strip()
    fromNumber = pinpointEvent["originationNumber"]
    # store them together
    incoming_throw = [throw, fromNumber]

    s3 = boto3.resource("s3")
    # an object is defined by its bucket and key, irrelevant of if it exists or not.
    object = s3.Object("rock-paper-scissors-csci566", "/throwTEST.txt")

    # Try to get existing throw
    try:
        # this will throw an exception if there is no throw already stored on the s3 bucket
        saved_object = object.get()
        # if the previous line succeeds, we have everything we need to play.

        # load the list object that contains throw string and phone number string
        saved_throw = json.loads(saved_object["Body"].read().decode("utf-8"))
        # debug print, view in CloudWatch logs:
        # print("Saved throw: ", saved_throw)
        # print("Incoming throw: ", incoming_throw)

        # determine which phone number won
        result = determine_winner(saved_throw, incoming_throw)
        # print("Result: ", result)

        # text back the results
        client = boto3.client("sns", region_name="us-east-1")
        response = client.publish(
            TargetArn="arn:aws:sns:us-east-1:802108040626:game_result", Message=result
        )
        # print("Result published: ", response)

        # delete the saved throw from s3 for new match
        object.delete()

    # if Try did not work, no throw exists, so store this throw for later
    except botocore.exceptions.ClientError:
        # dump to json string
        saveThrowJSON = json.dumps([throw, fromNumber])
        # save to the s3 object key
        object.put(Body=saveThrowJSON.encode("utf-8"))
        # print(saveThrowJSON)

        # text update message
        client = boto3.client("sns", region_name="us-east-1")
        response = client.publish(
            TargetArn="arn:aws:sns:us-east-1:802108040626:game_result",
            Message="Waiting for other player",
        )

    return {"statusCode": 200}


# helper function
def determine_winner(first_throw, second_throw):
    """
    input parameters are each a list with contents: ["throw", "phone_number"]
    returns a string of format "phone_number wins."
    """
    t1 = first_throw[0]
    t2 = second_throw[0]

    if t1 == t2:
        response = "tie"
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
