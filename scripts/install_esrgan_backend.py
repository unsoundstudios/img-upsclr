#!/usr/bin/env python3
"""
Install or verify Real-ESRGAN backend for IMG-UPSCLR.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from esrgan_backend import ENV_CACHE, ensure_realesrgan_binary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Real-ESRGAN backend for IMG-UPSCLR.")
    parser.add_argument(
        "--target-dir",
        default="",
        help="Optional install directory for the backend bundle.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.target_dir:
        os.environ[ENV_CACHE] = str(Path(args.target_dir).expanduser().resolve())

    try:
        binary = ensure_realesrgan_binary(auto_install=True)
    except Exception as exc:
        print(f"Real-ESRGAN install failed: {exc}", file=sys.stderr)
        return 1
    print(f"Real-ESRGAN ready: {binary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
