import IAm, Lambda, Pinpoint, SNS, Dynamodb
import logging

logging.basicConfig(filename="rps.log", level=logging.INFO)

# service names and parameters
sns_incoming_SMS_topic_name = "rps_incoming_sms_test"
sns_outgoing_SMS_topic_name = "rps_outgoing_sms_test"
lambda_policy_name = "BasicLambdaExecutionRoleDynamoCRUD"
lambda_policy_file_name = "lambda_policy.json"
lambda_assume_role_policy_file_name = "lambda_assume_role_policy.json"
lambda_function_filename = "lambda_function_handler.py"
lambda_handler_name = "lambda_function_handler.lambda_handler"
lambda_role_name = "rps-lambda-role_test"
lambda_function_name = "rps-lambda-function_test"
lamda_function_description = "Rock Paper Scissors lambda function_test"
pinpoint_app_name = "rock_paper_scissors_test"
db_table_name = "players"
db_key_schema = [
    {"AttributeName": "phone_number", "KeyType": "HASH"},  # Partition key
    {"AttributeName": "round", "KeyType": "RANGE"},  # Partition key
]
db_attribute_definitions = [
    {"AttributeName": "phone_number", "AttributeType": "S"},
    {"AttributeName": "round", "AttributeType": "S"},
]
teardown = True

########
# SNS  #
########
# create sns topic to handle incoming SMS messages from Pinpoint
sns_in_topic = SNS.create_topic(sns_incoming_SMS_topic_name)
# add a policy to allow Pinpoint to publish to this SNS topic
pinpoint_policy_statement = {
    "Sid": "PinpointPublish",
    "Effect": "Allow",
    "Principal": {"Service": "mobile.amazonaws.com"},
    "Action": "sns:Publish",
    "Resource": sns_in_topic.arn,
}
SNS.add_policy_statement(sns_in_topic, pinpoint_policy_statement)

# create sns topic to handle outgoing SMS messages from Lambda
sns_out_topic = SNS.create_topic(sns_outgoing_SMS_topic_name)
# add a policy to allow Lambda to publish to this SNS topic
lambda_policy_statement = {
    "Sid": "LambdaPublish",
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sns:Publish",
    "Resource": sns_out_topic.arn,
}
SNS.add_policy_statement(sns_out_topic, lambda_policy_statement)


###########
# LAMBDA  #
###########
# create lambda function to handle Rock Paper Scissors logic when SMS are received
with open(lambda_policy_file_name) as file:
    lambda_policy_json = file.read()
with open(lambda_assume_role_policy_file_name) as file:
    assume_role_json = file.read()

iam_policy = IAm.create_policy(lambda_policy_name, lambda_policy_json)
iam_role = IAm.create_role(lambda_role_name, assume_role_json, [iam_policy.arn])
function_code = Lambda.zip_lambda_code(lambda_function_filename)

response = Lambda.create_lambda_function(
    lambda_function_name,
    lamda_function_description,
    lambda_handler_name,
    iam_role,
    function_code,
)
function_arn = Lambda.get_function(lambda_function_name)["FunctionArn"]

# Give the sns topic permission to invoke the Lambda function
Lambda.add_permission(
    action="lambda:InvokeFunction",
    function_name=lambda_function_name,
    principal="sns.amazonaws.com",
    source_arn=sns_in_topic.arn,
    statement_id="sns",
)

# add a lambda as a subscriber to the topic
response = SNS.add_subscription(
    topic_arn=sns_in_topic.arn,
    protocol="lambda",
    endpoint=function_arn,
)

#############
# DYNAMODB  #
#############
response = Dynamodb.create_table(db_table_name, db_key_schema, db_attribute_definitions)

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

input( "Pausing here for testing. Press enter to continue.")

if teardown:
    SNS.delete_topic(sns_in_topic)
    SNS.delete_topic(sns_out_topic)
    IAm.delete_role(iam_role)
    IAm.delete_policy(iam_policy)
    Lambda.delete_lambda_function(lambda_function_name)
    Dynamodb.delete_table(db_table_name)
    Pinpoint.delete_pinpoint_app(pinpoint_app_id)
    print("Service teardown complete")
