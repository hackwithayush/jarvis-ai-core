import { useStore } from '../store';
import { motion } from 'framer-motion';

// ─── Premium CSS Orb (no WebGL dependency — works everywhere) ───
export default function VoiceOrb() {
  const isStreaming = useStore(s => s.isStreaming);
  const isVoiceActive = useStore(s => s.isVoiceActive);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.8, ease: 'easeOut' }}
      className="relative w-44 h-44 flex items-center justify-center"
    >
      {/* Outer ambient glow */}
      <div className={`absolute inset-0 rounded-full transition-all duration-1000 ${
        isStreaming
          ? 'shadow-[0_0_60px_rgba(0,245,255,0.4),0_0_120px_rgba(138,92,255,0.2)]'
          : isVoiceActive
          ? 'shadow-[0_0_50px_rgba(0,245,255,0.35),0_0_100px_rgba(0,245,255,0.15)]'
          : 'shadow-[0_0_30px_rgba(0,245,255,0.2),0_0_60px_rgba(138,92,255,0.08)]'
      }`} />

      {/* Orbital ring 3 (outermost) */}
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
        className="absolute inset-0 rounded-full border border-omega-cyan/10"
      />

      {/* Orbital ring 2 */}
      <motion.div
        animate={{ rotate: -360 }}
        transition={{ duration: 14, repeat: Infinity, ease: 'linear' }}
        className="absolute inset-2 rounded-full border border-omega-purple/20"
      />

      {/* Orbital ring 1 (inner) */}
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
        className="absolute inset-4 rounded-full border border-omega-cyan/30"
      />

      {/* Pulsing core sphere */}
      <motion.div
        animate={{
          scale: isStreaming ? [1, 1.1, 1] : [1, 1.05, 1],
          opacity: [0.8, 1, 0.8],
        }}
        transition={{ duration: isStreaming ? 1.2 : 2.5, repeat: Infinity, ease: 'easeInOut' }}
        className="w-24 h-24 rounded-full relative z-10"
        style={{
          background: `radial-gradient(circle at 35% 35%, 
            rgba(0,245,255,0.5) 0%, 
            rgba(138,92,255,0.35) 40%, 
            rgba(0,245,255,0.15) 70%, 
            rgba(5,8,22,0.8) 100%)`,
          boxShadow: `
            0 0 40px rgba(0,245,255,0.3), 
            0 0 80px rgba(138,92,255,0.15),
            inset 0 0 20px rgba(0,245,255,0.2),
            inset 0 -10px 30px rgba(138,92,255,0.15)
          `,
        }}
      >
        {/* Inner light spot */}
        <div
          className="absolute top-3 left-4 w-6 h-6 rounded-full"
          style={{
            background: 'radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%)',
            filter: 'blur(2px)',
          }}
        />
      </motion.div>

      {/* Pulse ring animation (expanding outward) */}
      {isStreaming && (
        <>
          <motion.div
            animate={{ scale: [1, 2], opacity: [0.4, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
            className="absolute inset-6 rounded-full border border-omega-cyan/40"
          />
          <motion.div
            animate={{ scale: [1, 2], opacity: [0.3, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeOut', delay: 0.7 }}
            className="absolute inset-6 rounded-full border border-omega-purple/30"
          />
        </>
      )}

      {/* Status label */}
      <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 text-center">
        <span className={`text-[9px] font-hud tracking-widest uppercase ${
          isStreaming ? 'text-omega-cyan animate-pulse' : isVoiceActive ? 'text-omega-purple' : 'text-text-muted'
        }`}>
          {isStreaming ? 'Processing' : isVoiceActive ? 'Listening' : 'Ready'}
        </span>
      </div>
    </motion.div>
  );
}
