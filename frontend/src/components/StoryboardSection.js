import React from 'react';
import RTLText from './RTLText';
import { formatStoryboardTime } from '../utils/timeUtils';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const StoryboardSection = ({ frames, onSeek }) => {
  if (frames.length === 0) {
    return (
      <div className="storyboard-section storyboard-sidebar">
        <div className="storyboard-loading">
          <p>Loading storyboard frames...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="storyboard-section storyboard-sidebar">
      <h3 className="storyboard-title">📽️ Scene Shots ({frames.length})</h3>
      <div className="storyboard-frames-slider">
        {frames.map((frame) => {
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
          
          const displayTime = formatStoryboardTime(frame.time_str);
          
          return (
            <div
              key={frame.index}
              className="storyboard-frame-item"
              onClick={() => onSeek(frame.timestamp)}
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
    </div>
  );
};

export default StoryboardSection;

