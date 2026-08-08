"""
Tests for the agreement statistics.

These check against published worked examples rather than against whatever the
code currently returns. A statistic that is confidently wrong is worse than one
that is absent, because nobody re-derives a number that looks plausible.
"""

from __future__ import annotations

import pytest

from rubrictk.agreement import (AgreementError, cohens_kappa, fleiss_kappa,
                                interpret, krippendorff_alpha, rater_bias)


# --- Cohen's kappa -------------------------------------------------------

def test_perfect_agreement_is_one():
    a = [1, 2, 3, 4, 5, 1, 2]
    assert cohens_kappa(a, a).value == pytest.approx(1.0)


def test_cohens_kappa_classic_worked_example():
    """
    Cohen (1960), the standard 2x2 illustration.

    50 items: 20 both yes, 15 both no, 10 A-yes B-no, 5 A-no B-yes.
    Observed 0.70, expected 0.50, kappa 0.40.
    """
    a = [1] * 20 + [0] * 15 + [1] * 10 + [0] * 5
    b = [1] * 20 + [0] * 15 + [0] * 10 + [1] * 5
    assert cohens_kappa(a, b, weights="unweighted").value == pytest.approx(0.4, abs=1e-9)


def test_quadratic_weighting_forgives_near_misses():
    """
    Ordinal scores are not nominal. A 3-versus-4 disagreement should cost less
    than a 1-versus-5, and unweighted kappa cannot express that.
    """
    a = [1, 2, 3, 4, 5]
    near = [1, 2, 3, 4, 4]
    far = [1, 2, 3, 4, 1]
    assert (cohens_kappa(a, near, "quadratic").value
            > cohens_kappa(a, far, "quadratic").value)
    assert (cohens_kappa(a, near, "quadratic").value
            > cohens_kappa(a, near, "unweighted").value)


def test_systematic_disagreement_goes_negative():
    a = [1, 1, 1, 5, 5, 5]
    b = [5, 5, 5, 1, 1, 1]
    assert cohens_kappa(a, b, "unweighted").value < 0


def test_missing_scores_are_dropped_pairwise():
    res = cohens_kappa([1, 2, None, 4], [1, 2, 3, None], "unweighted")
    assert res.n_items == 2


def test_mismatched_lengths_raise():
    with pytest.raises(AgreementError, match="different numbers"):
        cohens_kappa([1, 2], [1])


def test_no_overlap_raises():
    with pytest.raises(AgreementError, match="no items"):
        cohens_kappa([1, None], [None, 2])


def test_single_category_is_undefined_not_zero():
    """
    Both raters said 3 to everything. That is perfect agreement with no
    discrimination, and reporting kappa = 0 would read as 'they disagreed'.
    """
    with pytest.raises(AgreementError, match="undefined"):
        cohens_kappa([3, 3, 3], [3, 3, 3])


def test_unknown_weighting_scheme_raises():
    with pytest.raises(AgreementError, match="unknown weighting"):
        cohens_kappa([1, 2], [1, 2], weights="cubic")


# --- Fleiss' kappa -------------------------------------------------------

def test_fleiss_perfect_agreement():
    rows = [[1, 1, 1], [5, 5, 5], [3, 3, 3], [2, 2, 2]]
    assert fleiss_kappa(rows).value == pytest.approx(1.0)


def test_fleiss_random_disagreement_is_near_zero():
    """Three raters spread evenly across categories: nothing beyond chance."""
    rows = [[1, 2, 3], [2, 3, 1], [3, 1, 2], [1, 2, 3], [2, 3, 1], [3, 1, 2]]
    assert fleiss_kappa(rows).value == pytest.approx(-0.5, abs=0.6)


def test_fleiss_rejects_two_raters():
    with pytest.raises(AgreementError, match="at least three"):
        fleiss_kappa([[1, 1], [2, 2], [3, 3]])


def test_fleiss_reports_dropped_incomplete_items():
    rows = [[1, 1, 1], [2, 2, 2], [3, 3, None]]
    res = fleiss_kappa(rows)
    assert res.n_items == 2
    assert "1 incomplete" in res.detail


def test_fleiss_rejects_ragged_rows():
    with pytest.raises(AgreementError, match="different numbers of raters"):
        fleiss_kappa([[1, 1, 1], [2, 2, 2, 2]])


# --- Krippendorff's alpha ------------------------------------------------

def test_alpha_perfect_agreement():
    rows = [[1, 1], [3, 3], [5, 5], [2, 2]]
    assert krippendorff_alpha(rows).value == pytest.approx(1.0)


def test_alpha_tolerates_missing_data():
    """
    The reason to reach for alpha at all: raters rarely score every item, and
    kappa cannot cope with that.
    """
    rows = [[1, 1, None], [3, None, 3], [5, 5, 5], [2, 2, None]]
    res = krippendorff_alpha(rows)
    assert res.value == pytest.approx(1.0)
    assert res.n_items == 4


def test_alpha_ignores_units_with_one_rating():
    """A single rating carries no information about agreement."""
    rows = [[1, 1], [3, 3], [5, None], [2, 2]]
    assert krippendorff_alpha(rows).n_items == 3


def test_alpha_ordinal_beats_nominal_on_near_misses():
    rows = [[1, 2], [2, 3], [3, 4], [4, 5], [5, 4]]
    ordinal = krippendorff_alpha(rows, "ordinal").value
    nominal = krippendorff_alpha(rows, "nominal").value
    assert ordinal > nominal


def test_alpha_rejects_unknown_level():
    with pytest.raises(AgreementError, match="unsupported level"):
        krippendorff_alpha([[1, 1]], level="ratio")


def test_alpha_needs_two_ratings_somewhere():
    with pytest.raises(AgreementError, match="two or more"):
        krippendorff_alpha([[1, None], [2, None]])


# --- rater bias ----------------------------------------------------------

def test_bias_finds_the_harsh_rater():
    """
    Agreement statistics say raters disagree. This says which one is
    consistently lower, which is the actionable version.
    """
    rows = [[4, 5, 5], [3, 4, 4], [2, 3, 3], [4, 5, 5]]
    bias = rater_bias(rows, ["harsh", "b", "c"])
    assert bias[0][0] == "harsh"
    assert bias[0][1] < 0


def test_bias_is_zero_when_raters_are_calibrated():
    rows = [[3, 3, 3], [4, 4, 4], [5, 5, 5]]
    for _, mean, mad in rater_bias(rows):
        assert mean == pytest.approx(0.0)
        assert mad == pytest.approx(0.0)


def test_bias_skips_items_with_a_single_rating():
    rows = [[4, None, None], [3, 4, 5]]
    bias = rater_bias(rows)
    assert all(abs(m) < 2 for _, m, _ in bias)


def test_bias_on_empty_input():
    assert rater_bias([]) == []


# --- interpretation ------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    (-0.1, "worse than chance"), (0.1, "slight"), (0.3, "fair"),
    (0.5, "moderate"), (0.7, "substantial"), (0.9, "almost perfect"),
])
def test_landis_koch_bands(value, expected):
    assert interpret(value) == expected


def test_result_renders_readably():
    res = cohens_kappa([1, 2, 3, 4], [1, 2, 3, 5])
    text = str(res)
    assert "Cohen's kappa" in text and "=" in text
