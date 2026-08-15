"""
Thin client for the ACE-Step inference server.

ACE-Step (https://github.com/ace-step/ACE-Step-1.5) ships its own REST API
you run alongside the model (`python api_server.py` in their repo, or via
their Gradio UI with the API enabled). This module just calls that server
over HTTP so your GPU can live anywhere: your own machine, a RunPod pod,
etc. Point ACE_STEP_BASE_URL at wherever it's running.

Set these in a .env file or your shell before starting the backend:
  ACE_STEP_BASE_URL   e.g. http://127.0.0.1:8019  or  https://xxxx.runpod.net
  ACE_STEP_HINDI_LORA_PATH   path/name of your trained Hindi LoRA (phase 2;
                              leave unset until you've trained one)
"""
import os
import re
import time
import uuid

import requests

ACE_STEP_BASE_URL = os.environ.get("ACE_STEP_BASE_URL", "http://127.0.0.1:8019")
ACE_STEP_API_KEY = os.environ.get("ACE_STEP_API_KEY")  # required for Lightning AI's Autoscale deployments
ACE_STEP_HINDI_LORA_PATH = os.environ.get("ACE_STEP_HINDI_LORA_PATH")  # None until Phase 2
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./generated_audio")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def _auth_headers() -> dict:
    """Bearer auth header, if ACE_STEP_API_KEY is set. Lightning AI's
    Autoscale deployments require this on every request; a self-hosted
    ACE-Step (Colab/Modal) generally won't need it, so this is a no-op
    when the env var is unset."""
    if ACE_STEP_API_KEY:
        return {"Authorization": f"Bearer {ACE_STEP_API_KEY}"}
    return {}

# Devanagari unicode block — catches lyrics actually written in Hindi script.
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


class AceStepError(Exception):
    pass


def infer_language(prompt: str, lyrics: str | None) -> str:
    """
    Decide "hindi" vs "english" (base) from what the user actually wrote.

    Priority:
      1. Lyrics written in Devanagari script -> hindi, no ambiguity.
      2. The prompt explicitly says "hindi" (or "bollywood", a strong
         proxy for it) -> hindi.
      3. The prompt explicitly says "english" -> english.
      4. Default: english/base, since that's what the un-augmented model
         is actually good at (see README on Hindi vocal quality).
    """
    text = f"{prompt} {lyrics or ''}"

    if _DEVANAGARI_RE.search(text):
        return "hindi"

    lowered = text.lower()
    if "hindi" in lowered or "bollywood" in lowered:
        return "hindi"
    if "english" in lowered:
        return "english"

    return "english"


class AceStepService:
    def ping(self) -> bool:
        try:
            r = requests.get(f"{ACE_STEP_BASE_URL}/health", headers=_auth_headers(), timeout=5)
            return r.ok
        except requests.RequestException:
            return False

    def generate_song(
        self,
        prompt: str,
        lyrics: str | None,
        duration_seconds: int,
        seed: int | None,
        job_id: str,
        language_override: str | None = None,
    ) -> tuple[str, str]:
        """
        Calls ACE-Step's /generate endpoint and saves the resulting audio
        to disk. Returns (file_path, language_used) so the caller/UI can
        show which model actually generated the track.

        Language routing: the Hindi LoRA is only used when the prompt/lyrics
        are actually in Hindi (Devanagari script) or explicitly say
        "Hindi"/"Bollywood". Everything else — including no signal either
        way — falls back to base ACE-Step. Pass language_override to skip
        detection (e.g. a user-facing manual override, if you add one later).

        NOTE: the exact payload shape depends on which ACE-Step API build
        you deploy (their api_server.py vs a custom FastAPI wrapper vs
        Gradio's /run/predict). Adjust the `payload` dict below to match
        whatever you stood up on the GPU side — this is the one place
        you'll likely need to tweak after following their README.
        """
        language = language_override or infer_language(prompt, lyrics)

        payload = {
            "prompt": prompt,
            "lyrics": lyrics or "",
            "audio_duration": duration_seconds,
            "seed": seed if seed is not None else -1,
            "infer_step": 27,
            "guidance_scale": 15.0,
        }

        if language == "hindi":
            if not ACE_STEP_HINDI_LORA_PATH:
                raise AceStepError(
                    "This prompt looks like it wants Hindi, but no Hindi LoRA is "
                    "configured yet. Train one (see README, Phase 2) and set "
                    "ACE_STEP_HINDI_LORA_PATH — or rephrase the prompt in English "
                    "to use base ACE-Step for now."
                )
            payload["lora_name_or_path"] = ACE_STEP_HINDI_LORA_PATH

        try:
            resp = requests.post(
                f"{ACE_STEP_BASE_URL}/generate",
                json=payload,
                headers=_auth_headers(),
                timeout=600,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise AceStepError(f"Could not reach ACE-Step server at {ACE_STEP_BASE_URL}: {e}") from e

        # Assumes the server returns raw audio bytes. If your deployment
        # instead returns a JSON with a URL or base64 payload, adjust here.
        out_path = os.path.join(OUTPUT_DIR, f"{job_id}.wav")
        with open(out_path, "wb") as f:
            f.write(resp.content)

        return out_path, language
