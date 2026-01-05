"""Settings Pydantic schemas"""
from pydantic import BaseModel, Field, field_validator


class CentralServerConfig(BaseModel):
    """Schema for central server configuration response"""
    central_server_url: str = Field(..., description="Central server URL for detections")
    central_server_api_key: str = Field(..., description="API key for central server (masked)")
    central_server_timeout: int = Field(default=30, ge=1, le=300, description="Timeout for central server requests in seconds")
    central_server_enabled: bool = Field(default=True, description="Enable/disable uploads to central server")
    organization_id: int = Field(default=1, ge=1, description="Organization ID")

    class Config:
        json_schema_extra = {
            "example": {
                "central_server_url": "http://localhost:8010/api/v1/detections",
                "central_server_api_key": "8605fa5c...0467",
                "central_server_timeout": 30,
                "organization_id": 1
            }
        }


class CentralServerUpdate(BaseModel):
    """Schema for updating central server configuration"""
    central_server_url: str = Field(..., min_length=1, max_length=512, description="Central server URL for detections")
    central_server_api_key: str = Field(..., min_length=1, max_length=512, description="API key for central server authentication")
    central_server_enabled: bool = Field(default=True, description="Enable/disable uploads to central server")

    @field_validator("central_server_url")
    @classmethod
    def validate_url(cls, v):
        """Validate URL format"""
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("central_server_api_key")
    @classmethod
    def validate_api_key(cls, v):
        """Validate API key is not empty"""
        v = v.strip()
        if not v:
            raise ValueError("API key cannot be empty")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "central_server_url": "http://localhost:8010/api/v1/detections",
                "central_server_api_key": "8605fa5cba1d507c7e348186f070f05458fdba9192b9e4791a0026034e790467"
            }
        }
