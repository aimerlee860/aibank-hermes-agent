import { clsx } from 'clsx';
import { Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message, TimelineEntry, DebugLogEntry, ToolCall } from '@/types/message';

interface MessageListProps {
  messages: Message[];
  currentResponse: string;
  timeline: TimelineEntry[];
  isLoading: boolean;
  showLogs: boolean;
}

export function MessageList({ messages, currentResponse, timeline, isLoading, showLogs }: MessageListProps) {
  return (
    <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-3">
      {messages.map((msg, idx) => (
        <MessageItem key={idx} message={msg} showLogs={showLogs} />
      ))}

      {/* 当前响应区域：统一一个头像 */}
      {isLoading && (
        <div className="flex gap-2">
          <div className="w-6 h-6 rounded-full bg-[var(--hermes-amber)] flex items-center justify-center text-[var(--hermes-bg-dark)] text-xs font-bold shrink-0">
            ⚕
          </div>
          <div className="flex-1 space-y-1">
            {/* 统一时间线：日志和工具调用按顺序交替 */}
            {showLogs && timeline.length > 0 && (
              <div className="bg-[var(--hermes-bg)] border border-[var(--hermes-border)] rounded-lg p-2 opacity-70">
                {timeline.map((entry, idx) => (
                  <TimelineEntryDisplay key={idx} entry={entry} />
                ))}
              </div>
            )}

            {/* 流式响应 */}
            {currentResponse && (
              <div className="bg-[var(--hermes-bg)] border border-[var(--hermes-border)] rounded-lg p-3">
                <MarkdownContent content={currentResponse} />
              </div>
            )}

            {/* 加载/处理中指示器 */}
            <div className="flex items-center gap-2 text-xs text-[var(--hermes-dim)] pt-1">
              <Loader2 size={12} className="animate-spin text-[var(--hermes-amber)]" />
              <span>{currentResponse || timeline.length > 0 ? '正在处理...' : '正在思考...'}</span>
            </div>
          </div>
        </div>
      )}

      {/* 无加载状态但仍有残留内容 */}
      {!isLoading && (showLogs && timeline.length > 0 || currentResponse) && (
        <div className="flex gap-2">
          <div className="w-6 h-6 rounded-full bg-[var(--hermes-amber)] flex items-center justify-center text-[var(--hermes-bg-dark)] text-xs font-bold shrink-0">
            ⚕
          </div>
          <div className="flex-1 space-y-1">
            {showLogs && timeline.length > 0 && (
              <div className="bg-[var(--hermes-bg)] border border-[var(--hermes-border)] rounded-lg p-2 opacity-70">
                {timeline.map((entry, idx) => (
                  <TimelineEntryDisplay key={idx} entry={entry} />
                ))}
              </div>
            )}
            {currentResponse && (
              <div className="bg-[var(--hermes-bg)] border border-[var(--hermes-border)] rounded-lg p-3">
                <MarkdownContent content={currentResponse} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** 统一时间线条目渲染 */
function TimelineEntryDisplay({ entry }: { entry: TimelineEntry }) {
  if (entry.type === 'log') {
    const isGuard = entry.source === 'guard';
    return (
      <div className={clsx(
        'text-xs font-mono whitespace-pre-wrap mb-1',
        isGuard ? 'text-purple-400' : 'text-[var(--hermes-dim)]'
      )}>
        {isGuard && <span className="mr-1">🛡️</span>}
        {entry.message}
      </div>
    );
  }

  // tool
  return (
    <div className="text-xs font-mono mb-1">
      <div className="flex items-center gap-1.5">
        <span>🔧</span>
        <span className="text-[var(--hermes-amber)] font-semibold">{entry.name}</span>
        {entry.result ? (
          <span className="text-green-400">✓</span>
        ) : (
          <span className="animate-pulse">⏳</span>
        )}
      </div>
      {/* 参数 */}
      {entry.args && Object.keys(entry.args).length > 0 && (
        <div className="ml-4 mt-0.5 text-[var(--hermes-dim)]">
          {Object.entries(entry.args).map(([key, value]) => (
            <div key={key}>
              <span className="text-[var(--hermes-text)]">{key}</span>
              <span className="text-[var(--hermes-dim)]">: </span>
              <span className="text-blue-300">{formatValue(value)}</span>
            </div>
          ))}
        </div>
      )}
      {/* 结果 */}
      {entry.result && (
        <div className="ml-4 mt-0.5 text-green-400 whitespace-pre-wrap">
          → {entry.result}
        </div>
      )}
    </div>
  );
}

/** 兼容旧的历史消息（debug_logs + tool_calls 分开存储） */
function LegacyTimeline({ logs, toolCalls }: { logs?: DebugLogEntry[]; toolCalls?: ToolCall[] }) {
  return (
    <>
      {logs?.map((log, idx) => {
        const isGuard = log.source === 'guard';
        return (
          <div key={`log-${idx}`} className={clsx(
            'text-xs font-mono whitespace-pre-wrap mb-1',
            isGuard ? 'text-purple-400' : 'text-[var(--hermes-dim)]'
          )}>
            {isGuard && <span className="mr-1">🛡️</span>}
            {log.message}
          </div>
        );
      })}
      {toolCalls?.map((tc, idx) => (
        <TimelineEntryDisplay key={`tool-${idx}`} entry={{ type: 'tool', ...tc }} />
      ))}
    </>
  );
}

function formatValue(value: unknown): string {
  if (typeof value === 'string') {
    return `"${value}"`;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  if (value === null) {
    return 'null';
  }
  if (Array.isArray(value)) {
    return JSON.stringify(value);
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

function MessageItem({ message, showLogs }: { message: Message; showLogs: boolean }) {
  const isUser = message.role === 'user';
  const isTool = message.role === 'tool';

  // 统一时间线内容：优先使用 timeline，否则回退到旧的 debug_logs + tool_calls
  const hasTimeline = (message.timeline?.length ?? 0) > 0;
  const hasLegacy = (message.debug_logs?.length ?? 0) > 0 || (message.tool_calls?.length ?? 0) > 0;
  const showProcess = showLogs && (hasTimeline || hasLegacy);

  return (
    <div className={clsx('flex gap-2', isUser && 'justify-end')}>
      {!isUser && (
        <div className={clsx(
          'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0',
          isTool ? 'bg-[var(--hermes-dim)] text-[var(--hermes-text)]' : 'bg-[var(--hermes-amber)] text-[var(--hermes-bg-dark)]'
        )}>
          {isTool ? '🔧' : '⚕'}
        </div>
      )}

      <div className={clsx(
        'max-w-[80%] space-y-1',
      )}>
        {/* 执行过程：统一时间线 */}
        {showProcess && (
          <div className="bg-[var(--hermes-bg)] border border-[var(--hermes-border)] rounded-lg p-2 opacity-70">
            {hasTimeline ? (
              message.timeline!.map((entry, idx) => (
                <TimelineEntryDisplay key={idx} entry={entry} />
              ))
            ) : (
              <LegacyTimeline logs={message.debug_logs} toolCalls={message.tool_calls} />
            )}
          </div>
        )}

        {/* 消息内容 */}
        <div className={clsx(
          'rounded-lg p-3 text-sm',
          isUser ? 'bg-[var(--hermes-border)] text-[var(--hermes-text)]' : 'bg-[var(--hermes-bg)] border border-[var(--hermes-border)] text-[var(--hermes-text)]'
        )}>
          {isUser ? (
            <div className="whitespace-pre-wrap leading-relaxed break-words">
              {message.content}
            </div>
          ) : (
            <MarkdownContent content={message.content} />
          )}
          {message.timestamp && (
            <div className="text-xs text-[var(--hermes-dim)] mt-1 opacity-60">
              {new Date(message.timestamp).toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>

      {isUser && (
        <div className="w-6 h-6 rounded-full bg-[var(--hermes-dim)] flex items-center justify-center text-[var(--hermes-text)] text-xs shrink-0">
          你
        </div>
      )}
    </div>
  );
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="text-[var(--hermes-text)]">
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      className="markdown-content"
      components={{
        // 标题
        h1: ({ children }) => (
          <h1 className="text-lg font-bold text-[var(--hermes-title)] mb-2 mt-1">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-base font-semibold text-[var(--hermes-title)] mb-1.5 mt-1">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-sm font-semibold text-[var(--hermes-text)] mb-1 mt-0.5">{children}</h3>
        ),
        // 粗体
        strong: ({ children }) => (
          <strong className="font-semibold text-[var(--hermes-title)]">{children}</strong>
        ),
        // 斜体
        em: ({ children }) => (
          <em className="italic text-[var(--hermes-dim)]">{children}</em>
        ),
        // 列表
        ul: ({ children }) => (
          <ul className="list-disc list-inside space-y-0.5 mb-2 text-[var(--hermes-text)]">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal list-inside space-y-0.5 mb-2 text-[var(--hermes-text)]">{children}</ol>
        ),
        li: ({ children }) => (
          <li className="leading-relaxed">{children}</li>
        ),
        // 代码块
        pre: ({ children }) => (
          <pre className="bg-[var(--hermes-bg-dark)] rounded-md p-2 my-1.5 overflow-x-auto text-xs font-mono">
            {children}
          </pre>
        ),
        code: ({ className, children, ...props }) => {
          // 行内代码 vs 代码块
          const isInline = !className;
          return isInline ? (
            <code className="bg-[var(--hermes-bg-dark)] px-1 py-0.5 rounded text-xs font-mono text-blue-300" {...props}>
              {children}
            </code>
          ) : (
            <code className="font-mono" {...props}>{children}</code>
          )
        },
        // 引用块
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-[var(--hermes-amber)] pl-2 my-1 text-[var(--hermes-dim)] italic">
            {children}
          </blockquote>
        ),
        // 段落
        p: ({ children }) => (
          <p className="leading-relaxed mb-1 last:mb-0">{children}</p>
        ),
        // 分割线
        hr: () => (
          <hr className="border-[var(--hermes-border)] my-2" />
        ),
        // 链接
        a: ({ href, children }) => (
          <a href={href} className="text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">
            {children}
          </a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
    </div>
  );
}
