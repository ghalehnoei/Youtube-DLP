import React from 'react';
import { isPersianText } from '../utils/textUtils';

const PlaylistModal = ({
  show,
  playlists,
  selectedPlaylistId,
  showCreatePlaylist,
  newPlaylistTitle,
  newPlaylistDescription,
  newPlaylistStatus,
  onClose,
  onSelectPlaylist,
  onSave,
  onCreatePlaylist,
  onShowCreatePlaylist,
  onHideCreatePlaylist,
  onTitleChange,
  onDescriptionChange,
  onStatusChange
}) => {
  if (!show) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="playlist-modal" onClick={(e) => e.stopPropagation()}>
        <div className="playlist-modal-header">
          <h2>Save to Playlist</h2>
          <button 
            className="modal-close-btn"
            onClick={onClose}
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
              <path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/>
            </svg>
          </button>
        </div>
        
        {!showCreatePlaylist ? (
          <div className="playlist-modal-content">
            <div className="playlist-select-section">
              <label className="playlist-label">
                Select Playlist <span className="required">*</span>
              </label>
              <select
                value={selectedPlaylistId || ''}
                onChange={(e) => onSelectPlaylist(e.target.value || null)}
                className="playlist-select"
              >
                <option value="">No Playlist</option>
                {playlists.map(playlist => (
                  <option key={playlist.id} value={playlist.id} dir={isPersianText(playlist.title) ? 'rtl' : 'ltr'}>
                    {playlist.title}
                  </option>
                ))}
              </select>
            </div>
            
            <button
              className="create-playlist-btn"
              onClick={onShowCreatePlaylist}
            >
              ➕ Create New Playlist
            </button>
            
            <div className="playlist-modal-actions">
              <button
                className="playlist-cancel-btn"
                onClick={onClose}
              >
                Cancel
              </button>
              <button
                className="playlist-save-btn"
                onClick={onSave}
              >
                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z"/>
                </svg>
                Save
              </button>
            </div>
          </div>
        ) : (
          <div className="playlist-modal-content">
            <div className="create-playlist-section">
              <label className="playlist-label">
                Playlist Title <span className="required">*</span>
              </label>
              <input
                type="text"
                value={newPlaylistTitle}
                onChange={(e) => onTitleChange(e.target.value)}
                placeholder="Enter a title for your playlist"
                className="playlist-input"
                maxLength={100}
              />
              
              <label className="playlist-label">Description</label>
              <textarea
                value={newPlaylistDescription}
                onChange={(e) => {
                  const value = e.target.value;
                  if (value.length <= 50) {
                    onDescriptionChange(value);
                  }
                }}
                placeholder="Add playlist description"
                className="playlist-textarea"
                rows={3}
                maxLength={50}
              />
              <div className="char-counter">
                {newPlaylistDescription.length} of 50
              </div>
              
              <label className="playlist-label">
                Publish Status <span className="required">*</span>
              </label>
              <select
                value={newPlaylistStatus}
                onChange={(e) => onStatusChange(e.target.value)}
                className="playlist-select"
              >
                <option value="private">Private</option>
                <option value="public">Public</option>
                <option value="unlisted">Unlisted</option>
              </select>
            </div>
            
            <div className="playlist-modal-actions">
              <button
                className="playlist-cancel-btn"
                onClick={onHideCreatePlaylist}
              >
                Cancel
              </button>
              <button
                className="playlist-save-btn"
                onClick={onCreatePlaylist}
                disabled={!newPlaylistTitle.trim()}
              >
                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z"/>
                </svg>
                Create
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PlaylistModal;

