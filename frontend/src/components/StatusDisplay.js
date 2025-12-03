import React from 'react';
import RTLText from './RTLText';

const StatusDisplay = ({ status, onCancel, onReset }) => {
  if (!status) return null;

  const percent = status.percent || 0;
  const stage = status.stage || 'unknown';

  const getStageDisplayName = (stage) => {
    const names = {
      connecting: 'در حال اتصال',
      download: 'در حال دانلود',
      upload: 'در حال آپلود',
      complete: 'تکمیل شد',
      error: 'خطا',
      cancelled: 'لغو شد'
    };
    return names[stage] || stage.charAt(0).toUpperCase() + stage.slice(1);
  };

  return (
    <div className="status-container">
      <div className="status-card">
        <h2>وضعیت: {getStageDisplayName(stage)}</h2>
        
        {stage === 'connecting' && (
          <div className="progress-section">
            <h3>🔌 در حال اتصال به سرور</h3>
            <div className="progress-bar-container">
              <div className="progress-bar connecting" style={{ width: '100%' }} />
            </div>
            <p className="status-message">
              <RTLText>{status.message || 'در حال برقراری اتصال...'}</RTLText>
            </p>
          </div>
        )}

        {stage === 'download' && (
          <div className="progress-section">
            <h3>📥 در حال دانلود ویدیو</h3>
            <div className="progress-bar-container">
              <div 
                className="progress-bar" 
                style={{ width: `${Math.max(0, Math.min(100, percent))}%` }}
              />
            </div>
            <div className="progress-info">
              <span><strong>{percent.toFixed(1)}%</strong></span>
              {status.speed && <span>سرعت: {status.speed}</span>}
              {status.eta && <span>زمان باقی‌مانده: {status.eta}</span>}
            </div>
            <p className="status-message">
              <RTLText>{status.message || 'در حال دانلود ویدیو...'}</RTLText>
            </p>
            {onCancel && (
              <button onClick={onCancel} className="cancel-btn">
                ⏹️ لغو دانلود
              </button>
            )}
          </div>
        )}

        {stage === 'upload' && (
          <div className="progress-section">
            <h3>☁️ در حال آپلود به S3</h3>
            <div className="progress-bar-container">
              <div 
                className="progress-bar upload" 
                style={{ width: `${Math.max(0, Math.min(100, percent))}%` }}
              />
            </div>
            <div className="progress-info">
              <span><strong>{percent.toFixed(1)}%</strong></span>
              {status.speed && <span>سرعت: {status.speed}</span>}
              {status.uploaded && <span>آپلود شده: {status.uploaded}</span>}
            </div>
            <p className="status-message">
              <RTLText>{status.message || 'در حال آپلود به S3...'}</RTLText>
            </p>
          </div>
        )}

        {stage === 'cancelled' && (
          <div className="error-section">
            <h3>⏹️ لغو شد</h3>
            <p className="status-message">
              <RTLText>{status.message || 'دانلود لغو شد'}</RTLText>
            </p>
            {onReset && (
              <button onClick={onReset} className="reset-btn">
                شروع دانلود جدید
              </button>
            )}
          </div>
        )}

        {stage === 'error' && (
          <div className="error-section">
            <h3>❌ خطا</h3>
            <p className="status-message">
              <RTLText>{status.message || 'خطایی در هنگام دانلود رخ داد'}</RTLText>
            </p>
            {onReset && (
              <button onClick={onReset} className="reset-btn">
                تلاش مجدد
              </button>
            )}
          </div>
        )}

        {stage === 'complete' && (
          <div className="complete-section">
            <div className="success-icon">✅</div>
            <h3>تکمیل شد!</h3>
            <p className="status-message">
              <RTLText>{status.message || 'دانلود و آپلود با موفقیت انجام شد'}</RTLText>
            </p>
            {onReset && (
              <button onClick={onReset} className="reset-btn">
                شروع دانلود جدید
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default StatusDisplay;

