"""
Health check endpoint.

Observability:
- ALB uses this endpoint for health checks (every 30 seconds)
- If backend fails 3 consecutive checks, ALB removes instance
- Enables automated recovery and scaling decisions
- CloudWatch logs all checks for monitoring
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.schemas.mobility import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    
    Returns:
        Health status including database connectivity
        
    Used by:
    - ALB for instance health monitoring
    - CloudWatch for observability
    - Kubernetes (if deployed on EKS)
    """
    try:
        # Test database connectivity
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return HealthResponse(
        status="healthy",
        database=db_status,
        version="1.0.0"
    )
