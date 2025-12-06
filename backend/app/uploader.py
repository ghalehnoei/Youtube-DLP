"""
S3 uploader with progress tracking.
"""
import boto3
import os
from typing import Optional, Callable
from pathlib import Path
from botocore.exceptions import ClientError, NoCredentialsError
from app.config import settings
import asyncio


class S3Uploader:
    """Handles file uploads to S3 with progress tracking."""
    
    def __init__(self):
        self.s3_client = None
        self._init_s3_client()
    
    def _init_s3_client(self):
        """Initialize S3 client with credentials."""
        try:
            if settings.s3_endpoint_url:
                # For S3-compatible services (MinIO, etc.)
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=settings.s3_endpoint_url,
                    aws_access_key_id=settings.s3_access_key_id,
                    aws_secret_access_key=settings.s3_secret_access_key,
                    region_name=settings.s3_region
                )
            else:
                # Standard AWS S3
                if settings.s3_access_key_id and settings.s3_secret_access_key:
                    self.s3_client = boto3.client(
                        's3',
                        aws_access_key_id=settings.s3_access_key_id,
                        aws_secret_access_key=settings.s3_secret_access_key,
                        region_name=settings.s3_region
                    )
                else:
                    # Use default credentials (IAM role, environment, etc.)
                    self.s3_client = boto3.client('s3', region_name=settings.s3_region)
        except Exception as e:
            print(f"Error initializing S3 client: {e}")
            self.s3_client = None
    
    def _upload_progress(self, bytes_amount: int, callback: Optional[Callable] = None):
        """Progress callback for S3 upload."""
        # This will be called by boto3's upload_fileobj with TransferConfig
        # We'll track progress manually in the upload method
        pass
    
    async def upload(
        self,
        file_path: str,
        job_id: str,
        progress_callback: Optional[Callable] = None
    ) -> Optional[str]:
        """
        Upload file to S3 with progress tracking.
        
        Args:
            file_path: Local file path
            job_id: Job ID for organizing files in S3
            progress_callback: Callback function(percent, message)
        
        Returns:
            S3 URL or None if failed
        """
        if not self.s3_client:
            if progress_callback:
                progress_callback(0, "S3 client not initialized")
            return None
        
        if not settings.s3_bucket:
            if progress_callback:
                progress_callback(0, "S3 bucket not configured")
            return None
        
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            if progress_callback:
                progress_callback(0, f"File not found: {file_path}")
            return None
        
        # Generate S3 key with standard filename format
        # Extract extension from original file
        file_ext = file_path_obj.suffix or '.mp4'
        # Use standard naming: video_{job_id}.{ext}
        standard_filename = f"video_{job_id}{file_ext}"
        s3_key = f"videos/{job_id}/{standard_filename}"
        
        file_size = file_path_obj.stat().st_size
        
        try:
            # Upload file with progress tracking
            loop = asyncio.get_event_loop()
            s3_key = await loop.run_in_executor(
                None,
                self._upload_sync,
                str(file_path),
                s3_key,
                file_size,
                progress_callback
            )
            
            if not s3_key:
                return None
            
            # Generate URL
            if settings.s3_public_urls:
                # Public URL
                if settings.s3_endpoint_url:
                    # Custom endpoint
                    s3_url = f"{settings.s3_endpoint_url.rstrip('/')}/{settings.s3_bucket}/{s3_key}"
                else:
                    # Standard S3 URL
                    s3_url = f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com/{s3_key}"
            else:
                # Generate presigned URL
                s3_url = self._generate_presigned_url(s3_key)
            
            # Clean up local file
            try:
                os.remove(file_path)
                # Also try to remove parent directory if empty
                parent_dir = file_path_obj.parent
                try:
                    parent_dir.rmdir()
                except:
                    pass
            except Exception as e:
                print(f"Warning: Could not delete temp file {file_path}: {e}")
            
            return s3_url
        
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            print(error_msg)
            if progress_callback:
                progress_callback(0, error_msg)
            return None
    
    def _upload_sync(
        self,
        file_path: str,
        s3_key: str,
        file_size: int,
        progress_callback: Optional[Callable] = None
    ) -> Optional[str]:
        """Synchronous upload function with progress tracking."""
        try:
            from boto3.s3.transfer import TransferConfig
            
            # Use multipart upload for large files
            config = TransferConfig(
                multipart_threshold=1024 * 25,  # 25MB
                max_concurrency=10,
                multipart_chunksize=1024 * 25,  # 25MB chunks
                use_threads=True
            )
            
            # Track upload progress
            uploaded = 0
            
            def upload_callback(bytes_amount):
                nonlocal uploaded
                uploaded += bytes_amount
                if progress_callback and file_size > 0:
                    percent = (uploaded / file_size) * 100
                    progress_callback(percent, f"Uploaded {uploaded / 1024 / 1024:.2f}MB")
            
            # Create callback wrapper
            class ProgressCallback:
                def __init__(self, callback):
                    self.callback = callback
                
                def __call__(self, bytes_amount):
                    if self.callback:
                        self.callback(bytes_amount)
            
            # Determine content type based on file extension
            file_path_obj = Path(file_path) if file_path else None
            file_ext = (file_path_obj.suffix or '.mp4').lower() if file_path_obj else '.mp4'
            content_type_map = {
                '.mp4': 'video/mp4',
                '.webm': 'video/webm',
                '.mkv': 'video/x-matroska',
                '.avi': 'video/x-msvideo',
                '.flv': 'video/x-flv',
                '.mov': 'video/quicktime',
                '.m4v': 'video/mp4',
            }
            content_type = content_type_map.get(file_ext, 'video/mp4')
            
            # Extra args for metadata and CORS
            extra_args = {
                'ContentType': content_type,
                'Metadata': {
                    'original-filename': Path(file_path).name
                }
            }
            
            # Upload file with content type
            self.s3_client.upload_file(
                file_path,
                settings.s3_bucket,
                s3_key,
                Config=config,
                Callback=ProgressCallback(upload_callback),
                ExtraArgs=extra_args
            )
            
            # Final progress update
            if progress_callback:
                progress_callback(100.0, "Upload complete!")
            
            return s3_key
        
        except NoCredentialsError:
            error_msg = "AWS credentials not found"
            print(error_msg)
            if progress_callback:
                progress_callback(0, error_msg)
            return None
        except ClientError as e:
            error_msg = f"AWS S3 error: {str(e)}"
            print(error_msg)
            if progress_callback:
                progress_callback(0, error_msg)
            return None
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            print(error_msg)
            if progress_callback:
                progress_callback(0, error_msg)
            return None
    
    async def upload_thumbnail(
        self,
        thumbnail_path: str,
        job_id: str,
        progress_callback: Optional[Callable] = None
    ) -> Optional[str]:
        """
        Upload thumbnail image to S3.
        
        Args:
            thumbnail_path: Local thumbnail file path
            job_id: Job ID for organizing files in S3
            progress_callback: Callback function(percent, message)
        
        Returns:
            S3 URL or None if failed
        """
        if not self.s3_client:
            return None
        
        if not settings.s3_bucket:
            return None
        
        file_path_obj = Path(thumbnail_path)
        if not file_path_obj.exists():
            return None
        
        # Generate S3 key for thumbnail
        s3_key = f"thumbnails/{job_id}/thumbnail_{job_id}.jpg"
        
        try:
            loop = asyncio.get_event_loop()
            s3_key = await loop.run_in_executor(
                None,
                self._upload_thumbnail_sync,
                str(thumbnail_path),
                s3_key,
                progress_callback
            )
            
            if not s3_key:
                return None
            
            # Generate URL
            if settings.s3_public_urls:
                if settings.s3_endpoint_url:
                    s3_url = f"{settings.s3_endpoint_url.rstrip('/')}/{settings.s3_bucket}/{s3_key}"
                else:
                    s3_url = f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com/{s3_key}"
            else:
                s3_url = self._generate_presigned_url_thumbnail(s3_key)
            
            return s3_url
        
        except Exception as e:
            print(f"Error uploading thumbnail: {e}")
            return None
    
    def _upload_thumbnail_sync(
        self,
        thumbnail_path: str,
        s3_key: str,
        progress_callback: Optional[Callable] = None
    ) -> Optional[str]:
        """Synchronous thumbnail upload."""
        try:
            extra_args = {
                'ContentType': 'image/jpeg',
                'Metadata': {
                    'original-filename': Path(thumbnail_path).name
                }
            }
            
            self.s3_client.upload_file(
                thumbnail_path,
                settings.s3_bucket,
                s3_key,
                ExtraArgs=extra_args
            )
            
            if progress_callback:
                progress_callback(100.0, "Thumbnail uploaded")
            
            return s3_key
        
        except Exception as e:
            print(f"Error uploading thumbnail: {e}")
            return None
    
    def _generate_presigned_url_thumbnail(self, s3_key: str) -> str:
        """Generate a presigned URL for thumbnail."""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.s3_bucket,
                    'Key': s3_key,
                    'ResponseContentType': 'image/jpeg',
                },
                ExpiresIn=settings.s3_url_expiration
            )
            return url
        except Exception as e:
            print(f"Error generating presigned URL for thumbnail: {e}")
            if settings.s3_endpoint_url:
                return f"{settings.s3_endpoint_url.rstrip('/')}/{settings.s3_bucket}/{s3_key}"
            else:
                return f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com/{s3_key}"
    
    def _generate_presigned_url(self, s3_key: str) -> str:
        """Generate a presigned URL for the uploaded file with proper headers for video playback."""
        try:
            # Generate presigned URL with ResponseContentType for video streaming
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.s3_bucket,
                    'Key': s3_key,
                    'ResponseContentType': 'video/mp4',  # Helps with video playback
                },
                ExpiresIn=settings.s3_url_expiration
            )
            return url
        except Exception as e:
            print(f"Error generating presigned URL: {e}")
            # Fallback to public URL format
            if settings.s3_endpoint_url:
                return f"{settings.s3_endpoint_url.rstrip('/')}/{settings.s3_bucket}/{s3_key}"
            else:
                return f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com/{s3_key}"
    
    def generate_presigned_url_from_key(self, s3_key: str) -> Optional[str]:
        """Generate a fresh presigned URL from an S3 key."""
        if not self.s3_client:
            return None
        try:
            return self._generate_presigned_url(s3_key)
        except Exception as e:
            print(f"Error generating presigned URL from key: {e}")
            return None
    
    def generate_url_from_key(self, s3_key: str, content_type: str = 'video/mp4') -> Optional[str]:
        """
        Generate a URL from an S3 key using current settings.
        This ensures URLs are always generated from current settings, not stored URLs.
        
        Args:
            s3_key: S3 key (e.g., "videos/job_id/video_job_id.mp4")
            content_type: Content type for presigned URLs (default: 'video/mp4')
        
        Returns:
            URL string or None if failed
        """
        if not s3_key:
            return None
        
        if not self.s3_client or not settings.s3_bucket:
            return None
        
        try:
            if settings.s3_public_urls:
                # Public URL
                if settings.s3_endpoint_url:
                    return f"{settings.s3_endpoint_url.rstrip('/')}/{settings.s3_bucket}/{s3_key}"
                else:
                    return f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com/{s3_key}"
            else:
                # Generate presigned URL
                if content_type == 'text/html':
                    return self._generate_presigned_url_storyboard(s3_key, content_type)
                elif content_type == 'image/jpeg':
                    return self._generate_presigned_url_storyboard(s3_key, content_type)
                else:
                    return self._generate_presigned_url(s3_key)
        except Exception as e:
            print(f"Error generating URL from key: {e}")
            return None
    
    async def upload_storyboard_html(
        self,
        html_path: str,
        job_id: str,
        progress_callback: Optional[Callable] = None
    ) -> Optional[str]:
        """
        Upload storyboard HTML file to S3.
        
        Args:
            html_path: Local HTML file path
            job_id: Job ID for organizing files in S3
            progress_callback: Callback function(percent, message)
        
        Returns:
            S3 URL or None if failed
        """
        if not self.s3_client or not settings.s3_bucket:
            return None
        
        file_path_obj = Path(html_path)
        if not file_path_obj.exists():
            return None
        
        # Generate S3 key for storyboard HTML
        s3_key = f"storyboards/{job_id}/storyboard.html"
        
        try:
            loop = asyncio.get_event_loop()
            s3_key = await loop.run_in_executor(
                None,
                self._upload_file_sync,
                str(html_path),
                s3_key,
                'text/html',
                progress_callback
            )
            
            if not s3_key:
                return None
            
            # Generate URL
            if settings.s3_public_urls:
                if settings.s3_endpoint_url:
                    s3_url = f"{settings.s3_endpoint_url.rstrip('/')}/{settings.s3_bucket}/{s3_key}"
                else:
                    s3_url = f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com/{s3_key}"
            else:
                s3_url = self._generate_presigned_url_storyboard(s3_key, 'text/html')
            
            return s3_url
        except Exception as e:
            print(f"Error uploading storyboard HTML: {e}")
            return None
    
    async def upload_storyboard_frame(
        self,
        frame_path: str,
        job_id: str,
        frame_index: int,
        progress_callback: Optional[Callable] = None
    ) -> Optional[str]:
        """
        Upload a storyboard frame image to S3.
        
        Args:
            frame_path: Local frame image file path
            job_id: Job ID for organizing files in S3
            frame_index: Index of the frame
            progress_callback: Callback function(percent, message)
        
        Returns:
            S3 URL or None if failed
        """
        if not self.s3_client or not settings.s3_bucket:
            return None
        
        file_path_obj = Path(frame_path)
        if not file_path_obj.exists():
            return None
        
        # Generate S3 key for frame
        s3_key = f"storyboards/{job_id}/frames/frame_{frame_index:04d}.jpg"
        
        try:
            loop = asyncio.get_event_loop()
            s3_key = await loop.run_in_executor(
                None,
                self._upload_file_sync,
                str(frame_path),
                s3_key,
                'image/jpeg',
                progress_callback
            )
            
            if not s3_key:
                return None
            
            # Generate URL
            if settings.s3_public_urls:
                if settings.s3_endpoint_url:
                    s3_url = f"{settings.s3_endpoint_url.rstrip('/')}/{settings.s3_bucket}/{s3_key}"
                else:
                    s3_url = f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com/{s3_key}"
            else:
                s3_url = self._generate_presigned_url_storyboard(s3_key, 'image/jpeg')
            
            return s3_url
        except Exception as e:
            print(f"Error uploading storyboard frame: {e}")
            return None
    
    def _upload_file_sync(
        self,
        file_path: str,
        s3_key: str,
        content_type: str,
        progress_callback: Optional[Callable] = None
    ) -> Optional[str]:
        """Synchronous file upload helper."""
        try:
            extra_args = {
                'ContentType': content_type,
                'Metadata': {
                    'original-filename': Path(file_path).name
                }
            }
            
            self.s3_client.upload_file(
                file_path,
                settings.s3_bucket,
                s3_key,
                ExtraArgs=extra_args
            )
            
            if progress_callback:
                progress_callback(100.0, "Upload complete")
            
            return s3_key
        except Exception as e:
            print(f"Error uploading file: {e}")
            return None
    
    def _generate_presigned_url_storyboard(self, s3_key: str, content_type: str) -> str:
        """Generate a presigned URL for storyboard files."""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.s3_bucket,
                    'Key': s3_key,
                    'ResponseContentType': content_type,
                },
                ExpiresIn=settings.s3_url_expiration
            )
            return url
        except Exception as e:
            print(f"Error generating presigned URL for storyboard: {e}")
            if settings.s3_endpoint_url:
                return f"{settings.s3_endpoint_url.rstrip('/')}/{settings.s3_bucket}/{s3_key}"
            else:
                return f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com/{s3_key}"
    
    def generate_presigned_url_for_frame(self, s3_key: str) -> Optional[str]:
        """
        Generate a fresh presigned URL for a storyboard frame from its S3 key.
        This should be called on-demand since presigned URLs expire.
        
        Args:
            s3_key: S3 key of the frame (e.g., "storyboards/job_id/frames/frame_0001.jpg")
        
        Returns:
            Presigned URL or None if failed
        """
        if not self.s3_client or not settings.s3_bucket:
            return None
        
        if not s3_key:
            return None
        
        try:
            if settings.s3_public_urls:
                # Public URLs don't expire
                if settings.s3_endpoint_url:
                    return f"{settings.s3_endpoint_url.rstrip('/')}/{settings.s3_bucket}/{s3_key}"
                else:
                    return f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com/{s3_key}"
            else:
                # Generate fresh presigned URL
                return self._generate_presigned_url_storyboard(s3_key, 'image/jpeg')
        except Exception as e:
            print(f"Error generating presigned URL for frame {s3_key}: {e}")
            return None
    
    def extract_s3_key_from_url(self, s3_url: str) -> Optional[str]:
        """
        Extract S3 key from a presigned URL or public URL.
        This method tries multiple patterns to extract the key, making it independent
        of current settings so it can work with old URLs even if settings changed.
        """
        try:
            from urllib.parse import urlparse, parse_qs
            
            # Remove query parameters for key extraction
            url_without_params = s3_url.split('?')[0]
            
            # Try current settings first (for backward compatibility)
            if settings.s3_bucket:
                if settings.s3_endpoint_url:
                    # Custom endpoint format: https://endpoint/bucket/key
                    prefix = f"{settings.s3_endpoint_url.rstrip('/')}/{settings.s3_bucket}/"
                    if url_without_params.startswith(prefix):
                        return url_without_params[len(prefix):]
                else:
                    # Standard S3 format: https://bucket.s3.region.amazonaws.com/key
                    prefix = f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com/"
                    if url_without_params.startswith(prefix):
                        return url_without_params[len(prefix):]
            
            # Try generic patterns that work regardless of settings
            # Pattern 1: Standard S3 format - https://bucket.s3.region.amazonaws.com/key
            # Match: https://[bucket].s3.[region].amazonaws.com/[key]
            import re
            s3_pattern = r'https://([^/]+)\.s3\.([^/]+)\.amazonaws\.com/(.+)'
            match = re.match(s3_pattern, url_without_params)
            if match:
                return match.group(3)
            
            # Pattern 2: Custom endpoint format - https://endpoint/bucket/key
            # Match: https://[endpoint]/[bucket]/[key]
            # We need to identify where bucket ends and key starts
            # Common S3 key patterns: videos/, thumbnails/, storyboards/
            parsed = urlparse(url_without_params)
            path_parts = parsed.path.strip('/').split('/')
            
            # Look for known key prefixes
            known_prefixes = ['videos/', 'thumbnails/', 'storyboards/']
            for i, part in enumerate(path_parts):
                if any(part.startswith(prefix.rstrip('/')) for prefix in known_prefixes):
                    # Found a known prefix, everything from here is the key
                    return '/'.join(path_parts[i:])
            
            # Pattern 3: If path has 3+ parts, assume format is /bucket/prefix/key
            # and key starts from the third part
            if len(path_parts) >= 3:
                # Assume: /bucket/videos/job_id/file.mp4
                # Key would be: videos/job_id/file.mp4
                return '/'.join(path_parts[1:])
            
            # Pattern 4: If path has 2 parts, assume format is /bucket/key
            if len(path_parts) == 2:
                return path_parts[1]
            
            return None
        except Exception as e:
            print(f"Error extracting S3 key from URL: {e}")
            return None


