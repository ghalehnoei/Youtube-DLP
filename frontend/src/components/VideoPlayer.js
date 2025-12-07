import React from 'react';
import YouTubeEmbed from './YouTubeEmbed';
import RTLText from './RTLText';
import StoryboardSection from './StoryboardSection';
import StatusDisplay from './StatusDisplay';
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
  onBack,
  onSeek,
  onConvert,
  isConverting,
  onCancel,
  onReset
}) => {
  // Always show if we have s3Url, status, or jobId
  const shouldShow = url.trim() || s3Url || status || jobId;
  if (!shouldShow) {
    console.log('VideoPlayer: Not showing (no url, s3Url, status, or jobId)');
    return null;
  }
  
  console.log('VideoPlayer: Rendering with', { url: !!url.trim(), s3Url: !!s3Url, status: !!status, jobId });

  const title = status?.metadata?.title || 'ویدیو';
  const uploader = status?.metadata?.uploader || '';
  const titleIsPersian = isPersianText(title);
  const uploaderIsPersian = isPersianText(uploader);
  const isComplete = status && status.stage === 'complete';
  // Show processing if we have jobId and status is not complete/error/cancelled
  // OR if we have jobId but no status yet (connecting)
  const isProcessing = jobId && status && status.stage !== 'complete' && status.stage !== 'error' && status.stage !== 'cancelled';
  const isConnecting = jobId && !status;
  
  // Debug logging
  if (jobId) {
    console.log('VideoPlayer render:', { jobId, status, isProcessing, isConnecting, isComplete });
  }

  return (
    <div className="player-page-wrapper">
      <div className="player-content">
        <>
          {/* Show status during conversion */}
          {(isProcessing || isConnecting) && (
            <div className="player-status-section">
              <StatusDisplay
                status={status || {
                  stage: 'connecting',
                  message: 'در حال اتصال به سرور...',
                  percent: 0
                }}
                onCancel={onCancel}
                onReset={onReset}
              />
            </div>
          )}
          
          <div className="player-main-section">
            <div className="player-video-section">
              <div className="video-wrapper" style={{ position: 'relative' }}>
                {s3Url && !isProcessing ? (
                  <div 
                    ref={videoContainerRef}
                    className="dash-video-container"
                  />
                ) : s3Url && isProcessing ? (
                  <div className="video-placeholder">
                    <div className="video-placeholder-content">
                      <div className="loading-spinner"></div>
                      <p>در حال تبدیل ویدیو...</p>
                    </div>
                  </div>
                ) : url.trim() ? (
                  <YouTubeEmbed 
                    url={url} 
                    onDurationChange={() => {}}
                  />
                ) : null}
              </div>
            </div>
            
            {s3Url && isComplete && !isProcessing && (
              <div className="player-info-section">
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
                      <span className="player-view-count">{status.metadata.view_count.toLocaleString()} بازدید</span>
                    )}
                    {videoWidth && videoHeight && (
                      <span className="player-resolution">{videoWidth} × {videoHeight}</span>
                    )}
                  </div>
                </div>
              </div>
            )}
            
            {s3Url && isComplete && !isProcessing && (
              <div className="player-actions-section">
                  <div className="player-action-buttons">
                    {videoHeight && videoWidth && videoHeight > videoWidth && (
                      <button
                        onClick={onConvert}
                        className="player-action-btn convert-btn"
                        title="تبدیل به افقی"
                        disabled={isConverting}
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="20" height="20">
                          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                          <line x1="9" y1="3" x2="9" y2="21"/>
                          <line x1="15" y1="3" x2="15" y2="21"/>
                        </svg>
                        <span>{isConverting ? 'در حال تبدیل...' : 'تبدیل به افقی'}</span>
                      </button>
                    )}
                    <a
                      href={s3Url}
                      download
                      className="player-action-btn download-btn"
                      title="دانلود ویدیو"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="20" height="20">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                      </svg>
                      <span>دانلود</span>
                    </a>
                  </div>
                </div>
            )}
            
            <div className="player-footer">
              <button 
                onClick={onBack}
                className="back-to-main-btn"
                title="بازگشت به ویدیوهای ذخیره شده"
              >
                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
                </svg>
                <span>بازگشت به ویدیوهای ذخیره شده</span>
              </button>
            </div>
          </div>

          {s3Url && isComplete && !isProcessing && (
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

