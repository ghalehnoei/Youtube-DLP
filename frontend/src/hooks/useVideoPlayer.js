import { useEffect, useRef } from 'react';
import dashjs from 'dashjs';

export const useVideoPlayer = (s3Url, videoDuration, onMetadataLoaded) => {
  const videoContainerRef = useRef(null);
  const videoRef = useRef(null);
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
      if (onMetadataLoaded) {
        onMetadataLoaded(e);
      }
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
  }, [s3Url, videoDuration, onMetadataLoaded]);

  // Function to seek video to a specific timestamp
  const seekToTimestamp = (timestamp) => {
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
  };

  return {
    videoContainerRef,
    videoRef,
    dashPlayerRef,
    seekToTimestamp
  };
};

