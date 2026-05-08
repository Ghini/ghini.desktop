#!/usr/bin/env bash
set -euo pipefail

# Resume the primary Codex session for this branch/workflow.
SESSION_ID="${CODEX_SESSION_ID:-019dc3fa-46f4-7cd0-bed8-d55381655bd5}"

exec codex resume "$SESSION_ID"
