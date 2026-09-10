# Excel Analyzer integration

Coding Agent treats `excel_ai_analyzer` as an Excel specialist capability. The
analyzer is **not imported** into the Coding Agent process. Production analysis
and natural-language workbook transforms go through repository-owned tools and
a dedicated subprocess client. Chat Excel/CSV upload, input preview,
original-file download, and Files explorer delete remain Coding Agent UI features.
Structure inspection uses `inspect_spreadsheet` / `read_spreadsheet` first.

## Runtime path

```
Coding Agent Streamlit UI
  → chat upload (uploads/) and/or existing workspace files
  → DeepAgentsBridge
    → create_cli_agent(
         tools=inspect_spreadsheet + read_spreadsheet
               + analyze_excel + transform_excel,
         enable_shell=True
       )
      → inspect_spreadsheet / read_spreadsheet  (structure, bounded rows)
      → analyze_excel custom tool
      → transform_excel custom tool
        → dedicated subprocess (process group)
          → excel_ai_analyzer venv: python -m core.application.cli
            → JSON stdout / diagnostic stderr
            → Analyze: workspace/outputs/excel_agent/<uuid>/ nested by Analyzer
            → Transform: workspace/outputs/excel_agent/<uuid>/ as output_directory
```

This host is a Linux server. Timeout handling uses `start_new_session=True`
and `os.killpg` (SIGTERM, then SIGKILL, then wait/reap).

## Environment

| Variable | Role | Default |
| --- | --- | --- |
| `CODING_AGENT_EXCEL_ROOT` | `excel_ai_analyzer` repository root. Must contain `core/application/cli.py`. | Sibling `../excel_ai_analyzer` if it exists and is valid |
| `CODING_AGENT_EXCEL_PYTHON` | Excel-only Python executable. Coding Agent `sys.executable` is never used as a fallback. | `$ROOT/.venv/bin/python` |
| `CODING_AGENT_EXCEL_TIMEOUT` | Subprocess timeout in seconds (1–86400) | `180` |
| `CODING_AGENT_EXCEL_OUTPUT_ROOT` | Output root **inside** the current Coding Agent workspace | `<workspace>/outputs/excel_agent` |
| `CODING_AGENT_EXCEL_MODEL` | Model name forwarded to Excel Analyzer | `qwen2.5:7b` (Excel production default) |
| `CODING_AGENT_EXCEL_OLLAMA` | Ollama base URL forwarded to Excel Analyzer | `http://localhost:11434` |

Invalid configuration does not prevent `import coding_agent` or app startup.
The tool returns `configuration_error` when invoked.

Example:

```bash
export CODING_AGENT_EXCEL_ROOT=<excel-analyzer-root>
export CODING_AGENT_EXCEL_PYTHON=<excel-analyzer-root>/.venv/bin/python
export CODING_AGENT_EXCEL_TIMEOUT=180
export CODING_AGENT_EXCEL_OUTPUT_ROOT=<project-root>/workspace/outputs/excel_agent
./run_app.sh --server.port 8503
```

## Tool usage

Input files may come from chat attachments under `uploads/` or from
files already in the workspace.

- `inspect_spreadsheet`: workbook structure, sheet names, columns, bounded metadata (**prefer first**)
- `read_spreadsheet`: bounded inspection of selected sheet/columns/rows (**prefer for row slices**)
- `analyze_excel(files, prompt, analysis_mode="single", profile_name="generic", sheets=None)`:
  natural-language summary, comparison, aggregation, multi-file analysis
- `transform_excel(files, prompt)`: copy-preserving workbook changes
  (`extract_to_sheet`, `unmerge_cells`). v1 accepts exactly one `.xlsx`. The user
  prompt is forwarded unchanged. Product policies
  (`include_descendants_and_subtotals`, `copy_with_new_sheet`, `fill_all`) are set
  by the adapter and cannot be overridden by the model.

`analyze_excel` notes:

- Pass workspace-relative or workspace-absolute paths (`.xlsx` / `.xls` / `.xlsm` / `.csv`).
- `single` requires one file; `multi` requires two or more.
- Output directory is not a tool argument. Each call writes under
  `outputs/excel_agent/<request-id>/` (visible in Files; Download from the editor).
- Original uploaded files stay in `uploads/`.

`transform_excel` notes:

- Coding Agent creates `outputs/excel_agent/<request-id>/` and passes that directory
  as CLI `output_directory`. Pre-existing request dirs are refused (no silent overwrite).
- The source workbook is not modified; SHA-256 is checked after the run.
- Artifacts are hash-/path-validated inside the workspace before being returned.

## Boundaries

- Built-in filesystem and `execute` tools remain available for non-Excel work.
  Do not use `execute` to run Excel Analyzer CLI.
- Do not reimplement production semantic analysis or coordinate planning with
  pandas in Coding Agent.
- Excel semantic routing and transform planning stay in `excel_ai_analyzer`.
- Coding Agent validates paths, runs the process, enforces timeout, checks the
  JSON contract, and verifies artifact hashes/sizes/workspace containment.
- Existing Coding Agent HITL (shell/write, Auto-approve) is unchanged.
  When Auto-approve is off, `analyze_excel` / `transform_excel` are added to the
  stock HITL interrupt map so the Streamlit Approve/Reject panel gates them
  (deepagents-code has no public `interrupt_on` kwarg; Coding Agent patches the
  interrupt map at agent creation).
