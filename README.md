# Coding Agent

Cursor 스타일 로컬 코딩 에이전트. Ollama `gemma4:31b` + 워크스페이스 도구 루프로, 채팅·코드·트레이싱을 한 화면에서 보여 줍니다.

나중에 검증되면 `research-memory`의 **Coding Agent** 페이지로 이식할 예정입니다.

## What it does:

[tasking-agent (Agent Harness Console)](https://github.com/FeynmanZhou/tasking-agent) / [deepagents-code](https://pypi.org/project/deepagents-code/)를 참고한 **경량 웹 워크벤치**입니다.


| Pane           | 역할                                 |
| -------------- | ---------------------------------- |
| Left (sidebar) | 모델 · workspace · 파일 트리             |
| Center         | Chat + deepagents-code 스타일 프롬프트 입력 |
| Right-center   | Code / Artifacts (파일 내용 · diff)    |
| Far right      | Tracing (LLM/tool 스텝)              |


**Brain / Hands**

- Brain: Ollama chat API (`tools` 네이티브) — 기본 `gemma4:31b`
- Hands: workspace 한정 `list_dir` / `read_file` / `write_file` / `edit_file` / `grep` / `run_shell`

이벤트 타입은 tasking-agent와 비슷하게 정규화했습니다: `assistant_delta`, `tool_call`, `tool_result`, `file_view`, `trace`, `error`, `done`.

> 로컬 Python이 3.10이라 `deepagents-code`(Python ≥3.12)는 의존성에 넣지 않았습니다. UX·도구 루프는 동일 계열로 맞춰 두었고, 이후 3.12+ 환경이면 dcode 런타임으로 교체 가능합니다.



## 실행

전제: Ollama 실행 중, `gemma4:31b` pull 완료.

```bash
cd ~/coding-agent
chmod +x run_app.sh
./run_app.sh
```

또는:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

환경 변수(선택):


| 변수                        | 기본                       |
| ------------------------- | ------------------------ |
| `CODING_AGENT_MODEL`      | `gemma4:31b`             |
| `CODING_AGENT_OLLAMA`     | `http://127.0.0.1:11434` |
| `CODING_AGENT_WORKSPACE`  | `./workspace`            |
| `CODING_AGENT_MAX_ROUNDS` | `12`                     |


## 구조

```
coding-agent/
├── app.py                 # Streamlit 3-pane UI
├── coding_agent/
│   ├── agent.py           # tool loop
│   ├── events.py          # normalized events
│   ├── ollama_client.py
│   ├── tools.py           # Hands
│   └── config.py
├── workspace/             # agent cwd
├── requirements.txt
└── run_app.sh
```

