# AI 튜터 (음성 · 이미지 기반 학습 대시보드)

> 사진을 찍어서 올리거나 목소리로 질문하면, AI 튜터가 힌트와 해설을 알려 주고 비슷한 유형의 퀴즈까지 만들어 주는 학습 도우미입니다

---

## 주요 기능
1. 하나의 채팅창에서 텍스트·사진·음성으로 질문
2. 단계별 AI 해설 (힌트 / 풀이 방향 / 해설)
3. 유사 퀴즈 생성

## 필요 패키지

```powershell
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화 (Windows PowerShell)
.venv\Scripts\Activate.ps1

# 가상환경 활성화 (macOS / Linux)
source .venv/bin/activate

# 패키지 설치
pip install -r requirements.txt

# 환경변수 설정
# .env 파일에 OPENAI_API_KEY 등록

# 실행
streamlit run app.py
```

---

## 폴더 구조

```
tutor_agent/
├── .env                  
├── .gitignore            
├── requirements.txt      # 필요 패키지 목록            
├── README.md             
├── AGENTS.md             
├── app.py                # 웹 화면
├── prompts.py            # 튜터의 말투·규칙 프롬프트
└── modules/             
    ├── client.py         # OpenAI 클라이언트 생성 및 공유
    ├── llm.py            # 질문·답변 생성
    ├── vision.py         # 이미지 분석
    ├── stt.py            # 음성 인식
    ├── tts.py            # 음성 출력
    └── quiz.py           # 유사 퀴즈 생성
```

---

## 비고

- 사진 분석은 정확도를 고려해 `gpt-4o`를 사용합니다
- 일반 대화·퀴즈 생성은 `gpt-4o-mini`를 사용합니다