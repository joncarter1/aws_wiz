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
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich import box


QUOTA_BUCKETS = [
    {
        "name": "Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances",
        "code": "L-1216C47A",
        "includes": "Standard (A, C, D, M, T...) (On-Demand)",
    },
    {
        "name": "All Standard (A, C, D, H, I, M, R, T, Z) Spot Instance Requests",
        "code": "L-34B43A08",
        "includes": "Standard (A, C, D, M, T...) (Spot)",
    },
    {
        "name": "Running On-Demand G and VT instances",
        "code": "L-DB2E81BA",
        "includes": "G* + VT1 (On-Demand)",
    },
    {
        "name": "Running On-Demand P instances",
        "code": "L-417A185B",
        "includes": "P* (On-Demand)",
    },
    {
        "name": "All G and VT Spot Instance Requests",
        "code": "L-3819A6DF",
        "includes": "G* + VT1 (Spot)",
    },
    {
        "name": "All P4, P3 and P2 Spot Instance Requests",
        "code": "L-7212CCBC",
        "includes": "P2/P3/P4* (Spot)",
    },
    {
        "name": "All P5 Spot Instance Requests",
        "code": "L-C4BD4855",
        "includes": "P5* (Spot)",
    },
]

def get_regions():
    try:
        ec2 = boto3.client('ec2', region_name='us-east-1')
        response = ec2.describe_regions()
        return [r['RegionName'] for r in response['Regions']]
    except Exception:
        return ['us-east-1']

def scan_region_buckets(region):
    sq_client = boto3.client('service-quotas', region_name=region)
    results = {}

    for item in QUOTA_BUCKETS:
        try:
            resp = sq_client.get_service_quota(ServiceCode="ec2", QuotaCode=item["code"])
            results[item["code"]] = resp["Quota"].get("Value", 0.0)
        except Exception:
            results[item["code"]] = 0.0
            
    # Also search for Capacity Blocks
    capacity_matches = []
    try:
        paginator = sq_client.get_paginator("list_service_quotas")
        for page in paginator.paginate(ServiceCode="ec2"):
            for q in page.get("Quotas", []):
                name = q.get("QuotaName", "")
                if "Capacity Block" in name:
                    capacity_matches.append({
                        "name": name,
                        "code": q.get("QuotaCode"),
                        "value": q.get("Value")
                    })
    except Exception:
        pass

    return {
        "region": region,
        "buckets": results,
        "capacity": capacity_matches
    }

async def run_scan(target_region=None):
    if target_region and target_region != 'all':
        regions = [target_region]
    else:
        regions = get_regions()
    
    executor = ThreadPoolExecutor(max_workers=20)
    loop = asyncio.get_running_loop()
    
    tasks = [loop.run_in_executor(executor, scan_region_buckets, r) for r in regions]
    return await asyncio.gather(*tasks)

def print_pretty_table(results):
    console = Console()
    
    # We want one row per Bucket, showing aggregate info
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold white")
    table.add_column("Bucket Name", style="cyan", no_wrap=True)
    table.add_column("QuotaCode", style="dim")
    table.add_column("Description", style="italic")
    table.add_column("vCPUs", justify="right", style="bold green")
    table.add_column("Regions (Value > 0)", style="yellow")

    for bucket in QUOTA_BUCKETS:
        code = bucket["code"]
        
        # Find max value and which regions have it > 0
        max_val = 0.0
        active_regions = []
        for res in results:
            val = res["buckets"].get(code, 0.0)
            if val > 0:
                active_regions.append(res["region"])
                max_val = max(max_val, val)

        # Format regions: show first 4 then ... (+N)
        def sort_key(r):
            if r.startswith('us-'): return (0, r)
            if r.startswith('eu-'): return (1, r)
            return (2, r)
        
        sorted_regions = sorted(active_regions, key=sort_key)
        if len(sorted_regions) > 2:
            reg_str = f"{', '.join(sorted_regions[:2])}  +{len(sorted_regions)-2}"
        else:
            reg_str = ", ".join(sorted_regions)

        # Styling for 0.0 values
        style = ""
        val_display = str(max_val)
        bucket_name = bucket["name"]
        
        if max_val == 0.0:
            style = "dim"
            val_display = "[grey70]0.0[/grey70]"
            bucket_name = f"[grey70]{bucket_name}[/grey70]"
        else:
            val_display = f"[bold green]{max_val}[/bold green]"

        table.add_row(
            bucket_name,
            code,
            bucket["includes"],
            val_display,
            reg_str or "[dim]None[/dim]",
            style=style
        )

    console.print(table)
    
    # Capacity Blocks Section
    console.print("\n[bold cyan]Capacity Blocks & Specialized Quotas[/bold cyan]")
    cap_table = Table(box=box.SIMPLE, show_header=True)
    cap_table.add_column("Region", style="dim")
    cap_table.add_column("Quota Name")
    cap_table.add_column("Value", justify="right")

    found_any = False
    for res in results:
        for cap in res["capacity"]:
            if cap["value"] > 0:
                cap_table.add_row(res["region"], cap["name"], str(cap["value"]))
                found_any = True
    
    if found_any:
        console.print(cap_table)
    else:
        console.print("[dim]No active Capacity Block quotas found in scanned regions.[/dim]")

@click.command()
@click.option('--region', '-r', default='all', help='AWS Region or "all"')
@click.option('--pretty', '-p', is_flag=True, help='Pretty print table')
def main(region, pretty):
    results = asyncio.run(run_scan(region))
    
    if pretty:
        print_pretty_table(results)
    else:
        print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()