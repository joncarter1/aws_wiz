import boto3


def get_regions():
    try:
        ec2 = boto3.client('ec2', region_name='us-east-1')
        response = ec2.describe_regions()
        return [r['RegionName'] for r in response['Regions']]
    except Exception:
        return ['us-east-1']
