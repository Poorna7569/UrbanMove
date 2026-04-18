# UrbanMove Quick Reference

## 🚀 Quick Start (60 seconds)

```bash
# 1. Clone/enter project
cd urbanmove

# 2. Start everything
docker-compose up --build

# 3. In new terminal, test
python test_api.py

# Expected: ✓ All 7 tests passed
```

---

## 📋 API Quick Reference

### Login & Get JWT
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"demo_password_123"}'

# Response: {"access_token":"eyJ0eXAi...", "token_type":"bearer"}
```

### Ingest Vehicle Data
```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id":"CAR-001",
    "latitude":40.7128,
    "longitude":-74.0060,
    "traffic_level":"high"
  }'

# Response: {"id":1, "vehicle_id":"CAR-001", ...}
```

### Get Optimized Route (requires JWT)
```bash
curl -X GET "http://localhost:8000/api/v1/route?source=NYC&destination=Boston" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Response: {"route":"NYC → [ALTERNATE] → Boston", "traffic_status":"high", ...}
```

### Health Check
```bash
curl http://localhost:8000/api/v1/health

# Response: {"status":"healthy", "database":"connected", "version":"1.0.0"}
```

---

## 🐳 Docker Compose Commands

```bash
# Start all services
docker-compose up --build

# View logs
docker-compose logs -f backend
docker-compose logs -f postgres

# Stop services
docker-compose down

# Remove volumes (clean database)
docker-compose down -v

# Enter container shell
docker-compose exec backend bash

# Access PostgreSQL directly
docker-compose exec postgres psql -U urbanmove -d urbanmove_db
```

---

## 🏗️ Terraform Quick Reference

```bash
cd terraform/

# Preview changes
terraform plan -var="db_password=YourPassword123!"

# Deploy infrastructure
terraform apply -var="db_password=YourPassword123!"

# Get outputs
terraform output -json

# Destroy everything
terraform destroy -var="db_password=YourPassword123!"
```

---

## 🧪 Testing

```bash
# Run all API tests
python test_api.py

# Test individual endpoints
curl http://localhost:8000/api/v1/health
curl -X POST http://localhost:8000/api/v1/auth/login ...
curl -X POST http://localhost:8000/api/v1/ingest ...
curl http://localhost:8000/api/v1/route?source=X&destination=Y -H "Authorization: Bearer TOKEN"
```

---

## 🗄️ Database

### Connect to PostgreSQL
```bash
# Local (docker-compose)
docker-compose exec postgres psql -U urbanmove -d urbanmove_db

# AWS RDS (replace ENDPOINT)
psql -h urbanmove-db.xxxxx.us-east-1.rds.amazonaws.com \
     -U urbanmove \
     -d urbanmove_db
```

### Useful SQL Queries
```sql
-- View all mobility data
SELECT * FROM mobility_data ORDER BY timestamp DESC LIMIT 10;

-- Count records by traffic level
SELECT traffic_level, COUNT(*) as count FROM mobility_data GROUP BY traffic_level;

-- Recent data (last 30 mins)
SELECT * FROM mobility_data 
WHERE timestamp >= NOW() - INTERVAL '30 minutes' 
ORDER BY timestamp DESC;

-- Data by vehicle
SELECT vehicle_id, COUNT(*) as records, MAX(timestamp) as last_seen 
FROM mobility_data 
GROUP BY vehicle_id;
```

---

## 📊 Architecture at a Glance

### Local (Docker Compose)
```
┌──────────────────────────┐
│   Your Computer          │
├──────────────────────────┤
│  localhost:8000          │  ← FastAPI Backend
│       ↓↑                 │
│  localhost:5432          │  ← PostgreSQL
└──────────────────────────┘
```

### AWS (Terraform)
```
┌─────────────────────────────────────┐
│  AWS VPC (10.0.0.0/16)              │
├───────────────────┬─────────────────┤
│  PUBLIC (ALB)     │  PRIVATE        │
│                   │  ├─ Backend     │
│  Internet         │  └─ RDS         │
│  ↓↑               │                 │
│  ALB (80/443)     │                 │
│  ↓                │                 │
│  NAT Gateway      │                 │
└───────────────────┴─────────────────┘
```

---

## 🔐 Security Summary

| Layer | Protection |
|-------|-----------|
| Network | VPC, Security Groups, Private subnets |
| Transport | TLS/HTTPS (ALB) |
| Application | JWT authentication |
| Data | PostgreSQL encryption |
| Access | IAM roles, least privilege |

---

## 📈 Scaling

```bash
# Local: Auto-scales within container limits

# AWS: Scale backend (ECS)
aws ecs update-service \
  --cluster urbanmove-cluster \
  --service urbanmove-backend \
  --desired-count 5

# Database: RDS read replicas (manual)
aws rds create-db-instance-read-replica ...
```

---

## 🐛 Troubleshooting

### Service won't start
```bash
docker-compose logs backend
# Check for: DATABASE_URL, missing dependencies, port conflicts
```

### Database connection error
```bash
docker-compose exec backend bash
python -c "from app.database import engine; engine.connect()"
```

### Tests failing
```bash
# Ensure service is running
docker-compose ps

# Wait a bit longer for startup
sleep 5
python test_api.py
```

### Port conflicts
```bash
# Change docker-compose ports:
# ports:
#   - "8001:8000"  # Change 8000 to 8001

# Update test_api.py:
# BASE_URL = "http://localhost:8001/api/v1"
```

---

## 📚 Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI application setup |
| `app/routes/` | API endpoints |
| `app/database.py` | Database configuration |
| `app/models/` | ORM models |
| `app/schemas/` | Pydantic validation |
| `app/services/` | Business logic |
| `app/auth/` | JWT authentication |
| `Dockerfile` | Container image |
| `docker-compose.yml` | Local environment |
| `terraform/main.tf` | AWS infrastructure |
| `test_api.py` | API tests |
| `README.md` | Main documentation |
| `DEPLOYMENT.md` | AWS deployment guide |

---

## ✅ Pre-Deployment Checklist

- [ ] All tests pass (`python test_api.py`)
- [ ] Docker images build without errors
- [ ] Requirements.txt has all dependencies
- [ ] Terraform syntax is valid (`terraform validate`)
- [ ] AWS credentials configured (`aws configure`)
- [ ] ECR repository created
- [ ] Secrets are in environment variables (not hardcoded)
- [ ] README and docs are up to date
- [ ] Git repo initialized and committed

---

## 🆘 Support

**Files to check:**
1. README.md - Architecture & setup
2. DEPLOYMENT.md - AWS deployment steps
3. BUILD_SUMMARY.md - Feature completeness
4. app/main.py - Application structure

**Common questions:**
- Q: How do I run locally?
  A: `docker-compose up --build && python test_api.py`

- Q: How do I deploy to AWS?
  A: See DEPLOYMENT.md (step-by-step guide)

- Q: What's the default admin password?
  A: `demo_password_123` (change in production)

- Q: Can I scale horizontally?
  A: Yes! Backend is stateless. Increase ECS desired count.

- Q: How's the database backed up?
  A: RDS Multi-AZ with daily snapshots (7-day retention)

---

**Last Updated**: 2024
**Status**: Production Ready ✅
