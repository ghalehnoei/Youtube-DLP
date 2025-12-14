"""
User storage using database or Supabase Data API.
"""
from typing import List, Dict, Optional
from datetime import datetime, timezone
import uuid
import hashlib
from app.database import get_session, User
from sqlalchemy.orm import Session as SQLSession
from app.supabase_store import SupabaseStore


class UserStore:
    """Manages user storage in database or Supabase."""
    
    def __init__(self):
        """Initialize user store."""
        self.supabase_store = SupabaseStore()
        self.use_supabase = self.supabase_store.is_available()
        if self.use_supabase:
            print("Using Supabase Data API for user storage")
        else:
            print("Using local database (SQLite/PostgreSQL/MySQL) for user storage")
    
    def _to_dict(self, user: User) -> Dict:
        """Convert database model to dictionary."""
        return {
            "id": user.id,
            "phone_number": user.phone_number,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_active": bool(user.is_active),
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        }
    
    def create_user(
        self,
        phone_number: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> str:
        """Create a new user and return the user ID."""
        if self.use_supabase:
            return self._create_user_supabase(phone_number, first_name, last_name, email)
        
        db: SQLSession = get_session()
        try:
            # Check if user already exists
            existing = db.query(User).filter(User.phone_number == phone_number).first()
            if existing:
                raise ValueError(f"User with phone number {phone_number} already exists")
            
            user_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            user = User(
                id=user_id,
                phone_number=phone_number,
                first_name=first_name,
                last_name=last_name,
                email=email,
                is_active=1,
                created_at=now,
                updated_at=now
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            return user_id
        except Exception as e:
            db.rollback()
            print(f"Error creating user: {e}")
            raise
        finally:
            db.close()
    
    def _create_user_supabase(
        self,
        phone_number: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> str:
        """Create user in Supabase."""
        # Check if user exists
        existing = self.get_user_by_phone(phone_number)
        if existing:
            raise ValueError(f"User with phone number {phone_number} already exists")
        
        return self.supabase_store.create_user(phone_number, first_name, last_name, email)
    
    def get_user_by_phone(self, phone_number: str) -> Optional[Dict]:
        """Get user by phone number."""
        if self.use_supabase:
            return self._get_user_by_phone_supabase(phone_number)
        
        db: SQLSession = get_session()
        try:
            user = db.query(User).filter(User.phone_number == phone_number).first()
            if user:
                return self._to_dict(user)
            return None
        except Exception as e:
            print(f"Error getting user by phone: {e}")
            return None
        finally:
            db.close()
    
    def _get_user_by_phone_supabase(self, phone_number: str) -> Optional[Dict]:
        """Get user by phone from Supabase."""
        return self.supabase_store.get_user_by_phone(phone_number)
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        if self.use_supabase:
            return self._get_user_by_id_supabase(user_id)
        
        db: SQLSession = get_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return self._to_dict(user)
            return None
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
        finally:
            db.close()
    
    def _get_user_by_id_supabase(self, user_id: str) -> Optional[Dict]:
        """Get user by ID from Supabase."""
        return self.supabase_store.get_user_by_id(user_id)
    
    def verify_password(self, password: str) -> bool:
        """Verify password. Currently accepts only '111111'."""
        return password == "111111"
    
    def update_user(self, user_id: str, updates: Dict) -> bool:
        """Update user data."""
        if self.use_supabase:
            return self._update_user_supabase(user_id, updates)
        
        db: SQLSession = get_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            if "first_name" in updates:
                user.first_name = updates["first_name"]
            if "last_name" in updates:
                user.last_name = updates["last_name"]
            if "email" in updates:
                user.email = updates["email"]
            if "is_active" in updates:
                user.is_active = 1 if updates["is_active"] else 0
            
            user.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error updating user: {e}")
            return False
        finally:
            db.close()
    
    def _update_user_supabase(self, user_id: str, updates: Dict) -> bool:
        """Update user in Supabase."""
        return self.supabase_store.update_user(user_id, updates)

