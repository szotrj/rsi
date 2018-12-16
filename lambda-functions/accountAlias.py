#!/usr/bin/python

from __future__ import print_function
import boto3

# ===============================================================================

def lambda_handler(event, context):
    try:
        alias = boto3.client('iam').list_account_aliases()['AccountAliases'][0]
    except:
        alias = boto3.client('sts').get_caller_identity().get('Account')

    print('Account Alias: {}'.format(alias))

lambda_handler(None, None)
