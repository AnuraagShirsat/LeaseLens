"""Look and feel helpers for LeaseLens (black + blue style, wide layout).

This file only changes how things LOOK. It never contains legal rules.
Use these small functions inside app.py.
"""
import html  # standard Python tool that makes text safe to show in HTML

import streamlit as st

# Professional font stack. These fonts are already on your computer,
# so nothing is downloaded from the internet.
FONT = "'Segoe UI', 'Segoe UI Variable', 'Helvetica Neue', Arial, sans-serif"

CSS = """
<style>
/* ---------- Page: full wide layout ---------- */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stToolbar"] {display: none;}   /* hides the Deploy button */
.stApp {background: #000000;}
.block-container {
    max-width: 1600px !important;
    padding: 2rem 4rem 5rem 4rem !important;
}

/* Use the professional font for all normal text (icons are left alone) */
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3,
.stApp h4, .stApp button, .stApp input, .stApp textarea,
.stApp [data-baseweb="tab"], .ll-hero, .ll-hero *, .ll-h2, .ll-gcard, .ll-gcard *,
.ll-pillbtn, .ll-hex, .ll-hex *, .ll-steps, .ll-steps *, .ll-card, .ll-card *,
.ll-stat, .ll-stat *, .ll-disclaimer, .ll-letter {
    font-family: __FONT__;
}

/* ---------- Hero banner ---------- */
.ll-hero {
    position: relative; overflow: hidden; border-radius: 32px;
    padding: 3.5rem; margin-bottom: 2rem;
    background: linear-gradient(180deg, #A8DDF0 0%, #1E6FE0 25%, #0A2A6B 55%, #000000 100%);
}
.ll-hero-in {position: relative; z-index: 2; display: flex; gap: 3.5rem; flex-wrap: wrap; align-items: center;}
.ll-glass {
    flex: 1 1 520px; padding: 3.2rem 3.4rem; border-radius: 48px 120px 48px 48px;
    border: 1px solid rgba(255,255,255,0.45);
    background: linear-gradient(180deg, rgba(255,255,255,0.22) 0%, rgba(0,20,60,0.55) 100%);
}
.ll-tag {color: #FFFFFF; letter-spacing: 0.16em; font-size: 0.85rem; text-transform: uppercase; font-weight: 600;}
.ll-big1 {font-size: 4.6rem; line-height: 1.05; font-weight: 300; color: #FFFFFF; letter-spacing: -0.02em; margin-top: 1.8rem;}
.ll-big2 {font-size: 4.6rem; line-height: 1.05; font-weight: 700; color: #FFFFFF; letter-spacing: -0.02em; margin-bottom: 1.8rem;}
.ll-sub {color: #E6F0FF; font-size: 1.25rem; line-height: 1.6; max-width: 540px;}

/* Glowing blue rings (stand-in for the 3D blue shapes) */
.ll-ring {
    position: absolute; border-radius: 50%; z-index: 1;
    border: 44px solid #6C8BF2;
    box-shadow: inset 0 0 30px #B5C4FF, 0 0 50px rgba(60,100,255,0.55);
}
.ll-ring-a {width: 260px; height: 260px; right: -70px; top: -80px;}
.ll-ring-b {width: 220px; height: 220px; left: -90px; bottom: -70px;}

/* Hexagon-shaped panel */
.ll-hex {
    flex: 1 1 380px; min-height: 380px; padding: 3.2rem 3.4rem;
    background: #1B1B1D; color: #FFFFFF;
    clip-path: polygon(10% 0, 90% 0, 100% 12%, 100% 88%, 90% 100%, 10% 100%, 0 88%, 0 12%);
    display: flex; flex-direction: column; justify-content: center;
}
.ll-hex .ll-tag {color: #8FB2FF; margin-bottom: 1.2rem;}
.ll-hex-big {font-size: 3.8rem; font-weight: 700; line-height: 1.05; letter-spacing: -0.02em;}
.ll-hex-sub {font-size: 1.15rem; color: #CFE0FF; margin-top: 1rem; line-height: 1.6;}
.ll-row {
    font-size: 1.05rem; display: flex; justify-content: space-between; align-items: center;
    padding: 0.9rem 0; border-bottom: 1px solid #333; color: #FFFFFF;
}

/* ---------- Section titles ---------- */
.ll-h2 {
    text-align: center; font-size: 3rem; line-height: 1.15; font-weight: 300;
    color: #FFFFFF; letter-spacing: -0.02em; margin: 6.5rem 0 3rem 0;
}
.ll-h2 b {font-weight: 700;}
.ll-h2-left {text-align: left; margin: 0 0 2rem 0;}

/* ---------- Gradient cards ---------- */
.ll-grid {display: flex; gap: 2rem; flex-wrap: wrap;}
.ll-gcard {
    flex: 1 1 300px; padding: 2.6rem 2.4rem 3rem 2.4rem; border-radius: 36px;
    border: 2px solid rgba(255,255,255,0.85); color: #FFFFFF;
    background: linear-gradient(180deg, #000000 0%, #0A2A6B 30%, #1363D8 68%, #A8DDF0 100%);
}
.ll-gcard h3 {font-size: 1.45rem; font-weight: 700; line-height: 1.3; margin: 0 0 1.4rem 0; color: #FFFFFF;}
.ll-gcard p {font-size: 1.1rem; line-height: 1.7; margin: 0; color: #F2F7FF;}

/* ---------- Offer section: pills + hexagon ---------- */
.ll-split {display: flex; gap: 4rem; flex-wrap: wrap; align-items: center; margin-top: 6.5rem;}
.ll-split > div {flex: 1 1 420px;}
.ll-pills {display: flex; flex-direction: column; gap: 1.2rem; max-width: 520px;}
.ll-pillbtn {
    text-align: center; color: #FFFFFF; font-size: 1.05rem; font-weight: 600;
    letter-spacing: 0.08em; text-transform: uppercase; padding: 1.1rem 1.6rem;
    border-radius: 999px; border: 1px solid rgba(255,255,255,0.7);
    background: linear-gradient(180deg, #A8DDF0 0%, #2F7BEA 100%);
}

/* ---------- How it works ---------- */
.ll-steps {
    border-radius: 32px; padding: 3.5rem; margin-top: 6.5rem;
    background: linear-gradient(180deg, #000000 0%, #0C3A82 100%);
}
.ll-step-num {font-size: 0.9rem; color: #A8DDF0; letter-spacing: 0.16em; font-weight: 600; margin-bottom: 1rem;}

/* ---------- Disclaimer strip ---------- */
.ll-disclaimer {
    font-size: 1rem; line-height: 1.6; color: #CFE0FF;
    border: 1px solid #1E6FE0; border-radius: 16px; padding: 1.1rem 1.5rem;
    background: rgba(10,99,240,0.10); margin-bottom: 1.5rem;
}

/* ---------- Result cards used inside tabs ---------- */
.ll-card {
    border: 1px solid rgba(255,255,255,0.3); border-radius: 24px;
    padding: 1.5rem 1.8rem; margin-bottom: 1.2rem; color: #FFFFFF;
    background: linear-gradient(180deg, #05070D 0%, #0A2A6B 100%);
}
.ll-card h4 {margin: 0 0 0.6rem 0; font-size: 1.2rem; font-weight: 600; color: #FFFFFF;}
.ll-card p {margin: 0.4rem 0; font-size: 1.05rem; line-height: 1.6; color: #E6EEFF;}
.ll-stat {
    border: 1px solid rgba(255,255,255,0.3); border-radius: 24px; padding: 1.6rem 1rem;
    text-align: center; background: linear-gradient(180deg, #05070D 0%, #0A2A6B 100%);
}
.ll-stat .ll-num {font-size: 2.8rem; font-weight: 700; color: #FFFFFF; line-height: 1.1;}
.ll-stat .ll-label {font-size: 0.95rem; color: #A8DDF0; margin-top: 0.4rem;}
.ll-badge {
    display: inline-block; padding: 0.2rem 0.8rem; border-radius: 999px;
    font-size: 0.78rem; font-weight: 700; letter-spacing: 0.06em;
    margin-right: 0.8rem; vertical-align: middle;
}
.ll-letter {
    white-space: pre-wrap; font-size: 1.05rem; line-height: 1.7; color: #FFFFFF;
    border: 1px dashed #A8DDF0; border-radius: 22px; padding: 1.6rem 1.8rem; background: #05070D;
}

/* ---------- Streamlit widgets ---------- */
.stTabs [data-baseweb="tab-list"] {gap: 12px; margin-bottom: 1.2rem;}
.stTabs [data-baseweb="tab"] {font-size: 1.05rem; font-weight: 600; padding: 0.8rem 1.4rem;}
.stButton > button, .stDownloadButton > button {
    font-size: 1.05rem; font-weight: 600; border-radius: 12px; padding: 0.8rem 2rem;
}
.stButton > button[kind="primary"] {background: #0A63F0; border: none; color: #FFFFFF;}

@media (max-width: 800px) {
    .block-container {padding: 1.5rem 1rem 3rem 1rem !important;}
    .ll-big1, .ll-big2 {font-size: 2.8rem;}
    .ll-h2 {font-size: 2rem; margin-top: 4rem;}
    .ll-hero, .ll-steps {padding: 1.5rem;}
}
</style>
""".replace("__FONT__", FONT)

# Badge colors: (text color, background color)
BADGE_COLORS = {
    "high": ("#FFB4B4", "#5A1620"),
    "medium": ("#FFE08A", "#5A4210"),
    "low": ("#9CF0BC", "#10402A"),
    "unknown": ("#CFE0FF", "#1B2A4D"),
    "fail": ("#FFB4B4", "#5A1620"),
    "warn": ("#FFE08A", "#5A4210"),
    "ok": ("#9CF0BC", "#10402A"),
}


def _html(text: str) -> str:
    """Remove line indents so Streamlit never mistakes HTML for a code block."""
    return "".join(line.strip() for line in text.splitlines())


def _e(text: str) -> str:
    """Make any text safe to place inside HTML."""
    return html.escape(str(text))


def apply_style() -> None:
    """Call once near the top of app.py, right after st.set_page_config."""
    st.markdown(CSS, unsafe_allow_html=True)


def badge_html(label: str, level: str) -> str:
    """A small colored badge. level: high, medium, low, unknown, ok, warn, fail."""
    text_color, bg_color = BADGE_COLORS.get(level.lower(), BADGE_COLORS["unknown"])
    return (
        f'<span class="ll-badge" style="color:{text_color};background:{bg_color};">'
        f"{_e(label.upper())}</span>"
    )


def hero_banner(
    tag: str = "Karnataka tenant helper",
    line1: str = "Let's read",
    line2: str = "your lease",
    sub: str = "Our local AI helper may explain your rental agreement in plain words.",
) -> None:
    """Big top banner: glass card on the left, hexagon sample panel on the right."""
    rows = (
        f'<div class="ll-row"><span>Security deposit</span>{badge_html("ask", "medium")}</div>'
        f'<div class="ll-row"><span>Notice period</span>{badge_html("check", "warn")}</div>'
        f'<div class="ll-row"><span>Monthly rent</span>{badge_html("clear", "ok")}</div>'
    )
    st.markdown(
        _html(
            f"""
            <div class="ll-hero">
            <div class="ll-ring ll-ring-a"></div>
            <div class="ll-ring ll-ring-b"></div>
            <div class="ll-hero-in">
            <div class="ll-glass">
            <div class="ll-tag">{_e(tag)}</div>
            <div class="ll-big1">{_e(line1)}</div>
            <div class="ll-big2">{_e(line2)}</div>
            <div class="ll-sub">{_e(sub)}</div>
            </div>
            <div class="ll-hex">
            <div class="ll-tag">Sample result (example only)</div>
            {rows}
            </div>
            </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def disclaimer_bar() -> None:
    """Safety strip shown on every screen: information only, never legal advice."""
    st.markdown(
        '<div class="ll-disclaimer"><b>Information only, not legal advice.</b> '
        "LeaseLens may point out things worth a closer look. You may want to ask "
        "a qualified lawyer before you sign. Your files stay on this computer.</div>",
        unsafe_allow_html=True,
    )


def section_title(plain: str, bold: str, left: bool = False) -> None:
    """Big two-line heading: light first line, heavy second line."""
    extra = " ll-h2-left" if left else ""
    st.markdown(
        f'<div class="ll-h2{extra}">{_e(plain)}<br><b>{_e(bold)}</b></div>',
        unsafe_allow_html=True,
    )


def gradient_cards(items: list[tuple[str, str]]) -> None:
    """Row of rounded blue gradient cards. items = [(heading, text), ...]"""
    cards = "".join(
        f'<div class="ll-gcard"><h3>{_e(h)}</h3><p>{_e(t)}</p></div>' for h, t in items
    )
    st.markdown(_html(f'<div class="ll-grid">{cards}</div>'), unsafe_allow_html=True)


def offer_section(title: str, pills: list[str], big: str, small: str) -> None:
    """Left: title and pill buttons. Right: hexagon panel with a big message."""
    pill_html = "".join(f'<div class="ll-pillbtn">{_e(p)}</div>' for p in pills)
    st.markdown(
        _html(
            f"""
            <div class="ll-split">
            <div>
            <div class="ll-h2 ll-h2-left">{_e(title)}</div>
            <div class="ll-pills">{pill_html}</div>
            </div>
            <div><div class="ll-hex">
            <div class="ll-tag">Privacy first</div>
            <div class="ll-hex-big">{_e(big)}</div>
            <div class="ll-hex-sub">{_e(small)}</div>
            </div></div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def steps_section(title: str, subtitle: str, steps: list[tuple[str, str]]) -> None:
    """Dark-to-blue block with numbered steps. steps = [(heading, text), ...]"""
    cards = "".join(
        f'<div class="ll-gcard"><div class="ll-step-num">STEP 0{i}</div>'
        f"<h3>{_e(h)}</h3><p>{_e(t)}</p></div>"
        for i, (h, t) in enumerate(steps, start=1)
    )
    st.markdown(
        _html(
            f"""
            <div class="ll-steps">
            <div class="ll-h2 ll-h2-left" style="margin:0 0 0.6rem 0;">{_e(title)}</div>
            <div class="ll-sub" style="margin-bottom:2.5rem;">{_e(subtitle)}</div>
            <div class="ll-grid">{cards}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def stat_cards(items: list[tuple[str, str]]) -> None:
    """Row of number cards. items = [("3", "Clauses to review"), ...]"""
    columns = st.columns(len(items), gap="large")
    for column, (number, label) in zip(columns, items):
        with column:
            st.markdown(
                f'<div class="ll-stat"><div class="ll-num">{_e(number)}</div>'
                f'<div class="ll-label">{_e(label)}</div></div>',
                unsafe_allow_html=True,
            )


def clause_card(title: str, level: str, body: str, extra: str = "") -> None:
    """Card for one clause: colored badge + title + plain explanation."""
    extra_html = f"<p><i>{_e(extra)}</i></p>" if extra else ""
    st.markdown(
        _html(
            f'<div class="ll-card"><h4>{badge_html(level, level)}{_e(title)}</h4>'
            f"<p>{_e(body)}</p>{extra_html}</div>"
        ),
        unsafe_allow_html=True,
    )


def check_row(status: str, text: str) -> None:
    """One checklist line. status: ok, warn or fail."""
    st.markdown(
        f'<div class="ll-card" style="padding:1rem 1.6rem;">'
        f"{badge_html(status, status)}<span>{_e(text)}</span></div>",
        unsafe_allow_html=True,
    )


def letter_box(text: str) -> None:
    """Ready-to-copy message box, for example a negotiation email."""
    st.markdown(f'<div class="ll-letter">{_e(text)}</div>', unsafe_allow_html=True)