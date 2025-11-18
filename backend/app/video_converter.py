"""
Video converter using FFmpeg to convert videos to 1920x1080 horizontal format.
"""
import subprocess as sp
import os
from pathlib import Path
from typing import Optional, Callable
import asyncio


class VideoConverter:
    """Converts videos to 1920x1080 horizontal format using FFmpeg."""
    
    def __init__(self):
        self.ffmpeg_path = self._get_ffmpeg_path()
    
    def _get_ffmpeg_path(self) -> Optional[str]:
        """Get FFmpeg executable path."""
        # Try imageio-ffmpeg first
        try:
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            if ffmpeg_path and os.path.exists(ffmpeg_path):
                return ffmpeg_path
        except ImportError:
            pass
        
        # Try system PATH
        try:
            result = sp.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                return 'ffmpeg'
        except (FileNotFoundError, sp.TimeoutExpired):
            pass
        
        # Try common Windows locations
        if os.name == 'nt':
            common_paths = [
                r'C:\ffmpeg\bin\ffmpeg.exe',
                r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
            ]
            for path in common_paths:
                if os.path.exists(path):
                    return path
        
        return None
    
    async def convert_to_horizontal(
        self,
        input_file_path: str,
        output_file_path: Optional[str] = None,
        target_width: int = 1920,
        target_height: int = 1080,
        progress_callback: Optional[Callable] = None,
        cancellation_check: Optional[Callable] = None,
        job_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert video to horizontal 1920x1080 format.
        
        Args:
            input_file_path: Path to input video file
            output_file_path: Output file path (optional)
            target_width: Target width (default: 1920)
            target_height: Target height (default: 1080)
            progress_callback: Callback function(percent, message)
            cancellation_check: Function to check if operation should be cancelled
            job_id: Job ID for temp file naming
        
        Returns:
            Path to converted video file, or None if failed
        """
        if not self.ffmpeg_path:
            if progress_callback:
                progress_callback(0, "FFmpeg not found")
            return None
        
        if not os.path.exists(input_file_path):
            if progress_callback:
                progress_callback(0, f"Input file not found: {input_file_path}")
            return None
        
        # Generate output path if not provided
        if not output_file_path:
            if job_id:
                output_file_path = str(Path(input_file_path).parent / f"converted_{job_id}.mp4")
            else:
                input_path = Path(input_file_path)
                output_file_path = str(input_path.parent / f"{input_path.stem}_converted.mp4")
        
        output_path = Path(output_file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # First, probe video dimensions
            if progress_callback:
                progress_callback(5, "Analyzing video...")
            
            probe_cmd = [
                self.ffmpeg_path,
                '-i', input_file_path,
                '-hide_banner'
            ]
            
            probe_result = sp.run(
                probe_cmd,
                capture_output=True,
                timeout=30,
                check=False
            )
            
            # Extract dimensions from probe output
            width = None
            height = None
            if probe_result.stderr:
                stderr_str = probe_result.stderr.decode('utf-8', errors='ignore')
                # Look for video stream info
                import re
                # Pattern: Video: ... 1920x1080 ...
                dimension_match = re.search(r'(\d{2,5})x(\d{2,5})', stderr_str)
                if dimension_match:
                    width = int(dimension_match.group(1))
                    height = int(dimension_match.group(2))
            
            if progress_callback:
                progress_callback(10, "Converting video to 1920x1080...")
            
            # Build FFmpeg command for conversion
            cmd = [
                self.ffmpeg_path,
                '-y',  # Overwrite output
                '-i', input_file_path,
            ]
            
            # Calculate scale and pad to fit 1920x1080
            # Maintain aspect ratio, center the video
            if width and height:
                # Calculate scale to fit within target dimensions
                scale_ratio_w = target_width / width
                scale_ratio_h = target_height / height
                scale_ratio = min(scale_ratio_w, scale_ratio_h)  # Use smaller ratio to fit
                
                scaled_width = int(width * scale_ratio)
                scaled_height = int(height * scale_ratio)
                
                # Calculate padding (letterboxing/pillarboxing)
                pad_x = (target_width - scaled_width) // 2
                pad_y = (target_height - scaled_height) // 2
                
                # Video filter: scale and pad
                vf = f"scale={scaled_width}:{scaled_height},pad={target_width}:{target_height}:{pad_x}:{pad_y}:black"
            else:
                # If dimensions unknown, use scale to fit
                vf = f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black"
            
            cmd.extend([
                '-vf', vf,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',  # Web optimization
                output_file_path
            ])
            
            # Run FFmpeg conversion
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._run_ffmpeg,
                cmd,
                progress_callback,
                cancellation_check
            )
            
            if result and os.path.exists(output_file_path):
                if progress_callback:
                    progress_callback(100, "Conversion complete")
                return output_file_path
            else:
                if progress_callback:
                    progress_callback(0, "Conversion failed")
                return None
                
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Conversion error: {str(e)}")
            return None
    
    def _run_ffmpeg(
        self,
        cmd: list,
        progress_callback: Optional[Callable] = None,
        cancellation_check: Optional[Callable] = None
    ) -> bool:
        """Run FFmpeg command synchronously."""
        try:
            process = sp.Popen(
                cmd,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor progress from stderr
            last_progress = 0
            for line in process.stderr:
                if cancellation_check and cancellation_check():
                    process.terminate()
                    return False
                
                # Parse FFmpeg progress (time=00:00:05.00)
                if 'time=' in line:
                    try:
                        import re
                        time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2}\.\d{2})', line)
                        if time_match:
                            # Estimate progress (rough, since we don't know total duration)
                            # Update every 5% to avoid spam
                            current_progress = min(last_progress + 5, 95)
                            if current_progress > last_progress and progress_callback:
                                progress_callback(current_progress, "Converting...")
                                last_progress = current_progress
                    except:
                        pass
            
            process.wait()
            return process.returncode == 0
            
        except Exception as e:
            return False

