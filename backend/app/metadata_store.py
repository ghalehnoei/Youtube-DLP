"""
Metadata storage using JSON file.
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import uuid


class MetadataStore:
    """Manages file metadata storage in JSON file."""
    
    def __init__(self, storage_file: str = "metadata.json"):
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
            print(f"Error reading metadata file: {e}")
            return []
    
    def _write_data(self, data: List[Dict]):
        """Write data to JSON file."""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error writing metadata file: {e}")
            raise
    
    def save(self, metadata: Dict) -> str:
        """Save metadata and return the file ID."""
        data = self._read_data()
        
        file_id = str(uuid.uuid4())
        file_data = {
            "id": file_id,
            "s3_url": metadata.get("s3_url"),  # Keep for backward compatibility
            "s3_key": metadata.get("s3_key"),  # Store S3 key for generating fresh URLs
            "job_id": metadata.get("job_id"),
            "metadata": metadata.get("metadata", {}),
            "video_width": metadata.get("video_width"),
            "video_height": metadata.get("video_height"),
            "thumbnail_url": metadata.get("thumbnail_url"),
            "thumbnail_key": metadata.get("thumbnail_key"),  # Store thumbnail key too
            "playlist_id": metadata.get("playlist_id"),  # Store playlist ID
            "created_at": metadata.get("created_at", datetime.now().isoformat())
        }
        
        data.append(file_data)
        self._write_data(data)
        
        return file_id
    
    def get_all(self) -> List[Dict]:
        """Get all saved files."""
        return self._read_data()
    
    def get_by_id(self, file_id: str) -> Optional[Dict]:
        """Get a file by ID."""
        data = self._read_data()
        for file in data:
            if file.get("id") == file_id:
                return file
        return None
    
    def delete(self, file_id: str) -> bool:
        """Delete a file by ID."""
        data = self._read_data()
        original_length = len(data)
        data = [f for f in data if f.get("id") != file_id]
        
        if len(data) < original_length:
            self._write_data(data)
            return True
        return False
    
    def update(self, file_id: str, updates: Dict) -> bool:
        """Update metadata for a file."""
        data = self._read_data()
        for file in data:
            if file.get("id") == file_id:
                file.update(updates)
                self._write_data(data)
                return True
        return False

