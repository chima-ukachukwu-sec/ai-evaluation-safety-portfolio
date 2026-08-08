"""
Command line interface.

Two things it does: check a rubric's structure before anyone scores against it,
and report agreement once they have.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from .agreement import (AgreementError, cohens_kappa, fleiss_kappa,
                        krippendorff_alpha, rater_bias)
from .schema import RubricError, load_rubric, summarise, validate


def _read_scores(path: str) -> tuple[list[str], list[list[float | None]]]:
    """
    Read a scores CSV: one row per item, one column per rater.

    A blank cell means that rater did not score that item, which is normal and
    is why Krippendorff's alpha exists.
    """
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        raise ValueError(f"{path} is empty")
    header, body = rows[0], rows[1:]
    # Drop a leading item-id column if present.
    start = 1 if header and header[0].strip().lower() in {"item", "id", "item_id"} else 0
    names = [h.strip() for h in header[start:]]
    out: list[list[float | None]] = []
    for r in body:
        if not any(c.strip() for c in r):
            continue
        vals: list[float | None] = []
        for cell in r[start:start + len(names)]:
            cell = cell.strip()
            vals.append(float(cell) if cell else None)
        out.append(vals)
    return names, out


def cmd_check(args) -> int:
    try:
        rubric = load_rubric(args.rubric)
    except RubricError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    findings = validate(rubric)
    counts = summarise(findings)

    if args.json:
        print(json.dumps({
            "rubric": rubric.get("name", Path(args.rubric).name),
            "counts": counts,
            "findings": [{"severity": f.severity, "where": f.where,
                          "message": f.message, "why": f.why} for f in findings],
        }, indent=2))
    else:
        print(f"\n{rubric.get('name', args.rubric)}")
        print(f"  {len(rubric.get('dimensions', []))} dimensions, "
              f"{counts['error']} errors, {counts['warning']} warnings\n")
        for f in findings:
            print(f"  {f}")
        if not findings:
            print("  no findings")
    return 1 if counts["error"] else 0


def cmd_agree(args) -> int:
    try:
        names, rows = _read_scores(args.scores)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    n_raters = len(names)
    print(f"\n{args.scores}: {len(rows)} items, {n_raters} raters\n")

    results = []
    try:
        if n_raters == 2:
            results.append(cohens_kappa([r[0] for r in rows],
                                        [r[1] for r in rows], args.weights))
        elif n_raters >= 3:
            try:
                results.append(fleiss_kappa(rows))
            except AgreementError as exc:
                print(f"  Fleiss' kappa unavailable: {exc}")
        results.append(krippendorff_alpha(rows, args.level))
    except AgreementError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for r in results:
        print(f"  {r}")
        if r.detail:
            print(f"      {r.detail}")

    bias = rater_bias(rows, names)
    if bias:
        print("\n  rater calibration (offset from item mean):")
        for name, mean, mad in bias:
            flag = "  <-- consistently harsher" if mean <= -0.4 else (
                   "  <-- consistently more lenient" if mean >= 0.4 else "")
            print(f"    {name:16} {mean:+.2f}   spread {mad:.2f}{flag}")

    if args.json:
        print(json.dumps({
            "items": len(rows), "raters": n_raters,
            "statistics": [{"name": r.statistic, "value": round(r.value, 4),
                            "interpretation": r.label} for r in results],
            "bias": [{"rater": n, "offset": round(m, 4),
                      "spread": round(d, 4)} for n, m, d in bias],
        }, indent=2))

    if args.min_agreement is not None:
        worst = min(r.value for r in results)
        if worst < args.min_agreement:
            print(f"\n  below threshold: {worst:.3f} < {args.min_agreement}")
            return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rubrictk",
        description="Validate rubrics and measure inter-rater agreement.")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("check", help="validate a rubric's structure")
    c.add_argument("rubric")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_check)

    a = sub.add_parser("agree", help="agreement statistics from a scores CSV")
    a.add_argument("scores")
    a.add_argument("--weights", default="quadratic",
                   choices=["unweighted", "linear", "quadratic"])
    a.add_argument("--level", default="ordinal",
                   choices=["nominal", "ordinal", "interval"])
    a.add_argument("--min-agreement", type=float,
                   help="exit 1 if any statistic falls below this")
    a.add_argument("--json", action="store_true")
    a.set_defaults(func=cmd_agree)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
