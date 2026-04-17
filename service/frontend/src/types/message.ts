// WebSocket 事件类型
export type WSEventType =
  | 'connected'
  | 'start'
  | 'text_delta'
  | 'tool_start'
  | 'tool_complete'
  | 'status'
  | 'complete'
  | 'error'
  | 'cleared'
  | 'history';

// WebSocket 事件
export interface WSEvent {
  type: WSEventType;
  session_id: string;
  content?: string;
  message?: string;
  response?: string;
  name?: string;
  args?: Record<string, unknown>;
  result?: string;
  tool_call_id?: string;
  messages?: Message[];
  source?: string;  // 日志来源：agent | guard
}

// 调试日志条目
export interface DebugLogEntry {
  message: string;
  source?: string;  // agent | guard
}

// 消息类型
export interface Message {
  id?: number;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  timestamp?: number;
  tool_name?: string;
  tool_calls?: ToolCall[];
  debug_logs?: DebugLogEntry[];  // 执行过程日志，带来源标识
}

// 工具调用
export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: string;
}

// 会话类型
export interface Session {
  id: string;
  source: string;
  user_id?: string;
  model?: string;
  title?: string;
  started_at: number;
  ended_at?: number;
  message_count: number;
}