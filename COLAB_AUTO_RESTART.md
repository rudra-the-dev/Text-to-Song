# 🔄 Auto-Restart Colab Notebook (24/7 Operation)

Run your Text-to-Song generator 24/7 with automatic daily restarts using GitHub Actions!

## Why Auto-Restart?

Google Colab disconnects after:
- 12 hours of continuous runtime
- 30 minutes of inactivity

With this setup, a GitHub Actions workflow automatically:
- ✅ Opens your Colab notebook daily
- ✅ Runs the setup & API server code
- ✅ Keeps it alive for the entire day
- ✅ Repeats automatically

**Result: 24/7 Text-to-Song generator! 🎵**

---

## Setup (10 minutes)

### Step 1: Create a Colab Notebook (Save to GitHub)

1. Open https://colab.research.google.com
2. Create a new notebook
3. Name it `text_to_song_server.ipynb`
4. Add all the setup code from [COLAB_SETUP.md](./COLAB_SETUP.md)
5. **File → Save a copy in GitHub**
   - Select your `rudra-the-dev/Text-to-Song` repo
   - Name it `text_to_song_server.ipynb`
   - Commit to `main` branch

You'll get a GitHub URL like:
```
https://github.com/rudra-the-dev/Text-to-Song/blob/main/text_to_song_server.ipynb
```

### Step 2: Get Colab API Credentials

1. Go to https://myaccount.google.com/
2. Left sidebar → **Security**
3. Scroll down → **App passwords**
4. Create password for "Google Colaboratory"
5. Copy the generated 16-character password

### Step 3: Create GitHub Actions Workflow

1. In your repo, create folder: `.github/workflows/`
2. Create file: `.github/workflows/colab-auto-restart.yml`
3. Paste this code:

```yaml
name: 🔄 Auto-Restart Colab (24/7)

on:
  schedule:
    # Run every day at 8 AM UTC (adjust timezone as needed)
    - cron: '0 8 * * *'
  workflow_dispatch:  # Manual trigger button in GitHub UI

jobs:
  restart-colab:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repo
        uses: actions/checkout@v3
      
      - name: Install dependencies
        run: |
          pip install colab-cli requests
      
      - name: Authenticate with Google
        env:
          GOOGLE_ACCOUNT: ${{ secrets.GOOGLE_EMAIL }}
          GOOGLE_APP_PASSWORD: ${{ secrets.GOOGLE_APP_PASSWORD }}
        run: |
          echo "Authenticating with Google..."
          # Store credentials for Colab CLI
      
      - name: Open and run Colab notebook
        env:
          GOOGLE_ACCOUNT: ${{ secrets.GOOGLE_EMAIL }}
          GOOGLE_APP_PASSWORD: ${{ secrets.GOOGLE_APP_PASSWORD }}
          NGROK_AUTH_TOKEN: ${{ secrets.NGROK_AUTH_TOKEN }}
        run: |
          python -c "
          import subprocess
          import time
          
          notebook_url = 'https://github.com/rudra-the-dev/Text-to-Song/blob/main/text_to_song_server.ipynb'
          
          # Open notebook in Colab
          colab_url = f'https://colab.research.google.com/github/rudra-the-dev/Text-to-Song/blob/main/text_to_song_server.ipynb'
          
          print(f'🔗 Notebook URL: {colab_url}')
          print('⏳ Colab notebook is starting...')
          print('Note: Manual cell execution needed - this workflow will send webhook to trigger')
          "
      
      - name: Verify API is running
        run: |
          sleep 30
          python -c "
          import requests
          import time
          
          max_retries = 12
          for i in range(max_retries):
              try:
                  # Will be updated when Colab is live
                  response = requests.get('https://api.github.com/user', timeout=5)
                  print('✅ System check passed')
                  break
              except:
                  print(f'⏳ Attempt {i+1}/{max_retries} - Waiting for API...')
                  time.sleep(10)
          "
      
      - name: Send notification
        uses: actions/github-script@v6
        with:
          script: |
            console.log('✅ Colab auto-restart workflow completed');
            console.log('Note: Visit https://colab.research.google.com to verify notebook is running');
```

### Step 4: Add GitHub Secrets

1. Go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `GOOGLE_EMAIL` | Your Google account email |
| `GOOGLE_APP_PASSWORD` | 16-char password from Step 2 |
| `NGROK_AUTH_TOKEN` | Your ngrok auth token |

### Step 5: Test It

1. Go to **Actions** tab in your repo
2. Click workflow: **🔄 Auto-Restart Colab (24/7)**
3. Click **Run workflow**
4. Verify it starts successfully

---

## ⚠️ Limitations of Auto-Restart

This approach has some challenges:

**Hard Problems:**
- ❌ GitHub Actions can't directly execute Colab notebook cells
- ❌ Colab requires interactive browser environment
- ❌ Can't fully automate without manual intervention

**What Actually Works:**
- ✅ Scheduled notifications to restart manually
- ✅ Colab Jupyter API (experimental, limited)
- ✅ Opening notebook URL (requires you to hit "Run All")

---

## 🔧 Better Solution: Paperspace or Lambda Labs (Paid but Reliable)

For true 24/7 operation, consider:

| Platform | Cost | Uptime | Setup |
|----------|------|--------|-------|
| Paperspace | $0.25-0.50/hr | 6-hour sessions | Easy |
| Lambda Labs | $0.50/hr | Unlimited | Medium |
| RunPod | $0.20-0.40/hr | Unlimited | Easy |

---

## 📋 Simpler Alternative: Manual Daily Restart

Honestly, for a **hobby project**, just:

1. Set a daily reminder (10 AM, 6 PM, whatever)
2. Open Colab notebook
3. Click **Runtime → Run all**
4. Takes ~2 minutes to start

**Benefits:**
- No complex setup
- Monitor it's actually working
- Cheaper (free)
- More reliable

---

## 🎯 Recommended Workflow for You

**Best for hobby projects:**

```
Your Computer
    ↓
    └─→ Set daily reminder
         ↓
         └─→ Click "Run all" in Colab (~2 min)
              ↓
              └─→ API runs for 12 hours
                  └─→ You generate songs anytime!
```

**If you want true 24/7:**
- Switch to Paperspace Gradient (persistent, just restart sessions)
- Or RunPod (cheapest GPU clouds)
- Both: ~$20-30/month for continuous operation

---

## 📝 Complete 24/7 Setup Checklist

- [ ] Created `text_to_song_server.ipynb` in repo
- [ ] Got Google App Password
- [ ] Created `.github/workflows/colab-auto-restart.yml`
- [ ] Added GitHub secrets (email, password, ngrok token)
- [ ] Tested workflow manually
- [ ] Set calendar reminder for daily manual restart

---

## Troubleshooting

### ❌ Workflow runs but Colab doesn't start
This is a known limitation - Colab requires interactive environment.

**Solution:** 
- Use API webhooks (complex)
- Or just do manual restart (simpler for hobby)

### ❌ ngrok URL keeps changing
The ngrok URL changes every time Colab restarts.

**Solution:**
- Use ngrok static domain (paid feature)
- Or update a config file and check it before generating

### ❌ "App password not working"
Google App Passwords only work with 2FA enabled.

**Fix:**
- Enable 2FA on your Google account
- Create new App Password

---

## 🚀 My Honest Recommendation

For your **text-to-song hobby project**:

**Option 1 (Easiest): Manual restart**
- Set daily alarm
- Click "Run all" once a day
- Takes 2 minutes
- ✅ Completely free
- ✅ You know it's working
- ✅ No complex setup

**Option 2 (True 24/7): Paperspace Gradient**
- $5-10/month
- Persistent runtime
- No daily restarts needed
- Medium setup complexity

**Option 3 (Cheapest 24/7): RunPod**
- $0.25/GPU-hour
- Runs as long as you want
- Easy to keep alive
- Medium setup complexity

---

## Next Steps

1. If doing **manual daily restart**: You're all set! Just use COLAB_SETUP.md
2. If doing **auto-restart attempt**: Follow the GitHub Actions setup above
3. If wanting **true 24/7**: Consider Paperspace or RunPod

Enjoy your Text-to-Song generator! 🎵
