from __future__ import annotations

import difflib
import sys
from html import escape
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coding_agent.agent import run_agent
from coding_agent.config import MODEL_NAME, resolve_workspace
from coding_agent.ollama_client import available as ollama_available
from coding_agent.ollama_client import list_models
from coding_agent.tools import tree_snapshot

st.set_page_config(
    page_title="Coding Agent",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Cursor-ish workbench look (not purple/cream AI defaults)
st.markdown(
    """
<style>
  :root {
    --ca-bg: #0f1419;
    --ca-panel: #151b23;
    --ca-border: #2a3340;
    --ca-accent: #3d9a6a;
    --ca-text: #e6edf3;
    --ca-muted: #8b9bab;
    --ca-tool: #1c2430;
  }
  .stApp { background: linear-gradient(160deg, #0f1419 0%, #121820 45%, #0d1a16 100%); }
  [data-testid="stSidebar"] {
    background: var(--ca-panel);
    border-right: 1px solid var(--ca-border);
  }
  h1, h2, h3, p, label, .stMarkdown { color: var(--ca-text); }
  .ca-brand {
    font-family: "IBM Plex Mono", "JetBrains Mono", ui-monospace, monospace;
    font-size: 1.35rem;
    letter-spacing: 0.04em;
    color: var(--ca-accent);
    margin-bottom: 0.15rem;
  }
  .ca-sub { color: var(--ca-muted); font-size: 0.9rem; margin-bottom: 0.8rem; }
  .ca-panel-title {
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--ca-muted);
    margin: 0.2rem 0 0.5rem;
  }
  .ca-tool {
    background: var(--ca-tool);
    border: 1px solid var(--ca-border);
    border-left: 3px solid var(--ca-accent);
    border-radius: 4px;
    padding: 0.55rem 0.7rem;
    margin: 0.35rem 0;
    font-family: ui-monospace, monospace;
    font-size: 0.8rem;
  }
  .ca-tool .name { color: #7dcea0; }
  .ca-file-chip {
    display: inline-block;
    background: #1a2330;
    border: 1px solid var(--ca-border);
    padding: 0.15rem 0.45rem;
    border-radius: 3px;
    font-family: ui-monospace, monospace;
    font-size: 0.78rem;
    color: #9ecbff;
    margin: 0.15rem 0.2rem 0.15rem 0;
  }
  div[data-testid="stChatInput"] textarea {
    background: #121820 !important;
    border: 1px solid var(--ca-border) !important;
  }
</style>
""",
    unsafe_allow_html=True,
)


def _init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "traces" not in st.session_state:
        st.session_state.traces = []
    if "file_views" not in st.session_state:
        st.session_state.file_views = []
    if "selected_file" not in st.session_state:
        st.session_state.selected_file = None
    if "workspace" not in st.session_state:
        st.session_state.workspace = str(resolve_workspace())
    if "model" not in st.session_state:
        st.session_state.model = MODEL_NAME


def _read_selected(workspace: Path) -> tuple[str, str]:
    rel = st.session_state.selected_file
    if not rel:
        return "", ""
    path = (workspace / rel).resolve()
    try:
        path.relative_to(workspace.resolve())
    except ValueError:
        return "", ""
    if not path.is_file():
        return "", ""
    try:
        return path.read_text(encoding="utf-8", errors="replace"), Path(rel).suffix
    except OSError:
        return "", ""


def _render_tool_html(name: str, arguments: dict, result: str | None = None, ok: bool = True) -> str:
    args_preview = escape(str(arguments)[:400])
    body = f'<div class="ca-tool"><span class="name">{escape(name)}</span> {args_preview}'
    if result is not None:
        flag = "ok" if ok else "err"
        body += f"<pre style='white-space:pre-wrap;margin:0.4rem 0 0;color:#c5d0db'>({flag}) {escape(result[:1200])}</pre>"
    body += "</div>"
    return body


def _sidebar(workspace: Path) -> None:
    st.markdown('<div class="ca-brand">CODING AGENT</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ca-sub">deepagents-code · Ollama · visible code & tools</div>',
        unsafe_allow_html=True,
    )

    models = list_models() or [MODEL_NAME]
    default_idx = models.index(st.session_state.model) if st.session_state.model in models else 0
    st.session_state.model = st.selectbox("Model", models, index=default_idx)

    ws_in = st.text_input("Workspace", value=st.session_state.workspace)
    if ws_in.strip() and ws_in.strip() != st.session_state.workspace:
        st.session_state.workspace = str(resolve_workspace(ws_in.strip()))
        st.rerun()

    ok = ollama_available()
    st.caption(f"Ollama: {'connected' if ok else 'offline'} · {st.session_state.model}")

    st.markdown('<div class="ca-panel-title">Files</div>', unsafe_allow_html=True)
    entries = tree_snapshot(workspace)
    if not entries:
        st.caption("(empty workspace)")
    for entry in entries:
        is_dir = entry.endswith("/")
        label = entry
        if is_dir:
            st.markdown(f"`{label}`")
            continue
        if st.button(label, key=f"file-{label}", use_container_width=True):
            st.session_state.selected_file = label
            st.rerun()

    st.divider()
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.traces = []
        st.session_state.file_views = []
        st.rerun()

    st.caption("Runtime: deepagents-code · UI inspired by tasking-agent.")


def _example_prompts() -> None:
    st.markdown('<div class="ca-panel-title">Example prompts</div>', unsafe_allow_html=True)
    examples = [
        "이 깃에서처럼 deep agent editor (deepagents-code) 스타일로 prompt 입력창 생성해줘",
        "workspace에 hello.py를 만들고 실행해줘",
        "현재 파일 트리를 보고 README.md 초안을 작성해줘",
    ]
    cols = st.columns(len(examples))
    for i, (col, text) in enumerate(zip(cols, examples)):
        with col:
            if st.button(text[:42] + ("…" if len(text) > 42 else ""), key=f"ex-{i}"):
                st.session_state._pending_prompt = text


def main() -> None:
    _init_state()
    workspace = resolve_workspace(st.session_state.workspace)
    st.session_state.workspace = str(workspace)

    with st.sidebar:
        _sidebar(workspace)

    # Three panes: chat | code | traces
    chat_col, code_col, trace_col = st.columns([1.15, 1.15, 0.9], gap="medium")

    with chat_col:
        st.markdown('<div class="ca-panel-title">Chat · Prompt</div>', unsafe_allow_html=True)
        _example_prompts()

        for msg in st.session_state.messages:
            role = msg.get("role", "assistant")
            with st.chat_message(role if role in {"user", "assistant"} else "assistant"):
                if role == "tool":
                    st.markdown(
                        _render_tool_html(
                            msg.get("name", "tool"),
                            msg.get("arguments") or {},
                            msg.get("content"),
                            msg.get("ok", True),
                        ),
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(msg.get("content") or "")

        pending = st.session_state.pop("_pending_prompt", None)
        prompt = st.chat_input(
            "Ask the coding agent… (e.g. deepagents-code style prompt editor)"
        )
        user_text = pending or prompt

        if user_text:
            st.session_state.messages.append({"role": "user", "content": user_text})
            with st.chat_message("user"):
                st.markdown(user_text)

            history = [
                m
                for m in st.session_state.messages[:-1]
                if m.get("role") in {"user", "assistant"} and m.get("content")
            ]

            assistant_chunks: list[str] = []
            with st.chat_message("assistant"):
                status_box = st.status("Running agent…", expanded=True)
                live = st.empty()
                for event in run_agent(
                    user_text,
                    workspace,
                    history=history,
                    model=st.session_state.model,
                ):
                    et = event.type
                    data = event.data
                    if et == "status":
                        status_box.update(label=data.get("message") or "…", state="running")
                    elif et == "thinking":
                        st.session_state.traces.append(
                            {"step": "thinking", "detail": data.get("text", "")[:2000]}
                        )
                    elif et == "trace":
                        st.session_state.traces.append(
                            {
                                "step": data.get("step"),
                                "detail": data.get("detail", ""),
                                **{
                                    k: v
                                    for k, v in data.items()
                                    if k not in {"step", "detail"}
                                },
                            }
                        )
                    elif et == "assistant_delta":
                        assistant_chunks.append(data.get("text") or "")
                        live.markdown("\n\n".join(assistant_chunks))
                    elif et == "assistant_end":
                        text = data.get("text") or "\n\n".join(assistant_chunks)
                        if text and (
                            not st.session_state.messages
                            or st.session_state.messages[-1].get("content") != text
                        ):
                            st.session_state.messages.append(
                                {"role": "assistant", "content": text}
                            )
                    elif et == "tool_call":
                        st.session_state.messages.append(
                            {
                                "role": "tool",
                                "name": data.get("name"),
                                "arguments": data.get("arguments") or {},
                                "content": None,
                                "ok": True,
                            }
                        )
                        st.markdown(
                            _render_tool_html(
                                data.get("name") or "tool",
                                data.get("arguments") or {},
                            ),
                            unsafe_allow_html=True,
                        )
                    elif et == "tool_result":
                        # Update last matching tool bubble content
                        for m in reversed(st.session_state.messages):
                            if m.get("role") == "tool" and m.get("content") is None:
                                m["content"] = data.get("content")
                                m["ok"] = data.get("ok", True)
                                break
                        st.markdown(
                            _render_tool_html(
                                data.get("name") or "tool",
                                {},
                                data.get("content"),
                                data.get("ok", True),
                            ),
                            unsafe_allow_html=True,
                        )
                        art = data.get("artifact") or {}
                        if art.get("path") and art.get("kind") == "file":
                            st.session_state.file_views.append(art)
                            st.session_state.selected_file = art["path"]
                            st.markdown(
                                f'<span class="ca-file-chip">{escape(art["path"])}</span>',
                                unsafe_allow_html=True,
                            )
                    elif et == "file_view":
                        st.session_state.file_views.append(data)
                        if data.get("path"):
                            st.session_state.selected_file = data["path"]
                    elif et == "error":
                        st.error(data.get("message") or "error")
                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": f"⚠️ {data.get('message')}",
                            }
                        )
                    elif et == "done":
                        status_box.update(label="Done", state="complete")

            st.rerun()

    with code_col:
        st.markdown('<div class="ca-panel-title">Code · Artifacts</div>', unsafe_allow_html=True)
        selected = st.session_state.selected_file
        if selected:
            st.markdown(f'<span class="ca-file-chip">{escape(selected)}</span>', unsafe_allow_html=True)
            text, _sfx = _read_selected(workspace)
            # Prefer latest in-memory artifact if fresher
            for art in reversed(st.session_state.file_views):
                if art.get("path") == selected and art.get("content") is not None:
                    text = str(art["content"])
                    before = art.get("before")
                    if before is not None and before != text:
                        st.caption("Diff (before → after)")
                        diff = difflib.unified_diff(
                            str(before).splitlines(),
                            text.splitlines(),
                            fromfile="before",
                            tofile="after",
                            lineterm="",
                        )
                        st.code("\n".join(list(diff)[:200]) or "(no textual diff)", language="diff")
                    break
            lang = Path(selected).suffix.lstrip(".") or None
            st.code(text if text else "(empty or unreadable)", language=lang)
        else:
            st.info("파일이 선택되거나 에이전트가 파일을 읽/쓰면 여기에 코드가 표시됩니다.")

        if st.session_state.file_views:
            st.markdown('<div class="ca-panel-title">Recent file ops</div>', unsafe_allow_html=True)
            for art in reversed(st.session_state.file_views[-8:]):
                path = art.get("path") or "?"
                action = art.get("action") or "view"
                if st.button(f"{action}: {path}", key=f"art-{path}-{action}-{id(art)}"):
                    st.session_state.selected_file = path
                    st.rerun()

    with trace_col:
        st.markdown('<div class="ca-panel-title">Tracing</div>', unsafe_allow_html=True)
        if not st.session_state.traces:
            st.caption("Tool / LLM steps appear here.")
        for i, tr in enumerate(reversed(st.session_state.traces[-40:]), 1):
            step = tr.get("step") or "event"
            detail = tr.get("detail") or ""
            with st.expander(f"{step}", expanded=(i <= 3)):
                st.write(detail)
                extra = {k: v for k, v in tr.items() if k not in {"step", "detail"}}
                if extra:
                    st.json(extra)


if __name__ == "__main__":
    main()
