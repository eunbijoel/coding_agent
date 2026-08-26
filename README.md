# Coding Agent

Cursor 스타일 로컬 코딩 에이전트. **[deepagents-code](https://pypi.org/project/deepagents-code/)** 하네스 + Ollama **`gemma4:31b`** 로 동작하고, 채팅·코드·트레이싱을 한 화면에서 보여 줍니다.

나중에 검증되면 `research-memory`의 **Coding Agent** 페이지로 이식할 예정입니다.

## 스택

| 층 | 기술 |
|----|------|
| UI | Streamlit 3-pane (chat / code / tracing) |
| Brain | [deepagents-code](https://pypi.org/project/deepagents-code/) `create_cli_agent` |
| Model | Ollama `gemma4:31b` (`ollama:gemma4:31b`) |
| Hands | dcode filesystem + shell (workspace `cwd`) |

[tasking-agent](https://github.com/FeynmanZhou/tasking-agent) 의 이벤트/3-pane UX를 참고했고, 에이전트 실행은 deepagents-code 를 그대로 사용합니다.

**요구사항:** Python **≥ 3.12** (uv 권장).

## 실행

전제: Ollama 실행 중, `gemma4:31b` pull 완료.

```bash
# uv (권장)
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

환경 변수(선택):

| 변수 | 기본 |
|------|------|
| `CODING_AGENT_MODEL` | `gemma4:31b` (자동으로 `ollama:` prefix) |
| `CODING_AGENT_OLLAMA` | `http://127.0.0.1:11434` |
| `CODING_AGENT_WORKSPACE` | `./workspace` |
| `CODING_AGENT_MAX_ROUNDS` | `12` |

## 예시 프롬프트

```
이 깃에서처럼 deep agent editor (deepagents-code) 스타일로 prompt 입력창 생성해줘
```

## 구조

```
coding-agent/
├── app.py                 # Streamlit 3-pane UI
├── coding_agent/
│   ├── agent.py           # deepagents-code bridge + event stream
│   ├── events.py          # normalized UI events
│   ├── ollama_client.py   # model list / health
│   ├── tools.py           # sidebar file tree helpers
│   └── config.py
├── workspace/             # agent cwd
├── requirements.txt
└── run_app.sh
```

## research-memory로 옮길 때

1. Python 3.12+ venv 와 `deepagents-code[ollama]` 의존성 추가
2. `coding_agent/` 패키지를 엔진 아래로 복사
3. `_coding_agent_page()` 에서 이 UI/`run_agent` 호출
