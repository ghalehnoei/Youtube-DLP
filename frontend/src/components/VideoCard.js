import React, { useState } from 'react';
import axios from 'axios';
import RTLText from './RTLText';
import { isPersianText } from '../utils/textUtils';
import { formatDuration } from '../utils/timeUtils';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const VideoCard = ({ file, onPlay, onDelete, onTitleUpdate }) => {
  const [editingTitleId, setEditingTitleId] = useState(null);
  const [editingTitle, setEditingTitle] = useState('');

  const handleSaveTitle = async (fileId) => {
    if (!editingTitle.trim()) {
      setEditingTitleId(null);
      setEditingTitle('');
      return;
    }
    
    try {
      await axios.put(`${API_BASE_URL}/api/files/${fileId}`, {
        title: editingTitle.trim()
      });
      if (onTitleUpdate) onTitleUpdate();
      setEditingTitleId(null);
      setEditingTitle('');
    } catch (err) {
      console.error('Error updating title:', err);
      alert('به‌روزرسانی عنوان با خطا مواجه شد');
    }
  };

  const handleOpenVideo = (s3Url) => {
    window.open(s3Url, '_blank');
  };

  const title = file.metadata?.title || 'ویدیو بدون عنوان';
  const uploader = file.metadata?.uploader || '';
  const titleIsPersian = isPersianText(title);
  const uploaderIsPersian = isPersianText(uploader);

  return (
    <div className="saved-video-card">
      <div className="video-thumbnail-container" onClick={() => onPlay(file.s3_url)}>
        {file.thumbnail_url ? (
          <img 
            src={file.thumbnail_url} 
            alt={title}
            className="video-thumbnail"
          />
        ) : (
          <div className="video-thumbnail-placeholder">
            <span>📹</span>
          </div>
        )}
        <div className="video-duration-overlay">
          {file.metadata?.duration && formatDuration(file.metadata.duration)}
        </div>
        <div className="play-overlay">
          <svg viewBox="0 0 24 24" fill="white" width="48" height="48">
            <path d="M8 5v14l11-7z"/>
          </svg>
        </div>
      </div>
      <div className="video-info-card">
        {editingTitleId === file.id ? (
          <div className="title-edit-container">
            <input
              type="text"
              value={editingTitle}
              onChange={(e) => setEditingTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleSaveTitle(file.id);
                } else if (e.key === 'Escape') {
                  setEditingTitleId(null);
                  setEditingTitle('');
                }
              }}
              className="title-edit-input"
              autoFocus
            />
            <button
              onClick={() => handleSaveTitle(file.id)}
              className="title-save-btn"
              title="Save"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                <path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z"/>
              </svg>
            </button>
            <button
              onClick={() => {
                setEditingTitleId(null);
                setEditingTitle('');
              }}
              className="title-cancel-btn"
              title="لغو"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                <path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/>
              </svg>
            </button>
          </div>
        ) : (
          <h3 className="video-title" onClick={() => onPlay(file.s3_url)} dir={titleIsPersian ? 'rtl' : 'ltr'}>
            <RTLText>{title}</RTLText>
          </h3>
        )}
        <div className="video-meta-card">
          {uploader && (
            <p className="video-channel" dir={uploaderIsPersian ? 'rtl' : 'ltr'}>
              <RTLText>{uploader}</RTLText>
            </p>
          )}
          <div className="video-stats">
            {file.metadata?.duration && (
              <span className="video-stat">{formatDuration(file.metadata.duration)}</span>
            )}
            {file.video_width && file.video_height && (
              <span className="video-stat">{file.video_width}×{file.video_height}</span>
            )}
            <span className="video-stat">{new Date(file.created_at).toLocaleDateString()}</span>
          </div>
        </div>
        <div className="video-actions-card">
          <button 
            onClick={() => onPlay(file.s3_url)}
            className="video-action-btn play-action"
            title="پخش"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
              <path d="M8 5v14l11-7z"/>
            </svg>
          </button>
          <button 
            onClick={() => {
              setEditingTitleId(file.id);
              setEditingTitle(title);
            }}
            className="video-action-btn edit-action"
            title="ویرایش عنوان"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
              <path d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z"/>
            </svg>
          </button>
          <button 
            onClick={() => handleOpenVideo(file.s3_url)}
            className="video-action-btn open-action"
            title="باز کردن در تب جدید"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
              <path d="M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V12H19V19Z"/>
            </svg>
          </button>
          <button 
            onClick={() => onDelete(file.id)}
            className="video-action-btn delete-action"
            title="حذف"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
              <path d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default VideoCard;

