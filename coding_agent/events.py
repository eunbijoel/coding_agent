"""Normalized event vocabulary (inspired by tasking-agent / Agent Harness Console)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

EventType = Literal[
    "status",
    "assistant_delta",
    "assistant_end",
    "thinking",
    "tool_call",
    "tool_result",
    "file_view",
    "trace",
    "error",
    "done",
]


@dataclass
class AgentEvent:
    type: EventType
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def status(message: str, **extra: Any) -> AgentEvent:
    return AgentEvent("status", {"message": message, **extra})


def assistant_delta(text: str) -> AgentEvent:
    return AgentEvent("assistant_delta", {"text": text})


def assistant_end(text: str) -> AgentEvent:
    return AgentEvent("assistant_end", {"text": text})


def thinking(text: str) -> AgentEvent:
    return AgentEvent("thinking", {"text": text})


def tool_call(name: str, arguments: dict[str, Any], call_id: str = "") -> AgentEvent:
    return AgentEvent(
        "tool_call",
        {"name": name, "arguments": arguments, "call_id": call_id},
    )


def tool_result(
    name: str,
    content: str,
    *,
    call_id: str = "",
    ok: bool = True,
    artifact: dict[str, Any] | None = None,
) -> AgentEvent:
    return AgentEvent(
        "tool_result",
        {
            "name": name,
            "content": content,
            "call_id": call_id,
            "ok": ok,
            "artifact": artifact or {},
        },
    )


def file_view(path: str, content: str, *, language: str = "") -> AgentEvent:
    return AgentEvent(
        "file_view",
        {"path": path, "content": content, "language": language},
    )


def trace(step: str, detail: str = "", **extra: Any) -> AgentEvent:
    return AgentEvent("trace", {"step": step, "detail": detail, **extra})


def error(message: str) -> AgentEvent:
    return AgentEvent("error", {"message": message})


def done() -> AgentEvent:
    return AgentEvent("done", {})
