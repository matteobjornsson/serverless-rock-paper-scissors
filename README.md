
<p align="center">
  <img width="20%" src="img/rock.png"> <img width="20%" src="img/paper.png"> <img width="20%" src="img/scissors.png">
</p>

# Serverless Rock Paper Scissors

A *mostly* one-click-deploy serverless implementation of Rock Paper Scissors. 


<p align="center">
  <img width="100%" src="img/architecture.png"> 
</p>

## Overview

This repository contains the code and configurations to deploy a small set of AWS services used to play rock paper scissors via SMS. Any two players can text the Amazon Pinpoint number a number of set commands to play rock-paper-scissors with a friend. The pinpoint access point sends incoming messages to a Simple Notification Service topic, which triggers a Lambda function to process the game logic. The Lambda function uses DynamoDB to store state such as players and their throws. The Lambda function sends an SMS back to the original players notifying them of their result. 
## AWS Credentials

Running this code requires you to have an AWS account and to have your AWS credentials configured on the machine you are using to run this code. If you already have AWS credentials set up you can skip this section.

If you do not have an account you can sign up for one here: https://aws.amazon.com/. It is recommended that you do not use you root credentials but rather [create a separate IAM user role](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#create-iam-users) for yourself (This is similar to root vs user on a personal computer). 

Once you have your credentials (access key id and secret access key) you will need to store them locally. The easiest way to do this is using the [AWS Command Line Interface](https://aws.amazon.com/cli/) command `aws configure` . You can find helpful instructions [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html). 

Otherwise you will have to configure your credentials by hand by editing or creating the following file
* `~/.aws/credentials` on macOS or Linux
* `C:\Users\YOUR_USERNAME\.aws\credentials` on Windows. 

Your credentials should have the following format:
```
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
```
If configuring by hand you will also need to follow a similar process to set up your region, which lives in the file

* `~/.aws/config` on macOS or Linux
* `C:\Users\YOUR_USERNAME\.aws\config` on Windows. 

Which should look like 
```
[default]
region=us-east-1
output=text
```
## Python Dependencies
This project uses `python3.8` and the [AWS SDK for Python](https://aws.amazon.com/sdk-for-python/), Boto3. 
```
pip install boto3
```
With boto3 installed, you should be all set!

## Usage

To deploy the game you will need to run the setup file. 
```
python setup.py
```
This will automatically deploy all of the services and their required permission configurations. However, there is one thing you will be prompted to do which is request a phone number for your AWS account online. 
