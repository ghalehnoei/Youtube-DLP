import React from 'react';

const DownloadForm = ({ 
  url, 
  setUrl, 
  onSubmit, 
  onFileUpload, 
  fileUploadName,
  showBackButton,
  onBack
}) => {
  return (
    <div className="url-form">
      {showBackButton && (
        <div className="download-page-header">
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
      )}
      <div className="input-group">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="آدرس ویدیو را اینجا بچسبانید (یوتیوب، ویمئو و ...)"
          className="url-input"
        />
        <button 
          type="button" 
          onClick={onSubmit}
          className="submit-btn"
          disabled={!url.trim()}
        >
          دانلود و آپلود
        </button>
      </div>
      <div className="upload-divider">
        <span>یا</span>
      </div>
      <div className="file-upload-group">
        <label htmlFor="file-upload" className="file-upload-label">
          <input
            id="file-upload"
            type="file"
            accept="video/*"
            onChange={onFileUpload}
            className="file-upload-input"
          />
          <span className="file-upload-button">📁 آپلود فایل ویدیو</span>
          {fileUploadName && <span className="file-upload-name">{fileUploadName}</span>}
        </label>
      </div>
    </div>
  );
};

export default DownloadForm;

