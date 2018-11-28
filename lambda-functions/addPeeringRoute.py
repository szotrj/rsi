'''
Lambda function to add routes to complete peering connection
Invoked by CloudFormation custom SNS resource
'''
import boto3
import json
import urllib2
import sys
import logging
from botocore.exceptions import ClientError

def lambda_handler(event, context):
  print("SNS Event: " + json.dumps(event))
  event = json.loads(event['Records'][0]['Sns']['Message'])
  print("Lambda Event: " + json.dumps(event))

  #Connect to EC2
  ec2 = boto3.client('ec2')

  try:
    type = event['RequestType']
    PeeringName = event['ResourceProperties']['PeeringName']
    CidrBlock = event['ResourceProperties']['CidrBlock']
    PeeringConnectionId = event['ResourceProperties']['PeeringConnectionId']
    RouteTableId = event['ResourceProperties']['RouteTableId']

    if type == 'Create':
      print "Creating Route " + CidrBlock + "->" + PeeringConnectionId + " in " + RouteTableId + " for " + PeeringName
      response = ec2.create_route(
        DestinationCidrBlock = CidrBlock,
        VpcPeeringConnectionId = PeeringConnectionId,
        RouteTableId = RouteTableId,
      )
      print(response)
      response = ec2.create_tags(
        Resources=[
          PeeringConnectionId,
        ],
        Tags=[
          {
            'Key': 'Name',
            'Value': PeeringName
          },
        ]
      )
      print(response)
    elif type == 'Update':
      # If Update, delete old route then create new route
      oldCidrBlock = event['OldResourceProperties']['CidrBlock']
      oldPeeringConnectionId = event['OldResourceProperties']['PeeringConnectionId']
      oldRouteTableId = event['OldResourceProperties']['RouteTableId']
      print "Deleting old Route " + oldCidrBlock + "->" + oldPeeringConnectionId + " in " + oldRouteTableId + " for " + PeeringName
      response = ec2.delete_route(
        DestinationCidrBlock = oldCidrBlock,
        RouteTableId = oldRouteTableId,
      )
      print(response)
      print "Creating Route " + CidrBlock + "->" + PeeringConnectionId + " in " + RouteTableId + " for " + PeeringName
      response = ec2.create_route(
        DestinationCidrBlock = CidrBlock,
        VpcPeeringConnectionId = PeeringConnectionId,
        RouteTableId = RouteTableId,
      )
      print(response)
      response = ec2.create_tags(
        Resources=[
          PeeringConnectionId,
        ],
        Tags=[
          {
            'Key': 'Name',
            'Value': PeeringName
          },
        ]
      )
      print(response)
    elif type == 'Delete':
      print "Deleting Route " + CidrBlock + "->" + PeeringConnectionId + " in " + RouteTableId + " for " + PeeringName
      response = ec2.delete_route(
        DestinationCidrBlock = CidrBlock,
        RouteTableId = RouteTableId,
      )
      print(response)
    else:
      print "Unexpected Request Type"
      raise Exception("Unexpected Request Type")

    print "Completed successfully"
    responseStatus = 'SUCCESS'
    responseData = {}
    sendResponse(event, context, responseStatus, responseData)

  except ClientError as e:
    logger = logging.getLogger(__name__)
    logger.error("Received error: %s", e, exc_info=True)
    print("Error:", sys.exc_info()[0])
    responseStatus = 'FAILED'
    responseData = {}
    sendResponse(event, context, responseStatus, responseData)

def sendResponse(event, context, responseStatus, responseData):
  data = json.dumps({
    'Status': responseStatus,
    'Reason': 'See the details in CloudWatch Log Stream: ' + context.log_stream_name,
    'PhysicalResourceId': context.log_stream_name,
    'StackId': event['StackId'],
    'RequestId': event['RequestId'],
    'LogicalResourceId': event['LogicalResourceId'],
    'Data': responseData
  })
  opener = urllib2.build_opener(urllib2.HTTPHandler)
  request = urllib2.Request(url=event['ResponseURL'], data=data)
  request.add_header('Content-Type', '')
  request.get_method = lambda: 'PUT'
  url = opener.open(request)
