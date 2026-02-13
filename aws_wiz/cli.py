import click

from aws_wiz.commands.scan import scan
from aws_wiz.commands.launch import launch
from aws_wiz.commands.quota_check import quota_check
from aws_wiz.commands.quota_request import quota_request
from aws_wiz.commands.quota_status import quota_status
from aws_wiz.commands.list_instances import list_instances
from aws_wiz.commands.ami import ami
from aws_wiz.commands.start import start
from aws_wiz.commands.stop import stop
from aws_wiz.commands.terminate import terminate
from aws_wiz.commands.costs import costs
from aws_wiz.commands.fellow_costs import fellow_costs
from aws_wiz.commands.create_auditor import create_auditor
from aws_wiz.commands.cleanup_sg import cleanup_sg
from aws_wiz.commands.cleanup_vpc import cleanup_vpc
from aws_wiz.commands.nuke import nuke
from aws_wiz.commands.create_cluster import create_cluster
from aws_wiz.commands.setup_iam import setup_iam


@click.group()
@click.version_option(version="0.1.0", prog_name="awiz")
def cli():
    """AWS infrastructure CLI for rapid prototyping."""

cli.add_command(scan)
cli.add_command(launch)
cli.add_command(quota_check, "quota-check")
cli.add_command(quota_request, "quota-request")
cli.add_command(quota_status, "quota-status")
cli.add_command(list_instances, "list-instances")
cli.add_command(ami)
cli.add_command(start)
cli.add_command(stop)
cli.add_command(terminate)
cli.add_command(costs)
cli.add_command(fellow_costs, "fellow-costs")
cli.add_command(create_auditor, "create-auditor")
cli.add_command(cleanup_sg, "cleanup-sg")
cli.add_command(cleanup_vpc, "cleanup-vpc")
cli.add_command(nuke)
cli.add_command(create_cluster, "create-cluster")
cli.add_command(setup_iam, "setup-iam")
