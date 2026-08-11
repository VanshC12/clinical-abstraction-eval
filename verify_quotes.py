"""
Day 2 — Evidence grounding check.

The model returns an `evidence_quote` field claiming to be verbatim text from
the note. This script checks whether that text actually appears in the note.

A quote that doesn't exist in the source is a fabrication. A model can produce
the correct final answer while citing evidence it invented — which means the
answer was not actually derived from the document.

Usage:
    python verify_quotes.py v1
    python verify_quotes.py v1 v2

Writes output/grounding_<version>.csv
"""

import sys, csv, re, pathlib, difflib

NOTES_DIR = pathlib.Path("notes")
OUT_DIR = pathlib.Path("output")

# A quote scoring at or above this against the best-matching window in the
# note is treated as a real quote with minor transcription drift.
NEAR_MATCH_THRESHOLD = 0.85


def normalize(text):
    """Collapse whitespace, lowercase, strip punctuation that models drift on."""
    text = text.lower()
    text = text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"[^\w\s.<>/-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def best_window_ratio(quote, note):
    """
    Slide a window the length of the quote across the note and return the
    similarity of the closest match. Catches quotes that are nearly right
    but have a dropped word or altered punctuation.
    """
    q, n = normalize(quote), normalize(note)
    if not q:
        return 0.0
    if q in n:
        return 1.0

    qlen = len(q)
    if qlen > len(n):
        return difflib.SequenceMatcher(None, q, n).ratio()

    best = 0.0
    # Step by a fraction of the quote length; fine enough to catch matches,
    # coarse enough to stay fast on 40 notes.
    step = max(1, qlen // 8)
    for i in range(0, len(n) - qlen + 1, step):
        window = n[i:i + qlen]
        ratio = difflib.SequenceMatcher(None, q, window).ratio()
        if ratio > best:
            best = ratio
            if best >= 0.995:
                break
    return best


def split_fragments(quote):
    """Models often join non-contiguous text with an ellipsis. Split on it."""
    parts = re.split(r"\s*(?:\.\.\.|\u2026)\s*", quote)
    return [p.strip() for p in parts if p.strip()]


def classify(ratio, quote, note):
    if not quote or not quote.strip():
        return "EMPTY", ratio
    if ratio >= 0.995:
        return "EXACT", ratio
    if ratio >= NEAR_MATCH_THRESHOLD:
        return "NEAR", ratio

    # Not contiguous. Check whether it is a splice of genuine fragments.
    frags = split_fragments(quote)
    if len(frags) > 1:
        frag_ratios = [best_window_ratio(f, note) for f in frags]
        if all(r >= NEAR_MATCH_THRESHOLD for r in frag_ratios):
            return "SPLICED", min(frag_ratios)

    return "FABRICATED", ratio


def check(version):
    pred_path = OUT_DIR / f"predictions_{version}.csv"
    if not pred_path.exists():
        print(f"missing {pred_path} — run extract.py {version} first")
        return None

    rows = []
    with open(pred_path) as f:
        for r in csv.DictReader(f):
            note_id = r["note_id"]
            quote = (r.get("evidence_quote") or "").strip()
            note_file = NOTES_DIR / f"{note_id}.txt"
            if not note_file.exists():
                continue
            note = note_file.read_text()

            ratio = best_window_ratio(quote, note)
            verdict, ratio = classify(ratio, quote, note)

            rows.append({
                "note_id": note_id,
                "verdict": verdict,
                "similarity": round(ratio, 3),
                "quote_len": len(quote),
                "evidence_quote": quote[:200],
            })

    counts = {v: sum(1 for r in rows if r["verdict"] == v)
              for v in ["EXACT", "NEAR", "SPLICED", "FABRICATED", "EMPTY"]}
    n = len(rows)
    grounded = counts["EXACT"] + counts["NEAR"]
    traceable = grounded + counts["SPLICED"]

    print(f"\n{'=' * 54}")
    print(f"  {version.upper()}  evidence grounding   n = {n}")
    print("=" * 54)
    print(f"  EXACT       {counts['EXACT']:>3}   quote found verbatim")
    print(f"  NEAR        {counts['NEAR']:>3}   minor drift, still traceable")
    print(f"  SPLICED     {counts['SPLICED']:>3}   real fragments joined by an ellipsis")
    print(f"  FABRICATED  {counts['FABRICATED']:>3}   no matching text in the note")
    print(f"  EMPTY       {counts['EMPTY']:>3}   no quote returned")
    if n:
        print(f"\n  verbatim grounding   {grounded / n:.1%}   (EXACT + NEAR)")
        print(f"  traceable to source  {traceable / n:.1%}   (+ SPLICED)")

    bad = [r for r in rows if r["verdict"] in ("FABRICATED", "EMPTY")]
    if bad:
        print(f"\n  ungrounded notes:")
        for r in bad:
            print(f"    {r['note_id']}  sim={r['similarity']}  \"{r['evidence_quote'][:70]}\"")

    out_path = OUT_DIR / f"grounding_{version}.csv"
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["note_id", "verdict", "similarity",
                                          "quote_len", "evidence_quote"])
        w.writeheader()
        w.writerows(rows)
    print(f"\n  saved to {out_path}")

    return (grounded / n, traceable / n) if n else (0.0, 0.0)


def main():
    versions = sys.argv[1:] or ["v1"]
    results = {v: check(v) for v in versions}

    if len(versions) == 2 and all(r is not None for r in results.values()):
        a, b = versions
        print(f"\n{'=' * 54}")
        print(f"  verbatim grounding:  {a} {results[a][0]:.1%}  ->  {b} {results[b][0]:.1%}")
        print(f"  traceable to source: {a} {results[a][1]:.1%}  ->  {b} {results[b][1]:.1%}")
        print("=" * 54)


if __name__ == "__main__":
    main()
