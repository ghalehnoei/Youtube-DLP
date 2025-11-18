"""
Playlist storage using JSON file.
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import uuid


class PlaylistStore:
    """Manages playlist storage in JSON file."""
    
    def __init__(self, storage_file: str = "playlists.json"):
        # Store in backend directory
        backend_dir = Path(__file__).parent.parent
        self.storage_file = backend_dir / storage_file
        self._ensure_storage_file()
    
    def _ensure_storage_file(self):
        """Ensure the storage file exists."""
        if not self.storage_file.exists():
            self._write_data([])
    
    def _read_data(self) -> List[Dict]:
        """Read data from JSON file."""
        try:
            if self.storage_file.exists():
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading playlist file: {e}")
            return []
    
    def _write_data(self, data: List[Dict]):
        """Write data to JSON file."""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error writing playlist file: {e}")
            raise
    
    def create(self, title: str, description: Optional[str] = None, publish_status: str = "private") -> str:
        """Create a new playlist and return the playlist ID."""
        data = self._read_data()
        
        playlist_id = str(uuid.uuid4())
        playlist_data = {
            "id": playlist_id,
            "title": title,
            "description": description or "",
            "publish_status": publish_status,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        data.append(playlist_data)
        self._write_data(data)
        
        return playlist_id
    
    def get_all(self) -> List[Dict]:
        """Get all playlists."""
        return self._read_data()
    
    def get_by_id(self, playlist_id: str) -> Optional[Dict]:
        """Get a playlist by ID."""
        data = self._read_data()
        for playlist in data:
            if playlist.get("id") == playlist_id:
                return playlist
        return None
    
    def update(self, playlist_id: str, updates: Dict) -> bool:
        """Update playlist data."""
        data = self._read_data()
        for playlist in data:
            if playlist.get("id") == playlist_id:
                playlist.update(updates)
                playlist["updated_at"] = datetime.now().isoformat()
                self._write_data(data)
                return True
        return False
    
    def delete(self, playlist_id: str) -> bool:
        """Delete a playlist by ID."""
        data = self._read_data()
        original_length = len(data)
        data = [p for p in data if p.get("id") != playlist_id]
        
        if len(data) < original_length:
            self._write_data(data)
            return True
        return False

