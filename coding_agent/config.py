from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKSPACE = ROOT / "workspace"

OLLAMA_HOST = os.environ.get("CODING_AGENT_OLLAMA", "http://127.0.0.1:11434").rstrip("/")
# Bare Ollama tag; agent layer prefixes with ollama:
MODEL_NAME = os.environ.get("CODING_AGENT_MODEL", "gemma4:31b")
LLM_TIMEOUT_SEC = int(os.environ.get("CODING_AGENT_TIMEOUT", "600"))
MAX_TOOL_ROUNDS = int(os.environ.get("CODING_AGENT_MAX_ROUNDS", "12"))
MAX_FILE_CHARS = int(os.environ.get("CODING_AGENT_MAX_FILE_CHARS", "24000"))
SHELL_TIMEOUT_SEC = int(os.environ.get("CODING_AGENT_SHELL_TIMEOUT", "30"))

SHELL_DENY = (
    "rm -rf /",
    "mkfs",
    ":(){",
    "shutdown",
    "reboot",
    "dd if=",
    "> /dev/",
)


def resolve_workspace(path: str | Path | None = None) -> Path:
    raw = path or os.environ.get("CODING_AGENT_WORKSPACE") or DEFAULT_WORKSPACE
    ws = Path(raw).expanduser().resolve()
    ws.mkdir(parents=True, exist_ok=True)
    return ws
