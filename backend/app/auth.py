"""
Authentication utilities using JWT tokens.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import jwt
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
_project_root = Path(__file__).parent.parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    load_dotenv(_env_file)
else:
    load_dotenv()

# JWT Secret Key (should be in .env file)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days


def create_access_token(user_id: str, phone_number: str) -> str:
    """Create JWT access token for user."""
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "user_id": user_id,
        "phone_number": phone_number,
        "exp": expiration,
        "iat": datetime.now(timezone.utc)
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> Optional[Dict]:
    """Verify JWT token and return payload if valid."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

