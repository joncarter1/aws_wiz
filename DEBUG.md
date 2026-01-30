# Debug Report: EC2 Instance SSH Connection Failure

## Problem Statement
Unable to SSH to EC2 instance `i-09ecac2ff6aad4b78` at IP `44.193.39.62` - connection timing out.

## Root Cause
The VPC's Internet Gateway (IGW) was missing, causing all outbound internet traffic to be blackholed.

## Network Architecture (Before Fix)
```
Internet ──X──> [Missing IGW] ──X──> VPC (172.31.0.0/16)
                                           │
                                           ├── Subnet (172.31.0.0/20)
                                           │      │
                                           │      └── EC2 Instance
                                           │          ├── Public IP: 44.193.39.62
                                           │          └── Private IP: 172.31.2.65
                                           │
                                           └── Route Table (rtb-0491c40cb340ad52c)
                                                  ├── 172.31.0.0/16 -> local ✓
                                                  └── 0.0.0.0/0 -> igw-0d615e4d90c557b4b (BLACKHOLE!)
```

## Debugging Process

### Step 1: Basic Connectivity Check
**Command:** `ssh -o ConnectTimeout=5 ... ubuntu@44.193.39.62`  
**Result:** Operation timed out  
**Thinking:** Timeout suggests network routing issue, not authentication problem

### Step 2: Verify Instance State
**Command:** `aws ec2 describe-instances ...`  
**Findings:**
- Instance: Running ✓
- Public IP: Assigned ✓  
- Security Group: sg-0cc926469d0c69714 ✓

### Step 3: Check Security Group Rules
**Command:** `aws ec2 describe-security-groups ...`  
**Findings:** Port 22 open to 0.0.0.0/0 ✓  
**Thinking:** Security group is correct, problem must be network routing

### Step 4: Investigate Subnet Routing
**Command:** `aws ec2 describe-route-tables ...`  
**Key Finding:**
```json
{
  "DestinationCidrBlock": "0.0.0.0/0",
  "GatewayId": "igw-0d615e4d90c557b4b",
  "State": "blackhole"  // <-- PROBLEM!
}
```
**Thinking:** "blackhole" state means packets are being dropped - IGW might be missing

### Step 5: Verify Internet Gateway
**Command:** `aws ec2 describe-internet-gateways ... igw-0d615e4d90c557b4b`  
**Result:** InvalidInternetGatewayID.NotFound  
**Confirmation:** IGW doesn't exist!

## Why This Happened

The default VPC had a route table pointing to a non-existent Internet Gateway. Possible causes:
1. **Manual Deletion**: Someone deleted the IGW without updating routes
2. **Incomplete Cleanup**: A previous cleanup operation removed the IGW but left the route
3. **AWS Account Issue**: Unusual state for a default VPC (they typically come with working IGWs)

## The Fix

### Step 1: Create New Internet Gateway
```bash
aws ec2 create-internet-gateway --region us-east-1
# Result: igw-0c111979d70665779
```

### Step 2: Attach IGW to VPC
```bash
aws ec2 attach-internet-gateway \
  --vpc-id vpc-03de6683d77c0d083 \
  --internet-gateway-id igw-0c111979d70665779
```

### Step 3: Fix Route Table
```bash
# Remove broken route
aws ec2 delete-route --route-table-id rtb-0491c40cb340ad52c \
  --destination-cidr-block 0.0.0.0/0

# Add working route
aws ec2 create-route --route-table-id rtb-0491c40cb340ad52c \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id igw-0c111979d70665779
```

## Network Architecture (After Fix)
```
Internet <────> [IGW: igw-0c111979d70665779] <────> VPC (172.31.0.0/16)
                       │                                    │
                       │                                    ├── Subnet (172.31.0.0/20)
                       │                                    │      │
                       │                                    │      └── EC2 Instance
                       │                                    │          ├── Public IP: 44.193.39.62
                       │                                    │          └── Private IP: 172.31.2.65
                       │                                    │
                       │                                    └── Route Table
                       │                                           ├── 172.31.0.0/16 -> local ✓
                       └───────────────────────────────────────────┤
                                                                   └── 0.0.0.0/0 -> igw-0c111979d70665779 ✓
```

## Key Lessons

1. **Route Table State Matters**: A "blackhole" state in route tables indicates missing resources
2. **Default VPCs Can Break**: Even AWS default VPCs can have missing components
3. **Systematic Debugging**: Work from instance → security → routing → gateways
4. **Internet Connectivity Requirements**:
   - Instance needs public IP ✓
   - Security group must allow traffic ✓
   - Subnet must have route to IGW ✓
   - IGW must exist and be attached ✓

## Quick Troubleshooting Checklist for Future

```
┌─────────────────────────────────────┐
│   SSH Connection Troubleshooting    │
├─────────────────────────────────────┤
│ [ ] Instance running?                │
│ [ ] Public IP assigned?              │
│ [ ] Security group allows port 22?   │
│ [ ] Key file permissions = 400?      │
│ [ ] Route table has 0.0.0.0/0 route? │
│ [ ] Route state = "active"?          │
│ [ ] IGW exists and attached?         │
│ [ ] Subnet has public IP mapping?    │
└─────────────────────────────────────┘
```

## Prevention

To prevent this in the future, the `launch.py` tool should:
1. Verify IGW exists before launching instances
2. Check route table states
3. Create IGW if missing in default VPC
4. Validate full network path before reporting success