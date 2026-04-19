import { clsx } from 'clsx';
import { Menu, X, Plus, Trash2 } from 'lucide-react';
import type { Session } from '@/types/message';

interface SidebarProps {
  sessions: Session[];
  currentSessionId: string;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export function Sidebar({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  isOpen,
  onToggle
}: SidebarProps) {
  return (
    <>
      {/* Toggle button for mobile */}
      <button
        onClick={onToggle}
        className="fixed top-3 left-3 z-50 p-1.5 rounded-lg bg-[var(--hermes-bg)] border border-[var(--hermes-border)] text-[var(--hermes-amber)] shadow-lg md:hidden"
      >
        {isOpen ? <X size={18} /> : <Menu size={18} />}
      </button>

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed left-0 top-0 h-full w-56 bg-[var(--hermes-bg-dark)] border-r border-[var(--hermes-border)] z-40 overflow-hidden',
          'transition-transform duration-300 flex flex-col',
          isOpen ? 'translate-x-0' : '-translate-x-full',
          'md:translate-x-0 md:relative md:shrink-0'
        )}
      >
        {/* Header */}
        <div className="shrink-0 p-3 border-b border-[var(--hermes-border)]">
          <h1 className="text-base font-semibold text-[var(--hermes-title)]">⚕ Hermes</h1>
          <button
            onClick={onNewSession}
            className="mt-2 w-full flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg bg-[var(--hermes-amber)] hover:bg-[var(--hermes-gold)] text-[var(--hermes-bg-dark)] text-sm transition-colors"
          >
            <Plus size={14} />
            新会话
          </button>
        </div>

        {/* Session list - 可滚动 */}
        <div className="flex-1 min-h-0 overflow-y-auto p-2">
          {sessions.length === 0 ? (
            <div className="text-center text-[var(--hermes-dim)] py-6 text-sm opacity-60">
              暂无会话
            </div>
          ) : (
            <ul className="space-y-1">
              {sessions.map((session) => (
                <li
                  key={session.id}
                  className={clsx(
                    'group flex items-center rounded-lg p-1.5 cursor-pointer transition-colors',
                    session.id === currentSessionId
                      ? 'bg-[var(--hermes-border)] text-[var(--hermes-text)]'
                      : 'text-[var(--hermes-dim)] hover:bg-[var(--hermes-bg)] hover:text-[var(--hermes-text)]'
                  )}
                  onClick={() => onSelectSession(session.id)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="truncate text-sm">
                      {session.title || `会话 ${session.id.slice(0, 6)}`}
                    </div>
                    <div className="text-xs opacity-60">
                      {session.message_count} 条
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(session.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition-opacity"
                  >
                    <Trash2 size={12} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Footer */}
        <div className="shrink-0 p-2 border-t border-[var(--hermes-border)]">
          <div className="text-xs text-[var(--hermes-dim)] opacity-50">
            Hermes Agent
          </div>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={onToggle}
        />
      )}
    </>
  );
}