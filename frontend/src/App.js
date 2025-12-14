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
import ActiveJobsList from './components/ActiveJobsList';
import LoginForm from './components/LoginForm';

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
  const [isConverting, setIsConverting] = useState(false);
  const [showActiveJobs, setShowActiveJobs] = useState(false);
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);

  // Track auto-saved job IDs to prevent duplicate saves
  const autoSavedJobIdsRef = useRef(new Set());

  // Check for existing authentication on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('access_token');
    const storedUser = localStorage.getItem('user');
    
    if (storedToken && storedUser) {
      try {
        const userData = JSON.parse(storedUser);
        setToken(storedToken);
        setUser(userData);
        
        // Set default axios authorization header
        axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
        
        // Verify token is still valid
        axios.get(`${API_BASE_URL}/api/auth/me`)
          .then(response => {
            setUser(response.data);
          })
          .catch(() => {
            // Token invalid, clear storage
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            setToken(null);
            setUser(null);
            delete axios.defaults.headers.common['Authorization'];
          });
      } catch (e) {
        console.error('Error parsing stored user:', e);
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
      }
    }
  }, []);

  // Handle successful login
  const handleLoginSuccess = (userData, accessToken) => {
    setUser(userData);
    setToken(accessToken);
    axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
  };

  // Handle logout
  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setUser(null);
    setToken(null);
    delete axios.defaults.headers.common['Authorization'];
  };

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
    console.log('WebSocket message received:', data);
    console.log('Current jobId:', jobId);
    console.log('Message stage:', data.stage);
    setStatus(data);
    
    if (data.stage === 'complete' && data.s3_url) {
      setS3Url(data.s3_url);
      setIsConverting(false);
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
      setIsConverting(false);
    } else if (data.stage === 'download' || data.stage === 'upload') {
      // Keep isConverting true during conversion process
      setIsConverting(true);
    }
  }, [jobId]);

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

  const handleHome = () => {
    console.log('handleHome called');
    // Reset to home state
    handleReset();
    setShowNewDownload(false);
    setShowActiveJobs(false);
    // Force re-render by clearing any active states
    setUrl('');
    setError(null);
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
        // Get video dimensions from metadata if not already set from video element
        // This ensures horizontal videos are saved even if videoWidth/videoHeight state isn't set
        const width = videoWidth || status.metadata?.width || null;
        const height = videoHeight || status.metadata?.height || null;
        
        const metadata = {
          s3_url: s3Url,
          job_id: jobId,
          metadata: status.metadata,
          video_width: width,
          video_height: height,
          thumbnail_url: status.metadata?.thumbnail_url || null,
          // thumbnail_key is stored in metadata and will be extracted by backend
          playlist_id: null, // Auto save without playlist
          is_public: 0, // Default to private
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
  }, [s3Url, status, jobId, loadSavedFiles]); // eslint-disable-line react-hooks/exhaustive-deps
  // videoWidth and videoHeight intentionally excluded - we get dimensions from metadata instead

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

  const handleConvert = async () => {
    if (!s3Url || isConverting) return;
    
    setIsConverting(true);
    setError(null);
    
    try {
      const response = await axios.post(`${API_BASE_URL}/api/convert`, {
        s3_url: s3Url
      });
      
      const convertJobId = response.data.job_id;
      setJobId(convertJobId);
      // Set initial status to show user that conversion has started
      setStatus({ 
        stage: 'download', 
        message: 'در حال دانلود ویدیو از S3...',
        percent: 0
      });
      console.log('Convert job started with ID:', convertJobId);
      // Keep original s3Url visible during conversion
      // It will be updated when conversion completes via WebSocket
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'تبدیل ویدیو با خطا مواجه شد';
      setError(errorMessage);
      setIsConverting(false);
      setStatus(null);
      setJobId(null);
      console.error('Error converting video:', err);
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

  const showMainLayout = (savedFiles.length > 0 || showActiveJobs) && !showNewDownload && !jobId && !status && !s3Url;
  const isJobComplete = status && status.stage === 'complete';
  const isJobInProgress = jobId && status && (status.stage === 'download' || status.stage === 'upload' || status.stage === 'connecting');
  // Show download form when: (no saved files OR new download clicked) AND job is not complete AND no active job
  const showDownloadForm = (!savedFiles.length || showNewDownload) && !isJobComplete && !jobId && !showActiveJobs;
  // Show video player when there is a job in progress or a completed job (or s3Url/url ready) and no hard error
  const showVideoPlayer = ((url.trim() || s3Url || jobId) && (isJobComplete || isJobInProgress || status)) && !error;

  // Show login form if user is not authenticated
  if (!user || !token) {
    return <LoginForm onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="App">
      {showMainLayout && (
        <MainLayout
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onNewDownload={() => setShowNewDownload(true)}
          showActiveJobs={showActiveJobs}
          onToggleActiveJobs={() => setShowActiveJobs(!showActiveJobs)}
          user={user}
          onLogout={handleLogout}
          onHome={handleHome}
        >
          {showActiveJobs ? (
            <ActiveJobsList
              onJobClick={(job) => {
                if (job.s3_url) {
                  setS3Url(job.s3_url);
                  setJobId(job.jobId);
                  setStatus({
                    stage: job.stage,
                    percent: job.percent,
                    message: job.message,
                    metadata: job.metadata,
                    s3_url: job.s3_url
                  });
                  setShowActiveJobs(false);
                }
              }}
              onCancelJob={(cancelledJobId) => {
                if (cancelledJobId === jobId) {
                  setJobId(null);
                  setStatus(null);
                  setS3Url(null);
                }
              }}
            />
          ) : (
            <SavedFilesList
              savedFiles={savedFiles}
              searchQuery={searchQuery}
              selectedPlaylistFilter={selectedPlaylistFilter}
              playlists={playlists}
              onPlay={handleOpenPlayer}
              user={user}
              onDelete={handleDeleteFile}
              onTitleUpdate={loadSavedFiles}
              onNewDownload={() => setShowNewDownload(true)}
              onFilterChange={setSelectedPlaylistFilter}
              onSearchChange={setSearchQuery}
            />
          )}
        </MainLayout>
      )}

      {showDownloadForm && (
        <MainLayout
          searchQuery=""
          onSearchChange={() => {}}
          onNewDownload={() => {}}
          showSidebar={false}
          onHome={handleHome}
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
          onHome={handleHome}
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
              onBack={handleHome}
              onSeek={seekToTimestamp}
              onConvert={handleConvert}
              isConverting={isConverting}
              onCancel={handleCancel}
              onReset={handleReset}
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
