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
from rich.console import Console
from rich.panel import Panel

@click.command()
@click.option('--type', '-t', required=True, type=click.Choice(['ec2', 's3']), help='Resource type (ec2 or s3)')
@click.option('--id', '-i', required=True, help='Resource ID (Instance ID or Bucket Name)')
@click.option('--region', '-r', default='us-east-1', help='AWS Region (default: us-east-1)')
def main(type, id, region):
    """Safely terminate an AWS resource (EC2 Instance or S3 Bucket)."""
    console = Console()
    
    # 1. Verification Phase
    if type == 'ec2':
        ec2 = boto3.client('ec2', region_name=region)
        try:
            resp = ec2.describe_instances(InstanceIds=[id])
            instance = resp['Reservations'][0]['Instances'][0]
            
            # Extract details
            state = instance['State']['Name']
            name_tag = next((t['Value'] for t in instance.get('Tags', []) if t['Key'] == 'Name'), "N/A")
            launch_time = instance['LaunchTime']
            
            details = (
                f"Type: [bold]EC2 Instance[/bold]\n"
                f"ID: [cyan]{id}[/cyan]\n"
                f"Name: [yellow]{name_tag}[/yellow]\n"
                f"Region: {region}\n"
                f"State: [bold]{state}[/bold]\n"
                f"Launched: {launch_time}"
            )
            
            if state == 'terminated':
                console.print(f"[yellow]Instance {id} is already terminated.[/yellow]")
                return

        except Exception as e:
            console.print(f"[red]Error finding EC2 instance {id} in {region}: {e}[/red]")
            return

    elif type == 's3':
        s3 = boto3.client('s3', region_name=region)
        try:
            # Check if exists
            s3.head_bucket(Bucket=id)
            
            # Check if empty
            objs = s3.list_objects_v2(Bucket=id, MaxKeys=1)
            is_empty = 'Contents' not in objs
            
            details = (
                f"Type: [bold]S3 Bucket[/bold]\n"
                f"Name: [cyan]{id}[/cyan]\n"
                f"Region: {region}\n"
                f"Status: [green]Active[/green]\n"
                f"Empty: {('[green]Yes[/green]' if is_empty else '[red]No - Contains Objects[/red]')}"
            )
            
            if not is_empty:
                console.print(Panel(details, title="Resource Found", border_style="red"))
                console.print("[bold red]WARNING: Bucket is not empty! This tool only deletes empty buckets for safety.[/bold red]")
                return

        except Exception as e:
            console.print(f"[red]Error finding S3 bucket {id}: {e}[/red]")
            return

    # 2. Confirmation Phase
    console.print(Panel(details, title="Confirm Deletion", border_style="red"))
    
    if not click.confirm(f"Are you sure you want to PERMANENTLY DELETE this {type.upper()} resource?"):
        console.print("[yellow]Deletion cancelled.[/yellow]")
        return

    # 3. Execution Phase
    try:
        if type == 'ec2':
            console.print(f"Terminating instance {id}...")
            ec2.terminate_instances(InstanceIds=[id])
            console.print(f"[bold green]Termination signal sent to {id}.[/bold green]")
            
        elif type == 's3':
            console.print(f"Deleting bucket {id}...")
            s3.delete_bucket(Bucket=id)
            console.print(f"[bold green]Bucket {id} deleted.[/bold green]")

    except Exception as e:
        console.print(f"[bold red]Error during deletion:[/bold red] {e}")

if __name__ == "__main__":
    main()
