#!/bin/bash

inputfile=$1
accounts=accounts.txt
for id in $(cat $accounts); do
    if ! [[ $(grep "$id" "$inputfile") ]]; then
	echo "Adding $id to $inputfile"
        jq ".Resource += [{ \"Fn::Sub\": \"arn:\${AWS::Partition}:s3:::\${pCloudTrailBucketName}/AWSLogs/"$id"/*\" }]" $inputfile > tmp.json
        mv tmp.json $inputfile
    else
	echo "$id exists in $inputfile"
    fi
done
cat $inputfile
