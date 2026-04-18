"""
Business logic for mobility operations.
Implements route optimization and data ingestion.

Scalability Note:
- Service layer is stateless, enabling horizontal scaling
- Multiple container instances process requests independently
- Database layer handles concurrency control
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.mobility import MobilityData
from app.schemas.mobility import MobilityDataIngest, RouteResponse
from datetime import datetime, timedelta


class MobilityService:
    """Service for mobility data operations."""
    
    @staticmethod
    def ingest_mobility_data(db: Session, data: MobilityDataIngest) -> MobilityData:
        """
        Ingest vehicle mobility telemetry.
        
        Cloud Flow:
        1. Request arrives at ALB (Public Subnet)
        2. ALB routes to backend container (Private Subnet)
        3. Backend ingests into RDS PostgreSQL (Private Subnet)
        4. Response flows back: DB → Backend → ALB → User
        
        Args:
            db: Database session
            data: Mobility data from vehicle
            
        Returns:
            Created MobilityData record
        """
        mobility_record = MobilityData(
            vehicle_id=data.vehicle_id,
            latitude=data.latitude,
            longitude=data.longitude,
            traffic_level=data.traffic_level
        )
        db.add(mobility_record)
        db.commit()
        db.refresh(mobility_record)
        return mobility_record
    
    @staticmethod
    def calculate_route(db: Session, source: str, destination: str) -> RouteResponse:
        """
        Calculate optimized route based on current traffic.
        
        Algorithm:
        - Queries recent mobility data (last 30 minutes)
        - Analyzes traffic_level distribution
        - If high traffic: suggests alternate route
        - If low/medium: suggests direct route
        
        Args:
            db: Database session
            source: Starting location
            destination: Ending location
            
        Returns:
            RouteResponse with route and traffic recommendation
        """
        # Query recent traffic data (last 30 minutes)
        thirty_mins_ago = datetime.utcnow() - timedelta(minutes=30)
        recent_data = db.query(MobilityData).filter(
            MobilityData.timestamp >= thirty_mins_ago
        ).order_by(desc(MobilityData.timestamp)).limit(100).all()
        
        # Analyze traffic levels
        if not recent_data:
            return RouteResponse(
                route=f"{source} → {destination}",
                estimated_duration="30 mins",
                traffic_status="unknown",
                recommendation="No recent traffic data available. Proceed with caution."
            )
        
        traffic_levels = [d.traffic_level for d in recent_data]
        high_traffic_count = traffic_levels.count("high")
        high_traffic_percentage = (high_traffic_count / len(traffic_levels)) * 100
        
        # Decision logic
        if high_traffic_percentage > 50:
            # High congestion detected → alternate route
            return RouteResponse(
                route=f"{source} → [ALTERNATE] → {destination}",
                estimated_duration="45 mins",
                traffic_status="high",
                recommendation="High traffic detected. Alternate route recommended."
            )
        elif high_traffic_percentage > 25:
            # Moderate congestion → direct route with caution
            return RouteResponse(
                route=f"{source} → {destination}",
                estimated_duration="35 mins",
                traffic_status="medium",
                recommendation="Moderate traffic. Direct route available."
            )
        else:
            # Low congestion → direct route
            return RouteResponse(
                route=f"{source} → {destination}",
                estimated_duration="25 mins",
                traffic_status="low",
                recommendation="Clear traffic. Direct route optimal."
            )
    
    @staticmethod
    def get_recent_traffic_summary(db: Session, hours: int = 1) -> dict:
        """
        Get traffic summary for monitoring/observability.
        
        Args:
            db: Database session
            hours: Look back period in hours
            
        Returns:
            Dictionary with traffic statistics
        """
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        data = db.query(MobilityData).filter(
            MobilityData.timestamp >= time_threshold
        ).all()
        
        if not data:
            return {"total_records": 0, "status": "no data"}
        
        traffic_counts = {
            "low": len([d for d in data if d.traffic_level == "low"]),
            "medium": len([d for d in data if d.traffic_level == "medium"]),
            "high": len([d for d in data if d.traffic_level == "high"])
        }
        
        return {
            "total_records": len(data),
            "traffic_distribution": traffic_counts,
            "period_hours": hours
        }
