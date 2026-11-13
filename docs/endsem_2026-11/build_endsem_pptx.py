"""Build ASP_Endsem.pptx: the end-sem talk "Right in meaning, wrong in place?", in the style of
../checkin_2026-11/ASP_Checkin2.pptx, with ENDSEM_Script.md as speaker notes.

Type size: the canvas is 1920 px wide and 1 px is 0.5 pt, so body text is 32 px (16 pt) or more and
notes, labels and chart text are 24 px (12 pt) or more. The builder warns if its line estimate says a
text box runs past the slide.

Every chart and table value comes from a result file (numbers.csv, paper_compare.json, c_checks.json,
frontier_holm.json, figures/stage_numbers.json) or, for part 3, from slots.json. A null in slots.json
shows TBD and a grey "result pending" mark. SOURCES.md says which file and key stand behind each number.

Usage (from the project root):
    .venv_offline/bin/python docs/endsem_2026-11/figures/make_stage_picture.py   # slide 13, once
    .venv_offline/bin/python docs/endsem_2026-11/build_endsem_pptx.py
"""
import csv
import json
import math
import os
import re
import sys
from decimal import ROUND_HALF_UP, Decimal

from pptx import Presentation
from pptx.enum.dml import MSO_LINE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PROJECT, "docs", "checkin"))
from build_checkin_pptx import (BODY, FAINT, INK, LIGHT, LINE, MID, MONO, RULE, SANS, WASH, WHITE,  # noqa: E402
                                fill_frame, hline, kick, oval, px, rect, run, svg_text, text)

# ENDSEM_SLOTS and ENDSEM_OUT let a test build use other files without touching the real ones.
OUT = os.environ.get("ENDSEM_OUT", os.path.join(HERE, "ASP_Endsem.pptx"))
SCRIPT = os.path.join(HERE, "ENDSEM_Script.md")
SLOTS = os.environ.get("ENDSEM_SLOTS", os.path.join(HERE, "slots.json"))
LP = os.path.join(PROJECT, "tools", "live_policy")
NUMBERS = os.path.join(LP, "results_2026-10-31", "numbers.csv")
FRONTIER = os.path.join(LP, "results_2026-10-31", "frontier_seeds", "frontier_holm.json")
CHECKS = os.path.join(LP, "results_paper_compare_1112", "c_checks.json")
R1113 = os.path.join(LP, "results_paper_compare_1113")
C1_TABLE = os.path.join(R1113, "c1_area_table.json")
STAGE_PNG = os.path.join(HERE, "figures", "stage.png")
STAGE_JSON = os.path.join(HERE, "figures", "stage_numbers.json")
TOTAL = 24
ACCENT = "c2410c"
MINUS = "−"
DASH = "–"
B, NT = 32, 24          # body and note size in canvas px (16 pt and 12 pt)
DISTANCE_WEIGHT = "0.2"  # per metre; tools/decision_replay.py:173 (MOVE_COST_LAMBDA)
WARN = []


# ---------------------------------------------------------------- data

def numbers():
    out = {}
    with open(NUMBERS, newline="") as f:
        for row in csv.DictReader(f):
            try:
                out[row["key"]] = float(row["value"])
            except ValueError:
                pass
    return out


def paper_cells(slots):
    d = json.load(open(os.path.join(PROJECT, slots["paper_compare_json"])))
    cells = {}
    for c in d["cells"]:
        if c["reference"] == "apr" and c["variant"] == "B":
            cells[(c["scene"], c["arm"], c["fraction"])] = c
    return cells, d["meta"]["budgets"]


def c2_f1_853():
    """C2 on 853: F1 of the repeat tour against the first. The newest c2_*.json in results_paper_compare_1113
    holds it; while a rescore is rewriting that folder, the figure quoted in its NOTES.md item 3 stands in."""
    import glob
    files = sorted(glob.glob(os.path.join(R1113, "c2_*.json")))
    if files:
        v = json.load(open(files[-1]))["scenes"]["00853"]["f1"]
        if v is not None:
            return float(v)
    m = re.search(r"00853: F1 (0\.\d+)", open(os.path.join(R1113, "NOTES.md")).read())
    return float(m.group(1))


def leaves(d):
    if isinstance(d, dict):
        for k, v in d.items():
            if not k.startswith("_"):
                yield from leaves(v)
    else:
        yield d


def is_pending(d):
    return any(v is None for v in leaves(d))


def rnd(v, nd):
    """Round half away from zero on the printed decimal, so 0.575 prints 0.58 as WRITEUP.md does."""
    return Decimal(repr(round(v, 10))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)


def sg(v, nd=3):
    d = rnd(v, nd)
    return (f"{d:+}" if d else f"{d}").replace("-", MINUS)


def num(v, nd=1):
    return f"{rnd(v, nd)}".replace("-", MINUS)


def tbd(v, fmt):
    return ("TBD", FAINT) if v is None else (fmt(v), INK)


# ---------------------------------------------------------------- text helpers (with a fit check)

def est_lines(txt, size, w, mono=False):
    cpl = max(1, int(w / (size * (0.6 if mono else 0.52))))
    return sum(max(1, math.ceil(len(p) / cpl)) for p in txt.split("\n"))


def P(s, x, y, w, parts, size=B, color=BODY, line=1.4, mono=False, align=PP_ALIGN.LEFT, limit=1000, tag=""):
    """Write a paragraph and return the y below it. parts: a string, or a list of (text, style) with
    style b (bold, ink), n (normal), f (faint), a (accent, bold), m (mono, ink)."""
    if isinstance(parts, str):
        parts = [(parts, "n")]
    runs, plain = [], ""
    for t, st in parts:
        plain += t
        if st == "b":
            runs.append(run(t, size, INK, SANS, True))
        elif st == "a":
            runs.append(run(t, size, ACCENT, SANS, True))
        elif st == "f":
            runs.append(run(t, size, FAINT, SANS))
        elif st == "m":
            runs.append(run(t, size, INK, MONO))
        else:
            runs.append(run(t, size, color, MONO if mono else SANS))
    h = est_lines(plain, size, w, mono) * size * line
    text(s, x, y, w, h + 6, [runs], align, line)
    if y + h > limit:
        WARN.append(f"{tag or plain[:40]!r}: ends at y={y + h:.0f}")
    return y + h


def N(s, x, y, w, txt, limit=1000):
    """A note: 24 px, grey."""
    return P(s, x, y, w, txt, NT, MID, 1.4, limit=limit)


def lab(s, x, y, w, t):
    text(s, x, y, w, 34, [kick(t, NT, 0.14)])
    return y + 40


def box(s, x, y, w, head, body, size=B, fill=WASH, edge=RULE, dashed=False, hmin=0):
    """A shaded box with a bold lead-in. Returns the y below it."""
    plain = (head + " " if head else "") + body
    h = max(hmin, est_lines(plain, size, w - 56) * size * 1.5 + 44)
    r = rect(s, x, y, w, h, fill, edge, 2 if dashed else 1)
    if dashed:
        r.line.dash_style = MSO_LINE.DASH
    runs = ([run(head + " ", size, INK, SANS, True)] if head else []) + [run(body, size, BODY)]
    fill_frame(r.text_frame, [runs], line=1.5, anchor=MSO_ANCHOR.MIDDLE, margins=(28, 18, 28, 18))
    if y + h > 995:
        WARN.append(f"box {plain[:40]!r}: ends at y={y + h:.0f}")
    return y + h


def box_bottom(s, head, body, size=B, bottom=990, x=120, w=1680):
    plain = head + " " + body
    h = est_lines(plain, size, w - 56) * size * 1.5 + 44
    return box(s, x, bottom - h, w, head, body, size)


def pill(s, x, y, w, h, txt, fill=RULE, color=MID):
    r = rect(s, x, y, w, h, fill)
    fill_frame(r.text_frame, [run(txt, NT, color, SANS, True, spacing=0.1)], PP_ALIGN.CENTER, 1.0,
               MSO_ANCHOR.MIDDLE)


def frame(prs, n, k, title, pending=None, backup=False):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    text(s, 120, 80, 1380, 34, [kick(k, NT, 0.14)])
    text(s, 120, 123, 1680, 74, [run(title, 56, INK, LIGHT, spacing=-0.02)], line=1.15)
    hline(s, 120, 222, 1800, 222, RULE)
    text(s, 120, 1018, 1200, 30, [run("Right in meaning, wrong in place? · End-sem", NT, FAINT)])
    text(s, 1400, 1018, 400, 30, [run("Backup" if backup else f"{n:02d} / {TOTAL}", NT, FAINT)], PP_ALIGN.RIGHT)
    if pending:
        pill(s, 1500 if len(pending) < 16 else 1380, 76, 300 if len(pending) < 16 else 420, 38, pending)
    if len(title) > 50:
        WARN.append(f"title may wrap: {title!r}")
    return s


def stat(s, x, y, w, value, label, size=56, label_lines=2):
    hline(s, x, y, x + w, y, RULE)
    text(s, x, y + 12, w, size * 1.2, [run(value, size, INK, LIGHT)], line=1.1)
    ly = y + 12 + size * 1.2 + 6
    return P(s, x, ly, w, label, NT if label_lines == 0 else B, MID if label_lines == 0 else BODY, 1.35)


# ---------------------------------------------------------------- 1. Cover

def cover(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    text(s, 160, 120, 1600, 34, [kick("End-sem · Computer vision and perception", NT, 0.14)])
    text(s, 160, 180, 1600, 250, [run("Right in meaning,", 112, INK, LIGHT, spacing=-0.03),
                                  run("wrong in place?", 112, INK, LIGHT, spacing=-0.03)], line=1.05)
    P(s, 160, 440, 1560, "ASP asks a language model to guess the rooms and objects a robot has not seen, then "
                         "drives to where the guesses disagree. Its author says the guesses are often in the wrong "
                         "place but name the right things, and that this is enough. We test that in three parts.",
      B, BODY, 1.45)
    cols = [("Part 1 · Live test", "Do the guesses improve a live map? Done."),
            ("Part 2 · Paper's scale", "Our scores beside the paper's. The 871 numbers are being rerun."),
            ("Part 3 · The author's defense", "Is the meaning right? Is it enough? Is it the model?")]
    for i, (name, body) in enumerate(cols):
        x = 160 + i * 552
        hline(s, x, 650, x + 496, 650, INK, 2)
        text(s, x, 664, 496, 34, [run(f"{i + 1:02d}", NT, FAINT, MONO)])
        P(s, x, 704, 496, [(name, "b")], B, line=1.3)
        P(s, x, 756, 496, body, B, BODY, 1.35, limit=900)
    hline(s, 160, 930, 1760, 930, RULE)
    text(s, 160, 950, 900, 34, [run("Sher Partap Singh · Preesha Katial · Ananya Singla", NT, MID)])
    text(s, 860, 950, 900, 34, [run("Base paper: Tang & Chaudhari, Active Semantic Perception, arXiv:2510.05430",
                                    NT, MID)], PP_ALIGN.RIGHT)


# ---------------------------------------------------------------- 2. ASP in one picture

OBSERVED = [(0.15, 0.25), (0.45, 0.72), (0.82, 0.30)]
GUESSES = [[(.62, .80), (.90, .62), (.30, .08)], [(.10, .78), (.70, .90), (.92, .10)],
           [(.55, .10), (.95, .50), (.25, .92)], [(.04, .50), (.62, .52), (.85, .88)],
           [(.36, .30), (.72, .08), (.15, .95)], [(.95, .90), (.30, .52), (.60, .04)],
           [(.08, .06), (.55, .95), (.98, .30)], [(.70, .46), (.20, .62), (.45, .02)]]


def glyph(s, x, y, w, h, member=None, r=6):
    def pt(p):
        return x + p[0] * w, y + p[1] * h
    obs = [pt(p) for p in OBSERVED]
    gs = [pt(p) for p in GUESSES[member]] if member is not None else []
    hline(s, *obs[0], *obs[1], MID, 2)
    hline(s, *obs[1], *obs[2], MID, 2)
    for g in gs:
        near = min(obs, key=lambda o: (o[0] - g[0]) ** 2 + (o[1] - g[1]) ** 2)
        hline(s, *near, *g, ACCENT, 1)
    for o in obs:
        oval(s, o[0], o[1], r, INK)
    for g in gs:
        oval(s, g[0], g[1], r, WHITE, ACCENT, 2)


def asp_picture(prs):
    s = frame(prs, 2, "ASP in one picture", "ASP scores views by disagreement, not by truth")
    top, h = 262, 300

    def panel(x, w, head):
        rect(s, x, top, w, h, WASH, RULE)
        lab(s, x + 20, top + 16, w - 40, head)

    def arrow(x):
        svg_text(s, x + 25, top + h / 2 + 18, "→", 56, FAINT, anchor="middle", w=70)

    panel(120, 270, "Map so far")
    glyph(s, 150, top + 90, 210, 130, None, 8)
    text(s, 145, top + 245, 230, 34, [run("dots: mapped", NT, MID)])
    arrow(390)
    panel(440, 570, "8 guessed graphs")
    for i in range(8):
        glyph(s, 465 + (i % 4) * 135, top + 78 + (i // 4) * 108, 112, 82, i, 5)
    arrow(1010)
    panel(1060, 380, "Each view")
    P(s, 1080, top + 70, 340, "What a camera there sees in each graph, and how far the 8 differ.", B, BODY, 1.35,
      limit=top + h)
    arrow(1440)
    panel(1490, 310, "Pick")
    P(s, 1510, top + 70, 270, "The view with the top score.", B, BODY, 1.35, limit=top + h)

    text(s, 120, 590, 1680, 60, [run(f"score = gain(objects) + gain(rooms) {MINUS} {DISTANCE_WEIGHT} × distance",
                                     36, INK, MONO)], PP_ALIGN.CENTER, 1.3)
    cols = [("Gain", "The 8 graphs' disagreement about the view. All agree: zero."),
            ("Truth", "No term asks if a guess is true."),
            ("Unknown space", "No term asks if the space is unexplored.")]
    for i, (head, body) in enumerate(cols):
        x = 120 + i * 580
        hline(s, x, 670, x + 520, 670, INK, 2)
        P(s, x, 686, 520, [(head, "b")], B, line=1.3)
        P(s, x, 736, 520, body, B, BODY, 1.35, limit=880)
    box_bottom(s, "Reading.", "A guess earns score by differing from the others, not by being right.", bottom=990)


# ---------------------------------------------------------------- 3. Part 1, contrasts

def live_test(prs, Nn):
    s = frame(prs, 3, "Part 1 · Live test · 2 homes, seeds 42-44, human labels",
              "Live test: no detectable difference")
    L = 120
    lab(s, L, 250, 1680, "Difference in F1, area under the curve to 60 m; 95% interval")
    fr = json.load(open(FRONTIER))
    # E2 is registered as official minus filter_only; the slide shows filter minus LLM, so its sign flips.
    e2 = (-Nn["E2:hm3d:60m:statistic"], -Nn["E2:hm3d:60m:permutation_hi"], -Nn["E2:hm3d:60m:permutation_lo"])
    rows = [("LLM guesses vs random guesses",
             (Nn["E1:hm3d:60m:statistic"], Nn["E1:hm3d:60m:permutation_lo"], Nn["E1:hm3d:60m:permutation_hi"])),
            ("LLM + our filter vs LLM", e2),
            ("LLM vs plain frontier", (fr["official"]["d60"], *fr["official"]["ci60"])),
            ("Random guesses vs plain frontier", (fr["placebo"]["d60"], *fr["placebo"]["ci60"])),
            ("Exact objects vs random (871)", (Nn["E3:hm3d:60m:statistic"], None, None))]
    x0, x1, lo, hi = 700, 1180, -0.08, 0.10

    def dx(v):
        return x0 + (min(max(v, lo), hi) - lo) / (hi - lo) * (x1 - x0)

    top, step = 330, 78
    for v in (-0.05, 0.0, 0.05):
        hline(s, dx(v), top - 24, dx(v), top + step * len(rows) - 34, LINE if v else MID, 1 if v else 2,
              dash=bool(v))
        svg_text(s, dx(v), top + step * len(rows) + 8, sg(v, 2) if v else "0", NT, FAINT, anchor="middle", w=100)
    for i, (name, (d, a, b)) in enumerate(rows):
        y = top + i * step + 14
        text(s, L, y - 20, 570, 40, [run(name, 28, INK)], line=1.3)
        if a is None:
            hline(s, dx(lo), y, dx(hi), y, INK, 3, dash=True)
            svg_text(s, dx(lo) - 2, y + 9, "◀", 24, INK, anchor="end", w=30)
            svg_text(s, dx(hi) + 2, y + 9, "▶", 24, INK, w=30)
            tail = f"{sg(d)}  (p {num(Nn['E3:hm3d:60m:p'], 2)}; no bounds)"
        else:
            hline(s, dx(a), y, dx(b), y, INK, 3)
            tail = f"{sg(d)}  ({sg(a)} to {sg(b)})"
        oval(s, dx(d), y, 11, INK, WHITE, 3)
        svg_text(s, x1 + 50, y + 9, tail, 28, INK, MONO, w=600)
    y = N(s, L, top + step * len(rows) + 40, 1680,
          "Registered tests, pilot status. The filter row was registered as LLM minus filter; its sign is flipped "
          "here. Exact objects: one house (871), 3 runs against 3, kept under deviation 26; the smallest p such a "
          "test can give is 0.10. Frontier rows: frontier stopped more often on 871, and its paths almost never "
          "crossed wall cells, so the comparison may tilt in an unknown direction.", limit=900)
    box_bottom(s, "Registered reading.", "No detectable difference in any contrast.")


# ---------------------------------------------------------------- 4. Part 1, why

def why(prs, Nn):
    s = frame(prs, 4, "Part 1 · Why · exploratory, offline replay of saved stages",
              "Why: swapping the guesses barely moves the pick")
    L = 120
    lab(s, L, 250, 840, "Pick move, median m · 121 stages")
    bars = [("LLM → random set", Nn["replay:official:move_plc"]),
            ("Random set → another", Nn["replay:official:move_floor"])]
    for i, (name, v) in enumerate(bars):
        y = 304 + i * 66
        text(s, L, y, 400, 40, [run(name, 28, INK)], line=1.3)
        rect(s, 540, y + 4, v / 3.0 * 270, 32, INK if i == 0 else MID)
        svg_text(s, 540 + v / 3.0 * 270 + 14, y + 32, f"{v:.2f}", 28, INK, MONO, w=100)
    d, a, b = (Nn["replay:official:diff_move_plc_minus_floor"], Nn["replay:official:diff_move_plc_minus_floor:ci_lo"],
               Nn["replay:official:diff_move_plc_minus_floor:ci_hi"])
    stat(s, L, 450, 380, sg(d, 2) + " m", f"({sg(a, 2)} to {sg(b, 2)})")
    od, oa, ob = (Nn["replay:official:diff_move_oracle_minus_floor"],
                  Nn["replay:official:diff_move_oracle_minus_floor:ci_lo"],
                  Nn["replay:official:diff_move_oracle_minus_floor:ci_hi"])
    stat(s, 540, 450, 380, sg(od, 2) + " m", f"({sg(oa, 2)} to {sg(ob, 2)})")
    text(s, L, 596, 380, 34, [run("LLM v random, beyond a redraw", NT, MID)])
    text(s, 540, 596, 400, 34, [run("exact objects v random", NT, MID)])
    N(s, L, 650, 820,
      f"The exact-object shift holds on 853 stages ({sg(Nn['replay:oracle_minus_floor:00853'], 2)} m, "
      f"{sg(Nn['replay:oracle_minus_floor:00853:ci_lo'], 2)} to {sg(Nn['replay:oracle_minus_floor:00853:ci_hi'], 2)}) "
      f"and not on 871 stages ({sg(Nn['replay:oracle_minus_floor:00871'], 2)} m, "
      f"{sg(Nn['replay:oracle_minus_floor:00871:ci_lo'], 2)} to {sg(Nn['replay:oracle_minus_floor:00871:ci_hi'], 2)}).")

    R = 1000
    lab(s, R, 250, 800, "View ranking, median rho · 119 stages")
    cols = [("LLM's guesses", Nn["cf:rho_score_U360_median:official:actual"]),
            ("Random set", Nn["cf:rho_score_U360_median:official:plc"]),
            ("No guesses", Nn["cf:rho_score_U360_median:official:obs"]),
            ("Exact objects", Nn["cf:rho_score_U360_median:official:orc"])]
    base, sc = 560, 300
    hline(s, R, base, R + 800, base, MID, 2)
    for i, (name, v) in enumerate(cols):
        cx = R + 100 + i * 200
        hgt = abs(v) * sc
        rect(s, cx - 45, base - hgt if v >= 0 else base, 90, max(hgt, 2), INK if i != 3 else MID)
        svg_text(s, cx, (base - hgt - 12) if v >= 0 else (base + hgt + 32), num(v, 2), 28, INK, MONO,
                 anchor="middle", w=120)
        text(s, cx - 95, 640, 190, 70, [run(name, NT, BODY)], PP_ALIGN.CENTER, 1.3)
    N(s, R, 720, 800,
      f"The LLM's guesses add {sg(Nn['cf:paired_actual_minus_placebo_median:official'], 2)} over a random set "
      "(paired median, 73 of 119 stages). Exact objects score high in part by construction.")
    box_bottom(s, "Reading.", "The LLM's guesses add a little ranking over random ones, but do not move the pick "
                              "more than a redraw does.")


# ---------------------------------------------------------------- 5. Part 1, where the guesses land

def land(prs, Nn):
    s = frame(prs, 5, "Part 1 · Where the guesses land", "Near a real object, but rarely close")
    lab(s, 120, 250, 1680, "New objects near a real object with the same name: LLM v random guesses")
    for i, m in enumerate(("0.5", "1", "2")):
        x = 120 + i * 580
        o = Nn[f"precision_pooled:official:final:{m}m"]
        p = Nn[f"precision_pooled:placebo:final:{m}m"]
        hline(s, x, 310, x + 520, 310, RULE)
        text(s, x, 322, 540, 90, [run(f"{num(100 * o)}% v {num(100 * p)}%", 64, INK, LIGHT)], line=1.1)
        P(s, x, 410, 520, f"within {m} m", B, BODY, 1.3)
    far = 100 * (1 - Nn["precision_pooled:official:final:0.5m"])
    P(s, 120, 520, 1680, f"The LLM lands near a real object about 6 times as often as random guesses do. Still, "
                         f"{far:.0f}% of its objects miss by more than 0.5 m.", B, BODY, 1.45)
    N(s, 120, 680, 1680,
      f"Counted live runs, both homes, per (stage, member) guess. By home, within 0.5 m: 853 "
      f"{num(100 * Nn['precision05:official:00853:final'])}% v {num(100 * Nn['precision05:placebo:00853:final'])}%; "
      f"871 {num(100 * Nn['precision05:official:00871:final'])}% v {num(100 * Nn['precision05:placebo:00871:final'])}%. "
      "Not tested.")
    box_bottom(s, "Reading.", "Right place is rare. This is the “wrong in place” half of the claim.")


# ---------------------------------------------------------------- 6. Part 1, limits

def live_limits(prs, Nn):
    s = frame(prs, 6, "Part 1 · Limits of the live test", "Live test limits: what it could not rule out")
    xs, w = (120, 700, 1280), 520
    cols = [(sg(Nn["E1:hm3d:60m:permutation_hi"]), "top of the interval, LLM − random",
             "A real gain of this size stays possible. The test saw only gains of 0.024 to 0.028 or more."),
            ("5 of 5", "pairs differ in pacing",
             f"Members agree on {num(100 * Nn['agreement:same_label_1m:official'])}% of the LLM's guesses, "
             f"{num(100 * Nn['agreement:same_label_1m:placebo'])}% of random ones."),
            (sg(Nn["secondary:E1:f1point60:statistic"]), "F1 at 60 m: the LLM arm led",
             f"p {num(Nn['secondary:E1:f1point60:p'], 3)}, and {num(Nn['holm_E1_secondaries:f1point60'], 2)} after "
             f"correction. At 30 m: {sg(Nn['secondary:E1:f1point30:statistic'])}.")]
    for x, (big, labl, body) in zip(xs, cols):
        hline(s, x, 262, x + w, 262, INK, 2)
        text(s, x, 274, w, 70, [run(big, 56, INK, LIGHT)], line=1.1)
        P(s, x, 346, w, labl, NT, MID, 1.35)
        P(s, x, 420, w, body, B, BODY, 1.4, limit=700)
    hline(s, 120, 640, 1800, 640, RULE)
    y = lab(s, 120, 654, 1680, "Our filter, live")
    P(s, 120, y + 4, 1680,
      f"{sg(-Nn['E2:hm3d:60m:statistic'])} ({sg(-Nn['E2:hm3d:60m:permutation_hi'])} to "
      f"{sg(-Nn['E2:hm3d:60m:permutation_lo'])}): no detectable difference. It removed "
      f"{num(100 * Nn['validator:removed_share:all'], 0)}% of new guesses ({int(Nn['validator:removed_new:all']):,} of "
      f"{int(Nn['validator:raw_new:all']):,}); {num(100 * Nn['validator:precision_kept_0.5:all'])}% of what it kept "
      f"were hits within 0.5 m, against {num(100 * Nn['validator:precision_raw_0.5:all'])}% of all.",
      B, BODY, 1.4, limit=840)
    box_bottom(s, "Reading.", "No detectable difference at this size. That is not proof of no effect.")


# ---------------------------------------------------------------- 7. Part 2, rules and budget

def timeline(s, x0, x1, y, budget, mark):
    hline(s, x0, y, x1, y, MID, 2)
    for frac in (0.1, 0.5, 1.0):
        xx = x0 + (x1 - x0) * frac
        hline(s, xx, y - 12, xx, y + 12, INK, 2)
        svg_text(s, xx, y - 22, f"{int(round(frac * 100))}%", NT, FAINT, anchor="middle", w=100)
        svg_text(s, xx, y + 50, f"{frac * budget:.0f} s", 28, INK, MONO, anchor="middle", w=140)
    if mark:
        text(s, x0, y + 66, 600, 30, [run("TO BE UPDATED", NT, ACCENT, SANS, True, spacing=0.1)])


def paper_rules(prs, budgets, checks, slots):
    s = frame(prs, 7, "Part 2 · Same rules as the paper", "Same rules as the paper")
    upd = slots["table871_updated"]
    stops = [checks[sc]["use_rule"]["reached"] for sc in ("00853", "00871")]
    L, w = 120, 780
    blocks = [("Scoring.", "The author's own F1 and GED code, on the paper's time axis."),
              ("Reference.", f"A scripted stand-in for the author's hand-driven tour: navmesh paths, the same mapper "
                             f"({stops[0]} and {stops[1]} stops)."),
              ("Frontier.", "Run to its natural end: 5 of 5 runs on 853, 1 of 5 on 871."),
              ("LLM.", "Ours is DeepSeek. The paper's is Gemini 2.5 Pro.")]
    y = 262
    for head, body in blocks:
        y = P(s, L, y, w, [(head + " ", "b"), (body, "n")], B, BODY, 1.4, limit=960) + 26
    R = 980
    lab(s, R, 250, 820, "What “budget” means")
    P(s, R, 300, 820, "The paper gives no value for its budget. We set one for each home.", B, BODY, 1.4)
    text(s, R, 478, 150, 40, [run("Home 853", 28, INK, SANS, True)])
    timeline(s, R + 190, R + 790, 510, budgets["00853"], False)
    N(s, R, 592, 820, "Median end of 5 frontier runs (612 to 868 s).")
    text(s, R, 718, 150, 40, [run("Home 871", 28, INK, SANS, True)])
    timeline(s, R + 190, R + 790, 750, budgets["00871"], not upd)
    N(s, R, 850, 820, "Fallback: only 1 of 5 frontier runs finished. The reruns replace it with a median.")


# ---------------------------------------------------------------- 8 and 9. Part 2, tables

def stat_cell(C, scene, arm, frac):
    c = C[(scene, arm, frac)]
    sv = c["stage_value_x100"]
    if not sv["n"] or sv["n"] * 2 < c["n_runs"]:
        return None, "no run reaches it" if not sv["n"] else f"{sv['n']} of {c['n_runs']} runs"
    n = f"n={sv['n']}" if sv["n"] == c["n_runs"] else f"n={sv['n']} of {c['n_runs']}"
    return f"{sv['mean']:.1f} [{sv['min']:.1f}{DASH}{sv['max']:.1f}]", n


def table(s, x, y, lw, cw, rows, rowh):
    """rows: (label, cells, kind) with cells [(main, sub, main_color, sub_color)], kind paper|ours|slot."""
    for j, head in enumerate(("10%", "50%", "100%")):
        svg_text(s, x + lw + j * cw + cw / 2, y + 34, head, 28, MID, SANS, anchor="middle", w=cw)
    y += 46
    hline(s, x, y, x + lw + 3 * cw, y, LINE)
    for lab_, cells, kind in rows:
        rh = rowh[kind]
        if kind == "slot":
            r = rect(s, x, y + 3, lw + 3 * cw, rh - 6, WASH, LINE, 2)
            r.line.dash_style = MSO_LINE.DASH
        text(s, x + 8, y + (rh - 40) / 2, lw - 10, 40, [run(lab_, 28, INK if kind == "paper" else BODY)], line=1.2)
        for j, (main, sub, mc, sc) in enumerate(cells):
            cx = x + lw + j * cw
            if kind == "paper":
                text(s, cx, y + 12, cw, 40, [run(main, 32, mc, MONO)], PP_ALIGN.CENTER, 1.2)
            else:
                text(s, cx, y + 8, cw, 40, [run(main, 32, mc, MONO)], PP_ALIGN.CENTER, 1.2)
                if sub:
                    text(s, cx, y + 50, cw, 30, [run(sub, NT, sc)], PP_ALIGN.CENTER, 1.2)
        y += rh
        hline(s, x, y, x + lw + 3 * cw, y, RULE)
    return y


def table_rows(C, scene, arms, mark, full=None):
    def paper(arm):
        return [(f"{C[(scene, arm, f)]['paper_f1_x100']:.1f}", None, INK, MID) for f in ("10", "50", "100")]
    rows = [("Paper · ASP", paper("official"), "paper"), ("Paper · frontier", paper("frontier_end"), "paper")]
    names = {"official": "Ours · ASP", "filter_only": "Ours · ASP + filter", "placebo": "Ours · random guesses",
             "frontier_end": "Ours · frontier"}
    for arm in arms:
        cells = []
        for f in ("10", "50", "100"):
            main, sub = stat_cell(C, scene, arm, f)
            if mark:
                cells.append((main or "none", (sub + " · to be updated") if main else "to be updated",
                              FAINT, ACCENT))
            else:
                cells.append((main or "none", sub, INK if main else FAINT, MID))
        rows.append((names[arm], cells, "ours"))
    if full is not None:
        cells = []
        for f in ("10", "50", "100"):
            d = full[f]
            if d["mean"] is None:
                cells.append(("TBD", "may be run", FAINT, MID))
            else:
                cells.append((f"{d['mean']:.1f} [{d['min']:.1f}{DASH}{d['max']:.1f}]",
                              f"n={full['runs']}" if full["runs"] else None, INK, MID))
        rows.append(("Ours · ASP, full budget", cells, "slot"))
    return rows


def table853(prs, C, budgets, slots):
    full = slots["asp853_full_budget"]
    s = frame(prs, 8, f"Part 2 · Object F1 × 100, mean [min{DASH}max] · home 853 · budget "
                       f"{budgets['00853']:.0f} s", "On 853, the paper's ASP lead did not appear",
              pending="ONE ROW PENDING" if is_pending(full) else None)
    y = table(s, 120, 250, 500, 380, table_rows(C, "00853", ("official", "filter_only", "placebo", "frontier_end"),
                                                 False, full), {"paper": 62, "ours": 90, "slot": 90})
    N(s, 120, y + 14, 1680,
      "Paper: Fig. 4 (left), one run. Ours: runs that reach that time, shown if at least half do. ASP stops at "
      "60 m. The paper's lead did not appear on 853 at 10% and 50%, with DeepSeek and a rebuilt reference.", limit=1000)


def table871(prs, C, budgets, slots):
    upd = slots["table871_updated"]
    s = frame(prs, 9, f"Part 2 · Object F1 × 100, mean [min{DASH}max] · home 871 · budget "
                       f"{budgets['00871']:.0f} s", "On 871, our numbers are to be updated",
              pending=None if upd else "TO BE UPDATED")
    y = table(s, 120, 250, 500, 380, table_rows(C, "00871", ("official", "filter_only", "placebo", "frontier_end"),
                                                 not upd), {"paper": 62, "ours": 90, "slot": 90})
    N(s, 120, y + 14, 1680,
      "The paper's cells do not change. Ours will: four frontier runs and the repeat tour are being rerun, and the "
      "budget moves with them. Do not read these cells yet.", limit=1000)


# ---------------------------------------------------------------- 10. Part 2, limits of the reference

def limits_reference(prs, checks, f1):
    s = frame(prs, 10, "Part 2 · Limits of the reference", "The reference is rebuilt, and it moves")
    rec = [checks[sc]["C3"]["apr_a_recall_vs_hm3d"] for sc in ("00853", "00871")]
    c1t = json.load(open(C1_TABLE))
    L, w = 120, 900
    y = P(s, L, 262, w, [("Rebuilt. ", "b"), (f"It holds {100 * rec[0]:.0f}% and {100 * rec[1]:.0f}% of the "
                                                "human-labelled objects (853, 871).", "n")], B, BODY, 1.4)
    y = P(s, L, y + 24, w, [("Repeat tour. ", "b"),
                            (f"On 853 it is not frozen, and the two tours agree at F1 {f1:.3f} (C2). That is below "
                             "the 0.90 line: the reference itself moves by more than the paper's margins. The first "
                             "tour's damage is mixed in. On 871 the repeat tour is pending.", "n")], B, BODY, 1.4,
          limit=960)
    N(s, L, y + 16, w, "Nvblox died partway through both first tours, so each reference lacks about its last 60 s.",
      limit=1000)
    R = 1060
    lab(s, R, 250, 740, "Check C1: size of the reference")
    rows = [("Rooms, ours", [str(checks[sc]["C1"]["room_nodes"]) for sc in ("00853", "00871")]),
            ("Rooms, paper", [str(checks[sc]["C1"]["paper_rooms"]) for sc in ("00853", "00871")]),
            ("Navmesh island, m²", [f"{checks[sc]['C1']['start_island_area_m2']:.0f}" for sc in ("00853", "00871")]),
            ("Waypoint grid, m²", [num(checks[sc]["C1"]["kept_area_estimate_m2"], 0) for sc in ("00853", "00871")]),
            ("Labelled floor, m²", [num(c1t[sc]["labelled_floor_m2"], 0) for sc in ("00853", "00871")]),
            ("Outline of all labelled geometry, m²", [num(c1t[sc]["footprint_hull_m2"], 0) for sc in ("00853", "00871")]),
            ("Paper, m²", [f"{checks[sc]['C1']['paper_area_m2']:.0f}" for sc in ("00853", "00871")])]
    for j, hd in enumerate(("853", "871")):
        svg_text(s, R + 560 + j * 90 + 40, 330, hd, 28, MID, anchor="middle", w=100)
    yy = 346
    hline(s, R, yy, R + 740, yy, LINE)
    for name, vals in rows:
        text(s, R, yy + 14, 560, 40, [run(name, 26, BODY)], line=1.2)
        for j, v in enumerate(vals):
            text(s, R + 560 + j * 90, yy + 12, 80, 40, [run(v, 32, INK, MONO)], PP_ALIGN.RIGHT, 1.2)
        yy += 62
        hline(s, R, yy, R + 740, yy, RULE)
    paper = {sc: checks[sc]["C1"]["paper_area_m2"] for sc in ("00853", "00871")}
    ratio = [paper[sc] / c1t[sc]["navmesh_start_island_m2"] for sc in ("00853", "00871")]
    within = max(abs(paper[sc] - c1t[sc]["footprint_hull_m2"]) / c1t[sc]["footprint_hull_m2"] for sc in paper)
    N(s, R, yy + 14, 740, f"The paper's figure is {num(ratio[0], 1)} and {num(ratio[1], 1)} times the walkable floor "
                          f"and within about {num(100 * within, 0)}% of the outline of everything labelled. We do not "
                          "know how the paper measured area.", limit=1012)


# ---------------------------------------------------------------- 11. Part 2, limits of the runs

def limits_runs(prs, C):
    s = frame(prs, 11, "Part 2 · Limits of the runs", "What limits the runs")

    def rng(arm, frac):
        sv = C[("00853", arm, frac)]["stage_value_x100"]
        return f"{sv['mean']:.1f} [{sv['min']:.1f}{DASH}{sv['max']:.1f}]"
    L, w = 120, 1680
    y = P(s, L, 262, w, [("Two batches of one frontier explorer. ", "b"),
                         (f"On 853 at 50% of the budget: {rng('frontier_60m', '50')} in October (3 runs, cut at 60 m) "
                          f"and {rng('frontier_end', '50')} in November (5 runs, to the natural end). At 10%: "
                          f"{rng('frontier_60m', '10')} and {rng('frontier_end', '10')}. The ranges overlap.", "n")],
          B, BODY, 1.4)
    y = P(s, L, y + 28, w, [("ASP stops at 60 m. ", "b"),
                            ("No ASP run reaches 100% of the budget. ASP ran in October and frontier in November.",
                             "n")], B, BODY, 1.4)
    y = P(s, L, y + 28, w, [("The clocks differ. ", "b"),
                            ("In the host's copy of the code, frontier's clock also counts its waits for a path; "
                             "ASP's does not.", "n")], B, BODY, 1.4)
    N(s, L, y + 12, w, "The clock finding comes from the host's patched copy; we have not checked it against the "
                       "released code.")
    box_bottom(s, "Reading.", "We read the table as a check on scale. It does not test the paper's claim.")


# ---------------------------------------------------------------- 12. Part 3, the defense

def defense(prs):
    s = frame(prs, 12, "Part 3", "The author's defense, in three questions")
    P(s, 120, 262, 1680, "The author: often wrong in place, but right in meaning, and that is enough.",
      B, INK, 1.4)
    steps = [("Is the meaning right?", "Beat the controls: baselines that see the same map."),
             ("Is it enough for ASP?", "Give ASP true labels, moved by real error."),
             ("Is it the model?", "Replay Claude on the same 44 saved inputs.")]
    for i, (name, what) in enumerate(steps):
        x = 120 + i * 580
        hline(s, x, 420, x + 520, 420, INK, 2)
        y = P(s, x, 440, 520, [(name, "b")], B, line=1.3)
        P(s, x, y + 12, 520, what, B, BODY, 1.35, limit=800)
    box_bottom(s, "Blind test:", "the scorer was frozen first.")


# ---------------------------------------------------------------- 13. Part 3, a hit and a miss on one real stage

def picture_levels(prs, slots):
    n = json.load(open(STAGE_JSON))
    chance = slots["blind"]["models"]["opus"]
    s = frame(prs, 13, "Part 3", "A hit and a miss, on one stage")
    s.shapes.add_picture(STAGE_PNG, px(120), px(250), px(730), px(730))
    X, w = 900, 900
    y = 256

    def row(draw, txt, dy=40):
        nonlocal y
        draw(y)
        text(s, X + 112, y + 2, w - 112, 38, [run(txt, 28, BODY)], line=1.2)
        y += dy

    def d_nodes(yy):
        rect(s, X + 10, yy + 10, 20, 20, WHITE, INK, 3)
        oval(s, X + 64, yy + 20, 6, INK)

    def d_regions(yy):
        for i, c in enumerate(("e5e7eb", "cbd5e1", "fde8dc")):
            rect(s, X + 6 + i * 32, yy + 8, 28, 22, c)

    def d_open(yy):
        rect(s, X + 6, yy + 8, 28, 22, "fde8dc", ACCENT, 4)
        r = rect(s, X + 44, yy + 8, 28, 22, WHITE, ACCENT, 2)
        r.line.dash_style = MSO_LINE.DASH

    def d_hit(yy):
        svg_text(s, X + 30, yy + 32, "★", 34, ACCENT, anchor="middle", w=60)

    def d_miss(yy):
        svg_text(s, X + 30, yy + 32, "✖", 28, INK, anchor="middle", w=60)

    row(d_nodes, "Mapped rooms, objects")
    row(d_regions, "Seen, partly seen, unobserved")
    row(d_open, "Open room type, 0.5 m reach")
    row(d_hit, f"Opus guess: {n['guess_hit']['label']}, a hit")
    row(d_miss, f"Opus guess: {n['guess_miss']['label']}, a miss", 56)
    y = P(s, X, y, w, [("L1, rooms: ", "b"), ("the type is still open.", "n")], B, BODY, 1.3)
    y = P(s, X, y + 8, w, [("L2, objects: ", "b"), ("the class is still open.", "n")], B, BODY, 1.3)
    y = P(s, X, y + 8, w, [("L3, roughly where: ", "b"), ("the guess reaches an unobserved region that fits it.", "n")], B, BODY, 1.3)
    P(s, X, y + 22, w, [("Base rate: ", "b"), (f"random guesses score {num(100 * chance['L1']['placebo_score'])}%, "
                                               f"{num(100 * chance['L2']['placebo_score'])}%, "
                                               f"{num(100 * chance['L3']['placebo_score'])}%.", "n")],
      B, BODY, 1.3, limit=1000)


# ---------------------------------------------------------------- 14. Part 3, controls

def controls(prs, slots):
    mg = slots["blind"]["models"]["opus"]
    s = frame(prs, 14, "Part 3", "What each guess is compared with")
    mtxt = ", ".join(num(100 * mg[lv]["margin"], 0) for lv in ("L1", "L2", "L3"))
    y = P(s, 120, 252, 1680, f"A control sees the same map. Margin: the gain over it we would count ({mtxt} "
                             "points at L1, L2, L3). Named: the control the verdict uses.", B, BODY, 1.4)
    items = [("Prior from 179 other houses", "L1, L2 · named"), ("Random guesses", "L1, L2"),
             ("Own labels, swapped among guesses", "L3"), ("Regions, trading contents", "L3 · named"),
             ("Prior's labels at the model's places", "L3")]
    y += 20
    for txt, lv in items:
        y0 = y
        y = P(s, 120, y, 1280, txt, B, BODY, 1.35)
        text(s, 1400, y0 + 4, 400, 40, [run(lv, 28, MID, MONO)], PP_ALIGN.RIGHT, 1.2)
        hline(s, 120, y + 12, 1800, y + 12, RULE)
        y += 30


# ---------------------------------------------------------------- 15. Part 3, the blind test

def pts(v, nd=1):
    """A fraction as signed points (x100)."""
    return sg(100 * v, nd)


def blind_table(prs, slots):
    b = slots["blind"]["models"]
    s = frame(prs, 15, "Part 3 · Blind test", "Blind test: the claim fails")
    cols = [("opus", "Opus 5.5", ""), ("haiku", "Haiku 5.5", ""), ("deepseek", "DeepSeek", "exploratory")]
    X, lw, cw = 120, 420, 420
    xs = [X + lw + i * cw for i in range(3)]
    for x, (_, name, sub) in zip(xs, cols):
        text(s, x, 246, cw - 10, 34, [kick(name, NT, 0.1)])
        if sub:
            text(s, x, 276, cw - 10, 30, [run(sub, NT, MID)])
    text(s, X + 90, 276, lw - 90, 30, [run("difference, in points", NT, MID)])
    hline(s, X, 314, X + lw + 3 * cw, 314, LINE)
    rows = [("L1", "which rooms", "prior"), ("L2", "which objects", "prior"), ("L3", "roughly where", "region trade")]
    y = 322
    for lv, what, named in rows:
        text(s, X, y + 14, 90, 50, [run(lv, 36, INK, MONO)], line=1.2)
        text(s, X + 90, y + 12, lw - 90, 36, [run(what, 28, BODY)], line=1.2)
        e0 = b["opus"][lv]
        text(s, X + 90, y + 50, lw - 90, 60, [run(f"v {named}, margin {num(100 * e0['margin'], 0)}", NT, MID)],
             line=1.3)
        for x, (key, _, _) in zip(xs, cols):
            e = b[key][lv]
            # two decimals only where the verdict turns on them: Opus L3's upper end, 2.95 against 3
            hi = pts(e["hi"], 2) if (key == "opus" and lv == "L3") else pts(e["hi"])
            text(s, x, y + 4, cw - 20, 44, [[run(pts(e["diff"]), 32, INK, MONO),
                                             run("  " + e["verdict"], NT, INK, SANS, True)]], line=1.2)
            text(s, x, y + 44, cw - 20, 32, [run(f"[{pts(e['lo'])}, {hi}]", NT, MID, MONO)], line=1.2)
            if lv == "L3":
                tail = f"score {num(100 * e['score'], 1)}% · random {num(100 * e['placebo_score'], 1)}%"
            else:
                tail = f"score {num(100 * e['score'], 1)}% · v random {pts(e['placebo']['diff'])}"
            text(s, x, y + 78, cw - 20, 32, [run(tail, NT, MID)], line=1.2)
        y += 128
        hline(s, X, y, X + lw + 3 * cw, y, RULE)
    N(s, X, y + 8, 1680,
      "Difference = model minus comparator. Score = hit rate, mean over 12 clusters (home, seed, arm). One run with "
      "the frozen scorer; no other run is recorded. Opus L3 shows two decimals: its upper end, 2.95, is just under "
      "the margin, 3.", limit=905)
    box_bottom(s, "Rejected:", "the interval rules out a gain over the named comparator as large as the margin. It "
                               "does not say the model is worse. At L2 the interval lies wholly below zero, so both "
                               "models are worse than the prior.")


# ---------------------------------------------------------------- 16. Part 3, two facts against the headline

def facts(prs, slots):
    b = slots["blind"]["models"]
    chk = slots["blind"]["opus_l3_check"]
    hh = b["haiku"]["L2"]["placebo"]
    s = frame(prs, 16, "Part 3", "Two facts")
    t1 = (f"the top of the interval is {num(100 * chk['registered_upper'], 2)} points, the margin "
          f"{num(100 * chk['margin'], 0)}. {chk['runs']} reruns of the region trade after the result "
          f"(deviation 55): {num(100 * chk['rerun_min'], 2)} to {num(100 * chk['rerun_max'], 2)}.")
    t2 = (f"is {num(100 * hh['diff'], 1)} points above random guesses (p {num(hh['p'], 3)}; one contrast, "
          "not adjusted).")
    hm = max(est_lines("Opus at L3 is close: " + t1, B, 764), est_lines("Haiku at L2 " + t2, B, 764)) * B * 1.5 + 44
    box(s, 120, 270, 820, "Opus at L3 is close:", t1, B, hmin=hm)
    box(s, 980, 270, 820, "Haiku at L2", t2, B, hmin=hm)
    box_bottom(s, "At L2,", "in these two houses, a prior from 179 other houses, making as many claims as the "
                            "model, scored above both models at naming objects.")


# ---------------------------------------------------------------- 17. Part 3, what the test could see

def detect(prs, slots):
    m = slots["blind"]["mdd"]
    ops = slots["blind"]["models"]
    s = frame(prs, 17, "Part 3", "What the test could see")
    L = 120
    for j, hd in enumerate(("Detectable", "Margin")):
        text(s, L + 150 + j * 260, 250, 250, 34, [kick(hd, NT, 0.06)])
    hline(s, L, 288, L + 700, 288, LINE)
    y = 296
    for lv in ("L1", "L2"):
        text(s, L, y + 12, 140, 44, [run(lv, 32, INK, MONO)], line=1.2)
        for j, v in enumerate((100 * m[lv]["mdd"], 100 * m[lv]["margin"])):
            text(s, L + 150 + j * 260, y + 12, 250, 44, [run(num(v, 1), 32, INK, MONO)], line=1.2)
        y += 64
        hline(s, L, y, L + 700, y, RULE)
    y = P(s, L, y + 20, 1680, "Rejected was within reach at each level. At L1 and L2 a true gain equal to the margin "
                              "would be found less than 80% of the time.", B, BODY, 1.4)
    y = P(s, L, y + 16, 1680, f"Gains up to {num(100 * ops['opus']['L3']['hi'], 2)} (Opus) and "
                              f"{num(100 * ops['haiku']['L3']['hi'], 2)} (Haiku) points at L3 are not ruled out.",
          B, BODY, 1.4)
    P(s, L, y + 16, 1680, f"No L3 row: its registered figure, {num(100 * m['L3']['mdd'], 1)} points, comes "
                          "from the random guesses' contrast.", B, BODY, 1.4, limit=990)


# ---------------------------------------------------------------- 18. Part 3, the wrong-house check

def wrong_house(prs, slots):
    w = slots["blind"]["wrong_house"]
    s = frame(prs, 18, "Part 3 · Controls", "The wrong-house check")
    y = P(s, 120, 252, 1680, "We score the model's guesses for the other home against this home. Right guesses "
                             "should beat them.", B, BODY, 1.4)
    X = 120
    for j, hd in enumerate(("L1", "L2")):
        text(s, X + 520 + j * 300, y + 24, 280, 34, [kick(hd, NT, 0.06)])
    hline(s, X, y + 62, X + 1100, y + 62, LINE)
    yy = y + 70
    for key, name in (("opus", "Opus"), ("haiku", "Haiku"), ("deepseek", "DeepSeek, exploratory")):
        text(s, X, yy + 12, 500, 44, [run(name, 28, INK, SANS, True)], line=1.2)
        for j, lv in enumerate(("L1", "L2")):
            text(s, X + 520 + j * 300, yy + 12, 280, 44, [run("p " + num(w[key][lv]["p"], 3), 32, INK, MONO)], line=1.2)
        yy += 64
        hline(s, X, yy, X + 1100, yy, RULE)
    N(s, X, yy + 16, 1680, "Gemini's 8 rows have no partner. Haiku L1 has 5 pairs, the rest 6.", limit=900)
    box_bottom(s, "No model passes:", "a pass needs p below 0.05 over 6 pairs.")


# ---------------------------------------------------------------- 19. Part 3, how far a guess sits from an object it could name

def placement_slide(prs, slots):
    p = slots["placement"]
    s = frame(prs, 19, "Part 3", "How far a guess is from an object it could name")
    text(s, 1330, 250, 470, 30, [run("guesses used / all", NT, MID)], PP_ALIGN.RIGHT)
    order = sorted(p.items(), key=lambda kv: kv[1]["median"])
    names = {"gemini": "Gemini, exploratory", "haiku": "Haiku 5.5", "deepseek": "DeepSeek, exploratory",
             "opus": "Opus 5.5", "placebo": "Random guesses"}
    y = 300
    for key, d in order:
        text(s, 120, y, 440, 44, [run(names[key], 28, INK, SANS, True), ], line=1.2)
        rect(s, 580, y + 6, d["median"] / 10.0 * 560, 34, MID if key == "placebo" else INK)
        svg_text(s, 580 + d["median"] / 10.0 * 560 + 16, y + 34, f"{num(d['median'], 1)} m", 28, INK, MONO, w=140)
        text(s, 1330, y + 4, 470, 40, [run(f"{d['n']:,} / {d['all_guesses']:,}", 24, MID, MONO)], PP_ALIGN.RIGHT, 1.2)
        y += 62
    N(s, 120, y + 20, 1680, "Input to the next slide. The nearest object of a class is a minimum; guesses with none are "
                            "left out.", limit=900)


# ---------------------------------------------------------------- 20. Part 3, M2

def factorial(prs, slots):
    m = slots["m2"]
    rho, dif = m["rho"], m["diff"]
    s = frame(prs, 20, "Part 3", "Right meaning: not shown enough")
    R, W = 120, 1680
    lab(s, R, 250, W, "Spearman rho: ASP's view score vs unmapped objects in view (the yardstick)")
    x0, x1, lo, hi = R + 560, R + 1400, -0.1, 0.35

    def dx(v):
        return x0 + (min(max(v, lo), hi) - lo) / (hi - lo) * (x1 - x0)

    rows = [("True objects", rho["F1"]), ("Room type only", rho["F-room"]),
            ("Moved: DeepSeek (expl.)", rho["F3-deepseek"]), ("Moved: Haiku", rho["F3-haiku"]),
            ("Moved: Opus", rho["F3-opus"]), ("Random guesses", rho["F5"]), ("No guesses", rho["F6"]),
            ("All true objects", rho["F0"])]
    top, step = 312, 50
    for v in (0.0, 0.1, 0.2, 0.3):
        hline(s, dx(v), top - 14, dx(v), top + step * len(rows) - 18, MID if v == 0 else LINE, 2 if v == 0 else 1,
              dash=bool(v))
        svg_text(s, dx(v), top + step * len(rows) + 14, num(v, 1), NT, FAINT, anchor="middle", w=80)
    for i, (name, d) in enumerate(rows):
        yy = top + i * step + 12
        text(s, R, yy - 18, 530, 36, [run(name, 28, BODY)], line=1.2)
        hline(s, dx(d["lo"]), yy, dx(d["hi"]), yy, INK, 3)
        oval(s, dx(d["mean"]), yy, 10, INK, WHITE, 3)
        svg_text(s, x1 + 40, yy + 8, sg(d["mean"], 3), NT, INK, MONO, w=120)
    A = dif["A"]
    P(s, R, 748, W, f"True objects beat random guesses by {num(A['mean'], 3)}. Enough: keep half of that, "
                    f"{num(A['mean'] / 2, 3)}. No arm does. Not shown sufficient; yardstick provisional.",
      B, BODY, 1.35, limit=960)


# ---------------------------------------------------------------- 21. Limits of scope

def limits(prs, slots):
    s = frame(prs, 21, "Limits", "What this talk cannot show")
    items = [("Two houses.", "Every result holds for 853 and 871 only, not other houses."),
             ("Proxy truth.", "Human labels stand in for what the camera saw."),
             ("Static replays.", "Claude saw saved inputs; no robot acted on its guesses."),
             ("Claude, not Gemini.", "The paper used Gemini 2.5 Pro. We used Claude with the author's prompt and "
                                     "loop. A Claude result does not speak for Gemini.")]
    y = 256
    for head, body in items:
        y = P(s, 120, y, 1680, [(head + " ", "b"), (body, "n")], B, BODY, 1.4, limit=1000) + 28


# ---------------------------------------------------------------- 22. Limits of method

def limits_method(prs, slots):
    m = slots["blind"]["members"]
    s = frame(prs, 22, "Limits", "How the test was made")
    items = ["We wrote the scorer after we saw DeepSeek's numbers.",
             "We set the L3 margin knowing the Gemini–DeepSeek gap.",
             "M2 is provisional: its yardstick failed part of an October check.",
             f"One Haiku member stopped at the token limit and its text did not parse "
             f"({m['haiku']['parsed']} of {m['haiku']['members']} did).",
             "Part 2 is open: the 871 numbers and the 853 full-budget row."]
    y = 256
    for t in items:
        y = P(s, 120, y, 1680, t, B, BODY, 1.4, limit=1000) + 26


# ---------------------------------------------------------------- 23. The answer

def answer(prs, slots):
    s = frame(prs, 23, "Answer", "The answer to the author")
    P(s, 120, 252, 1680, [(slots["thesis"] + ".", "b")], 44, INK, 1.2)
    y = P(s, 120, 330, 1680, "The registered line for the first half of the claim (that the guesses are right in "
                             "meaning).", B, BODY, 1.4)
    y = P(s, 120, y + 20, 1680, "In these two houses, both Claude models scored far below the other-house prior at "
                                "naming objects. Neither beat a trade of region contents by the 3-point margin; a "
                                "smaller gain is not ruled out.", B, BODY, 1.4)
    box(s, 120, y + 30, 1680, "M2 (offline, provisional):",
        "right labels moved by each model's error were not shown sufficient.")


# ---------------------------------------------------------------- 24. What the answer does not say

def not_shown(prs, slots):
    hh = slots["blind"]["models"]["haiku"]["L2"]["placebo"]
    s = frame(prs, 24, "The answer", "What the answer does not say")
    items = ["It does not say the guesses reach the map, or where they sit.",
             f"It does not say the models are no better than random guesses: Haiku is "
             f"{num(100 * hh['diff'], 1)} points above at L2 (one contrast, not adjusted).",
             "It says nothing about live runs, other models or the paper's scale.",
             "It does not show that a language model cannot help exploration."]
    y = 256
    for t in items:
        y = P(s, 120, y, 1680, t, B, BODY, 1.4, limit=1000) + 26


# ---------------------------------------------------------------- Backup 1. The paper's room test

def room_test(prs, slots):
    rt, h = slots["room_test"], slots["hint"]
    s = frame(prs, 25, "Backup · The paper's room test",
              "The paper's room test, on DeepSeek's live runs", backup=True)
    X, lw, cw = 120, 480, 300
    heads = ["Type matched", "No type", "Type matched", "No type"]
    text(s, X + lw, 246, 2 * cw, 30, [run("All stages", NT, MID, SANS, True)])
    text(s, X + lw + 2 * cw, 246, 2 * cw, 30, [run("8-member stages", NT, MID, SANS, True)])
    for j, hd in enumerate(heads):
        text(s, X + lw + j * cw, 278, cw - 10, 30, [run(hd, NT, MID)])
    hline(s, X, 314, X + lw + 4 * cw, 314, LINE)
    y = 322
    for key, name in (("llm", "DeepSeek, expl."), ("filter", "DeepSeek + filter"), ("placebo", "Random: chance")):
        d = rt["live"][key]
        text(s, X, y + 16, lw - 10, 40, [run(name, 28, INK, SANS, True)], line=1.2)
        for j, k in enumerate(("typed_all", "untyped_all", "typed_8", "untyped_8")):
            text(s, X + lw + j * cw, y + 16, cw - 10, 40,
                 [run(f"{d[k]} / {d['of']} · {num(100 * d[k] / d['of'], 0)}%", 28, INK, MONO)], line=1.2)
        y += 70
        hline(s, X, y, X + lw + 4 * cw, y, RULE)
    pp = rt["paper"]
    y = P(s, X, y + 18, 1680, [("The paper: ", "b"), (f"{pp['hit']} of {pp['of']} rooms "
                                                      f"({num(100 * pp['hit'] / pp['of'], 0)}%); a room counts if at "
                                                      "least 2 of 8 members place one within 2.5 m before the region "
                                                      "is seen.", "n")], B, BODY, 1.3)
    rp = rt["replay"]
    y = P(s, X, y + 8, 1680, [("Claude replays, 1 of 4, type matched, of "
                               f"{rp['opus']['of']} rooms: ", "b"),
                              (f"Opus {rp['opus']['t1']}, Haiku {rp['haiku']['t1']}, DeepSeek {rp['deepseek']['t1']}, "
                               f"random {rp['placebo']['t1']}.", "n")], B, BODY, 1.3)
    wo, wi = h["without"], h["with"]
    P(s, X, y + 8, 1680, [("Prompt hint (Haiku, 12 round-1 rows, after the result, deviation 56): ", "b"),
                          (f"room claims that hit {wo['l1_hits']} of {wo['l1_n']} without the sentence, "
                           f"{wi['l1_hits']} of {wi['l1_n']} with it; object claims {wo['l2_hits']} of {wo['l2_n']} "
                           f"and {wi['l2_hits']} of {wi['l2_n']}.", "n")], B, BODY, 1.3, limit=1000)


# ---------------------------------------------------------------- Backup 2. Do the filter and the vote keep right guesses?

def validity(prs, slots):
    v = slots["validity"]
    s = frame(prs, 26, "Backup · Our filter and vote", "Do the filter and the vote keep right guesses?",
              backup=True)
    X, lw = 120, 460
    cws = [240, 340, 600]
    heads = ["Removed", "L3, kept minus removed", "Can the interval be read?"]
    xs = [X + lw]
    for c_ in cws[:-1]:
        xs.append(xs[-1] + c_)
    for j, hd in enumerate(heads):
        P(s, xs[j], 250, cws[j] - 12, hd, NT, MID, 1.3)
    text(s, xs[0], 280, cws[0], 30, [run("% of guesses", NT, MID)])
    text(s, xs[1], 280, cws[1], 30, [run("points", NT, MID)])
    hline(s, X, 326, X + lw + sum(cws), 326, LINE)
    y = 336
    for key, name in (("opus", "Opus 5.5"), ("haiku", "Haiku 5.5"), ("deepseek", "DeepSeek, expl."),
                      ("random", "Random guesses")):
        d = v[key]
        text(s, X, y + 18, lw - 10, 40, [run(name, 28, INK, SANS, True)], line=1.2)
        text(s, xs[0], y + 14, cws[0] - 12, 44, [run(num(100 * d["removed_share"], 1), 32, INK, MONO)], line=1.2)
        text(s, xs[1], y + 14, cws[1] - 12, 44, [run(sg(100 * d["l3_diff"], 1), 32, INK, MONO)], line=1.2)
        verdict = ("no, too wide" if "beyond" in d["l3_verdict"] else "yes: no detectable difference")
        text(s, xs[2], y + 18, cws[2] - 12, 40, [run(verdict, 28, BODY)], line=1.2)
        y += 76
        hline(s, X, y, X + lw + sum(cws), y, RULE)
    box_bottom(s, "Reading.", "No detectable difference between kept and removed guesses (Haiku, DeepSeek and random "
                              "guesses at L3). Elsewhere the interval is too wide to read.")


# ---------------------------------------------------------------- Backup 3. Why does ASP not gain from all true objects?

def f0_slide(prs, slots):
    m = slots["m2"]
    d, a = m["diff"]["F0-F5"], m["diff"]["A"]
    z = m["f0_ig_zero"]
    s = frame(prs, 27, "Backup · A likely question", "Why does ASP not gain from all true objects?",
              backup=True)
    y = P(s, 120, 256, 1680, "If every member holds every true object, why does ASP's score not rise?", B, INK, 1.4)
    y = P(s, 120, y + 24, 1680, [("What we found: ", "b"),
                                 (f"all true objects for every member scored {sg(d['mean'])} "
                                  f"({sg(d['lo'])} to {sg(d['hi'])}) against random guesses. True objects in "
                                  f"differing subsets scored {sg(a['mean'])} above them.", "n")], B, BODY, 1.4)
    y = P(s, 120, y + 24, 1680, [("Why it should not rise: ", "b"),
                                 ("the score counts disagreement between members. We registered that before the "
                                  "run (M2, section 7).", "n")], B, BODY, 1.4)
    P(s, 120, y + 24, 1680, [("What we cannot explain: ", "b"),
                             (f"why it falls below random guesses. The gain is zero for every candidate in only "
                              f"{z['stages']} of {z['of']} stages.", "n")], B, BODY, 1.4, limit=990)


# ---------------------------------------------------------------- Backup 4. The four outcomes

def outcomes(prs, slots):
    h = slots["blind"]["models"]
    s = frame(prs, 28, "Backup · The four outcomes", "The four outcomes, and the rule that picked one",
              backup=True)
    pick = slots["outcome"]
    cx = (120, 400, 1080)
    for x, hd in zip(cx, ("Outcome", "The registered rule", "Met?")):
        text(s, x, 246, 600, 34, [kick(hd, NT, 0.1)])
    rows = [("works", "Holds", "A Claude model is Supported at L3.", "No. Neither is Supported at L3."),
            ("mixed", "Mixed", "No Claude model is Supported at L3. One is Supported at L1 or L2 and passes the "
                               "wrong-house check.", "No. None is Supported at L1 or L2, and none passes the check."),
            ("fails", "Fails", "Every Claude model is Rejected at L2 and L3. At L3 the margin is over the region "
                               "trade.", "Yes. Both models, at L2 and L3."),
            ("inconclusive", "Inconclusive", "None of the rules above is met.", "Not reached. The rows apply in "
                                                                                  "this order.")]
    y = 290
    for key, name, rule, met in rows:
        chosen = pick == key
        # height from the text: the rule column is 640 px wide, the answer column 700 px
        hgt = max(est_lines(rule, B * 0.83, 640), est_lines(met, B * 0.83, 700)) * B * 1.35 + 28
        r = rect(s, 112, y + 2, 1696, hgt - 4, WHITE if chosen else WASH, INK if chosen else RULE, 3 if chosen else 1)
        text(s, 130, y + 14, 260, 44, [run(name, B, INK if chosen else MID, SANS, True)], line=1.3)
        P(s, cx[1], y + 14, 640, rule, B, BODY if chosen else MID, 1.35)
        P(s, cx[2], y + 14, 700, met, B, BODY if chosen else MID, 1.35)
        y += hgt + 12
    if y > 985:
        WARN.append(f"outcomes table ends at y={y:.0f}")
    ps = {h[k][lv]["p_holm"] for k in ("opus", "haiku") for lv in ("L1", "L2", "L3")}
    ptxt = f"all six Holm p-values are {num(ps.pop(), 2)}" if len(ps) == 1 else \
        f"the six Holm p-values are {num(min(ps), 2)} or higher"
    N(s, 120, y, 1680, f"Supported needs a Holm-adjusted p below 0.05; {ptxt}.", limit=1012)


# ---------------------------------------------------------------- notes and main

def speaker_notes():
    md = open(SCRIPT).read()
    parts = re.split(r"^## (?:Slide|Backup) \d+:.*$", md, flags=re.M)[1:]
    out = []
    for p in parts:
        p = p.split("\n---")[0]
        lines = [ln.strip() for ln in p.strip().splitlines()]
        out.append("\n".join(ln for ln in lines if ln and not re.fullmatch(r"\*\(.*\)\*", ln)))
    return out


def main():
    Nn = numbers()
    slots = json.load(open(SLOTS))
    C, budgets = paper_cells(slots)
    checks = json.load(open(CHECKS))
    c2 = c2_f1_853()
    prs = Presentation()
    prs.slide_width, prs.slide_height = px(1920), px(1080)
    cover(prs)
    asp_picture(prs)
    live_test(prs, Nn)
    why(prs, Nn)
    land(prs, Nn)
    live_limits(prs, Nn)
    paper_rules(prs, budgets, checks, slots)
    table853(prs, C, budgets, slots)
    table871(prs, C, budgets, slots)
    limits_reference(prs, checks, c2)
    limits_runs(prs, C)
    defense(prs)
    picture_levels(prs, slots)
    controls(prs, slots)
    blind_table(prs, slots)
    facts(prs, slots)
    detect(prs, slots)
    wrong_house(prs, slots)
    placement_slide(prs, slots)
    factorial(prs, slots)
    limits(prs, slots)
    limits_method(prs, slots)
    answer(prs, slots)
    not_shown(prs, slots)
    room_test(prs, slots)
    validity(prs, slots)
    f0_slide(prs, slots)
    outcomes(prs, slots)
    assert len(prs.slides) == TOTAL + 4, len(prs.slides)
    notes = speaker_notes()
    assert len(notes) == TOTAL + 4, len(notes)
    for slide, n in zip(prs.slides, notes):
        slide.notes_slide.notes_text_frame.text = n
    prs.core_properties.title = "Right in meaning, wrong in place?"
    prs.core_properties.author = "ASP replication, end-sem"
    prs.core_properties.last_modified_by = "ASP replication, end-sem"
    prs.save(OUT)
    print(OUT, len(prs.slides), "slides (", TOTAL, "main + 4 backup )")
    for w in WARN:
        print("FIT WARNING:", w)


if __name__ == "__main__":
    main()
