# /// script
# dependencies = [
#   "boto3",
#   "click",
#   "rich",
# ]
# ///

import boto3
import click
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

console = Console()

def get_regions():
    try:
        ec2 = boto3.client('ec2', region_name='us-east-1')
        response = ec2.describe_regions()
        return [r['RegionName'] for r in response['Regions']]
    except Exception:
        return ['us-east-1']

def terminate_instances(region):
    """Terminate all EC2 instances in a region"""
    terminated = []
    try:
        ec2 = boto3.client('ec2', region_name=region)
        response = ec2.describe_instances()
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                if instance['State']['Name'] not in ['terminated', 'terminating']:
                    instance_id = instance['InstanceId']
                    name = 'Unknown'
                    for tag in instance.get('Tags', []):
                        if tag['Key'] == 'Name':
                            name = tag['Value']
                            break
                    
                    try:
                        ec2.terminate_instances(InstanceIds=[instance_id])
                        terminated.append((instance_id, name, region))
                    except Exception as e:
                        console.print(f"[red]Error terminating {instance_id}: {e}[/red]")
    except Exception as e:
        if 'AuthFailure' not in str(e):
            console.print(f"[red]Error in {region}: {e}[/red]")
    
    return terminated

def delete_vpcs(region):
    """Delete all non-default VPCs and their dependencies"""
    deleted_vpcs = []
    try:
        ec2 = boto3.client('ec2', region_name=region)
        
        # Get all VPCs
        vpcs = ec2.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['false']}])
        
        for vpc in vpcs['Vpcs']:
            vpc_id = vpc['VpcId']
            vpc_name = vpc_id
            for tag in vpc.get('Tags', []):
                if tag['Key'] == 'Name':
                    vpc_name = tag['Value']
                    break
            
            try:
                # Delete subnets
                subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
                for subnet in subnets['Subnets']:
                    try:
                        ec2.delete_subnet(SubnetId=subnet['SubnetId'])
                    except Exception:
                        pass
                
                # Delete route tables
                route_tables = ec2.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
                for rt in route_tables['RouteTables']:
                    if not any(assoc.get('Main', False) for assoc in rt.get('Associations', [])):
                        try:
                            ec2.delete_route_table(RouteTableId=rt['RouteTableId'])
                        except Exception:
                            pass
                
                # Detach and delete internet gateways
                igws = ec2.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}])
                for igw in igws['InternetGateways']:
                    try:
                        ec2.detach_internet_gateway(InternetGatewayId=igw['InternetGatewayId'], VpcId=vpc_id)
                        ec2.delete_internet_gateway(InternetGatewayId=igw['InternetGatewayId'])
                    except Exception:
                        pass
                
                # Delete NAT gateways
                nat_gateways = ec2.describe_nat_gateways(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
                for nat in nat_gateways['NatGateways']:
                    if nat['State'] not in ['deleted', 'deleting']:
                        try:
                            ec2.delete_nat_gateway(NatGatewayId=nat['NatGatewayId'])
                        except Exception:
                            pass
                
                # Delete security groups
                sgs = ec2.describe_security_groups(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
                for sg in sgs['SecurityGroups']:
                    if sg['GroupName'] != 'default':
                        try:
                            ec2.delete_security_group(GroupId=sg['GroupId'])
                        except Exception:
                            pass
                
                # Delete VPC
                ec2.delete_vpc(VpcId=vpc_id)
                deleted_vpcs.append((vpc_id, vpc_name, region))
                
            except Exception as e:
                console.print(f"[red]Error deleting VPC {vpc_id}: {e}[/red]")
    
    except Exception as e:
        if 'AuthFailure' not in str(e):
            console.print(f"[red]Error in {region}: {e}[/red]")
    
    return deleted_vpcs

def release_elastic_ips(region):
    """Release all Elastic IPs"""
    released = []
    try:
        ec2 = boto3.client('ec2', region_name=region)
        eips = ec2.describe_addresses()
        
        for eip in eips['Addresses']:
            try:
                if 'AssociationId' in eip:
                    ec2.disassociate_address(AssociationId=eip['AssociationId'])
                ec2.release_address(AllocationId=eip['AllocationId'])
                released.append((eip.get('PublicIp', 'Unknown'), region))
            except Exception as e:
                console.print(f"[red]Error releasing EIP: {e}[/red]")
    
    except Exception:
        pass
    
    return released

def delete_key_pairs(region):
    """Delete all key pairs"""
    deleted = []
    try:
        ec2 = boto3.client('ec2', region_name=region)
        key_pairs = ec2.describe_key_pairs()
        
        for kp in key_pairs['KeyPairs']:
            try:
                ec2.delete_key_pair(KeyName=kp['KeyName'])
                deleted.append((kp['KeyName'], region))
            except Exception as e:
                console.print(f"[red]Error deleting key pair {kp['KeyName']}: {e}[/red]")
    
    except Exception:
        pass
    
    return deleted

def delete_volumes(region):
    """Delete all available EBS volumes"""
    deleted = []
    try:
        ec2 = boto3.client('ec2', region_name=region)
        volumes = ec2.describe_volumes(Filters=[{'Name': 'status', 'Values': ['available']}])
        
        for volume in volumes['Volumes']:
            try:
                ec2.delete_volume(VolumeId=volume['VolumeId'])
                deleted.append((volume['VolumeId'], volume['Size'], region))
            except Exception as e:
                console.print(f"[red]Error deleting volume {volume['VolumeId']}: {e}[/red]")
    
    except Exception:
        pass
    
    return deleted

@click.command()
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@click.option('--region', help='Specific region to nuke (default: all regions)')
def nuke(force, region):
    """Nuclear option: Delete ALL AWS resources (except S3 buckets)"""
    
    # Warning panel
    console.print(Panel.fit(
        "[bold red]⚠️  EXTREME DANGER ⚠️[/bold red]\n\n"
        "This will PERMANENTLY DELETE:\n"
        "• All EC2 instances\n"
        "• All VPCs and networking\n"
        "• All Elastic IPs\n"
        "• All Key Pairs\n"
        "• All available EBS volumes\n\n"
        "[bold]This action cannot be undone![/bold]",
        title="[bold red]NUCLEAR DELETION WARNING[/bold red]",
        border_style="red"
    ))
    
    if not force:
        confirmation = console.input("\n[bold red]Type 'DESTROY EVERYTHING' to confirm: [/bold red]")
        if confirmation != "DESTROY EVERYTHING":
            console.print("[yellow]Aborted. Nothing was deleted.[/yellow]")
            return
    
    regions = [region] if region else get_regions()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Phase 1: Terminate instances
        task = progress.add_task(f"[red]Terminating EC2 instances across {len(regions)} regions...[/red]", total=None)
        
        all_terminated = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(terminate_instances, r) for r in regions]
            for future in as_completed(futures):
                all_terminated.extend(future.result())
        
        if all_terminated:
            console.print(f"\n[red]Terminated {len(all_terminated)} instances[/red]")
            for instance_id, name, region in all_terminated[:10]:
                console.print(f"  • {instance_id} ({name}) in {region}")
            if len(all_terminated) > 10:
                console.print(f"  ... and {len(all_terminated) - 10} more")
        
        # Wait for instances to terminate
        if all_terminated:
            progress.update(task, description="[yellow]Waiting for instances to terminate...[/yellow]")
            time.sleep(30)
        
        # Phase 2: Delete VPCs
        progress.update(task, description="[red]Deleting VPCs and networking...[/red]")
        
        all_vpcs = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(delete_vpcs, r) for r in regions]
            for future in as_completed(futures):
                all_vpcs.extend(future.result())
        
        if all_vpcs:
            console.print(f"\n[red]Deleted {len(all_vpcs)} VPCs[/red]")
            for vpc_id, name, region in all_vpcs:
                console.print(f"  • {vpc_id} ({name}) in {region}")
        
        # Phase 3: Release Elastic IPs
        progress.update(task, description="[red]Releasing Elastic IPs...[/red]")
        
        all_eips = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(release_elastic_ips, r) for r in regions]
            for future in as_completed(futures):
                all_eips.extend(future.result())
        
        if all_eips:
            console.print(f"\n[red]Released {len(all_eips)} Elastic IPs[/red]")
        
        # Phase 4: Delete Key Pairs
        progress.update(task, description="[red]Deleting key pairs...[/red]")
        
        all_keys = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(delete_key_pairs, r) for r in regions]
            for future in as_completed(futures):
                all_keys.extend(future.result())
        
        if all_keys:
            console.print(f"\n[red]Deleted {len(all_keys)} key pairs[/red]")
            for key_name, region in all_keys:
                console.print(f"  • {key_name} in {region}")
        
        # Phase 5: Delete available volumes
        progress.update(task, description="[red]Deleting available EBS volumes...[/red]")
        
        all_volumes = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(delete_volumes, r) for r in regions]
            for future in as_completed(futures):
                all_volumes.extend(future.result())
        
        if all_volumes:
            total_gb = sum(size for _, size, _ in all_volumes)
            console.print(f"\n[red]Deleted {len(all_volumes)} volumes ({total_gb} GB total)[/red]")
        
        progress.update(task, description="[bold green]Nuclear deletion complete![/bold green]")
    
    # Summary
    console.print("\n" + "="*50)
    console.print(Panel.fit(
        f"[bold red]DESTRUCTION COMPLETE[/bold red]\n\n"
        f"• Instances terminated: {len(all_terminated)}\n"
        f"• VPCs deleted: {len(all_vpcs)}\n"
        f"• Elastic IPs released: {len(all_eips)}\n"
        f"• Key pairs deleted: {len(all_keys)}\n"
        f"• Volumes deleted: {len(all_volumes)}\n\n"
        f"[yellow]S3 buckets were preserved (as requested)[/yellow]",
        title="[bold]Final Report[/bold]",
        border_style="red"
    ))

if __name__ == "__main__":
    nuke()