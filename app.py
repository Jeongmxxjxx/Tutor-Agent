"""Streamlit 화면으로 app.py는 화면 구성과 st.session_state 관리 담당"""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any

import streamlit as st

from modules.client import describe_error

st.set_page_config(page_title="AI 튜터", layout="wide")

IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]

# (stage, 버튼 이름, 화면에 남길 사용자 요청 문장)
ACTIONS = {
    "approach": ("풀이 방향", "풀이 방향을 알려 주세요."),
    "solution": ("정답과 전체 풀이", "전체 풀이와 정답을 보여 주세요."),
    "quiz": ("유사 퀴즈", "같은 개념으로 유사 문제를 내 주세요."),
}
STEPS = ("hint", "approach", "solution")


# ---------------------------------------------------------------------------
# 기능 모듈 연결
# ---------------------------------------------------------------------------

def _load_module(name: str) -> ModuleType | None:
    try:
        return importlib.import_module(f"modules.{name}")
    except ModuleNotFoundError as e:
        if e.name == f"modules.{name}":
            return None  # 아직 파일 없음
        raise


MODULES = {name: _load_module(name) for name in ("vision", "stt", "llm", "quiz")}


def call_module(module: str, func: str, *args: Any, spinner: str = "처리 중...") -> Any:
    """기능 모듈 호출. 실패하면 오류 메시지를 상태에 저장하고 None을 반환한다."""
    target = getattr(MODULES.get(module), func, None)
    if not callable(target):
        st.session_state.error = f"modules/{module}.py의 {func}()가 아직 구현되지 않았습니다."
        return None
    try:
        with st.spinner(spinner):
            return target(*args)
    except Exception as e:
        st.session_state.error = describe_error(e)
        return None


# ---------------------------------------------------------------------------
# 세션 상태
# ---------------------------------------------------------------------------

def new_state() -> dict[str, Any]:
    return {
        # 채팅 기록: {"role", "content", "text", "image", "audio", "problem", "stage"}
        "messages": [],
        "problem": "",          # 현재 문제 텍스트
        "problem_start": 0,     # LLM에 넘길 기록의 시작 위치
        "steps": set(),         # 현재 문제에서 진행한 단계 (hint / approach / solution)
        "pending": None,        # 이번 실행에서 처리할 입력 {"text", "image", "image_mime", "audio", "audio_name", "action"}
        "error": None,
    }


def init_state() -> None:
    for key, value in new_state().items():
        st.session_state.setdefault(key, value)


def start_new_chat() -> None:
    """사이드바 '새 대화'"""
    for key, value in new_state().items():
        st.session_state[key] = value


def llm_history() -> list[dict]:
    """현재 문제의 대화 기록을 llm.chat() 형식으로 만든다."""
    return [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[st.session_state.problem_start:]
    ]


# ---------------------------------------------------------------------------
# 입력 처리
# ---------------------------------------------------------------------------

def queue_input(value: Any) -> None:
    """입력(텍스트·이미지·음성)을 이번 실행에서 처리하도록 저장"""
    image = value.files[0] if value.files else None
    audio = value.audio
    st.session_state.pending = {
        "text": (value.text or "").strip(),
        "image": image.getvalue() if image else None,
        "image_mime": (image.type if image else None) or "image/jpeg",
        "audio": audio.getvalue() if audio else None,
        "audio_name": getattr(audio, "name", None) or "recording.wav",
        "action": None,
    }


def queue_action(action: str) -> None:
    """답변 아래 버튼(풀이 방향·정답·유사 퀴즈) 클릭"""
    st.session_state.pending = {"text": ACTIONS[action][1], "image": None, "audio": None, "action": action}


def handle_pending() -> None:
    """입력을 처리해 사용자·튜터 메시지를 기록에 추가한다.

    중간에 실패하면 아무것도 기록하지 않고 오류만 표시한다 (UI 상태 복구).
    """
    pending = st.session_state.pending
    st.session_state.pending = None
    action = pending["action"]

    # 처리 중에도 사용자 입력이 바로 보이도록 먼저 그린다
    with st.chat_message("user"):
        if pending["image"]:
            st.image(pending["image"], width=280)
        if pending["audio"]:
            st.audio(pending["audio"], format="audio/wav")
        if pending["text"]:
            st.markdown(pending["text"])

    with st.chat_message("assistant"):
        text = pending["text"]

        # 음성 → 텍스트
        if pending["audio"]:
            spoken = call_module("stt", "transcribe", pending["audio"], pending["audio_name"], spinner="음성을 인식하는 중...")
            if spoken is None:
                return
            text = f"{text}\n\n{spoken}".strip()

        # 이미지 → 문제 텍스트
        extracted = None
        if pending["image"]:
            extracted = call_module("vision", "extract_problem", pending["image"], pending["image_mime"], spinner="사진에서 문제를 읽는 중...")
            if extracted is None:
                return

        if not text and not extracted:
            st.session_state.error = "질문 내용을 입력하거나 이미지·음성을 첨부해 주세요."
            return

        # 이미지가 오거나 현재 문제가 없으면 새 문제, 아니면 이어지는 질문
        is_new_problem = action is None and (extracted is not None or not st.session_state.problem)
        content = text
        if extracted is not None:
            content = f"[사진에서 인식한 문제]\n{extracted}" + (f"\n\n{text}" if text else "")

        # 실패 시 되돌릴 상태
        prev = (st.session_state.problem, st.session_state.problem_start, set(st.session_state.steps))
        if is_new_problem:
            st.session_state.problem = (extracted or text).strip()
            st.session_state.problem_start = len(st.session_state.messages)
            st.session_state.steps = set()
        st.session_state.messages.append({
            "role": "user",
            "content": content,      # LLM에 넘기는 내용
            "text": text,            # 화면에 보여줄 문장 (음성은 인식 결과)
            "image": pending["image"],
            "audio": pending["audio"],
            "problem": extracted,
        })

        # 튜터 답변
        if action == "quiz":
            stage = "quiz"
            answer = call_module("quiz", "generate_quiz", st.session_state.problem, spinner="유사 퀴즈를 만드는 중...")
        else:
            stage = action or ("hint" if is_new_problem else "followup")
            answer = call_module("llm", "chat", llm_history(), stage, spinner="튜터가 생각하는 중...")

        if not answer:
            st.session_state.messages.pop()
            st.session_state.problem, st.session_state.problem_start, st.session_state.steps = prev
            return

        st.session_state.messages.append({"role": "assistant", "content": answer, "stage": stage})
        if stage in STEPS:
            st.session_state.steps.add(stage)


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------

def render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        if message.get("image"):
            st.image(message["image"], width=280)
        if message.get("audio"):
            st.audio(message["audio"], format="audio/wav")
        if message.get("problem"):
            with st.expander("인식된 문제"):
                st.markdown(message["problem"])
        st.markdown(message["text"] if message["role"] == "user" else message["content"])


def render_actions() -> None:
    """마지막 튜터 답변 아래의 빠른 버튼"""
    messages = st.session_state.messages
    if not st.session_state.problem or not messages or messages[-1]["role"] != "assistant":
        return

    for col, (action, (label, _)) in zip(st.columns(len(ACTIONS)), ACTIONS.items()):
        col.button(
            label,
            key=f"action_{action}",
            on_click=queue_action,
            args=(action,),
            disabled=action in st.session_state.steps,  # 이미 본 풀이 방향·정답은 비활성화
            width="stretch",
        )


def render_welcome() -> None:
    st.title("AI 튜터")
    with st.chat_message("assistant"):
        st.markdown(
            "안녕하세요! 풀고 싶은 문제를 보내 주세요.\n\n"
            "- **사진**을 올리거나\n"
            "- **음성**으로 얘기하거나\n"
            "- **텍스트**로 입력해도 됩니다.\n\n"
            "차근차근 알려 드릴게요."
        )


# ---------------------------------------------------------------------------
# 실행
# ---------------------------------------------------------------------------

init_state()

with st.sidebar:
    st.title("AI 튜터")
    st.button("새 대화", on_click=start_new_chat, width="stretch")

submitted = st.chat_input(
    "문제를 입력하거나 사진·음성으로 질문하세요",
    accept_file=True,
    file_type=IMAGE_TYPES,
    accept_audio=True,
)
if submitted:
    queue_input(submitted)

if not st.session_state.messages and not st.session_state.pending:
    render_welcome()

for message in st.session_state.messages:
    render_message(message)

if st.session_state.pending:
    handle_pending()
    st.rerun()

if st.session_state.error:
    st.error(st.session_state.error)
    st.session_state.error = None

render_actions()