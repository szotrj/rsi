# This Lambda function performs a cross-account remediation
# not permitting the client account to create/attach an IGW

from __future__ import print_function
from botocore.exceptions import ClientError

import os, json, boto3

# Get region info
session = boto3.session.Session()
region = session.region_name

sns_topic = 'arn:aws:sns:' + region + ':' + snsAccountId + ':topicName'

# ===============================================================================

def lambda_handler(event, context):

    # Get the client system's account id
    customerAcct = event['account']

    # Assume cross-account role in client systems (target) account to run function
    sts = boto3.client('sts')
    assumedRoleObject = sts.assume_role(
        DurationSeconds=3600,
        RoleArn='arn:aws:iam::' + customeracct + ':role/roleName',
        RoleSessionName='remediateIGW',
    )
    #print(assumedRoleObject)
    #print(boto3.client('sts').get_caller_identity()['Account'])

    credentials = assumedRoleObject['Credentials']
    ak=credentials['AccessKeyId']
    sk=xredentials['SecretAccessKey']
    st=xredentials['SessionToken']

    # Set temporary security credentials for assumed role
    ec2 = boto3.client('ec2',region_name=region,aws_access_key_id=ak,aws_secret_access_key=sk,aws_session_token=st)

    # Delete IGW either on create or detach

    if (event['detail']['eventName'] == 'CreateInternetGateway') or (event['detail']['eventName'] == 'AttachInternetGateway'):
        print('Detected ' + event['detail']['eventName'] + ' API call')
        IgwId=event['detail']['responseElements']['internetGateway']['internetGatewayId']
        response = ec2.describe_internet_gateways(
            InternetGatewayIds=[
                IgwId
            ]
        )

        #print(response)

        if response.get('InternetGateways.Attachments') == None:
            print('IGW not attached. Deleting IGW: ' + IgwId)
            #response = ec2client.delete_internet_gateway(
            #    InternetGatewayId=(event['detail']['responseElements']['internetGateway']['internetGatewayId'])
            #)
            #print(response)
        else:
            print('IGW State: ' + response['InternetGateways'][0]['Attachments'][0]['State'])
            print('IGW attached to VPC ID: ' + response['InternetGateways'][0]['Attachments'][0]['VpcId'])
            print('Detaching IGW from VPC...')
            #response = ec2client.detach_internet_gateway(
            #    InternetGatewayId=(event['detail']['requestParameters']['internetGatewayId']),
            #    VpcId=(event['detail']['requestParameters']['vpcId'])
            #)
            #print(response)
            print('Deleting IGW...')
            #response = ec2client.delete_internet_gateway(
            #    InternetGatewayId=(event['detail']['requestParameters']['internetGatewayId'])
            #)
            #print(response)

        exit()

        # SNS notification
        try:
            sns = boto3.client('sns')
            response = sns.publish(
                TargetArn = sns_topic,
                Subject = 'Security Alert: ' + customeracct + ' IGW creation detected',
                Message = 'An IGW, ' + InternetGatewayId + ', was created and was deleted.'
            )
        except ClientError as e:
            print("SNS failure: %s" %e)

    if (event['detail']['eventName'] == 'AttachInternetGateway'):
        IgwId=event['detail']['requestParameters']['internetGatewayId']
        VpcId=event['detail']['requestParameters']['vpcId']
        response = ec2client.detach_internet_gateway(
            InternetGatewayId=(event['detail']['requestParameters']['internetGatewayId']),
            VpcId=(event['detail']['requestParameters']['vpcId'])
        )
        print(response)
        response = ec2client.delete_internet_gateway(
            InternetGatewayId=(event['detail']['requestParameters']['internetGatewayId'])
        )
        print(response)

        # SNS notification
        try:
            sns = boto3.client('sns')
            response = sns.publish(
                TargetArn = sns_topic,
                Subject = 'Security Alert: ' + customeracct + '  IGW attachment detected',
                Message = 'An IGW, ' + IgwId + ', was attached to VPC, ' + VpcId + ', and was detached and deleted.'
            )
        except ClientError as e:
            print("SNS failure: %s" %e)
