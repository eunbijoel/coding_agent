"""Prototype: streamlit-antd-components Tree for hierarchical file explorer.

Run:
  .venv/bin/streamlit run prototypes/sac_file_tree_prototype.py --server.headless true

Do NOT integrate into app.py until this prototype is verified.
"""

from __future__ import annotations

import streamlit as st
import streamlit_antd_components as sac
from streamlit_antd_components import BsIcon, TreeItem

PROTOTYPE_TREE: list[TreeItem] = [
    TreeItem(
        label="folder:workspace",
        icon=BsIcon("folder2-open"),
        children=[
            TreeItem(
                label="folder:mini_research_agents",
                icon=BsIcon("folder"),
                children=[
                    TreeItem(
                        label="folder:mini_research_agents/tests",
                        icon=BsIcon("folder"),
                        children=[
                            TreeItem(
                                label="mini_research_agents/tests/test_pipeline.py",
                                icon=BsIcon("filetype-py"),
                            ),
                        ],
                    ),
                    TreeItem(
                        label="mini_research_agents/agents.py",
                        icon=BsIcon("filetype-py"),
                    ),
                    TreeItem(
                        label="mini_research_agents/app.py",
                        icon=BsIcon("filetype-py"),
                    ),
                ],
            ),
            TreeItem(
                label="calculator.py",
                icon=BsIcon("filetype-py"),
            ),
            TreeItem(
                label="memo_app.py",
                icon=BsIcon("filetype-py"),
            ),
            # Duplicate basename for path disambiguation test
            TreeItem(
                label="folder:other_pkg",
                icon=BsIcon("folder"),
                children=[
                    TreeItem(
                        label="other_pkg/app.py",
                        icon=BsIcon("filetype-py"),
                    ),
                ],
            ),
        ],
    ),
]


def _display_name(node_value: str) -> str:
    if node_value.startswith("folder:"):
        rel = node_value.removeprefix("folder:")
        return rel.rsplit("/", 1)[-1] if rel else "workspace"
    return node_value.rsplit("/", 1)[-1]


def _is_file_node(node_value: str | None) -> bool:
    return bool(node_value) and not node_value.startswith("folder:")


def _selected_index(items: list[TreeItem], target: str | None) -> int | None:
    if not target:
        return None
    idx = 0

    def walk(nodes: list[TreeItem]) -> int | None:
        nonlocal idx
        for node in nodes:
            if node.label == target:
                return idx
            idx += 1
            if node.children:
                found = walk(node.children)
                if found is not None:
                    return found
        return None

    return walk(items)


st.set_page_config(page_title="SAC File Tree Prototype", layout="wide")
st.title("File Tree Prototype — streamlit-antd-components")
st.caption(f"Package version: {sac.__VERSION__}")

theme = st.radio("Theme preview", ["Light", "Dark"], horizontal=True, key="proto_theme")
if theme == "Dark":
    st.markdown(
        """
<style>
  .stApp { background: #0d1117; color: #e6edf3; }
  [data-testid="stSidebar"] { background: #161b22; }
</style>
""",
        unsafe_allow_html=True,
    )

if "proto_selected_file" not in st.session_state:
    st.session_state.proto_selected_file = None
if "proto_open_index" not in st.session_state:
    st.session_state.proto_open_index = [0, 1, 2]

left, right = st.columns([1, 1])

with left:
    st.subheader("FILES")
    selected = sac.tree(
        PROTOTYPE_TREE,
        index=_selected_index(PROTOTYPE_TREE, st.session_state.proto_selected_file),
        format_func=_display_name,
        checkbox=False,
        show_line=True,
        open_index=st.session_state.proto_open_index,
        height=420,
        width=360,
        return_index=False,
        key="proto_file_tree",
    )

    if isinstance(selected, list):
        selected = selected[0] if selected else None

    if _is_file_node(selected):
        st.session_state.proto_selected_file = selected

with right:
    st.subheader("Python return value")
    st.code(repr(selected), language="python")
    st.write("**Resolved file path:**", st.session_state.proto_selected_file or "(none)")
    st.write("**Is file node:**", _is_file_node(selected))
    st.write("**Folder click ignored for selection:**", not _is_file_node(selected))

    st.subheader("Verification checklist")
    checks = {
        "No checkbox/radio UI (checkbox=False)": True,
        "Folder expand/collapse via tree arrows": "manual",
        "File click returns full relative path": _is_file_node(selected)
        and selected == st.session_state.proto_selected_file,
        "Duplicate app.py paths are distinct values": True,
        "Selected file path stored in session_state": st.session_state.proto_selected_file
        in {
            "mini_research_agents/app.py",
            "other_pkg/app.py",
            "mini_research_agents/agents.py",
            "mini_research_agents/tests/test_pipeline.py",
            "calculator.py",
            "memo_app.py",
        }
        or st.session_state.proto_selected_file is None,
    }
    for label, ok in checks.items():
        if ok is True:
            st.success(f"✓ {label}")
        elif ok is False:
            st.error(f"✗ {label}")
        else:
            st.info(f"? {label} — confirm visually in tree")

    st.markdown(
        """
**Manual checks**
1. Tree rows must not show Streamlit radio circles or checkboxes.
2. Expand/collapse `mini_research_agents` and `tests` with folder arrows.
3. Click `mini_research_agents/app.py` → path `mini_research_agents/app.py`.
4. Click `other_pkg/app.py` → path `other_pkg/app.py` (same basename, different folder).
5. Selected row should highlight; folder-only clicks must not change stored file path.
6. Rerun (change theme) — expanded folders should stay open if component preserves state.
"""
    )
