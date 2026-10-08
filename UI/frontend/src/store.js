import { create } from 'zustand';

const API_BASE = '/api';

export const useStore = create((set, get) => ({
  // ─── UI State ───
  sidebarOpen: true,
  rightPanelOpen: true,
  activeView: 'chat', // chat | settings | agents
  
  // ─── Chat State ───
  messages: [],
  conversations: [],
  currentConvId: null,
  isStreaming: false,
  streamingText: '',
  inputText: '',
  conversationsLoading: false,
  abortController: null,

  // ─── System State ───
  systemStats: { cpu: '0%', gpu: '0%', ram: '0G', net: '0M' },
  neuralStatus: 'online', // online | degraded | offline
  activeModel: 'llama2-uncensored:latest',
  aiMode: 'chat',
  securityState: 'secure',
  internetStatus: 'connected',
  
  // ─── Voice State ───
  isVoiceActive: false,
  voiceLevel: 0,

  // ─── Notifications ───
  notifications: [],

  // ─── Actions ───
  toggleSidebar: () => set(s => ({ sidebarOpen: !s.sidebarOpen })),
  toggleRightPanel: () => set(s => ({ rightPanelOpen: !s.rightPanelOpen })),
  setActiveView: (view) => set({ activeView: view }),
  setInputText: (text) => set({ inputText: text }),
  setAiMode: (mode) => set({ aiMode: mode }),
  setActiveModel: (model) => set({ activeModel: model }),

  abortStream: () => {
    const ctrl = get().abortController;
    if (ctrl) {
      try { ctrl.abort(); } catch (_) {}
    }
    set({ isStreaming: false, abortController: null });
    get().addNotification('Neural stream halted by operator.', 'info');
  },

  addNotification: (message, type = 'info') => {
    const id = Date.now();
    set(s => ({
      notifications: [...s.notifications, { id, message, type }]
    }));
    setTimeout(() => {
      set(s => ({ notifications: s.notifications.filter(n => n.id !== id) }));
    }, 5000);
  },

  // ─── Chat Actions ───
  sendMessage: async (text, fileContext = '', imageMeta = null) => {
    if (get().isStreaming) return;
    const hasImage = Boolean(imageMeta && (imageMeta.imageUrl || imageMeta.localPath));
    if (!text.trim() && !fileContext && !hasImage) return;

    const promptText = text.trim() || (hasImage ? "Analyze this image thoroughly: identify all subjects, layout, transcribed text/code/errors (OCR), and provide key insights." : "");

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: promptText,
      imageUrl: imageMeta?.previewUrl || imageMeta?.imageUrl || null,
      fileName: imageMeta?.fileName || null,
      timestamp: new Date().toISOString(),
    };

    const controller = new AbortController();

    set(s => ({
      messages: [...s.messages, userMsg],
      isStreaming: true,
      streamingText: '',
      inputText: '',
      abortController: controller,
    }));

    const assistantMsg = {
      id: Date.now() + 1,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
    };

    set(s => ({ messages: [...s.messages, assistantMsg] }));

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          message: promptText,
          conversation_id: get().currentConvId,
          file_context: fileContext,
          image_url: imageMeta?.imageUrl || null,
          image_path: imageMeta?.localPath || null,
          mode: get().aiMode,
          model: get().activeModel,
        }),
      });

      // ── Handle non-OK responses (proxy errors, auth failures, credit issues) ──
      if (!response.ok) {
        let errorMsg = `Neural link error (${response.status})`;
        try {
          const errData = await response.json();
          errorMsg = errData.error || errData.message || errorMsg;
        } catch {
          try {
            const errText = await response.text();
            if (errText) errorMsg = errText.slice(0, 200);
          } catch { /* ignore */ }
        }
        set(s => ({
          messages: s.messages.map(m =>
            m.id === assistantMsg.id
              ? { ...m, content: `⚠ ${errorMsg}`, isError: true }
              : m
          ),
        }));
        return;
      }

      // ── Stream SSE response ──
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // keep the incomplete line in buffer

        for (const line of lines) {
          if (line.trim().startsWith('data: ')) {
            try {
              const data = JSON.parse(line.trim().slice(6));
              if (data.error) {
                fullText = `⚠ ${data.error}`;
                set(s => ({
                  messages: s.messages.map(m =>
                    m.id === assistantMsg.id
                      ? { ...m, content: fullText, isError: true }
                      : m
                  ),
                }));
                return;
              }
              if (data.chunk) {
                fullText += data.chunk;
                set(s => ({
                  messages: s.messages.map(m =>
                    m.id === assistantMsg.id
                      ? { ...m, content: fullText }
                      : m
                  ),
                }));
              }
              if (data.done) {
                set({ currentConvId: data.conversation_id });
              }
            } catch (e) { /* partial JSON chunk — skip */ }
          }
        }
      }

      // ── Handle empty response (stream completed but no content) ──
      if (!fullText.trim()) {
        set(s => ({
          messages: s.messages.map(m =>
            m.id === assistantMsg.id
              ? { ...m, content: '⚠ Neural stream returned empty. The AI model may be loading or offline.', isError: true }
              : m
          ),
        }));
      }
    } catch (e) {
      if (e.name === 'AbortError') {
        // Stream aborted gracefully by operator
        return;
      }
      set(s => ({
        messages: s.messages.map(m =>
          m.id === assistantMsg.id
            ? { ...m, content: '⚠ Neural link error. Check that the backend is running.', isError: true }
            : m
        ),
      }));
    } finally {
      set(s => ({
        isStreaming: false,
        abortController: null,
        messages: s.messages.map(m =>
          m.id === assistantMsg.id
            ? { ...m, isStreaming: false }
            : m
        ),
      }));
      // Refresh conversation list after sending a message
      get().fetchConversations();
    }
  },

  newConversation: () => set({
    messages: [],
    currentConvId: null,
    streamingText: '',
  }),

  loadConversation: async (id) => {
    try {
      const res = await fetch(`${API_BASE}/conversations/${id}`);
      if (!res.ok) return;
      const data = await res.json();
      // Backend returns { id, title, history: [...] }
      const history = data.history || data.messages || [];
      set({
        currentConvId: id,
        messages: history.map((m, i) => ({
          id: i,
          role: m.role,
          content: m.content,
          timestamp: m.timestamp || new Date().toISOString(),
        })),
      });
    } catch (e) {
      console.error('Failed to load conversation:', e);
      get().addNotification('Failed to load conversation', 'error');
    }
  },

  deleteConversation: async (id) => {
    try {
      const res = await fetch(`${API_BASE}/conversations/${id}`, { method: 'DELETE' });
      // Even if backend doesn't support DELETE yet, remove from local state
      set(s => ({
        conversations: s.conversations.filter(c => c.id !== id),
        ...(s.currentConvId === id ? { currentConvId: null, messages: [] } : {}),
      }));
      get().addNotification('Thread purged from neural memory', 'success');
    } catch (e) {
      // Remove from local state anyway
      set(s => ({
        conversations: s.conversations.filter(c => c.id !== id),
        ...(s.currentConvId === id ? { currentConvId: null, messages: [] } : {}),
      }));
    }
  },

  fetchConversations: async () => {
    set({ conversationsLoading: true });
    try {
      const res = await fetch(`${API_BASE}/conversations`);
      if (!res.ok) {
        set({ conversationsLoading: false });
        return;
      }
      const text = await res.text();
      if (!text) {
        set({ conversationsLoading: false });
        return;
      }
      const data = JSON.parse(text);
      set({ conversations: Array.isArray(data) ? data : [], conversationsLoading: false });
    } catch (e) {
      // Backend offline or proxy error — fail silently
      set({ conversationsLoading: false });
    }
  },

  // ─── System Actions ───
  fetchSystemStats: async () => {
    try {
      const res = await fetch(`${API_BASE}/system/stats`);
      if (!res.ok) {
        set({ neuralStatus: 'degraded' });
        return;
      }
      const data = await res.json();
      set({ systemStats: data, neuralStatus: 'online' });
    } catch (e) {
      set({ neuralStatus: 'degraded' });
    }
  },

  toggleVoice: () => set(s => ({ isVoiceActive: !s.isVoiceActive })),
}));
