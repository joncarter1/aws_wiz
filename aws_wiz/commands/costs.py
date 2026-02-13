import boto3
import click
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich import box

@click.command()
@click.option('--months', '-m', default=3, help='Number of months to look back')
def costs(months):
    """AWS Cost Statement with improved vertical spacing and Net Cost row."""
    console = Console()
    ce = boto3.client('ce', region_name='us-east-1')

    # End date must be tomorrow to include today's latest data
    end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=months*30)).replace(day=1).strftime('%Y-%m-%d')

    try:
        with console.status("[bold green]Generating Formatted Statement..."):
            response = ce.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'RECORD_TYPE'},
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'}
                ]
            )

        statement = {}
        months_list = []
        all_usage_services = set()
        all_credit_types = set()

        for period in response['ResultsByTime']:
            m_label = period['TimePeriod']['Start']
            months_list.append(m_label)
            statement[m_label] = {"Usage": {}, "Credits": {}, "Tax": 0.0}

            for group in period['Groups']:
                rtype = group['Keys'][0]
                service = group['Keys'][1]
                amount = float(group['Metrics']['UnblendedCost']['Amount'])

                if amount == 0: continue

                if "Usage" in rtype:
                    statement[m_label]["Usage"][service] = statement[m_label]["Usage"].get(service, 0) + amount
                    all_usage_services.add(service)
                elif "Credit" in rtype or "Discount" in rtype:
                    statement[m_label]["Credits"][service] = statement[m_label]["Credits"].get(service, 0) + amount
                    all_credit_types.add(service)
                elif "Tax" in rtype:
                    statement[m_label]["Tax"] += amount

        # Render Table
        table = Table(title="\nAWS MONTHLY COST STATEMENT", title_style="bold", box=box.ROUNDED, show_footer=True)
        table.add_column("Description", footer="[bold]NET BILLABLE TOTAL[/bold]", width=40)

        for m in months_list:
            table.add_column(m, justify="right")

        # --- EXTRA TOP PADDING ---
        table.add_row("", *["" for _ in months_list])

        # --- SECTION: OPERATING COSTS ---
        table.add_row("[bold underline]Gross Operating Costs[/bold underline]")
        for svc in sorted(all_usage_services):
            row = [f"  {svc}"]
            for m in months_list:
                val = statement[m]["Usage"].get(svc, 0)
                row.append(f"${val:.2f}" if val != 0 else "[dim]-[/dim]")
            table.add_row(*row)

        # --- SECTION: TAXES ---
        tax_row = ["  Taxes"]
        for m in months_list:
            tax_row.append(f"${statement[m]['Tax']:.2f}" if statement[m]['Tax'] != 0 else "[dim]-[/dim]")
        table.add_row(*tax_row)

        # --- SUB-TOTAL ---
        table.add_section()
        subtotal_row = ["[bold cyan]TOTAL GROSS COST[/bold cyan]"]
        for m in months_list:
            sub = sum(statement[m]["Usage"].values()) + statement[m]["Tax"]
            subtotal_row.append(f"[bold cyan]${sub:.2f}[/bold cyan]")
        table.add_row(*subtotal_row)
        table.add_row("")

        # --- SECTION: CREDITS ---
        table.add_row("[bold red underline]Less: Credits & Discounts[/bold red underline]")
        for cr in sorted(all_credit_types):
            row = [f"  {cr}"]
            for m in months_list:
                val = statement[m]["Credits"].get(cr, 0)
                row.append(f"[green](${abs(val):.2f})[/green]" if val != 0 else "[dim]-[/dim]")
            table.add_row(*row)

        # --- NEW SECTION: NET COST ---
        table.add_row("")
        net_cost_row = ["[bold yellow]NET COST (AFTER CREDITS)[/bold yellow]"]

        # Calculate totals for footers and the final row
        for i, m in enumerate(months_list):
            usage_total = sum(statement[m]["Usage"].values())
            credit_total = sum(statement[m]["Credits"].values())
            net = usage_total + credit_total + statement[m]["Tax"]

            # Format value for the table row
            formatted_net = f"[bold yellow]${max(0, net):.2f}[/bold yellow]"
            net_cost_row.append(formatted_net)

            # Update footer for each column
            table.columns[i+1].footer = formatted_net

        table.add_row(*net_cost_row)

        # --- EXTRA BOTTOM PADDING ---
        table.add_row("", *["" for _ in months_list])
        table.add_section()

        console.print(table)
        console.print(f"[dim]Data reflects sticker price (UnblendedCost) vs. applied credits.[/dim]\n")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
