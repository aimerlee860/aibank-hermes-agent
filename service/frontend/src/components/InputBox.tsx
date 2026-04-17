import { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';

interface InputBoxProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function InputBox({ onSend, disabled, placeholder = '输入消息...' }: InputBoxProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

  const handleSubmit = () => {
    if (!input.trim() || disabled) return;
    onSend(input.trim());
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="p-2 border-t border-[var(--hermes-border)] bg-[var(--hermes-bg-dark)]">
      <div className="flex gap-2 items-end">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className="flex-1 resize-none rounded-lg border border-[var(--hermes-border)] bg-[var(--hermes-bg)] px-2 py-1.5 text-sm text-[var(--hermes-text)] placeholder-[var(--hermes-dim)] focus:border-[var(--hermes-amber)] focus:outline-none disabled:opacity-50 max-h-[120px] overflow-y-auto"
          rows={1}
        />
        <button
          onClick={handleSubmit}
          disabled={disabled || !input.trim()}
          className="shrink-0 p-1.5 rounded-lg bg-[var(--hermes-amber)] hover:bg-[var(--hermes-gold)] disabled:opacity-50 disabled:cursor-not-allowed text-[var(--hermes-bg-dark)] transition-colors"
        >
          <Send size={16} />
        </button>
      </div>
      <div className="text-xs text-[var(--hermes-dim)] mt-0.5 opacity-60">
        Enter 发送 · Shift+Enter 换行
      </div>
    </div>
  );
}