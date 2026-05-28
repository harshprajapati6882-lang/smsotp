# TempSMS — Free Real SMS Verification Tool

A **real Python Flask backend** that scrapes live phone numbers and SMS messages
from free public sites server-side. No API key. No money. No fake numbers.

---

## 🚀 Deploy to Render.com (Free Hosting)

### Step 1 — Upload to GitHub
1. Go to [github.com](https://github.com) → Sign in → Click **New Repository**
2. Name it `tempsms` → Click **Create Repository**
3. Upload all files from this folder to the repo (drag & drop or use GitHub Desktop)

### Step 2 — Deploy on Render (Free)
1. Go to [render.com](https://render.com) → Sign up free
2. Click **New +** → **Web Service**
3. Connect your GitHub account → Select the `tempsms` repo
4. Render auto-detects settings from `render.yaml`
5. Click **Create Web Service**
6. Wait ~2 minutes → Your site is live at `https://tempsms-xxxx.onrender.com` 🎉

---

## 💻 Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py

# Open in browser
# http://localhost:5000
```

---

## 📁 File Structure

```
tempsms-app/
├── app.py              ← Python Flask backend (scraper)
├── requirements.txt    ← Python dependencies
├── render.yaml         ← Render deployment config
├── Procfile            ← Process file for hosting
├── templates/
│   └── index.html      ← Frontend UI (glass design)
└── README.md           ← This file
```

---

## ⚙️ How It Works

1. **Frontend** calls `/api/numbers` → server scrapes live numbers from receive-smss.com, quackr.io, receivesms.co
2. User picks a number → **Frontend** calls `/api/messages/{number}` → server scrapes that number's inbox
3. Messages + OTP codes returned as JSON → displayed in the UI

---

## ⚠️ Notes

- These are **public shared numbers** — anyone can see messages
- Do NOT use for banking, primary email, or sensitive accounts
- Numbers refresh every 5 minutes automatically
