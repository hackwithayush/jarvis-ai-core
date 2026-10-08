import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store';
import {
  Brain, Shield, Wifi, WifiOff, Cpu,
  PanelLeftOpen, PanelLeftClose,
  PanelRightOpen, PanelRightClose,
  Zap, Activity, ChevronDown
} from 'lucide-react';

export default function TopBar() {
  const neuralStatus = useStore(s => s.neuralStatus);
  const activeModel = useStore(s => s.activeModel);
  const setActiveModel = useStore(s => s.setActiveModel);
  const securityState = useStore(s => s.securityState);
  const internetStatus = useStore(s => s.internetStatus);
  const sidebarOpen = useStore(s => s.sidebarOpen);
  const rightPanelOpen = useStore(s => s.rightPanelOpen);
  const toggleSidebar = useStore(s => s.toggleSidebar);
  const toggleRightPanel = useStore(s => s.toggleRightPanel);
  const systemStats = useStore(s => s.systemStats);
  const addNotification = useStore(s => s.addNotification);

  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  const availableModels = [
    { id: 'llama2-uncensored:latest', label: 'Llama 2 Uncensored', tag: 'LOCAL RAW', color: 'bg-rose-500' },
    { id: 'llama3.2:latest', label: 'Llama 3.2 Local', tag: 'LOCAL FAST', color: 'bg-purple-500' },
    { id: 'openai/gpt-oss-120b', label: 'GPT-OSS 120B', tag: 'FLAGSHIP', color: 'bg-cyan-500' },
    { id: 'qwen/qwen3.8-27b', label: 'Qwen 3.8 27B', tag: 'FAST CODE', color: 'bg-emerald-500' },
    { id: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', tag: 'MULTIMODAL', color: 'bg-sky-500' },
    { id: 'meta-llama/llama-3.3-70b-instruct', label: 'Llama 3.3 70B', tag: 'PRO REASON', color: 'bg-amber-500' },
  ];

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setModelDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const statusColor = {
    online: 'bg-omega-green',
    degraded: 'bg-omega-amber',
    offline: 'bg-omega-red',
  }[neuralStatus] || 'bg-omega-green';

  return (
    <motion.div
      initial={{ y: -40, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="h-11 flex-shrink-0 glass border-b border-glass-border flex items-center justify-between px-4 relative z-50"
    >
      {/* Left Section */}
      <div className="flex items-center gap-3">
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-md hover:bg-white/5 transition-colors text-text-secondary hover:text-omega-cyan"
          title="Toggle sidebar"
        >
          {sidebarOpen ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
        </button>

        <div 
          onClick={() => addNotification(`Neural Link Status: ${neuralStatus.toUpperCase()} (Bi-directional SSE active)`, 'info')}
          className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
          title="Neural Link Health"
        >
          <div className="relative">
            <Brain size={16} className="text-omega-cyan" />
            <div className={`absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full ${statusColor}`} />
          </div>
          <span className="font-hud text-[10px] tracking-widest text-omega-cyan uppercase">
            Neural Link
          </span>
          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded-sm ${
            neuralStatus === 'online'
              ? 'bg-omega-green/10 text-omega-green'
              : neuralStatus === 'degraded'
              ? 'bg-omega-amber/10 text-omega-amber'
              : 'bg-omega-red/10 text-omega-red'
          }`}>
            {neuralStatus.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Center Section — Brand */}
      <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2">
        <div className="w-5 h-5 rounded-full bg-gradient-to-tr from-omega-cyan to-omega-purple flex items-center justify-center shadow-[0_0_15px_rgba(0,245,255,0.3)]">
          <Zap size={10} className="text-white" />
        </div>
        <span className="font-hud text-xs tracking-[0.3em] text-text-primary">
          JARVIS
        </span>
        <span className="font-hud text-[10px] tracking-widest text-omega-purple">
          OMEGA
        </span>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-3">
        {/* Quick Stats */}
        <div className="hidden md:flex items-center gap-3 text-[10px] font-mono text-text-secondary">
          <div className="flex items-center gap-1" title="Real-time Host CPU Utilization">
            <Cpu size={11} className="text-omega-cyan" />
            <span>{systemStats.cpu}</span>
          </div>
          <div className="flex items-center gap-1" title="Hardware GPU / Graphics State">
            <Activity size={11} className="text-omega-purple" />
            <span>{systemStats.gpu}</span>
          </div>
        </div>

        <div className="h-4 w-px bg-white/10" />

        {/* Active Model Selector */}
        <div ref={dropdownRef} className="relative hidden md:block">
          <button
            onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/5 hover:bg-white/10 border border-white/10 text-[10px] cursor-pointer transition-all"
            title="Click to switch intelligence engine"
          >
            <div className="w-1.5 h-1.5 rounded-full bg-omega-cyan animate-pulse" />
            <span className="font-mono text-text-primary">
              {availableModels.find(m => m.id === activeModel)?.label || activeModel}
            </span>
            <ChevronDown size={10} className={`text-text-secondary transition-transform ${modelDropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          <AnimatePresence>
            {modelDropdownOpen && (
              <motion.div
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 5 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 mt-1.5 w-60 rounded-lg glass border border-glass-border bg-[#0a0f1d]/95 backdrop-blur-xl shadow-2xl p-1 z-50 overflow-hidden font-mono text-[10px]"
              >
                <div className="px-2 py-1 text-[9px] text-text-muted uppercase tracking-wider font-semibold border-b border-white/5 flex items-center justify-between">
                  <span>Intelligence Matrix</span>
                  <span className="text-[8px] text-omega-cyan">OLLAMA / CLOUD</span>
                </div>
                <div className="py-1 flex flex-col gap-0.5">
                  {availableModels.map((m) => {
                    const isSelected = activeModel === m.id;
                    return (
                      <button
                        key={m.id}
                        onClick={() => {
                          setActiveModel(m.id);
                          setModelDropdownOpen(false);
                          addNotification(`Active Engine switched to ${m.label}`, 'success');
                        }}
                        className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-left transition-colors ${
                          isSelected ? 'bg-omega-cyan/15 text-omega-cyan font-bold' : 'text-text-secondary hover:bg-white/5 hover:text-text-primary'
                        }`}
                      >
                        <div className="flex items-center gap-2 truncate">
                          <div className={`w-1.5 h-1.5 rounded-full ${m.color}`} />
                          <span className="truncate">{m.label}</span>
                        </div>
                        <span className={`text-[8px] px-1 py-0.5 rounded font-mono ${
                          m.tag.includes('LOCAL') ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 'bg-white/5 text-text-muted'
                        }`}>
                          {m.tag}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Security */}
        <div 
          onClick={() => addNotification('Security Perimeter: Zero-Trust Active (Sandboxed)', 'success')}
          className="flex items-center gap-1 text-[10px] cursor-pointer hover:opacity-80 transition-opacity"
          title="Zero-Trust Security Perimeter: Enforced"
        >
          <Shield size={12} className={securityState === 'secure' ? 'text-omega-green' : 'text-omega-red'} />
        </div>

        {/* Internet */}
        <div 
          onClick={() => addNotification(internetStatus === 'connected' ? 'Network Link: Connected to Cloud Gateway & Local Subsystems' : 'Network Link: Offline', 'info')}
          className="flex items-center cursor-pointer hover:opacity-80 transition-opacity"
          title={`Network: ${internetStatus === 'connected' ? 'Connected' : 'Offline'}`}
        >
          {internetStatus === 'connected' ? (
            <Wifi size={13} className="text-omega-green" />
          ) : (
            <WifiOff size={13} className="text-omega-red" />
          )}
        </div>

        <div className="h-4 w-px bg-white/10" />

        <button
          onClick={toggleRightPanel}
          className="p-1.5 rounded-md hover:bg-white/5 transition-colors text-text-secondary hover:text-omega-cyan"
          title="Toggle system panel"
        >
          {rightPanelOpen ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
        </button>
      </div>
    </motion.div>
  );
}
