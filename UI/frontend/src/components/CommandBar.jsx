import { useRef, useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store';
import {
  Send, Mic, MicOff, Paperclip, Square,
  Sparkles, Code2, Globe, Image, Wrench,
  ChevronUp, X, Loader2, FileText, CheckCircle2
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
  const [attachment, setAttachment] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
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
          useStore.getState().toggleVoice();
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

  // Upload handler for pasted/selected/dropped files
  const uploadFile = async (file) => {
    if (!file) return;
    const isImg = file.type.startsWith('image/') || /\.(png|jpe?g|webp|gif|bmp|svg)$/i.test(file.name);
    const previewUrl = isImg ? URL.createObjectURL(file) : null;

    setAttachment({
      file,
      previewUrl,
      isImage: isImg,
      isUploading: true,
      imageUrl: null,
      localPath: null,
      fileName: file.name,
      content: '',
      error: null,
    });

    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (data.status === 'success') {
        setAttachment(prev => prev ? ({
          ...prev,
          isUploading: false,
          imageUrl: data.image_url || data.url,
          localPath: data.local_path,
          fileName: data.original_filename || file.name,
          content: data.content || '',
        }) : null);
      } else {
        throw new Error(data.error || 'Upload failed');
      }
    } catch (err) {
      console.error('File upload error:', err);
      setAttachment(prev => prev ? ({
        ...prev,
        isUploading: false,
        error: err.message || 'Upload failed',
      }) : null);
    }
  };

  // Robust Clipboard Image Paste Handler (Ctrl+V / Screenshot / Browser Copy)
  const handlePaste = useCallback((e) => {
    const clipboardData = e.clipboardData || (e.originalEvent && e.originalEvent.clipboardData) || window.clipboardData;
    if (!clipboardData) return;

    let targetFile = null;

    // 1. Check clipboard files (File Explorer Ctrl+C or file paste)
    if (clipboardData.files && clipboardData.files.length > 0) {
      for (let i = 0; i < clipboardData.files.length; i++) {
        const f = clipboardData.files[i];
        if (f.type.startsWith('image/') || /\.(png|jpe?g|webp|gif|bmp)$/i.test(f.name)) {
          targetFile = f;
          break;
        }
      }
    }

    // 2. Check clipboard items (Snipping Tool, Win+Shift+S, Browser image copy)
    if (!targetFile && clipboardData.items && clipboardData.items.length > 0) {
      for (let i = 0; i < clipboardData.items.length; i++) {
        const item = clipboardData.items[i];
        if (item.type.indexOf('image') !== -1 || (item.kind === 'file' && item.type.startsWith('image/'))) {
          const blob = item.getAsFile();
          if (blob) {
            const mime = blob.type || 'image/png';
            const ext = mime.split('/')[1] || 'png';
            targetFile = new File([blob], `screenshot_${Date.now()}.${ext}`, { type: mime });
            break;
          }
        }
      }
    }

    if (targetFile) {
      e.preventDefault();
      e.stopPropagation();
      console.log('📸 Pasted image detected:', targetFile.name, targetFile.size);
      uploadFile(targetFile);
    }
  }, []);

  // Global paste listener: catches paste whether textarea is focused or document is focused
  useEffect(() => {
    const globalPasteListener = (e) => {
      // If user is typing in another input element, don't hijack unless it's an image
      const clipboardData = e.clipboardData || window.clipboardData;
      if (!clipboardData) return;
      
      const hasImage = Array.from(clipboardData.items || []).some(
        it => it.type.indexOf('image') !== -1 || (it.kind === 'file' && it.type.startsWith('image/'))
      ) || Array.from(clipboardData.files || []).some(
        f => f.type.startsWith('image/') || /\.(png|jpe?g|webp|gif|bmp)$/i.test(f.name)
      );

      if (hasImage) {
        handlePaste(e);
      }
    };

    window.addEventListener('paste', globalPasteListener);
    return () => window.removeEventListener('paste', globalPasteListener);
  }, [handlePaste]);

  const clearAttachment = () => {
    if (attachment?.previewUrl) {
      try { URL.revokeObjectURL(attachment.previewUrl); } catch (e) {}
    }
    setAttachment(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSend = () => {
    if (!inputText.trim() && !attachment) return;
    if (attachment?.isUploading) return;

    const text = inputText;
    const fileContext = attachment?.content || '';
    const imageMeta = attachment ? {
      imageUrl: attachment.imageUrl,
      localPath: attachment.localPath,
      previewUrl: attachment.previewUrl,
      fileName: attachment.fileName,
    } : null;

    sendMessage(text, fileContext, imageMeta);
    clearAttachment();

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
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  };

  const handleFileInput = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadFile(file);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  };

  const hasContent = inputText.trim().length > 0 || (attachment && !attachment.isUploading);

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
          {/* Attachment Preview Card */}
          <AnimatePresence>
            {attachment && (
              <motion.div
                initial={{ opacity: 0, y: 8, height: 0 }}
                animate={{ opacity: 1, y: 0, height: 'auto' }}
                exit={{ opacity: 0, y: 8, height: 0 }}
                className="flex items-center gap-3 bg-omega-surface/95 backdrop-blur-md border border-glass-border border-b-0 rounded-t-xl px-4 py-2.5 mb-[-1px] relative z-20 shadow-lg"
              >
                {attachment.isImage && attachment.previewUrl ? (
                  <img
                    src={attachment.previewUrl}
                    alt="Pasted/Uploaded Preview"
                    className="w-11 h-11 rounded-lg object-cover border border-omega-cyan/40 shadow-sm flex-shrink-0"
                  />
                ) : (
                  <div className="w-11 h-11 rounded-lg bg-white/5 border border-glass-border flex items-center justify-center flex-shrink-0 text-omega-cyan">
                    <FileText size={20} />
                  </div>
                )}

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono font-medium text-text-primary truncate max-w-[220px]">
                      {attachment.fileName}
                    </span>
                    {attachment.isUploading ? (
                      <span className="inline-flex items-center gap-1.5 text-[11px] text-omega-cyan font-mono animate-pulse">
                        <Loader2 size={12} className="animate-spin text-omega-cyan" /> Ingesting visual data...
                      </span>
                    ) : attachment.error ? (
                      <span className="inline-flex items-center gap-1 text-[11px] text-omega-red font-mono">
                        ⚠ {attachment.error}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] text-omega-green font-mono">
                        <CheckCircle2 size={12} /> Ready for vision analysis
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] text-text-muted font-mono mt-0.5">
                    {attachment.isImage ? 'Visual Intelligence Node attached · Paste anywhere to replace' : 'Document context ready'}
                  </p>
                </div>

                <button
                  onClick={clearAttachment}
                  className="p-1.5 rounded-lg text-text-muted hover:text-omega-red hover:bg-white/5 transition-colors ml-auto"
                  title="Remove attachment"
                >
                  <X size={15} />
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Input Container */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`
              relative glass rounded-2xl border transition-all duration-300 flex flex-col p-2
              ${isDragging
                ? 'border-omega-cyan shadow-[0_0_30px_rgba(0,245,255,0.2)] bg-omega-cyan/5'
                : hasContent
                ? 'border-omega-cyan/30 shadow-[0_0_25px_rgba(0,245,255,0.08)]'
                : 'border-glass-border hover:border-glass-border-light'
              }
            `}
          >
            <textarea
              ref={textareaRef}
              value={inputText}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              rows={1}
              placeholder={attachment ? "Ask a question about this image, or press Enter to analyze..." : "Message JARVIS... (or paste image Ctrl+V)"}
              className="w-full bg-transparent border-none outline-none text-text-primary font-sans text-sm
                         placeholder:text-text-muted resize-none py-2.5 px-3 max-h-40"
              autoFocus
            />

            {/* Bottom Controls */}
            <div className="flex items-center justify-between px-1 pb-0.5 pt-1">
              <div className="flex items-center gap-0.5">
                {/* File Upload Button */}
                <input
                  type="file"
                  ref={fileInputRef}
                  className="hidden"
                  onChange={handleFileInput}
                  accept="image/*,.pdf,.txt,.py,.js,.html,.json,.csv,.xlsx,.docx"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="p-2 rounded-lg text-text-muted hover:text-omega-cyan hover:bg-white/5 transition-colors"
                  title="Attach image or file"
                >
                  <Paperclip size={15} />
                </button>

                {/* Voice Input */}
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
                  disabled={isStreaming || !hasContent || attachment?.isUploading}
                  className={`w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-300
                    ${hasContent && !isStreaming && !attachment?.isUploading
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
