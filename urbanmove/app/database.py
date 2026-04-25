"""
Database configuration module.
Handles SQLAlchemy setup for AWS RDS PostgreSQL connection.

Architecture:
- In AWS ECS/Fargate: Connects to RDS PostgreSQL in the PRIVATE SUBNET
- Database endpoint is only accessible from backend containers
- Backend runs in containers behind the ALB (PUBLIC SUBNET)
- Data flow: User → ALB (Public Subnet) → Backend (Private Subnet) → RDS (Private Subnet)

Database Credentials:
- Retrieved from AWS Secrets Manager in production
- DATABASE_URL environment variable is required
- No local Docker fallback - RDS only
- Credentials are never hardcoded
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
import os
import json
import boto3
from botocore.exceptions import ClientError
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def get_database_url():
    """
    Retrieve DATABASE_URL from AWS Secrets Manager or environment variable.
    
    RDS-only configuration - no local Docker fallback.
    
    Returns:
        str: PostgreSQL connection URL
        
    Raises:
        RuntimeError: If DATABASE_URL cannot be obtained or is invalid
    """
    # First check if DATABASE_URL is explicitly set in environment
    # This is the primary method for ECS/Docker deployments
    env_db_url = os.getenv("DATABASE_URL")
    
    if env_db_url:
        logger.info("✓ DATABASE_URL found in environment variable")
        return env_db_url
    
    # Try AWS Secrets Manager as fallback (for EC2 or local AWS CLI access)
    try:
        secret_name = "urbanmove-db-secret"
        region_name = os.getenv("AWS_REGION", "eu-north-1")
        
        logger.info(f"DATABASE_URL not in environment, attempting AWS Secrets Manager...")
        client = boto3.client("secretsmanager", region_name=region_name)
        
        try:
            response = client.get_secret_value(SecretId=secret_name)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFoundException":
                logger.info(f"Secret {secret_name} not found in Secrets Manager")
                raise ValueError(f"Secret {secret_name} not found")
            elif error_code in ["InvalidRequestException", "InvalidParameterException"]:
                logger.info(f"Invalid request to Secrets Manager")
                raise ValueError(f"Invalid request for secret {secret_name}")
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
        logger.info(f"✓ Database credentials retrieved from AWS Secrets Manager")
        logger.info(f"  RDS Host: {host}:{port}")
        logger.info(f"  Database: {dbname}")
        return database_url
        
    except Exception as e:
        error_msg = (
            "CRITICAL: Cannot initialize database connection.\n"
            "DATABASE_URL environment variable is not set, and AWS Secrets Manager is unavailable.\n"
            "Application requires either:\n"
            "1. DATABASE_URL environment variable (recommended for ECS/Docker), OR\n"
            "2. AWS Secrets Manager secret 'urbanmove-db-secret' with proper IAM permissions\n"
            "This application ONLY connects to AWS RDS - no local Docker database fallback.\n"
            f"Error: {str(e)}"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def validate_database_url(url: str) -> None:
    """
    Validate that DATABASE_URL is properly formatted and points to RDS.
    
    Args:
        url: PostgreSQL connection URL
        
    Raises:
        ValueError: If URL is invalid or uses local/docker hostnames
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid DATABASE_URL format: {str(e)}")
    
    # Check for local/docker hostnames
    local_hostnames = ["localhost", "127.0.0.1", "postgres", "0.0.0.0"]
    if parsed.hostname and parsed.hostname.lower() in local_hostnames:
        raise ValueError(
            f"Invalid DATABASE_URL: hostname '{parsed.hostname}' is a local/docker name. "
            "This application ONLY connects to AWS RDS."
        )
    
    # Check database name
    db_path = parsed.path.lstrip("/")
    if not db_path:
        raise ValueError("DATABASE_URL must include database name (path)")
    
    logger.info(f"✓ DATABASE_URL validation passed")
    logger.info(f"  Host: {parsed.hostname}")
    logger.info(f"  Database: {db_path}")


# Retrieve and validate DATABASE_URL at module load time
try:
    DATABASE_URL = get_database_url()
    validate_database_url(DATABASE_URL)
    logger.info("✓ Database configuration ready")
except RuntimeError as e:
    logger.critical(f"Failed to initialize database configuration: {str(e)}")
    raise
except ValueError as e:
    logger.critical(f"Invalid database configuration: {str(e)}")
    raise RuntimeError(f"Database configuration error: {str(e)}")

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
