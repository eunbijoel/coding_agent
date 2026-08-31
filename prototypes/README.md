# Prototypes

Isolated Streamlit experiments. Not wired into `app.py` until verified.

## SAC file tree (`sac_file_tree_prototype.py`)

Validates `streamlit-antd-components` `tree()` for a VS Code–style sidebar explorer.

```bash
uv pip install streamlit-antd-components==0.3.2   # prototype only; not in requirements.txt yet
.venv/bin/streamlit run prototypes/sac_file_tree_prototype.py
```

See the verification checklist in the app UI after clicking files and folders.
