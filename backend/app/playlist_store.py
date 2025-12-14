"""
Playlist storage using database (PostgreSQL, MySQL, or SQLite) or Supabase Data API.
"""
from typing import List, Dict, Optional
from datetime import datetime, timezone
import uuid
from app.database import get_session, Playlist
from sqlalchemy.orm import Session as SQLSession
from app.supabase_store import SupabaseStore


class PlaylistStore:
    """Manages playlist storage in database or Supabase."""
    
    def __init__(self):
        """Initialize playlist store."""
        self.supabase_store = SupabaseStore()
        self.use_supabase = self.supabase_store.is_available()
        if self.use_supabase:
            print("Using Supabase Data API for playlist storage")
        else:
            print("Using local database (SQLite/PostgreSQL/MySQL) for playlist storage")
    
    def _to_dict(self, playlist: Playlist) -> Dict:
        """Convert database model to dictionary."""
        return {
            "id": playlist.id,
            "title": playlist.title,
            "description": playlist.description or "",
            "publish_status": playlist.publish_status,
            "created_at": playlist.created_at.isoformat() if playlist.created_at else None,
            "updated_at": playlist.updated_at.isoformat() if playlist.updated_at else None
        }
    
    def create(self, title: str, description: Optional[str] = None, publish_status: str = "private") -> str:
        """Create a new playlist and return the playlist ID."""
        if self.use_supabase:
            return self.supabase_store.create_playlist(title, description, publish_status)
        
        db: SQLSession = get_session()
        try:
            playlist_id = str(uuid.uuid4())
            playlist = Playlist(
                id=playlist_id,
                title=title,
                description=description or "",
                publish_status=publish_status,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            db.add(playlist)
            db.commit()
            db.refresh(playlist)
            
            return playlist_id
        except Exception as e:
            db.rollback()
            print(f"Error creating playlist: {e}")
            raise
        finally:
            db.close()
    
    def get_all(self) -> List[Dict]:
        """Get all playlists."""
        if self.use_supabase:
            return self.supabase_store.get_all_playlists()
        
        db: SQLSession = get_session()
        try:
            playlists = db.query(Playlist).order_by(Playlist.created_at.desc()).all()
            return [self._to_dict(p) for p in playlists]
        except Exception as e:
            print(f"Error getting all playlists: {e}")
            return []
        finally:
            db.close()
    
    def get_by_id(self, playlist_id: str) -> Optional[Dict]:
        """Get a playlist by ID."""
        if self.use_supabase:
            return self.supabase_store.get_playlist_by_id(playlist_id)
        
        db: SQLSession = get_session()
        try:
            playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
            if playlist:
                return self._to_dict(playlist)
            return None
        except Exception as e:
            print(f"Error getting playlist by ID: {e}")
            return None
        finally:
            db.close()
    
    def update(self, playlist_id: str, updates: Dict) -> bool:
        """Update playlist data."""
        if self.use_supabase:
            return self.supabase_store.update_playlist(playlist_id, updates)
        
        db: SQLSession = get_session()
        try:
            playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
            if not playlist:
                return False
            
            if "title" in updates:
                playlist.title = updates["title"]
            if "description" in updates:
                playlist.description = updates["description"]
            if "publish_status" in updates:
                playlist.publish_status = updates["publish_status"]
            
            playlist.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error updating playlist: {e}")
            return False
        finally:
            db.close()
    
    def delete(self, playlist_id: str) -> bool:
        """Delete a playlist by ID."""
        if self.use_supabase:
            return self.supabase_store.delete_playlist(playlist_id)
        
        db: SQLSession = get_session()
        try:
            playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
            if playlist:
                db.delete(playlist)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            print(f"Error deleting playlist: {e}")
            return False
        finally:
            db.close()
