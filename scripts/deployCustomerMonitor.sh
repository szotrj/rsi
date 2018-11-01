#!/bin/bash
###############################################################################
## Title: deployCMonitor.sh
## Description: Deploys security monitoring resources to customer accounts
## Note: Deploying CIS Benchmark for customer accounts TBD
## Author: Rob Szot
## Version History: Initial script created 09/18/2018
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
EVENTRULES=$WORKSPACE/cfn/cpmo-event-rules.json
XROLE=$WORKSPACE/cfn/cpmo-monitor-xaccount-role.json
#TARGET=$WORKSPACE/cfn/esoc-audit-target-account.json
if [[ $DEPLOYCIS == "true" ]]; then
  CISROLE=$WORKSPACE/cfn/cpmo-cis-service-role.json
  BENCHMARK=$WORKSPACE/cfn/cis-benchmark.json
  BENCHMARK1=$WORKSPACE/cfn/cis-cloudtrail-setup.json
  BENCHMARK2=$WORKSPACE/cfn/cis-config-setup.json
  BENCHMARK3=$WORKSPACE/cfn/cis-prerequisite-template.json
fi

###################################################################################
# Verify CloudFormation templates json syntax
echo "Validating CloudFormation template syntax with JQ"
if [[ $(cat $EVENTRULES | jq '.') ]]; then echo "$EVENTRULES syntax: passed"; else echo "$EVENTRULES syntax: failed"; exit 1; fi
if [[ $(cat $XROLE | jq '.') ]]; then echo "$XROLE syntax: passed"; else echo "$XROLE syntax: failed"; exit 1; fi
if [[ $DEPLOYCIS == "true" ]]; then
  if [[ $(cat $CISROLE | jq '.') ]]; then echo "$CISROLE syntax: passed"; else echo "$CISROLE syntax: failed"; exit 1; fi
fi

# Validate Lambda Role CloudFormation stack
echo "Validating $XROLE"
aws cloudformation validate-template --template-body file://$XROLE 1>/dev/null
if [[ $? -eq 0 ]]; then echo "Stack validation complete."; else echo "Template validation failed. Exiting script."; exit 1; fi

# Validate Lambda Rule CloudFormation stack
echo "Validating $EVENTRULES"
aws cloudformation validate-template --template-body file://$EVENTRULES 1>/dev/null
if [[ $? -eq 0 ]]; then echo "Stack validation complete."; else echo "Template validation failed. Exiting script."; exit 1; fi

# Validate CISROLE CloudFormation stack
if [[ $DEPLOYCIS == "true" ]]; then
  echo "Validating $CISROLE"
  aws cloudformation validate-template --template-body file://$CISROLE 1>/dev/null
  if [[ $? -eq 0 ]]; then echo "Stack validation complete."; else echo "Template validation failed. Exiting script."; exit 1; fi
fi

###################################################################################

echo "Deploying security remediation stacks to $ACCOUNTNAME"
echo "####################################################################"

# DETERMINE IF THE SM RELATED BUCKET ALREADY EXIST
if [[ $(aws s3 ls s3://$BUCKET 1>/dev/null) ]]; then
	echo "$BUCKET exists"
else
	# Make S3 bucket
	echo "Making S3 bucket: $BUCKET"
	aws s3 mb s3://$BUCKET
	aws s3api put-bucket-versioning --bucket $BUCKET --versioning-configuration Status=Enabled
fi

if [[ $DEPLOYCIS == "true" ]]; then
  echo "Copying CloudFormation templates to client s3://$BUCKET"
  aws s3 cp $BENCHMARK s3://$BUCKET
  aws s3 cp $BENCHMARK1 s3://$BUCKET
  aws s3 cp $BENCHMARK2 s3://$BUCKET
  aws s3 cp $BENCHMARK3 s3://$BUCKET
fi

#############################################################################
# Create or update stacks

## Lambda role stack
aws cloudformation describe-stacks --stack-name cpmo-xmonitor-role 1>/dev/null
if [[ $? -eq 0 ]]; then
	echo "Stack exists. Updating stack..."
  aws cloudformation update-stack --stack-name cpmo-xmonitor-role --template-body file://$XROLE --capabilities CAPABILITY_NAMED_IAM
else
	echo "Stack does not exist. Creating $XROLE..."
	aws cloudformation create-stack --role-arn arn:aws-us-gov:iam::$ACCOUNTID:role/$ROLE \
  --stack-name cpmo-xmonitor-role --template-body file://$XROLE --capabilities CAPABILITY_NAMED_IAM
	if [[ $? -eq 0 ]]; then
    echo "Stack creation initiated. Monitor progress in the AWS Management Console."
	else
    echo "STack creation failed. Exiting script."; exit 1
	fi
fi

## CloudWatch Event Rules stack
aws cloudformation describe-stacks --stack-name cpmo-event-rules 1>/dev/null
if [[ $? -eq 0 ]]; then
	echo "Stack exists. Updating stack..."
	aws cloudformation update-stack --stack-name cpmo-event-rules --template-body file://$EVENTRULES
else
	echo "Stack does not exist. Creating $EVENTRULES..."
	aws cloudformation create-stack --role-arn arn:aws-us-gov:iam::$ACCOUNTID:role/$ROLE \
  --stack-name cpmo-event-rules --template-body file://$EVENTRULES
	if [[ $? -eq 0 ]]; then
    echo "Stack creation initiated. Monitor progress in the AWS Management Console."
	else
    echo "Stack creation failed. Exiting script."; exit 1
	fi
fi

# Create ESOC Target CloudFormation stack
#aws cloudformation describe-stacks --stack-name esoc-audit-target-account
#if [[ $? -eq 0 ]]; then
#  echo "Updating Stack..."
#	 aws cloudformation update-stack --stack-name esoc-audit-target-account --template-body file://$TARGET;
#else
#	 echo "Stack does not exist so Creating $TARGET"
#	 aws cloudformation create-stack --role-arn arn:aws-us-gov:iam::$ACCOUNTID:role/$ROLE1 \
#--stack-name esoc-audit-target-account --template-body file://$TARGET
  #if [[ $? -eq 0 ]]; then
  #  echo "Stack creation complete. Monitor progress in the AWS Management Console."
  #else
  #  echo "Template creation failed. Exiting script."; exit 1
  #fi
#fi

##############################################################################################
# TBD for CIS BenchMark
if [[ $DEPLOYCIS == "true" ]]; then
  echo "Deploying CIS Benchmark"
	## CIS service role stack
	aws cloudformation describe-stacks --stack-name cpmo-cis-service-role 1>/dev/null
	if [[ $? -eq 0 ]]; then
		echo "Stack exists. Updating stack...";
	  aws cloudformation update-stack --stack-name cpmo-cis-service-role --template-body file://$CISBENCHMARKROLE --capabilities CAPABILITY_NAMED_IAM
	else
		echo "Stack does not exist. Creating $CISBENCHMARKROLE..."
		aws cloudformation create-stack --role-arn arn:aws-us-gov:iam::$ACCOUNTID:role/$CISROLE \
  	--stack-name cpmo-cis-service-role --template-body file://$CISBENCHMARKROLE --capabilities CAPABILITY_NAMED_IAM
		if [[ $? -eq 0 ]]; then
	    echo "Stack creation initiated. Monitor progress in the AWS Management Console."
		else
	    echo "Stack creation failed. Exiting script."; exit 1
		fi
	fi
  # Wait to allow the Security Monitoring service role being created
  if [[ $(aws cloudformation wait stack-exists --stack-name cpmo-cis-service-role) ]]; then
    aws cloudformation wait stack-create-complete --stack-name cpmo-cis-service-role
  else
    continue
  fi
  aws cloudformation describe-stacks --stack-name cpmo-cis-benchmark-stack
  if [[ $? -eq 0 ]]; then aws cloudformation delete-stack --stack-name cpmo-cis-benchmark-stack; fi
  # Create CIS BenchMark CloudFormation stack
  echo "Validating $BENCHMARK"
  aws cloudformation validate-template --template-body file://$BENCHMARK
  if [[ $? -eq 0 ]]; then
    echo "Creating stack..."
    aws cloudformation create-stack --role-arn arn:aws-us-gov:iam::$ACCOUNTID:role/$CISROLE \
		--stack-name cpmo-cis-benchmark --template-body file://$BENCHMARK  --capabilities CAPABILITY_NAMED_IAM
    if [[ $? -eq 0 ]]; then echo "Stack creation complete. Monitor progress in the AWS Management Console."; else echo "Stack creation failed."; fi
  else
    echo "Template creation failed. Exiting script."; exit 1
  fi
else
  echo "Skipping CIS Benchmark deployment"
fi

##############################################################################################
echo -e "####################################################################\n"
echo "deployCMonitor.sh complete"
echo -e "####################################################################"
