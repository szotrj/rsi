from __future__ import print_function # Python 2/3 compatibility
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1', endpoint_url="http://localhost:8000")


table = dynamodb.create_table(
    TableName='Accounts',
    KeySchema=[
        {
            'AttributeName': 'accountid',
            'KeyType': 'HASH'  #Partition key
        },
        {
            'AttributeName': 'accountname',
            'KeyType': 'RANGE'  #Sort key
        }
    ],
    AttributeDefinitions=[
        {
            'AttributeName': 'accountid',
            'AttributeType': 'N'
        },
        {
            'AttributeName': 'accountname',
            'AttributeType': 'S'
        },

    ],
    ProvisionedThroughput={
        'ReadCapacityUnits': 10,
        'WriteCapacityUnits': 10
    }
)

print("Table status:", table.table_status)
