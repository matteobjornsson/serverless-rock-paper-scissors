import IAm, Lambda, Pinpoint, SNS
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)

# service names and parameters
# sns_incoming_SMS_topic_name = 'rps_incoming_sms'
# lambda_function_filename = 'lambda_function_handler.py'
# lambda_handler_name = 'lambda_function_handler.lambda_handler'
# lambda_role_name = 'rps-lambda-role'
# lambda_function_name = 'rps-lambda-function'
# lamda_function_description = 'Rock Paper Scissors lambda function'
# pinpoint_app_name = 'rock_paper_scissors'

# alternative parameters for testing?
sns_incoming_SMS_topic_name = "rps_incoming_sms_test"
lambda_function_filename = "lambda_function_handler.py"
lambda_handler_name = "lambda_function_handler.lambda_handler"
lambda_role_name = "rps-lambda-role_test"
lambda_function_name = "rps-lambda-function_test"
lamda_function_description = "Rock Paper Scissors lambda function_test"
pinpoint_app_name = "rock_paper_scissors_test"
teardown = True

########
# SNS  #
########
# create sns topic to handle incoming SMS messages from Pinpoint
sns_topic = SNS.create_topic(sns_incoming_SMS_topic_name)
# add a policy to allow Pinpoint to publish to this SNS topic
pinpoint_policy_statement = {
    "Sid": "PinpointPublish",
    "Effect": "Allow",
    "Principal": {"Service": "mobile.amazonaws.com"},
    "Action": "sns:Publish",
    "Resource": sns_topic.arn,
}
SNS.add_policy_statement(sns_topic, pinpoint_policy_statement)

###########
# LAMBDA  #
###########
# create lambda function to handle Rock Paper Scissors logic when SMS are received
iam_role = IAm.create_basic_lambda_execution_role(lambda_role_name)
function_code = Lambda.zip_lambda_code(lambda_function_filename)

response = Lambda.create_lambda_function(
    lambda_function_name,
    lamda_function_description,
    lambda_handler_name,
    iam_role,
    function_code,
)
function_arn = response["FunctionArn"]

# Give the sns topic permission to invoke the Lambda function
Lambda.add_permission(
    action="lambda:InvokeFunction",
    function_name=lambda_function_name,
    principal="sns.amazonaws.com",
    # source_arn=sns_topic.arn,
    source_arn="arn:aws:sns:us-east-1:802108040626:rps_incoming_sms_test",
    statement_id="sns",
)

# add a lambda as a subscriber to the topic
response = SNS.add_subscription(
    topic_arn=sns_topic.arn,
    protocol="lambda",
    endpoint=function_arn,
)

#############
# PINPOINT  #
#############
# Create pinpoint app to handle incoming SMS
response = Pinpoint.create_pinpoint_app(pinpoint_app_name)
pinpoint_app_id = response["ApplicationResponse"]["Id"]

Pinpoint.enable_pinpoint_SMS(pinpoint_app_id)
input(
    "Enable Two-Way SMS on your Pinpoint App via the aws browser console. Press Enter to continue."
)
print("Instructions here to play the game")

if teardown:
    SNS.delete_topic(sns_topic)
    IAm.delete_role(iam_role)
    Lambda.delete_lambda_function(lambda_function_name)
    Pinpoint.delete_pinpoint_app(pinpoint_app_id)
    print("Service teardown complete")
