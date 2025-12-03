import React from 'react';
import RTLText from './RTLText';

const StatusDisplay = ({ status, onCancel, onReset }) => {
  if (!status || status.stage === 'complete') return null;

  return (
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
            <button onClick={onCancel} className="cancel-btn">
              ⏹️ Cancel Download
            </button>
          </div>
        )}

        {status.stage === 'cancelled' && (
          <div className="error-section">
            <h3>⏹️ Cancelled</h3>
            <p><RTLText>{status.message || 'Download was cancelled'}</RTLText></p>
            <button onClick={onReset} className="reset-btn">
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

        {status.stage === 'error' && (
          <div className="error-section">
            <h3>❌ Error</h3>
            <p><RTLText>{status.message || 'An error occurred'}</RTLText></p>
            <button onClick={onReset} className="reset-btn">
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default StatusDisplay;

