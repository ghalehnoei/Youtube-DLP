"""
Storyboard generator that detects scene changes and extracts frames.
"""
import subprocess as sp
import os
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Callable, Any
import asyncio
import tempfile


class StoryboardGenerator:
    """Generates storyboards by detecting scene changes and extracting frames."""
    
    def __init__(self):
        self.ffmpeg_path = self._get_ffmpeg_path()
        self.ffprobe_path = self._get_ffprobe_path()
    
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
    
    def _get_ffprobe_path(self) -> Optional[str]:
        """Get FFprobe executable path."""
        # Try imageio-ffmpeg binaries directory first
        try:
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            if ffmpeg_path:
                # ffprobe should be in the same directory as ffmpeg
                ffprobe_path = os.path.join(os.path.dirname(ffmpeg_path), 'ffprobe.exe')
                if os.path.exists(ffprobe_path):
                    return ffprobe_path
                # Also try without .exe extension (for Unix-like systems)
                ffprobe_path_no_ext = os.path.join(os.path.dirname(ffmpeg_path), 'ffprobe')
                if os.path.exists(ffprobe_path_no_ext):
                    return ffprobe_path_no_ext
        except ImportError:
            pass
        
        # Try system PATH
        try:
            result = sp.run(['ffprobe', '-version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                return 'ffprobe'
        except (FileNotFoundError, sp.TimeoutExpired):
            pass
        
        # Try common Windows locations
        if os.name == 'nt':
            common_paths = [
                r'C:\ffmpeg\bin\ffprobe.exe',
                r'C:\Program Files\ffmpeg\bin\ffprobe.exe',
            ]
            for path in common_paths:
                if os.path.exists(path):
                    return path
        
        return None
    
    def _get_video_duration(self, video_path: str) -> Optional[float]:
        """Get video duration in seconds."""
        if not self.ffprobe_path:
            return None
        
        try:
            cmd = [
                self.ffprobe_path,
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'json',
                video_path
            ]
            
            result = sp.run(cmd, capture_output=True, timeout=30, check=False)
            
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout.decode('utf-8'))
                if 'format' in data and 'duration' in data['format']:
                    return float(data['format']['duration'])
        except Exception:
            pass
        
        return None
    
    def detect_scene_changes(
        self,
        video_path: str,
        threshold: float = 0.3,
        progress_callback: Optional[Callable] = None
    ) -> List[float]:
        """
        Detect scene changes in video using FFmpeg's scene filter.
        
        Args:
            video_path: Path to video file (can be local file or URL)
            threshold: Scene change detection threshold (0.0-1.0, default: 0.3)
            progress_callback: Optional callback function(percent, message)
        
        Returns:
            List of timestamps (in seconds) where scene changes occur
        """
        if not self.ffmpeg_path:
            return []
        
        scene_times = []
        
        try:
            if progress_callback:
                progress_callback(10, "Detecting scene changes...")
            
            # Use FFmpeg's select filter to detect scene changes
            # The select filter with 'gt(scene,threshold)' outputs frames where scene change > threshold
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-vf', f"select='gt(scene,{threshold})',showinfo",
                '-f', 'null',
                '-'
            ]
            
            process = sp.Popen(
                cmd,
                stderr=sp.PIPE,
                stdout=sp.PIPE,
                universal_newlines=True,
                errors='replace'
            )
            
            stderr_output = []
            for line in process.stderr:
                stderr_output.append(line)
                # Parse showinfo output to extract timestamps
                # Format: n:0 pts:1234567 pts_time:12.345678
                match = re.search(r'pts_time:([\d.]+)', line)
                if match:
                    timestamp = float(match.group(1))
                    scene_times.append(timestamp)
            
            process.wait()
            
            # Always include the first frame (time 0)
            if not scene_times or scene_times[0] > 0.1:
                scene_times.insert(0, 0.0)
            
            # Sort and remove duplicates (within 0.1 seconds)
            scene_times = sorted(set(scene_times))
            filtered_times = [scene_times[0]]
            for t in scene_times[1:]:
                if t - filtered_times[-1] >= 0.1:  # At least 0.1 seconds apart
                    filtered_times.append(t)
            scene_times = filtered_times
            
            if progress_callback:
                progress_callback(30, f"Found {len(scene_times)} scene changes")
            
            return scene_times
            
        except Exception as e:
            print(f"Error detecting scene changes: {e}")
            return []
    
    async def extract_frames(
        self,
        video_path: str,
        timestamps: List[float],
        output_dir: Optional[str] = None,
        thumbnail_width: int = 320,
        thumbnail_height: int = 180,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract frames at specified timestamps.
        
        Args:
            video_path: Path to video file
            timestamps: List of timestamps (in seconds) to extract frames
            output_dir: Directory to save frames (optional, creates temp dir if not provided)
            thumbnail_width: Width of extracted frames
            thumbnail_height: Height of extracted frames
            progress_callback: Optional callback function(percent, message)
        
        Returns:
            List of dictionaries with 'timestamp', 'time_str', and 'image_path' keys
        """
        if not self.ffmpeg_path:
            return []
        
        if not timestamps:
            return []
        
        # Create output directory
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix='storyboard_')
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        frames = []
        total = len(timestamps)
        
        loop = asyncio.get_event_loop()
        
        for idx, timestamp in enumerate(timestamps):
            if progress_callback:
                progress = 30 + int((idx / total) * 60)
                progress_callback(progress, f"Extracting frame {idx + 1}/{total}...")
            
            # Format timestamp for filename
            hours = int(timestamp // 3600)
            minutes = int((timestamp % 3600) // 60)
            seconds = int(timestamp % 60)
            milliseconds = int((timestamp % 1) * 1000)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            filename = f"frame_{idx:04d}_{hours:02d}h{minutes:02d}m{seconds:02d}s.jpg"
            output_path = os.path.join(output_dir, filename)
            
            # Extract frame using FFmpeg
            cmd = [
                self.ffmpeg_path,
                '-y',
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-vf', f'scale={thumbnail_width}:{thumbnail_height}:force_original_aspect_ratio=decrease,pad={thumbnail_width}:{thumbnail_height}:(ow-iw)/2:(oh-ih)/2:black',
                '-q:v', '2',
                output_path
            ]
            
            try:
                def run_ffmpeg():
                    return sp.run(
                        cmd,
                        capture_output=True,
                        timeout=30,
                        check=False
                    )
                
                result = await loop.run_in_executor(None, run_ffmpeg)
                
                if result.returncode == 0 and os.path.exists(output_path):
                    frames.append({
                        'timestamp': timestamp,
                        'time_str': time_str,
                        'image_path': output_path,
                        'index': idx
                    })
                else:
                    print(f"Failed to extract frame at {timestamp}s")
            except Exception as e:
                print(f"Error extracting frame at {timestamp}s: {e}")
        
        return frames
    
    def create_storyboard_html(
        self,
        frames: List[Dict[str, Any]],
        output_path: str,
        video_title: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> bool:
        """
        Create an HTML storyboard page with all extracted frames.
        
        Args:
            frames: List of frame dictionaries from extract_frames()
            output_path: Path to save HTML file
            video_title: Optional title for the storyboard
        
        Returns:
            True if successful, False otherwise
        """
        try:
            html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Storyboard""" + (f" - {video_title}" if video_title else "") + """</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 2.5em;
            text-align: center;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1em;
        }
        .stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .stat-item {
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .storyboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .frame-card {
            background: #fff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            cursor: pointer;
        }
        .frame-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        }
        .frame-image {
            width: 100%;
            height: 180px;
            object-fit: cover;
            display: block;
        }
        .frame-info {
            padding: 15px;
            background: #f8f9fa;
        }
        .frame-number {
            font-weight: bold;
            color: #667eea;
            font-size: 1.1em;
            margin-bottom: 5px;
        }
        .frame-time {
            color: #666;
            font-size: 0.9em;
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.9);
            animation: fadeIn 0.3s;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        .modal-content {
            position: relative;
            margin: auto;
            padding: 20px;
            max-width: 90%;
            max-height: 90%;
            top: 50%;
            transform: translateY(-50%);
        }
        .modal-image {
            max-width: 100%;
            max-height: 80vh;
            display: block;
            margin: 0 auto;
            border-radius: 8px;
        }
        .close {
            position: absolute;
            top: 15px;
            right: 35px;
            color: #f1f1f1;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
        }
        .close:hover {
            color: #fff;
        }
        .frame-details {
            text-align: center;
            color: white;
            margin-top: 20px;
            font-size: 1.2em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📽️ Video Storyboard</h1>
        <div class="subtitle">Scene changes detected and extracted</div>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-value">""" + str(len(frames)) + """</div>
                <div class="stat-label">Scenes Detected</div>
            </div>
        </div>
        
        <div class="storyboard-grid">
"""
            
            # Add frame cards
            for frame in frames:
                # Use API endpoint if job_id is provided, otherwise use file:// URL
                if job_id:
                    image_url = f"/api/storyboard/{job_id}/frame/{frame['index']}"
                else:
                    # Fallback to file:// protocol for local files
                    image_path = frame['image_path']
                    if os.path.isabs(image_path):
                        image_url = f"file:///{image_path.replace(os.sep, '/')}"
                    else:
                        image_url = image_path
                
                html_content += f"""
            <div class="frame-card" onclick="openModal({frame['index']})">
                <img src="{image_url}" alt="Frame at {frame['time_str']}" class="frame-image" loading="lazy">
                <div class="frame-info">
                    <div class="frame-number">Shot #{frame['index'] + 1}</div>
                    <div class="frame-time">⏱️ {frame['time_str']}</div>
                </div>
            </div>
"""
            
            html_content += """
        </div>
    </div>
    
    <div id="imageModal" class="modal" onclick="closeModal()">
        <span class="close">&times;</span>
        <div class="modal-content">
            <img id="modalImage" class="modal-image" src="" alt="Enlarged frame">
            <div class="frame-details" id="modalDetails"></div>
        </div>
    </div>
    
    <script>
        const frames = """ + json.dumps(frames, indent=2) + """;
        
        function openModal(index) {
            const modal = document.getElementById('imageModal');
            const modalImg = document.getElementById('modalImage');
            const modalDetails = document.getElementById('modalDetails');
            const frame = frames[index];
            
            modal.style.display = 'block';
            """ + (f"const jobId = '{job_id}';" if job_id else "const jobId = null;") + """
            if (jobId) {
                modalImg.src = `/api/storyboard/${jobId}/frame/${index}`;
            } else {
                modalImg.src = frame.image_path.startsWith('file://') ? frame.image_path : 'file:///' + frame.image_path.replace(/\\\\/g, '/');
            }
            modalDetails.textContent = `Shot #${frame.index + 1} - Time: ${frame.time_str}`;
        }
        
        function closeModal() {
            document.getElementById('imageModal').style.display = 'none';
        }
        
        // Close modal on Escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                closeModal();
            }
        });
        
        // Prevent modal from closing when clicking on image
        document.querySelector('.modal-content').addEventListener('click', function(e) {
            e.stopPropagation();
        });
    </script>
</body>
</html>
"""
            
            # Write HTML file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return True
            
        except Exception as e:
            print(f"Error creating storyboard HTML: {e}")
            return False
    
    async def generate_storyboard(
        self,
        video_path: str,
        output_dir: Optional[str] = None,
        threshold: float = 0.3,
        thumbnail_width: int = 320,
        thumbnail_height: int = 180,
        progress_callback: Optional[Callable] = None,
        job_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a complete storyboard: detect scenes, extract frames, and create HTML.
        
        Args:
            video_path: Path to video file (can be local file or URL)
            output_dir: Directory to save storyboard files (optional)
            threshold: Scene change detection threshold (0.0-1.0, default: 0.3)
            thumbnail_width: Width of extracted frames
            thumbnail_height: Height of extracted frames
            progress_callback: Optional callback function(percent, message)
        
        Returns:
            Dictionary with 'html_path', 'frames_dir', 'frame_count', and 'frames' keys, or None if failed
        """
        if not self.ffmpeg_path:
            if progress_callback:
                progress_callback(0, "FFmpeg not found")
            return None
        
        if progress_callback:
            progress_callback(5, "Starting storyboard generation...")
        
        # Create output directory
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix='storyboard_')
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        frames_dir = os.path.join(output_dir, 'frames')
        os.makedirs(frames_dir, exist_ok=True)
        
        # Detect scene changes
        scene_times = self.detect_scene_changes(video_path, threshold, progress_callback)
        
        if not scene_times:
            if progress_callback:
                progress_callback(0, "No scene changes detected")
            return None
        
        # Extract frames
        frames = await self.extract_frames(
            video_path,
            scene_times,
            frames_dir,
            thumbnail_width,
            thumbnail_height,
            progress_callback
        )
        
        if not frames:
            if progress_callback:
                progress_callback(0, "Failed to extract frames")
            return None
        
        # Update frame paths to be relative to output_dir
        for frame in frames:
            # Keep absolute path for now, will be converted in HTML
            pass
        
        # Create HTML storyboard
        html_path = os.path.join(output_dir, 'storyboard.html')
        video_title = os.path.basename(video_path)
        
        if progress_callback:
            progress_callback(95, "Creating storyboard HTML...")
        
        success = self.create_storyboard_html(frames, html_path, video_title, job_id)
        
        if not success:
            if progress_callback:
                progress_callback(0, "Failed to create storyboard HTML")
            return None
        
        if progress_callback:
            progress_callback(100, "Storyboard generation complete!")
        
        return {
            'html_path': html_path,
            'frames_dir': frames_dir,
            'frame_count': len(frames),
            'frames': frames
        }

