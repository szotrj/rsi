# This Lambda function performs a cross-account remediation of
# an unsanctioned Internet Gateway creation/attachment

from __future__ import print_function
from botocore.exceptions import ClientError

import os, json, boto3
import botocore.config

# Set retries to 0
cfg = botocore.config.Config(retries={'max_attempts': 0})
client = boto3.client('lambda', config=cfg)

# Get region identifier
session = boto3.session.Session()
region = session.region_name
if region == 'us-gov-west-1':
    partition = 'aws-us-gov'
if region == 'us-isob-east-1':
    partition = 'aws-isob'
if region == 'us-iso-east-1':
    partition = 'aws-iso'

# Get current Account ID
sts = boto3.client('sts')
currAccountId = sts.get_caller_identity().get('Account')

# Set SNS topic ARN
sns = boto3.client('sns')
sns_topic = 'arn:' + partition + ':sns:' + region + ':' + currAccountId + ':topic-name'

# ==============================================================================

def lambda_handler(event, context):
    # Get the client Account ID
    customerAcct = event['account']

    # Print event detail
    print(event['detail'])
    print('')

    # Gather details about the event
    affectedRoleName = event['detail']['requestParameters']['roleName']
    eventName = event['detail']['eventName']
    if type in event:
        userType = event['detail']['userIdentity']['type']
    else:
        userType = 'unknown'

    if userType == 'IAMUser':
        userName = event['detail']['userIdentity']['userName']
        message = 'IAM User ' + userName + ' performed ' + eventName + ' on ' + affectedRoleName
    elif userType == 'AssumedRole':
        arn = event['detail']['userIdentity']['arn'].split("/")
        userRole = arn[1]
        userName = arn[2]
        message = 'Assumed Role ' + userRole + '/' + userName + ' performed ' + eventName + ' on ' + affectedRoleName
    elif userType == 'Root':
        message = 'The root user performed ' + eventName + ' on ' + affectedRoleName
    elif userType == 'FederatedUser':
        userName = event['detail']['userIdentity']['sessionContext']['sessionIssuer']['userName']
        message = 'Federated user ' + userName + ' performed ' + eventName + ' on ' + affectedRoleName
    elif userType == 'AWSService':
        invokedBy = event['detail']['userIdentity']['invokedBy']
        message = 'AWS Service ' + invokedBy + ' performed ' + eventName + ' on ' + affectedRoleName
    else:
        message = 'An unknown principal ' + userType + ' performed ' + eventName + ' on ' + affectedRoleName

    print(message+'\n')
    # SNS notification
    try:
        response = sns.publish(
            TargetArn = sns_topic,
            Subject = 'Security Alert: Federation modification detected in ' + customerAcct,
            Message = message
        )
    except ClientError as e:
        print("SNS failure: %s" %e)
        print('Error code: ' + e.response['Error']['Code'])
        print('HTTP status code: ' + str(e.response['ResponseMetadata']['HTTPStatusCode']))
