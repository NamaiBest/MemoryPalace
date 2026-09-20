#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
provider="${1:-meta}"

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
export ELASTICSEARCH_URL="${ELASTICSEARCH_URL:-https://my-vectordb-project-bece59.es.us-east4.gcp.elastic.cloud}"
export DEMO_TOKEN="${DEMO_TOKEN:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')}"
export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8771}"

python3 "$repo_dir/hardware-demo/run.py" serve \
  --source synthetic --recorder phone --host 0.0.0.0 --port 8771 &
backend_pid=$!
trap 'kill "$backend_pid" 2>/dev/null || true' EXIT INT TERM

cd "$repo_dir/app"
npm run dev
