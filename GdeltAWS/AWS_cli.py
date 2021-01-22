#!/usr/bin/env python

import argparse
from pathlib import Path
import sys
import os
import boto3
import time
from botocore.exceptions import ClientError
import logging

# Intern variables
project_path = Path.cwd()
script_path = 'script/'
secrets_path = 'secrets/'
sys.path.append(script_path)
availibility_zone = "us-east-1e"



# Retrieve the list of existing buckets
s3 = boto3.client('s3')
response = s3.list_buckets()

if(False):
    # Print -> set it to True if you want it printed in the terminal
    print(project_path)
    print('Existing buckets:')
    for bucket in response['Buckets']:
        print(f'  {bucket["Name"]}')



def create_volume(availability_zone):
    client = boto3.client('ec2', region_name='us-east-1')
    ebs_vol = client.create_volume(Size=20, AvailabilityZone=availability_zone)

    # check that the EBS volume has been created successfully
    if ebs_vol['ResponseMetadata']['HTTPStatusCode'] == 200:
        print("Successfully created Volume! " + ebs_vol['VolumeId'])
    return ebs_vol['VolumeId']


def attach_volume(volume_id, instance_id, first_time=False):
    client = boto3.client('ec2', region_name='us-east-1')
    public_dns_instance = client.describe_instances(InstanceIds=[instance_id])['Reservations'][0] \
        ['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicDnsName']
    client.attach_volume(VolumeId=volume_id, InstanceId=instance_id,
                         Device='/dev/sdm')

    os.system("ssh -o StrictHostKeyChecking=no -i {} hadoop@{} sudo mkdir -p /cassandra/data".format(
        secrets_path / 'gdeltKeyPair.pem',
        public_dns_instance))

    if first_time:
        os.system("ssh -o StrictHostKeyChecking=no -i {} hadoop@{} sudo mkfs -t ext4 /dev/sdm".format(
            secrets_path / 'gdeltKeyPair.pem',
            public_dns_instance))
    os.system("ssh -o StrictHostKeyChecking=no -i {} hadoop@{} sudo mount /dev/sdm /cassandra/data".format(
        secrets_path / 'gdeltKeyPair.pem',
        public_dns_instance))
    print(f"Successfully attached {volume_id} volume to {instance_id} instance!")
    return


def run_db_container(instance_id, db_type, first_node=None):
    """
    For mongo : https://www.freecodecamp.org/news/how-to-deploy-mongo-on-aws-using-docker-the-definitive-guide-for-first-timers-3738f3babd48/
    For neo4j : https://neo4j.com/developer/docker-run-neo4j/
    :param instance_id: string
    :param db_type: string
    :param first_node: boolean
    :return:
    """
    client = boto3.client('ec2', region_name='us-east-1')
    public_dns_instance = client.describe_instances(InstanceIds=[instance_id])['Reservations'][0] \
        ['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicDnsName']
    private_ip_address = client.describe_instances(InstanceIds=[instance_id])['Reservations'][0] \
        ['Instances'][0]['NetworkInterfaces'][0]['PrivateIpAddress']
    if first_node is None:
        if db_type == "cassandra":
            command = f"ssh -o StrictHostKeyChecking=no -i {project_path+'/secrets/gdeltKeyPair.pem'} hadoop@{public_dns_instance} sudo docker run --name {db_type}-node -d -v /{db_type}/data:/var/lib/{db_type} -e CASSANDRA_BROADCAST_ADDRESS={private_ip_address} -p 7000:7000 -p 9042:9042 {db_type}"
            print('Run {}'.format(command))
            os.system(command)
        if db_type == "mongo":
            command = f"ssh -o StrictHostKeyChecking=no -i {project_path+'/secrets/gdeltKeyPair.pem'} hadoop@{public_dns_instance} sudo docker run --name {db_type}-node -d -v /{db_type}/data:/var/lib/{db_type} -e -p 27888:27017 {db_type}"
            print('Run {}'.format(command))
            os.system(command)
        if db_type == "neo4j":
            command = f"ssh -o StrictHostKeyChecking=no -i {project_path+'/secrets/gdeltKeyPair.pem'} hadoop@{public_dns_instance} sudo docker run --name {db_type}-node -d -v /{db_type}/data:/var/lib/{db_type} -e -p 7474:7474 -p 7687:7687 {db_type}"
            print('Run {}'.format(command))
            os.system(command)
        else:
            print(f"FAILED run {db_type} container on the {instance_id} instance! ")
    else:
        private_ip_address_first_node = client.describe_instances(InstanceIds=[first_node])['Reservations'][0] \
            ['Instances'][0]['NetworkInterfaces'][0]['PrivateIpAddress']
        if db_type == "cassandra":
            command = f"ssh -o StrictHostKeyChecking=no -i {project_path+'/secrets/gdeltKeyPair.pem'} hadoop@{public_dns_instance} sudo docker run --name {db_type}-node -d -v /{db_type}/data:/var/lib/{db_type} -e CASSANDRA_SEEDS={private_ip_address_first_node} -e CASSANDRA_BROADCAST_ADDRESS={private_ip_address} -p 7000:7000 -p 9042:9042 {db_type}"
            print('Run {}'.format(command))
            os.system(command)
        if db_type == "mongo":
            command = f"ssh -o StrictHostKeyChecking=no -i {project_path+'/secrets/gdeltKeyPair.pem'} hadoop@{public_dns_instance} sudo docker run --name {db_type}-node -d -v /{db_type}/data:/var/lib/{db_type} -e --add-host manager:{private_ip_address_first_node} -e --add-host worker:{private_ip_address} -p 7000:7000 -p 9042:9042 {db_type}"
            print('Run {}'.format(command))
            os.system(command)
        else:
            print(f"FAILED run {db_type} container on the {instance_id} instance! ")
    print(f"Succesfully run {db_type} container on the {instance_id} instance!")

def create_bucket(bucket_name):
    """Create an S3 bucket in a specified region
    :param bucket_name: Bucket to create
    :return: True if bucket created, else False
    """
    # Create bucket
    try:
        _location="us-east-1"
        s3_client = boto3.client('s3', region_name=_location)
        s3_client.create_bucket(Bucket=bucket_name,
                                CreateBucketConfiguration=_location)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket
    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('params', nargs='*', help='list of parameters')
    parser.add_argument('--create_bucket', dest='create_bucket', action='store_true',
                        help='Create a S3 bucket, indicate name bucket as argument')
    parser.add_argument('--upload_bucket', dest='upload_s3_file', action='store_true',
                        help='upload file into s3 directory, have 2 args : filename and bucket name')
    parser.add_argument('--create_cluster', dest='create_cluster', action='store_true',
                        help='Create a Spark or a db cluster depending on the given parameter : \
                        spark or cassandra or mongo or neo4j / number of instances desired (begin at 0 in case -1)/ type of instance (example : m4.large)')
    parser.add_argument('--attach_volume', dest='attach_volume', action='store_true',
                        help='Attache the given volume to the given instance')
    parser.add_argument('--first_time', dest='first_time', action='store_true',
                        help='Must be set if this is the first volume attachment to format the file system')
    parser.add_argument('--create_volume', dest='create_volume', action='store_true',
                        help='Must provide two parameter : number of volume to create and availability zone.\
                         Create x volume with x corresponding to the given parameter')
    parser.add_argument('--deploy_db', dest='deploy_db', action='store_true',
                        help='Must provide a list of instance id: Launch a db type container on each\
                         specify instances')
    parser.add_argument('--list_instancesEC2', dest='list_instances', action='store_true',
                        help='Give list of all instances EC2 with Platform, Type, Public IPv4, AMI, State infos')
    args = parser.parse_args()
    if args.create_cluster:
        cluster_type = args.params[0]
        nb_instance = args.params[1]
        instance_type = args.params[2]
        if (cluster_type == "spark"):
            os.system(f'ansible-playbook {project_path}/script/spark.yml --extra-vars "type={cluster_type} nb_instance={nb_instance} instance_type={instance_type}"')
        else:
            os.system(f'ansible-playbook {project_path}/script/cluster.yml --extra-vars "type={cluster_type} nb_instance={nb_instance} instance_type={instance_type}"')
    elif args.create_bucket:
        name_bucket = args.params.pop()
        create_bucket(name_bucket)
    elif args.attach_volume:
        instance_id = args.params[0]
        volume_id = args.params[1]
        attach_volume(volume_id=volume_id, instance_id=instance_id, first_time=args.first_time)
    elif args.create_volume:
        n_volumes = int(args.params[0])
        availability_zone = args.params[1]
        for i in range(n_volumes):
            create_volume(availability_zone)
    elif args.deploy_db:
        first_node = args.params.params[0]
        db_type = args.params.params[-1]
        run_db_container(instance_id=first_node, db_type=db_type)
        time.sleep(20)
        for instance_id in args.params:
            run_db_container(instance_id=instance_id, db_type=db_type, first_node=first_node)

    elif args.list_instances:
        ec2 = boto3.resource('ec2')
        with open('inventory_instances.yml') as file:
            for instance in ec2.instances.all():
                file.write("Id: {0}\nPlatform: {1}\nType: {2}\nPublic IPv4: {3}\nAMI: {4}\nState: {5}\n".format(
                        instance.id, instance.platform, instance.instance_type, instance.public_ip_address,
                        instance.image.id,
                        instance.state
                    ))
                print(
                    "Id: {0}\nPlatform: {1}\nType: {2}\nPublic IPv4: {3}\nAMI: {4}\nState: {5}\n".format(
                        instance.id, instance.platform, instance.instance_type, instance.public_ip_address,
                        instance.image.id,
                        instance.state
                    )
                )
    elif args.upload_s3_file:
        file_name = args.params[0]
        bucket = args.params[1]
        upload_file(file_name=file_name, bucket=bucket)