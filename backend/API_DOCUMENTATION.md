# Backend API Documentation

Complete API reference for the YouTube Downloader & Video Management Service.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication. In production, you should implement proper authentication.

---

## Endpoints

### Health Check

#### `GET /`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "message": "Video Download & S3 Upload Service"
}
```

---

## Video Download & Upload

### Download Video from URL

#### `POST /api/download`

Start a video download job from a URL (YouTube, Vimeo, etc.).

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "format": "bestvideo+bestaudio"  // Optional
}
```

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "started",
  "message": "Download job started. Connect to WebSocket to track progress."
}
```

**Features:**
- Automatically detects vertical videos and converts to 1920x1080 horizontal
- Generates thumbnails automatically
- Uploads to S3/MinIO storage

---

### Upload Local Video File

#### `POST /api/upload`

Upload a local video file, convert to 1920x1080, and upload to S3.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: File upload (video file)

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "started",
  "message": "Upload job started. Connect to WebSocket to track progress."
}
```

**Features:**
- Converts all videos to 1920x1080 horizontal format
- Generates thumbnails automatically
- Uploads to S3/MinIO storage

---

### Split/Trim Video

#### `POST /api/split`

Split/trim a video from S3 by specifying start and end times.

**Request Body:**
```json
{
  "s3_url": "https://s3-url/video.mp4",
  "start_time": 10.5,
  "end_time": 30.0,
  "convert_to_horizontal": false,  // Optional, defaults to false
  "original_metadata": {  // Optional, preserves original metadata
    "title": "Original Title",
    "uploader": "Channel Name",
    "duration": 120
  }
}
```

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "started",
  "message": "Split job started. Connect to WebSocket to track progress."
}
```

**Features:**
- Creates new video with preserved metadata
- Generates new thumbnail
- Uploads split video to S3

---

## Job Management

### Get Job Status (REST)

#### `GET /api/job/{job_id}`

Get current status of a job (REST fallback).

**Response:**
```json
{
  "job_id": "uuid-string",
  "stage": "download",  // download, upload, split, complete, error, cancelled
  "percent": 45.5,
  "message": "Downloading...",
  "speed": "2.5 MB/s",
  "eta": "30s",
  "s3_url": "https://s3-url/video.mp4",  // Available when complete
  "metadata": {
    "title": "Video Title",
    "duration": 120,
    "uploader": "Channel Name",
    "view_count": 1000,
    "width": 1920,
    "height": 1080
  }
}
```

---

### Cancel Job

#### `POST /api/job/{job_id}/cancel`

Cancel a running download/upload/split job.

**Response:**
```json
{
  "status": "cancelled",
  "message": "Job cancellation requested"
}
```

---

### WebSocket Connection

#### `WS /ws/{job_id}`

Real-time job status updates via WebSocket.

**Connection:**
```
ws://localhost:8000/ws/{job_id}
```

**Messages Received:**
```json
{
  "job_id": "uuid-string",
  "stage": "download",
  "percent": 45.5,
  "message": "Downloading...",
  "speed": "2.5 MB/s",
  "eta": "30s"
}
```

**Job Stages:**
- `download` - Downloading video
- `upload` - Uploading to S3
- `split` - Splitting/trimming video
- `complete` - Job completed successfully
- `error` - Job failed
- `cancelled` - Job was cancelled

---

### Proxy Video

#### `GET /api/video/{job_id}`

Proxy endpoint to serve video with proper CORS headers.

**Response:**
- Streaming video file with proper headers
- Falls back to redirect if streaming fails

---

## File Metadata Management

### Save File Metadata

#### `POST /api/files`

Save video file metadata to storage.

**Request Body:**
```json
{
  "s3_url": "https://s3-url/video.mp4",
  "job_id": "uuid-string",  // Optional
  "metadata": {
    "title": "Video Title",
    "duration": 120,
    "uploader": "Channel Name",
    "view_count": 1000,
    "s3_key": "videos/job-id/video.mp4",
    "thumbnail_key": "thumbnails/job-id/thumbnail.jpg"
  },
  "video_width": 1920,
  "video_height": 1080,
  "thumbnail_url": "https://s3-url/thumbnail.jpg",  // Optional
  "playlist_id": "playlist-uuid",  // Optional
  "created_at": "2025-01-01T00:00:00Z"  // Optional
}
```

**Response:**
```json
{
  "id": "file-uuid",
  "message": "File metadata saved successfully"
}
```

---

### Get All Files

#### `GET /api/files`

Get all saved file metadata with fresh presigned URLs.

**Query Parameters:**
- `playlist_id` (optional) - Filter files by playlist ID

**Response:**
```json
{
  "files": [
    {
      "id": "file-uuid",
      "s3_url": "https://fresh-presigned-url/video.mp4",
      "s3_key": "videos/job-id/video.mp4",
      "job_id": "job-uuid",
      "metadata": {
        "title": "Video Title",
        "duration": 120,
        "uploader": "Channel Name",
        "view_count": 1000,
        "width": 1920,
        "height": 1080
      },
      "video_width": 1920,
      "video_height": 1080,
      "thumbnail_url": "https://fresh-presigned-url/thumbnail.jpg",
      "thumbnail_key": "thumbnails/job-id/thumbnail.jpg",
      "playlist_id": "playlist-uuid",  // Optional
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

**Features:**
- Automatically generates fresh presigned URLs for expired URLs
- Extracts S3 keys from old URLs for backward compatibility
- Sorts by creation date (newest first)

---

### Update File Metadata

#### `PUT /api/files/{file_id}`

Update file metadata (e.g., title).

**Request Body:**
```json
{
  "title": "New Video Title"
}
```

**Response:**
```json
{
  "message": "File updated successfully"
}
```

---

### Delete File

#### `DELETE /api/files/{file_id}`

Delete a file from metadata storage.

**Response:**
```json
{
  "message": "File deleted successfully"
}
```

---

## Playlist Management

### Create Playlist

#### `POST /api/playlists`

Create a new playlist.

**Request Body:**
```json
{
  "title": "My Playlist",
  "description": "Playlist description",  // Optional
  "publish_status": "private"  // private, public, or unlisted
}
```

**Response:**
```json
{
  "id": "playlist-uuid",
  "playlist": {
    "id": "playlist-uuid",
    "title": "My Playlist",
    "description": "Playlist description",
    "publish_status": "private",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
  },
  "message": "Playlist created successfully"
}
```

---

### Get All Playlists

#### `GET /api/playlists`

Get all playlists.

**Response:**
```json
{
  "playlists": [
    {
      "id": "playlist-uuid",
      "title": "My Playlist",
      "description": "Playlist description",
      "publish_status": "private",
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

---

### Get Playlist by ID

#### `GET /api/playlists/{playlist_id}`

Get a specific playlist by ID.

**Response:**
```json
{
  "playlist": {
    "id": "playlist-uuid",
    "title": "My Playlist",
    "description": "Playlist description",
    "publish_status": "private",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
  }
}
```

---

### Update Playlist

#### `PUT /api/playlists/{playlist_id}`

Update playlist data.

**Request Body:**
```json
{
  "title": "Updated Title",  // Optional
  "description": "Updated description",  // Optional
  "publish_status": "public"  // Optional
}
```

**Response:**
```json
{
  "playlist": {
    "id": "playlist-uuid",
    "title": "Updated Title",
    "description": "Updated description",
    "publish_status": "public",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T01:00:00Z"
  },
  "message": "Playlist updated successfully"
}
```

---

### Delete Playlist

#### `DELETE /api/playlists/{playlist_id}`

Delete a playlist.

**Response:**
```json
{
  "message": "Playlist deleted successfully"
}
```

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Error message description"
}
```

**Common HTTP Status Codes:**
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error

---

## Environment Variables

The backend requires the following environment variables (set in `.env` file):

```env
# S3/MinIO Configuration
S3_BUCKET=your-bucket-name
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_ENDPOINT_URL=http://localhost:9000  # For MinIO, omit for AWS S3

# Optional Settings
S3_URL_EXPIRATION=3600  # Presigned URL expiration in seconds
S3_PUBLIC_URLS=false  # Use public URLs instead of presigned
MAX_FILE_SIZE_MB=5000  # Maximum file size in MB
TEMP_DIR=./tmp/jobs  # Temporary directory for downloads
FFMPEG_PATH=/path/to/ffmpeg  # Custom FFmpeg path (optional)
```

---

## Notes

1. **Presigned URLs**: S3 URLs are generated with expiration times. The API automatically refreshes expired URLs when fetching files.

2. **Vertical Video Conversion**: Videos with height > width are automatically converted to 1920x1080 horizontal format during download/upload.

3. **Thumbnail Generation**: Thumbnails are automatically generated for all videos.

4. **WebSocket**: For real-time updates, use WebSocket connections. REST endpoint is available as fallback.

5. **Job Cancellation**: Jobs can be cancelled at any time, but cleanup may take a moment.

6. **File Storage**: Metadata is stored in JSON files (`metadata.json` and `playlists.json`) in the backend directory.

---

## Example Usage

### Download a Video

```bash
curl -X POST "http://localhost:8000/api/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID"
  }'
```

### Check Job Status via WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/JOB_ID');
ws.onmessage = (event) => {
  const status = JSON.parse(event.data);
  console.log('Status:', status);
};
```

### Save File Metadata

```bash
curl -X POST "http://localhost:8000/api/files" \
  -H "Content-Type: application/json" \
  -d '{
    "s3_url": "https://s3-url/video.mp4",
    "metadata": {
      "title": "My Video",
      "duration": 120
    },
    "video_width": 1920,
    "video_height": 1080
  }'
```

### Create Playlist

```bash
curl -X POST "http://localhost:8000/api/playlists" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Playlist",
    "description": "A collection of videos",
    "publish_status": "private"
  }'
```

