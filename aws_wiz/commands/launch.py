import boto3
import click
import os
import stat
from datetime import datetime
from rich.console import Console
from rich.panel import Panel

from aws_wiz.state import KEYS_DIR, ensure_state_dirs

console = Console()


def get_latest_ami(ec2, framework):
    if framework == 'pytorch':
        pattern = "Deep Learning OSS Nvidia Driver AMI GPU PyTorch 2.* (Ubuntu 22.04)*"
    elif framework == 'tensorflow':
        pattern = "Deep Learning OSS Nvidia Driver AMI GPU TensorFlow 2.* (Ubuntu 22.04)*"
    else:
        pattern = "Deep Learning Base OSS Nvidia Driver AMI (Ubuntu 22.04)*"

    filters = [
        {'Name': 'name', 'Values': [pattern]},
        {'Name': 'state', 'Values': ['available']},
        {'Name': 'owner-alias', 'Values': ['amazon']},
        {'Name': 'architecture', 'Values': ['x86_64']}
    ]
    resp = ec2.describe_images(Filters=filters)
    images = resp.get('Images', [])
    images.sort(key=lambda x: x['CreationDate'], reverse=True)
    return images[0]['ImageId'] if images else None

def get_or_create_key(ec2, region):
    ensure_state_dirs()

    # 1. Check if any local key in keys dir exists in AWS
    local_keys = [f for f in os.listdir(KEYS_DIR) if f.endswith(".pem")]
    if local_keys:
        aws_keys_resp = ec2.describe_key_pairs()
        aws_key_names = [k['KeyName'] for k in aws_keys_resp['KeyPairs']]

        for lk in local_keys:
            key_name = lk.replace(".pem", "")
            if key_name in aws_key_names:
                console.print(f"Using existing local key: [green]{lk}[/green]")
                return key_name, str(KEYS_DIR / lk)

    # 2. Otherwise, create a new one
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    key_name = f"aws-wiz-{region}-{timestamp}"
    key_file = str(KEYS_DIR / f"{key_name}.pem")

    console.print(f"Generating new key pair: [bold cyan]{key_name}[/bold cyan]...")
    resp = ec2.create_key_pair(KeyName=key_name)

    with open(key_file, "w") as f:
        f.write(resp['KeyMaterial'])

    # Set permissions to 400 (required for SSH)
    os.chmod(key_file, stat.S_IRUSR)

    return key_name, key_file

def get_or_create_sg(ec2, vpc_id=None):
    sg_name = "aws-wiz-ssh"

    if not vpc_id:
        vpcs = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
        if vpcs['Vpcs']:
            vpc_id = vpcs['Vpcs'][0]['VpcId']
        else:
            vpcs = ec2.describe_vpcs()
            if vpcs['Vpcs']: vpc_id = vpcs['Vpcs'][0]['VpcId']
            else: return None

    try:
        resp = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [sg_name]}, {'Name': 'vpc-id', 'Values': [vpc_id]}]
        )
        if resp['SecurityGroups']:
            return resp['SecurityGroups'][0]['GroupId']
    except Exception:
        pass

    try:
        resp = ec2.create_security_group(GroupName=sg_name, Description="Allow SSH for AWS Wiz", VpcId=vpc_id)
        group_id = resp['GroupId']
        ec2.authorize_security_group_ingress(
            GroupId=group_id,
            IpPermissions=[{'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}]
        )
        return group_id
    except Exception as e:
        console.print(f"[red]Error creating SG: {e}[/red]")
        return None

@click.command()
@click.option('--type', '-t', required=True, help='Instance Type')
@click.option('--region', '-r', default='us-east-1', help='AWS Region')
@click.option('--name', '-n', default='training-rig', help='Instance Name')
@click.option('--spot', '-s', is_flag=True, help='Use Spot')
@click.option('--framework', '-f', default='pytorch', type=click.Choice(['pytorch', 'tensorflow', 'base']), help='DL Framework')
@click.option('--iam-profile', help='IAM Instance Profile Name')
def launch(type, region, name, spot, framework, iam_profile):
    """Launch a GPU instance and manage SSH keys automatically."""
    ec2 = boto3.client('ec2', region_name=region)

    console.print(Panel(f"Launching [bold cyan]{type}[/bold cyan] in [yellow]{region}[/yellow]", title="AwsWiz Launch"))

    # 1. AMI
    with console.status("Finding AMI..."):
        ami_id = get_latest_ami(ec2, framework)
        if not ami_id: return

    # 2. Key Pair (Auto-Managed)
    key_name, key_path = get_or_create_key(ec2, region)

    # 3. Security Group
    sg_id = get_or_create_sg(ec2)
    if not sg_id: return

    # 4. Launch
    # Get first available subnet
    vpcs = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
    if vpcs['Vpcs']:
        vpc_id = vpcs['Vpcs'][0]['VpcId']
        subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
        if subnets['Subnets']:
            subnet_id = subnets['Subnets'][0]['SubnetId']
        else:
            console.print("[red]No subnets found in default VPC[/red]")
            return

    launch_args = {
        'ImageId': ami_id, 'InstanceType': type, 'KeyName': key_name,
        'SecurityGroupIds': [sg_id], 'MinCount': 1, 'MaxCount': 1,
        'SubnetId': subnet_id,
        'TagSpecifications': [{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': name}]}]
    }
    if spot: launch_args['InstanceMarketOptions'] = {'MarketType': 'spot'}
    if iam_profile:
        launch_args['IamInstanceProfile'] = {'Name': iam_profile}

    try:
        with console.status("Launching..."):
            resp = ec2.run_instances(**launch_args)
            instance_id = resp['Instances'][0]['InstanceId']
            console.print(f"[bold green]Launch Successful! ID: {instance_id}[/bold green]")

        # 5. Wait for IP
        with console.status("Waiting for Public IP..."):
            waiter = ec2.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])
            resp = ec2.describe_instances(InstanceIds=[instance_id])
            public_ip = resp['Reservations'][0]['Instances'][0].get('PublicIpAddress')

        if public_ip:
            console.print(Panel(
                f"Instance is RUNNING.\n\n"
                f"Public IP: [bold cyan]{public_ip}[/bold cyan]\n"
                f"Connect: [bold green]ssh -i {key_path} ubuntu@{public_ip}[/bold green]",
                title="Ready", border_style="green"
            ))
    except Exception as e:
        console.print(f"[bold red]Launch Failed:[/bold red] {e}")
