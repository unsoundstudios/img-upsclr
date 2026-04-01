#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_SLUG="IMG-UPSCLR"
APP_PATH="${1:-${ROOT_DIR}/dist/${APP_SLUG}.app}"
PROFILE="${NOTARY_KEYCHAIN_PROFILE:-APPLE_NOTARY}"
IDENTITY="${MACOS_CODESIGN_IDENTITY:-}"
ENTITLEMENTS="${MACOS_ENTITLEMENTS_FILE:-}"
SKIP_SIGN="${SKIP_SIGN:-0}"
DRY_RUN="${DRY_RUN:-0}"

if [[ ! -d "${APP_PATH}" ]]; then
  echo "Missing app bundle: ${APP_PATH}"
  exit 1
fi

if ! command -v xcrun >/dev/null 2>&1; then
  echo "xcrun is required for notarization."
  exit 1
fi

if [[ "${SKIP_SIGN}" != "1" ]]; then
  if [[ -z "${IDENTITY}" ]]; then
    echo "MACOS_CODESIGN_IDENTITY is required for notarization."
    echo "Example: export MACOS_CODESIGN_IDENTITY='Developer ID Application: Your Name (TEAMID)'"
    exit 1
  fi

  SIGN_CMD=(codesign --force --deep --options runtime --timestamp --sign "${IDENTITY}")
  if [[ -n "${ENTITLEMENTS}" ]]; then
    if [[ ! -f "${ENTITLEMENTS}" ]]; then
      echo "Entitlements file not found: ${ENTITLEMENTS}"
      exit 1
    fi
    SIGN_CMD+=(--entitlements "${ENTITLEMENTS}")
  fi
  SIGN_CMD+=("${APP_PATH}")

  echo "Signing app with identity: ${IDENTITY}"
  "${SIGN_CMD[@]}"
fi

echo "Verifying code signature..."
codesign --verify --deep --strict "${APP_PATH}"

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "Dry run enabled. Skipping notary submission and stapling."
  exit 0
fi

if ! xcrun notarytool history --keychain-profile "${PROFILE}" >/dev/null 2>&1; then
  cat <<EOF
Notary keychain profile '${PROFILE}' is not configured or inaccessible.

Set:
  export APPLE_ID='you@example.com'
  export TEAM_ID='ABCDE12345'
  export APP_SPECIFIC_PASSWORD='xxxx-xxxx-xxxx-xxxx'

Then run:
  ./scripts/setup_notary_profile.sh ${PROFILE}
EOF
  exit 1
fi

TMP_DIR="$(mktemp -d /tmp/unsound-notary.XXXXXX)"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

ZIP_PATH="${TMP_DIR}/${APP_SLUG}-notary.zip"
echo "Creating notarization archive..."
ditto -c -k --keepParent "${APP_PATH}" "${ZIP_PATH}"

NOTARY_DIR="${ROOT_DIR}/release/notary"
mkdir -p "${NOTARY_DIR}"
STAMP="$(date +%Y%m%d-%H%M%S)"
RESULT_JSON="${NOTARY_DIR}/notary-result-${STAMP}.json"

echo "Submitting to Apple notarization service with profile '${PROFILE}'..."
xcrun notarytool submit "${ZIP_PATH}" \
  --keychain-profile "${PROFILE}" \
  --wait \
  --output-format json > "${RESULT_JSON}"

STATUS="$(python3 - <<'PY' "${RESULT_JSON}"
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload.get("status", ""))
PY
)"

if [[ "${STATUS}" != "Accepted" ]]; then
  echo "Notarization failed. See: ${RESULT_JSON}"
  exit 1
fi

echo "Notarization accepted. Stapling ticket..."
xcrun stapler staple "${APP_PATH}"
xcrun stapler validate "${APP_PATH}"

echo "Notarization complete."
echo "App: ${APP_PATH}"
echo "Result JSON: ${RESULT_JSON}"
