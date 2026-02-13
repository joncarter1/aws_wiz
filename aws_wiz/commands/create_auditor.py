import boto3
import click
import json
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from botocore.exceptions import ClientError
from datetime import datetime, timedelta

console = Console()

POLICY_DOCUMENT = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ce:Get*",
                "ce:List*",
                "ce:Describe*",
                "billing:GetBillingView"
            ],
            "Resource": "*"
        }
    ]
}

def check_ce_enabled(ce_client):
    """Checks if Cost Explorer is actually enabled in the console."""
    try:
        today = datetime.now()
        start = (today - timedelta(days=2)).strftime('%Y-%m-%d')
        end = (today - timedelta(days=1)).strftime('%Y-%m-%d')

        ce_client.get_cost_and_usage(
            TimePeriod={'Start': start, 'End': end},
            Granularity='DAILY',
            Metrics=['UnblendedCost']
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'DataUnavailableException':
            return True
        raise e

@click.command()
@click.option('--name', default='awswiz-auditor', help='Name of the IAM user to create')
def create_auditor(name):
    """Creates a restricted IAM user for cost auditing."""
    iam = boto3.client('iam')
    ce = boto3.client('ce', region_name='us-east-1')

    console.print(Panel("[bold blue]AWSWiz Auditor Setup[/bold blue]", subtitle="Step 1: Verification"))

    # 1. Verification
    try:
        check_ce_enabled(ce)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not verify Cost Explorer status ({e}).[/yellow]")
        console.print("Ensure you have enabled 'Cost Explorer' in the Billing Console, or the keys won't work.")

    # 2. Creation logic
    try:
        user_created = False
        try:
            with console.status(f"Creating IAM user '{name}'..."):
                iam.create_user(
                    UserName=name,
                    Tags=[
                        {'Key': 'CreatedBy', 'Value': 'AwsWiz'},
                        {'Key': 'Purpose', 'Value': 'CostAudit'}
                    ]
                )
                user_created = True
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                console.print(f"[yellow]User '{name}' already exists.[/yellow]")
                if not click.confirm("Do you want to generate a new key for this existing user?"):
                    console.print("Aborted.")
                    return
            else:
                raise e

        # Attach Policy (PutUserPolicy is idempotent, so safe to re-run)
        with console.status("Attaching permissions..."):
            iam.put_user_policy(
                UserName=name,
                PolicyName="CostExplorerOnly",
                PolicyDocument=json.dumps(POLICY_DOCUMENT)
            )

        # Create Keys
        with console.status("Generating access keys..."):
            response = iam.create_access_key(UserName=name)
            creds = response['AccessKey']

        # 3. Final Output
        action = "Created" if user_created else "Updated"
        console.print(f"\n[bold green]Success! User {action}.[/bold green]")

        creds_text = Text()
        creds_text.append(f"User: {name}\n", style="dim")
        creds_text.append(f"AWS_ACCESS_KEY_ID: {creds['AccessKeyId']}\n", style="bold yellow")
        creds_text.append(f"AWS_SECRET_ACCESS_KEY: {creds['SecretAccessKey']}", style="bold yellow")

        console.print(Panel(
            creds_text,
            title="Copy and send these credentials to your instructor",
            expand=False,
            border_style="green"
        ))

        console.print("[dim]Note: These keys only have permission to view cost data.[/dim]\n")

    except ClientError as e:
        console.print(f"[bold red]AWS Error:[/bold red] {e}")
