# AwsWiz

Experimental AI-first Infrastructure Tool for rapid AI prototyping.

## Installation

```sh
$ brew install awscli
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Tool Registry

| Category       | Example                                                      | Description                             |
| :------------- | :----------------------------------------------------------- | :-------------------------------------- |
| **Scanning**   | `uv run tools/scan.py --pretty`                              | Global snapshot of resources (parallel) |
| **Quotas**     | `uv run tools/quota_check.py --pretty`                       | Check GPU/Standard vCPU limits          |
| **Quotas**     | `uv run tools/quota_request.py --code L-DB2E81BA --value 48` | Request a quota increase                |
| **Quotas**     | `uv run tools/quota_status.py --all`                         | Track status of pending requests        |
| **Discovery**  | `uv run tools/list_instances.py --filter g5 --region all`    | Find instances matching pattern         |
| **Discovery**  | `uv run tools/ami.py --framework pytorch`                    | Find latest DLAMIs & check subscription |
| **Deployment** | `uv run tools/launch.py --type g4dn.xlarge`                  | Smart launch with auto-key/SG setup     |
| **Control**    | `uv run tools/stop.py --id i-0abc123`                        | Stop a running instance                 |
| **Control**    | `uv run tools/terminate.py --type ec2 --id i-0abc123`        | Permanently delete a resource           |
| **Cleanup**    | `uv run tools/cleanup_sg.py`                                 | Delete unused security groups           |
| **Cleanup**    | `uv run tools/cleanup_vpc.py --all`                          | Wipe non-default VPCs and dependencies  |
| **Billing**    | `uv run tools/fellow_costs.py`                               | Detailed cost statement for all fellows |
| **Billing**    | `uv run tools/costs.py --months 3`                           | Check AWS spending over the last months |
