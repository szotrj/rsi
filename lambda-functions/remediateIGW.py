'''
Purpose: This Lambda function performs a cross-account remediation of
an unsanctioned Internet Gateway creation/attachment
Author: Rob Szot (rjszot@fbi.gov)
Change History: 11/7/2018 - Initial function
'''

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
if region == 'us-gov-west-1' or region == 'us-gov-east-1':
    partition = 'aws-us-gov'
if region == 'us-isob-east-1':
    partition = 'aws-isob'
if region == 'us-iso-east-1':
    partition = 'aws-iso'

# Get current Account ID
sts = boto3.client('sts')
currAccountId = sts.get_caller_identity().get('Account')

# Set SNS client for central account
sns = boto3.client('sns')
# Getting the SNS Topic ARN passed in by the environment variable
snsARN = os.environ['SNSARN']
# Getting the cross-account role ARN passed in by the environment variable
xRoleName = os.environ['XROLENAME']

# =============================================================================

def lambda_handler(event, context):
    # Print event
    print(json.dumps(event))

    # Get the client Account ID
    customerAcct = event['account']
    customerRegion = event['region']

    # Assume cross-account role in target account to run function
    if customerRegion == 'us-gov-west-1' or customerRegion == 'us-gov-east-1':
        partition = 'aws-us-gov'
    else:
        partition = 'aws'
    xRoleARN='arn:' + partition + ':iam::' + customerAcct + ':role/' + xRoleName
    assumedRoleObject = sts.assume_role(
        DurationSeconds=3600,
        RoleArn=xRoleARN,
        RoleSessionName='remediateIGW',
    )

    credentials = assumedRoleObject['Credentials']
    ak=credentials['AccessKeyId']
    sk=credentials['SecretAccessKey']
    st=credentials['SessionToken']

    # Use ec2 client customer region from event region
    ec2 = boto3.client('ec2',region_name=customerRegion,aws_access_key_id=ak,aws_secret_access_key=sk,aws_session_token=st)
    # Use default region for SNS
    snsCustomer = boto3.client('sns',region_name=region,aws_access_key_id=ak,aws_secret_access_key=sk,aws_session_token=st)

    # Delete or detach and delete IGW
    eventName = event['detail']['eventName']
    print('Detected ' + eventName + ' API call')

    # Determine who/what performed the action
    try:
        userType = event['detail']['userIdentity']['type']
    except Exception, e:
        userType = 'None'

    if userType == 'IAMUser':
        userName = event['detail']['userIdentity']['userName']
    elif userType == 'AssumedRole':
        arn = event['detail']['userIdentity']['arn'].split("/")
        userRole = arn[1]
        userName = arn[2]
        userName = userRole + '/' + userName
    elif userType == 'Root':
        userName = 'Root'
    elif userType == 'AWSAccount':
        accountId = event['detail']['userIdentity']['accountId']
        userName = accountId
    elif userType == 'FederatedUser':
        userName = event['detail']['userIdentity']['sessionContext']['sessionIssuer']['userName']
    elif userType == 'AWSService':
        invokedBy = event['detail']['userIdentity']['invokedBy']
        userName = invokedBy
    else:
        username = 'Unknown'

    try:
        if event['detail']['errorCode'] == 'Client.UnauthorizedOperation':
            message = userName + ' attempted to perform ' + eventName + ' in ' + customerAcct + ' but was unauthorized and denied'
            print(message)
            sendCentralNotification(message, customerAcct)
            sendCustomerNotification(message, currAccountId, customerAcct, snsCustomer)
    except:
        if (event['detail']['eventName'] == 'CreateInternetGateway'):
            IgwId=event['detail']['responseElements']['internetGateway']['internetGatewayId']
            try:
                response = ec2.describe_internet_gateways(
                    InternetGatewayIds=[
                        IgwId
                    ]
                )
                try:
                    VpcId=response['InternetGateways'][0]['Attachments'][0]['VpcId']
                    state=response['InternetGateways'][0]['Attachments'][0]['State']
                    print('IGW State: ' + state)
                except:
                    pass
            except ClientError as e:
                print('Error code: ' + e.response['Error']['Code'])
                print('HTTP status code: ' + str(e.response['ResponseMetadata']['HTTPStatusCode']))
                print('IGW may have already been deleted.')
        elif (event['detail']['eventName'] == 'AttachInternetGateway'):
            IgwId=event['detail']['requestParameters']['internetGatewayId']
            VpcId=event['detail']['requestParameters']['vpcId']
            try:
                response = ec2.describe_internet_gateways(
                    InternetGatewayIds=[
                        IgwId
                    ]
                )
                state=response['InternetGateways'][0]['Attachments'][0]['State']
                print('IGW State: ' + state)
            except ClientError as e:
                print('Error code: ' + e.response['Error']['Code'])
                print('HTTP status code: ' + str(e.response['ResponseMetadata']['HTTPStatusCode']))
                print('IGW may have already been deleted.')
                exit(0)
        try:
            VpcId
            print('IGW (' + IgwId + ') attached to VPC (' + VpcId + ')')
            print('Detaching IGW from VPC...')
            response = ec2.detach_internet_gateway(
                InternetGatewayId=(IgwId),
                VpcId=(VpcId)
            )
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                print('Detach IGW successful')
            else:
                print('Detach IGW failed. Check resource.')
            print('Deleting IGW...')
            response = ec2.delete_internet_gateway(
                InternetGatewayId=(IgwId)
            )
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                print('Delete IGW successful')
                message = 'An unsanctioned Internet Gateway (' + IgwId + ') was automatically detached and deleted from ' + VpcId
    	        sendCentralNotification(message, customerAcct)
    	        sendCustomerNotification(message, currAccountId, customerAcct, snsCustomer)
            else:
                print('Delete IGW failed. There may be public IPs associated.')
        except:
            print('IGW not attached. Deleting IGW: ' + IgwId)
            try:
                response = ec2.delete_internet_gateway(
                    InternetGatewayId=(IgwId)
                )
                if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                    print('Delete IGW successful')
                    message = 'An unsanctioned Internet Gateway (' + IgwId + ') was automatically deleted.'
                    sendCentralNotification(message, customerAcct)
                    sendCustomerNotification(message, currAccountId, customerAcct, snsCustomer)
            except ClientError as e:
                print('Error code: ' + e.response['Error']['Code'])
                print('HTTP status code: ' + str(e.response['ResponseMetadata']['HTTPStatusCode']))

def sendCentralNotification(message, customerAcct):
    # SNS notification for central account topic
    try:
        print('Publishing notification to central SNS topic')
        response = sns.publish(
            TargetArn = snsARN,
            Subject = 'Security Alert: IGW modification detected in ' + customerAcct,
            Message = message
        )
    except ClientError as e:
        print("SNS failure: %s" %e)
        print('Error code: ' + e.response['Error']['Code'])
        print('HTTP status code: ' + str(e.response['ResponseMetadata']['HTTPStatusCode']))

def sendCustomerNotification(message, currAccountId, customerAcct, snsCustomer):
    # SNS notification for customer account topic
    try:
        print('Publishing notification to customer SNS topic')
        snsCustomerARN = snsARN.replace(currAccountId, customerAcct)
        response = snsCustomer.publish(
            TargetArn = snsCustomerARN,
            Subject = 'Security Alert: IGW modification detected in ' + customerAcct,
            Message = message
        )
    except ClientError as e:
        print("SNS failure: %s" %e)
        print('Error code: ' + e.response['Error']['Code'])
        print('HTTP status code: ' + str(e.response['ResponseMetadata']['HTTPStatusCode']))
