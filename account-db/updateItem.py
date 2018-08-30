from __future__ import print_function # Python 2/3 compatibility
import boto3
import json
import decimal

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

dynamodb = boto3.resource('dynamodb', region_name='us-east-1', endpoint_url="http://localhost:8000")

table = dynamodb.Table('Accounts')

accountname = "Account-4"
accountid = 123456789014

response = table.update_item(
    Key={
        'accountid': accountid,
        'accountname': accountname
    },
    UpdateExpression="set info.regionname = :r, info.envtype=:e",
    ExpressionAttributeValues={
        ':r': "GovCloud",
        ':e': "Prod"
    },
    ReturnValues="UPDATED_NEW"
)

print("UpdateItem succeeded:")
print(json.dumps(response, indent=4, cls=DecimalEncoder))
