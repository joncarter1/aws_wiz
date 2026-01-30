# /// script
# dependencies = [
#   "boto3",
#   "click",
#   "rich",
# ]
# ///

import boto3
import json
import sys
import asyncio
import click
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def get_regions():
    try:
        ec2 = boto3.client('ec2', region_name='us-east-1')
        response = ec2.describe_regions()
        return [r['RegionName'] for r in response['Regions']]
    except Exception:
        return ['us-east-1']

def scan_region_sync(region):
    ec2 = boto3.client('ec2', region_name=region)
    data = {
        "ec2": [], "volumes": [], "security_groups": [], 
        "key_pairs": [], "elastic_ips": [], "vpcs": [], 
        "subnets": [], "igws": []
    }
    
    try:
        # Batch 1: Instances
        for res in ec2.describe_instances().get('Reservations', []):
            for i in res.get('Instances', []):
                data["ec2"].append({
                    'InstanceId': i.get('InstanceId'),
                    'InstanceType': i.get('InstanceType'),
                    'State': i.get('State', {}).get('Name'),
                    'PublicIpAddress': i.get('PublicIpAddress'),
                    'PrivateIpAddress': i.get('PrivateIpAddress'),
                    'LaunchTime': i.get('LaunchTime'),
                    'KeyName': i.get('KeyName'),
                    'ImageId': i.get('ImageId'),
                    'PlatformDetails': i.get('PlatformDetails', ''),
                    'Tags': {tag['Key']: tag['Value'] for tag in i.get('Tags', [])},
                    'Region': region
                })
        
        # Batch 2: Volumes
        for v in ec2.describe_volumes().get('Volumes', []):
            data["volumes"].append({
                'VolumeId': v.get('VolumeId'),
                'Size': v.get('Size'),
                'State': v.get('State'),
                'Region': region
            })

        # Batch 3: Security Groups
        for sg in ec2.describe_security_groups().get('SecurityGroups', []):
            data["security_groups"].append({
                'GroupId': sg.get('GroupId'),
                'GroupName': sg.get('GroupName'),
                'Description': sg.get('Description'),
                'Region': region
            })

        # Batch 4: Key Pairs
        for k in ec2.describe_key_pairs().get('KeyPairs', []):
            data["key_pairs"].append({
                'KeyName': k.get('KeyName'),
                'KeyPairId': k.get('KeyPairId'),
                'Region': region
            })

        # Batch 5: Elastic IPs
        for e in ec2.describe_addresses().get('Addresses', []):
            data["elastic_ips"].append({
                'PublicIp': e.get('PublicIp'),
                'AllocationId': e.get('AllocationId'),
                'Region': region
            })

        # Batch 6: VPCs
        for v in ec2.describe_vpcs().get('Vpcs', []):
            name = next((t['Value'] for t in v.get('Tags', []) if t['Key'] == 'Name'), "-")
            data["vpcs"].append({
                'VpcId': v.get('VpcId'),
                'IsDefault': v.get('IsDefault'),
                'CidrBlock': v.get('CidrBlock'),
                'Name': name,
                'Region': region
            })

        # Batch 7: Subnets
        for s in ec2.describe_subnets().get('Subnets', []):
            name = next((t['Value'] for t in s.get('Tags', []) if t['Key'] == 'Name'), "-")
            data["subnets"].append({
                'SubnetId': s.get('SubnetId'),
                'VpcId': s.get('VpcId'),
                'CidrBlock': s.get('CidrBlock'),
                'Name': name,
                'Region': region
            })

        # Batch 8: IGWs
        for i in ec2.describe_internet_gateways().get('InternetGateways', []):
            name = next((t['Value'] for t in i.get('Tags', []) if t['Key'] == 'Name'), "-")
            vpc_id = i['Attachments'][0]['VpcId'] if i['Attachments'] else "-"
            data["igws"].append({
                'InternetGatewayId': i.get('InternetGatewayId'),
                'VpcId': vpc_id,
                'Name': name,
                'Region': region
            })

    except Exception:
        pass
        
    return data

def scan_s3():
    s3 = boto3.client('s3')
    buckets = []
    try:
        response = s3.list_buckets()
        for bucket in response.get('Buckets', []):
            buckets.append({
                'Name': bucket.get('Name'),
                'CreationDate': bucket.get('CreationDate')
            })
    except Exception:
        pass
    return buckets

async def scan_all_async():
    regions = get_regions()
    
    # Setup Progress Bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        
        task_id = progress.add_task(f"[cyan]Scanning {len(regions)} regions...", total=len(regions))
        
        executor = ThreadPoolExecutor(max_workers=20)
        loop = asyncio.get_running_loop()
        
        # Helper to update progress
        async def run_and_track(region):
            res = await loop.run_in_executor(executor, scan_region_sync, region)
            progress.advance(task_id)
            return res

        tasks = [run_and_track(r) for r in regions]
        results = await asyncio.gather(*tasks)
    
    # S3 is global
    s3_data = scan_s3()

    data = {
        "ec2": [], "volumes": [], "security_groups": [], 
        "key_pairs": [], "elastic_ips": [], "vpcs": [],
        "subnets": [], "igws": [], "s3": s3_data,
        "timestamp": datetime.now().isoformat()
    }
    
    for res in results:
        for key in res:
            data[key].extend(res[key])
            
    return data

def calculate_uptime(launch_time):
    if not launch_time: return "-"
    now = datetime.now(timezone.utc)
    diff = now - launch_time
    days = diff.days
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    if days > 0: return f"{days}d {hours}h"
    elif hours > 0: return f"{hours}h {minutes}m"
    else: return f"{minutes}m"

def get_ssh_user(platform_details):
    """Determine SSH user based on platform details"""
    platform = platform_details.lower()
    if 'windows' in platform:
        return 'Administrator'
    elif 'ubuntu' in platform or 'deep learning' in platform:
        return 'ubuntu'
    elif 'amazon' in platform or 'amzn' in platform:
        return 'ec2-user'
    elif 'centos' in platform:
        return 'centos'
    elif 'debian' in platform:
        return 'admin'
    elif 'fedora' in platform:
        return 'fedora'
    elif 'rhel' in platform or 'red hat' in platform:
        return 'ec2-user'
    elif 'suse' in platform:
        return 'ec2-user'
    else:
        return 'ec2-user'  # default

def print_pretty(data):
    console = Console()
    
    # 1. EC2 Table
    console.print("\n[bold cyan]EC2 Instances[/bold cyan]")
    if not data['ec2']:
        console.print("[dim]No instances found.[/dim]")
    else:
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold white")
        table.add_column("Instance ID", style="cyan")
        table.add_column("Name", style="yellow")
        table.add_column("Type")
        table.add_column("State")
        table.add_column("Uptime", justify="right")
        table.add_column("Public IP", style="green")
        table.add_column("Private IP", style="blue")
        table.add_column("SSH Key", style="magenta")
        table.add_column("SSH User", style="bright_magenta")
        table.add_column("Region", style="dim")

        for i in data['ec2']:
            name = i['Tags'].get('Name', '-')
            state_style = "green" if i['State'] == 'running' else "red" if i['State'] == 'terminated' else "yellow"
            uptime = "-"
            if i['State'] == 'running': uptime = calculate_uptime(i['LaunchTime'])
            ssh_user = get_ssh_user(i.get('PlatformDetails', ''))
            
            table.add_row(
                i['InstanceId'], name, i['InstanceType'],
                f"[{state_style}]{i['State']}[/{state_style}]",
                uptime, i['PublicIpAddress'] or "-", i.get('PrivateIpAddress') or "-", 
                i.get('KeyName') or "-", ssh_user, i['Region']
            )
        console.print(table)

    # 2. Volumes
    console.print("\n[bold cyan]EBS Volumes[/bold cyan]")
    if not data['volumes']:
        console.print("[dim]No volumes found.[/dim]")
    else:
        v_table = Table(box=box.ROUNDED, show_header=True)
        v_table.add_column("Volume ID", style="blue")
        v_table.add_column("Size (GiB)", justify="right")
        v_table.add_column("State")
        v_table.add_column("Region", style="dim")
        for v in data['volumes']:
            v_table.add_row(v['VolumeId'], str(v['Size']), v['State'], v['Region'])
        console.print(v_table)

    # 3. Security Groups
    non_defaults = [sg for sg in data['security_groups'] if sg['GroupName'] != 'default']
    console.print(f"\n[bold cyan]Security Groups[/bold cyan] [dim]({len(non_defaults)} non-default found)[/dim]")
    if non_defaults:
        sg_table = Table(box=box.SIMPLE)
        sg_table.add_column("Group ID", style="cyan")
        sg_table.add_column("Name", style="yellow")
        sg_table.add_column("Region", style="dim")
        for sg in non_defaults[:5]:
            sg_table.add_row(sg['GroupId'], sg['GroupName'], sg['Region'])
        console.print(sg_table)
        if len(non_defaults) > 5: console.print(f"[dim]...and {len(non_defaults)-5} more.[/dim]")
    else:
        console.print("[dim]No non-default security groups found.[/dim]")

    # 4. Networking
    console.print("\n[bold cyan]Networking (Non-Default)[/bold cyan]")
    non_default_vpcs = [v for v in data['vpcs'] if not v['IsDefault']]
    if non_default_vpcs:
        v_table = Table(box=box.SIMPLE, title="Custom VPCs")
        v_table.add_column("VPC ID", style="cyan")
        v_table.add_column("Name", style="yellow")
        v_table.add_column("CIDR")
        v_table.add_column("Region", style="dim")
        vpc_ids = {v['VpcId'] for v in non_default_vpcs}
        for v in non_default_vpcs:
            v_table.add_row(v['VpcId'], v['Name'], v['CidrBlock'], v['Region'])
        console.print(v_table)
        
        custom_subnets = [s for s in data['subnets'] if s['VpcId'] in vpc_ids]
        if custom_subnets:
            console.print(f"[dim]Found {len(custom_subnets)} subnets and {len([i for i in data['igws'] if i['VpcId'] in vpc_ids])} IGWs associated with these VPCs.[/dim]")
    else:
        console.print("[dim]No non-default VPCs found.[/dim]")

    # 5. Keys
    console.print("\n[bold cyan]Key Pairs[/bold cyan]")
    if not data['key_pairs']: console.print("[dim]No key pairs found.[/dim]")
    else:
        k_table = Table(box=box.SIMPLE)
        k_table.add_column("Key Name", style="green")
        k_table.add_column("Region", style="dim")
        for k in data['key_pairs']: k_table.add_row(k['KeyName'], k['Region'])
        console.print(k_table)

    # 6. S3
    console.print("\n[bold cyan]S3 Buckets[/bold cyan]")
    if not data['s3']: console.print("[dim]No buckets found.[/dim]")
    else:
        s3_table = Table(box=box.ROUNDED)
        s3_table.add_column("Bucket Name", style="magenta")
        s3_table.add_column("Creation Date", style="dim")
        for b in data['s3']: s3_table.add_row(b['Name'], str(b['CreationDate']))
        console.print(s3_table)

    console.print(f"\n[dim]Scan completed at {data['timestamp']}. {len(data['ec2'])} instances, {len(data['vpcs'])} VPCs.[/dim]\n")

@click.command()
@click.option('--pretty', '-p', is_flag=True, help='Pretty print table')
def main(pretty):
    data = asyncio.run(scan_all_async())
    if pretty:
        print_pretty(data)
    else:
        print(json.dumps(data, indent=2, default=json_serial))

if __name__ == "__main__":
    main()
