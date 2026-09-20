#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
provider="${1:-meta}"

# Local credentials live in a gitignored .env. Values already exported in the
# environment win, so a one-off override on the command line still works.
if [[ -f "$repo_dir/.env" ]]; then
  while IFS= read -r line; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue
    key="${line%%=*}"
    [[ -n "${!key:-}" ]] && continue
    value="${line#*=}"
    value="${value%\"}"; value="${value#\"}"
    value="${value%\'}"; value="${value#\'}"
    export "${key}=${value}"
  done < "$repo_dir/.env"
fi

case "$provider" in
  meta)
    required_key="MODEL_API_KEY"
    ;;
  grok)
    required_key="XAI_API_KEY"
    ;;
  *)
    echo "Usage: $0 [meta|grok]" >&2
    exit 2
    ;;
esac

if [[ -z "${!required_key:-}" ]]; then
  echo "$required_key must be set for the $provider Memory Guard launch." >&2
  exit 2
fi
export MEMORYPALACE_AGENT_PROVIDER="$provider"
export ELASTICSEARCH_URL="${ELASTICSEARCH_URL:-https://my-elasticsearch-project-f50785.es.us-central1.gcp.elastic.cloud:443}"
export DEMO_TOKEN="${DEMO_TOKEN:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')}"
export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8771}"

# The detector venv owns numpy/scipy; the system interpreter usually does not.
py="$repo_dir/confusion-detector/.venv/bin/python"
[[ -x "$py" ]] || py="python3"

"$py" "$repo_dir/hardware-demo/run.py" serve \
  --source synthetic --recorder phone --host 0.0.0.0 --port 8771 &
backend_pid=$!
trap 'kill "$backend_pid" 2>/dev/null || true' EXIT INT TERM

# next dev never completes hydration in this project (HANDOFF.md, error 1), so the
# web app must be served as a production build.
cd "$repo_dir/app"
npm run build
npm start
