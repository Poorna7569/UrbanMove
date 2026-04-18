"""
Pydantic schemas for request/response validation.
Ensures data integrity at API boundaries.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal


class MobilityDataIngest(BaseModel):
    """Schema for POST /ingest endpoint."""
    vehicle_id: str = Field(..., min_length=1, max_length=50)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    traffic_level: Literal["low", "medium", "high"] = Field(...)


class MobilityDataResponse(BaseModel):
    """Schema for mobility data responses."""
    id: int
    vehicle_id: str
    latitude: float
    longitude: float
    traffic_level: str
    timestamp: datetime

    class Config:
        from_attributes = True


class RouteRequest(BaseModel):
    """Schema for GET /route endpoint."""
    source: str = Field(..., min_length=1)
    destination: str = Field(..., min_length=1)


class RouteResponse(BaseModel):
    """Schema for route response."""
    route: str
    estimated_duration: str
    traffic_status: str
    recommendation: str


class LoginRequest(BaseModel):
    """Schema for POST /auth/login endpoint."""
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Schema for login response."""
    access_token: str
    token_type: str


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    database: str
    version: str
