"""Starts the real LeaseLens app (app.py) with the new black + blue look.

This file does not change app.py. It only adds the style and banner on top.
"""
from pathlib import Path
import runpy

import streamlit as st

from core.ui_style import apply_style, hero_banner, disclaimer_bar

# Page setup must be the first Streamlit command, so we do it here (wide layout).
# The "try" stops an error if Streamlit has already been set up on a re-run.
try:
    st.set_page_config(page_title="LeaseLens", page_icon="🏠", layout="wide")
except Exception:
    pass

# app.py may also call set_page_config. Streamlit allows it only once,
# so we turn app.py's own call into "do nothing".
st.set_page_config = lambda *args, **kwargs: None

# New look: styles, top banner and the safety strip
apply_style()

# Extra styling so the upload box is easy to see and click in the dark theme
st.markdown(
    """
    <style>
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploaderDropzone"] {
        background: #0A0F1C !important;
        border: 2px dashed #2F7BEA !important;
        border-radius: 20px !important;
        padding: 2rem !important;
        cursor: pointer;
    }
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploader"] p {
        color: #E6EEFF !important;
    }
    [data-testid="stFileUploader"] button {
        background: #0A63F0 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 1.6rem !important;
        font-weight: 600 !important;
        opacity: 1 !important;
        pointer-events: auto !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

hero_banner()
disclaimer_bar()

# Now run your real app below the banner
runpy.run_path(str(Path(__file__).parent / "app.py"), run_name="__main__")