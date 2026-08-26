# Coding Agent

Streamlit 코딩 워크벤치. **에이전트 엔진은 [deepagents-code](https://pypi.org/project/deepagents-code/)** 이고, UI만 tasking-agent 스타일 3-pane.

모델: Ollama `gemma4:31b` (`ollama:gemma4:31b`)

## 구조

```mermaid
flowchart TB
    UI["Streamlit UI · app.py<br/>events: assistant · tool_call · tool_result<br/>file_change · interrupt · test_result"]
    Bridge["DeepAgentsBridge · bridge.py<br/>create_cli_agent()<br/>SqliteSaver thread 재개<br/>HITL approve/reject"]
    Runtime["deepagents-code runtime"]
    Model["Ollama gemma4:31b"]
    Hands["Hands<br/>ls · read_file · write_file · edit_file · execute"]
    WS["workspace/"]
    Data["data/checkpoints.sqlite<br/>data/messages/"]

    UI --> Bridge
    Bridge --> Runtime
    Bridge --> Data
    Runtime --> Model
    Runtime --> Hands
    Hands --> WS
```



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


| 변수                        | 기본                       |
| ------------------------- | ------------------------ |
| `CODING_AGENT_MODEL`      | `gemma4:31b`             |
| `CODING_AGENT_OLLAMA`     | `http://127.0.0.1:11434` |
| `CODING_AGENT_WORKSPACE`  | `./workspace`            |
| `CODING_AGENT_DATA`       | `./data`                 |
| `CODING_AGENT_MAX_ROUNDS` | `12`                     |


## 참고

- [https://pypi.org/project/deepagents-code/](https://pypi.org/project/deepagents-code/)
- [https://github.com/FeynmanZhou/tasking-agent](https://github.com/FeynmanZhou/tasking-agent) (DeepAgentsBridge / 이벤트 정규화 UX)
- 이후 `research-memory` Coding Agent 페이지로 추가 예정

