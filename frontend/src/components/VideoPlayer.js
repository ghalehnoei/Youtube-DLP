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
  onBack,
  onSeek
}) => {
  if (!url.trim() && !s3Url) return null;

  const title = status?.metadata?.title || 'ویدیو';
  const uploader = status?.metadata?.uploader || '';
  const titleIsPersian = isPersianText(title);
  const uploaderIsPersian = isPersianText(uploader);
  const isComplete = status && status.stage === 'complete';

  return (
    <div className="player-page-wrapper">
      <div className="player-content">
        <>
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
                    onDurationChange={() => {}}
                  />
                ) : null}
              </div>
            </div>
            
            {s3Url && isComplete && (
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
            
            {s3Url && isComplete && (
              <div className="player-actions-section">
                  <div className="player-action-buttons">
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

