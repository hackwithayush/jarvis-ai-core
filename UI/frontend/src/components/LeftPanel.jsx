import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store';
import {
  Plus, MessageSquare, Search, Clock, Brain,
  Sparkles, Code2, Shield, Globe, Bot,
  ChevronDown, Settings, Layers, Trash2,
  MoreHorizontal, Hash, Calendar,
  Loader2, RefreshCw, X
} from 'lucide-react';
import MemoryGraph from './MemoryGraph';

const AI_MODES = [
  { id: 'chat', label: 'Neural Chat', icon: MessageSquare, color: 'text-omega-cyan' },
  { id: 'code', label: 'Code Forge', icon: Code2, color: 'text-omega-purple' },
  { id: 'creative', label: 'Creative Core', icon: Sparkles, color: 'text-omega-amber' },
  { id: 'security', label: 'Security Scan', icon: Shield, color: 'text-omega-red' },
  { id: 'research', label: 'Intel Research', icon: Globe, color: 'text-omega-green' },
];

// ─── Time Grouping Helper ───
function groupConversationsByTime(conversations) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const lastWeek = new Date(today);
  lastWeek.setDate(lastWeek.getDate() - 7);
  const lastMonth = new Date(today);
  lastMonth.setMonth(lastMonth.getMonth() - 1);

  const groups = {
    today: [],
    yesterday: [],
    thisWeek: [],
    thisMonth: [],
    older: [],
  };

  conversations.forEach(conv => {
    const date = new Date(conv.updated_at || conv.created_at || Date.now());
    if (date >= today) {
      groups.today.push(conv);
    } else if (date >= yesterday) {
      groups.yesterday.push(conv);
    } else if (date >= lastWeek) {
      groups.thisWeek.push(conv);
    } else if (date >= lastMonth) {
      groups.thisMonth.push(conv);
    } else {
      groups.older.push(conv);
    }
  });

  return groups;
}

const GROUP_LABELS = {
  today: { label: 'Today', icon: Clock },
  yesterday: { label: 'Yesterday', icon: Clock },
  thisWeek: { label: 'This Week', icon: Calendar },
  thisMonth: { label: 'This Month', icon: Calendar },
  older: { label: 'Older', icon: Calendar },
};

// ─── Context Menu for Conversation ───
function ConversationContextMenu({ conv, position, onClose, onDelete }) {
  const menuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  return (
    <motion.div
      ref={menuRef}
      initial={{ opacity: 0, scale: 0.9, y: -5 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9, y: -5 }}
      transition={{ duration: 0.15 }}
      className="absolute z-50 glass-card border border-glass-border-light shadow-xl rounded-lg py-1 min-w-[160px]"
      style={{ top: position.y, left: position.x }}
    >
      <button
        onClick={() => { onDelete(conv.id); onClose(); }}
        className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-omega-red hover:bg-omega-red/10 transition-colors"
      >
        <Trash2 size={12} />
        <span>Delete Thread</span>
      </button>
    </motion.div>
  );
}

// ─── Single Conversation Item ───
function ConversationItem({ conv, isActive, onClick, onDelete }) {
  const [showMenu, setShowMenu] = useState(false);
  const [menuPos, setMenuPos] = useState({ x: 0, y: 0 });
  const itemRef = useRef(null);

  const handleContextMenu = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const rect = itemRef.current?.getBoundingClientRect();
    if (rect) {
      setMenuPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    }
    setShowMenu(true);
  };

  const messageCount = conv.message_count || 0;
  const timeStr = conv.updated_at
    ? formatRelativeTime(new Date(conv.updated_at))
    : '';

  return (
    <div ref={itemRef} className="relative">
      <motion.button
        layout
        onClick={onClick}
        onContextMenu={handleContextMenu}
        className={`w-full text-left px-3 py-2.5 rounded-lg text-xs transition-all duration-200 group relative
          ${isActive
            ? 'bg-omega-cyan/5 border border-omega-cyan/15 text-text-primary'
            : 'text-text-secondary hover:bg-white/3 hover:text-text-primary border border-transparent'
          }`}
      >
        {/* Active indicator bar */}
        {isActive && (
          <motion.div
            layoutId="activeConvIndicator"
            className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-omega-cyan rounded-r"
          />
        )}

        <div className="flex items-center gap-2">
          <MessageSquare size={12} className={
            isActive ? 'text-omega-cyan flex-shrink-0' : 'text-text-muted group-hover:text-text-secondary flex-shrink-0'
          } />
          <span className="truncate flex-1 font-medium leading-tight">
            {conv.title || 'Untitled Thread'}
          </span>
          
          {/* Hover actions */}
          <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 flex-shrink-0">
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(conv.id); }}
              className="p-1 rounded hover:bg-omega-red/10 text-text-muted hover:text-omega-red transition-colors"
              title="Delete thread"
            >
              <Trash2 size={11} />
            </button>
          </div>
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-2 mt-1 ml-5">
          {messageCount > 0 && (
            <span className="text-[9px] font-mono text-text-muted flex items-center gap-1">
              <Hash size={8} />
              {messageCount} msg{messageCount !== 1 ? 's' : ''}
            </span>
          )}
          {timeStr && (
            <span className="text-[9px] font-mono text-text-muted">
              {timeStr}
            </span>
          )}
        </div>
      </motion.button>

      {/* Context Menu */}
      <AnimatePresence>
        {showMenu && (
          <ConversationContextMenu
            conv={conv}
            position={menuPos}
            onClose={() => setShowMenu(false)}
            onDelete={onDelete}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Relative Time Formatting ───
function formatRelativeTime(date) {
  const now = new Date();
  const diff = now - date;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function LeftPanel() {
  const conversations = useStore(s => s.conversations);
  const conversationsLoading = useStore(s => s.conversationsLoading);
  const currentConvId = useStore(s => s.currentConvId);
  const newConversation = useStore(s => s.newConversation);
  const loadConversation = useStore(s => s.loadConversation);
  const deleteConversation = useStore(s => s.deleteConversation);
  const fetchConversations = useStore(s => s.fetchConversations);
  const aiMode = useStore(s => s.aiMode);
  const setAiMode = useStore(s => s.setAiMode);
  const [searchQuery, setSearchQuery] = useState('');
  const [showModes, setShowModes] = useState(true);
  const [panelTab, setPanelTab] = useState('history'); // history | graph

  // Auto-fetch on mount
  useEffect(() => {
    fetchConversations();
  }, []);

  // Filter by search
  const filtered = conversations.filter(c =>
    !searchQuery || (c.title || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group by time
  const grouped = groupConversationsByTime(filtered);

  const totalCount = conversations.length;

  return (
    <motion.div
      initial={{ x: -280, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: -280, opacity: 0 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className="w-[280px] flex-shrink-0 glass border-r border-glass-border flex flex-col h-full relative z-30"
    >
      {/* Header — New Thread */}
      <div className="p-4 border-b border-glass-border">
        <button
          onClick={newConversation}
          className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-omega-cyan/10 to-omega-purple/10 
                     border border-omega-cyan/20 hover:border-omega-cyan/40
                     hover:from-omega-cyan/15 hover:to-omega-purple/15
                     transition-all duration-300 flex items-center gap-3 text-sm font-medium
                     group"
        >
          <div className="w-7 h-7 rounded-lg bg-omega-cyan/10 flex items-center justify-center
                          group-hover:bg-omega-cyan/20 transition-colors">
            <Plus size={14} className="text-omega-cyan" />
          </div>
          <span className="text-text-primary">New Thread</span>
          <span className="ml-auto text-[10px] font-mono text-text-muted px-1.5 py-0.5 rounded bg-white/5">
            ⌘N
          </span>
        </button>
      </div>

      {/* AI Mode Selector */}
      <div className="px-4 pt-3">
        <button
          onClick={() => setShowModes(!showModes)}
          className="w-full flex items-center justify-between text-[10px] font-hud tracking-widest text-text-muted uppercase mb-2 hover:text-text-secondary transition-colors"
        >
          <div className="flex items-center gap-2">
            <Layers size={11} />
            <span>AI Mode</span>
          </div>
          <ChevronDown size={11} className={`transition-transform duration-200 ${showModes ? 'rotate-180' : ''}`} />
        </button>

        <AnimatePresence>
          {showModes && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="space-y-1 mb-3 overflow-hidden"
            >
              {AI_MODES.map(mode => {
                const Icon = mode.icon;
                const isActive = aiMode === mode.id;
                return (
                  <button
                    key={mode.id}
                    onClick={() => setAiMode(mode.id)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs transition-all duration-200
                      ${isActive
                        ? 'bg-white/5 border border-glass-border-light text-text-primary'
                        : 'text-text-secondary hover:bg-white/3 hover:text-text-primary border border-transparent'
                      }`}
                  >
                    <Icon size={13} className={isActive ? mode.color : 'text-text-muted'} />
                    <span className="font-medium">{mode.label}</span>
                    {isActive && (
                      <div className="ml-auto w-1.5 h-1.5 rounded-full bg-omega-cyan animate-pulse" />
                    )}
                  </button>
                );
              })}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Search */}
      <div className="px-4 pb-2">
        <div className="relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            placeholder="Search threads..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full bg-white/3 border border-glass-border rounded-lg py-2 pl-9 pr-8 text-xs text-text-primary
                       placeholder:text-text-muted focus:outline-none focus:border-omega-cyan/30
                       transition-colors"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Tab Switcher (History vs Memory Graph) */}
      <div className="px-4 pb-2 flex gap-1 border-b border-glass-border mb-2">
        <button
          onClick={() => setPanelTab('history')}
          className={`flex-1 py-1 rounded text-[10px] font-hud uppercase tracking-wider transition-colors
            ${panelTab === 'history'
              ? 'bg-omega-cyan/15 text-omega-cyan border border-omega-cyan/20'
              : 'text-text-muted hover:text-text-secondary border border-transparent'
            }`}
        >
          History
        </button>
        <button
          onClick={() => setPanelTab('graph')}
          className={`flex-1 py-1 rounded text-[10px] font-hud uppercase tracking-wider transition-colors
            ${panelTab === 'graph'
              ? 'bg-omega-green/15 text-omega-green border border-omega-green/20'
              : 'text-text-muted hover:text-text-secondary border border-transparent'
            }`}
        >
          Memory Graph
        </button>
      </div>

      {/* ════════════════════════════════════════
          CONVERSATION HISTORY / GRAPH VIEW
          ════════════════════════════════════════ */}
      <div className="flex-1 overflow-y-auto px-3 py-2 relative">
        {panelTab === 'graph' ? (
          <MemoryGraph />
        ) : (
          <>
            {/* Section Header */}
            <div className="flex items-center justify-between mb-2 px-1">
              <div className="text-[10px] font-hud tracking-widest text-text-muted uppercase flex items-center gap-2">
                <Clock size={10} />
                <span>History</span>
                {totalCount > 0 && (
                  <span className="text-[9px] font-mono text-text-muted bg-white/5 rounded px-1.5 py-0.5">
                    {totalCount}
                  </span>
                )}
              </div>
              <button
                onClick={() => fetchConversations()}
                className="p-1 rounded hover:bg-white/5 text-text-muted hover:text-omega-cyan transition-colors"
                title="Refresh conversations"
              >
                <RefreshCw size={11} className={conversationsLoading ? 'animate-spin' : ''} />
              </button>
            </div>

            {/* Loading State */}
            {conversationsLoading && conversations.length === 0 && (
              <div className="flex flex-col items-center py-10 gap-3">
                <Loader2 size={20} className="text-omega-cyan animate-spin" />
                <span className="text-[10px] text-text-muted font-mono">Loading neural threads...</span>
              </div>
            )}

            {/* Empty State */}
            {!conversationsLoading && filtered.length === 0 && (
              <div className="px-3 py-10 text-center">
                <div className="w-12 h-12 rounded-xl bg-omega-surface-light border border-glass-border flex items-center justify-center mx-auto mb-3">
                  <Bot size={20} className="text-text-muted" />
                </div>
                {searchQuery ? (
                  <>
                    <p className="text-xs text-text-muted">No threads matching</p>
                    <p className="text-[11px] text-omega-cyan font-mono mt-1">"{searchQuery}"</p>
                  </>
                ) : (
                  <>
                    <p className="text-xs text-text-secondary font-medium">No threads yet</p>
                    <p className="text-[10px] text-text-muted mt-1 leading-relaxed">
                      Start a conversation and it will<br />appear in your neural memory
                    </p>
                  </>
                )}
              </div>
            )}

            {/* Grouped Conversations */}
            {Object.entries(grouped).map(([groupKey, convs]) => {
              if (convs.length === 0) return null;
              const { label, icon: GroupIcon } = GROUP_LABELS[groupKey];

              return (
                <div key={groupKey} className="mb-3">
                  {/* Group Label */}
                  <div className="flex items-center gap-2 px-2 py-1.5 text-[9px] font-hud tracking-widest text-text-muted uppercase">
                    <GroupIcon size={9} />
                    <span>{label}</span>
                    <div className="flex-1 h-px bg-glass-border ml-1" />
                    <span className="font-mono text-[8px]">{convs.length}</span>
                  </div>

                  {/* Conversation Items */}
                  <div className="space-y-0.5">
                    {convs.map(conv => (
                      <ConversationItem
                        key={conv.id}
                        conv={conv}
                        isActive={currentConvId === conv.id}
                        onClick={() => loadConversation(conv.id)}
                        onDelete={deleteConversation}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </>
        )}
      </div>

      {/* Footer Status */}
      <div className="p-3 border-t border-glass-border">
        <div className="flex items-center justify-between text-[10px]">
          <div className="flex items-center gap-2 text-text-muted">
            <div className="status-dot status-online" />
            <span className="font-mono">Local Node Active</span>
          </div>
          <button className="p-1.5 rounded-md hover:bg-white/5 text-text-muted hover:text-text-secondary transition-colors">
            <Settings size={13} />
          </button>
        </div>
      </div>
    </motion.div>
  );
}
