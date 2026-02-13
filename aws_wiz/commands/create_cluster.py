import boto3
import click
import json
import time
import base64
import os
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from aws_wiz.state import KEYS_DIR, ensure_state_dirs

console = Console()

def create_vpc_and_subnet(ec2, region):
    """Create VPC and subnet for the cluster"""
    console.print("[cyan]Creating VPC...[/cyan]")

    vpc_response = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']

    ec2.create_tags(Resources=[vpc_id], Tags=[{'Key': 'Name', 'Value': 'cluster-vpc'}])

    waiter = ec2.get_waiter('vpc_available')
    waiter.wait(VpcIds=[vpc_id])

    console.print("[cyan]Creating subnet...[/cyan]")
    subnet_response = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')
    subnet_id = subnet_response['Subnet']['SubnetId']

    ec2.create_tags(Resources=[subnet_id], Tags=[{'Key': 'Name', 'Value': 'cluster-subnet'}])

    console.print("[cyan]Creating Internet Gateway...[/cyan]")
    igw_response = ec2.create_internet_gateway()
    igw_id = igw_response['InternetGateway']['InternetGatewayId']

    ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)

    route_tables = ec2.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
    main_route_table_id = route_tables['RouteTables'][0]['RouteTableId']

    ec2.create_route(
        RouteTableId=main_route_table_id,
        DestinationCidrBlock='0.0.0.0/0',
        GatewayId=igw_id
    )

    ec2.modify_subnet_attribute(SubnetId=subnet_id, MapPublicIpOnLaunch={'Value': False})

    return vpc_id, subnet_id, igw_id

def create_security_groups(ec2, vpc_id):
    """Create security groups for bastion and private instances"""
    console.print("[cyan]Creating security groups...[/cyan]")

    bastion_sg_response = ec2.create_security_group(
        GroupName='cluster-bastion-sg',
        Description='Security group for NAT bastion',
        VpcId=vpc_id
    )
    bastion_sg_id = bastion_sg_response['GroupId']

    ec2.authorize_security_group_ingress(
        GroupId=bastion_sg_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },
            {
                'IpProtocol': '-1',
                'IpRanges': [{'CidrIp': '10.0.0.0/16'}]
            }
        ]
    )


    private_sg_response = ec2.create_security_group(
        GroupName='cluster-private-sg',
        Description='Security group for private instances',
        VpcId=vpc_id
    )
    private_sg_id = private_sg_response['GroupId']

    ec2.authorize_security_group_ingress(
        GroupId=private_sg_id,
        IpPermissions=[
            {
                'IpProtocol': '-1',
                'IpRanges': [{'CidrIp': '10.0.0.0/16'}]
            }
        ]
    )

    return bastion_sg_id, private_sg_id

def get_or_create_key_pair(ec2, region):
    """Get existing or create new key pair"""
    key_name = f"cluster-key-{region}"

    try:
        ec2.describe_key_pairs(KeyNames=[key_name])
        console.print(f"[yellow]Using existing key pair: {key_name}[/yellow]")
    except Exception:
        console.print(f"[cyan]Creating key pair: {key_name}[/cyan]")
        response = ec2.create_key_pair(KeyName=key_name)

        ensure_state_dirs()
        key_file = str(KEYS_DIR / f"{key_name}.pem")
        with open(key_file, 'w') as f:
            f.write(response['KeyMaterial'])
        os.chmod(key_file, 0o600)
        console.print(f"[green]Saved private key to {key_file}[/green]")

    return key_name

def get_nat_user_data():
    """Generate user data script for NAT configuration"""
    nat_script = """#!/bin/bash
echo 1 > /proc/sys/net/ipv4/ip_forward
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf

iptables -t nat -A POSTROUTING -o ens5 -j MASQUERADE
iptables -A FORWARD -i ens5 -o ens5 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i ens5 -o ens5 -j ACCEPT

apt-get update
apt-get install -y iptables-persistent
netfilter-persistent save
"""
    return base64.b64encode(nat_script.encode()).decode()

def get_worker_user_data(bastion_ip):
    """Generate user data script for worker nodes to route through bastion"""
    worker_script = f"""#!/bin/bash
# Wait for network to be fully up
sleep 10

# Delete default route through VPC gateway and add route through bastion
ip route del default via 10.0.1.1 2>/dev/null || true
ip route add default via {bastion_ip}

# Make it persistent across reboots
cat > /etc/rc.local << 'EOF'
#!/bin/bash
ip route del default via 10.0.1.1 2>/dev/null || true
ip route add default via {bastion_ip}
exit 0
EOF

chmod +x /etc/rc.local

# Also add as systemd service for modern Ubuntu
cat > /etc/systemd/system/fix-routing.service << EOF
[Unit]
Description=Fix routing to use bastion as gateway
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'sleep 5; ip route del default via 10.0.1.1 2>/dev/null || true; ip route add default via {bastion_ip}'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable fix-routing.service
"""
    return base64.b64encode(worker_script.encode()).decode()

@click.command()
@click.option('--instance-type', default='t3.large', help='Instance type for all instances')
@click.option('--region', default='us-east-1', help='AWS region')
@click.option('--ami-id', help='AMI ID (will auto-detect PyTorch AMI if not provided)')
def create_cluster(instance_type, region, ami_id):
    """Create a 4-machine cluster with custom NAT"""

    ec2 = boto3.client('ec2', region_name=region)

    if not ami_id:
        console.print("[cyan]Using latest PyTorch Deep Learning AMI...[/cyan]")
        ami_id = 'ami-019bc5029386e3730'

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        task = progress.add_task("Setting up VPC infrastructure...", total=None)
        vpc_id, subnet_id, igw_id = create_vpc_and_subnet(ec2, region)

        progress.update(task, description="Creating security groups...")
        bastion_sg_id, private_sg_id = create_security_groups(ec2, vpc_id)

        progress.update(task, description="Setting up key pair...")
        key_name = get_or_create_key_pair(ec2, region)

        progress.update(task, description="Launching bastion instance...")

        bastion_response = ec2.run_instances(
            ImageId=ami_id,
            InstanceType=instance_type,
            KeyName=key_name,
            MaxCount=1,
            MinCount=1,
            NetworkInterfaces=[{
                'DeviceIndex': 0,
                'SubnetId': subnet_id,
                'Groups': [bastion_sg_id],
                'AssociatePublicIpAddress': True,
                'PrivateIpAddress': '10.0.1.10'
            }],
            UserData=get_nat_user_data(),
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value': 'cluster-bastion'},
                    {'Key': 'Role', 'Value': 'bastion'}
                ]
            }],
            InstanceMarketOptions={
                'MarketType': 'spot',
                'SpotOptions': {
                    'SpotInstanceType': 'one-time',
                    'InstanceInterruptionBehavior': 'terminate'
                }
            }
        )

        bastion_id = bastion_response['Instances'][0]['InstanceId']

        progress.update(task, description="Waiting for bastion to be running...")
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[bastion_id])

        bastion_info = ec2.describe_instances(InstanceIds=[bastion_id])
        bastion_public_ip = bastion_info['Reservations'][0]['Instances'][0]['PublicIpAddress']
        bastion_private_ip = '10.0.1.10'

        progress.update(task, description="Configuring bastion for NAT...")

        # Disable source/destination check on bastion so it can forward traffic
        ec2.modify_instance_attribute(
            InstanceId=bastion_id,
            SourceDestCheck={'Value': False}
        )

        progress.update(task, description="Launching private instances...")

        private_instances = []
        for i in range(3):
            private_ip = f'10.0.1.{11 + i}'

            response = ec2.run_instances(
                ImageId=ami_id,
                InstanceType=instance_type,
                KeyName=key_name,
                MaxCount=1,
                MinCount=1,
                NetworkInterfaces=[{
                    'DeviceIndex': 0,
                    'SubnetId': subnet_id,
                    'Groups': [private_sg_id],
                    'AssociatePublicIpAddress': False,
                    'PrivateIpAddress': private_ip
                }],
                UserData=get_worker_user_data(bastion_private_ip),
                TagSpecifications=[{
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'cluster-worker-{i+1}'},
                        {'Key': 'Role', 'Value': 'worker'}
                    ]
                }],
                InstanceMarketOptions={
                    'MarketType': 'spot',
                    'SpotOptions': {
                        'SpotInstanceType': 'one-time',
                        'InstanceInterruptionBehavior': 'terminate'
                    }
                }
            )

            private_instances.append({
                'id': response['Instances'][0]['InstanceId'],
                'private_ip': private_ip,
                'name': f'cluster-worker-{i+1}'
            })

        progress.update(task, description="Waiting for all instances to be running...")
        waiter.wait(InstanceIds=[inst['id'] for inst in private_instances])

        progress.update(task, description="Cluster setup complete!")

    key_path = str(KEYS_DIR / f"{key_name}.pem")

    table = Table(title="Cluster Created Successfully", box=None)
    table.add_column("Instance", style="cyan")
    table.add_column("Instance ID", style="yellow")
    table.add_column("Private IP", style="green")
    table.add_column("Public IP", style="magenta")
    table.add_column("Role", style="blue")

    table.add_row("cluster-bastion", bastion_id, bastion_private_ip, bastion_public_ip, "NAT/Bastion")
    for inst in private_instances:
        table.add_row(inst['name'], inst['id'], inst['private_ip'], "-", "Worker")

    console.print(table)
    console.print(f"\n[green]SSH Access:[/green]")
    console.print(f"  Bastion: ssh -i {key_path} ubuntu@{bastion_public_ip}")
    console.print(f"  Workers: SSH through bastion using private IPs (10.0.1.11-13)")
    console.print(f"\n[yellow]Note: NAT is configured on the bastion instance.[/yellow]")
    console.print(f"[yellow]Workers automatically route internet traffic through bastion at 10.0.1.10[/yellow]")
    console.print(f"[green]Routing is persistent across reboots via systemd service.[/green]")
