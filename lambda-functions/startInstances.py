import boto3

session = boto3.session.Session()
region = session.region_name

# Enter your instances here: ex. ['X-XXXXXXXX', 'X-XXXXXXXX']
instances = ['']

def lambda_handler():

    ec2 = boto3.client('ec2', region_name=region)

    for instance_id in instances:
        instance = ec2.describe_tags(Filters=[{'Name':'resource-id','Values':instance_id.split()}])
        for tags in instance['Tags']:
            if tags["Key"] == 'Name':
                name = tags["Value"]
        try:
            ec2.start_instances(InstanceIds=instance_id.split())
            print 'Started instance: ' + name + '(' + str(instance_id) + ')\n'
        except Exception as e:
            print "An error occurred while attempting to start %s: %s\n" % (instance_id, e)
