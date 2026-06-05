import { useMemo, useState } from 'react';
import { useStore } from '../store';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, HelpCircle, Layers } from 'lucide-react';

export default function MemoryGraph() {
  const systemStats = useStore(s => s.systemStats);
  const [hoveredNode, setHoveredNode] = useState(null);

  // Parse the memory graph nodes and edges from the real-time telemetry stats
  const graphData = useMemo(() => {
    const defaultGraph = {
      nodes: [
        { id: 'user', label: 'Boss (Ayush)', group: 'user' },
        { id: 'jarvis', label: 'JARVIS OS', group: 'system' }
      ],
      edges: [
        { from: 'user', to: 'jarvis' }
      ]
    };
    return systemStats.memory_graph || defaultGraph;
  }, [systemStats]);

  // Compute futuristic concentric coordinates for deterministic circular layout
  const layout = useMemo(() => {
    const width = 240;
    const height = 240;
    const centerX = width / 2;
    const centerY = height / 2;

    const { nodes, edges } = graphData;
    if (nodes.length <= 2) {
      return {
        nodes: [
          { ...nodes[0], x: centerX - 40, y: centerY },
          { ...nodes[1], x: centerX + 40, y: centerY }
        ],
        edges
      };
    }

    // Place core nodes at the center
    const positionedNodes = [];
    const coreNodes = nodes.filter(n => n.group === 'user' || n.group === 'system');
    const outerNodes = nodes.filter(n => n.group !== 'user' && n.group !== 'system');

    // Central core placement
    coreNodes.forEach((node, idx) => {
      positionedNodes.push({
        ...node,
        x: centerX + (idx === 0 ? -25 : 25),
        y: centerY + (idx === 0 ? -15 : 15)
      });
    });

    // Outer circle placement
    const radius = 70;
    outerNodes.forEach((node, idx) => {
      const angle = (idx / outerNodes.length) * 2 * Math.PI;
      positionedNodes.push({
        ...node,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle)
      });
    });

    // Map edges to coordinate pairs
    const mappedEdges = edges.map(edge => {
      const source = positionedNodes.find(n => n.id === edge.from);
      const target = positionedNodes.find(n => n.id === edge.to);
      return {
        ...edge,
        x1: source ? source.x : centerX,
        y1: source ? source.y : centerY,
        x2: target ? target.x : centerX,
        y2: target ? target.y : centerY
      };
    });

    return { nodes: positionedNodes, edges: mappedEdges };
  }, [graphData]);

  // Color mapping based on HUD neon theme
  const getNodeColor = (group) => {
    switch (group) {
      case 'user': return '#FFFFFF';
      case 'system': return '#00F5FF'; // Cyan
      case 'preference': return '#8A5CFF'; // Purple
      case 'memory': return '#00FFB2'; // Green
      default: return '#FFB800'; // Amber
    }
  };

  return (
    <div className="flex flex-col h-full items-center justify-center p-2 relative">
      {/* Immersive HUD Legend */}
      <div className="flex items-center gap-3 mb-2 text-[8px] font-mono text-text-muted justify-center uppercase tracking-widest">
        <div className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-white" />
          <span>User</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-omega-cyan" />
          <span>Core</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-omega-purple" />
          <span>Prefs</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-omega-green" />
          <span>Facts</span>
        </div>
      </div>

      {/* Futuristic Circular Scanner Background */}
      <div className="relative w-[240px] h-[240px] border border-white/5 rounded-full flex items-center justify-center bg-white/[0.01]">
        {/* Animated Scanning Ring */}
        <div className="absolute inset-2 border border-omega-cyan/10 rounded-full animate-[spin_40s_linear_infinite]" />
        <div className="absolute inset-8 border border-omega-purple/10 border-dashed rounded-full animate-[spin_20s_linear_infinite_reverse]" />
        
        <svg className="w-full h-full relative z-10 overflow-visible">
          {/* Neural Connections (Edges) */}
          {layout.edges.map((edge, idx) => (
            <g key={idx}>
              {/* Glowing background line */}
              <line
                x1={edge.x1}
                y1={edge.y1}
                x2={edge.x2}
                y2={edge.y2}
                stroke={edge.from === 'user' ? '#8A5CFF' : '#00F5FF'}
                strokeWidth={2}
                opacity={0.08}
              />
              {/* Animated pulse stroke */}
              <line
                x1={edge.x1}
                y1={edge.y1}
                x2={edge.x2}
                y2={edge.y2}
                stroke={edge.from === 'user' ? '#8A5CFF' : '#00F5FF'}
                strokeWidth={1}
                strokeDasharray="4 8"
                opacity={0.3}
                className="animate-[dash_2s_linear_infinite]"
              />
            </g>
          ))}

          {/* Neural Memory Nodes */}
          {layout.nodes.map((node) => {
            const color = getNodeColor(node.group);
            const isHovered = hoveredNode?.id === node.id;
            return (
              <g
                key={node.id}
                onMouseEnter={() => setHoveredNode(node)}
                onMouseLeave={() => setHoveredNode(null)}
                className="cursor-pointer"
              >
                {/* Node outer glowing pulse */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={node.group === 'user' || node.group === 'system' ? 8 : 5}
                  fill={color}
                  opacity={isHovered ? 0.4 : 0.15}
                  className="transition-all duration-300"
                />
                {/* Node inner core */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={node.group === 'user' || node.group === 'system' ? 4 : 2.5}
                  fill={color}
                  className="transition-colors duration-300"
                />
                
                {/* Render labels for core nodes permanently, hide outer ones unless hovered */}
                {(node.group === 'user' || node.group === 'system' || isHovered) && (
                  <text
                    x={node.x}
                    y={node.y - 10}
                    textAnchor="middle"
                    fill="#E0E6ED"
                    fontSize="7px"
                    fontFamily="monospace"
                    className="select-none font-semibold"
                  >
                    {node.label}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* Floating Glassmorphic Details Tooltip */}
        <AnimatePresence>
          {hoveredNode && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="absolute bottom-1.5 left-2.5 right-2.5 glass-card border border-glass-border-light p-2 relative z-50 text-left"
            >
              <div className="flex items-center gap-1.5 text-[8px] font-mono font-semibold uppercase text-omega-cyan mb-0.5">
                <Brain size={10} />
                <span>{hoveredNode.group} Fact</span>
              </div>
              <p className="text-[10px] text-text-primary leading-normal font-sans">
                {hoveredNode.details || hoveredNode.label}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
