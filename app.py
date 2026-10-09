# app.py
# LeaseLens - Streamlit web app (step D8: Negotiator screen added).
# Run with:  streamlit run app.py

import html

import streamlit as st

from core.negotiator import generate_drafts
from core.sample_data import get_sample_bundle, get_sample_rules
from core.schema import Deduction
from core.simulator import DISCLAIMER as SIM_DISCLAIMER
from core.simulator import simulate

# ---------------------------------------------------------------
# Page setup (must be the first Streamlit call)
# ---------------------------------------------------------------
st.set_page_config(page_title="LeaseLens", page_icon="🏠", layout="wide")

DISCLAIMER = (
    "LeaseLens gives information to help you ask better questions. "
    "It is not legal advice. For legal advice, consult a qualified lawyer."
)

MISSING_NOTE = (
    "A missing detail is not automatically a legal violation. "
    "These are things you may want to ask to be written down."
)

# Colours and words used on the screens
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

# Friendly names for the deduction categories (Deposit Simulator)
CATEGORY_NAMES = {
    "painting_repairs": "Painting and repairs",
    "damage": "Damage",
    "cleaning": "Cleaning",
    "unpaid_rent": "Unpaid rent",
    "utility_dues": "Utility bills",
    "other": "Other",
}

# Colours and words for the simulator statuses
STATUS_COLOURS = {
    "supported": "#2e7d32",
    "needs_clarification": "#ef6c00",
    "review_further": "#d32f2f",
}
STATUS_NAMES = {
    "supported": "Supported",
    "needs_clarification": "Needs clarification",
    "review_further": "Review further",
}


def topic_name(topic: str) -> str:
    """Turn a topic code like 'lock_in' into plain words."""
    return TOPIC_NAMES.get(topic, topic.replace("_", " ").title())


def rupees(amount) -> str:
    """Format a number like 48000 as 'Rs. 48,000'."""
    return "Rs. " + format(amount, ",.0f")


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
        st.error("Sorry, the analysis did not work: " + str(error))
        return None

    progress_bar.progress(1.0)
    status_text.write("Done!")
    return bundle


# ---------------------------------------------------------------
# Small HTML helpers (badges and quote block)
# ---------------------------------------------------------------
def badge_html(colour: str, label: str) -> str:
    """A small coloured label."""
    style = (
        "background:" + colour + ";color:white;padding:2px 10px;"
        "border-radius:12px;font-size:0.8rem;font-weight:600;"
    )
    return '<span style="' + style + '">' + html.escape(label) + "</span>"


def risk_badge_html(risk: str) -> str:
    """A badge such as HIGH RISK."""
    colour = RISK_COLOURS.get(risk, "#555555")
    return badge_html(colour, risk.upper() + " RISK")


def severity_badge_html(severity: str) -> str:
    """A badge such as HIGH SEVERITY."""
    colour = RISK_COLOURS.get(severity, "#555555")
    return badge_html(colour, severity.upper() + " SEVERITY")


def status_badge_html(status: str) -> str:
    """A badge such as Supported (green) or Review further (red)."""
    colour = STATUS_COLOURS.get(status, "#555555")
    return badge_html(colour, STATUS_NAMES.get(status, status))


def quote_html(text: str) -> str:
    """The exact clause text in a quote block with a yellow highlight."""
    style = (
        "background:#fff3b0;color:#222222;padding:10px 14px;"
        "border-left:4px solid #f9a825;border-radius:4px;margin:6px 0;"
    )
    return '<div style="' + style + '">' + html.escape(text) + "</div>"


# ---------------------------------------------------------------
# Findings screen
# ---------------------------------------------------------------
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
                    link = "[" + rule.source_name + "](" + rule.source_url + ")"
                    st.markdown("Source: " + link)
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
# Gaps screen
# ---------------------------------------------------------------
def show_gap_card(gap) -> None:
    """Draw one gap (conflict or missing detail) as a bordered card."""
    with st.container(border=True):
        heading = (
            severity_badge_html(gap.severity)
            + " &nbsp; <b>"
            + html.escape(gap.title)
            + "</b>"
        )
        st.markdown(heading, unsafe_allow_html=True)
        st.write(gap.description)
        if gap.related_clause_ids:
            clauses_text = ", ".join(gap.related_clause_ids)
        else:
            clauses_text = "none"
        st.write("Related clauses: " + clauses_text)


def show_gaps_tab() -> None:
    """The whole Gaps tab: conflicts first, then missing details."""
    st.subheader("Gaps")

    if "bundle" not in st.session_state:
        st.info("Upload an agreement first.")
        return

    gaps = st.session_state["bundle"].gaps
    conflicts = [g for g in gaps if g.kind == "conflict"]
    missing = [g for g in gaps if g.kind == "missing"]
    conflicts.sort(key=lambda g: RISK_ORDER.get(g.severity, 3))
    missing.sort(key=lambda g: RISK_ORDER.get(g.severity, 3))

    # Section 1: conflicts
    st.markdown("### Details that disagree (conflicts)")
    if conflicts:
        for gap in conflicts:
            show_gap_card(gap)
    else:
        st.success("Good news: no conflicting details were found.")

    # Section 2: missing details
    st.markdown("### Details that are missing")
    st.caption(MISSING_NOTE)
    if missing:
        for gap in missing:
            show_gap_card(gap)
    else:
        st.success("Good news: no missing details were found.")


# ---------------------------------------------------------------
# Deposit Simulator screen
# ---------------------------------------------------------------
def deductions_table_html(items) -> str:
    """Build an HTML table of the deductions with coloured statuses."""
    cell = "padding:6px 10px;border-bottom:1px solid #8884;vertical-align:top;"
    head = (
        "<tr>"
        '<th style="' + cell + 'text-align:left;">Deduction</th>'
        '<th style="' + cell + 'text-align:left;">Amount</th>'
        '<th style="' + cell + 'text-align:left;">Status</th>'
        '<th style="' + cell + 'text-align:left;">Why</th>'
        "</tr>"
    )
    rows = ""
    for item in items:
        rows += (
            "<tr>"
            '<td style="' + cell + '">' + html.escape(item["label"]) + "</td>"
            '<td style="' + cell + '">' + rupees(item["amount"]) + "</td>"
            '<td style="' + cell + '">'
            + status_badge_html(item["status"])
            + "</td>"
            '<td style="' + cell + '">' + html.escape(item["reason"]) + "</td>"
            "</tr>"
        )
    return '<table style="width:100%;border-collapse:collapse;">' + head + rows + "</table>"


def show_sim_results(result) -> None:
    """Show the results of the last simulation run."""
    st.markdown("### Results")

    months = result["deposit_months_of_rent"]
    if months is not None:
        st.write("Your deposit is about **" + str(months) + " months of rent**.")

    st.markdown(deductions_table_html(result["items"]), unsafe_allow_html=True)

    st.markdown("### What may come back to you")
    scenarios = result["scenarios"]
    col_a, col_b, col_c = st.columns(3)

    col_a.metric(
        "Only supported deductions",
        rupees(scenarios["tenant_favourable"]["amount_returned"]),
    )
    col_a.caption(
        "Deducted: " + rupees(scenarios["tenant_favourable"]["total_deducted"])
    )

    col_b.metric(
        "Supported + needs clarification",
        rupees(scenarios["middle"]["amount_returned"]),
    )
    col_b.caption("Deducted: " + rupees(scenarios["middle"]["total_deducted"]))

    col_c.metric(
        "All deductions as proposed",
        rupees(scenarios["as_proposed"]["amount_returned"]),
    )
    col_c.caption("Deducted: " + rupees(scenarios["as_proposed"]["total_deducted"]))


def show_simulator_tab() -> None:
    """The whole Deposit Simulator tab."""
    st.subheader("Deposit Simulator")
    st.write(
        "Try out how much of your deposit may come back. "
        "This is only a scenario estimate."
    )

    # Use the agreement's numbers if we have them, else simple defaults.
    default_deposit = 60000.0
    default_rent = 20000.0
    clauses = []
    bundle = st.session_state.get("bundle")
    if bundle is not None:
        clauses = bundle.extract.clauses
        terms = bundle.extract.key_terms
        if terms.security_deposit:
            default_deposit = float(terms.security_deposit)
        if terms.monthly_rent:
            default_rent = float(terms.monthly_rent)

    # The key changes when the default changes, so new data refills the box.
    col_dep, col_rent = st.columns(2)
    deposit = col_dep.number_input(
        "Security deposit (Rs.)",
        min_value=0.0,
        value=default_deposit,
        step=1000.0,
        key="sim_deposit_" + str(int(default_deposit)),
    )
    rent = col_rent.number_input(
        "Monthly rent (Rs.)",
        min_value=0.0,
        value=default_rent,
        step=500.0,
        key="sim_rent_" + str(int(default_rent)),
    )

    # Choices for the "linked clause" box
    clause_labels = ["None"]
    clause_id_by_label = {"None": None}
    for clause in clauses:
        label = clause.clause_id + ": " + clause.text[:50]
        clause_labels.append(label)
        clause_id_by_label[label] = clause.clause_id

    st.markdown("### Deductions the landlord may propose")
    count = st.number_input(
        "How many deductions?",
        min_value=1,
        max_value=8,
        value=1,
        step=1,
        key="sim_count",
    )

    deductions = []
    for i in range(int(count)):
        number = str(i + 1)
        with st.container(border=True):
            st.markdown("**Deduction " + number + "**")
            col1, col2, col3 = st.columns(3)
            label = col1.text_input("What is it for?", key="ded_label_" + number)
            category = col2.selectbox(
                "Kind of cost",
                options=list(CATEGORY_NAMES.keys()),
                format_func=lambda c: CATEGORY_NAMES[c],
                key="ded_category_" + number,
            )
            amount = col3.number_input(
                "Amount (Rs.)",
                min_value=0.0,
                value=0.0,
                step=500.0,
                key="ded_amount_" + number,
            )
            col4, col5 = st.columns(2)
            chosen = col4.selectbox(
                "Linked clause",
                options=clause_labels,
                key="ded_clause_" + number,
            )
            has_proof = col5.checkbox(
                "I have bills, photos or other proof",
                key="ded_proof_" + number,
            )

        if amount > 0:
            if label.strip():
                shown_label = label.strip()
            else:
                shown_label = "Deduction " + number
            deductions.append(
                Deduction(
                    label=shown_label,
                    category=category,
                    amount=amount,
                    linked_clause_id=clause_id_by_label[chosen],
                    has_proof=has_proof,
                )
            )

    if st.button("Run scenarios", type="primary"):
        if not deductions:
            st.warning("Please enter at least one deduction amount above 0.")
        else:
            st.session_state["sim_result"] = simulate(
                deposit, rent, deductions, clauses
            )

    if "sim_result" in st.session_state:
        show_sim_results(st.session_state["sim_result"])
        st.info(SIM_DISCLAIMER)


# ---------------------------------------------------------------
# Negotiator screen
# ---------------------------------------------------------------
def finding_label(finding) -> str:
    """A short name for a finding, used in the choice box."""
    return (
        finding.clause_id
        + " - "
        + topic_name(finding.topic)
        + " - "
        + finding.risk
        + " risk"
    )


def show_draft_box(title: str, text: str, name: str, finding_index: int, gen: int):
    """Show one editable draft with the read-and-edited tick box."""
    st.markdown("### " + title)
    base_key = "neg_" + name + "_" + str(finding_index) + "_" + str(gen)

    edited = st.text_area(
        "Edit your " + title.lower() + " message",
        value=text,
        height=220,
        key=base_key + "_text",
        label_visibility="collapsed",
    )

    approved = st.checkbox(
        "I have read and edited this message",
        key=base_key + "_ok",
    )

    if approved:
        st.caption("Copy it with the button at the top right of the box.")
        st.code(edited, language=None, wrap_lines=True)
        st.download_button(
            "Download as a text file",
            data=edited,
            file_name="leaselens_" + name + "_message.txt",
            mime="text/plain",
            key=base_key + "_download",
        )


def show_negotiator_tab() -> None:
    """The whole Negotiator tab."""
    st.subheader("Negotiator")

    if "bundle" not in st.session_state:
        st.info("Upload an agreement first.")
        return

    bundle = st.session_state["bundle"]
    findings = bundle.findings
    if not findings:
        st.info("There are no findings to write a message about.")
        return

    st.info(
        "LeaseLens never sends anything. Read and edit the message first."
    )

    # Preselect the finding chosen with the "Draft a message" button.
    wanted = st.session_state.get("negotiate_clause")
    default_index = 0
    for i, finding in enumerate(findings):
        if finding.clause_id == wanted:
            default_index = i
            break

    chosen = st.selectbox(
        "Which finding do you want to write about?",
        options=list(range(len(findings))),
        index=default_index,
        format_func=lambda i: finding_label(findings[i]),
    )
    finding = findings[chosen]

    st.markdown("**What the agreement says**")
    st.markdown(quote_html(finding.quoted_text), unsafe_allow_html=True)

    terms = bundle.extract.key_terms

    if st.button("Generate drafts", type="primary"):
        with st.spinner("Writing your drafts. This can take a minute..."):
            try:
                drafts = generate_drafts(
                    finding, terms.tenant_name, terms.landlord_name
                )
            except Exception as error:
                st.error("Sorry, the drafts could not be written: " + str(error))
            else:
                store = st.session_state.setdefault("drafts", {})
                old = store.get(chosen)
                if old:
                    gen = old["gen"] + 1
                else:
                    gen = 1
                store[chosen] = {
                    "friendly": drafts.friendly,
                    "firm": drafts.firm,
                    "compromise": drafts.compromise,
                    "gen": gen,
                }

    saved = st.session_state.get("drafts", {}).get(chosen)
    if saved is None:
        st.write("Click 'Generate drafts' to get three messages you can edit.")
        return

    show_draft_box("Friendly", saved["friendly"], "friendly", chosen, saved["gen"])
    show_draft_box("Firm", saved["firm"], "firm", chosen, saved["gen"])
    show_draft_box(
        "Compromise", saved["compromise"], "compromise", chosen, saved["gen"]
    )


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
            st.session_state.pop("drafts", None)
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
                    st.session_state.pop("drafts", None)
                    st.success("Analysis finished. Open the Findings tab.")

    if "bundle" in st.session_state:
        st.info("A result is loaded and ready to explore in the other tabs.")

# ----- Tab 2: Findings -----
with tab_findings:
    show_findings_tab()

# ----- Tab 3: Gaps -----
with tab_gaps:
    show_gaps_tab()

# ----- Tab 4: Deposit Simulator -----
with tab_sim:
    show_simulator_tab()

# ----- Tab 5: Negotiator -----
with tab_neg:
    show_negotiator_tab()

# ----- Tab 6: Move-in Vault -----
with tab_vault:
    st.subheader("Move-in Vault")
    st.write("Coming soon")

# ---------------------------------------------------------------
# Footer
# ---------------------------------------------------------------
st.divider()
st.caption(DISCLAIMER)