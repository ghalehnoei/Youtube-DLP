import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import StatusDisplay from './StatusDisplay';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const ActiveJobsList = ({ onJobClick, onCancelJob }) => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [includeCompleted, setIncludeCompleted] = useState(false);
  const websocketsRef = useRef({});

  const loadJobs = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/jobs?include_completed=${includeCompleted}`);
      console.log('Jobs API response:', response.data);
      if (response.data && response.data.jobs) {
        console.log('Setting jobs:', response.data.jobs);
        setJobs(response.data.jobs);
      } else {
        console.log('No jobs in response, setting empty array');
        setJobs([]);
      }
    } catch (err) {
      console.error('Error loading jobs:', err);
      if (err.response) {
        console.error('Response error:', err.response.data);
      }
      setJobs([]);
    } finally {
      setLoading(false);
    }
  }, [includeCompleted]);

  useEffect(() => {
    loadJobs();
    // Refresh every 2 seconds
    const interval = setInterval(loadJobs, 2000);
    return () => clearInterval(interval);
  }, [loadJobs]);

  // Connect WebSocket for each active job
  useEffect(() => {
    const activeJobs = jobs.filter(job => 
      job.stage && !['complete', 'error', 'cancelled'].includes(job.stage)
    );

    const currentWs = websocketsRef.current;

    // Close old WebSocket connections
    Object.keys(currentWs).forEach(jobId => {
      if (!activeJobs.find(j => j.jobId === jobId)) {
        const ws = currentWs[jobId];
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
        delete currentWs[jobId];
      }
    });

    // Create new WebSocket connections
    activeJobs.forEach(job => {
      if (!currentWs[job.jobId]) {
        try {
          // Convert HTTP/HTTPS URL to WebSocket URL
          const wsProtocol = API_BASE_URL.startsWith('https') ? 'wss' : 'ws';
          const wsUrl = `${wsProtocol}://${API_BASE_URL.replace(/^https?:\/\//, '')}/ws/${job.jobId}`;
          const ws = new WebSocket(wsUrl);
          
          ws.onopen = () => {
            console.log(`WebSocket connected for job ${job.jobId}`);
          };

          ws.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data);
              setJobs(prevJobs => 
                prevJobs.map(j => 
                  j.jobId === job.jobId 
                    ? { ...j, ...data, stage: data.stage || j.stage }
                    : j
                )
              );
            } catch (e) {
              console.error('Error parsing WebSocket message:', e);
            }
          };

          ws.onerror = (error) => {
            console.error(`WebSocket error for job ${job.jobId}:`, error);
          };

          ws.onclose = () => {
            console.log(`WebSocket closed for job ${job.jobId}`);
            delete currentWs[job.jobId];
          };

          currentWs[job.jobId] = ws;
        } catch (error) {
          console.error(`Failed to create WebSocket for job ${job.jobId}:`, error);
        }
      }
    });

    return () => {
      // Cleanup WebSocket connections on unmount
      Object.values(currentWs).forEach(ws => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      });
      websocketsRef.current = {};
    };
  }, [jobs]);

  const getStageLabel = (stage) => {
    const labels = {
      'pending': 'در انتظار',
      'download': 'در حال دانلود',
      'upload': 'در حال آپلود',
      'split': 'در حال تقسیم',
      'storyboard': 'در حال تولید استوری‌بورد',
      'complete': 'تکمیل شده',
      'error': 'خطا',
      'cancelled': 'لغو شده'
    };
    return labels[stage] || stage;
  };

  const getStageColor = (stage) => {
    const colors = {
      'pending': '#888',
      'download': '#2196F3',
      'upload': '#4CAF50',
      'split': '#FF9800',
      'storyboard': '#9C27B0',
      'complete': '#4CAF50',
      'error': '#F44336',
      'cancelled': '#888'
    };
    return colors[stage] || '#888';
  };

  const handleCancel = async (jobId) => {
    if (!window.confirm('آیا مطمئن هستید که می‌خواهید این کار را لغو کنید؟')) {
      return;
    }
    try {
      await axios.post(`${API_BASE_URL}/api/job/${jobId}/cancel`);
      loadJobs();
      if (onCancelJob) {
        onCancelJob(jobId);
      }
    } catch (err) {
      console.error('Error cancelling job:', err);
      alert('خطا در لغو کار: ' + (err.response?.data?.detail || err.message));
    }
  };

  if (loading && jobs.length === 0) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p>در حال بارگذاری کارها...</p>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p>هیچ کاری در حال انجام نیست</p>
        <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', marginTop: '20px' }}>
          <input
            type="checkbox"
            checked={includeCompleted}
            onChange={(e) => setIncludeCompleted(e.target.checked)}
          />
          <span>نمایش کارهای تکمیل شده</span>
        </label>
      </div>
    );
  }

  const activeJobs = jobs.filter(j => !['complete', 'error', 'cancelled'].includes(j.stage));
  const completedJobs = jobs.filter(j => ['complete', 'error', 'cancelled'].includes(j.stage));

  return (
    <div style={{ padding: '20px' }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '20px',
        flexWrap: 'wrap',
        gap: '10px'
      }}>
        <h2 style={{ margin: 0 }}>کارهای فعال ({activeJobs.length})</h2>
        <label style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <input
            type="checkbox"
            checked={includeCompleted}
            onChange={(e) => setIncludeCompleted(e.target.checked)}
          />
          <span>نمایش کارهای تکمیل شده ({completedJobs.length})</span>
        </label>
      </div>

      {activeJobs.length > 0 && (
        <div style={{ marginBottom: '30px' }}>
          <h3 style={{ marginBottom: '15px', color: '#2196F3' }}>در حال انجام</h3>
          <div style={{ display: 'grid', gap: '15px' }}>
            {activeJobs.map(job => (
              <div
                key={job.jobId}
                style={{
                  border: '1px solid #ddd',
                  borderRadius: '8px',
                  padding: '15px',
                  backgroundColor: '#fff',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                      <span
                        style={{
                          padding: '4px 12px',
                          borderRadius: '12px',
                          backgroundColor: getStageColor(job.stage) + '20',
                          color: getStageColor(job.stage),
                          fontSize: '12px',
                          fontWeight: 'bold'
                        }}
                      >
                        {getStageLabel(job.stage)}
                      </span>
                      <span style={{ fontSize: '12px', color: '#888' }}>
                        {job.jobId.substring(0, 8)}...
                      </span>
                    </div>
                    {job.metadata?.title && (
                      <div style={{ marginBottom: '8px', fontWeight: 'bold' }}>
                        {job.metadata.title}
                      </div>
                    )}
                    {job.url && (
                      <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px', wordBreak: 'break-all' }}>
                        {job.url}
                      </div>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    {job.stage && !['complete', 'error', 'cancelled'].includes(job.stage) && (
                      <button
                        onClick={() => handleCancel(job.jobId)}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#F44336',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '12px'
                        }}
                      >
                        لغو
                      </button>
                    )}
                    {job.s3_url && (
                      <button
                        onClick={() => onJobClick && onJobClick(job)}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#2196F3',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '12px'
                        }}
                      >
                        مشاهده
                      </button>
                    )}
                  </div>
                </div>
                <StatusDisplay
                  status={{
                    stage: job.stage,
                    percent: job.percent || 0,
                    message: job.message || '',
                    speed: job.speed,
                    eta: job.eta
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {includeCompleted && completedJobs.length > 0 && (
        <div>
          <h3 style={{ marginBottom: '15px', color: '#888' }}>تکمیل شده / خطا / لغو شده</h3>
          <div style={{ display: 'grid', gap: '15px' }}>
            {completedJobs.map(job => (
              <div
                key={job.jobId}
                style={{
                  border: '1px solid #ddd',
                  borderRadius: '8px',
                  padding: '15px',
                  backgroundColor: '#f9f9f9',
                  opacity: 0.8
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                      <span
                        style={{
                          padding: '4px 12px',
                          borderRadius: '12px',
                          backgroundColor: getStageColor(job.stage) + '20',
                          color: getStageColor(job.stage),
                          fontSize: '12px',
                          fontWeight: 'bold'
                        }}
                      >
                        {getStageLabel(job.stage)}
                      </span>
                      <span style={{ fontSize: '12px', color: '#888' }}>
                        {job.jobId.substring(0, 8)}...
                      </span>
                    </div>
                    {job.metadata?.title && (
                      <div style={{ marginBottom: '8px', fontWeight: 'bold' }}>
                        {job.metadata.title}
                      </div>
                    )}
                    {job.url && (
                      <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px', wordBreak: 'break-all' }}>
                        {job.url}
                      </div>
                    )}
                    {job.message && (
                      <div style={{ fontSize: '12px', color: '#666' }}>
                        {job.message}
                      </div>
                    )}
                  </div>
                  {job.s3_url && (
                    <button
                      onClick={() => onJobClick && onJobClick(job)}
                      style={{
                        padding: '6px 12px',
                        backgroundColor: '#2196F3',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '12px'
                      }}
                    >
                      مشاهده
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ActiveJobsList;

