import { useState, useEffect, useRef } from 'react';
import type { WSEvent, Message, TimelineEntry } from '@/types/message';

const WS_URL = 'ws://127.0.0.1:18080';

export function useWebSocket(sessionId: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentResponse, setCurrentResponse] = useState('');
  const [status, setStatus] = useState('');
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const sessionIdRef = useRef<string>(sessionId);
  const isConnectingRef = useRef(false);
  const timelineRef = useRef<TimelineEntry[]>([]);

  // sessionId 变化时重连
  useEffect(() => {
    // 如果 sessionId 没变化，跳过
    if (sessionIdRef.current === sessionId && wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    sessionIdRef.current = sessionId;

    // 清理旧连接
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // 重置状态
    setIsConnected(false);
    setMessages([]);
    setCurrentResponse('');
    setTimeline([]);
    timelineRef.current = [];
    setStatus('');
    setError(null);
    isConnectingRef.current = false;

    // 建立新连接
    const connect = () => {
      if (isConnectingRef.current) return;
      isConnectingRef.current = true;

      const ws = new WebSocket(`${WS_URL}/ws/chat/${sessionId}`);

      ws.onopen = () => {
        isConnectingRef.current = false;
        setIsConnected(true);
        setError(null);
      };

      ws.onclose = () => {
        isConnectingRef.current = false;
        setIsConnected(false);
        // 只在 sessionId 未变化时重连（断线重连）
        if (sessionIdRef.current === sessionId) {
          reconnectTimeoutRef.current = window.setTimeout(() => {
            if (sessionIdRef.current === sessionId && !wsRef.current) {
              connect();
            }
          }, 3000);
        }
      };

      ws.onerror = () => {
        isConnectingRef.current = false;
        setError('连接失败');
      };

      ws.onmessage = (event) => {
        const data: WSEvent = JSON.parse(event.data);
        handleEvent(data);
      };

      wsRef.current = ws;
    };

    connect();

    // 清理函数
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [sessionId]);

  const appendTimeline = (entry: TimelineEntry) => {
    const next = [...timelineRef.current, entry];
    timelineRef.current = next;
    setTimeline(next);
  };

  const updateTimelineTool = (toolCallId: string, result: string) => {
    const next = timelineRef.current.map(e =>
      e.type === 'tool' && e.id === toolCallId ? { ...e, result } : e
    );
    timelineRef.current = next;
    setTimeline(next);
  };

  const handleEvent = (event: WSEvent) => {
    switch (event.type) {
      case 'connected':
        setIsConnected(true);
        break;

      case 'start':
        setCurrentResponse('');
        setTimeline([]);
        timelineRef.current = [];
        setStatus('');
        // 保持 isLoading=true，直到收到实际内容
        break;

      case 'text_delta':
        setCurrentResponse(prev => prev + (event.content || ''));
        break;

      case 'tool_start':
        appendTimeline({
          type: 'tool',
          id: event.tool_call_id || event.name || '',
          name: event.name || '',
          args: event.args || {},
        });
        break;

      case 'tool_complete':
        updateTimelineTool(event.tool_call_id || '', event.result || '');
        break;

      case 'status':
        setStatus(event.message || '');
        break;

      case 'debug_log':
        appendTimeline({
          type: 'log',
          message: event.message || '',
          source: event.source || 'agent',
        });
        break;

      case 'complete':
        setIsLoading(false);
        if (event.response) {
          // 使用 ref 获取最新的时间线，保存到历史消息
          const currentTimeline = timelineRef.current;
          setMessages(prev => [...prev, {
            role: 'assistant' as const,
            content: event.response || '',
            timestamp: Date.now(),
            timeline: currentTimeline.length > 0 ? currentTimeline : undefined,
          }]);
        }
        // 清空中间状态（已保存到消息中）
        setCurrentResponse('');
        setTimeline([]);
        timelineRef.current = [];
        setStatus('');
        break;

      case 'error':
        setIsLoading(false);
        setError(event.message || 'Unknown error');
        break;

      case 'history':
        if (event.messages) {
          setMessages(event.messages);
        }
        break;

      case 'cleared':
        setMessages([]);
        setTimeline([]);
        timelineRef.current = [];
        break;
    }
  };

  const sendMessage = (content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('WebSocket not connected');
      return;
    }

    setMessages(prev => [...prev, {
      role: 'user',
      content,
      timestamp: Date.now()
    }]);

    setIsLoading(true);
    setCurrentResponse('');
    setTimeline([]);
    timelineRef.current = [];

    wsRef.current.send(JSON.stringify({
      type: 'message',
      content
    }));
  };

  const clearHistory = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: 'clear' }));
    setMessages([]);
    setTimeline([]);
    timelineRef.current = [];
  };

  return {
    isConnected,
    messages,
    currentResponse,
    status,
    timeline,
    error,
    isLoading,
    sendMessage,
    clearHistory
  };
}
