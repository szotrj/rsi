#!/bin/bash
# Sets up GuardDuty for the Master account and invites members

# Set up GuardDuty on Master and invite Members
if [[ $(aws guardduty list-detectors) ]]; then
  echo "Master detector already exists"
else
  aws guardduty create-detector --enable
fi

# Get DetectorId
DETECTORID=$(aws guardduty list-detectors --query 'DetectorIds[]' --output text)

aws guardduty invite-members \
  --detector-id $DETECTORID \
  --account-ids $WORKSPACE/accounts/$ACCOUNTS \
  --message "Invitation to join ECSO GuardDuty Master"
