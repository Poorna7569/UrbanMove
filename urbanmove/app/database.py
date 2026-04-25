"""
Database configuration module.
Handles SQLAlchemy setup for PostgreSQL connection.

Cloud Deployment Note:
- In AWS, this connects to RDS PostgreSQL in the PRIVATE SUBNET
- Database endpoint is only accessible from backend containers
- Backend runs in containers behind the ALB (PUBLIC SUBNET)
- Data flow: User → ALB (Public Subnet) → Backend (Private Subnet) → RDS (Private Subnet)
- Database credentials are fetched from AWS Secrets Manager
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
import os
import json
import boto3
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


def get_database_url():
    """
    Retrieve DATABASE_URL from AWS Secrets Manager or fallback to environment variable.
    
    In AWS ECS/Fargate:
    - Fetches secret "urbanmove-db-secret" from Secrets Manager
    - Parses JSON to extract credentials
    
    In local/development:
    - Falls back to DATABASE_URL environment variable
    
    Returns:
        str: PostgreSQL connection URL
        
    Raises:
        ValueError: If database credentials cannot be retrieved
    """
    # Try AWS Secrets Manager first (production)
    try:
        secret_name = "urbanmove-db-secret"
        region_name = os.getenv("AWS_REGION", "us-east-1")
        
        client = boto3.client("secretsmanager", region_name=region_name)
        
        try:
            response = client.get_secret_value(SecretId=secret_name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.warning(f"Secret {secret_name} not found in AWS Secrets Manager")
                raise ValueError(f"Secret {secret_name} not found")
            elif e.response["Error"]["Code"] == "InvalidRequestException":
                logger.warning(f"Invalid request for secret {secret_name}")
                raise ValueError(f"Invalid request for secret {secret_name}")
            elif e.response["Error"]["Code"] == "InvalidParameterException":
                logger.warning(f"Invalid parameter for secret {secret_name}")
                raise ValueError(f"Invalid parameter for secret {secret_name}")
            else:
                raise
        
        # Parse the secret JSON
        if "SecretString" in response:
            secret = json.loads(response["SecretString"])
        else:
            logger.error("Secret is not in JSON format")
            raise ValueError("Secret must be in JSON format")
        
        # Extract database credentials
        username = secret.get("username")
        password = secret.get("password")
        host = secret.get("host")
        port = secret.get("port", 5432)
        dbname = secret.get("dbname")
        
        # Validate all required fields
        required_fields = {"username": username, "password": password, "host": host, "dbname": dbname}
        missing_fields = [key for key, value in required_fields.items() if not value]
        
        if missing_fields:
            raise ValueError(f"Missing required fields in secret: {', '.join(missing_fields)}")
        
        # Construct DATABASE_URL
        database_url = f"postgresql://{username}:{password}@{host}:{port}/{dbname}"
        logger.info(f"Successfully retrieved database credentials from Secrets Manager for host: {host}")
        return database_url
        
    except Exception as e:
        logger.warning(f"Could not retrieve credentials from AWS Secrets Manager: {str(e)}")
        logger.info("Attempting to use environment variable DATABASE_URL")
        
        # Fallback to environment variable (local development)
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://urbanmove:urbanmove_pass@postgres:5432/urbanmove_db"
        )
        
        if database_url == "postgresql://urbanmove:urbanmove_pass@postgres:5432/urbanmove_db":
            logger.warning("Using default database URL - this is insecure for production!")
        
        return database_url


# Retrieve database URL at module load time
DATABASE_URL = get_database_url()

# Create engine with NullPool for horizontal scalability
# NullPool prevents connection pooling issues when scaling horizontally
# Each container instance manages its own connections
engine = create_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,  # Better for containerized, stateless services
    connect_args={"connect_timeout": 10}
)

# Session factory for dependency injection
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """
    Dependency injection function for database sessions.
    Used in FastAPI route parameters.
    Ensures proper session cleanup after each request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
