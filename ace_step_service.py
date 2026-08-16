"""
Thin client for the ACE-Step 1.5 REST API.

This is written against ACE-Step's own documented API (docs/en/API.md in
their repo, https://github.com/ace-step/ACE-Step-1.5), not guessed. The
real flow is async and three calls, not one:

  1. POST /release_task   -> submit a job, get back a task_id
  2. POST /query_result    -> poll with that task_id until status is
                               1 (succeeded) or 2 (failed)
  3. GET  /v1/audio?path=... -> download the actual audio bytes, using
                               the "file" path from the query_result payload

Every response is wrapped: {"data": ..., "code": 200, "error": null, ...}.
Inside query_result's data, "result" is itself a JSON *string* that needs
a second json.loads() -- easy to miss.

Env vars:
  ACE_STEP_BASE_URL       e.g. https://<your-deployment-url>
  ACE_STEP_API_KEY        sent as `Authorization: Bearer <key>` -- required
                           by some hosts (e.g. Lightning AI Autoscale),
                           harmless to leave unset for others
  ACE_STEP_HINDI_LORA_PATH  name/path of your trained Hindi LoRA (Phase 2;
                             leave unset until you've trained one)
"""
import json
import os
import re
import time

import requests

ACE_STEP_BASE_URL = os.environ.get("ACE_STEP_BASE_URL", "http://127.0.0.1:8001")
ACE_STEP_API_KEY = os.environ.get("ACE_STEP_API_KEY")
ACE_STEP_HINDI_LORA_PATH = os.environ.get("ACE_STEP_HINDI_LORA_PATH")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./generated_audio")

os.makedirs(OUTPUT_DIR, exist_ok=True)

POLL_INTERVAL_SECONDS = 5
MAX_WAIT_SECONDS = 600  # matches the server's own documented max duration

# Devanagari unicode block -- catches lyrics actually written in Hindi script.
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


class AceStepError(Exception):
    pass


def _auth_headers() -> dict:
    if ACE_STEP_API_KEY:
        return {"Authorization": f"Bearer {ACE_STEP_API_KEY}"}
    return {}


def _unwrap(resp: requests.Response) -> dict:
    """Every ACE-Step response is {"data": ..., "code": 200, "error": null, ...}.
    Raise on non-200 `code` or a transport-level error status."""
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 200:
        raise AceStepError(body.get("error") or f"ACE-Step returned code {body.get('code')}")
    return body["data"]


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
        Submits a generation job, polls until it's done, downloads the
        result. Returns (file_path, language_used).

        Language routing: the Hindi LoRA is only used when the prompt/lyrics
        are actually in Hindi (Devanagari script) or explicitly say
        "Hindi"/"Bollywood". Everything else falls back to base ACE-Step.
        """
        language = language_override or infer_language(prompt, lyrics)

        if language == "hindi":
            if not ACE_STEP_HINDI_LORA_PATH:
                raise AceStepError(
                    "This prompt looks like it wants Hindi, but no Hindi LoRA is "
                    "configured yet. Train one (see README, Phase 2) and set "
                    "ACE_STEP_HINDI_LORA_PATH — or rephrase the prompt in English "
                    "to use base ACE-Step for now."
                )
            self._ensure_hindi_lora_active()

        payload = {
            "prompt": prompt,
            "lyrics": lyrics or "",
            "audio_duration": duration_seconds,
            "inference_steps": 8,       # turbo model default per ACE-Step's docs
            "guidance_scale": 7.0,      # only affects base model, harmless default otherwise
            "use_random_seed": seed is None,
            "batch_size": 1,            # the API defaults to 2 -- we only want one song per job
        }
        if seed is not None:
            payload["seed"] = seed

        try:
            resp = requests.post(
                f"{ACE_STEP_BASE_URL}/release_task",
                json=payload,
                headers=_auth_headers(),
                timeout=30,  # this call just enqueues the job, should be fast
            )
            data = _unwrap(resp)
        except requests.RequestException as e:
            raise AceStepError(f"Could not reach ACE-Step server at {ACE_STEP_BASE_URL}: {e}") from e

        task_id = data["task_id"]
        audio_path_on_server = self._wait_for_result(task_id)

        # The server may return an already-absolute URL, or a path that
        # needs the base URL prepended -- handle both rather than assuming.
        if audio_path_on_server.startswith("http://") or audio_path_on_server.startswith("https://"):
            download_url = audio_path_on_server
        else:
            download_url = f"{ACE_STEP_BASE_URL}{audio_path_on_server if audio_path_on_server.startswith('/') else '/' + audio_path_on_server}"

        try:
            audio_resp = requests.get(download_url, headers=_auth_headers(), timeout=120)
            audio_resp.raise_for_status()
        except requests.RequestException as e:
            raise AceStepError(
                f"Job finished but downloading the result failed. "
                f"Tried URL: {download_url} (server gave path: {audio_path_on_server!r}). Error: {e}"
            ) from e

        out_path = os.path.join(OUTPUT_DIR, f"{job_id}.wav")
        with open(out_path, "wb") as f:
            f.write(audio_resp.content)

        return out_path, language

    def _wait_for_result(self, task_id: str) -> str:
        """Polls /query_result until the task succeeds or fails. Returns the
        server-side file path (e.g. "/v1/audio?path=...") on success."""
        deadline = time.monotonic() + MAX_WAIT_SECONDS

        while time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL_SECONDS)
            try:
                resp = requests.post(
                    f"{ACE_STEP_BASE_URL}/query_result",
                    json={"task_id_list": [task_id]},
                    headers=_auth_headers(),
                    timeout=30,
                )
                data = _unwrap(resp)
            except requests.RequestException as e:
                # Transient poll failure -- don't give up on a single blip,
                # just try again next cycle (bounded by the overall deadline).
                continue

            entry = data[0]
            status = entry.get("status")

            if status == 1:  # succeeded
                result = json.loads(entry["result"])
                items = result if isinstance(result, list) else [result]
                # In case batching still produces multiple entries, take the
                # first one that actually has a non-empty file path.
                file_path = None
                for item in items:
                    candidate = item.get("file") or item.get("path") or item.get("audio_path") or item.get("url")
                    if candidate:
                        file_path = candidate
                        break
                if not file_path:
                    raise AceStepError(
                        f"Generation succeeded but no file path was found in the result. "
                        f"Raw result: {json.dumps(items)}"
                    )
                return file_path

            if status == 2:  # failed
                result = entry.get("result")
                raise AceStepError(f"ACE-Step generation failed: {result}")

            # status 0 -- still queued/running, keep polling

        raise AceStepError(f"Timed out after {MAX_WAIT_SECONDS}s waiting for generation to finish.")

    def _ensure_hindi_lora_active(self):
        """Loads and enables the Hindi LoRA via ACE-Step's stateful LoRA
        endpoints. Only called when Phase 2 is actually set up
        (ACE_STEP_HINDI_LORA_PATH configured)."""
        try:
            requests.post(
                f"{ACE_STEP_BASE_URL}/v1/lora/load",
                json={"lora_name_or_path": ACE_STEP_HINDI_LORA_PATH},
                headers=_auth_headers(),
                timeout=60,
            ).raise_for_status()
            requests.post(
                f"{ACE_STEP_BASE_URL}/v1/lora/toggle",
                json={"enabled": True},
                headers=_auth_headers(),
                timeout=30,
            ).raise_for_status()
        except requests.RequestException as e:
            raise AceStepError(f"Could not activate the Hindi LoRA: {e}") from e
