# Excel Analyzer integration (Phase I2-B / I2-R1)

Coding Agent treats `excel_ai_analyzer` as an Excel specialist capability. The
analyzer is **not imported** into the Coding Agent process. Production analysis
goes through a repository-owned `analyze_excel` tool and a dedicated subprocess
client. Chat Excel/CSV upload, input preview, original-file download, and
Files explorer delete remain remote UI features. Structure inspection uses
`inspect_spreadsheet` / `read_spreadsheet`.

## Runtime path

```
Coding Agent Streamlit UI
  → chat upload (.session_uploads) and/or existing workspace files
  → DeepAgentsBridge
    → create_cli_agent(
         tools=inspect_spreadsheet + read_spreadsheet + analyze_excel,
         enable_shell=True
       )
      → inspect_spreadsheet / read_spreadsheet  (structure, bounded rows)
      → analyze_excel custom tool
        → dedicated subprocess (process group)
          → excel_ai_analyzer venv: python -m core.application.cli
            → JSON stdout / diagnostic stderr
            → request-scoped workspace/.excel_agent/<uuid>/
```

This host is a Linux server. Timeout handling uses `start_new_session=True`
and `os.killpg` (SIGTERM, then SIGKILL, then wait/reap).

## Environment

| Variable | Role | Default |
| --- | --- | --- |
| `CODING_AGENT_EXCEL_ROOT` | `excel_ai_analyzer` repository root. Must contain `core/application/cli.py`. | Sibling `../excel_ai_analyzer` if it exists and is valid |
| `CODING_AGENT_EXCEL_PYTHON` | Excel-only Python executable. Coding Agent `sys.executable` is never used as a fallback. | `$ROOT/.venv/bin/python` |
| `CODING_AGENT_EXCEL_TIMEOUT` | Subprocess timeout in seconds (1–86400) | `180` |
| `CODING_AGENT_EXCEL_OUTPUT_ROOT` | Output root **inside** the current Coding Agent workspace | `<workspace>/.excel_agent` |
| `CODING_AGENT_EXCEL_MODEL` | Model name forwarded to Excel Analyzer | `qwen2.5:7b` (Excel production default) |
| `CODING_AGENT_EXCEL_OLLAMA` | Ollama base URL forwarded to Excel Analyzer | `http://localhost:11434` |

Invalid configuration does not prevent `import coding_agent` or app startup.
The tool returns `configuration_error` when invoked.

Example:

```bash
export CODING_AGENT_EXCEL_ROOT=/home/raven323/Project/excel_ai_analyzer
export CODING_AGENT_EXCEL_PYTHON=/home/raven323/Project/excel_ai_analyzer/.venv/bin/python
export CODING_AGENT_EXCEL_TIMEOUT=180
export CODING_AGENT_EXCEL_OUTPUT_ROOT=/home/raven323/Project/coding_agent/workspace/.excel_agent
./run_app.sh --server.port 8503
```

## Tool usage

Input files may come from chat attachments under `.session_uploads/` or from
files already in the workspace.

- `inspect_spreadsheet`: workbook structure, sheet names, columns, bounded metadata
- `read_spreadsheet`: bounded inspection of selected sheet/columns/rows
- `analyze_excel(files, prompt, analysis_mode="single", profile_name="generic", sheets=None)`:
  natural-language summary, comparison, aggregation, multi-file analysis, and
  Excel Analyzer production pipeline

`analyze_excel` notes:

- Pass workspace-relative or workspace-absolute paths (`.xlsx` / `.xls` / `.xlsm` / `.csv`).
- `single` requires one file; `multi` requires two or more.
- The user prompt is forwarded unchanged. Coding Agent does not rewrite it or
  pick a profile from keywords.
- Output directory is not a tool argument. Each call writes under
  `.excel_agent/<request-id>/`.
- Original uploaded files stay in `.session_uploads/`. Analysis artifacts are a
  separate output tree. Artifact rendering/download UI is not implemented yet
  (I2-C2).

## Boundaries

- Built-in filesystem and `execute` tools remain available for non-Excel work.
  Do not use `execute` to run Excel Analyzer CLI.
- Do not reimplement production semantic analysis with pandas in Coding Agent.
- Excel semantic routing stays in `excel_ai_analyzer`.
- Coding Agent validates paths, runs the process, enforces timeout, checks the
  JSON contract, and verifies artifact hashes/sizes/workspace containment.
- HITL: `deepagents-code==0.1.65` does not expose a public `create_cli_agent`
  API to interrupt custom `tools=` callables. Excel execution is constrained by
  workspace containment instead. Custom `analyze_excel` HITL is not present;
  I2-C1 execution-confirm UI is still required. Do not assume an approval
  prompt for this tool.
