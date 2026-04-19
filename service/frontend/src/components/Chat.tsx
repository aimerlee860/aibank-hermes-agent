import { useState, useEffect, useCallback, useMemo } from 'react';
import { clsx } from 'clsx';
import { AlertCircle, CheckCircle, Loader2, Eye, EyeOff } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { MessageList } from './MessageList';
import { InputBox } from './InputBox';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { Session } from '@/types/message';

function generateSessionId(): string {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  const arr = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(arr, b => chars[b % chars.length]).join('');
}

export function Chat() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState(() => generateSessionId());
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showLogs, setShowLogs] = useState(false);

  const sessionLabel = useMemo(
    () => sessions.find(s => s.id === currentSessionId)?.title || currentSessionId,
    [sessions, currentSessionId]
  );

  const {
    isConnected,
    messages,
    currentResponse,
    status,
    timeline,
    error,
    isLoading,
    sendMessage,
    clearHistory
  } = useWebSocket(currentSessionId);

  // 加载会话列表
  const refreshSessions = useCallback(() => {
    fetch('/api/sessions?limit=20')
      .then(res => res.json())
      .then(data => setSessions(data.sessions || []))
      .catch(console.error);
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  // 当收到 assistant 回复时刷新侧边栏（更新消息数）
  const lastAssistantMsgCount = messages.filter(m => m.role === 'assistant').length;
  useEffect(() => {
    if (lastAssistantMsgCount > 0) {
      refreshSessions();
    }
  }, [lastAssistantMsgCount, refreshSessions]);

  const handleNewSession = useCallback(() => {
    const newId = generateSessionId();
    setCurrentSessionId(newId);
    setSidebarOpen(false);
    // 延迟刷新侧边栏，等待后端保存上一个会话
    setTimeout(refreshSessions, 500);
  }, [refreshSessions]);

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
        <header className="shrink-0 px-3 py-2 border-b border-[var(--hermes-border)] bg-[var(--hermes-bg-dark)] flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <h2 className="text-sm font-medium text-[var(--hermes-text)] truncate max-w-[200px]" title={sessionLabel}>
              {sessionLabel}
            </h2>
            <div className={clsx(
              'flex items-center gap-1 text-xs shrink-0',
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

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => setShowLogs(!showLogs)}
              className={clsx(
                'flex items-center gap-1 text-xs transition-colors',
                showLogs ? 'text-[var(--hermes-amber)]' : 'text-[var(--hermes-dim)] hover:text-[var(--hermes-text)]'
              )}
              title={showLogs ? '隐藏日志' : '显示日志'}
            >
              {showLogs ? <Eye size={14} /> : <EyeOff size={14} />}
              日志
            </button>
            <button
              onClick={clearHistory}
              className="text-xs text-[var(--hermes-dim)] hover:text-[var(--hermes-text)] transition-colors"
            >
              清空
            </button>
          </div>
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
          timeline={timeline}
          isLoading={isLoading}
          showLogs={showLogs}
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