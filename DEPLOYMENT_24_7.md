# 🚀 JARVIS AI — 24/7 Autonomous Cloud Deployment Guide (100% Free / Zero Subscription)

This guide walks you through deploying your **JARVIS AI** assistant to a **100% free cloud server** with **zero subscription costs and no credit card required**. 

Once deployed, JARVIS will run **24 hours a day, 7 days a week**, handling Web and Telegram requests, sending security breach alerts, and dispatching morning executive reports to your Gmail—even when your laptop is completely powered off.

---

## 🏗️ Architecture Overview

```
                      +---------------------------------------+
                      |         100% FREE CLOUD HOST          |
                      |   (Render.com / Hugging Face / Koyeb) |
                      |                                       |
                      |   [jarvis_guardian.py Supervisor]    |
                      |     ├── Node A: Web Gateway (app.py)  |
                      |     └── Node B: Telegram Bot (tg.py)  |
                      +-------------------+-------------------+
                                          |
                   +----------------------+----------------------+
                   |                                             |
                   v                                             v
       [cron-job.org / UptimeRobot]                   [Ayush Chaudhary]
      (Free 10-min ping to /health)               Telegram Bot + Gmail Inbox
       Keeps free server awake 24/7               Instant alerts & daily report
```

---

## ⚡ Option 1 (Recommended): Render.com (3-Minute Setup)

Render offers a generous **100% free Web Service** tier with direct GitHub repository integration.

### Step 1: Push Local Code to GitHub
Open your terminal in `c:\AI\jarvis-ai` and run:
```bash
git push origin main
```
*(If prompted by Windows Git Credential Manager, click Sign in with Browser).*

### Step 2: Create Free Web Service on Render
1. Go to [https://dashboard.render.com](https://dashboard.render.com) and log in with your GitHub account.
2. Click **New +** $\rightarrow$ **Web Service** (or **Blueprint**).
3. Connect your repository: `hackwithayush/jarvis-ai-core`.
4. Configure the settings:
   - **Name**: `jarvis-ai-core`
   - **Region**: Choose closest to you (e.g., `Singapore` or `Oregon`)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python jarvis_guardian.py`
   - **Instance Type**: **Free** ($0/month)

### Step 3: Configure Environment Variables
Under the **Environment Variables** tab in Render, add the following keys from your `.env`:

| Key | Description |
| :--- | :--- |
| `SERVER_MODE` | `true` |
| `PYTHONUNBUFFERED` | `1` |
| `BOT_TOKEN` | Your Telegram Bot Token (`7780404840:...`) |
| `GEMINI_API_KEY` | Your Google Gemini API Key |
| `GROQ_API_KEY` | Your Groq API Key |
| `OPENROUTER_API_KEY` | Your OpenRouter API Key |
| `GMAIL_SENDER` | `ayushchaudhary22790@gmail.com` |
| `GMAIL_APP_PASSWORD` | Your 16-character App Password (`uidmbtqgdjczestf`) |
| `ALERT_RECIPIENT_EMAIL` | `ayushchaudhary22790@gmail.com` |
| `EMAIL_ALERTS_ENABLED` | `true` |
| `GMAIL_SMTP_SERVER` | `smtp.gmail.com` |
| `GMAIL_SMTP_PORT` | `587` |
| `DAILY_REPORT_HOUR` | `8` |

5. Click **Create Web Service**. Render will build and deploy JARVIS automatically!

### Step 4: Keep Alive 24/7 (Prevent Free Sleep)
Free Render services sleep after 15 minutes of inactivity. To keep JARVIS awake 24/7 forever for $0:
1. Go to [https://cron-job.org](https://cron-job.org) or [https://uptimerobot.com](https://uptimerobot.com) (both are 100% free).
2. Create a free HTTP ping monitor:
   - **URL**: `https://<your-render-subdomain>.onrender.com/health`
   - **Interval**: Every **10 minutes**
3. **Result**: Your server will receive an automated heartbeat every 10 minutes, keeping JARVIS and your Telegram bot awake 24/7 without spending a penny!

---

## ⚡ Option 2: Hugging Face Spaces (Docker 2 vCPU / 16GB RAM)

Hugging Face Spaces provides **free Docker hosting** with 16GB RAM and **zero sleeping** on basic CPU tier.

1. Go to [https://huggingface.co/spaces](https://huggingface.co/spaces) and click **Create new Space**.
2. Select:
   - **Space SDK**: **Docker** $\rightarrow$ **Blank**
   - **Space Hardware**: **CPU basic • 2 vCPU • 16 GB • Free**
3. Under **Settings** $\rightarrow$ **Variables and secrets**, add your environment variables (`BOT_TOKEN`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `GMAIL_APP_PASSWORD`, etc.).
4. Connect or push your repository. Hugging Face will build the included `Dockerfile` and run JARVIS 24/7 continuously.

---

## ⚡ Option 3: Koyeb (Eco Free Tier)

1. Go to [https://app.koyeb.com](https://app.koyeb.com) (sign up with GitHub).
2. Click **Create Service** $\rightarrow$ select GitHub $\rightarrow$ `hackwithayush/jarvis-ai-core`.
3. Choose **Free Eco Tier** (512 MB RAM, $0/month).
4. Koyeb automatically reads `Dockerfile` or `Procfile` (`web: python jarvis_guardian.py`).
5. Add your environment variables in the Koyeb dashboard and click **Deploy**.

---

## 🔄 Coordination: Laptop vs. Cloud

- **When Laptop is ON**: If you want to run JARVIS locally on your laptop, double-click `run_jarvis_24_7.bat`.
- **When Laptop is SHUT DOWN**: The cloud instance continues running autonomously in the background. Telegram commands, intrusion detection, and morning email reports work non-stop.
- **Stopping Local Node**: Run `stop_jarvis_24_7.bat` on your PC before leaving or turning off your laptop so only the cloud node handles Telegram traffic.
