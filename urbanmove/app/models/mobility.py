"""
Database models for mobility data.

Schema Design:
- mobility_data: Stores vehicle telemetry (location, traffic level)
- This data drives route optimization decisions
- Indexed on vehicle_id and timestamp for efficient queries
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base


class MobilityData(Base):
    """
    Stores vehicle mobility telemetry.
    
    Cloud Context:
    - Data stored in RDS PostgreSQL (Private Subnet)
    - Accessed only by backend services
    - Enables analytics and route optimization
    """
    __tablename__ = "mobility_data"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(String(50), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    traffic_level = Column(String(10), nullable=False)  # "low", "medium", "high"
    timestamp = Column(DateTime, default=func.now(), nullable=False)

    # Index for common query patterns: find vehicle data within time range
    __table_args__ = (
        Index('idx_vehicle_timestamp', 'vehicle_id', 'timestamp'),
    )
