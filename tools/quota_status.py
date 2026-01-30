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
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich import box

def get_regions():
    try:
        ec2 = boto3.client('ec2', region_name='us-east-1')
        response = ec2.describe_regions()
        return [r['RegionName'] for r in response['Regions']]
    except Exception:
        return ['us-east-1']

def get_quota_history(region):
    sq = boto3.client('service-quotas', region_name=region)
    try:
        # Fetching the last 10 requests for brevity
        response = sq.list_requested_service_quota_change_history(
            ServiceCode='ec2'
        )
        history = response.get('RequestedQuotas', [])
        
        # Add region info to each entry
        for h in history:
            h['Region'] = region
            
        return history
    except Exception:
        return []

async def scan_all_history(target_region=None):
    if target_region and target_region != 'all':
        regions = [target_region]
    else:
        regions = get_regions()
    
    executor = ThreadPoolExecutor(max_workers=20)
    loop = asyncio.get_running_loop()
    
    tasks = [loop.run_in_executor(executor, get_quota_history, r) for r in regions]
    results = await asyncio.gather(*tasks)
    
    # Flatten results
    flat_history = [item for sublist in results for item in sublist]
    
    # Sort by creation date (newest first)
    return sorted(flat_history, key=lambda x: x.get('Created', datetime.min), reverse=True)

@click.command()
@click.option('--region', '-r', default='us-east-1', help='AWS Region or "all"')
@click.option('--all', 'scan_all', is_flag=True, help='Scan all regions')
def main(region, scan_all):
    """Check status of service quota increase requests."""
    console = Console()
    target = 'all' if scan_all else region
    
    with console.status(f"[bold green]Fetching quota request history in {target}..."):
        results = asyncio.run(scan_all_history(target))
    
    if not results:
        console.print(f"[yellow]No quota request history found.[/yellow]")
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold white")
    table.add_column("Created", style="dim")
    table.add_column("Region", style="cyan")
    table.add_column("Quota Name")
    table.add_column("Desired vCPU", justify="right", style="bold green")
    table.add_column("Status", style="bold")
    table.add_column("Request ID", style="dim")

    for r in results:
        status = r['Status']
        status_style = "yellow" if status == 'CASE_OPENED' or status == 'PENDING' else "green" if status == 'APPROVED' else "red"
        
        # Some items might not have a quota name if they are very old or specific
        quota_name = r.get('QuotaName', 'Unknown Quota')
        
        table.add_row(
            r.get('Created').strftime("%Y-%m-%d %H:%M") if r.get('Created') else "N/A",
            r['Region'],
            quota_name,
            str(r.get('DesiredValue')),
            f"[{status_style}]{status}[/{status_style}]",
            r['Id']
        )

    console.print(table)

    # Links Section
    unique_regions = sorted(list(set(r['Region'] for r in results)))
    if unique_regions:
        console.print("\n[bold]Direct Console Links:[/bold]")
        for reg in unique_regions:
            link = f"https://{reg}.console.aws.amazon.com/servicequotas/home/requests"
            console.print(f"- {reg}: {link}")
        console.print("")

if __name__ == "__main__":
    main()
