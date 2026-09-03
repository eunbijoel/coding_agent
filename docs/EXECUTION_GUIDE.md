# Coding Agent 실행·테스트 가이드

---

## 1. 시스템 개요

### 실행 흐름

```text
사용자 프롬프트
→ Streamlit Coding Agent UI
→ DeepAgentsBridge
→ deepagents-code
→ Ollama gemma4:31b
→ 파일 작성·수정·명령 실행
→ 코드 및 실행 결과 확인
```

### Coding Agent 주요 기능


| 기능                  | 사용자에게 의미하는 것                                         |
| ------------------- | ---------------------------------------------------- |
| **자연어 기반 프로젝트 생성**  | 채팅에 원하는 앱을 설명하면 코드와 파일 구조를 자동으로 만들어 줌                |
| **파일 구조 확인**        | 사이드바 **Files** 트리에서 `workspace/` 내용을 탐색              |
| **코드 확인 및 직접 수정**   | 오른쪽 Editor에서 파일을 열고 수정·저장                            |
| **Tool 실행 전 승인·거절** | 파일 쓰기·셸 실행 전 **Approve** / **Reject**로 통제            |
| **Terminal 실행**     | 하단 **Terminal**에서 `pytest`, `streamlit run` 등을 직접 실행 |
| **웹 Preview**       | Header **Preview**로 Streamlit/HTML 앱을 미리 확인          |




## 2. 실행 환경


| 구분              | 실제 측정값                      |
| --------------- | --------------------------- |
| GPU             | NVIDIA GeForce RTX 5090 x 2 |
| GPU 메모리         | GPU당 약 32GB                 |
| CPU             | Intel(R) Core(TM) i7-14700K |
| System RAM      | 31 GB total                 |
| OS              | Linux 6.8.0-124-generic     |
| NVIDIA Driver   | 575.57.08                   |
| CUDA            | 12.9                        |
| deepagents-code | 0.1.65 (`.venv` 설치 기준)      |
| Streamlit       | 1.63.0 (`.venv` 설치 기준)      |
| 사용 모델           | Ollama `gemma4:31b`         |




## 3. 설치 및 실행 방법



### 사전 조건

- Python 3.12 이상
- [Ollama](https://ollama.com/) 설치 및 실행
- `ollama pull gemma4:31b`
- Git
- GPU VRAM 24GB 이상 권장 (31B 모델 기준)



### 설치

```bash
git clone https://github.com/eunbijoel/coding_agent.git
cd coding_agent
chmod +x run_app.sh
```

수동 설치:

```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
streamlit run app.py
```



### 실행

```bash
./run_app.sh
```



### 3-1 간단 활용 방법

1. Coding Agent를 실행
2. 채팅창에 프롬프트 입력
3. 파일 작성과 명령 실행 요청을 확인한 후 승인
4. 생성된 파일을 사이드바에서 확인
5. Terminal에서 테스트를 실행하거나 Preview에서 결과 확인

상세 설치 및 기능 설명은 프로젝트 [README](https://github.com/eunbijoel/coding_agent)를 참고합니다.

## 4. 테스트 프롬프트 예

```text
workspace/mini_research_agents 폴더에 실행 가능한 최소 멀티에이전트 시스템을 처음부터 만들어줘.

프로젝트 이름은 Mini Research Brief Agents

사용자가 연구 주제와 참고 메모를 입력하면 다음 4개의 역할 기반 에이전트가 순차적으로 협업하여 짧은 연구 브리프를 작성하는 Streamlit 웹 앱을 만든다.

1. Planner Agent
2. Writer Agent
3. Reviewer Agent
4. Reviser Agent

각 에이전트는 동일한 Ollama gemma4:31b 모델에 서로 다른 system prompt를 적용하여 역할을 구분한다.

파일 구조는 app.py, agents.py, ollama_client.py, prompts.py, requirements.txt, README.md, tests/test_pipeline.py 정도로 제한한다.

구현 후 py_compile과 pytest를 실행하고, Streamlit 앱을 실행하여 결과를 확인해줘.
```
<img width="1885" height="900" alt="image" src="https://github.com/user-attachments/assets/1d50d726-49da-494b-aa35-653cf05ef168" />

1. 사용자가 연구 주제와 참고 메모를 입력하면 Planner, Writer, Reviewer, Reviser가 순차적으로 협업하여 연구 브리프를 작성하는 Streamlit 앱 생성.
2. 각 에이전트는 동일한 Ollama gemma4:31b 모델에 프롬프트를 적용.
3. 구현 후 Python 문법검사와 단위 테스트를 수행하고, Streamlit 앱을 실행하여 결과 확인.



Coding Agent는 위 요청에 따라 프로젝트 구조와 Python 파일을 생성하고, 문법검사·단위 테스트 및 웹 앱 실행까지 수행함.

---



## 5. 테스트 설명



### 입력 예시

```text
중소 제조기업의 생성형 AI 도입 방안
```

### 참고 메모

```text
중소기업은 전문인력
과 GPU 비용이 부족하다. 보안 때문에 생산데이터를 외부 API로 보내기 어렵다. 초기에는 문서 검색, 설비 매뉴얼 질의응답, 보고서 작성과 같은 저위험 업무부터 적용할 필요가 있다.
```
<img width="1861" height="832" alt="image" src="https://github.com/user-attachments/assets/7dbe8d3f-0bf1-4947-9d2e-f79c07bad709" />

## 6. 실행 시간 측정


| 실행    | Planner | Writer | Reviewer | Reviser | 전체     |
| ----- | ------- | ------ | -------- | ------- | ------ |
| 1차    | 38.6s   | 35.0s  | 26.0s    | 37.8s   | 137.4s |
| 2차    | 85.8s   | 32.8s  | 20.9s    | 62.3s   | 201.8s |
| 3차 실행 | 18.9s   | 38.6s  | 25.7s    | 41.0s   | 124.3s |
| 중앙값   | 38.6s   | 35.0s  | 25.7s    | 41.0s   | 137.4s |


Coding Agent가 프로젝트 코드 전체를 최초 생성하는 시간은 별도로 계측하지 않았으며, 위 결과는 생성된 멀티에이전트 앱의 실행시간입니다.

### 추가 검증 항목


| 항목               | 결과                                        |
| ---------------- | ----------------------------------------- |
| 최초 모델 로딩 시간      | Planner 38.6s에 포함                         |
| 실행 중 최대 GPU VRAM | GPU0 22645 MiB, GPU1 21839 MiB (2 GPU 사용) |
| 정상 완료 여부         | 3회 성공                                     |
| 오류 및 재시도 여부      | 1차 Ollama 500 오류 1회 → 5초 대기 후 재시도 성공      |
| 최종 출력 문자 수       | 1차 3223 / 2차 3921 / 3차 3375               |


