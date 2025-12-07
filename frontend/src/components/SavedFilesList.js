import React from 'react';
import VideoCard from './VideoCard';
import { isPersianText } from '../utils/textUtils';

const SavedFilesList = ({ 
  savedFiles, 
  searchQuery, 
  selectedPlaylistFilter,
  playlists,
  onPlay, 
  onDelete, 
  onTitleUpdate,
  onNewDownload,
  onFilterChange,
  onSearchChange
}) => {
  const filteredFiles = savedFiles.filter(file => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    const title = (file.metadata?.title || 'ویدیو بدون عنوان').toLowerCase();
    const uploader = (file.metadata?.uploader || '').toLowerCase();
    return title.includes(query) || uploader.includes(query);
  });

  // Separate vertical and horizontal videos
  const verticalVideos = filteredFiles.filter(file => {
    return file.video_height && file.video_width && file.video_height > file.video_width;
  });

  const horizontalVideos = filteredFiles.filter(file => {
    return !file.video_height || !file.video_width || file.video_height <= file.video_width;
  });

  return (
    <div className="saved-files-section">
      <div className="saved-files-header">
        <h2>ویدیوهای ذخیره شده</h2>
        <div className="header-actions">
          <select
            value={selectedPlaylistFilter || ''}
            onChange={(e) => onFilterChange(e.target.value || null)}
            className="playlist-filter-select"
          >
            <option value="">همه پلی‌لیست‌ها</option>
            <option value="none">بدون پلی‌لیست</option>
            {playlists.map(playlist => (
              <option key={playlist.id} value={playlist.id} dir={isPersianText(playlist.title) ? 'rtl' : 'ltr'}>
                {playlist.title}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="🔍 جستجوی ویدیو..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="search-input"
          />
          <button 
            onClick={onNewDownload}
            className="new-download-btn"
          >
            ➕ دانلود جدید
          </button>
        </div>
      </div>

      {/* Horizontal Videos Section */}
      {horizontalVideos.length > 0 && (
        <div className="videos-section horizontal-videos-section">
          <h3 className="section-title">ویدیوهای افقی</h3>
          <div className="saved-files-grid horizontal-videos-grid">
            {horizontalVideos.map((file) => (
              <VideoCard
                key={file.id}
                file={file}
                onPlay={onPlay}
                onDelete={onDelete}
                onTitleUpdate={onTitleUpdate}
              />
            ))}
          </div>
        </div>
      )}

      {/* Vertical Videos Section */}
      {verticalVideos.length > 0 && (
        <div className="videos-section vertical-videos-section">
          <h3 className="section-title">ویدیوهای عمودی</h3>
          <div className="saved-files-grid vertical-videos-grid">
            {verticalVideos.map((file) => (
              <VideoCard
                key={file.id}
                file={file}
                onPlay={onPlay}
                onDelete={onDelete}
                onTitleUpdate={onTitleUpdate}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {filteredFiles.length === 0 && (
        <div className="empty-state">
          <p>ویدیویی یافت نشد</p>
        </div>
      )}
    </div>
  );
};

export default SavedFilesList;

