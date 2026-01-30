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
@click.option('--code', '-c', required=True, help='The Quota Code (e.g. L-DB2E81BA)')
@click.option('--value', '-v', required=True, type=float, help='The new desired vCPU value')
@click.option('--region', '-r', default='us-east-1', help='AWS Region')
@click.option('--service', '-s', default='ec2', help='Service code (default: ec2)')
def main(code, value, region, service):
    """Request a service quota increase."""
    console = Console()
    sq = boto3.client('service-quotas', region_name=region)
    
    # 1. Fetch current info for confirmation
    try:
        resp = sq.get_service_quota(ServiceCode=service, QuotaCode=code)
        quota = resp['Quota']
        name = quota['QuotaName']
        current_val = quota['Value']
    except Exception as e:
        console.print(f"[red]Error fetching quota info: {e}[/red]")
        return

    # 2. Display confirmation panel
    console.print(Panel(
        f"Requesting increase for: [bold cyan]{name}[/bold cyan]\n"
        f"Quota Code: [dim]{code}[/dim]\n"
        f"Region: [yellow]{region}[/yellow]\n\n"
        f"Current Value: [bold]{current_val}[/bold]\n"
        f"Requested Value: [bold green]{value}[/bold green]",
        title="Quota Increase Request",
        border_style="cyan"
    ))

    if value <= current_val:
        console.print(f"[yellow]Warning: Requested value ({value}) is not greater than current value ({current_val}).[/yellow]")

    if not click.confirm("Do you want to submit this request to AWS?"):
        console.print("[yellow]Request cancelled.[/yellow]")
        return

    # 3. Submit
    try:
        response = sq.request_service_quota_increase(
            ServiceCode=service,
            QuotaCode=code,
            DesiredValue=value
        )
        req = response['RequestedQuota']
        
        console.print(f"\n[bold green]Success! Request submitted.[/bold green]")
        console.print(f"Request ID: [bold]{req['Id']}[/bold]")
        console.print(f"Status: [yellow]{req['Status']}[/yellow]")
        console.print("\n[dim]Note: Quota increases are reviewed by AWS and can take minutes to hours.[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error submitting request:[/bold red] {e}")

if __name__ == "__main__":
    main()
