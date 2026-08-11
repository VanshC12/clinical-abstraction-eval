"""
Runs an LLM over the discharge notes and extracts structured abstraction fields.

Usage:
    export ANTHROPIC_API_KEY=sk-...
    python extract.py v1
    python extract.py v2

Writes results to output/predictions_<version>.csv
"""

import os, sys, json, csv, time, pathlib
from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"
NOTES_DIR = pathlib.Path("notes")
OUT_DIR = pathlib.Path("output")
OUT_DIR.mkdir(exist_ok=True)

FIELDS = ["in_denominator", "lowest_glucose_mg_dl", "antidiabetic_given",
          "meets_numerator", "exclusion_reason", "evidence_quote"]

# ----------------------------------------------------------------------------
# V1 — the naive prompt. This is what most people would write on a first pass.
# ----------------------------------------------------------------------------
PROMPT_V1 = """You are reviewing a hospital discharge summary for quality reporting.

Determine whether this encounter counts for the Hospital Harm severe hypoglycemia measure.

Respond with ONLY a JSON object, no markdown fences, no preamble:
{{"in_denominator": bool, "lowest_glucose_mg_dl": number or null,
"antidiabetic_given": bool, "meets_numerator": bool,
"exclusion_reason": string or null, "evidence_quote": string}}

NOTE:
{note}"""

# ----------------------------------------------------------------------------
# V2 — the spec-grounded prompt. Full measure definition + worked examples.
# ----------------------------------------------------------------------------
SPEC = pathlib.Path("MEASURE_SPEC.md").read_text()

PROMPT_V2 = """You are a certified clinical chart abstractor applying a quality measure
specification. Apply the rules literally and mechanically. Do not use clinical judgment
beyond what the specification states.

<specification>
{spec}
</specification>

<worked_examples>
Example A — "Patient on IV insulin infusion. HD2 0400 glucose 32 mg/dL, D50 given."
  -> in_denominator: true (insulin given by hospital)
  -> meets_numerator: true (32 < 40, occurred during insulin infusion)

Example B — "Field glucose 30, ED glucose 28, D50 given in ED. No insulin administered
  by hospital at any point during admission."
  -> in_denominator: false (no hospital-administered antidiabetic)
  -> meets_numerator: false
  -> exclusion_reason: "present on admission; no hospital antidiabetic administered"

Example C — "Patient on glargine. Lowest glucose 44 mg/dL, treated with juice."
  -> in_denominator: true
  -> meets_numerator: false (44 is not below 40)

Example D — "Last insulin dose 11/03. Glucose 35 mg/dL on 11/06."
  -> in_denominator: true
  -> meets_numerator: false (low glucose is more than 24 hours after the med)
</worked_examples>

Work through the note step by step internally, then respond with ONLY a JSON object,
no markdown fences and no preamble:
{{"in_denominator": bool, "lowest_glucose_mg_dl": number or null,
"antidiabetic_given": bool, "meets_numerator": bool,
"exclusion_reason": string or null, "evidence_quote": string}}

evidence_quote must be copied verbatim from the note.

NOTE:
{note}"""


def build_prompt(version, note_text):
    if version == "v1":
        return PROMPT_V1.format(note=note_text)
    return PROMPT_V2.format(spec=SPEC, note=note_text)


def parse_json(raw):
    """LLMs sometimes wrap JSON in fences despite instructions. Strip and parse."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found")
    return json.loads(cleaned[start:end + 1])


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else "v1"
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    rows, failures = [], 0
    in_tok = out_tok = 0
    t_start = time.time()

    for path in sorted(NOTES_DIR.glob("*.txt")):
        note_id = path.stem
        note_text = path.read_text()

        t0 = time.time()
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": build_prompt(version, note_text)}],
        )
        latency = round(time.time() - t0, 2)
        in_tok += resp.usage.input_tokens
        out_tok += resp.usage.output_tokens

        raw = "".join(b.text for b in resp.content if b.type == "text")
        try:
            data = parse_json(raw)
            parse_ok = True
        except Exception as e:
            print(f"  !! {note_id} parse failure: {e}")
            data = {f: None for f in FIELDS}
            parse_ok = False
            failures += 1

        row = {"note_id": note_id, "parse_ok": parse_ok, "latency_s": latency}
        row.update({f: data.get(f) for f in FIELDS})
        rows.append(row)
        print(f"  {note_id}  denom={row['in_denominator']}  num={row['meets_numerator']}  ({latency}s)")

    out_path = OUT_DIR / f"predictions_{version}.csv"
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["note_id", "parse_ok", "latency_s"] + FIELDS)
        w.writeheader()
        w.writerows(rows)

    # Sonnet pricing: $3 per million input tokens, $15 per million output
    cost = in_tok / 1e6 * 3 + out_tok / 1e6 * 15
    elapsed = round(time.time() - t_start, 1)

    print(f"\n{'='*52}")
    print(f"version         {version}")
    print(f"notes           {len(rows)}")
    print(f"parse failures  {failures}")
    print(f"tokens          {in_tok} in / {out_tok} out")
    print(f"cost            ${cost:.4f}  (${cost/len(rows)*1000:.2f} per 1,000 charts)")
    print(f"wall time       {elapsed}s")
    print(f"saved to        {out_path}")


if __name__ == "__main__":
    main()
