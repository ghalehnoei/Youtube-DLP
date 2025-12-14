import React from 'react';

const DownloadForm = ({ 
  url, 
  setUrl, 
  onSubmit, 
  onFileUpload, 
  fileUploadName
}) => {
  return (
    <div className="url-form">
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

