#!/usr/bin/env python
"""
This script performs a STS Assume Role operation for a role in a target account
It takes in an AWS Account ID, Role Name, and optional clobber flag 
It assumes the role and sets credentials for the AWS CLI
"""

import boto3
import sys
import time
import argparse
import re
import ConfigParser

from os.path import expanduser
from botocore.exceptions import ClientError

def role_name(aws_account_number, role_name, no_clobber):
    """
    Assumes the provided role in an account
    :param aws_account_number: AWS Account Number
    :param role_name: Role to assume in target account
    :param no_clobber: Whether to clobber default credentials or not
    :return: Assumed role session
    """

    # Beginning the assume role process for account
    sts_client = boto3.client('sts')
    
    # Get the current partition
    partition = sts_client.get_caller_identity()['Arn'].split(":")[1]
   
    # Get the region
    session = boto3.session.Session()
    region = session.region_name

    response = sts_client.assume_role(
        RoleArn='arn:{}:iam::{}:role/{}'.format(
            partition,
            aws_account_number,
            role_name
        ),
        RoleSessionName='AssumedRoleSession'
    )
    
    # Storing STS credentials
    session = boto3.Session(
        aws_access_key_id=response['Credentials']['AccessKeyId'],
        aws_secret_access_key=response['Credentials']['SecretAccessKey'],
        aws_session_token=response['Credentials']['SessionToken']
    )

    # Write the AWS STS token into the AWS credential file
    home = expanduser("~")
    awsconfigfile = '/.aws/credentials'
    filename = home + awsconfigfile

    # Read in the existing config file
    config = ConfigParser.RawConfigParser()
    config.read(filename)

    # Set profile based on no_clobber
    if no_clobber:
        profile=aws_account_number
    else:
        profile='default'

    # Put the credentials into a profile specific for the account
    if not config.has_section(profile):
        config.add_section(profile)
    config.set(profile, 'region', region)
    config.set(profile, 'aws_access_key_id', response['Credentials']['AccessKeyId'])
    config.set(profile, 'aws_secret_access_key', response['Credentials']['SecretAccessKey'])
    config.set(profile, 'aws_session_token', response['Credentials']['SessionToken'])

    # Write the updated config file
    with open(filename, 'w+') as configfile:
        config.write(configfile)

    print("Assumed session for {}.".format(
        aws_account_number
    ))

    return session

if __name__ == '__main__':
    
    # Setup command line arguments
    parser = argparse.ArgumentParser(description='Perform STS Assume Role in another account')
    parser.add_argument('--account_id', type=str, required=True, help="AccountId for target AWS Account")
    parser.add_argument('--role_name', type=str, required=True, help="Role Name to assume in target account")
    parser.add_argument('--no_clobber', action='store_true', required=False, help="Do not clobber default profile")
    args = parser.parse_args()

    # Processing Master account
    session = role_name(args.account_id, args.role_name, args.no_clobber)
