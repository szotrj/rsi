# This Lambda function performs a cross-account remediation of
# an unsanctioned Internet Gateway creation/attachment

from __future__ import print_function
from botocore.exceptions import ClientError

import os, json, boto3

# Get region identifier
session = boto3.session.Session()
region = session.region_name

sns = boto3.client('sns')
sns_topic = 'arn:aws:sns:' + region + ':AccountId:IGW_Change'

# ===============================================================================

def lambda_handler(event, context):

    # Get the client Account ID
    customerAcct = event['account']

    # Assume cross-account role in client systems (target) account to run function
    sts = boto3.client('sts')
    assumedRoleObject = sts.assume_role(
        DurationSeconds=3600,
        RoleArn='arn:aws:iam::' + customerAcct + ':role/roleName',
        RoleSessionName='remediateIGW',
    )
    #print(assumedRoleObject)
    #print(boto3.client('sts').get_caller_identity()['Account'])

    credentials = assumedRoleObject['Credentials']
    ak=credentials['AccessKeyId']
    sk=credentials['SecretAccessKey']
    st=credentials['SessionToken']

    ec2 = boto3.client('ec2',region_name=region,aws_access_key_id=ak,aws_secret_access_key=sk,aws_session_token=st)

    # Delete or detach and delete IGW
    print('Detected ' + event['detail']['eventName'] + ' API call')
    if (event['detail']['eventName'] == 'CreateInternetGateway'):
        IgwId=event['detail']['responseElements']['internetGateway']['internetGatewayId']
        print(IgwId)
    elif (event['detail']['eventName'] == 'AttachInternetGateway'):
        IgwId=event['detail']['requestParameters']['internetGatewayId']
        VpcId=event['detail']['requestParameters']['vpcId']
        print(IgwId)
        print(VpcId)

    # Check for VPC attachment (add try/except for non-existant IGW)
    response = ec2.describe_internet_gateways(
        InternetGatewayIds=[
            IgwId
        ]
    )

    if response['InternetGateways'][0]['Attachments']:
        print('IGW State: ' + response['InternetGateways'][0]['Attachments'][0]['State'])
        print('IGW attached to VPC ID: ' + response['InternetGateways'][0]['Attachments'][0]['VpcId'])
        print('Detaching IGW from VPC...')
        response = ec2.detach_internet_gateway(
            InternetGatewayId=(IgwId),
            VpcId=(VpcId)
        )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                print('Detach successful')
        #print(response)
        print('Deleting IGW...')
        response = ec2.delete_internet_gateway(
            InternetGatewayId=(event['detail']['requestParameters']['internetGatewayId'])
        )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                print('Delete successful')

        # SNS notification
        try:
            response = sns.publish(
                TargetArn = sns_topic,
                Subject = 'Security Alert: IGW modification detected in ' + customerAcct,
                Message = 'An unsanctioned Internet Gateway (' + IgwId + ') was automatically detached and deleted from ' + VpcId
                )
        except ClientError as e:
            print("SNS failure: %s" %e)
        print('IGW not attached. Deleting IGW: ' + IgwId)
        try:
            response = ec2.delete_internet_gateway(
                InternetGatewayId=(IgwId)
            )
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                print('Delete successful')

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
            print(e.response['Error']['Code'])
            print(e.response['ResponseMetadata']['HTTPStatusCode'])
    else:
        print('IGW not attached. Deleting IGW: ' + IgwId)
        try:
            response = ec2.delete_internet_gateway(
                InternetGatewayId=(IgwId)
            )
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                print('Delete successful')

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
            print(e.response['Error']['Code'])
            print(e.response['ResponseMetadata']['HTTPStatusCode'])
