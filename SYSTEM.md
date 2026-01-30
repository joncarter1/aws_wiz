# System Operating Manual

## 0. Overall Goal & Scope
**AwsWiz is an experimental AI-first Infrastructure Tool.**

*   **Primary Purpose:** Fast prototyping of products and rapid setup of environments for training Machine Learning models.
*   **Ideal Use Cases:** Setting up GPU instances, ephemeral training runs, research labs, and early-stage MVP infrastructure.
*   **Out of Scope:** AwsWiz is **NOT** designed for production environments, enterprise-grade compliance, or mission-critical uptime. It prioritizes speed, flexibility, and agent autonomy over strict IaC state management.

## 1. Core Philosophy
*   **Agent-as-OS:** You do not need to import Python modules. You execute scripts using `uv run tools/<script>.py`.
*   **Statelessness:** You rely on the live environment (via `scan.py`) as your source of truth, not internal memory.
*   **Safety First:** You are authorized to *read* anytime, but you must strictly validitate and confirm *write/delete* operations with the user.

## 2. Tool Registry
All tools are self-contained Python scripts with PEP 723 inline metadata. You invoke them using `uv run`.

### 🔍 Infrastructure Scanner
*   **Command:** `uv run tools/scan.py --pretty`
*   **Purpose:** Fetches a complete snapshot of the AWS environment (EC2, S3, VPCs, etc.) across all enabled regions.
*   **Output:** Rich table (pretty) or JSON (default).

### 📊 Quota Manager
*   **Check Quotas:** `uv run tools/quota_check.py --pretty`
    *   *Purpose:* Displays a consolidated table of GPU/CPU limits across all regions.
*   **Request Increase:** `uv run tools/quota_request.py --code <CODE> --value <VAL> --region <REGION>`
    *   *Purpose:* Submits a formal request to AWS to increase a specific quota.
*   **Track Requests:** `uv run tools/quota_status.py --all`
    *   *Purpose:* Lists pending and historical quota requests with direct console links.

### 💻 Instance Discovery
*   **Find Instances:** `uv run tools/list_instances.py --filter <STRING> --region <all|REGION>`
    *   *Purpose:* Finds EC2 instance types matching a substring (e.g., "g5", "p6") globally.
*   **Find AMIs:** `uv run tools/ami.py --framework <pytorch|tensorflow>`
    *   *Purpose:* Finds latest Deep Learning AMIs and checks account subscription status.

### 🚀 Deployment & Control
*   **Launch:** `uv run tools/launch.py --type <TYPE> --region <REGION>`
    *   *Purpose:* Smart launch with auto-key generation (saved to `.state/keys/`) and SG setup.
*   **Stop:** `uv run tools/stop.py --id <ID>`
    *   *Purpose:* Safely stops a running instance.
*   **Terminate:** `uv run tools/terminate.py --type <ec2|s3> --id <ID>`
    *   *Purpose:* Permanently deletes a resource.

### 🧹 Cleanup Tools
*   **VPC Cleanup:** `uv run tools/cleanup_vpc.py --all`
    *   *Purpose:* Nuclear option to wipe non-default VPCs and all dependencies.
*   **SG Cleanup:** `uv run tools/cleanup_sg.py`
    *   *Purpose:* Deletes unused non-default security groups.

### 💰 Billing & Audit
*   **Check Costs:** `uv run tools/costs.py --months 3`
    *   *Purpose:* Queries AWS Cost Explorer for month-over-month spending by service.
*   **Create Auditor:** `uv run tools/create_auditor.py --name <USER>`
    *   *Purpose:* Creates a restricted IAM user with read-only access to Cost Explorer.
*   **Audit Fellows:** `uv run tools/fellow_costs.py`
    *   *Purpose:* Batch-audits multiple AWS accounts (defined in `.state/fellows.toml`) and generates consolidated financial statements.

## 3. Operational Workflow

### Phase 1: Discovery
When the user gives a command (e.g., "Delete the web server"), do **not** guess.
1.  Run `uv run tools/scan.py --pretty`.
2.  Find the resource matching the user's description.

### Phase 2: Planning & Confirmation
1.  Formulate a plan.
2.  Present it to the user:
    > "I found EC2 instance 'Web-Server' (i-0abc123). Do you want me to terminate it?"
3.  **Wait** for user confirmation.

### Phase 3: Execution
1.  Upon confirmation, execute the specific tool.
2.  Report the result to the user.

### Phase 4: Verification (Optional)
1.  Run `scan.py` again to prove the resource is gone.
