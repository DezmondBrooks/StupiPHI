from __future__ import annotations

import re
from typing import List, Tuple

from models.canonical_record import CanonicalRecord

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"""
    \b
    (?:\+?1[\s\-\.]?)?                   # optional country code
    (?:\(?\d{3}\)?[\s\-\.]?)             # area code
    \d{3}[\s\-\.]?\d{4}                  # local number
    (?:\s*(?:x|ext\.?|extension)\s*\d+)? # optional extension
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)



def verify_basic(record: CanonicalRecord) -> Tuple[bool, List[str]]:
    """
    MVP verification checks. This is NOT a compliance guarantee.
    It's a safety baseline to catch obvious leakage.
    """
    issues: List[str] = []

    # Check free text for obvious patterns
    if EMAIL_RE.search(record.encounter_notes):
        issues.append("encounter_notes still contains an email-like pattern")

    if PHONE_RE.search(record.encounter_notes):
        issues.append("encounter_notes still contains a phone-like pattern")

    ok = len(issues) == 0
    return ok, issues
