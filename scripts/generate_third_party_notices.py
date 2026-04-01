#!/usr/bin/env python3
"""
Generate THIRD_PARTY_NOTICES.md from installed Python dependencies.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata as im
import re
from pathlib import Path


REQUIREMENT_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")

# Build-time tools can be excluded from end-user notice docs by default.
DEFAULT_EXCLUDES = {"pyinstaller"}

# Metadata is sometimes incomplete depending on wheel version; these fallbacks
# keep the notice document user-facing and explicit.
LICENSE_OVERRIDES = {
    "pillow": "HPND",
    "pyside6": "LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only",
}

HOMEPAGE_OVERRIDES = {
    "pillow": "https://python-pillow.org",
    "pyside6": "https://pyside.org",
}

EXTRA_COMPONENTS: list[tuple[str, str, str, str]] = [
    ("realesrgan-ncnn-vulkan", "v0.2.5.0", "BSD-3-Clause", "https://github.com/xinntao/Real-ESRGAN")
]


def normalize_dep(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def parse_dependency_names(requirement_files: list[Path]) -> list[str]:
    names: set[str] = set()
    for path in requirement_files:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            match = REQUIREMENT_NAME_RE.match(line)
            if not match:
                continue
            package = match.group(1).split("[", 1)[0]
            names.add(normalize_dep(package))
    return sorted(names)


def pick_homepage(meta: im.PackageMetadata, dep: str) -> str:
    override = HOMEPAGE_OVERRIDES.get(dep)
    if override:
        return override

    home = (meta.get("Home-page") or "").strip()
    if home:
        return home

    project_urls = meta.get_all("Project-URL") or []
    ranked: list[tuple[int, str]] = []
    for entry in project_urls:
        if "," in entry:
            label, url = entry.split(",", 1)
            label = label.strip().lower()
            url = url.strip()
        else:
            label = ""
            url = entry.strip()
        if not url:
            continue
        rank = 9
        if "homepage" in label:
            rank = 0
        elif "source" in label or "repository" in label:
            rank = 1
        elif "documentation" in label:
            rank = 2
        elif "changelog" in label:
            rank = 3
        ranked.append((rank, url))

    if ranked:
        ranked.sort(key=lambda item: item[0])
        return ranked[0][1]

    return ""


def best_license(meta: im.PackageMetadata, dep: str) -> str:
    override = LICENSE_OVERRIDES.get(dep)
    if override:
        return override

    license_field = (meta.get("License") or "").strip()
    if license_field and license_field.upper() not in {"UNKNOWN", "NONE", "N/A"}:
        return license_field.replace("\n", " ")

    classifiers = meta.get_all("Classifier") or []
    license_classifiers = [c for c in classifiers if c.startswith("License ::")]
    cleaned: list[str] = []
    for item in license_classifiers:
        # Keep the right-most useful component of the classifier.
        part = item.split("::")[-1].strip()
        if part and part not in cleaned:
            cleaned.append(part)

    if cleaned:
        return "; ".join(cleaned)

    return ""


def build_markdown(
    dependency_names: list[str],
    *,
    include_missing: bool,
    allow_unknown: bool,
    include_extras: bool,
) -> str:
    lines: list[str] = []
    lines.append("# Third-Party Notices")
    lines.append("")
    lines.append(
        "This document lists third-party Python packages used by IMG-UPSCLR "
        "and their declared license metadata."
    )
    lines.append("")
    lines.append(f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}")
    lines.append("")
    lines.append("| Package | Version | License | Home Page |")
    lines.append("|---|---|---|---|")

    rows_added = 0
    for dep in dependency_names:
        try:
            meta = im.metadata(dep)
            version = im.version(dep)
        except im.PackageNotFoundError:
            if include_missing:
                lines.append(f"| {dep} | Missing | Metadata unavailable | |")
                rows_added += 1
            continue

        license_name = best_license(meta, dep)
        homepage = pick_homepage(meta, dep)

        if not allow_unknown and (not license_name or not homepage):
            continue

        if not license_name:
            license_name = "Metadata unavailable"
        if not homepage:
            homepage = ""

        lines.append(f"| {dep} | {version} | {license_name} | {homepage} |")
        rows_added += 1

    if include_extras:
        for name, version, license_name, homepage in EXTRA_COMPONENTS:
            lines.append(f"| {name} | {version} | {license_name} | {homepage} |")
            rows_added += 1

    if rows_added == 0:
        lines.append("| (none) | - | - | - |")

    lines.append("")
    lines.append(
        "Note: verify all licenses with legal counsel before commercial distribution, "
        "especially for transitive dependencies and binary redistribution."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate THIRD_PARTY_NOTICES.md")
    parser.add_argument(
        "--requirements",
        nargs="*",
        default=["requirements-desktop.txt"],
        help="Requirement files used to determine dependency scope.",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=sorted(DEFAULT_EXCLUDES),
        help="Package names to exclude from notices.",
    )
    parser.add_argument(
        "--include-missing",
        action="store_true",
        help="Include rows for packages not found in current environment.",
    )
    parser.add_argument(
        "--allow-unknown",
        action="store_true",
        help="Allow rows even when license/homepage metadata is incomplete.",
    )
    parser.add_argument(
        "--no-include-extras",
        action="store_true",
        help="Do not append non-Python bundled components.",
    )
    parser.add_argument(
        "--output",
        default="THIRD_PARTY_NOTICES.md",
        help="Output markdown path.",
    )
    args = parser.parse_args()

    root = Path.cwd()
    req_files = [root / item for item in args.requirements]
    names = parse_dependency_names(req_files)
    if not names:
        print("No dependency names found in requirements files.")
        return 1

    excluded = {normalize_dep(item) for item in (args.exclude or [])}
    names = [item for item in names if item not in excluded]
    if not names:
        print("No dependency names remain after exclusions.")
        return 1

    output = root / args.output
    output.write_text(
        build_markdown(
            names,
            include_missing=args.include_missing,
            allow_unknown=args.allow_unknown,
            include_extras=not args.no_include_extras,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
