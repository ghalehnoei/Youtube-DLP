"""
Main FastAPI application for video download and S3 upload service.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, RedirectResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import asyncio
import httpx
import os
from pathlib import Path
from contextlib import asynccontextmanager

from app.downloader import VideoDownloader
from app.uploader import S3Uploader
from app.splitter import VideoSplitter
from app.config import settings
from app.job_manager import JobManager
from app.validators import validate_url
from app.metadata_store import MetadataStore
from app.thumbnail_generator import ThumbnailGenerator
from app.video_converter import VideoConverter
from app.playlist_store import PlaylistStore
from app.storyboard_generator import StoryboardGenerator
from fastapi import UploadFile, File

# Global job manager
job_manager = JobManager()

# Global metadata store
metadata_store = MetadataStore()

# Global playlist store
playlist_store = PlaylistStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("Starting application...")
    # Store the main event loop for worker thread notifications
    loop = asyncio.get_event_loop()
    job_manager.set_main_loop(loop)
    yield
    # Shutdown
    print("Shutting down application...")
    job_manager.cleanup_all_jobs()


app = FastAPI(
    title="Youtube Downloader",
    description="Download videos Youtube Videos",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DownloadRequest(BaseModel):
    url: HttpUrl
    format: Optional[str] = None  # Optional format selection


class SplitRequest(BaseModel):
    s3_url: str  # S3 URL of the video to split
    start_time: float  # Start time in seconds
    end_time: Optional[float] = None  # End time in seconds (optional)
    convert_to_horizontal: Optional[bool] = False  # Convert vertical video to horizontal
    original_metadata: Optional[Dict[str, Any]] = None  # Original video metadata to preserve


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class UploadResponse(BaseModel):
    job_id: str
    status: str
    message: str


class StoryboardRequest(BaseModel):
    video_url: str  # Can be S3 URL, local file path, or HTTP URL
    threshold: Optional[float] = 0.3  # Scene change detection threshold (0.0-1.0)
    thumbnail_width: Optional[int] = 320
    thumbnail_height: Optional[int] = 180


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Video Download & S3 Upload Service"}


@app.post("/api/download", response_model=JobResponse)
async def start_download(request: DownloadRequest):
    """
    Start a video download job.
    Returns a job_id that can be used to track progress via WebSocket.
    """
    url_str = str(request.url)
    
    # Validate URL
    is_valid, error_msg = validate_url(url_str)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_msg or "Invalid URL"
        )
    
    # Validate S3 configuration
    if not settings.s3_bucket:
        raise HTTPException(
            status_code=500,
            detail="S3 bucket not configured. Please set S3_BUCKET environment variable."
        )
    
    job_id = str(uuid.uuid4())
    
    # Create job
    job_manager.create_job(job_id, url_str)
    
    # Start download and upload process in background
    task = asyncio.create_task(process_video(
        job_id, 
        url_str, 
        request.format
    ))
    job_manager.set_job_task(job_id, task)
    
    return JobResponse(
        job_id=job_id,
        status="started",
        message="Download job started. Connect to WebSocket to track progress."
    )


@app.post("/api/upload", response_model=UploadResponse)
async def start_upload(file: UploadFile = File(...)):
    """
    Start a video upload and conversion job.
    Uploads a local file, converts it to 1920x1080, and uploads to S3.
    Returns a job_id that can be used to track progress via WebSocket.
    """
    # Validate S3 configuration
    if not settings.s3_bucket:
        raise HTTPException(
            status_code=500,
            detail="S3 bucket not configured. Please set S3_BUCKET environment variable."
        )
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('video/'):
        raise HTTPException(
            status_code=400,
            detail="File must be a video"
        )
    
    job_id = str(uuid.uuid4())
    
    # Create job
    job_manager.create_job(job_id, f"upload:{file.filename}")
    
    # Save uploaded file temporarily
    temp_dir = Path(settings.temp_dir) / "uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file_path = temp_dir / f"upload_{job_id}_{file.filename}"
    
    try:
        # Save uploaded file
        with open(temp_file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Start conversion and upload process in background
        task = asyncio.create_task(process_upload(
            job_id,
            str(temp_file_path),
            file.filename
        ))
        job_manager.set_job_task(job_id, task)
        
        return UploadResponse(
            job_id=job_id,
            status="started",
            message="Upload job started. Connect to WebSocket to track progress."
        )
    except Exception as e:
        # Clean up temp file on error
        if temp_file_path.exists():
            try:
                os.remove(temp_file_path)
            except:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded file: {str(e)}"
        )


@app.post("/api/storyboard", response_model=JobResponse)
async def start_storyboard(request: StoryboardRequest):
    """
    Start a storyboard generation job.
    Detects scene changes in a video and extracts frames to create a storyboard.
    Returns a job_id that can be used to track progress via WebSocket.
    """
    job_id = str(uuid.uuid4())
    
    # Create job
    job_manager.create_job(job_id, f"storyboard:{request.video_url}")
    
    # Start storyboard generation in background
    task = asyncio.create_task(process_storyboard(
        job_id,
        request.video_url,
        request.threshold,
        request.thumbnail_width,
        request.thumbnail_height
    ))
    job_manager.set_job_task(job_id, task)
    
    return JobResponse(
        job_id=job_id,
        status="started",
        message="Storyboard generation started. Connect to WebSocket to track progress."
    )


async def process_storyboard(
    job_id: str,
    video_url: str,
    threshold: float = 0.3,
    thumbnail_width: int = 320,
    thumbnail_height: int = 180
):
    """
    Process storyboard generation: detect scene changes and extract frames.
    """
    generator = StoryboardGenerator()
    
    try:
        # Check if cancelled before starting
        if job_manager.is_cancelled(job_id):
            return
        
        # Notify start
        job_manager.update_job_status(job_id, "storyboard", 0, "Starting storyboard generation...")
        
        # Create output directory
        output_dir = Path(settings.temp_dir) / "storyboards" / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate storyboard
        result = await generator.generate_storyboard(
            video_path=video_url,
            output_dir=str(output_dir),
            threshold=threshold,
            thumbnail_width=thumbnail_width,
            thumbnail_height=thumbnail_height,
            progress_callback=lambda p, s: job_manager.update_job_status(
                job_id, "storyboard", p, s
            ),
            job_id=job_id
        )
        
        if result:
            uploader = S3Uploader()
            
            # Extract keywords for each frame
            try:
                from app.keyword_extractor import KeywordExtractor
                # Use None to get backend from settings
                keyword_extractor = KeywordExtractor(backend=None)
                
                job_manager.update_job_status(job_id, "storyboard", 80, "Extracting keywords from frames...")
                
                # Extract keywords for all frames
                image_paths = [frame['image_path'] for frame in result['frames']]
                keyword_results = await keyword_extractor.extract_keywords_batch(
                    image_paths,
                    max_keywords=None,  # Use default from settings
                    progress_callback=lambda p, s: job_manager.update_job_status(
                        job_id, "storyboard", 80 + int(p * 0.05), s
                    )
                )
                
                # Add keywords to frames
                for frame, keyword_result in zip(result['frames'], keyword_results):
                    frame['keywords'] = keyword_result['keywords']
                
                print(f"✅ Extracted keywords for {len(keyword_results)} frames")
            except Exception as e:
                print(f"Warning: Could not extract keywords: {e}")
                import traceback
                traceback.print_exc()
                # Continue without keywords
                for frame in result['frames']:
                    frame['keywords'] = []
            
            # Upload frame images to S3 first (so we can update HTML with S3 URLs)
            uploaded_frames = []
            frame_count = len(result['frames'])
            for idx, frame in enumerate(result['frames']):
                try:
                    frame_s3_url = await uploader.upload_storyboard_frame(
                        frame['image_path'],
                        job_id,
                        frame['index'],
                        lambda p, s: job_manager.update_job_status(
                            job_id, "storyboard", 85 + ((idx / frame_count) * 0.05), 
                            f"Uploading frame {idx + 1}/{frame_count}..."
                        )
                    )
                    if frame_s3_url:
                        frame_s3_key = uploader.extract_s3_key_from_url(frame_s3_url)
                        uploaded_frames.append({
                            'index': frame['index'],
                            'timestamp': frame['timestamp'],
                            'time_str': frame['time_str'],
                            'image_path': frame['image_path'],  # Keep local path as fallback
                            'image_s3_key': frame_s3_key,  # Store only S3 key, not URL (URLs expire)
                            'keywords': frame.get('keywords', [])  # Include keywords
                        })
                    else:
                        # Keep original frame if upload failed
                        uploaded_frames.append({
                            'index': frame['index'],
                            'timestamp': frame['timestamp'],
                            'time_str': frame['time_str'],
                            'image_path': frame['image_path'],
                            'keywords': frame.get('keywords', [])  # Include keywords even if upload failed
                        })
                except Exception as e:
                    print(f"Warning: Could not upload frame {frame['index']}: {e}")
                    # Keep original frame if upload failed
                    uploaded_frames.append(frame)
            
            # Note: We don't update HTML with S3 URLs anymore since presigned URLs expire
            # The HTML will use API endpoints which generate fresh presigned URLs on-demand
            html_path_to_upload = result['html_path']
            
            # Upload storyboard HTML to S3
            html_s3_url = None
            html_s3_key = None
            try:
                job_manager.update_job_status(job_id, "storyboard", 90, "Uploading storyboard HTML to S3...")
                html_s3_url = await uploader.upload_storyboard_html(
                    html_path_to_upload,
                    job_id,
                    lambda p, s: job_manager.update_job_status(job_id, "storyboard", 90 + (p * 0.05), s)
                )
                if html_s3_url:
                    html_s3_key = uploader.extract_s3_key_from_url(html_s3_url)
            except Exception as e:
                print(f"Warning: Could not upload storyboard HTML: {e}")
            
            
            # Store storyboard result in job metadata (including S3 URLs)
            metadata = {
                'html_path': result['html_path'],  # Keep local path as fallback
                'html_s3_url': html_s3_url,
                'html_s3_key': html_s3_key,
                'frames_dir': result['frames_dir'],
                'frame_count': result['frame_count'],
                'frames': uploaded_frames,  # Store frames with S3 URLs
                'video_url': video_url
            }
            job_manager.set_job_metadata(job_id, metadata)
            
            # Complete job with HTML path (use S3 URL if available, otherwise local path)
            complete_url = html_s3_url if html_s3_url else result['html_path']
            job_manager.complete_job(job_id, complete_url, metadata)
            
            # Also store frames in parent job metadata if this is a storyboard job
            # Find parent job by checking if any job has this storyboard_job_id
            try:
                files = metadata_store.get_all()
                updated_count = 0
                for file in files:
                    file_metadata = file.get('metadata', {})
                    if file_metadata.get('storyboard_job_id') == job_id:
                        # Found parent file, update its metadata with storyboard frames
                        # Get the current metadata and merge with new storyboard data
                        current_metadata = file.get('metadata', {})
                        current_metadata = current_metadata.copy() if current_metadata else {}
                        current_metadata['frames'] = uploaded_frames
                        current_metadata['storyboard_html_s3_url'] = html_s3_url
                        current_metadata['storyboard_html_s3_key'] = html_s3_key
                        current_metadata['storyboard_completed'] = True
                        current_metadata['storyboard_frame_count'] = len(uploaded_frames)
                        if metadata_store.update(file.get('id'), {'metadata': current_metadata}):
                            updated_count += 1
                            print(f"✅ Updated parent file {file.get('id')} with storyboard frames ({len(uploaded_frames)} frames)")
                            # Verify the update worked
                            updated_file = metadata_store.get_by_id(file.get('id'))
                            if updated_file:
                                updated_metadata = updated_file.get('metadata', {})
                                if 'frames' in updated_metadata:
                                    print(f"✅ Verified: Parent file now has {len(updated_metadata.get('frames', []))} frames in metadata")
                                else:
                                    print(f"❌ Warning: Parent file update may have failed - frames not found after update")
                        else:
                            print(f"❌ Failed to update parent file {file.get('id')}")
                
                if updated_count == 0:
                    print(f"⚠️ Warning: No parent file found with storyboard_job_id={job_id}")
                    print(f"   Searched {len(files)} files")
                    # Debug: print all storyboard_job_ids found
                    found_job_ids = [f.get('metadata', {}).get('storyboard_job_id') for f in files if f.get('metadata', {}).get('storyboard_job_id')]
                    print(f"   Found storyboard_job_ids: {found_job_ids[:5]}...")  # Show first 5
                
                # Also check if there's a parent job in job manager
                # Find all jobs and check if any have this storyboard_job_id
                with job_manager._lock:
                    all_jobs = list(job_manager.jobs.values())
                for job in all_jobs:
                    job_metadata = job.metadata if hasattr(job, 'metadata') else {}
                    if job_metadata.get('storyboard_job_id') == job_id:
                        # Update parent job metadata with frames
                        job_metadata = job_metadata.copy()
                        job_metadata['frames'] = uploaded_frames
                        job_metadata['storyboard_html_s3_url'] = html_s3_url
                        job_metadata['storyboard_html_s3_key'] = html_s3_key
                        job_manager.set_job_metadata(job.job_id, job_metadata)
                        print(f"Updated parent job {job.job_id} with storyboard frames ({len(uploaded_frames)} frames)")
                        break
            except Exception as e:
                print(f"Warning: Could not update parent job/file with storyboard frames: {e}")
                import traceback
                traceback.print_exc()
            
            # Clean up local files after successful upload
            if html_s3_url and html_s3_key:
                try:
                    # Clean up HTML file
                    if os.path.exists(result['html_path']):
                        os.remove(result['html_path'])
                    # Clean up frame images that were successfully uploaded
                    uploaded_frame_indices = {f.get('index') for f in uploaded_frames if f.get('image_s3_url')}
                    for frame in result['frames']:
                        if frame['index'] in uploaded_frame_indices:
                            if os.path.exists(frame['image_path']):
                                try:
                                    os.remove(frame['image_path'])
                                except:
                                    pass
                    # Try to remove empty directories
                    try:
                        if os.path.exists(result['frames_dir']) and not os.listdir(result['frames_dir']):
                            os.rmdir(result['frames_dir'])
                        if os.path.exists(str(Path(result['html_path']).parent)) and not os.listdir(str(Path(result['html_path']).parent)):
                            os.rmdir(str(Path(result['html_path']).parent))
                    except:
                        pass
                except Exception as e:
                    print(f"Warning: Could not clean up local storyboard files: {e}")
        else:
            job_manager.update_job_status(
                job_id, "error", 0, "Storyboard generation failed"
            )
    
    except Exception as e:
        error_str = str(e) if e else "Unknown error"
        job_manager.update_job_status(
            job_id, "error", 0, f"Storyboard generation error: {error_str}"
        )
        import traceback
        traceback.print_exc()


@app.get("/api/storyboard/{job_id}/status")
async def get_storyboard_status(job_id: str):
    """Get storyboard job status and frame count."""
    status = job_manager.get_job_status(job_id)
    
    # If job not found in job manager, check saved files
    if not status:
        files = metadata_store.get_all()
        for file in files:
            file_metadata = file.get('metadata', {})
            if file_metadata.get('storyboard_job_id') == job_id:
                frames_count = len(file_metadata.get('frames', []))
                return {
                    "job_id": job_id,
                    "status": "complete" if frames_count > 0 else "pending",
                    "frame_count": frames_count,
                    "has_frames": frames_count > 0,
                    "parent_file_id": file.get('id'),
                    "parent_job_id": file.get('job_id')
                }
            if file.get('job_id') == job_id:
                frames_count = len(file_metadata.get('frames', []))
                return {
                    "job_id": job_id,
                    "status": "complete" if frames_count > 0 else "pending",
                    "frame_count": frames_count,
                    "has_frames": frames_count > 0
                }
        return {
            "job_id": job_id,
            "status": "not_found",
            "frame_count": 0,
            "has_frames": False
        }
    
    metadata = status.get('metadata', {})
    frames_count = len(metadata.get('frames', []))
    return {
        "job_id": job_id,
        "status": status.get('stage', 'unknown'),
        "frame_count": frames_count,
        "has_frames": frames_count > 0,
        "percent": status.get('percent', 0)
    }


@app.get("/api/storyboard/{job_id}/html")
async def get_storyboard_html(job_id: str):
    """Serve the generated storyboard HTML file."""
    status = job_manager.get_job_status(job_id)
    
    # If job not found in job manager, try to find it in saved files metadata
    if not status:
        files = metadata_store.get_all()
        for file in files:
            file_metadata = file.get('metadata', {})
            if file_metadata.get('storyboard_job_id') == job_id:
                # Check if HTML S3 URL is in metadata
                html_s3_url = file_metadata.get('storyboard_html_s3_url')
                if html_s3_url:
                    return RedirectResponse(url=html_s3_url)
                break
    
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    metadata = status.get('metadata', {})
    if not metadata:
        raise HTTPException(status_code=404, detail="Storyboard not found or not generated yet")
    
    # Prefer S3 URL if available, otherwise use local path
    html_s3_url = metadata.get('html_s3_url')
    if html_s3_url:
        # Redirect to S3 URL
        return RedirectResponse(url=html_s3_url)
    
    html_path = metadata.get('html_path')
    if not html_path or not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="Storyboard HTML file not found")
    
    # Read and return HTML file
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read storyboard HTML: {str(e)}")


@app.get("/api/storyboard/{job_id}/frames")
async def get_storyboard_frames(job_id: str):
    """Get all storyboard frames for a video job."""
    status = job_manager.get_job_status(job_id)
    
    # If job not found in job manager, try to find it in saved files metadata
    if not status:
        # Try to find the job in saved files by checking if this is a storyboard job ID
        # or if we can find a parent job that references this storyboard job
        files = metadata_store.get_all()
        for file in files:
            file_metadata = file.get('metadata', {})
            # Check if this file has a storyboard_job_id matching the requested job_id
            if file_metadata.get('storyboard_job_id') == job_id:
                # Found parent job, check if frames are in parent metadata
                if 'frames' in file_metadata and file_metadata['frames']:
                    frames = file_metadata['frames']
                    uploader = S3Uploader()
                    # Filter out invalid frames and generate fresh presigned URLs
                    valid_frames = []
                    for idx, frame in enumerate(frames):
                        if not isinstance(frame, dict):
                            continue
                        frame_index = frame.get('index', idx)
                        # Generate fresh presigned URL from S3 key if available
                        image_url = f"/api/storyboard/{job_id}/frame/{frame_index}"
                        s3_key = frame.get('image_s3_key')
                        if s3_key:
                            fresh_url = uploader.generate_presigned_url_for_frame(s3_key)
                            if fresh_url:
                                image_url = fresh_url
                        valid_frames.append({
                            "index": frame_index,
                            "timestamp": frame.get('timestamp', 0),
                            "time_str": frame.get('time_str', '00:00'),
                            "image_url": image_url,
                            "keywords": frame.get('keywords', [])
                        })
                    if valid_frames:
                        return {"frames": valid_frames}
                # If frames not found but storyboard_job_id exists, storyboard might still be generating
                # Return empty array instead of 404
                return {"frames": []}
            # Check if this file's job_id matches and has frames
            if file.get('job_id') == job_id and 'frames' in file_metadata and file_metadata['frames']:
                frames = file_metadata['frames']
                uploader = S3Uploader()
                valid_frames = []
                for idx, frame in enumerate(frames):
                    if not isinstance(frame, dict):
                        continue
                    frame_index = frame.get('index', idx)
                    # Generate fresh presigned URL from S3 key if available
                    image_url = f"/api/storyboard/{job_id}/frame/{frame_index}"
                    s3_key = frame.get('image_s3_key')
                    if s3_key:
                        fresh_url = uploader.generate_presigned_url_for_frame(s3_key)
                        if fresh_url:
                            image_url = fresh_url
                    valid_frames.append({
                        "index": frame_index,
                        "timestamp": frame.get('timestamp', 0),
                        "time_str": frame.get('time_str', '00:00'),
                        "image_url": image_url,
                        "keywords": frame.get('keywords', [])
                    })
                if valid_frames:
                    return {"frames": valid_frames}
        
        # If we found a file with this storyboard_job_id but no frames, return empty array
        # (storyboard might still be generating)
        files = metadata_store.get_all()
        for file in files:
            file_metadata = file.get('metadata', {})
            if file_metadata.get('storyboard_job_id') == job_id or file.get('job_id') == job_id:
                return {"frames": []}
        
        raise HTTPException(status_code=404, detail="Job not found")
    
    metadata = status.get('metadata', {})
    if not metadata or 'frames' not in metadata:
        # Try to get storyboard_job_id from metadata
        storyboard_job_id = metadata.get('storyboard_job_id') if metadata else None
        if storyboard_job_id:
            # Get frames from storyboard job
            storyboard_status = job_manager.get_job_status(storyboard_job_id)
            if storyboard_status:
                storyboard_metadata = storyboard_status.get('metadata', {})
                if storyboard_metadata and 'frames' in storyboard_metadata:
                    frames = storyboard_metadata['frames']
                    uploader = S3Uploader()
                    # Generate fresh presigned URLs for frames
                    valid_frames = []
                    for idx, frame in enumerate(frames):
                        if not isinstance(frame, dict):
                            continue
                        frame_index = frame.get('index', idx)
                        # Generate fresh presigned URL from S3 key if available
                        image_url = f"/api/storyboard/{storyboard_job_id}/frame/{frame_index}"
                        s3_key = frame.get('image_s3_key')
                        if s3_key:
                            fresh_url = uploader.generate_presigned_url_for_frame(s3_key)
                            if fresh_url:
                                image_url = fresh_url
                        valid_frames.append({
                            "index": frame_index,
                            "timestamp": frame.get('timestamp', 0),
                            "time_str": frame.get('time_str', '00:00'),
                            "image_url": image_url,
                            "keywords": frame.get('keywords', [])
                        })
                    return {"frames": valid_frames}
            else:
                # Storyboard job not in memory, try to find in saved files
                files = metadata_store.get_all()
                for file in files:
                    file_metadata = file.get('metadata', {})
                    if file_metadata.get('storyboard_job_id') == storyboard_job_id:
                        if 'frames' in file_metadata and file_metadata['frames']:
                            frames = file_metadata['frames']
                            uploader = S3Uploader()
                            valid_frames = []
                            for idx, frame in enumerate(frames):
                                if not isinstance(frame, dict):
                                    continue
                                frame_index = frame.get('index', idx)
                                # Generate fresh presigned URL from S3 key if available
                                image_url = f"/api/storyboard/{storyboard_job_id}/frame/{frame_index}"
                                s3_key = frame.get('image_s3_key')
                                if s3_key:
                                    fresh_url = uploader.generate_presigned_url_for_frame(s3_key)
                                    if fresh_url:
                                        image_url = fresh_url
                                valid_frames.append({
                                    "index": frame_index,
                                    "timestamp": frame.get('timestamp', 0),
                                    "time_str": frame.get('time_str', '00:00'),
                                    "image_url": image_url,
                                    "keywords": frame.get('keywords', [])
                                })
                            if valid_frames:
                                return {"frames": valid_frames}
                        # If storyboard_job_id exists but no frames, storyboard might still be generating
                        return {"frames": []}
        # If we have a storyboard_job_id but no frames found, return empty array (might still be generating)
        if storyboard_job_id:
            return {"frames": []}
        raise HTTPException(status_code=404, detail="Storyboard frames not found")
    
    frames = metadata['frames']
    uploader = S3Uploader()
    # Generate fresh presigned URLs for frames
    valid_frames = []
    for idx, frame in enumerate(frames):
        if not isinstance(frame, dict):
            continue
        frame_index = frame.get('index', idx)
        # Generate fresh presigned URL from S3 key if available
        image_url = f"/api/storyboard/{job_id}/frame/{frame_index}"
        s3_key = frame.get('image_s3_key')
        if s3_key:
            fresh_url = uploader.generate_presigned_url_for_frame(s3_key)
            if fresh_url:
                image_url = fresh_url
        valid_frames.append({
            "index": frame_index,
            "timestamp": frame.get('timestamp', 0),
            "time_str": frame.get('time_str', '00:00'),
            "image_url": image_url,
            "keywords": frame.get('keywords', [])
        })
    return {"frames": valid_frames}


@app.get("/api/storyboard/{job_id}/frame/{frame_index}")
async def get_storyboard_frame(job_id: str, frame_index: int):
    """Serve a storyboard frame image."""
    status = job_manager.get_job_status(job_id)
    frames = None
    metadata = {}
    
    # If job not found in job manager, try to find it in saved files metadata
    if not status:
        files = metadata_store.get_all()
        for file in files:
            file_metadata = file.get('metadata', {})
            # Check if this file has a storyboard_job_id matching the requested job_id
            if file_metadata.get('storyboard_job_id') == job_id:
                if 'frames' in file_metadata:
                    frames = file_metadata['frames']
                    metadata = file_metadata
                    break
            # Check if this file's job_id matches and has frames
            if file.get('job_id') == job_id and 'frames' in file_metadata:
                frames = file_metadata['frames']
                metadata = file_metadata
                break
        
        if not frames:
            raise HTTPException(status_code=404, detail="Job not found")
    else:
        metadata = status.get('metadata', {})
        if 'frames' in metadata:
            frames = metadata['frames']
        else:
            # Try to get storyboard_job_id from metadata
            storyboard_job_id = metadata.get('storyboard_job_id')
            if storyboard_job_id:
                # Try to get from storyboard job
                storyboard_status = job_manager.get_job_status(storyboard_job_id)
                if storyboard_status:
                    storyboard_metadata = storyboard_status.get('metadata', {})
                    if 'frames' in storyboard_metadata:
                        frames = storyboard_metadata['frames']
                else:
                    # Try saved files
                    files = metadata_store.get_all()
                    for file in files:
                        file_metadata = file.get('metadata', {})
                        if file_metadata.get('storyboard_job_id') == storyboard_job_id:
                            if 'frames' in file_metadata:
                                frames = file_metadata['frames']
                                break
    
    if not frames:
        raise HTTPException(status_code=404, detail="Storyboard frames not found")
    
    if frame_index < 0 or frame_index >= len(frames):
        raise HTTPException(status_code=404, detail="Frame index out of range")
    
    frame = frames[frame_index]
    
    # Generate fresh presigned URL from S3 key if available
    uploader = S3Uploader()
    s3_key = frame.get('image_s3_key')
    if s3_key:
        fresh_url = uploader.generate_presigned_url_for_frame(s3_key)
        if fresh_url:
            # Redirect to fresh presigned URL
            return RedirectResponse(url=fresh_url)
    
    # Fallback to local path if available
    frame_path = frame.get('image_path')
    if frame_path and os.path.exists(frame_path):
        # Return image file
        from fastapi.responses import FileResponse
        return FileResponse(
            frame_path,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
            }
        )
    
    raise HTTPException(status_code=404, detail="Frame image not found")


async def process_video(
    job_id: str, 
    url: str, 
    format_option: Optional[str] = None
):
    """
    Main processing function: Download video and upload to S3.
    """
    downloader = VideoDownloader()
    uploader = S3Uploader()
    
    try:
        # Check if cancelled before starting
        if job_manager.is_cancelled(job_id):
            return
        
        # Notify download start
        job_manager.update_job_status(job_id, "download", 0, "Starting download...")
        
        # Download video with cancellation check
        try:
            file_path = await downloader.download(
                url=url,
                format_option=format_option,
                progress_callback=lambda p, s, e: (
                    job_manager.update_job_status(
                        job_id, "download", p, f"Downloading... {s}", speed=s, eta=e
                    ) if not job_manager.is_cancelled(job_id) else None
                ),
                cancellation_check=lambda: job_manager.is_cancelled(job_id),
                job_id=job_id
            )
        except asyncio.CancelledError:
            job_manager.update_job_status(job_id, "cancelled", 0, "Download cancelled")
            return
        except Exception as e:
            error_str = str(e) if e else ""
            if error_str and "cancelled" in error_str.lower():
                job_manager.update_job_status(job_id, "cancelled", 0, "Download cancelled")
                return
            raise
        
        # Check if cancelled after download
        if job_manager.is_cancelled(job_id):
            if file_path and Path(file_path).exists():
                try:
                    os.remove(file_path)
                except:
                    pass
            return
        
        if not file_path:
            error_details = "Download failed: No file was downloaded. This could be due to:\n"
            error_details += "- Invalid or unsupported video URL\n"
            error_details += "- Video is unavailable or geo-blocked\n"
            error_details += "- Network connectivity issues\n"
            error_details += "- File size exceeds the maximum limit\n"
            error_details += "Check the backend logs for more details."
            job_manager.update_job_status(
                job_id, "error", 0, error_details
            )
            return
        
        # Get video metadata
        metadata = downloader.get_metadata()
        job_manager.set_job_metadata(job_id, metadata)
        
        # Check if video is vertical and convert to horizontal automatically
        # First try metadata, if not available, probe the file
        video_width = metadata.get('width')
        video_height = metadata.get('height')
        
        # If dimensions not in metadata, probe the file
        converter = VideoConverter()
        if not video_width or not video_height:
            try:
                if converter.ffmpeg_path:
                    import subprocess as sp
                    probe_cmd = [converter.ffmpeg_path, '-i', file_path, '-hide_banner']
                    probe_result = sp.run(probe_cmd, capture_output=True, timeout=30, check=False)
                    if probe_result.stderr:
                        import re
                        stderr_str = probe_result.stderr.decode('utf-8', errors='ignore')
                        dimension_match = re.search(r'(\d{2,5})x(\d{2,5})', stderr_str)
                        if dimension_match:
                            video_width = int(dimension_match.group(1))
                            video_height = int(dimension_match.group(2))
                            metadata['width'] = video_width
                            metadata['height'] = video_height
            except Exception as e:
                print(f"Warning: Could not probe video dimensions: {e}")
        
        is_vertical = video_height > video_width if video_width and video_height else False
        
        final_file_path = file_path
        
        if is_vertical and converter.ffmpeg_path:
            # Convert vertical video to horizontal 1920x1080
            try:
                job_manager.update_job_status(job_id, "upload", 0, "Converting vertical video to horizontal...")
                converted_path = await converter.convert_to_horizontal(
                    input_file_path=file_path,
                    progress_callback=lambda p, s: job_manager.update_job_status(
                        job_id, "upload", p * 0.4, s  # Use first 40% for conversion
                    ),
                    cancellation_check=lambda: job_manager.is_cancelled(job_id),
                    job_id=job_id
                )
                if converted_path:
                    # Clean up original file
                    try:
                        if Path(file_path).exists():
                            os.remove(file_path)
                    except:
                        pass
                    final_file_path = converted_path
                    # Update metadata dimensions
                    metadata['width'] = 1920
                    metadata['height'] = 1080
                    metadata['converted_to_horizontal'] = True
            except Exception as e:
                print(f"Warning: Could not convert vertical video: {e}")
                # Continue with original file
        
        # Generate thumbnail before uploading (file will be deleted after upload)
        thumbnail_path = None
        try:
            job_manager.update_job_status(job_id, "upload", 40 if is_vertical else 0, "Generating thumbnail...")
            thumbnail_gen = ThumbnailGenerator()
            thumbnail_path = thumbnail_gen.generate_thumbnail(final_file_path)
        except Exception as e:
            print(f"Warning: Could not generate thumbnail: {e}")
        
        # Notify upload start
        job_manager.update_job_status(job_id, "upload", 50 if is_vertical else 10, "Starting upload to S3...")
        
        # Upload to S3
        s3_url = await uploader.upload(
            file_path=final_file_path,
            job_id=job_id,
            progress_callback=lambda p, s: job_manager.update_job_status(
                job_id, "upload", (50 if is_vertical else 10) + (p * 0.35), f"Uploading... {s}"  # Reserve for upload
            )
        )
        
        if s3_url:
            # Extract S3 key from URL for storage
            s3_key = uploader.extract_s3_key_from_url(s3_url)
            if s3_key:
                metadata['s3_key'] = s3_key
            
            # Upload thumbnail if generated
            thumbnail_url = None
            thumbnail_key = None
            if thumbnail_path:
                try:
                    job_manager.update_job_status(job_id, "upload", 90, "Uploading thumbnail...")
                    thumbnail_url = await uploader.upload_thumbnail(
                        thumbnail_path=thumbnail_path,
                        job_id=job_id
                    )
                    # Extract thumbnail key
                    if thumbnail_url:
                        thumbnail_key = uploader.extract_s3_key_from_url(thumbnail_url)
                        if thumbnail_key:
                            metadata['thumbnail_key'] = thumbnail_key
                    # Clean up local thumbnail
                    try:
                        os.remove(thumbnail_path)
                    except:
                        pass
                except Exception as e:
                    print(f"Warning: Could not upload thumbnail: {e}")
            
            # Add thumbnail URL to metadata
            if thumbnail_url:
                metadata['thumbnail_url'] = thumbnail_url
            
            # Success
            job_manager.complete_job(job_id, s3_url, metadata)
            
            # Automatically generate storyboard after successful upload
            try:
                storyboard_job_id = str(uuid.uuid4())
                job_manager.create_job(storyboard_job_id, f"storyboard:{s3_url}")
                
                # Start storyboard generation in background
                storyboard_task = asyncio.create_task(process_storyboard(
                    storyboard_job_id,
                    s3_url,
                    0.3,  # Default threshold
                    320,  # Default thumbnail width
                    180   # Default thumbnail height
                ))
                job_manager.set_job_task(storyboard_job_id, storyboard_task)
                
                # Store storyboard job_id in original job metadata
                metadata['storyboard_job_id'] = storyboard_job_id
                job_manager.set_job_metadata(job_id, metadata)
                
                print(f"Started automatic storyboard generation for job {job_id} -> storyboard job {storyboard_job_id}")
            except Exception as e:
                # Don't fail the main job if storyboard generation fails to start
                print(f"Warning: Failed to start automatic storyboard generation: {e}")
        else:
            job_manager.update_job_status(
                job_id, "error", 0, "Upload failed: Could not upload to S3"
            )
    
    except Exception as e:
        # Safely convert exception to string
        try:
            if e is None:
                error_str = "Unknown error"
            else:
                error_str = str(e) if e else "Unknown error"
                # Ensure it's a string and not None
                if not isinstance(error_str, str):
                    error_str = "Unknown error"
        except Exception:
            error_str = "Unknown error"
        
        error_msg = error_str if error_str else "Unknown error"
        # Provide more user-friendly error messages
        if error_msg and isinstance(error_msg, str) and "Could not extract video information" in error_msg:
            user_msg = "Could not access video. The URL may be invalid, the video may be private/unavailable, or the site may not be supported."
        elif error_msg and isinstance(error_msg, str) and "yt-dlp download error" in error_msg:
            user_msg = f"Download error: {error_msg.split(':', 1)[-1].strip() if ':' in error_msg else error_msg}"
        else:
            user_msg = f"Error: {error_msg}"
        
        job_manager.update_job_status(job_id, "error", 0, user_msg)
        print(f"Error processing job {job_id}: {error_msg}")
        import traceback
        traceback.print_exc()


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job status updates.
    """
    await websocket.accept()
    
    # Register WebSocket connection
    job_manager.register_websocket(job_id, websocket)
    
    try:
        # Send initial status if available
        job_status = job_manager.get_job_status(job_id)
        if job_status:
            await websocket.send_json(job_status)
        
        # Keep connection alive and forward updates
        last_status = None
        while True:
            # Wait for any message (ping/pong for keepalive)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
                # Echo back or handle client messages if needed
                await websocket.send_json({"type": "pong", "data": data})
            except asyncio.TimeoutError:
                # Poll for status updates frequently
                job_status = job_manager.get_job_status(job_id)
                if job_status:
                    # Only send if status changed to avoid spam
                    status_key = (job_status.get("stage"), job_status.get("percent"))
                    if status_key != last_status:
                        await websocket.send_json(job_status)
                        last_status = status_key
                    
                    # Check if job is complete or error
                    if job_status.get("stage") in ["complete", "error", "cancelled"]:
                        # Keep connection open for a bit, then close
                        await asyncio.sleep(2)
                        break
                continue
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error for job {job_id}: {e}")
    finally:
        job_manager.unregister_websocket(job_id, websocket)


@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Get current job status (REST endpoint as fallback)"""
    status = job_manager.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@app.get("/api/video/{job_id}")
async def proxy_video(job_id: str):
    """
    Proxy endpoint to serve video with proper CORS headers.
    This bypasses CORS issues when the S3/MinIO server doesn't have CORS configured.
    """
    status = job_manager.get_job_status(job_id)
    if not status or not status.get("s3_url"):
        raise HTTPException(status_code=404, detail="Video not found or not uploaded yet")
    
    s3_url = status["s3_url"]
    
    try:
        # Stream the video from S3 with proper headers
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream('GET', s3_url) as response:
                if response.status_code != 200:
                    raise HTTPException(status_code=response.status_code, detail="Failed to fetch video")
                
                # Return streaming response with proper video headers
                return StreamingResponse(
                    response.aiter_bytes(),
                    media_type="video/mp4",
                    headers={
                        "Content-Type": "video/mp4",
                        "Accept-Ranges": "bytes",
                        "Cache-Control": "public, max-age=3600",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                        "Access-Control-Allow-Headers": "Range",
                    }
                )
    except Exception as e:
        print(f"Error proxying video: {e}")
        # Fallback: redirect to S3 URL
        return RedirectResponse(url=s3_url)


@app.post("/api/job/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running download job."""
    success = job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Job cannot be cancelled (may already be complete, error, or not found)"
        )
    return {"status": "cancelled", "message": "Job cancellation requested"}


@app.post("/api/split", response_model=JobResponse)
async def start_split(request: SplitRequest):
    """
    Start a video split/trim job.
    Downloads the video from S3, trims it, and uploads the trimmed version.
    Returns a job_id that can be used to track progress via WebSocket.
    """
    # Validate S3 configuration
    if not settings.s3_bucket:
        raise HTTPException(
            status_code=500,
            detail="S3 bucket not configured. Please set S3_BUCKET environment variable."
        )
    
    if request.start_time < 0:
        raise HTTPException(
            status_code=400,
            detail="Start time must be >= 0"
        )
    
    if request.end_time is not None and request.end_time <= request.start_time:
        raise HTTPException(
            status_code=400,
            detail="End time must be greater than start time"
        )
    
    job_id = str(uuid.uuid4())
    
    # Create job
    job_manager.create_job(job_id, request.s3_url)
    
    # Start split process in background
    # Always pass convert_to_horizontal (defaults to False if not provided)
    convert_to_horizontal = request.convert_to_horizontal if request.convert_to_horizontal is not None else False
    
    task = asyncio.create_task(process_split(
        job_id,
        request.s3_url,
        request.start_time,
        request.end_time,
        convert_to_horizontal,
        request.original_metadata
    ))
    job_manager.set_job_task(job_id, task)
    
    return JobResponse(
        job_id=job_id,
        status="started",
        message="Split job started. Connect to WebSocket to track progress."
    )


# File metadata management endpoints

class FileMetadataRequest(BaseModel):
    s3_url: str
    job_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    video_width: Optional[int] = None
    video_height: Optional[int] = None
    thumbnail_url: Optional[str] = None
    playlist_id: Optional[str] = None
    created_at: Optional[str] = None


@app.post("/api/files")
async def save_file_metadata(request: FileMetadataRequest):
    """Save file metadata to JSON storage."""
    try:
        # Extract S3 key from URL if not provided
        s3_key = request.metadata.get("s3_key")
        thumbnail_key = request.metadata.get("thumbnail_key")
        
        if not s3_key and request.s3_url:
            # Try to extract S3 key from URL
            uploader = S3Uploader()
            s3_key = uploader.extract_s3_key_from_url(request.s3_url)
        
        # Clean metadata - remove storyboard frames if this is a split video
        # (frames will be generated fresh for the clip via storyboard_job_id)
        cleaned_metadata = request.metadata.copy() if request.metadata else {}
        if cleaned_metadata.get('is_split'):
            # Remove storyboard frames from split videos - they should only have frames from their own storyboard
            storyboard_fields_to_remove = [
                'frames', 'html_path', 'html_s3_url', 'html_s3_key', 
                'frames_dir', 'frame_count'
            ]
            for field in storyboard_fields_to_remove:
                cleaned_metadata.pop(field, None)
            # Keep storyboard_job_id so the frontend can fetch frames when they're ready
        
        metadata_dict = {
            "s3_url": request.s3_url,  # Keep for backward compatibility
            "s3_key": s3_key,  # Store S3 key for generating fresh URLs
            "job_id": request.job_id,
            "metadata": cleaned_metadata,  # Use cleaned metadata
            "video_width": request.video_width,
            "video_height": request.video_height,
            "thumbnail_url": request.thumbnail_url,
            "thumbnail_key": thumbnail_key,
            "playlist_id": request.playlist_id,  # Store playlist ID
            "created_at": request.created_at or datetime.now().isoformat()
        }
        file_id = metadata_store.save(metadata_dict)
        return {"id": file_id, "message": "File metadata saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save metadata: {str(e)}")


@app.get("/api/files")
async def get_all_files(playlist_id: Optional[str] = None):
    """Get all saved file metadata with fresh presigned URLs. Optionally filter by playlist_id."""
    try:
        files = metadata_store.get_all()
        
        # Filter by playlist if specified
        if playlist_id:
            files = [f for f in files if f.get("playlist_id") == playlist_id]
        uploader = S3Uploader()
        
        # Generate fresh presigned URLs for each file
        for file in files:
            s3_key = file.get("s3_key")
            if not s3_key:
                # Try to extract from old URL (for backward compatibility)
                old_url = file.get("s3_url")
                if old_url:
                    s3_key = uploader.extract_s3_key_from_url(old_url)
                    if s3_key:
                        # Save the extracted key for future use
                        file["s3_key"] = s3_key
                        metadata_store.update(file.get("id"), {"s3_key": s3_key})
            
            if s3_key:
                # Generate fresh presigned URL
                fresh_url = uploader.generate_presigned_url_from_key(s3_key)
                if fresh_url:
                    file["s3_url"] = fresh_url
            
            # Also refresh thumbnail URL if we have the key
            thumbnail_key = file.get("thumbnail_key")
            if not thumbnail_key:
                # Try to extract from old thumbnail URL
                old_thumbnail_url = file.get("thumbnail_url")
                if old_thumbnail_url:
                    thumbnail_key = uploader.extract_s3_key_from_url(old_thumbnail_url)
                    if thumbnail_key:
                        file["thumbnail_key"] = thumbnail_key
                        metadata_store.update(file.get("id"), {"thumbnail_key": thumbnail_key})
            
            if thumbnail_key:
                fresh_thumbnail_url = uploader._generate_presigned_url_thumbnail(thumbnail_key)
                if fresh_thumbnail_url:
                    file["thumbnail_url"] = fresh_thumbnail_url
        
        # Sort by created_at descending (newest first)
        files.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load files: {str(e)}")


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str):
    """Delete a file from metadata storage."""
    try:
        success = metadata_store.delete(file_id)
        if success:
            return {"message": "File deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


class UpdateFileRequest(BaseModel):
    title: Optional[str] = None


@app.put("/api/files/{file_id}")
async def update_file(file_id: str, request: UpdateFileRequest):
    """Update file metadata (e.g., title)."""
    try:
        file_data = metadata_store.get_by_id(file_id)
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        updates = {}
        if request.title is not None:
            # Update title in metadata
            metadata = file_data.get("metadata", {})
            metadata["title"] = request.title
            updates["metadata"] = metadata
        
        if updates:
            success = metadata_store.update(file_id, updates)
            if success:
                return {"message": "File updated successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to update file")
        else:
            return {"message": "No updates provided"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update file: {str(e)}")


# Playlist management endpoints

class CreatePlaylistRequest(BaseModel):
    title: str
    description: Optional[str] = None
    publish_status: str = "private"


class UpdatePlaylistRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    publish_status: Optional[str] = None


@app.post("/api/playlists")
async def create_playlist(request: CreatePlaylistRequest):
    """Create a new playlist."""
    try:
        if not request.title or not request.title.strip():
            raise HTTPException(status_code=400, detail="Playlist title is required")
        
        playlist_id = playlist_store.create(
            title=request.title.strip(),
            description=request.description,
            publish_status=request.publish_status
        )
        playlist = playlist_store.get_by_id(playlist_id)
        return {"id": playlist_id, "playlist": playlist, "message": "Playlist created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create playlist: {str(e)}")


@app.get("/api/playlists")
async def get_all_playlists():
    """Get all playlists."""
    try:
        playlists = playlist_store.get_all()
        return {"playlists": playlists}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load playlists: {str(e)}")


@app.get("/api/playlists/{playlist_id}")
async def get_playlist(playlist_id: str):
    """Get a playlist by ID."""
    try:
        playlist = playlist_store.get_by_id(playlist_id)
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")
        return {"playlist": playlist}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load playlist: {str(e)}")


@app.put("/api/playlists/{playlist_id}")
async def update_playlist(playlist_id: str, request: UpdatePlaylistRequest):
    """Update playlist data."""
    try:
        playlist = playlist_store.get_by_id(playlist_id)
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")
        
        updates = {}
        if request.title is not None:
            updates["title"] = request.title.strip()
        if request.description is not None:
            updates["description"] = request.description
        if request.publish_status is not None:
            updates["publish_status"] = request.publish_status
        
        if updates:
            playlist_store.update(playlist_id, updates)
        
        updated_playlist = playlist_store.get_by_id(playlist_id)
        return {"playlist": updated_playlist, "message": "Playlist updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update playlist: {str(e)}")


@app.delete("/api/playlists/{playlist_id}")
async def delete_playlist(playlist_id: str):
    """Delete a playlist."""
    try:
        success = playlist_store.delete(playlist_id)
        if success:
            return {"message": "Playlist deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Playlist not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete playlist: {str(e)}")


async def process_split(
    job_id: str,
    s3_url: str,
    start_time: float,
    end_time: Optional[float] = None,
    convert_to_horizontal: bool = False,
    original_metadata: Optional[Dict[str, Any]] = None
):
    """
    Process video split: Download from S3, trim, and upload trimmed version.
    """
    splitter = VideoSplitter()
    uploader = S3Uploader()
    
    try:
        # Check if cancelled before starting
        if job_manager.is_cancelled(job_id):
            return
        
        # Notify split start
        job_manager.update_job_status(job_id, "split", 0, "Splitting video from S3...")
        
        # Split video directly from S3 URL (FFmpeg can handle HTTP/HTTPS URLs)
        try:
            split_file_path = await splitter.split(
                input_file_path=s3_url,  # Use S3 URL directly
                start_time=start_time,
                end_time=end_time,
                convert_to_horizontal=convert_to_horizontal,
                progress_callback=lambda p, s: job_manager.update_job_status(
                    job_id, "split", p, s
                ),
                cancellation_check=lambda: job_manager.is_cancelled(job_id),
                job_id=job_id
            )
        except Exception as e:
            error_str = str(e) if e else "Unknown error"
            job_manager.update_job_status(
                job_id, "error", 0, f"Failed to split video: {error_str}"
            )
            return
        
        if not split_file_path:
            job_manager.update_job_status(job_id, "error", 0, "Split failed: No output file created")
            return
        
        # Check if cancelled after split
        if job_manager.is_cancelled(job_id):
            if split_file_path and Path(split_file_path).exists():
                try:
                    os.remove(split_file_path)
                except:
                    pass
            return
        
        # Create new metadata based on original
        new_metadata = {}
        if original_metadata:
            # Preserve original title and add split info
            original_title = original_metadata.get('title', 'Unknown')
            # Copy metadata but exclude storyboard-related fields (frames will be generated fresh for the clip)
            new_metadata = original_metadata.copy()
            # Remove storyboard frames and related data - new storyboard will be generated for the clip
            storyboard_fields_to_remove = [
                'frames', 'storyboard_job_id', 'storyboard_html_s3_url', 
                'storyboard_html_s3_key', 'storyboard_completed', 'storyboard_frame_count',
                'html_path', 'html_s3_url', 'html_s3_key', 'frames_dir', 'frame_count'
            ]
            for field in storyboard_fields_to_remove:
                new_metadata.pop(field, None)
            
            new_metadata['title'] = f"{original_title} (Split {start_time:.1f}s-{end_time:.1f}s)" if end_time else f"{original_title} (Split from {start_time:.1f}s)"
            new_metadata['is_split'] = True
            new_metadata['original_duration'] = original_metadata.get('duration', 0)
            new_metadata['split_start'] = start_time
            new_metadata['split_end'] = end_time
        else:
            new_metadata = {
                'title': f"Split Video ({start_time:.1f}s-{end_time:.1f}s)" if end_time else f"Split Video (from {start_time:.1f}s)",
                'is_split': True
            }
        
        # Generate thumbnail before uploading (file will be deleted after upload)
        thumbnail_path = None
        try:
            job_manager.update_job_status(job_id, "upload", 0, "Generating thumbnail...")
            thumbnail_gen = ThumbnailGenerator()
            thumbnail_path = thumbnail_gen.generate_thumbnail(split_file_path)
        except Exception as e:
            print(f"Warning: Could not generate thumbnail: {e}")
        
        # Notify upload start
        job_manager.update_job_status(job_id, "upload", 10, "Uploading trimmed video to S3...")
        
        # Upload to S3
        s3_url_new = await uploader.upload(
            file_path=split_file_path,
            job_id=job_id,
            progress_callback=lambda p, s: job_manager.update_job_status(
                job_id, "upload", 10 + (p * 0.8), f"Uploading... {s}"  # Reserve 10-90% for upload
            )
        )
        
        if s3_url_new:
            # Extract S3 key from URL for storage
            s3_key = uploader.extract_s3_key_from_url(s3_url_new)
            if s3_key:
                new_metadata['s3_key'] = s3_key
            
            # Upload thumbnail if generated
            thumbnail_url = None
            thumbnail_key = None
            if thumbnail_path:
                try:
                    job_manager.update_job_status(job_id, "upload", 90, "Uploading thumbnail...")
                    thumbnail_url = await uploader.upload_thumbnail(
                        thumbnail_path=thumbnail_path,
                        job_id=job_id
                    )
                    # Extract thumbnail key
                    if thumbnail_url:
                        thumbnail_key = uploader.extract_s3_key_from_url(thumbnail_url)
                        if thumbnail_key:
                            new_metadata['thumbnail_key'] = thumbnail_key
                    # Clean up local thumbnail
                    try:
                        os.remove(thumbnail_path)
                    except:
                        pass
                except Exception as e:
                    print(f"Warning: Could not upload thumbnail: {e}")
            
            # Add thumbnail URL to metadata
            if thumbnail_url:
                new_metadata['thumbnail_url'] = thumbnail_url
            
            # Success
            job_manager.complete_job(job_id, s3_url_new, new_metadata)
            
            # Automatically generate storyboard after successful upload
            try:
                storyboard_job_id = str(uuid.uuid4())
                job_manager.create_job(storyboard_job_id, f"storyboard:{s3_url_new}")
                
                # Start storyboard generation in background
                storyboard_task = asyncio.create_task(process_storyboard(
                    storyboard_job_id,
                    s3_url_new,
                    0.3,  # Default threshold
                    320,  # Default thumbnail width
                    180   # Default thumbnail height
                ))
                job_manager.set_job_task(storyboard_job_id, storyboard_task)
                
                # Store storyboard job_id in original job metadata
                new_metadata['storyboard_job_id'] = storyboard_job_id
                job_manager.set_job_metadata(job_id, new_metadata)
                
                print(f"Started automatic storyboard generation for split job {job_id} -> storyboard job {storyboard_job_id}")
            except Exception as e:
                # Don't fail the main job if storyboard generation fails to start
                print(f"Warning: Failed to start automatic storyboard generation: {e}")
        else:
            job_manager.update_job_status(
                job_id, "error", 0, "Upload failed: Could not upload to S3"
            )
    
    except Exception as e:
        error_str = str(e) if e else "Unknown error"
        job_manager.update_job_status(job_id, "error", 0, f"Error: {error_str}")
        print(f"Error processing split job {job_id}: {error_str}")
        import traceback
        traceback.print_exc()


async def process_upload(
    job_id: str,
    input_file_path: str,
    original_filename: str
):
    """
    Process uploaded video: Convert to 1920x1080 and upload to S3.
    """
    converter = VideoConverter()
    uploader = S3Uploader()
    converted_file_path = None
    
    try:
        # Check if cancelled before starting
        if job_manager.is_cancelled(job_id):
            return
        
        # Notify conversion start
        job_manager.update_job_status(job_id, "upload", 0, "Converting video to 1920x1080...")
        
        # Convert video to 1920x1080
        print(f"Upload job {job_id}: Starting conversion of {input_file_path}")
        try:
            converted_file_path = await converter.convert_to_horizontal(
                input_file_path=input_file_path,
                progress_callback=lambda p, s: job_manager.update_job_status(
                    job_id, "upload", p * 0.5, s  # Use first 50% for conversion
                ),
                cancellation_check=lambda: job_manager.is_cancelled(job_id),
                job_id=job_id
            )
            print(f"Upload job {job_id}: Conversion result: {converted_file_path}")
        except Exception as e:
            error_str = str(e) if e else "Unknown error"
            print(f"Upload job {job_id}: Conversion exception: {error_str}")
            import traceback
            traceback.print_exc()
            job_manager.update_job_status(
                job_id, "error", 0, f"Failed to convert video: {error_str}"
            )
            # Clean up input file
            try:
                if Path(input_file_path).exists():
                    os.remove(input_file_path)
            except:
                pass
            return
        
        if not converted_file_path:
            # Check if FFmpeg is available
            if not converter.ffmpeg_path:
                error_msg = "Conversion failed: FFmpeg is not installed or not found in PATH. Please install FFmpeg to enable video conversion."
            else:
                error_msg = "Conversion failed: No output file created. Check backend logs for FFmpeg error details."
            print(f"Upload job {job_id}: {error_msg}")
            job_manager.update_job_status(job_id, "error", 0, error_msg)
            # Clean up input file
            try:
                if Path(input_file_path).exists():
                    os.remove(input_file_path)
            except:
                pass
            return
        
        # Check if cancelled after conversion
        if job_manager.is_cancelled(job_id):
            if converted_file_path and Path(converted_file_path).exists():
                try:
                    os.remove(converted_file_path)
                except:
                    pass
            try:
                if Path(input_file_path).exists():
                    os.remove(input_file_path)
            except:
                pass
            return
        
        # Clean up original uploaded file
        try:
            if Path(input_file_path).exists():
                os.remove(input_file_path)
        except:
            pass
        
        # Generate thumbnail before uploading
        thumbnail_path = None
        try:
            job_manager.update_job_status(job_id, "upload", 50, "Generating thumbnail...")
            thumbnail_gen = ThumbnailGenerator()
            thumbnail_path = thumbnail_gen.generate_thumbnail(converted_file_path)
        except Exception as e:
            print(f"Warning: Could not generate thumbnail: {e}")
        
        # Notify upload start
        job_manager.update_job_status(job_id, "upload", 60, "Uploading to S3...")
        
        # Upload to S3
        s3_url = await uploader.upload(
            file_path=converted_file_path,
            job_id=job_id,
            progress_callback=lambda p, s: job_manager.update_job_status(
                job_id, "upload", 60 + (p * 0.25), f"Uploading... {s}"  # Use 60-85% for upload
            )
        )
        
        if s3_url:
            # Extract S3 key from URL for storage
            s3_key = uploader.extract_s3_key_from_url(s3_url)
            
            # Upload thumbnail if generated
            thumbnail_url = None
            thumbnail_key = None
            if thumbnail_path:
                try:
                    job_manager.update_job_status(job_id, "upload", 85, "Uploading thumbnail...")
                    thumbnail_url = await uploader.upload_thumbnail(
                        thumbnail_path=thumbnail_path,
                        job_id=job_id
                    )
                    # Extract thumbnail key
                    if thumbnail_url:
                        thumbnail_key = uploader.extract_s3_key_from_url(thumbnail_url)
                    # Clean up local thumbnail
                    try:
                        os.remove(thumbnail_path)
                    except:
                        pass
                except Exception as e:
                    print(f"Warning: Could not upload thumbnail: {e}")
            
            # Create metadata
            metadata = {
                'title': Path(original_filename).stem,
                's3_key': s3_key,
                'thumbnail_key': thumbnail_key,
                'uploader': 'Local Upload',
                'duration': 0,  # Could probe for duration if needed
                'format': 'mp4',
                'filesize': Path(converted_file_path).stat().st_size if Path(converted_file_path).exists() else 0,
                'ext': 'mp4',
                'thumbnail_url': thumbnail_url
            }
            
            # Success
            job_manager.complete_job(job_id, s3_url, metadata)
            
            # Automatically generate storyboard after successful upload
            try:
                storyboard_job_id = str(uuid.uuid4())
                job_manager.create_job(storyboard_job_id, f"storyboard:{s3_url}")
                
                # Start storyboard generation in background
                storyboard_task = asyncio.create_task(process_storyboard(
                    storyboard_job_id,
                    s3_url,
                    0.3,  # Default threshold
                    320,  # Default thumbnail width
                    180   # Default thumbnail height
                ))
                job_manager.set_job_task(storyboard_job_id, storyboard_task)
                
                # Store storyboard job_id in original job metadata
                metadata['storyboard_job_id'] = storyboard_job_id
                job_manager.set_job_metadata(job_id, metadata)
                
                print(f"Started automatic storyboard generation for upload job {job_id} -> storyboard job {storyboard_job_id}")
            except Exception as e:
                # Don't fail the main job if storyboard generation fails to start
                print(f"Warning: Failed to start automatic storyboard generation: {e}")
        else:
            job_manager.update_job_status(
                job_id, "error", 0, "Upload failed: Could not upload to S3"
            )
    
    except Exception as e:
        error_str = str(e) if e else "Unknown error"
        job_manager.update_job_status(job_id, "error", 0, f"Error: {error_str}")
        print(f"Error processing upload job {job_id}: {error_str}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up converted file
        try:
            if converted_file_path and Path(converted_file_path).exists():
                os.remove(converted_file_path)
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

