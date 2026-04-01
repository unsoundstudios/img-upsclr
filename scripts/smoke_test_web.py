#!/usr/bin/env python3
"""
Local smoke test for the FastAPI web upscaler flow.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import web_api


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test web upscaler API.")
    parser.add_argument(
        "--image",
        default="_images/BitFlanger_UI.png",
        help="Path to a test image.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument("--scale", type=float, default=2.0)
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use dry-run processing for fast smoke tests.",
    )
    parser.add_argument(
        "--check-limit",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also verify that >12 images is rejected.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    image_path = Path(args.image).resolve()
    if not image_path.exists():
        print(f"Missing test image: {image_path}")
        return 2

    client = TestClient(web_api.app, base_url="http://localhost")
    with image_path.open("rb") as handle:
        response = client.post(
            "/jobs",
            files=[("files", (image_path.name, handle, "image/png"))],
            data={
                "scale": str(args.scale),
                "mode": "auto",
                "dry_run": "true" if args.dry_run else "false",
            },
        )
    if response.status_code != 200:
        print("Job creation failed:", response.status_code, response.text)
        return 1

    payload = response.json()
    job_id = payload["job_id"]
    print(f"Created job {job_id}")

    deadline = time.time() + args.timeout_seconds
    while time.time() < deadline:
        status_response = client.get(f"/jobs/{job_id}")
        if status_response.status_code != 200:
            print("Status fetch failed:", status_response.status_code, status_response.text)
            return 1
        status_payload = status_response.json()
        status = status_payload.get("status")
        if status in {"completed", "failed"}:
            print("Final status:", status)
            print("Progress:", status_payload.get("progress"))
            print("Results:", len(status_payload.get("results", [])))
            print("Download URL:", status_payload.get("download_url"))
            if status != "completed":
                return 1
            break
        time.sleep(0.2)
    else:
        print("Timed out waiting for job completion.")
        return 1

    if args.check_limit:
        handles = []
        files = []
        for i in range(13):
            handle = image_path.open("rb")
            handles.append(handle)
            files.append(("files", (f"limit_{i}.png", handle, "image/png")))
        limit_response = client.post("/jobs", files=files, data={"scale": str(args.scale)})
        for handle in handles:
            handle.close()

        print("Limit check status:", limit_response.status_code)
        if limit_response.status_code != 400:
            print("Expected status 400 for >12 images.")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
