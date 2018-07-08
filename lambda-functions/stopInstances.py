import boto3
import re

session = boto3.session.Session()
region = session.region_name

def lambda_handler(event, context):

    # Set EC2 resource based on region
    ec2 = boto3.resource('ec2', region_name=region)

    # Filter on running instances
    filters= [
        { 'Name':'instance-state-name', 'Values': ['running'] }
    ]

    # Get list of instances based on filters
    instances = ec2.instances.filter(Filters=filters)
    
    # Loop through filtered instances
    for instance in instances:
        # Get the instance name and Shutdown tag
        for tag in instance.tags:
            if tag['Key'] == 'Name':
                name = tag['Value']
            if tag['Key'] == 'Shutdown':
                shutdown = tag['Value']
        # Check if there's a Shutdown tag
        shutdown_tag = re.findall('Shutdown|shutdown', str(instance.tags))
        # Stop instance if there's no Shutdown tag or if Shutdown != false|False
        if not shutdown_tag or str.lower(shutdown) != 'false':
            # Stop the instance
            print 'Stopping instance: ' + name + ' (' + instance.id + ')'
            instance.stop(DryRun=False)
