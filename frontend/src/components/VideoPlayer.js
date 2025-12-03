import React from 'react';
import YouTubeEmbed from './YouTubeEmbed';
import RTLText from './RTLText';
import StoryboardSection from './StoryboardSection';
import { isPersianText } from '../utils/textUtils';
const VideoPlayer = ({
  url,
  s3Url,
  status,
  videoDuration,
  videoWidth,
  videoHeight,
  savedFiles,
  jobId,
  videoContainerRef,
  storyboardFrames,
  onSave,
  onBack,
  onSeek
}) => {
  if (!url.trim() && !s3Url) return null;

  const title = status?.metadata?.title || 'Video';
  const uploader = status?.metadata?.uploader || '';
  const titleIsPersian = isPersianText(title);
  const uploaderIsPersian = isPersianText(uploader);
  const isComplete = status && status.stage === 'complete';
  const isAlreadySaved = savedFiles.some(file => file.s3_url === s3Url || file.job_id === jobId);

  return (
    <div className="player-page-wrapper">
      <div className="player-content">
        <>
          <div className="player-main-section">
            {s3Url && isComplete && (
              <div className="player-info-section player-info-top">
                <div className="player-info-header">
                  <h1 className="player-video-title" dir={titleIsPersian ? 'rtl' : 'ltr'}>
                    <RTLText>{title}</RTLText>
                  </h1>
                  <div className="player-meta-info">
                    {uploader && (
                      <span className="player-channel-name" dir={uploaderIsPersian ? 'rtl' : 'ltr'}>
                        <RTLText>{uploader}</RTLText>
                      </span>
                    )}
                    {status?.metadata?.view_count && (
                      <span className="player-view-count">{status.metadata.view_count.toLocaleString()} views</span>
                    )}
                    {videoWidth && videoHeight && (
                      <span className="player-resolution">{videoWidth} × {videoHeight}</span>
                    )}
                  </div>
                </div>
              </div>
            )}
            
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
                    onDurationChange={() => {}}
                  />
                ) : null}
              </div>
            </div>
            
            {s3Url && isComplete && (
              <div className="player-actions-section">
                  <div className="player-action-buttons">
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
                    
                    {!isAlreadySaved && (
                      <button
                        onClick={onSave}
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
            )}
            
            <div className="player-footer">
              <button 
                onClick={onBack}
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

          {s3Url && isComplete && (
            <StoryboardSection
              frames={storyboardFrames || []}
              onSeek={onSeek}
            />
          )}
        </>
      </div>
    </div>
  );
};

export default VideoPlayer;

