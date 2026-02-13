# AwsWiz

Experimental AI-first Infrastructure Tool for rapid AI prototyping.

## Prerequisites

- Python 3.11+
- AWS CLI configured with valid credentials (`aws configure`)

## Installation

Install the [AWS CLI](https://aws.amazon.com/cli/) and [uv](https://docs.astral.sh/uv/) (if you don't have them) and then install `awiz`:

```sh
$ brew install awscli
$ curl -LsSf https://astral.sh/uv/install.sh | sh
$ uv tool install git+https://github.com/besarthoxhaj/aws_wiz
```

This installs `awiz` into an isolated environment and adds it to your `PATH` — no virtualenv activation required.

To install from a local checkout instead:

```sh
$ uv tool install --editable .
```

Verify the installation:

```sh
$ awiz --help
```

## Tool Registry

| Category       | Example                                            | Description                             |
| :------------- | :------------------------------------------------- | :-------------------------------------- |
| **Scanning**   | `awiz scan --pretty`                               | Global snapshot of resources (parallel) |
| **Quotas**     | `awiz quota-check --pretty`                        | Check GPU/Standard vCPU limits          |
| **Quotas**     | `awiz quota-request --code L-DB2E81BA --value 48`  | Request a quota increase                |
| **Quotas**     | `awiz quota-status --all`                          | Track status of pending requests        |
| **Discovery**  | `awiz list-instances --filter g5 --region all`     | Find instances matching pattern         |
| **Discovery**  | `awiz ami --framework pytorch`                     | Find latest DLAMIs & check subscription |
| **Deployment** | `awiz launch --type g4dn.xlarge`                   | Smart launch with auto-key/SG setup     |
| **Control**    | `awiz stop --id i-0abc123`                         | Stop a running instance                 |
| **Control**    | `awiz terminate --type ec2 --id i-0abc123`         | Permanently delete a resource           |
| **Cleanup**    | `awiz cleanup-sg`                                  | Delete unused security groups           |
| **Cleanup**    | `awiz cleanup-vpc --all`                           | Wipe non-default VPCs and dependencies  |
| **Billing**    | `awiz fellow-costs`                                | Detailed cost statement for all fellows |
| **Billing**    | `awiz costs --months 3`                            | Check AWS spending over the last months |
