"""AI 관상가 - Streamlit 앱."""

import datetime
import os
import re
import threading

import openai
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

import styles
from image_utils import (
    MAX_FILE_BYTES,
    ImageProcessingError,
    ImageTooLargeError,
    image_hash,
    is_size_ok,
    preprocess_image,
    to_base64,
)
from prompts import DEFAULT_TONE, NO_FACE_MESSAGE, TONES, USER_PROMPT, build_system_prompt

load_dotenv()

DEFAULT_MODEL = "gpt-4.1-mini"
MAX_ANALYSES_PER_SESSION = 10
DEFAULT_DAILY_LIMIT = 200  # 서버 전체(모든 접속자 합계) 하루 API 호출 상한. DAILY_LIMIT로 변경 가능
API_TIMEOUT_SECONDS = 60
# gpt-5 계열 같은 추론 모델은 내부 추론에도 토큰을 쓰므로 넉넉하게 둔다.
MAX_COMPLETION_TOKENS = 1500

DISCLAIMER = "⚠️ 재미로 보는 관상입니다. 과학적 근거가 없으니 결과를 진지하게 받아들이지 마세요."
PRIVACY_NOTICE = (
    "🔒 사진은 저장되지 않으며 분석을 위해 OpenAI로 전송됩니다. "
    "본인 또는 동의를 받은 사람의 사진만 올려 주세요."
)


def get_secret(key: str, default: str | None = None) -> str | None:
    """Streamlit Cloud의 st.secrets를 먼저 보고, 없으면 .env/환경변수를 읽는다."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        # 로컬에 .streamlit/secrets.toml이 없으면 예외가 발생한다.
        pass
    return os.getenv(key, default)


class AnalysisError(Exception):
    """모델 응답을 결과로 쓸 수 없을 때 발생한다. 메시지는 사용자에게 그대로 보여준다."""


class DailyLimitError(Exception):
    """서버 전체의 하루 호출 상한에 도달했을 때 발생한다."""


class DailyUsage:
    """모든 세션이 공유하는 하루 호출 카운터 (서버 메모리에만 있음, 재시작 시 초기화)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._date = datetime.date.today()
        self._count = 0

    def try_acquire(self, limit: int) -> bool:
        """상한 안이면 1회를 차감하고 True, 상한에 도달했으면 False."""
        with self._lock:
            today = datetime.date.today()
            if today != self._date:
                self._date, self._count = today, 0
            if self._count >= limit:
                return False
            self._count += 1
            return True


@st.cache_resource
def get_daily_usage() -> DailyUsage:
    return DailyUsage()


def get_daily_limit() -> int:
    try:
        return max(int(get_secret("DAILY_LIMIT") or DEFAULT_DAILY_LIMIT), 0)
    except ValueError:
        return DEFAULT_DAILY_LIMIT


def extract_result(response) -> str:
    """API 응답에서 결과 텍스트를 꺼낸다. 거절·잘림·빈 응답이면 AnalysisError."""
    if not response.choices:
        raise AnalysisError("관상가가 아무 말도 하지 않았소. 다시 시도해 주세요.")
    choice = response.choices[0]
    message = choice.message
    if getattr(message, "refusal", None):
        raise AnalysisError("관상가가 이 사진의 풀이를 사양했소. 얼굴이 잘 보이는 다른 사진으로 시도해 주세요.")
    content = (message.content or "").strip()
    if choice.finish_reason == "length":
        raise AnalysisError("풀이가 너무 길어 중간에 끊겼소. 다시 시도해 주세요.")
    if choice.finish_reason == "content_filter":
        raise AnalysisError("이 사진은 풀이할 수 없소. 다른 사진으로 시도해 주세요.")
    if not content:
        raise AnalysisError("관상가가 아무 말도 하지 않았소. 다시 시도해 주세요.")
    return content


def analyze_face(client: OpenAI, model: str, image_b64: str, tone: str) -> str:
    """OpenAI 비전 모델에 이미지를 보내 관상 풀이 텍스트를 받는다."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": build_system_prompt(tone)},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                    },
                ],
            },
        ],
        max_completion_tokens=MAX_COMPLETION_TOKENS,
    )
    return extract_result(response)


def friendly_error(exc: Exception) -> str:
    """예외를 사용자용 한국어 메시지로 바꾼다. 스택트레이스는 보여주지 않는다."""
    if isinstance(exc, AnalysisError):
        return str(exc)
    if isinstance(exc, DailyLimitError):
        return "오늘은 관상가가 너무 많은 얼굴을 보아 쉬어야 하오. 내일 다시 찾아 주시오."
    if isinstance(exc, openai.AuthenticationError):
        return "API 키가 올바르지 않습니다. OPENAI_API_KEY 설정을 확인해 주세요."
    if isinstance(exc, openai.RateLimitError):
        return "요청이 너무 많거나 API 사용 한도를 넘었습니다. 잠시 후 다시 시도해 주세요."
    if isinstance(exc, openai.APITimeoutError):
        return "관상가의 응답이 너무 늦어 시간이 초과되었습니다. 다시 시도해 주세요."
    if isinstance(exc, openai.APIConnectionError):
        return "OpenAI 서버에 연결할 수 없습니다. 인터넷 연결을 확인해 주세요."
    if isinstance(exc, openai.BadRequestError):
        return "요청이 거절되었습니다. 다른 사진으로 시도하거나 모델 설정(OPENAI_MODEL)을 확인해 주세요."
    if isinstance(exc, openai.APIError):
        return "OpenAI 서버에서 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
    return "알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."


# ---------- 결과 파싱 (화면 구성용) ----------

SECTION_KEYS = ("첫인상", "부위별 관상", "종합 운세", "한 줄 요약")
_PART_LINE = re.compile(r"^\s*[-*]\s*\*\*(.+?)\*\*\s*[:：]\s*(.+?)\s*$")


def parse_sections(text: str) -> dict[str, str]:
    """'## ...' 제목 기준으로 결과를 나눈다. 제목에 SECTION_KEYS가 들어 있으면 그 키로 저장한다."""
    sections: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                sections[current] = "\n".join(buf).strip()
            current = next((k for k in SECTION_KEYS if k in line), line[3:].strip())
            buf = []
        elif current:
            buf.append(line)
    if current:
        sections[current] = "\n".join(buf).strip()
    return sections


def parse_parts(body: str) -> list[tuple[str, str]]:
    """'- **이마**: 풀이' 형식의 줄을 [(이마, 풀이)]로 바꾼다."""
    return [(m.group(1).strip(), m.group(2)) for line in body.splitlines() if (m := _PART_LINE.match(line))]


def clean_summary(body: str) -> str:
    return body.strip().strip('"“”').strip()


# ---------- 화면 ----------


def init_state() -> None:
    st.session_state.setdefault("analysis_count", 0)
    st.session_state.setdefault("result", None)  # 마지막 분석 결과 텍스트
    st.session_state.setdefault("result_key", None)  # (이미지 해시, 말투)
    st.session_state.setdefault("input_nonce", 0)  # 입력 위젯 초기화용
    st.session_state.setdefault("input_source", None)  # 마지막으로 입력한 쪽: "upload" / "camera"


def reset_for_new_photo() -> None:
    st.session_state.result = None
    st.session_state.result_key = None
    st.session_state.input_nonce += 1
    st.session_state.input_source = None


def _mark_source(source: str) -> None:
    st.session_state.input_source = source


def pick_source(uploaded, captured, last: str | None):
    """업로드와 촬영이 둘 다 있으면 마지막으로 입력한 쪽을 쓴다."""
    if last == "camera" and captured is not None:
        return captured
    if last == "upload" and uploaded is not None:
        return uploaded
    return uploaded if uploaded is not None else captured


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown('<p class="gs-side-title">관상가의 방</p>', unsafe_allow_html=True)
        tone = st.radio("관상가 말투", list(TONES.keys()), index=list(TONES).index(DEFAULT_TONE))
        remaining = max(MAX_ANALYSES_PER_SESSION - st.session_state.analysis_count, 0)
        st.metric("남은 분석 횟수", f"{remaining} / {MAX_ANALYSES_PER_SESSION}")
        st.divider()
        st.markdown(
            "**사용 방법**\n"
            "1. 얼굴이 잘 보이는 사진을 올리거나 찍습니다.\n"
            "2. 관상가의 말투를 고릅니다.\n"
            "3. **관상을 보거라** 버튼을 누릅니다."
        )
        st.divider()
        st.caption(PRIVACY_NOTICE)
        st.caption(DISCLAIMER)
    return tone


def get_input_image() -> bytes | None:
    """업로드 탭 또는 카메라 탭에서 이미지를 받아 원본 바이트를 반환한다."""
    nonce = st.session_state.input_nonce
    tab_upload, tab_camera = st.tabs(["📜 사진 올리기", "📷 카메라로 찍기"])
    with tab_upload:
        uploaded = st.file_uploader(
            "얼굴 사진을 올려 주시오 (jpg, png, webp · 최대 10MB)",
            type=["jpg", "jpeg", "png", "webp"],
            key=f"uploader_{nonce}",
            on_change=_mark_source,
            args=("upload",),
        )
    with tab_camera:
        # 탭 내용은 처음부터 모두 그려지므로, camera_input을 바로 두면 페이지를 열자마자
        # 브라우저가 카메라 권한을 요청한다. 사용자가 켤 때만 카메라를 띄운다.
        captured = None
        if st.toggle("📷 카메라 켜기", key=f"camera_on_{nonce}"):
            captured = st.camera_input(
                "카메라로 얼굴을 비춰 주시오",
                key=f"camera_{nonce}",
                on_change=_mark_source,
                args=("camera",),
            )
        else:
            st.caption("카메라는 켜기 전까지 사용하지 않습니다.")

    source = pick_source(uploaded, captured, st.session_state.input_source)
    return source.getvalue() if source is not None else None


def render_result(result: str) -> None:
    if result.startswith(NO_FACE_MESSAGE):
        st.warning(result)
        return

    sections = parse_sections(result)
    if not all(k in sections for k in SECTION_KEYS):
        # 모델이 형식을 지키지 않은 경우: 원문을 한지 카드 하나에 그대로 보여준다.
        with st.container(key="gs-card-raw"):
            st.markdown(result)
    else:
        with st.container(key="gs-card-first"):
            st.markdown("### 🔮 첫인상")
            st.markdown(sections["첫인상"])

        with st.container(key="gs-card-parts"):
            st.markdown("### 👁️ 부위별 관상")
            parts = parse_parts(sections["부위별 관상"])
            if parts:
                st.markdown(styles.parts_html(parts), unsafe_allow_html=True)
            else:
                st.markdown(sections["부위별 관상"])

        with st.container(key="gs-card-fortune"):
            st.markdown("### 🍀 종합 운세")
            st.markdown(sections["종합 운세"])

        st.markdown(styles.scroll_html(clean_summary(sections["한 줄 요약"])), unsafe_allow_html=True)

    st.caption(DISCLAIMER)
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📄 결과 내려받기",
            data=result,
            file_name="gwansang_result.txt",
            mime="text/plain",
            width="stretch",
        )
    with col2:
        st.button("🔄 다른 얼굴 보기", on_click=reset_for_new_photo, width="stretch")


def main() -> None:
    st.set_page_config(page_title="AI 관상가", page_icon="🔮", layout="centered")
    init_state()
    styles.inject_css()

    st.markdown(styles.hero_html([DISCLAIMER, PRIVACY_NOTICE]), unsafe_allow_html=True)

    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        st.error(
            "OPENAI_API_KEY가 설정되지 않았습니다. "
            "로컬에서는 .env 파일에, Streamlit Cloud에서는 Secrets에 키를 넣어 주세요."
        )
        st.stop()

    model = get_secret("OPENAI_MODEL") or DEFAULT_MODEL
    tone = render_sidebar()
    styles.brush_divider()

    raw = get_input_image()
    processed: bytes | None = None
    if raw is not None:
        if not is_size_ok(len(raw)):
            st.error(f"사진 용량이 너무 큽니다. {MAX_FILE_BYTES // (1024 * 1024)}MB 이하의 사진을 올려 주세요.")
        else:
            try:
                processed = preprocess_image(raw)
            except ImageTooLargeError:
                st.error("사진 해상도가 너무 큽니다. 일반 사진 크기(4000만 화소 이하)로 올려 주세요.")
            except ImageProcessingError:
                st.error("사진을 열 수 없습니다. jpg, png, webp 형식의 이미지 파일인지 확인해 주세요.")

    current_key = None
    if processed is not None:
        _, mid, _ = st.columns([1, 1.2, 1])
        with mid:
            st.image(processed, caption="관상을 볼 얼굴", width="stretch")
        current_key = (image_hash(processed), tone)

    limit_reached = st.session_state.analysis_count >= MAX_ANALYSES_PER_SESSION
    clicked = st.button(
        "관상을 보거라",
        type="primary",
        disabled=processed is None or limit_reached,
        width="stretch",
    )

    if clicked and processed is not None:
        if st.session_state.result_key == current_key and st.session_state.result:
            st.info("같은 사진과 말투로 이미 본 관상이오. 아래 풀이를 확인하시오.")
        else:
            client = OpenAI(api_key=api_key, timeout=API_TIMEOUT_SECONDS, max_retries=1)
            try:
                if not get_daily_usage().try_acquire(get_daily_limit()):
                    raise DailyLimitError()
                with st.spinner("관상가가 그대의 얼굴을 살피는 중이오..."):
                    result = analyze_face(client, model, to_base64(processed), tone)
            except (AnalysisError, DailyLimitError) as exc:
                st.warning(friendly_error(exc))
            except Exception as exc:  # noqa: BLE001 - 사용자에게는 친절한 메시지만 보여준다
                st.error(friendly_error(exc))
            else:
                # 세션 횟수는 실제 관상 풀이를 받았을 때만 차감한다 (얼굴 없음 응답은 제외).
                if not result.startswith(NO_FACE_MESSAGE):
                    st.session_state.analysis_count += 1
                st.session_state.result = result
                st.session_state.result_key = current_key
                st.rerun()  # 사이드바의 남은 횟수를 갱신

    if limit_reached:
        st.warning(f"이번 세션의 분석 횟수({MAX_ANALYSES_PER_SESSION}회)를 모두 사용했소.")

    # 지금 보이는 사진·말투에 해당하는 결과만 표시한다 (rerun 후에도 유지).
    if st.session_state.result and current_key and st.session_state.result_key == current_key:
        styles.brush_divider()
        render_result(st.session_state.result)


if __name__ == "__main__":
    main()
