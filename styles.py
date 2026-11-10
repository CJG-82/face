"""UI 스타일: 조선시대 사극 분위기 (먹색 배경, 한지 카드, 낙관 도장, 금색 포인트).

외부 이미지는 쓰지 않고 CSS, 인라인 SVG, 유니코드로만 장식을 만든다.
모델 응답을 HTML에 넣을 때는 반드시 html.escape를 거친다.
"""

import html

import streamlit as st

INK = "#0f0d0b"
INK_2 = "#1c1814"
HANJI = "#e8dcc4"
HANJI_DARK = "#d9c9a8"
INK_TEXT = "#2a1f17"
SEAL = "#8b1a1a"
SEAL_BRIGHT = "#b3312a"
GOLD = "#b08d57"

# 한지 질감: feTurbulence 노이즈를 data URI SVG로 만든다.
_HANJI_NOISE = (
    "url(\"data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'>"
    "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/>"
    "<feColorMatrix values='0 0 0 0 0.35  0 0 0 0 0.27  0 0 0 0 0.18  0 0 0 0.10 0'/></filter>"
    "<rect width='100%25' height='100%25' filter='url(%23n)'/></svg>\")"
)

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=Nanum+Brush+Script&family=Nanum+Myeongjo:wght@400;700;800&display=swap');

/* 배경: 먹색 + 촛불 비네팅 */
.stApp {{
  background:
    radial-gradient(ellipse 70% 45% at 50% 12%, rgba(176,141,87,0.16), transparent 70%),
    radial-gradient(ellipse at 50% 50%, transparent 55%, rgba(0,0,0,0.65) 100%),
    {INK};
}}
[data-testid="stHeader"] {{ background: transparent; }}

/* 서체 (아이콘 폰트가 깨지지 않도록 span 전체에는 적용하지 않는다) */
.stApp, .stApp p, .stApp li, .stApp label, .stApp button, .stApp input,
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
  font-family: 'Gowun Batang', 'Nanum Myeongjo', serif;
  word-break: keep-all; overflow-wrap: anywhere;
}}

/* 히어로 */
.gs-hero {{ text-align: center; padding: 0.5rem 0 0.25rem; }}
.gs-seal {{
  display: inline-flex; align-items: center; justify-content: center;
  width: 52px; height: 84px; padding: 4px; margin-bottom: 0.6rem; letter-spacing: 0.1em;
  background: {SEAL}; color: {HANJI};
  border: 3px double {HANJI}; border-radius: 6px;
  font-family: 'Nanum Myeongjo', serif; font-weight: 800; font-size: 26px; line-height: 1.05;
  transform: rotate(-4deg);
  box-shadow: 0 0 0 2px {SEAL}, 0 6px 18px rgba(0,0,0,0.5);
  writing-mode: vertical-rl;
}}
.stApp .gs-title {{
  font-family: 'Nanum Brush Script', cursive; font-weight: 400;
  font-size: clamp(2.6rem, 9vw, 3.8rem); line-height: 1.1;
  color: {HANJI}; margin: 0; letter-spacing: 0.02em;
  text-shadow: 0 2px 12px rgba(176,141,87,0.35);
}}
.stApp .gs-sub {{ color: {GOLD}; font-size: 1.02rem; margin: 0.4rem 0 0.2rem; }}
.stApp .gs-fine {{ color: #a39780; font-size: 0.82rem; margin: 0.15rem 0; }}

/* 붓 터치 구분선 */
.gs-brush {{
  height: 6px; margin: 1.1rem auto; width: 92%;
  background:
    linear-gradient(90deg, transparent 0%, {SEAL} 6%, {SEAL_BRIGHT} 40%, {SEAL} 80%, transparent 100%);
  border-radius: 50% 40% 60% 30% / 100% 60% 100% 60%;
  opacity: 0.85; transform: skewX(-12deg);
}}

/* 한지 카드: st.container(key="gs-card-...") */
[class*="st-key-gs-card"] {{
  background: {_HANJI_NOISE}, linear-gradient(160deg, {HANJI} 0%, {HANJI_DARK} 100%);
  color: {INK_TEXT};
  border-radius: 4px; padding: 1.1rem 1.25rem 1rem;
  box-shadow: inset 0 0 40px rgba(90,60,30,0.35), 0 8px 24px rgba(0,0,0,0.55);
  border-left: 4px solid {SEAL};
}}
[class*="st-key-gs-card"] p, [class*="st-key-gs-card"] li,
[class*="st-key-gs-card"] strong, [class*="st-key-gs-card"] h2,
[class*="st-key-gs-card"] h3 {{ color: {INK_TEXT}; }}
[class*="st-key-gs-card"] h3 {{
  font-family: 'Nanum Myeongjo', serif; font-weight: 800; font-size: 1.2rem;
  border-bottom: 1px solid rgba(139,26,26,0.35); padding-bottom: 0.35rem; margin-bottom: 0.4rem;
}}

/* 부위별 관상: 옛 관상서 페이지 */
.gs-parts {{ display: grid; gap: 0; }}
.gs-part {{
  display: grid; grid-template-columns: 3.2rem 1fr; gap: 0.8rem; align-items: start;
  padding: 0.55rem 0; border-bottom: 1px dashed rgba(42,31,23,0.25);
}}
.gs-part:last-child {{ border-bottom: none; }}
.gs-part-hanja {{
  font-family: 'Nanum Myeongjo', serif; font-weight: 800; font-size: 1.5rem; color: {SEAL};
  text-align: center; border-right: 2px solid rgba(139,26,26,0.5); line-height: 1.2;
}}
.gs-part-hanja small {{ display: block; font-size: 0.7rem; color: {INK_TEXT}; font-weight: 700; }}
.stApp .gs-part-text {{ color: {INK_TEXT}; line-height: 1.65; }}

/* 한 줄 요약: 두루마리 */
.gs-scroll {{
  position: relative; margin: 0.8rem 0.6rem 1.4rem; padding: 1.6rem 1.4rem;
  background: {_HANJI_NOISE}, linear-gradient(180deg, {HANJI_DARK}, {HANJI} 12%, {HANJI} 88%, {HANJI_DARK});
  color: {INK_TEXT}; text-align: center;
  box-shadow: inset 0 0 30px rgba(90,60,30,0.35), 0 10px 28px rgba(0,0,0,0.6);
}}
.gs-scroll::before, .gs-scroll::after {{
  content: ""; position: absolute; left: -0.6rem; right: -0.6rem; height: 14px; border-radius: 7px;
  background: linear-gradient(180deg, #5a3a22, #2e1d10 60%, #5a3a22);
}}
.gs-scroll::before {{ top: -7px; }}
.gs-scroll::after {{ bottom: -7px; }}
.stApp .gs-scroll-label {{ font-size: 0.8rem; color: {SEAL}; letter-spacing: 0.3em; font-weight: 700; }}
.stApp .gs-scroll-text {{
  font-family: 'Nanum Brush Script', cursive; font-size: clamp(1.7rem, 6vw, 2.2rem);
  line-height: 1.35; margin: 0.4rem 0 0;
}}
.gs-stamp {{
  display: inline-block; margin-top: 0.6rem; padding: 2px 6px; border: 2px solid {SEAL};
  color: {SEAL}; font-family: 'Nanum Myeongjo', serif; font-weight: 800; font-size: 0.85rem;
  transform: rotate(-6deg);
}}

/* 미리보기 이미지 */
[data-testid="stImage"] img {{
  border-radius: 6px; border: 2px solid {GOLD};
  box-shadow: 0 0 0 4px rgba(176,141,87,0.15), 0 10px 26px rgba(0,0,0,0.6);
}}
[data-testid="stImage"] {{ margin: 0 auto; }}
[data-testid="stImageCaption"], [data-testid="caption"] {{ color: #a39780; }}

/* 버튼 */
.stButton > button[kind="primary"] {{
  background: linear-gradient(180deg, {SEAL_BRIGHT}, {SEAL});
  border: 1px solid {GOLD}; color: {HANJI};
  font-family: 'Nanum Myeongjo', serif; font-weight: 800; font-size: 1.1rem; letter-spacing: 0.15em;
  min-height: 3rem;
}}
.stButton > button[kind="primary"]:hover {{ filter: brightness(1.12); border-color: {HANJI}; color: #fff; }}
.stButton > button[kind="primary"]:disabled {{ filter: grayscale(0.7) brightness(0.6); }}

/* 업로드 칸의 영어 용량 안내(서버 상한 50MB)는 숨기고, 라벨의 한국어 안내(10MB)만 보여준다 */
[data-testid="stFileUploaderDropzoneInstructions"] {{ display: none; }}

/* 탭 */
.stTabs [data-baseweb="tab"] {{ font-family: 'Gowun Batang', serif; }}

/* 사이드바 */
[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, #17130f, {INK});
  border-right: 1px solid rgba(176,141,87,0.25);
}}
.stApp .gs-side-title {{ font-family: 'Nanum Brush Script', cursive; font-size: 2rem; color: {HANJI}; margin: 0; }}

/* 모바일 */
@media (max-width: 640px) {{
  .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
  [class*="st-key-gs-card"] {{ padding: 0.9rem 0.95rem; }}
  .gs-part {{ grid-template-columns: 2.6rem 1fr; gap: 0.6rem; }}
  [data-testid="stImage"] img {{ max-width: 220px !important; height: auto !important; margin: 0 auto; display: block; }}
  [data-testid="stImage"] {{ align-items: center; }}
}}
</style>
"""

# 부위 이름 → (한자, 짧은 이름). 모델 출력의 "**이마**:" 같은 굵은 표기를 기준으로 맞춘다.
PART_HANJA = {
    "이마": ("額", "이마"),
    "눈썹·눈": ("眉眼", "눈썹·눈"),
    "코": ("鼻", "코"),
    "입·입술": ("口", "입"),
    "귀": ("耳", "귀"),
    "턱·얼굴형": ("顎", "턱"),
}


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero_html(notices: list[str]) -> str:
    fine = "".join(f'<p class="gs-fine">{html.escape(n)}</p>' for n in notices)
    return (
        '<div class="gs-hero">'
        '<div class="gs-seal" aria-hidden="true">觀相</div>'
        '<h1 class="gs-title">그대의 관상을 보겠소</h1>'
        '<p class="gs-sub">얼굴을 보여 주시오. 이마에서 턱까지, 그대의 운명을 읽어 드리리다.</p>'
        f"{fine}</div>"
    )


def brush_divider() -> None:
    st.markdown('<div class="gs-brush" role="separator"></div>', unsafe_allow_html=True)


def parts_html(parts: list[tuple[str, str]]) -> str:
    """부위별 관상 [(부위명, 풀이)]를 옛 관상서 페이지 형태의 HTML로 만든다."""
    rows = []
    for name, text in parts:
        hanja, short = PART_HANJA.get(name, ("相", name))
        rows.append(
            '<div class="gs-part">'
            f'<div class="gs-part-hanja">{html.escape(hanja)}<small>{html.escape(short)}</small></div>'
            f'<div class="gs-part-text">{html.escape(text)}</div>'
            "</div>"
        )
    return '<div class="gs-parts">' + "".join(rows) + "</div>"


def scroll_html(summary: str) -> str:
    return (
        '<div class="gs-scroll">'
        '<div class="gs-scroll-label">一 言</div>'
        f'<p class="gs-scroll-text">{html.escape(summary)}</p>'
        '<span class="gs-stamp">觀相</span>'
        "</div>"
    )
