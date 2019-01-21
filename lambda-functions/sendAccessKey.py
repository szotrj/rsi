# Invoked by CloudFormation Lambda-backed custom resource
# Sends IAM Access Key to SNS subscription

import json
import boto3
import logging
import os
import botocore.session
import signal
from botocore.exceptions import ClientError
from urllib2 import build_opener, HTTPHandler, Request

session = botocore.session.get_session()

logging.basicConfig(level=logging.DEBUG)
logger=logging.getLogger(__name__)

# Getting the SNS Topic ARN passed in by the environment variable
snsARN = os.environ['SNSARN']

iam = boto3.client('iam')
sns = boto3.client('sns')
response = iam.list_account_aliases()

def lambda_handler(event, context):
    logger.setLevel(logging.DEBUG)
    try:
        if not response['AccountAliases']:
            accntAlias = (boto3.client('sts').get_caller_identity()['Account'])
            logger.info("Account Alias is not defined. Account ID is %s" %accntAlias)
        else:
            accntAlias = response['AccountAliases'][0]
            logger.info("Account Alias is : %s" %accntAlias)    
    except ClientError as e:
        logger.error("Client Error occured")
    
    #logger.debug("Event is --- %s" %json.dumps(event))
    logger.debug("SNSARN is-- %s" %snsARN)
    logger.debug("List Account Alias response --- %s" %response)

    # Setup alarm for remaining runtime minus a second
    signal.alarm((context.get_remaining_time_in_millis() / 1000) - 1)
    try:
        #logger.info('REQUEST RECEIVED:\n %s', event)
        #logger.info('REQUEST RECEIVED:\n %s', context)

        AccessKeyId = event['ResourceProperties']['AccessKeyId']
        SecretAccessKey = event['ResourceProperties']['SecretAccessKey']
        message = 'AccessKeyId: ' + AccessKeyId + '\r\n' + 'SecretAccessKey: ' + SecretAccessKey
        if event['RequestType'] == 'Create':
            logger.info('CREATE!')
            try:
                # Sending the notification...
                snspublish = sns.publish(
                    TargetArn= snsARN,
                    Subject=(("IAM Access Key for %s" %(accntAlias))[:100]),
                    Message=json.dumps({'default':message}),
                    MessageStructure='json')
                logger.debug("SNS publish response is-- %s" %snspublish)
            except ClientError as e:
                logger.error("An error occured: %s" %e)
            send_response(event, context, "SUCCESS",
                {"Message": "Resource creation successful!"})
        elif event['RequestType'] == 'Update':
            logger.info('UPDATE!')
            try:
                # Sending the notification...
                snspublish = sns.publish(
                    TargetArn= snsARN,
                    Subject=(("IAM Access Key for %s" %(accntAlias))[:100]),
                    Message=json.dumps({'default':message}),
                    MessageStructure='json')
                logger.debug("SNS publish response is-- %s" %snspublish)
            except ClientError as e:
                logger.error("An error occured: %s" %e)
            send_response(event, context, "SUCCESS",
                {"Message": "Resource update successful!"})
        elif event['RequestType'] == 'Delete':
            logger.info('DELETE!')
            send_response(event, context, "SUCCESS",
                {"Message": "Resource deletion successful!"})
        else:
            logger.info('FAILED!')
            send_response(event, context, "FAILED",
                {"Message": "Unexpected event received from CloudFormation"})
    except: #pylint: disable=W0702
        logger.info('FAILED!')
        send_response(event, context, "FAILED", {
            "Message": "Exception during processing"})

def send_response(event, context, response_status, response_data):
    '''Send a resource manipulation status response to CloudFormation'''
    response_body = json.dumps({
        "Status": response_status,
        "Reason": "See the details in CloudWatch Log Stream: " + context.log_stream_name,
        "PhysicalResourceId": context.log_stream_name,
        "StackId": event['StackId'],
        "RequestId": event['RequestId'],
        "LogicalResourceId": event['LogicalResourceId'],
        "Data": response_data
    })

    logger.info('ResponseURL: %s', event['ResponseURL'])
    logger.info('ResponseBody: %s', response_body)

    opener = build_opener(HTTPHandler)
    request = Request(event['ResponseURL'], data=response_body)
    request.add_header('Content-Type', '')
    request.add_header('Content-Length', len(response_body))
    request.get_method = lambda: 'PUT'
    response = opener.open(request)
    logger.info("Status code: %s", response.getcode())
    logger.info("Status message: %s", response.msg)

def timeout_handler(_signal, _frame):
    '''Handle SIGALRM'''
    raise Exception('Time exceeded')

signal.signal(signal.SIGALRM, timeout_handler)