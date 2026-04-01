#!/usr/bin/env python3
"""
Batch upscale images in a folder with quality-focused defaults.

Examples:
  python3 upscale_images.py
  python3 upscale_images.py --scale 10 --input . --output upscaled_10x
  python3 upscale_images.py --dry-run
  python3 upscale_images.py --force-large --include-already-upscaled
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from upscaler_core import ACCEPTED_MODES, UpscaleConfig, print_summary, run_batch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upscale images in a folder with production-ready smart defaults for mixed asset types."
    )
    parser.add_argument("--input", default=".", help="Input folder. Defaults to current folder.")
    parser.add_argument(
        "--output",
        default="upscaled_10x",
        help="Output folder for generated files. Defaults to ./upscaled_10x",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=10.0,
        help="Upscale factor. Defaults to 10.",
    )
    parser.add_argument(
        "--suffix",
        default="_UPSCALED",
        help="Suffix appended before the extension. Defaults to _UPSCALED",
    )
    parser.add_argument(
        "--mode",
        choices=ACCEPTED_MODES,
        default="smart",
        help=(
            "Processing profile. Primary modes: smart, crisp, photo, classic. "
            "Legacy aliases (auto/ui/artwork) are still accepted."
        ),
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=12,
        help="Maximum images per run. Defaults to 12. Use 0 to disable this limit.",
    )
    parser.add_argument(
        "--max-output-megapixels",
        type=float,
        default=600.0,
        help="Skip files whose output would exceed this size unless --force-large is used.",
    )
    parser.add_argument(
        "--force-large",
        action="store_true",
        help="Allow outputs larger than --max-output-megapixels.",
    )
    parser.add_argument(
        "--include-already-upscaled",
        action="store_true",
        help="Include files whose names already look upscaled.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned work without generating files.",
    )
    parser.add_argument(
        "--artwork-sharpness",
        type=float,
        default=1.06,
        help="Sharpness multiplier for creative assets on the non-AI path.",
    )
    parser.add_argument(
        "--ui-sharpness",
        type=float,
        default=1.12,
        help="Sharpness multiplier for crisp/detail assets on the non-AI path.",
    )
    parser.add_argument(
        "--disable-artwork-ai",
        action="store_true",
        help="Disable Real-ESRGAN AI path and use original non-AI processing for all images.",
    )
    parser.add_argument(
        "--artwork-ai-target-scale",
        type=float,
        default=16.0,
        help="AI target scale for photo/render assets when AI path is enabled.",
    )
    parser.add_argument(
        "--esrgan-model-artwork",
        default="realesrgan-x4plus",
        help="Real-ESRGAN model for the AI path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = UpscaleConfig(
        input_dir=Path(args.input),
        output_dir=Path(args.output),
        scale=args.scale,
        suffix=args.suffix,
        mode=args.mode,
        max_images=None if args.max_images == 0 else args.max_images,
        max_output_megapixels=args.max_output_megapixels,
        force_large=args.force_large,
        include_already_upscaled=args.include_already_upscaled,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        artwork_sharpness=args.artwork_sharpness,
        ui_sharpness=args.ui_sharpness,
        artwork_ai_enabled=not args.disable_artwork_ai,
        artwork_ai_target_scale=args.artwork_ai_target_scale,
        auto_install_backend=True,
        esrgan_model_artwork=args.esrgan_model_artwork,
    )

    try:
        results = run_batch(config)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print_summary(results)
    return 0 if not any(item.status == "failed" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
