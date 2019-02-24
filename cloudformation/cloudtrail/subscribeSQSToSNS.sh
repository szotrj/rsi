#!/bin/bash

ACCOUNTS=
CENTRALACCOUNTID=

for id in `cat $ACCOUNTS`; do
	echo "aws sns subscribe --topic-arn arn:aws-us-gov:sns:us-gov-west-1:$id:cloudtrail --notification-endpoint arn:aws-us-gov:sqs:us-gov-west-1:$CENTRALACCOUNTID:SplunkQueue --protocol sqs"
done
