# YouTube Downloader & Video Management System

A full-stack application for downloading videos from YouTube and other platforms, managing video libraries, creating playlists, and processing videos with FFmpeg.

## Features

- 🎥 **Download Videos**: Download videos from YouTube, Vimeo, and other platforms using `yt-dlp`
- 📤 **Upload Local Videos**: Upload local video files with automatic conversion to 1920x1080
- ✂️ **Video Splitting**: Trim videos by selecting start and end times
- 🖼️ **Thumbnail Generation**: Automatic thumbnail generation for all videos
- 📁 **Playlist Management**: Create and manage playlists
- 🔍 **Search & Filter**: Search videos and filter by playlists
- ☁️ **S3/MinIO Storage**: Store videos in S3-compatible storage (AWS S3 or MinIO)
- 🔄 **Real-time Updates**: WebSocket-based real-time job status updates
- 📱 **Modern UI**: YouTube-like interface built with React

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **yt-dlp** - Video downloader
- **FFmpeg** - Video processing (conversion, splitting, thumbnails)
- **boto3** - S3/MinIO integration
- **WebSocket** - Real-time communication

### Frontend
- **React** - UI framework
- **dash.js** - Video playback for DASH streams
- **Axios** - HTTP client

## Prerequisites

- Python 3.8+
- Node.js 14+
- FFmpeg (see [INSTALL_FFMPEG.md](INSTALL_FFMPEG.md))
- S3-compatible storage (AWS S3 or MinIO)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/Youtube-DLP.git
cd Youtube-DLP
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the project root:

```env
# S3/MinIO Configuration
S3_BUCKET=your-bucket-name
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_ENDPOINT_URL=http://localhost:9000  # For MinIO, omit for AWS S3

# Optional Settings
S3_URL_EXPIRATION=3600
MAX_FILE_SIZE_MB=5000
TEMP_DIR=./tmp/jobs
```

### 4. Frontend Setup

```bash
cd frontend
npm install
```

### 5. Start the Application

**Windows:**
```bash
start-servers.bat
```

**Linux/Mac:**
```bash
./start.sh
```

**Manual:**
```bash
# Terminal 1 - Backend
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm start
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Project Structure

```
Youtube-DLP/
├── backend/
│   ├── app/
│   │   ├── config.py           # Configuration settings
│   │   ├── downloader.py       # Video downloader
│   │   ├── uploader.py         # S3 uploader
│   │   ├── splitter.py         # Video splitter
│   │   ├── video_converter.py  # Video format converter
│   │   ├── thumbnail_generator.py  # Thumbnail generator
│   │   ├── metadata_store.py   # File metadata storage
│   │   ├── playlist_store.py   # Playlist storage
│   │   ├── job_manager.py      # Job management
│   │   └── validators.py       # URL validation
│   ├── main.py                 # FastAPI application
│   ├── metadata.json           # Video metadata (auto-generated)
│   └── playlists.json          # Playlists (auto-generated)
├── frontend/
│   ├── src/
│   │   ├── App.js              # Main React component
│   │   ├── App.css             # Styles
│   │   └── index.js            # Entry point
│   └── package.json
├── .env                        # Environment variables (create this)
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## API Documentation

Complete API documentation is available in [backend/API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md).

### Key Endpoints

- `POST /api/download` - Download video from URL
- `POST /api/upload` - Upload local video file
- `POST /api/split` - Split/trim video
- `GET /api/files` - Get all saved videos
- `POST /api/files` - Save video metadata
- `GET /api/playlists` - Get all playlists
- `POST /api/playlists` - Create playlist
- `WS /ws/{job_id}` - WebSocket for job status

## Usage

### Downloading a Video

1. Enter a video URL (YouTube, Vimeo, etc.)
2. Click "Download & Upload"
3. Monitor progress via WebSocket
4. Video is automatically converted if vertical
5. Thumbnail is generated automatically

### Uploading a Local Video

1. Click "Upload Video File"
2. Select a video file
3. File is automatically converted to 1920x1080
4. Uploaded to S3 storage

### Splitting a Video

1. Open a saved video
2. Use keyboard shortcuts:
   - Press `I` to set start time
   - Press `O` to set end time
3. Click "Clip" button
4. New split video is created and saved

### Creating Playlists

1. When saving a video, select or create a playlist
2. Use playlist filter in main menu to filter videos
3. Manage playlists via API

## Configuration

### S3/MinIO Setup

For MinIO (local development):
```env
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET=your-bucket
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
```

For AWS S3:
```env
S3_BUCKET=your-bucket
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
# Omit S3_ENDPOINT_URL
```

### FFmpeg Installation

See [INSTALL_FFMPEG.md](INSTALL_FFMPEG.md) for detailed instructions.

## Development

### Running in Development Mode

Backend with auto-reload:
```bash
cd backend
uvicorn main:app --reload
```

Frontend with hot-reload:
```bash
cd frontend
npm start
```

### Testing

```bash
# Backend tests (if available)
pytest

# Frontend tests (if available)
cd frontend
npm test
```

## Troubleshooting

### FFmpeg Not Found

- Ensure FFmpeg is installed and in PATH
- Or set `FFMPEG_PATH` in `.env` file

### S3 Connection Errors

- Verify S3 credentials in `.env`
- Check S3 endpoint URL (for MinIO)
- Ensure bucket exists

### Video Download Fails

- Check if URL is valid and accessible
- Verify video is not geo-blocked
- Check network connectivity

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
- Open an issue on GitHub
- Check [API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md) for API details

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video downloader
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [React](https://reactjs.org/) - UI library
