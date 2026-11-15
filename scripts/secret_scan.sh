#!/usr/bin/env bash
# Pre-push scan (or, with an archive path as argument, a scan of that archive): the DeepSeek key (read from ../.env) and the Claude account e-mail (read from ~/.claude.json) must
# appear in no tracked or staged file, and in no commit about to be pushed.  Neither value is printed or stored.
set -uo pipefail
cd "$(dirname "$0")/.."
KEY=$(grep -E '^DEEPSEEK_API_KEY=' ../.env | head -1 | cut -d= -f2- | tr -d "\"'")
MAIL=$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.claude.json'))).get('oauthAccount',{}).get('emailAddress',''))")
[ -n "$KEY" ] && [ -n "$MAIL" ] || { echo "scan: could not read the values to scan for" >&2; exit 2; }
hits=0
if [ -n "${1:-}" ]; then   # D122: scan a release archive (every member, decompressed) before upload
  for v in "$KEY" "$MAIL"; do
    if tar -xOzf "$1" | grep -qaF -e "$v"; then hits=1; fi
  done
  [ $hits = 0 ] && echo "scan: archive clean (key, account e-mail): $1" || { echo "scan: FOUND a secret in $1" >&2; exit 1; }
  exit 0
fi
for v in "$KEY" "$MAIL"; do
  if git grep -qF -e "$v" -- . ; then hits=1; fi
  if git grep -qF --cached -e "$v" -- . ; then hits=1; fi
  if git log -p origin/sprint..HEAD 2>/dev/null | grep -qF -e "$v"; then hits=1; fi
done
[ $hits = 0 ] && echo "scan: clean (key, account e-mail; worktree, index, unpushed commits)" || { echo "scan: FOUND a secret" >&2; exit 1; }
