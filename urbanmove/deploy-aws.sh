#!/bin/bash
# AWS Deployment Script for UrbanMove
# Prerequisites: AWS CLI configured, ECR repo created

set -e

# Configuration
AWS_REGION="us-east-1"
ECR_REPO_NAME="urbanmove"
IMAGE_TAG="latest"
ECS_CLUSTER="urbanmove-cluster"
ECS_SERVICE="urbanmove-backend"
DOCKER_FILE="Dockerfile"

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${ECR_REGISTRY}/${ECR_REPO_NAME}:${IMAGE_TAG}"

echo "=========================================="
echo "UrbanMove AWS Deployment"
echo "=========================================="
echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "ECR Image: $IMAGE_URI"
echo ""

# Step 1: Authenticate with ECR
echo "Step 1: Authenticating with ECR..."
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REGISTRY

# Step 2: Build Docker image
echo "Step 2: Building Docker image..."
docker build -f $DOCKER_FILE -t $ECR_REPO_NAME:$IMAGE_TAG .

# Step 3: Tag for ECR
echo "Step 3: Tagging image for ECR..."
docker tag $ECR_REPO_NAME:$IMAGE_TAG $IMAGE_URI

# Step 4: Push to ECR
echo "Step 4: Pushing to ECR..."
docker push $IMAGE_URI

# Step 5: Update ECS service
echo "Step 5: Updating ECS service..."
aws ecs update-service \
  --cluster $ECS_CLUSTER \
  --service $ECS_SERVICE \
  --force-new-deployment \
  --region $AWS_REGION

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Monitor deployment:"
echo "aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION"
echo ""
echo "Check logs:"
echo "aws logs tail /ecs/urbanmove-backend --follow --region $AWS_REGION"
