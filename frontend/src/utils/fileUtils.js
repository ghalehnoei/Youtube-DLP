// Format file size
export const formatFileSize = (bytes) => {
  if (!bytes) return 'Unknown';
  const mb = bytes / (1024 * 1024);
  if (mb < 1) return `${(bytes / 1024).toFixed(2)} KB`;
  return `${mb.toFixed(2)} MB`;
};

