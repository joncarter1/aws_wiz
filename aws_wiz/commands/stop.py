import boto3
import click
from rich.console import Console
from rich.panel import Panel

@click.command()
@click.option('--id', '-i', required=True, help='Instance ID')
@click.option('--region', '-r', default='us-east-1', help='AWS Region')
def stop(id, region):
    """Stop an EC2 instance."""
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

        if state == 'stopped':
            console.print("[yellow]Instance is already stopped.[/yellow]")
            return
        if state == 'terminated':
            console.print("[red]Instance is terminated and cannot be stopped.[/red]")
            return

    except Exception as e:
        console.print(f"[red]Error finding instance {id}: {e}[/red]")
        return

    # 2. Confirm
    if not click.confirm(f"Are you sure you want to STOP instance {id}?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    # 3. Stop
    try:
        console.print("Stopping instance...")
        ec2.stop_instances(InstanceIds=[id])
        console.print(f"[bold green]Stop signal sent to {id}.[/bold green]")

        # Optional: Wait
        with console.status("Waiting for instance to stop..."):
            waiter = ec2.get_waiter('instance_stopped')
            waiter.wait(InstanceIds=[id])
        console.print("[bold green]Instance successfully STOPPED.[/bold green]")

    except Exception as e:
        console.print(f"[red]Error stopping instance: {e}[/red]")
