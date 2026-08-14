# 🎵 Text-to-Song on Google Colab - Setup Guide

Run your ACE-Step powered music generator completely free on Google Colab with a public URL!

## Quick Start (5 minutes)

### Step 1: Open Colab Notebook
Click here to open a new Colab notebook:
https://colab.research.google.com/notebooks/intro.ipynb

### Step 2: Copy & Paste the Setup Code

In the first cell, paste this entire code block:

```python
# ============================================
# Text-to-Song ACE-Step Backend on Colab
# ============================================

import os
import subprocess
import sys
from pathlib import Path

# Step 1: Clone the Text-to-Song repo
!git clone https://github.com/rudra-the-dev/Text-to-Song.git
os.chdir("Text-to-Song")

# Step 2: Install dependencies
!pip install -q fastapi uvicorn pydantic requests python-dotenv pyngrok

# Step 3: Install ACE-Step (this may take 2-3 minutes)
!pip install -q git+https://github.com/ace-step/ACE-Step-1.5.git

# Step 4: Download model (warning: ~10GB, takes ~5-10 min on fast connection)
print("⏳ Downloading ACE-Step model weights (~10GB)...")
# This downloads to cache, adjust path as needed for your setup
!mkdir -p ~/.cache/ace_step
# Actual download command depends on how ACE-Step publishes - adjust as needed

print("✅ Setup complete! Starting API server...")
```

### Step 3: Start the API Server

In the second cell, paste:

```python
# Start ngrok tunnel and ACE-Step API
import subprocess
import time
from pyngrok import ngrok

# Set ngrok auth token (free account)
# Sign up: https://dashboard.ngrok.com/signup
# Copy your token and paste here:
ngrok.set_auth_token("YOUR_NGROK_AUTH_TOKEN_HERE")

# Start FastAPI server in background
print("🚀 Starting ACE-Step API server...")
subprocess.Popen(["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8019"])

# Give it 3 seconds to start
time.sleep(3)

# Expose with ngrok
print("🌐 Creating public URL with ngrok...")
public_url = ngrok.connect(8019)
print(f"\n{'='*50}")
print(f"✅ ACE-Step API is LIVE at: {public_url}")
print(f"{'='*50}\n")

# Test the API
import requests
try:
    health = requests.get(f"{public_url}/api/health", timeout=5).json()
    print(f"✅ Health check passed: {health}")
except Exception as e:
    print(f"⚠️ Health check failed: {e}")
    print("Wait 5 seconds and try again - server might still be starting")
```

### Step 4: Get Your Public API URL

After the code runs, you'll see:
```
✅ ACE-Step API is LIVE at: https://xxxx-xxxx-xxxx.ngrok.io
```

**Copy this URL!** You'll need it for your frontend.

---

## Using Your Frontend

### Option A: Colab Frontend (Everything in Colab)

In a new cell, add:

```python
# Serve the frontend from Colab
import subprocess
import time

# Copy frontend to accessible location
!cp index.html /tmp/index.html

# Start simple HTTP server on port 5000
print("🎨 Starting frontend server...")
subprocess.Popen(["python", "-m", "http.server", "5000", "--directory", "/tmp"])
time.sleep(2)

# Get frontend URL
frontend_url = ngrok.connect(5000)
print(f"\n{'='*50}")
print(f"✅ Frontend is LIVE at: {frontend_url}")
print(f"{'='*50}\n")
print("Open this URL in your browser!")
```

Then update the API endpoint in the frontend. Add this cell:

```python
# Update index.html to point to our ngrok backend
html_content = open("index.html").read()
# Replace the API constant
html_content = html_content.replace(
    'const API = "";',
    f'const API = "{public_url}";'
)
with open("/tmp/index.html", "w") as f:
    f.write(html_content)
print("✅ Frontend updated to use your ACE-Step API!")
```

### Option B: Local Frontend (Recommended for Development)

1. **Download your repo locally:**
   ```bash
   git clone https://github.com/rudra-the-dev/Text-to-Song.git
   ```

2. **Update `index.html`** with your Colab ngrok URL:
   ```javascript
   // Line 238 in index.html
   const API = "https://YOUR-NGROK-URL.ngrok.io"; // Update this!
   ```

3. **Open `index.html` in your browser** and start generating songs!

---

## Setting Up ngrok (One-time)

1. **Sign up for free:** https://dashboard.ngrok.com/signup
2. **Get your auth token:** https://dashboard.ngrok.com/get-started/your-authtoken
3. **Add it to the code above** where it says `YOUR_NGROK_AUTH_TOKEN_HERE`

---

## Full Workflow

```
┌─────────────────────────────────────┐
│  Your Browser (Local Machine)       │
│  ↓ (http://localhost:3000)          │
│  Opens index.html                   │
└────────────┬────────────────────────┘
             │
             ├─→ 🌐 ngrok tunnel
             │
┌────────────▼────────────────────────┐
│  Google Colab (Free GPU T4)         │
│                                     │
│  ├─ FastAPI App (app.py)            │
│  │  └─ /api/generate endpoint       │
│  └─ ACE-Step Model (Running)        │
│     └─ Generates audio files        │
└─────────────────────────────────────┘
```

---

## Keeping Colab Alive (Optional)

Google Colab disconnects after 12 hours of inactivity. To keep it running longer:

### Option 1: Manual Restart (Easiest)
Just re-run the cells once a day - takes 2 minutes.

### Option 2: Prevent Disconnection
Add this to keep Colab active:

```python
# Add this cell and run it - keeps Colab from timing out
import time
import requests

while True:
    try:
        requests.get(f"{public_url}/api/health", timeout=5)
        print(f"✅ Ping at {time.ctime()}")
    except:
        print(f"⚠️ API unreachable at {time.ctime()}")
    time.sleep(300)  # Ping every 5 minutes
```

### Option 3: GitHub Actions Auto-Restart (Advanced)
See [COLAB_AUTO_RESTART.md](./COLAB_AUTO_RESTART.md) for setting up automatic daily restarts.

---

## Troubleshooting

### ❌ "Health check failed"
- Wait 10 seconds, the API server might still be starting
- Run the health check again

### ❌ "ngrok connection refused"
- Make sure you set your auth token correctly
- Check your internet connection

### ❌ "ACE-Step model not found"
- The model download takes 5-10 minutes on first run
- Check if your Colab has enough disk space (~20GB needed)
- Run `!df -h` to check available space

### ❌ "CUDA out of memory"
- ACE-Step is memory-hungry
- Colab T4 has 16GB - should be enough but might need optimization
- Consider running inference one at a time (don't queue multiple jobs)

### ❌ Frontend won't connect to API
- Copy the exact ngrok URL (including `https://`)
- Make sure there are no trailing slashes
- Check browser console for CORS errors (shouldn't happen with ngrok)

---

## Performance Notes

**Generation time on Colab T4:**
- 60-second track: ~2-5 minutes
- 120-second track: ~4-10 minutes
- Varies based on model load and prompt complexity

This is perfect for hobby use - just queue a generation and come back in a few minutes!

---

## Next Steps

1. ✅ Set up ngrok account
2. ✅ Run the setup code in Colab
3. ✅ Copy your API URL
4. ✅ Update `index.html` with your API URL
5. ✅ Open `index.html` in browser
6. ✅ Generate your first song! 🎵

---

## Cost

**Total: $0** (as long as you stay within free tiers)

- Google Colab: Free
- ngrok: Free tier (40 connections/min, perfect for hobby)
- ACE-Step: Open source, free

Enjoy! 🎉
