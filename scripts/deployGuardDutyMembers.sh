#!/bin/bash

# Set up GuardGuty on Members and accept invitations
while read line
do
  if [[ $(aws guardduty list-detectors) ]]; then
    echo "Master detector already exists"
  else
    aws guardduty create-detector --enable
  fi

  # Get DetectorId
  DETECTORID=$(aws guardduty list-detectors --query 'DetectorIds[]' --output text)

done < $WORKSPACE/accounts/$ACCOUNTS
