from __future__ import print_function # Python 2/3 compatibility
import boto3
import json
import decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1', endpoint_url="http://localhost:8000")

table = dynamodb.Table('Accounts')

with open("accounts.json") as json_file:
    accounts = json.load(json_file, parse_float = decimal.Decimal)
    for account in accounts:
        accountid = int(account['accountid'])
        accountname = account['accountname']

        print("Adding account:", accountid, accountname)

        table.put_item(
           Item={
               'accountid': accountid,
               'accountname': accountname
            }
        )
