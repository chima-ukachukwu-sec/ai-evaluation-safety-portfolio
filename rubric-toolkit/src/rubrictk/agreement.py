"""
Inter-rater agreement for ordinal rubric scores.

The reason this exists: a rubric is only worth what two raters independently
agree on. Percent agreement is the number people quote and it is close to
useless, because on a 5-point scale two raters guessing at random agree about
20% of the time, and on a skewed distribution far more. Chance-corrected
statistics say how much agreement is left once you subtract what luck explains.

Implemented in plain Python with no numeric dependency. These are small
matrices and the arithmetic is not the hard part; being able to read the
formula next to the citation is worth more here than speed.

References:
  Cohen, J. (1960). A coefficient of agreement for nominal scales.
  Cohen, J. (1968). Weighted kappa.
  Fleiss, J.L. (1971). Measuring nominal scale agreement among many raters.
  Krippendorff, K. (2004). Content Analysis, 2nd ed.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence

Score = int | float | None


class AgreementError(ValueError):
    """Raised when the input cannot support the statistic requested."""


# Landis and Koch (1977). Widely cited, widely over-applied. These labels are a
# convention for talking about a number, not a standard anybody should treat as
# a pass mark.
def interpret(kappa: float) -> str:
    if kappa < 0:
        return "worse than chance"
    if kappa < 0.21:
        return "slight"
    if kappa < 0.41:
        return "fair"
    if kappa < 0.61:
        return "moderate"
    if kappa < 0.81:
        return "substantial"
    return "almost perfect"


@dataclass(frozen=True)
class AgreementResult:
    statistic: str
    value: float
    n_items: int
    n_raters: int
    detail: str = ""

    @property
    def label(self) -> str:
        return interpret(self.value)

    def __str__(self) -> str:
        return f"{self.statistic} = {self.value:.3f} ({self.label})"


def _weight(a: float, b: float, categories: Sequence[float], scheme: str) -> float:
    """Disagreement weight between two categories, 0 = identical."""
    if scheme == "unweighted":
        return 0.0 if a == b else 1.0
    span = max(categories) - min(categories)
    if span == 0:
        return 0.0
    d = abs(a - b) / span
    if scheme == "linear":
        return d
    if scheme == "quadratic":
        return d * d
    raise AgreementError(f"unknown weighting scheme {scheme!r}")


def cohens_kappa(rater_a: Sequence[Score], rater_b: Sequence[Score],
                 weights: str = "quadratic") -> AgreementResult:
    """
    Agreement between exactly two raters on the same items.

    Quadratic weighting is the default because rubric scores are ordinal: a
    3-versus-4 disagreement is not the same failure as a 1-versus-5, and
    unweighted kappa treats them identically. Items either rater left blank are
    dropped pairwise.
    """
    if len(rater_a) != len(rater_b):
        raise AgreementError("raters scored different numbers of items")

    pairs = [(a, b) for a, b in zip(rater_a, rater_b) if a is not None and b is not None]
    if not pairs:
        raise AgreementError("no items scored by both raters")

    cats = sorted({v for pair in pairs for v in pair})
    if len(cats) == 1:
        # Everyone agreed on everything and used one category. Kappa is
        # undefined here (expected agreement is 1), and reporting 0 would be
        # actively misleading.
        raise AgreementError(
            "both raters used a single category; kappa is undefined. "
            "Perfect agreement, no discrimination.")

    n = len(pairs)
    observed = sum(1 - _weight(a, b, cats, weights) for a, b in pairs) / n

    count_a = Counter(a for a, _ in pairs)
    count_b = Counter(b for _, b in pairs)
    expected = sum(
        (count_a[x] / n) * (count_b[y] / n) * (1 - _weight(x, y, cats, weights))
        for x in cats for y in cats
    )
    if math.isclose(expected, 1.0):
        raise AgreementError("expected agreement is 1; kappa is undefined")

    k = (observed - expected) / (1 - expected)
    return AgreementResult("Cohen's kappa", k, n, 2, f"{weights} weighting")


def fleiss_kappa(ratings: Sequence[Sequence[Score]]) -> AgreementResult:
    """
    Agreement among three or more raters.

    `ratings` is one row per item, one column per rater. Unlike Cohen's, this
    does not assume the same raters scored every item, only that the number of
    ratings per item is constant. Rows with missing scores are dropped, and how
    many were dropped is reported rather than swallowed.
    """
    rows = [list(r) for r in ratings]
    if not rows:
        raise AgreementError("no items")

    complete = [r for r in rows if all(v is not None for v in r)]
    dropped = len(rows) - len(complete)
    if len(complete) < 2:
        raise AgreementError("fewer than two fully-scored items")

    n_raters = len(complete[0])
    if n_raters < 3:
        raise AgreementError("Fleiss' kappa needs at least three raters; "
                             "use Cohen's kappa for two")
    if any(len(r) != n_raters for r in complete):
        raise AgreementError("items have different numbers of raters")

    cats = sorted({v for row in complete for v in row})
    n_items = len(complete)

    # Per-item agreement: the proportion of rater pairs that agree.
    p_i = []
    for row in complete:
        counts = Counter(row)
        agree = sum(c * (c - 1) for c in counts.values())
        p_i.append(agree / (n_raters * (n_raters - 1)))
    p_bar = sum(p_i) / n_items

    # Expected agreement from the marginal distribution of each category.
    totals = Counter(v for row in complete for v in row)
    p_e = sum((totals[c] / (n_items * n_raters)) ** 2 for c in cats)

    if math.isclose(p_e, 1.0):
        raise AgreementError("expected agreement is 1; kappa is undefined")

    k = (p_bar - p_e) / (1 - p_e)
    detail = f"{n_raters} raters" + (f", {dropped} incomplete items dropped" if dropped else "")
    return AgreementResult("Fleiss' kappa", k, n_items, n_raters, detail)


def krippendorff_alpha(ratings: Sequence[Sequence[Score]],
                       level: str = "ordinal") -> AgreementResult:
    """
    Krippendorff's alpha, which tolerates missing data by design.

    This is the statistic to reach for when raters did not all score every
    item, which is the normal situation in a real evaluation pipeline. Items
    with fewer than two ratings carry no information about agreement and are
    excluded, per the definition.
    """
    if level not in {"nominal", "ordinal", "interval"}:
        raise AgreementError(f"unsupported level {level!r}")

    units = [[v for v in row if v is not None] for row in ratings]
    usable = [u for u in units if len(u) >= 2]
    if not usable:
        raise AgreementError("no items have two or more ratings")

    values = sorted({v for u in usable for v in u})
    if len(values) == 1:
        raise AgreementError("only one distinct value was used; alpha is undefined")

    def delta(a: float, b: float) -> float:
        if level == "nominal":
            return 0.0 if a == b else 1.0
        if level == "interval":
            return (a - b) ** 2
        # Ordinal: distance measured across the observed rank scale.
        lo, hi = sorted((values.index(a), values.index(b)))
        return float((hi - lo) ** 2)

    # Observed disagreement, weighted by how many ratings each unit received.
    n_total = sum(len(u) for u in usable)
    d_o = 0.0
    for u in usable:
        m = len(u)
        pair_sum = sum(delta(a, b) for i, a in enumerate(u)
                       for j, b in enumerate(u) if i != j)
        d_o += pair_sum / (m - 1)
    d_o /= n_total

    # Expected disagreement across the whole pooled distribution.
    pooled = [v for u in usable for v in u]
    d_e = sum(delta(a, b) for i, a in enumerate(pooled)
              for j, b in enumerate(pooled) if i != j)
    d_e /= (n_total * (n_total - 1))

    if math.isclose(d_e, 0.0):
        raise AgreementError("expected disagreement is zero; alpha is undefined")

    alpha = 1 - (d_o / d_e)
    max_raters = max(len(u) for u in usable)
    return AgreementResult("Krippendorff's alpha", alpha, len(usable), max_raters,
                           f"{level} level")


def rater_bias(ratings: Sequence[Sequence[Score]],
               rater_names: Sequence[str] | None = None) -> list[tuple[str, float, float]]:
    """
    Per-rater mean offset from the item mean.

    Agreement statistics tell you whether raters disagree. They do not tell you
    which rater is consistently harsher, and that is the actionable finding: a
    rater sitting half a point below everyone else is a calibration
    conversation, not a rubric problem.

    Returns (name, mean offset, mean absolute deviation), sorted by offset.
    """
    if not ratings:
        return []
    n_raters = max(len(r) for r in ratings)
    names = list(rater_names) if rater_names else [f"rater_{i+1}" for i in range(n_raters)]

    offsets: dict[int, list[float]] = {i: [] for i in range(n_raters)}
    for row in ratings:
        present = [(i, v) for i, v in enumerate(row) if v is not None]
        if len(present) < 2:
            continue
        item_mean = sum(v for _, v in present) / len(present)
        for i, v in present:
            offsets[i].append(v - item_mean)

    out = []
    for i in range(n_raters):
        vals = offsets[i]
        if not vals:
            continue
        mean = sum(vals) / len(vals)
        mad = sum(abs(v) for v in vals) / len(vals)
        out.append((names[i] if i < len(names) else f"rater_{i+1}", mean, mad))
    return sorted(out, key=lambda t: t[1])
