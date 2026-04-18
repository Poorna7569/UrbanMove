# UrbanMove - AWS Deployment Guide

This guide covers deployment of UrbanMove on AWS using the provided Terraform infrastructure-as-code.

---

## Quick Start: Local Development with Docker Compose

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Git

### Start Local Environment

```bash
# Navigate to project directory
cd urbanmove

# Start services (backend + PostgreSQL)
docker-compose up --build

# In another terminal, run tests
python test_api.py
```

**Expected Output**: All 7 tests should pass

### API Endpoints (Local)
- Health Check: `GET http://localhost:8000/api/v1/health`
- Login: `POST http://localhost:8000/api/v1/auth/login`
- Ingest: `POST http://localhost:8000/api/v1/ingest`
- Route: `GET http://localhost:8000/api/v1/route` (requires JWT)

---

## Production: AWS Deployment with Terraform

### Architecture Deployed

```
AWS VPC (10.0.0.0/16)
├── Public Subnet (10.0.1.0/24)
│   ├── Application Load Balancer (ALB)
│   │   - Routes HTTP/HTTPS to backend
│   │   - Health check: /api/v1/health (every 30s)
│   │   - TLS termination (SSL/HTTPS ready)
│   └── NAT Gateway
│       - Outbound internet access for backend
│
└── Private Subnet (10.0.2.0/24)
    ├── ECS/Fargate Backend Containers
    │   - FastAPI application (port 8000)
    │   - Auto-scaling (horizontal)
    │   - CloudWatch logging
    │
    └── RDS PostgreSQL (Multi-AZ)
        - Primary + Standby replicas
        - Automated failover
        - Daily backups
        - Enhanced monitoring
```

### Prerequisites for AWS Deployment

1. **AWS Account** with billing enabled
2. **AWS CLI** configured with credentials:
   ```bash
   aws configure
   # Enter: Access Key, Secret Key, Region (e.g., us-east-1), Format (json)
   ```

3. **Terraform** installed:
   ```bash
   # macOS
   brew install terraform
   
   # Windows (with choco)
   choco install terraform
   
   # Or download from: https://www.terraform.io/downloads.html
   ```

4. **Docker** & **ECR Repository** created:
   ```bash
   aws ecr create-repository --repository-name urbanmove --region us-east-1
   ```

### Step 1: Initialize Terraform

```bash
cd terraform/

# Initialize Terraform (downloads provider plugins)
terraform init

# View what will be created
terraform plan -var="db_password=YourSecurePassword123!"
```

### Step 2: Deploy Infrastructure

```bash
# Apply infrastructure (creates VPC, ALB, RDS, Security Groups, etc.)
terraform apply -var="db_password=YourSecurePassword123!"

# Type "yes" when prompted

# Save outputs for later
terraform output -json > outputs.json
```

**Terraform creates:**
- VPC with public & private subnets
- Internet Gateway & NAT Gateway
- Application Load Balancer (ALB) with target group
- RDS PostgreSQL (Multi-AZ, encrypted)
- Security Groups (network firewall rules)
- CloudWatch Log Group
- IAM Roles & Policies

### Step 3: Build & Push Docker Image to ECR

```bash
#!/bin/bash

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-1"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_NAME="urbanmove"
IMAGE_TAG="latest"

# Authenticate Docker with ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REGISTRY

# Build Docker image
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

# Tag for ECR
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ECR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}

# Push to ECR
docker push ${ECR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}

echo "Image pushed to: ${ECR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
```

Or use the included script:
```bash
bash deploy-aws.sh
```

### Step 4: Create ECS Cluster & Task Definition

```bash
# Create ECS Cluster
aws ecs create-cluster --cluster-name urbanmove-cluster --region us-east-1

# Register Task Definition
# Replace DB_ENDPOINT with output from terraform
aws ecs register-task-definition \
  --cli-input-json file://ecs-task-definition.json \
  --region us-east-1
```

**ECS Task Definition** (save as `ecs-task-definition.json`):
```json
{
  "family": "urbanmove-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "urbanmove-backend",
      "image": "YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/urbanmove:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://urbanmove:PASSWORD@RDS_ENDPOINT:5432/urbanmove_db"
        },
        {
          "name": "ENVIRONMENT",
          "value": "production"
        },
        {
          "name": "SECRET_KEY",
          "value": "CHANGE_IN_PRODUCTION"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/urbanmove-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Step 5: Create ECS Service

```bash
aws ecs create-service \
  --cluster urbanmove-cluster \
  --service-name urbanmove-backend \
  --task-definition urbanmove-backend:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-private-id],securityGroups=[sg-backend-id],assignPublicIp=DISABLED}" \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=urbanmove-backend,containerPort=8000 \
  --region us-east-1
```

### Step 6: Test Deployment

```bash
# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names urbanmove-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

# Test health endpoint
curl http://${ALB_DNS}/api/v1/health

# Login
curl -X POST http://${ALB_DNS}/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"demo_password_123"}'
```

---

## Scaling Behavior

### Horizontal Scaling

The backend is **stateless**, enabling horizontal scaling:

```bash
# Update ECS service desired count
aws ecs update-service \
  --cluster urbanmove-cluster \
  --service urbanmove-backend \
  --desired-count 5 \
  --region us-east-1
```

The ALB automatically distributes traffic across all backend instances.

### Auto-Scaling

For production, set up target tracking:

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/urbanmove-cluster/urbanmove-backend \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10 \
  --region us-east-1

# Create scaling policy (scale up when CPU > 70%)
aws application-autoscaling put-scaling-policy \
  --policy-name cpu-scaling \
  --service-namespace ecs \
  --resource-id service/urbanmove-cluster/urbanmove-backend \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration TargetValue=70.0,PredefinedMetricSpecification="{PredefinedMetricType=ECSServiceAverageCPUUtilization}" \
  --region us-east-1
```

---

## Disaster Recovery

### RDS Multi-AZ Automatic Failover

The Terraform configuration deploys RDS in **Multi-AZ** mode:

```hcl
multi_az = true
backup_retention_period = 7  # 7 days of daily backups
```

**What happens in case of failure:**
1. Primary database fails
2. RDS automatically promotes standby (< 1 minute)
3. Application reconnects automatically
4. No manual intervention needed

### Backup & Recovery

```bash
# Manual backup
aws rds create-db-snapshot \
  --db-instance-identifier urbanmove-db \
  --db-snapshot-identifier urbanmove-backup-$(date +%s) \
  --region us-east-1

# List snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier urbanmove-db \
  --region us-east-1

# Restore from snapshot (creates new DB)
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier urbanmove-db-restored \
  --db-snapshot-identifier urbanmove-backup-1234567890 \
  --region us-east-1
```

---

## Security Best Practices Implemented

### Network Security
✓ VPC isolation (private subnets for backend & database)
✓ Security Groups enforce least privilege
✓ ALB only allows HTTP/HTTPS from internet
✓ Backend only accessible from ALB
✓ RDS only accessible from backend

### Application Security
✓ JWT authentication on protected endpoints
✓ Password hashing with bcrypt
✓ Input validation (Pydantic schemas)
✓ HTTPS-ready (ALB handles TLS termination)

### Data Security
✓ RDS encryption at rest (KMS)
✓ Encrypted connections (PostgreSQL SSL)
✓ Automated backups (7-day retention)
✓ No sensitive data in logs

### IAM Roles
Each service has least-privilege IAM role:
- Backend: CloudWatch Logs, RDS access
- RDS: Encryption key access
- ALB: Target group management

---

## Monitoring & Observability

### CloudWatch Logs

```bash
# View backend logs
aws logs tail /ecs/urbanmove-backend --follow

# Filter by error
aws logs filter-log-events \
  --log-group-name /ecs/urbanmove-backend \
  --filter-pattern "ERROR"
```

### CloudWatch Metrics

```bash
# View CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=urbanmove-backend \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 300 \
  --statistics Average
```

### ALB Health Checks

The ALB performs health checks every 30 seconds:

```bash
# View target health
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:ACCOUNT_ID:targetgroup/urbanmove-backend/abc123 \
  --region us-east-1
```

Unhealthy targets are automatically removed and replaced.

---

## Cost Estimation

**Approximate monthly costs** (us-east-1):

| Component | Size | Cost |
|-----------|------|------|
| ALB | 1 × ALB | $16.20 |
| NAT Gateway | 1 × NAT | $32.00 |
| ECS Fargate | 2 × (256 CPU, 512 MB) | $14.00 |
| RDS PostgreSQL | db.t3.micro, Multi-AZ | $65.00 |
| Data Transfer | ~10 GB | $0.90 |
| **Total** | | **~$128/month** |

*Note: Prices vary by region. Use AWS pricing calculator for exact estimates.*

---

## Cleanup (Destroy Infrastructure)

```bash
# Delete ECS service
aws ecs delete-service \
  --cluster urbanmove-cluster \
  --service urbanmove-backend \
  --force \
  --region us-east-1

# Delete cluster
aws ecs delete-cluster \
  --cluster urbanmove-cluster \
  --region us-east-1

# Destroy Terraform infrastructure
cd terraform/
terraform destroy -var="db_password=YourSecurePassword123!"

# Delete ECR repository
aws ecr delete-repository \
  --repository-name urbanmove \
  --force \
  --region us-east-1
```

---

## Troubleshooting

### Backend not healthy (ALB health check failing)

```bash
# SSH into container (for debugging)
aws ecs execute-command \
  --cluster urbanmove-cluster \
  --task <TASK_ID> \
  --container urbanmove-backend \
  --command "/bin/bash" \
  --interactive \
  --region us-east-1

# Check logs
aws logs tail /ecs/urbanmove-backend --follow
```

### Database connection refused

```bash
# Verify RDS is running
aws rds describe-db-instances \
  --db-instance-identifier urbanmove-db \
  --query 'DBInstances[0].DBInstanceStatus' \
  --region us-east-1

# Check security group rules
aws ec2 describe-security-groups \
  --group-ids sg-rds-id \
  --region us-east-1
```

### Service won't start

```bash
# Check task definition
aws ecs describe-task-definition \
  --task-definition urbanmove-backend:1 \
  --region us-east-1

# View task events
aws ecs describe-tasks \
  --cluster urbanmove-cluster \
  --tasks <TASK_ARN> \
  --region us-east-1
```

---

## Next Steps

1. ✅ Local development with Docker Compose
2. ✅ Deploy infrastructure with Terraform
3. ✅ Build and push Docker image to ECR
4. ✅ Create ECS cluster and service
5. 📈 Set up auto-scaling policies
6. 📊 Create CloudWatch dashboards
7. 🔔 Configure SNS alerts
8. 🔐 Enable AWS WAF on ALB
9. 🌍 Map custom domain (Route 53)
10. 📜 Set up CI/CD pipeline (GitHub Actions)

---

For questions or issues, refer to the main [README.md](README.md).
