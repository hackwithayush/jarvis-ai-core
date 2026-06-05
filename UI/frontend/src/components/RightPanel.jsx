import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useStore } from '../store';
import {
  Cpu, HardDrive, Activity, Thermometer,
  Wifi, Server, Database, Gauge,
  ChevronDown, ChevronUp, Radio,
  Heart, Zap, MemoryStick, Globe, Code2
} from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';

function MiniChart({ data, color, height = 40 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#grad-${color})`}
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function StatCard({ icon: Icon, label, value, color, chartData, unit = '' }) {
  return (
    <div className="glass-card p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon size={12} className={color} />
          <span className="text-[10px] font-hud tracking-wider text-text-muted uppercase">{label}</span>
        </div>
        <span className={`text-sm font-mono font-semibold ${color}`}>{value}{unit}</span>
      </div>
      {chartData && <MiniChart data={chartData} color={color === 'text-omega-cyan' ? '#00F5FF' : color === 'text-omega-purple' ? '#8A5CFF' : color === 'text-omega-green' ? '#00FFB2' : '#FFB800'} />}
    </div>
  );
}

function AgentCard({ name, status, model, tasks }) {
  const statusColors = {
    active: 'bg-omega-green',
    idle: 'bg-omega-amber',
    offline: 'bg-omega-red',
  };

  return (
    <div className="glass-card p-3 flex items-center gap-3">
      <div className="relative">
        <div className="w-8 h-8 rounded-lg bg-omega-purple/10 border border-omega-purple/20 flex items-center justify-center">
          <Radio size={13} className="text-omega-purple" />
        </div>
        <div className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full ${statusColors[status]} border-2 border-omega-bg`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold text-text-primary truncate">{name}</p>
        <p className="text-[10px] font-mono text-text-muted">{model}</p>
      </div>
      <span className="text-[10px] font-mono text-text-muted">{tasks} tasks</span>
    </div>
  );
}

export default function RightPanel() {
  const systemStats = useStore(s => s.systemStats);
  const neuralStatus = useStore(s => s.neuralStatus);
  const activeModel = useStore(s => s.activeModel);
  const [cpuHistory, setCpuHistory] = useState([]);
  const [gpuHistory, setGpuHistory] = useState([]);
  const [expandedSection, setExpandedSection] = useState('system');

  useEffect(() => {
    const interval = setInterval(() => {
      setCpuHistory(prev => {
        const next = [...prev, { value: parseFloat(systemStats.cpu) || Math.random() * 40 + 10 }];
        return next.slice(-20);
      });
      setGpuHistory(prev => {
        const next = [...prev, { value: parseFloat(systemStats.gpu) || Math.random() * 30 + 5 }];
        return next.slice(-20);
      });
    }, 2000);
    return () => clearInterval(interval);
  }, [systemStats]);

  const agents = systemStats.agents || [
    { name: 'Neural Core', status: 'active', model: activeModel, tasks: 1 },
    { name: 'Code Forge', status: 'idle', model: 'codestral', tasks: 0 },
    { name: 'Vision Node', status: 'offline', model: 'llava', tasks: 0 },
    { name: 'Intel Agent', status: 'active', model: 'deepseek-r1', tasks: 2 },
  ];

  const apiEndpoints = systemStats.api_health || [
    { name: '/api/chat', status: 'healthy', latency: '23ms' },
    { name: '/api/system', status: 'healthy', latency: '8ms' },
    { name: '/api/upload', status: 'healthy', latency: '45ms' },
    { name: '/api/studio', status: 'degraded', latency: '120ms' },
  ];

  return (
    <motion.div
      initial={{ x: 300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 300, opacity: 0 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className="w-[280px] flex-shrink-0 glass border-l border-glass-border flex flex-col h-full overflow-y-auto relative z-30"
    >
      {/* Header */}
      <div className="p-3 border-b border-glass-border flex items-center gap-2">
        <Activity size={13} className="text-omega-cyan" />
        <span className="text-[10px] font-hud tracking-widest text-omega-cyan uppercase">System Monitor</span>
        <div className="ml-auto flex items-center gap-1.5">
          <Heart size={10} className="text-omega-green animate-pulse" />
          <span className="text-[9px] font-mono text-omega-green">LIVE</span>
        </div>
      </div>

      <div className="p-3 space-y-3 flex-1">
        {/* ─── System Stats ─── */}
        <div>
          <button
            onClick={() => setExpandedSection(expandedSection === 'system' ? null : 'system')}
            className="w-full flex items-center justify-between text-[10px] font-hud tracking-widest text-text-muted uppercase mb-2"
          >
            <div className="flex items-center gap-2">
              <Gauge size={11} />
              <span>Hardware</span>
            </div>
            {expandedSection === 'system' ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          </button>

          {expandedSection === 'system' && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              className="space-y-2"
            >
              <StatCard icon={Cpu} label="CPU" value={systemStats.cpu} color="text-omega-cyan" chartData={cpuHistory} />
              <StatCard icon={Zap} label="GPU" value={systemStats.gpu} color="text-omega-purple" chartData={gpuHistory} />
              <StatCard icon={MemoryStick} label="RAM" value={systemStats.ram} color="text-omega-green" />
              <StatCard icon={Globe} label="NET" value={systemStats.net} color="text-omega-amber" />
            </motion.div>
          )}
        </div>

        {/* ─── Active Models ─── */}
        <div>
          <button
            onClick={() => setExpandedSection(expandedSection === 'agents' ? null : 'agents')}
            className="w-full flex items-center justify-between text-[10px] font-hud tracking-widest text-text-muted uppercase mb-2 mt-2"
          >
            <div className="flex items-center gap-2">
              <Server size={11} />
              <span>Agents</span>
            </div>
            {expandedSection === 'agents' ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          </button>

          {expandedSection === 'agents' && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              className="space-y-2"
            >
              {agents.map((agent, i) => (
                <AgentCard key={i} {...agent} />
              ))}
            </motion.div>
          )}
        </div>

        {/* ─── API Health ─── */}
        <div>
          <button
            onClick={() => setExpandedSection(expandedSection === 'api' ? null : 'api')}
            className="w-full flex items-center justify-between text-[10px] font-hud tracking-widest text-text-muted uppercase mb-2 mt-2"
          >
            <div className="flex items-center gap-2">
              <Database size={11} />
              <span>API Health</span>
            </div>
            {expandedSection === 'api' ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          </button>

          {expandedSection === 'api' && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              className="space-y-1.5"
            >
              {apiEndpoints.map((ep, i) => (
                <div key={i} className="glass-card p-2.5 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-1.5 h-1.5 rounded-full ${
                      ep.status === 'healthy' ? 'bg-omega-green' : 'bg-omega-amber'
                    }`} />
                    <span className="text-[11px] font-mono text-text-secondary">{ep.name}</span>
                  </div>
                  <span className="text-[10px] font-mono text-text-muted">{ep.latency}</span>
                </div>
              ))}
            </motion.div>
          )}
        </div>

        {/* ─── Neural Traces ─── */}
        <div>
          <button
            onClick={() => setExpandedSection(expandedSection === 'traces' ? null : 'traces')}
            className="w-full flex items-center justify-between text-[10px] font-hud tracking-widest text-text-muted uppercase mb-2 mt-2"
          >
            <div className="flex items-center gap-2">
              <Radio size={11} className="text-omega-cyan animate-pulse" />
              <span>Neural Traces</span>
            </div>
            {expandedSection === 'traces' ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          </button>

          {expandedSection === 'traces' && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              className="glass-card p-2.5 max-h-36 overflow-y-auto font-mono text-[9px] text-omega-cyan leading-normal space-y-1"
            >
              {(systemStats.traces || ['Waiting for neural sequence...']).map((trace, i) => (
                <div key={i} className="border-b border-white/5 pb-1 last:border-0 truncate">
                  {trace}
                </div>
              ))}
            </motion.div>
          )}
        </div>

        {/* ─── Tool Executions ─── */}
        <div>
          <button
            onClick={() => setExpandedSection(expandedSection === 'tools' ? null : 'tools')}
            className="w-full flex items-center justify-between text-[10px] font-hud tracking-widest text-text-muted uppercase mb-2 mt-2"
          >
            <div className="flex items-center gap-2">
              <Code2 size={11} className="text-omega-purple" />
              <span>Tool Logs</span>
            </div>
            {expandedSection === 'tools' ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          </button>

          {expandedSection === 'tools' && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              className="space-y-1.5 max-h-36 overflow-y-auto"
            >
              {(!systemStats.tool_logs || systemStats.tool_logs.length === 0) ? (
                <div className="text-[9px] font-mono text-text-muted italic glass-card p-2.5">No tools executed yet.</div>
              ) : (
                systemStats.tool_logs.map((log, i) => (
                  <div key={i} className="glass-card p-2 text-[9px] font-mono">
                    <div className="flex items-center justify-between text-omega-purple">
                      <span className="font-semibold">{log.tool}</span>
                      <span>{log.duration}</span>
                    </div>
                    <div className="text-text-secondary truncate mt-0.5">{log.query}</div>
                  </div>
                ))
              )}
            </motion.div>
          )}
        </div>

        {/* ─── Runtime Info ─── */}
        <div className="mt-4 glass-card p-3">
          <div className="text-[10px] font-hud tracking-widest text-text-muted uppercase mb-3">Runtime</div>
          <div className="space-y-2">
            {[
              { label: 'Uptime', value: systemStats.runtime?.uptime || '24h 32m' },
              { label: 'Threads', value: systemStats.runtime?.threads || '12' },
              { label: 'Memory Pool', value: systemStats.runtime?.memory_pool || '2.4 GB' },
              { label: 'Trace ID', value: systemStats.runtime?.trace_id || 'trc_a8f3e2' },
            ].map((item, i) => (
              <div key={i} className="flex items-center justify-between text-[11px]">
                <span className="text-text-muted">{item.label}</span>
                <span className="font-mono text-text-secondary">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-glass-border text-center">
        <span className="text-[9px] font-mono text-text-muted">
          JARVIS OMEGA v5.0 · Neural Grid
        </span>
      </div>
    </motion.div>
  );
}
