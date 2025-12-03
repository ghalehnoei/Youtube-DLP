// Format time in MM:SS format
export const formatTime = (seconds) => {
  if (!seconds && seconds !== 0) return '00:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

// Format duration in HH:MM:SS or MM:SS format
export const formatDuration = (seconds) => {
  if (!seconds) return '00:00';
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

// Format storyboard time - convert to MM:SS format
export const formatStoryboardTime = (timeStr) => {
  if (!timeStr) return '00:00';
  // If it's in HH:MM:SS.mmm format, convert to MM:SS
  if (timeStr.includes(':')) {
    const parts = timeStr.split(':');
    if (parts.length === 3) {
      // HH:MM:SS.mmm format
      const hours = parseInt(parts[0]) || 0;
      const mins = parseInt(parts[1]) || 0;
      const secs = parseFloat(parts[2]) || 0;
      const totalMins = hours * 60 + mins;
      const secsInt = Math.floor(secs);
      return `${totalMins.toString().padStart(2, '0')}:${secsInt.toString().padStart(2, '0')}`;
    } else if (parts.length === 2) {
      // Already MM:SS format
      return timeStr.split('.')[0]; // Remove milliseconds if present
    }
  }
  // If it's a number (seconds), format it
  const seconds = parseFloat(timeStr);
  if (!isNaN(seconds)) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return timeStr;
};

