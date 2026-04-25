"""
API Key authentication module.
Implements header-based API key validation using FastAPI dependency injection.

The valid API key is read from the API_KEY environment variable with a default fallback.
Public endpoints are exempt from API key validation.
All other requests must include the "x-api-key" header with the correct value.
Invalid or missing API keys result in HTTP 403 Forbidden responses.
"""

from fastapi import Header, HTTPException, Request
import logging
import os

logger = logging.getLogger(__name__)

API_KEY = os.getenv("API_KEY", "urbanmove123")


async def verify_api_key(request: Request, x_api_key: str = Header(None)) -> str:
    """
    Verify API key from request header for protected endpoints.
    
    Public endpoints are exempt from API key validation.
    Protected endpoints require a valid API key in the "x-api-key" header.
    
    Args:
        request: FastAPI Request object to check the path
        x_api_key: API key from "x-api-key" header
        
    Returns:
        str: The validated API key for protected endpoints
        
    Raises:
        HTTPException: 403 Forbidden if API key is missing or invalid for protected endpoints
    """
    # Allow public endpoints (exempt from API key validation)
    public_paths = [
        "/",
        "/api/v1/health",
        "/api/v1/status",
        "/docs",
        "/openapi.json"
    ]

    if request.url.path in public_paths:
        return

    # Enforce API key for protected endpoints
    if x_api_key != API_KEY:
        logger.warning(f"Invalid or missing API key for path: {request.url.path}")
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return x_api_key

