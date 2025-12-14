"""
Metadata storage using database (PostgreSQL, MySQL, or SQLite) or Supabase Data API.
"""
from typing import List, Dict, Optional
from datetime import datetime, timezone
import uuid
from app.database import get_session, FileMetadata
from sqlalchemy.orm import Session as SQLSession
from app.supabase_store import SupabaseStore


class MetadataStore:
    """Manages file metadata storage in database or Supabase."""
    
    def __init__(self):
        """Initialize metadata store."""
        self.supabase_store = SupabaseStore()
        self.use_supabase = self.supabase_store.is_available()
        if self.use_supabase:
            print("Using Supabase Data API for metadata storage")
        else:
            print("Using local database (SQLite/PostgreSQL/MySQL) for metadata storage")
    
    def _to_dict(self, file_metadata: FileMetadata) -> Dict:
        """Convert database model to dictionary."""
        return {
            "id": file_metadata.id,
            "s3_url": file_metadata.s3_url,
            "s3_key": file_metadata.s3_key,
            "job_id": file_metadata.job_id,
            "metadata": file_metadata.file_metadata or {},  # Use file_metadata instead of metadata
            "video_width": file_metadata.video_width,
            "video_height": file_metadata.video_height,
            "thumbnail_url": file_metadata.thumbnail_url,
            "thumbnail_key": file_metadata.thumbnail_key,
            "playlist_id": file_metadata.playlist_id,
            "user_id": file_metadata.user_id,
            "is_public": file_metadata.is_public if file_metadata.is_public is not None else 0,
            "created_at": file_metadata.created_at.isoformat() if file_metadata.created_at else None
        }
    
    def save(self, metadata: Dict) -> str:
        """Save metadata and return the file ID."""
        if self.use_supabase:
            return self.supabase_store.save_file_metadata(metadata)
        
        db: SQLSession = get_session()
        try:
            file_id = str(uuid.uuid4())
            
            # Parse created_at if it's a string
            created_at = metadata.get("created_at")
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = datetime.now(timezone.utc)
            elif created_at is None:
                created_at = datetime.now(timezone.utc)
            
            file_metadata = FileMetadata(
                id=file_id,
                s3_url=metadata.get("s3_url"),
                s3_key=metadata.get("s3_key"),
                job_id=metadata.get("job_id"),
                file_metadata=metadata.get("metadata", {}),  # Use file_metadata instead of metadata
                video_width=metadata.get("video_width"),
                video_height=metadata.get("video_height"),
                thumbnail_url=metadata.get("thumbnail_url"),
                thumbnail_key=metadata.get("thumbnail_key"),
                playlist_id=metadata.get("playlist_id"),
                user_id=metadata.get("user_id"),
                is_public=metadata.get("is_public", 0),
                created_at=created_at
            )
            
            db.add(file_metadata)
            db.commit()
            db.refresh(file_metadata)
            
            return file_id
        except Exception as e:
            db.rollback()
            print(f"Error saving metadata: {e}")
            raise
        finally:
            db.close()
    
    def get_all(self) -> List[Dict]:
        """Get all saved files."""
        if self.use_supabase:
            return self.supabase_store.get_all_file_metadata()
        
        db: SQLSession = get_session()
        try:
            files = db.query(FileMetadata).order_by(FileMetadata.created_at.desc()).all()
            return [self._to_dict(f) for f in files]
        except Exception as e:
            print(f"Error getting all metadata: {e}")
            return []
        finally:
            db.close()
    
    def get_by_id(self, file_id: str) -> Optional[Dict]:
        """Get a file by ID."""
        if self.use_supabase:
            return self.supabase_store.get_file_metadata_by_id(file_id)
        
        db: SQLSession = get_session()
        try:
            file_metadata = db.query(FileMetadata).filter(FileMetadata.id == file_id).first()
            if file_metadata:
                return self._to_dict(file_metadata)
            return None
        except Exception as e:
            print(f"Error getting metadata by ID: {e}")
            return None
        finally:
            db.close()
    
    def delete(self, file_id: str) -> bool:
        """Delete a file by ID."""
        if self.use_supabase:
            return self.supabase_store.delete_file_metadata(file_id)
        
        db: SQLSession = get_session()
        try:
            file_metadata = db.query(FileMetadata).filter(FileMetadata.id == file_id).first()
            if file_metadata:
                db.delete(file_metadata)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            print(f"Error deleting metadata: {e}")
            return False
        finally:
            db.close()
    
    def update(self, file_id: str, updates: Dict) -> bool:
        """Update metadata for a file."""
        if self.use_supabase:
            return self.supabase_store.update_file_metadata(file_id, updates)
        
        db: SQLSession = get_session()
        try:
            file_metadata = db.query(FileMetadata).filter(FileMetadata.id == file_id).first()
            if not file_metadata:
                return False
            
            # Update fields
            if "s3_url" in updates:
                file_metadata.s3_url = updates["s3_url"]
            if "s3_key" in updates:
                file_metadata.s3_key = updates["s3_key"]
            if "job_id" in updates:
                file_metadata.job_id = updates["job_id"]
            if "metadata" in updates:
                # Merge metadata dictionaries
                if file_metadata.file_metadata:
                    file_metadata.file_metadata.update(updates["metadata"])
                else:
                    file_metadata.file_metadata = updates["metadata"]
            if "video_width" in updates:
                file_metadata.video_width = updates["video_width"]
            if "video_height" in updates:
                file_metadata.video_height = updates["video_height"]
            if "thumbnail_url" in updates:
                file_metadata.thumbnail_url = updates["thumbnail_url"]
            if "thumbnail_key" in updates:
                file_metadata.thumbnail_key = updates["thumbnail_key"]
            if "playlist_id" in updates:
                file_metadata.playlist_id = updates["playlist_id"]
            if "is_public" in updates:
                file_metadata.is_public = updates["is_public"]
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error updating metadata: {e}")
            return False
        finally:
            db.close()
