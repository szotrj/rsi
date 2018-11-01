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

# ===============================================================================

def lambda_handler(event, context):
    # Get the client Account ID
    customerAcct = event['account']

    # Assume cross-account role in target account to run function
    assumedRoleObject = sts.assume_role(
        DurationSeconds=3600,
        RoleArn='arn:' + partition + ':iam::' + customerAcct + ':role/XMonitorRole',
        RoleSessionName='remediateIGW',
    )

    credentials = assumedRoleObject['Credentials']
    ak=credentials['AccessKeyId']
    sk=credentials['SecretAccessKey']
    st=credentials['SessionToken']

    ec2 = boto3.client('ec2',region_name=region,aws_access_key_id=ak,aws_secret_access_key=sk,aws_session_token=st)

    # Delete or detach and delete IGW
    print('Detected ' + event['detail']['eventName'] + ' API call')
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
        else:
            print('Delete IGW failed. There may be public IPs associated.')

        # SNS notification
        try:
            response = sns.publish(
                TargetArn = sns_topic,
                Subject = 'Security Alert: IGW modification detected in ' + customerAcct,
                Message = 'An unsanctioned Internet Gateway (' + IgwId + ') was automatically detached and deleted from ' + VpcId
                )
        except ClientError as e:
            print("SNS failure: %s" %e)
    except:
        print('IGW not attached. Deleting IGW: ' + IgwId)
        try:
            response = ec2.delete_internet_gateway(
                InternetGatewayId=(IgwId)
            )
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                print('Delete IGW successful')

                # SNS notification
                try:
                    response = sns.publish(
                        TargetArn = sns_topic,
                        Subject = 'Security Alert: IGW modification detected in ' + customerAcct,
                        Message = 'An unsanctioned Internet Gateway (' + IgwId + ') was automatically deleted.'
                )
                except ClientError as e:
                    print("SNS failure: %s" %e)
        except ClientError as e:
            print('Error code: ' + e.response['Error']['Code'])
            print('HTTP status code: ' + str(e.response['ResponseMetadata']['HTTPStatusCode']))
