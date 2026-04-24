"""
Data ingestion endpoint.
Receives vehicle telemetry and stores in database.
Also uploads data to S3 for archival/analytics.

Architecture Flow:
User (Vehicle) → ALB (Public Subnet, HTTP/HTTPS) 
               → Backend Container (Private Subnet) 
               → RDS PostgreSQL (Private Subnet)
               → S3 Bucket (async, non-blocking)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.mobility import MobilityDataIngest, MobilityDataResponse
from app.services.mobility_service import MobilityService
from app.services.s3_service import S3Service
import logging

logger = logging.getLogger(__name__)

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
    - Backend uploads to S3 (async, non-blocking)
    - Security Groups enforce traffic flow:
      * ALB Security Group: allows HTTP/HTTPS from internet
      * Backend Security Group: allows traffic only from ALB
      * RDS Security Group: allows only backend access
      * S3 accessed via IAM role (no credentials exposed)
    
    Args:
        data: Vehicle telemetry (location, traffic level)
        db: Database session (dependency injection)
        
    Returns:
        Created MobilityData record
        
    Raises:
        HTTPException: If database operation fails
    """
    try:
        # 1. Persist to database
        record = MobilityService.ingest_mobility_data(db, data)
        
        # 2. Upload to S3 (non-blocking - don't fail API if S3 fails)
        data_dict = {
            "id": record.id,
            "vehicle_id": record.vehicle_id,
            "latitude": record.latitude,
            "longitude": record.longitude,
            "traffic_level": record.traffic_level,
            "timestamp": record.timestamp.isoformat() if record.timestamp else None
        }
        
        s3_result = S3Service.upload_to_s3(data_dict)
        logger.info(f"S3 upload result: {s3_result}")
        
        return record
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest data: {str(e)}"
        )
