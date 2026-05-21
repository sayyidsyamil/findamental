#!/usr/bin/env bash
set -euo pipefail

# Reset Hermes Telegram memory for Findamental demos.
#
# What this clears:
# - Telegram session rows in ~/.hermes/state.db
# - Telegram session JSON/JSONL files in ~/.hermes/sessions
# - ~/.hermes/memories/USER.md
#
# What this keeps:
# - Telegram bot token
# - Telegram allowed users
# - channel_directory.json
# - Findamental PDF index/cache
#
# A timestamped backup is created before anything is changed.

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$HERMES_HOME/backups/findamental_memory_reset_$STAMP"

echo "Findamental reset."
echo "Backup: $BACKUP_DIR"

mkdir -p "$BACKUP_DIR"

if command -v hermes >/dev/null 2>&1; then
  echo "Stopping Hermes gateway..."
  hermes gateway stop || true
fi

if [ -f "$HERMES_HOME/state.db" ]; then
  cp "$HERMES_HOME/state.db" "$BACKUP_DIR/state.db"
fi

if [ -d "$HERMES_HOME/sessions" ]; then
  mkdir -p "$BACKUP_DIR/sessions"
  cp -R "$HERMES_HOME/sessions/." "$BACKUP_DIR/sessions/" || true
fi

if [ -f "$HERMES_HOME/memories/USER.md" ]; then
  mkdir -p "$BACKUP_DIR/memories"
  cp "$HERMES_HOME/memories/USER.md" "$BACKUP_DIR/memories/USER.md"
fi

if [ -f "$HERMES_HOME/state.db" ]; then
  echo "Clearing Telegram sessions from state.db..."
  sqlite3 "$HERMES_HOME/state.db" <<'SQL'
PRAGMA foreign_keys = OFF;
CREATE TEMP TABLE reset_sessions AS
  SELECT id FROM sessions WHERE source = 'telegram';
DELETE FROM messages WHERE session_id IN (SELECT id FROM reset_sessions);
DELETE FROM sessions WHERE id IN (SELECT id FROM reset_sessions);
INSERT INTO messages_fts(messages_fts) VALUES('rebuild');
INSERT INTO messages_fts_trigram(messages_fts_trigram) VALUES('rebuild');
VACUUM;
SQL
fi

if [ -d "$HERMES_HOME/sessions" ]; then
  echo "Removing Telegram session files..."
  while IFS= read -r -d '' file; do
    if grep -q '"platform": "telegram"' "$file" 2>/dev/null; then
      rm -f "$file"
    fi
  done < <(find "$HERMES_HOME/sessions" -type f \( -name '*.json' -o -name '*.jsonl' \) -print0)
fi

if [ -f "$HERMES_HOME/sessions/sessions.json" ]; then
  cp "$HERMES_HOME/sessions/sessions.json" "$BACKUP_DIR/sessions/sessions.json.after_file_delete" || true
fi

if [ -f "$HERMES_HOME/memories/USER.md" ]; then
  echo "Clearing USER memory..."
  : > "$HERMES_HOME/memories/USER.md"
fi

if command -v hermes >/dev/null 2>&1; then
  echo "Starting Hermes gateway..."
  hermes gateway start || true
  hermes gateway status || true
fi

echo "Done."
echo "Existing Telegram users should now get a fresh Findamental session."
echo "Ask them to send: /findamental"
