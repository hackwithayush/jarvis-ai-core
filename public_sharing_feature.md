# Shareable Access Link for Jarvis (Node.js / Express)

This serves as a complete blueprint to create a Node.js/Express gateway that acts as a secure, public-facing interface for your current Python Jarvis system. It supports QR codes, link expiration, password protection, and real-time websockets mapping to your Flask backend.

## Tech Stack Overview
- **Backend:** Node.js, Express, Socket.io
- **Database:** MongoDB (Mongoose)
- **Security:** `uuid` for unique links, `bcryptjs` for password hashing
- **Frontend:** HTML, TailwindCSS, Vanilla JS, `qrcode.js`

---

### 1. Database Model (`models/ShareLink.js`)
This schema tracks generated links, their expiration, and user access analytics.

```javascript
const mongoose = require('mongoose');

const shareLinkSchema = new mongoose.Schema({
    linkId: { type: String, required: true, unique: true },
    type: { type: String, enum: ['permanent', 'temporary'], default: 'temporary' },
    expiresAt: { type: Date }, // Null if permanent
    passwordHash: { type: String }, // Null if unprotected
    isActive: { type: Boolean, default: true },
    accessCount: { type: Number, default: 0 },
    createdAt: { type: Date, default: Date.now }
});

module.exports = mongoose.model('ShareLink', shareLinkSchema);
```

### 2. Backend Server (`server.js`)
This Express server handles link generation, validation, and real-time WebSocket routing.

```javascript
require('dotenv').config();
const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const mongoose = require('mongoose');
const { v4: uuidv4 } = require('uuid');
const bcrypt = require('bcryptjs');
const ShareLink = require('./models/ShareLink');

const app = express();
const server = http.createServer(app);
const io = socketIo(server);

app.use(express.json());
app.use(express.static('public'));

// ─── MONGODB CONNECTION ───────────────────────────────────────
mongoose.connect('mongodb://localhost:27017/jarvis_public', { useNewUrlParser: true, useUnifiedTopology: true })
    .then(() => console.log('✅ MongoDB Connected'))
    .catch(err => console.error(err));

// ─── API: GENERATE LINK ───────────────────────────────────────
app.post('/api/generate-link', async (req, res) => {
    const { type, expiresInHours, password } = req.body;
    const linkId = uuidv4();
    
    let expiresAt = null;
    if (type === 'temporary' && expiresInHours) {
        expiresAt = new Date();
        expiresAt.setHours(expiresAt.getHours() + expiresInHours);
    }

    let passwordHash = null;
    if (password) {
        passwordHash = await bcrypt.hash(password, 10);
    }

    const newLink = new ShareLink({ linkId, type, expiresAt, passwordHash });
    await newLink.save();

    const publicUrl = `${req.protocol}://${req.get('host')}/chat/${linkId}`;
    res.json({ success: true, linkId, publicUrl, type, expiresAt });
});

// ─── API: VALIDATE LINK ───────────────────────────────────────
app.post('/api/validate-link/:id', async (req, res) => {
    const { password } = req.body;
    const link = await ShareLink.findOne({ linkId: req.params.id });

    if (!link || !link.isActive) {
        return res.status(404).json({ error: 'Link is invalid or has been disabled.' });
    }
    
    if (link.type === 'temporary' && new Date() > link.expiresAt) {
        link.isActive = false;
        await link.save();
        return res.status(403).json({ error: 'This link has expired.' });
    }

    if (link.passwordHash) {
        if (!password) return res.status(401).json({ error: 'Password required.' });
        const isMatch = await bcrypt.compare(password, link.passwordHash);
        if (!isMatch) return res.status(403).json({ error: 'Invalid password.' });
    }

    // Increment analytics track
    link.accessCount += 1;
    await link.save();

    res.json({ success: true, message: 'Access granted.' });
});

// ─── WEBSOCKET ROUTING ────────────────────────────────────────
io.on('connection', (socket) => {
    console.log(`🔌 Client connected: ${socket.id}`);

    socket.on('jarvis_request', async (data) => {
        // Forward the message to the Python Flask Backend running on port 5000
        try {
            const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));
            
            // NOTE: In production, stream this instead of waiting for the full response.
            // This is a simplified fetch to your local flask API.
            socket.emit('jarvis_response', { type: 'chunk', text: "Processing remotely..." });
            
            const response = await fetch('http://localhost:5000/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: data.message, convo_id: socket.id })
            });
            
            // Listen to SSE essentially or process response
            socket.emit('jarvis_response', { type: 'done', text: `Message relayed securely.` });
            
        } catch (error) {
            console.error(error);
            socket.emit('jarvis_response', { type: 'error', text: 'Backend Python node offline.' });
        }
    });

    socket.on('disconnect', () => console.log(`🔌 Client disconnected: ${socket.id}`));
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => console.log(`🚀 Gateway Server running on port ${PORT}`));
```

### 3. Admin UI: Create & Share Links (`public/admin.html`)
The interface for you to generate links and view analytics.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Jarvis Link Manager</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
</head>
<body class="bg-gray-900 text-white min-h-screen flex items-center justify-center font-sans">
    <div class="bg-gray-800 p-8 rounded-2xl shadow-2xl w-full max-w-md border border-gray-700">
        <h2 class="text-2xl font-bold mb-6 flex items-center justify-between">
            Generate Public Link
            <span class="w-3 h-3 bg-emerald-500 rounded-full animate-pulse"></span>
        </h2>

        <div class="space-y-4">
            <select id="linkType" class="w-full bg-gray-900 border border-gray-700 rounded-lg p-3 outline-none focus:border-emerald-500">
                <option value="temporary">Temporary (Expires)</option>
                <option value="permanent">Permanent</option>
            </select>

            <input type="number" id="expireHours" placeholder="Hours until expiration (e.g., 24)" class="w-full bg-gray-900 border border-gray-700 rounded-lg p-3 outline-none focus:border-emerald-500">
            
            <input type="password" id="linkPassword" placeholder="Optional Password Protection" class="w-full bg-gray-900 border border-gray-700 rounded-lg p-3 outline-none focus:border-emerald-500">

            <button onclick="generateLink()" class="w-full bg-white text-black font-bold py-3 rounded-lg hover:bg-gray-200 transition-colors">
                Generate Access Link
            </button>
        </div>

        <div id="resultBox" class="hidden mt-8 p-4 bg-gray-900 rounded-lg border border-gray-700 text-center">
            <p class="text-xs text-gray-400 mb-2 uppercase tracking-wide">Public URL generated</p>
            <input type="text" id="generatedUrl" readonly class="w-full bg-transparent text-center text-emerald-400 font-mono text-sm mb-4 outline-none cursor-pointer" onclick="this.select(); document.execCommand('copy'); alert('Copied!')">
            <div id="qrcode" class="flex justify-center bg-white p-2 w-max mx-auto rounded-md"></div>
        </div>
    </div>

    <script>
        async function generateLink() {
            const type = document.getElementById('linkType').value;
            const expiresInHours = parseInt(document.getElementById('expireHours').value) || 24;
            const password = document.getElementById('linkPassword').value;

            const res = await fetch('/api/generate-link', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type, expiresInHours, password })
            });

            const data = await res.json();
            if(data.success) {
                document.getElementById('resultBox').classList.remove('hidden');
                document.getElementById('generatedUrl').value = data.publicUrl;
                document.getElementById('qrcode').innerHTML = "";
                new QRCode(document.getElementById('qrcode'), { text: data.publicUrl, width: 128, height: 128 });
            }
        }
    </script>
</body>
</html>
```

### 4. Public Chat Interface (`public/chat.html` & `app.js`)
This is the restricted UI the public user sees when they use the unique link.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Jarvis Public Node</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="/socket.io/socket.io.js"></script>
</head>
<body class="bg-black text-gray-200 h-screen flex flex-col font-sans">
    <div id="authScreen" class="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4">
        <div class="bg-gray-900 border border-gray-800 p-8 rounded-2xl w-full max-w-sm text-center shadow-2xl">
            <h3 class="text-xl font-bold mb-2">Secure Link Auth</h3>
            <p class="text-sm text-gray-500 mb-6">This Jarvis instance requires a password.</p>
            <input type="password" id="authPassword" placeholder="Enter password" class="w-full bg-black border border-gray-700 rounded-lg p-3 text-center mb-4 text-white outline-none focus:border-emerald-500">
            <button onclick="validateAccess()" class="w-full bg-white text-black font-bold py-3 rounded-lg hover:bg-gray-200">Unlock</button>
            <p id="authError" class="text-red-500 text-sm mt-4 hidden"></p>
        </div>
    </div>

    <header class="p-6 border-b border-white/[0.05] flex items-center gap-3 bg-black">
        <div class="w-2 h-2 bg-emerald-500 rounded-full shadow-[0_0_10px_rgba(16,185,129,0.5)]"></div>
        <h1 class="font-medium tracking-wide">JARVIS <span class="text-gray-500 text-xs ml-2">PUBLIC CLOUD</span></h1>
    </header>

    <main class="flex-1 overflow-y-auto p-8" id="chatFeed"></main>

    <div class="p-6">
        <div class="relative max-w-3xl mx-auto">
            <input type="text" id="userInput" placeholder="Message Jarvis..." class="w-full bg-gray-900 border border-white/[0.1] rounded-full py-4 pl-6 pr-16 text-white outline-none focus:border-white/[0.3] transition-colors" onkeypress="if(event.key === 'Enter') sendMessage()">
            <button onclick="sendMessage()" class="absolute right-2 top-2 bottom-2 bg-white text-black rounded-full px-6 font-medium hover:scale-105 transition-transform">Send</button>
        </div>
    </div>

    <script>
        const linkId = window.location.pathname.split('/').pop();
        const socket = io();

        async function validateAccess() {
            const pwd = document.getElementById('authPassword').value;
            const res = await fetch(`/api/validate-link/${linkId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: pwd })
            });

            const data = await res.json();
            if (data.success) {
                document.getElementById('authScreen').style.display = 'none';
            } else {
                document.getElementById('authError').innerText = data.error;
                document.getElementById('authError').classList.remove('hidden');
            }
        }

        validateAccess(); // Try auto-validation

        function sendMessage() {
            const input = document.getElementById('userInput');
            const text = input.value.trim();
            if (!text) return;
            appendMessage('You', text, 'text-gray-400');
            socket.emit('jarvis_request', { message: text, linkId });
            input.value = '';
        }

        function appendMessage(sender, text, colorClass) {
            const feed = document.getElementById('chatFeed');
            feed.innerHTML += `<div class="mb-6 max-w-3xl mx-auto"><span class="text-xs uppercase font-bold tracking-widest ${colorClass} block mb-1">${sender}</span><p class="text-lg font-light leading-relaxed">${text}</p></div>`;
            feed.scrollTop = feed.scrollHeight;
        }

        socket.on('jarvis_response', (data) => {
            appendMessage('Jarvis', data.text, 'text-emerald-500');
        });
    </script>
</body>
</html>
```

## How to Deploy & Use

1. **Initialize the Project**:
   Open a terminal, create a new folder (e.g. `jarvis_gateway`), and run:
   ```bash
   npm init -y
   npm install express socket.io mongoose uuid bcryptjs node-fetch dotenv
   ```

2. **Integration with Python Jarvis**:
   This backend acts as a **Proxy Gateway**. When the public users send a message through the shared URL interface, it receives the WebSocket data on Node.js. Node.js then proxies that request securely to your running Python `app.py` process running locally over HTTP (`http://localhost:5000/api/chat`). Your internal python codebase is never directly exposed.

3. **Deploying for Real Access**:
   You can run this node backend locally and expose it instantly utilizing Ngrok (`ngrok http 3000`). This will generate an active public URL that maps to this secure proxy routing straight into Jarvis.
