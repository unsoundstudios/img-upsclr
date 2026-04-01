#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${ROOT_DIR}"
./scripts/build_macos_app.sh
./scripts/notarize_macos_app.sh
./scripts/package_release_bundle.sh

echo "Built notarized release package for macOS."
