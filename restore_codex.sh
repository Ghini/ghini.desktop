#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat <<'EOF'
Usage:
  ./restore_codex.sh SESSION_ID [BACKUP_DIR]

Restore a Codex CLI session JSONL from a backup into $CODEX_HOME/sessions.

Arguments:
  SESSION_ID   Codex session UUID to restore.
  BACKUP_DIR   Optional backup directory, e.g.
               ~/codex-session-backups/sessions-20260508-082006

Environment:
  CODEX_HOME         default: ~/.codex
  CODEX_BACKUP_ROOT  default: ~/codex-session-backups

Safe test example:
  TEST_CODEX_HOME="$(mktemp -d "$HOME/tmp-codex-home.XXXXXX")"
  CODEX_HOME="$TEST_CODEX_HOME" ./restore_codex.sh SESSION_ID BACKUP_DIR
EOF
    exit 0
fi

CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
BACKUP_ROOT="${CODEX_BACKUP_ROOT:-$HOME/codex-session-backups}"
SESSION_ID="${1:-}"
BACKUP_DIR="${2:-}"

if [[ -z "$SESSION_ID" ]]; then
    echo "Usage: $0 SESSION_ID [BACKUP_DIR]" >&2
    exit 2
fi

if [[ ! -d "$CODEX_HOME" ]]; then
    echo "ERROR: Codex home not found: $CODEX_HOME" >&2
    exit 1
fi

if [[ -z "$BACKUP_DIR" ]]; then
    BACKUP_DIR="$(
        find "$BACKUP_ROOT" -maxdepth 1 -type d -name 'sessions-*' -printf '%T@ %p\n' 2>/dev/null \
            | sort -n \
            | tail -1 \
            | cut -d' ' -f2-
    )"
fi

if [[ -z "$BACKUP_DIR" || ! -d "$BACKUP_DIR" ]]; then
    echo "ERROR: Backup directory not found." >&2
    echo "Checked: $BACKUP_DIR" >&2
    exit 1
fi

echo "Codex home:  $CODEX_HOME"
echo "Backup dir:  $BACKUP_DIR"
echo "Session ID:  $SESSION_ID"
echo

mapfile -t matches < <(
    {
        find "$BACKUP_DIR" -type f -name "*${SESSION_ID}*.jsonl" 2>/dev/null
        find "$BACKUP_ROOT/important" -type f -name "*${SESSION_ID}*.jsonl" 2>/dev/null || true
    } | sort -u
)

if (( ${#matches[@]} == 0 )); then
    echo "ERROR: No backed-up session file found for ID: $SESSION_ID" >&2
    exit 1
fi

if (( ${#matches[@]} > 1 )); then
    echo "Multiple matches found; using the largest file:"
    printf '  %s\n' "${matches[@]}"
    echo
    src="$(
        for f in "${matches[@]}"; do
            printf '%s\t%s\n' "$(stat -c '%s' "$f")" "$f"
        done | sort -n | tail -1 | cut -f2-
    )"
else
    src="${matches[0]}"
fi

base="$(basename "$src")"

# Prefer restoring to the original dated path if the backup has sessions/YYYY/MM/DD.
rel=""
case "$src" in
    *"/sessions/"*)
        rel="${src#*/sessions/}"
        ;;
esac

if [[ "$rel" == "$src" || -z "$rel" ]]; then
    # Fall back to parsing date from filename: rollout-YYYY-MM-DDT...
    if [[ "$base" =~ rollout-([0-9]{4})-([0-9]{2})-([0-9]{2})T ]]; then
        rel="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}/${BASH_REMATCH[3]}/$base"
    else
        echo "ERROR: Could not determine restore path for $base" >&2
        exit 1
    fi
fi

dest="$CODEX_HOME/sessions/$rel"
mkdir -p "$(dirname "$dest")"

if [[ -e "$dest" ]]; then
    stamp="$(date +%Y%m%d-%H%M%S)"
    safety="$dest.pre-restore-$stamp"
    cp -a "$dest" "$safety"
    echo "Existing live session backed up to:"
    echo "  $safety"
fi

cp -a "$src" "$dest"

echo
echo "Restored:"
echo "  $src"
echo "-> $dest"

echo
echo "Verify:"
echo "  ls -lh '$dest'"
echo
echo "Resume:"
echo "  codex resume $SESSION_ID"
