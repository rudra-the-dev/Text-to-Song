"""
Main FastAPI application.

Exposes a small job-queue API in front of an ACE-Step inference server
(running locally or on a rented GPU pod). The frontend polls /jobs/{id}
until status == "done", then plays /jobs/{id}/audio.
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ace_step_service import AceStepService, AceStepError

app = FastAPI(title="Hindi Music Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this once you have a real domain
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- in-memory job store -----------------------------------------------
# Fine for a solo-dev prototype with one server process. If you outgrow
# this (multiple workers, need for persistence/retries) swap this dict
# for Redis + an RQ/Celery worker; the API shape below doesn't change.
JOBS: dict[str, dict] = {}

ace_step = AceStepService()


class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Style/genre/mood description, e.g. 'upbeat Bollywood pop, female vocals, dhol and strings'")
    lyrics: Optional[str] = Field(None, description="Lyrics text. Leave blank for instrumental.")
    duration_seconds: int = Field(60, ge=10, le=240)
    seed: Optional[int] = None
    # No manual LoRA picker: language is detected from the prompt/lyrics
    # (see ace_step_service.infer_language). This lets a caller force it
    # for testing without exposing a toggle in the UI.
    language_override: Optional[Literal["hindi", "english"]] = None


class JobStatus(BaseModel):
    id: str
    status: Literal["queued", "running", "done", "failed"]
    created_at: str
    error: Optional[str] = None
    language_used: Optional[str] = None


@app.post("/api/generate", response_model=JobStatus)
def generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "id": job_id,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "error": None,
        "audio_path": None,
        "language_used": None,
        "request": req.model_dump(),
    }
    background_tasks.add_task(_run_job, job_id, req)
    return JobStatus(**{k: JOBS[job_id][k] for k in ("id", "status", "created_at", "error", "language_used")})


def _run_job(job_id: str, req: GenerateRequest):
    JOBS[job_id]["status"] = "running"
    try:
        audio_path, language_used = ace_step.generate_song(
            prompt=req.prompt,
            lyrics=req.lyrics,
            duration_seconds=req.duration_seconds,
            seed=req.seed,
            job_id=job_id,
            language_override=req.language_override,
        )
        JOBS[job_id]["audio_path"] = audio_path
        JOBS[job_id]["language_used"] = language_used
        JOBS[job_id]["status"] = "done"
    except AceStepError as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)
    except Exception as e:  # noqa: BLE001 - surface unexpected errors to the UI too
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = f"Unexpected error: {e}"


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return JobStatus(**{k: job[k] for k in ("id", "status", "created_at", "error", "language_used")})


@app.get("/api/jobs/{job_id}/audio")
def get_job_audio(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] != "done" or not job["audio_path"]:
        raise HTTPException(409, "Job not finished yet")
    return FileResponse(job["audio_path"], media_type="audio/wav")


@app.get("/api/health")
def health():
    # Kept fast and dependency-free on purpose -- this is what Render's own
    # health check hits to decide if the deploy succeeded. Pinging ACE-Step
    # here would make deploys fail/hang whenever the GPU is scaled to zero
    # (Lightning/Modal cold start), which has nothing to do with whether
    # this backend itself is up. Use /api/ace-step-status to check that
    # separately, on demand.
    return {"ok": True}


@app.get("/api/ace-step-status")
def ace_step_status():
    return {"ace_step_reachable": ace_step.ping()}


# Serve the frontend — resolved relative to this file, not the process's
# cwd. Assumes index.html sits in the same folder as app.py (flat repo
# layout). If you later split into backend/frontend folders, change this
# to parent.parent / "frontend" instead.
FRONTEND_DIR = Path(__file__).resolve().parent
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
