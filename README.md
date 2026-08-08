# AI Evaluation, Safety & Red-Teaming Portfolio

Rubrics, evaluation methodology, and a toolkit that checks whether a rubric is
structurally sound before anyone scores against it.

Built by **Chima Anthony Ukachukwu**, AI Evaluation & Safety Specialist.
[chimaukachukwu.com](https://chimaukachukwu.com) · [LinkedIn](https://linkedin.com/in/chima-anthony-u)

> **NDA-compliant.** Everything here is a generalized reconstruction. No
> proprietary prompts, datasets, tools, personas or client identifiers. See
> [NDA_DISCLAIMER.md](NDA_DISCLAIMER.md).

---

## Start here

The most useful thing in this repository is not a description of my work. It is
a tool that found a real defect in my own rubrics.

```bash
cd rubric-toolkit && pip install -e .
rubrictk check ../rubrics/safety-rubric.json
```

At v1.0 both rubrics declared a 1 to 5 scale and defined anchors only at 1, 3
and 5. Raters could select 2 or 4 with nothing telling them what those meant.
Eight dimensions across two files, every one affected.

Read the write-up: [`docs/rubric-audit.md`](docs/rubric-audit.md). It covers why
that defect produces disagreement nobody can trace, what changed at v2.0, and a
false positive the checker raised against itself afterwards.

---

## What is here

### `rubric-toolkit/`

Rubric validation and inter-rater agreement. No dependencies outside the
standard library, 52 tests, statistics checked against published worked
examples rather than against their own output.

- Structural checks that run before data collection: scale gaps, hedged
  anchors, mixed ranges, duplicate dimensions
- Cohen's kappa with quadratic weighting, Fleiss' kappa, Krippendorff's alpha
- Per-rater calibration offsets, which is the actionable half: agreement
  statistics say raters disagree, calibration says which one runs harsh

One thing it makes visible, on the bundled example:

```
Fleiss' kappa        = 0.300 (fair)
Krippendorff's alpha = 0.850 (almost perfect)
```

Same data. Fleiss treats an ordinal scale as nominal, so a 4 against a 5 counts
as badly as a 1 against a 5. Rubric scores are ordinal, and quoting the wrong
statistic has caused teams to rewrite rubrics that were working.

### `rubrics/`

Scoring rubrics as structured JSON, versioned, with changelogs.

- [`safety-rubric.json`](rubrics/safety-rubric.json), four dimensions: policy
  compliance, harm enablement, refusal quality, privacy handling
- [`reasoning-rubric.json`](rubrics/reasoning-rubric.json), four dimensions:
  problem understanding, logical consistency, evidence, correctness
- [`qa-checklist.md`](rubrics/qa-checklist.md)

Both at v2.0, both validating clean, both guarded by a test.

### `project-archetypes/`

Four reconstructions of the kinds of evaluation work I do, written at
methodology level.

| Archetype | Focus |
|---|---|
| [Adversarial safety testing](project-archetypes/adversarial-ai-safety-testing.md) | Multi-turn privacy and data-exfiltration risk |
| [Governance and risk control](project-archetypes/ai-safety-governance-risk-control.md) | When a model should respond, uplevel or refuse |
| [Harm-precision rubric design](project-archetypes/harm-precision-rubric-governance.md) | Cutting false positives without losing harm detection |
| [Long-context red teaming](project-archetypes/long-context-authentic-red-teaming.md) | Failures that only appear over extended conversation |

### `workflow/`

How the work runs: [evaluation
workflow](workflow/evaluation-workflow.md) and [time tracking
practices](workflow/time-tracking-best-practices.md).

---

## Structure

```
rubric-toolkit/          validation and agreement statistics, 52 tests
  src/rubrictk/
    schema.py            structural checks, each finding says why it exists
    agreement.py         Cohen, Fleiss, Krippendorff, rater calibration
    cli.py               rubrictk check | rubrictk agree
  examples/              worked scores CSV
rubrics/                 versioned JSON rubrics with changelogs
docs/rubric-audit.md     what the validator found in my own rubrics
project-archetypes/      four methodology reconstructions
workflow/                process documentation
```

---

## What this repository is careful about

**NDA discipline.** Working prompts, client identifiers, real datasets and
proprietary policy language are absent by choice. Their absence is not a gap
for a contributor to fill. See [SECURITY.md](SECURITY.md) if you believe
something here should not be public.

**Not overclaiming.** The toolkit checks structure. Structure is necessary and
nowhere near sufficient: a structurally perfect rubric can still produce poor
agreement because a construct is ambiguous or raters were trained differently.
Those need scored data, not a schema check, and the audit document says so
plainly.

**Statistics that can be checked.** Every agreement figure is computed by code
in this repository, tested against published examples, and reproducible from
the bundled CSV. Nothing here asks to be taken on trust.

## Licence

Written material under CC BY 4.0, see [LICENSE](LICENSE) and
[NOTICE.md](NOTICE.md). Code in `rubric-toolkit/` under MIT.
