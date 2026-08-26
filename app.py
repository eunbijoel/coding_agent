from __future__ import annotations

import sys
from html import escape
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coding_agent.bridge import DeepAgentsBridge, deepagents_version
from coding_agent.config import DATA_DIR, MODEL_NAME, resolve_workspace
from coding_agent.ollama_client import available as ollama_available
from coding_agent.ollama_client import list_models
from coding_agent.threads import ThreadStore
from coding_agent.tools import tree_snapshot

st.set_page_config(
    page_title="Coding Agent",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded",
)

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


def _store() -> ThreadStore:
    return ThreadStore(DATA_DIR)


@st.cache_resource(show_spinner=False)
def _bridge(workspace: str, model: str, auto_approve: bool) -> DeepAgentsBridge:
    return DeepAgentsBridge(workspace, model=model, auto_approve=auto_approve)


def _init_state() -> None:
    store = _store()
    if "thread_id" not in st.session_state:
        threads = store.list_threads()
        if threads:
            st.session_state.thread_id = threads[0]["id"]
        else:
            row = store.create(title="Thread 1", model=MODEL_NAME)
            st.session_state.thread_id = row["id"]
    if "messages" not in st.session_state:
        st.session_state.messages = store.load_messages(st.session_state.thread_id)
    if "traces" not in st.session_state:
        st.session_state.traces = []
    if "file_views" not in st.session_state:
        st.session_state.file_views = []
    if "file_changes" not in st.session_state:
        st.session_state.file_changes = []
    if "test_results" not in st.session_state:
        st.session_state.test_results = []
    if "selected_file" not in st.session_state:
        st.session_state.selected_file = None
    if "workspace" not in st.session_state:
        st.session_state.workspace = str(resolve_workspace())
    if "model" not in st.session_state:
        st.session_state.model = MODEL_NAME
    if "auto_approve" not in st.session_state:
        st.session_state.auto_approve = False
    if "pending_interrupt" not in st.session_state:
        st.session_state.pending_interrupt = None


def _persist_messages() -> None:
    _store().save_messages(st.session_state.thread_id, st.session_state.messages)
    title = None
    for m in st.session_state.messages:
        if m.get("role") == "user" and m.get("content"):
            title = str(m["content"]).strip().splitlines()[0]
            break
    _store().touch(
        st.session_state.thread_id,
        title=title,
        model=st.session_state.model,
    )


def _switch_thread(thread_id: str) -> None:
    st.session_state.thread_id = thread_id
    st.session_state.messages = _store().load_messages(thread_id)
    st.session_state.traces = []
    st.session_state.file_views = []
    st.session_state.file_changes = []
    st.session_state.test_results = []
    st.session_state.pending_interrupt = None
    st.rerun()


def _read_selected(workspace: Path) -> str:
    rel = st.session_state.selected_file
    if not rel:
        return ""
    path = (workspace / rel).resolve()
    try:
        path.relative_to(workspace.resolve())
    except ValueError:
        return ""
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _render_tool_html(name: str, arguments: dict, result: str | None = None, ok: bool = True) -> str:
    args_preview = escape(str(arguments)[:400])
    body = f'<div class="ca-tool"><span class="name">{escape(name)}</span> {args_preview}'
    if result is not None:
        flag = "ok" if ok else "err"
        body += (
            f"<pre style='white-space:pre-wrap;margin:0.4rem 0 0;color:#c5d0db'>"
            f"({flag}) {escape(result[:1200])}</pre>"
        )
    body += "</div>"
    return body


def _consume_events(events, status_box, live, assistant_chunks: list[str]) -> None:
    for event in events:
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
                    **{k: v for k, v in data.items() if k not in {"step", "detail"}},
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
                st.session_state.messages.append({"role": "assistant", "content": text})
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
                _render_tool_html(data.get("name") or "tool", data.get("arguments") or {}),
                unsafe_allow_html=True,
            )
        elif et == "tool_result":
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
        elif et == "file_view":
            st.session_state.file_views.append(data)
            if data.get("path"):
                st.session_state.selected_file = data["path"]
                st.markdown(
                    f'<span class="ca-file-chip">{escape(data["path"])}</span>',
                    unsafe_allow_html=True,
                )
        elif et == "file_change":
            st.session_state.file_changes.append(data)
            if data.get("path"):
                st.session_state.selected_file = data["path"]
        elif et == "test_result":
            st.session_state.test_results.append(data)
            if data.get("ok"):
                st.success(data.get("summary") or "tests ok")
            else:
                st.warning(data.get("summary") or "tests failed")
            if data.get("details"):
                with st.expander("Verification details"):
                    st.code(data["details"])
        elif et == "interrupt":
            st.session_state.pending_interrupt = data
            st.warning("도구 실행 승인이 필요합니다.")
        elif et == "error":
            st.error(data.get("message") or "error")
            st.session_state.messages.append(
                {"role": "assistant", "content": f"⚠️ {data.get('message')}"}
            )
        elif et == "done":
            interrupted = bool(data.get("interrupted"))
            status_box.update(
                label="Waiting for approval" if interrupted else "Done",
                state="complete",
            )


def _sidebar(workspace: Path) -> None:
    st.markdown('<div class="ca-brand">CODING AGENT</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="ca-sub">deepagents-code {escape(deepagents_version())} · Ollama</div>',
        unsafe_allow_html=True,
    )

    store = _store()
    st.markdown('<div class="ca-panel-title">Threads</div>', unsafe_allow_html=True)
    threads = store.list_threads()
    labels = {t["id"]: f"{t.get('title') or t['id'][:8]}" for t in threads}
    ids = [t["id"] for t in threads]
    if ids:
        idx = ids.index(st.session_state.thread_id) if st.session_state.thread_id in ids else 0
        chosen = st.selectbox(
            "Resume thread",
            ids,
            index=idx,
            format_func=lambda i: labels.get(i, i),
        )
        if chosen != st.session_state.thread_id:
            _switch_thread(chosen)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("New", use_container_width=True):
            row = store.create(title="New thread", model=st.session_state.model)
            _switch_thread(row["id"])
    with c2:
        if st.button("Delete", use_container_width=True) and st.session_state.thread_id:
            store.delete(st.session_state.thread_id)
            remaining = store.list_threads()
            if not remaining:
                remaining = [store.create(title="Thread 1", model=st.session_state.model)]
            _switch_thread(remaining[0]["id"])

    models = list_models() or [MODEL_NAME]
    default_idx = models.index(st.session_state.model) if st.session_state.model in models else 0
    st.session_state.model = st.selectbox("Model", models, index=default_idx)
    st.session_state.auto_approve = st.toggle(
        "Auto-approve tools",
        value=st.session_state.auto_approve,
        help="Off = deepagents-code HITL for execute / write_file / edit_file / delete",
    )

    ws_in = st.text_input("Workspace", value=st.session_state.workspace)
    if ws_in.strip() and ws_in.strip() != st.session_state.workspace:
        st.session_state.workspace = str(resolve_workspace(ws_in.strip()))
        st.cache_resource.clear()
        st.rerun()

    ok = ollama_available()
    st.caption(
        f"Ollama: {'connected' if ok else 'offline'} · "
        f"{st.session_state.model} · thread {st.session_state.thread_id[:8]}"
    )

    st.markdown('<div class="ca-panel-title">Files</div>', unsafe_allow_html=True)
    entries = tree_snapshot(workspace)
    if not entries:
        st.caption("(empty workspace)")
    for entry in entries:
        if entry.endswith("/"):
            st.markdown(f"`{entry}`")
            continue
        if st.button(entry, key=f"file-{entry}", use_container_width=True):
            st.session_state.selected_file = entry
            st.rerun()

    st.divider()
    if st.button("Clear UI messages", use_container_width=True):
        st.session_state.messages = []
        st.session_state.traces = []
        st.session_state.file_views = []
        st.session_state.file_changes = []
        st.session_state.test_results = []
        st.session_state.pending_interrupt = None
        _persist_messages()
        st.rerun()

    st.caption("Runtime: deepagents-code create_cli_agent (Bridge).")


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


def _approval_panel(bridge: DeepAgentsBridge) -> None:
    pending = st.session_state.pending_interrupt
    if not pending:
        return
    st.markdown('<div class="ca-panel-title">Approval required</div>', unsafe_allow_html=True)
    actions = pending.get("action_requests") or []
    for i, ar in enumerate(actions):
        st.markdown(
            _render_tool_html(ar.get("name") or "tool", ar.get("args") or {}),
            unsafe_allow_html=True,
        )
        if ar.get("description"):
            st.caption(ar["description"])

    a1, a2 = st.columns(2)
    with a1:
        if st.button("Approve all", type="primary", use_container_width=True):
            decisions = [{"type": "approve"} for _ in actions] or [{"type": "approve"}]
            st.session_state.pending_interrupt = None
            assistant_chunks: list[str] = []
            with st.chat_message("assistant"):
                status_box = st.status("Resuming…", expanded=True)
                live = st.empty()
                _consume_events(
                    bridge.resume(
                        thread_id=st.session_state.thread_id,
                        decisions=decisions,
                    ),
                    status_box,
                    live,
                    assistant_chunks,
                )
            _persist_messages()
            st.rerun()
    with a2:
        if st.button("Reject all", use_container_width=True):
            decisions = [
                {"type": "reject", "message": "Rejected by user in Coding Agent UI"}
                for _ in actions
            ] or [{"type": "reject", "message": "Rejected by user"}]
            st.session_state.pending_interrupt = None
            assistant_chunks = []
            with st.chat_message("assistant"):
                status_box = st.status("Rejecting…", expanded=True)
                live = st.empty()
                _consume_events(
                    bridge.resume(
                        thread_id=st.session_state.thread_id,
                        decisions=decisions,
                    ),
                    status_box,
                    live,
                    assistant_chunks,
                )
            _persist_messages()
            st.rerun()


def main() -> None:
    _init_state()
    workspace = resolve_workspace(st.session_state.workspace)
    st.session_state.workspace = str(workspace)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    bridge = _bridge(
        str(workspace),
        st.session_state.model,
        bool(st.session_state.auto_approve),
    )

    with st.sidebar:
        _sidebar(workspace)

    chat_col, code_col, trace_col = st.columns([1.15, 1.15, 0.9], gap="medium")

    with chat_col:
        st.markdown('<div class="ca-panel-title">Chat · Prompt</div>', unsafe_allow_html=True)
        _example_prompts()
        _approval_panel(bridge)

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

        blocked = st.session_state.pending_interrupt is not None
        pending = st.session_state.pop("_pending_prompt", None)
        prompt = None
        if not blocked:
            prompt = st.chat_input("Ask the coding agent… (deepagents-code runtime)")
        else:
            st.info("승인 또는 거절 후 계속할 수 있습니다.")
        user_text = pending or prompt

        if user_text and not blocked:
            st.session_state.messages.append({"role": "user", "content": user_text})
            with st.chat_message("user"):
                st.markdown(user_text)

            assistant_chunks: list[str] = []
            with st.chat_message("assistant"):
                status_box = st.status("Running deepagents-code…", expanded=True)
                live = st.empty()
                _consume_events(
                    bridge.run(user_text, thread_id=st.session_state.thread_id),
                    status_box,
                    live,
                    assistant_chunks,
                )
            _persist_messages()
            st.rerun()

    with code_col:
        st.markdown('<div class="ca-panel-title">Code · Artifacts</div>', unsafe_allow_html=True)
        selected = st.session_state.selected_file
        if selected:
            st.markdown(
                f'<span class="ca-file-chip">{escape(selected)}</span>',
                unsafe_allow_html=True,
            )
            text = _read_selected(workspace)
            for art in reversed(st.session_state.file_views):
                if art.get("path") == selected and art.get("content") is not None:
                    text = str(art["content"])
                    break
            for ch in reversed(st.session_state.file_changes):
                if ch.get("path") == selected and ch.get("diff"):
                    st.caption(f"Diff ({ch.get('action')})")
                    st.code(ch["diff"], language="diff")
                    break
            lang = Path(selected).suffix.lstrip(".") or None
            st.code(text if text else "(empty or unreadable)", language=lang)
        else:
            st.info("파일이 선택되거나 에이전트가 파일을 바꾸면 여기에 표시됩니다.")

        if st.session_state.file_changes:
            st.markdown('<div class="ca-panel-title">Changed files</div>', unsafe_allow_html=True)
            for ch in reversed(st.session_state.file_changes[-12:]):
                path = ch.get("path") or "?"
                action = ch.get("action") or "modify"
                if st.button(f"{action}: {path}", key=f"chg-{path}-{action}-{id(ch)}"):
                    st.session_state.selected_file = path
                    st.rerun()

        if st.session_state.test_results:
            st.markdown('<div class="ca-panel-title">Verification</div>', unsafe_allow_html=True)
            latest = st.session_state.test_results[-1]
            st.write(("✅ " if latest.get("ok") else "❌ ") + (latest.get("summary") or ""))
            if latest.get("details"):
                st.code(latest["details"])

    with trace_col:
        st.markdown('<div class="ca-panel-title">Tracing</div>', unsafe_allow_html=True)
        if not st.session_state.traces:
            st.caption("deepagents-code tool / LLM steps appear here.")
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
