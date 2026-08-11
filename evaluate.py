"""
Scores model predictions against your hand-labeled gold standard.

Usage:
    python evaluate.py v1
    python evaluate.py v1 v2      # compare two prompt versions
"""

import sys, csv, pathlib

GOLD = pathlib.Path("gold_labels.csv")
OUT_DIR = pathlib.Path("output")


def to_bool(v):
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "y"):
        return True
    if s in ("false", "0", "no", "n"):
        return False
    return None


def load(path, cols):
    with open(path) as f:
        return {r["note_id"]: {c: to_bool(r.get(c)) for c in cols}
                for r in csv.DictReader(f)}


def confusion(gold, pred, field):
    tp = fp = fn = tn = 0
    disagreements = []
    for nid, g in gold.items():
        if nid not in pred:
            continue
        gv, pv = g[field], pred[nid][field]
        if gv is None:
            continue
        if gv and pv:
            tp += 1
        elif not gv and pv:
            fp += 1
            disagreements.append((nid, "FALSE POSITIVE"))
        elif gv and not pv:
            fn += 1
            disagreements.append((nid, "FALSE NEGATIVE"))
        else:
            tn += 1
    return tp, fp, fn, tn, disagreements


def metrics(tp, fp, fn, tn):
    n = tp + fp + fn + tn
    acc = (tp + tn) / n if n else 0
    prec = tp / (tp + fp) if (tp + fp) else 0
    rec = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
    return acc, prec, rec, f1


def report(version, gold):
    path = OUT_DIR / f"predictions_{version}.csv"
    pred = load(path, ["in_denominator", "meets_numerator"])

    print(f"\n{'='*58}")
    print(f"  {version.upper()}   n = {len(pred)}")
    print("=" * 58)

    results = {}
    for field in ["in_denominator", "meets_numerator"]:
        tp, fp, fn, tn, dis = confusion(gold, pred, field)
        acc, prec, rec, f1 = metrics(tp, fp, fn, tn)
        results[field] = (acc, prec, rec, f1)

        print(f"\n  {field}")
        print(f"    accuracy   {acc:.1%}")
        print(f"    precision  {prec:.1%}")
        print(f"    recall     {rec:.1%}")
        print(f"    F1         {f1:.1%}")
        print(f"    TP {tp}   FP {fp}   FN {fn}   TN {tn}")
        if dis:
            print(f"    misses: " + ", ".join(f"{n}({k[0]}{k[6]})" for n, k in dis))

    return results


def main():
    if not GOLD.exists():
        print("gold_labels.csv not found.")
        print("Copy gold_labels_TEMPLATE.csv to gold_labels.csv and fill it in first.")
        sys.exit(1)

    gold = load(GOLD, ["in_denominator", "meets_numerator"])
    labeled = sum(1 for g in gold.values() if g["meets_numerator"] is not None)
    print(f"gold set: {labeled}/{len(gold)} notes labeled")

    versions = sys.argv[1:] or ["v1"]
    all_results = {v: report(v, gold) for v in versions}

    if len(versions) == 2:
        a, b = versions
        print(f"\n{'='*58}")
        print(f"  {a} -> {b}")
        print("=" * 58)
        for field in ["in_denominator", "meets_numerator"]:
            for i, name in enumerate(["accuracy", "precision", "recall", "F1"]):
                x, y = all_results[a][field][i], all_results[b][field][i]
                arrow = "+" if y > x else ("-" if y < x else " ")
                print(f"  {field:<16} {name:<10} {x:6.1%} -> {y:6.1%}  {arrow}{abs(y-x):.1%}")


if __name__ == "__main__":
    main()
