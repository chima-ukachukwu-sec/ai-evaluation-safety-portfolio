# Evaluation Workflow (NDA-Safe)

## Purpose
This document describes a generalized, NDA-compliant workflow for AI evaluation and safety testing. It focuses on methodology and decision discipline rather than proprietary tooling.

---

## 1. Intake & Task Understanding
- Read task instructions and rubric carefully (off-timer if using a platform timer)
- Identify the evaluation goal (accuracy, safety, policy compliance, realism, consistency)
- Note any constraints (format requirements, refusal policy, escalation rules)

---

## 2. Context & Risk Identification
- Determine what the user is asking for (intent + capability level)
- Identify safety-relevant risk factors (privacy, harm enablement, unlawful activity, self-harm, etc.)
- Decide whether content should be: Respond / Uplevel / Refuse (based on project rules)

---

## 3. Structured Evaluation
- Apply the rubric criteria consistently
- Score only what is present in the content (avoid assumptions)
- Prioritize “material enablement” signals over theoretical prerequisites
- Separate observations from conclusions

---

## 4. Justification Writing
Write explanations that are:
- Specific (tie to concrete parts of the content)
- Policy-aligned (no internal policy text)
- Reviewer-friendly (short, clear reasoning)

---

## 5. Quality Control (QC)
Before submission:
- Confirm scores match justification
- Check for false positives (over-attribution)
- Ensure format compliance (JSON fields, required structure)
- Verify the response strategy aligns with risk

---

## 6. Logging & Pattern Tracking (Optional)
- Record recurring failure modes (high-level, non-sensitive)
- Track trends (e.g., long-context drift, refusal weakening, inconsistent persona)
- Note edge cases that require clarification

---

## NDA Notice
This workflow is a generalized reconstruction and does not include proprietary tools, prompts, or internal schemas.
