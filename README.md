# LLM Clinical Chart Abstraction with Evaluation Harness

Automating the first pass of hospital quality-measure chart abstraction, and measuring
how often the model is actually right.

## The problem

Hospitals report quality measures to CMS. To do that, trained abstractors read discharge
summaries and decide, case by case, whether an encounter meets a measure's numerator.
It is rule-application work, not clinical judgment, and it is slow: roughly 10 minutes
per chart, thousands of charts per quarter.

An LLM can do the first pass. The open question is whether it does it correctly — and
nobody should deploy one without an answer.

## What this repo does

1. Applies a simplified **Hospital Harm — Severe Hypoglycemia** measure spec to 40
   synthetic discharge summaries
2. Extracts structured fields via LLM (denominator, numerator, lowest glucose, exclusion
   reason, supporting evidence quote)
3. Scores predictions against a **hand-labeled gold standard**
4. Compares a naive prompt against a specification-grounded prompt

## Results

| Metric | v1 naive | v2 spec-grounded |
|---|---|---|
| Numerator accuracy | __% | __% |
| Precision | __% | __% |
| Recall | __% | __% |
| F1 | __% | __% |
| Parse failures | _ / 40 | _ / 40 |
| Cost per 1,000 charts | $__ | $__ |

## Where the model fails

_(fill in after running — these are the most interesting part)_

- **Unit conversion.** ...
- **Timing windows.** ...
- **Present on admission vs hospital harm.** ...
- **Narrative without a numeric value.** ...
- **Flagged lab errors.** ...

## Dataset

40 synthetic discharge summaries written to exercise specific edge cases: clear positives,
clear negatives, denominator failures, present-on-admission exclusions, mmol/L units,
out-of-window timing, hemolyzed-specimen lab errors, narrative-only documentation, and
prior-admission history used as a distractor. No real patient data.

## Running it

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-...

cp gold_labels_TEMPLATE.csv gold_labels.csv   # then label all 40 by hand
python extract.py v1
python extract.py v2
python evaluate.py v1 v2
```

## Files

```
MEASURE_SPEC.md   the rule set, applied by both human and model
notes/            40 synthetic discharge summaries
extract.py        LLM extraction, v1 and v2 prompts
evaluate.py       precision / recall / F1 against the gold set
gold_labels.csv   hand-labeled ground truth
```

## Limitations

Synthetic notes are cleaner than real charts. The gold standard is single-rater, so there
is no inter-rater reliability estimate. n=40 gives wide confidence intervals. This is a
demonstration of evaluation methodology, not a validated clinical tool.
