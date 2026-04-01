#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_VENV="${ROOT_DIR}/.venv-desktop"
WEB_VENV="${ROOT_DIR}/.venv-web"

cd "${ROOT_DIR}"
if [[ ! -x "${DESKTOP_VENV}/bin/python3" ]]; then
  python3 -m venv "${DESKTOP_VENV}"
fi
source "${DESKTOP_VENV}/bin/activate"
python3 -m pip install -r requirements-desktop.txt >/dev/null
python3 scripts/smoke_test_macos.py
deactivate

if [[ ! -x "${WEB_VENV}/bin/python3" ]]; then
  python3 -m venv "${WEB_VENV}"
fi
source "${WEB_VENV}/bin/activate"
python3 -m pip install -r requirements-web.txt >/dev/null
python3 scripts/smoke_test_web.py
deactivate

echo "All local smoke tests passed."
