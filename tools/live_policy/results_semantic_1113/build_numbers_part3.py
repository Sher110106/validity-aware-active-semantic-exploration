#!/usr/bin/env python3
"""Rebuild numbers_part3.csv from the result files and check RESULTS.md against them.

Run from anywhere:  .venv_offline/bin/python tools/live_policy/results_semantic_1113/build_numbers_part3.py

What it does
  1. Reads the result files (JSON, the replay ledgers and records, the parsed graphs, a few lines of the frozen
     text files and `git log`), and registers every number that RESULTS.md shows, with the file and the path it
     came from.
  2. Builds each table of RESULTS.md from those numbers and compares it, text for text, with the block between
     `<!-- table:NAME -->` and `<!-- /table:NAME -->` in RESULTS.md. A cell that no longer matches fails the run.
  3. Checks each number in the prose. A prose number is written as `-5.8<!--n:KEY-->`: the text before the tag
     must equal the number the files give for KEY. A tag with an unknown key fails the run.
  4. Writes numbers_part3.csv (one row per number) when all checks pass.

Options
  --fill       rewrite the table blocks of RESULTS.md from the files (then run again, without it, to check)
  --audit      list numerals in RESULTS.md that carry no tag and sit in no table
  --no-replay  skip the numbers that need the replay folders outside this repository
  --no-git     skip the numbers that need `git log`

Nothing here computes a new statistic. The only arithmetic is the mean of a cluster list, a median, a sum, a count
and a half-width (upper minus lower, over two), each named in the row's `path` column.
"""
from __future__ import annotations

import argparse
import ast
import collections
import csv
import json
import math
import re
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LP = HERE.parent                      # tools/live_policy
ROOT = HERE.parents[2]                # the repository root (project/)
CVP = ROOT.parent                     # holds replay_outputs/ and replay_inputs/
RESULTS_MD = HERE / "RESULTS.md"
CSV_OUT = HERE / "numbers_part3.csv"

OPUS, HAIKU = "claude-opus-5-5", "claude-haiku-5-5"
SEMDIR = "tools/live_policy/results_semantic_1113/"
CL, EX, NH = SEMDIR + "claude/", SEMDIR + "exploratory/", SEMDIR + "nohint_haiku/"
M2DIR = "tools/live_policy/results_m2_1113/"
REPLAY = CVP / "replay_outputs"
INPUTS = CVP / "replay_inputs" / "frame_inputs"

NAMES = {"opus": "Opus", "haiku": "Haiku", "deepseek": "DeepSeek (exploratory)", "gemini": "Gemini (exploratory)",
         "placebo": "Placebo (exploratory)"}
MODEL_ID = {"opus": OPUS, "haiku": HAIKU, "deepseek": "deepseek", "gemini": "gemini", "placebo": "placebo"}
MODEL_FILE = {"opus": CL + "results.json", "haiku": CL + "results.json",
              "deepseek": EX + "results.json", "gemini": EX + "results.json", "placebo": EX + "results.json"}
RECORD_FILE = {"opus": CL + f"records_{OPUS}.json", "haiku": CL + f"records_{HAIKU}.json",
               "deepseek": EX + "records_deepseek.json", "gemini": EX + "records_gemini.json",
               "placebo": EX + "records_placebo.json"}
VALID_FILE = {"opus": CL + "validity.json", "haiku": CL + "validity.json", "deepseek": EX + "validity.json",
              "gemini": EX + "validity.json", "placebo": EX + "validity.json"}
ERR_FILE = {"opus": CL + f"error_sample_{OPUS}.json", "haiku": CL + f"error_sample_{HAIKU}.json",
            "deepseek": EX + "error_sample_deepseek.json", "gemini": EX + "error_sample_gemini.json",
            "placebo": EX + "error_sample_placebo.json"}
ROOM_FILE = {"opus": CL + "room_test.json", "haiku": CL + "room_test.json", "deepseek": EX + "room_test.json",
             "gemini": EX + "room_test.json", "placebo": EX + "room_test.json"}


class Fail(Exception):
    pass


# ------------------------------------------------------------------------------------------ files

_cache: dict = {}


def abspath(rel: str) -> Path:
    return (ROOT / rel).resolve()


def J(rel: str):
    if rel not in _cache:
        p = abspath(rel)
        if not p.exists():
            raise Fail(f"missing file: {rel}")
        _cache[rel] = json.loads(p.read_text())
    return _cache[rel]


def T(rel: str) -> str:
    if rel not in _cache:
        p = abspath(rel)
        if not p.exists():
            raise Fail(f"missing file: {rel}")
        _cache[rel] = p.read_text()
    return _cache[rel]


def at(obj, *keys):
    for k in keys:
        obj = obj[k]
    return obj


def jp(*keys) -> str:
    return "".join(f"[{k}]" if isinstance(k, int) else "/" + str(k) for k in keys)


def relsrc(p: Path) -> str:
    p = p.resolve()
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return "../" + str(p.relative_to(CVP))


# ------------------------------------------------------------------------------------------ formats

def _clean(s: str) -> str:
    return "0" + s[1:] if False else s


def f_pts(v, dp=1, sign=False):
    x = float(v) * 100.0
    s = f"{x:+.{dp}f}" if sign else f"{x:.{dp}f}"
    if float(s) == 0:
        s = s.lstrip("+-")
    return s


def f_pct(v, dp=1):
    return f_pts(v, dp) + "%"


def f_p(v):
    if v is None:
        return "n/a"
    if v < 0.0005 and v != 0:
        return "<0.001"
    return f"{v:.3f}"


def f_rho(v, sign=True):
    s = f"{v:+.3f}" if sign else f"{v:.3f}"
    return s


def f_int(v):
    return f"{int(round(v))}"


def f_num(dp):
    return lambda v: f"{v:.{dp}f}"


def f_usd(v, dp=2):
    return f"${v:.{dp}f}"


def f_str(v):
    return str(v)


# ------------------------------------------------------------------------------------------ registry

class Registry:
    def __init__(self):
        self.rows: dict = {}
        self.tables: dict = {}
        self.skipped: set = set()
        self.table_keys: set = set()

    def add(self, key, value, shown, unit, source, path, where=None):
        if key in self.rows:
            r = self.rows[key]
            if r["shown"] != shown:
                raise Fail(f"key {key} registered twice with different numbers: {r['shown']} / {shown}")
            if where and where not in r["where"]:
                r["where"].append(where)
            return shown
        self.rows[key] = {"key": key, "value": value, "shown": shown, "unit": unit, "source": source,
                          "path": path, "where": [where] if where else [], "prose": []}
        if where:
            self.table_keys.add(key)
        return shown


R = Registry()


def reg(key, value, fmt, unit, source, path, where=None):
    return R.add(key, value, fmt(value) if callable(fmt) else fmt, unit, source, path, where)


def regj(key, src, keys, fmt, unit, where=None):
    """Register a value read straight from a JSON file."""
    return reg(key, at(J(src), *keys), fmt, unit, src, jp(*keys), where)


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return out


# ------------------------------------------------------------------------------------------ cell helpers

class Tab:
    """Builds one table; remembers the table name for the `supports` text."""

    def __init__(self, name, headers):
        self.name, self.headers, self.rows = name, headers, []

    def row(self, label, cells):
        self.rows.append([label] + cells)

    def where(self, row, col):
        return f"table {self.name}: row '{row}', column '{col}'"

    def done(self):
        R.tables[self.name] = md_table(self.headers, self.rows)


def ci_cell(tab, rowlabel, col, key, src, keys, unit="points", sign=True, dp=1):
    """[lo, hi] in points, or 'unbounded' when the file holds an infinite end."""
    lo, hi = at(J(src), *keys)
    w = tab.where(rowlabel, col)
    if isinstance(lo, str) or isinstance(hi, str):
        reg(key + "_ci", "unbounded", f_str, "text", src, jp(*keys), w)
        return "unbounded"
    a = reg(key + "_lo", lo, lambda v: f_pts(v, dp, sign), unit, src, jp(*keys, 0), w)
    b = reg(key + "_hi", hi, lambda v: f_pts(v, dp, sign), unit, src, jp(*keys, 1), w)
    return f"[{a}, {b}]"


def mean_clusters(src, keys):
    d = at(J(src), *keys)
    return statistics.fmean(d.values()), len(d)


# ------------------------------------------------------------------------------------------ level nodes

def lkeys(m, L, view=None):
    base = ("models", MODEL_ID[m])
    if view is None:
        return base + ("analysis", "levels", L)
    return base + ("secondary", view, "levels", L)


def score_cell(key, m, L, view=None, tab=None, row=None, col=None, dp=1):
    src = MODEL_FILE[m]
    v, n = mean_clusters(src, lkeys(m, L, view) + ("model_cluster_scores",))
    path = "mean of " + jp(*lkeys(m, L, view), "model_cluster_scores") + "/*"
    w = tab.where(row, col) if tab else None
    return R.add(key, v, f_pct(v, dp), "fraction of hits", src, path, w)


def diff_p_cell(tab, rowlabel, col, key, m, L, comp, view=None, with_p=True):
    src = MODEL_FILE[m]
    node = at(J(src), *lkeys(m, L, view), "comparators", comp)
    w = tab.where(rowlabel, col)
    if node["mean_diff"] is None:
        return "n/a"
    base = lkeys(m, L, view) + ("comparators", comp)
    d = reg(key + "_diff", node["mean_diff"], lambda v: f_pts(v, 1, True), "points", src, jp(*base, "mean_diff"), w)
    if not with_p:
        return d
    p = reg(key + "_p", node["p"], f_p, "p", src, jp(*base, "p"), w)
    return f"{d} (p {p})"


def diff_ci_cell(tab, rowlabel, col, key, m, L, comp, view=None):
    src = MODEL_FILE[m]
    node = at(J(src), *lkeys(m, L, view), "comparators", comp)
    if node["mean_diff"] is None:
        return "n/a"
    base = lkeys(m, L, view) + ("comparators", comp)
    d = reg(key + "_diff", node["mean_diff"], lambda v: f_pts(v, 1, True), "points", src, jp(*base, "mean_diff"),
            tab.where(rowlabel, col))
    c = ci_cell(tab, rowlabel, col, key, src, base + ("ci",))
    return f"{d} {c}"


# ------------------------------------------------------------------------------------------ section 3 and 6 tables

def hyp_keys(m, L):
    if m in ("opus", "haiku"):
        return ("family", "hypotheses", f"{MODEL_ID[m]}|{L}")
    return ("models", MODEL_ID[m], "exploratory_family", "hypotheses", f"{MODEL_ID[m]}|{L}")


def gate_keys(m, L):
    if m in ("opus", "haiku"):
        return ("family", "wrong_house_gate", f"{MODEL_ID[m]}|{L}")
    return ("models", MODEL_ID[m], "exploratory_family", "wrong_house_gate", f"{MODEL_ID[m]}|{L}")


def conf_tables(prefix, models, t12, t3, clusters):
    h12 = ["Hypothesis", "Rows"] + (["Clusters"] if clusters else []) + [
        "Score", "Placebo's own score", "Diff vs B3 (p)", "Diff vs B1 placebo (p)", "95% interval vs B3",
        "Margin (points)", "Largest p", "Holm p", "Verdict"]
    h3 = ["Hypothesis", "Rows"] + (["Clusters"] if clusters else []) + [
        "Score", "Placebo's own score", "Diff vs B5 (p)", "Diff vs D (p)", "Diff vs B3L (p)", "95% interval vs D",
        "Margin (points)", "Largest p", "Holm p", "Verdict"]
    A, B = Tab(t12, h12), Tab(t3, h3)
    for L, tab in (("L1", A), ("L2", A), ("L3", B)):
        for m in models:
            label = f"{NAMES[m]} {L}"
            src = MODEL_FILE[m]
            hk = hyp_keys(m, L)
            hyp = at(J(src), *hk)
            named = hyp["named"]
            node = at(J(src), *lkeys(m, L), "comparators", named)
            if node["ci"] is not None and not isinstance(node["ci"][1], str):
                if abs(node["ci"][1] - hyp["ci_upper_named"]) > 1e-12:
                    raise Fail(f"{label}: interval upper end differs from the hypothesis record")
            k = f"{prefix}{m}_{L}"
            cells = [reg(k + "_rows", node["n_rows"], f_int, "rows", src,
                         jp(*lkeys(m, L), "comparators", named, "n_rows"), tab.where(label, "Rows"))]
            if clusters:
                cells.append(reg(k + "_clusters", node["n_clusters"], f_int, "clusters", src,
                                 jp(*lkeys(m, L), "comparators", named, "n_clusters"),
                                 tab.where(label, "Clusters")))
            cells.append(score_cell(k + "_score", m, L, None, tab, label, "Score"))
            cells.append(score_cell(f"placebo_prim_{L}_score", "placebo", L, None, tab, label, "Placebo's own score"))
            if L in ("L1", "L2"):
                cells.append(diff_p_cell(tab, label, "Diff vs B3 (p)", k + "_B3", m, L, "B3"))
                cells.append(diff_p_cell(tab, label, "Diff vs B1 placebo (p)", k + "_B1", m, L, "B1"))
                cells.append(ci_cell(tab, label, "95% interval vs B3", k + "_B3ci", src,
                                     lkeys(m, L) + ("comparators", "B3", "ci")))
            else:
                cells.append(diff_p_cell(tab, label, "Diff vs B5 (p)", k + "_B5", m, L, "B5"))
                cells.append(diff_p_cell(tab, label, "Diff vs D (p)", k + "_D", m, L, "D"))
                cells.append(diff_p_cell(tab, label, "Diff vs B3L (p)", k + "_B3L", m, L, "B3L"))
                cells.append(ci_cell(tab, label, "95% interval vs D", k + "_Dci", src,
                                     lkeys(m, L) + ("comparators", "D", "ci")))
            cells.append(reg(k + "_margin", hyp["delta"], lambda v: f_pts(v, 0), "points", src,
                             jp(*hk, "delta"), tab.where(label, "Margin (points)")))
            cells.append(reg(k + "_pmax", hyp["p"], f_p, "p", src, jp(*hk, "p"), tab.where(label, "Largest p")))
            cells.append(reg(k + "_holm", hyp["p_holm"], f_p, "p", src, jp(*hk, "p_holm"), tab.where(label, "Holm p")))
            cells.append(reg(k + "_verdict", hyp["verdict"], f_str, "verdict", src, jp(*hk, "verdict"),
                             tab.where(label, "Verdict")))
            tab.row(label, cells)
    A.done()
    B.done()


def gate_table(name, models):
    tab = Tab(name, ["Row", "Mean difference (points)", "Pairs", "p", "Passes"])
    for L in ("L1", "L2"):
        for m in models:
            label = f"{NAMES[m]} {L}"
            src = MODEL_FILE[m]
            gk = gate_keys(m, L)
            g = at(J(src), *gk)
            k = f"gate_{m}_{L}"
            if g["n_pairs"] == 0:
                cells = ["none", reg(k + "_pairs", 0, f_int, "pairs", src, jp(*gk, "n_pairs"),
                                     tab.where(label, "Pairs")), "n/a", "no"]
            else:
                cells = [reg(k + "_diff", g["mean_diff"], lambda v: f_pts(v, 1, True), "points", src,
                             jp(*gk, "mean_diff"), tab.where(label, "Mean difference (points)")),
                         reg(k + "_pairs", g["n_pairs"], f_int, "pairs", src, jp(*gk, "n_pairs"),
                             tab.where(label, "Pairs")),
                         reg(k + "_p", g["p"], f_p, "p", src, jp(*gk, "p"), tab.where(label, "p")),
                         reg(k + "_pass", g["pass"], lambda v: "yes" if v else "no", "bool", src, jp(*gk, "pass"),
                             tab.where(label, "Passes"))]
            tab.row(label, cells)
    tab.done()


def b2_table():
    tab = Tab("b2", ["Row", "Rows", "Diff vs B2 (p)", "Interval"])
    for L in ("L1", "L2"):
        for m in ("opus", "haiku", "deepseek"):
            label = f"{NAMES[m]} {L}"
            src = MODEL_FILE[m]
            node = at(J(src), *lkeys(m, L), "comparators", "B2")
            k = f"b2_{m}_{L}"
            tab.row(label, [
                reg(k + "_rows", node["n_rows"], f_int, "rows", src, jp(*lkeys(m, L), "comparators", "B2", "n_rows"),
                    tab.where(label, "Rows")),
                diff_p_cell(tab, label, "Diff vs B2 (p)", k, m, L, "B2"),
                ci_cell(tab, label, "Interval", k + "ci", src, lkeys(m, L) + ("comparators", "B2", "ci"))])
    tab.done()


SUP = SEMDIR + "supplement/supplement.json"
SUP_MODELS = (("opus", OPUS), ("haiku", HAIKU), ("deepseek", "deepseek"), ("gemini", "gemini"), ("placebo", "placebo"))


def supplement_tables():
    if not abspath(SUP).exists():
        raise Fail(f"missing {SUP}: run supplement/supplement.py first")
    tab = Tab("sup_labels", ["Model", "Members", "New objects", "Labelled other", "Labelled structure",
                             "Share other or structure", "With the flag", "Without the flag", "New rooms",
                             "Untyped", "Share untyped", "Typed dining (left out)"])
    for m, mid in SUP_MODELS:
        base = ("labels", mid)
        k = f"sup_{m}"
        w = lambda col: tab.where(NAMES[m], col)   # noqa: E731
        d = at(J(SUP), *base)
        share_o = (d["objects_other"] + d["objects_structure"]) / d["new_objects"]
        share_u = d["rooms_untyped"] / d["new_rooms"] if d["new_rooms"] else 0.0
        tab.row(NAMES[m], [
            regj(k + "_members", SUP, base + ("members",), f_int, "members", w("Members")),
            regj(k + "_objects", SUP, base + ("new_objects",), f_int, "objects", w("New objects")),
            regj(k + "_other", SUP, base + ("objects_other",), f_int, "objects", w("Labelled other")),
            regj(k + "_structure", SUP, base + ("objects_structure",), f_int, "objects", w("Labelled structure")),
            reg(k + "_share_os", share_o, f_pct, "share", SUP,
                "(objects_other + objects_structure) / new_objects of " + jp(*base), w("Share other or structure")),
            regj(k + "_flag", SUP, base + ("objects_flagged",), f_int, "objects", w("With the flag")),
            regj(k + "_noflag", SUP, base + ("objects_unflagged",), f_int, "objects", w("Without the flag")),
            regj(k + "_rooms", SUP, base + ("new_rooms",), f_int, "rooms", w("New rooms")),
            regj(k + "_untyped", SUP, base + ("rooms_untyped",), f_int, "rooms", w("Untyped")),
            reg(k + "_share_u", share_u, f_pct, "share", SUP, "rooms_untyped / new_rooms of " + jp(*base), w("Share untyped")),
            regj(k + "_dining", SUP, base + ("rooms_dining",), f_int, "rooms", w("Typed dining (left out)"))])
    tab.done()
    bt = Tab("sup_balance", ["Model", "Members", "Dropped", "Drop rate", "Ledger lines not ok", "Member records with an error"])
    for m, mid in SUP_MODELS[:2]:
        base = ("balance", mid)
        k = f"bal_{m}"
        d = at(J(SUP), *base)
        w = lambda col: bt.where(NAMES[m], col)   # noqa: E731
        bt.row(NAMES[m], [
            regj(k + "_members", SUP, base + ("members",), f_int, "members", w("Members")),
            regj(k + "_dropped", SUP, base + ("members_dropped",), f_int, "members", w("Dropped")),
            reg(k + "_rate", d["members_dropped"] / d["members"], lambda v: f_pct(v, 1), "share", SUP,
                "members_dropped / members of " + jp(*base), w("Drop rate")),
            regj(k + "_ledger_bad", SUP, base + ("ledger_lines_not_ok",), f_int, "lines", w("Ledger lines not ok")),
            regj(k + "_rec_err", SUP, base + ("member_records_with_error",), f_int, "records", w("Member records with an error"))])
    bt.done()
    # prose numbers
    lo = ("looser",)
    regj("loose_rows", SUP, lo + ("rows_where_truth_sets_differ",), f_int, "rows")
    regj("loose_rows_types", SUP, lo + ("rows_where_types_differ",), f_int, "rows")
    regj("loose_rows_classes", SUP, lo + ("rows_where_classes_differ",), f_int, "rows")
    reg("loose_label", ", ".join(at(J(SUP), *lo, "labels_that_differ")), f_str, "label", SUP, jp(*lo, "labels_that_differ"))
    for m, mid in SUP_MODELS:
        if m in ("gemini", "placebo"):
            continue
        reg(f"loose_claims_{m}", at(J(SUP), *lo, "members_with_a_claim_of_a_differing_label", mid), f_int, "members", SUP,
            jp(*lo, "members_with_a_claim_of_a_differing_label", mid))
        reg(f"loose_members_in_rows_{m}", sum(x["proposed"][mid]["members"] for x in at(J(SUP), *lo, "rows")), f_int,
            "members", SUP, "sum over looser/rows[*] of proposed/" + mid + "/members")
    for m, mid in SUP_MODELS[:3]:
        base = ("one_claim_vs_plain_l1", mid)
        regj(f"oneclaim_diff_{m}", SUP, base + ("members_where_one_claim_score_differs",), f_int, "members")
        regj(f"oneclaim_n_{m}", SUP, base + ("members_with_l1_score",), f_int, "members")
    regj("bal_ledger_lines_opus", SUP, ("balance", OPUS, "ledger_lines"), f_int, "lines")
    regj("bal_ledger_lines_haiku", SUP, ("balance", HAIKU, "ledger_lines"), f_int, "lines")
    regj("bal_records_opus", SUP, ("balance", OPUS, "member_records"), f_int, "records")
    regj("bal_records_haiku", SUP, ("balance", HAIKU, "member_records"), f_int, "records")


def mdd_table():
    src = EX + "mdd_table.json"
    regj("mdd_power", src, ("power",), lambda v: f_pct(v, 0), "power")
    tab = Tab("mdd", ["Level", "Contrast", "Clusters", "SD of the contrast (points)", "Detectable difference (points)",
                      "Margin (points)", "Interval half-width (points)"])
    for L in ("L1", "L2", "L3"):
        n = at(J(src), "levels", L)
        k = f"mdd_{L}"
        cells = [at(J(src), "levels", L, "contrast"),
                 regj(k + "_n", src, ("levels", L, "n_clusters"), f_int, "clusters", tab.where(L, "Clusters")),
                 regj(k + "_sd", src, ("levels", L, "sd"), lambda v: f_pts(v, 1), "points",
                      tab.where(L, "SD of the contrast (points)")),
                 regj(k + "_mdd", src, ("levels", L, "mdd"), lambda v: f_pts(v, 1), "points",
                      tab.where(L, "Detectable difference (points)")),
                 regj(k + "_delta", src, ("levels", L, "delta"), lambda v: f_pts(v, 0), "points",
                      tab.where(L, "Margin (points)")),
                 regj(k + "_hw", src, ("levels", L, "half_width"), lambda v: f_pts(v, 1), "points",
                      tab.where(L, "Interval half-width (points)"))]
        tab.row(L, cells)
    tab.done()


# ------------------------------------------------------------------------------------------ records and counts

def records(m):
    return J(RECORD_FILE[m])["records"]


def claims_table():
    tab = Tab("claims", ["Model", "Members scored", "Rows behind the L1 contrasts", "L1 claims", "L2 claims", "L3 items"])
    for m in ("opus", "haiku", "deepseek", "gemini", "placebo"):
        src = RECORD_FILE[m]
        recs = records(m)
        mem = sum(len(r["model"]) for r in recs)
        rows1 = sum(1 for r in recs if r["possible"]["L1"] and any(x["L1"] is not None for x in r["model"].values()))
        sums = {lv: sum(x["counts"][f"{lv}_n"] for r in recs for x in r["model"].values()) for lv in ("l1", "l2", "l3")}
        k = f"claims_{m}"
        w = lambda c: tab.where(NAMES[m], c)   # noqa: E731
        tab.row(NAMES[m], [
            reg(k + "_members", mem, f_int, "members", src, "count of records[*]/model/*", w("Members scored")),
            reg(k + "_rows1", rows1, f_int, "rows", src, "count of records[*] with possible/L1 true and some model/*/L1 not null",
                w("Rows behind the L1 contrasts")),
            reg(k + "_l1", sums["l1"], f_int, "claims", src, "sum of records[*]/model/*/counts/l1_n", w("L1 claims")),
            reg(k + "_l2", sums["l2"], f_int, "claims", src, "sum of records[*]/model/*/counts/l2_n", w("L2 claims")),
            reg(k + "_l3", sums["l3"], f_int, "items", src, "sum of records[*]/model/*/counts/l3_n", w("L3 items"))])
    tab.done()


# ------------------------------------------------------------------------------------------ section 7 tables

def secondary_tables():
    """Secondary views of section 11 of the pre-registration."""
    models = ("opus", "haiku", "deepseek")
    views12 = [("Looser rule", "loose", ("L1", "L2")), ("Detector words only", "detector_vocab", ("L2",)),
               ("Without extended table", "synonym_primary_only", ("L2",))]
    A = Tab("sec_l1l2", ["Reading", "Score", "Diff vs B3 [interval]", "Diff vs B1 placebo [interval]"])
    for title, view, levels in views12:
        for m in models:
            for L in levels:
                label = f"{title}, {NAMES[m]} {L}"
                k = f"sec_{view}_{m}_{L}"
                A.row(label, [score_cell(k + "_score", m, L, view, A, label, "Score"),
                              diff_ci_cell(A, label, "Diff vs B3 [interval]", k + "_B3", m, L, "B3", view),
                              diff_ci_cell(A, label, "Diff vs B1 placebo [interval]", k + "_B1", m, L, "B1", view)])
    A.done()
    B = Tab("sec_l3", ["Reading", "Score", "Rows with no region (left out)", "Diff vs B5 [interval]",
                       "Diff vs D [interval]", "Diff vs B3L [interval]"])
    for title, view in (("Partly seen regions", "l3_partly_seen"), ("Detector words only", "detector_vocab"),
                        ("Without extended table", "synonym_primary_only")):
        for m in models:
            label = f"{title}, {NAMES[m]}"
            k = f"sec_{view}_{m}_L3"
            src = MODEL_FILE[m]
            B.row(label, [
                score_cell(k + "_score", m, "L3", view, B, label, "Score"),
                regj(k + "_left", src, lkeys(m, "L3", view) + ("n_rows_impossible",), f_int, "rows",
                     B.where(label, "Rows with no region (left out)")),
                diff_ci_cell(B, label, "Diff vs B5 [interval]", k + "_B5", m, "L3", "B5", view),
                diff_ci_cell(B, label, "Diff vs D [interval]", k + "_D", m, "L3", "D", view),
                diff_ci_cell(B, label, "Diff vs B3L [interval]", k + "_B3L", m, "L3", "B3L", view)])
    B.done()
    # secondary L3 clusters for the D contrast on partly seen regions (small n)
    C = Tab("sec_partly_n", ["Row", "Clusters vs B5", "Clusters vs D"])
    for m in models:
        label = NAMES[m]
        src = MODEL_FILE[m]
        k = f"sec_partly_{m}"
        base = lkeys(m, "L3", "l3_partly_seen") + ("comparators",)
        C.row(label, [regj(k + "_nB5", src, base + ("B5", "n_clusters"), f_int, "clusters",
                           C.where(label, "Clusters vs B5")),
                      regj(k + "_nD", src, base + ("D", "n_clusters"), f_int, "clusters",
                           C.where(label, "Clusters vs D"))])
    C.done()
    # the three forms of the prior
    P = Tab("sec_prior", ["Row", "B3 (registered)", "B3 with seen counts", "B3 with house size", "B3 with both"])
    for L in ("L1", "L2"):
        for m in models:
            label = f"{NAMES[m]} {L}"
            k = f"prior_{m}_{L}"
            P.row(label, [diff_ci_cell(P, label, "B3 (registered)", k + "_B3", m, L, "B3"),
                          diff_ci_cell(P, label, "B3 with seen counts", k + "_seen", m, L, "B3_seen"),
                          diff_ci_cell(P, label, "B3 with house size", k + "_size", m, L, "B3_size"),
                          diff_ci_cell(P, label, "B3 with both", k + "_both", m, L, "B3_seen_size")])
    P.done()


def extras_tables():
    models = ("opus", "haiku", "deepseek")
    groups = [("x_misc", "One claim, one region; rooms and objects apart",
               [("l1_matched", "L1, one claim to one region"), ("l3_rooms", "L3, rooms only"),
                ("l3_objects", "L3, objects only")]),
              ("x_multi", "Items that reach two regions",
               [("l3_multi", "Share reaching two or more regions"),
                ("l3_multi_unobs", "Share reaching two or more unobserved regions")]),
              ("x_l4", "L4",
               [("l4_0p5m", "Within 0.5 m"), ("l4_1p0m", "Within 1 m"), ("l4_2p0m", "Within 2 m"),
                ("l4_3p0m", "Within 3 m")])]
    for tname, _title, items in groups:
        tab = Tab(tname, ["Readout", "Model", "Model's share", "Placebo's share", "Diff vs placebo [interval]", "p"])
        for key, label in items:
            for m in models:
                src = MODEL_FILE[m]
                base = ("models", MODEL_ID[m], "extras", key)
                node = at(J(src), *base)
                rowlabel = f"{label}, {NAMES[m]}"
                k = f"extra_{key}_{m}"
                mv = statistics.fmean(node["model_clusters"].values())
                pv = statistics.fmean(node["placebo_clusters"].values())
                w = lambda c: tab.where(rowlabel, c)   # noqa: E731
                cells = [NAMES[m],
                         R.add(k + "_model", mv, f_pct(mv), "share", src, "mean of " + jp(*base, "model_clusters") + "/*", w("Model's share")),
                         R.add(k + "_placebo", pv, f_pct(pv), "share", src, "mean of " + jp(*base, "placebo_clusters") + "/*", w("Placebo's share")),
                         reg(k + "_diff", node["mean_diff"], lambda v: f_pts(v, 1, True), "points", src,
                             jp(*base, "mean_diff"), w("Diff vs placebo [interval]")) + " " +
                         ci_cell(tab, rowlabel, "Diff vs placebo [interval]", k, src, base + ("ci",)),
                         reg(k + "_p", node["p"], f_p, "p", src, jp(*base, "p"), w("p"))]
                tab.row(label, cells)
        tab.done()


def error_table():
    tab = Tab("err", ["Model", "Distances", "Guesses left out", "Median (m)"])
    for m in ("opus", "haiku", "deepseek", "gemini", "placebo"):
        src = MODEL_FILE[m]
        e = J(ERR_FILE[m])
        n = at(J(src), "models", MODEL_ID[m], "error_sample_n")
        if n != len(e):
            raise Fail(f"error sample count differs from the file for {m}")
        k = f"err_{m}"
        tab.row(NAMES[m], [
            regj(k + "_n", src, ("models", MODEL_ID[m], "error_sample_n"), f_int, "distances", tab.where(NAMES[m], "Distances")),
            regj(k + "_left", src, ("models", MODEL_ID[m], "error_sample_left_out"), f_int, "guesses",
                 tab.where(NAMES[m], "Guesses left out")),
            reg(k + "_median", statistics.median(e), f_num(2), "m", ERR_FILE[m], "median of the list",
                tab.where(NAMES[m], "Median (m)"))])
    tab.done()


def room_tables():
    src = EX + "room_test.json"
    tab = Tab("room_live", ["Live arm", "Regions", "Typed, all stages", "Untyped, all stages",
                            "Typed, 8-member stages", "Untyped, 8-member stages"])
    arms = [("official", "Official"), ("filter_only", "Filter only"), ("oracle_visible", "Oracle visible"),
            ("placebo", "Placebo (chance rate)")]
    for a, label in arms:
        base = ("live", "by_arm", "arms", a)
        k = f"room_live_{a}"
        w = lambda c: tab.where(label, c)   # noqa: E731
        cells = [regj(k + "_of", src, base + ("of",), f_int, "regions", w("Regions"))]
        for fld, col in (("all_stages_typed", "Typed, all stages"), ("all_stages_untyped", "Untyped, all stages"),
                         ("stages_with_8_members_typed", "Typed, 8-member stages"),
                         ("stages_with_8_members_untyped", "Untyped, 8-member stages")):
            c = regj(f"{k}_{fld}_n", src, base + (f"predicted_{fld}",), f_int, "regions", w(col))
            r = regj(f"{k}_{fld}_rate", src, base + (f"rate_{fld}",), f_pct, "share", w(col))
            cells.append(f"{c} ({r})")
        tab.row(label, cells)
    tab.done()
    paper = Tab("room_paper", ["Source", "Regions", "Predicted before found"])
    paper.row("The paper", [regj("room_paper_of", src, ("live", "by_arm", "paper", "of"), f_int, "regions",
                                 paper.where("The paper", "Regions")),
                            regj("room_paper_pred", src, ("live", "by_arm", "paper", "predicted"), f_int, "regions",
                                 paper.where("The paper", "Predicted before found"))])
    paper.done()
    rep = Tab("room_replay", ["Model", "Regions", "1 of 4, typed", "1 of 4, untyped", "2 of 4, typed", "2 of 4, untyped"])
    for m in ("opus", "haiku", "deepseek", "gemini", "placebo"):
        s = ROOM_FILE[m]
        base = ("replay", MODEL_ID[m], "totals")
        k = f"room_rep_{m}"
        w = lambda c: rep.where(NAMES[m], c)   # noqa: E731
        rep.row(NAMES[m], [regj(k + "_of", s, base + ("of",), f_int, "regions", w("Regions"))] + [
            regj(f"{k}_{f}", s, base + (f"predicted_{f}",), f_int, "regions", w(col))
            for f, col in (("1of4_typed", "1 of 4, typed"), ("1of4_untyped", "1 of 4, untyped"),
                           ("2of4_typed", "2 of 4, typed"), ("2of4_untyped", "2 of 4, untyped"))])
    rep.done()


def validity_tables():
    models = ("opus", "haiku", "deepseek")
    models5 = models + ("gemini", "placebo")
    T1 = Tab("val_removed", ["Model", "Guesses", "Removed", "Share removed", "Box conflict", "Impassable crossing",
                             "Object parent"])
    for m in models5:
        src = VALID_FILE[m]
        base = (MODEL_ID[m], "share_removed")
        k = f"val_rem_{m}"
        w = lambda c: T1.where(NAMES[m], c)   # noqa: E731
        by = at(J(src), *base, "by_reason")

        def reason(r, col):
            if r not in by:
                return "-"
            return regj(f"{k}_{r}", src, base + ("by_reason", r, "n"), f_int, "guesses", w(col))
        T1.row(NAMES[m], [regj(k + "_n", src, base + ("n_guesses",), f_int, "guesses", w("Guesses")),
                          regj(k + "_rm", src, base + ("n_removed",), f_int, "guesses", w("Removed")),
                          regj(k + "_share", src, base + ("share_removed",), f_pct, "share", w("Share removed")),
                          reason("aabb_conflict", "Box conflict"), reason("impassable_crossing", "Impassable crossing"),
                          reason("object_parent", "Object parent")])
    T1.done()
    T2 = Tab("val_kept", ["Row", "Rows", "Clusters", "Kept minus removed [interval]", "Reading"])
    for L in ("L2", "L3"):
        for m in models5:
            src = VALID_FILE[m]
            base = (MODEL_ID[m], "kept_vs_removed", L)
            label = f"{NAMES[m]} {L}"
            k = f"val_kr_{m}_{L}"
            node = at(J(src), *base)
            verdict = node["verdict"].replace("+-0.05", "±5 points")
            T2.row(label, [
                regj(k + "_rows", src, base + ("n_rows",), f_int, "rows", T2.where(label, "Rows")),
                regj(k + "_clusters", src, base + ("n_clusters",), f_int, "clusters", T2.where(label, "Clusters")),
                reg(k + "_diff", node["mean_diff"], lambda v: f_pts(v, 1, True), "points", src, jp(*base, "mean_diff"),
                    T2.where(label, "Kept minus removed [interval]")) + " " +
                ci_cell(T2, label, "Kept minus removed [interval]", k, src, base + ("ci",)),
                reg(k + "_reading", verdict, f_str, "text", src, jp(*base, "verdict"), T2.where(label, "Reading"))])
    T2.done()
    T3 = Tab("val_reliab", ["Model", "Items", "Brier", "ECE"])
    T3b = Tab("val_cross", ["Model and test house", "Brier, raw support", "Brier, calibrated", "ECE, raw support",
                            "ECE, calibrated"])
    for m in models:
        src = VALID_FILE[m]
        base = (MODEL_ID[m], "reliability")
        T3.row(NAMES[m], [
            regj(f"val_rel_{m}_items", src, base + ("n_items",), f_int, "items", T3.where(NAMES[m], "Items")),
            regj(f"val_rel_{m}_brier", src, base + ("brier",), f_num(3), "Brier", T3.where(NAMES[m], "Brier")),
            regj(f"val_rel_{m}_ece", src, base + ("ece",), f_num(3), "ECE", T3.where(NAMES[m], "ECE"))])
        for sc in ("00853", "00871"):
            label = f"{NAMES[m]}, tested on {sc}"
            k = f"val_rel_{m}_{sc}"
            w = lambda c: T3b.where(label, c)   # noqa: E731
            cs = base + ("cross_scene", sc)
            T3b.row(label, [
                regj(k + "_brier_raw", src, cs + ("brier_raw_support",), f_num(3), "Brier", w("Brier, raw support")),
                regj(k + "_brier_cal", src, cs + ("brier",), f_num(3), "Brier", w("Brier, calibrated")),
                regj(k + "_ece_raw", src, cs + ("ece_raw_support",), f_num(3), "ECE", w("ECE, raw support")),
                regj(k + "_ece_cal", src, cs + ("ece",), f_num(3), "ECE", w("ECE, calibrated"))])
    T3.done()
    T3b.done()
    T4 = Tab("val_curve", ["Model and support", "Items", "L3 hit rate"])
    for m in models:
        src = VALID_FILE[m]
        curve = at(J(src), MODEL_ID[m], "reliability", "curve")
        for i, c in enumerate(curve):
            label = f"{NAMES[m]} {c['mean_p']:.2f}"
            base = (MODEL_ID[m], "reliability", "curve", i)
            k = f"val_curve_{m}_{i}"
            T4.row(label, [regj(k + "_n", src, base + ("n",), f_int, "items", T4.where(label, "Items")),
                           regj(k + "_y", src, base + ("mean_y",), f_pct, "share", T4.where(label, "L3 hit rate"))])
    T4.done()
    T5 = Tab("val_votes", ["Model and view", "Guesses kept", "L2 hits", "L2 claims", "L3 hits", "L3 items"])
    for m in models:
        src = VALID_FILE[m]
        for view, vlabel in (("raw", "raw"), ("V", "validator"), ("V+2of8", "validator + the paper's 2-of-8 rule"),
                             ("V+vote0.5", "validator + vote 0.5"),
                             ("V+vote0.75", "validator + vote 0.75"), ("V+vote1.0", "validator + vote 1.0")):
            if view not in at(J(src), MODEL_ID[m], "kept_vs_guesses"):
                continue
            base = (MODEL_ID[m], "kept_vs_guesses", view)
            label = f"{NAMES[m]}, {vlabel}"
            k = f"val_vote_{m}_{view}"
            w = lambda c: T5.where(label, c)   # noqa: E731
            T5.row(label, [
                regj(f"{k}_{f}", src, base + (f,), f_int, unit, w(col))
                for f, unit, col in (("guesses_kept", "guesses", "Guesses kept"), ("l2_hits", "hits", "L2 hits"),
                                     ("l2_claims", "claims", "L2 claims"), ("l3_hits", "hits", "L3 hits"),
                                     ("l3_items", "items", "L3 items"))])
    T5.done()


def loose_equals_primary():
    """Count members whose L1 or L2 score under the looser rule differs from the primary score."""
    out = {}
    for m in ("opus", "haiku", "deepseek"):
        d = J(RECORD_FILE[m])
        diff = 0
        n = 0
        for a, b in zip(d["records"], d["secondary_records"]["loose"]):
            for k, x in a["model"].items():
                y = b["model"][k]
                n += 1
                if x["L1"] != y["L1"] or x["L2"] != y["L2"]:
                    diff += 1
        out[m] = (diff, n)
        reg(f"loose_diff_{m}", diff, f_int, "members", RECORD_FILE[m],
            "count of members where secondary_records/loose/*/model/*/L1 or L2 differs from records/*/model/*")
        reg(f"loose_n_{m}", n, f_int, "members", RECORD_FILE[m], "count of records[*]/model/*")
    return out


# ------------------------------------------------------------------------------------------ M2

M2SRC = M2DIR + "pass2/summary_factorial.json"
M2ERR = {"deepseek": (M2DIR + "pass1/err_deepseek.json", "F3-deepseek", "B_deepseek", "DeepSeek"),
         "haiku": (M2DIR + "pass2/err_haiku.json", "F3-haiku", "B_haiku", "Haiku"),
         "opus": (M2DIR + "pass2/err_opus.json", "F3-opus", "B_opus", "Opus")}
M2ARMS = (("F1", "F1 (true guesses)"), ("F5", "F5 (placebo)"), ("F6", "F6 (no guesses)"), ("F0", "F0 (all true)"),
          ("F3-deepseek", "F3 with DeepSeek's error"), ("F3-haiku", "F3 with Haiku's error"),
          ("F3-opus", "F3 with Opus's error"), ("F-room", "F-room (types only)"))


def m2_interval(tab, row, col, key, keys):
    node = at(J(M2SRC), *keys)
    w = tab.where(row, col)
    m = reg(key + "_mean", node["mean"], f_rho, "rho", M2SRC, jp(*keys, "mean"), w)
    lo = reg(key + "_lo", node["lo"], f_rho, "rho", M2SRC, jp(*keys, "lo"), w)
    hi = reg(key + "_hi", node["hi"], f_rho, "rho", M2SRC, jp(*keys, "hi"), w)
    return f"{m} [{lo}, {hi}]"


def m2_scope_tables(scope):
    """The arm, reading, regret and count tables for all stages (scope 'all') or the official-arm stages."""
    src = M2SRC
    main = ("analysis", "main", scope)
    sfx = "" if scope == "all" else "_off"
    pre = "m2" + sfx
    counts = ("counts_all_stages",) if scope == "all" else ("counts_official_stages",)
    arms = Tab("m2_arms" + sfx, ["Arm", "Mean correlation [interval]", "Median per stage", "Median placement error (m)"])
    for arm, label in M2ARMS:
        k = pre + "_" + arm.replace("-", "_")
        med = "-"
        for m, (efile, a, _b, _n) in M2ERR.items():
            if a == arm:
                med = reg(f"m2_err_{m}_median", statistics.median(J(efile)), f_num(2), "m", efile,
                          "median of the list", arms.where(label, "Median placement error (m)"))
        arms.row(label, [m2_interval(arms, label, "Mean correlation [interval]", k, main + ("arm_mean_rho", arm)),
                         regj(k + "_median", src, main + ("median_stage_rho", arm), f_rho, "rho",
                              arms.where(label, "Median per stage")), med])
    arms.done()
    verdict = lambda key: at(J(src), *main, "reading", "verdicts", key)   # noqa: E731
    rd = Tab("m2_reading" + sfx, ["Contrast", "X minus F5 [interval]", "X minus half of A [interval]", "Verdict"])
    ra = "A = F1 minus F5"
    rd.row(ra, [m2_interval(rd, ra, "X minus F5 [interval]", pre + "_A", main + ("differences", "A")), "-",
                "F1 separates from F5"])
    for key, label in (("B_deepseek", "B, F3 with DeepSeek's error"), ("B_haiku", "B, F3 with Haiku's error"),
                       ("B_opus", "B, F3 with Opus's error"), ("C", "C, F-room")):
        k = pre + "_" + key
        rd.row(label, [m2_interval(rd, label, "X minus F5 [interval]", k, main + ("differences", key)),
                       m2_interval(rd, label, "X minus half of A [interval]", k + "_half", main + ("reading_series", key)),
                       reg(k + "_verdict", verdict(key), f_str, "verdict", src, jp(*main, "reading", "verdicts", key),
                           rd.where(label, "Verdict"))])
    for key, label in (("F0-F5", "F0 minus F5"), ("F6-F5", "F6 minus F5")):
        k = pre + "_" + key.replace("-", "")
        rd.row(label, [m2_interval(rd, label, "X minus F5 [interval]", k, main + ("differences", key)), "-",
                       "not part of the reading rule"])
    rd.done()
    # regret
    rg = Tab("m2_regret" + sfx, ["Arm", "R1 regret under U_wall [interval]", "R1 regret under U_wall_cone [interval]"])
    for arm, label in M2ARMS:
        cells = []
        for yard, ycol in (("Uwall", "R1 regret under U_wall [interval]"), ("Ucone", "R1 regret under U_wall_cone [interval]")):
            keys = main + ("regret_R1", yard, "arm_mean", arm)
            node = at(J(src), *keys)
            k = f"{pre}_regret_{yard}_{arm.replace('-', '_')}"
            w = rg.where(label, ycol)
            cells.append("{} [{}, {}]".format(
                reg(k + "_mean", node["mean"], f_num(2), "R1 regret", src, jp(*keys, "mean"), w),
                reg(k + "_lo", node["lo"], f_num(2), "R1 regret", src, jp(*keys, "lo"), w),
                reg(k + "_hi", node["hi"], f_num(2), "R1 regret", src, jp(*keys, "hi"), w)))
        rg.row(label, cells)
    rg.done()
    # objects per member and ig = 0
    ob = Tab("m2_objects" + sfx, ["Arm", "Objects per member (mean)", "Fewest", "Most", "Stages with ig = 0 for every candidate"])
    for arm, label in (("F1", "F1"), ("F5a", "F5, set A"), ("F5b", "F5, set B"), ("F6", "F6"), ("F0", "F0"),
                       ("F3-deepseek", "F3 with DeepSeek's error"), ("F3-haiku", "F3 with Haiku's error"),
                       ("F3-opus", "F3 with Opus's error"), ("F-room", "F-room")):
        k = f"{pre}_obj_{arm.replace('-', '_')}"
        base = counts + ("objects_per_member", arm)
        zero = counts + ("ig_zero_stage_share", arm)
        ob.row(label, [
            regj(k + "_mean", src, base + ("mean_per_member",), f_num(2), "objects", ob.where(label, "Objects per member (mean)")),
            regj(k + "_min", src, base + ("min",), f_int, "objects", ob.where(label, "Fewest")),
            regj(k + "_max", src, base + ("max",), f_int, "objects", ob.where(label, "Most")),
            "{} of {}".format(
                regj(k + "_zero", src, zero + ("stages_ig_zero_for_every_candidate",), f_int, "stages",
                     ob.where(label, "Stages with ig = 0 for every candidate")),
                regj(k + "_zero_of", src, zero + ("n_stages",), f_int, "stages",
                     ob.where(label, "Stages with ig = 0 for every candidate")))])
    ob.done()


def m2_tables():
    src = M2SRC
    m2_scope_tables("all")
    m2_scope_tables("official")
    def secondary(name, reps, sfx):
        sec = Tab(name, ["Repeat", "Stages", "A = F1 minus F5", "B DeepSeek (X minus F5)", "B Haiku (X minus F5)",
                         "B Opus (X minus F5)", "C (X minus F5)", "Verdicts (from X minus half of A)"])
        for label, base in reps:
            k = "m2_sec" + sfx + "_" + re.sub(r"\W+", "_", label.lower()).strip("_")
            node = at(J(src), *base)
            vd = node["reading"]["verdicts"]
            short = lambda v: "not shown" if v.startswith("not shown") else v   # noqa: E731
            bv = {short(vd[x]) for x in ("B_deepseek", "B_haiku", "B_opus")}
            vtext = ("B: " + "/".join(sorted(bv)) + "; C: " + short(vd["C"]))
            cells = [regj(k + "_stages", src, base + ("n_stages_kept",), f_int, "stages", sec.where(label, "Stages"))
                     if "n_stages_kept" in node else "-"]
            for col, dk in (("A = F1 minus F5", "A"), ("B DeepSeek (X minus F5)", "B_deepseek"),
                            ("B Haiku (X minus F5)", "B_haiku"), ("B Opus (X minus F5)", "B_opus"),
                            ("C (X minus F5)", "C")):
                cells.append(m2_interval(sec, label, col, f"{k}_{dk}", base + ("differences", dk)))
            cells.append(vtext)
            for dk in vd:
                reg(f"{k}_v_{dk}", vd[dk], f_str, "verdict", src, jp(*base, "reading", "verdicts", dk),
                    sec.where(label, "Verdicts (from X minus half of A)"))
            sec.row(label, cells)
        sec.done()

    secondary("m2_secondary", [("`ig` alone", ("analysis", "ig_alone", "all")),
                               ("Audit's U_cone", ("analysis", "audit_Ucone", "all")),
                               ("U_360", ("analysis", "U360", "all")),
                               ("Official-arm stages", ("analysis", "main", "official")),
                               ("Runs clustered by scene and seed (6)", ("clustered_by_scene_seed", "main"))], "")
    secondary("m2_secondary_off", [("`ig` alone", ("analysis", "ig_alone", "official")),
                                   ("Audit's U_cone", ("analysis", "audit_Ucone", "official")),
                                   ("U_360", ("analysis", "U360", "official"))], "_off")


def m2_numbers():
    src = M2DIR + "pass2/summary_factorial.json"
    c = ("counts_all_stages",)
    regj("m2_stages", src, ("n_rows_usable",), f_int, "stages")
    regj("m2_left_out", src, ("left_out", "n_left_out"), f_int, "stages")
    regj("m2_runs", src, ("analysis", "main", "all", "n_runs"), f_int, "runs")
    regj("m2_official_stages", src, ("analysis", "main", "official", "n_stages_kept"), f_int, "stages")
    regj("m2_official_runs", src, ("analysis", "main", "official", "n_runs"), f_int, "runs")
    regj("m2_f0_ig_zero", src, c + ("ig_zero_stage_share", "F0", "stages_ig_zero_for_every_candidate"), f_int, "stages")
    regj("m2_f0_ig_zero_of", src, c + ("ig_zero_stage_share", "F0", "n_stages"), f_int, "stages")
    regj("m2_f0_ig_zero_share", src, c + ("ig_zero_stage_share", "F0", "share"), f_pct, "share")
    regj("m2_froom_objects", src, c + ("objects_per_member", "F-room", "mean_per_member"), f_num(2), "objects")
    regj("m2_f1_objects", src, c + ("objects_per_member", "F1", "mean_per_member"), f_num(2), "objects")
    regj("m2_froom_f0_objects", src, c + ("objects_per_member", "F0", "mean_per_member"), f_num(2), "objects")
    regj("m2_froom_members", src, c + ("froom_no_unseen_typed", "members"), f_int, "members")
    regj("m2_members_total", src, c + ("froom_no_unseen_typed", "members_total"), f_int, "members")
    regj("m2_froom_stages", src, c + ("froom_no_unseen_typed", "stages_with_a_member"), f_int, "stages")
    regj("m2_froom_stages_all", src, c + ("froom_no_unseen_typed", "stages_all_members"), f_int, "stages")
    regj("m2_fallback_deepseek", src, c + ("f3_fallback_members_not_moved", "F3-deepseek", "members"), f_int, "members")
    regj("m2_fallback_haiku", src, c + ("f3_fallback_members_not_moved", "F3-haiku", "members"), f_int, "members")
    regj("m2_fallback_opus", src, c + ("f3_fallback_members_not_moved", "F3-opus", "members"), f_int, "members")
    regj("m2_prereg_hash", M2DIR + "pass2/factorial_meta.json", ("prereg_sha256",), lambda v: v[:8], "sha256 prefix")


# ------------------------------------------------------------------------------------------ replay, spend, events

def replay_numbers(skip_replay):
    if skip_replay:
        R.skipped.add("replay")
        return
    totals = {}
    for tag, ledger in (("smoke", REPLAY / "smoke" / "usage.jsonl"), ("replay", REPLAY / "m4" / "usage.jsonl"),
                        ("nohint", REPLAY / "nohint" / "usage.jsonl")):
        if not ledger.exists():
            raise Fail(f"missing ledger: {ledger}")
        by = collections.defaultdict(float)
        n = 0
        for line in ledger.read_text().splitlines():
            if line.strip():
                x = json.loads(line)
                by[x["model"]] += x["cost"]
                n += 1
        totals[tag] = by
        s = relsrc(ledger)
        reg(f"spend_{tag}", sum(by.values()), f_usd, "USD", s, "sum of cost over all lines")
        if tag == "replay":
            for model, short in ((OPUS, "opus"), (HAIKU, "haiku")):
                reg(f"spend_{tag}_{short}", by[model], f_usd, "USD", s, f"sum of cost where model = {model}")
    grand = sum(sum(b.values()) for b in totals.values())
    reg("spend_all", grand, f_usd, "USD", "replay_outputs/{smoke,m4,nohint}/usage.jsonl",
        "sum of cost over the three ledgers")
    # members: record.json and parse.json
    for model, short in ((OPUS, "opus"), (HAIKU, "haiku")):
        files = sorted((REPLAY / "m4" / model / "effort_medium").glob("*/member_*/record.json"))
        calls, tools, ok, parse_fail = [], [], 0, 0
        for p in files:
            r = json.loads(p.read_text())
            pj = json.loads((p.parent / "parse.json").read_text())
            calls.append(len(r["calls"]))
            tools.append(len(r["tool_calls"]))
            ok += r["status"] == "ok"
            parse_fail += not pj["ok"]
        rel = relsrc(REPLAY / "m4" / model / "effort_medium") + "/<row>/member_<k>/record.json"
        reg(f"mem_{short}_n", len(files), f_int, "members", rel, "count of files")
        if short == "haiku":
            reg(f"mem_{short}_parse_fail", parse_fail, f_int, "members", rel.replace("record.json", "parse.json"),
                "count of ok = false")
        reg(f"mem_{short}_calls", statistics.fmean(calls), f_num(2), "calls per member", rel, "mean of len(calls)")
        reg(f"mem_{short}_tools", statistics.fmean(tools), f_num(1), "tool calls per member", rel,
            "mean of len(tool_calls)")
    for model, short in ((OPUS, "opus"), (HAIKU, "haiku")):
        files = sorted((REPLAY / "m4" / model / "effort_medium").glob("*/member_*/record.json"))
        flagged = [p for p in files if "stop_max_tokens" in json.loads(p.read_text()).get("flags", [])]
        if short == "haiku":
            reg(f"mem_{short}_maxtok", len(flagged), f_int, "members", relsrc(REPLAY / "m4" / model / "effort_medium") +
                "/<row>/member_<k>/record.json", "count of records whose flags hold stop_max_tokens")
    drop = REPLAY / "m4" / HAIKU / "effort_medium" / "e2_00871_s43_filter_st03" / "member_3"
    dr = json.loads((drop / "record.json").read_text())
    if "stop_max_tokens" not in dr["flags"] or dr["stop_reasons"][-1] != "max_tokens" or json.loads((drop / "parse.json").read_text())["ok"]:
        raise Fail("the dropped Haiku member is no longer the max_tokens member that failed to parse")
    reg("mem_total", sum(len(list((REPLAY / "m4" / m / "effort_medium").glob("*/member_*/record.json")))
                         for m in (OPUS, HAIKU)), f_int, "members", "replay_outputs/m4", "count of record.json files")
    log = (REPLAY / "m4" / "replay_run.log").read_text().splitlines()
    for key, line, label in (("t_replay_start", next(x for x in log if x.startswith("start ")), "first line"),
                             ("t_replay_end", next(x for x in reversed(log) if x.startswith("end ")), "last line")):
        hhmm = line.split()[1][:5]
        reg(key, hhmm, f_str, "IST time", relsrc(REPLAY / "m4" / "replay_run.log"), f"{label}: '{line}'")
    # no-hint run
    s = relsrc(REPLAY / "nohint" / "summary.json")
    sj = json.loads((REPLAY / "nohint" / "summary.json").read_text())
    reg("nohint_members", sj["counts"]["ok"], f_int, "members", s, "/counts/ok")


def event_numbers(skip_git):
    plan = "docs/ENDSEM_FINAL_PLAN_2026-11-13.md"
    dev = "tools/live_policy/DEVIATIONS_NOVEMBER.md"
    for key, text, rx, fname in (
            ("t_prereg_hash", "18:59", r"11-13 18:59: `PREREGISTRATION_SEMANTIC\.md` hashed", plan),
            ("t_m2_hash", "19:15", r"11-13 19:15: `PREREGISTRATION_M2\.md` hashed", plan),
            ("t_exploratory", "20:13", r"20:13: first real scoring run, exploratory", plan),
            ("t_nohint", "20:50", r"\*\*11-13 20:50: the no-hint replay", dev),
            ("t_margin_check", "21:10", r"\*\*11-13 21:10: a check made after", dev)):
        if not re.search(rx, T(fname)):
            raise Fail(f"{fname} no longer holds the line for {key}")
        reg(key, text, f_str, "IST time", fname, f"text match: {rx}")
    if skip_git:
        R.skipped.add("git")
        return
    for key, h in (("t_prereg_push", "49307ed"), ("t_cost_hash", "2e8a06c"), ("t_truth_hash", "61d5965"),
                   ("t_freeze", "04e6afc"), ("t_scored", "2e46ec8")):
        out = subprocess.run(["git", "-C", str(ROOT), "show", "-s", "--format=%cI", h], capture_output=True, text=True)
        if out.returncode != 0:
            raise Fail(f"git cannot find commit {h}: {out.stderr.strip()}")
        stamp = out.stdout.strip()
        hhmm = stamp[11:16]
        reg(key, hhmm, f_str, "IST time", "git log", f"commit {h}: {stamp}")


def rule_numbers():
    pre = "tools/live_policy/PREREGISTRATION_SEMANTIC.md"
    m2 = "tools/live_policy/PREREGISTRATION_M2.md"
    cost = "tools/live_policy/m4/COST_ADDENDUM.md"
    for key, val, unit, fname, rx in (
            ("rule_houses", 179, "houses", pre, r"179 remain"),
            ("rule_reach_m", 0.5, "m", pre, r"within 0\.5 m of one of its footprint cells"),
            ("rule_alpha", 0.05, "alpha", pre, r"Holm, α = 0\.05"),
            ("rule_hypotheses", 6, "hypotheses", pre, r"six hypotheses"),
            ("rule_members", 4, "members", pre, r"4 members per row"),
            ("rule_max_tokens", 64000, "tokens", pre, r"`max_tokens` 64,000"),
            ("rule_turns", 50, "turns", pre, r"at most 50 turns"),
            ("rule_cap_opus", 280, "USD", cost, r"Opus \$280"),
            ("rule_cap_haiku", 20, "USD", cost, r"Haiku \$20"),
            ("rule_gate_pairs", 6, "pairs", pre, r"over the 6 seed × arm pairs"),
            ("rule_gate_pmin", "1/64", "fraction", pre, r"smallest possible p is 1/64"),
            ("rule_valid_band", 5, "points", pre, r"within ±5 points"),
            ("rule_f3_models", 3, "models", m2, r"F3 runs first for DeepSeek, and for Claude Haiku and Opus"),
            ("rule_m2_half", 0.5, "factor", m2, r"X − 0\.5 × A"),
            ("rule_vocab", 52, "words", pre, r"52-word detector vocabulary"),
            ("rule_drop_flag", 25, "percent", pre, r"a rate above 25% is flagged"),
            ("rule_room_m", 2.5, "m", pre, r"within 2\.5 m of the region's `centroid_xy`"),
            ("rule_room_k", 2, "members", pre, r"at least 2 of the 8 members")):
        if not re.search(rx, T(fname)):
            raise Fail(f"{fname} no longer holds the rule for {key}: /{rx}/")
        reg(key, val, f_str if isinstance(val, str) else (lambda v: f"{v:g}" if not isinstance(v, int) else f"{v:,}" if v >= 10000 else f"{v}"),
            unit, fname, f"text match: {rx}")
    h = T("tools/live_policy/PREREGISTRATION_SEMANTIC.sha256").split()[0]
    reg("hash_prereg", h, lambda v: v[:8], "sha256 prefix", "tools/live_policy/PREREGISTRATION_SEMANTIC.sha256", "first field")
    reg("hash_freeze", at(J(CL + "results.json"), "run_info", "freeze_sha256"), lambda v: v[:8], "sha256 prefix",
        CL + "results.json", "/run_info/freeze_sha256")


def frame_numbers():
    txt = T("tools/live_policy/semantic/sample_frame.txt")
    rows = [(l.split()[0]) for l in txt.splitlines() if l.strip() and not l.startswith("#")]
    rnd, cur = {}, 0
    for l in txt.splitlines():
        mm = re.match(r"# Round (\d)", l)
        if mm:
            cur = int(mm.group(1))
        elif l.strip() and not l.startswith("#"):
            rnd[l.split()[0]] = cur
    src = "tools/live_policy/semantic/sample_frame.txt"
    reg("frame_rows", len(rows), f_int, "rows", src, "count of non-comment lines")
    reg("frame_rows_runs", sum(1 for r in rows if r.startswith(("e1_", "e2_"))), f_int, "rows", src,
        "count of rows starting e1_ or e2_")
    reg("frame_rows_gemini", sum(1 for r in rows if r.startswith("fa1_")), f_int, "rows", src,
        "count of rows starting fa1_")
    reg("frame_round1", sum(1 for r in rows if rnd[r] == 1), f_int, "rows", src, "count of rows under '# Round 1'")
    run_rows = [l.split() for l in txt.splitlines() if l.strip() and not l.startswith("#") and l.startswith(("e1_", "e2_"))]
    reg("frame_runs", len({x[1] for x in run_rows}), f_int, "runs", src, "count of distinct run_dir over rows starting e1_ or e2_")
    stg = sorted({int(x[2]) for x in run_rows})
    reg("frame_stages", ", ".join(map(str, stg[:-1])) + f" and {stg[-1]}", f_str, "stages", src,
        "distinct stage numbers over rows starting e1_ or e2_")
    cl = J(CL + "results.json")
    reg("frame_clusters", len(at(cl, "models", OPUS, "analysis", "levels", "L1", "model_cluster_scores")), f_int,
        "clusters", CL + "results.json", "count of /models/claude-opus-5-5/analysis/levels/L1/model_cluster_scores")
    reg("rounds_used", len(cl["rounds_used"]), f_int, "rounds", CL + "results.json", "count of /rounds_used")
    for short, model in (("opus", OPUS), ("haiku", HAIKU)):
        st = at(cl, "models", model, "status")
        cnt = collections.Counter(v for row in st.values() for v in row.values())
        reg(f"status_{short}_ok", cnt.get("ok", 0), f_int, "members", CL + "results.json",
            f"count of status = ok in /models/{model}/status")
        reg(f"status_{short}_dropped", cnt.get("dropped", 0), f_int, "members", CL + "results.json",
            f"count of status = dropped in /models/{model}/status")
    return rows, rnd


def recompute_numbers():
    src = SEMDIR + "independent_recompute/margin_summary.json"
    s = J(src)["summary"]
    for short, model in (("opus", OPUS), ("haiku", HAIKU)):
        a, b = s[f"{model}|200"], s[f"{model}|5000"]
        lo = min(a["ci_high_min"], b["ci_high_min"])
        hi = max(a["ci_high_max"], b["ci_high_max"])
        reg(f"rc_{short}_hi_min", lo, lambda v: f_pts(v, 2), "points", src,
            f"min of /summary/{model}|200/ci_high_min and /summary/{model}|5000/ci_high_min")
        reg(f"rc_{short}_hi_max", hi, lambda v: f_pts(v, 2), "points", src,
            f"max of /summary/{model}|200/ci_high_max and /summary/{model}|5000/ci_high_max")
        if short == "opus":
            reg(f"rc_{short}_runs200", a["runs"], f_int, "runs", src, f"/summary/{model}|200/runs")
            reg(f"rc_{short}_runs5000", b["runs"], f_int, "runs", src, f"/summary/{model}|5000/runs")
        reg(f"rc_{short}_below", a["below_0.03"] + b["below_0.03"], f_int, "runs", src,
            f"sum of /summary/{model}|200/below_0.03 and /summary/{model}|5000/below_0.03")
        if short == "opus":
            reg(f"rc_{short}_draws_hi", 5000, f_int, "draws", src, "the key '|5000' of /summary")
            reg(f"rc_{short}_draws_lo", 200, f_int, "draws", src, "the key '|200' of /summary")
    # Opus and Haiku interval upper ends and half-widths against D, two decimals
    for short, m in (("opus", "opus"), ("haiku", "haiku")):
        ci = at(J(CL + "results.json"), *lkeys(m, "L3"), "comparators", "D", "ci")
        base = CL + "results.json"
        reg(f"p_{short}_L3_D_hi2", ci[1], lambda v: f_pts(v, 2), "points", base,
            jp(*lkeys(m, "L3"), "comparators", "D", "ci", 1))
        reg(f"p_{short}_L3_D_hw", (ci[1] - ci[0]) / 2, lambda v: f_pts(v, 1), "points", base,
            "(ci[1] - ci[0]) / 2 of " + jp(*lkeys(m, "L3"), "comparators", "D", "ci"))
        reg(f"p_{short}_L3_D_gap", 0.03 - ci[1], lambda v: f_pts(v, 2), "points", base,
            "margin 0.03 minus ci[1] of " + jp(*lkeys(m, "L3"), "comparators", "D", "ci"))
    for short, m in (("opus", "opus"), ("haiku", "haiku")):
        for comp, L, tag in ((("B1", "L2", "B1ci"),) if short == "opus" else ()) + (("B5", "L3", "B5ci"),):
            ci = at(J(CL + "results.json"), *lkeys(m, L), "comparators", comp, "ci")
            for i, part in enumerate(("lo", "hi")):
                reg(f"p_{short}_{L}_{tag}_{part}", ci[i], lambda v: f_pts(v, 1, True), "points", CL + "results.json",
                    jp(*lkeys(m, L), "comparators", comp, "ci", i))
    for short, m in (("opus", "opus"), ("haiku", "haiku")):
        for L in ("L1", "L2"):
            node = at(J(CL + "results.json"), *lkeys(m, L), "comparators", "B3")
            reg(f"p_{short}_{L}_B3_hi", node["ci"][1], lambda v: f_pts(v, 1, True), "points", CL + "results.json",
                jp(*lkeys(m, L), "comparators", "B3", "ci", 1))


def thesis_numbers():
    reg("thesis", at(J(CL + "results.json"), "family", "thesis"), f_str, "text", CL + "results.json", "/family/thesis")
    reg("gemini_clusters", len(at(J(EX + "results.json"), "models", "gemini", "analysis", "levels", "L1",
                                  "model_cluster_scores")), f_int, "clusters", EX + "results.json",
        "count of /models/gemini/analysis/levels/L1/model_cluster_scores")
    reg("gemini_rows", at(J(EX + "results.json"), "models", "gemini", "analysis", "levels", "L1", "comparators", "B1",
                          "n_rows"), f_int, "rows", EX + "results.json",
        "/models/gemini/analysis/levels/L1/comparators/B1/n_rows")
    reg("deepseek_members", sum(len(r["model"]) for r in records("deepseek")), f_int, "members",
        RECORD_FILE["deepseek"], "count of records[*]/model/*")
    reg("gemini_members", sum(len(r["model"]) for r in records("gemini")), f_int, "members",
        RECORD_FILE["gemini"], "count of records[*]/model/*")
    # other-views of Haiku L1: rows behind each contrast
    for short, m in (("opus", "opus"), ("haiku", "haiku"), ("deepseek", "deepseek")):
        reg(f"l1_noclaim_{short}", sum(1 for r in records(m) if r["possible"]["L1"] and
                                       all(x["L1"] is None for x in r["model"].values())), f_int, "rows", RECORD_FILE[m],
            "count of records[*] with possible/L1 true and no model/*/L1 score")
    s360 = ("analysis", "U360", "all", "reading_series", "C")
    for part in ("mean", "lo", "hi"):
        reg(f"m2_u360_Chalf_{part}", at(J(M2SRC), *s360, part), f_rho, "rho", M2SRC, jp(*s360, part))
    reg("l1_rows_deepseek", at(J(EX + "results.json"), *lkeys("deepseek", "L1"), "comparators", "B3", "n_rows"), f_int,
        "rows", EX + "results.json", jp(*lkeys("deepseek", "L1"), "comparators", "B3", "n_rows"))
    for short, m in (("opus", "opus"), ("haiku", "haiku")):
        reg(f"l1_rows_{short}", at(J(CL + "results.json"), *lkeys(m, "L1"), "comparators", "B3", "n_rows"), f_int,
            "rows", CL + "results.json", jp(*lkeys(m, "L1"), "comparators", "B3", "n_rows"))
        if short == "opus":
            reg(f"l1_impossible_{short}", at(J(CL + "results.json"), *lkeys(m, "L1"), "n_rows_impossible"), f_int, "rows",
                CL + "results.json", jp(*lkeys(m, "L1"), "n_rows_impossible"))


# ------------------------------------------------------------------------------------------ no-hint run

def room_nodes(path: Path):
    import yaml
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    d = yaml.load(path.read_text(), Loader=loader)
    out = []
    for n in d["nodes"]:
        if n.get("node_type") == "room":
            p = n["position"]
            p = ast.literal_eval(p) if isinstance(p, str) else p
            out.append((n.get("name", ""), float(p[0]), float(p[1])))
    return out


def nohint_tables(rows, rnd, skip_replay):
    r1 = [r for r in rows if rnd[r] == 1]
    hint_src = CL + f"records_{HAIKU}.json"
    nh_src = NH + f"records_{HAIKU}.json"
    tab = Tab("nohint", ["Run", "Rows with an L1 score", "L1 claims", "L1 hits", "L1 score (mean of row scores)",
                         "Members with a claim", "L2 claims", "L2 hits"])
    for label, src in (("With the hint", hint_src), ("Without the hint", nh_src)):
        recs = [r for r in J(src)["records"] if r["round"] == 1]
        if len(recs) != len(r1):
            raise Fail("round 1 rows differ from the frame")
        row_scores = []
        claims = hits = withc = l2n = l2h = 0
        for r in recs:
            sc = [m["L1"] for m in r["model"].values() if m["L1"] is not None]
            if sc:
                row_scores.append(statistics.fmean(sc))
            for m in r["model"].values():
                claims += m["counts"]["l1_n"]
                hits += m["counts"]["l1_hits"]
                l2n += m["counts"]["l2_n"]
                l2h += m["counts"]["l2_hits"]
                withc += m["counts"]["l1_n"] > 0
        k = "nohint_" + ("hint" if label.startswith("With the") else "nohint")
        w = lambda c: tab.where(label, c)   # noqa: E731
        path = "round 1 rows: "
        tab.row(label, [
            reg(k + "_rows", len(row_scores), f_int, "rows", src, path + "count of rows with a member L1 score", w("Rows behind the L1 contrasts")),
            reg(k + "_claims", claims, f_int, "claims", src, path + "sum of model/*/counts/l1_n", w("L1 claims")),
            reg(k + "_hits", hits, f_int, "hits", src, path + "sum of model/*/counts/l1_hits", w("L1 hits")),
            reg(k + "_score", statistics.fmean(row_scores), f_pct, "share", src,
                path + "mean over rows of the mean of model/*/L1", w("L1 score (mean of row scores)")),
            reg(k + "_members", withc, f_int, "members", src, path + "count of members with l1_n > 0", w("Members with a claim")),
            reg(k + "_l2n", l2n, f_int, "claims", src, path + "sum of model/*/counts/l2_n", w("L2 claims")),
            reg(k + "_l2h", l2h, f_int, "hits", src, path + "sum of model/*/counts/l2_hits", w("L2 hits"))])
    tab.done()
    # the no-hint run's own file: the same score
    nh = J(NH + "results.json")
    sc, n = mean_clusters(NH + "results.json", lkeys("haiku", "L1") + ("model_cluster_scores",))
    reg("nohint_file_score", sc, f_pct, "share", NH + "results.json",
        "mean of " + jp(*lkeys("haiku", "L1"), "model_cluster_scores") + "/*")
    if skip_replay:
        return
    # new rooms from the parsed graphs
    names = {"hint": collections.Counter(), "nohint": collections.Counter()}
    counts = {"hint": [0, 0], "nohint": [0, 0]}
    for tag, root in (("hint", REPLAY / "m4"), ("nohint", REPLAY / "nohint")):
        for row in r1:
            obs = room_nodes(INPUTS / row / "graph.yaml")
            for k in range(4):
                p = root / HAIKU / "effort_medium" / row / f"member_{k}" / "parsed_graph.yaml"
                if not p.exists():
                    raise Fail(f"missing parsed graph: {p}")
                counts[tag][1] += 1
                new = [n for n in room_nodes(p) if all(math.hypot(n[1] - o[1], n[2] - o[2]) > 0.5 for o in obs)]
                counts[tag][0] += len(new)
                for n in new:
                    nm = re.sub(r"^an image of (a|an) ", "", n[0].lower()).strip()
                    names[tag][nm] += 1
    all_names = sorted(set(names["hint"]) | set(names["nohint"]), key=lambda x: (-(names["hint"][x] + names["nohint"][x]), x))
    nt = Tab("nohint_rooms", ["New room name", "With the hint", "Without the hint"])
    for nm in all_names:
        nt.row(nm, [reg(f"nhr_hint_{nm.replace(' ', '_')}", names["hint"][nm], f_int, "rooms",
                        "replay_outputs/m4/claude-haiku-5-5/effort_medium/<row>/member_<k>/parsed_graph.yaml",
                        "count of new room nodes named so (>0.5 m from every room node of replay_inputs/frame_inputs/<row>/graph.yaml)",
                        nt.where(nm, "With the hint")),
                    reg(f"nhr_nohint_{nm.replace(' ', '_')}", names["nohint"][nm], f_int, "rooms",
                        "replay_outputs/nohint/claude-haiku-5-5/effort_medium/<row>/member_<k>/parsed_graph.yaml",
                        "count of new room nodes named so (>0.5 m from every room node of replay_inputs/frame_inputs/<row>/graph.yaml)",
                        nt.where(nm, "Without the hint"))])
    nt.row("All new rooms", [
        reg("nhr_hint_total", counts["hint"][0], f_int, "rooms", "replay_outputs/m4/.../parsed_graph.yaml",
            "count of new room nodes over the 48 members", nt.where("All new rooms", "With the hint")),
        reg("nhr_nohint_total", counts["nohint"][0], f_int, "rooms", "replay_outputs/nohint/.../parsed_graph.yaml",
            "count of new room nodes over the 48 members", nt.where("All new rooms", "Without the hint"))])
    nt.done()
    reg("nhr_hint_members", counts["hint"][1], f_int, "members", "replay_outputs/m4/.../parsed_graph.yaml",
        "count of members read")
    reg("nhr_nohint_members", counts["nohint"][1], f_int, "members", "replay_outputs/nohint/.../parsed_graph.yaml",
        "count of members read")


# ------------------------------------------------------------------------------------------ build

def build(skip_replay=False, skip_git=False):
    global R
    R = Registry()
    _cache.clear()
    conf_tables("c_", ["opus", "haiku"], "conf_l12", "conf_l3", clusters=False)
    gate_table("gate", ["opus", "haiku"])
    conf_tables("e_", ["deepseek", "gemini", "placebo"], "exp_l12", "exp_l3", clusters=True)
    gate_table("gate_exp", ["deepseek", "gemini"])
    mdd_table()
    b2_table()
    supplement_tables()
    claims_table()
    secondary_tables()
    extras_tables()
    error_table()
    room_tables()
    validity_tables()
    loose_equals_primary()
    m2_tables()
    m2_numbers()
    rows, rnd = frame_numbers()
    thesis_numbers()
    recompute_numbers()
    rule_numbers()
    replay_numbers(skip_replay)
    event_numbers(skip_git)
    nohint_tables(rows, rnd, skip_replay)
    return R


# ------------------------------------------------------------------------------------------ check RESULTS.md

REPLAY_TABLES = {"nohint_rooms"}
TABLE_RE = re.compile(r"<!-- table:(\w+) -->\n(.*?)\n<!-- /table:\1 -->", re.S)
TAG_RE = re.compile(r"<!--n:(\w+)-->")


def sentence_of(text: str, pos: int) -> str:
    start = max(text.rfind("\n", 0, pos), text.rfind(". ", 0, pos) + 1 if text.rfind(". ", 0, pos) > text.rfind("\n", 0, pos) else -1)
    start = start + 1 if start >= 0 else 0
    end_nl = text.find("\n", pos)
    end_dot = text.find(". ", pos)
    ends = [e for e in (end_nl, end_dot) if e != -1]
    end = min(ends) + 1 if ends else len(text)
    s = TAG_RE.sub("", text[start:end]).strip()
    s = re.sub(r"\s+", " ", s)
    return s[:260]


def check(text: str, fill: bool):
    errors = []
    blocks = {m.group(1): m for m in TABLE_RE.finditer(text)}
    if fill:
        def repl(m):
            name = m.group(1)
            if name not in R.tables:
                errors.append(f"RESULTS.md has a block for unknown table {name}")
                return m.group(0)
            return f"<!-- table:{name} -->\n" + "\n".join(R.tables[name]) + f"\n<!-- /table:{name} -->"
        text = TABLE_RE.sub(repl, text)
        blocks = {m.group(1): m for m in TABLE_RE.finditer(text)}
    for name, lines in R.tables.items():
        if name not in blocks:
            errors.append(f"RESULTS.md has no block for table {name}")
            continue
        have = blocks[name].group(2).strip().splitlines()
        if have != lines:
            for i, (a, b) in enumerate(zip(have + [None] * len(lines), lines + [None] * len(have))):
                if a != b:
                    errors.append(f"table {name}, line {i + 1} differs:\n   RESULTS.md: {a}\n   files:      {b}")
                    break
    for name in blocks:
        if name not in R.tables and not ("replay" in R.skipped and name in REPLAY_TABLES):
            errors.append(f"RESULTS.md has a block for unknown table {name}")
    seen = set()
    for m in TAG_RE.finditer(text):
        key = m.group(1)
        if key not in R.rows:
            if (key.startswith(("rc_", "spend_", "mem_", "t_replay", "nhr_", "nohint_")) and "replay" in R.skipped) or \
               (key.startswith("t_") and "git" in R.skipped):
                continue
            errors.append(f"unknown key in a tag: {key}")
            continue
        row = R.rows[key]
        before = text[:m.start()]
        if not before.endswith(row["shown"]):
            errors.append(f"prose number for {key}: RESULTS.md has '{before[-len(row['shown']) - 6:]}' before the tag, "
                          f"the files give '{row['shown']}'")
        seen.add(key)
        row["prose"].append(sentence_of(text, m.start()))
    for key, row in R.rows.items():
        if not row["where"] and key not in seen:
            errors.append(f"registered number {key} appears nowhere in RESULTS.md (tag it or drop it)")
    return errors, text


def audit(text: str):
    body = TABLE_RE.sub("", text)
    for m in reversed(list(TAG_RE.finditer(body))):
        key = m.group(1)
        n = len(R.rows[key]["shown"]) if key in R.rows else 0
        body = body[:m.start() - n] + " " * n + body[m.end():]
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    body = re.sub(r"`[^`]*`", " ", body)
    body = re.sub(r"^#+ .*$", " ", body, flags=re.M)
    body = re.sub(r"\b(L[1-4]|B[1-5]L?|F[0-9]|M[0-9]b?|H[0-9]|E[0-9]|D)\b", " ", body)
    hits = []
    for i, line in enumerate(body.splitlines(), 1):
        for m in re.finditer(r"[-+]?\$?\d[\d,.]*%?", line):
            hits.append((i, m.group(0), line.strip()[:110]))
    return hits


def write_csv():
    with CSV_OUT.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["key", "value", "shown", "unit", "source_file", "path", "supports"])
        for key in sorted(R.rows):
            r = R.rows[key]
            supports = list(r["where"]) + [f'sentence: "{s}"' for s in r["prose"]]
            v = r["value"]
            if isinstance(v, float):
                v = repr(v)
            w.writerow([key, v, r["shown"], r["unit"], r["source"], r["path"], " || ".join(supports)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fill", action="store_true")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--no-replay", action="store_true")
    ap.add_argument("--no-git", action="store_true")
    a = ap.parse_args()
    try:
        build(a.no_replay, a.no_git)
    except Fail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 2
    if not RESULTS_MD.exists():
        print("FAIL: RESULTS.md does not exist", file=sys.stderr)
        return 2
    text = RESULTS_MD.read_text()
    errors, new_text = check(text, a.fill)
    if a.fill and new_text != text:
        RESULTS_MD.write_text(new_text)
        print("RESULTS.md: table blocks rewritten from the files")
        text = new_text
        errors, _ = check(text, False)
    if a.audit:
        for i, tok, line in audit(text):
            print(f"untagged numeral line {i}: {tok:>10}   {line}")
    if errors:
        print(f"FAIL: {len(errors)} problem(s)", file=sys.stderr)
        for e in errors[:60]:
            print("  " + e, file=sys.stderr)
        return 1
    write_csv()
    print(f"ok: {len(R.rows)} numbers, {len(R.tables)} tables checked; wrote {CSV_OUT.name}")
    if R.skipped:
        print("skipped:", ", ".join(sorted(R.skipped)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
