#!/usr/bin/env python3
"""
Real-ESRGAN backend setup and invocation helpers.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path

from PIL import Image


REAL_ESRGAN_URLS: dict[str, list[str]] = {
    "darwin": [
        "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-macos.zip"
    ],
    "linux": [
        "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip"
    ],
    "windows": [
        "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip"
    ],
}

DEFAULT_CACHE_ROOT = Path.home() / ".img-upsclr" / "vendor" / "realesrgan"
ENV_BIN = "REAL_ESRGAN_BIN"
ENV_CACHE = "IMG_UPSCLR_ESRGAN_DIR"

_INSTALL_LOCK = threading.Lock()


def _system_key() -> str:
    system = platform.system().lower()
    if system.startswith("darwin"):
        return "darwin"
    if system.startswith("windows"):
        return "windows"
    if system.startswith("linux"):
        return "linux"
    raise RuntimeError(f"Unsupported platform for Real-ESRGAN install: {platform.system()}")


def _binary_name() -> str:
    return "realesrgan-ncnn-vulkan.exe" if _system_key() == "windows" else "realesrgan-ncnn-vulkan"


def _cache_root() -> Path:
    override = os.getenv(ENV_CACHE, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    try:
        DEFAULT_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
        return DEFAULT_CACHE_ROOT
    except OSError:
        fallback = (Path.cwd() / ".cache" / "realesrgan").resolve()
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _find_binary_in(root: Path) -> Path | None:
    if not root.exists():
        return None
    name = _binary_name()
    direct = root / name
    if direct.exists() and direct.is_file():
        return direct
    for candidate in root.rglob(name):
        if candidate.is_file():
            return candidate
    return None


def resolve_backend_binary() -> Path | None:
    env_bin = os.getenv(ENV_BIN, "").strip()
    if env_bin:
        candidate = Path(env_bin).expanduser().resolve()
        if candidate.exists() and candidate.is_file():
            return candidate

    path_hit = shutil.which(_binary_name())
    if path_hit:
        return Path(path_hit).resolve()

    # Bundled PyInstaller app resources.
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        frozen_candidates = [
            exe_dir / "realesrgan",
            exe_dir.parent / "Resources" / "realesrgan",
            exe_dir.parent / "Resources",
            exe_dir.parent / "Frameworks" / "realesrgan",
            exe_dir.parent / "Frameworks",
        ]
        for item in frozen_candidates:
            hit = _find_binary_in(item)
            if hit:
                return hit

    return _find_binary_in(_cache_root())


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "IMG-UPSCLR/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response, dest.open("wb") as output:
        shutil.copyfileobj(response, output)


def _extract_archive(archive: Path, target: Path) -> None:
    with zipfile.ZipFile(archive, "r") as zf:
        zf.extractall(target)


def _install_from_release_urls(root: Path) -> Path:
    system = _system_key()
    urls = REAL_ESRGAN_URLS.get(system, [])
    if not urls:
        raise RuntimeError(f"No Real-ESRGAN download URL configured for platform: {system}")

    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="img-upsclr-esrgan-") as tmp:
        temp_dir = Path(tmp)
        archive_path = temp_dir / "realesrgan.zip"
        extract_dir = temp_dir / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)

        last_error = "Unknown error"
        for url in urls:
            try:
                _download(url, archive_path)
                _extract_archive(archive_path, extract_dir)
                binary = _find_binary_in(extract_dir)
                if not binary:
                    raise RuntimeError("Downloaded archive did not include realesrgan binary")
                source_root = binary.parent
                if root.exists():
                    shutil.rmtree(root, ignore_errors=True)
                shutil.copytree(source_root, root, dirs_exist_ok=True)
                installed = _find_binary_in(root)
                if not installed:
                    raise RuntimeError("Install completed but binary not found")
                if _system_key() != "windows":
                    installed.chmod(
                        installed.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                    )
                return installed
            except Exception as exc:
                last_error = str(exc)

        raise RuntimeError(
            "Unable to install Real-ESRGAN automatically. "
            "Check internet access and try again. "
            f"Last error: {last_error}"
        )


def ensure_realesrgan_binary(auto_install: bool = True) -> Path:
    with _INSTALL_LOCK:
        existing = resolve_backend_binary()
        if existing:
            return existing
        if not auto_install:
            raise RuntimeError(
                "Real-ESRGAN backend is not installed. "
                "Set REAL_ESRGAN_BIN or run scripts/install_esrgan_backend.py."
            )
        return _install_from_release_urls(_cache_root())


def resolve_model_dir(executable: Path) -> Path:
    candidates: list[Path] = [executable.parent / "models"]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend(
            [
                exe_dir.parent / "Resources" / "realesrgan" / "models",
                exe_dir.parent / "Resources" / "models",
                exe_dir.parent / "Frameworks" / "realesrgan" / "models",
            ]
        )
    candidates.append(_cache_root() / "models")

    for item in candidates:
        if item.exists() and item.is_dir():
            return item
    return executable.parent / "models"


def resolve_model_name(preferred: str | None, model_dir: Path) -> str:
    if preferred:
        param = model_dir / f"{preferred}.param"
        bin_file = model_dir / f"{preferred}.bin"
        if param.exists() and bin_file.exists():
            return preferred

    for candidate in ("realesrgan-x4plus", "realesrgan-x4plus-anime", "realesr-animevideov3"):
        if (model_dir / f"{candidate}.param").exists() and (model_dir / f"{candidate}.bin").exists():
            return candidate
    raise RuntimeError("No Real-ESRGAN model files found in backend/models directory.")


def decompose_scale(scale: float) -> list[int]:
    # Kept for backward compatibility with older callers. Current engine path
    # uses a single ESRGAN pass to avoid quality drift from repeated inference.
    return [4] if scale > 1.0 else []


def model_native_scale(model_name: str) -> int:
    match = re.search(r"x(\d+)", model_name)
    if match:
        return max(1, int(match.group(1)))
    return 4


def planned_native_passes(scale: float, native_scale: int, max_native_passes: int) -> int:
    if scale <= 1.0:
        return 0
    passes = 1
    while passes < max(1, max_native_passes) and (native_scale**passes) < scale:
        passes += 1
    return passes


def run_realesrgan_chain(
    source_rgb: Image.Image,
    target_size: tuple[int, int],
    model: str | None,
    auto_install: bool = True,
    max_native_passes: int = 2,
) -> Image.Image:
    executable = ensure_realesrgan_binary(auto_install=auto_install)
    model_dir = resolve_model_dir(executable)
    resolved_model = resolve_model_name(model, model_dir)

    scale = target_size[0] / max(1, source_rgb.size[0])
    if scale <= 1.0:
        return source_rgb.resize(target_size, resample=Image.Resampling.LANCZOS)
    native_scale = model_native_scale(resolved_model)
    pass_count = planned_native_passes(scale, native_scale=native_scale, max_native_passes=max_native_passes)

    with tempfile.TemporaryDirectory(prefix="img-upsclr-run-") as tmp:
        tmp_dir = Path(tmp)
        src = tmp_dir / "input.png"
        source_rgb.save(src, format="PNG")
        current_input = src

        for step in range(1, pass_count + 1):
            current_output = tmp_dir / f"output_step_{step}.png"
            command = [
                str(executable),
                "-i",
                str(current_input),
                "-o",
                str(current_output),
                "-n",
                resolved_model,
                "-s",
                str(native_scale),
                "-f",
                "png",
                "-m",
                str(model_dir),
            ]
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
            if process.returncode != 0:
                detail = process.stderr.strip() or process.stdout.strip() or "unknown error"
                lowered = detail.lower()
                if "invalid gpu device" in lowered or "vk_error_incompatible_driver" in lowered:
                    detail = (
                        "No compatible Vulkan/Metal GPU detected for Real-ESRGAN ncnn backend. "
                        "Install GPU drivers/Metal support."
                    )
                raise RuntimeError(f"Real-ESRGAN failed: {detail}")
            current_input = current_output

        with Image.open(current_input) as upscaled:
            final_rgb = upscaled.convert("RGB")

    if final_rgb.size != target_size:
        final_rgb = final_rgb.resize(target_size, resample=Image.Resampling.LANCZOS)
    return final_rgb
