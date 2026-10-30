#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="$repo/artifacts/postgres"
while (($#)); do
  case "$1" in
    --output-dir) out="${2:?Missing output directory}"; shift 2;;
    --help|-h) echo 'Usage: bash audit-postgres.sh [--output-dir DIR]'; exit 0;;
    *) echo "Unknown option: $1" >&2; exit 2;;
  esac
done
out="$(realpath -m "$out")"
cd "$repo"
mvn -B -ntp verify
java -jar plan-audit/target/plan-audit-1.0.0.jar "$out"/pg-before-index-*.json "$out"/pg-after-index-*.json > "$out/pg-cardinality-audit.json"
