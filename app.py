# app.py
# LeaseLens - Streamlit web app (step D3: Findings screen added).
# Run with:  streamlit run app.py

import html

import streamlit as st

from core.sample_data import get_sample_bundle, get_sample_rules

# ---------------------------------------------------------------
# Page setup (must be the first Streamlit call)
# ---------------------------------------------------------------
st.set_page_config(page_title="LeaseLens", page_icon="🏠", layout="wide")

DISCLAIMER = (
    "LeaseLens gives information to help you ask better questions. "
    "It is not legal advice. For legal advice, consult a qualified lawyer."
)

# Colours and words used on the Findings screen
RISK_COLOURS = {"high": "#d32f2f", "medium": "#ef6c00", "low": "#2e7d32"}
RISK_ORDER = {"high": 0, "medium": 1, "low": 2}

TOPIC_NAMES = {
    "deposit": "Security deposit",
    "deductions": "Deposit deductions",
    "lock_in": "Lock-in period",
    "termination_notice": "Notice to end the agreement",
    "rent_escalation": "Rent increase",
    "maintenance_repairs": "Maintenance and repairs",
    "entry_inspection": "Landlord entry and inspection",
    "subletting": "Subletting",
    "registration_stamp": "Registration and stamp duty",
    "utilities": "Utilities",
    "eviction": "Eviction",
    "renewal": "Renewal",
    "other": "Other",
}

RULE_TYPE_NAMES = {
    "legal_requirement": "Legal requirement",
    "contract_guidance": "Contract guidance",
    "best_practice": "Best practice",
}


def topic_name(topic: str) -> str:
    """Turn a topic code like 'lock_in' into plain words."""
    return TOPIC_NAMES.get(topic, topic.replace("_", " ").title())


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
# Helper: look up a rule by its id
# ---------------------------------------------------------------
def lookup_rule(rule_id: str):
    """Find a rule. Try the real knowledge base first, then the demo rules.

    Returns a RuleEntry, or None if the rule cannot be found.
    """
    try:
        from core.rules import get_rule  # written by Member 1
        rule = get_rule(rule_id)
        if rule is not None:
            return rule
    except Exception:
        pass  # knowledge base not ready: fall back to demo rules
    try:
        for rule in get_sample_rules():
            if rule.rule_id == rule_id:
                return rule
    except Exception:
        pass
    return None


# ---------------------------------------------------------------
# Helper: run the real analysis on uploaded files
# ---------------------------------------------------------------
def run_real_analysis(files):
    """Read the uploaded files and run Member 1's pipeline.

    Returns an AnalysisBundle, or None if something is not ready yet.
    A friendly message is shown on screen in that case.
    """
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
# Helpers for the Findings screen
# ---------------------------------------------------------------
def risk_badge_html(risk: str) -> str:
    """A small coloured label such as HIGH RISK."""
    colour = RISK_COLOURS.get(risk, "#555555")
    style = (
        "background:" + colour + ";color:white;padding:2px 10px;"
        "border-radius:12px;font-size:0.8rem;font-weight:600;"
    )
    label = html.escape(risk.upper()) + " RISK"
    return '<span style="' + style + '">' + label + "</span>"


def quote_html(text: str) -> str:
    """The exact clause text in a quote block with a yellow highlight."""
    style = (
        "background:#fff3b0;color:#222222;padding:10px 14px;"
        "border-left:4px solid #f9a825;border-radius:4px;margin:6px 0;"
    )
    return '<div style="' + style + '">' + html.escape(text) + "</div>"


def show_evidence(finding) -> None:
    """Show the Evidence box for one finding."""
    with st.container(border=True):
        st.markdown("**Evidence**")

        if finding.evidence_status == "verified_rule" and finding.rule_ids:
            for rule_id in finding.rule_ids:
                rule = lookup_rule(rule_id)
                if rule is None:
                    st.write("Rule " + rule_id)
                    continue
                st.markdown("**" + rule.title + "**")
                type_name = RULE_TYPE_NAMES.get(rule.rule_type, rule.rule_type)
                st.write("Type: " + type_name)
                if rule.section:
                    st.write("Section: " + rule.section)
                if rule.source_url and rule.source_url.startswith("http"):
                    st.markdown(
                        "Source: [" + rule.source_name + "](" + rule.source_url + ")"
                    )
                else:
                    st.write("Source: " + rule.source_name)
                st.write("Date checked: " + rule.date_checked)
            if finding.applicability_note:
                st.write("Does it apply to you? " + finding.applicability_note)
        else:
            st.info(
                "No verified rule was found in our knowledge base for this "
                "clause. This does not mean no rule exists."
            )


def show_finding_card(finding, index: int) -> None:
    """Draw one finding as a bordered card."""
    with st.container(border=True):
        heading = (
            risk_badge_html(finding.risk)
            + " &nbsp; <b>"
            + html.escape(topic_name(finding.topic))
            + "</b> (clause "
            + html.escape(finding.clause_id)
            + ")"
        )
        st.markdown(heading, unsafe_allow_html=True)

        st.markdown("**What the agreement says**")
        st.markdown(quote_html(finding.quoted_text), unsafe_allow_html=True)

        st.markdown("**Risk explanation**")
        st.write(finding.risk_explanation)

        st.markdown("**Why it matters**")
        st.write(finding.why_it_matters)

        show_evidence(finding)

        st.write("Confidence in this reading: **" + finding.confidence + "**")

        if finding.suggested_question:
            st.write("You may want to ask: " + finding.suggested_question)

        if st.button("Draft a message about this", key="draft_" + str(index)):
            st.session_state["negotiate_clause"] = finding.clause_id
            st.success("Saved. Now open the Negotiator tab to see your drafts.")


def show_findings_tab() -> None:
    """The whole Findings tab."""
    st.subheader("Findings")

    if "bundle" not in st.session_state:
        st.info("Upload an agreement first.")
        return

    findings = st.session_state["bundle"].findings
    if not findings:
        st.info("No findings were returned for this agreement.")
        return

    # (1) Summary row of counts
    col_high, col_med, col_low = st.columns(3)
    col_high.metric("High risk", sum(f.risk == "high" for f in findings))
    col_med.metric("Medium risk", sum(f.risk == "medium" for f in findings))
    col_low.metric("Low risk", sum(f.risk == "low" for f in findings))

    # (2) Filters
    topics_present = sorted({f.topic for f in findings})
    filter_left, filter_right = st.columns(2)
    chosen_risks = filter_left.multiselect(
        "Risk",
        options=["high", "medium", "low"],
        default=["high", "medium", "low"],
        format_func=lambda r: r.title(),
        key="filter_risk",
    )
    chosen_topics = filter_right.multiselect(
        "Topic",
        options=topics_present,
        default=topics_present,
        format_func=topic_name,
        key="filter_topic",
    )

    # (3) Cards, high risk first
    shown = [
        f for f in findings
        if f.risk in chosen_risks and f.topic in chosen_topics
    ]
    shown.sort(key=lambda f: RISK_ORDER.get(f.risk, 3))

    if not shown:
        st.info("No findings match the filters you chose.")
        return

    for index, finding in enumerate(shown):
        show_finding_card(finding, index)


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

# ----- Tab 2: Findings -----
with tab_findings:
    show_findings_tab()

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