import { useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store';
import { Bot, User, Copy, Check, RotateCcw, Cpu, Sparkles, Server, Code2 } from 'lucide-react';
import VoiceOrb from './VoiceOrb';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';

// ─── Typing Indicator ───
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 py-1">
      {[0, 1, 2].map(i => (
        <motion.div
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-omega-cyan"
          animate={{ scale: [1, 1.4, 1], opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
        />
      ))}
      <span className="text-[10px] font-mono text-text-muted ml-2">Processing neural sequence...</span>
    </div>
  );
}

// ─── Copy Button for Code Blocks ───
function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1.5 text-text-muted hover:text-text-primary transition-colors"
    >
      {copied ? <Check size={11} className="text-omega-green" /> : <Copy size={11} />}
      <span className="text-[10px]">{copied ? 'Copied!' : 'Copy'}</span>
    </button>
  );
}

// ─── Custom Markdown Renderers ───
const markdownComponents = {
  // Code blocks with syntax header and copy button
  code({ children, className, ...props }) {
    const match = /language-(\w+)/.exec(className || '');
    const codeText = String(children).replace(/\n$/, '');

    // Inline code (no language class & short)
    if (!match) {
      return (
        <code className="bg-[rgba(0,245,255,0.1)] text-omega-cyan px-1.5 py-0.5 rounded-md text-[0.85em] font-mono" {...props}>
          {children}
        </code>
      );
    }

    // Fenced code block
    return (
      <div className="my-3 rounded-xl overflow-hidden border border-glass-border">
        <div className="code-header">
          <span className="text-text-muted">{match[1] || 'code'}</span>
          <CopyButton text={codeText} />
        </div>
        <pre className="!m-0 !rounded-none !border-0 overflow-x-auto">
          <code className="block px-5 py-4 text-[13px] leading-relaxed font-mono text-text-primary">
            {codeText}
          </code>
        </pre>
      </div>
    );
  },
  // Override pre to avoid double-wrapping
  pre({ children }) {
    return <>{children}</>;
  },
  p({ children }) {
    return <p className="mb-3 leading-relaxed text-[#CCD6F6]">{children}</p>;
  },
  strong({ children }) {
    return <strong className="text-white font-semibold">{children}</strong>;
  },
  em({ children }) {
    return <em className="text-omega-cyan">{children}</em>;
  },
  ul({ children }) {
    return <ul className="mb-3 pl-5 space-y-1.5 text-[#CCD6F6] list-disc">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="mb-3 pl-5 space-y-1.5 text-[#CCD6F6] list-decimal">{children}</ol>;
  },
  li({ children }) {
    return <li className="leading-relaxed">{children}</li>;
  },
  h1({ children }) {
    return <h1 className="text-xl font-display font-bold text-white mt-5 mb-3">{children}</h1>;
  },
  h2({ children }) {
    return <h2 className="text-lg font-display font-semibold text-white mt-4 mb-2">{children}</h2>;
  },
  h3({ children }) {
    return <h3 className="text-base font-display font-semibold text-white mt-3 mb-2">{children}</h3>;
  },
  a({ href, children }) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer"
        className="text-omega-cyan border-b border-omega-cyan/30 hover:border-omega-cyan transition-colors">
        {children}
      </a>
    );
  },
  blockquote({ children }) {
    return (
      <blockquote className="border-l-3 border-omega-purple pl-4 my-3 text-text-secondary italic">
        {children}
      </blockquote>
    );
  },
};

// ─── Message Bubble ───
function MessageBubble({ msg }) {
  const isUser = msg.role === 'user';
  const sendMessage = useStore(s => s.sendMessage);
  const messages = useStore(s => s.messages);

  const retryMessage = () => {
    const idx = messages.findIndex(m => m.id === msg.id);
    if (idx > 0 && messages[idx - 1].role === 'user') {
      sendMessage(messages[idx - 1].content);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="flex gap-3 w-full group"
    >
      {/* Avatar */}
      <div className={`w-7 h-7 rounded-lg flex-shrink-0 flex items-center justify-center mt-0.5 ${
        isUser
          ? 'bg-white/5 border border-glass-border'
          : msg.isError
          ? 'bg-omega-red/10 border border-omega-red/20'
          : 'bg-gradient-to-tr from-omega-cyan/20 to-omega-purple/20 border border-omega-cyan/20'
      }`}>
        {isUser ? (
          <User size={13} className="text-text-secondary" />
        ) : (
          <Bot size={13} className={msg.isError ? 'text-omega-red' : 'text-omega-cyan'} />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-[11px] font-semibold ${
            isUser ? 'text-text-secondary' : msg.isError ? 'text-omega-red' : 'text-omega-cyan'
          }`}>
            {isUser ? 'You' : 'JARVIS'}
          </span>
          <span className="text-[9px] font-mono text-text-muted">
            {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
          {!isUser && msg.isStreaming && (
            <span className="text-[9px] font-hud tracking-wider text-omega-cyan animate-pulse uppercase">
              streaming
            </span>
          )}
        </div>

        {isUser ? (
          <div className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap">
            {msg.content}
          </div>
        ) : (
          <div className="text-sm">
            {msg.isStreaming && !msg.content ? (
              <TypingIndicator />
            ) : msg.isError ? (
              <div className="space-y-2">
                <div className="text-omega-red text-sm flex items-start gap-2 leading-relaxed glass-card p-3 border-omega-red/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-omega-red flex-shrink-0 mt-1.5" />
                  <span>{msg.content}</span>
                </div>
                <button
                  onClick={retryMessage}
                  className="flex items-center gap-1.5 text-[11px] text-text-muted hover:text-omega-cyan transition-colors font-medium"
                >
                  <RotateCcw size={11} />
                  Retry
                </button>
              </div>
            ) : msg.content ? (
              <div className="prose-omega">
                <ReactMarkdown components={markdownComponents}>
                  {msg.content}
                </ReactMarkdown>
              </div>
            ) : (
              <span className="text-text-muted text-xs italic">No response received</span>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ─── Welcome Screen ───
function WelcomeScreen() {
  const sendMessage = useStore(s => s.sendMessage);
  const setInputText = useStore(s => s.setInputText);

  const suggestions = [
    { icon: Server, title: 'System Diagnostics', desc: 'Check CPU, GPU, and RAM loads', prompt: 'Analyze system performance and generate a diagnostic report.', color: 'text-omega-cyan' },
    { icon: Code2, title: 'Code Optimization', desc: 'Refactor algorithms for speed', prompt: 'Review my codebase for performance optimizations.', color: 'text-omega-purple' },
    { icon: Sparkles, title: 'Creative Generation', desc: 'Stories, scripts, and ideas', prompt: 'Help me brainstorm creative ideas for my project.', color: 'text-omega-amber' },
    { icon: Cpu, title: 'Neural Analysis', desc: 'Deep pattern recognition', prompt: 'Perform a neural analysis on the current system state.', color: 'text-omega-green' },
  ];

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6">
      {/* Voice Orb */}
      <VoiceOrb />

      {/* Title */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.6 }}
        className="text-center mt-8 mb-10"
      >
        <h1 className="text-3xl font-display font-semibold text-text-primary mb-2">
          How can I assist you?
        </h1>
        <p className="text-sm text-text-secondary max-w-md mx-auto leading-relaxed">
          Connected to local neural architecture. Ready for deep analysis, coding, creative generation, or system operations.
        </p>
      </motion.div>

      {/* Suggestion Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.6 }}
        className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-2xl"
      >
        {suggestions.map((s, i) => {
          const Icon = s.icon;
          return (
            <motion.button
              key={i}
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setInputText(s.prompt)}
              className="glass-card p-4 text-left group"
            >
              <Icon size={18} className={`${s.color} mb-3 group-hover:scale-110 transition-transform`} />
              <h3 className="text-sm font-semibold text-text-primary mb-1">{s.title}</h3>
              <p className="text-[11px] text-text-muted leading-relaxed">{s.desc}</p>
            </motion.button>
          );
        })}
      </motion.div>
    </div>
  );
}

// ─── Center Panel (Main Chat Area) ───
export default function CenterPanel() {
  const messages = useStore(s => s.messages);
  const isStreaming = useStore(s => s.isStreaming);
  const scrollContainerRef = useRef(null);
  const messagesEndRef = useRef(null);
  const [userScrolledUp, setUserScrolledUp] = useState(false);

  // Auto-scroll: only when user hasn't scrolled up
  const scrollToBottom = useCallback(() => {
    if (!userScrolledUp) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [userScrolledUp]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Detect if user scrolled up manually
  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    setUserScrolledUp(!atBottom);
  }, []);

  // Reset scroll lock when streaming ends
  useEffect(() => {
    if (!isStreaming) {
      setUserScrolledUp(false);
    }
  }, [isStreaming]);

  const hasMessages = messages.length > 0;

  return (
    <div className="flex-1 flex flex-col min-w-0 relative">
      {hasMessages ? (
        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto px-4 md:px-8 py-6"
        >
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map(msg => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>
      ) : (
        <WelcomeScreen />
      )}

      {/* Scroll to bottom FAB when user scrolled up */}
      <AnimatePresence>
        {userScrolledUp && hasMessages && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={() => {
              setUserScrolledUp(false);
              messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="absolute bottom-4 left-1/2 -translate-x-1/2 w-8 h-8 rounded-full
                       bg-omega-surface border border-glass-border flex items-center justify-center
                       text-text-secondary hover:text-omega-cyan hover:border-omega-cyan/30 transition-all
                       shadow-lg z-10"
            title="Scroll to bottom"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
}
