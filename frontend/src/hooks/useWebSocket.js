import { useRef, useEffect } from 'react';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const useWebSocket = (jobId, onMessage, onError) => {
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const shouldReconnectRef = useRef(true);
  const isConnectingRef = useRef(false);
  const currentJobIdRef = useRef(null);
  const onMessageRef = useRef(onMessage);
  const onErrorRef = useRef(onError);

  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage;
    onErrorRef.current = onError;
  }, [onMessage, onError]);

  useEffect(() => {
    // Update current job ID
    currentJobIdRef.current = jobId;

    if (!jobId) {
      // Close connection if jobId is cleared
      shouldReconnectRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        const ws = wsRef.current;
        wsRef.current = null;
        if (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      }
      return;
    }

    // Don't connect if already connecting or connected for this job
    if (isConnectingRef.current || (wsRef.current && wsRef.current.readyState === WebSocket.OPEN)) {
      return;
    }

    shouldReconnectRef.current = true;
    isConnectingRef.current = true;

    const connectWebSocket = () => {
      // Check if jobId has changed
      if (currentJobIdRef.current !== jobId) {
        isConnectingRef.current = false;
        return;
      }

      // Clear any pending reconnection
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      // Close existing connection if any (but not if it's the same job and open)
      if (wsRef.current) {
        const oldWs = wsRef.current;
        if (oldWs.readyState === WebSocket.CONNECTING || oldWs.readyState === WebSocket.OPEN) {
          shouldReconnectRef.current = false;
          oldWs.close();
        }
        wsRef.current = null;
      }

      try {
        const wsUrl = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
        const ws = new WebSocket(`${wsUrl}/ws/${jobId}`);
        
        ws.onopen = () => {
          isConnectingRef.current = false;
          console.log('WebSocket connected for job:', jobId);
          if (onErrorRef.current) onErrorRef.current(null);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (onMessageRef.current) {
              onMessageRef.current(data);
            }
            // If job is complete, don't reconnect
            if (data.stage === 'complete' || data.stage === 'error' || data.stage === 'cancelled') {
              shouldReconnectRef.current = false;
            }
          } catch (e) {
            console.error('Error parsing WebSocket message:', e);
          }
        };

        ws.onerror = (error) => {
          // Only log errors, don't show user-facing errors during connection
          // The onclose handler will handle reconnection
          if (ws.readyState === WebSocket.OPEN) {
            console.error('WebSocket error after connection:', error);
            if (onErrorRef.current) {
              onErrorRef.current('Connection error occurred.');
            }
          }
        };

        ws.onclose = (event) => {
          isConnectingRef.current = false;
          wsRef.current = null;
          
          // Only reconnect if we should, jobId matches, and it wasn't a normal closure
          if (shouldReconnectRef.current && currentJobIdRef.current === jobId && event.code !== 1000) {
            reconnectTimeoutRef.current = setTimeout(() => {
              if (shouldReconnectRef.current && currentJobIdRef.current === jobId && !isConnectingRef.current) {
                connectWebSocket();
              }
            }, 2000);
          }
        };

        wsRef.current = ws;
      } catch (error) {
        isConnectingRef.current = false;
        console.error('Error creating WebSocket:', error);
        if (onErrorRef.current) {
          onErrorRef.current('Failed to establish connection. Please try again.');
        }
      }
    };

    connectWebSocket();

    // Cleanup on unmount or jobId change
    return () => {
      shouldReconnectRef.current = false;
      isConnectingRef.current = false;
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      
      if (wsRef.current) {
        const ws = wsRef.current;
        wsRef.current = null;
        // Only close if not already closed
        if (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      }
    };
  }, [jobId]); // Only depend on jobId, not callbacks

  return { wsRef, reconnectTimeoutRef };
};

