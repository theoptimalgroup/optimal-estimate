"""Helpers for comparing XLSX internal notes in integration tests."""

from __future__ import annotations

import re


def normalize_internal_notes_for_test(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        normalized = re.sub(r"\s+/\s+", " / ", stripped)
        normalized = re.sub(r":\s*£", ": £", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        lines.append(normalized)
    return "\n".join(lines)


def extract_core_internal_notes(text: str) -> str:
    normalized = normalize_internal_notes_for_test(text)
    core_lines: list[str] = []
    for line in normalized.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if (
            "Comms @" in stripped
            or "QUOTE HELPER USED" in stripped
            or stripped.startswith(
                ("BUDGET:", "TOTAL COST TO OPTIMAL:", "TOTAL CHARGE TO CLIENT:", "PROFIT ON JOB:")
            )
            or ("Carpenter" in stripped and ("Hour/s" in stripped or "Day/s" in stripped))
        ):
            core_lines.append(stripped)
    return "\n".join(core_lines)
