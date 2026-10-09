"""Temporary preview of the new LeaseLens look. Delete after checking."""
import streamlit as st

from core.ui_style import (
    apply_style, hero_banner, disclaimer_bar, section_title, gradient_cards,
    offer_section, steps_section, stat_cards, clause_card, check_row, letter_box,
)

st.set_page_config(page_title="LeaseLens preview", page_icon="🏠", layout="wide")
apply_style()

# Top banner
hero_banner()
disclaimer_bar()

# Problems LeaseLens may help with
section_title("Rental agreements are hard to read.", "We're here to help.")
gradient_cards([
    ("Signing without understanding?",
     "Long clauses and legal words are hard to follow. LeaseLens may explain each clause in plain language."),
    ("Not sure what to ask?",
     "You may see a list of questions you may want to ask your landlord before you sign."),
    ("Worried about privacy?",
     "The AI runs on your own computer. Your agreement is never sent to an online service."),
])

# Features
offer_section(
    "What we offer",
    ["Clause explainer", "What-if simulator", "Negotiation helper", "Move-in vault"],
    "100% local",
    "No cloud. No account. Your files stay on this computer.",
)

# How it works
steps_section(
    "How it works",
    "Three simple steps",
    [
        ("Upload", "Add your rental agreement as a PDF or as photos of each page."),
        ("Review", "Read a plain-language summary. Items that may need a closer look are marked."),
        ("Prepare", "Get questions you may want to ask, and a draft message you can edit."),
    ],
)

# Components that will be used inside the app tabs
st.write("")
st.header("Components used inside the tabs")
stat_cards([("3", "Clauses to review"), ("1", "Missing items"), ("2", "Questions to ask")])
st.write("")
clause_card("Security deposit", "high", "The deposit may be higher than usual. You may want to ask why.",
            "Source: Karnataka rules file")
clause_card("Notice period", "medium", "The notice period may differ for each side.")
clause_card("Maintenance", "low", "This clause may look balanced.")
check_row("ok", "Rent amount is written clearly.")
check_row("warn", "Lock-in period may need a closer look.")
check_row("fail", "No mention of when the deposit may be returned.")
st.write("")
letter_box("Dear Landlord,\n\nI have read the agreement and you may want to consider...")
st.write("")
st.button("Upload agreement", type="primary")