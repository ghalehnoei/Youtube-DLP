"""
Job manager for tracking download/upload jobs and WebSocket connections.
"""
import asyncio
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from fastapi import WebSocket
import json
import threading


@dataclass
class JobStatus:
    """Status information for a job."""
    job_id: str
    url: str
    stage: str = "pending"  # pending, download, upload, complete, error, cancelled
    percent: float = 0.0
    message: str = ""
    speed: str = ""
    eta: str = ""
    s3_url: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    websockets: List[WebSocket] = field(default_factory=list)
    cancelled: bool = False
    task: Optional[asyncio.Task] = None


class JobManager:
    """Manages job status and WebSocket connections."""
    
    def __init__(self):
        self.jobs: Dict[str, JobStatus] = {}
        self._lock = threading.Lock()
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
    
    def set_main_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the main event loop (called from FastAPI startup)."""
        self._main_loop = loop
    
    def create_job(self, job_id: str, url: str):
        """Create a new job."""
        with self._lock:
            self.jobs[job_id] = JobStatus(job_id=job_id, url=url, stage="pending")
    
    def update_job_status(
        self,
        job_id: str,
        stage: str,
        percent: float,
        message: str = "",
        speed: str = "",
        eta: str = ""
    ):
        """Update job status and notify all connected WebSockets."""
        with self._lock:
            if job_id not in self.jobs:
                return
            
            job = self.jobs[job_id]
            job.stage = stage
            job.percent = percent
            job.message = message
            job.speed = speed
            job.eta = eta
        
        # Notify WebSocket clients (thread-safe)
        self._schedule_notification(job_id)
    
    def _schedule_notification(self, job_id: str):
        """Schedule WebSocket notification in a thread-safe way."""
        try:
            # Try to get the running event loop (we're in async context)
            loop = asyncio.get_running_loop()
            # Schedule the coroutine
            asyncio.create_task(self._notify_websockets(job_id))
        except RuntimeError:
            # No event loop in current thread - we're in a worker thread
            # Use the stored main loop to schedule notification
            if self._main_loop and self._main_loop.is_running():
                try:
                    asyncio.run_coroutine_threadsafe(
                        self._notify_websockets(job_id),
                        self._main_loop
                    )
                except Exception as e:
                    # If notification fails, that's okay - WebSocket polling will pick it up
                    pass
            # If no main loop stored, WebSocket polling will handle updates
    
    def set_job_metadata(self, job_id: str, metadata: Dict):
        """Set metadata for a job."""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].metadata = metadata
    
    def complete_job(self, job_id: str, s3_url: str, metadata: Dict):
        """Mark job as complete."""
        with self._lock:
            if job_id not in self.jobs:
                return
            
            job = self.jobs[job_id]
            job.stage = "complete"
            job.percent = 100.0
            job.s3_url = s3_url
            job.metadata = metadata
            job.message = "Upload complete!"
        
        self._schedule_notification(job_id)
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get current job status as dictionary."""
        with self._lock:
            if job_id not in self.jobs:
                return None
            
            job = self.jobs[job_id]
            
            # Generate fresh URL from s3_key if available (to use current settings)
            s3_url = job.s3_url
            if job.metadata:
                # Check for s3_key in metadata and generate fresh URL
                s3_key = job.metadata.get('s3_key')
                if s3_key:
                    try:
                        from app.uploader import S3Uploader
                        uploader = S3Uploader()
                        fresh_url = uploader.generate_presigned_url_from_key(s3_key)
                        if fresh_url:
                            s3_url = fresh_url
                    except Exception as e:
                        # If URL generation fails, use stored URL as fallback
                        print(f"Warning: Could not generate fresh URL from key: {e}")
            
            return {
                "jobId": job.job_id,
                "stage": job.stage,
                "percent": job.percent,
                "message": job.message,
                "speed": job.speed,
                "eta": job.eta,
                "s3_url": s3_url,
                "metadata": job.metadata,
                "url": job.url
            }
    
    def register_websocket(self, job_id: str, websocket: WebSocket):
        """Register a WebSocket connection for a job."""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].websockets.append(websocket)
    
    def unregister_websocket(self, job_id: str, websocket: WebSocket):
        """Unregister a WebSocket connection."""
        with self._lock:
            if job_id in self.jobs:
                try:
                    self.jobs[job_id].websockets.remove(websocket)
                except ValueError:
                    pass
    
    async def _notify_websockets(self, job_id: str):
        """Notify all WebSocket connections for a job."""
        if job_id not in self.jobs:
            return
        
        job = self.jobs[job_id]
        status = self.get_job_status(job_id)
        
        if not status:
            return
        
        # Send to all connected WebSockets
        disconnected = []
        for ws in job.websockets:
            try:
                await ws.send_json(status)
            except (ConnectionResetError, OSError):
                # Client disconnected abruptly - this is normal, especially on Windows
                disconnected.append(ws)
            except Exception as e:
                # Only log unexpected errors
                print(f"Error sending to WebSocket: {e}")
                disconnected.append(ws)
        
        # Remove disconnected WebSockets
        for ws in disconnected:
            self.unregister_websocket(job_id, ws)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        with self._lock:
            if job_id not in self.jobs:
                return False
            
            job = self.jobs[job_id]
            if job.stage in ["complete", "error", "cancelled"]:
                return False
            
            job.cancelled = True
            job.stage = "cancelled"
            job.message = "Download cancelled by user"
        
        # Cancel the task if it exists
        if job.task:
            job.task.cancel()
        
        self._schedule_notification(job_id)
        return True
    
    def set_job_task(self, job_id: str, task: asyncio.Task):
        """Set the asyncio task for a job (for cancellation)."""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].task = task
    
    def is_cancelled(self, job_id: str) -> bool:
        """Check if a job is cancelled."""
        with self._lock:
            if job_id not in self.jobs:
                return True
            return self.jobs[job_id].cancelled
    
    def get_all_jobs(self, include_completed: bool = False) -> List[Dict]:
        """Get all jobs (active or all including completed)."""
        with self._lock:
            jobs_list = []
            for job in self.jobs.values():
                # Filter out completed/error/cancelled jobs if not requested
                if not include_completed and job.stage in ["complete", "error", "cancelled"]:
                    continue
                
                # Generate fresh URL from s3_key if available
                s3_url = job.s3_url
                if job.metadata:
                    s3_key = job.metadata.get('s3_key')
                    if s3_key:
                        try:
                            from app.uploader import S3Uploader
                            uploader = S3Uploader()
                            fresh_url = uploader.generate_presigned_url_from_key(s3_key)
                            if fresh_url:
                                s3_url = fresh_url
                        except Exception:
                            pass
                
                jobs_list.append({
                    "jobId": job.job_id,
                    "stage": job.stage,
                    "percent": job.percent,
                    "message": job.message,
                    "speed": job.speed,
                    "eta": job.eta,
                    "s3_url": s3_url,
                    "metadata": job.metadata,
                    "url": job.url,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "websocket_count": len(job.websockets),
                    "cancelled": job.cancelled
                })
            
            # Sort by created_at descending (newest first)
            jobs_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return jobs_list
    
    def cleanup_all_jobs(self):
        """Cleanup all jobs (called on shutdown)."""
        # Close all WebSocket connections
        for job in self.jobs.values():
            for ws in job.websockets:
                try:
                    asyncio.create_task(ws.close())
                except:
                    pass
        self.jobs.clear()

