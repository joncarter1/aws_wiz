# /// script
# dependencies = [
#   "boto3",
# ]
# ///

import boto3

ec2 = boto3.client('ec2', region_name='us-east-1')
pattern = 'Deep Learning OSS Nvidia Driver AMI GPU PyTorch 2.* (Ubuntu 22.04)*'
filters = [
    {'Name': 'name', 'Values': [pattern]},
    {'Name': 'state', 'Values': ['available']},
    {'Name': 'owner-alias', 'Values': ['amazon']},
    {'Name': 'architecture', 'Values': ['x86_64']}
]
resp = ec2.describe_images(Filters=filters)
images = resp.get('Images', [])
images.sort(key=lambda x: x['CreationDate'], reverse=True)
if images:
    print(f'AMI ID: {images[0]["ImageId"]}')
    print(f'Name: {images[0]["Name"]}')
else:
    print("No AMI found")