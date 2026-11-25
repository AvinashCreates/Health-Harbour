#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
TARGET_URL="${TARGET_URL:-http://localhost:8000}"
. "$SCRIPT_DIR/require-local-target.sh"
require_local_target "$TARGET_URL"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required to run the k6 current-stack test." >&2
  exit 127
fi

OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/reports}"
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"
REPORT_NAME="${REPORT_NAME:-k6-summary.json}"
docker run --rm --network host \
  -e TARGET_URL="$TARGET_URL" \
  -e AUTH_TOKEN="${AUTH_TOKEN:-}" \
  -e AUTH_PATH="${AUTH_PATH:-/auth/me}" \
  -e RAMP_DURATION="${RAMP_DURATION:-1m}" \
  -v "$SCRIPT_DIR:/scripts:ro" \
  -v "$OUTPUT_DIR:/reports:rw" \
  grafana/k6:0.55.0 run \
  --summary-export="/reports/$REPORT_NAME" \
  /scripts/current-stack.js
