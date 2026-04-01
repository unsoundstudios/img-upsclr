#!/usr/bin/env python3
"""
Shared upscaler processing engine used by the desktop app and CLI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat

from esrgan_backend import run_realesrgan_chain

try:
    Image.MAX_IMAGE_PIXELS = None
except Exception:
    pass


SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".tif",
    ".tiff",
    ".bmp",
}

DEFAULT_SKIP_PATTERNS = (
    "upscaled",
    "10x",
    "20x",
    "ultra_clean",
    "gigapixel",
    "esrgan",
)

# Public product-facing modes
PUBLIC_MODES = ("smart", "crisp", "photo", "classic")

# Backward compatible aliases accepted from existing configs/UI builds.
MODE_ALIASES = {
    "smart": "smart",
    "auto": "smart",
    "crisp": "crisp",
    "detail": "crisp",
    "ui": "crisp",
    "photo": "photo",
    "ai": "photo",
    "artwork": "photo",
    "classic": "classic",
    "original": "classic",
}
ACCEPTED_MODES = tuple(sorted(MODE_ALIASES.keys()))

DETAIL_HINT_PATTERN = re.compile(
    r"(ui|interface|logo|icon|label|diagram|chart|screenshot|screen|glyph|wireframe|typography|barcode|qr|packshot|spec)",
)
PHOTO_HINT_PATTERN = re.compile(
    r"(photo|portrait|render|lifestyle|scene|camera|product|hero|cover|album|banner|mockup|art|illustration)",
)


@dataclass
class UpscaleConfig:
    input_dir: Path
    output_dir: Path
    selected_files: list[Path] | None = None
    scale: float = 10.0
    suffix: str = "_UPSCALED"
    mode: str = "smart"
    max_images: int | None = None
    max_output_megapixels: float = 600.0
    force_large: bool = False
    include_already_upscaled: bool = False
    overwrite: bool = False
    dry_run: bool = False

    # Original script tuning
    artwork_sharpness: float = 1.06
    ui_sharpness: float = 1.12

    # Smart AI photo/artwork path
    artwork_ai_enabled: bool = True
    artwork_ai_target_scale: float = 16.0
    auto_install_backend: bool = True
    esrgan_model_artwork: str = "realesrgan-x4plus"
    artwork_ai_max_native_passes: int = 2


@dataclass
class JobResult:
    source: str
    output: str | None
    kind: str | None
    status: str
    reason: str | None
    input_size: tuple[int, int] | None
    output_size: tuple[int, int] | None
    estimated_output_megapixels: float | None


def normalize_mode(value: str) -> str:
    return MODE_ALIASES.get((value or "").strip().lower(), "smart")


def iter_images(folder: Path) -> Iterable[Path]:
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        if path.name.startswith(".") or path.name.startswith("._"):
            continue
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def looks_already_upscaled(path: Path) -> bool:
    stem = path.stem.lower()
    return any(token in stem for token in DEFAULT_SKIP_PATTERNS)


def classify_image_legacy(path: Path, img: Image.Image) -> str:
    """Original script classifier kept for classic mode compatibility."""
    name = path.stem.lower()
    width, height = img.size
    aspect_ratio = max(width, height) / max(1, min(width, height))
    has_alpha = "A" in img.getbands()

    if re.search(r"(ui|interface|plugin|panel|knob|injector|moltenq|flanger)", name):
        return "ui"
    if has_alpha or aspect_ratio >= 1.35:
        return "ui"
    if re.search(r"(cover|art|album|ritual|toolbox|kicks|hats|black\\s*hole)", name):
        return "artwork"
    return "artwork"


def analyze_style_metrics(img: Image.Image) -> tuple[int, float, float, float]:
    sample = img.convert("RGB").resize((128, 128), resample=Image.Resampling.BILINEAR)

    colors = sample.getcolors(maxcolors=4096)
    unique_colors = len(colors) if colors is not None else 4096

    edge_map = sample.convert("L").filter(ImageFilter.FIND_EDGES)
    hist = edge_map.histogram()
    total = max(1, sum(hist))
    edge_mean = sum(level * count for level, count in enumerate(hist)) / total

    luma_stddev = float(ImageStat.Stat(sample.convert("L")).stddev[0])
    saturation_mean = float(ImageStat.Stat(sample.convert("HSV").getchannel("S")).mean[0])
    return unique_colors, edge_mean, luma_stddev, saturation_mean


def should_preserve_detail(path: Path, img: Image.Image) -> bool:
    name = path.stem.lower()
    has_alpha = "A" in img.getbands()
    max_side = max(img.size)
    detail_score = 0
    creative_score = 0

    if has_alpha:
        detail_score += 5

    if DETAIL_HINT_PATTERN.search(name):
        detail_score += 3
    if PHOTO_HINT_PATTERN.search(name):
        creative_score += 2

    unique_colors, edge_mean, luma_stddev, saturation_mean = analyze_style_metrics(img)

    # Strong indicators for detail/asset-safe path.
    if unique_colors <= 180 and edge_mean >= 16.5:
        detail_score += 4
    if edge_mean >= 28.0:
        detail_score += 3
    if max_side <= 900 and edge_mean >= 17.5 and luma_stddev >= 26.0:
        detail_score += 2
    if saturation_mean <= 12.0 and edge_mean >= 20.0:
        detail_score += 1

    # Strong indicators for photo/render creative path.
    if (
        unique_colors >= 2000
        and edge_mean <= 17.2
        and 10.0 <= luma_stddev <= 100.0
        and max_side >= 900
    ):
        creative_score += 4
    if (
        unique_colors >= 1500
        and edge_mean <= 20.5
        and luma_stddev >= 14.0
        and max_side >= 1024
    ):
        creative_score += 2
    if 25.0 <= saturation_mean <= 185.0 and edge_mean <= 18.5 and unique_colors >= 1800:
        creative_score += 1

    # Filename hints boost confidence but still require signal quality.
    if PHOTO_HINT_PATTERN.search(name) and unique_colors >= 900 and edge_mean <= 22.0:
        creative_score += 2
    if DETAIL_HINT_PATTERN.search(name) and edge_mean >= 14.0:
        detail_score += 1

    # Tie-breaker intentionally favors detail-safe to prevent AI morphing on critical assets.
    return detail_score >= creative_score


def classify_image(path: Path, img: Image.Image, forced_mode: str) -> str:
    mode = normalize_mode(forced_mode)

    if mode == "crisp":
        return "detail"
    if mode == "photo":
        return "creative"
    if mode == "classic":
        return classify_image_legacy(path, img)

    # smart mode
    return "detail" if should_preserve_detail(path, img) else "creative"


def effective_scale_for_kind(kind: str, config: UpscaleConfig) -> float:
    mode = normalize_mode(config.mode)
    if mode in {"smart", "photo"} and kind == "creative" and config.artwork_ai_enabled:
        return max(config.scale, config.artwork_ai_target_scale)
    return config.scale


def progressive_sizes(size: tuple[int, int], scale: float) -> list[tuple[int, int]]:
    width, height = size
    target = (
        max(1, int(round(width * scale))),
        max(1, int(round(height * scale))),
    )
    sizes: list[tuple[int, int]] = []
    current_w, current_h = width, height

    while current_w < target[0] or current_h < target[1]:
        next_w = min(target[0], max(current_w + 1, int(round(current_w * 2.0))))
        next_h = min(target[1], max(current_h + 1, int(round(current_h * 2.0))))
        if next_w == target[0] and next_h == target[1]:
            sizes.append(target)
            break
        sizes.append((next_w, next_h))
        current_w, current_h = next_w, next_h

    if not sizes or sizes[-1] != target:
        sizes.append(target)

    deduped: list[tuple[int, int]] = []
    for item in sizes:
        if not deduped or deduped[-1] != item:
            deduped.append(item)
    return deduped


def split_alpha(img: Image.Image) -> tuple[Image.Image, Image.Image | None]:
    if "A" not in img.getbands():
        return img, None

    rgba = img.convert("RGBA")
    rgb = rgba.convert("RGB")
    alpha = rgba.getchannel("A")
    return rgb, alpha


def merge_alpha(rgb: Image.Image, alpha: Image.Image | None) -> Image.Image:
    if alpha is None:
        return rgb
    merged = rgb.convert("RGBA")
    merged.putalpha(alpha)
    return merged


def resize_progressive(
    img: Image.Image,
    scale: float,
    resample: Image.Resampling,
) -> Image.Image:
    result = img
    for size in progressive_sizes(img.size, scale):
        result = result.resize(size, resample=resample)
    return result


def enhance_artwork(img: Image.Image, sharpness: float) -> Image.Image:
    img = img.filter(ImageFilter.UnsharpMask(radius=1.35, percent=135, threshold=2))
    img = ImageEnhance.Contrast(img).enhance(1.03)
    img = ImageEnhance.Color(img).enhance(1.01)
    img = ImageEnhance.Sharpness(img).enhance(sharpness)
    return img


def enhance_ui(img: Image.Image, sharpness: float) -> Image.Image:
    img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=160, threshold=1))
    img = ImageEnhance.Contrast(img).enhance(1.02)
    img = ImageEnhance.Sharpness(img).enhance(sharpness)
    return img


def prepare_image(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img)
    if img.mode in {"P", "1"}:
        return img.convert("RGBA")
    if img.mode == "LA":
        return img.convert("RGBA")
    if img.mode == "CMYK":
        return img.convert("RGB")
    return img.copy()


def upscale_image_original(
    img: Image.Image,
    kind: str,
    scale: float,
    artwork_sharpness: float,
    ui_sharpness: float,
) -> Image.Image:
    base = prepare_image(img)
    rgb, alpha = split_alpha(base)
    resampled_rgb = resize_progressive(rgb, scale, Image.Resampling.LANCZOS)

    resampled_alpha = None
    if alpha is not None:
        resampled_alpha = resize_progressive(alpha, scale, Image.Resampling.LANCZOS)

    if kind == "ui":
        enhanced = enhance_ui(resampled_rgb, ui_sharpness)
    else:
        enhanced = enhance_artwork(resampled_rgb, artwork_sharpness)

    return merge_alpha(enhanced, resampled_alpha)


def upscale_artwork_ai(
    img: Image.Image,
    target_scale: float,
    config: UpscaleConfig,
) -> Image.Image:
    base = prepare_image(img)
    rgb, alpha = split_alpha(base)
    target_size = (
        max(1, int(round(base.size[0] * target_scale))),
        max(1, int(round(base.size[1] * target_scale))),
    )

    upscaled_rgb = run_realesrgan_chain(
        source_rgb=rgb,
        target_size=target_size,
        model=config.esrgan_model_artwork,
        auto_install=config.auto_install_backend,
        max_native_passes=config.artwork_ai_max_native_passes,
    )
    if alpha is None:
        return upscaled_rgb

    upscaled_alpha = resize_progressive(alpha, target_scale, Image.Resampling.LANCZOS)
    return merge_alpha(upscaled_rgb, upscaled_alpha)


def upscale_image(img: Image.Image, kind: str, config: UpscaleConfig) -> Image.Image:
    mode = normalize_mode(config.mode)
    item_scale = effective_scale_for_kind(kind, config)

    if mode in {"smart", "photo"} and kind == "creative" and config.artwork_ai_enabled:
        return upscale_artwork_ai(img, target_scale=item_scale, config=config)

    if mode == "classic":
        legacy_kind = kind if kind in {"ui", "artwork"} else "artwork"
        return upscale_image_original(
            img=img,
            kind=legacy_kind,
            scale=item_scale,
            artwork_sharpness=config.artwork_sharpness,
            ui_sharpness=config.ui_sharpness,
        )

    # smart/crisp non-AI paths use detail/artwork sharpen profile mapping.
    non_ai_kind = "ui" if kind == "detail" else "artwork"
    return upscale_image_original(
        img=img,
        kind=non_ai_kind,
        scale=item_scale,
        artwork_sharpness=config.artwork_sharpness,
        ui_sharpness=config.ui_sharpness,
    )


def estimate_megapixels(size: tuple[int, int], scale: float) -> float:
    width, height = size
    pixels = width * height * (scale**2)
    return pixels / 1_000_000


def build_output_path(output_dir: Path, source: Path, suffix: str) -> Path:
    return output_dir / f"{source.stem}{suffix}{source.suffix.lower()}"


def save_image(result: Image.Image, source_img: Image.Image, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    save_kwargs: dict[str, object] = {}
    if "icc_profile" in source_img.info:
        save_kwargs["icc_profile"] = source_img.info["icc_profile"]
    if "exif" in source_img.info:
        save_kwargs["exif"] = source_img.info["exif"]

    extension = output.suffix.lower()
    if extension in {".jpg", ".jpeg"}:
        if result.mode not in {"RGB", "L"}:
            result = result.convert("RGB")
        save_kwargs.update({"quality": 100, "subsampling": 0, "optimize": True})
    elif extension == ".png":
        save_kwargs.update({"compress_level": 2, "optimize": False})
    elif extension == ".webp":
        save_kwargs.update({"quality": 100, "method": 6, "lossless": True})

    result.save(output, **save_kwargs)


def process_file(path: Path, config: UpscaleConfig) -> JobResult:
    if looks_already_upscaled(path) and not config.include_already_upscaled:
        return JobResult(
            source=str(path),
            output=None,
            kind=None,
            status="skipped",
            reason="filename looks already upscaled",
            input_size=None,
            output_size=None,
            estimated_output_megapixels=None,
        )

    try:
        with Image.open(path) as img:
            img.load()
            kind = classify_image(path, img, config.mode)
            item_scale = effective_scale_for_kind(kind, config)
            estimate_mp = estimate_megapixels(img.size, item_scale)
            output = build_output_path(config.output_dir, path, config.suffix)
            target_size = (
                max(1, int(round(img.size[0] * item_scale))),
                max(1, int(round(img.size[1] * item_scale))),
            )

            if estimate_mp > config.max_output_megapixels and not config.force_large:
                return JobResult(
                    source=str(path),
                    output=str(output),
                    kind=kind,
                    status="skipped",
                    reason=(
                        f"estimated output size {estimate_mp:.1f} MP exceeds limit "
                        f"{config.max_output_megapixels:.1f} MP"
                    ),
                    input_size=img.size,
                    output_size=target_size,
                    estimated_output_megapixels=round(estimate_mp, 2),
                )

            if output.exists() and not config.overwrite:
                return JobResult(
                    source=str(path),
                    output=str(output),
                    kind=kind,
                    status="skipped",
                    reason="output file already exists",
                    input_size=img.size,
                    output_size=target_size,
                    estimated_output_megapixels=round(estimate_mp, 2),
                )

            if config.dry_run:
                return JobResult(
                    source=str(path),
                    output=str(output),
                    kind=kind,
                    status="planned",
                    reason=None,
                    input_size=img.size,
                    output_size=target_size,
                    estimated_output_megapixels=round(estimate_mp, 2),
                )

            result = upscale_image(img=img, kind=kind, config=config)
            save_image(result, img, output)
            return JobResult(
                source=str(path),
                output=str(output),
                kind=kind,
                status="processed",
                reason=None,
                input_size=img.size,
                output_size=result.size,
                estimated_output_megapixels=round(estimate_mp, 2),
            )
    except Exception as exc:
        return JobResult(
            source=str(path),
            output=None,
            kind=None,
            status="failed",
            reason=str(exc),
            input_size=None,
            output_size=None,
            estimated_output_megapixels=None,
        )


def print_summary(results: list[JobResult]) -> None:
    processed = [item for item in results if item.status == "processed"]
    planned = [item for item in results if item.status == "planned"]
    skipped = [item for item in results if item.status == "skipped"]
    failed = [item for item in results if item.status == "failed"]

    for item in results:
        line = f"[{item.status.upper():8}] {Path(item.source).name}"
        if item.kind:
            line += f" [{item.kind}]"
        if item.output:
            line += f" -> {Path(item.output).name}"
        if item.output_size:
            line += f" ({item.output_size[0]}x{item.output_size[1]})"
        if item.reason:
            line += f" | {item.reason}"
        print(line)

    print()
    print(
        "Summary: "
        f"{len(processed)} processed, "
        f"{len(planned)} planned, "
        f"{len(skipped)} skipped, "
        f"{len(failed)} failed"
    )


def run_batch(
    config: UpscaleConfig,
    on_result: Callable[[int, int, JobResult], None] | None = None,
) -> list[JobResult]:
    config.input_dir = config.input_dir.expanduser().resolve()
    output_dir = config.output_dir.expanduser()
    if not output_dir.is_absolute():
        output_dir = (config.input_dir / output_dir).resolve()
    config.output_dir = output_dir

    if not config.input_dir.exists() or not config.input_dir.is_dir():
        raise FileNotFoundError(f"Input folder not found: {config.input_dir}")

    if config.selected_files:
        images: list[Path] = []
        for item in config.selected_files:
            path = Path(item).expanduser().resolve()
            if not path.exists() or not path.is_file():
                raise FileNotFoundError(f"Input file not found: {path}")
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                raise ValueError(f"Unsupported image type: {path.name}")
            images.append(path)
    else:
        images = list(iter_images(config.input_dir))

    if not images:
        raise ValueError(f"No supported images found in {config.input_dir}")

    if config.max_images is not None and config.max_images > 0 and len(images) > config.max_images:
        raise ValueError(
            f"Too many input images: {len(images)}. Maximum allowed is {config.max_images}."
        )

    results: list[JobResult] = []
    for idx, path in enumerate(images, start=1):
        item = process_file(path, config)
        results.append(item)
        if on_result:
            on_result(idx, len(images), item)
    return results
