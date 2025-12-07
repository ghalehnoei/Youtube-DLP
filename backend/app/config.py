"""
Configuration settings for the application.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional, Union
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Find .env file in project root (parent of backend directory)
    _project_root = Path(__file__).parent.parent.parent
    _env_file = _project_root / ".env"
    
    model_config = SettingsConfigDict(
        env_file=str(_env_file) if _env_file.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True  # Allow both field name and alias
    )
    
    # S3 Configuration - pydantic will automatically map s3_bucket to S3_BUCKET
    s3_bucket: Optional[str] = None
    s3_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None  # Maps to AWS_ACCESS_KEY_ID
    aws_secret_access_key: Optional[str] = None  # Maps to AWS_SECRET_ACCESS_KEY
    s3_endpoint_url: Optional[str] = None
    
    # S3 URL settings
    s3_url_expiration: int = 3600
    s3_public_urls: Union[bool, str] = False
    
    @field_validator('s3_public_urls', mode='before')
    @classmethod
    def parse_s3_public_urls(cls, v):
        """Convert string to boolean."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() == "true"
        return False
    
    # Download settings
    max_file_size_mb: int = 5000
    temp_dir: str = "./tmp/jobs"
    allowed_hosts: Optional[str] = None
    ffmpeg_path: Optional[str] = None  # Custom FFmpeg path if not in PATH
    no_check_certificate: Union[bool, str] = False  # Disable SSL certificate verification (for development/testing)
    
    @field_validator('no_check_certificate', mode='before')
    @classmethod
    def parse_no_check_certificate(cls, v):
        """Convert string to boolean."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() == "true"
        return False
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Keyword extraction settings
    keyword_extraction_backend: str = "auto"  # "openai", "blip", "basic", or "auto"
    openai_api_key: Optional[str] = None  # Maps to OPENAI_API_KEY
    openai_base_url: Optional[str] = None  # Maps to OPENAI_BASE_URL (for custom endpoints)
    openai_model: str = "gpt-4o-mini"  # OpenAI model to use
    keyword_max_count: int = 10  # Maximum number of keywords per frame
    
    @property
    def s3_access_key_id(self) -> Optional[str]:
        """Get S3 access key ID."""
        return self.aws_access_key_id
    
    @property
    def s3_secret_access_key(self) -> Optional[str]:
        """Get S3 secret access key."""
        return self.aws_secret_access_key
    


settings = Settings()


