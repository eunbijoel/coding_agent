#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="${HOME}/.local/bin:${PATH}"

if [[ ! -d .venv ]]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv .venv --python 3.12
    # shellcheck disable=SC1091
    source .venv/bin/activate
    uv pip install -r requirements.txt
  else
    echo "Python 3.12+ required (deepagents-code). Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
  fi
fi

exec .venv/bin/streamlit run app.py --server.headless true "$@"
