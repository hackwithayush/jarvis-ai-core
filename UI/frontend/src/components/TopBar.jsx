import { motion } from 'framer-motion';
import { useStore } from '../store';
import {
  Brain, Shield, Wifi, WifiOff, Cpu,
  PanelLeftOpen, PanelLeftClose,
  PanelRightOpen, PanelRightClose,
  Zap, Activity
} from 'lucide-react';

export default function TopBar() {
  const neuralStatus = useStore(s => s.neuralStatus);
  const activeModel = useStore(s => s.activeModel);
  const securityState = useStore(s => s.securityState);
  const internetStatus = useStore(s => s.internetStatus);
  const sidebarOpen = useStore(s => s.sidebarOpen);
  const rightPanelOpen = useStore(s => s.rightPanelOpen);
  const toggleSidebar = useStore(s => s.toggleSidebar);
  const toggleRightPanel = useStore(s => s.toggleRightPanel);
  const systemStats = useStore(s => s.systemStats);

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

        <div className="flex items-center gap-2">
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
          <div className="flex items-center gap-1">
            <Cpu size={11} className="text-omega-cyan" />
            <span>{systemStats.cpu}</span>
          </div>
          <div className="flex items-center gap-1">
            <Activity size={11} className="text-omega-purple" />
            <span>{systemStats.gpu}</span>
          </div>
        </div>

        <div className="h-4 w-px bg-white/10" />

        {/* Active Model */}
        <div className="hidden md:flex items-center gap-1.5 text-[10px]">
          <div className="w-1.5 h-1.5 rounded-full bg-omega-cyan animate-pulse" />
          <span className="font-mono text-text-secondary">{activeModel}</span>
        </div>

        {/* Security */}
        <div className="flex items-center gap-1 text-[10px]">
          <Shield size={12} className={securityState === 'secure' ? 'text-omega-green' : 'text-omega-red'} />
        </div>

        {/* Internet */}
        <div className="flex items-center">
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
