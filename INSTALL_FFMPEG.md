# Installing FFmpeg

FFmpeg is required for merging separate video and audio streams to get the best quality downloads. However, the app will work without it (using a single format, which may be lower quality).

## Windows Installation

### Option 1: Using Chocolatey (Recommended)
```powershell
# Install Chocolatey first if you don't have it: https://chocolatey.org/install
choco install ffmpeg
```

### Option 2: Manual Installation
1. Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/
2. Download the "ffmpeg-release-essentials.zip" file
3. Extract it to a folder (e.g., `C:\ffmpeg`)
4. Add `C:\ffmpeg\bin` to your system PATH:
   - Open System Properties → Environment Variables
   - Edit the "Path" variable
   - Add `C:\ffmpeg\bin`
   - Restart your terminal/IDE

### Option 3: Using winget (Windows 10/11)
```powershell
winget install ffmpeg
```

## Verify Installation

After installing, verify FFmpeg is available:
```powershell
ffmpeg -version
```

You should see version information. If you get "command not found", FFmpeg is not in your PATH.

## Restart Backend

After installing FFmpeg, restart the backend server for it to detect FFmpeg.

## Note

- **With FFmpeg**: Downloads will merge best video + best audio = highest quality
- **Without FFmpeg**: Downloads will use a single format (may be lower quality, but still works)

