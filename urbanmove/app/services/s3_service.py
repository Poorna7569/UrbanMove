"""
AWS S3 upload service.
Handles uploading mobility data to S3 bucket using IAM role.

Security:
- Uses IAM role attached to EC2 instance (no hardcoded credentials)
- Credentials managed automatically by boto3
- S3 bucket: urbanmove-data-poorna
"""

import boto3
import json
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# S3 bucket configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "urbanmove-data-poorna")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


class S3Service:
    """Service for S3 operations using IAM role."""
    
    _s3_client = None
    
    @staticmethod
    def _get_s3_client():
        """
        Get or create S3 client.
        Uses IAM role credentials automatically (no hardcoded keys).
        
        Returns:
            boto3 S3 client
        """
        if S3Service._s3_client is None:
            S3Service._s3_client = boto3.client(
                's3',
                region_name=AWS_REGION
            )
        return S3Service._s3_client
    
    @staticmethod
    def upload_to_s3(data: dict) -> dict:
        """
        Upload mobility data to S3 as JSON.
        
        Architecture:
        - Runs after database persistence (non-blocking failure)
        - Uses IAM role for authentication
        - Generates unique filename with timestamp
        - Logs all operations
        
        Args:
            data: Dictionary containing mobility data
                  Example: {
                      "vehicle_id": "VEH-001",
                      "latitude": 40.7128,
                      "longitude": -74.0060,
                      "traffic_level": "high",
                      "timestamp": "2026-04-24T15:30:00"
                  }
        
        Returns:
            dict: Upload result with status and details
                  Success: {"status": "success", "bucket": "...", "key": "..."}
                  Failure: {"status": "failed", "error": "..."}
        
        Side Effects:
            - Logs successful upload with S3 key
            - Logs errors without raising exceptions
        """
        try:
            # Generate unique filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            vehicle_id = data.get("vehicle_id", "unknown")
            filename = f"mobility_{vehicle_id}_{timestamp}.json"
            s3_key = f"raw-data/{filename}"
            
            # Convert data to JSON
            json_data = json.dumps(data, default=str)
            
            # Get S3 client
            s3_client = S3Service._get_s3_client()
            
            # Upload to S3
            response = s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=s3_key,
                Body=json_data,
                ContentType='application/json',
                Metadata={
                    'vehicle_id': vehicle_id,
                    'uploaded_at': datetime.utcnow().isoformat()
                }
            )
            
            logger.info(
                f"✓ S3 upload successful: s3://{S3_BUCKET_NAME}/{s3_key} "
                f"(ETag: {response.get('ETag')})"
            )
            
            return {
                "status": "success",
                "bucket": S3_BUCKET_NAME,
                "key": s3_key,
                "etag": response.get('ETag')
            }
            
        except Exception as e:
            error_message = f"S3 upload failed: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            return {
                "status": "failed",
                "error": error_message
            }
