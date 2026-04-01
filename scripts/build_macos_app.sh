#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
APP_SLUG="IMG-UPSCLR"
APP_PATH="${DIST_DIR}/${APP_SLUG}.app"
ICON_SOURCE_PNG="${ROOT_DIR}/assets/img-upsclr_logo.png"
TMP_ROOT="$(mktemp -d /tmp/unsound-upscaler-build.XXXXXX)"
VENV_DIR="${TMP_ROOT}/.venv"
STAGE_DIR="${TMP_ROOT}/src"
ESRGAN_BUNDLE_DIR="${STAGE_DIR}/realesrgan"
ICONSET_DIR="${TMP_ROOT}/${APP_SLUG}.iconset"
ICON_ICNS="${TMP_ROOT}/${APP_SLUG}.icns"

cleanup() {
  rm -rf "${TMP_ROOT}"
}
trap cleanup EXIT

mkdir -p "${STAGE_DIR}" "${DIST_DIR}"
cp "${ROOT_DIR}/desktop_app.py" "${STAGE_DIR}/desktop_app.py"
cp "${ROOT_DIR}/upscaler_core.py" "${STAGE_DIR}/upscaler_core.py"
cp "${ROOT_DIR}/esrgan_backend.py" "${STAGE_DIR}/esrgan_backend.py"

if [[ ! -f "${ICON_SOURCE_PNG}" ]]; then
  echo "Missing app icon source: ${ICON_SOURCE_PNG}"
  exit 1
fi

mkdir -p "${ICONSET_DIR}"
for size in 16 32 128 256 512; do
  sips -z "${size}" "${size}" "${ICON_SOURCE_PNG}" \
    --out "${ICONSET_DIR}/icon_${size}x${size}.png" >/dev/null
  sips -z "$((size * 2))" "$((size * 2))" "${ICON_SOURCE_PNG}" \
    --out "${ICONSET_DIR}/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "${ICONSET_DIR}" -o "${ICON_ICNS}"

python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"
python3 -m pip install --upgrade pip
python3 -m pip install -r "${ROOT_DIR}/requirements-desktop.txt"
python3 "${ROOT_DIR}/scripts/generate_third_party_notices.py"
python3 "${ROOT_DIR}/scripts/install_esrgan_backend.py" --target-dir "${ESRGAN_BUNDLE_DIR}"
find "${ESRGAN_BUNDLE_DIR}" -name '._*' -type f -delete || true
dot_clean "${ESRGAN_BUNDLE_DIR}" 2>/dev/null || true
cp "${ROOT_DIR}/THIRD_PARTY_NOTICES.md" "${STAGE_DIR}/THIRD_PARTY_NOTICES.md"
cp "${ROOT_DIR}/SECURITY.md" "${STAGE_DIR}/SECURITY.md"
cp "${ROOT_DIR}/LICENSE" "${STAGE_DIR}/LICENSE"

cd "${STAGE_DIR}"

pyinstaller \
  --clean \
  --noconfirm \
  --windowed \
  --name "${APP_SLUG}" \
  --icon "${ICON_ICNS}" \
  --add-data "realesrgan:realesrgan" \
  --add-data "THIRD_PARTY_NOTICES.md:." \
  --add-data "SECURITY.md:." \
  --add-data "LICENSE:." \
  desktop_app.py

rm -rf "${APP_PATH}"
cp -R "${STAGE_DIR}/dist/${APP_SLUG}.app" "${APP_PATH}"
find "${APP_PATH}" -name '._*' -type f -delete || true
dot_clean "${APP_PATH}" 2>/dev/null || true

if ! codesign --force --deep --sign - "${APP_PATH}" 2>/dev/null; then
  echo "Warning: ad-hoc codesign did not complete cleanly on this volume."
fi
find "${APP_PATH}" -name '._*' -type f -delete || true

echo "Built app: ${APP_PATH}"
