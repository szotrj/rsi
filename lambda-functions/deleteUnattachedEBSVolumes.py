import boto3
import re

session = boto3.session.Session()
region = session.region_name

def lambda_handler(event, context):

    ec2 = boto3.resource('ec2', region_name)

    for v in ec2.volumes.all():
        vid=v.id
        vol=ec2.Volume(vid)
        if v.state=='available':
            # EBS volume with no tags at all
            if v.tags is None:
                vol.delete()
                print "Deleted " + vid
                continue
            # EBS volume with a Delete tag
            for tag in v.tags:
                if tag['Key'] == 'Delete':
                    value=tag['Value']
                    if value != 'false' and value != 'False' and v.state=='available':
                        vol.delete()
                        print "Deleted " + vid + " with Delete=" + value
            # EBS volume tagged, but missing Delete tag
            delete_tag = re.findall(r'Delete', str(v.tags))
            if not delete_tag:
                vol.delete()
                print "Deleted " + vid + " with missing Delete tag"
