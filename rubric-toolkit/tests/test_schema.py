"""
Tests for rubric validation.

The check that matters is the missing-anchor one: it is the defect that found
a real gap in both shipped rubrics, and it is the kind that produces
unexplainable disagreement weeks after the data is collected.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rubrictk.schema import RubricError, load_rubric, summarise, validate

RUBRICS = Path(__file__).resolve().parents[2] / "rubrics"


def rubric(**dims):
    return {"name": "T", "version": "1",
            "dimensions": [{"dimension": k, "scale": v} for k, v in dims.items()]}


FULL = {str(i): f"A specific and checkable criterion for level {i}." for i in range(1, 6)}


# --- the check that found a real defect ----------------------------------

def test_gap_in_the_scale_is_an_error():
    r = rubric(D={"1": "Lowest level, clearly defined here.",
                  "3": "Middle level, clearly defined here.",
                  "5": "Highest level, clearly defined here."})
    errs = [f for f in validate(r) if f.severity == "error"]
    assert any("no anchor for 2, 4" in f.message for f in errs)


def test_complete_scale_passes():
    assert not [f for f in validate(rubric(D=FULL)) if f.severity == "error"]


def test_the_finding_explains_itself():
    """A finding a reader cannot act on is noise."""
    r = rubric(D={"1": "Lowest level, clearly defined here.",
                  "3": "Middle level, clearly defined here."})
    f = next(f for f in validate(r) if f.severity == "error")
    assert f.why and len(f.why.split()) > 8


# --- other structural defects --------------------------------------------

def test_missing_dimensions_is_an_error():
    assert any(f.severity == "error" for f in validate({"name": "x", "version": "1"}))


def test_missing_scale_is_an_error():
    r = {"name": "x", "version": "1", "dimensions": [{"dimension": "D"}]}
    assert any("no scale" in f.message for f in validate(r))


def test_duplicate_dimension_names_are_an_error():
    r = {"name": "x", "version": "1",
         "dimensions": [{"dimension": "D", "scale": FULL},
                        {"dimension": "D", "scale": FULL}]}
    assert any("duplicate" in f.message for f in validate(r))


def test_empty_anchor_is_an_error():
    bad = dict(FULL); bad["3"] = "   "
    assert any("empty anchor" in f.message for f in validate(rubric(D=bad)))


def test_missing_name_and_version_are_warnings():
    r = {"dimensions": [{"dimension": "D", "scale": FULL}]}
    msgs = [f.message for f in validate(r) if f.severity == "warning"]
    assert "no name" in msgs and "no version" in msgs


def test_short_anchor_is_flagged():
    bad = dict(FULL); bad["3"] = "Fine."
    assert any("words" in f.message for f in validate(rubric(D=bad)))


def test_hedged_language_is_flagged():
    bad = dict(FULL); bad["4"] = "The response is generally acceptable to a reader."
    assert any("vague term" in f.message for f in validate(rubric(D=bad)))


def test_contrastive_rather_than_is_not_flagged():
    """
    A false positive this checker raised against its own corrected rubrics.
    Warning on ordinary prose teaches the reader to ignore warnings.
    """
    ok = dict(FULL)
    ok["4"] = "Consistent throughout, though one transition is asserted rather than shown."
    assert not [f for f in validate(rubric(D=ok)) if "vague" in f.message]


def test_mixed_scale_ranges_are_flagged():
    r = {"name": "x", "version": "1", "dimensions": [
        {"dimension": "A", "scale": FULL},
        {"dimension": "B", "scale": {str(i): f"Level {i} defined clearly here." for i in (1, 2, 3)}},
    ]}
    assert any("different scales" in f.message for f in validate(r))


def test_findings_are_sorted_worst_first():
    r = {"dimensions": [{"dimension": "D", "scale": {"1": "Only one level here now."}}]}
    sev = [f.severity for f in validate(r)]
    assert sev == sorted(sev, key=lambda s: {"error": 0, "warning": 1, "info": 2}[s])


# --- loading -------------------------------------------------------------

def test_missing_file_raises():
    with pytest.raises(RubricError, match="not found"):
        load_rubric("/nonexistent/rubric.json")


def test_invalid_json_raises(tmp_path):
    p = tmp_path / "r.json"; p.write_text("{not json")
    with pytest.raises(RubricError, match="not valid JSON"):
        load_rubric(p)


def test_non_object_raises(tmp_path):
    p = tmp_path / "r.json"; p.write_text("[1,2,3]")
    with pytest.raises(RubricError, match="JSON object"):
        load_rubric(p)


def test_summarise_counts_by_severity():
    counts = summarise(validate({"dimensions": []}))
    assert set(counts) == {"error", "warning", "info"}


# --- the shipped rubrics must stay clean ---------------------------------

@pytest.mark.parametrize("name", ["safety-rubric.json", "reasoning-rubric.json"])
def test_shipped_rubrics_have_no_errors(name):
    """
    A regression guard. Both files failed this check at v1.0, which is how the
    gap was found. They must not regress.
    """
    path = RUBRICS / name
    if not path.is_file():
        pytest.skip(f"{name} not present in this checkout")
    findings = validate(load_rubric(path))
    errors = [f for f in findings if f.severity == "error"]
    assert not errors, "\n".join(str(f) for f in errors)


@pytest.mark.parametrize("name", ["safety-rubric.json", "reasoning-rubric.json"])
def test_shipped_rubrics_record_their_history(name):
    path = RUBRICS / name
    if not path.is_file():
        pytest.skip(f"{name} not present")
    data = load_rubric(path)
    assert data.get("changelog"), "a rubric version with no changelog is not comparable"
