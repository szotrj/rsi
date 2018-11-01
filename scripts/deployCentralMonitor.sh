#!/bin/bash
###############################################################################
## Title: deployMonitor.sh
## Description: Deploys security monitoring resource in central account
## Note: Deploying CIS Benchmark for customer accounts TBD
## Author: Rob Szot
## Version History: Initial script created on 09/18/2018
##                  Script overhaul and cleanup - 10/26/2018 - rjszot
###############################################################################

ACCOUNTID=$(aws sts get-caller-identity --output text --query 'Account')
ACCOUNTNAME=$(aws iam list-account-aliases --query 'AccountAliases[0]' --output text | sed 's/"//g')
if [[ "x$ACCOUNTNAME" == "x" ]]; then ACCOUNTNAME=$ACCOUNTID; fi
BUCKET=cpmo-monitor-functions-$ACCOUNTID
ROLE=CloudFormationRole
CISROLE=CISRole
DEPLOYCIS=$DEPLOYCIS
DEPLOYCIS=false

# Check if the script is run by Jenkins
if [[ "x$(whoami)" == "xjenkins" ]]; then WORKSPACE=$1; else WORKSPACE=~/cpmo; fi
PACKAGE=$WORKSPACE/lambda-functions/$ZIPFILE
LAMBDA=$WORKSPACE/cfn/cpmo-remediation-functions.json
CENTRALROLE=$WORKSPACE/cfn/cpmo-central-monitor-role.json
XROLE=$WORKSPACE/cfn/cpmo-monitor-xaccount-role.json
#LOGGING=$WORKSPACE/cfn/esoc-audit-logging-bucket.json
if [[ $DEPLOYCIS == "true" ]]; then
  CISROLE=$WORKSPACE/cfn/cpmo-cis-service-role.json
  BENCHMARK=$WORKSPACE/cfn/cis-benchmark.json
  BENCHMARK1=$WORKSPACE/cfn/cis-cloudtrail-setup.json
  BENCHMARK2=$WORKSPACE/cfn/cis-config-setup.json
  BENCHMARK3=$WORKSPACE/cfn/cis-prerequisite-template.json
fi
##############################################################################

# Verify Cloud Formation templates is in correct json format:
echo "Validate CloudFormation Template JSON syntax with JQ"
if [[ $(cat $LAMBDA | jq '.') ]]; then echo "$LAMBDA syntax: passed"; else echo "$LAMBDA syntax: failed"; exit 1; fi
if [[ $(cat $CENTRALROLE | jq '.') ]]; then echo "$CENTRALROLE syntax: passed"; else echo "$CENTRALROLE syntax: failed"; exit 1; fi
if [[ $(cat $XROLE | jq '.') ]]; then echo "$XROLE syntax: passed"; else echo "$XROLE syntax: failed"; exit 1; fi
#if [[ $(cat $LOGGING | jq '.') ]]; then echo "$LOGGING syntax: passed"; else echo "$LOGGING syntax: failed"; exit 1; fi
if [[ $DEPLOYCIS == "true" ]]; then
  if [[ $(cat $CISROLE | jq '.') ]]; then echo "$CISROLE syntax: passed"; else echo "$CISROLE syntax: failed"; exit 1; fi
fi

##############################################################################

## Validating ALL CF stacks at this stage,
## If any CF stack is not properly formatted then exit this program immediately

## Validate CISROLE CloudFormation stack
if [[ $DEPLOYCIS == "true" ]]; then
  echo "Validating $CISROLE"
  aws cloudformation validate-template --template-body file://$CISROLE 1>/dev/null
  if [[ $? -eq 0 ]]; then echo "Stack validation complete."; else echo "Template validation failed. Exiting script."; exit 1; fi
fi

## Validate Lambda Role CloudFormation stack
echo "Validating $CENTRALROLE"
aws cloudformation validate-template --template-body file://$CENTRALROLE 1>/dev/null
if [[ $? -eq 0 ]]; then echo "Stack validation complete."; else echo "Template validation failed. Exiting script."; exit 1; fi

## Validate Lambda Functions CloudFormation stack
echo "Validating $LAMBDA"
aws cloudformation validate-template --template-body file://$LAMBDA 1>/dev/null
if [[ $? -eq 0 ]]; then echo "Stack validation complete."; else echo "Template validation failed. Exiting script."; exit 1; fi

## Validate XRole CloudFormation stack for Lambda to assume
echo "Validating $XROLE"
aws cloudformation validate-template --template-body file://$XROLE 1>/dev/null
if [[ $? -eq 0 ]]; then echo "Stack validation complete."; else echo "Template validation failed. Exiting script."; exit 1; fi

## Validate Logging CloudFormation stack for ESOC use
#echo "Validating $LOGGING"
#aws cloudformation validate-template --template-body file://$LOGGING 1>/dev/null
#if [[ $? -eq 0 ]]; then echo "Stack validation complete."; else echo "Template validation failed. Exiting script."; exit 1; fi

###########################################################################

echo "Deploying security remediation stacks to $ACCOUNTNAME"
echo -"####################################################################"

# DETERMINE IF SM RELATED BUCKET ALREADY EXIST
if [[ $(aws s3 ls s3://$BUCKET 1>/dev/null) ]]; then
	echo "$BUCKET exists"
else
	# Make S3 bucket
	echo "Making S3 bucket: $BUCKET"
	aws s3 mb s3://$BUCKET
	aws s3api put-bucket-versioning --bucket $BUCKET --versioning-configuration Status=Enabled
fi

echo "Copying CloudFormation templates and Lambda code to s3://$BUCKET"
aws s3 cp $PACKAGE s3://$BUCKET
if [[ $DEPLOYCIS == "true" ]]; then
  aws s3 cp $BENCHMARK s3://$BUCKET
  aws s3 cp $BENCHMARK1 s3://$BUCKET
  aws s3 cp $BENCHMARK2 s3://$BUCKET
  aws s3 cp $BENCHMARK3 s3://$BUCKET
fi

# Get latest object version to pass to Monitor Functions CloudFormation template
VERSIONID=$(aws s3api list-object-versions --bucket $BUCKET --prefix $ZIPFILE --query 'Versions[?IsLatest==`true`].[VersionId]' --output text)
echo "$VERSIONID is latest Lambda zip file object version ID"

#############################################################################
# Create or update stacks

aws cloudformation describe-stacks --stack-name cpmo-cis-service-role 1>/dev/null
if [[ $? -eq 0 ]]; then
	echo "Stack exists. Updating stack...";
  aws cloudformation update-stack --stack-name cpmo-cis-service-role --template-body file://$CISROLE --capabilities CAPABILITY_NAMED_IAM;
else
	echo "Stack does not exist. Creating $CISROLE...";
	aws cloudformation create-stack --role-arn arn:aws-us-gov:iam::$ACCOUNTID:role/$ROLE \
  --stack-name cpmo-cis-service-role --template-body file://$CISROLE --capabilities CAPABILITY_NAMED_IAM
	if [[ $? -eq 0 ]]; then
    echo "Stack creation initiated. Monitor progress in the AWS Management Console."
	else
    echo "Stack creation failed. Exiting script."; exit 1
	fi
fi

## Create Lambda Role CloudFormation stack
aws cloudformation describe-stacks --stack-name cpmo-monitor-role 1>/dev/null
if [[ $? -eq 0 ]]; then
	echo "Stack exists. Updating stack...";
  aws cloudformation update-stack --stack-name cpmo-monitor-role --template-body file://$CENTRALROLE --capabilities CAPABILITY_NAMED_IAM;
else
	echo "Stack does not exist. Creating $CENTRALROLE...";
	aws cloudformation create-stack --role-arn arn:aws-us-gov:iam::$ACCOUNTID:role/$ROLE \
  --stack-name cpmo-monitor-role --template-body file://$CENTRALROLE --capabilities CAPABILITY_NAMED_IAM
	if [[ $? -eq 0 ]]; then
    echo "Stack creation initiated. Monitor progress in the AWS Management Console."
	else
    echo "Stack creation failed. Exiting script."; exit 1
	fi
fi

## Create Lambda Functions CloudFormation stack
aws cloudformation describe-stacks --stack-name cpmo-remediation-functions 1>/dev/null
if [[ $? -eq 0 ]]; then
	echo "Updating stack with new Lambda package..."
	aws cloudformation update-stack --stack-name cpmo-remediation-functions --template-body file://$LAMBDA \
	--parameters ParameterKey=Package,ParameterValue=$ZIPFILE ParameterKey=VersionId,ParameterValue=$VERSIONID --capabilities CAPABILITY_NAMED_IAM
else
	echo "Stack does not exist. Creating $LAMBDA..."
	aws cloudformation create-stack --stack-name cpmo-remediation-functions --template-body file://$LAMBDA \
  --parameters ParameterKey=Package,ParameterValue=$ZIPFILE ParameterKey=VersionId,ParameterValue=$VERSIONID --capabilities CAPABILITY_NAMED_IAM
	if [[ $? -eq 0 ]]; then
    echo "Stack creation initiated. Monitor progress in the AWS Management Console."
	else
    echo "Stack creation failed. Exiting script."; exit 1
	fi
fi

# Wait to allow the Security Monitoring service role being created
if [[ $(aws cloudformation wait stack-exists --stack-name cpmo-remediation-functions) ]]; then
	aws cloudformation wait stack-create-complete --stack-name cpmo-remediation-functions
else
	continue
fi

# Create Event Bus permission for customer account
echo "Creating Event Bus Permission"
aws events put-permission --action events:PutEvents --statement-id $ACCOUNTID --principal $ACCOUNTID

echo "Verify Event Bus"
aws events describe-event-bus

## Create ESOC Logging CloudFormation stack
#aws cloudformation describe-stacks --stack-name esoc-audit-logging-bucket
#if [[ $? -eq 0 ]]; then
#	 echo "Updating Stack..."
#	 aws cloudformation update-stack --stack-name esoc-audit-logging-bucket --template-body file://$LOGGING;
#else
#  echo "Stack does not exist so Creating $LOGGING"
#	 aws cloudformation create-stack --role-arn arn:aws-us-gov:iam::$ACCOUNTID:role/$CISBENCHMARKROLE \
#  --stack-name cpmo-esoc-logging --template-body file://$LOGGING
#	 if [[ $? -eq 0 ]]; then
#    echo "Stack creation complete. Monitor progress in the AWS Management Console."
#	 else
#    echo "Template creation failed. Exiting script."; exit 1
#	 fi
#fi

#####################################################################################
# TBD for CIS Benchmark

if [[ $DEPLOYCIS == "true" ]]; then
  echo "Deploying CIS Benchmark"
  # Create Lambda XRole CloudFormation stack
  aws cloudformation describe-stacks --stack-name cpmo-xmonitor-account-role-stack
  if [[ $? -eq 0 ]]; then
    echo "Updating Stack..."
    aws cloudformation update-stack --stack-name cpmo-xmonitor-account-role-stack --template-body file://$XROLE --capabilities CAPABILITY_NAMED_IAM;
  else
    echo "Stack does not exist so Creating $XROLE"
    aws cloudformation create-stack --role-arn arn:aws-us-gov:iam::$ACCOUNTID:role/$ROLE1 --stack-name cpmo-monitor-role-stack --template-body file://$XROLE --capabilities CAPABILITY_NAMED_IAM
		if [[ $? -eq 0 ]]; then
      echo "Stack creation complete. Monitor progress in the AWS Management Console."
		else
      echo "Template creation failed. Exiting script."; exit 1
		fi
  fi

  # Create CIS Benchmark CloudFormation stack
  echo "Validating $BENCHMARK"
  aws cloudformation validate-template --template-body file://$BENCHMARK
  if [[ $? -eq 0 ]]; then
    echo "Creating stack..."
    aws cloudformation create-stack --role-arn arn:aws-us-gov:iam::$ACCOUNTID:role/$ROLE --stack-name cpmo-cis-benchmark-stack --template-body file://$BENCHMARK  --capabilities CAPABILITY_NAMED_IAM
    if [[ $? -eq 0 ]]; then
      echo "Stack creation initiated. Monitor progress in the AWS Management Console."
    else
      echo "Stack creation failed."; exit 1
    fi
  else
    echo "Stack validation failed. Exiting script."; exit 1
  fi
else
  echo "Skipping CIS Benchmark deployment"
fi

##############################################################################################
echo "####################################################################"
echo "deployCustomerMonitor.sh complete"
echo "####################################################################"
