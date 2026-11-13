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
STAGE_PNG = os.path.join(HERE, "figures", "stage.png")
STAGE_JSON = os.path.join(HERE, "figures", "stage_numbers.json")
TOTAL = 20
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


def box(s, x, y, w, head, body, size=B, fill=WASH, edge=RULE, dashed=False):
    """A shaded box with a bold lead-in. Returns the y below it."""
    plain = (head + " " if head else "") + body
    h = est_lines(plain, size, w - 56) * size * 1.5 + 44
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
            ("Part 2 · Paper's scale", "Our scores beside his. The 871 numbers are being rerun."),
            ("Part 3 · His defense", "Is the meaning right? Is it enough? Is it the model?")]
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
    lab(s, R, 250, 800, "View ranking, median ρ · 119 stages")
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
    blocks = [("Scoring.", "The author's own F1 and GED code, on his time axis."),
              ("Reference.", f"A scripted stand-in for his hand-driven tour: navmesh paths, the same mapper "
                             f"({stops[0]} and {stops[1]} stops)."),
              ("Frontier.", "Run to its natural end: 5 of 5 runs on 853, 1 of 5 on 871."),
              ("LLM.", "Ours is DeepSeek. His is Gemini 2.5 Pro.")]
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
      "60 m. His lead did not appear on 853 at 10% and 50%, with DeepSeek and a rebuilt reference.", limit=1000)


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
            ("Paper, m²", [f"{checks[sc]['C1']['paper_area_m2']:.0f}" for sc in ("00853", "00871")])]
    for j, hd in enumerate(("853", "871")):
        svg_text(s, R + 520 + j * 110 + 40, 330, hd, 28, MID, anchor="middle", w=100)
    yy = 346
    hline(s, R, yy, R + 740, yy, LINE)
    for name, vals in rows:
        text(s, R, yy + 14, 520, 40, [run(name, 28, BODY)], line=1.2)
        for j, v in enumerate(vals):
            text(s, R + 520 + j * 110, yy + 12, 80, 40, [run(v, 32, INK, MONO)], PP_ALIGN.RIGHT, 1.2)
        yy += 66
        hline(s, R, yy, R + 740, yy, RULE)
    N(s, R, yy + 20, 740, "The gap is partly explained: the grid reaches under furniture, which the navmesh leaves "
                          "out. On 853 it comes near the paper's figure; on 871 it does not.", limit=1000)


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
    s = frame(prs, 12, "Part 3 · The author's defense", "The author's defense, in three questions")
    lab(s, 120, 250, 1680, "What the author told us")
    P(s, 120, 290, 1680, "The guesses are often in the wrong place, but they name the right things, and that is "
                         "enough.", B, INK, 1.4)
    steps = [("Is the meaning right, beyond base rates?",
              "Compare the saved guesses with controls that see the same map.",
              "The prompt says a scene may hold more than one bedroom and bathroom. Naming one proves little."),
             ("Would right meaning be enough?",
              "Offline, give ASP true labels moved by real placement error. See how much of its ranking is left.",
              "ASP rewards disagreement. Guesses that all agree add nothing."),
             ("Is it the model?",
              "Replay Claude Haiku 5.5 and Opus 5.5 on the same 44 saved inputs.",
              "If the replays do not run, DeepSeek's results stay exploratory.")]
    for i, (name, what, why_) in enumerate(steps):
        x = 120 + i * 580
        hline(s, x, 380, x + 520, 380, INK, 2)
        text(s, x, 392, 520, 34, [run(f"{i + 1:02d}", NT, FAINT, MONO)])
        y = P(s, x, 430, 520, [(name, "b")], B, line=1.3)
        y = P(s, x, y + 10, 520, what, B, BODY, 1.35, limit=800)
        N(s, x, y + 14, 520, why_, limit=880)
    box_bottom(s, "Same pass.", "The validity layer, for every model. We hash the rules before we score any Claude "
                                "output.")


# ---------------------------------------------------------------- 13. Part 3, one real stage

def picture(prs):
    n = json.load(open(STAGE_JSON))
    s = frame(prs, 13, "Part 3 · One stage, drawn from files", "What a hit would need, on one real stage")
    s.shapes.add_picture(STAGE_PNG, px(120), px(250), px(730), px(730))
    X, w = 900, 900
    items = [("sq", "Room node, mapped"), ("dot", "Object node, mapped"), ("seen", "Seen region"),
             ("part", "Partly seen region"), ("unobs", "Unobserved region"),
             ("open", "Keeps a room type open"), ("halo", "0.5 m reach of such a region")]
    y = 256
    for kind, txt in items:
        cx, cy = X + 20, y + 20
        if kind == "sq":
            rect(s, cx - 10, cy - 10, 20, 20, WHITE, INK, 3)
        elif kind == "dot":
            oval(s, cx, cy, 6, INK)
        elif kind in ("seen", "part", "unobs"):
            rect(s, cx - 14, cy - 11, 28, 22, {"seen": "e5e7eb", "part": "cbd5e1", "unobs": "fde8dc"}[kind])
        elif kind == "open":
            rect(s, cx - 14, cy - 11, 28, 22, "fde8dc", ACCENT, 4)
        else:
            r = rect(s, cx - 14, cy - 11, 28, 22, WHITE, ACCENT, 2)
            r.line.dash_style = MSO_LINE.DASH
        text(s, X + 56, y + 2, w - 56, 38, [run(txt, 28, BODY)], line=1.2)
        y += 42
    y += 14
    y = P(s, X, y, w, [("L1, L2: ", "b"), (f"no place. The type or class must be open. Here: "
                                           f"{' and '.join(n['open_types'])}, and {n['open_classes']} classes.", "n")],
          B, BODY, 1.35)
    y = P(s, X, y + 10, w, [("L3: ", "b"), ("the guess must reach an unobserved region of its type or class, "
                                             "inside the dashed line.", "n")], B, BODY, 1.35, limit=980)
    N(s, X, y + 10, w, f"Run {n['run']}, stage {n['stage']}: {n['observed_object_nodes']} object and "
                       f"{n['observed_room_nodes']} room nodes mapped; {n['regions']} regions: {n['seen']} seen, "
                       f"{n['partly_seen']} partly seen, {n['unobserved']} unobserved. No model's guesses, no score.",
      limit=1010)


# ---------------------------------------------------------------- 14. Part 3, levels

def levels(prs, slots):
    br = slots["base_rates"]
    s = frame(prs, 14, "Part 3 · Three levels of “right”", "Three levels of “right”",
              pending="RESULT PENDING" if is_pending(br) else None)
    rows = [("L1", "Which rooms", "A hit: the room type is still open. An unseen region of that type has nothing "
                                  "of it mapped."),
            ("L2", "Which objects", "A hit: the object class is still open. An unseen region holds an unmapped "
                                    "object of that class."),
            ("L3", "Roughly where", "A hit: the guess reaches an unobserved region that is of its type, or holds "
                                    "its class."),
            ("L4", "Exactly where · secondary", "The share of guessed objects within 0.5, 1, 2 or 3 m of such "
                                                     "an object.")]
    y = 252
    for tag, head, body in rows:
        yh = y
        rect(s, 120, y + 4, 90, 90, WASH, RULE)
        text(s, 120, y + 28, 90, 50, [run(tag, 36, INK, MONO)], PP_ALIGN.CENTER, 1.2)
        y2 = P(s, 240, y, 1560, [(head, "b")], B, line=1.3)
        P(s, 240, y2 + 2, 1560, body, B, BODY, 1.35)
        y = yh + 128
    t = [tbd(br[k], lambda v: f"{100 * v:.0f}%") for k in ("unseen_bathroom", "unseen_bedroom", "unseen_kitchen")]
    r = rect(s, 120, 810, 1680, 180, WASH, LINE, 2)
    r.line.dash_style = MSO_LINE.DASH
    text(s, 148, 826, 1620, 34, [kick("Base rate: stages where such a region remains, under the frozen rule", NT, 0.1)])
    text(s, 148, 872, 1620, 50, [[run("Bathroom ", B, BODY), run(t[0][0], B, t[0][1], MONO),
                                  run("   Bedroom ", B, BODY), run(t[1][0], B, t[1][1], MONO),
                                  run("   Kitchen ", B, BODY), run(t[2][0], B, t[2][1], MONO)]], line=1.3)
    N(s, 148, 930, 1620, "If these are high, naming such a room needs a control to mean anything.",
      limit=1000)


# ---------------------------------------------------------------- 15. Part 3, controls

def controls(prs):
    s = frame(prs, 15, "Part 3 · Controls", "What each guess is compared with")
    items = [("A prior from 179 other annotated houses, given the same map.", "L1, L2"),
             ("The random-guess placebo.", "L1, L2"),
             ("The model's own labels, swapped among its own guesses. The places stay.", "L3"),
             ("The unobserved regions, trading contents.", "L3"),
             ("The prior's labels, at the model's places.", "L3")]
    y = 262
    for txt, lv in items:
        y0 = y
        y = P(s, 120, y, 1330, txt, B, BODY, 1.35)
        text(s, 1500, y0 + 4, 300, 40, [run(lv, 28, MID, MONO)], PP_ALIGN.RIGHT, 1.2)
        hline(s, 120, y + 12, 1800, y + 12, RULE)
        y += 30
    box_bottom(s, "Apart: the wrong-house check.",
               "The same model's guesses for the other home, over 6 pairs of seed and arm. It is a gate for L1 and "
               "L2, not part of the test family.")


# ---------------------------------------------------------------- 16. Part 3, the room test

def room_test(prs, slots):
    rt = slots["room_test"]
    s = frame(prs, 16, "Part 3 · The paper's room test", "The paper's room test, with a chance rate",
              pending="RESULT PENDING" if is_pending(rt) else None)
    L, w = 120, 780
    y = P(s, L, 262, w, "A room counts as predicted if at least 2 of 8 members place a room within 2.5 m of its "
                        "centre before the robot sees the region. The paper: 9 of 28.", B, BODY, 1.4)
    y = P(s, L, y + 24, w, "We score it with and without the room's type, and add a chance rate from random guesses.",
          B, BODY, 1.4, limit=980)
    R, W = 960, 840
    lab(s, R, 250, W, "Rooms predicted before they were seen")
    rows = [("LLM guesses", rt["llm_live"]), ("Filtered guesses", rt["filter_live"]),
            ("Random, the chance rate", rt["placebo_live"]), ("Paper, Gemini", {"hit": 9, "of": 28})]
    yy, bx, bw = 304, R + 330, 300
    for name, d in rows:
        text(s, R, yy + 6, 320, 40, [run(name, 28, BODY)], line=1.2)
        if d["hit"] is None or d["of"] is None:
            r = rect(s, bx, yy + 8, bw, 34, WASH, LINE, 2)
            r.line.dash_style = MSO_LINE.DASH
            svg_text(s, bx + bw + 14, yy + 36, "TBD", 28, FAINT, MONO, w=140)
        else:
            rect(s, bx, yy + 8, bw, 34, RULE)
            rect(s, bx, yy + 8, bw * d["hit"] / d["of"], 34, INK)
            svg_text(s, bx + bw + 14, yy + 36, f"{d['hit']} of {d['of']}", 28, INK, MONO, w=180)
        yy += 64
    hline(s, R, yy + 6, R + W, yy + 6, RULE)
    yy += 24
    lab(s, R, yy, W, "Claude replays, 4 members")
    yy += 48
    for name, k in (("1 of 4", "claude_1of4"), ("2 of 4", "claude_2of4")):
        d = rt[k]
        a = "TBD" if d["hit"] is None else f"{d['hit']} of {d['of']}"
        b_ = "TBD" if d["chance_hit"] is None else f"{d['chance_hit']} of {d['chance_of']}"
        text(s, R, yy + 4, 200, 40, [run(name, 28, BODY)], line=1.2)
        text(s, R + 200, yy + 4, 640, 40, [[run("Claude ", 28, MID), run(a, 28, FAINT if a == "TBD" else INK, MONO),
                                            run("  chance ", 28, MID), run(b_, 28, FAINT if b_ == "TBD" else INK, MONO)]],
             line=1.2)
        yy += 56
    N(s, L, 800, 1680, "Live arms are the October runs, which have 8 members. Replays have 4, so we do not set them "
                       "against the paper's 9 of 28.", limit=1000)


# ---------------------------------------------------------------- 17. Part 3, three models

def three_models(prs, slots):
    m = slots["models"]
    s = frame(prs, 17, "Part 3 · Same 44 inputs for every model", "Same inputs, three models",
              pending="RESULT PENDING" if is_pending(m) else None)
    X, y0 = 120, 250
    cols = [("", 150), ("Compared with", 330), ("Opus 5.5", 250), ("Haiku 5.5", 250), ("DeepSeek", 250),
            ("Detectable", 250)]
    xs = [X]
    for _, cw in cols[:-1]:
        xs.append(xs[-1] + cw)
    for (hd, cw), x in zip(cols, xs):
        if hd:
            text(s, x, y0, cw - 10, 34, [kick(hd, NT, 0.06)])
    text(s, xs[4], y0 + 28, 250, 30, [run("exploratory", NT, MID)])
    text(s, xs[5], y0 + 28, 250, 30, [run("difference", NT, MID)])
    hline(s, X, y0 + 66, X + sum(c for _, c in cols), y0 + 66, LINE)
    named = {"L1": "prior · 5 pts", "L2": "prior · 5 pts", "L3": "region trade · 3 pts"}
    y = y0 + 76
    for lv in ("L1", "L2", "L3"):
        text(s, xs[0], y + 30, 140, 50, [run(lv, 36, INK, MONO)], line=1.2)
        text(s, xs[1], y + 22, 320, 70, [run(named[lv], NT, MID)], line=1.3)
        for key, x in (("opus", xs[2]), ("haiku", xs[3]), ("deepseek", xs[4])):
            d = m[key][lv]
            if d["lift_pp"] is None:
                text(s, x, y + 22, 240, 40, [run("TBD", 32, FAINT, MONO)], line=1.2)
            else:
                text(s, x, y + 4, 240, 40, [run(sg(d["lift_pp"], 1), 32, INK, MONO)], line=1.2)
                ci = "" if d["lo"] is None or d["hi"] is None else f"[{sg(d['lo'], 1)}, {sg(d['hi'], 1)}]"
                text(s, x, y + 44, 240, 30, [run(ci, NT, MID)], line=1.2)
                text(s, x, y + 76, 240, 30, [run(d["verdict"] or "TBD", NT, INK, SANS, True)], line=1.2)
        t, c = tbd(m["mdd"][lv], lambda v: f"{v:.1f} pts")
        text(s, xs[5], y + 22, 240, 40, [run(t, 32, c, MONO)], line=1.2)
        y += 118
        hline(s, X, y, X + sum(c_ for _, c_ in cols), y, RULE)
    y += 18
    wh = m["wrong_house"]
    pw = lambda v: "TBD" if v is None else f"p {num(v, 2)}"  # noqa: E731
    P(s, X, y, 1680, [("Wrong-house check, L1 / L2: ", "b"),
                      (f"Opus {pw(wh['opus']['L1'])} / {pw(wh['opus']['L2'])}; Haiku {pw(wh['haiku']['L1'])} / "
                       f"{pw(wh['haiku']['L2'])}", "n")], 28, BODY, 1.35)
    y += 46
    cd = m["l1_cannot_decide"]
    l1 = ("L1 cannot decide at 44 inputs, as the freeze confirms." if cd is True else
          "L1 can decide at 44 inputs, as the freeze shows." if cd is False else
          "L1: the plan puts its detectable difference near 20 points. The freeze confirms or corrects that: TBD.")
    N(s, X, y + 6, 1680,
      "Lift: model rate minus the named comparator's, in points. Each cell's p is the largest over its comparators; "
      "2 Claude models × 3 levels, Holm. Rejected: the interval's top is below the margin. " + l1, limit=1010)


# ---------------------------------------------------------------- 18. Part 3, M2

def factorial(prs, slots):
    f = slots["factorial"]
    s = frame(prs, 18, "Part 3 · Would right meaning be enough for ASP's score?",
              "Would right meaning be enough?", pending="RESULT PENDING" if is_pending(f) else None)
    L, w = 120, 800
    arms = [("F1", "true objects, the best case"), ("F5", "random guesses, the floor"), ("F6", "no guesses"),
            ("F3", "true objects moved by each model's own placement error"),
            ("F-room", "only what room types tell, as many guesses"),
            ("F0", "all-true anchor: a property of the score, shown as it comes out")]
    y = 250
    for tag, body in arms:
        text(s, L, y + 2, 140, 40, [run(tag, 28, INK, MONO)], line=1.2)
        y = max(P(s, L + 150, y, w - 150, body, 28, BODY, 1.3), y + 44) + 14
    R, W = 960, 840
    lab(s, R, 250, W, "Spearman ρ: score against the yardstick")
    x0, x1, lo, hi = R + 330, R + 800, -0.2, 1.0

    def dx(v):
        return x0 + (min(max(v, lo), hi) - lo) / (hi - lo) * (x1 - x0)

    rows = [("F1", f["F1_exact"]), ("F-room", f["F_room"]), ("F3 DeepSeek", f["F3_deepseek_err"]),
            ("F3 Haiku", f["F3_haiku_err"]), ("F3 Opus", f["F3_opus_err"]), ("F5", f["F5_random"]),
            ("F6", f["F6_none"]), ("F0", f["F0_anchor"])]
    top, step = 308, 52
    for v in (0.0, 0.5, 1.0):
        hline(s, dx(v), top - 14, dx(v), top + step * len(rows) - 20, MID if v == 0 else LINE, 2 if v == 0 else 1,
              dash=bool(v))
        svg_text(s, dx(v), top + step * len(rows) + 14, num(v, 1), NT, FAINT, anchor="middle", w=80)
    for i, (name, d) in enumerate(rows):
        yy = top + i * step + 12
        text(s, R, yy - 18, 320, 36, [run(name, 28, BODY)], line=1.2)
        if d["rho"] is None:
            hline(s, x0, yy, x1, yy, LINE, 3, dash=True)
        else:
            if d.get("lo") is not None and d.get("hi") is not None:
                hline(s, dx(d["lo"]), yy, dx(d["hi"]), yy, INK, 3)
            oval(s, dx(d["rho"]), yy, 10, INK, WHITE, 3)
    z = f["F0_anchor"]["share_ig_zero"]
    t, c = tbd(z, lambda v: f"{100 * v:.0f}%")
    P(s, R, top + step * len(rows) + 50, W, [("F0: stages with zero gain for every view: ", "n"), (t, "m")], 28, BODY,
      1.3)
    yb = 836
    P(s, L, yb, 1680, [("Rule. ", "b"), ("Step 1: does F1 separate from F5? If not, stop. Step 2: an arm is "
                                         "sufficient if it keeps at least half of that gap and its interval lies "
                                         "wholly above; not shown sufficient if wholly below.", "n")],
      B, BODY, 1.35, limit=960)
    N(s, L, 948, 1680, "Yardstick: the bench's wall-aware cone count, 24 runs, wild cluster bootstrap. Every "
                          "verdict is provisional.", limit=1012)


# ---------------------------------------------------------------- 19. Limits

def limits(prs, Nn, slots):
    s = frame(prs, 19, "Limits", "What this talk cannot show")
    cd = slots["models"]["l1_cannot_decide"]
    l1 = ("The test cannot decide room types (L1) at 44 inputs." if cd is True else
          "The test can decide room types (L1) at 44 inputs." if cd is False else
          "The plan expects the test cannot decide room types (L1) at 44 inputs. The freeze will say.")
    left = [("Two houses.", "Any inference holds for homes 853 and 871."),
            ("Proxy truth.", "HM3D's human labels and a footprint rule for “seen” stand in for what the "
                             "camera saw."),
            ("Static replays.", "Claude sees saved inputs, 4 members. No robot acts on its guesses, and we ran no "
                                "live Claude test."),
            ("A weak yardstick.", f"About 1 in 12 unseen objects in view of a stop reach the next map "
                                  f"({num(100 * Nn['audit:yardstick_in_view_mapped:all'])}%). The count ignores "
                                  "unmapped walls.")]
    right = [("Late scorer.", "We wrote it after DeepSeek's numbers were seen. We freeze it before any Claude "
                              "output is scored."),
             ("Provisional M2.", "Every verdict is provisional: the yardstick failed part of its October check."),
             ("No partner.", "The 8 Gemini rows have no wrong-house partner."),
             ("Room types.", l1)]
    for xcol, items in ((120, left), (980, right)):
        y = 256
        for head, body in items:
            y = P(s, xcol, y, 820, [(head + " ", "b"), (body, "n")], B, BODY, 1.35, limit=1000) + 26


# ---------------------------------------------------------------- 20. The answers

ROWS = [
    ("works", "Works", "A Claude model is Supported at L3.",
     "Claude places content in the right unobserved region better than the named comparators. Not shown: that "
     "this reaches the map."),
    ("mixed", "Mixed", "No Claude model is Supported at L3. One is Supported at L1 or L2 and passes the "
                       "wrong-house check.",
     "Right at house level, wrong in place."),
    ("fails", "Fails", "Every Claude model is Rejected at L2 and L3. At L3 the margin is over the region trade, "
                       "not the prior.",
     "Claude's lead over a prior that sees the same map is under the margin. The semantics are mostly base rate."),
    ("inconclusive", "Inconclusive", "None of the rules above is met.",
     "Neither supported nor rejected. We state what the test could detect."),
]


def answers(prs, slots):
    s = frame(prs, 20, "The answer to the author", "The one-line answer to the author")
    pick = slots.get("outcome")
    cx = (120, 380, 1000)
    for x, hd in zip(cx, ("Outcome", "The registered rule", "The answer")):
        text(s, x, 246, 600, 34, [kick(hd, NT, 0.1)])
    y = 290
    for key, name, rule, ans in ROWS:
        chosen, faded = pick == key, pick is not None and pick != key
        h = max(est_lines(rule, B, 580), est_lines(ans, B, 800)) * B * 1.35 + 28
        r = rect(s, 110, y, 1700, h, WHITE if chosen else WASH, INK if chosen else RULE, 4 if chosen else 1)
        text(s, 130, y + 14, 240, 44, [run(name, B, FAINT if faded else INK, SANS, True)], line=1.3)
        P(s, cx[1], y + 14, 580, rule, B, FAINT if faded else BODY, 1.35)
        P(s, cx[2], y + 14, 800, ans, B, FAINT if faded else BODY, 1.35)
        y += h + 14
    if y > 985:
        WARN.append(f"answers table ends at y={y:.0f}")
    N(s, 120, y + 2, 1680, "The registered rules pick one, after the data exist. If the replays do not run, no row applies.",
      limit=1010)


# ---------------------------------------------------------------- Backup. The validity layer

def validity(prs, slots):
    v = slots["validity"]
    s = frame(prs, 21, "Backup · The validity layer, same pass", "The validity layer across models",
              pending="RESULT PENDING" if is_pending(v) else None, backup=True)
    X, lw = 120, 360
    cws = [260, 380, 340, 340]
    heads = ["Removed", "L3 hits, kept v removed", "Support v truth: Brier", "Hits kept per guess kept"]
    xs = [X + lw]
    for c_ in cws[:-1]:
        xs.append(xs[-1] + c_)
    for j, hd in enumerate(heads):
        P(s, xs[j], 250, cws[j] - 12, hd, NT, MID, 1.3)
    hline(s, X, 330, X + lw + sum(cws), 330, LINE)
    y = 340
    for key, name in (("opus", "Claude Opus 5.5"), ("haiku", "Claude Haiku 5.5"), ("deepseek", "DeepSeek"),
                      ("random", "Random guesses")):
        d = v[key]
        text(s, X, y + 22, lw - 10, 40, [run(name, 28, INK, SANS, True)], line=1.2)
        cells = [tbd(d["removed_share"], lambda a: f"{100 * a:.0f}%"),
                 ("TBD", FAINT) if d["hit_kept"] is None or d["hit_removed"] is None else
                 (f"{100 * d['hit_kept']:.1f}% v {100 * d['hit_removed']:.1f}%", INK),
                 tbd(d["brier"], lambda a: f"{a:.3f}"), tbd(d["yield_tau1"], lambda a: f"{100 * a:.1f}%")]
        for j, (t, c) in enumerate(cells):
            text(s, xs[j], y + 18, cws[j] - 12, 44, [run(t, 32, c, MONO)], line=1.2)
        y += 84
        hline(s, X, y, X + lw + sum(cws), y, RULE)
    y = N(s, X, y + 24, 1680, "Four readouts: the share the validator removes; whether valid guesses are right more "
                              "often than removed ones; whether member agreement tracks truth; the yield of the vote "
                              "filter at tau = 1. The fifth readout, on decisions, needed the cut bench replay.")
    box_bottom(s, "Why it matters.", "The vote keeps what members agree on, and ASP's score gives agreed content "
                                     "zero. If the vote finds the true guesses, the score has nowhere to use them.")


# ---------------------------------------------------------------- notes and main

def speaker_notes():
    md = open(SCRIPT).read()
    parts = re.split(r"^## Slide \d+:.*$", md, flags=re.M)[1:]
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
    picture(prs)
    levels(prs, slots)
    controls(prs)
    room_test(prs, slots)
    three_models(prs, slots)
    factorial(prs, slots)
    limits(prs, Nn, slots)
    answers(prs, slots)
    validity(prs, slots)
    assert len(prs.slides) == TOTAL + 1, len(prs.slides)
    notes = speaker_notes()
    assert len(notes) == TOTAL + 1, len(notes)
    for slide, n in zip(prs.slides, notes):
        slide.notes_slide.notes_text_frame.text = n
    prs.core_properties.title = "Right in meaning, wrong in place?"
    prs.core_properties.author = "Sher Partap Singh, Preesha Katial, Ananya Singla"
    prs.save(OUT)
    print(OUT, len(prs.slides), "slides (", TOTAL, "main + 1 backup )")
    for w in WARN:
        print("FIT WARNING:", w)


if __name__ == "__main__":
    main()
