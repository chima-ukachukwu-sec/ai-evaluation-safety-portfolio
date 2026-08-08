# rubric-toolkit

Validates rubric structure before anyone scores against it, and measures
inter-rater agreement once they have.

```bash
pip install -e .
rubrictk check ../rubrics/safety-rubric.json
rubrictk agree examples/scores-example.csv
```

No dependencies outside the standard library.

---

## Why this exists

A rubric fails quietly. Nobody gets an error when a scale runs 1 to 5 but only
defines 1, 3 and 5. A rater picks 4 for their own reasons, a second rater picks
it for different reasons, and the disagreement surfaces weeks later as noise
nobody can trace back to its cause.

That is not hypothetical. Running `rubrictk check` against the two rubrics in
this repository found exactly that defect in **all eight dimensions across both
files**. They are fixed at v2.0, and a test now guards against the regression.
The full account is in [`docs/rubric-audit.md`](../docs/rubric-audit.md).

---

## The finding worth knowing

Run the bundled example and two statistics disagree sharply about the same
data:

```
Fleiss' kappa        = 0.300 (fair)
Krippendorff's alpha = 0.850 (almost perfect)
```

Both are correct. Fleiss' kappa treats the scale as **nominal**: a rater
scoring 4 where another scored 5 is counted as exactly as wrong as 1 against 5.
Krippendorff's ordinal alpha knows that 4 and 5 are adjacent.

Rubric scores are ordinal. Quoting Fleiss on ordinal data understates agreement
badly, and teams have rewritten working rubrics because of that number. Use a
weighted or ordinal statistic, and say which one you used.

This is the reason quadratic weighting is the default for Cohen's kappa here.

---

## What it does

### `rubrictk check`

Structural checks that run before any data is collected:

| Check | Severity | Why |
|---|---|---|
| Gap in the scale | error | A selectable level with no anchor means every rater invents its meaning |
| No scale, or non-numeric levels | error | Nothing to score, or nothing to order |
| Duplicate dimension names | error | Cannot report on them separately |
| Empty anchor | error | Nothing for a rater to apply |
| Hedged wording | warning | "Generally acceptable" is not falsifiable |
| Anchor under four words | warning | Usually a label rather than a criterion |
| Mixed scale ranges | warning | Averaging a 1-3 with a 1-5 weights them unequally by accident |
| No name or version | warning | Scores are not comparable across time without them |

Every finding states why it exists, not only what it wants. Exit code 1 on any
error, so it can gate a pipeline.

### `rubrictk agree`

Reads a scores CSV, one row per item, one column per rater. Blank cells mean
that rater did not score that item, which is normal.

- **Cohen's kappa** for two raters, quadratic weighting by default
- **Fleiss' kappa** for three or more
- **Krippendorff's alpha**, which tolerates missing data by design
- **Rater calibration**: per-rater offset from the item mean

The calibration table is the actionable part. Agreement statistics tell you
that raters disagree. They do not tell you which rater is consistently harsher,
and that is a conversation about calibration rather than a reason to rewrite
the rubric.

```
rater calibration (offset from item mean):
  carol            -0.17   spread 0.39
  alice            -0.00   spread 0.28
  bob              +0.17   spread 0.44
```

---

## Usage

```bash
rubrictk check rubric.json --json          # machine-readable findings
rubrictk agree scores.csv --weights linear # or unweighted, quadratic
rubrictk agree scores.csv --level nominal  # for genuinely categorical labels
rubrictk agree scores.csv --min-agreement 0.7   # exit 1 below threshold
```

```python
from rubrictk import validate, load_rubric, cohens_kappa, rater_bias

findings = validate(load_rubric("rubric.json"))
result = cohens_kappa(alice_scores, bob_scores)     # quadratic by default
print(result)          # "Cohen's kappa = 0.812 (almost perfect)"
```

---

## Design notes

**No numeric dependency.** These are small matrices and the arithmetic is not
the hard part. Being able to read the formula next to its citation is worth
more here than speed, and it means the package installs anywhere.

**Undefined is not zero.** When two raters use a single category, kappa is
undefined: expected agreement is 1. Returning 0 would read as "they disagreed"
when in fact they agreed perfectly and discriminated nothing. It raises instead
and says so.

**Missing data is reported, not swallowed.** Fleiss drops incomplete items and
tells you how many. Alpha excludes units with fewer than two ratings, which is
the definition rather than a shortcut.

---

## Testing

```bash
pip install -e ".[dev]"
pytest -q      # 52 tests
```

The statistics are tested against published worked examples rather than against
whatever the code currently returns, including Cohen's 1960 two-by-two
illustration which must produce exactly 0.40. A statistic that is confidently
wrong is worse than one that is absent, because nobody re-derives a number that
looks plausible.

Two defects were found by these tests and by running the tool on this
repository's own rubrics:

1. **Both shipped rubrics had unanchored levels 2 and 4**, in all eight
   dimensions. Fixed at v2.0, guarded by a test.
2. **The vague-language check flagged "rather than"**, ordinary contrastive
   prose, as a hedge. Warning on correct writing teaches a reader to ignore
   warnings, which is worse than not warning. Fixed with a negative lookahead
   and a test.

---

## Limitations

- Agreement statistics describe consistency, not correctness. Two raters can
  agree perfectly and both be wrong, and no number here will tell you.
- The Landis and Koch labels ("fair", "substantial") are a convention for
  talking about a value, not a standard. They are widely over-applied.
- Rater bias is a mean offset. It will not distinguish a harsh rater from one
  who happened to be assigned harder items, which needs a design that overlaps
  assignments deliberately.
- The vague-language list is heuristic and English-only.
- No confidence intervals. For a small item count a kappa is noisier than the
  three decimal places suggest.

---

## Future improvements

1. **Bootstrap confidence intervals** on each statistic, so a kappa from 12
   items is not read with the confidence of one from 1,200.
2. **Per-dimension agreement**, to show which dimension carries the
   disagreement. That is the number that tells you which anchor to rewrite.
3. **Disagreement triage**: list the specific items where raters diverged most,
   since those are the adjudication queue.
4. **Rubric diffing**, so a version bump reports which anchors changed and
   whether historical scores remain comparable.

## Licence

MIT for this directory. The written material in the wider repository is
CC BY 4.0. See [../LICENSE](../LICENSE) and [../NOTICE.md](../NOTICE.md).
