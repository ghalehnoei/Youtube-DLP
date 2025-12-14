"""
Migration script to migrate data from JSON files to database.
Run this script once to migrate existing data.
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from app.database import init_db, get_session, FileMetadata, Playlist
from app.metadata_store import MetadataStore
from app.playlist_store import PlaylistStore

def migrate_metadata():
    """Migrate metadata from JSON to database."""
    backend_dir = Path(__file__).parent
    metadata_file = backend_dir / "metadata.json"
    
    if not metadata_file.exists():
        print("No metadata.json file found. Skipping metadata migration.")
        return
    
    print("Migrating metadata from JSON to database...")
    
    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            print("Invalid metadata.json format. Expected a list.")
            return
        
        db = get_session()
        migrated = 0
        skipped = 0
        
        for item in data:
            try:
                # Check if already exists
                existing = db.query(FileMetadata).filter(FileMetadata.id == item.get("id")).first()
                if existing:
                    print(f"Skipping {item.get('id')} - already exists in database")
                    skipped += 1
                    continue
                
                # Parse created_at
                created_at = item.get("created_at")
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except:
                        created_at = datetime.now(timezone.utc)
                elif created_at is None:
                    created_at = datetime.now(timezone.utc)
                
                file_metadata = FileMetadata(
                    id=item.get("id"),
                    s3_url=item.get("s3_url"),
                    s3_key=item.get("s3_key"),
                    job_id=item.get("job_id"),
                    file_metadata=item.get("metadata", {}),  # Use file_metadata instead of metadata
                    video_width=item.get("video_width"),
                    video_height=item.get("video_height"),
                    thumbnail_url=item.get("thumbnail_url"),
                    thumbnail_key=item.get("thumbnail_key"),
                    playlist_id=item.get("playlist_id"),
                    created_at=created_at
                )
                
                db.add(file_metadata)
                migrated += 1
            except Exception as e:
                print(f"Error migrating item {item.get('id', 'unknown')}: {e}")
                continue
        
        db.commit()
        db.close()
        
        print(f"Metadata migration complete: {migrated} items migrated, {skipped} skipped.")
    except Exception as e:
        print(f"Error reading metadata.json: {e}")


def migrate_playlists():
    """Migrate playlists from JSON to database."""
    backend_dir = Path(__file__).parent
    playlists_file = backend_dir / "playlists.json"
    
    if not playlists_file.exists():
        print("No playlists.json file found. Skipping playlist migration.")
        return
    
    print("Migrating playlists from JSON to database...")
    
    try:
        with open(playlists_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            print("Invalid playlists.json format. Expected a list.")
            return
        
        db = get_session()
        migrated = 0
        skipped = 0
        
        for item in data:
            try:
                # Check if already exists
                existing = db.query(Playlist).filter(Playlist.id == item.get("id")).first()
                if existing:
                    print(f"Skipping playlist {item.get('id')} - already exists in database")
                    skipped += 1
                    continue
                
                # Parse dates
                created_at = item.get("created_at")
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except:
                        created_at = datetime.now(timezone.utc)
                else:
                    created_at = datetime.now(timezone.utc)
                
                updated_at = item.get("updated_at")
                if isinstance(updated_at, str):
                    try:
                        updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    except:
                        updated_at = datetime.now(timezone.utc)
                else:
                    updated_at = datetime.now(timezone.utc)
                
                playlist = Playlist(
                    id=item.get("id"),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    publish_status=item.get("publish_status", "private"),
                    created_at=created_at,
                    updated_at=updated_at
                )
                
                db.add(playlist)
                migrated += 1
            except Exception as e:
                print(f"Error migrating playlist {item.get('id', 'unknown')}: {e}")
                continue
        
        db.commit()
        db.close()
        
        print(f"Playlist migration complete: {migrated} playlists migrated, {skipped} skipped.")
    except Exception as e:
        print(f"Error reading playlists.json: {e}")


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    
    print("\nStarting migration...")
    migrate_metadata()
    print()
    migrate_playlists()
    
    print("\nMigration complete!")

