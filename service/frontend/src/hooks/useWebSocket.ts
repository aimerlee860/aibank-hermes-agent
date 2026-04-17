import { useState, useEffect, useRef } from 'react';
import type { WSEvent, Message, DebugLogEntry } from '@/types/message';

const WS_URL = 'ws://127.0.0.1:18080';

export function useWebSocket(sessionId: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentResponse, setCurrentResponse] = useState('');
  const [status, setStatus] = useState('');
  const [toolCalls, setToolCalls] = useState<{ id: string; name: string; args: Record<string, unknown>; result?: string }[]>([]);
  const [debugLogs, setDebugLogs] = useState<DebugLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const sessionIdRef = useRef<string>(sessionId);
  const isConnectingRef = useRef(false);
  const toolCallsRef = useRef<{ id: string; name: string; args: Record<string, unknown>; result?: string }[]>([]);
  const debugLogsRef = useRef<DebugLogEntry[]>([]);

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
    setToolCalls([]);
    toolCallsRef.current = [];
    setDebugLogs([]);
    debugLogsRef.current = [];
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

  const handleEvent = (event: WSEvent) => {
    switch (event.type) {
      case 'connected':
        setIsConnected(true);
        break;

      case 'start':
        setCurrentResponse('');
        setToolCalls([]);
        toolCallsRef.current = [];
        setStatus('');
        setDebugLogs([]);
        debugLogsRef.current = [];
        break;

      case 'text_delta':
        setCurrentResponse(prev => prev + (event.content || ''));
        break;

      case 'tool_start':
        const newToolCall = {
          id: event.tool_call_id || event.name || '',
          name: event.name || '',
          args: event.args || {}
        };
        setToolCalls(prev => [...prev, newToolCall]);
        toolCallsRef.current = [...toolCallsRef.current, newToolCall];
        break;

      case 'tool_complete':
        setToolCalls(prev => prev.map(tc =>
          tc.id === event.tool_call_id ? { ...tc, result: event.result } : tc
        ));
        toolCallsRef.current = toolCallsRef.current.map(tc =>
          tc.id === event.tool_call_id ? { ...tc, result: event.result } : tc
        );
        break;

      case 'status':
        setStatus(event.message || '');
        break;

      case 'debug_log':
        // 添加调试日志（带来源标识）
        const newLog: DebugLogEntry = {
          message: event.message || '',
          source: event.source || 'agent'
        };
        setDebugLogs(prev => [...prev, newLog]);
        debugLogsRef.current = [...debugLogsRef.current, newLog];
        break;

      case 'complete':
        if (event.response) {
          // 使用 ref 获取最新的工具调用和日志信息，保存到历史消息
          const currentToolCalls = toolCallsRef.current;
          const currentDebugLogs = debugLogsRef.current;
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: event.response,
            timestamp: Date.now(),
            tool_calls: currentToolCalls.length > 0 ? currentToolCalls : undefined,
            debug_logs: currentDebugLogs.length > 0 ? currentDebugLogs : undefined
          }]);
        }
        // 清空中间状态（已保存到消息中）
        setCurrentResponse('');
        setToolCalls([]);
        toolCallsRef.current = [];
        setDebugLogs([]);
        debugLogsRef.current = [];
        setStatus('');
        break;

      case 'error':
        setError(event.message || 'Unknown error');
        break;

      case 'history':
        if (event.messages) {
          setMessages(event.messages);
        }
        break;

      case 'cleared':
        setMessages([]);
        setToolCalls([]);
        toolCallsRef.current = [];
        setDebugLogs([]);
        debugLogsRef.current = [];
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

    wsRef.current.send(JSON.stringify({
      type: 'message',
      content
    }));
  };

  const clearHistory = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: 'clear' }));
    setMessages([]);
    setToolCalls([]);
    toolCallsRef.current = [];
    setDebugLogs([]);
    debugLogsRef.current = [];
  };

  return {
    isConnected,
    messages,
    currentResponse,
    status,
    toolCalls,
    debugLogs,
    error,
    sendMessage,
    clearHistory
  };
}