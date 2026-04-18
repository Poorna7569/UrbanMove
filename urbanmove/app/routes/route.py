"""
Route optimization endpoint.
Calculates optimized routes based on real-time traffic.

Security: JWT-protected endpoint
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.mobility import RouteRequest, RouteResponse
from app.services.mobility_service import MobilityService
from app.auth.jwt_handler import verify_token
from typing import Optional

router = APIRouter()


def verify_jwt(authorization: Optional[str] = Header(None)) -> str:
    """
    Dependency for JWT verification.
    
    Security:
    - Extracts token from Authorization header
    - Validates JWT signature and expiration
    - Rejects expired or invalid tokens
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Username from token
        
    Raises:
        HTTPException: Invalid or missing token
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authentication scheme")
        
        payload = verify_token(token)
        username = payload.get("sub")
        
        if not username:
            raise ValueError("No username in token")
        
        return username
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.get("/route", response_model=RouteResponse)
def calculate_route(
    source: str,
    destination: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_jwt)
):
    """
    Calculate optimized route based on traffic.
    
    Security:
    - Requires valid JWT token in Authorization header
    - Token obtained from POST /auth/login
    
    Algorithm:
    - Queries recent traffic data (last 30 minutes)
    - Analyzes traffic distribution
    - If >50% high traffic: suggests alternate route
    - If 25-50% high traffic: direct route with caution
    - If <25% high traffic: direct route
    
    Flow:
    User → Authorization Header (JWT) → ALB → Backend → RDS Query → Route Calculation → Response
    
    Args:
        source: Starting location
        destination: Ending location
        db: Database session
        current_user: Authenticated user (from JWT)
        
    Returns:
        Optimized route with traffic-aware recommendation
        
    Raises:
        HTTPException: Missing/invalid JWT token
    """
    try:
        route_response = MobilityService.calculate_route(db, source, destination)
        return route_response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate route: {str(e)}"
        )
