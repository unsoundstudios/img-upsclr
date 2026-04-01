#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-desktop"

if [[ ! -x "${VENV_DIR}/bin/python3" ]]; then
  python3 -m venv "${VENV_DIR}"
  source "${VENV_DIR}/bin/activate"
  python3 -m pip install --upgrade pip
  python3 -m pip install -r "${ROOT_DIR}/requirements-desktop.txt"
else
  source "${VENV_DIR}/bin/activate"
fi

cd "${ROOT_DIR}"
if ! python3 scripts/install_esrgan_backend.py; then
  echo "Warning: Real-ESRGAN backend is not ready. Upscaling jobs may fail until install succeeds."
fi
python3 desktop_app.py
