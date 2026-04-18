"""
Database configuration module.
Handles SQLAlchemy setup for PostgreSQL connection.

Cloud Deployment Note:
- In AWS, this connects to RDS PostgreSQL in the PRIVATE SUBNET
- Database endpoint is only accessible from backend containers
- Backend runs in containers behind the ALB (PUBLIC SUBNET)
- Data flow: User → ALB (Public Subnet) → Backend (Private Subnet) → RDS (Private Subnet)
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
import os

# RDS PostgreSQL connection string
# In production, these environment variables are injected by AWS ECS/Docker
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://urbanmove:urbanmove_pass@postgres:5432/urbanmove_db"
)

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
