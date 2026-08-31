from __future__ import annotations

import shlex
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
from coding_agent.tools import IGNORE_DIR_NAMES, IGNORE_SUFFIXES
from coding_agent.workbench import (
    classify_file,
    detect_preview_kind,
    poll_preview,
    poll_user_terminal,
    read_workspace_text,
    resolve_workspace_file,
    start_preview_process,
    start_user_command_bg,
    stop_process,
    stop_user_terminal,
    unified_diff,
    validate_user_command,
    write_workspace_text,
)

st.set_page_config(
    page_title="KETI Coding Agent",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Enables per-panel scroll regions; CSS overrides to viewport height.
PANEL_SCROLL_HEIGHT = 720


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
  .ca-brand,
  .ca-brand-link,
  .ca-brand-link:visited {
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 0.95rem;
    font-weight: 500;
    letter-spacing: 0.04em;
    color: var(--ca-accent) !important;
    margin: 0 0 0.15rem;
    display: block;
    text-decoration: none;
  }
  .ca-brand-link:hover {
    color: #7dcea0 !important;
    text-decoration: none;
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
  section.main .block-container { padding-top: 0.65rem !important; padding-bottom: 0.5rem !important; }
  .ca-new-chat-hint {
    color: var(--ca-muted) !important;
    font-size: 1.05rem;
    padding: 0.75rem 0 0.5rem;
  }
  section.main div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid var(--ca-border) !important;
    border-radius: 8px !important;
    background: var(--ca-panel) !important;
    padding: 0.5rem 0.65rem !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
  }
  section.main div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
    height: calc(100vh - 9.5rem) !important;
    max-height: calc(100vh - 9.5rem) !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    box-sizing: border-box !important;
  }
  section.main div[data-testid="column"] { align-self: stretch !important; }
  .ca-wb-header [data-testid="stMarkdownContainer"] p { margin-bottom: 0.1rem !important; }
  .ca-wb-actions .stButton > button {
    white-space: nowrap !important;
    min-width: 2.4rem !important;
    padding: 0.2rem 0.5rem !important;
    font-size: 0.82rem !important;
  }
  section.main [data-testid="stExpander"] { margin-top: 0.25rem !important; margin-bottom: 0.25rem !important; }
  [data-testid="stSidebar"] .streamlit-expanderHeader {
    font-family: "IBM Plex Mono", ui-monospace, monospace !important;
    font-size: 0.76rem !important;
    padding: 0.15rem 0 !important;
  }
  [data-testid="stSidebar"] [data-testid="stExpander"] { margin-bottom: 0.15rem !important; }
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
  .ca-brand,
  .ca-brand-link,
  .ca-brand-link:visited {
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 0.95rem;
    font-weight: 500;
    letter-spacing: 0.06em;
    color: var(--ca-accent);
    margin: 0 0 0.15rem;
    display: block;
    text-decoration: none;
  }
  .ca-brand-link:hover {
    color: #0a5c50;
    text-decoration: none;
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
  section.main .block-container { padding-top: 0.65rem !important; padding-bottom: 0.5rem !important; }
  .ca-new-chat-hint {
    color: var(--ca-muted) !important;
    font-size: 1.05rem;
    padding: 0.75rem 0 0.5rem;
  }
  section.main div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid var(--ca-border) !important;
    border-radius: 8px !important;
    background: var(--ca-panel) !important;
    padding: 0.5rem 0.65rem !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
  }
  section.main div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
    height: calc(100vh - 9.5rem) !important;
    max-height: calc(100vh - 9.5rem) !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    box-sizing: border-box !important;
  }
  section.main div[data-testid="column"] { align-self: stretch !important; }
  .ca-wb-header [data-testid="stMarkdownContainer"] p { margin-bottom: 0.1rem !important; }
  .ca-wb-actions .stButton > button {
    white-space: nowrap !important;
    min-width: 2.4rem !important;
    padding: 0.2rem 0.5rem !important;
    font-size: 0.82rem !important;
  }
  section.main [data-testid="stExpander"] { margin-top: 0.25rem !important; margin-bottom: 0.25rem !important; }
  [data-testid="stSidebar"] .streamlit-expanderHeader {
    font-family: "IBM Plex Mono", ui-monospace, monospace !important;
    font-size: 0.76rem !important;
    padding: 0.15rem 0 !important;
  }
  [data-testid="stSidebar"] [data-testid="stExpander"] { margin-bottom: 0.15rem !important; }
</style>
"""
    st.markdown(css, unsafe_allow_html=True)


def _store() -> ThreadStore:
    return ThreadStore(DATA_DIR)


@st.cache_resource(show_spinner=False)
def _bridge(workspace: str, model: str, auto_approve: bool) -> DeepAgentsBridge:
    return DeepAgentsBridge(workspace, model=model, auto_approve=auto_approve)


def _init_state() -> None:
    if "new_chat_mode" not in st.session_state:
        st.session_state.new_chat_mode = True
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
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
    if "theme" not in st.session_state:
        st.session_state.theme = "Light"
    if "editor_draft" not in st.session_state:
        st.session_state.editor_draft = ""
    if "editor_draft_path" not in st.session_state:
        st.session_state.editor_draft_path = None
    if "editor_disk" not in st.session_state:
        st.session_state.editor_disk = ""
    if "editor_force_reload" not in st.session_state:
        st.session_state.editor_force_reload = False
    if "editor_pending_save" not in st.session_state:
        st.session_state.editor_pending_save = False
    if "terminal_history" not in st.session_state:
        st.session_state.terminal_history = []
    if "terminal_proc" not in st.session_state:
        st.session_state.terminal_proc = None
    if "terminal_running_cmd" not in st.session_state:
        st.session_state.terminal_running_cmd = ""
    if "terminal_output_buf" not in st.session_state:
        st.session_state.terminal_output_buf = ""
    if "preview_state" not in st.session_state:
        st.session_state.preview_state = {
            "running": False,
            "kind": "",
            "target": "",
            "port": None,
            "pid": None,
            "proc": None,
            "log": [],
            "exit_code": None,
        }
    if "wb_show_diff" not in st.session_state:
        st.session_state.wb_show_diff = False
    if "wb_preview_mode" not in st.session_state:
        st.session_state.wb_preview_mode = False
    if "terminal_cmd_prefill" not in st.session_state:
        st.session_state.terminal_cmd_prefill = ""
    if "terminal_open" not in st.session_state:
        st.session_state.terminal_open = False
    if "terminal_auto_run" not in st.session_state:
        st.session_state.terminal_auto_run = None
    if "terminal_interactive_warn" not in st.session_state:
        st.session_state.terminal_interactive_warn = False


def _persist_messages() -> None:
    if not st.session_state.thread_id:
        return
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


def _go_new_chat() -> None:
    st.session_state.new_chat_mode = True
    st.session_state.thread_id = None
    st.session_state.messages = []
    st.session_state.traces = []
    st.session_state.file_views = []
    st.session_state.file_changes = []
    st.session_state.test_results = []
    st.session_state.pending_interrupt = None
    st.session_state.selected_file = None
    st.session_state.editor_draft_path = None
    st.session_state.editor_draft = ""
    st.session_state.editor_disk = ""
    st.rerun()


def _switch_thread(thread_id: str) -> None:
    st.session_state.new_chat_mode = False
    st.session_state.thread_id = thread_id
    st.session_state.messages = _store().load_messages(thread_id)
    st.session_state.traces = []
    st.session_state.file_views = []
    st.session_state.file_changes = []
    st.session_state.test_results = []
    st.session_state.pending_interrupt = None
    st.rerun()



def _render_tool_html(name: str, arguments: dict, result: str | None = None, ok: bool = True) -> str:
    short_args = escape(str(arguments)[:180])
    body = f'<div class="ca-tool"><span class="name">{escape(name)}</span> {short_args}'
    if result is not None:
        flag = "ok" if ok else "err"
        body += f"<pre>({flag}) {escape(result[:500])}</pre>"
    body += "</div>"
    return body


def _compact_tool_label(name: str) -> str:
    n = (name or "").lower()
    if "read" in n:
        return "Reading file"
    if "write" in n or "edit" in n:
        return "Editing file"
    if "execute" in n or "shell" in n:
        return "Running command"
    return name or "tool"


def _tool_path_hint(arguments: dict) -> str:
    for key in ("path", "file_path", "file"):
        val = arguments.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _command_high_risk(command: str) -> bool:
    low = (command or "").lower()
    for token in ("rm ", "sudo", "kill", "pkill", "chmod", "mv ", "curl", "wget", "> /"):
        if token in low:
            return True
    return False


def _diff_for_file(rel: str | None) -> str | None:
    if not rel:
        return None
    for ch in reversed(st.session_state.file_changes):
        if ch.get("path") == rel and ch.get("diff"):
            return ch["diff"]
    return None


def _change_file_count() -> int:
    seen: set[str] = set()
    for ch in st.session_state.file_changes:
        p = ch.get("path")
        if p and ch.get("diff"):
            seen.add(p)
    return len(seen)


def _preview_eligible(workspace: Path, rel: str) -> str | None:
    if rel.lower().endswith((".html", ".htm")):
        return "html"
    if not rel.lower().endswith(".py"):
        return None
    try:
        path = resolve_workspace_file(workspace, rel)
    except PermissionError:
        return None
    text, err = read_workspace_text(workspace, rel)
    if err or text is None:
        return None
    kind = detect_preview_kind(path, text)
    if kind in {"streamlit", "flask", "fastapi"}:
        return "web"
    return None


def _python_run_cmd(rel: str) -> str:
    return f"python3 {shlex.quote(rel)}"


def _file_has_input_call(text: str) -> bool:
    return "input(" in (text or "")


def _start_terminal_command(workspace: Path, cmd: str) -> bool:
    ok, msg = validate_user_command(cmd)
    if not ok:
        st.error(msg)
        return False
    bg = start_user_command_bg(workspace, cmd)
    if not bg.get("ok"):
        st.error(bg.get("error") or "Failed to start")
        return False
    st.session_state.terminal_proc = bg["proc"]
    st.session_state.terminal_running_cmd = cmd
    st.session_state.terminal_output_buf = ""
    st.session_state.terminal_open = True
    return True


def _trigger_header_run(workspace: Path, rel: str) -> None:
    cmd = _python_run_cmd(rel)
    st.session_state.terminal_open = True
    st.session_state["user-terminal-cmd"] = cmd
    source = st.session_state.editor_draft or st.session_state.editor_disk or ""
    if _file_has_input_call(source):
        st.session_state.terminal_interactive_warn = True
    else:
        st.session_state.terminal_auto_run = cmd
    st.rerun()


def _should_keep_trace(step: str | None) -> bool:
    s = (step or "").lower()
    if s in {"middleware", "start", "complete"}:
        return False
    if "middleware" in s:
        return False
    return True


def _sidebar_skip(name: str, path: Path) -> bool:
    if name.startswith(".") or name in IGNORE_DIR_NAMES:
        return True
    if "__pycache__" in path.parts:
        return True
    if path.is_file() and path.suffix.lower() in IGNORE_SUFFIXES:
        return True
    return False


def _list_workspace_files(
    workspace: Path,
    rel_dir: str = "",
    depth: int = 0,
    max_depth: int = 4,
    counter: list[int] | None = None,
) -> list[str]:
    if counter is None:
        counter = [0]
    if depth > max_depth or counter[0] >= 200:
        return []
    base = workspace / rel_dir if rel_dir else workspace
    try:
        children = sorted(base.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError:
        return []
    out: list[str] = []
    for child in children:
        if _sidebar_skip(child.name, child):
            continue
        rel = str(child.relative_to(workspace))
        if child.is_dir():
            out.extend(_list_workspace_files(workspace, rel, depth + 1, max_depth, counter))
        else:
            counter[0] += 1
            out.append(rel)
    return out


def _format_file_pick(path: str) -> str:
    if path == "—":
        return "Select a file…"
    return " › ".join(path.split("/"))


def _render_file_picker(workspace: Path) -> None:
    files = sorted(_list_workspace_files(workspace))
    if not files:
        st.caption("Empty workspace")
        return
    options = ["—"] + files
    current = st.session_state.selected_file
    idx = options.index(current) if current in options else 0
    picked = st.selectbox(
        "Open file",
        options,
        index=idx,
        format_func=_format_file_pick,
        label_visibility="collapsed",
    )
    if picked != "—" and picked != st.session_state.selected_file:
        st.session_state.selected_file = picked
        st.session_state.editor_force_reload = True
        st.rerun()
    st.caption(f"{len(files)} files")


def _sidebar_settings(workspace: Path) -> None:
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
        ws_in = st.text_input("Workspace", value=st.session_state.workspace)
        if ws_in.strip() and ws_in.strip() != st.session_state.workspace:
            st.session_state.workspace = str(resolve_workspace(ws_in.strip()))
            st.cache_resource.clear()
            st.rerun()
        ok = ollama_available()
        tid = st.session_state.thread_id[:8] if st.session_state.thread_id else "new"
        st.caption(f"{'●' if ok else '○'} {st.session_state.model} · {tid}")
        if st.button("Clear chat", use_container_width=True):
            _go_new_chat()


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
                if data["path"] == st.session_state.editor_draft_path:
                    st.session_state.editor_force_reload = True
        elif et == "file_change":
            st.session_state.file_changes.append(data)
            if data.get("path"):
                st.session_state.selected_file = data["path"]
                if data["path"] == st.session_state.editor_draft_path:
                    st.session_state.editor_force_reload = True
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
    if st.query_params.get("keti_home"):
        st.query_params.clear()
        _go_new_chat()
    st.markdown(
        '<a href="?keti_home=1" target="_self" class="ca-brand ca-brand-link">KETI Coding Agent</a>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="ca-sub">deepagents-code {escape(deepagents_version())}</div>',
        unsafe_allow_html=True,
    )

    store = _store()
    st.markdown('<div class="ca-section">Thread</div>', unsafe_allow_html=True)
    threads = store.list_threads()
    labels = {t["id"]: (t.get("title") or t["id"][:8])[:40] for t in threads}
    ids = ["__new__"] + [t["id"] for t in threads]
    labels["__new__"] = "New chat"
    current = "__new__" if st.session_state.new_chat_mode else st.session_state.thread_id
    if current not in ids:
        current = "__new__"
    chosen = st.selectbox(
        "Thread",
        ids,
        index=ids.index(current),
        format_func=lambda i: labels.get(i, i),
        label_visibility="collapsed",
    )
    if chosen == "__new__" and not st.session_state.new_chat_mode:
        _go_new_chat()
    elif chosen != "__new__" and chosen != st.session_state.thread_id:
        _switch_thread(chosen)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("New", use_container_width=True):
            _go_new_chat()
    with c2:
        if st.button("Delete", use_container_width=True) and st.session_state.thread_id:
            store.delete(st.session_state.thread_id)
            _go_new_chat()

    st.markdown('<div class="ca-section">Files</div>', unsafe_allow_html=True)
    _render_file_picker(workspace)

    _sidebar_settings(workspace)


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
                name = msg.get("name", "tool")
                args = msg.get("arguments") or {}
                ok = msg.get("ok", True)
                path = _tool_path_hint(args)
                label = _compact_tool_label(name)
                status = "Completed" if ok else "Failed"
                line = f"{label} — {status}"
                if path:
                    line = f"{label} · `{path}` — {status}"
                st.caption(line)
        else:
            with st.chat_message(role):
                st.markdown(msg.get("content") or "")


def _agent_details_panel() -> None:
    failed_tool = any(
        m.get("role") == "tool" and not m.get("ok", True) for m in st.session_state.messages
    )
    failed_verify = bool(st.session_state.test_results) and not st.session_state.test_results[-1].get(
        "ok", True
    )
    useful = [t for t in st.session_state.traces if _should_keep_trace(t.get("step"))]
    expanded = failed_tool or failed_verify
    with st.expander("Agent details", expanded=expanded):
        if not useful:
            st.caption("Detailed agent steps appear here during runs.")
        else:
            for tr in reversed(useful[-30:]):
                step = tr.get("step") or "event"
                detail = tr.get("detail") or ""
                st.markdown(f"**{step}** — {detail}" if detail else f"**{step}**")

def _sync_editor_buffer(workspace: Path) -> None:
    rel = st.session_state.selected_file
    if not rel:
        st.session_state.editor_draft_path = None
        st.session_state.editor_draft = ""
        st.session_state.editor_disk = ""
        return
    if st.session_state.editor_draft_path != rel or st.session_state.editor_force_reload:
        text, _ = read_workspace_text(workspace, rel)
        for art in reversed(st.session_state.file_views):
            if art.get("path") == rel and art.get("content") is not None:
                text = str(art["content"])
                break
        st.session_state.editor_draft_path = rel
        st.session_state.editor_draft = text or ""
        st.session_state.editor_disk = text or ""
        st.session_state.editor_force_reload = False


def _save_editor_file(workspace: Path, rel: str) -> None:
    old = st.session_state.editor_disk
    ok, err = write_workspace_text(workspace, rel, st.session_state.editor_draft)
    if not ok:
        st.error(err or "Save failed")
        return
    diff = unified_diff(old, st.session_state.editor_draft, rel)
    if diff.strip():
        st.session_state.file_changes.append(
            {"path": rel, "action": "user_edit", "diff": diff[:8000]}
        )
    st.session_state.editor_disk = st.session_state.editor_draft
    st.session_state.editor_pending_save = False
    st.rerun()


def _editor_header(workspace: Path, rel: str, *, dirty: bool, preview_kind: str | None) -> None:
    name = Path(rel).name
    left, right = st.columns([6, 4], gap="small")
    with left:
        title = escape(name)
        if dirty:
            st.markdown(f"**{title}** · Modified")
        else:
            st.markdown(f"**{title}**")
        if rel != name:
            st.caption(rel)

    actions: list[tuple[str, str, str]] = []
    if _diff_for_file(rel) or _change_file_count() > 0:
        actions.append(("changes", f"Changes {_change_file_count()}", "Show file changes"))
    if preview_kind and not st.session_state.wb_preview_mode:
        actions.append(("preview", "Preview", "Open web preview"))
    elif preview_kind is None and rel.lower().endswith(".py"):
        actions.append(("run", "▶ Run", "Run current file in Terminal"))
    if dirty:
        actions.append(("save", "Save", "Save file"))
    actions.append(("more", "⋯", "More actions"))

    with right:
        st.markdown('<div class="ca-wb-actions">', unsafe_allow_html=True)
        cols = st.columns(len(actions), gap="small")
        for col, (action, label, help_text) in zip(cols, actions):
            with col:
                if action == "changes":
                    if st.button(label, key="wb-changes", help=help_text, use_container_width=True):
                        st.session_state.wb_show_diff = not st.session_state.wb_show_diff
                        st.rerun()
                elif action == "preview":
                    if st.button(label, key="wb-preview", help=help_text, use_container_width=True):
                        st.session_state.wb_preview_mode = True
                        st.rerun()
                elif action == "run":
                    if st.button(label, key="wb-run", help=help_text, use_container_width=True):
                        _trigger_header_run(workspace, rel)
                elif action == "save":
                    if st.button(label, key="wb-save", type="primary", help=help_text, use_container_width=True):
                        st.session_state.editor_pending_save = True
                elif action == "more":
                    with st.popover(label, help=help_text):
                        if st.button("Reload", key="wb-reload"):
                            st.session_state.editor_force_reload = True
                            st.session_state.editor_pending_save = False
                            st.session_state.wb_preview_mode = False
                            st.rerun()
                        if st.button("Discard", key="wb-discard", disabled=not dirty):
                            st.session_state.editor_draft = st.session_state.editor_disk
                            st.session_state.editor_pending_save = False
                            st.rerun()
                        if preview_kind and st.session_state.wb_preview_mode:
                            if st.button("Back to editor", key="wb-back-editor"):
                                st.session_state.wb_preview_mode = False
                                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.editor_pending_save:
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.caption(f"Save `{name}`?")
        if c2.button("Confirm", key="wb-save-yes", type="primary"):
            _save_editor_file(workspace, rel)
        if c3.button("Cancel", key="wb-save-no"):
            st.session_state.editor_pending_save = False
            st.rerun()


def _editor_body(workspace: Path, rel: str, *, term_open: bool) -> None:
    try:
        path = resolve_workspace_file(workspace, rel)
    except PermissionError as exc:
        st.error(str(exc))
        return
    kind = classify_file(path)
    if kind == "binary":
        st.info("Binary file — editing is not supported.")
        return
    if kind == "missing":
        st.warning("File not found.")
        return
    height = 440 if term_open else 540

    if rel.lower().endswith(".md"):
        preview_tab, source_tab = st.tabs(["Preview", "Source"])
        with preview_tab:
            body = st.session_state.editor_draft or ""
            with st.container(height=height):
                if body.strip():
                    st.markdown(body)
                else:
                    st.caption("Nothing to preview.")
        with source_tab:
            draft = st.text_area(
                "Editor",
                value=st.session_state.editor_draft,
                height=height,
                key=f"editor-area-{rel}",
                label_visibility="collapsed",
            )
            st.session_state.editor_draft = draft
        return

    draft = st.text_area(
        "Editor",
        value=st.session_state.editor_draft,
        height=height,
        key=f"editor-area-{rel}",
        label_visibility="collapsed",
    )
    st.session_state.editor_draft = draft


def _diff_panel(workspace: Path, rel: str) -> None:
    diff = _diff_for_file(rel)
    if diff:
        st.code(diff, language="diff")

    if _change_file_count() > 1:
        with st.expander("All changes", expanded=False):
            seen: set[str] = set()
            for ch in reversed(st.session_state.file_changes):
                p = ch.get("path")
                if not p or p in seen or not ch.get("diff"):
                    continue
                seen.add(p)
                if st.button(f"{ch.get('action', 'modify')}: {p}", key=f"diff-jump-{p}"):
                    st.session_state.selected_file = p
                    st.session_state.editor_force_reload = True
                    st.rerun()

    if st.session_state.test_results:
        latest = st.session_state.test_results[-1]
        if latest.get("ok"):
            st.caption("Verification ok")
        else:
            with st.expander("Verification failed", expanded=True):
                st.code(latest.get("details") or latest.get("summary") or "")


def _preview_body(workspace: Path, rel: str, preview_kind: str) -> None:
    state = poll_preview(dict(st.session_state.preview_state))
    st.session_state.preview_state = state

    if preview_kind == "html":
        text, err = read_workspace_text(workspace, rel)
        if err:
            st.warning(err)
            return
        st.components.v1.html(text or "", height=420, scrolling=True)
        if st.button("Back to editor", key="wb-html-back"):
            st.session_state.wb_preview_mode = False
            st.rerun()
        return

    proc = state.get("proc")
    if proc is None and preview_kind == "web":
        result = start_preview_process(workspace, rel)
        if not result.get("ok"):
            st.error(result.get("error") or "Preview failed to start")
            return
        st.session_state.preview_state = {
            "running": True,
            "kind": result.get("kind"),
            "target": rel,
            "port": result.get("port"),
            "pid": result.get("pid"),
            "proc": result.get("proc"),
            "log": result.get("log") or [],
            "exit_code": None,
        }
        st.rerun()

    if proc is not None and state.get("running", True):
        port = state.get("port")
        st.caption(f"Preview running · port {port}" if port else "Preview running")
        if port:
            st.link_button("Open preview", f"http://127.0.0.1:{port}")
        log = "".join(state.get("log") or [])
        if log and (state.get("exit_code") not in (None, 0) or "error" in log.lower()):
            st.code(log[-4000:])
        if st.button("Stop Preview", type="primary", key="wb-stop-preview"):
            stop_process(proc)
            st.session_state.preview_state = {
                "running": False,
                "kind": "",
                "target": "",
                "port": None,
                "pid": None,
                "proc": None,
                "log": state.get("log") or [],
                "exit_code": None,
            }
            st.session_state.wb_preview_mode = False
            st.rerun()
        with st.expander("Connection details", expanded=False):
            st.caption(f"Port {port} · PID {state.get('pid')}")
            if port:
                st.code(f"ssh -L {port}:127.0.0.1:{port} user@host")
        return

    st.caption("Preview stopped.")
    if st.button("Back to editor", key="wb-preview-back"):
        st.session_state.wb_preview_mode = False
        st.rerun()


def _terminal_panel(workspace: Path) -> None:
    if st.session_state.terminal_interactive_warn:
        st.warning("Interactive input is not supported in this terminal MVP.")
        st.session_state.terminal_interactive_warn = False

    auto_cmd = st.session_state.terminal_auto_run
    if auto_cmd and st.session_state.terminal_proc is None:
        st.session_state.terminal_auto_run = None
        if _start_terminal_command(workspace, auto_cmd):
            st.rerun()

    proc = st.session_state.terminal_proc
    if proc is not None:
        chunk, running, code = poll_user_terminal(proc)
        if chunk:
            st.session_state.terminal_output_buf += chunk
        if not running:
            st.session_state.terminal_history.append(
                {
                    "command": st.session_state.terminal_running_cmd,
                    "stdout": st.session_state.terminal_output_buf,
                    "stderr": "",
                    "exit_code": code,
                }
            )
            st.session_state.terminal_proc = None
            st.session_state.terminal_running_cmd = ""
            st.session_state.terminal_output_buf = ""
            st.rerun()

    if st.session_state.terminal_proc is not None:
        if st.session_state.terminal_output_buf:
            st.code(st.session_state.terminal_output_buf[-8000:])
        if st.button("Stop", type="primary", key="term-stop"):
            stop_user_terminal(st.session_state.terminal_proc)
            st.session_state.terminal_history.append(
                {
                    "command": st.session_state.terminal_running_cmd,
                    "stdout": st.session_state.terminal_output_buf,
                    "stderr": "(stopped by user)",
                    "exit_code": -1,
                }
            )
            st.session_state.terminal_proc = None
            st.session_state.terminal_running_cmd = ""
            st.session_state.terminal_output_buf = ""
            st.rerun()
        return

    prefill = st.session_state.get("terminal_cmd_prefill") or ""
    if prefill:
        st.session_state["user-terminal-cmd"] = prefill
        st.session_state.terminal_cmd_prefill = ""

    cmd = st.text_input(
        "Command",
        placeholder="python3 calculator.py",
        key="user-terminal-cmd",
        label_visibility="collapsed",
    )
    if not (cmd or "").strip() and not st.session_state.terminal_history:
        st.caption("Enter a command, or use ▶ Run in the header.")

    high_risk = _command_high_risk(cmd)
    if high_risk and (cmd or "").strip():
        st.checkbox("Confirm potentially destructive command", key="terminal_danger_ack")

    run_disabled = not (cmd or "").strip() or (high_risk and not st.session_state.get("terminal_danger_ack"))
    if st.button("Run", type="primary", key="term-run", disabled=run_disabled):
        if _start_terminal_command(workspace, cmd):
            st.rerun()

    if st.session_state.terminal_history:
        with st.expander("History", expanded=False):
            for row in reversed(st.session_state.terminal_history[-12:]):
                code = row.get("exit_code")
                st.markdown(f"`$ {row.get('command')}` · exit {code}")
                out = (row.get("stdout") or "") + (row.get("stderr") or "")
                if out.strip():
                    st.code(out[-3000:])


def _workbench_panel(workspace: Path) -> None:
    rel = st.session_state.selected_file
    term_open = bool(st.session_state.terminal_proc) or bool(st.session_state.terminal_open)

    if not rel:
        st.markdown(
            '<div class="ca-empty">Select a file from the sidebar.</div>',
            unsafe_allow_html=True,
        )
        with st.expander("Terminal", expanded=term_open):
            _terminal_panel(workspace)
        return

    _sync_editor_buffer(workspace)
    dirty = st.session_state.editor_draft != st.session_state.editor_disk
    preview_kind = _preview_eligible(workspace, rel)

    if preview_kind is None:
        st.session_state.wb_preview_mode = False

    _editor_header(workspace, rel, dirty=dirty, preview_kind=preview_kind)

    if st.session_state.wb_preview_mode and preview_kind:
        _preview_body(workspace, rel, preview_kind)
    else:
        _editor_body(workspace, rel, term_open=term_open)

    if st.session_state.wb_show_diff and (_diff_for_file(rel) or _change_file_count() > 0):
        with st.expander("Changes", expanded=True):
            _diff_panel(workspace, rel)

    with st.expander("Terminal", expanded=term_open):
        _terminal_panel(workspace)


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
        _approval_panel(bridge)
        with st.container(height=PANEL_SCROLL_HEIGHT, border=True):
            if st.session_state.new_chat_mode and not st.session_state.messages:
                st.markdown(
                    '<div class="ca-new-chat-hint">New chat</div>',
                    unsafe_allow_html=True,
                )
            _render_chat_history()
            _agent_details_panel()

        blocked = st.session_state.pending_interrupt is not None
        prompt = None
        if not blocked:
            prompt = st.chat_input("Message the coding agent…")
        else:
            st.caption("Approve or reject to continue.")
        user_text = prompt

        if user_text and not blocked:
            if st.session_state.new_chat_mode or not st.session_state.thread_id:
                title = user_text.strip().splitlines()[0]
                if len(title) > 48:
                    title = title[:48] + "…"
                row = _store().create(title=title, model=st.session_state.model)
                st.session_state.thread_id = row["id"]
                st.session_state.new_chat_mode = False

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
        with st.container(height=PANEL_SCROLL_HEIGHT, border=True):
            _workbench_panel(workspace)


if __name__ == "__main__":
    main()
