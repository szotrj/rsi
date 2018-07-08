import boto3
import json
import re

ec2 = boto3.resource('ec2')

def lambda_handler(event, context):

    instances = ec2.instances.all()

    for instance in instances:
       for vol in instance.volumes.all():
           if vol.tags is None:
               print "Volume " + str(vol.id) + " has no tags"
               createTags(instance, vol)
           name_tag = re.findall(r'Name', str(vol.tags))
           app_tag = re.findall(r'Application', str(vol.tags))
           env_tag = re.findall(r'Environment', str(vol.tags))
           if not name_tag:
               print "Volume " + str(vol.id) + " has no Name tag"
               createTags(instance, vol)
           if not app_tag:
               print "Volume " + str(vol.id) + " has no Application tag"
               createTags(instance, vol)
           if not env_tag:
               print "Volume " + str(vol.id) + " has no Environment tag"
               createTags(instance, vol)

def createTags(instance, volume):

    print "Instance is " + str(instance.id)
    try:
        for tags in instance.tags:
            if tags["Key"] == 'Name':
                instance_name = tags["Value"]
                print "Instance name is " + instance_name
    except Exception as e:
        print "An error occurred %s: %s\n" % (instance_id, e)
        pass
    try:
        for tags in instance.subnet.tags:
            if tags["Key"] == 'Name':
                subnet_name = tags["Value"]
                print "Subnet name is " + subnet_name
    except Exception as e:
        print "An error occurred %s: %s\n" % (instance_id, e)
        pass
    if re.search(r'dev', subnet_name):
        env = "Dev"
    if re.search(r'test', subnet_name):
        env = "Test"
    if re.search(r'trng', subnet_name):
        env = "Trng"
    if re.search(r'prod', subnet_name):
        env = "Prod"
    if re.search(r'egar', subnet_name):
        app = "eGuardian"
    if re.search(r'cyn', subnet_name):
        app = "Cynergy"

    print "Tagging " + str(volume.id) + " Name as " + instance_name
    print "Tagging " + str(volume.id) + " Application as " + app
    print "Tagging " + str(volume.id) + " Environment as " + env

    volume.create_tags(
        DryRun=False,
        Tags=[
            {
                'Key': 'Name',
                'Value': instance_name
            },
            {
                'Key': 'Application',
                'Value': app
            },
            {
                'Key': 'Environment',
                'Value': env
            }
        ]
    )
    print "\n"