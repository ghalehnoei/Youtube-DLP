import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import './App.css';

// Components
import RTLText from './components/RTLText';
import VideoPlayer from './components/VideoPlayer';
import SavedFilesList from './components/SavedFilesList';
import DownloadForm from './components/DownloadForm';
import StatusDisplay from './components/StatusDisplay';
import PlaylistModal from './components/PlaylistModal';
import MainLayout from './components/MainLayout';

// Hooks
import { useWebSocket } from './hooks/useWebSocket';
import { useVideoPlayer } from './hooks/useVideoPlayer';
import { useStoryboard } from './hooks/useStoryboard';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const APP_NAME = process.env.REACT_APP_NAME || 'RAFO VIDEO Downloader';

function App() {
  // Set document title
  useEffect(() => {
    document.title = APP_NAME;
  }, []);

  // State management
  const [url, setUrl] = useState('');
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [s3Url, setS3Url] = useState(null);
  const [videoDuration, setVideoDuration] = useState(null);
  const [videoWidth, setVideoWidth] = useState(null);
  const [videoHeight, setVideoHeight] = useState(null);
  const [savedFiles, setSavedFiles] = useState([]);
  const [showNewDownload, setShowNewDownload] = useState(false);
  const [fileUploadName, setFileUploadName] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [playlists, setPlaylists] = useState([]);
  const [showPlaylistModal, setShowPlaylistModal] = useState(false);
  const [selectedPlaylistId, setSelectedPlaylistId] = useState(null);
  const [newPlaylistTitle, setNewPlaylistTitle] = useState('');
  const [newPlaylistDescription, setNewPlaylistDescription] = useState('');
  const [newPlaylistStatus, setNewPlaylistStatus] = useState('private');
  const [showCreatePlaylist, setShowCreatePlaylist] = useState(false);
  const [selectedPlaylistFilter, setSelectedPlaylistFilter] = useState(null);

  // Track auto-saved job IDs to prevent duplicate saves
  const autoSavedJobIdsRef = useRef(new Set());

  // Custom hooks
  const handleVideoLoadedMetadata = (e) => {
    const video = e.target;
    const duration = video.duration;
    if (duration && !isNaN(duration)) {
      setVideoDuration(duration);
    }
    if (video.videoWidth && video.videoHeight) {
      setVideoWidth(video.videoWidth);
      setVideoHeight(video.videoHeight);
    }
  };

  const { videoContainerRef, seekToTimestamp } = useVideoPlayer(
    s3Url,
    videoDuration,
    handleVideoLoadedMetadata
  );

  const storyboardFrames = useStoryboard(jobId, status, s3Url);

  // WebSocket handlers
  const handleWebSocketMessage = useCallback((data) => {
    setStatus(data);
    
    if (data.stage === 'complete' && data.s3_url) {
      setS3Url(data.s3_url);
      if (data.metadata) {
        if (data.metadata.duration) {
          setVideoDuration(data.metadata.duration);
        }
        if (data.metadata.width && data.metadata.height) {
          setVideoWidth(data.metadata.width);
          setVideoHeight(data.metadata.height);
        }
      }
    } else if (data.stage === 'error') {
      setError(data.message || 'خطایی رخ داد');
    }
  }, []);

  const handleWebSocketError = useCallback((errorMsg) => {
    setError(errorMsg);
  }, []);

  useWebSocket(jobId, handleWebSocketMessage, handleWebSocketError);

  // Load playlists and saved files
  const loadPlaylists = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/playlists`);
      setPlaylists(response.data.playlists || []);
    } catch (err) {
      console.error('Error loading playlists:', err);
    }
  }, []);

  const loadSavedFiles = useCallback(async () => {
    try {
      let url = `${API_BASE_URL}/api/files`;
      if (selectedPlaylistFilter && selectedPlaylistFilter !== 'none') {
        url = `${API_BASE_URL}/api/files?playlist_id=${selectedPlaylistFilter}`;
      }
      const response = await axios.get(url);
      let files = response.data.files || [];
      
      if (selectedPlaylistFilter === 'none') {
        files = files.filter(file => !file.playlist_id);
      }
      
      setSavedFiles(files);
    } catch (err) {
      console.error('Error loading saved files:', err);
    }
  }, [selectedPlaylistFilter]);

  useEffect(() => {
    loadSavedFiles();
    loadPlaylists();
  }, [loadSavedFiles, loadPlaylists]);

  // Handlers
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!url.trim()) {
      setError('لطفاً یک آدرس معتبر وارد کنید');
      return;
    }

    setError(null);
    setStatus(null);
    setS3Url(null);
    setJobId(null);
    setFileUploadName(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/download`, {
        url: url.trim()
      });
      setJobId(response.data.job_id);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'شروع دانلود با خطا مواجه شد';
      setError(errorMessage);
      console.error('Error starting download:', err);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (!file.type.startsWith('video/')) {
      setError('لطفاً یک فایل ویدیو انتخاب کنید');
      return;
    }

    setError(null);
    setStatus(null);
    setS3Url(null);
    setJobId(null);
    setUrl('');
    setFileUploadName(file.name);

    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setJobId(response.data.job_id);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'آپلود فایل با خطا مواجه شد';
      setError(errorMessage);
      console.error('Error uploading file:', err);
      setFileUploadName(null);
    }
  };

  const handleCancel = async () => {
    if (!jobId) return;
    try {
      await axios.post(`${API_BASE_URL}/api/job/${jobId}/cancel`);
      setStatus({ ...status, stage: 'cancelled', message: 'Download cancelled' });
    } catch (err) {
      console.error('Error cancelling job:', err);
      setError('لغو دانلود با خطا مواجه شد');
    }
  };

  const handleReset = () => {
    setUrl('');
    setJobId(null);
    setStatus(null);
    setError(null);
    setS3Url(null);
    setVideoDuration(null);
    setVideoWidth(null);
    setVideoHeight(null);
    setShowNewDownload(false);
    setFileUploadName(null);
    // Clear auto-saved tracking when resetting
    autoSavedJobIdsRef.current.clear();
  };

  const handleBackToMain = () => {
    handleReset();
    if (savedFiles.length > 0) {
      setShowNewDownload(false);
    }
  };

  // Auto-save when download is complete
  useEffect(() => {
    const autoSave = async () => {
      if (!s3Url || !status || status.stage !== 'complete' || !status.metadata || !jobId) {
        return;
      }
      
      // Check if already auto-saved for this job (prevent duplicate saves)
      if (autoSavedJobIdsRef.current.has(jobId)) {
        return;
      }
      
      try {
        const metadata = {
          s3_url: s3Url,
          job_id: jobId,
          metadata: status.metadata,
          video_width: videoWidth,
          video_height: videoHeight,
          thumbnail_url: status.metadata?.thumbnail_url || null,
          playlist_id: null, // Auto save without playlist
          created_at: new Date().toISOString()
        };
        
        // Mark as auto-saved BEFORE making the API call to prevent duplicate saves
        autoSavedJobIdsRef.current.add(jobId);
        
        await axios.post(`${API_BASE_URL}/api/files`, metadata);
        await loadSavedFiles();
      } catch (err) {
        // If save failed, remove from ref so it can be retried
        autoSavedJobIdsRef.current.delete(jobId);
        console.error('Error auto-saving file:', err);
        // Don't show error to user for auto-save
      }
    };

    // Delay auto-save slightly to ensure all state is updated
    const timer = setTimeout(() => {
      autoSave();
    }, 1000);

    return () => clearTimeout(timer);
  }, [s3Url, status, jobId, videoWidth, videoHeight, loadSavedFiles]);

  const handleConfirmSave = async () => {
    if (!s3Url || !status || !status.metadata) return;
    
    try {
      const metadata = {
        s3_url: s3Url,
        job_id: jobId,
        metadata: status.metadata,
        video_width: videoWidth,
        video_height: videoHeight,
        thumbnail_url: status.metadata?.thumbnail_url || null,
        playlist_id: selectedPlaylistId || null,
        created_at: new Date().toISOString()
      };
      
      await axios.post(`${API_BASE_URL}/api/files`, metadata);
      await loadSavedFiles();
      setError(null);
      setShowPlaylistModal(false);
      setSelectedPlaylistId(null);
      setShowNewDownload(false);
      setS3Url(null);
      setStatus(null);
      setJobId(null);
      setUrl('');
      setVideoDuration(null);
      setVideoWidth(null);
      setVideoHeight(null);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'ذخیره فایل با خطا مواجه شد';
      setError(errorMessage);
      console.error('Error saving file:', err);
    }
  };

  const handleCreatePlaylist = async () => {
    if (!newPlaylistTitle.trim()) {
      setError('عنوان پلی‌لیست الزامی است');
      return;
    }
    
    try {
      const response = await axios.post(`${API_BASE_URL}/api/playlists`, {
        title: newPlaylistTitle.trim(),
        description: newPlaylistDescription.trim() || null,
        publish_status: newPlaylistStatus
      });
      
      await loadPlaylists();
      setSelectedPlaylistId(response.data.id);
      setNewPlaylistTitle('');
      setNewPlaylistDescription('');
      setNewPlaylistStatus('private');
      setShowCreatePlaylist(false);
      setError(null);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'ایجاد پلی‌لیست با خطا مواجه شد';
      setError(errorMessage);
      console.error('Error creating playlist:', err);
    }
  };

  const handleDeleteFile = async (fileId) => {
    try {
      await axios.delete(`${API_BASE_URL}/api/files/${fileId}`);
      await loadSavedFiles();
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'حذف فایل با خطا مواجه شد';
      setError(errorMessage);
      console.error('Error deleting file:', err);
    }
  };

  const handleOpenPlayer = (s3Url) => {
    const file = savedFiles.find(f => f.s3_url === s3Url);
    setS3Url(s3Url);
    setUrl('');
    setJobId(null);
    setStatus({ 
      stage: 'complete', 
      percent: 100, 
      message: 'از فایل‌های ذخیره شده بارگذاری شد',
      metadata: file?.metadata || {}
    });
    setShowNewDownload(false);
    if (file) {
      if (file.video_width && file.video_height) {
        setVideoWidth(file.video_width);
        setVideoHeight(file.video_height);
      }
      if (file.metadata?.duration) {
        setVideoDuration(file.metadata.duration);
      }
    }
  };

  const showSavedFiles = savedFiles.length > 0 && !showNewDownload && !jobId && !status && !s3Url;
  // Show download form when: (no saved files OR new download clicked) AND job is not complete
  const isJobComplete = status && status.stage === 'complete';
  const showDownloadForm = (!savedFiles.length || showNewDownload) && !isJobComplete;
  // Show video player when: has URL or S3 URL AND status is complete AND no error
  const showVideoPlayer = (url.trim() || s3Url) && isJobComplete && !error;

  return (
    <div className="App">
      {showSavedFiles && (
        <MainLayout
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onNewDownload={() => setShowNewDownload(true)}
        >
          <SavedFilesList
            savedFiles={savedFiles}
            searchQuery={searchQuery}
            selectedPlaylistFilter={selectedPlaylistFilter}
            playlists={playlists}
            onPlay={handleOpenPlayer}
            onDelete={handleDeleteFile}
            onTitleUpdate={loadSavedFiles}
            onNewDownload={() => setShowNewDownload(true)}
            onFilterChange={setSelectedPlaylistFilter}
            onSearchChange={setSearchQuery}
          />
        </MainLayout>
      )}

      {showDownloadForm && (
        <MainLayout
          searchQuery=""
          onSearchChange={() => {}}
          onNewDownload={() => {}}
          showSidebar={false}
        >
          <div className="download-page-content">
            {/* Show error if exists and no active job */}
            {error && !jobId && !status && (
              <div className="error-box">
                <h3>❌ خطا</h3>
                <p><RTLText>{error}</RTLText></p>
                <button onClick={handleReset} className="reset-btn">
                  تلاش مجدد
                </button>
              </div>
            )}

            {/* Show status/progress if job is active or status exists */}
            {(jobId || status) && (
              <StatusDisplay
                status={
                  status || {
                    stage: 'connecting',
                    message: 'در حال اتصال به سرور...',
                    percent: 0
                  }
                }
                onCancel={
                  status &&
                  status.stage !== 'complete' &&
                  status.stage !== 'error' &&
                  status.stage !== 'cancelled'
                    ? handleCancel
                    : null
                }
                onReset={handleReset}
              />
            )}

            {/* Show error in status if status has error */}
            {status && status.stage === 'error' && error && (
              <div className="error-box" style={{ marginTop: '16px' }}>
                <p><RTLText>{error}</RTLText></p>
              </div>
            )}

            {/* Show form only when no active job and no status */}
            {!jobId && !status && (
              <DownloadForm
                url={url}
                setUrl={setUrl}
                onSubmit={handleSubmit}
                onFileUpload={handleFileUpload}
                fileUploadName={fileUploadName}
                showBackButton={savedFiles.length > 0}
                onBack={handleBackToMain}
              />
            )}
          </div>
        </MainLayout>
      )}

      {showVideoPlayer && (
        <MainLayout
          searchQuery=""
          onSearchChange={() => {}}
          onNewDownload={() => {}}
          showSidebar={false}
        >
          {error && (
            <div className="error-box">
              <h3>❌ خطا</h3>
              <p><RTLText>{error}</RTLText></p>
              <button onClick={handleReset} className="reset-btn">
                تلاش مجدد
              </button>
            </div>
          )}
          {!error && (
            <VideoPlayer
              url={url}
              s3Url={s3Url}
              status={status}
              videoDuration={videoDuration}
              videoWidth={videoWidth}
              videoHeight={videoHeight}
              savedFiles={savedFiles}
              jobId={jobId}
              videoContainerRef={videoContainerRef}
              storyboardFrames={storyboardFrames}
              onBack={handleBackToMain}
              onSeek={seekToTimestamp}
            />
          )}
        </MainLayout>
      )}

        <PlaylistModal
          show={showPlaylistModal}
          playlists={playlists}
          selectedPlaylistId={selectedPlaylistId}
          showCreatePlaylist={showCreatePlaylist}
          newPlaylistTitle={newPlaylistTitle}
          newPlaylistDescription={newPlaylistDescription}
          newPlaylistStatus={newPlaylistStatus}
          onClose={() => {
                        setShowPlaylistModal(false);
                        setSelectedPlaylistId(null);
                      }}
          onSelectPlaylist={setSelectedPlaylistId}
          onSave={handleConfirmSave}
          onCreatePlaylist={handleCreatePlaylist}
          onShowCreatePlaylist={() => setShowCreatePlaylist(true)}
          onHideCreatePlaylist={() => {
                        setShowCreatePlaylist(false);
                        setNewPlaylistTitle('');
                        setNewPlaylistDescription('');
                        setNewPlaylistStatus('private');
                      }}
          onTitleChange={setNewPlaylistTitle}
          onDescriptionChange={setNewPlaylistDescription}
          onStatusChange={setNewPlaylistStatus}
        />
    </div>
  );
}

export default App;
