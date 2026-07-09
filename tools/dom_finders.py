"""
tools/dom_finders.py
====================
Utilities to locate agent-browser element refs (@e123) inside accessibility-tree snapshots.
Uses regex + fuzzy text matching to find the best matching element ref for a hint.
"""

import re
import os
import difflib
from typing import Optional


def extract_refs(snapshot: str) -> list[str]:
    """Return all @eNNN refs found in the snapshot text."""
    return re.findall(r"@e\d+", snapshot)


def find_ref_in_snapshot(snapshot: str, hint: Optional[str] = None) -> Optional[str]:
    """Find the best element ref in `snapshot` that matches `hint`.

    Strategy:
    - Scan snapshot lines for refs and collect surrounding text
    - If hint provided, use difflib to fuzzy-match hint against surrounding text
    - Prefer inputs/search/textarea-like candidates
    - Fallback to first found ref
    """
    if not snapshot:
        return None

    candidates = []  # (ref, surrounding_text)
    for line in snapshot.splitlines():
        refs = re.findall(r"@e\d+", line)
        if refs:
            # remove refs from line for a cleaner text
            text = re.sub(r"@e\d+", "", line).strip()
            for r in refs:
                candidates.append((r, text))

    if not candidates:
        return None

    # If hint given, try fuzzy match on surrounding texts
    if hint:
        texts = [t for (_r, t) in candidates]
        # Use a low cutoff to allow loose matching
        matches = difflib.get_close_matches(hint, texts, n=1, cutoff=0.3)
        if matches:
            best = matches[0]
            for r, t in candidates:
                if t == best:
                    return r
        # substring match
        for r, t in candidates:
            if hint.lower() in t.lower():
                return r

    # Prefer candidates that look like inputs/search boxes
    for r, t in candidates:
        lowered = t.lower()
        if any(k in lowered for k in ["input", "textbox", "search", "query", "type", "text", "email", "password", "textarea"]):
            return r

    # Fallback: return first ref
    return candidates[0][0]
