#!/usr/bin/env python3
"""
FastAPI backend for web upscaler jobs.
"""

from __future__ import annotations

import os
import re
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from upscaler_core import (
    ACCEPTED_MODES,
    PUBLIC_MODES,
    SUPPORTED_EXTENSIONS,
    UpscaleConfig,
    iter_images,
    normalize_mode,
    process_file,
)


ROOT_DIR = Path(__file__).resolve().parent
JOBS_DIR = ROOT_DIR / ".web_jobs"
FRONTEND_DIR = ROOT_DIR / "web_frontend"
JOBS_DIR.mkdir(parents=True, exist_ok=True)


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_frame_ancestors_env(default: str = "'none'") -> str:
    raw = os.getenv("FRAME_ANCESTORS", default)
    value = " ".join(raw.split()).strip()
    if not value:
        return default
    if ";" in value or "\n" in value or "\r" in value:
        return default
    return value


MAX_UPLOAD_FILES = int(os.getenv("MAX_UPLOAD_FILES", "12"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "25"))
MAX_FILE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_JOB_AGE_HOURS = int(os.getenv("MAX_JOB_AGE_HOURS", "24"))
ENABLE_API_DOCS = env_flag("ENABLE_API_DOCS", False)

ALLOWED_ORIGINS = parse_csv_env(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000",
)
TRUSTED_HOSTS = parse_csv_env(
    "TRUSTED_HOSTS",
    "localhost,127.0.0.1,testserver",
)
FRAME_ANCESTORS = parse_frame_ancestors_env("'none'")

FILENAME_SANITIZER = re.compile(r"[^A-Za-z0-9._-]+")

app = FastAPI(
    title="IMG-UPSCLR API",
    version="1.0.0",
    docs_url="/docs" if ENABLE_API_DOCS else None,
    redoc_url="/redoc" if ENABLE_API_DOCS else None,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=TRUSTED_HOSTS or ["*"])

allow_any_origin = ALLOWED_ORIGINS == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=not allow_any_origin,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=max(2, min(4, os.cpu_count() or 2)))
jobs_lock = threading.Lock()
jobs: dict[str, dict[str, Any]] = {}


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    if FRAME_ANCESTORS == "'none'":
        response.headers["X-Frame-Options"] = "DENY"
    elif FRAME_ANCESTORS == "'self'":
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    # Current web frontend uses an inline script; keep CSP permissive enough to run.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; "
        f"frame-ancestors {FRAME_ANCESTORS}; "
        "base-uri 'self';"
    )
    return response


def update_job(job_id: str, **fields: Any) -> None:
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            return
        job.update(fields)


def cleanup_old_job_dirs(max_age_hours: int = MAX_JOB_AGE_HOURS) -> None:
    if max_age_hours <= 0:
        return
    cutoff = time.time() - (max_age_hours * 3600)
    for path in JOBS_DIR.iterdir():
        if path.is_dir() and path.stat().st_mtime < cutoff:
            shutil.rmtree(path, ignore_errors=True)


def run_job(job_id: str, config: UpscaleConfig) -> None:
    try:
        images = list(iter_images(config.input_dir))
        if not images:
            update_job(job_id, status="failed", error="No supported images were uploaded.")
            return

        results = []
        for idx, image_path in enumerate(images, start=1):
            result = process_file(image_path, config)
            results.append(result)
            update_job(
                job_id,
                progress=int((idx / len(images)) * 100),
                processed=idx,
                total=len(images),
                results=[asdict(item) for item in results],
            )

        processed = sum(1 for item in results if item.status == "processed")
        failed = sum(1 for item in results if item.status == "failed")
        if failed == len(results):
            first_error = next((item.reason for item in results if item.status == "failed"), None)
            update_job(
                job_id,
                status="failed",
                progress=100,
                failed=failed,
                error=first_error or "All files failed to process.",
                zip_path=None,
            )
            return

        zip_base = config.output_dir.parent / f"{job_id}_result_bundle"
        zip_path = shutil.make_archive(str(zip_base), "zip", root_dir=config.output_dir)
        update_job(
            job_id,
            status="completed",
            progress=100,
            failed=failed,
            error=None,
            processed=processed,
            zip_path=zip_path,
        )
    except Exception as exc:
        update_job(job_id, status="failed", error=str(exc))


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def sanitize_filename(name: str) -> str:
    cleaned = FILENAME_SANITIZER.sub("_", name).strip("._")
    return cleaned[:120] if cleaned else "upload"


async def persist_upload(upload: UploadFile, destination: Path) -> int:
    size = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as buffer:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{upload.filename}: exceeds max size of {MAX_FILE_SIZE_MB} MB per image"
                    ),
                )
            buffer.write(chunk)
    return size


def is_valid_image(path: Path) -> bool:
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except (UnidentifiedImageError, OSError):
        return False


@app.get("/limits")
def limits() -> dict[str, Any]:
    return {
        "max_upload_files": MAX_UPLOAD_FILES,
        "max_file_size_mb": MAX_FILE_SIZE_MB,
        "modes": [
            {"value": "smart", "label": "Smart (Recommended)"},
            {"value": "crisp", "label": "Crisp Assets (Logos/UI/Text)"},
            {"value": "photo", "label": "Photo & Renders (AI)"},
            {"value": "classic", "label": "Classic Script (Original)"},
        ],
    }


@app.post("/jobs")
async def create_job(
    files: list[UploadFile] = File(...),
    scale: float = Form(10.0),
    mode: str = Form("smart"),
    suffix: str = Form("_UPSCALED"),
    max_output_megapixels: float = Form(600.0),
    force_large: str = Form("false"),
    include_already_upscaled: str = Form("false"),
    overwrite: str = Form("false"),
    dry_run: str = Form("false"),
    artwork_ai: str = Form("true"),
) -> dict[str, Any]:
    raw_mode = (mode or "").strip().lower()
    if raw_mode not in ACCEPTED_MODES:
        valid = ", ".join(PUBLIC_MODES)
        raise HTTPException(status_code=400, detail=f"mode must be one of: {valid}")
    resolved_mode = normalize_mode(raw_mode)
    if scale < 1.0 or scale > 30.0:
        raise HTTPException(status_code=400, detail="scale must be between 1.0 and 30.0")
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_UPLOAD_FILES} images per job",
        )

    cleanup_old_job_dirs()

    job_id = uuid.uuid4().hex[:12]
    job_dir = JOBS_DIR / job_id
    input_dir = job_dir / "input"
    output_dir = job_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_files = 0
    skipped_files = 0
    used_names: set[str] = set()

    for idx, upload in enumerate(files, start=1):
        original = Path(upload.filename or "").name
        if not original:
            skipped_files += 1
            continue

        suffix_ext = Path(original).suffix.lower()
        if suffix_ext not in SUPPORTED_EXTENSIONS:
            skipped_files += 1
            continue

        safe_stem = sanitize_filename(Path(original).stem)
        candidate = f"{safe_stem}{suffix_ext}"
        while candidate in used_names:
            candidate = f"{safe_stem}_{idx}{suffix_ext}"
        used_names.add(candidate)

        destination = input_dir / candidate
        try:
            await persist_upload(upload, destination)
        except HTTPException:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

        if not is_valid_image(destination):
            destination.unlink(missing_ok=True)
            skipped_files += 1
            continue

        saved_files += 1

    if saved_files == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "No valid image files uploaded. Supported: png, jpg, jpeg, webp, tif, tiff, bmp"
            ),
        )

    config = UpscaleConfig(
        input_dir=input_dir,
        output_dir=output_dir,
        scale=scale,
        suffix=suffix,
        mode=resolved_mode,
        max_images=MAX_UPLOAD_FILES,
        max_output_megapixels=max_output_megapixels,
        force_large=parse_bool(force_large),
        include_already_upscaled=parse_bool(include_already_upscaled),
        overwrite=parse_bool(overwrite),
        dry_run=parse_bool(dry_run),
        artwork_ai_enabled=parse_bool(artwork_ai),
        artwork_ai_target_scale=16.0,
        auto_install_backend=True,
        esrgan_model_artwork="realesrgan-x4plus",
    )

    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "progress": 0,
            "processed": 0,
            "total": 0,
            "failed": 0,
            "error": None,
            "results": [],
            "zip_path": None,
            "saved_files": saved_files,
            "skipped_files": skipped_files,
            "created_at": int(time.time()),
        }

    update_job(job_id, status="running")
    executor.submit(run_job, job_id, config)
    return {
        "job_id": job_id,
        "saved_files": saved_files,
        "skipped_files": skipped_files,
        "max_upload_files": MAX_UPLOAD_FILES,
    }


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        payload = dict(job)

    payload["download_url"] = (
        f"/jobs/{job_id}/download" if payload.get("status") == "completed" else None
    )
    return payload


@app.get("/jobs/{job_id}/download")
def download_job(job_id: str) -> FileResponse:
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        zip_path = job.get("zip_path")
        status = job.get("status")

    if status != "completed" or not zip_path:
        raise HTTPException(status_code=409, detail="job is not completed yet")

    path = Path(str(zip_path))
    if not path.exists():
        raise HTTPException(status_code=404, detail="result bundle missing")

    return FileResponse(path, media_type="application/zip", filename=f"{job_id}_upscaled.zip")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "max_upload_files": MAX_UPLOAD_FILES,
        "max_file_size_mb": MAX_FILE_SIZE_MB,
    }


if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="app")


@app.get("/")
def root() -> RedirectResponse:
    if FRONTEND_DIR.exists():
        return RedirectResponse(url="/app/")
    return RedirectResponse(url="/health")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("web_api:app", host="0.0.0.0", port=port, reload=False)
