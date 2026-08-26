"""Workspace-scoped tools (Hands layer). Paths cannot escape the workspace."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from coding_agent.config import MAX_FILE_CHARS, SHELL_DENY, SHELL_TIMEOUT_SEC


@dataclass
class ToolOutcome:
    content: str
    ok: bool = True
    artifact: dict[str, Any] | None = None


def _safe_join(workspace: Path, rel: str) -> Path:
    rel = (rel or ".").strip() or "."
    # Normalize absolute-looking paths to workspace-relative
    if rel.startswith("/"):
        rel = rel.lstrip("/")
    target = (workspace / rel).resolve()
    try:
        target.relative_to(workspace.resolve())
    except ValueError as exc:
        raise PermissionError(f"Path escapes workspace: {rel}") from exc
    return target


def list_dir(workspace: Path, path: str = ".", max_entries: int = 200) -> ToolOutcome:
    target = _safe_join(workspace, path)
    if not target.exists():
        return ToolOutcome(f"Not found: {path}", ok=False)
    if not target.is_dir():
        return ToolOutcome(f"Not a directory: {path}", ok=False)
    entries: list[str] = []
    for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        mark = "/" if child.is_dir() else ""
        entries.append(f"{child.name}{mark}")
        if len(entries) >= max_entries:
            entries.append("… (truncated)")
            break
    rel = str(target.relative_to(workspace)) if target != workspace else "."
    body = f"{rel}/\n" + "\n".join(entries) if entries else f"{rel}/\n(empty)"
    return ToolOutcome(body, artifact={"path": rel, "kind": "dir"})


def read_file(workspace: Path, path: str, offset: int = 1, limit: int = 400) -> ToolOutcome:
    target = _safe_join(workspace, path)
    if not target.exists() or not target.is_file():
        return ToolOutcome(f"File not found: {path}", ok=False)
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return ToolOutcome(f"Read failed: {exc}", ok=False)

    lines = text.splitlines()
    offset = max(1, int(offset or 1))
    limit = max(1, min(int(limit or 400), 2000))
    slice_lines = lines[offset - 1 : offset - 1 + limit]
    numbered = [f"{i + offset:4d}|{line}" for i, line in enumerate(slice_lines)]
    clipped = "\n".join(numbered)
    if len(clipped) > MAX_FILE_CHARS:
        clipped = clipped[:MAX_FILE_CHARS] + "\n… (truncated by size)"
    rel = str(target.relative_to(workspace))
    return ToolOutcome(
        clipped or "(empty file)",
        artifact={
            "path": rel,
            "kind": "file",
            "content": text if len(text) <= MAX_FILE_CHARS else text[:MAX_FILE_CHARS],
            "language": _guess_lang(rel),
            "total_lines": len(lines),
        },
    )


def write_file(workspace: Path, path: str, content: str) -> ToolOutcome:
    target = _safe_join(workspace, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    before = ""
    if target.exists() and target.is_file():
        before = target.read_text(encoding="utf-8", errors="replace")
    target.write_text(content or "", encoding="utf-8")
    rel = str(target.relative_to(workspace))
    return ToolOutcome(
        f"Wrote {len(content or '')} chars → {rel}",
        artifact={
            "path": rel,
            "kind": "file",
            "content": content or "",
            "before": before,
            "language": _guess_lang(rel),
            "action": "write",
        },
    )


def edit_file(
    workspace: Path,
    path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> ToolOutcome:
    target = _safe_join(workspace, path)
    if not target.exists() or not target.is_file():
        return ToolOutcome(f"File not found: {path}", ok=False)
    before = target.read_text(encoding="utf-8", errors="replace")
    if old_string not in before:
        return ToolOutcome("old_string not found in file", ok=False)
    count = before.count(old_string)
    if count > 1 and not replace_all:
        return ToolOutcome(
            f"old_string matched {count} times; set replace_all=true or make it unique",
            ok=False,
        )
    after = before.replace(old_string, new_string) if replace_all else before.replace(
        old_string, new_string, 1
    )
    target.write_text(after, encoding="utf-8")
    rel = str(target.relative_to(workspace))
    return ToolOutcome(
        f"Edited {rel} ({count if replace_all else 1} replacement(s))",
        artifact={
            "path": rel,
            "kind": "file",
            "content": after if len(after) <= MAX_FILE_CHARS else after[:MAX_FILE_CHARS],
            "before": before if len(before) <= MAX_FILE_CHARS else before[:MAX_FILE_CHARS],
            "language": _guess_lang(rel),
            "action": "edit",
            "diff_preview": _simple_diff(old_string, new_string),
        },
    )


def grep_files(
    workspace: Path,
    pattern: str,
    path: str = ".",
    max_hits: int = 50,
) -> ToolOutcome:
    root = _safe_join(workspace, path)
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return ToolOutcome(f"Invalid regex: {exc}", ok=False)

    hits: list[str] = []
    files = [root] if root.is_file() else sorted(root.rglob("*"))
    for fp in files:
        if not fp.is_file():
            continue
        if any(part.startswith(".") for part in fp.relative_to(workspace).parts):
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if regex.search(line):
                rel = str(fp.relative_to(workspace))
                hits.append(f"{rel}:{i}:{line[:200]}")
                if len(hits) >= max_hits:
                    return ToolOutcome("\n".join(hits) + "\n… (truncated)")
    return ToolOutcome("\n".join(hits) if hits else "No matches")


def run_shell(workspace: Path, command: str) -> ToolOutcome:
    cmd = (command or "").strip()
    if not cmd:
        return ToolOutcome("Empty command", ok=False)
    lower = cmd.lower()
    for bad in SHELL_DENY:
        if bad in lower:
            return ToolOutcome(f"Blocked dangerous command pattern: {bad}", ok=False)
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=SHELL_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        return ToolOutcome(f"Timed out after {SHELL_TIMEOUT_SEC}s", ok=False)
    except OSError as exc:
        return ToolOutcome(f"Shell error: {exc}", ok=False)

    out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    out = out.strip() or "(no output)"
    if len(out) > MAX_FILE_CHARS:
        out = out[:MAX_FILE_CHARS] + "\n… (truncated)"
    return ToolOutcome(
        out,
        ok=proc.returncode == 0,
        artifact={"exit_code": proc.returncode, "command": cmd, "kind": "shell"},
    )


def _guess_lang(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".jsx": "jsx",
        ".json": "json",
        ".md": "markdown",
        ".html": "html",
        ".css": "css",
        ".sh": "bash",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".toml": "toml",
        ".rs": "rust",
        ".go": "go",
    }.get(ext, "")


def _simple_diff(old: str, new: str) -> str:
    old_l = old.splitlines()
    new_l = new.splitlines()
    lines = ["--- old", "+++ new"]
    for line in old_l[:40]:
        lines.append(f"- {line}")
    for line in new_l[:40]:
        lines.append(f"+ {line}")
    return "\n".join(lines)


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and folders under a workspace-relative path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path (default '.')",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file with optional 1-based line offset/limit. Returns numbered lines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "offset": {"type": "integer", "description": "1-based start line"},
                    "limit": {"type": "integer", "description": "Max lines to return"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a text file with full content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace old_string with new_string in a file (unique match unless replace_all).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                    "replace_all": {"type": "boolean"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search for a regex pattern under a path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command inside the workspace (cwd=workspace). Prefer file tools for edits.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
]


def dispatch(workspace: Path, name: str, arguments: dict[str, Any]) -> ToolOutcome:
    handlers: dict[str, Callable[..., ToolOutcome]] = {
        "list_dir": lambda **kw: list_dir(workspace, **kw),
        "read_file": lambda **kw: read_file(workspace, **kw),
        "write_file": lambda **kw: write_file(workspace, **kw),
        "edit_file": lambda **kw: edit_file(workspace, **kw),
        "grep": lambda **kw: grep_files(workspace, **kw),
        "run_shell": lambda **kw: run_shell(workspace, **kw),
    }
    fn = handlers.get(name)
    if not fn:
        return ToolOutcome(f"Unknown tool: {name}", ok=False)
    try:
        return fn(**(arguments or {}))
    except TypeError as exc:
        return ToolOutcome(f"Bad arguments for {name}: {exc}", ok=False)
    except PermissionError as exc:
        return ToolOutcome(str(exc), ok=False)
    except Exception as exc:  # noqa: BLE001
        return ToolOutcome(f"{name} failed: {exc}", ok=False)


IGNORE_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".deepagents",
    "data",
}
IGNORE_SUFFIXES = {".pyc", ".pyo", ".pyd", ".so", ".dll", ".egg"}


def tree_snapshot(workspace: Path, max_depth: int = 3, max_entries: int = 120) -> list[str]:
    """Flat relative paths for the sidebar file tree (source files only)."""
    out: list[str] = []
    root = workspace.resolve()

    def walk(cur: Path, depth: int) -> None:
        if len(out) >= max_entries or depth > max_depth:
            return
        try:
            children = sorted(cur.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return
        for child in children:
            if child.name.startswith(".") or child.name in IGNORE_DIR_NAMES:
                continue
            if "__pycache__" in child.parts:
                continue
            if child.is_file() and child.suffix.lower() in IGNORE_SUFFIXES:
                continue
            rel = str(child.relative_to(root))
            if "__pycache__" in rel or rel.endswith(tuple(IGNORE_SUFFIXES)):
                continue
            if child.is_dir():
                out.append(rel + "/")
                walk(child, depth + 1)
            else:
                out.append(rel)

    walk(root, 0)
    return out
