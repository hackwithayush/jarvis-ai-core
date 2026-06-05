import { useEffect, Component } from 'react';
import { AnimatePresence } from 'framer-motion';
import { useStore } from './store';
import TopBar from './components/TopBar';
import LeftPanel from './components/LeftPanel';
import CenterPanel from './components/CenterPanel';
import RightPanel from './components/RightPanel';
import CommandBar from './components/CommandBar';
import NotificationOverlay from './components/NotificationOverlay';
import AmbientBackground from './components/AmbientBackground';

// ─── Global Error Boundary ───
// Catches any React rendering crash and shows a fallback instead of blank screen
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('JARVIS ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen w-screen flex items-center justify-center bg-omega-bg">
          <div className="text-center max-w-md p-8">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-omega-red/10 border border-omega-red/20 flex items-center justify-center">
              <span className="text-2xl">⚠</span>
            </div>
            <h1 className="text-xl font-display font-semibold text-text-primary mb-2">
              Neural Link Disrupted
            </h1>
            <p className="text-sm text-text-secondary mb-4">
              A component crashed during rendering. This is usually a temporary issue.
            </p>
            <pre className="text-left text-xs text-omega-red bg-omega-surface border border-glass-border rounded-lg p-4 mb-6 overflow-auto max-h-40">
              {this.state.error?.message || 'Unknown error'}
            </pre>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-omega-cyan to-omega-cyan-dim text-omega-bg font-semibold text-sm hover:shadow-[0_0_20px_rgba(0,245,255,0.3)] transition-all"
            >
              Reboot Interface
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

function App() {
  const fetchSystemStats = useStore(s => s.fetchSystemStats);
  const fetchConversations = useStore(s => s.fetchConversations);
  const sidebarOpen = useStore(s => s.sidebarOpen);
  const rightPanelOpen = useStore(s => s.rightPanelOpen);

  useEffect(() => {
    // Initial fetch
    fetchSystemStats();
    fetchConversations();

    // Poll system stats every 2s for a LIVE feel
    const interval = setInterval(fetchSystemStats, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-omega-bg relative">
      {/* Ambient Background Effects */}
      <AmbientBackground />

      {/* Top Navigation Bar */}
      <TopBar />

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Panel — Memory / Conversations */}
        <AnimatePresence mode="wait">
          {sidebarOpen && <LeftPanel />}
        </AnimatePresence>

        {/* Center Panel — Main Chat */}
        <CenterPanel />

        {/* Right Panel — System Monitor */}
        <AnimatePresence mode="wait">
          {rightPanelOpen && <RightPanel />}
        </AnimatePresence>
      </div>

      {/* Bottom Command Bar */}
      <CommandBar />

      {/* Notifications */}
      <NotificationOverlay />
    </div>
  );
}

// Wrap the entire app in ErrorBoundary
export default function AppWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}
