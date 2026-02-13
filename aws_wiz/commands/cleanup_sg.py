import boto3
import click
from rich.console import Console
from rich.table import Table
from rich import box

@click.command()
@click.option('--region', '-r', default='us-east-1', help='AWS Region')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
def cleanup_sg(region, force):
    """Find and delete unused Security Groups."""
    console = Console()
    ec2 = boto3.client('ec2', region_name=region)

    with console.status(f"[bold green]Scanning Security Groups in {region}..."):
        # 1. Get all SGs
        all_sgs = ec2.describe_security_groups()['SecurityGroups']

        # 2. Get used SGs (from Network Interfaces)
        # Network Interfaces represent ALL usage (Instances, Lambda, ELB, RDS, etc.)
        used_sg_ids = set()
        paginator = ec2.get_paginator('describe_network_interfaces')
        for page in paginator.paginate():
            for ni in page['NetworkInterfaces']:
                for group in ni['Groups']:
                    used_sg_ids.add(group['GroupId'])

    # 3. Filter
    unused_sgs = []
    for sg in all_sgs:
        if sg['GroupName'] == 'default': continue # Never delete default
        if sg['GroupId'] not in used_sg_ids:
            unused_sgs.append(sg)

    if not unused_sgs:
        console.print(f"[green]No unused Security Groups found in {region}.[/green]")
        return

    # 4. Report
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold white", title=f"Unused Security Groups ({len(unused_sgs)})")
    table.add_column("Group ID", style="cyan")
    table.add_column("Name", style="yellow")
    table.add_column("Description", style="dim")

    for sg in unused_sgs:
        table.add_row(sg['GroupId'], sg['GroupName'], sg['Description'][:50])

    console.print(table)

    # 5. Confirm & Delete
    if not force:
        if not click.confirm(f"\nAre you sure you want to DELETE these {len(unused_sgs)} security groups?"):
            console.print("[yellow]Cleanup cancelled.[/yellow]")
            return

    deleted_count = 0
    with console.status("Deleting..."):
        for sg in unused_sgs:
            try:
                ec2.delete_security_group(GroupId=sg['GroupId'])
                console.print(f"Deleted: [green]{sg['GroupName']}[/green] ({sg['GroupId']})")
                deleted_count += 1
            except Exception as e:
                # Common error: Referenced by another SG
                if 'DependencyViolation' in str(e):
                    console.print(f"[red]Skipped {sg['GroupName']}: Referenced by another group.[/red]")
                else:
                    console.print(f"[red]Error deleting {sg['GroupName']}: {e}[/red]")

    console.print(f"\n[bold green]Cleanup Complete. Deleted {deleted_count} groups.[/bold green]")
