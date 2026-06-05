/* ════════════════════════════════════
   JARVIS UI v15.0 — Core Intelligence Logic
   ════════════════════════════════════ */

// ── STATE ──
const state = {
  currentConvId: null,
  conversations: [],
  personality: 'normal',
  isStreaming: false,
  voiceSettings: { rate: 0, pitch: 0, vol: 0 },
  recognition: null,
  micActive: false,
  currentRTab: 'status',
  logs: [],
  isAdmin: false,
  fileContext: null,
  isAnalyzing: false
};

// ── CONFIG ──
const PERSONALITIES = [
  { id: 'normal',    label: 'Normal',    desc: 'Balanced and direct' },
  { id: 'savage',    label: 'Savage',    desc: 'Bold and brutally direct' },
  { id: 'hacker',    label: 'Hacker',    desc: 'Technical, terminal-style' },
  { id: 'assistant', label: 'Assistant', desc: 'Maximally helpful' },
  { id: 'formal',    label: 'Formal',    desc: 'Academic, structured' },
];

const SUGGESTIONS = [
  'What can you do?', 'Search latest AI news', 'Write Python code to sort a list',
  'Generate an image of a futuristic city', 'Explain quantum computing',
];

// ── BOOT ──
document.addEventListener('DOMContentLoaded', () => {
  buildPersonalityPills();
  buildSuggestionChips();
  initVoiceRecognition();
  loadConversations();
  updateHUD();
  renderRightPanel();
  setupTextareaAutoResize();
  addLog('System initialized', 'success');
  addLog('Neural nodes online', 'accent');

  // URL payment feedback
  const p = new URLSearchParams(location.search);
  if (p.get('payment') === 'success') {
    appendMessage('jarvis', 'Transaction confirmed. Neural credits provisioned. Welcome to the elite tier, Operator.');
    history.replaceState({}, '', location.pathname);
    setTimeout(updateHUD, 1500);
  } else if (p.get('payment') === 'cancelled') {
    appendMessage('jarvis', 'Transaction aborted by operator.');
    history.replaceState({}, '', location.pathname);
  }
});

// ── OVERLAYS ──
function openOverlay(id) { document.getElementById(id).classList.remove('hidden'); }
function closeOverlay(id) { document.getElementById(id).classList.add('hidden'); }

document.querySelectorAll('.overlay').forEach(o => {
  o.addEventListener('click', e => { if (e.target === o) o.classList.add('hidden'); });
});

// ── NAV ──
function navClick(el, panel) {
  document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
  el.classList.add('active');
  if (panel === 'gallery') {
    openOverlay('gallery-overlay');
    loadGallery();
  }
}

// ── PERSONALITY ──
function buildPersonalityPills() {
  const c = document.getElementById('mode-pills');
  if (!c) return;
  PERSONALITIES.forEach(p => {
    const el = document.createElement('button');
    el.className = 'mode-pill' + (p.id === state.personality ? ' active' : '');
    el.textContent = p.label;
    el.onclick = () => setPersonality(p.id, el);
    c.appendChild(el);
  });
}

async function setPersonality(id, el) {
  state.personality = id;
  document.querySelectorAll('.mode-pill').forEach(p => p.classList.remove('active'));
  if (el) el.classList.add('active');
  
  // Update settings overlay tiles if they exist
  document.querySelectorAll('.setting-tile').forEach(t => {
    t.classList.toggle('active', t.dataset.mode === id);
  });

  try {
    await fetch('/api/user/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ personality: id }),
    });
    addLog(`Personality set: ${id}`, 'accent');
  } catch (err) {
    addLog('Personality sync failed', 'warn');
  }
}

function buildSettingsTiles() {
  const g = document.getElementById('personality-grid');
  if (!g || g.children.length) return;
  PERSONALITIES.forEach(p => {
    const t = document.createElement('div');
    t.className = 'setting-tile' + (p.id === state.personality ? ' active' : '');
    t.dataset.mode = p.id;
    t.innerHTML = `<div class="setting-tile-name">${p.label}</div><div class="setting-tile-desc">${p.desc}</div>`;
    t.onclick = () => setPersonality(p.id, null);
    g.appendChild(t);
  });
}

// Initial build of settings tiles if they are ready
document.getElementById('settings-overlay').addEventListener('click', (e) => {
    if (e.target.id === 'settings-overlay' || e.target.classList.contains('panel-header-bar')) {
        buildSettingsTiles();
    }
}, { once: true });

// ── SUGGESTIONS ──
function buildSuggestionChips() {
  const c = document.getElementById('suggestion-chips');
  if (!c) return;
  SUGGESTIONS.forEach(s => {
    const chip = document.createElement('button');
    chip.className = 'chip';
    chip.textContent = s;
    chip.onclick = () => { 
        document.getElementById('user-input').value = s; 
        sendMessage(); 
    };
    c.appendChild(chip);
  });
}

// ── HUD ──
async function updateHUD() {
  try {
    const res = await fetch('/api/user/status');
    if (!res.ok) throw new Error();
    const data = await res.json();
    
    document.getElementById('hud-username').textContent = data.username.toUpperCase();
    document.getElementById('user-avatar').textContent = (data.username || 'ST').substring(0, 2).toUpperCase();

    const creditsEl = document.getElementById('hud-credits');
    const badgeEl = document.getElementById('tier-badge');
    const tierTextEl = document.getElementById('hud-tier');

    if (data.is_unlimited) {
      creditsEl.textContent = '⚡ UNLIMITED';
      badgeEl.className = 'tier-badge tier-master';
      badgeEl.textContent = 'MASTER';
      tierTextEl.textContent = 'MASTER OPERATOR';
    } else {
      creditsEl.textContent = `⚡ ${data.credits || 0}`;
      creditsEl.style.color = (data.credits || 0) < 10 ? 'var(--danger)' : 'var(--success)';
      
      if (data.tier === 'PRO') {
          badgeEl.className = 'tier-badge tier-pro';
          badgeEl.textContent = 'PRO';
          tierTextEl.textContent = 'PRO OPERATOR';
      } else {
          badgeEl.className = 'tier-badge tier-free';
          badgeEl.textContent = 'FREE';
          tierTextEl.textContent = 'FREE TIER';
      }
    }

    if (data.is_admin) {
      document.getElementById('admin-nav').style.display = 'flex';
      document.getElementById('logout-btn').style.display = 'flex';
      state.isAdmin = true;
    }
  } catch (err) {
      addLog('HUD Sync failure', 'warn');
  }
}

// ── CONVERSATIONS ──
async function loadConversations() {
  try {
    const res = await fetch('/api/conversations');
    const convs = await res.json();
    state.conversations = convs;
    renderConvList();
  } catch (err) {
      console.error("Failed to load conversations");
  }
}

function renderConvList() {
  const list = document.getElementById('conv-list');
  if (!list) return;
  list.innerHTML = '';
  if (!state.conversations.length) {
    list.innerHTML = '<div style="padding:12px 16px;font-size:11px;color:var(--muted);">No conversations yet</div>';
    return;
  }
  state.conversations.forEach(c => {
    const el = document.createElement('div');
    el.className = 'conv-item' + (c.id === state.currentConvId ? ' active' : '');
    const date = new Date(c.updated_at || Date.now());
    const timeStr = date.toLocaleDateString(undefined, { month:'short', day:'numeric' });
    el.innerHTML = `
      <div class="conv-title">${escHtml(c.title || 'Untitled')}</div>
      <div class="conv-meta">${timeStr} · Active</div>`;
    el.onclick = () => loadConversation(c.id);
    list.appendChild(el);
  });
}

async function loadConversation(id) {
  try {
    const res = await fetch(`/api/conversations/${id}`);
    const data = await res.json();
    state.currentConvId = id;
    hideEmpty();
    document.getElementById('topbar-title').textContent = data.title || 'Conversation';

    const feed = document.getElementById('chat-feed');
    // Remove existing message groups
    [...feed.querySelectorAll('.msg-group')].forEach(m => m.remove());

    (data.history || []).forEach(m => {
      appendMessage(m.role === 'user' ? 'user' : 'jarvis', m.content);
    });
    renderConvList();
    feed.scrollTop = feed.scrollHeight;
  } catch (err) {
      addLog('Failed to retrieve neural memory', 'warn');
  }
}

function newConversation() {
  state.currentConvId = null;
  [...document.getElementById('chat-feed').querySelectorAll('.msg-group')].forEach(m => m.remove());
  document.getElementById('empty-state').style.display = 'flex';
  document.getElementById('topbar-title').textContent = 'New Conversation';
  document.getElementById('user-input').focus();
  renderConvList();
}

// ── CHAT ──
async function sendMessage() {
  const input = document.getElementById('user-input');
  const text = input.value.trim();
  if (!text || state.isStreaming) return;

  hideEmpty();
  appendMessage('user', text);
  input.value = '';
  input.style.height = 'auto';
  updateCharCount(0);

  setThinking(true);
  state.isStreaming = true;
  document.getElementById('send-btn').disabled = true;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
          message: text, 
          conversation_id: state.currentConvId,
          mode: state.personality,
          file_context: state.fileContext ? state.fileContext.snippet : ""
      }),
    });

    if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || `HTTP ${res.status}`);
    }

    setThinking(false);
    const bubble = createMsgBubble('jarvis');
    const feed = document.getElementById('chat-feed');
    feed.scrollTop = feed.scrollHeight;

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let fullContent = '';
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data:')) continue;
        const raw = line.slice(5).trim();
        if (!raw) continue;
        try {
          const p = JSON.parse(raw);
          
          // Unified Object Handler (Direct Multimodal JSON)
          if (p.type === 'image' || p.type === 'video') {
              hideSynthLoader();
              const bubble = createMsgBubble('jarvis');
              const assetUrl = p.url || p.content; 
              if (p.type === 'image') {
                  bubble.innerHTML = `<img src="${assetUrl}" class="neural-img" alt="Neural Synthesis" loading="lazy" onclick="window.open('${assetUrl}')">`;
              } else {
                  bubble.innerHTML = `<video src="${assetUrl}" controls autoplay loop loading="lazy" style="width:100%;border-radius:12px;"></video>`;
              }
              feed.scrollTop = feed.scrollHeight;
              continue;
          }

          if (p.chunk) {
            const chunk = p.chunk;
            
            // Multimodal Yield Handlers (Streaming Markers)
            if (chunk.startsWith('__STATUS__:')) {
                const status = chunk.split('__STATUS__:')[1];
                showSynthLoader(status);
                continue;
            }
            if (chunk.startsWith('__IMAGE__:')) {
                hideSynthLoader();
                const url = chunk.split('__IMAGE__:')[1];
                bubble.innerHTML = `<img src="${url}" class="neural-img" alt="Neural Synthesis" loading="lazy" onclick="window.open('${url}')">`;
                fullContent = ''; 
                continue;
            }
            if (chunk.startsWith('__VIDEO__:')) {
                hideSynthLoader();
                const url = chunk.split('__VIDEO__:')[1];
                bubble.innerHTML = `<video src="${url}" controls autoplay loop loading="lazy"></video>`;
                fullContent = '';
                continue;
            }
            if (chunk.startsWith('__STATUS__:')) {
                const status = chunk.split('__STATUS__:')[1];
                showNeuralStatus(status);
                continue;
            }

            fullContent += chunk;
            bubble.innerHTML = window.marked ? marked.parse(fullContent) : fullContent;
            feed.scrollTop = feed.scrollHeight;
          }
          if (p.done) {
            if (p.conversation_id) state.currentConvId = p.conversation_id;
            addLog('Response complete', 'success');
            if (state.micActive) speakResponse(fullContent);
            setTimeout(() => {
                loadConversations();
                updateHUD();
            }, 500);
          }
          if (p.error) {
            bubble.innerHTML += `<div style="color:var(--danger)">⚠️ Error: ${p.error}</div>`;
            addLog(p.error, 'warn');
          }
        } catch (e) { /* partial JSON */ }
      }
      if (done) break;
    }
  } catch (err) {
    setThinking(false);
    appendMessage('jarvis', `⚠️ Neural link failure: ${err.message}`);
    addLog(err.message, 'warn');
  } finally {
    state.isStreaming = false;
    document.getElementById('send-btn').disabled = false;
  }
}

function hideEmpty() {
  const es = document.getElementById('empty-state');
  if (es) es.style.display = 'none';
}

function createMsgBubble(role) {
  const feed = document.getElementById('chat-feed');
  const group = document.createElement('div');
  group.className = 'msg-group';
  const label = document.createElement('div');
  label.className = `msg-label${role === 'jarvis' ? ' jarvis-label' : ''}`;
  label.textContent = role === 'jarvis' ? 'JARVIS' : 'YOU';
  const bubble = document.createElement('div');
  bubble.className = `msg-bubble ${role}`;
  group.appendChild(label);
  group.appendChild(bubble);
  
  const thinking = document.getElementById('thinking');
  feed.insertBefore(group, thinking);
  return bubble;
}

function appendMessage(role, text) {
  hideEmpty();
  const bubble = createMsgBubble(role);
  bubble.innerHTML = window.marked ? marked.parse(text) : text;
  document.getElementById('chat-feed').scrollTop = 9999;
}

function setThinking(on) {
  const el = document.getElementById('thinking');
  const dot = document.getElementById('status-dot');
  if (el) el.classList.toggle('visible', on);
  if (dot) {
      if (on) { dot.className = 'status-dot thinking'; }
      else { dot.className = 'status-dot' + (navigator.onLine ? '' : ' offline'); }
  }
}

let synthTimeout = null;

function showSynthLoader(text) {
  hideSynthLoader(); // Clean previous
  const feed = document.getElementById('chat-feed');
  const thinking = document.getElementById('thinking');
  const loader = document.createElement('div');
  loader.id = 'neural-synthesis-loader';
  loader.className = 'neural-status-indicator';
  loader.textContent = text || 'Synthesizing neural asset...';
  feed.insertBefore(loader, thinking);
  feed.scrollTop = feed.scrollHeight;
  
  // 8s Timeout Failsafe
  synthTimeout = setTimeout(() => {
    hideSynthLoader();
  }, 8000);
}

function hideSynthLoader() {
  const loader = document.getElementById('neural-synthesis-loader');
  if (loader) loader.remove();
  if (synthTimeout) {
      clearTimeout(synthTimeout);
      synthTimeout = null;
  }
}

function clearChat() {
  [...document.getElementById('chat-feed').querySelectorAll('.msg-group')].forEach(m => m.remove());
  document.getElementById('empty-state').style.display = 'flex';
  state.currentConvId = null;
  document.getElementById('topbar-title').textContent = 'New Conversation';
}

// ── TEXTAREA ──
function setupTextareaAutoResize() {
  const ta = document.getElementById('user-input');
  if (!ta) return;
  ta.addEventListener('input', () => {
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 180) + 'px';
    updateCharCount(ta.value.length);
  });
  ta.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { 
        e.preventDefault(); 
        sendMessage(); 
    }
  });
}

function updateCharCount(n) {
  const el = document.getElementById('char-count');
  if (!el) return;
  el.textContent = `${n} / 4000`;
  el.classList.toggle('warn', n > 3500);
}

// ── FILE INGESTION ──
function triggerUpload() {
  document.getElementById('file-input').click();
}

async function handleFileSelect(input) {
  const file = input.files[0];
  if (!file) return;

  addLog(`Ingesting file: ${file.name}`, 'accent');
  state.isAnalyzing = true;
  showNeuralStatus("Ingesting file content...");

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.status === 'success') {
      state.fileContext = {
        name: file.name,
        url: data.url,
        snippet: data.content_snippet
      };
      renderFilePill();
      addLog("Neural ingestion complete", 'success');
    } else {
      addLog(`Ingestion failure: ${data.error}`, 'warn');
    }
  } catch (err) {
    addLog("Neural link timeout during ingestion", 'warn');
  } finally {
    state.isAnalyzing = false;
    hideNeuralStatus();
    input.value = ''; // Reset input
  }
}

function renderFilePill() {
  const container = document.getElementById('input-area');
  let pill = document.getElementById('active-file-pill');
  if (!pill) {
    pill = document.createElement('div');
    pill.id = 'active-file-pill';
    pill.className = 'upload-pill';
    container.insertBefore(pill, document.getElementById('input-box'));
  }
  pill.innerHTML = `<span>📄 ${state.fileContext.name}</span><button onclick="removeFile()">×</button>`;
}

function removeFile() {
  state.fileContext = null;
  const pill = document.getElementById('active-file-pill');
  if (pill) pill.remove();
  addLog("File context purged", 'muted');
}

function showNeuralStatus(msg) {
  const feed = document.getElementById('chat-feed');
  let s = document.getElementById('neural-status');
  if (!s) {
    s = document.createElement('div');
    s.id = 'neural-status';
    s.className = 'status-indicator';
    feed.insertBefore(s, document.getElementById('thinking'));
  }
  s.textContent = `● ${msg}`;
  s.style.display = 'block';
}

function hideNeuralStatus() {
  const s = document.getElementById('neural-status');
  if (s) s.style.display = 'none';
}

function insertCommand(cmd) {
  const ta = document.getElementById('user-input');
  if (!ta) return;
  if (cmd === '/upload') { triggerUpload(); return; }
  ta.value = cmd + ' ';
  ta.focus();
}

// ── VOICE ──
function initVoiceRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;
  const r = new SR();
  r.continuous = false;
  r.interimResults = false;
  r.lang = 'en-US';
  r.onresult = e => {
    const text = e.results[0][0].transcript;
    document.getElementById('user-input').value = text;
    document.getElementById('mic-btn').classList.remove('mic-active');
    state.micActive = false;
    sendMessage();
  };
  r.onerror = () => {
    document.getElementById('mic-btn').classList.remove('mic-active');
    state.micActive = false;
  };
  r.onend = () => {
    document.getElementById('mic-btn').classList.remove('mic-active');
  };
  state.recognition = r;
}

function toggleMic() {
  if (!state.recognition) { alert('Voice not supported by this browser.'); return; }
  if (state.micActive) {
    state.recognition.stop();
    state.micActive = false;
    document.getElementById('mic-btn').classList.remove('mic-active');
  } else {
    state.recognition.start();
    state.micActive = true;
    document.getElementById('mic-btn').classList.add('mic-active');
  }
}

async function speakResponse(text) {
  if (!text) return;
  try {
      const cleanText = text.replace(/[#*`_~]/g, '').substring(0, 800);
      const r = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            text: cleanText,
            rate: (state.voiceSettings.rate >= 0 ? '+' : '') + state.voiceSettings.rate + '%',
            pitch: (state.voiceSettings.pitch >= 0 ? '+' : '') + state.voiceSettings.pitch + 'Hz'
        }),
      });
      const blob = await r.blob();
      const audio = new Audio(URL.createObjectURL(blob));
      audio.play();
  } catch (err) {}
}

// ── VOICE SETTINGS ──
function updateVoice(param, val) {
  state.voiceSettings[param] = Number(val);
  const n = Number(val);
  const display = (n >= 0 ? '+' : '') + n;
  const suffix = param === 'pitch' ? 'Hz' : '%';
  document.getElementById(`v-${param}-val`).textContent = display + suffix;
  
  // Save to prefs
  fetch('/api/user/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [`voice_${param}`]: display + suffix }),
  });
}

async function testVoice() {
  try {
    const r = await fetch('/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: 'Neural vocal link verified. Calibration optimal.' }),
    });
    const blob = await r.blob();
    new Audio(URL.createObjectURL(blob)).play();
  } catch { alert('Vocal node offline.'); }
}

// ── RIGHT PANEL ──
function switchRTab(tab) {
  document.querySelectorAll('.panel-tab').forEach(t => t.classList.remove('active'));
  document.getElementById(`rtab-${tab}`).classList.add('active');
  state.currentRTab = tab;
  renderRightPanel();
}

function renderRightPanel() {
  const body = document.getElementById('right-panel-body');
  if (!body) return;
  const tab = state.currentRTab;

  if (tab === 'status') {
    body.innerHTML = `
      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-label">SYSTEM STATUS</div>
        </div>
        <div class="stat-card-value success" id="rp-status">ONLINE</div>
        <div style="font-size:11px;color:var(--muted);margin-top:4px;font-family:var(--mono);" id="rp-time"></div>
      </div>
      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-label">ACTIVE MODEL</div>
        </div>
        <div class="stat-card-value accent" style="font-size:13px;">Llama 3.3 70B</div>
        <div class="progress-bar" style="margin-top:8px;"><div class="progress-fill" style="width:95%"></div></div>
      </div>
      <div class="stat-card" style="flex: 1; min-height: 200px;">
        <div class="stat-card-label" style="margin-bottom:8px;">ACTIVITY LOG</div>
        <div id="log-container" style="display:flex;flex-direction:column;gap:0;"></div>
      </div>`;
    renderLogs();
    updateRPTime();
    if (!window.statusInterval) window.statusInterval = setInterval(updateRPTime, 1000);
  }

  if (tab === 'missions') {
    body.innerHTML = `<div style="color:var(--muted);font-size:11px;font-family:var(--mono);">SYNCING MISSIONS...</div>`;
    fetch('/api/missions')
      .then(r => r.json())
      .then(data => {
        if (!data.length) {
            body.innerHTML = `<div style="padding:20px;text-align:center;color:var(--muted);font-size:12px;">No active missions.</div>`;
            return;
        }
        body.innerHTML = data.map(m => `
          <div class="stat-card">
            <div class="stat-card-header">
              <div class="stat-card-label">MISSION ID: ${m.id}</div>
              <div class="stat-card-label">${m.timestamp}</div>
            </div>
            <div style="font-size:12px;font-weight:600;color:var(--text);margin-bottom:8px;">${m.topic}</div>
            <div style="display:flex;justify-content:between;font-size:10px;font-family:var(--mono);margin-bottom:4px;">
                <span style="color:var(--accent)">${m.status.toUpperCase()}</span>
                <span style="flex:1;text-align:right;color:var(--muted);">${m.progress}%</span>
            </div>
            <div class="progress-bar"><div class="progress-fill ${m.status === 'completed' ? 'green' : (m.status === 'failed' ? 'orange' : '')}" style="width:${m.progress}%"></div></div>
          </div>
        `).join('');
      });
  }

  if (tab === 'models') {
    const models = [
      { name: 'Llama 3.1 70B', desc: 'Pro Reasoning', badge: 'PRIME', active: true },
      { name: 'Llama 3.1 8B',  desc: 'Fast Response', badge: 'SPEED', active: false },
      { name: 'Qwen 2.5 7B',   desc: 'Local Engine',  badge: 'LOCAL', active: false },
      { name: 'GPT-4o Mini',   desc: 'External Node', badge: 'API',   active: false },
      { name: 'Mistral 7B',    desc: 'Versatile',     badge: 'LOCAL', active: false },
    ];
    body.innerHTML = models.map(m => `
      <div class="model-card ${m.active ? 'active' : ''}">
        <div class="model-dot"></div>
        <div class="model-info">
          <div class="model-name">${m.name}</div>
          <div class="model-desc">${m.desc}</div>
        </div>
        <div class="model-badge">${m.badge}</div>
      </div>`).join('');
  }

  if (tab === 'tools') {
    const tools = [
      { icon:'🔍', name:'Search', status:'online' },
      { icon:'🖼️', name:'Imaging', status:'online' },
      { icon:'⚡', name:'Python',  status:'online' },
      { icon:'🎤', name:'Vocal',   status:'online' },
      { icon:'📄', name:'Files',   status:'online' },
      { icon:'🤖', name:'Agents',  status:'online' },
    ];
    body.innerHTML = `<div class="tool-grid">${tools.map(t => `
      <div class="tool-node online">
        <div class="tool-node-icon">${t.icon}</div>
        <div class="tool-node-name">${t.name}</div>
        <div class="tool-node-status">● ${t.status}</div>
      </div>`).join('')}</div>`;
  }
}

function updateRPTime() {
  const el = document.getElementById('rp-time');
  if (el) el.textContent = new Date().toLocaleTimeString();
  const s = document.getElementById('rp-status');
  if (s) {
    s.textContent = navigator.onLine ? 'ONLINE' : 'OFFLINE';
    s.className = 'stat-card-value ' + (navigator.onLine ? 'success' : 'danger');
  }
}

// ── ACTIVITY LOG ──
function addLog(msg, type = '') {
  const t = new Date().toLocaleTimeString([], { hour:'2-digit', minute:'2-digit', second:'2-digit' });
  state.logs.unshift({ t, msg, type });
  if (state.logs.length > 30) state.logs.pop();
  renderLogs();
}

function renderLogs() {
  const c = document.getElementById('log-container');
  if (!c) return;
  c.innerHTML = state.logs.slice(0, 10).map(l => `
    <div class="log-entry">
      <span class="log-time">${l.t}</span>
      <span class="log-msg ${l.type}">${escHtml(l.msg)}</span>
    </div>`).join('');
}

// ── GALLERY ──
async function loadGallery() {
  const grid = document.getElementById('gallery-grid');
  grid.innerHTML = '<p style="color:var(--muted);font-size:12px;font-family:var(--mono);">Accessing neural archive...</p>';
  try {
    const res = await fetch('/api/public/gallery');
    const items = await res.json();
    if (!items.length) {
      grid.innerHTML = '<p style="color:var(--muted);font-size:12px;font-family:var(--mono);">No assets generated.</p>';
      return;
    }
    grid.innerHTML = items.map(a => `
      <div class="gallery-item">
        ${a.type === 'video'
          ? `<video src="${a.url}" muted onmouseover="this.play()" onmouseout="this.pause()"></video>`
          : `<img src="${a.url}" alt="${escHtml(a.name)}" loading="lazy">`}
        <div class="gallery-item-overlay">
          <div class="gallery-item-name">${escHtml(a.name)}</div>
          <button class="tool-btn" onclick="copyLink('${a.hash}')">SHARE</button>
        </div>
      </div>`).join('');
  } catch (err) {
    grid.innerHTML = '<p style="color:var(--danger);font-size:12px;font-family:var(--mono);">Registry failure.</p>';
  }
}

function copyLink(hash) {
  navigator.clipboard.writeText(`${location.origin}/s/${hash}`);
  addLog(`Link copied: ${hash}`, 'accent');
}

// ── STORE ──
async function checkout(pack) {
  try {
    const res = await fetch('/api/payment/create-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pack_id: pack }),
    });
    const data = await res.json();
    if (data.url) location.href = data.url;
    else alert('Payment interface failure.');
  } catch (err) { alert('Financial node offline.'); }
}

// ── ADMIN ──
function switchAdminTab(tab) {
  document.getElementById('admin-users-content').style.display = tab === 'users' ? '' : 'none';
  document.getElementById('admin-logs-content').style.display  = tab === 'logs'  ? '' : 'none';
  document.querySelectorAll('[id^="atab-"]').forEach(b => b.classList.remove('active'));
  document.getElementById(`atab-${tab}`).classList.add('active');
  if (tab === 'users') loadAdminUsers();
  if (tab === 'logs')  loadAdminLogs();
}

async function loadAdminUsers() {
  try {
    const res = await fetch('/api/admin/users');
    const users = await res.json();
    const body = document.getElementById('admin-user-list');
    body.innerHTML = users.map(u => `
      <tr>
        <td>${escHtml(u.username)}</td>
        <td>
          <select onchange="updateUser(${u.id},'tier',this.value)">
            <option value="free"      ${u.tier==='free'      ?'selected':''}>Free</option>
            <option value="pro"       ${u.tier==='pro'       ?'selected':''}>Pro</option>
            <option value="unlimited" ${u.tier==='unlimited' ?'selected':''}>Unlimited</option>
          </select>
        </td>
        <td><input type="number" value="${u.credits||0}" onchange="updateUser(${u.id},'credits',this.value)"></td>
        <td><button class="tool-btn" onclick="updateUser(${u.id},'credits',999999)">MAX</button></td>
      </tr>`).join('');
  } catch (err) { alert('Admin protocol failed.'); }
}

async function updateUser(id, field, val) {
  await fetch('/api/admin/user/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: id, [field]: val }),
  });
  setTimeout(loadAdminUsers, 400);
}

async function loadAdminLogs() {
  try {
    const res = await fetch('/api/admin/logs');
    const data = await res.json();
    document.getElementById('log-viewer').textContent = data.logs || 'No system logs found.';
  } catch (err) {}
}

async function logout() {
  await fetch('/api/logout', { method: 'POST' });
  location.reload();
}

// ── UTILS ──
function escHtml(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

window.addEventListener('online',  () => { addLog('Connection restored','success'); setThinking(false); });
window.addEventListener('offline', () => { addLog('Connection lost','warn'); setThinking(false); });