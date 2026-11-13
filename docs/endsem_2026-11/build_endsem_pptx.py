"""Build ASP_Endsem.pptx: the end-sem talk "Right in meaning, wrong in place?", in the style of
../checkin_2026-11/ASP_Checkin2.pptx, with ENDSEM_Script.md as speaker notes.

Every chart and table value comes from a result file (numbers.csv, paper_compare.json, c_checks.json) or,
for part 3, from slots.json. A null in slots.json shows TBD and a grey "result pending" mark.
SOURCES.md says which file and key stand behind each number.

Usage (from the project root):
    .venv_offline/bin/python docs/endsem_2026-11/build_endsem_pptx.py
"""
import csv
import json
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
                                callout, fill_frame, hline, kick, label, note, oval, px, rect, run, stat,
                                svg_text, text)

# ENDSEM_SLOTS and ENDSEM_OUT let a test build use other files without touching the real ones.
OUT = os.environ.get("ENDSEM_OUT", os.path.join(HERE, "ASP_Endsem.pptx"))
SCRIPT = os.path.join(HERE, "ENDSEM_Script.md")
SLOTS = os.environ.get("ENDSEM_SLOTS", os.path.join(HERE, "slots.json"))
NUMBERS = os.path.join(PROJECT, "tools", "live_policy", "results_2026-10-31", "numbers.csv")
CHECKS = os.path.join(PROJECT, "tools", "live_policy", "results_paper_compare_1112", "c_checks.json")
FRONTIER = os.path.join(PROJECT, "tools", "live_policy", "results_2026-10-31", "frontier_seeds",
                        "frontier_holm.json")
TOTAL = 16
ACCENT = "c2410c"
MINUS = "−"
DISTANCE_WEIGHT = "0.2"  # per metre; tools/live_policy/results_2026-10-31/WRITEUP.md section 4, "The score"


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


def load_slots():
    return json.load(open(SLOTS))


def paper_cells(slots):
    path = os.path.join(PROJECT, slots["paper_compare_json"])
    d = json.load(open(path))
    cells = {}
    for c in d["cells"]:
        if c["reference"] == "apr" and c["variant"] == "B":
            cells[(c["scene"], c["arm"], c["fraction"])] = c
    return cells, d["meta"]["budgets"]


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
    q = Decimal(1).scaleb(-nd)
    return Decimal(repr(round(v, 10))).quantize(q, rounding=ROUND_HALF_UP)


def sg(v, nd=3):
    """Signed number with a true minus sign."""
    d = rnd(v, nd)
    return (f"{d:+}" if d else f"{d}").replace("-", MINUS)


def num(v, nd=1):
    return f"{rnd(v, nd)}".replace("-", MINUS)


def tbd(v, fmt):
    return ("TBD", FAINT) if v is None else (fmt(v), INK)


# ---------------------------------------------------------------- shared pieces

def pill(s, x, y, w, h, txt, fill=RULE, color=MID):
    r = rect(s, x, y, w, h, fill)
    fill_frame(r.text_frame, [run(txt, 16, color, SANS, True, spacing=0.14)], PP_ALIGN.CENTER, 1.0,
               MSO_ANCHOR.MIDDLE)


def frame(prs, n, k, title, pending=False):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    text(s, 120, 84, 1380, 30, [kick(k)])
    text(s, 120, 123, 1680, 74, [run(title, 56, INK, LIGHT, spacing=-0.02)], line=1.15)
    hline(s, 120, 222, 1800, 222, RULE)
    text(s, 120, 1010, 1200, 28, [run("Right in meaning, wrong in place? · End-sem", 20, FAINT)])
    text(s, 1500, 1010, 300, 28, [run(f"{n:02d} / {TOTAL}", 20, FAINT)], PP_ALIGN.RIGHT)
    if pending:
        pill(s, 1520, 78, 280, 36, "RESULT PENDING")
    return s


def pending_box(s, x, y, w, h, body, size=22):
    r = rect(s, x, y, w, h, WASH, LINE, 2)
    r.line.dash_style = MSO_LINE.DASH
    fill_frame(r.text_frame, [run("RESULT PENDING", 16, FAINT, SANS, True, spacing=0.14),
                              run(body, size, MID)], line=1.4, anchor=MSO_ANCHOR.MIDDLE,
               margins=(24, 14, 24, 14))
    return r


def card(s, x, w, y, big, head, body, big_size=52, head_h=80, body_size=21):
    hline(s, x, y, x + w, y, INK, 2)
    text(s, x, y + 20, w, 66, [run(big, big_size, INK, LIGHT)], line=1.1)
    text(s, x, y + 100, w, head_h, [run(head, 26, INK, SANS, True)], line=1.3)
    text(s, x, y + 100 + head_h + 10, w, 330, [run(body, body_size, BODY)], line=1.45)


# ---------------------------------------------------------------- 1. Cover

def cover(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    text(s, 160, 140, 1600, 30, [kick("End-sem · Computer vision and perception")])
    text(s, 160, 205, 1600, 250, [run("Right in meaning,", 112, INK, LIGHT, spacing=-0.03),
                                  run("wrong in place?", 112, INK, LIGHT, spacing=-0.03)], line=1.05)
    text(s, 160, 470, 1500, 150, [run(
        "ASP asks a language model to guess the rooms and objects a robot has not yet seen, then drives "
        "to where the guesses disagree. Its author says the guesses are often in the wrong place but name "
        "the right things, and that this is enough. We test that claim in three parts.", 30, BODY)], line=1.5)
    cols = [("Part 1 · The live test", "Do the guesses improve a live robot's map? A random-guess placebo, "
                                         "our filter, exact objects and plain frontier."),
            ("Part 2 · The paper's scale", "The author's own scoring code, a reference rebuilt his way, and "
                                           "his Fig. 4 numbers beside ours."),
            ("Part 3 · The author's defense", "Is the meaning right beyond base rates? Would that be enough "
                                              "for ASP's score? Is it the model?")]
    for i, (name, body) in enumerate(cols):
        x = 160 + i * 552
        hline(s, x, 688, x + 496, 688, INK, 2)
        text(s, x, 708, 496, 30, [run(f"{i + 1:02d}", 20, FAINT, MONO)], line=1.5)
        text(s, x, 748, 496, 45, [run(name, 30, INK, SANS, True)], line=1.5)
        text(s, x, 803, 496, 110, [run(body, 25, BODY)], line=1.45)
    hline(s, 160, 935, 1760, 935, RULE)
    text(s, 160, 958, 900, 32, [run("Sher Partap Singh · Preesha Katial · Ananya Singla", 24, MID)])
    text(s, 860, 958, 900, 32, [run("Base paper: Tang & Chaudhari, Active Semantic Perception, "
                                    "arXiv:2510.05430", 24, MID)], PP_ALIGN.RIGHT)


# ---------------------------------------------------------------- 2. ASP in one picture

OBSERVED = [(0.15, 0.25), (0.45, 0.72), (0.82, 0.30)]
GUESSES = [[(.62, .80), (.90, .62), (.30, .08)], [(.10, .78), (.70, .90), (.92, .10)],
           [(.55, .10), (.95, .50), (.25, .92)], [(.04, .50), (.62, .52), (.85, .88)],
           [(.36, .30), (.72, .08), (.15, .95)], [(.95, .90), (.30, .52), (.60, .04)],
           [(.08, .06), (.55, .95), (.98, .30)], [(.70, .46), (.20, .62), (.45, .02)]]


def glyph(s, x, y, w, h, member=None, r=6):
    """A small scene graph: the same mapped nodes, and one member's guessed nodes."""
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


def asp_picture(prs, N):
    s = frame(prs, 2, "ASP in one picture", "ASP scores views by disagreement, not by truth")
    top, h = 290, 330

    def box(x, w, head):
        rect(s, x, top, w, h, WASH, RULE)
        label(s, x + 24, top + 22, w - 48, head)

    def arrow(x):
        svg_text(s, x + 30, top + h / 2 + 18, "→", 56, FAINT, anchor="middle", w=80)

    box(120, 270, "Map so far")
    glyph(s, 150, top + 100, 210, 170, None, 8)
    text(s, 150, top + 280, 220, 30, [run("filled: mapped", 18, MID)])
    arrow(390)
    box(450, 560, "8 guessed graphs")
    for i in range(8):
        gx = 471 + (i % 4) * 130
        gy = top + 90 + (i // 4) * 120
        glyph(s, gx, gy, 112, 90, i, 5)
    arrow(1010)
    box(1070, 340, "Each candidate view")
    text(s, 1094, top + 100, 292, 200, [run("For each graph, what a camera at that view would see. "
                                             "Then: how far the 8 graphs differ.", 24, BODY)], line=1.45)
    arrow(1410)
    box(1470, 330, "Pick")
    text(s, 1494, top + 100, 282, 200, [run("The view with the top score. Its path cost counts against "
                                             "it.", 24, BODY)], line=1.45)

    text(s, 120, 648, 1680, 60, [run(f"score = gain(objects) + gain(rooms) {MINUS} {DISTANCE_WEIGHT} × distance",
                                     36, INK, MONO)], PP_ALIGN.CENTER, 1.3)
    cols = [("Gain", "How much the 8 graphs disagree about what the view shows. If all 8 agree, the gain is "
                     "zero."),
            ("Truth", "No term asks whether a guess is true."),
            ("Unknown space", "No term asks whether the space is unexplored.")]
    for i, (head, body) in enumerate(cols):
        x = 120 + i * 580
        hline(s, x, 730, x + 520, 730, INK, 2)
        text(s, x, 746, 520, 40, [run(head, 28, INK, SANS, True)], line=1.3)
        text(s, x, 790, 520, 100, [run(body, 23, BODY)], line=1.45)
    callout(s, 120, 900, 1680, 90, "Reading.", "A guess earns score by differing from the others, not by "
                                               "being right.", 26)


# ---------------------------------------------------------------- 3. Part 1, contrasts

def live_test(prs, N):
    s = frame(prs, 3, "Part 1 · The live test · 2 homes, seeds 42-44, human labels",
              "Live test: no detectable difference in any contrast")
    L = 120
    fr = json.load(open(FRONTIER))  # full precision; numbers.csv holds the same values to 4 places
    label(s, L, 262, 1500, "Difference in F1, area under the curve to 60 m, with its 95% interval")
    # E2 is registered as official minus filter_only; the slide shows filter minus LLM, so its sign flips.
    e2 = (-N["E2:hm3d:60m:statistic"], -N["E2:hm3d:60m:permutation_hi"], -N["E2:hm3d:60m:permutation_lo"])
    rows = [("LLM guesses vs random guesses",
             (N["E1:hm3d:60m:statistic"], N["E1:hm3d:60m:permutation_lo"], N["E1:hm3d:60m:permutation_hi"])),
            ("LLM + our filter vs LLM", e2),
            ("LLM vs plain frontier", (fr["official"]["d60"], *fr["official"]["ci60"])),
            ("Random guesses vs plain frontier", (fr["placebo"]["d60"], *fr["placebo"]["ci60"])),
            ("Exact objects vs random guesses (871)", (N["E3:hm3d:60m:statistic"], None, None))]
    x0, x1, lo, hi = 650, 1230, -0.08, 0.10

    def dx(v):
        return x0 + (min(max(v, lo), hi) - lo) / (hi - lo) * (x1 - x0)

    top, step = 330, 84
    for v in (-0.05, 0.0, 0.05):
        hline(s, dx(v), top - 20, dx(v), top + step * len(rows) - 30, LINE if v else MID, 1 if v else 2,
              dash=bool(v))
        svg_text(s, dx(v), top + step * len(rows) + 6, sg(v, 2) if v else "0", 20, FAINT, anchor="middle", w=100)
    for i, (name, (d, a, b)) in enumerate(rows):
        y = top + i * step + 18
        text(s, L, y - 22, 500, 40, [run(name, 24, INK)], line=1.3)
        if a is None:  # unbounded at 3 v 3: drawn to both edges
            hline(s, dx(lo), y, dx(hi), y, INK, 3, dash=True)
            svg_text(s, dx(lo) - 2, y + 9, "◀", 22, INK, anchor="end", w=30)
            svg_text(s, dx(hi) + 2, y + 9, "▶", 22, INK, w=30)
            tail = f"{sg(d)}  (p {num(N['E3:hm3d:60m:p'], 2)}; unbounded)"
        else:
            hline(s, dx(a), y, dx(b), y, INK, 3)
            tail = f"{sg(d)}  ({sg(a)} to {sg(b)})"
        oval(s, dx(d), y, 11, INK, WHITE, 3)
        svg_text(s, x1 + 50, y + 8, tail, 22, INK, MONO, w=520)
    note(s, L, top + step * len(rows) + 36, 1680, 3,
         "Registered tests, pilot status. The filter row was registered as LLM minus filter; its sign is flipped "
         "here. Exact objects: home 871 only, 3 runs against 3. The smallest p a 3-v-3 test can give is 0.10, "
         "so its interval has no bounds. The LLM arm has 2 runs on 853.")
    callout(s, L, 900, 1680, 90, "Registered reading.",
            "No detectable difference in any contrast. Effects up to the end of each interval stay possible.", 24)


# ---------------------------------------------------------------- 4. Part 1, why

def why(prs, N):
    s = frame(prs, 4, "Part 1 · Why, from an offline replay of saved stages",
              "Why: swapping the guesses barely moves the pick")
    L = 120
    label(s, L, 262, 820, "How far the top-scored view moves (median, m)")
    bars = [("LLM's guesses → random set", N["replay:official:move_plc"]),
            ("One random set → another", N["replay:official:move_floor"])]
    for i, (name, v) in enumerate(bars):
        y = 330 + i * 80
        text(s, L, y, 420, 40, [run(name, 24, INK)], line=1.3)
        rect(s, 560, y + 2, v / 3.0 * 330, 34, INK if i == 0 else MID)
        svg_text(s, 560 + v / 3.0 * 330 + 16, y + 30, f"{v:.2f}", 26, INK, MONO, w=100)
    stat(s, L, 520, 380, sg(N["replay:official:diff_move_plc_minus_floor"], 2) + " m",
         f"LLM v random, beyond a redraw ({sg(N['replay:official:diff_move_plc_minus_floor:ci_lo'], 2)} to "
         f"{sg(N['replay:official:diff_move_plc_minus_floor:ci_hi'], 2)})", 3)
    stat(s, 540, 520, 380, sg(N["replay:official:diff_move_oracle_minus_floor"], 2) + " m",
         f"exact objects v random, beyond a redraw ({sg(N['replay:official:diff_move_oracle_minus_floor:ci_lo'], 2)}"
         f" to {sg(N['replay:official:diff_move_oracle_minus_floor:ci_hi'], 2)})", 3)

    R = 1040
    label(s, R, 262, 760, "Does the score rank views by unseen true objects?")
    text(s, R, 296, 760, 30, [run("Median Spearman ρ, official stages", 20, MID)])
    cols = [("LLM's guesses", N["cf:rho_score_U360_median:official:actual"]),
            ("Random set", N["cf:rho_score_U360_median:official:plc"]),
            ("No guesses", N["cf:rho_score_U360_median:official:obs"]),
            ("Exact objects", N["cf:rho_score_U360_median:official:orc"])]
    base, sc = 640, 330  # baseline y of rho = 0, pixels per unit rho
    hline(s, R, base, R + 760, base, MID, 2)
    for i, (name, v) in enumerate(cols):
        cx = R + 90 + i * 190
        hgt = abs(v) * sc
        rect(s, cx - 42, base - hgt if v >= 0 else base, 84, max(hgt, 2), INK if i != 3 else MID)
        svg_text(s, cx, (base - hgt - 14) if v >= 0 else (base + hgt + 34), num(v, 2), 26, INK, MONO,
                 anchor="middle", w=120)
        text(s, cx - 90, 720, 180, 60, [run(name, 21, BODY)], PP_ALIGN.CENTER, 1.3)
    note(s, L, 790, 1680, 3,
         f"{int(N['replay:official:n_stages'])} official stages, first-stage candidates, same robot state; only the "
         "guess file changes. Exact objects score high in part by construction: the count uses the same objects.")
    callout(s, L, 900, 1680, 90, "Reading.",
            "A random set moves the pick about as far as the LLM's guesses do, and ranks views about as they do.",
            24)


# ---------------------------------------------------------------- 5. Part 1, limits

def live_limits(prs, N):
    s = frame(prs, 5, "Part 1 · Limits of the live test", "Live test limits: what it could not rule out")
    xs = (120, 700, 1280)
    w = 520
    # 1. the interval
    hline(s, xs[0], 262, xs[0] + w, 262, INK, 2)
    text(s, xs[0], 280, w, 66, [run(sg(N["E1:hm3d:60m:permutation_hi"]), 56, INK, LIGHT)], line=1.1)
    text(s, xs[0], 358, w, 62, [run("top of the 95% interval for LLM − random", 22, MID)], line=1.4)
    text(s, xs[0], 440, w, 300, [run(
        f"The interval runs from {sg(N['E1:hm3d:60m:permutation_lo'])} to {sg(N['E1:hm3d:60m:permutation_hi'])}. "
        f"With 80% power the test sees only differences of about 0.024 to 0.028. A real gain of "
        f"{sg(N['E1:hm3d:60m:permutation_hi'])} stays possible.", 23, BODY)], line=1.45)
    # 2. pacing and agreement
    flagged = [(int(N[f"pacing_flag:stages_off:{k}"]), int(N[f"pacing_flag:stages_compared:{k}"]))
               for k in ("00853_s42", "00853_s43", "00871_s42", "00871_s43", "00871_s44")]
    hline(s, xs[1], 262, xs[1] + w, 262, INK, 2)
    text(s, xs[1], 280, w, 66, [run("5 of 5 pairs", 56, INK, LIGHT)], line=1.1)
    text(s, xs[1], 358, w, 62, [run("differ in pacing between placebo and LLM", 22, MID)], line=1.4)
    text(s, xs[1], 440, w, 160, [run(
        "A pair is flagged if the placebo's wait differs from its LLM partner's by more than 20% at three or more "
        "stages. Stages off, per pair: " + ", ".join(f"{a} of {b}" for a, b in flagged) + ".", 21, BODY)], line=1.45)
    hline(s, xs[1], 620, xs[1] + w, 620, RULE)
    text(s, xs[1], 632, w, 66, [run(f"{100 * N['agreement:same_label_1m:official']:.1f}% v "
                                    f"{100 * N['agreement:same_label_1m:placebo']:.1f}%", 48, INK, LIGHT)], line=1.1)
    text(s, xs[1], 696, w, 100, [run("of guesses matched by another member within 1 m, LLM v placebo. "
                                     "ASP's score falls when members agree.", 21, MID)], line=1.4)
    # 3. the 60 m lead
    hline(s, xs[2], 262, xs[2] + w, 262, INK, 2)
    text(s, xs[2], 280, w, 66, [run(sg(N["secondary:E1:f1point60:statistic"]), 56, INK, LIGHT)], line=1.1)
    text(s, xs[2], 358, w, 62, [run("F1 at 60 m: the LLM arm led", 22, MID)], line=1.4)
    text(s, xs[2], 440, w, 330, [run(
        f"p {num(N['secondary:E1:f1point60:p'], 3)}, and {num(N['holm_E1_secondaries:f1point60'], 2)} after Holm "
        f"over six secondary tests. At 30 m the difference is {sg(N['secondary:E1:f1point30:statistic'])} "
        f"(p {num(N['secondary:E1:f1point30:p'], 2)}). On 853 the placebo led earlier "
        f"({sg(N['secondary:E1:f1point30:per_scene_d:00853'])} at 30 m). The primary test, over the whole path, "
        "shows no detectable difference.", 23, BODY)], line=1.45)
    callout(s, 120, 850, 1680, 140, "Reading.",
            "Our test found no detectable difference at its size. That is not proof of no effect. The two arms "
            "also differ in pacing and in member agreement, so content is not the only change between them.", 24)


# ---------------------------------------------------------------- 6. Part 2, rules

def timeline(s, x0, x1, y, budget, mark):
    hline(s, x0, y, x1, y, MID, 2)
    for frac in (0.1, 0.5, 1.0):
        xx = x0 + (x1 - x0) * frac
        hline(s, xx, y - 12, xx, y + 12, INK, 2)
        svg_text(s, xx, y - 22, f"{int(round(frac * 100))}%", 20, FAINT, anchor="middle", w=100)
        svg_text(s, xx, y + 46, f"{frac * budget:.0f} s", 24, INK, MONO, anchor="middle", w=140)
    if mark:
        text(s, x0, y + 62, 600, 26, [run("TO BE UPDATED", 16, ACCENT, SANS, True, spacing=0.14)])


def paper_rules(prs, budgets, checks, slots):
    s = frame(prs, 6, "Part 2 · Same rules as the paper", "Same rules as the paper")
    upd = slots["table871_updated"]
    L = 120
    stops = [checks[sc]["use_rule"]["reached"] for sc in ("00853", "00871")]
    label(s, L, 262, 760, "As in the paper")
    blocks = [("Scoring", "the author's own F1 and GED code, on his time axis.", 2),
              ("Reference", "his protocol, scripted: a tour through every reachable point on the start floor, "
                            f"with the same mapper ({stops[0]} and {stops[1]} stops).", 3),
              ("Frontier", "run to its natural end: 5 of 5 runs on 853, 1 of 5 on 871.", 2)]
    y = 304
    for head, body, lines in blocks:
        text(s, L, y, 760, 38 * lines + 6, [[run(head + ". ", 24, INK, SANS, True), run(body, 24, BODY)]], line=1.45)
        y += 38 * lines + 24
    label(s, L, y + 10, 760, "Where we differ")
    text(s, L, y + 48, 760, 110, [[run("LLM. ", 24, INK, SANS, True),
                                    run("Ours is DeepSeek; the author's is Gemini 2.5 Pro.", 24, BODY)]], line=1.45)
    text(s, L, y + 130, 760, 110, [[run("Runs. ", 24, INK, SANS, True),
                                     run("We average several runs per cell and say how many reach each time.",
                                         24, BODY)]], line=1.45)

    R = 1000
    label(s, R, 262, 800, "What “budget” means")
    text(s, R, 300, 800, 130, [run("The paper reads F1 and GED at 10%, 50% and 100% of a fixed navigation "
                                    "time. It gives no value for that time. We set one for each home.", 24, BODY)],
         line=1.45)
    text(s, R, 468, 120, 36, [run("Home 853", 22, INK, SANS, True)])
    timeline(s, R + 150, R + 770, 520, budgets["00853"], False)
    text(s, R, 678, 120, 36, [run("Home 871", 22, INK, SANS, True)])
    timeline(s, R + 150, R + 770, 730, budgets["00871"], not upd)
    note(s, R, 820, 800, 5,
         "853: the median end of 5 frontier runs that ran to their natural end (612 to 868 s). 871: only 1 of 5 "
         "finished, so the registered fallback applies, the end of the frontier-made reference run. The reruns "
         "replace it with the median of the valid runs.")


# ---------------------------------------------------------------- 7. Part 2, the table

def paper_table(prs, C, budgets, slots):
    pend = is_pending(slots["asp853_full_budget"])
    s = frame(prs, 7, "Part 2 · Object F1 × 100 at 10, 50 and 100% of the budget",
              "The paper's Fig. 4 numbers beside ours", pending=pend)
    upd = slots["table871_updated"]

    def ours(scene, arm, frac):
        c = C.get((scene, arm, frac))
        if not c:
            return None, None
        sv = c["stage_value_x100"]
        if not sv["n"] or sv["n"] * 2 < c["n_runs"]:
            return None, "no run reaches it" if not sv["n"] else f"{sv['n']} of {c['n_runs']} runs"
        return sv["mean"], (f"{sv['n']} of {c['n_runs']} runs" if sv["n"] < c["n_runs"] else None)

    def row_cells(scene, arm, mark):
        out = []
        for frac in ("10", "50", "100"):
            v, sub = ours(scene, arm, frac)
            main = "none" if v is None else f"{v:.1f}"
            color = INK if v is not None else FAINT
            if mark:
                out.append((main, "to be updated", FAINT if v is not None else FAINT, True))
            else:
                out.append((main, sub, color, False))
        return out

    def paper_cells_row(scene, arm):
        return [(f"{C[(scene, arm, f)]['paper_f1_x100']:.1f}", None, INK, False) for f in ("10", "50", "100")]

    n = {k: C[k]["n_runs"] for k in C}

    def runs(scene, arm):
        k = n[(scene, arm, "10")]
        return f"{k} run" + ("" if k == 1 else "s")

    full = slots["asp853_full_budget"]
    fb = [tbd(full[k], lambda v: f"{v:.1f}") for k in ("f1_10", "f1_50", "f1_100")]
    full_row = [(t, "may be run" if v is None else None, c, False) for (t, c), v in
                zip(fb, (full["f1_10"], full["f1_50"], full["f1_100"]))]

    t853 = [("Paper · ASP", paper_cells_row("00853", "official"), False),
            ("Paper · frontier", paper_cells_row("00853", "frontier_end"), False),
            (f"Ours · ASP, DeepSeek ({runs('00853', 'official')})", row_cells("00853", "official", False), False),
            (f"Ours · random guesses ({runs('00853', 'placebo')})", row_cells("00853", "placebo", False), False),
            (f"Ours · frontier ({runs('00853', 'frontier_end')})", row_cells("00853", "frontier_end", False), False),
            ("Ours · ASP to the full budget", full_row, pend)]
    t871 = [("Paper · ASP", paper_cells_row("00871", "official"), False),
            ("Paper · frontier", paper_cells_row("00871", "frontier_end"), False),
            (f"Ours · ASP, DeepSeek ({runs('00871', 'official')})", row_cells("00871", "official", not upd), False),
            (f"Ours · random guesses ({runs('00871', 'placebo')})", row_cells("00871", "placebo", not upd), False),
            (f"Ours · frontier ({runs('00871', 'frontier_end')})", row_cells("00871", "frontier_end", not upd), False)]

    def table(x, lw, cw, title, rows, tag):
        label(s, x, 262, lw + 3 * cw, title)
        if tag:
            pill(s, x + lw + 3 * cw - 250, 256, 250, 32, "TO BE UPDATED", "fde8dc", ACCENT)
        y = 304
        for j, head in enumerate(("10%", "50%", "100%")):
            svg_text(s, x + lw + j * cw + cw / 2, y + 34, head, 20, MID, SANS, anchor="middle", w=cw)
        y += 46
        hline(s, x, y, x + lw + 3 * cw, y, LINE)
        for lab, cells, dashed in rows:
            rh = 66
            if dashed:
                r = rect(s, x, y + 2, lw + 3 * cw, rh - 4, WASH, LINE, 2)
                r.line.dash_style = MSO_LINE.DASH
            text(s, x + 8, y + 18, lw - 10, 30, [run(lab, 19, INK if lab.startswith("Paper") else BODY)], line=1.2)
            for j, (main, sub, color, mark) in enumerate(cells):
                cx = x + lw + j * cw
                text(s, cx, y + 6, cw, 34, [run(main, 26, color, MONO)], PP_ALIGN.CENTER, 1.2)
                if sub:
                    text(s, cx, y + 42, cw, 20, [run(sub, 16, ACCENT if mark else FAINT)], PP_ALIGN.CENTER, 1.2)
            y += rh
            hline(s, x, y, x + lw + 3 * cw, y, RULE)

    table(120, 380, 150, f"Home 853 · budget {budgets['00853']:.0f} s", t853, False)
    table(1000, 350, 150, f"Home 871 · budget {budgets['00871']:.0f} s", t871, not upd)
    note(s, 120, 776, 1680, 3,
         "Paper: Fig. 4 (left) of arXiv 2510.05430v2, one run against its own reference. Ours: mean of runs, "
         "stage value, against the rebuilt reference; a time shows only if at least half the runs reach it. "
         "ASP runs stop at 60 m. The 871 budget and every 871 number of ours will change after the reruns.")
    # Leads are differences of the values as shown (one decimal), so a reader can check them by hand.
    a10, a50, f10, f50 = (round(C[("00853", arm, fr)]["stage_value_x100"]["mean"], 1)
                          for arm, fr in (("official", "10"), ("official", "50"),
                                          ("frontier_end", "10"), ("frontier_end", "50")))
    p10 = C[("00853", "official", "10")]["paper_f1_x100"] - C[("00853", "frontier_end", "10")]["paper_f1_x100"]
    p50 = C[("00853", "official", "50")]["paper_f1_x100"] - C[("00853", "frontier_end", "50")]["paper_f1_x100"]
    callout(s, 120, 872, 1680, 124, "Reading.",
            f"The paper's ASP lead over frontier on 853 is {p10:.1f} points at 10% and {p50:.1f} at 50%. It did not "
            f"appear on 853 at 10% and 50%, with DeepSeek and a rebuilt reference: ours is {num(a10 - f10)} and "
            f"{num(a50 - f50)} points, from 2 ASP runs.", 22)


# ---------------------------------------------------------------- 8. Part 2, limits

def paper_limits(prs, C, checks):
    s = frame(prs, 8, "Part 2 · Limits of the comparison", "What limits the paper comparison")
    c3 = [checks[sc]["C3"]["apr_a_recall_vs_hm3d"] for sc in ("00853", "00871")]
    c5 = [checks[sc]["C5"]["apr_a_vs_frontier_made_f1_prec_rec"][0] for sc in ("00853", "00871")]
    rooms = [checks[sc]["C1"]["room_nodes"] for sc in ("00853", "00871")]
    prooms = [checks[sc]["C1"]["paper_rooms"] for sc in ("00853", "00871")]
    area = [checks[sc]["C1"]["start_island_area_m2"] for sc in ("00853", "00871")]
    parea = [checks[sc]["C1"]["paper_area_m2"] for sc in ("00853", "00871")]
    f60_50 = C[("00853", "frontier_60m", "50")]["stage_value_x100"]["mean"]
    fend_50 = C[("00853", "frontier_end", "50")]["stage_value_x100"]["mean"]
    f60_10 = C[("00853", "frontier_60m", "10")]["stage_value_x100"]["mean"]
    fend_10 = C[("00853", "frontier_end", "10")]["stage_value_x100"]["mean"]
    cards = [
        (f"{100 * c3[0]:.0f}%, {100 * c3[1]:.0f}%", "The reference is rebuilt, not the author's",
         f"It holds {100 * c3[0]:.0f}% and {100 * c3[1]:.0f}% of the human-labelled objects (853, 871). Its F1 "
         f"against our older frontier-made reference is {c5[0]:.2f} and {c5[1]:.2f}. The repeat tour froze, so we "
         "cannot say how far the reference itself moves. It is being rerun."),
        (f"{rooms[0]} v {prooms[0]} rooms", "Rooms and floor area differ (check C1)",
         f"Rooms: {rooms[0]} and {rooms[1]}, against the paper's {prooms[0]} and {prooms[1]}. Start-floor navmesh: "
         f"{area[0]:.0f} and {area[1]:.0f} m², against {parea[0]:.0f} and {parea[1]:.0f}. We cannot explain "
         "the gap yet."),
        (f"{f60_50:.1f} v {fend_50:.1f}", "Two batches of one explorer differ",
         f"Frontier on 853 at 50% of the budget: {f60_50:.1f} in the October batch (3 runs, cut at 60 m) and "
         f"{fend_50:.1f} in the November batch (5 runs, to the natural end). At 10%: {f60_10:.1f} and "
         f"{fend_10:.1f}."),
        ("60 m", "ASP runs stop at 60 m",
         "No ASP run reaches 100% of the budget, so ASP has no value in that column. ASP ran in October, frontier "
         "in November. In the host's copy of the code, frontier's clock also counts its waits for a path and "
         "ASP's does not."),
    ]
    for i, (big, head, body) in enumerate(cards):
        card(s, 120 + i * 430, 390, 262, big, head, body, 50, 80, 23)
    callout(s, 120, 860, 1680, 130, "Reading.",
            "Every number in the table sits on a rebuilt reference. We read it as a check on the paper's scale, "
            "not as a test of the paper's claim.", 24)


# ---------------------------------------------------------------- 9. Part 3, the defense

def defense(prs):
    s = frame(prs, 9, "Part 3 · The author's defense", "The author's defense, in three questions")
    label(s, 120, 262, 1680, "What the author told us")
    text(s, 120, 296, 1680, 90, [run("The guesses are often in the wrong place, but they name the right "
                                     "things, and that is enough.", 32, INK, LIGHT)], line=1.4)
    steps = [("Is the meaning right, beyond base rates?",
              "Score the saved guesses against controls that see the same map: a prior from house statistics, "
              "the same model asked about another house, and its own guesses with positions shuffled.",
              "The prompt says a scene may contain more than one bedroom and more than one bathroom. Naming one "
              "proves little."),
             ("Would right meaning be enough?",
              "Offline, give ASP true labels with the placement error real models make. See how much of its view "
              "ranking survives.",
              "ASP's score rewards disagreement. Guesses that all agree add nothing to it."),
             ("Is it the model?",
              "Replay Claude Haiku 5.5 and Claude Opus 5.5 on the same 44 saved inputs as DeepSeek, so a gap "
              "points to the model and not the inputs.",
              "If the Claude replays do not run, DeepSeek's results stay exploratory.")]
    for i, (name, what, why_) in enumerate(steps):
        x = 120 + i * 580
        hline(s, x, 420, x + 520, 420, INK, 2)
        text(s, x, 436, 520, 30, [run(f"{i + 1:02d}", 20, FAINT, MONO)], line=1.5)
        text(s, x, 474, 520, 80, [run(name, 28, INK, SANS, True)], line=1.3)
        text(s, x, 566, 520, 150, [run(what, 22, BODY)], line=1.45)
        text(s, x, 724, 520, 130, [[run("WHY · ", 16, FAINT, SANS, spacing=0.18), run(why_, 20, MID)]],
             line=1.45)
    callout(s, 120, 868, 1680, 122, "Same pass.",
            "The validity layer, for every model: what our filter removes, and whether what it keeps is right more "
            "often. We hash the rules before any Claude output is scored.", 24)


# ---------------------------------------------------------------- 10. Part 3, base rates and levels

def base_rates(prs, slots):
    br = slots["base_rates"]
    s = frame(prs, 10, "Part 3 · Slot: definitions now, numbers later", "Base rates, and four levels of “right”",
              pending=is_pending(br))
    L = 120
    label(s, L, 262, 780, "The prompt names the room types")
    text(s, L, 300, 780, 130, [run("“Scene may contain more than one bedroom and more than one bathroom.”",
                                    28, INK, LIGHT)], line=1.4)
    text(s, L, 410, 780, 70, [run("So naming a bedroom or a bathroom proves little. We count how often those "
                                   "rooms stay unseen anyway.", 22, BODY)], line=1.45)
    label(s, L, 510, 780, "Base rates, under the frozen truth rule")
    rows = [("An unseen bathroom remains in", br["unseen_bathroom"]),
            ("An unseen bedroom remains in", br["unseen_bedroom"]),
            ("An unseen kitchen remains in", br["unseen_kitchen"])]
    y = 552
    for name, v in rows:
        t, c = tbd(v, lambda x: f"{100 * x:.0f}%")
        text(s, L, y, 560, 36, [run(name + " … of stages", 23, BODY)], line=1.3)
        text(s, L + 600, y - 4, 180, 40, [run(t, 30, c, MONO)], PP_ALIGN.RIGHT, 1.2)
        hline(s, L, y + 44, L + 780, y + 44, RULE)
        y += 56
    t1, c1 = tbd(br["new_rooms_bedroom"], str)
    t2, c2 = tbd(br["new_rooms_bathroom"], str)
    t3, c3 = tbd(br["new_rooms_total"], str)
    text(s, L, y + 6, 780, 70, [[run("The LLM's new rooms: ", 23, BODY), run(t1, 23, c1, MONO),
                                  run(" bedrooms and ", 23, BODY), run(t2, 23, c2, MONO),
                                  run(" bathrooms, of ", 23, BODY), run(t3, 23, c3, MONO)]], line=1.4)

    R = 1000
    label(s, R, 262, 800, "Four levels of “right”")
    levels = [("L1", "Which room types exist unseen", "Room type T has an unseen region. Five types are typable."),
              ("L2", "Which objects exist unseen", "Class c has an instance in an unseen region."),
              ("L3", "Roughly where", "A guessed centre lies in, or within 0.5 m of, an unseen region of type T "
                                      "or holding c. Scored on the unobserved stratum only."),
              ("L4", "Exactly where", "A same-class unseen instance lies within 0.5, 1, 2 or 3 m. "
                                      "Secondary.")]
    y = 304
    for tag, head, body in levels:
        rect(s, R, y, 90, 120, WASH, RULE)
        text(s, R, y + 36, 90, 50, [run(tag, 36, INK, MONO)], PP_ALIGN.CENTER, 1.2)
        text(s, R + 112, y + 4, 690, 36, [run(head, 26, INK, SANS, True)], line=1.3)
        text(s, R + 112, y + 46, 690, 80, [run(body, 21, BODY)], line=1.4)
        y += 138
    callout(s, L, 880, 1680, 110, "Controls a skeptic accepts.",
            "A prior that sees the same map. The same model asked about the wrong house. The same guesses with "
            "positions shuffled.", 24)


# ---------------------------------------------------------------- 11. Part 3, the room test

def room_test(prs, slots):
    rt = slots["room_test"]
    s = frame(prs, 11, "Part 3 · Slot: the paper's room test", "The paper's room test, with a chance rate",
              pending=is_pending(rt))
    L = 120
    label(s, L, 262, 760, "The paper's rule")
    text(s, L, 300, 760, 250, [run("A room counts as predicted if at least 2 of 8 samples place a room of its "
                                    "type within 2.5 m of its centre, before the robot finds it. The paper "
                                    "reports 9 of 28 rooms.", 25, BODY)], line=1.5)
    label(s, L, 520, 760, "What we add")
    text(s, L, 558, 760, 300, [run("The same rule on random guesses of the LLM's shape. That gives the rate chance "
                                    "alone produces. On the Claude replays, which have 4 members, we report 1 of 4 "
                                    "and 2 of 4 beside the same chance rate, and do not compare them with the "
                                    "paper's 9 of 28.", 23, BODY)], line=1.5)

    R, W = 960, 840
    label(s, R, 262, W, "Rooms predicted before they were found")
    rows = [("LLM guesses (8 members)", rt["llm_live"]), ("Filtered LLM guesses", rt["filter_live"]),
            ("Random guesses, chance", rt["placebo_live"]), ("Paper, Gemini 2.5 Pro", {"hit": 9, "of": 28})]
    y, bx, bw = 310, R + 300, 380
    for name, d in rows:
        text(s, R, y + 6, 290, 40, [run(name, 21, BODY)], line=1.3)
        if d["hit"] is None or d["of"] is None:
            r = rect(s, bx, y + 8, bw, 32, WASH, LINE, 2)
            r.line.dash_style = MSO_LINE.DASH
            svg_text(s, bx + bw + 14, y + 34, "TBD", 24, FAINT, MONO, w=120)
        else:
            rect(s, bx, y + 8, bw, 32, RULE)
            rect(s, bx, y + 8, bw * d["hit"] / d["of"], 32, INK)
            svg_text(s, bx + bw + 14, y + 34, f"{d['hit']} of {d['of']}", 24, INK, MONO, w=160)
        y += 66
    hline(s, R, y + 6, R + W, y + 6, RULE)
    y += 22
    label(s, R, y, W, "Claude replays, 4 members")
    y += 40
    for name, k in (("1 of 4 members", "claude_1of4"), ("2 of 4 members", "claude_2of4")):
        d = rt[k]
        text(s, R, y + 6, 290, 40, [run(name, 21, BODY)], line=1.3)
        a = "TBD" if d["hit"] is None else f"{d['hit']} of {d['of']}"
        b = "TBD" if d["chance_hit"] is None else f"{d['chance_hit']} of {d['chance_of']}"
        text(s, bx - 20, y + 4, 420, 40, [[run("Claude ", 20, MID), run(a, 24, FAINT if a == "TBD" else INK, MONO),
                                           run("   chance ", 20, MID),
                                           run(b, 24, FAINT if b == "TBD" else INK, MONO)]], line=1.3)
        y += 56
    note(s, L, 880, 1680, 3,
         "Live arms come from the October runs, which have 8 members. A room is “not yet found” "
         "if it was unseen at stage 0. We score the test with and without the type match.")


# ---------------------------------------------------------------- 12. Part 3, three models

def three_models(prs, slots):
    m = slots["models"]
    s = frame(prs, 12, "Part 3 · Slot: same 44 inputs for every model", "Same inputs, three models",
              pending=is_pending(m))
    X, lw, cw = 120, 360, 440
    y0 = 270
    for j, head in enumerate(("L1 · room types", "L2 · objects", "L3 · roughly where")):
        text(s, X + lw + j * cw, y0, cw - 20, 30, [kick(head, 18, 0.14)])
    hline(s, X, y0 + 40, X + lw + 3 * cw, y0 + 40, LINE)
    names = [("deepseek", "DeepSeek", "exploratory"), ("haiku", "Claude Haiku 5.5", "blind test"),
             ("opus", "Claude Opus 5.5", "blind test")]
    y = y0 + 52
    for key, name, kind in names:
        text(s, X, y + 22, lw - 20, 40, [run(name, 26, INK, SANS, True)], line=1.2)
        text(s, X, y + 62, lw - 20, 30, [run(kind, 18, MID)], line=1.2)
        for j, lvl in enumerate(("L1", "L2", "L3")):
            d = m[key][lvl]
            cx = X + lw + j * cw
            if d["lift_pp"] is None:
                r = rect(s, cx, y + 8, cw - 30, 118, WASH, LINE, 2)
                r.line.dash_style = MSO_LINE.DASH
                svg_text(s, cx + (cw - 30) / 2, y + 66, "TBD", 30, FAINT, MONO, anchor="middle", w=200)
                svg_text(s, cx + (cw - 30) / 2, y + 102, "lift · 95% interval · verdict", 18, FAINT,
                         anchor="middle", w=360)
            else:
                text(s, cx, y + 8, cw - 30, 50, [run(sg(d["lift_pp"], 1) + " pp", 36, INK, MONO)], line=1.2)
                lo_, hi_ = d["lo"], d["hi"]
                ci = "" if lo_ is None or hi_ is None else f"95% interval {sg(lo_, 1)} to {sg(hi_, 1)}"
                text(s, cx, y + 60, cw - 30, 30, [run(ci, 19, MID)], line=1.2)
                text(s, cx, y + 92, cw - 30, 30, [run(d["verdict"] or "TBD", 22, INK, SANS, True)], line=1.2)
        y += 140
        hline(s, X, y, X + lw + 3 * cw, y, RULE)
    note(s, X, 750, 1680, 3,
         "Lift: the model's rate minus the strongest comparator's rate, with the comparators of slide 10. "
         "Supported: Holm-adjusted p below 0.05. Rejected: the interval's top lies below a margin set in the "
         "pre-registration. Inconclusive: neither. The test family is 2 Claude models × 3 levels.")
    callout(s, X, 868, 1680, 122, "Rules.",
            "DeepSeek is exploratory, because we saw pilot numbers first. Under a null the verdict is "
            "Inconclusive, not Mixed. At 44 inputs, L1 cannot decide.", 24)


# ---------------------------------------------------------------- 13. Part 3, the oracle factorial

def factorial(prs, slots):
    f = slots["factorial"]
    s = frame(prs, 13, "Part 3 · Slot: the oracle factorial, offline", "Would right meaning be enough for ASP's score?",
              pending=is_pending(f))
    L = 120
    label(s, L, 262, 800, "Member sets we score offline")
    arms = [("F1", "True unseen objects at true positions (best case)"),
            ("F-room", "True room types at their footprints"),
            ("F3", "True labels moved by a model's measured placement error"),
            ("F5", "Random guesses, two seeds (reference)"),
            ("F6", "No guesses (reference)")]
    y = 300
    for tag, body in arms:
        text(s, L, y, 110, 36, [run(tag, 24, INK, MONO)], line=1.3)
        text(s, L + 120, y + 2, 680, 60, [run(body, 22, BODY)], line=1.35)
        y += 62
    r = rect(s, L, 628, 800, 170, WASH, ACCENT, 2)
    fill_frame(r.text_frame, [[run("F0, the anchor. ", 22, ACCENT, SANS, True),
                               run("Every member holds the full truth, so members agree, ASP's score gives "
                                   "unexplored space zero, and the pick falls to the nearest candidate. This is an "
                                   "identity, not a finding.", 22, BODY)]], line=1.45, anchor=MSO_ANCHOR.MIDDLE,
               margins=(24, 14, 24, 14))
    text(s, L, 816, 800, 130, [run("Enough, if F3 gains at least half of what F1 gains over F5, and the interval "
                                   "by run lies wholly above that line. Not enough, if the top of the interval "
                                   "falls below it. Otherwise inconclusive.", 20, MID)], line=1.45)

    R, W = 1000, 800
    label(s, R, 262, W, "Spearman ρ: score against true unseen count")
    x0, x1, lo, hi = R + 300, R + 760, -0.2, 1.0

    def dx(v):
        return x0 + (min(max(v, lo), hi) - lo) / (hi - lo) * (x1 - x0)

    rows = [("F1, exact", f["F1_exact"]), ("F-room", f["F_room"]),
            ("F3, DeepSeek's error", f["F3_deepseek_err"]), ("F3, Haiku's error", f["F3_haiku_err"]),
            ("F3, Opus's error", f["F3_opus_err"]), ("F5, random", f["F5_random"]), ("F6, none", f["F6_none"])]
    top, step = 330, 62
    for v in (0.0, 0.5, 1.0):
        hline(s, dx(v), top - 14, dx(v), top + step * len(rows) - 24, MID if v == 0 else LINE, 2 if v == 0 else 1,
              dash=bool(v))
        svg_text(s, dx(v), top + step * len(rows) + 6, num(v, 1), 20, FAINT, anchor="middle", w=80)
    for i, (name, d) in enumerate(rows):
        yy = top + i * step + 14
        text(s, R, yy - 18, 290, 36, [run(name, 21, BODY)], line=1.3)
        if d["rho"] is None:
            hline(s, x0, yy, x1, yy, LINE, 3, dash=True)
            svg_text(s, x1 + 8, yy + 8, "TBD", 20, FAINT, MONO, w=70)
        else:
            if d["lo"] is not None and d["hi"] is not None:
                hline(s, dx(d["lo"]), yy, dx(d["hi"]), yy, INK, 3)
            oval(s, dx(d["rho"]), yy, 10, INK, WHITE, 3)
    sk = f["share_kept_deepseek_err"]
    t, c = tbd(sk, lambda v: f"{100 * v:.0f}%")
    text(s, R, 790, W, 60, [[run("Share of F1's gain kept at DeepSeek's error: ", 22, BODY), run(t, 26, c, MONO)]],
         line=1.4)
    callout(s, R, 850, W, 140, "Bias.",
            "F1 is high by construction, so the verdict leans toward “not enough”. It reads “not shown "
            "sufficient, on a yardstick biased toward rejection” unless the data say otherwise.", 22)


# ---------------------------------------------------------------- 14. Part 3, the validity layer

def validity(prs, N, slots):
    v = slots["validity"]
    s = frame(prs, 14, "Part 3 · Slot: the validity layer, same pass", "The validity layer across models",
              pending=is_pending(v))
    L = 120
    label(s, L, 262, 520, "October, DeepSeek only")
    stat(s, L, 300, 480, f"{100 * N['validator:removed_share:all']:.0f}%",
         f"of new guessed objects removed: {int(N['validator:removed_new:all']):,} of {int(N['validator:raw_new:all']):,}", 2)
    stat(s, L, 450, 480, f"{num(100 * N['validator:precision_kept_0.5:all'])}% v "
                         f"{num(100 * N['validator:precision_raw_0.5:all'])}%",
         "hit rate within 0.5 m, kept v all guesses", 2)
    text(s, L, 606, 480, 100, [run(f"{int(N['validator:removed_hits_0.5:all'])} of the removed guesses were hits. "
                                    "The filter made no detectable difference to the live map.", 21, MID)], line=1.45)

    X = 700
    label(s, X, 262, 1100, "Four readouts, per model (secondary, no gate)")
    heads = ["Removed", "L3 hit rate\nkept v removed", "Support v truth\nBrier score", "Yield at τ = 1\nhits / kept"]
    cws = [150, 250, 250, 220]
    lw = 230
    xs = [X + lw]
    for w_ in cws[:-1]:
        xs.append(xs[-1] + w_)
    for j, hd in enumerate(heads):
        text(s, xs[j], 300, cws[j] - 10, 60, [run(hd.replace("\n", " "), 17, MID, SANS, True)], line=1.25)
    hline(s, X, 366, X + lw + sum(cws), 366, LINE)
    names = [("deepseek", "DeepSeek"), ("haiku", "Claude Haiku 5.5"), ("opus", "Claude Opus 5.5"),
             ("random", "Random guesses")]
    y = 374
    for key, name in names:
        d = v[key]
        text(s, X, y + 16, lw - 10, 36, [run(name, 21, INK, SANS, True)], line=1.2)
        cells = [tbd(d["removed_share"], lambda a: f"{100 * a:.0f}%"),
                 None,
                 tbd(d["brier"], lambda a: f"{a:.3f}"),
                 tbd(d["yield_tau1"], lambda a: f"{100 * a:.1f}%")]
        if d["hit_kept"] is None or d["hit_removed"] is None:
            cells[1] = ("TBD", FAINT)
        else:
            cells[1] = (f"{100 * d['hit_kept']:.1f}% v {100 * d['hit_removed']:.1f}%", INK)
        for j, (t, c) in enumerate(cells):
            text(s, xs[j], y + 12, cws[j] - 10, 40, [run(t, 24, c, MONO)], line=1.2)
        y += 72
        hline(s, X, y, X + lw + sum(cws), y, RULE)
    note(s, X, y + 14, 1100, 3, "Readouts: the share the validator removes; whether valid guesses are right more "
                                "often than removed ones; whether member agreement tracks truth; the yield of the "
                                "vote filter. A fifth readout, on decisions, needed the cut bench replay.")
    callout(s, L, 850, 1680, 140, "Why it matters.",
            "The vote keeps what members agree on, and ASP's score gives agreed content zero. If the vote finds the "
            "true guesses, ASP's score still has nowhere to use them.", 24)


# ---------------------------------------------------------------- 15. Limits

def limits(prs, N):
    s = frame(prs, 15, "Limits", "What this talk cannot show")
    rows = [("Two houses.", "Homes 853 and 871 only. Any inference holds for these two homes."),
            ("Proxy truth.", "Truth comes from HM3D's human labels and a footprint rule for “seen”. "
                             "It stands in for what is in the house. It is not what the robot sees."),
            ("Static replays.", "Claude sees saved inputs, with 4 members. No robot acts on its guesses, and we "
                                "ran no live Claude test."),
            ("A weak yardstick.", f"Of the unseen true objects in view of a stop, about 1 in 12 "
                                  f"({100 * N['audit:yardstick_in_view_mapped:all']:.1f}%) reach the next map. "
                                  "The count ignores unmapped walls. Small gains in the map are hard to see."),
            ("Room-type claims.", "Cannot be decided at 44 inputs: 12 run clusters, five typable room types. At L1 "
                                  "a null reads Inconclusive.")]
    y = 262
    for head, body in rows:
        hline(s, 120, y, 1800, y, RULE)
        text(s, 120, y + 22, 520, 60, [run(head, 28, INK, SANS, True)], line=1.3)
        text(s, 680, y + 24, 1120, 100, [run(body, 24, BODY)], line=1.45)
        y += 140


# ---------------------------------------------------------------- 16. The one-line answer

ANSWERS = [
    ("works", "Works",
     "A Claude model is Supported at L3 on the unobserved stratum.",
     "On the robot's own saved inputs, Claude names which rooms and objects lie in which unexplored region better "
     "than the named comparators, in two houses, on proxy truth. We have not shown that this reaches the map."),
    ("mixed", "Mixed",
     "Supported at L1 or L2 and ahead of the wrong-house control, but not at L3.",
     "Right at house level, wrong in place. Claude knows a house like this has another bathroom, beyond the prior, "
     "but cannot say which unexplored region holds it. ASP's score runs on positions."),
    ("fails", "Fails",
     "Both Claude models are Rejected at L2 and L3.",
     "Claude's lead over a prior that sees the same map is smaller than the registered margin. The “right "
     "semantics” in the demo are mostly base rate. This is a claim about ASP's guesses on these inputs, "
     "not about LLM-guided exploration in general."),
    ("inconclusive", "Inconclusive",
     "Anything else, including every null at 44 inputs.",
     "We found no detectable difference between Claude's guesses and the named comparators. At 44 inputs in two "
     "houses the test detects only differences of the size stated in the pre-registration, so the claim is neither "
     "supported nor rejected."),
]


def answer(prs, slots):
    s = frame(prs, 16, "The answer to the author", "The one-line answer to the author")
    pick = slots.get("outcome")
    for i, (key, name, when, line) in enumerate(ANSWERS):
        x = 120 + (i % 2) * 860
        y = 262 + (i // 2) * 320
        chosen = pick == key
        faded = pick is not None and not chosen
        r = rect(s, x, y, 820, 300, WASH if not chosen else WHITE, INK if chosen else RULE, 4 if chosen else 1)
        c_head, c_body, c_when = (FAINT, FAINT, FAINT) if faded else (INK, BODY, MID)
        text(s, x + 28, y + 22, 760, 40, [run(name.upper(), 22, c_head, SANS, True, spacing=0.18)])
        text(s, x + 28, y + 62, 764, 62, [[run("When: ", 19, FAINT, SANS, True), run(when, 19, c_when)]], line=1.4)
        text(s, x + 28, y + 130, 764, 160, [run(line, 22, c_body)], line=1.45)
    note(s, 120, 912, 1680, 3,
         "The registered rules pick one, after the data exist. If the Claude replays do not run, DeepSeek's results "
         "stay exploratory and no line applies. The oracle factorial reads apart, and leans toward “not shown "
         "sufficient”.")


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
    N = numbers()
    slots = load_slots()
    C, budgets = paper_cells(slots)
    checks = json.load(open(CHECKS))
    prs = Presentation()
    prs.slide_width, prs.slide_height = px(1920), px(1080)
    cover(prs)
    asp_picture(prs, N)
    live_test(prs, N)
    why(prs, N)
    live_limits(prs, N)
    paper_rules(prs, budgets, checks, slots)
    paper_table(prs, C, budgets, slots)
    paper_limits(prs, C, checks)
    defense(prs)
    base_rates(prs, slots)
    room_test(prs, slots)
    three_models(prs, slots)
    factorial(prs, slots)
    validity(prs, N, slots)
    limits(prs, N)
    answer(prs, slots)
    assert len(prs.slides) == TOTAL, len(prs.slides)
    notes = speaker_notes()
    assert len(notes) == TOTAL, len(notes)
    for slide, n in zip(prs.slides, notes):
        slide.notes_slide.notes_text_frame.text = n
    prs.core_properties.title = "Right in meaning, wrong in place?"
    prs.core_properties.author = "Sher Partap Singh, Preesha Katial, Ananya Singla"
    prs.save(OUT)
    print(OUT, len(prs.slides), "slides")


if __name__ == "__main__":
    main()
