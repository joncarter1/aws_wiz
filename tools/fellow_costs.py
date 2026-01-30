# /// script
# dependencies = [
#   "boto3",
#   "click",
#   "rich",
#   "tomli",
# ]
# ///

import boto3
import click
import asyncio
import os
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich import box

# Use tomli for compatibility with Python < 3.11
try:
    import tomllib
except ImportError:
    import tomli as tomllib

FELLOWS_FILE = ".state/fellows.toml"

def get_detailed_fellow_statement(name, creds):
    """Fetches comprehensive cost statement logic matching tools/costs.py."""
    try:
        session = boto3.Session(
            aws_access_key_id=creds['aws_access_key_id'],
            aws_secret_access_key=creds['aws_secret_access_key'],
            region_name='us-east-1'
        )
        ce = session.client('ce')

        # 3 Month Range
        end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=3*30)).replace(day=1).strftime('%Y-%m-%d')

        response = ce.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'RECORD_TYPE'},
                {'Type': 'DIMENSION', 'Key': 'SERVICE'}
            ]
        )

        statement_data = {}
        months_list = []
        all_usage_services = set()
        all_credit_types = set()

        for period in response['ResultsByTime']:
            m_label = period['TimePeriod']['Start']
            months_list.append(m_label)
            
            statement_data[m_label] = {
                "Usage": {},
                "Credits": {},
                "Tax": 0.0
            }
            
            for group in period['Groups']:
                rtype = group['Keys'][0]
                service = group['Keys'][1]
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                
                if amount == 0:
                    continue

                if "Usage" in rtype:
                    current = statement_data[m_label]["Usage"].get(service, 0.0)
                    statement_data[m_label]["Usage"][service] = current + amount
                    if amount > 0.01:
                        all_usage_services.add(service)
                elif "Credit" in rtype or "Discount" in rtype:
                    current = statement_data[m_label]["Credits"].get(service, 0.0)
                    statement_data[m_label]["Credits"][service] = current + amount
                    if abs(amount) > 0.01:
                        all_credit_types.add(service)
                elif "Tax" in rtype:
                    statement_data[m_label]["Tax"] += amount

        return {
            "name": name,
            "status": "OK",
            "months": months_list,
            "statement": statement_data,
            "usage_services": sorted(list(all_usage_services)),
            "credit_types": sorted(list(all_credit_types))
        }

    except Exception as e:
        return {
            "name": name, 
            "status": "Error", 
            "error": str(e)
        }

async def scan_all_fellows(fellows_dict):
    executor = ThreadPoolExecutor(max_workers=5)
    loop = asyncio.get_running_loop()
    
    tasks = [
        loop.run_in_executor(executor, get_detailed_fellow_statement, name, creds)
        for name, creds in fellows_dict.items()
    ]
    return await asyncio.gather(*tasks)

def print_statement_table(console, title, months, statement_data, usage_services, credit_types, style="cyan"):
    """Generic function to print a cost statement table."""
    filtered_usage = []
    for svc in usage_services:
        if any(statement_data[m]['Usage'].get(svc, 0) > 0.01 for m in months):
            filtered_usage.append(svc)
            
    filtered_credits = []
    for cr in credit_types:
        if any(abs(statement_data[m]['Credits'].get(cr, 0)) > 0.01 for m in months):
            filtered_credits.append(cr)

    table = Table(
        title=f"\n{title}", 
        title_style=f"bold {style}", 
        box=box.ROUNDED, 
        show_footer=True
    )
    table.add_column("Description", footer="[bold]NET BILLABLE TOTAL[/bold]", width=45)
    for m in months:
        table.add_column(m, justify="right")

    table.add_row("", *["" for _ in months])
    table.add_row("[bold underline]Gross Operating Costs[/bold underline]")
    for svc in filtered_usage:
        row = [f"  {svc}"]
        for m in months:
            val = statement_data[m]["Usage"].get(svc, 0)
            row.append(f"${val:.2f}" if val > 0.01 else "[dim]-""[/dim]")
        table.add_row(*row)

    tax_row = ["  Taxes"]
    for m in months:
        tax = statement_data[m]['Tax']
        tax_row.append(f"${tax:.2f}" if tax > 0.01 else "[dim]-""[/dim]")
    table.add_row(*tax_row)

    table.add_section()
    subtotal_row = [f"[bold {style}]TOTAL GROSS COST[/bold {style}]"]
    for m in months:
        sub = sum(statement_data[m]["Usage"].values()) + statement_data[m]["Tax"]
        subtotal_row.append(f"[bold {style}]${sub:.2f}[/bold {style}]")
    table.add_row(*subtotal_row)
    table.add_row("") 

    if filtered_credits:
        table.add_row("[bold red underline]Less: Credits & Discounts[/bold red underline]")
        for cr in filtered_credits:
            row = [f"  {cr}"]
            for m in months:
                val = statement_data[m]["Credits"].get(cr, 0)
                row.append(f"[green](${abs(val):.2f})[/green]" if abs(val) > 0.01 else "[dim]-""[/dim]")
            table.add_row(*row)

    table.add_row("")
    net_cost_row = ["[bold yellow]NET COST (AFTER CREDITS)[/bold yellow]"]
    for i, m in enumerate(months):
        u_total = sum(statement_data[m]["Usage"].values())
        c_total = sum(statement_data[m]["Credits"].values())
        tax = statement_data[m]["Tax"]
        net = u_total + c_total + tax
        formatted_net = f"[bold yellow]${max(0, net):.2f}[/bold yellow]"
        net_cost_row.append(formatted_net)
        table.columns[i+1].footer = formatted_net

    table.add_row(*net_cost_row)
    table.add_row("", *["" for _ in months])
    table.add_section()
    console.print(table)

@click.command()
def main():
    """Detailed financial audit for all fellows."""
    console = Console()
    if not os.path.exists(FELLOWS_FILE):
        console.print(f"[red]Error: {FELLOWS_FILE} not found.[/red]")
        return

    try:
        with open(FELLOWS_FILE, "rb") as f:
            fellows = tomllib.load(f)
    except Exception as e:
        console.print(f"[red]Error parsing {FELLOWS_FILE}: {e}[/red]")
        return

    if 'template' in fellows: del fellows['template']
    if not fellows: return

    with console.status(f"[bold green]Auditing {len(fellows)} fellows..."):
        results = asyncio.run(scan_all_fellows(fellows))

    cohort_months = []
    cohort_statement = {}
    cohort_usage = set()
    cohort_credits = set()

    for res in results:
        if res['status'] != "OK":
            console.print(f"[red]Skipping {res['name']}: {res['status']}[/red]")
            continue
        
        print_statement_table(
            console, 
            f"AWS MONTHLY COST STATEMENT: {res['name'].upper()}",
            res['months'],
            res['statement'],
            res['usage_services'],
            res['credit_types']
        )

        if not cohort_months: 
            cohort_months = res['months']
            for m in cohort_months:
                cohort_statement[m] = {"Usage": {}, "Credits": {}, "Tax": 0.0}

        for m in res['months']:
            cohort_statement[m]["Tax"] += res['statement'][m]["Tax"]
            for svc, cost in res['statement'][m]["Usage"].items():
                cohort_statement[m]["Usage"][svc] = cohort_statement[m]["Usage"].get(svc, 0.0) + cost
                cohort_usage.add(svc)
            for svc, cost in res['statement'][m]["Credits"].items():
                cohort_statement[m]["Credits"][svc] = cohort_statement[m]["Credits"].get(svc, 0.0) + cost
                cohort_credits.add(svc)

    if cohort_months:
        print_statement_table(
            console,
            "FELLOWS CONSOLIDATED STATEMENT (ALL FELLOWS)",
            cohort_months,
            cohort_statement,
            sorted(list(cohort_usage)),
            sorted(list(cohort_credits)),
            style="green"
        )

if __name__ == "__main__":
    main()
