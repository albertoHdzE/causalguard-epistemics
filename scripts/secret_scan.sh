#!/usr/bin/env bash
# Pre-push scan: the DeepSeek key (read from ../.env) and the Claude account e-mail (read from ~/.claude.json) must
# appear in no tracked or staged file, and in no commit about to be pushed.  Neither value is printed or stored.
set -uo pipefail
cd "$(dirname "$0")/.."
KEY=$(grep -E '^DEEPSEEK_API_KEY=' ../.env | head -1 | cut -d= -f2- | tr -d "\"'")
MAIL=$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.claude.json'))).get('oauthAccount',{}).get('emailAddress',''))")
[ -n "$KEY" ] && [ -n "$MAIL" ] || { echo "scan: could not read the values to scan for" >&2; exit 2; }
hits=0
for v in "$KEY" "$MAIL"; do
  if git grep -qF -e "$v" -- . ; then hits=1; fi
  if git grep -qF --cached -e "$v" -- . ; then hits=1; fi
  if git log -p origin/sprint..HEAD 2>/dev/null | grep -qF -e "$v"; then hits=1; fi
done
[ $hits = 0 ] && echo "scan: clean (key, account e-mail; worktree, index, unpushed commits)" || { echo "scan: FOUND a secret" >&2; exit 1; }
