import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Cpu, Mic, StopCircle, Globe, Send } from 'lucide-react';

const API_BASE = "http://127.0.0.1:5000"; // Assuming local flask dev server

function App() {
  const [stats, setStats] = useState({ cpu: '0%', ram: '0G', net: '0M', gpu: '0%' });
  const [messages, setMessages] = useState<{role: string, content: string, type?: string}[]>([]);
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    // Polling System Stats
    const fetchStats = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/system/stats`);
        const data = await res.json();
        setStats(data);
      } catch (e) {
        console.error("Stats Error:", e);
      }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Voice Recognition Init
  useEffect(() => {
    if ('webkitSpeechRecognition' in window) {
      const SpeechRecognition = (window as any).webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        sendMessage(transcript);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
  }, []);

  const toggleListen = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      recognitionRef.current?.start();
      setIsListening(true);
    }
  };

  const synthesizeVoice = async (text: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/voice/synthesize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
      });
      if (!res.ok) return;
      const audioBlob = await res.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.play();
    } catch (e) {
      console.error("TTS Error:", e);
    }
  };

  const sendMessage = async (text: string = input) => {
    if (!text.trim()) return;
    setInput('');
    const newMessages = [...messages, { role: 'user', content: text }];
    setMessages(newMessages);
    setIsProcessing(true);

    try {
      // In a real app we'd use Server-Sent Events, but we'll fetch full response here for simplicity
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, mode: "chat" })
      });

      if (!res.ok) throw new Error("Network error");
      
      const reader = res.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      
      let aiResponse = "";
      
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.error) {
                  aiResponse += `\n[SYSTEM ERROR]: ${data.error}`;
                  setMessages([...newMessages, { role: 'assistant', content: aiResponse }]);
                  setIsProcessing(false);
                  return;
                }
                
                if (data.chunk) {
                  if (data.chunk.includes('__STATUS__:')) {
                    // It's a status message, we could show it differently, but for now just show it clearly
                    aiResponse += `\n> ${data.chunk.replace('__STATUS__:', '')}\n`;
                  } else {
                    aiResponse += data.chunk;
                  }
                  setMessages([...newMessages, { role: 'assistant', content: aiResponse }]);
                }
              } catch (e) {}
            }
          }
        }
      }
      
      setIsProcessing(false);
      synthesizeVoice(aiResponse.replace(/<[^>]+>/g, '').replace(/__STATUS__:[^\n]+/g, '')); // Read out text

    } catch (e) {
      setIsProcessing(false);
      setMessages([...newMessages, { role: 'assistant', content: 'Neural Link Error: Failed to connect to core.' }]);
    }
  };

  return (
    <div className="flex h-screen w-full bg-background text-gray-100 font-sans overflow-hidden">
      
      {/* Sidebar / Telemetry */}
      <div className="w-72 border-r border-border bg-surface flex flex-col z-10 hidden md:flex">
        <div className="p-6 border-b border-border flex items-center gap-3">
          <div className="relative flex h-8 w-8 items-center justify-center">
            <div className="absolute inset-0 rounded-full bg-accent/20 blur animate-pulse-slow"></div>
            <Cpu className="text-accent relative z-10 w-5 h-5" />
          </div>
          <h1 className="font-brand font-bold tracking-widest text-lg">JARVIS <span className="text-accent text-xs">OMEGA</span></h1>
        </div>

        <div className="p-6 flex-1 overflow-y-auto custom-scrollbar">
          <h2 className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-4">Live Telemetry</h2>
          
          <div className="space-y-6">
            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-gray-400">CPU CORE</span>
                <span className="text-accent font-mono">{stats.cpu}</span>
              </div>
              <div className="h-1.5 w-full bg-[#101722] rounded-full overflow-hidden">
                <motion.div 
                  className="h-full bg-accent" 
                  initial={{ width: 0 }}
                  animate={{ width: stats.cpu }}
                  transition={{ duration: 1 }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-gray-400">MEMORY (RAM)</span>
                <span className="text-purple-400 font-mono">{stats.ram}</span>
              </div>
              <div className="h-1.5 w-full bg-[#101722] rounded-full overflow-hidden">
                <motion.div 
                  className="h-full bg-purple-400" 
                  initial={{ width: 0 }}
                  animate={{ width: '45%' }} // Simulated based on string
                  transition={{ duration: 1 }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-gray-400">NETWORK IO</span>
                <span className="text-emerald-400 font-mono">{stats.net}</span>
              </div>
              <div className="h-1.5 w-full bg-[#101722] rounded-full overflow-hidden">
                <motion.div 
                  className="h-full bg-emerald-400" 
                  initial={{ width: 0 }}
                  animate={{ width: '60%' }} // Simulated based on string
                  transition={{ duration: 1 }}
                />
              </div>
            </div>
          </div>

          <h2 className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mt-10 mb-4">Active Modules</h2>
          <div className="space-y-2">
            <div className="flex items-center gap-3 text-xs text-gray-300 bg-surfaceHover p-2.5 rounded-lg border border-border">
              <Terminal className="w-4 h-4 text-accent" />
              <span>OS Control Module</span>
              <div className="ml-auto w-1.5 h-1.5 rounded-full bg-accent shadow-[0_0_5px_#00f0ff]"></div>
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-300 bg-surfaceHover p-2.5 rounded-lg border border-border">
              <Globe className="w-4 h-4 text-emerald-400" />
              <span>Live Web Search</span>
              <div className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_5px_#34d399]"></div>
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-300 bg-surfaceHover p-2.5 rounded-lg border border-border">
              <Mic className="w-4 h-4 text-purple-400" />
              <span>Voice Engine (TTS)</span>
              <div className="ml-auto w-1.5 h-1.5 rounded-full bg-purple-400 shadow-[0_0_5px_#a78bfa]"></div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative z-0 bg-background">
        
        {/* Background Grid */}
        <div className="absolute inset-0 opacity-10 pointer-events-none" style={{ backgroundImage: 'linear-gradient(#1a2636 1px, transparent 1px), linear-gradient(90deg, #1a2636 1px, transparent 1px)', backgroundSize: '40px 40px' }}></div>
        
        {/* Top bar mobile */}
        <div className="md:hidden p-4 border-b border-border flex items-center justify-between">
          <h1 className="font-brand font-bold tracking-widest">JARVIS</h1>
          <div className="w-2 h-2 rounded-full bg-accent animate-pulse"></div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6 custom-scrollbar relative z-10">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center opacity-70">
              <div className="relative w-32 h-32 mb-8 flex items-center justify-center">
                <div className="absolute w-24 h-24 rounded-full bg-accent/20 blur-xl animate-pulse-slow"></div>
                <svg className="absolute w-32 h-32 animate-spin-slow opacity-50" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="46" fill="none" stroke="#00f0ff" strokeWidth="1" strokeDasharray="6,4" />
                  <circle cx="50" cy="50" r="38" fill="none" stroke="#00f0ff" strokeWidth="1" strokeDasharray="25,12" />
                </svg>
                <Cpu className="w-10 h-10 text-accent relative z-10 glow-cyan" />
              </div>
              <h2 className="text-xl font-brand text-accent glow-cyan tracking-widest">SYSTEM ONLINE</h2>
              <p className="text-gray-500 font-mono text-xs mt-2 uppercase tracking-widest">Awaiting Command Directive</p>
            </div>
          ) : (
            <AnimatePresence>
              {messages.map((msg, idx) => (
                <motion.div 
                  key={idx} 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[85%] rounded-2xl px-5 py-4 ${
                    msg.role === 'user' 
                      ? 'bg-surfaceHover border border-border text-gray-200' 
                      : 'bg-transparent text-gray-300'
                  }`}>
                    {msg.role === 'assistant' && (
                      <div className="flex items-center gap-2 mb-2 text-accent">
                        <Cpu className="w-4 h-4" />
                        <span className="text-[10px] font-mono tracking-wider uppercase">JARVIS</span>
                      </div>
                    )}
                    
                    {/* Render text with basic Markdown handling or Tool block styles */}
                    <div className="text-sm md:text-base leading-relaxed whitespace-pre-wrap font-sans">
                      {msg.content}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          )}
          
          {isProcessing && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
              <div className="flex items-center gap-2 text-accent/70 px-5">
                <div className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </motion.div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 md:p-6 bg-background/80 backdrop-blur-md border-t border-border relative z-10">
          <div className="max-w-4xl mx-auto flex items-end gap-3 bg-surface border border-border p-2 rounded-2xl focus-within:border-accent/50 transition-colors box-glow">
            
            <button 
              onClick={toggleListen}
              className={`p-3 rounded-xl transition-colors ${isListening ? 'bg-red-500/20 text-red-400' : 'bg-surfaceHover text-gray-400 hover:text-accent'}`}
            >
              {isListening ? <StopCircle className="w-5 h-5 animate-pulse" /> : <Mic className="w-5 h-5" />}
            </button>
            
            <textarea 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
              placeholder="Deploy directive..."
              className="flex-1 bg-transparent border-none text-gray-100 placeholder-gray-600 resize-none outline-none py-3 px-2 max-h-32 custom-scrollbar"
              rows={1}
            />
            
            <button 
              onClick={() => sendMessage()}
              disabled={!input.trim() || isProcessing}
              className="p-3 rounded-xl bg-accent/10 text-accent hover:bg-accent hover:text-black transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
          <div className="text-center mt-3 text-[9px] font-mono text-gray-600 uppercase tracking-widest">
            JARVIS Level 5 Neural Link Active
          </div>
        </div>

      </div>
    </div>
  );
}

export default App;
