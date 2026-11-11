# Coding Agent
> Korean README: [README.md](README.md)

Streamlit coding workbench | **Agent engine: [deepagents-code](https://pypi.org/project/deepagents-code/)** | Model: Ollama `gemma4:31b`

<img width="1024" height="572" alt="image" src="https://github.com/user-attachments/assets/6010e194-a4fe-462b-bfa9-c5ed26b05a3d" />


## Run

```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

git clone https://github.com/eunbijoel/coding_agent.git
cd coding_agent
chmod +x run_app.sh
./run_app.sh
```

Or manually:

```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
streamlit run app.py
```



### Workbench

Select a file in the sidebar Files Explorer to open it on the right.


| Area | Description |
| --- | --- |
| **Header** | Filename · `Modified` (unsaved changes) · relative path. Buttons: **Changes**, **Preview**, **▶ Run**, **Save**, **⋯** |
| **Editor** | Plain files use `text_area`. `.md` uses **Preview / Source** tabs |
| **Changes** | When the agent edited files: Header **Changes** → bottom expander |
| **Terminal** | Collapsible bottom panel — command input, Run/Stop, History (separate from the agent shell) |


## Excel Analyzer integration (custom tool)

Attach Excel/CSV in chat, or use files already in the workspace.
Attachments are stored under `workspace/uploads/`, visible in Files, and kept after New chat.

Roles:

- **inspect_spreadsheet / read_spreadsheet**: sheet/column/partial-row structure checks (**prefer first**; Coding Agent process)
- **analyze_excel**: natural-language summary, comparison, aggregation (dedicated Analyzer venv subprocess)
- **transform_excel**: copy-preserving `extract_to_sheet` / `unmerge_cells` (dedicated subprocess). Coding Agent does not invent coordinates.
- Results are written under `workspace/outputs/excel_agent/` and can be opened / downloaded in Files Explorer.
- Existing shell/write HITL and Auto-approve are unchanged. With Auto-approve off,
  `analyze_excel` / `transform_excel` also pause on the **same Approve/Reject panel**.

Coding Agent calls `excel_ai_analyzer` in a **separate Python venv subprocess**. Bad Analyzer config does not crash the app; only Excel tools return `configuration_error`.

Minimum setup:

```bash
export CODING_AGENT_EXCEL_ROOT=<excel-analyzer-root>
export CODING_AGENT_EXCEL_PYTHON=<excel-analyzer-root>/.venv/bin/python
export CODING_AGENT_EXCEL_TIMEOUT=180
export CODING_AGENT_EXCEL_OUTPUT_ROOT=<project-root>/workspace/outputs/excel_agent
```

- Use inspect/read for structure, `analyze_excel` for summary/aggregation, `transform_excel` for sheet extract / unmerge.

## Runtime environment and test examples

For detailed run instructions, hardware notes, prompts, and measured results, see the
[execution / verification guide](EXECUTION_GUIDE.md).

<img width="1280" height="595" alt="photo_2026-10-05 22 20 12" src="https://github.com/user-attachments/assets/cf31fe3b-2609-491d-aa15-a8a99f6695a5" />


### Limitations:

- **Terminal** is not a PTY. Interactive `input()` is not supported.
- Header **▶ Run** runs `python3 '<file>'` in Terminal. If the source uses `input()`, it only warns and does not auto-run.
- **Preview** depends on file type: `.md` in Editor tabs; HTML/web apps use a separate preview mode.
- Binary files are not editable.

## References

- [https://pypi.org/project/deepagents-code/](https://pypi.org/project/deepagents-code/)
- [https://github.com/FeynmanZhou/tasking-agent](https://github.com/FeynmanZhou/tasking-agent) (DeepAgentsBridge / event-normalization UX)
- Excel Analyzer subprocess integration: [Jihei-Boun](https://github.com/Jihei-Boun) (`excel_ai_analyzer` / I2 integrate)
