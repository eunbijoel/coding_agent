"""Coding agent loop — Brain (Ollama) + Hands (workspace tools)."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from coding_agent import events as ev
from coding_agent.config import MAX_TOOL_ROUNDS, MODEL_NAME
from coding_agent.events import AgentEvent
from coding_agent.ollama_client import OllamaError, chat
from coding_agent.tools import TOOL_SCHEMAS, dispatch

SYSTEM_PROMPT = """You are a coding agent similar to Cursor / Claude Code / deepagents-code.
You work ONLY inside the given workspace directory using tools.

Rules:
1. Prefer tools over guessing. Read files before editing.
2. Keep changes small and correct. Use edit_file for surgical edits; write_file for new files.
3. After meaningful edits, briefly explain what changed and why.
4. Show important code in your final answer using markdown fenced blocks with the file path.
5. Do not escape the workspace. Do not run destructive shell commands.
6. When the user asks to create a UI (e.g. prompt input like deepagents-code), implement it with working code in the workspace.
7. Reply in the same language the user uses (Korean or English).

Workspace tools: list_dir, read_file, write_file, edit_file, grep, run_shell.
"""


def run_agent(
    user_prompt: str,
    workspace: Path,
    *,
    history: list[dict[str, Any]] | None = None,
    model: str | None = None,
) -> Iterator[AgentEvent]:
    """Yield normalized events while running the tool loop."""
    model_name = (model or MODEL_NAME).strip() or MODEL_NAME
    yield ev.status(f"model={model_name}", workspace=str(workspace))
    yield ev.trace("start", f"prompt length={len(user_prompt)}")

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    if history:
        # Keep only user/assistant text turns from prior UI history
        for item in history[-12:]:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_prompt})

    final_text = ""
    try:
        for round_i in range(1, MAX_TOOL_ROUNDS + 1):
            yield ev.status(f"thinking · round {round_i}/{MAX_TOOL_ROUNDS}")
            yield ev.trace("llm_call", f"round={round_i}")

            message = chat(messages, tools=TOOL_SCHEMAS, model=model_name)
            thinking = (message.get("thinking") or "").strip()
            if thinking:
                yield ev.thinking(thinking)

            content = (message.get("content") or "").strip()
            tool_calls = message.get("tool_calls") or []

            # Persist assistant turn (with tool_calls if any)
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)

            if content and not tool_calls:
                final_text = content
                yield ev.assistant_delta(content)
                yield ev.assistant_end(content)
                break

            if content and tool_calls:
                # Partial narration before tools
                yield ev.assistant_delta(content)

            if not tool_calls:
                if not content:
                    yield ev.error("Model returned empty response")
                break

            for tc in tool_calls:
                call_id = str(tc.get("id") or uuid.uuid4())
                fn = tc.get("function") or {}
                name = (fn.get("name") or "").strip()
                raw_args = fn.get("arguments")
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args) if raw_args.strip() else {}
                    except json.JSONDecodeError:
                        args = {"_raw": raw_args}
                elif isinstance(raw_args, dict):
                    args = raw_args
                else:
                    args = {}

                yield ev.tool_call(name, args, call_id=call_id)
                yield ev.trace("tool_call", name, arguments=args)

                outcome = dispatch(workspace, name, args)
                yield ev.tool_result(
                    name,
                    outcome.content,
                    call_id=call_id,
                    ok=outcome.ok,
                    artifact=outcome.artifact,
                )

                art = outcome.artifact or {}
                if art.get("kind") == "file" and art.get("content") is not None:
                    yield ev.file_view(
                        str(art.get("path") or args.get("path") or ""),
                        str(art.get("content") or ""),
                        language=str(art.get("language") or ""),
                    )

                # Feed tool result back to the model
                messages.append(
                    {
                        "role": "tool",
                        "name": name,
                        "tool_name": name,
                        "content": outcome.content[:20000],
                    }
                )
        else:
            yield ev.error(f"Stopped after {MAX_TOOL_ROUNDS} tool rounds")

    except OllamaError as exc:
        yield ev.error(str(exc))
    except Exception as exc:  # noqa: BLE001
        yield ev.error(f"Agent failed: {exc}")

    if final_text:
        yield ev.trace("complete", "assistant reply ready")
    yield ev.done()
