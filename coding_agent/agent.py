"""Coding agent loop powered by deepagents-code (create_cli_agent)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from coding_agent import events as ev
from coding_agent.config import MAX_TOOL_ROUNDS, MODEL_NAME, MAX_FILE_CHARS
from coding_agent.events import AgentEvent

# Keep short — create_cli_agent owns the real system prompt (cwd, tools, skills).
USER_HINT = (
    "[Workbench] Prefer tools over guessing; reply in the user's language; "
    "after edits briefly explain what changed.\n\n"
)


def _normalize_model(model: str | None) -> str:
    name = (model or MODEL_NAME).strip() or MODEL_NAME
    if ":" in name and name.split(":", 1)[0] in {
        "ollama",
        "openai",
        "anthropic",
        "google_genai",
        "bedrock",
        "groq",
        "fireworks",
    }:
        return name
    # Bare Ollama tag from the UI selector → provider prefix
    return f"ollama:{name}"


def _content_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def _maybe_file_view(workspace: Path, tool_name: str, args: dict[str, Any], result: str) -> AgentEvent | None:
    """If a file was read/written, surface content for the Code pane."""
    path = args.get("path") or args.get("file_path") or args.get("file")
    if not path or not isinstance(path, str):
        return None
    # deepagents sometimes returns absolute paths
    p = Path(path)
    try:
        if p.is_absolute():
            rel = p.resolve().relative_to(workspace.resolve())
            target = p.resolve()
        else:
            target = (workspace / path).resolve()
            rel = target.relative_to(workspace.resolve())
    except Exception:  # noqa: BLE001
        return None

    name = (tool_name or "").lower()
    if name in {"read_file", "write_file", "edit_file"} and target.is_file():
        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = result
        if len(text) > MAX_FILE_CHARS:
            text = text[:MAX_FILE_CHARS] + "\n… (truncated)"
        return ev.file_view(str(rel), text, language=target.suffix.lstrip("."))
    return None


def run_agent(
    user_prompt: str,
    workspace: Path,
    *,
    history: list[dict[str, Any]] | None = None,
    model: str | None = None,
) -> Iterator[AgentEvent]:
    """Yield normalized UI events while running deepagents-code."""
    from deepagents_code.agent import create_cli_agent

    model_name = _normalize_model(model)
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    yield ev.status(f"model={model_name} · deepagents-code", workspace=str(workspace))
    yield ev.trace("start", f"prompt length={len(user_prompt)}")

    try:
        agent, _backend = create_cli_agent(
            model=model_name,
            assistant_id="coding-agent-ui",
            cwd=workspace,
            interactive=False,
            auto_approve=True,
            enable_ask_user=False,
            enable_memory=False,
            enable_skills=False,
            enable_shell=True,
        )
    except Exception as exc:  # noqa: BLE001
        yield ev.error(f"Failed to create deepagents-code agent: {exc}")
        yield ev.done()
        return

    messages: list[Any] = []
    if history:
        for item in history[-12:]:
            role = item.get("role")
            content = item.get("content")
            if role == "user" and isinstance(content, str) and content.strip():
                messages.append(HumanMessage(content=content))
            elif role == "assistant" and isinstance(content, str) and content.strip():
                messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=USER_HINT + user_prompt))

    # Track last tool call args by id for file_view pairing
    pending_args: dict[str, tuple[str, dict[str, Any]]] = {}
    final_text = ""
    recursion = max(25, MAX_TOOL_ROUNDS * 8)

    try:
        yield ev.status("running deepagents-code…")
        for chunk in agent.stream(
            {"messages": messages},
            stream_mode="updates",
            config={"recursion_limit": recursion},
        ):
            if not isinstance(chunk, dict):
                continue
            for node, update in chunk.items():
                if update is None or not isinstance(update, dict):
                    continue

                if node == "model":
                    for m in update.get("messages") or []:
                        if not isinstance(m, AIMessage):
                            continue
                        thinking = getattr(m, "additional_kwargs", {}) or {}
                        # Some models put reasoning elsewhere; ignore if absent
                        tool_calls = list(m.tool_calls or [])
                        text = _content_text(m.content).strip()

                        for tc in tool_calls:
                            name = tc.get("name") or ""
                            args = tc.get("args") or {}
                            call_id = str(tc.get("id") or "")
                            pending_args[call_id] = (name, args if isinstance(args, dict) else {})
                            yield ev.tool_call(name, args if isinstance(args, dict) else {"_raw": args}, call_id=call_id)
                            yield ev.trace("tool_call", name, arguments=args)

                        if text and not tool_calls:
                            final_text = text
                            yield ev.assistant_delta(text)
                            yield ev.assistant_end(text)
                        elif text and tool_calls:
                            yield ev.assistant_delta(text)

                elif node == "tools":
                    for m in update.get("messages") or []:
                        if not isinstance(m, ToolMessage):
                            continue
                        name = getattr(m, "name", "") or ""
                        call_id = str(getattr(m, "tool_call_id", "") or "")
                        content = _content_text(m.content)
                        status = getattr(m, "status", None)
                        ok = status != "error"
                        yield ev.tool_result(name, content, call_id=call_id, ok=ok)
                        yield ev.trace("tool_result", name, ok=ok)

                        args: dict[str, Any] = {}
                        if call_id in pending_args:
                            name2, args = pending_args.pop(call_id)
                            name = name or name2
                        fv = _maybe_file_view(workspace, name, args, content)
                        if fv:
                            yield fv

                else:
                    # Lightweight middleware visibility
                    if node.endswith("before_model") or node.endswith("after_model"):
                        yield ev.trace("middleware", node)

    except Exception as exc:  # noqa: BLE001
        yield ev.error(f"deepagents-code run failed: {exc}")

    if final_text:
        yield ev.trace("complete", "assistant reply ready")
    yield ev.done()
