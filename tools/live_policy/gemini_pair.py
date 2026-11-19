"""Exploratory: one Gemini model minus another on the rows both ran (PREREGISTRATION_GEMINI.md, Note 3, E2).

Both models ran the author's own loop, so this contrast is of the model alone. It is computed after
both results were seen and decides nothing. It reads the two records files the wrapper wrote, takes a
member's score, then the row's mean over members that have one, then the cluster's mean over its rows
that both models scored, and tests the per-cluster differences with the frozen exact sign-flip test
(two-sided) and its 95% interval.

    .venv_offline/bin/python tools/live_policy/gemini_pair.py A_records.json B_records.json OUT.md

Either side may be several records files joined by commas (one model scored in two runs on different
rows, for example round 1 and then rounds 3 and 2); a row may appear in only one of them.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from semantic import stats  # noqa: E402

LEVELS = ("L1", "L2", "L3")


def row_scores(paths):
    """{row_id: (cluster, {level: mean over members with a score, or None})}, from one records file or
    from several joined by commas. A row found in two files is an error."""
    out = {}
    for path in str(paths).split(","):
        for rec in json.load(open(path))["records"]:
            per = {}
            for lv in LEVELS:
                vals = [m[lv] for m in rec["model"].values() if isinstance(m, dict) and m.get(lv) is not None]
                per[lv] = sum(vals) / len(vals) if vals else None
            if all(v is None for v in per.values()):
                continue                    # the wrapper lists every frame row; one a run did not hold has no score
            if rec["row_id"] in out:
                raise ValueError("row %s has scores in two of the files %s" % (rec["row_id"], paths))
            out[rec["row_id"]] = (rec["cluster"], per)
    return out


def contrast(a, b, level):
    """Per-cluster means of A and of B on the rows both scored at this level, and their differences."""
    by = {}
    for row, (cluster, sa) in a.items():
        if row in b and sa[level] is not None and b[row][1][level] is not None:
            by.setdefault(cluster, []).append((sa[level], b[row][1][level]))
    clusters = sorted(by)
    ma = [sum(x for x, _ in by[c]) / len(by[c]) for c in clusters]
    mb = [sum(y for _, y in by[c]) / len(by[c]) for c in clusters]
    d = [x - y for x, y in zip(ma, mb)]
    res = {"clusters": len(clusters), "rows": sum(len(v) for v in by.values()),
           "a": sum(ma) / len(ma) if ma else None, "b": sum(mb) / len(mb) if mb else None,
           "diff": sum(d) / len(d) if d else None, "p_two_sided": None, "interval": None}
    if len(d) >= 2 and any(abs(x) > 0 for x in d):
        res["p_two_sided"] = float(stats.sign_flip_test(d, alternative="two-sided").p)
        lo, hi = stats.sign_flip_ci(d, level=0.95, alternative="two-sided")[:2]
        res["interval"] = [float(lo), float(hi)]
    return res


def main(argv):
    pa, pb, out = argv
    a, b = row_scores(pa), row_scores(pb)
    na, nb = (Path(str(x).split(",")[0]).stem.replace("records_", "") for x in (pa, pb))
    table = {lv: contrast(a, b, lv) for lv in LEVELS}
    pct = lambda x: "n/a" if x is None else "%.1f%%" % (100 * x)
    lines = ["> **Exploratory.** Computed after both results were seen. No verdict rests on it. See `PREREGISTRATION_GEMINI.md`, Note 3.",
             "", "# %s minus %s, on the rows both ran" % (na, nb), "",
             "Both ran the author's own loop. Exact sign-flip test over clusters, two-sided; 95% interval from the same test.", "",
             "| level | clusters | rows | %s | %s | diff (pts) | p (two-sided) | 95%% interval (pts) |" % (na, nb), "|---|---|---|---|---|---|---|---|"]
    for lv in LEVELS:
        t = table[lv]
        iv = "n/a" if t["interval"] is None else "[%+.1f, %+.1f]" % (100 * t["interval"][0], 100 * t["interval"][1])
        p = "n/a" if t["p_two_sided"] is None else "%.4f" % t["p_two_sided"]
        d = "n/a" if t["diff"] is None else "%+.1f" % (100 * t["diff"])
        lines.append("| %s | %d | %d | %s | %s | %s | %s | %s |" % (lv, t["clusters"], t["rows"], pct(t["a"]), pct(t["b"]), d, p, iv))
    Path(out).write_text("\n".join(lines) + "\n")
    Path(out).with_suffix(".json").write_text(json.dumps({"a": na, "b": nb, "levels": table}, indent=1) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1:])
