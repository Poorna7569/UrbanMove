"""
API Key authentication module.
Implements header-based API key validation using FastAPI dependency injection.

The valid API key is read from the API_KEY environment variable.
All requests must include the "x-api-key" header with the correct value.
Invalid or missing API keys result in HTTP 403 Forbidden responses.
"""

from fastapi import Header, HTTPException, logging
import os

logger = logging.getLogger(__name__)


async def verify_api_key(x_api_key: str = Header(None)) -> str:
    """
    Verify API key from request header.
    
    Args:
        x_api_key: API key from "x-api-key" header
        
    Returns:
        str: The validated API key
        
    Raises:
        HTTPException: 403 Forbidden if API key is missing or invalid
    """
    valid_api_key = os.getenv("API_KEY")
    
    # Check if API_KEY environment variable is set
    if not valid_api_key:
        logger.error("API_KEY environment variable is not configured")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: API_KEY not set"
        )
    
    # Check if header is provided
    if not x_api_key:
        logger.warning("Request attempted without x-api-key header")
        raise HTTPException(
            status_code=403,
            detail="Missing API key. Include 'x-api-key' header."
        )
    
    # Validate API key
    if x_api_key != valid_api_key:
        logger.warning(f"Invalid API key attempt: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return x_api_key
