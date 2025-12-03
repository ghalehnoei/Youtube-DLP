import { useRef, useEffect } from 'react';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const useWebSocket = (jobId, onMessage, onError) => {
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  useEffect(() => {
    if (!jobId) return;

    const connectWebSocket = (jobId) => {
      if (wsRef.current) {
        wsRef.current.close();
      }

      const wsUrl = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
      const ws = new WebSocket(`${wsUrl}/ws/${jobId}`);
      
      ws.onopen = () => {
        if (onError) onError(null);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (onMessage) onMessage(data);
        } catch (e) {
          console.error('Error parsing WebSocket message:', e);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (onError) onError('Connection error. Please refresh and try again.');
      };

      ws.onclose = () => {
        // Only reconnect if job is still in progress
        // This will be handled by the parent component checking status
        reconnectTimeoutRef.current = setTimeout(() => {
          if (jobId) {
            connectWebSocket(jobId);
          }
        }, 2000);
      };

      wsRef.current = ws;
    };

    connectWebSocket(jobId);

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [jobId, onMessage, onError]);

  return { wsRef, reconnectTimeoutRef };
};

