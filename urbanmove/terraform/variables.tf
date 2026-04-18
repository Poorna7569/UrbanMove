# Terraform variables

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "db_password" {
  description = "RDS database password"
  type        = string
  sensitive   = true
}
