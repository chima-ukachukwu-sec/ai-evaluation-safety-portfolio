"""
Rubric validation.

A rubric fails quietly. Nobody gets an error when a scale has no anchor for
level 4; a rater just picks 4 for their own reasons, a second rater picks it
for different reasons, and the disagreement surfaces weeks later as noise
nobody can explain. These checks catch the structural problems that produce
that noise, before any data is collected.

The checks are opinionated on purpose, and each one says why it exists rather
than only what it wants.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Severity = Literal["error", "warning", "info"]

# Anchor text below this is usually a label rather than a criterion. "Good" is
# not something two raters can apply the same way.
MIN_ANCHOR_WORDS = 4

# Hedges make an anchor unfalsifiable. A rater cannot check "generally safe".
#
# "rather than" and "fairly" in the sense of "distributed fairly" are excluded:
# both are ordinary contrastive or literal usage, and flagging them trained the
# reader to ignore the warning, which is worse than not warning at all. Caught
# when this checker raised them against its own author's corrected rubrics.
VAGUE = re.compile(
    r"\b(?:good|bad|okay|ok|fine|poor|nice|appropriate|reasonable|acceptable"
    r"|generally|somewhat|quite|adequate"
    r"|fairly(?! (?:distributed|applied|priced))"
    r"|rather(?! than))\b", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    severity: Severity
    where: str
    message: str
    why: str = ""

    def __str__(self) -> str:
        base = f"[{self.severity.upper()}] {self.where}: {self.message}"
        return f"{base}\n         why: {self.why}" if self.why else base


class RubricError(ValueError):
    """Raised when a rubric file cannot be read at all."""


def load_rubric(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise RubricError(f"rubric not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RubricError(f"{p} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RubricError(f"{p} must contain a JSON object")
    return data


def _scale_levels(scale: dict[str, Any]) -> list[int]:
    out = []
    for k in scale:
        try:
            out.append(int(k))
        except (TypeError, ValueError):
            continue
    return sorted(out)


def validate(rubric: dict[str, Any]) -> list[Finding]:
    """Run every check and return findings, worst first."""
    findings: list[Finding] = []

    if not rubric.get("name"):
        findings.append(Finding("warning", "rubric",
                                "no name",
                                "A rubric without a name cannot be cited in a "
                                "disagreement about how something was scored."))
    if not rubric.get("version"):
        findings.append(Finding("warning", "rubric", "no version",
                                "Scores are only comparable across time if you "
                                "know which version produced them."))

    dims = rubric.get("dimensions")
    if not dims or not isinstance(dims, list):
        findings.append(Finding("error", "rubric", "no dimensions list",
                                "There is nothing to score."))
        return findings

    seen: set[str] = set()
    level_sets: list[tuple[str, tuple[int, ...]]] = []

    for i, dim in enumerate(dims):
        name = dim.get("dimension") or dim.get("name") or f"dimension[{i}]"
        where = f"dimension '{name}'"

        if name in seen:
            findings.append(Finding("error", where, "duplicate dimension name",
                                    "Two dimensions with one name cannot be "
                                    "reported on separately."))
        seen.add(name)

        scale = dim.get("scale")
        if not isinstance(scale, dict) or not scale:
            findings.append(Finding("error", where, "no scale",
                                    "A dimension with no scale cannot be scored."))
            continue

        levels = _scale_levels(scale)
        if not levels:
            findings.append(Finding("error", where, "scale keys are not numeric",
                                    "Ordinal statistics need ordered levels."))
            continue
        level_sets.append((name, tuple(levels)))

        # The check that matters most. A scale running 1..5 with anchors only
        # at 1, 3 and 5 still lets a rater select 2 or 4, and nothing tells
        # them what those mean.
        expected = list(range(min(levels), max(levels) + 1))
        missing = [lv for lv in expected if lv not in levels]
        if missing:
            findings.append(Finding(
                "error", where,
                f"scale spans {min(levels)}-{max(levels)} but has no anchor for "
                f"{', '.join(map(str, missing))}",
                "Raters can still choose those levels. Without an anchor each "
                "rater invents their own meaning, which shows up later as "
                "disagreement nobody can trace. Either write the anchors or "
                "state that only the anchored levels are selectable."))

        if len(levels) == 2:
            findings.append(Finding("warning", where, "only two levels",
                                    "A binary dimension is a checklist item. "
                                    "That is fine, but it should not be "
                                    "averaged with ordinal dimensions."))

        for lv, text in scale.items():
            spot = f"{where} level {lv}"
            if not isinstance(text, str) or not text.strip():
                findings.append(Finding("error", spot, "empty anchor",
                                        "Nothing for a rater to apply."))
                continue
            words = text.split()
            if len(words) < MIN_ANCHOR_WORDS:
                findings.append(Finding(
                    "warning", spot, f"anchor is {len(words)} words",
                    "Short anchors tend to be labels rather than criteria. A "
                    "rater cannot apply 'Good' consistently."))
            hedge = VAGUE.search(text)
            if hedge:
                findings.append(Finding(
                    "warning", spot, f"vague term {hedge.group(0)!r}",
                    "Hedged language makes an anchor unfalsifiable, so two "
                    "raters can both believe they applied it correctly."))

    # Mixed scales are a real trap: averaging a 1-3 dimension with a 1-5 one
    # silently weights them differently.
    distinct = {lv for _, lv in level_sets}
    if len(distinct) > 1:
        findings.append(Finding(
            "warning", "rubric",
            f"dimensions use {len(distinct)} different scales: "
            + "; ".join(f"{n}={list(lv)}" for n, lv in level_sets),
            "Averaging across dimensions with different ranges weights them "
            "unequally without anyone deciding to."))

    order = {"error": 0, "warning": 1, "info": 2}
    return sorted(findings, key=lambda f: order[f.severity])


def summarise(findings: list[Finding]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for f in findings:
        counts[f.severity] += 1
    return counts
