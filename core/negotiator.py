# core/negotiator.py
# Clause Negotiator: writes three draft messages (Friendly, Firm,
# Compromise) for a tenant to send to a landlord.
# Nothing is ever sent automatically. The tenant reads and edits first.

import re

from core.schema import Finding, NegotiationDrafts

MAX_WORDS = 120

# Words we never want in a draft (they sound like legal conclusions).
BANNED_WORDS = re.compile(
    r"\b(illegal|illegally|unlawful|unlawfully)\b", re.IGNORECASE
)

NO_LAW_RULE = (
    "Do not mention any law, Act, section or legal rule at all."
)

LAW_RULE = (
    "You may refer to the verified rule below in general terms, and "
    "you must introduce it with the words 'as I understand it'. "
    "Use ONLY the information given. Do not name any Act or section "
    "number that is not written below."
)


def _fix_banned_word(match):
    """Swap a banned word for a neutral phrase."""
    word = match.group(0).lower()
    if word.endswith("ly"):
        return "in a way that is not clearly allowed"
    return "not clearly allowed"


def trim_words(text, max_words=MAX_WORDS):
    """Shorten a message to at most max_words, ending on a full sentence."""
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    cut = " ".join(words[:max_words])
    last_stop = max(cut.rfind("."), cut.rfind("?"), cut.rfind("!"))
    if last_stop > len(cut) // 2:
        return cut[: last_stop + 1]
    return cut + "..."


def clean_message(text):
    """Apply the safety rules to one draft message."""
    text = BANNED_WORDS.sub(_fix_banned_word, text or "")
    return trim_words(text)


def _rule_notes(finding):
    """Return short notes about verified rules for this finding.

    Each note looks like 'Title: summary'. The list is empty if the
    finding has no verified rule or the knowledge base cannot be read.
    """
    if finding.evidence_status != "verified_rule" or not finding.rule_ids:
        return []
    try:
        from core.rules import get_rule  # written by Member 1
    except Exception:
        return []
    notes = []
    for rule_id in finding.rule_ids:
        try:
            rule = get_rule(rule_id)
        except Exception:
            rule = None
        if rule is not None:
            notes.append(rule.title + ": " + rule.summary)
    return notes


def build_prompt(finding, tenant_name, landlord_name, rule_notes):
    """Write the instructions we send to the AI."""
    tenant = tenant_name or "[Tenant Name]"
    landlord = landlord_name or "[Landlord Name]"

    lines = [
        "You help a tenant in Karnataka, India write polite messages to "
        "their landlord about one clause of a rental agreement.",
        "",
        "Clause number: " + finding.clause_id,
        "Exact clause text: " + finding.quoted_text,
        "Why the tenant is concerned: " + finding.risk_explanation,
        "A question the tenant may want to ask: " + finding.suggested_question,
        "The tenant is called: " + tenant,
        "The landlord is called: " + landlord,
        "",
        "Write THREE short messages from the tenant to the landlord.",
        "Each message must be at most 120 words.",
        "1. friendly: politely ask the landlord to clarify the clause.",
        "2. firm: politely request one specific change to the clause.",
        "3. compromise: suggest specific wording both sides could accept.",
        "",
        "Rules for every message:",
        "- Be polite and specific, in simple English.",
        "- Refer to the clause by its number.",
        "- Do not threaten and do not accuse the landlord of anything.",
        "- Never say anything is illegal or unlawful.",
        "- Use the names above exactly as written, including any text "
        "in square brackets.",
    ]

    if rule_notes:
        lines.append("- " + LAW_RULE)
        lines.append("")
        lines.append("Verified rule information:")
        for note in rule_notes:
            lines.append("* " + note)
    else:
        lines.append("- " + NO_LAW_RULE)

    lines.append("")
    lines.append("Return JSON with the keys friendly, firm and compromise.")
    return "\n".join(lines)


def _call_model(prompt):
    """Ask Gemma for the three drafts (Member 1's wrapper)."""
    from core import gemma  # loaded here so tests can run without it

    return gemma.ask_json(prompt, NegotiationDrafts)


def generate_drafts(finding, tenant_name=None, landlord_name=None):
    """Return three draft messages (NegotiationDrafts) for one finding."""
    notes = _rule_notes(finding)
    prompt = build_prompt(finding, tenant_name, landlord_name, notes)
    raw = _call_model(prompt)

    drafts = NegotiationDrafts(
        friendly=clean_message(raw.friendly),
        firm=clean_message(raw.firm),
        compromise=clean_message(raw.compromise),
    )

    if not (drafts.friendly and drafts.firm and drafts.compromise):
        raise RuntimeError(
            "The AI did not return all three drafts. Please try again."
        )
    return drafts