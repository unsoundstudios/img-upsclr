#!/usr/bin/env python3
"""
Smoke test for local macOS/Desktop prerequisites.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import desktop_app  # noqa: F401
from upscaler_core import UpscaleConfig, run_batch


def main() -> int:
    image_path = Path("_images/BitFlanger_UI.png").resolve()
    if not image_path.exists():
        print(f"Missing test image: {image_path}")
        return 2

    input_dir = image_path.parent
    output_dir = Path("_images/upscaled_smoke_macos").resolve()
    config = UpscaleConfig(
        input_dir=input_dir,
        output_dir=output_dir,
        selected_files=[image_path],
        scale=2.0,
        dry_run=True,
        max_images=12,
    )
    results = run_batch(config)
    print(f"Desktop import OK. Core dry-run planned: {len(results)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
