import { AnimatePresence, motion } from 'framer-motion';
import { useStore } from '../store';
import { AlertCircle, CheckCircle, Info, AlertTriangle, X } from 'lucide-react';

const ICONS = {
  info: Info,
  success: CheckCircle,
  warning: AlertTriangle,
  error: AlertCircle,
};

const COLORS = {
  info: 'border-omega-cyan/30 bg-omega-cyan/5 text-omega-cyan',
  success: 'border-omega-green/30 bg-omega-green/5 text-omega-green',
  warning: 'border-omega-amber/30 bg-omega-amber/5 text-omega-amber',
  error: 'border-omega-red/30 bg-omega-red/5 text-omega-red',
};

export default function NotificationOverlay() {
  const notifications = useStore(s => s.notifications);

  return (
    <div className="fixed top-14 right-4 z-[100] space-y-2 pointer-events-none max-w-sm">
      <AnimatePresence>
        {notifications.map(n => {
          const Icon = ICONS[n.type] || ICONS.info;
          const colorClass = COLORS[n.type] || COLORS.info;

          return (
            <motion.div
              key={n.id}
              initial={{ x: 100, opacity: 0, scale: 0.9 }}
              animate={{ x: 0, opacity: 1, scale: 1 }}
              exit={{ x: 100, opacity: 0, scale: 0.9 }}
              transition={{ type: 'spring', damping: 25, stiffness: 400 }}
              className={`glass-card px-4 py-3 flex items-center gap-3 pointer-events-auto border ${colorClass}`}
            >
              <Icon size={16} />
              <span className="text-xs text-text-primary flex-1">{n.message}</span>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
