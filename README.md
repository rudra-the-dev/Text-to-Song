# Sur — AI song generator (ACE-Step backend)

## How it fits together

```
Browser (frontend/index.html)
        |
        v
FastAPI backend (backend/app.py)  <-- job queue, serves the frontend
        |
        v
ACE-Step inference server  <-- runs on a GPU (yours, or a rented pod)
```

The backend never runs the model itself — it just calls ACE-Step's own
API over HTTP. That's what lets you swap GPUs without touching the app.

## Phase 1: get base generation working

1. **Get a GPU.** Easiest path while you're testing: rent one.
   - [RunPod](https://runpod.io) → deploy a pod with a CUDA template (RTX
     3090/4090 or A10, ~20GB VRAM covers the non-quantized model
     comfortably; 12GB works with offload+quantization).
   - SSH in, clone ACE-Step: `git clone https://github.com/ace-step/ACE-Step-1.5`
   - Follow their README to install deps and download model weights.
   - Start their API server (check their repo for the exact entrypoint —
     it's `api_server.py` or the Gradio app with API mode enabled,
     depending on which branch you pull). Expose the port RunPod gives
     you (usually via their proxy URL, `https://<pod-id>-8019.proxy.runpod.net`).

2. **Point the backend at it.**
   ```bash
   cd backend
   python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   export ACE_STEP_BASE_URL="https://<your-pod-url>"
   uvicorn app:app --reload --port 8000
   ```

3. Open `http://localhost:8000` — that's the frontend, served by the
   same backend. Type a prompt, hit Generate.

4. **The one thing you'll likely need to adjust:** `backend/ace_step_service.py`
   builds a request payload for ACE-Step's `/generate` endpoint. The
   exact field names depend on which version/fork of their API server
   you deployed — open their repo's `api_server.py` (or equivalent) and
   match the payload shape and response format (raw audio bytes vs. a
   JSON with a file URL). That file is the only place you should need
   to touch for this.

## Phase 2: train and wire in a Hindi LoRA

There's no off-the-shelf Hindi LoRA for ACE-Step — the official repo
only ships a Chinese rap one as an example, and Hindi vocal quality on
the base model is a known weak spot. You train your own using their
built-in LoRA trainer:

1. Collect ~20-50 Hindi/Bollywood-style songs (vocals + instrumental
   mix) with rough style/lyric tags — this is your training set. Mind
   licensing; there are open Indian-classical/folk datasets on Hugging
   Face and academic sources you can start with, or your own
   recordings.
2. On the same GPU pod, use ACE-Step's `LoRA Training` tab in their
   Gradio UI (one-click) or their CLI trainer (`Side-Step`, mentioned
   in their README) — point it at your dataset. Expect roughly
   30-90 minutes on a single A100-class GPU for a small set, based on
   how their own example LoRAs were trained.
3. This produces a LoRA weights file. Set:
   ```bash
   export ACE_STEP_HINDI_LORA_PATH="/path/or/name/of/your/lora"
   ```
4. Restart the backend. The "Hindi LoRA" button in the UI will now
   route generation through it.

## Notes

- The job store in `app.py` is an in-memory dict — fine solo, but it
  resets if the server restarts and won't work across multiple worker
  processes. If you deploy this for others to use, swap it for
  Redis + RQ/Celery; the API routes don't need to change.
- CORS is wide open (`allow_origins=["*"]`) for local dev — lock this
  down before putting it on a public domain.
