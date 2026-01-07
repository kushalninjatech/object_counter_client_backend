"""Application Configuration"""
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator

# Base directory of the backend application
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings with validation"""

    # Application
    APP_NAME: str = "ANPR Client Backend"
    APP_VERSION: str = "1.0.0"
    PROJECT_NAME: str = "Default Project"  # Client/Project name - configure in .env
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Database
    DB_URL: str = "postgresql://anpr_user:anpr_password@localhost:5432/anpr_client_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600
    DB_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Central Server
    CENTRAL_SERVER_URL: str = "https://flowershow.kushaldulani.xyz/api/v1/anpr/upload"
    CENTRAL_SERVER_API_KEY: str = "75719952247bc229de2fc6785950ce9592fa5028e911668ccdc672306ebe0c75"
    CENTRAL_SERVER_TIMEOUT: int = 30
    CENTRAL_SERVER_ENABLED: bool = True  # Set to False to disable uploads

    # Organization
    ORGANIZATION_ID: int = 3

    # YOLO Model
    MODEL_PATH: str = "yolov8n.pt"

    # Detection Classes (COCO dataset)
    # 0: person, 2: car, 3: motorcycle, 5: bus, 7: truck
    DETECTION_CLASSES_STR: str = "0,2,3,5,7"

    # Class names mapping
    CLASS_NAMES: dict = {
        0: 'person',
        2: 'car',
        3: 'motorcycle',
        5: 'bus',
        7: 'truck'
    }

    # Object capacities (maximum allowed for each object type)
    OBJECT_CAPACITIES: dict = {
        'person': 5000,
        'car': 5000,
        'motorcycle': 5000,
        'bus': 5000,
        'truck': 5000
    }

    # Storage
    DETECTIONS_DIR: Path = BASE_DIR / "detections"

    # RTSP Settings
    RTSP_TRANSPORT: str = "udp"  # Options: "udp" (faster, less reliable) or "tcp" (slower, more reliable)
    TARGET_FPS: int = 30
    CONFIDENCE: float = 0.5
    ZONE_PROXIMITY: int = 100

    # Number Plate Detection Settings
    MAX_IMAGES_PER_VEHICLE: int = 3
    FRAMES_BETWEEN_SAVES: int = 10

    # Upload Retry Settings
    MAX_RETRIES: int = 4
    RETRY_DELAY_1: int = 5      # 5 seconds
    RETRY_DELAY_2: int = 60     # 1 minute
    RETRY_DELAY_3: int = 300    # 5 minutes
    RETRY_DELAY_4: int = 3600   # 1 hour

    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

    @field_validator("DETECTIONS_DIR", mode="before")
    @classmethod
    def create_detections_dir(cls, v):
        """Create detections directory if it doesn't exist"""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def detection_classes(self) -> List[int]:
        """Parse detection classes from string"""
        return [int(c.strip()) for c in self.DETECTION_CLASSES_STR.split(",")]

    @property
    def retry_delays(self) -> List[int]:
        """Get retry delays as list"""
        return [
            self.RETRY_DELAY_1,
            self.RETRY_DELAY_2,
            self.RETRY_DELAY_3,
            self.RETRY_DELAY_4
        ]

    def update_central_server(self, url: str, api_key: str, enabled: bool = True) -> None:
        """
        Update central server configuration

        Note: This updates the in-memory settings only. Changes will be lost on restart.
        For persistent updates, modify the .env file or use a database.

        Args:
            url: New central server URL
            api_key: New API key for authentication
            enabled: Enable/disable uploads to central server
        """
        self.CENTRAL_SERVER_URL = url
        self.CENTRAL_SERVER_API_KEY = api_key
        self.CENTRAL_SERVER_ENABLED = enabled


# Global settings instance
settings = Settings()
