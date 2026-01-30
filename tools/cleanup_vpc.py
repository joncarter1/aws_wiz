# /// script
# dependencies = [
#   "boto3",
#   "click",
#   "rich",
# ]
# ///

import boto3
import click
import sys
import time
from rich.console import Console
from rich.panel import Panel

def delete_vpc_dependencies(ec2, vpc_id):
    console = Console()
    
    # 1. Delete Subnets
    subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['Subnets']
    for sn in subnets:
        try:
            ec2.delete_subnet(SubnetId=sn['SubnetId'])
            console.print(f"  - Deleted Subnet: {sn['SubnetId']}")
        except Exception as e:
            console.print(f"  [red]- Error Subnet {sn['SubnetId']}: {e}[/red]")

    # 2. Detach & Delete IGWs
    igws = ec2.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}])['InternetGateways']
    for igw in igws:
        try:
            ec2.detach_internet_gateway(InternetGatewayId=igw['InternetGatewayId'], VpcId=vpc_id)
            ec2.delete_internet_gateway(InternetGatewayId=igw['InternetGatewayId'])
            console.print(f"  - Deleted IGW: {igw['InternetGatewayId']}")
        except Exception as e:
            console.print(f"  [red]- Error IGW {igw['InternetGatewayId']}: {e}[/red]")

    # 3. Delete Route Tables (non-main)
    rts = ec2.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['RouteTables']
    for rt in rts:
        # Check if it's the main route table
        is_main = any(assoc.get('Main') for assoc in rt.get('Associations', []))
        if is_main: continue
        try:
            ec2.delete_route_table(RouteTableId=rt['RouteTableId'])
            console.print(f"  - Deleted Route Table: {rt['RouteTableId']}")
        except Exception as e:
            console.print(f"  [red]- Error RT {rt['RouteTableId']}: {e}[/red]")

    # 4. Delete Security Groups (non-default)
    sgs = ec2.describe_security_groups(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['SecurityGroups']
    for sg in sgs:
        if sg['GroupName'] == 'default': continue
        try:
            ec2.delete_security_group(GroupId=sg['GroupId'])
            console.print(f"  - Deleted SG: {sg['GroupId']}")
        except Exception as e:
            console.print(f"  [red]- Error SG {sg['GroupId']}: {e}[/red]")

@click.command()
@click.option('--region', '-r', default='us-east-1', help='AWS Region')
@click.option('--all', 'all_custom', is_flag=True, help='Delete ALL non-default VPCs')
@click.option('--vpc-id', help='Specific VPC ID to delete')
def main(region, all_custom, vpc_id):
    """Deep cleanup of non-default VPCs and their dependencies."""
    console = Console()
    ec2 = boto3.client('ec2', region_name=region)

    # 1. Discovery
    vpcs_to_delete = []
    if vpc_id:
        vpcs_to_delete = [vpc_id]
    elif all_custom:
        vpcs = ec2.describe_vpcs()['Vpcs']
        vpcs_to_delete = [v['VpcId'] for v in vpcs if not v['IsDefault']]

    if not vpcs_to_delete:
        console.print("[yellow]No VPCs found to delete.[/yellow]")
        return

    console.print(Panel(f"Found {len(vpcs_to_delete)} VPCs to clean up in {region}.", title="Cleanup Started"))

    for vid in vpcs_to_delete:
        console.print(f"\n[bold cyan]Processing VPC: {vid}[/bold cyan]")
        
        # Safety Check: Running instances
        instances = ec2.describe_instances(Filters=[
            {'Name': 'vpc-id', 'Values': [vid]},
            {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
        ])['Reservations']
        
        if instances:
            console.print(f"  [red]Skipping {vid}: Contains instances. Please terminate them first.[/red]")
            continue

        if not click.confirm(f"  Are you sure you want to PERMANENTLY WIPE VPC {vid} and all dependencies?"):
            continue

        # 2. Kill Chain
        delete_vpc_dependencies(ec2, vid)

        # 3. Final Blow
        try:
            ec2.delete_vpc(VpcId=vid)
            console.print(f"  [bold green]- VPC {vid} DELETED.[/bold green]")
        except Exception as e:
            console.print(f"  [bold red]- Error deleting VPC {vid}: {e}[/bold red]")

    console.print("\n[bold green]VPC Cleanup Finished.[/bold green]")

if __name__ == "__main__":
    main()
