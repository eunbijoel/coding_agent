# Coding Agent

Streamlit 코딩 워크벤치. **에이전트 엔진은 [deepagents-code](https://pypi.org/project/deepagents-code/)** 이고, UI만 tasking-agent 스타일 3-pane으로 감쌉니다.

모델: Ollama **`gemma4:31b`** (`ollama:gemma4:31b`)

## 구조 (현재)

```
Streamlit UI (app.py)
   │  events: assistant / tool_call / tool_result / file_change / interrupt / test_result
   ▼
DeepAgentsBridge (coding_agent/bridge.py)
   │  create_cli_agent()  ← deepagents-code 실제 import·실행
   │  SqliteSaver checkpointer (thread 재개)
   │  HITL approve/reject (auto_approve=False 일 때)
   ▼
deepagents-code Hands (ls / read_file / write_file / edit_file / execute / …)
   ▼
workspace/  +  data/checkpoints.sqlite  +  data/messages/
```

자체 Ollama tool loop는 **주 엔진이 아닙니다.** `coding_agent/agent.py`는 Bridge 호출 facade일 뿐입니다.

## 요구사항

- Python **≥ 3.12**
- [uv](https://github.com/astral-sh/uv) 권장
- Ollama + `gemma4:31b`

## 실행

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # 없으면
cd ~/coding-agent
chmod +x run_app.sh
./run_app.sh
```

또는:

```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
streamlit run app.py
```

환경 변수:

| 변수 | 기본 |
|------|------|
| `CODING_AGENT_MODEL` | `gemma4:31b` |
| `CODING_AGENT_OLLAMA` | `http://127.0.0.1:11434` |
| `CODING_AGENT_WORKSPACE` | `./workspace` |
| `CODING_AGENT_DATA` | `./data` |
| `CODING_AGENT_MAX_ROUNDS` | `12` |

## deepagents-code 사용 지점 (확인용)

| 파일 | 내용 |
|------|------|
| `requirements.txt` / `pyproject.toml` | `deepagents-code[ollama]>=0.1.62` |
| `coding_agent/bridge.py` | `import deepagents_code` + `from deepagents_code.agent import create_cli_agent` |
| `DeepAgentsBridge.agent` | `create_cli_agent(model="ollama:…", checkpointer=SqliteSaver, auto_approve=…)` |
| `DeepAgentsBridge.run` | `agent.stream({"messages": […]}, config={thread_id})` |
| `DeepAgentsBridge.resume` | `agent.stream(Command(resume={"decisions": […]}), …)` HITL 재개 |

설치 확인:

```bash
source .venv/bin/activate
python -c "import deepagents_code; from deepagents_code.agent import create_cli_agent; print(deepagents_code.__version__, create_cli_agent)"
```

## UI 기능

| Pane | 기능 |
|------|------|
| Sidebar | Thread 생성/재개/삭제, 모델, Auto-approve, workspace 파일 트리 |
| Chat | Prompt 입력, tool 표시, **Approve / Reject** (HITL) |
| Code | 파일 preview, 변경 diff, py_compile(/pytest) 결과 |
| Tracing | deepagents middleware / tool 스텝 |

- **Thread:** UI 메시지는 `data/messages/{id}.json`, LangGraph 상태는 `data/checkpoints.sqlite`
- **승인:** 기본은 HITL on (`execute` / `write_file` / `edit_file` / `delete`). 사이드바 Auto-approve로 YOLO 가능
- **검증:** 턴 종료 시 workspace 스냅샷 diff + `py_compile` (+ `tests/` 있으면 pytest)

## 참고

- https://pypi.org/project/deepagents-code/
- https://github.com/FeynmanZhou/tasking-agent (DeepAgentsBridge / 이벤트 정규화 UX)
- 이후 `research-memory` Coding Agent 페이지로 이식 예정

## 예시 프롬프트

```
이 깃에서처럼 deep agent editor (deepagents-code) 스타일로 prompt 입력창 생성해줘
```
