# Measure Specification (simplified)

**Hospital Harm — Severe Hypoglycemia**
Adapted and simplified from the CMS Hospital Harm eCQM family for demonstration purposes.
This is not the official specification. It is a clean, self-contained rule set so that a
human abstractor and an LLM can be scored against the same target.

---

## DENOMINATOR — does this encounter count at all?

An encounter is in the denominator if **all** of the following are true:

1. Inpatient admission
2. Patient age **18 or older**
3. The patient received **at least one antidiabetic medication administered by the hospital**
   during the stay

Antidiabetic medications include: insulin (any formulation — glargine, detemir, NPH, aspart,
lispro, regular, IV infusion), sulfonylureas (glipizide, glyburide, glimepiride), metformin,
DPP-4 inhibitors, SGLT2 inhibitors, GLP-1 agonists.

Note: a medication the patient takes at home but which was **held / never given** during the
admission does not count. A medication self-administered by the patient (e.g. their own pump)
does not count as hospital-administered.

---

## NUMERATOR — did a harm event occur?

The encounter meets the numerator if:

- There is at least one **glucose result below 40 mg/dL**, AND
- That result occurred **within 24 hours after** an antidiabetic medication administration

Glucose source may be laboratory or point-of-care. Both count.

**Unit conversion:** if glucose is reported in mmol/L, multiply by 18 to get mg/dL.
(40 mg/dL ≈ 2.2 mmol/L)

---

## EXCLUSIONS — do not count as hospital harm

Exclude the encounter from the numerator if the low glucose:

1. Was **present on admission** — i.e. occurred in the field, in the ED, or before any
   antidiabetic medication was administered by the hospital, and no qualifying low value
   occurred afterward
2. Was a **laboratory error** explicitly flagged as such (e.g. hemolyzed specimen) and
   contradicted by a repeat or simultaneous value
3. Is documented only as a **narrative characterization** with no recorded numeric value
   (e.g. "blood sugar in the 30s" with no corresponding lab or POC result)
4. Refers to a **prior admission or outpatient history**, not the current encounter

---

## Output fields to extract

| Field | Type | Meaning |
|---|---|---|
| `in_denominator` | bool | Meets all three denominator criteria |
| `lowest_glucose_mg_dl` | number or null | Lowest numeric glucose in the current encounter |
| `antidiabetic_given` | bool | Hospital administered an antidiabetic med |
| `meets_numerator` | bool | Qualifying low glucose after a med, not excluded |
| `exclusion_reason` | string or null | Which exclusion applied, if any |
| `evidence_quote` | string | Verbatim text from the note supporting the decision |
