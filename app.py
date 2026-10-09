# app.py
# LeaseLens - Streamlit web app (step D2: skeleton with six tabs).
# Run with:  streamlit run app.py

import streamlit as st

from core.sample_data import get_sample_bundle

# ---------------------------------------------------------------
# Page setup (must be the first Streamlit call)
# ---------------------------------------------------------------
st.set_page_config(page_title="LeaseLens", page_icon="🏠", layout="wide")

DISCLAIMER = (
    "LeaseLens gives information to help you ask better questions. "
    "It is not legal advice. For legal advice, consult a qualified lawyer."
)


# ---------------------------------------------------------------
# Helper: is the AI (Ollama) available?
# ---------------------------------------------------------------
def get_ai_status() -> str:
    """Return a short text describing whether the AI is connected."""
    try:
        # This file is written by Member 1. It may not exist yet.
        from core.gemma import is_ollama_running
    except Exception:
        return "AI not connected"
    try:
        if is_ollama_running():
            return "AI connected (Ollama is running)"
        return "Ollama is not running. Please open the Ollama app."
    except Exception:
        return "AI not connected"


# ---------------------------------------------------------------
# Helper: run the real analysis on uploaded files
# ---------------------------------------------------------------
def run_real_analysis(files):
    """Read the uploaded files and run Member 1's pipeline.

    Returns an AnalysisBundle, or None if something is not ready yet.
    A friendly message is shown on screen in that case.
    """
    # Try to load Member 1's code. It may not be merged yet.
    try:
        from core.pdf_images import load_pages
        from core.pipeline import run_analysis
    except Exception:
        st.warning(
            "The AI part of LeaseLens is not ready on this computer yet. "
            "Tick 'Use demo data' in the sidebar to try the app, or ask "
            "Member 1 to merge the AI core and update your branch."
        )
        return None

    progress_bar = st.progress(0.0)
    status_text = st.empty()

    def progress_cb(fraction, message):
        """Called by the pipeline to update the progress bar."""
        progress_bar.progress(min(max(float(fraction), 0.0), 1.0))
        status_text.write(message)

    try:
        page_images = load_pages(files)
        bundle = run_analysis(page_images, progress_cb)
    except Exception as error:
        st.error(f"Sorry, the analysis did not work: {error}")
        return None

    progress_bar.progress(1.0)
    status_text.write("Done!")
    return bundle


# ---------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------
with st.sidebar:
    st.header("LeaseLens")
    st.write(get_ai_status())
    use_demo = st.checkbox("Use demo data (no AI needed)", value=False)
    st.warning(DISCLAIMER)

# ---------------------------------------------------------------
# Title
# ---------------------------------------------------------------
st.title("LeaseLens")
st.caption("Understand your rental agreement before it costs you")

# ---------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------
tab_upload, tab_findings, tab_gaps, tab_sim, tab_neg, tab_vault = st.tabs([
    "1 Upload",
    "2 Findings",
    "3 Gaps",
    "4 Deposit Simulator",
    "5 Negotiator",
    "6 Move-in Vault",
])

# ----- Tab 1: Upload -----
with tab_upload:
    st.subheader("Upload your rental agreement")
    st.write(
        "Upload photos or a PDF of your agreement. "
        "Everything stays on this computer."
    )

    uploaded_files = st.file_uploader(
        "Choose files (png, jpg, jpeg or pdf)",
        type=["png", "jpg", "jpeg", "pdf"],
        accept_multiple_files=True,
    )
    camera_photo = st.camera_input("Or take a photo of a page (optional)")

    if st.button("Analyze agreement", type="primary"):
        if use_demo:
            # Demo mode: fake results, no AI needed.
            st.session_state["bundle"] = get_sample_bundle()
            st.success("Demo data loaded. Open the other tabs to look around.")
        else:
            files = list(uploaded_files or [])
            if camera_photo is not None:
                files.append(camera_photo)
            if not files:
                st.warning("Please upload at least one file first.")
            else:
                bundle = run_real_analysis(files)
                if bundle is not None:
                    st.session_state["bundle"] = bundle
                    st.success("Analysis finished. Open the Findings tab.")

    if "bundle" in st.session_state:
        st.info("A result is loaded and ready to explore in the other tabs.")

# ----- Tab 2: Findings (placeholder until step D3) -----
with tab_findings:
    st.subheader("Findings")
    if "bundle" not in st.session_state:
        st.info("Upload an agreement first.")
    else:
        count = len(st.session_state["bundle"].findings)
        st.write(f"{count} findings are ready. The full cards come in the next step.")

# ----- Tab 3: Gaps -----
with tab_gaps:
    st.subheader("Gaps")
    st.write("Coming soon")

# ----- Tab 4: Deposit Simulator -----
with tab_sim:
    st.subheader("Deposit Simulator")
    st.write("Coming soon")

# ----- Tab 5: Negotiator -----
with tab_neg:
    st.subheader("Negotiator")
    st.write("Coming soon")

# ----- Tab 6: Move-in Vault -----
with tab_vault:
    st.subheader("Move-in Vault")
    st.write("Coming soon")

# ---------------------------------------------------------------
# Footer
# ---------------------------------------------------------------
st.divider()
st.caption(DISCLAIMER)