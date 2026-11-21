# AGENTS.md

이 문서는 이 저장소에서 작업하는 AI 에이전트와 팀원이 지켜야 할 규칙이다    
프로젝트 설명은 `README.md`를 참고한다

---

## 프로젝트 요약

- 멀티모달 AI 튜터 (음성·이미지 기반 개인 맞춤형 학습 대시보드)
- 문제 사진/음성 질문 → 단계별 힌트·해설 → 유사 퀴즈

## 환경

| 구분 | 사용 기술 |
|---|---|
| 언어 | Python 3.12 |
| LLM SDK | `openai==1.58.1` (Chat Completions API) |
| 환경변수 | `python-dotenv` + `.env` |
| UI | Streamlit |
- 새 패키지를 추가하면 반드시 `requirements.txt`를 갱신한다

## OpenAI API 사용 규칙
- 공통 OpenAI 클라이언트를 modules/client.py에서 생성한다
- 모든 기능 모듈은 공통 클라이언트를 사용한다
- 텍스트 및 이미지 분석은 Chat Completions API를 사용한다
- STT는 Audio Transcriptions API를 사용한다
- 모델 ID는 설정 파일에서 관리한다
- API 키를 소스 코드에 직접 작성하지 않는다

## 폴더 구조

```
app.py          # Streamlit 화면만
prompts.py      # 모든 프롬프트 문자열
modules/
  client.py
  llm.py        # 질문·답변 생성
  vision.py     # 이미지 글자·수식 추출
  stt.py        # STT
  quiz.py       # 유사 퀴즈 생성
```

- 한 파일에 한 기능이며, 새 기능은 `modules/`에 새 파일로 만든다.
- `OpenAI()` 클라이언트는 `client.py`에서 한 번만 생성하고 다른 모듈은 불러서 사용한다
- `app.py`는 화면 구성과 `st.session_state` 관리만 담당한다
- 프롬프트 문자열은 `prompts.py`에 모으고, 모듈 안의 짧은 지시문은 예외로 허용한다

## 튜터 동작 규칙

에이전트가 생성하는 해설은 반드시 아래 내용을 따른다

1. 이미지·음성을 입력받고 문제 내용을 추출한다
2. 정답을 노출하지 않고 핵심 개념이나 힌트만 제공한다
3. 어떤 개념을 적용해야 하는지, 어떤 순서로 접근해야 하는지 안내한다
4. 사용자의 요청 시 전체 풀이와 정답을 제공한다
5. 동일한 개념을 활용하는 새로운 문제를 생성한다

## 오류 처리

| 위치 | 역할 |
| --- | --- |
| 각 모듈 | API 오류·데이터 처리 오류 감지 |
| 공통 오류 처리 | 오류 유형 분류 및 사용자 친화적 메시지 생성 |
| app.py | 오류 메시지를 화면에 표시 후 UI 상태 복구 |

## 커밋 규칙

- 형식: `<타입>: <요약>` 요약은 한국어로, 50자 이내
- 타입: `feat`(기능) · `fix`(버그) · `refactor` · `docs` · `style` · `chore`
- 예시
  ```
  feat: Whisper 음성 질문 입력 추가
  fix: 같은 녹음이 반복 전송되는 문제 수정
  docs: README 설치 방법 보완
  ```
- `main` 브랜치에 직접 커밋하지 않고 기능별 브랜치에서 작업한다.

## 모듈 구현 시 반드시 지킬 것

담당 모듈(`modules/*.py`)을 구현할 때 아래 규칙을 지킨다.

- **오류 처리**: 실패하면 예외를 그대로 `raise`한다. 사용자에게 보여줄 문구가 있으면 `raise ValueError("문구")`로 던진다. `except`로 잡아서 오류 문구를 `return`하지 않는다. 반환값은 그대로 화면에 답변으로 표시되고, 예외만 `modules/client.py`의 `describe_error()`가 오류 메시지로 바꿔 준다.
- **수정 범위**: `app.py`는 수정하지 않는다. 담당 파일만 수정하고, `prompts.py`는 담당 모듈의 프롬프트 변수만 수정한다.
- **클라이언트·모델**: `OpenAI()`를 새로 만들지 않고 `from modules.client import get_client, MODELS`로 가져와 쓴다. 모델 ID를 코드에 직접 쓰지 않고 `MODELS["chat"]`, `MODELS["vision"]`, `MODELS["stt"]`를 쓴다.
- **API**: 텍스트·이미지는 Chat Completions API(`client.chat.completions.create`)만 사용한다. STT만 Audio Transcriptions API를 사용한다.
- **프롬프트**: 모듈 안에 프롬프트를 새로 작성하지 않고 `prompts.py`에 있는 변수를 import해서 쓴다. 단, 모듈 안의 짧은 지시문은 예외로 허용한다.
- **패키지**: 새 패키지를 쓰면 `requirements.txt`에 버전과 함께 추가한다.

## app.py 연결 규칙

`app.py`는 아래 이름의 함수를 자동으로 찾아 호출한다. 함수 이름·인자 순서·반환 형태를 그대로 지키면 `app.py`를 수정하지 않아도 연결된다.

| 파일 | 함수 | 인자 | 반환 |
|---|---|---|---|
| `modules/stt.py` | `transcribe(audio, audio_name)` | `audio: bytes` 녹음 파일, `audio_name: str` 파일명 (예: `"recording.wav"`) | 인식한 텍스트 `str` |
| `modules/vision.py` | `extract_problem(image, image_mime)` | `image: bytes` 이미지 파일, `image_mime: str` MIME 타입 (예: `"image/png"`) | 추출한 문제 텍스트 `str` |
| `modules/llm.py` | `chat(history, stage)` | `history: list[dict]` `{"role", "content"}` 대화 기록, `stage: str` 답변 단계 | 튜터 답변 `str` |
| `modules/quiz.py` | `generate_quiz(problem)` | `problem: str` 현재 문제 텍스트 | 유사 퀴즈 텍스트 `str` (마크다운) |

- 반환값은 빈 문자열이나 `None`이 아니어야 한다. 실패하면 위 오류 처리 규칙대로 예외를 던진다.
- `stage` 값은 `"hint"`(힌트), `"approach"`(풀이 방향), `"solution"`(전체 풀이와 정답), `"followup"`(이어지는 질문) 중 하나다.