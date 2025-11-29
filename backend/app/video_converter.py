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
        self.ffprobe_path = self._get_ffprobe_path()
        if self.ffmpeg_path:
            print(f"VideoConverter initialized with FFmpeg at: {self.ffmpeg_path}")
        else:
            print("VideoConverter initialized but FFmpeg not found!")
        if self.ffprobe_path:
            print(f"VideoConverter initialized with FFprobe at: {self.ffprobe_path}")
    
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
            error_msg = "FFmpeg not found. Please install FFmpeg or ensure it's in your PATH."
            print(error_msg)
            if progress_callback:
                progress_callback(0, error_msg)
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
            
            print(f"Starting video conversion: {input_file_path} -> {output_file_path}")
            print(f"Using FFmpeg: {self.ffmpeg_path}")
            
            # Use ffprobe if available (more reliable), otherwise fall back to ffmpeg -i
            width = None
            height = None
            duration = None
            
            if self.ffprobe_path:
                # Use ffprobe with JSON output for reliable parsing
                probe_cmd = [
                    self.ffprobe_path,
                    '-v', 'error',
                    '-show_entries', 'stream=width,height,duration',
                    '-show_entries', 'format=duration',
                    '-of', 'json',
                    input_file_path
                ]
                
                try:
                    probe_result = sp.run(
                        probe_cmd,
                        capture_output=True,
                        timeout=30,
                        check=False
                    )
                    
                    if probe_result.returncode == 0 and probe_result.stdout:
                        import json
                        try:
                            probe_data = json.loads(probe_result.stdout.decode('utf-8'))
                            
                            # Get video stream info
                            if 'streams' in probe_data:
                                for stream in probe_data['streams']:
                                    if stream.get('codec_type') == 'video':
                                        width = stream.get('width')
                                        height = stream.get('height')
                                        if stream.get('duration'):
                                            duration = float(stream.get('duration'))
                                        break
                            
                            # Get format duration if not found in stream
                            if not duration and 'format' in probe_data:
                                format_duration = probe_data['format'].get('duration')
                                if format_duration:
                                    duration = float(format_duration)
                            
                            if width and height:
                                print(f"Detected video dimensions: {width}x{height}")
                            if duration:
                                print(f"Detected video duration: {duration:.2f} seconds")
                        except json.JSONDecodeError as e:
                            print(f"Warning: Failed to parse ffprobe JSON output: {e}")
                except Exception as e:
                    print(f"Warning: ffprobe failed, falling back to ffmpeg: {e}")
            
            # Fallback to ffmpeg -i if ffprobe not available or failed
            if (not width or not height) and self.ffmpeg_path:
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
                
                error_output = ""
                if probe_result.stderr:
                    stderr_str = probe_result.stderr.decode('utf-8', errors='ignore')
                    error_output = stderr_str
                    import re
                    
                    # Look for video stream info and dimensions
                    # Pattern: Video: ... 1920x1080 ...
                    if not width or not height:
                        dimension_match = re.search(r'(\d{2,5})x(\d{2,5})', stderr_str)
                        if dimension_match:
                            width = int(dimension_match.group(1))
                            height = int(dimension_match.group(2))
                            print(f"Detected video dimensions: {width}x{height}")
                    
                    # Look for duration: Duration: 00:01:23.45
                    if not duration:
                        duration_match = re.search(r'Duration:\s*(\d{2}):(\d{2}):(\d{2}\.\d{2})', stderr_str)
                        if duration_match:
                            hours = int(duration_match.group(1))
                            minutes = int(duration_match.group(2))
                            seconds = float(duration_match.group(3))
                            duration = hours * 3600 + minutes * 60 + seconds
                            print(f"Detected video duration: {duration:.2f} seconds")
                
                # Only fail if we couldn't extract dimensions AND there's a clear error
                if not width or not height:
                    if probe_result.returncode != 0 and error_output:
                        error_lower = error_output.lower()
                        if any(keyword in error_lower for keyword in ['no such file', 'cannot find', 'invalid', 'error', 'failed']):
                            error_msg = f"Failed to probe video: {error_output[:200]}"
                            print(error_msg)
                            if progress_callback:
                                progress_callback(0, "Failed to analyze video file")
                            return None
                    print("Warning: Could not extract video dimensions from probe, will use fallback scaling")
            
            if progress_callback:
                duration_msg = f" (Duration: {duration:.1f}s)" if duration else ""
                progress_callback(10, f"Converting video to 1920x1080...{duration_msg}")
            
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
            print(f"Running FFmpeg conversion command...")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._run_ffmpeg,
                cmd,
                progress_callback,
                cancellation_check,
                duration  # Pass duration for accurate progress calculation
            )
            
            print(f"FFmpeg conversion result: {result}")
            print(f"Output file exists: {os.path.exists(output_file_path) if output_file_path else False}")
            if output_file_path and os.path.exists(output_file_path):
                print(f"Output file size: {os.path.getsize(output_file_path)} bytes")
            
            if result and os.path.exists(output_file_path):
                # Verify the output file has content
                if os.path.getsize(output_file_path) > 0:
                    if progress_callback:
                        progress_callback(100, "Conversion complete!")
                    return output_file_path
                else:
                    error_msg = "Conversion failed: Output file is empty"
                    print(error_msg)
                    if progress_callback:
                        progress_callback(0, error_msg)
                    # Clean up empty file
                    try:
                        os.remove(output_file_path)
                    except:
                        pass
                    return None
            else:
                error_msg = "Conversion failed: FFmpeg returned an error or output file was not created"
                print(error_msg)
                if progress_callback:
                    progress_callback(0, error_msg)
                return None
                
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Conversion error: {str(e)}")
            return None
    
    def _run_ffmpeg(
        self,
        cmd: list,
        progress_callback: Optional[Callable] = None,
        cancellation_check: Optional[Callable] = None,
        duration: Optional[float] = None
    ) -> bool:
        """Run FFmpeg command synchronously."""
        stderr_lines = []
        try:
            process = sp.Popen(
                cmd,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                universal_newlines=True,
                bufsize=1,
                errors='replace'  # Handle encoding errors gracefully
            )
            
            # Monitor progress from stderr and capture all output
            last_progress = 0
            import threading
            import queue
            
            # Use a queue to read stderr in a separate thread to avoid blocking
            stderr_queue = queue.Queue()
            
            def read_stderr():
                try:
                    for line in iter(process.stderr.readline, ''):
                        if not line:
                            break
                        stderr_queue.put(line)
                except Exception:
                    pass
                finally:
                    stderr_queue.put(None)  # Signal end of stderr
            
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stderr_thread.start()
            
            # Process stderr lines
            process_finished = False
            while not process_finished:
                try:
                    line = stderr_queue.get(timeout=0.1)
                    if line is None:
                        # End of stderr stream
                        process_finished = True
                        break
                    
                    stderr_lines.append(line)
                    
                    if cancellation_check and cancellation_check():
                        process.terminate()
                        return False
                    
                    # Parse FFmpeg progress (time=00:00:05.00)
                    if 'time=' in line:
                        try:
                            import re
                            time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2}\.\d{2})', line)
                            if time_match:
                                hours = int(time_match.group(1))
                                minutes = int(time_match.group(2))
                                seconds = float(time_match.group(3))
                                current_time = hours * 3600 + minutes * 60 + seconds
                                
                                # Calculate accurate progress if we have duration
                                if duration and duration > 0:
                                    current_progress = min((current_time / duration) * 100, 95)
                                    # Update progress more frequently (every 1% change or every 0.5 seconds)
                                    if current_progress >= last_progress + 1 and progress_callback:
                                        time_str = f"{int(current_time // 60)}:{int(current_time % 60):02d}"
                                        duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}"
                                        progress_callback(current_progress, f"Converting... {int(current_progress)}% ({time_str}/{duration_str})")
                                        last_progress = current_progress
                                else:
                                    # Fallback: estimate progress (rough, since we don't know total duration)
                                    # Update every 2% to show some progress
                                    current_progress = min(last_progress + 2, 95)
                                    if current_progress > last_progress and progress_callback:
                                        time_str = f"{int(current_time // 60)}:{int(current_time % 60):02d}"
                                        progress_callback(current_progress, f"Converting... {int(current_progress)}% ({time_str})")
                                        last_progress = current_progress
                        except:
                            pass
                except queue.Empty:
                    # Check if process is still running
                    if process.poll() is not None:
                        # Process finished, but wait a bit for stderr thread to finish
                        import time
                        time.sleep(0.2)
                        # Try to read any remaining stderr
                        try:
                            while True:
                                line = stderr_queue.get_nowait()
                                if line is None:
                                    process_finished = True
                                    break
                                stderr_lines.append(line)
                        except queue.Empty:
                            process_finished = True
                            break
            
            # Wait for process to complete (should already be done)
            process.wait()
            
            # Read any remaining stderr that might have been queued
            try:
                while True:
                    line = stderr_queue.get_nowait()
                    if line is None:
                        break
                    stderr_lines.append(line)
            except queue.Empty:
                pass
            
            # If FFmpeg failed, log the error
            if process.returncode != 0:
                error_output = ''.join(stderr_lines)
                print(f"FFmpeg error (return code {process.returncode}):")
                print(f"Command: {' '.join(cmd)}")
                print(f"Error output: {error_output}")
                if progress_callback:
                    # Extract a meaningful error message
                    error_msg = "Conversion failed"
                    if error_output:
                        # Look for common error patterns
                        if "No such file" in error_output or "cannot find" in error_output.lower():
                            error_msg = "Input file not found"
                        elif "Invalid data" in error_output or "Invalid" in error_output:
                            error_msg = "Invalid video format"
                        elif "codec" in error_output.lower():
                            error_msg = "Codec error - video format may not be supported"
                        else:
                            # Get last few lines of error
                            error_lines = [l.strip() for l in error_output.split('\n') if l.strip()]
                            if error_lines:
                                error_msg = error_lines[-1][:100]  # Last error line, truncated
                    progress_callback(0, error_msg)
            
            return process.returncode == 0
            
        except Exception as e:
            error_output = ''.join(stderr_lines) if stderr_lines else str(e)
            print(f"FFmpeg execution error: {e}")
            print(f"Command: {' '.join(cmd)}")
            if error_output:
                print(f"Error output: {error_output}")
            if progress_callback:
                progress_callback(0, f"FFmpeg error: {str(e)}")
            return False

