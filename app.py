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
    page_title="KETI Coding Agent",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _inject_theme(theme: str) -> None:
    """Light = previous soft workbench. Dark = full dark with readable contrast."""
    if theme == "Dark":
        # Original cohesive dark workbench (full page dark + readable text)
        css = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
  :root {
    --ca-bg: #0f1419;
    --ca-panel: #151b23;
    --ca-sidebar: #121820;
    --ca-border: #2a3340;
    --ca-accent: #3d9a6a;
    --ca-text: #e6edf3;
    --ca-muted: #8b9bab;
    --ca-tool: #1c2430;
    --ca-chip-bg: #1a2330;
    --ca-chip-border: #2a3340;
    --ca-input-bg: #121820;
    --ca-hover: #1c2430;
  }
  html, body, [class*="css"] {
    font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
  }
  .stApp,
  [data-testid="stAppViewContainer"],
  [data-testid="stMain"],
  section.main,
  .main,
  .block-container {
    background: linear-gradient(160deg, #0f1419 0%, #121820 45%, #0d1a16 100%) !important;
    color: var(--ca-text) !important;
  }
  .stApp p, .stApp span, .stApp label, .stApp li,
  .stMarkdown, .stMarkdown p, .stCaption,
  [data-testid="stMarkdownContainer"],
  [data-testid="stMarkdownContainer"] h1,
  [data-testid="stMarkdownContainer"] h2,
  [data-testid="stMarkdownContainer"] h3,
  [data-testid="stMarkdownContainer"] strong,
  [data-testid="stWidgetLabel"] p,
  [data-testid="stChatMessageContent"] {
    color: var(--ca-text) !important;
  }
  [data-testid="stMarkdownContainer"] a { color: #7dcea0 !important; }
  [data-testid="stSidebar"] {
    background: var(--ca-sidebar) !important;
    border-right: 1px solid var(--ca-border);
  }
  [data-testid="stSidebar"] * { color: var(--ca-text) !important; }
  [data-testid="stHeader"] { background: transparent !important; }
  [data-testid="stChatMessage"] {
    background: var(--ca-panel) !important;
    border: 1px solid var(--ca-border);
    border-radius: 8px;
  }
  /* Select / input: dark surface + light text (no dark-on-dark) */
  [data-baseweb="select"] > div,
  [data-baseweb="select"] > div > div,
  [data-baseweb="input"] input,
  [data-baseweb="base-input"],
  .stTextInput input {
    background-color: #1c2430 !important;
    color: #e6edf3 !important;
    border-color: var(--ca-border) !important;
  }
  [data-baseweb="popover"] li, [data-baseweb="menu"] li {
    background-color: #151b23 !important;
    color: #e6edf3 !important;
  }
  .stButton > button {
    background-color: #1c2430 !important;
    color: #e6edf3 !important;
    border: 1px solid var(--ca-border) !important;
  }
  .stButton > button:hover {
    background-color: #243040 !important;
    border-color: var(--ca-accent) !important;
  }
  .stButton > button[kind="primary"] {
    background-color: #238636 !important;
    border-color: #238636 !important;
    color: #fff !important;
  }
  div[data-testid="stChatInput"] {
    background: transparent !important;
  }
  div[data-testid="stChatInput"] textarea {
    background: var(--ca-input-bg) !important;
    border: 1px solid var(--ca-border) !important;
    color: var(--ca-text) !important;
  }
  div[data-testid="stChatInput"] textarea::placeholder {
    color: var(--ca-muted) !important;
  }
  .ca-brand {
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 0.95rem;
    font-weight: 500;
    letter-spacing: 0.04em;
    color: var(--ca-accent) !important;
    margin: 0 0 0.15rem;
  }
  .ca-sub { color: var(--ca-muted) !important; font-size: 0.78rem; margin-bottom: 0.85rem; }
  .ca-section {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.06em;
    text-transform: uppercase; color: var(--ca-muted) !important; margin: 0.9rem 0 0.4rem;
  }
  .ca-tool {
    background: var(--ca-tool); border: 1px solid var(--ca-border);
    border-left: 3px solid var(--ca-accent); border-radius: 6px;
    padding: 0.45rem 0.65rem; margin: 0.3rem 0;
    font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.78rem;
    color: var(--ca-text) !important;
  }
  .ca-tool .name { color: #7dcea0 !important; font-weight: 500; }
  .ca-tool pre { white-space: pre-wrap; margin: 0.35rem 0 0; color: var(--ca-muted) !important; font-size: 0.74rem; }
  .ca-file-chip {
    display: inline-block; font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 0.78rem; color: #9ecbff !important;
    background: var(--ca-chip-bg); border: 1px solid var(--ca-chip-border);
    padding: 0.12rem 0.45rem; border-radius: 4px; margin-bottom: 0.5rem;
  }
  .ca-empty { color: var(--ca-muted) !important; font-size: 0.9rem; padding: 1.2rem 0.2rem; }
  [data-testid="stSidebar"] .stButton > button {
    justify-content: flex-start; text-align: left;
    font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.78rem; font-weight: 400;
    border: 1px solid transparent !important; background: transparent !important;
    color: var(--ca-text) !important; padding: 0.2rem 0.4rem; min-height: 1.7rem;
  }
  [data-testid="stSidebar"] .stButton > button:hover {
    background: var(--ca-hover) !important; border-color: var(--ca-border) !important;
  }
  div[data-baseweb="tab"] button { color: var(--ca-muted) !important; }
  div[data-baseweb="tab"] button[aria-selected="true"] { color: var(--ca-text) !important; }
  [data-testid="stExpander"] summary { color: var(--ca-text) !important; }
  .stSelectbox label, .stTextInput label, .stToggle label { color: var(--ca-muted) !important; }
  .block-container { padding-top: 1.2rem; padding-bottom: 1.5rem; }
</style>
"""
    else:
        # Previous Light workbench (unchanged look)
        css = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
  :root {
    --ca-bg: #f4f5f7;
    --ca-panel: #ffffff;
    --ca-sidebar: #eceef1;
    --ca-border: #dde1e6;
    --ca-accent: #0f7b6c;
    --ca-text: #1f2328;
    --ca-muted: #656d76;
    --ca-tool: #f6f8fa;
    --ca-code-bg: #f6f8fa;
  }
  html, body, [class*="css"] {
    font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
  }
  .stApp {
    background:
      radial-gradient(1200px 500px at 10% -10%, #e8f3ef 0%, transparent 55%),
      radial-gradient(900px 400px at 100% 0%, #eef1f6 0%, transparent 50%),
      var(--ca-bg);
  }
  [data-testid="stSidebar"] {
    background: var(--ca-sidebar);
    border-right: 1px solid var(--ca-border);
  }
  [data-testid="stSidebar"] * { color: var(--ca-text); }
  [data-testid="stHeader"] { background: transparent; }
  .ca-brand {
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 0.95rem;
    font-weight: 500;
    letter-spacing: 0.06em;
    color: var(--ca-accent);
    margin: 0 0 0.15rem;
  }
  .ca-sub { color: var(--ca-muted); font-size: 0.78rem; margin-bottom: 0.85rem; }
  .ca-section {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.06em;
    text-transform: uppercase; color: var(--ca-muted); margin: 0.9rem 0 0.4rem;
  }
  .ca-tool {
    background: var(--ca-tool); border: 1px solid var(--ca-border);
    border-left: 3px solid var(--ca-accent); border-radius: 6px;
    padding: 0.45rem 0.65rem; margin: 0.3rem 0;
    font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.78rem;
    color: var(--ca-text);
  }
  .ca-tool .name { color: var(--ca-accent); font-weight: 500; }
  .ca-tool pre {
    white-space: pre-wrap; margin: 0.35rem 0 0; color: var(--ca-muted); font-size: 0.74rem;
  }
  .ca-file-chip {
    display: inline-block; font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 0.78rem; color: var(--ca-accent);
    background: #e7f4f1; border: 1px solid #c7e6df;
    padding: 0.12rem 0.45rem; border-radius: 4px; margin-bottom: 0.5rem;
  }
  .ca-empty { color: var(--ca-muted); font-size: 0.9rem; padding: 1.2rem 0.2rem; }
  div[data-testid="stChatInput"] textarea {
    background: #fff !important;
    border: 1px solid var(--ca-border) !important;
    color: var(--ca-text) !important;
  }
  [data-testid="stSidebar"] .stButton > button {
    justify-content: flex-start; text-align: left;
    font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.78rem; font-weight: 400;
    border: 1px solid transparent; background: transparent; color: var(--ca-text);
    padding: 0.2rem 0.4rem; min-height: 1.7rem;
  }
  [data-testid="stSidebar"] .stButton > button:hover {
    background: #e2e6eb; border-color: var(--ca-border);
  }
  .block-container { padding-top: 1.2rem; padding-bottom: 1.5rem; }
</style>
"""
    st.markdown(css, unsafe_allow_html=True)


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
    if "show_trace" not in st.session_state:
        st.session_state.show_trace = False
    if "theme" not in st.session_state:
        st.session_state.theme = "Light"


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
    short_args = escape(str(arguments)[:180])
    body = f'<div class="ca-tool"><span class="name">{escape(name)}</span> {short_args}'
    if result is not None:
        flag = "ok" if ok else "err"
        body += f"<pre>({flag}) {escape(result[:500])}</pre>"
    body += "</div>"
    return body


def _should_keep_trace(step: str | None) -> bool:
    s = (step or "").lower()
    if s in {"middleware", "start", "complete"}:
        return False
    if "middleware" in s:
        return False
    return True


def _consume_events(events, status_box, live, assistant_chunks: list[str]) -> None:
    for event in events:
        et = event.type
        data = event.data
        if et == "status":
            status_box.update(label=data.get("message") or "…", state="running")
        elif et == "thinking":
            pass  # keep chat clean; details stay in optional Trace
        elif et == "trace":
            if _should_keep_trace(data.get("step")):
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
        elif et == "tool_result":
            for m in reversed(st.session_state.messages):
                if m.get("role") == "tool" and m.get("content") is None:
                    m["content"] = data.get("content")
                    m["ok"] = data.get("ok", True)
                    break
            # Live compact line (avoid double giant blocks)
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
        elif et == "file_change":
            st.session_state.file_changes.append(data)
            if data.get("path"):
                st.session_state.selected_file = data["path"]
        elif et == "test_result":
            st.session_state.test_results.append(data)
        elif et == "interrupt":
            st.session_state.pending_interrupt = data
        elif et == "error":
            st.error(data.get("message") or "error")
            st.session_state.messages.append(
                {"role": "assistant", "content": f"Error: {data.get('message')}"}
            )
        elif et == "done":
            interrupted = bool(data.get("interrupted"))
            status_box.update(
                label="Waiting for approval" if interrupted else "Done",
                state="complete",
            )


def _sidebar(workspace: Path) -> None:
    st.markdown('<div class="ca-brand">KETI Coding Agent</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="ca-sub">deepagents-code {escape(deepagents_version())}</div>',
        unsafe_allow_html=True,
    )

    store = _store()
    st.markdown('<div class="ca-section">Thread</div>', unsafe_allow_html=True)
    threads = store.list_threads()
    labels = {t["id"]: (t.get("title") or t["id"][:8])[:40] for t in threads}
    ids = [t["id"] for t in threads]
    if ids:
        idx = ids.index(st.session_state.thread_id) if st.session_state.thread_id in ids else 0
        chosen = st.selectbox(
            "Thread",
            ids,
            index=idx,
            format_func=lambda i: labels.get(i, i),
            label_visibility="collapsed",
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

    with st.expander("Settings", expanded=False):
        st.radio(
            "Theme",
            ["Light", "Dark"],
            horizontal=True,
            key="theme",
        )
        models = list_models() or [MODEL_NAME]
        default_idx = (
            models.index(st.session_state.model) if st.session_state.model in models else 0
        )
        st.session_state.model = st.selectbox("Model", models, index=default_idx)
        st.session_state.auto_approve = st.toggle(
            "Auto-approve tools",
            value=st.session_state.auto_approve,
            help="Off = approve execute / write / edit / delete",
        )
        st.session_state.show_trace = st.toggle(
            "Show activity trace",
            value=st.session_state.show_trace,
        )
        ws_in = st.text_input("Workspace", value=st.session_state.workspace)
        if ws_in.strip() and ws_in.strip() != st.session_state.workspace:
            st.session_state.workspace = str(resolve_workspace(ws_in.strip()))
            st.cache_resource.clear()
            st.rerun()
        ok = ollama_available()
        st.caption(
            f"{'●' if ok else '○'} {st.session_state.model} · {st.session_state.thread_id[:8]}"
        )
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.traces = []
            st.session_state.file_views = []
            st.session_state.file_changes = []
            st.session_state.test_results = []
            st.session_state.pending_interrupt = None
            _persist_messages()
            st.rerun()

    st.markdown('<div class="ca-section">Files</div>', unsafe_allow_html=True)
    entries = [e for e in tree_snapshot(workspace) if not e.endswith("/")]
    if not entries:
        st.caption("Empty workspace")
    else:
        options = ["—"] + entries
        current = st.session_state.selected_file if st.session_state.selected_file in entries else "—"
        picked = st.selectbox(
            "Open file",
            options,
            index=options.index(current) if current in options else 0,
            label_visibility="collapsed",
        )
        if picked != "—" and picked != st.session_state.selected_file:
            st.session_state.selected_file = picked
            st.rerun()
        for entry in entries[:40]:
            label = f"› {entry}" if entry == st.session_state.selected_file else entry
            if st.button(label, key=f"file-{entry}", use_container_width=True):
                st.session_state.selected_file = entry
                st.rerun()


def _example_prompts() -> None:
    if st.session_state.messages:
        return
    examples = [
        ("Prompt editor UI 만들기", "deepagents-code 스타일 prompt 입력창 HTML을 workspace에 만들어줘"),
        ("hello.py 만들고 실행", "workspace에 hello.py를 만들고 실행해줘"),
        ("README 초안", "현재 파일 트리를 보고 README.md 초안을 작성해줘"),
    ]
    cols = st.columns(len(examples))
    for i, (col, (label, text)) in enumerate(zip(cols, examples)):
        with col:
            if st.button(label, key=f"ex-{i}", use_container_width=True):
                st.session_state._pending_prompt = text


def _approval_panel(bridge: DeepAgentsBridge) -> None:
    pending = st.session_state.pending_interrupt
    if not pending:
        return
    st.info("도구 실행 승인이 필요합니다.")
    actions = pending.get("action_requests") or []
    for ar in actions:
        st.markdown(
            _render_tool_html(ar.get("name") or "tool", ar.get("args") or {}),
            unsafe_allow_html=True,
        )
    a1, a2 = st.columns(2)
    with a1:
        if st.button("Approve", type="primary", use_container_width=True):
            decisions = [{"type": "approve"} for _ in actions] or [{"type": "approve"}]
            st.session_state.pending_interrupt = None
            assistant_chunks: list[str] = []
            with st.chat_message("assistant"):
                status_box = st.status("Resuming…", expanded=False)
                live = st.empty()
                _consume_events(
                    bridge.resume(thread_id=st.session_state.thread_id, decisions=decisions),
                    status_box,
                    live,
                    assistant_chunks,
                )
            _persist_messages()
            st.rerun()
    with a2:
        if st.button("Reject", use_container_width=True):
            decisions = [
                {"type": "reject", "message": "Rejected by user"} for _ in actions
            ] or [{"type": "reject", "message": "Rejected by user"}]
            st.session_state.pending_interrupt = None
            assistant_chunks: list[str] = []
            with st.chat_message("assistant"):
                status_box = st.status("Rejecting…", expanded=False)
                live = st.empty()
                _consume_events(
                    bridge.resume(thread_id=st.session_state.thread_id, decisions=decisions),
                    status_box,
                    live,
                    assistant_chunks,
                )
            _persist_messages()
            st.rerun()


def _render_chat_history() -> None:
    for msg in st.session_state.messages:
        role = msg.get("role", "assistant")
        if role == "tool":
            with st.chat_message("assistant"):
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
            with st.chat_message(role):
                st.markdown(msg.get("content") or "")


def _editor_panel(workspace: Path) -> None:
    selected = st.session_state.selected_file
    if not selected:
        st.markdown(
            '<div class="ca-empty">Select a file, or let the agent edit one.</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(f'<span class="ca-file-chip">{escape(selected)}</span>', unsafe_allow_html=True)

    text = _read_selected(workspace)
    for art in reversed(st.session_state.file_views):
        if art.get("path") == selected and art.get("content") is not None:
            text = str(art["content"])
            break

    suffix = Path(selected).suffix.lower()
    body = text if text else "(empty)"

    if suffix == ".md":
        preview_tab, source_tab = st.tabs(["Preview", "Source"])
        with preview_tab:
            st.markdown(body)
        with source_tab:
            st.code(body, language="markdown")
    else:
        lang = suffix.lstrip(".") or None
        st.code(body, language=lang)

    diff = None
    action = None
    for ch in reversed(st.session_state.file_changes):
        if ch.get("path") == selected and ch.get("diff"):
            diff = ch["diff"]
            action = ch.get("action")
            break
    if diff:
        with st.expander(f"Diff ({action or 'change'})", expanded=False):
            st.code(diff, language="diff")

    if st.session_state.file_changes:
        changed = []
        seen = set()
        for ch in reversed(st.session_state.file_changes):
            p = ch.get("path")
            if p and p not in seen:
                seen.add(p)
                changed.append(p)
        if len(changed) > 1:
            pick = st.selectbox("Changed files", changed, key="changed-picker")
            if pick and pick != selected:
                st.session_state.selected_file = pick
                st.rerun()

    if st.session_state.test_results:
        latest = st.session_state.test_results[-1]
        with st.expander(
            ("Verification ok" if latest.get("ok") else "Verification failed"),
            expanded=False,
        ):
            st.code(latest.get("details") or latest.get("summary") or "")


def _trace_panel() -> None:
    if not st.session_state.show_trace:
        return
    with st.expander("Activity", expanded=False):
        useful = [t for t in st.session_state.traces if _should_keep_trace(t.get("step"))]
        if not useful:
            st.caption("No tool activity yet.")
            return
        for tr in reversed(useful[-20:]):
            step = tr.get("step") or "event"
            detail = tr.get("detail") or ""
            st.markdown(f"**{step}** — {detail}" if detail else f"**{step}**")


def main() -> None:
    _init_state()
    _inject_theme(st.session_state.theme)
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

    # Cursor-like: Chat + Editor only (trace optional)
    chat_col, code_col = st.columns([1.2, 1], gap="large")

    with chat_col:
        _example_prompts()
        _approval_panel(bridge)
        _render_chat_history()
        _trace_panel()

        blocked = st.session_state.pending_interrupt is not None
        pending = st.session_state.pop("_pending_prompt", None)
        prompt = None
        if not blocked:
            prompt = st.chat_input("Message the coding agent…")
        else:
            st.caption("Approve or reject to continue.")
        user_text = pending or prompt

        if user_text and not blocked:
            st.session_state.messages.append({"role": "user", "content": user_text})
            with st.chat_message("user"):
                st.markdown(user_text)

            assistant_chunks: list[str] = []
            with st.chat_message("assistant"):
                status_box = st.status("Working…", expanded=False)
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
        _editor_panel(workspace)


if __name__ == "__main__":
    main()
