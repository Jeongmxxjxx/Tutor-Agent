"""OpenAI 공통 클라이언트·공통 오류 처리

- OpenAI() 인스턴스는 이 파일에서 한 번만 생성하고, 다른 모듈은 get_client()로 호출
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

import openai
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ---------------------------------------------------------------------------
# 모델 설정
# ---------------------------------------------------------------------------
MODELS: dict[str, str] = {
    "vision": os.getenv("OPENAI_VISION_MODEL", "gpt-4o"),
    "chat": os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
    "stt": os.getenv("OPENAI_STT_MODEL", "whisper-1"),
}

REQUEST_TIMEOUT_SEC = 60
MAX_RETRIES = 2

# ---------------------------------------------------------------------------
# 공통 클라이언트
# ---------------------------------------------------------------------------

class MissingAPIKeyError(RuntimeError):
    """OPENAI_API_KEY가 설정되지 않은 경우"""

def has_api_key() -> bool:
    """API 키 환경변수 등록 여부 확인"""
    return bool(os.getenv("OPENAI_API_KEY"))

@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    """프로세스 전체에서 공유하는 OpenAI 클라이언트 반환"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise MissingAPIKeyError("OPENAI_API_KEY가 설정 필요")
    return OpenAI(api_key=api_key, timeout=REQUEST_TIMEOUT_SEC, max_retries=MAX_RETRIES)


# ---------------------------------------------------------------------------
# 공통 오류 처리: 오류 유형 분류
# ---------------------------------------------------------------------------
def describe_error(error: Exception) -> str:
    """예외를 분류해 화면에 보여줄 메시지로 변환

    각 모듈은 오류를 그대로 raise 하거나, 사용자에게 보여줄 문장을 담아 ValueError로 raise
    """
    if isinstance(error, MissingAPIKeyError):
        return "API 키가 없습니다."

    # --- OpenAI API 오류 (하위 클래스를 먼저 검사) ---
    if isinstance(error, openai.AuthenticationError):
        return "API 키가 올바르지 않습니다."
    if isinstance(error, openai.PermissionDeniedError):
        return "이 API 키는 해당 기능을 사용할 권한이 없습니다."
    if isinstance(error, openai.NotFoundError):
        return "요청한 모델을 찾을 수 없습니다."
    if isinstance(error, openai.RateLimitError):
        if getattr(error, "code", None) == "insufficient_quota":
            return "OpenAI 사용 한도를 모두 사용했습니다."
        return "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."
    if isinstance(error, openai.BadRequestError):
        return "요청을 처리할 수 없습니다. 파일 형식이나 크기를 확인하고 다시 시도해 주세요."
    if isinstance(error, openai.APITimeoutError):
        return "응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
    if isinstance(error, openai.APIConnectionError):
        return "OpenAI 서버에 연결할 수 없습니다. 인터넷 연결을 확인해 주세요."
    if isinstance(error, openai.InternalServerError):
        return "OpenAI 서버에 일시적인 문제가 있습니다. 잠시 후 다시 시도해 주세요."
    if isinstance(error, openai.APIError):
        return "AI 응답을 받는 중 오류가 발생했습니다. 다시 시도해 주세요."

    # --- 데이터 처리 오류 ---
    if isinstance(error, json.JSONDecodeError):
        return "저장된 데이터 또는 AI 응답의 형식이 올바르지 않습니다."
    if isinstance(error, FileNotFoundError):
        return "필요한 파일을 찾을 수 없습니다."
    if isinstance(error, PermissionError):
        return "파일에 접근할 권한이 없습니다."
    if isinstance(error, OSError):
        return "파일을 읽거나 저장하는 중 오류가 발생했습니다."
    if isinstance(error, ValueError) and str(error):
        # 모듈에서 사용자에게 보여줄 문장을 담아 raise 한 경우
        return str(error)

    return "알 수 없는 오류가 발생했습니다. 다시 시도해 주세요."