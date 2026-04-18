"""
Authentication endpoints.

Security:
- Issues JWT tokens on successful login
- Token used to authorize access to /route endpoint
- Tokens expire after 60 minutes
- In production: HTTPS enforced by ALB
"""

from fastapi import APIRouter, HTTPException, status
from app.schemas.mobility import LoginRequest, LoginResponse
from app.auth.jwt_handler import create_access_token, hash_password, verify_password

router = APIRouter()

# Simple in-memory credentials (in production, use database + secrets manager)
DEMO_CREDENTIALS = {
    "admin": hash_password("demo_password_123")
}


@router.post("/auth/login", response_model=LoginResponse)
def login(credentials: LoginRequest):
    """
    Login endpoint - issues JWT token.
    
    Security:
    - Validates username/password
    - Returns JWT token valid for 60 minutes
    - Token required for /route endpoint
    
    In Production AWS Setup:
    - Credentials stored in AWS Secrets Manager
    - Database queries instead of in-memory
    - CloudWatch logs authentication attempts
    - ALB enforces HTTPS-only (TLS termination)
    
    Args:
        credentials: Username and password
        
    Returns:
        JWT access token
        
    Raises:
        HTTPException: Invalid credentials
    """
    # Check credentials (demo implementation)
    if credentials.username not in DEMO_CREDENTIALS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not verify_password(credentials.password, DEMO_CREDENTIALS[credentials.username]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Generate JWT token
    token = create_access_token(data={"sub": credentials.username})
    
    return LoginResponse(
        access_token=token,
        token_type="bearer"
    )
