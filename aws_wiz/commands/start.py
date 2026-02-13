import boto3
import click
import os
from rich.console import Console
from rich.panel import Panel

from aws_wiz.state import KEYS_DIR

@click.command()
@click.option('--id', '-i', required=True, help='Instance ID')
@click.option('--region', '-r', default='us-east-1', help='AWS Region')
def start(id, region):
    """Start an EC2 instance."""
    console = Console()
    ec2 = boto3.client('ec2', region_name=region)

    # 1. Verify
    try:
        resp = ec2.describe_instances(InstanceIds=[id])
        instance = resp['Reservations'][0]['Instances'][0]
        state = instance['State']['Name']
        name = next((t['Value'] for t in instance.get('Tags', []) if t['Key'] == 'Name'), "N/A")

        console.print(Panel(
            f"ID: [cyan]{id}[/cyan]\nName: [yellow]{name}[/yellow]\nState: [bold]{state}[/bold]",
            title="Instance Found"
        ))

        if state == 'running':
            console.print("[yellow]Instance is already running.[/yellow]")
            return
        if state == 'terminated':
            console.print("[red]Instance is terminated and cannot be started.[/red]")
            return

    except Exception as e:
        console.print(f"[red]Error finding instance {id}: {e}[/red]")
        return

    # 2. Confirm
    if not click.confirm(f"Are you sure you want to START instance {id}?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    # 3. Start
    try:
        console.print("Starting instance...")
        ec2.start_instances(InstanceIds=[id])
        console.print(f"[bold green]Start signal sent to {id}.[/bold green]")

        # Wait
        with console.status("Waiting for instance to start..."):
            waiter = ec2.get_waiter('instance_running')
            waiter.wait(InstanceIds=[id])

            # Fetch public IP
            resp = ec2.describe_instances(InstanceIds=[id])
            public_ip = resp['Reservations'][0]['Instances'][0].get('PublicIpAddress')

        console.print("[bold green]Instance is now RUNNING.[/bold green]")
        if public_ip:
            console.print(f"Public IP: [bold cyan]{public_ip}[/bold cyan]")

            # Try to find the local key
            try:
                if not KEYS_DIR.is_dir():
                    raise FileNotFoundError
                local_keys = [f for f in os.listdir(KEYS_DIR) if f.endswith(".pem")]
                key_name = instance.get('KeyName')
                key_path = None
                if key_name:
                    for lk in local_keys:
                        if lk.startswith(key_name):
                            key_path = str(KEYS_DIR / lk)
                            break

                if key_path:
                    console.print(f"Connect: [bold green]ssh -i {key_path} ubuntu@{public_ip}[/bold green]")
                else:
                    console.print(f"Connect: [bold green]ssh ubuntu@{public_ip}[/bold green]")
            except Exception:
                console.print(f"Connect: [bold green]ssh ubuntu@{public_ip}[/bold green]")

    except Exception as e:
        console.print(f"[red]Error starting instance: {e}[/red]")
