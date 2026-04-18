"""
Data ingestion endpoint.
Receives vehicle telemetry and stores in database.

Architecture Flow:
User (Vehicle) → ALB (Public Subnet, HTTP/HTTPS) 
               → Backend Container (Private Subnet) 
               → RDS PostgreSQL (Private Subnet)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.mobility import MobilityDataIngest, MobilityDataResponse
from app.services.mobility_service import MobilityService

router = APIRouter()


@router.post("/ingest", response_model=MobilityDataResponse, status_code=status.HTTP_201_CREATED)
def ingest_vehicle_data(
    data: MobilityDataIngest,
    db: Session = Depends(get_db)
):
    """
    Ingest vehicle mobility telemetry.
    
    This endpoint receives vehicle location and traffic data.
    
    Cloud Architecture Context:
    - ALB (Public Subnet) receives request from vehicle
    - ALB routes to backend container (Private Subnet)
    - Backend persists to RDS (Private Subnet)
    - Security Groups enforce traffic flow:
      * ALB Security Group: allows HTTP/HTTPS from internet
      * Backend Security Group: allows traffic only from ALB
      * RDS Security Group: allows only backend access
    
    Args:
        data: Vehicle telemetry (location, traffic level)
        db: Database session (dependency injection)
        
    Returns:
        Created MobilityData record
        
    Raises:
        HTTPException: If database operation fails
    """
    try:
        record = MobilityService.ingest_mobility_data(db, data)
        return record
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest data: {str(e)}"
        )
