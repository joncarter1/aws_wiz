# /// script
# dependencies = [
#   "boto3",
#   "rich",
# ]
# ///

import boto3
import json
import time
from botocore.exceptions import ClientError
from rich.console import Console

console = Console()

BUCKET_NAME = "s3-throughput-test-1769529024"
ROLE_NAME = "S3ThroughputRole"
PROFILE_NAME = "S3ThroughputProfile"
POLICY_NAME = "S3ThroughputAccess"

def setup_iam():
    iam = boto3.client('iam')

    # 1. Create Role
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Role for S3 throughput testing"
        )
        console.print(f"[green]Created role: {ROLE_NAME}[/green]")
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            console.print(f"[yellow]Role {ROLE_NAME} already exists.[/yellow]")
        else:
            raise

    # 2. Put Role Policy (Inline)
    s3_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:*",
                    "ec2:Describe*"
                ],
                "Resource": "*"
            }
        ]
    }
    
    try:
        iam.put_role_policy(
            RoleName=ROLE_NAME,
            PolicyName=POLICY_NAME,
            PolicyDocument=json.dumps(s3_policy)
        )
        console.print(f"[green]Attached inline policy {POLICY_NAME} to {ROLE_NAME}[/green]")
    except Exception as e:
        console.print(f"[red]Error attaching policy: {e}[/red]")

    # 3. Create Instance Profile
    try:
        iam.create_instance_profile(InstanceProfileName=PROFILE_NAME)
        console.print(f"[green]Created instance profile: {PROFILE_NAME}[/green]")
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            console.print(f"[yellow]Instance profile {PROFILE_NAME} already exists.[/yellow]")
        else:
            raise

    # 4. Add Role to Instance Profile
    try:
        iam.add_role_to_instance_profile(
            InstanceProfileName=PROFILE_NAME,
            RoleName=ROLE_NAME
        )
        console.print(f"[green]Added role {ROLE_NAME} to profile {PROFILE_NAME}[/green]")
    except ClientError as e:
        if e.response['Error']['Code'] == 'LimitExceeded':
             console.print(f"[yellow]Role already added to profile (LimitExceeded usually means this).[/yellow]")
        elif 'already exists' in str(e): # Sometimes the error message varies
             console.print(f"[yellow]Role {ROLE_NAME} is already in profile {PROFILE_NAME}[/yellow]")
        else:
             # Often throws if already attached, let's just log and continue
             console.print(f"[dim]Note: {e}[/dim]")

    # Wait for propagation
    console.print("[dim]Waiting 10s for IAM propagation...[/dim]")
    time.sleep(10)
    console.print(f"[bold green]IAM Setup Complete. Profile Name: {PROFILE_NAME}[/bold green]")

if __name__ == "__main__":
    setup_iam()
