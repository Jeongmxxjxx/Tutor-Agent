"""질문·답변 생성

[임시] 구현 전까지 화면 테스트용으로 받은 입력을 그대로 보여 줌

이 파일 담당은 임시 함수를 지우고 실제 구현으로 교체
"""


def chat(history: list[dict], stage: str) -> str:
   last = history[-1]["content"] if history else ""
   return f"**[임시 응답 · stage={stage}]**\n\n{last}"