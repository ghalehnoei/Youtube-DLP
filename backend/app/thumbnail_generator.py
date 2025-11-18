"""
Thumbnail generator using FFmpeg.
"""
import subprocess as sp
import os
from pathlib import Path
from typing import Optional
import tempfile


class ThumbnailGenerator:
    """Generates thumbnails from video files using FFmpeg."""
    
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
    
    def generate_thumbnail(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        time_offset: float = 1.0,
        width: int = 320,
        height: int = 180
    ) -> Optional[str]:
        """
        Generate a thumbnail from a video file.
        
        Args:
            video_path: Path to video file (can be local file or URL)
            output_path: Output thumbnail path (optional, will create temp file if not provided)
            time_offset: Time in seconds to extract frame (default: 1.0)
            width: Thumbnail width (default: 320)
            height: Thumbnail height (default: 180)
        
        Returns:
            Path to generated thumbnail file, or None if failed
        """
        if not self.ffmpeg_path:
            return None
        
        if output_path is None:
            # Create temporary file
            temp_dir = Path(tempfile.gettempdir())
            output_path = str(temp_dir / f"thumbnail_{os.urandom(8).hex()}.jpg")
        
        try:
            # FFmpeg command to extract frame and resize
            cmd = [
                self.ffmpeg_path,
                '-y',  # Overwrite output file
                '-ss', str(time_offset),  # Seek to time offset
                '-i', video_path,  # Input video
                '-vframes', '1',  # Extract only 1 frame
                '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',  # Scale and pad
                '-q:v', '2',  # High quality JPEG
                output_path
            ]
            
            result = sp.run(
                cmd,
                capture_output=True,
                timeout=30,
                check=False
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                return output_path
            else:
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except:
                        pass
                return None
                
        except Exception as e:
            if output_path and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            return None

