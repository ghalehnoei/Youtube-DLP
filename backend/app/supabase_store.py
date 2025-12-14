"""
Supabase Data API storage implementation.
Uses Supabase REST API instead of direct database connection.
"""
from typing import List, Dict, Optional
from datetime import datetime, timezone
import uuid
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

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("Warning: supabase-py not installed. Install with: pip install supabase")


class SupabaseStore:
    """Manages data storage using Supabase Data API."""
    
    def __init__(self):
        """Initialize Supabase client."""
        self.client: Optional[Client] = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Supabase client from environment variables."""
        if not SUPABASE_AVAILABLE:
            return
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            return
        
        try:
            self.client = create_client(supabase_url, supabase_key)
            print(f"Supabase client initialized: {supabase_url}")
        except Exception as e:
            print(f"Error initializing Supabase client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Supabase is configured and available."""
        return self.client is not None
    
    # File Metadata methods
    def save_file_metadata(self, metadata: Dict) -> str:
        """Save file metadata and return the file ID."""
        if not self.client:
            raise Exception("Supabase client not initialized")
        
        file_id = str(uuid.uuid4())
        created_at = metadata.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                created_at = datetime.now(timezone.utc)
        elif created_at is None:
            created_at = datetime.now(timezone.utc)
        
        data = {
            "id": file_id,
            "s3_url": metadata.get("s3_url"),
            "s3_key": metadata.get("s3_key"),
            "job_id": metadata.get("job_id"),
            "metadata": metadata.get("metadata", {}),
            "video_width": metadata.get("video_width"),
            "video_height": metadata.get("video_height"),
            "thumbnail_url": metadata.get("thumbnail_url"),
            "thumbnail_key": metadata.get("thumbnail_key"),
            "playlist_id": metadata.get("playlist_id"),
            "user_id": metadata.get("user_id"),
            "is_public": metadata.get("is_public", 0),
            "created_at": created_at.isoformat()
        }
        
        try:
            result = self.client.table("file_metadata").insert(data).execute()
            return file_id
        except Exception as e:
            print(f"Error saving file metadata to Supabase: {e}")
            raise
    
    def get_all_file_metadata(self) -> List[Dict]:
        """Get all file metadata."""
        if not self.client:
            return []
        
        try:
            result = self.client.table("file_metadata").select("*").order("created_at", desc=True).execute()
            files = []
            for row in result.data:
                files.append({
                    "id": row.get("id"),
                    "s3_url": row.get("s3_url"),
                    "s3_key": row.get("s3_key"),
                    "job_id": row.get("job_id"),
                    "metadata": row.get("metadata", {}),
                    "video_width": row.get("video_width"),
                    "video_height": row.get("video_height"),
                    "thumbnail_url": row.get("thumbnail_url"),
                    "thumbnail_key": row.get("thumbnail_key"),
                    "playlist_id": row.get("playlist_id"),
                    "user_id": row.get("user_id"),
                    "is_public": row.get("is_public", 0),
                    "created_at": row.get("created_at")
                })
            return files
        except Exception as e:
            print(f"Error getting file metadata from Supabase: {e}")
            return []
    
    def get_file_metadata_by_id(self, file_id: str) -> Optional[Dict]:
        """Get file metadata by ID."""
        if not self.client:
            return None
        
        try:
            result = self.client.table("file_metadata").select("*").eq("id", file_id).execute()
            if result.data:
                row = result.data[0]
                return {
                    "id": row.get("id"),
                    "s3_url": row.get("s3_url"),
                    "s3_key": row.get("s3_key"),
                    "job_id": row.get("job_id"),
                    "metadata": row.get("metadata", {}),
                    "video_width": row.get("video_width"),
                    "video_height": row.get("video_height"),
                    "thumbnail_url": row.get("thumbnail_url"),
                    "thumbnail_key": row.get("thumbnail_key"),
                    "playlist_id": row.get("playlist_id"),
                    "user_id": row.get("user_id"),
                    "is_public": row.get("is_public", 0),
                    "created_at": row.get("created_at")
                }
            return None
        except Exception as e:
            print(f"Error getting file metadata by ID from Supabase: {e}")
            return None
    
    def update_file_metadata(self, file_id: str, updates: Dict) -> bool:
        """Update file metadata."""
        if not self.client:
            return False
        
        try:
            # Convert updates to Supabase format
            supabase_updates = {}
            if "s3_url" in updates:
                supabase_updates["s3_url"] = updates["s3_url"]
            if "s3_key" in updates:
                supabase_updates["s3_key"] = updates["s3_key"]
            if "job_id" in updates:
                supabase_updates["job_id"] = updates["job_id"]
            if "metadata" in updates:
                # For metadata field, we need to merge if it exists
                existing = self.get_file_metadata_by_id(file_id)
                if existing and existing.get("metadata"):
                    merged = existing["metadata"].copy()
                    merged.update(updates["metadata"])
                    supabase_updates["metadata"] = merged
                else:
                    supabase_updates["metadata"] = updates["metadata"]
            if "video_width" in updates:
                supabase_updates["video_width"] = updates["video_width"]
            if "video_height" in updates:
                supabase_updates["video_height"] = updates["video_height"]
            if "thumbnail_url" in updates:
                supabase_updates["thumbnail_url"] = updates["thumbnail_url"]
            if "thumbnail_key" in updates:
                supabase_updates["thumbnail_key"] = updates["thumbnail_key"]
            if "playlist_id" in updates:
                supabase_updates["playlist_id"] = updates["playlist_id"]
            if "is_public" in updates:
                supabase_updates["is_public"] = updates["is_public"]
            
            if not supabase_updates:
                return False
            
            result = self.client.table("file_metadata").update(supabase_updates).eq("id", file_id).execute()
            return True
        except Exception as e:
            print(f"Error updating file metadata in Supabase: {e}")
            return False
    
    def delete_file_metadata(self, file_id: str) -> bool:
        """Delete file metadata."""
        if not self.client:
            return False
        
        try:
            result = self.client.table("file_metadata").delete().eq("id", file_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting file metadata from Supabase: {e}")
            return False
    
    # Playlist methods
    def create_playlist(self, title: str, description: Optional[str] = None, publish_status: str = "private") -> str:
        """Create a new playlist and return the playlist ID."""
        if not self.client:
            raise Exception("Supabase client not initialized")
        
        playlist_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        data = {
            "id": playlist_id,
            "title": title,
            "description": description or "",
            "publish_status": publish_status,
            "created_at": now,
            "updated_at": now
        }
        
        try:
            result = self.client.table("playlists").insert(data).execute()
            return playlist_id
        except Exception as e:
            print(f"Error creating playlist in Supabase: {e}")
            raise
    
    def get_all_playlists(self) -> List[Dict]:
        """Get all playlists."""
        if not self.client:
            return []
        
        try:
            result = self.client.table("playlists").select("*").order("created_at", desc=True).execute()
            playlists = []
            for row in result.data:
                playlists.append({
                    "id": row.get("id"),
                    "title": row.get("title"),
                    "description": row.get("description", ""),
                    "publish_status": row.get("publish_status"),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at")
                })
            return playlists
        except Exception as e:
            print(f"Error getting playlists from Supabase: {e}")
            return []
    
    def get_playlist_by_id(self, playlist_id: str) -> Optional[Dict]:
        """Get playlist by ID."""
        if not self.client:
            return None
        
        try:
            result = self.client.table("playlists").select("*").eq("id", playlist_id).execute()
            if result.data:
                row = result.data[0]
                return {
                    "id": row.get("id"),
                    "title": row.get("title"),
                    "description": row.get("description", ""),
                    "publish_status": row.get("publish_status"),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at")
                }
            return None
        except Exception as e:
            print(f"Error getting playlist by ID from Supabase: {e}")
            return None
    
    def update_playlist(self, playlist_id: str, updates: Dict) -> bool:
        """Update playlist."""
        if not self.client:
            return False
        
        try:
            supabase_updates = {}
            if "title" in updates:
                supabase_updates["title"] = updates["title"]
            if "description" in updates:
                supabase_updates["description"] = updates["description"]
            if "publish_status" in updates:
                supabase_updates["publish_status"] = updates["publish_status"]
            
            supabase_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            if not supabase_updates:
                return False
            
            result = self.client.table("playlists").update(supabase_updates).eq("id", playlist_id).execute()
            return True
        except Exception as e:
            print(f"Error updating playlist in Supabase: {e}")
            return False
    
    def delete_playlist(self, playlist_id: str) -> bool:
        """Delete playlist."""
        if not self.client:
            return False
        
        try:
            result = self.client.table("playlists").delete().eq("id", playlist_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting playlist from Supabase: {e}")
            return False
    
    # User methods
    def create_user(
        self,
        phone_number: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> str:
        """Create a new user and return the user ID."""
        if not self.client:
            raise Exception("Supabase client not initialized")
        
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        data = {
            "id": user_id,
            "phone_number": phone_number,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "is_active": 1,
            "created_at": now,
            "updated_at": now
        }
        
        try:
            result = self.client.table("users").insert(data).execute()
            return user_id
        except Exception as e:
            print(f"Error creating user in Supabase: {e}")
            raise
    
    def get_user_by_phone(self, phone_number: str) -> Optional[Dict]:
        """Get user by phone number."""
        if not self.client:
            return None
        
        try:
            result = self.client.table("users").select("*").eq("phone_number", phone_number).execute()
            if result.data:
                row = result.data[0]
                return {
                    "id": row.get("id"),
                    "phone_number": row.get("phone_number"),
                    "first_name": row.get("first_name"),
                    "last_name": row.get("last_name"),
                    "email": row.get("email"),
                    "is_active": bool(row.get("is_active", 1)),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at")
                }
            return None
        except Exception as e:
            print(f"Error getting user by phone from Supabase: {e}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        if not self.client:
            return None
        
        try:
            result = self.client.table("users").select("*").eq("id", user_id).execute()
            if result.data:
                row = result.data[0]
                return {
                    "id": row.get("id"),
                    "phone_number": row.get("phone_number"),
                    "first_name": row.get("first_name"),
                    "last_name": row.get("last_name"),
                    "email": row.get("email"),
                    "is_active": bool(row.get("is_active", 1)),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at")
                }
            return None
        except Exception as e:
            print(f"Error getting user by ID from Supabase: {e}")
            return None
    
    def update_user(self, user_id: str, updates: Dict) -> bool:
        """Update user."""
        if not self.client:
            return False
        
        try:
            supabase_updates = {}
            if "first_name" in updates:
                supabase_updates["first_name"] = updates["first_name"]
            if "last_name" in updates:
                supabase_updates["last_name"] = updates["last_name"]
            if "email" in updates:
                supabase_updates["email"] = updates["email"]
            if "is_active" in updates:
                supabase_updates["is_active"] = 1 if updates["is_active"] else 0
            
            supabase_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            if not supabase_updates:
                return False
            
            result = self.client.table("users").update(supabase_updates).eq("id", user_id).execute()
            return True
        except Exception as e:
            print(f"Error updating user in Supabase: {e}")
            return False

