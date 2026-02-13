import boto3
import click
import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich import box

from aws_wiz.utils import get_regions


def check_region_for_types(region, pattern):
    ec2 = boto3.client('ec2', region_name=region)
    found_types = {}

    paginator = ec2.get_paginator('describe_instance_types')
    try:
        # We assume if the pattern is in the name, we want it.
        # We'll use a client-side filter for simplicity and flexibility with wildcards
        for page in paginator.paginate():
            for it in page['InstanceTypes']:
                name = it['InstanceType']
                if pattern.lower() in name.lower():
                    # Extract GPU info
                    gpus = it.get('GpuInfo', {}).get('Gpus', [])
                    gpu_count = sum(g['Count'] for g in gpus)
                    gpu_name = gpus[0]['Name'] if gpus else "N/A"
                    gpu_mem = sum(g['MemoryInfo']['SizeInMiB'] for g in gpus) / 1024 if gpus else 0

                    found_types[name] = {
                        "Name": name,
                        "vCPUs": it['VCpuInfo']['DefaultVCpus'],
                        "Memory (GiB)": it['MemoryInfo']['SizeInMiB'] / 1024,
                        "GPUs": gpu_count,
                        "GPU Name": gpu_name,
                        "GPU Mem (GiB)": gpu_mem,
                        "Region": region
                    }
    except Exception:
        # Region might be disabled or unreachable
        pass

    return found_types

async def scan_all_regions(pattern, specific_region=None):
    if specific_region and specific_region != 'all':
        regions = [specific_region]
    else:
        regions = get_regions()
        print(f"Scanning {len(regions)} regions for '{pattern}'...", file=sys.stderr)

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=20) as executor:
        tasks = [loop.run_in_executor(executor, check_region_for_types, r, pattern) for r in regions]
        results = await asyncio.gather(*tasks)

    # Aggregate results
    # Map: InstanceType -> {Specs, Regions: set()}
    aggregated = {}

    for res in results:
        for name, data in res.items():
            if name not in aggregated:
                aggregated[name] = data.copy()
                aggregated[name]['Regions'] = set()

            aggregated[name]['Regions'].add(data['Region'])

    # Convert sets to sorted lists, prioritizing US and EU
    final_list = []
    for name, data in aggregated.items():
        regions = list(data['Regions'])

        # Sort key: 0 for US, 1 for EU, 2 for others. Then alphabetically.
        def region_sort_key(r):
            if r.startswith('us-'): return (0, r)
            if r.startswith('eu-'): return (1, r)
            return (2, r)

        data['Regions'] = sorted(regions, key=region_sort_key)
        final_list.append(data)

    return sorted(final_list, key=lambda x: x['Name'])

@click.command()
@click.option('--region', '-r', default='us-east-1', help='AWS Region (use "all" for global search)')
@click.option('--filter', '-f', required=True, help='Substring to filter instance types (e.g. "g5")')
def list_instances(region, filter):
    """List EC2 instance types matching a substring."""
    console = Console()

    # Handle "all" explicitly or pass through
    target_region = 'all' if region == 'all' or region == '*' else region

    with console.status(f"[bold green]Searching for '{filter}'..."):
        results = asyncio.run(scan_all_regions(filter, target_region))

    if not results:
        console.print(f"[yellow]No instance types found matching '{filter}'.[/yellow]")
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold white")
    table.add_column("Instance Type", style="cyan")
    table.add_column("vCPUs", justify="right")
    table.add_column("Mem (GiB)", justify="right")
    table.add_column("GPUs", justify="right", style="green")
    table.add_column("GPU Name", style="magenta")
    table.add_column("GPU Mem", justify="right", style="magenta")
    table.add_column("Available Regions", style="yellow", max_width=60) # Wrap long lists

    for r in results:
        gpu_str = str(int(r['GPUs'])) if r['GPUs'] > 0 else "-"
        gpu_mem_str = f"{r['GPU Mem (GiB)']:.0f}" if r['GPU Mem (GiB)'] > 0 else "-"
        gpu_name = r['GPU Name'] if r['GPUs'] > 0 else "-"

        # Format regions nicely: show first 4 then +count
        if len(r['Regions']) > 4:
            regions_str = f"{r['Regions'][0]}, {r['Regions'][1]}, {r['Regions'][2]}, {r['Regions'][3]}  +{len(r['Regions']) - 4}"
        else:
            regions_str = ", ".join(r['Regions'])

        table.add_row(
            r['Name'],
            str(r['vCPUs']),
            f"{r['Memory (GiB)']:.1f}",
            gpu_str,
            gpu_name,
            gpu_mem_str,
            regions_str
        )

    console.print(table)
