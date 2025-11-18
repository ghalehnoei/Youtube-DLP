#!/usr/bin/env python3
"""Quick script to check FFmpeg installation and PATH."""
import shutil
import os
import sys

print("Checking for FFmpeg...")
print(f"Python executable: {sys.executable}")
print(f"PATH: {os.environ.get('PATH', 'Not set')[:200]}...")
print()

# Check using shutil.which (same method as the app)
ffmpeg_path = shutil.which('ffmpeg')
if ffmpeg_path:
    print(f"✓ FFmpeg found at: {ffmpeg_path}")
    print(f"  Full path: {os.path.abspath(ffmpeg_path)}")
    
    # Try to get version
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"  Version: {version_line}")
    except:
        print("  (Could not get version)")
else:
    print("X FFmpeg not found in PATH")
    print()
    print("Common installation locations to check:")
    print("  - C:\\ffmpeg\\bin\\ffmpeg.exe")
    print("  - C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe")
    print("  - Check where you installed FFmpeg")
    print()
    print("To fix:")
    print("  1. Find where FFmpeg is installed")
    print("  2. Add the 'bin' folder to your system PATH")
    print("  3. Restart your terminal and backend")

