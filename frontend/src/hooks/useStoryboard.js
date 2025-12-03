import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const useStoryboard = (jobId, status, s3Url) => {
  const [storyboardFrames, setStoryboardFrames] = useState([]);

  useEffect(() => {
    const loadStoryboardFrames = async () => {
      if (!status || status.stage !== 'complete') {
        setStoryboardFrames([]);
        return;
      }

      console.log('Loading storyboard frames...', { jobId, metadata: status.metadata });

      // First, check if frames are directly in metadata (for saved files)
      if (status.metadata && status.metadata.frames && Array.isArray(status.metadata.frames)) {
        console.log('Found frames in metadata:', status.metadata.frames.length);
        // Convert frames to the format expected by the UI
        const frames = status.metadata.frames.map(frame => ({
          index: frame.index,
          timestamp: frame.timestamp,
          time_str: frame.time_str,
          image_url: frame.image_s3_url || frame.image_url || `/api/storyboard/${status.metadata.storyboard_job_id || jobId}/frame/${frame.index}`,
          keywords: frame.keywords || []
        }));
        if (frames.length > 0) {
          setStoryboardFrames(frames);
          return;
        }
      }

      // Try to get storyboard frames from job_id if available
      if (jobId) {
        try {
          console.log('Fetching storyboard frames from jobId:', jobId);
          const response = await axios.get(`${API_BASE_URL}/api/storyboard/${jobId}/frames`);
          if (response.data && response.data.frames) {
            console.log('Found frames from jobId:', response.data.frames.length);
            setStoryboardFrames(response.data.frames);
            return;
          }
        } catch (err) {
          console.log('Failed to fetch from jobId:', err.response?.status, err.message);
          // Continue to try storyboard_job_id
        }
      }

      // Try storyboard_job_id from metadata
      if (status.metadata && status.metadata.storyboard_job_id) {
        try {
          const storyboardJobId = status.metadata.storyboard_job_id;
          console.log('Fetching storyboard frames from storyboard_job_id:', storyboardJobId);
          const response = await axios.get(`${API_BASE_URL}/api/storyboard/${storyboardJobId}/frames`);
          if (response.data && response.data.frames) {
            console.log('Found frames from storyboard_job_id:', response.data.frames.length);
            setStoryboardFrames(response.data.frames);
            return;
          }
        } catch (err2) {
          // Storyboard not available yet or doesn't exist
          console.log('Storyboard not found from storyboard_job_id:', err2.response?.status, err2.message);
        }
      }

      // If we get here, no storyboard was found
      console.log('No storyboard frames found');
      setStoryboardFrames([]);
    };

    loadStoryboardFrames();
  }, [jobId, status, s3Url]);

  return storyboardFrames;
};

