import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import dashjs from 'dashjs';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Utility function to detect Persian/Arabic text
const isPersianText = (text) => {
  if (!text || typeof text !== 'string') return false;
  // Persian/Arabic Unicode range: \u0600-\u06FF
  const persianRegex = /[\u0600-\u06FF]/;
  return persianRegex.test(text);
};

// Component to render text with RTL support for Persian
const RTLText = ({ children, className = '', tag: Tag = 'span' }) => {
  const text = typeof children === 'string' ? children : (children?.toString() || '');
  const hasPersian = isPersianText(text);
  
  return (
    <Tag 
      className={className}
      dir={hasPersian ? 'rtl' : 'ltr'}
      style={hasPersian ? { direction: 'rtl', textAlign: 'right' } : {}}
    >
      {children}
    </Tag>
  );
};

// Component to embed YouTube video
const YouTubeEmbed = ({ url, onDurationChange }) => {
  const getYouTubeEmbedUrl = (url) => {
    try {
      // Extract video ID from various YouTube URL formats
      const patterns = [
        /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([^&\n?#]+)/,
        /youtube\.com\/watch\?.*v=([^&\n?#]+)/
      ];
      
      for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match && match[1]) {
          return {
            embedUrl: `https://www.youtube.com/embed/${match[1]}`,
            videoId: match[1]
          };
        }
      }
      
      // If no match, return original URL (might work for other platforms)
      return { embedUrl: url, videoId: null };
    } catch (e) {
      return { embedUrl: url, videoId: null };
    }
  };

  const { embedUrl, videoId } = getYouTubeEmbedUrl(url);
  
  // Try to get duration from YouTube API
  React.useEffect(() => {
    if (videoId && onDurationChange) {
      // Use YouTube oEmbed API to get video info
      fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`)
        .then(res => res.json())
        .then(data => {
          // Note: oEmbed doesn't provide duration, but we can try other methods
          // For now, we'll let users enter duration manually
        })
        .catch(err => {
          // Silently fail - duration will be set from video metadata
        });
    }
  }, [videoId, onDurationChange]);
  
  if (embedUrl.includes('youtube.com/embed') || embedUrl.includes('youtu.be')) {
    return (
      <iframe
        src={embedUrl}
        title="YouTube video player"
        frameBorder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowFullScreen
      />
    );
  }
  
  // Fallback for non-YouTube URLs - try to use video tag
  return (
    <video 
      controls 
      className="video-player"
      src={url}
      preload="metadata"
      crossOrigin="anonymous"
      onLoadedMetadata={(e) => {
        if (onDurationChange && e.target.duration) {
          onDurationChange(e.target.duration);
        }
      }}
    >
      Your browser does not support the video tag.
      <source src={url} type="video/mp4" />
    </video>
  );
};

function App() {
  const [url, setUrl] = useState('');
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [s3Url, setS3Url] = useState(null);
  const [startTime, setStartTime] = useState(0);
  const [endTime, setEndTime] = useState(null);
  const [videoDuration, setVideoDuration] = useState(null);
  const [videoWidth, setVideoWidth] = useState(null);
  const [videoHeight, setVideoHeight] = useState(null);
  const [convertToHorizontal, setConvertToHorizontal] = useState(false);
  const [savedFiles, setSavedFiles] = useState([]);
  const [showNewDownload, setShowNewDownload] = useState(false);
  const [fileUploadName, setFileUploadName] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingTitleId, setEditingTitleId] = useState(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [playlists, setPlaylists] = useState([]);
  const [showPlaylistModal, setShowPlaylistModal] = useState(false);
  const [selectedPlaylistId, setSelectedPlaylistId] = useState(null);
  const [newPlaylistTitle, setNewPlaylistTitle] = useState('');
  const [newPlaylistDescription, setNewPlaylistDescription] = useState('');
  const [newPlaylistStatus, setNewPlaylistStatus] = useState('private');
  const [showCreatePlaylist, setShowCreatePlaylist] = useState(false);
  const [selectedPlaylistFilter, setSelectedPlaylistFilter] = useState(null);
  const [storyboardFrames, setStoryboardFrames] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const videoRef = useRef(null);
  const videoContainerRef = useRef(null);
  const dashPlayerRef = useRef(null);

  // Initialize dash.js player when s3Url changes
  useEffect(() => {
    if (!s3Url || !videoContainerRef.current) return;
    
    // Clean up existing player
    if (dashPlayerRef.current) {
      dashPlayerRef.current.destroy();
      dashPlayerRef.current = null;
    }
    
    // Create video element
    const videoElement = document.createElement('video');
    videoElement.controls = true;
    videoElement.className = 'video-player';
    videoElement.setAttribute('tabindex', '0'); // Make it focusable
    videoElement.style.width = '100%';
    videoElement.style.height = 'auto';
    videoElement.crossOrigin = 'anonymous';
    
    // Clear container and add video element
    videoContainerRef.current.innerHTML = '';
    videoContainerRef.current.appendChild(videoElement);
    
    // Check if URL is a DASH manifest (.mpd) or regular MP4
    const isDashManifest = s3Url.toLowerCase().endsWith('.mpd');
    
    if (isDashManifest) {
      // Initialize dash.js player for DASH manifest
      const player = dashjs.MediaPlayer().create();
      player.initialize(videoElement, s3Url, true);
      dashPlayerRef.current = player;
    } else {
      // For regular MP4 files, use native HTML5 video player
      videoElement.src = s3Url;
      // Add source element for better browser compatibility
      const source = document.createElement('source');
      source.src = s3Url;
      source.type = 'video/mp4';
      videoElement.appendChild(source);
    }
    
    // Store reference
    videoRef.current = videoElement;
    
    // Handle metadata loaded
    const handleMetadata = (e) => {
      handleVideoLoadedMetadata(e);
    };
    videoElement.addEventListener('loadedmetadata', handleMetadata);
    
    // Cleanup function
    return () => {
      if (dashPlayerRef.current) {
        dashPlayerRef.current.destroy();
        dashPlayerRef.current = null;
      }
      if (videoElement) {
        videoElement.removeEventListener('loadedmetadata', handleMetadata);
      }
    };
  }, [s3Url, videoDuration]);

  // Keyboard shortcuts for time selection (only when video player has focus)
  useEffect(() => {
    if (!s3Url || !videoDuration) return;
    
    // Find video element
    let video = videoRef.current;
    if (!video && videoContainerRef.current) {
      video = videoContainerRef.current.querySelector('video');
    }
    if (!video) return;
    
    const handleKeyPress = (e) => {
      // Only handle I and O keys
      if (e.key !== 'i' && e.key !== 'I' && e.key !== 'o' && e.key !== 'O') {
        return;
      }
      
      // Only handle if video element or its controls have focus
      const activeElement = document.activeElement;
      const videoContainer = videoContainerRef.current;
      
      // Check if focus is on video, video container, or any element within them
      const isVideoFocused = activeElement === video || 
                            video === activeElement ||
                            video.contains(activeElement) ||
                            (videoContainer && videoContainer.contains(activeElement)) ||
                            activeElement.closest('video') === video ||
                            activeElement.closest('.video-player') === video ||
                            activeElement.closest('.dash-video-container') === videoContainer ||
                            activeElement.closest('.video-wrapper') === videoContainer?.parentElement;
      
      if (!isVideoFocused) return;
      
      // Don't handle if typing in an input or textarea (but allow video controls)
      if (
        (activeElement.tagName === 'INPUT' && activeElement.type !== 'range') || 
        (activeElement.tagName === 'TEXTAREA') ||
        (activeElement.isContentEditable && !activeElement.closest('video'))
      ) {
        return;
      }
      
      // Prevent default behavior and stop propagation
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      
      // Make sure video has loaded metadata
      if (isNaN(video.currentTime)) return;
      
      // Store current time before any potential state updates
      const currentTime = video.currentTime;
      
      // Check for I key for start time
      if (e.key === 'i' || e.key === 'I') {
        const maxTime = endTime || videoDuration;
        if (currentTime >= 0 && currentTime < maxTime && currentTime < videoDuration) {
          setStartTime(currentTime);
        }
        return false;
      } 
      // Check for O key for end time
      else if (e.key === 'o' || e.key === 'O') {
        if (currentTime > startTime && currentTime <= videoDuration) {
          setEndTime(currentTime);
        }
        return false;
      }
    };
    
    // Add listener to video container to catch events from controls too
    const container = videoContainerRef.current;
    if (container) {
      container.addEventListener('keydown', handleKeyPress, true);
    }
    // Use capture phase to catch events before they reach video controls
    video.addEventListener('keydown', handleKeyPress, true);
    
    return () => {
      if (video) {
        video.removeEventListener('keydown', handleKeyPress, true);
      }
      if (container) {
        container.removeEventListener('keydown', handleKeyPress, true);
      }
    };
  }, [s3Url, videoDuration, startTime, endTime]);

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
      
      // If filtering for "none", filter client-side
      if (selectedPlaylistFilter === 'none') {
        files = files.filter(file => !file.playlist_id);
      }
      
      setSavedFiles(files);
    } catch (err) {
      console.error('Error loading saved files:', err);
    }
  }, [selectedPlaylistFilter]);

  // Load saved files and playlists on mount
  useEffect(() => {
    loadSavedFiles();
    loadPlaylists();
  }, [loadSavedFiles, loadPlaylists]);

  // Load storyboard frames when video is ready
  useEffect(() => {
    const loadStoryboardFrames = async () => {
      if (!status || status.stage !== 'complete') {
        setStoryboardFrames([]);
        return;
      }

      console.log('Loading storyboard frames...', { jobId, metadata: status.metadata });

      // First, check if frames are directly in metadata (for saved files)
      if (status.metadata && status.metadata.frames && Array.isArray(status.metadata.frames)) {
        console.log('Found frames in metadata:', status.metadata.frames.length);
        // Convert frames to the format expected by the UI
        const frames = status.metadata.frames.map(frame => ({
          index: frame.index,
          timestamp: frame.timestamp,
          time_str: frame.time_str,
          image_url: frame.image_s3_url || frame.image_url || `/api/storyboard/${status.metadata.storyboard_job_id || jobId}/frame/${frame.index}`
        }));
        if (frames.length > 0) {
          setStoryboardFrames(frames);
          return;
        }
      }

      // Try to get storyboard frames from job_id if available
      if (jobId) {
        try {
          console.log('Fetching storyboard frames from jobId:', jobId);
          const response = await axios.get(`${API_BASE_URL}/api/storyboard/${jobId}/frames`);
          if (response.data && response.data.frames) {
            console.log('Found frames from jobId:', response.data.frames.length);
            setStoryboardFrames(response.data.frames);
            return;
          }
        } catch (err) {
          console.log('Failed to fetch from jobId:', err.response?.status, err.message);
          // Continue to try storyboard_job_id
        }
      }

      // Try storyboard_job_id from metadata
      if (status.metadata && status.metadata.storyboard_job_id) {
        try {
          const storyboardJobId = status.metadata.storyboard_job_id;
          console.log('Fetching storyboard frames from storyboard_job_id:', storyboardJobId);
          const response = await axios.get(`${API_BASE_URL}/api/storyboard/${storyboardJobId}/frames`);
          if (response.data && response.data.frames) {
            console.log('Found frames from storyboard_job_id:', response.data.frames.length);
            setStoryboardFrames(response.data.frames);
            return;
          }
        } catch (err2) {
          // Storyboard not available yet or doesn't exist
          console.log('Storyboard not found from storyboard_job_id:', err2.response?.status, err2.message);
        }
      }

      // If we get here, no storyboard was found
      console.log('No storyboard frames found');
      setStoryboardFrames([]);
    };

    loadStoryboardFrames();
  }, [jobId, status, s3Url]);

  // Function to seek video to a specific timestamp
  const seekToTimestamp = useCallback((timestamp) => {
    let video = videoRef.current;
    if (!video && videoContainerRef.current) {
      video = videoContainerRef.current.querySelector('video');
    }
    if (video && !isNaN(timestamp)) {
      video.currentTime = timestamp;
      // If using dash.js player, also seek through the player
      if (dashPlayerRef.current && dashPlayerRef.current.seek) {
        dashPlayerRef.current.seek(timestamp);
      }
    }
  }, []);

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  const handleSaveMetadata = () => {
    if (!s3Url || !status || !status.metadata) return;
    
    // Check if video is already saved
    const isAlreadySaved = savedFiles.some(file => file.s3_url === s3Url || file.job_id === jobId);
    if (isAlreadySaved) {
      setError('This video is already saved');
      return;
    }
    
    // Show playlist selection modal
    setShowPlaylistModal(true);
  };

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
      await loadSavedFiles(); // Reload the list
      setError(null);
      // Close modal and reset
      setShowPlaylistModal(false);
      setSelectedPlaylistId(null);
      // Navigate to saved files list and reset video player
      setShowNewDownload(false);
      setS3Url(null);
      setStatus(null);
      setJobId(null);
      setUrl('');
      setStartTime(0);
      setEndTime(null);
      setVideoDuration(null);
      setVideoWidth(null);
      setVideoHeight(null);
      setConvertToHorizontal(false);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to save file';
      setError(errorMessage);
      console.error('Error saving file:', err);
    }
  };

  const handleCreatePlaylist = async () => {
    if (!newPlaylistTitle.trim()) {
      setError('Playlist title is required');
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
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to create playlist';
      setError(errorMessage);
      console.error('Error creating playlist:', err);
    }
  };

  const handleDeleteFile = async (fileId) => {
    try {
      await axios.delete(`${API_BASE_URL}/api/files/${fileId}`);
      await loadSavedFiles(); // Reload the list
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to delete file';
      setError(errorMessage);
      console.error('Error deleting file:', err);
    }
  };

  const handleSaveTitle = async (fileId) => {
    if (!editingTitle.trim()) {
      setEditingTitleId(null);
      setEditingTitle('');
      return;
    }
    
    try {
      await axios.put(`${API_BASE_URL}/api/files/${fileId}`, {
        title: editingTitle.trim()
      });
      await loadSavedFiles(); // Reload the list
      setEditingTitleId(null);
      setEditingTitle('');
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to update title';
      setError(errorMessage);
      console.error('Error updating title:', err);
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
      message: 'Loaded from saved files',
      metadata: file?.metadata || {}
    });
    setShowNewDownload(false);
    // Reset time selection
    setStartTime(0);
    setEndTime(null);
    // Load video metadata if available
    if (file) {
      if (file.video_width && file.video_height) {
        setVideoWidth(file.video_width);
        setVideoHeight(file.video_height);
      }
      if (file.metadata?.duration) {
        setVideoDuration(file.metadata.duration);
        setEndTime(file.metadata.duration);
      }
    }
  };

  const handleOpenVideo = (s3Url) => {
    window.open(s3Url, '_blank');
  };

  const connectWebSocket = (jobId) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
    const ws = new WebSocket(`${wsUrl}/ws/${jobId}`);
    
    ws.onopen = () => {
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setStatus(data);
        
        if (data.stage === 'complete' && data.s3_url) {
          setS3Url(data.s3_url);
          // Reset time selection after split completes and update metadata
          if (data.metadata) {
            setStartTime(0);
            if (data.metadata.duration) {
              setVideoDuration(data.metadata.duration);
              setEndTime(data.metadata.duration);
            }
            if (data.metadata.width && data.metadata.height) {
              setVideoWidth(data.metadata.width);
              setVideoHeight(data.metadata.height);
            }
          }
        } else if (data.stage === 'error') {
          setError(data.message || 'An error occurred');
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('Connection error. Please refresh and try again.');
    };

    ws.onclose = () => {
      // Only reconnect if job is still in progress
      if (status && status.stage !== 'complete' && status.stage !== 'error') {
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket(jobId);
        }, 2000);
      }
    };

    wsRef.current = ws;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!url.trim()) {
      setError('Please enter a valid URL');
      return;
    }

    setError(null);
    setStatus(null);
    setS3Url(null);
    setJobId(null);
    setFileUploadName(null);

    try {
      const payload = {
        url: url.trim()
      };

      const response = await axios.post(`${API_BASE_URL}/api/download`, payload);

      const newJobId = response.data.job_id;
      setJobId(newJobId);
      connectWebSocket(newJobId);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to start download';
      setError(errorMessage);
      console.error('Error starting download:', err);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (!file.type.startsWith('video/')) {
      setError('Please select a video file');
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
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const newJobId = response.data.job_id;
      setJobId(newJobId);
      connectWebSocket(newJobId);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to upload file';
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
      setError('Failed to cancel download');
    }
  };


  const handleSplit = async () => {
    if (!s3Url || !videoDuration) {
      setError('Video not loaded');
      return;
    }
    
    // Validate time range
    const effectiveEndTime = endTime || videoDuration;
    
    if (startTime < 0) {
      setError('Start time must be >= 0');
      return;
    }
    
    if (effectiveEndTime <= startTime) {
      setError('End time must be greater than start time');
      return;
    }
    
    if (startTime >= videoDuration) {
      setError('Start time must be less than video duration');
      return;
    }
    
    // Store the original S3 URL and metadata to use for splitting
    const originalS3Url = s3Url;
    const originalMetadata = status?.metadata || (savedFiles.find(f => f.s3_url === s3Url)?.metadata);
    
    setError(null);
    setStatus(null);
    // Don't clear s3Url yet - we'll update it when the split completes
    setJobId(null);
    
    try {
      const payload = {
        s3_url: originalS3Url,
        start_time: startTime,
        end_time: effectiveEndTime,
        convert_to_horizontal: false, // Auto-conversion is handled during download
        original_metadata: originalMetadata || null
      };
      
      const response = await axios.post(`${API_BASE_URL}/api/split`, payload);
      
      const newJobId = response.data.job_id;
      setJobId(newJobId);
      connectWebSocket(newJobId);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to start split';
      setError(errorMessage);
      console.error('Error starting split:', err);
    }
  };

  const handleReset = () => {
    setUrl('');
    setJobId(null);
    setStatus(null);
    setError(null);
    setS3Url(null);
    setStartTime(0);
    setEndTime(null);
    setVideoDuration(null);
    setVideoWidth(null);
    setVideoHeight(null);
    setConvertToHorizontal(false);
    setShowNewDownload(false);
    setFileUploadName(null);
    if (wsRef.current) {
      wsRef.current.close();
    }
  };

  const handleBackToMain = () => {
    handleReset();
    // Ensure saved files list is shown
    if (savedFiles.length > 0) {
      setShowNewDownload(false);
    }
  };

  const formatTime = (seconds) => {
    if (!seconds && seconds !== 0) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '00:00';
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hours > 0) {
      return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleVideoLoadedMetadata = (e) => {
    const video = e.target;
    const duration = video.duration;
    if (duration && !isNaN(duration)) {
      setVideoDuration(duration);
      if (!endTime) {
        setEndTime(duration);
      }
    }
    // Get video dimensions
    if (video.videoWidth && video.videoHeight) {
      setVideoWidth(video.videoWidth);
      setVideoHeight(video.videoHeight);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      alert('URL copied to clipboard!');
    }).catch(err => {
      console.error('Failed to copy:', err);
    });
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown';
    const mb = bytes / (1024 * 1024);
    if (mb < 1) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${mb.toFixed(2)} MB`;
  };

  return (
    <div className="App">
      <div className="container">
        <header className="header">
          <h1>🎥 Youtube Downloader</h1>
          <p className="subtitle">Download videos from YouTube and other platforms, then upload to S3</p>
        </header>

        {/* Saved Files List */}
        {savedFiles.length > 0 && !showNewDownload && !jobId && !status && (
          <div className="saved-files-section">
            <div className="saved-files-header">
              <h2>Saved Files</h2>
              <div className="header-actions">
                <select
                  value={selectedPlaylistFilter || ''}
                  onChange={(e) => setSelectedPlaylistFilter(e.target.value || null)}
                  className="playlist-filter-select"
                >
                  <option value="">All Playlists</option>
                  <option value="none">No Playlist</option>
                  {playlists.map(playlist => (
                    <option key={playlist.id} value={playlist.id}>
                      {playlist.title}
                    </option>
                  ))}
                </select>
                <input
                  type="text"
                  placeholder="🔍 Search videos..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="search-input"
                />
                <button 
                  onClick={() => setShowNewDownload(true)}
                  className="new-download-btn"
                >
                  ➕ Download New
                </button>
              </div>
            </div>
            <div className="saved-files-grid">
              {savedFiles
                .filter(file => {
                  if (!searchQuery.trim()) return true;
                  const query = searchQuery.toLowerCase();
                  const title = (file.metadata?.title || 'Untitled Video').toLowerCase();
                  const uploader = (file.metadata?.uploader || '').toLowerCase();
                  return title.includes(query) || uploader.includes(query);
                })
                .map((file) => (
                <div key={file.id} className="saved-video-card">
                  <div className="video-thumbnail-container" onClick={() => handleOpenPlayer(file.s3_url)}>
                    {file.thumbnail_url ? (
                      <img 
                        src={file.thumbnail_url} 
                        alt={file.metadata?.title || 'Video thumbnail'}
                        className="video-thumbnail"
                      />
                    ) : (
                      <div className="video-thumbnail-placeholder">
                        <span>📹</span>
                      </div>
                    )}
                    <div className="video-duration-overlay">
                      {file.metadata?.duration && formatDuration(file.metadata.duration)}
                    </div>
                    <div className="play-overlay">
                      <svg viewBox="0 0 24 24" fill="white" width="48" height="48">
                        <path d="M8 5v14l11-7z"/>
                      </svg>
                    </div>
                  </div>
                  <div className="video-info-card">
                    {editingTitleId === file.id ? (
                      <div className="title-edit-container">
                        <input
                          type="text"
                          value={editingTitle}
                          onChange={(e) => setEditingTitle(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              handleSaveTitle(file.id);
                            } else if (e.key === 'Escape') {
                              setEditingTitleId(null);
                              setEditingTitle('');
                            }
                          }}
                          className="title-edit-input"
                          autoFocus
                        />
                        <button
                          onClick={() => handleSaveTitle(file.id)}
                          className="title-save-btn"
                          title="Save"
                        >
                          <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                            <path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z"/>
                          </svg>
                        </button>
                        <button
                          onClick={() => {
                            setEditingTitleId(null);
                            setEditingTitle('');
                          }}
                          className="title-cancel-btn"
                          title="Cancel"
                        >
                          <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                            <path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/>
                          </svg>
                        </button>
                      </div>
                    ) : (
                      <h3 className="video-title" onClick={() => handleOpenPlayer(file.s3_url)}>
                        <RTLText>{file.metadata?.title || 'Untitled Video'}</RTLText>
                      </h3>
                    )}
                    <div className="video-meta-card">
                      {file.metadata?.uploader && (
                        <p className="video-channel"><RTLText>{file.metadata.uploader}</RTLText></p>
                      )}
                      <div className="video-stats">
                        {file.metadata?.duration && (
                          <span className="video-stat">{formatDuration(file.metadata.duration)}</span>
                        )}
                        {file.video_width && file.video_height && (
                          <span className="video-stat">{file.video_width}×{file.video_height}</span>
                        )}
                        <span className="video-stat">{new Date(file.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div className="video-actions-card">
                      <button 
                        onClick={() => handleOpenPlayer(file.s3_url)}
                        className="video-action-btn play-action"
                        title="Play"
                      >
                        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                          <path d="M8 5v14l11-7z"/>
                        </svg>
                      </button>
                      <button 
                        onClick={() => {
                          setEditingTitleId(file.id);
                          setEditingTitle(file.metadata?.title || 'Untitled Video');
                        }}
                        className="video-action-btn edit-action"
                        title="Edit title"
                      >
                        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                          <path d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z"/>
                        </svg>
                      </button>
                      <button 
                        onClick={() => handleOpenVideo(file.s3_url)}
                        className="video-action-btn open-action"
                        title="Open in new tab"
                      >
                        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                          <path d="M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V12H19V19Z"/>
                        </svg>
                      </button>
                      <button 
                        onClick={() => handleDeleteFile(file.id)}
                        className="video-action-btn delete-action"
                        title="Delete"
                      >
                        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                          <path d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"/>
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Download/Upload Form */}
        {(!savedFiles.length || showNewDownload) && !jobId && !status && (
          <div className="url-form">
            {savedFiles.length > 0 && (
              <div className="download-page-header">
                <button 
                  onClick={handleBackToMain}
                  className="back-to-main-btn"
                  title="Back to Saved Videos"
                >
                  <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                    <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
                  </svg>
                  <span>Back to Saved Videos</span>
                </button>
              </div>
            )}
            <div className="input-group">
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Paste video URL here (YouTube, Vimeo, etc.)"
                className="url-input"
              />
              <button 
                type="button" 
                onClick={handleSubmit}
                className="submit-btn"
                disabled={!url.trim()}
              >
                Download & Upload
              </button>
            </div>
            <div className="upload-divider">
              <span>OR</span>
            </div>
            <div className="file-upload-group">
              <label htmlFor="file-upload" className="file-upload-label">
                <input
                  id="file-upload"
                  type="file"
                  accept="video/*"
                  onChange={handleFileUpload}
                  className="file-upload-input"
                />
                <span className="file-upload-button">📁 Upload Video File</span>
                {fileUploadName && <span className="file-upload-name">{fileUploadName}</span>}
              </label>
            </div>
          </div>
        )}

        {/* Video Player Section - Shows YouTube video first, then S3 video after download */}
        {(url.trim() || s3Url) && (
          <div className="player-page-wrapper">
            <div className="player-content">
              <div className="player-main-section">
                <div className="player-video-section">
                  <div className="video-wrapper" style={{ position: 'relative' }}>
                    {s3Url ? (
                      <div 
                        ref={videoContainerRef}
                        className="dash-video-container"
                      />
                    ) : url.trim() ? (
                      <YouTubeEmbed 
                        url={url} 
                        onDurationChange={(duration) => {
                          setVideoDuration(duration);
                          if (!endTime) {
                            setEndTime(duration);
                          }
                        }}
                      />
                    ) : null}
                  </div>
                </div>

                
                {s3Url && status && status.stage === 'complete' && videoDuration && (
                  <div className="player-times-section">
                    <div className="time-selection-hint">
                      <span className="hint-icon">💡</span>
                      <span className="hint-text">Focus the player, then press <kbd>I</kbd> or <kbd>O</kbd></span>
                    </div>
                    <div className="time-selection-display">
                      <div className="time-display-item">
                        <span className="time-label">Start Time</span>
                        <span className="time-value">{formatTime(startTime)}</span>
                      </div>
                      <div className="time-display-item">
                        <span className="time-label">End Time</span>
                        <span className="time-value">{formatTime(endTime || videoDuration)}</span>
                      </div>
                      <div className="time-display-item">
                        <span className="time-label">Clip Duration</span>
                        <span className="time-value">{formatTime((endTime || videoDuration) - startTime)}</span>
                      </div>
                    </div>
                  </div>
                )}
                
                {s3Url && status && status.stage === 'complete' && (
                  <div className="player-info-section">
                    <div className="player-info-header">
                      <h1 className="player-video-title">
                        <RTLText>{status.metadata?.title || 'Video'}</RTLText>
                      </h1>
                      <div className="player-meta-info">
                        {status.metadata?.uploader && (
                          <span className="player-channel-name"><RTLText>{status.metadata.uploader}</RTLText></span>
                        )}
                        {status.metadata?.view_count && (
                          <span className="player-view-count">{status.metadata.view_count.toLocaleString()} views</span>
                        )}
                        {videoWidth && videoHeight && (
                          <span className="player-resolution">{videoWidth} × {videoHeight}</span>
                        )}
                      </div>
                    </div>
                    
                    <div className="player-actions-section">
                      <div className="player-action-buttons">
                        <button
                          onClick={handleSplit}
                          className="player-action-btn clip-btn"
                          disabled={!s3Url || !videoDuration}
                          title="Split video (Press I for start, O for end)"
                        >
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="20" height="20">
                            <path d="M6 9H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2h-2"/>
                            <path d="M6 15H4a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a2 2 0 0 0-2-2h-2"/>
                            <line x1="6" y1="12" x2="18" y2="12"/>
                          </svg>
                          <span>Clip</span>
                        </button>
                        
                        <a
                          href={s3Url}
                          download
                          className="player-action-btn download-btn"
                          title="Download video"
                        >
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="20" height="20">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="7 10 12 15 17 10"/>
                            <line x1="12" y1="15" x2="12" y2="3"/>
                          </svg>
                          <span>Download</span>
                        </a>
                        
                        {!savedFiles.some(file => file.s3_url === s3Url || file.job_id === jobId) && (
                          <button
                            onClick={handleSaveMetadata}
                            className="player-action-btn save-btn"
                            title="Save video to library"
                          >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="20" height="20">
                              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                              <polyline points="17 21 17 13 7 13 7 21"/>
                              <polyline points="7 3 7 8 15 8"/>
                            </svg>
                            <span>Save</span>
                          </button>
                        )}
                    </div>
                  </div>
                </div>
              )}

              <div className="player-footer">
                <button 
                  onClick={handleBackToMain}
                  className="back-to-main-btn"
                  title="Back to Saved Videos"
                >
                  <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                    <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
                  </svg>
                  <span>Back to Saved Videos</span>
                </button>
              </div>
              </div>

              {/* Storyboard Frames Section - Right Side Slider */}
              {s3Url && status && status.stage === 'complete' && (
                <div className="storyboard-section storyboard-sidebar">
                  {storyboardFrames.length > 0 ? (
                    <>
                      <h3 className="storyboard-title">📽️ Scene Shots ({storyboardFrames.length})</h3>
                      <div className="storyboard-frames-slider">
                        {storyboardFrames.map((frame) => {
                          // Use S3 URL directly if available, otherwise use API endpoint
                          const imageUrl = frame.image_url && frame.image_url.startsWith('http') 
                            ? frame.image_url 
                            : frame.image_url 
                              ? `${API_BASE_URL}${frame.image_url}`
                              : null;
                          
                          if (!imageUrl) {
                            console.warn('Frame missing image URL:', frame);
                            return null;
                          }
                          
                          // Format timestamp - convert to MM:SS format
                          const formatStoryboardTime = (timeStr) => {
                            if (!timeStr) return '00:00';
                            // If it's in HH:MM:SS.mmm format, convert to MM:SS
                            if (timeStr.includes(':')) {
                              const parts = timeStr.split(':');
                              if (parts.length === 3) {
                                // HH:MM:SS.mmm format
                                const hours = parseInt(parts[0]) || 0;
                                const mins = parseInt(parts[1]) || 0;
                                const secs = parseFloat(parts[2]) || 0;
                                const totalMins = hours * 60 + mins;
                                const secsInt = Math.floor(secs);
                                return `${totalMins.toString().padStart(2, '0')}:${secsInt.toString().padStart(2, '0')}`;
                              } else if (parts.length === 2) {
                                // Already MM:SS format
                                return timeStr.split('.')[0]; // Remove milliseconds if present
                              }
                            }
                            // If it's a number (seconds), format it
                            const seconds = parseFloat(timeStr);
                            if (!isNaN(seconds)) {
                              const mins = Math.floor(seconds / 60);
                              const secs = Math.floor(seconds % 60);
                              return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                            }
                            return timeStr;
                          };
                          
                          const displayTime = formatStoryboardTime(frame.time_str);
                          
                          return (
                            <div
                              key={frame.index}
                              className="storyboard-frame-item"
                              onClick={() => seekToTimestamp(frame.timestamp)}
                              title={`Click to jump to ${displayTime}`}
                            >
                              <img
                                src={imageUrl}
                                alt={`Frame at ${displayTime}`}
                                className="storyboard-frame-image"
                                loading="lazy"
                                onError={(e) => {
                                  console.error('Failed to load storyboard frame:', imageUrl);
                                  e.target.style.display = 'none';
                                }}
                              />
                              <div className="storyboard-frame-info">
                                <span className="storyboard-frame-time">{displayTime}</span>
                                {frame.keywords && frame.keywords.length > 0 && (
                                  <div className="storyboard-frame-keywords">
                                    {frame.keywords.slice(0, 3).map((keyword, kwIdx) => (
                                      <span key={kwIdx} className="storyboard-keyword-tag">
                                        <RTLText>{keyword}</RTLText>
                                      </span>
                                    ))}
                                    {frame.keywords.length > 3 && (
                                      <span className="storyboard-keyword-more">
                                        +{frame.keywords.length - 3}
                                      </span>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </>
                  ) : (
                    <div className="storyboard-loading">
                      <p>Loading storyboard frames...</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {error && (
          <div className="error-box">
            <h3>❌ Error</h3>
            <p><RTLText>{error}</RTLText></p>
            <button onClick={handleReset} className="reset-btn">
              Try Again
            </button>
          </div>
        )}

        {status && status.stage !== 'complete' && (
          <div className="status-container">
            <div className="status-card">
              <h2>Status: {status.stage.charAt(0).toUpperCase() + status.stage.slice(1)}</h2>
              
              {status.stage === 'download' && (
                <div className="progress-section">
                  <h3>📥 Downloading Video</h3>
                  <div className="progress-bar-container">
                    <div 
                      className="progress-bar" 
                      style={{ width: `${Math.max(0, Math.min(100, status.percent))}%` }}
                    />
                  </div>
                  <div className="progress-info">
                    <span>{status.percent.toFixed(1)}%</span>
                    {status.speed && <span>Speed: {status.speed}</span>}
                    {status.eta && <span>ETA: {status.eta}</span>}
                  </div>
                  <p className="status-message"><RTLText>{status.message}</RTLText></p>
                  <button onClick={handleCancel} className="cancel-btn">
                    ⏹️ Cancel Download
                  </button>
                </div>
              )}

              {status.stage === 'cancelled' && (
                <div className="error-section">
                  <h3>⏹️ Cancelled</h3>
                  <p><RTLText>{status.message || 'Download was cancelled'}</RTLText></p>
                  <button onClick={handleReset} className="reset-btn">
                    Start New Download
                  </button>
                </div>
              )}

              {status.stage === 'upload' && (
                <div className="progress-section">
                  <h3>☁️ Uploading to S3</h3>
                  <div className="progress-bar-container">
                    <div 
                      className="progress-bar upload" 
                      style={{ width: `${status.percent}%` }}
                    />
                  </div>
                  <div className="progress-info">
                    <span>{status.percent.toFixed(1)}%</span>
                    {status.speed && <span>Speed: {status.speed}</span>}
                  </div>
                  <p className="status-message"><RTLText>{status.message}</RTLText></p>
                </div>
              )}

              {status.stage === 'split' && (
                <div className="progress-section">
                  <h3>✂️ Splitting Video</h3>
                  <div className="progress-bar-container">
                    <div 
                      className="progress-bar split" 
                      style={{ width: `${status.percent}%` }}
                    />
                  </div>
                  <div className="progress-info">
                    <span>{status.percent.toFixed(1)}%</span>
                  </div>
                  <p className="status-message"><RTLText>{status.message}</RTLText></p>
                  <button onClick={handleCancel} className="cancel-btn">
                    ⏹️ Cancel Split
                  </button>
                </div>
              )}


              {status.stage === 'error' && (
                <div className="error-section">
                  <h3>❌ Error</h3>
                  <p><RTLText>{status.message || 'An error occurred'}</RTLText></p>
                  <button onClick={handleReset} className="reset-btn">
                    Try Again
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {jobId && !status && (
          <div className="loading">
            <p>Connecting to server...</p>
          </div>
        )}

        {/* Playlist Selection Modal */}
        {showPlaylistModal && (
          <div className="modal-overlay" onClick={() => setShowPlaylistModal(false)}>
            <div className="playlist-modal" onClick={(e) => e.stopPropagation()}>
              <div className="playlist-modal-header">
                <h2>Save to Playlist</h2>
                <button 
                  className="modal-close-btn"
                  onClick={() => setShowPlaylistModal(false)}
                >
                  <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
                    <path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/>
                  </svg>
                </button>
              </div>
              
              {!showCreatePlaylist ? (
                <div className="playlist-modal-content">
                  <div className="playlist-select-section">
                    <label className="playlist-label">
                      Select Playlist <span className="required">*</span>
                    </label>
                    <select
                      value={selectedPlaylistId || ''}
                      onChange={(e) => setSelectedPlaylistId(e.target.value || null)}
                      className="playlist-select"
                    >
                      <option value="">No Playlist</option>
                      {playlists.map(playlist => (
                        <option key={playlist.id} value={playlist.id} dir={isPersianText(playlist.title) ? 'rtl' : 'ltr'}>
                          {playlist.title}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <button
                    className="create-playlist-btn"
                    onClick={() => setShowCreatePlaylist(true)}
                  >
                    ➕ Create New Playlist
                  </button>
                  
                  <div className="playlist-modal-actions">
                    <button
                      className="playlist-cancel-btn"
                      onClick={() => {
                        setShowPlaylistModal(false);
                        setSelectedPlaylistId(null);
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      className="playlist-save-btn"
                      onClick={handleConfirmSave}
                    >
                      <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                        <path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z"/>
                      </svg>
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <div className="playlist-modal-content">
                  <div className="create-playlist-section">
                    <label className="playlist-label">
                      Playlist Title <span className="required">*</span>
                    </label>
                    <input
                      type="text"
                      value={newPlaylistTitle}
                      onChange={(e) => setNewPlaylistTitle(e.target.value)}
                      placeholder="Enter a title for your playlist"
                      className="playlist-input"
                      maxLength={100}
                    />
                    
                    <label className="playlist-label">Description</label>
                    <textarea
                      value={newPlaylistDescription}
                      onChange={(e) => {
                        const value = e.target.value;
                        if (value.length <= 50) {
                          setNewPlaylistDescription(value);
                        }
                      }}
                      placeholder="Add playlist description"
                      className="playlist-textarea"
                      rows={3}
                      maxLength={50}
                    />
                    <div className="char-counter">
                      {newPlaylistDescription.length} of 50
                    </div>
                    
                    <label className="playlist-label">
                      Publish Status <span className="required">*</span>
                    </label>
                    <select
                      value={newPlaylistStatus}
                      onChange={(e) => setNewPlaylistStatus(e.target.value)}
                      className="playlist-select"
                    >
                      <option value="private">Private</option>
                      <option value="public">Public</option>
                      <option value="unlisted">Unlisted</option>
                    </select>
                  </div>
                  
                  <div className="playlist-modal-actions">
                    <button
                      className="playlist-cancel-btn"
                      onClick={() => {
                        setShowCreatePlaylist(false);
                        setNewPlaylistTitle('');
                        setNewPlaylistDescription('');
                        setNewPlaylistStatus('private');
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      className="playlist-save-btn"
                      onClick={handleCreatePlaylist}
                      disabled={!newPlaylistTitle.trim()}
                    >
                      <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                        <path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z"/>
                      </svg>
                      Create
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;


