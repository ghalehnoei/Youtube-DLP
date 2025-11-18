# Quick Start Guide

## Prerequisites

- Python 3.8+
- Node.js 16+ and npm
- AWS S3 bucket and credentials
- FFmpeg (usually installed with yt-dlp)

## 5-Minute Setup

### 1. Configure Environment

Copy the example environment file:
```bash
cp env.example .env
```

Edit `.env` with your S3 credentials:
```env
S3_BUCKET=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_REGION=us-east-1
```

### 2. Install Backend Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 4. Start Backend

From project root:
```bash
cd backend
python main.py
```

Backend runs on `http://localhost:8000`

### 5. Start Frontend

In a new terminal:
```bash
cd frontend
npm start
```

Frontend runs on `http://localhost:3000`

## Using the Application

1. Open `http://localhost:3000` in your browser
2. Paste a video URL (YouTube, Vimeo, etc.)
3. Click "Download & Upload"
4. Watch real-time progress
5. Copy the S3 URL when complete

## Alternative: Use Startup Scripts

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

## Docker Deployment

```bash
# Build and run
docker-compose up --build

# Or build manually
docker build -t video-download-s3 .
docker run -p 8000:8000 \
  -e S3_BUCKET=your-bucket \
  -e AWS_ACCESS_KEY_ID=your-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  video-download-s3
```

## Troubleshooting

**Backend won't start:**
- Check that `.env` file exists and has valid S3 credentials
- Ensure Python 3.8+ is installed
- Verify all dependencies are installed: `pip install -r requirements.txt`

**Frontend won't connect:**
- Ensure backend is running on port 8000
- Check browser console for errors
- Verify CORS settings in `backend/main.py`

**Download fails:**
- Ensure FFmpeg is installed
- Check that the video URL is valid and accessible
- Verify yt-dlp is up to date: `pip install --upgrade yt-dlp`

**Upload fails:**
- Verify S3 credentials are correct
- Check S3 bucket permissions
- Ensure bucket exists in the specified region

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Configure `ALLOWED_HOSTS` in `.env` to restrict domains
- Adjust `MAX_FILE_SIZE_MB` for file size limits
- Set `S3_PUBLIC_URLS=true` for public S3 URLs (not recommended for production)


