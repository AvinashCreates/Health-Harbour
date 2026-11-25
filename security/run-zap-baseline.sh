#!/usr/bin/env sh
set -eu

: "${TARGET_URL:?Set TARGET_URL to the running application URL}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
. "$SCRIPT_DIR/require-local-target.sh"
require_local_target "$TARGET_URL"

OUTPUT_DIR="${OUTPUT_DIR:-./security/reports}"
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required to run the OWASP ZAP baseline scan." >&2
  exit 127
fi

docker run --rm --network host -t \
  -v "$OUTPUT_DIR:/zap/wrk:rw" \
  ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t "$TARGET_URL" -J zap-report.json -r zap-report.html
