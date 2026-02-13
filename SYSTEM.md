# System Operating Manual

## 0. Overall Goal & Scope
**AwsWiz is an experimental AI-first Infrastructure Tool.**

*   **Primary Purpose:** Fast prototyping of products and rapid setup of environments for training Machine Learning models.
*   **Ideal Use Cases:** Setting up GPU instances, ephemeral training runs, research labs, and early-stage MVP infrastructure.
*   **Out of Scope:** AwsWiz is **NOT** designed for production environments, enterprise-grade compliance, or mission-critical uptime. It prioritizes speed, flexibility, and agent autonomy over strict IaC state management.

## 1. Core Philosophy
*   **Agent-as-OS:** You do not need to import Python modules. You execute commands using the `awiz` CLI (e.g. `awiz scan --pretty`).
*   **Statelessness:** You rely on the live environment (via `awiz scan`) as your source of truth, not internal memory.
*   **Safety First:** You are authorized to *read* anytime, but you must strictly validitate and confirm *write/delete* operations with the user.

## 2. Tool Registry
### 🔍 Infrastructure Scanner
*   **Command:** `awiz scan --pretty`
*   **Purpose:** Fetches a complete snapshot of the AWS environment (EC2, S3, VPCs, etc.) across all enabled regions.
*   **Output:** Rich table (pretty) or JSON (default).

### 📊 Quota Manager
*   **Check Quotas:** `awiz quota-check --pretty`
    *   *Purpose:* Displays a consolidated table of GPU/CPU limits across all regions.
*   **Request Increase:** `awiz quota-request --code <CODE> --value <VAL> --region <REGION>`
    *   *Purpose:* Submits a formal request to AWS to increase a specific quota.
*   **Track Requests:** `awiz quota-status --all`
    *   *Purpose:* Lists pending and historical quota requests with direct console links.

### 💻 Instance Discovery
*   **Find Instances:** `awiz list-instances --filter <STRING> --region <all|REGION>`
    *   *Purpose:* Finds EC2 instance types matching a substring (e.g., "g5", "p6") globally.
*   **Find AMIs:** `awiz ami --framework <pytorch|tensorflow>`
    *   *Purpose:* Finds latest Deep Learning AMIs and checks account subscription status.

### 🚀 Deployment & Control
*   **Launch:** `awiz launch --type <TYPE> --region <REGION>`
    *   *Purpose:* Smart launch with auto-key generation (saved to `~/.aws-wiz/keys/`) and SG setup.
*   **Stop:** `awiz stop --id <ID>`
    *   *Purpose:* Safely stops a running instance.
*   **Terminate:** `awiz terminate --type <ec2|s3> --id <ID>`
    *   *Purpose:* Permanently deletes a resource.

### 🧹 Cleanup Tools
*   **VPC Cleanup:** `awiz cleanup-vpc --all`
    *   *Purpose:* Nuclear option to wipe non-default VPCs and all dependencies.
*   **SG Cleanup:** `awiz cleanup-sg`
    *   *Purpose:* Deletes unused non-default security groups.

### 💰 Billing & Audit
*   **Check Costs:** `awiz costs --months 3`
    *   *Purpose:* Queries AWS Cost Explorer for month-over-month spending by service.
*   **Create Auditor:** `awiz create-auditor --name <USER>`
    *   *Purpose:* Creates a restricted IAM user with read-only access to Cost Explorer.
*   **Audit Fellows:** `awiz fellow-costs`
    *   *Purpose:* Batch-audits multiple AWS accounts (defined in `~/.aws-wiz/fellows.toml`) and generates consolidated financial statements.

## 3. Operational Workflow

### Phase 1: Discovery
When the user gives a command (e.g., "Delete the web server"), do **not** guess.
1.  Run `awiz scan --pretty`.
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
1.  Run `awiz scan` again to prove the resource is gone.
