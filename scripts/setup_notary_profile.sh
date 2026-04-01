#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:-APPLE_NOTARY}"
APPLE_ID="${APPLE_ID:-}"
TEAM_ID="${TEAM_ID:-}"
APP_SPECIFIC_PASSWORD="${APP_SPECIFIC_PASSWORD:-}"

if [[ -z "${APPLE_ID}" || -z "${TEAM_ID}" || -z "${APP_SPECIFIC_PASSWORD}" ]]; then
  cat <<EOF
Missing required environment variables.

Set these and rerun:
  export APPLE_ID='you@example.com'
  export TEAM_ID='ABCDE12345'
  export APP_SPECIFIC_PASSWORD='xxxx-xxxx-xxxx-xxxx'

Then run:
  ./scripts/setup_notary_profile.sh ${PROFILE}
EOF
  exit 1
fi

xcrun notarytool store-credentials "${PROFILE}" \
  --apple-id "${APPLE_ID}" \
  --team-id "${TEAM_ID}" \
  --password "${APP_SPECIFIC_PASSWORD}"

echo "Stored keychain profile: ${PROFILE}"
