import { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useStore } from '../store';
import {
  Send, Mic, MicOff, Paperclip, Square,
  Sparkles, Code2, Globe, Image, Wrench,
  ChevronUp
} from 'lucide-react';

const TOOLS = [
  { id: 'web', icon: Globe, label: 'Web Search', color: 'text-omega-green', prefix: '/web ' },
  { id: 'code', icon: Code2, label: 'Code Mode', color: 'text-omega-purple', prefix: '/code ' },
  { id: 'image', icon: Image, label: 'Generate Image', color: 'text-omega-amber', prefix: '/image ' },
  { id: 'tools', icon: Wrench, label: 'System Tools', color: 'text-omega-cyan', prefix: '/tools ' },
];

export default function CommandBar() {
  const inputText = useStore(s => s.inputText);
  const setInputText = useStore(s => s.setInputText);
  const sendMessage = useStore(s => s.sendMessage);
  const isStreaming = useStore(s => s.isStreaming);
  const isVoiceActive = useStore(s => s.isVoiceActive);
  const toggleVoice = useStore(s => s.toggleVoice);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const [showTools, setShowTools] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const recognitionRef = useRef(null);
  
  // Setup Speech Recognition
  useRef(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition && !recognitionRef.current) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.onresult = (event) => {
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          }
        }
        if (finalTranscript) {
           setInputText((prev) => (prev ? prev + ' ' : '') + finalTranscript.trim());
        }
      };
      recognition.onend = () => {
         if (useStore.getState().isVoiceActive) {
            useStore.getState().toggleVoice(); // Auto turn-off when mic stops
         }
      };
      recognitionRef.current = recognition;
    }
  }).current?.();

  // Watch for isVoiceActive to toggle mic
  useRef(() => {
    try {
      if (isVoiceActive) {
        recognitionRef.current?.start();
      } else {
        recognitionRef.current?.stop();
      }
    } catch (e) {
      // Ignore if already started/stopped
    }
  }, [isVoiceActive]);

  const handleSend = () => {
    if (!inputText.trim() && !uploadedFile) return;

    if (uploadedFile) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const fileContent = e.target.result;
        sendMessage(inputText, `[Attached File: ${uploadedFile.name}]\n\n${fileContent}`);
        setUploadedFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
      };
      reader.readAsText(uploadedFile);
    } else {
      sendMessage(inputText);
    }

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e) => {
    setInputText(e.target.value);
    // Auto-resize
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  };

  const handleFile = (e) => {
    const file = e.target.files[0];
    if (file) {
      setUploadedFile(file);
    }
  };

  const hasContent = inputText.trim().length > 0 || uploadedFile;

  return (
    <div className="flex-shrink-0 relative z-40">
      {/* Tools Panel */}
      {showTools && (
        <motion.div
          initial={{ y: 10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 10, opacity: 0 }}
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-full max-w-3xl px-4"
        >
          <div className="glass-card p-3 flex items-center gap-2">
            {TOOLS.map(tool => {
              const Icon = tool.icon;
              return (
                <motion.button
                  key={tool.id}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => {
                    setInputText((prev) => tool.prefix + prev);
                    setShowTools(false);
                    textareaRef.current?.focus();
                  }}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/5 transition-colors"
                >
                  <Icon size={14} className={tool.color} />
                  <span className="text-xs text-text-secondary">{tool.label}</span>
                </motion.button>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* Command Bar */}
      <div className="px-4 pb-4 pt-2">
        <div className="max-w-3xl mx-auto">
          {/* File Preview */}
          {uploadedFile && (
            <div className="flex items-center gap-2 bg-omega-surface border border-glass-border rounded-t-xl px-4 py-2 mb-[-1px]">
              <Paperclip size={12} className="text-omega-cyan" />
              <span className="text-xs font-mono text-text-secondary truncate">{uploadedFile.name}</span>
              <button
                onClick={() => { setUploadedFile(null); fileInputRef.current.value = ''; }}
                className="text-text-muted hover:text-omega-red transition-colors text-xs ml-auto"
              >
                ✕
              </button>
            </div>
          )}

          {/* Input Container */}
          <div className={`
            relative glass rounded-2xl border transition-all duration-300 flex flex-col p-2
            ${hasContent
              ? 'border-omega-cyan/30 shadow-[0_0_25px_rgba(0,245,255,0.08)]'
              : 'border-glass-border hover:border-glass-border-light'
            }
          `}>
            <textarea
              ref={textareaRef}
              value={inputText}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              rows={1}
              placeholder="Message JARVIS..."
              className="w-full bg-transparent border-none outline-none text-text-primary font-sans text-sm
                         placeholder:text-text-muted resize-none py-2.5 px-3 max-h-40"
              autoFocus
            />

            {/* Bottom Controls */}
            <div className="flex items-center justify-between px-1 pb-0.5 pt-1">
              <div className="flex items-center gap-0.5">
                {/* File Upload */}
                <input type="file" ref={fileInputRef} className="hidden" onChange={handleFile} />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="p-2 rounded-lg text-text-muted hover:text-omega-cyan hover:bg-white/5 transition-colors"
                  title="Attach file"
                >
                  <Paperclip size={15} />
                </button>

                {/* Voice */}
                <button
                  onClick={toggleVoice}
                  className={`p-2 rounded-lg transition-all ${
                    isVoiceActive
                      ? 'text-omega-red bg-omega-red/10 animate-pulse'
                      : 'text-text-muted hover:text-omega-cyan hover:bg-white/5'
                  }`}
                  title={isVoiceActive ? 'Stop listening' : 'Voice input'}
                >
                  {isVoiceActive ? <MicOff size={15} /> : <Mic size={15} />}
                </button>

                {/* Tools Toggle */}
                <button
                  onClick={() => setShowTools(!showTools)}
                  className={`p-2 rounded-lg transition-all ${
                    showTools
                      ? 'text-omega-cyan bg-omega-cyan/10'
                      : 'text-text-muted hover:text-omega-cyan hover:bg-white/5'
                  }`}
                  title="AI Tools"
                >
                  <Sparkles size={15} />
                </button>
              </div>

              <div className="flex items-center gap-2">
                {/* Stop Button */}
                {isStreaming && (
                  <motion.button
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg 
                               bg-omega-surface text-text-secondary hover:text-text-primary 
                               hover:bg-omega-surface-light transition-colors text-xs font-medium"
                  >
                    <Square size={10} fill="currentColor" />
                    <span>Stop</span>
                  </motion.button>
                )}

                {/* Send Button */}
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.92 }}
                  onClick={handleSend}
                  disabled={isStreaming || !hasContent}
                  className={`w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-300
                    ${hasContent && !isStreaming
                      ? 'bg-gradient-to-r from-omega-cyan to-omega-cyan-dim text-omega-bg shadow-[0_0_15px_rgba(0,245,255,0.3)]'
                      : 'bg-white/5 text-text-muted cursor-not-allowed'
                    }
                  `}
                >
                  <Send size={14} />
                </motion.button>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="text-center mt-2">
            <span className="text-[9px] font-mono text-text-muted">
              JARVIS OMEGA · Neural Operating System · AI responses may require verification
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
