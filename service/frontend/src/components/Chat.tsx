import { useState, useEffect, useCallback } from 'react';
import { clsx } from 'clsx';
import { AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { MessageList } from './MessageList';
import { InputBox } from './InputBox';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { Session } from '@/types/message';

// 生成随机 session ID
function generateSessionId(): string {
  return `web-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function Chat() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState(() => generateSessionId());
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const {
    isConnected,
    messages,
    currentResponse,
    status,
    toolCalls,
    debugLogs,
    error,
    sendMessage,
    clearHistory
  } = useWebSocket(currentSessionId);

  // 加载会话列表
  useEffect(() => {
    fetch('/api/sessions?limit=20')
      .then(res => res.json())
      .then(data => setSessions(data.sessions || []))
      .catch(console.error);
  }, []);

  const handleNewSession = useCallback(() => {
    const newId = generateSessionId();
    setCurrentSessionId(newId);
    setSidebarOpen(false);
  }, []);

  const handleSelectSession = useCallback((id: string) => {
    setCurrentSessionId(id);
    setSidebarOpen(false);
  }, []);

  const handleDeleteSession = useCallback((id: string) => {
    // 调用 API 删除会话
    fetch(`/api/sessions/${id}`, { method: 'DELETE' })
      .catch(console.error);
    setSessions(prev => prev.filter(s => s.id !== id));
    if (id === currentSessionId) {
      handleNewSession();
    }
  }, [currentSessionId, handleNewSession]);

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--hermes-bg-dark)]">
      {/* Sidebar */}
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
        onDeleteSession={handleDeleteSession}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* Main chat area */}
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Header */}
        <header className="shrink-0 p-3 border-b border-[var(--hermes-border)] bg-[var(--hermes-bg-dark)] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-medium text-[var(--hermes-text)]">
              {currentSessionId.slice(0, 8)}
            </h2>
            <div className={clsx(
              'flex items-center gap-1 text-xs',
              isConnected ? 'text-green-400' : 'text-red-400'
            )}>
              {isConnected ? (
                <CheckCircle size={12} />
              ) : (
                <AlertCircle size={12} />
              )}
              {isConnected ? '已连接' : '未连接'}
            </div>
          </div>

          <button
            onClick={clearHistory}
            className="text-xs text-[var(--hermes-dim)] hover:text-[var(--hermes-text)] transition-colors"
          >
            清空
          </button>
        </header>

        {/* Status bar */}
        {(status || error) && (
          <div className={clsx(
            'shrink-0 px-3 py-1.5 text-xs',
            error ? 'bg-red-900/50 text-red-200' : 'bg-[var(--hermes-bg)] text-[var(--hermes-dim)]'
          )}>
            {error || status}
            {status && <Loader2 size={12} className="inline ml-1 animate-spin" />}
          </div>
        )}

        {/* Messages - 滚动区域 */}
        <MessageList
          messages={messages}
          currentResponse={currentResponse}
          toolCalls={toolCalls}
          debugLogs={debugLogs}
        />

        {/* Input - 固定底部 */}
        <div className="shrink-0">
          <InputBox
            onSend={sendMessage}
            disabled={!isConnected}
            placeholder={!isConnected ? '等待连接...' : '输入消息...'}
          />
        </div>
      </main>
    </div>
  );
}