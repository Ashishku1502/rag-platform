"""
Guardrail Layer (input + output)
Lightweight, dependency-free rule-based checks. Not a replacement for
NeMo Guardrails / Claude's own safety systems, but catches the common
cases: prompt injection attempts on the way in, and leaking secrets on
the way out.
"""
import re

# --- Input guardrail --------------------------------------------------

_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (all )?(previous|prior|above) instructions",
    r"reveal (your |the )?system prompt",
    r"what (is|are) your (system prompt|instructions)",
    r"you are now",
    r"act as (a )?jailbreak",
    r"pretend you have no (rules|restrictions|guardrails)",
    r"</?(system|assistant)>",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

MAX_QUERY_LENGTH = 2000


def check_input(query: str) -> tuple[bool, str]:
    """
    Returns (is_safe, reason). If is_safe is False, the query should be
    rejected before it ever reaches retrieval or the LLM.
    """
    if not query or not query.strip():
        return False, "Empty query."

    if len(query) > MAX_QUERY_LENGTH:
        return False, f"Query too long (max {MAX_QUERY_LENGTH} characters)."

    if _INJECTION_RE.search(query):
        return False, "Query blocked: looks like a prompt injection attempt."

    return True, ""


# --- Output guardrail ---------------------------------------------------

_SECRET_PATTERNS = [
    (re.compile(r"sk-ant-[a-zA-Z0-9\-_]{20,}"), "[REDACTED_ANTHROPIC_KEY]"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"Bearer\s+[a-zA-Z0-9\-_\.]{20,}"), "[REDACTED_TOKEN]"),
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "[REDACTED_EMAIL]"),
]


def check_output(text: str) -> str:
    """
    Scrubs the LLM's response for anything that looks like a leaked
    secret (API keys, tokens, emails) before it reaches the user.
    """
    cleaned = text
    for pattern, replacement in _SECRET_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned
