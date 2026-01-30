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
from rich.table import Table
from rich import box
from botocore.exceptions import ClientError

def get_latest_images(region, search_pattern):
    ec2 = boto3.client('ec2', region_name=region)
    filters = [
        {'Name': 'name', 'Values': [search_pattern]},
        {'Name': 'state', 'Values': ['available']},
        {'Name': 'owner-alias', 'Values': ['amazon']},
        {'Name': 'architecture', 'Values': ['x86_64']}
    ]
    try:
        response = ec2.describe_images(Filters=filters)
        images = response.get('Images', [])
        images.sort(key=lambda x: x['CreationDate'], reverse=True)
        return images[:3]
    except Exception:
        return []

def check_ami_subscription(region, ami_id):
    """
    Checks if the account is subscribed to the AMI by attempting a DryRun launch.
    Returns: (is_subscribed, message/link)
    """
    ec2 = boto3.client('ec2', region_name=region)
    try:
        ec2.run_instances(
            ImageId=ami_id,
            InstanceType='t3.nano',
            MaxCount=1,
            MinCount=1,
            DryRun=True
        )
        return True, "Subscription Active"
    except ClientError as e:
        code = e.response['Error']['Code']
        msg = e.response['Error']['Message']
        
        if code == 'DryRunOperation':
            return True, "Subscription Active"
        elif code == 'OptInRequired':
            # Extract URL from message if possible, or construct generic
            # Message usually looks like: "In order to use this AWS Marketplace product you need to accept terms and subscribe..."
            # We can construct a link if we had the product ID, but usually the error message contains a link.
            return False, "Opt-In Required"
        else:
            return False, f"Error: {code}"

@click.command()
@click.option('--region', '-r', default='us-east-1', help='AWS Region')
@click.option('--framework', '-f', default='pytorch', type=click.Choice(['pytorch', 'tensorflow', 'base']), help='DL Framework')
def main(region, framework):
    """Find and validate AWS Deep Learning AMIs."""
    console = Console()
    
    if framework == 'pytorch':
        pattern = "Deep Learning OSS Nvidia Driver AMI GPU PyTorch 2.* (Ubuntu 22.04)*"
    elif framework == 'tensorflow':
        pattern = "Deep Learning OSS Nvidia Driver AMI GPU TensorFlow 2.* (Ubuntu 22.04)*"
    else:
        pattern = "Deep Learning Base OSS Nvidia Driver AMI (Ubuntu 22.04)*"

    console.print(f"[bold cyan]Searching for {framework} AMIs in {region}...[/bold cyan]")
    images = get_latest_images(region, pattern)

    if not images:
        console.print(f"[yellow]No AMIs found matching pattern: {pattern}[/yellow]")
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold white")
    table.add_column("AMI ID", style="green")
    table.add_column("Name", style="cyan")
    table.add_column("Date", style="dim")
    table.add_column("Status", style="bold")

    for img in images:
        is_sub, status = check_ami_subscription(region, img['ImageId'])
        
        status_style = "green" if is_sub else "red"
        table.add_row(
            img['ImageId'],
            img['Name'],
            img['CreationDate'].split('T')[0],
            f"[{status_style}]{status}[/{status_style}]"
        )

    console.print(table)
    
    # If any need opt-in, provide general advice
    if any(not check_ami_subscription(region, i['ImageId'])[0] for i in images):
        console.print("\n[bold red]Action Required:[/bold red] Some AMIs require manual Opt-In.")
        console.print("Please visit the [link=https://aws.amazon.com/marketplace]AWS Marketplace[/link] and search for 'Deep Learning AMI' to subscribe.")

if __name__ == "__main__":
    main()
