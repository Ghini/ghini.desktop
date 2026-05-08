#!/usr/bin/env bash
set -euo pipefail

# Backup Codex CLI session data.
#
# Usage:
#   ./backup_codex.sh
#   ./backup_codex.sh 019dc3fa-46f4-7cd0-bed8-d55381655bd5
#
# Environment:
#   CODEX_HOME         default: ~/.codex
#   CODEX_BACKUP_ROOT  default: ~/codex-session-backups

CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
BACKUP_ROOT="${CODEX_BACKUP_ROOT:-$HOME/codex-session-backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="$BACKUP_ROOT/sessions-$STAMP"
SESSION_ID="${1:-}"

mkdir -p "$DEST"

echo "Codex home:   $CODEX_HOME"
echo "Backup dest:  $DEST"

if [[ ! -d "$CODEX_HOME" ]]; then
    echo "ERROR: Codex home not found: $CODEX_HOME" >&2
    exit 1
fi

if [[ -d "$CODEX_HOME/sessions" ]]; then
    cp -a "$CODEX_HOME/sessions" "$DEST/"
else
    echo "WARNING: No sessions directory found at $CODEX_HOME/sessions" >&2
fi

# Back up useful local state/index/config files, but do not fail if absent.
for f in \
    history.jsonl \
    session_index.jsonl \
    state_5.sqlite \
    logs_2.sqlite \
    config.toml
do
    if [[ -e "$CODEX_HOME/$f" ]]; then
        cp -a "$CODEX_HOME/$f" "$DEST/"
    fi
done

if [[ -n "$SESSION_ID" ]]; then
    IMPORTANT_DIR="$BACKUP_ROOT/important"
    mkdir -p "$IMPORTANT_DIR"

    mapfile -t matches < <(
        find "$CODEX_HOME/sessions" -type f -name "*${SESSION_ID}*.jsonl" 2>/dev/null | sort
    )

    if (( ${#matches[@]} == 0 )); then
        echo "WARNING: No session file found for ID: $SESSION_ID" >&2
    else
        echo
        echo "Important session matches:"
        for src in "${matches[@]}"; do
            base="$(basename "$src")"
            target="$IMPORTANT_DIR/$base"
            cp -a "$src" "$target"
            echo "  $src"
            echo "  -> $target"
        done
    fi
fi

echo
echo "Backup complete:"
echo "$DEST"

echo
echo "Recent backed-up sessions:"
find "$DEST/sessions" -type f -name 'rollout-*.jsonl' \
    -printf '%TY-%Tm-%Td %TH:%TM %10s %p\n' 2>/dev/null \
    | sort \
    | tail -20
