# ⚡ Quick Setup with ngrok URL

Your ACE-Step inference server is configured and ready to go!

## Current Configuration

```
🔗 ACE-Step GPU Server: https://swan-resale-fester.ngrok-free.dev/
📝 Configuration: .env (auto-created)
```

## How to Run

### Step 1: Install Dependencies
```bash
cd Text-to-Song
pip install -r requirements.txt
```

### Step 2: Start the Backend
```bash
# The .env file is already configured with your ngrok URL
python -m uvicorn app:app --reload --port 8000
```

### Step 3: Open in Browser
Navigate to: **http://localhost:8000**

## What's Configured

✅ **ACE_STEP_BASE_URL** = `https://swan-resale-fester.ngrok-free.dev/`
- This tells your backend where your GPU model server is running
- The backend will call this URL to generate audio

## Optional Configurations

### If you have a trained Hindi LoRA (Phase 2):
Edit `.env` and add:
```
ACE_STEP_HINDI_LORA_PATH=/path/or/name/of/your/lora
```

### Custom audio output directory:
Edit `.env` and add:
```
OUTPUT_DIR=./my_custom_audio_folder
```

## Testing the Setup

```bash
# Check if ACE-Step server is reachable
curl https://swan-resale-fester.ngrok-free.dev/health
```

## Troubleshooting

### ❌ "Connection refused" or "Cannot reach ACE-Step server"
- Verify your ngrok server is running and the URL is correct
- Check: `curl https://swan-resale-fester.ngrok-free.dev/health`

### ❌ "Module not found" errors
- Make sure you ran: `pip install -r requirements.txt`
- Check Python version (3.9+ recommended)

### ❌ Port 8000 already in use
```bash
# Use a different port
python -m uvicorn app:app --reload --port 8001
```

## File Layout
```
Text-to-Song/
├── .env                    ← Auto-configured with your ngrok URL
├── .env.example            ← Template for reference
├── app.py                  ← FastAPI backend
├── ace_step_service.py     ← ACE-Step client (uses ACE_STEP_BASE_URL)
├── index.html              ← Web frontend
├── requirements.txt        ← Python dependencies
├── README.md               ← Original documentation
├── COLAB_SETUP.md          ← Google Colab setup guide
└── SETUP_INSTRUCTIONS.md   ← This file
```

## Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Start backend: `python -m uvicorn app:app --reload --port 8000`
3. ✅ Open browser: `http://localhost:8000`
4. ✅ Generate your first song! 🎵

---

**For more details, see:**
- `README.md` - Architecture & Phase 2 (Hindi LoRA training)
- `COLAB_SETUP.md` - Running on Google Colab for free
- `.env.example` - All available configuration options
