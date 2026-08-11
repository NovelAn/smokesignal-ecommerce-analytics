#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON="$(cd "$(git -C "$ROOT" rev-parse --git-common-dir)/.." && pwd)/.venv/bin/python"

"$PYTHON" "$ROOT/scripts/prepare_ai_v2_review_cohort.py" --help >/dev/null
"$PYTHON" "$ROOT/scripts/evaluate_ai_v2_gold.py" --help >/dev/null
