
"""
Video splitter/trimmer using FFmpeg.
"""
import os
import asyncio
import subprocess
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


class VideoSplitter:
    """Handles video splitting/trimming using FFmpeg."""
    
    def __init__(self):
        self.temp_dir = Path(settings.temp_dir or "./tmp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_available = self._check_ffmpeg()
        self.ffmpeg_path = self._get_ffmpeg_path() if self.ffmpeg_available else None
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available."""
        ffmpeg_path = self._get_ffmpeg_path()
        if ffmpeg_path:
            try:
                result = subprocess.run(
                    [ffmpeg_path, "-version"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            except Exception:
                return False
        return False
    
    def _get_ffmpeg_path(self) -> Optional[str]:
        """Get FFmpeg executable path."""
        # Priority: custom path > imageio-ffmpeg > system PATH
        
        # 1. Check custom path from settings
        if settings.ffmpeg_path:
            custom_path = Path(settings.ffmpeg_path)
            if custom_path.exists() and custom_path.is_file():
                return str(custom_path.absolute())
            # If it's a directory, look for ffmpeg.exe inside
            if custom_path.is_dir():
                ffmpeg_exe = custom_path / "ffmpeg.exe" if os.name == 'nt' else custom_path / "ffmpeg"
                if ffmpeg_exe.exists():
                    return str(ffmpeg_exe.absolute())
        
        # 2. Check imageio-ffmpeg bundled binary
        if IMAGEIO_FFMPEG_AVAILABLE:
            try:
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                if ffmpeg_exe and os.path.exists(ffmpeg_exe):
                    return ffmpeg_exe
            except Exception:
                pass
        
        # 3. Check system PATH
        ffmpeg_name = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"
        ffmpeg_path = shutil.which(ffmpeg_name)
        if ffmpeg_path:
            return ffmpeg_path
        
        return None
    
    async def split(
        self,
        input_file_path: str,
        start_time: float,
        end_time: Optional[float] = None,
        output_file_path: Optional[str] = None,
        convert_to_horizontal: bool = False,
        progress_callback: Optional[Callable] = None,
        cancellation_check: Optional[Callable] = None,
        job_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Split/trim a video file.
        
        Args:
            input_file_path: Path to input video file
            start_time: Start time in seconds
            end_time: End time in seconds (optional, if None, trims to end)
            output_file_path: Path for output file (optional, auto-generated if None)
            progress_callback: Optional callback for progress updates
            cancellation_check: Optional function to check if operation should be cancelled
            job_id: Optional job ID for temp file naming
        
        Returns:
            Path to output file, or None if failed
        """
        if not self.ffmpeg_available:
            raise Exception("FFmpeg is required for video splitting but is not available.")
        
        # Check if input is a URL (HTTP/HTTPS) or local file path
        is_url = input_file_path.startswith('http://') or input_file_path.startswith('https://')
        
        if is_url:
            # For URLs, FFmpeg can handle them directly
            input_source = input_file_path
        else:
            # For local files, check if it exists
            input_path = Path(input_file_path)
            if not input_path.exists():
                raise Exception(f"Input file does not exist: {input_file_path}")
            input_source = str(input_path.absolute())
        
        # Generate output path if not provided
        if not output_file_path:
            if job_id:
                output_file_path = str(self.temp_dir / "downloads" / f"video_{job_id}.mp4")
            else:
                if is_url:
                    # For URLs, use temp directory
                    output_file_path = str(self.temp_dir / "downloads" / f"video_trimmed_temp.mp4")
                else:
                    # Use input filename with _trimmed suffix
                    input_path = Path(input_file_path)
                    output_file_path = str(input_path.parent / f"{input_path.stem}_trimmed{input_path.suffix}")
        
        output_path = Path(output_file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build FFmpeg command
        # -ss before -i for faster seeking (input seeking)
        # -t for duration or -to for end time
        cmd = [self.ffmpeg_path, "-y"]  # -y to overwrite output
        
        # Add start time (input seeking - faster)
        if start_time > 0:
            cmd.extend(["-ss", str(start_time)])
        
        # Use input source (URL or local path)
        cmd.extend(["-i", input_source])
        
        # Add end time or duration
        if end_time is not None and end_time > start_time:
            duration = end_time - start_time
            cmd.extend(["-t", str(duration)])
        elif start_time > 0:
            # If only start time, we still need to specify something
            # Just let it go to the end
            pass
        
        # Only convert orientation if explicitly requested
        if convert_to_horizontal:
            # Get video dimensions first
            import subprocess as sp
            probe_cmd = [
                self.ffmpeg_path, "-i", input_source,
                "-hide_banner"
            ]
            try:
                probe_result = sp.run(
                    probe_cmd,
                    capture_output=True,
                    timeout=30  # Increased timeout for URL access
                )
                
                # Parse dimensions from output (FFmpeg outputs to stderr)
                import re
                width = None
                height = None
                output = probe_result.stderr.decode('utf-8', errors='ignore') if probe_result.stderr else ''
                if not output:
                    output = probe_result.stdout.decode('utf-8', errors='ignore') if probe_result.stdout else ''
                
                # Try multiple patterns to find dimensions
                for line in output.split('\n'):
                    # Look for resolution patterns
                    # Pattern 1: "1920x1080" in Video: line
                    if 'Video:' in line or 'Stream #' in line:
                        match = re.search(r'(\d+)x(\d+)', line)
                        if match:
                            width = int(match.group(1))
                            height = int(match.group(2))
                            break
                    # Pattern 2: Look for resolution in any line
                    match = re.search(r'(\d{3,5})x(\d{3,5})', line)
                    if match:
                        potential_width = int(match.group(1))
                        potential_height = int(match.group(2))
                        # Reasonable video dimensions check
                        if 100 <= potential_width <= 7680 and 100 <= potential_height <= 4320:
                            if not width or not height:  # Use first reasonable match
                                width = potential_width
                                height = potential_height
                
                if width and height and height > width:
                    # Vertical video - convert to horizontal with letterboxing
                    # Target: 16:9 aspect ratio (common horizontal format)
                    target_width = 1920  # Standard HD width
                    target_height = 1080  # Standard HD height
                    
                    # Calculate scale to fit vertical video in horizontal frame
                    # Maintain aspect ratio, center the video
                    scale_w = width
                    scale_h = height
                    
                    # Scale to fit within target dimensions while maintaining aspect
                    if scale_h > target_height:
                        scale_ratio = target_height / scale_h
                        scale_w = int(scale_w * scale_ratio)
                        scale_h = target_height
                    
                    # Calculate padding (letterboxing)
                    pad_x = (target_width - scale_w) // 2
                    pad_y = (target_height - scale_h) // 2
                    
                    # Use filter_complex for scaling and padding
                    cmd.extend([
                        "-vf", f"scale={scale_w}:{scale_h},pad={target_width}:{target_height}:{pad_x}:{pad_y}:black",
                        "-c:v", "libx264",
                        "-preset", "medium",
                        "-crf", "23",
                        "-c:a", "aac",
                        "-b:a", "128k"
                    ])
                else:
                    # Not vertical or dimensions not found, use codec copy (no conversion needed)
                    cmd.extend([
                        "-c", "copy",
                        "-avoid_negative_ts", "make_zero"
                    ])
            except Exception as e:
                # If probe fails, fall back to codec copy (no conversion)
                print(f"Warning: Could not probe video dimensions: {e}. Using codec copy.")
                cmd.extend([
                    "-c", "copy",
                    "-avoid_negative_ts", "make_zero"
                ])
        else:
            # No conversion requested - just split with codec copy (preserves original orientation)
            cmd.extend([
                "-c", "copy",  # Copy both video and audio codecs
                "-avoid_negative_ts", "make_zero"  # Handle timestamp issues
            ])
        
        cmd.append(str(output_path.absolute()))
        
        # Run FFmpeg in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._split_sync,
            cmd,
            progress_callback,
            cancellation_check
        )
        
        if result and output_path.exists():
            return str(output_path.absolute())
        return None
    
    def _split_sync(
        self,
        cmd: list,
        progress_callback: Optional[Callable] = None,
        cancellation_check: Optional[Callable] = None
    ) -> bool:
        """Synchronous split function."""
        try:
            # Start FFmpeg process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor progress (FFmpeg outputs progress to stderr)
            if progress_callback:
                # Parse FFmpeg output for progress
                # FFmpeg outputs: frame=  123 fps= 45 q=28.0 size=    1024kB time=00:00:05.00 bitrate=1677.7kbits/s
                import re
                duration_pattern = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2})\.\d{2}")
                time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.\d{2}")
                
                duration_seconds = None
                
                for line in process.stderr:
                    if cancellation_check and cancellation_check():
                        process.terminate()
                        return False
                    
                    # Try to extract duration
                    duration_match = duration_pattern.search(line)
                    if duration_match:
                        hours, mins, secs = map(int, duration_match.groups())
                        duration_seconds = hours * 3600 + mins * 60 + secs
                    
                    # Try to extract current time
                    time_match = time_pattern.search(line)
                    if time_match and duration_seconds:
                        hours, mins, secs = map(int, time_match.groups())
                        current_seconds = hours * 3600 + mins * 60 + secs
                        progress = (current_seconds / duration_seconds) * 100 if duration_seconds > 0 else 0
                        progress_callback(progress, f"Processing... {current_seconds:.1f}s / {duration_seconds:.1f}s")
            
            # Wait for process to complete
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore') if isinstance(stderr, bytes) else str(stderr)
                print(f"FFmpeg error (return code {process.returncode}): {error_msg}")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error splitting video: {e}")
            return False

