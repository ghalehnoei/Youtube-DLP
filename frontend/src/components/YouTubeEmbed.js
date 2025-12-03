import React, { useEffect } from 'react';

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
  useEffect(() => {
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

export default YouTubeEmbed;

