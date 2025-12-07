"""
Video downloader using yt-dlp.
"""
import yt_dlp
import os
import asyncio
import shutil
from typing import Optional, Callable
from pathlib import Path
from app.config import settings

# Try to import imageio-ffmpeg for bundled FFmpeg binaries
try:
    import imageio_ffmpeg
    IMAGEIO_FFMPEG_AVAILABLE = True
except ImportError:
    IMAGEIO_FFMPEG_AVAILABLE = False


class VideoDownloader:
    """Handles video downloads using yt-dlp."""
    
    def __init__(self):
        self.metadata = {}
        self.temp_dir = Path(settings.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_available = self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is installed and available."""
        # First check custom path if configured
        if settings.ffmpeg_path and Path(settings.ffmpeg_path).exists():
            return True
        # Then check system PATH
        if shutil.which('ffmpeg') is not None:
            return True
        # Finally check if imageio-ffmpeg is available (includes FFmpeg binaries)
        if IMAGEIO_FFMPEG_AVAILABLE:
            try:
                ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
                if ffmpeg_path and Path(ffmpeg_path).exists():
                    return True
            except Exception:
                pass
        return False
    
    def _get_ffmpeg_path(self) -> Optional[str]:
        """Get FFmpeg executable path."""
        # Priority 1: Custom path from config
        if settings.ffmpeg_path and Path(settings.ffmpeg_path).exists():
            return str(Path(settings.ffmpeg_path).absolute())
        # Priority 2: System PATH
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            return ffmpeg_path
        # Priority 3: imageio-ffmpeg bundled binary
        if IMAGEIO_FFMPEG_AVAILABLE:
            try:
                ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
                if ffmpeg_path and Path(ffmpeg_path).exists():
                    return ffmpeg_path
            except Exception:
                pass
        return None
    
    def _progress_hook(self, d: dict, callback: Optional[Callable] = None, cancellation_check: Optional[Callable] = None):
        """Progress hook for yt-dlp."""
        # Check for cancellation
        if cancellation_check and cancellation_check():
            raise Exception("Download cancelled by user")
        
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            
            if total > 0:
                percent = (downloaded / total) * 100
            else:
                percent = 0
            
            speed = d.get('speed', 0)
            if speed:
                speed_str = f"{speed / 1024 / 1024:.2f}MB/s"
            else:
                speed_str = "Calculating..."
            
            eta = d.get('eta', 0)
            if eta and isinstance(eta, (int, float)) and eta > 0:
                # Convert to int to avoid float formatting issues
                eta_int = int(eta)
                eta_str = f"{eta_int // 60:02d}:{eta_int % 60:02d}"
            else:
                eta_str = "Calculating..."
            
            if callback:
                callback(percent, speed_str, eta_str)
        
        elif d['status'] == 'finished':
            if callback:
                callback(100.0, "Complete", "00:00")
    
    async def download(
        self,
        url: str,
        format_option: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        cancellation_check: Optional[Callable] = None,
        job_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Download video from URL.
        
        Args:
            url: Video URL
            format_option: Optional format selection
            progress_callback: Callback function(percent, speed, eta)
            start_time: Optional start time in seconds for trimming
            end_time: Optional end time in seconds for trimming
        
        Returns:
            Path to downloaded file or None if failed
        """
        # Create temporary directory for this download
        job_dir = self.temp_dir / "downloads"
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure yt-dlp options
        if format_option:
            format_str = format_option
        elif self.ffmpeg_available:
            # FFmpeg available - can merge video and audio
            format_str = 'bestvideo+bestaudio/best'
        else:
            # No FFmpeg - use single best format that doesn't require merging
            format_str = 'best[ext=mp4]/best'
            print("Warning: FFmpeg not found. Using single format (may be lower quality).")
        
        # Create progress hook with cancellation check
        def create_progress_hook():
            return lambda d: self._progress_hook(d, progress_callback, cancellation_check)
        
        # Use standard filename format: video_{job_id}.%(ext)s or video_{timestamp}.%(ext)s
        if job_id:
            outtmpl = str(job_dir / f'video_{job_id}.%(ext)s')
        else:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            outtmpl = str(job_dir / f'video_{timestamp}.%(ext)s')
        
        ydl_opts = {
            'format': format_str,
            'outtmpl': outtmpl,
            'progress_hooks': [create_progress_hook()],
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'writeinfojson': False,
            'writethumbnail': False,
            'force_keyframes_at_cuts': False,  # No trimming during download
            'print': ['after_move:filepath'],  # Print final filepath after post-processing
        }
        
        # Add SSL certificate verification setting
        if settings.no_check_certificate:
            ydl_opts['no_check_certificate'] = True
        
        # Add FFmpeg location if available (for yt-dlp to use)
        ffmpeg_path = self._get_ffmpeg_path()
        if ffmpeg_path:
            ffmpeg_path_obj = Path(ffmpeg_path).resolve()
            if ffmpeg_path_obj.exists():
                # yt-dlp's ffmpeg_location expects the directory containing ffmpeg
                # If it's a file, use its parent directory
                if ffmpeg_path_obj.is_file():
                    ffmpeg_dir = ffmpeg_path_obj.parent
                    # For imageio-ffmpeg, the executable has a non-standard name
                    # yt-dlp looks for 'ffmpeg.exe' in the directory
                    # Create a copy with the standard name if it doesn't exist
                    standard_ffmpeg = ffmpeg_dir / 'ffmpeg.exe'
                    if not standard_ffmpeg.exists() and ffmpeg_path_obj.name != 'ffmpeg.exe':
                        try:
                            # Copy the executable with standard name for yt-dlp to find
                            shutil.copy2(str(ffmpeg_path_obj), str(standard_ffmpeg))
                        except Exception as e:
                            # If copy fails, try symlink
                            try:
                                if hasattr(os, 'symlink'):
                                    os.symlink(ffmpeg_path_obj.name, str(standard_ffmpeg))
                            except Exception:
                                print(f"Warning: Could not create standard ffmpeg.exe name: {e}")
                                print(f"yt-dlp might not find FFmpeg. Using directory: {ffmpeg_dir}")
                    
                    ydl_opts['ffmpeg_location'] = str(ffmpeg_dir)
                    # Also set as environment variable for yt-dlp to find
                    os.environ['FFMPEG_BINARY'] = str(standard_ffmpeg) if standard_ffmpeg.exists() else str(ffmpeg_path_obj)
                elif ffmpeg_path_obj.is_dir():
                    ydl_opts['ffmpeg_location'] = str(ffmpeg_path_obj)
                else:
                    ydl_opts['ffmpeg_location'] = str(ffmpeg_path_obj.parent) if ffmpeg_path_obj.parent.exists() else str(ffmpeg_path_obj)
                
                # Log the source and verify
                # FFmpeg location configured
        
        # Add max file size limit
        max_bytes = settings.max_file_size_mb * 1024 * 1024
        ydl_opts['max_filesize'] = max_bytes
        
        try:
            # Run download in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            file_path = await loop.run_in_executor(
                None,
                self._download_sync,
                url,
                ydl_opts
            )
            
            return file_path
        
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
            # Don't treat cancellation as an error
            if error_msg and isinstance(error_msg, str) and "cancelled" in error_msg.lower():
                print(f"Download cancelled: {error_msg}")
                return None
            print(f"Download error: {e}")
            if progress_callback:
                progress_callback(0, "", f"Error: {error_msg}")
            return None
    
    def _download_sync(self, url: str, ydl_opts: dict) -> Optional[str]:
        """Synchronous download function."""
        downloaded_file = None
        
        # Store outtmpl as a string before yt-dlp potentially modifies ydl_opts
        outtmpl_str = ydl_opts.get('outtmpl', '')
        if not isinstance(outtmpl_str, str):
            # If outtmpl is not a string, try to extract it or use a default
            if isinstance(outtmpl_str, dict):
                outtmpl_str = outtmpl_str.get('default', '') or outtmpl_str.get('template', '')
            if not isinstance(outtmpl_str, str):
                # Fallback to a default pattern
                outtmpl_str = str(Path(ydl_opts.get('temp_dir', './tmp')).absolute() / 'downloads' / 'video_%(id)s.%(ext)s')
        
        def progress_hook(d):
            """Progress hook to capture the final filename after all post-processing."""
            nonlocal downloaded_file
            try:
                if not d or not isinstance(d, dict):
                    return
                
                status = d.get('status', '') if isinstance(d.get('status'), str) else ''
                
                # Capture filename after post-processing (merging/trimming) is complete
                # Priority: after_move > finished (after_move is the final file after merging)
                if status == 'after_move':
                    # Try multiple ways to get the filename
                    filename = None
                    if isinstance(d, dict):
                        filename = d.get('filename') or d.get('filepath')
                        if not filename:
                            info_dict = d.get('info_dict', {})
                            if isinstance(info_dict, dict):
                                filename = info_dict.get('_filename') or info_dict.get('filename') or info_dict.get('filepath')
                    
                    # Ensure filename is a string, not a dict or None
                    if filename and isinstance(filename, str):
                        downloaded_file = filename
                    elif filename and isinstance(filename, dict):
                        # If filename is a dict, try to extract the actual filename
                        downloaded_file = filename.get('filename') or filename.get('_filename') or filename.get('filepath')
                        if not downloaded_file or not isinstance(downloaded_file, str):
                            downloaded_file = str(filename) if filename else None
                elif status == 'finished':
                    # Only capture from 'finished' if we don't already have a filename from 'after_move'
                    # This is the intermediate file before merging
                    if downloaded_file is None:
                        filename = None
                        if isinstance(d, dict):
                            filename = d.get('filename') or d.get('filepath')
                            if not filename:
                                info_dict = d.get('info_dict', {})
                                if isinstance(info_dict, dict):
                                    filename = info_dict.get('_filename') or info_dict.get('filename') or info_dict.get('filepath')
                        
                        # Only store if it's a string and we don't have a final filename yet
                        if filename and isinstance(filename, str):
                            downloaded_file = filename
            except Exception as e:
                # Safely handle any errors in the progress hook
                try:
                    error_str = str(e) if e and isinstance(e, Exception) else "Unknown error in progress hook"
                    print(f"Error in progress_hook: {error_str}")
                except Exception:
                    print("Error in progress_hook: Could not format error message")
                # Don't fail the download if the hook has an error
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Extract info first to get metadata
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    raise Exception("Could not extract video information. The URL may be invalid or the video may be unavailable.")
                
                # Extract width and height
                width = info.get('width')
                height = info.get('height')
                
                # If not available, try to extract from resolution string
                if not width or not height:
                    resolution = info.get('resolution', '')
                    if resolution and 'x' in resolution:
                        try:
                            parts = resolution.split('x')
                            if len(parts) == 2:
                                width = int(parts[0]) if not width else width
                                height = int(parts[1]) if not height else height
                        except (ValueError, IndexError):
                            pass
                
                self.metadata = {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'format': info.get('format', 'Unknown'),
                    'filesize': info.get('filesize', 0),
                    'ext': info.get('ext', 'mp4'),
                    'width': width,
                    'height': height,
                }
                
                # Now download (progress hooks are already in ydl_opts)
                # Add our hook to capture filename
                original_hooks = ydl_opts.get('progress_hooks', [])
                ydl_opts['progress_hooks'] = original_hooks + [progress_hook]
                
                # Create a new YDL instance with updated hooks and download
                ydl_download = yt_dlp.YoutubeDL(ydl_opts)
                # Download and get the info_dict which contains the final filename
                download_info = ydl_download.extract_info(url, download=True)
                
                # Wait for post-processing (merging) to complete by checking file stability
                # The merger might still be running even after extract_info returns
                import time
                
                # Get the job directory to monitor files
                if isinstance(outtmpl_str, str):
                    job_dir = Path(outtmpl_str).parent
                else:
                    job_dir = self.temp_dir / "downloads"
                
                # Wait for files to stabilize (no changes for 1 second)
                # This ensures merging is complete
                max_wait_time = 10  # Maximum 10 seconds
                check_interval = 0.5  # Check every 0.5 seconds
                stable_time = 1.0  # File must be stable for 1 second
                waited_time = 0
                last_file_sizes = {}
                stable_since = None
                
                while waited_time < max_wait_time:
                    if job_dir.exists():
                        # Get all video files and their sizes
                        video_extensions = ['.webm', '.mp4', '.mkv', '.flv', '.avi', '.m4a', '.mp3', '.m4v', '.mov']
                        current_file_sizes = {}
                        for ext in video_extensions:
                            for f in job_dir.glob(f'*{ext}'):
                                if f.is_file():
                                    try:
                                        current_file_sizes[str(f)] = f.stat().st_size
                                    except:
                                        pass
                        
                        # Check if file sizes are stable (no changes)
                        if current_file_sizes == last_file_sizes:
                            if stable_since is None:
                                stable_since = time.time()
                            elif time.time() - stable_since >= stable_time:
                                break
                        else:
                            stable_since = None
                        
                        last_file_sizes = current_file_sizes.copy()
                    
                    time.sleep(check_interval)
                    waited_time += check_interval
                
                # After download and post-processing, find the most recently modified file
                # This is the most reliable method since post-processing changes the filename
                file_path = None
                
                # Get the job directory from outtmpl
                if isinstance(outtmpl_str, str):
                    job_dir = Path(outtmpl_str).parent
                else:
                    # Fallback to temp_dir
                    job_dir = self.temp_dir / "downloads"
                
                # Method 0: Try to get filename from info_dict after download
                # The info_dict should contain the final filename after all post-processing
                if download_info and isinstance(download_info, dict):
                    try:
                        # Try various keys that might contain the final filename
                        final_filename = (
                            download_info.get('_filename') or 
                            download_info.get('filename') or 
                            download_info.get('filepath') or
                            (download_info.get('requested_downloads', [{}])[0].get('filepath') if download_info.get('requested_downloads') else None)
                        )
                        
                        if final_filename and isinstance(final_filename, str):
                            final_path = Path(final_filename)
                            if final_path.exists():
                                file_path = str(final_path.absolute())
                                return file_path
                            else:
                                # Try relative to job_dir
                                resolved_path = (job_dir / final_filename).resolve()
                                if resolved_path.exists():
                                    file_path = str(resolved_path)
                                    return file_path
                                else:
                                    # Try to extract from the full path if it's in a subdirectory
                                    if '\\' in final_filename or '/' in final_filename:
                                        # Extract just the filename
                                        filename_only = Path(final_filename).name
                                        resolved_path = (job_dir / filename_only).resolve()
                                        if resolved_path.exists():
                                            file_path = str(resolved_path)
                                            return file_path
                    except Exception:
                        pass  # Silently continue to next method
                
                # Method 1: Find the most recently modified video file in the directory
                # This is the most reliable after post-processing
                # IMPORTANT: Filter out intermediate files (those with .fXXX pattern) to get the final merged file
                if not file_path:
                    try:
                        if job_dir.exists():
                            # Look for video files
                            video_extensions = ['.webm', '.mp4', '.mkv', '.flv', '.avi', '.m4a', '.mp3', '.m4v', '.mov']
                            all_files = []
                            for ext in video_extensions:
                                files = list(job_dir.glob(f'*{ext}'))
                                all_files.extend([f for f in files if f.is_file()])
                            
                            # Filter out intermediate files (those with .fXXX pattern like .f251, .f399, etc.)
                            # These are temporary files that get merged into the final file
                            final_files = []
                            for f in all_files:
                                stem = f.stem
                                # Check if this is an intermediate file (has .fXXX pattern)
                                if not ('.f' in stem and any(stem.endswith(f'.f{code}') for code in ['251', '399', '140', '141', '250', '249'])):
                                    final_files.append(f)
                            
                            # Prioritize final files (merged files) over intermediate ones
                            if final_files:
                                # Get the most recently modified final file (should be the merged file)
                                file_path = str(max(final_files, key=os.path.getmtime).absolute())
                            elif all_files:
                                # Fallback: if no final files found, use the most recent file anyway
                                file_path = str(max(all_files, key=os.path.getmtime).absolute())
                    except Exception as e:
                        # Continue to next method
                        pass
                
                # Method 2: Use the captured filename from progress hook (fallback)
                # But first, if the filename contains .fXXX pattern, try to find the merged version
                if not file_path and downloaded_file:
                    try:
                        # Ensure downloaded_file is a string, not a dict
                        if isinstance(downloaded_file, dict):
                            downloaded_file = downloaded_file.get('filename') or downloaded_file.get('_filename', '')
                        if downloaded_file and isinstance(downloaded_file, str):
                            downloaded_path = Path(downloaded_file)
                            
                            # If the filename has a format code (e.g., .f251.webm), try to find the merged version
                            # The merged file should be the same name without the .fXXX part
                            if '.f' in downloaded_path.stem and downloaded_path.stem.endswith(('.f251', '.f399', '.f140', '.f141')):
                                # Try to find the merged version (without .fXXX)
                                base_name = downloaded_path.stem
                                # Remove the .fXXX part
                                merged_stem = base_name.rsplit('.f', 1)[0] if '.f' in base_name else base_name
                                merged_path = downloaded_path.parent / f"{merged_stem}{downloaded_path.suffix}"
                                if merged_path.exists():
                                    file_path = str(merged_path.absolute())
                            
                            # If we still don't have a file, try the original captured filename
                            if not file_path:
                                if downloaded_path.exists():
                                    file_path = str(downloaded_path.absolute())
                                else:
                                    # Try to resolve relative path using stored outtmpl_str
                                    if isinstance(outtmpl_str, str):
                                        resolved_path = (job_dir / downloaded_file).resolve()
                                        if resolved_path.exists():
                                            file_path = str(resolved_path)
                    except Exception as e:
                        # Continue to next method
                        pass
                
                # Method 3: Use the outtmpl pattern to construct expected filename (fallback)
                if not file_path:
                    try:
                        # Use the stored outtmpl_str (captured before yt-dlp modified ydl_opts)
                        if isinstance(outtmpl_str, str):
                            # The merged file might have a different extension (e.g., .webm instead of .mp4)
                            # Extract the base name from outtmpl (remove %(ext)s placeholder)
                            base_pattern = outtmpl_str.replace('%(ext)s', '*').replace('%(title)s', '*').replace('%(id)s', '*')
                            base_name = Path(base_pattern).name
                            
                            # Look for files matching the pattern
                            matching_files = list(job_dir.glob(base_name))
                            if matching_files:
                                # Get the most recently modified file
                                file_path = str(max(matching_files, key=os.path.getmtime).absolute())
                    except Exception as e:
                        # Continue to next method
                        pass
                
                # Method 4: Last resort - any file in directory
                if not file_path:
                    try:
                        if job_dir.exists():
                            all_files = list(job_dir.glob('*'))
                            files = [f for f in all_files if f.is_file()]
                            if files:
                                file_path = str(max(files, key=os.path.getmtime).absolute())
                    except Exception as e:
                        pass
                
                if file_path:
                    # file_path is now a string, check if it exists
                    file_path_obj = Path(file_path)
                    if file_path_obj.exists():
                        return str(file_path)
                
                return None
            
            except yt_dlp.utils.DownloadError as e:
                # Safely convert exception to string
                try:
                    if e is None:
                        error_str = "Unknown download error"
                    else:
                        # Try to get error message from exception
                        error_str = str(e) if e else "Unknown download error"
                        # Ensure it's a string and not None
                        if not isinstance(error_str, str):
                            error_str = "Unknown download error"
                except Exception:
                    error_str = "Unknown download error"
                
                error_msg = error_str if error_str else "Unknown download error"
                # Ensure error_msg is a string before calling .lower()
                if not isinstance(error_msg, str):
                    error_msg = str(error_msg) if error_msg else "Unknown download error"
                # Check if it's an FFmpeg error and provide helpful message
                if error_msg and isinstance(error_msg, str) and len(error_msg) > 0:
                    error_msg_lower = error_msg.lower()
                    if "ffmpeg" in error_msg_lower and "not installed" in error_msg_lower:
                        error_msg = (
                            "FFmpeg is required for merging video and audio formats, but it's not installed.\n"
                            "Please install FFmpeg:\n"
                            "- Windows: Download from https://ffmpeg.org/download.html or use: choco install ffmpeg\n"
                            "- Linux: sudo apt-get install ffmpeg (or your package manager)\n"
                            "- Mac: brew install ffmpeg\n"
                            "Alternatively, the app will use a single format (may be lower quality) if FFmpeg is not available."
                        )
                    else:
                        error_msg = f"yt-dlp download error: {error_msg}" if error_msg else "yt-dlp download error: Unknown error"
                else:
                    error_msg = f"yt-dlp download error: {error_msg}" if error_msg else "yt-dlp download error: Unknown error"
                print(error_msg)
                raise Exception(error_msg if error_msg else "Unknown download error")
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
                
                error_msg = f"Unexpected download error: {error_str}" if error_str else "Unexpected download error: Unknown error"
                print(error_msg)
                raise Exception(error_msg if error_msg else "Unexpected download error: Unknown error")
    
    def get_metadata(self) -> dict:
        """Get metadata from the last download."""
        return self.metadata

