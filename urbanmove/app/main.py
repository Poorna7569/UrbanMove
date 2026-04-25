"""
UrbanMove FastAPI Application.
Smart Mobility Platform for real-time route optimization.

Architecture Overview:

AWS VPC Setup:
├── Public Subnet
│   ├── ALB (Application Load Balancer) - HTTP/HTTPS entry point
│   └── NAT Gateway - for outbound traffic
└── Private Subnet
    ├── Backend Containers (ECS/Docker) - REST API
    └── RDS PostgreSQL - Database
    
Data Flow:
Vehicle/User → ALB (Public) → Backend (Private) → RDS (Private) → Backend → ALB → Response

Security:
- ALB Security Group: Allows HTTP/HTTPS from internet (0.0.0.0/0)
- Backend Security Group: Allows traffic only from ALB
- RDS Security Group: Allows only backend access
- JWT-based API authentication
- HTTPS ready (ALB handles TLS termination)

Scalability:
- Stateless backend services (horizontal scaling)
- Database connection pooling
- CloudWatch logs for monitoring
- ALB health checks drive auto-scaling decisions
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os

# Import routes
from app.routes import health, ingest, auth, route
from app.database import engine, Base
from app.auth.api_key import verify_api_key

# Configure logging for CloudWatch
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="UrbanMove",
    description="Smart Mobility Platform - Real-time Route Optimization",
    version="1.0.0",
    dependencies=[Depends(verify_api_key)]
)

# CORS configuration (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables (with error handling for connection issues)
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully")
except Exception as e:
    logger.warning(f"Could not create database tables on startup: {str(e)}")
    logger.info("Tables will be created on first request if needed")

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(ingest.router, prefix="/api/v1", tags=["ingest"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(route.router, prefix="/api/v1", tags=["route"])


@app.get("/")
def root():
    """
    Root endpoint.
    Returns API information.
    """
    return {
        "message": "UrbanMove Smart Mobility Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "health": "GET /api/v1/health",
            "ingest": "POST /api/v1/ingest",
            "login": "POST /api/v1/auth/login",
            "route": "GET /api/v1/route?source=A&destination=B (requires JWT)"
        }
    }


@app.get("/api/v1/status")
def status():
    """
    Extended status endpoint for monitoring.
    Used by CloudWatch and ALB.
    """
    return {
        "status": "operational",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "region": os.getenv("AWS_REGION", "us-east-1")
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler.
    Logs all errors for CloudWatch observability.
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    # Local development only
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
