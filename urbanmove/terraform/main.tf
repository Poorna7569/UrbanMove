# Terraform configuration for UrbanMove AWS infrastructure
# Apply with: terraform apply

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ====================
# VPC & Networking
# ====================

resource "aws_vpc" "urbanmove" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "urbanmove-vpc"
  }
}

# Public Subnet (ALB)
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.urbanmove.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "urbanmove-public-subnet"
  }
}

# Private Subnet (Backend + RDS)
resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.urbanmove.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "urbanmove-private-subnet"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "urbanmove" {
  vpc_id = aws_vpc.urbanmove.id

  tags = {
    Name = "urbanmove-igw"
  }
}

# Elastic IP for NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "urbanmove-nat-eip"
  }

  depends_on = [aws_internet_gateway.urbanmove]
}

# NAT Gateway (in public subnet)
resource "aws_nat_gateway" "urbanmove" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id

  tags = {
    Name = "urbanmove-nat"
  }

  depends_on = [aws_internet_gateway.urbanmove]
}

# Route Table: Public
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.urbanmove.id

  route {
    cidr_block      = "0.0.0.0/0"
    gateway_id      = aws_internet_gateway.urbanmove.id
  }

  tags = {
    Name = "urbanmove-public-rt"
  }
}

# Route Table Association: Public
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Route Table: Private
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.urbanmove.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.urbanmove.id
  }

  tags = {
    Name = "urbanmove-private-rt"
  }
}

# Route Table Association: Private
resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}

# ====================
# Security Groups
# ====================

# ALB Security Group
resource "aws_security_group" "alb" {
  name   = "urbanmove-alb-sg"
  vpc_id = aws_vpc.urbanmove.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "urbanmove-alb-sg"
  }
}

# Backend Security Group
resource "aws_security_group" "backend" {
  name   = "urbanmove-backend-sg"
  vpc_id = aws_vpc.urbanmove.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "urbanmove-backend-sg"
  }
}

# RDS Security Group
resource "aws_security_group" "rds" {
  name   = "urbanmove-rds-sg"
  vpc_id = aws_vpc.urbanmove.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "urbanmove-rds-sg"
  }
}

# ====================
# RDS PostgreSQL
# ====================

resource "aws_db_subnet_group" "urbanmove" {
  name       = "urbanmove-db-subnet-group"
  subnet_ids = [aws_subnet.private.id, aws_subnet.public.id]

  tags = {
    Name = "urbanmove-db-subnet-group"
  }
}

resource "aws_db_instance" "urbanmove" {
  identifier     = "urbanmove-db"
  engine         = "postgres"
  engine_version = "15.3"
  instance_class = "db.t3.micro"

  allocated_storage = 20
  storage_encrypted = true

  db_name  = "urbanmove_db"
  username = "urbanmove"
  password = var.db_password

  db_subnet_group_name            = aws_db_subnet_group.urbanmove.name
  vpc_security_group_ids          = [aws_security_group.rds.id]
  publicly_accessible             = false
  multi_az                        = true
  backup_retention_period         = 7
  backup_window                   = "03:00-04:00"
  maintenance_window              = "mon:04:00-mon:05:00"
  enable_cloudwatch_logs_exports  = ["postgresql"]

  skip_final_snapshot = false
  final_snapshot_identifier = "urbanmove-db-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  tags = {
    Name = "urbanmove-postgres"
  }
}

# ====================
# Application Load Balancer
# ====================

resource "aws_lb" "urbanmove" {
  name               = "urbanmove-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.public.id, aws_subnet.public.id]

  tags = {
    Name = "urbanmove-alb"
  }
}

resource "aws_lb_target_group" "urbanmove" {
  name        = "urbanmove-backend"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.urbanmove.id
  target_type = "ip"

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/api/v1/health"
    matcher             = "200"
  }

  tags = {
    Name = "urbanmove-tg"
  }
}

resource "aws_lb_listener" "urbanmove" {
  load_balancer_arn = aws_lb.urbanmove.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.urbanmove.arn
  }
}

# ====================
# CloudWatch Logs
# ====================

resource "aws_cloudwatch_log_group" "urbanmove" {
  name              = "/ecs/urbanmove-backend"
  retention_in_days = 7

  tags = {
    Name = "urbanmove-logs"
  }
}

# ====================
# Data Sources
# ====================

data "aws_availability_zones" "available" {
  state = "available"
}

# ====================
# Outputs
# ====================

output "alb_dns_name" {
  value       = aws_lb.urbanmove.dns_name
  description = "DNS name of the load balancer"
}

output "rds_endpoint" {
  value       = aws_db_instance.urbanmove.endpoint
  description = "RDS endpoint"
}

output "vpc_id" {
  value       = aws_vpc.urbanmove.id
  description = "VPC ID"
}
