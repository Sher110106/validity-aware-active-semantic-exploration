"""Build ASP_Endsem.pptx: the end-sem talk "Right in meaning, wrong in place?", in the style of
../checkin_2026-11/ASP_Checkin2.pptx, with ENDSEM_Script.md as speaker notes.

Type size: the canvas is 1920 px wide and 1 px is 0.5 pt, so body text is 32 px (16 pt) or more and
notes, labels and chart text are 24 px (12 pt) or more. The builder warns if its line estimate says a
text box runs past the slide.

Every chart and table value comes from a result file (numbers.csv, paper_compare.json, budgets_*.json,
c2_*.json, c_checks.json, frontier_holm.json, equal_path.json, budget_sensitivity.json,
figures/stage_numbers.json) or, for part 3, from slots.json (which fill_slots_part3.py writes from the result files;
its "pinned" part holds facts from files that are not result tables). SOURCES.md says which file and key stand behind
each number. A claim in a sentence (a lead, "smaller than the paper's", a sign, "no detectable gain") is guarded: if
the cells no longer bear it, the build stops with BUILD STOPPED and a reason. The script and README hold typed figures
too; check_text stops the build if one is missing, and script_times stops it if the times in the script do not add
to 900 s. Anything not registered is marked exploratory on its slide.

Usage (from the project root):
    .venv_offline/bin/python docs/endsem_2026-11/figures/make_stage_picture.py   # slide 14, once
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
EQUAL_PATH = os.path.join(R1113, "equal_path", "equal_path.json")
BUDGET_SENS = os.path.join(R1113, "budget_sensitivity", "budget_sensitivity.json")
SEM_RESULTS_MD = os.path.join(LP, "results_semantic_1113", "RESULTS.md")
TOTAL = 26              # main slides; the time in the script headings adds to 900 s over these
BACKUPS = 6
ACCENT = "c2410c"
MINUS = "−"
DASH = "–"
B, NT = 32, 24          # body and note size in canvas px (16 pt and 12 pt)
DISTANCE_WEIGHT = "0.2"  # per metre; tools/decision_replay.py:173 (MOVE_COST_LAMBDA)
PATH_CAP_M = 250         # a frontier run stops at this path length; PREREGISTRATION_PAPER.md section 2a
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


def fail(msg):
    """A content guard: the text on a slide would claim more than the data carry. Stop the build. (WARN is for fit.)"""
    raise SystemExit("BUILD STOPPED: " + msg)


def paper_cells(slots, variant="B", reference="apr", path=None):
    """The cells for one reference and budget variant: B (the slides) or 0.8B / 1.2B (the registered sensitivity)."""
    d = json.load(open(path or os.path.join(PROJECT, slots["paper_compare_json"])))
    cells = {}
    for c in d["cells"]:
        if c["reference"] == reference and c["variant"] == variant:
            cells[(c["scene"], c["arm"], c["fraction"])] = c
    return cells, d["meta"]["budgets"]


def newest(pattern):
    """The newest file in results_paper_compare_1113 that matches; the time stamps in the names sort by date."""
    import glob
    files = sorted(glob.glob(os.path.join(R1113, pattern)))
    return files[-1] if files else None


def c2_data(scene):
    """C2 for one scene: (F1 of the repeat tour against the first, whether that tour is frozen). The newest
    c2_*.json in results_paper_compare_1113 holds both; while a rescore is rewriting that folder, the F1 quoted in
    its NOTES.md item 3 stands in and frozen is None (not known)."""
    f = newest("c2_*.json")
    if f:
        s = json.load(open(f))["scenes"][scene]
        if s["f1"] is not None:
            return float(s["f1"]), s.get("frozen")
    m = re.search(rf"{scene}: F1 (0\.\d+)", open(os.path.join(R1113, "NOTES.md")).read())
    return float(m.group(1)), None


def budget_runs():
    """Per scene, from the newest budgets_*.json: B, how many frontier runs set it, how many were run, the range
    of the end times of those that set it, and how many stopped at the path cap and are left out."""
    d = json.load(open(newest("budgets_*.json")))
    out = {}
    for sc, b in d.items():
        ends = [b["end_times_s"][r] for r in b["primary_runs"]]
        out[sc] = {"b": b["primary_s"], "n": b["n_primary"], "of": len(b["end_times_s"]), "lo": min(ends),
                   "hi": max(ends), "capped": len(b["capped_runs"])}
    return out


def read_equal_path():
    """equal_path.json (exploratory, 11-19): F1 x 100 at the last stage within L metres of path, per scene, reference
    (apr = scripted tour, hm3d = human labels, frontier_made), arm and length."""
    d = json.load(open(EQUAL_PATH))
    if d.get("registered") is not False:
        fail("equal_path.json no longer says registered=false: slides 9 and 10 mark it exploratory")
    return d


def read_sensitivity():
    """budget_sensitivity.json (exploratory, 11-19): F1 x 100 at 10, 50 and 100% of other budgets B."""
    d = json.load(open(BUDGET_SENS))
    if d.get("registered") is not False:
        fail("budget_sensitivity.json no longer says registered=false: slide 10 marks it exploratory")
    return d


def ecell(d, sc, ref, arm, L):
    """One equal-path cell: {mean, min, max, n, n_runs}."""
    return d["scenes"][sc]["tables"][ref][arm][str(L)]


def cell_str(c):
    """(text, n text) for an equal-path or sensitivity cell, or (None, 'none') when no run has a value."""
    if not c["n"]:
        return None, f"none, 0 of {c['n_runs']}"
    n = f"n={c['n']}" if c["n"] == c["n_runs"] else f"n={c['n']} of {c['n_runs']}"
    return f"{num(c['mean'])} [{num(c['min'])}{DASH}{num(c['max'])}]", n


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


NQ = 28                  # key qualifiers: 14 pt


def Nq(s, x, y, w, txt, limit=1000):
    """A note that carries a qualifier: 28 px (14 pt), grey."""
    return P(s, x, y, w, txt, NQ, MID, 1.35, limit=limit)


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
    # one line only: the title shrinks with its length (56, 46 or 38 px) so it stays above the rule at y=222
    tsize = 56 if len(title) <= 50 else 46 if len(title) <= 62 else 38 if len(title) <= 84 else 34 if len(title) <= 92 \
        else 31
    text(s, 120, 123 + (56 - tsize) / 2, 1680, 74, [run(title, tsize, INK, LIGHT, spacing=-0.02)], line=1.15)
    hline(s, 120, 222, 1800, 222, RULE)
    text(s, 120, 1018, 1200, 30, [run("Right in meaning, wrong in place? · End-sem", NT, FAINT)])
    text(s, 1400, 1018, 400, 30, [run("Backup" if backup else f"{n:02d} / {TOTAL}", NT, FAINT)], PP_ALIGN.RIGHT)
    if pending:
        pill(s, 1500 if len(pending) < 16 else 1380, 76, 300 if len(pending) < 16 else 420, 38, pending)
    if len(title) > 100:
        WARN.append(f"title may wrap: {title!r}")
    return s


def stat(s, x, y, w, value, label, size=56, label_lines=2):
    hline(s, x, y, x + w, y, RULE)
    text(s, x, y + 12, w, size * 1.2, [run(value, size, INK, LIGHT)], line=1.1)
    ly = y + 12 + size * 1.2 + 6
    return P(s, x, ly, w, label, NT if label_lines == 0 else B, MID if label_lines == 0 else BODY, 1.35)


# ---------------------------------------------------------------- 1. Cover

def cover(prs, f853):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    text(s, 160, 120, 1600, 34, [kick("End-sem · Computer vision and perception", NT, 0.14)])
    text(s, 160, 180, 1600, 250, [run("Right in meaning,", 112, INK, LIGHT, spacing=-0.03),
                                  run("wrong in place?", 112, INK, LIGHT, spacing=-0.03)], line=1.05)
    P(s, 160, 440, 1560, "ASP asks a language model to guess the rooms and objects a robot has not seen, then "
                         "drives to where the guesses disagree. As the author put it to us, the guesses are often "
                         "wrong in place but name the right things, and that is enough. We test that in three parts.",
      B, BODY, 1.45)
    cols = [("Part 1 · Live test", "Do the guesses improve a live map? Final."),
            ("Part 2 · Paper's scale", f"On 853, ASP reads above frontier by the clock; by the metre, it depends."),
            ("Part 3 · The author's claim", "Is the meaning right? Is it enough? Is it the model?")]
    for i, (name, body) in enumerate(cols):
        x = 160 + i * 552
        hline(s, x, 606, x + 496, 606, INK, 2)
        text(s, x, 618, 496, 34, [run(f"{i + 1:02d}", NT, FAINT, MONO)])
        P(s, x, 656, 496, [(name, "b")], B, line=1.3)
        P(s, x, 706, 496, body, B, BODY, 1.35, limit=860)
    N(s, 160, 872, 1600, "Final: Part 1, and the registered scores and tests, the Gemini replay included. Registered, "
                         "running and not shown: two control arms on 853.", limit=930)
    hline(s, 160, 930, 1760, 930, RULE)
    text(s, 160, 950, 900, 34, [run("Sher Partap Singh · Preesha Katial · Ananya Singla", NT, MID)])
    text(s, 860, 950, 900, 34, [run("Base paper: Tang & Chaudhari, Active Semantic Perception, arXiv:2510.05430",
                                    NT, MID)], PP_ALIGN.RIGHT)


# ---------------------------------------------------------------- 2. What became of the proposal

def proposal(prs, Nn, slots):
    p = slots["pinned"]["proposal"]
    lo, hi = -Nn["E2:hm3d:60m:permutation_hi"], -Nn["E2:hm3d:60m:permutation_lo"]    # filter minus LLM, as on slide 4
    if not lo < 0 < hi:
        fail("slide 2 says the live validator test showed no detectable difference, but its interval excludes 0")
    if p["kept"] * 100 >= p["of"]:
        fail("slide 2 says the filter kept a tiny share of the guesses, but the pinned share is 1% or more")
    s = frame(prs, 2, "The proposal", "The proposal's question was measured in part")
    cols = [("Asked",
             f"Can validation and calibration of ensemble support cut false-positive detours without cutting "
             f"discovery of unseen rooms? The plan: {p['policies']} policies, {p['scenes']} homes × {p['seeds']} seeds, "
             f"{p['budget_m']} m."),
            ("Measured",
             f"Our validator, live, in 2 homes: {sg(-Nn['E2:hm3d:60m:statistic'])} F1 ({sg(lo)} to {sg(hi)}) against "
             f"the LLM alone. No detectable difference. The test saw only gains of "
             f"{num(Nn['E2:hm3d:60m:mde'], 3)} or more."),
            ("Not measured",
             "Detours: replays never drove the chosen views, so detours are not identifiable. Collisions: not "
             "instrumented. Calibration: retired, its Brier score equals the base rate."),
            ("Withdrawn",
             f"September's claim that full agreement improves the map. The filter kept {p['kept']} of "
             f"{p['of']:,} guesses: the gain came from deleting the guesses.")]
    for i, (head, body) in enumerate(cols):
        x = 120 + i * 430
        hline(s, x, 262, x + 390, 262, INK, 2)
        P(s, x, 278, 390, [(head, "b")], B, line=1.3)
        P(s, x, 330, 390, body, B, BODY, 1.35, limit=860)
    box_bottom(s, "Since then:", "the question became whether the guesses carry any value: live (Part 1), at the "
                                 "paper's scale (Part 2), and in meaning (Part 3).")


# ---------------------------------------------------------------- 3. ASP in one picture

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
    s = frame(prs, 3, "ASP in one picture", "ASP scores views by disagreement, not by truth")
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
    cols = [("Gain", "The 8 graphs' disagreement about the view. If all 8 agree, the gain is zero."),
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
    s = frame(prs, 4, "Part 1 · Live test · 2 homes, seeds 42-44, human labels",
              "Live test: no detectable difference")
    L = 120
    lab(s, L, 244, 1680, "Difference in F1, area under the curve to 60 m; 95% interval")
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

    top, step = 322, 56
    for v in (-0.05, 0.0, 0.05):
        hline(s, dx(v), top - 24, dx(v), top + step * len(rows) - 34, LINE if v else MID, 1 if v else 2,
              dash=bool(v))
        svg_text(s, dx(v), top + step * len(rows) + 4, sg(v, 2) if v else "0", NT, FAINT, anchor="middle", w=100)
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
    y = N(s, L, top + step * len(rows) + 36, 1680,
          "Registered tests, pilot status. The filter row was registered as LLM minus filter; its sign is flipped "
          "here. Exact objects: one house (871), 3 runs against 3, kept under deviation 26; the smallest p such a "
          "test can give is 0.10. Frontier rows: frontier stopped more often on 871, and its paths almost never "
          "crossed wall cells, so the comparison may tilt in an unknown direction.", limit=800)
    box_bottom(s, "Registered reading.", "No detectable difference in any contrast, for ASP with a small model: "
                                         "DeepSeek V4.1 Flash at low reasoning effort. The paper (§IV, footnote) "
                                         f"says “{PINNED['paper']['small_model']}”.")


# ---------------------------------------------------------------- 4. Part 1, why

def why(prs, Nn):
    s = frame(prs, 5, "Part 1 · Why · exploratory, offline replay of saved stages",
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
    s = frame(prs, 6, "Part 1 · Where the guesses land", "Near a real object, but rarely close")
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
    s = frame(prs, 7, "Part 1 · Limits of the live test", "Live test limits: what it could not rule out")
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

def timeline(s, x0, x1, y, budget):
    hline(s, x0, y, x1, y, MID, 2)
    for frac in (0.1, 0.5, 1.0):
        xx = x0 + (x1 - x0) * frac
        hline(s, xx, y - 12, xx, y + 12, INK, 2)
        svg_text(s, xx, y - 22, f"{int(round(frac * 100))}%", NT, FAINT, anchor="middle", w=100)
        svg_text(s, xx, y + 50, f"{frac * budget:.0f} s", 28, INK, MONO, anchor="middle", w=140)


def capped_text(n):
    return "1 run" if n == 1 else f"{n} runs"


def budget_note(d):
    txt = (f"Median end of the {d['n']} frontier runs that logged “Exploration complete” "
           f"({d['lo']:.0f} to {d['hi']:.0f} s).")
    if d["capped"]:
        txt += (f" {capped_text(d['capped'])} stopped at the {PATH_CAP_M} m path cap and "
                f"{'is' if d['capped'] == 1 else 'are'} left out.")
    return txt


def paper_rules(prs, budgets, checks, bf):
    s = frame(prs, 8, "Part 2 · Same rules as the paper", "Same rules as the paper")
    stops = [checks[sc]["use_rule"]["reached"] for sc in ("00853", "00871")]
    a, b = bf["00853"], bf["00871"]
    ratio = budgets["00871"] / budgets["00853"]
    if not 1.9 < ratio < 2.1:
        fail(f"slide 8 says 871's budget is about twice 853's, but the ratio is {ratio:.2f}")
    for sc in bf:
        if abs(bf[sc]["b"] - budgets[sc]) > 0.01 or bf[sc]["n"] + bf[sc]["capped"] != bf[sc]["of"]:
            fail(f"the budgets file and paper_compare.json disagree for {sc}")
    frontier = f"Run to its natural end: {a['n']} of {a['of']} runs on 853, {b['n']} of {b['of']} on 871."
    L, w = 120, 780
    blocks = [("Scoring.", "The author's own F1 and GED code, on the paper's time axis."),
              ("Reference.", f"A scripted stand-in for the author's hand-driven tour: navmesh paths, the same mapper "
                             f"({stops[0]} and {stops[1]} stops)."),
              ("Frontier.", frontier),
              ("LLM.", "Ours is DeepSeek. The paper's is Gemini 2.5 Pro.")]
    y = 262
    for head, body in blocks:
        y = P(s, L, y, w, [(head + " ", "b"), (body, "n")], B, BODY, 1.4, limit=960) + 26
    R = 980
    lab(s, R, 250, 820, "What “budget” means")
    P(s, R, 300, 820, "The paper gives no value for its budget. We set one for each home. 871's is about twice "
                      "853's.", B, BODY, 1.4)
    text(s, R, 478, 150, 40, [run("Home 853", 28, INK, SANS, True)])
    timeline(s, R + 190, R + 790, 510, budgets["00853"])
    N(s, R, 592, 820, budget_note(a))
    text(s, R, 718, 150, 40, [run("Home 871", 28, INK, SANS, True)])
    timeline(s, R + 190, R + 790, 750, budgets["00871"])
    N(s, R, 850, 820, budget_note(b))


# ---------------------------------------------------------------- 8 and 9. Part 2, tables

def stat_cell(C, scene, arm, frac):
    c = C[(scene, arm, frac)]
    sv = c["stage_value_x100"]
    if not sv["n"] or sv["n"] * 2 < c["n_runs"]:
        return None, "no run reaches it" if not sv["n"] else f"{sv['n']} of {c['n_runs']} runs"
    if any(sv[k] is None for k in ("mean", "min", "max")):
        fail(f"the cell {scene} {arm} {frac}% has n={sv['n']} but a null mean, min or max")
    n = f"n={sv['n']}" if sv["n"] == c["n_runs"] else f"n={sv['n']} of {c['n_runs']}"
    return f"{num(sv['mean'])} [{num(sv['min'])}{DASH}{num(sv['max'])}]", n


def table(s, x, y, lw, cw, rows, rowh):
    """rows: (label, cells, kind) with cells [(main, sub, main_color, sub_color)], kind paper|ours."""
    for j, head in enumerate(("10%", "50%", "100%")):
        svg_text(s, x + lw + j * cw + cw / 2, y + 34, head, 28, MID, SANS, anchor="middle", w=cw)
    y += 46
    hline(s, x, y, x + lw + 3 * cw, y, LINE)
    for row in rows:
        lab_, cells, kind = row[:3]
        dim = len(row) > 3 and row[3]          # a row the speaker does not read aloud: grey
        rh = rowh[kind]
        text(s, x + 8, y + (rh - 40) / 2, lw - 10, 40,
             [run(lab_, 28, FAINT if dim else INK if kind == "paper" else BODY)], line=1.2)
        for j, (main, sub, mc, sc) in enumerate(cells):
            if dim:
                mc = FAINT if mc == INK else mc
            cx = x + lw + j * cw
            if kind == "paper":
                text(s, cx, y + (rh - 40) / 2, cw, 40, [run(main, 32, mc, MONO)], PP_ALIGN.CENTER, 1.2)
            else:       # the value, then its n just after it, on one line
                text(s, cx + 24, y + (rh - 34) / 2, cw - 36, 38, [run(main, 26, mc, MONO)], PP_ALIGN.LEFT, 1.2)
                if sub:
                    text(s, cx + 24 + len(main) * 15.6 + 14, y + (rh - 30) / 2 + 2, 250, 30, [run(sub, NT, sc)],
                         PP_ALIGN.LEFT, 1.2)
        y += rh
        hline(s, x, y, x + lw + 3 * cw, y, RULE)
    return y


def table_rows(C, scene, arms, names=None, dimmed=()):
    def paper(arm):
        for f in ("10", "50", "100"):
            if C[(scene, arm, f)]["paper_f1_x100"] is None:
                fail(f"the paper's value for {scene} {arm} {f}% is null")
        return [(num(C[(scene, arm, f)]['paper_f1_x100']), None, INK, MID) for f in ("10", "50", "100")]
    rows = [("Paper · ASP", paper("official"), "paper"), ("Paper · frontier", paper("frontier_end"), "paper")]
    all_names = {"official": "Ours · ASP", "filter_only": "Ours · ASP + filter", "placebo": "Ours · random guesses",
                 "frontier_end": "Ours · frontier", **(names or {})}
    for arm in arms:
        cells = []
        for f in ("10", "50", "100"):
            main, sub = stat_cell(C, scene, arm, f)
            cells.append((main or "none", sub, INK if main else FAINT, MID))
        rows.append((all_names[arm], cells, "ours", arm in dimmed))
    return rows


def facts_equal853(ep):
    """Slide 9's equal-path rows: ASP (November) minus our frontier at 50 m and 100 m, under the scripted reference
    (apr) and the human labels (hm3d), as printed. The title says the sign depends on the reference: stop if not."""
    sc, out = "00853", {}
    for ref in ("apr", "hm3d"):
        for L in (50, 100):
            a, f = ecell(ep, sc, ref, "official_nov", L), ecell(ep, sc, ref, "frontier_end", L)
            if not a["n"] or not f["n"]:
                fail(f"slide 9 needs equal-path values for ASP and frontier at {L} m under {ref}")
            out[(ref, L)] = lead(a["mean"], f["mean"])
    if not (out[("apr", 50)] > 0 and out[("apr", 100)] > 0 and out[("hm3d", 50)] < 0 and out[("hm3d", 100)] < 0):
        fail("slide 9's title says that by the metre the sign depends on the reference (ASP ahead under the scripted "
             "reference, frontier ahead under the human labels, at 50 m and 100 m), but the cells say " + str(out))
    for ref in ("apr", "hm3d"):
        if ecell(ep, sc, ref, "official_nov", 100)["n"] != 3 or ecell(ep, sc, ref, "frontier_end", 100)["n"] != 2:
            fail("slide 9 and the script say the 100 m row is 3 ASP runs against 2 of 5 frontier runs; the cells differ")
    return out


def table853(prs, C, budgets, slots, f853, ep):
    if slots["asp853_full_budget"] != FROM_PC:
        fail("slots.json asp853_full_budget must be the flag " + repr(FROM_PC) + ": slide 9 reads its November "
             "row from paper_compare.json, and no number is typed in slots.json")
    feq = f853["equal"]
    s = frame(prs, 9, f"Part 2 · Home 853 · object F1 × 100, mean [min{DASH}max] · registered budget "
                       f"{budgets['00853']:.0f} s",
              "By the clock ASP reads above frontier; by the metre the sign depends on the reference")
    names = {"official": f"Ours · ASP, October ({f853['oct_m']} m)",
             "official_nov": f"Ours · ASP, November ({f853['nov_m']} m)"}
    y = table(s, 120, 232, 440, 400,
              table_rows(C, "00853", ("official", "official_nov", "filter_only", "placebo", "frontier_end"), names,
                         dimmed=("filter_only", "placebo")),
              {"paper": 40, "ours": 52})
    L, PL = f853["leads"], f853["paper_leads"]
    y = Nq(s, 120, y + 4, 1680,
           f"Registered, equal time. Paper: Fig. 4, one run each. ASP's lead: {L['10']}, "
           f"{L['50']}, {L['100']} points; the paper's {PL['10']}, {PL['50']}, {PL['100']}. October's "
           f"{WORDS[f853['oct_runs']]} runs trailed by {abs(f853['oct50'])} at 50%; the batches differ by "
           f"{f853['batch50']}. By the rule seed {f853['seed']} loses its 100% value (dev. {DEV_SEED}): "
           f"{f853['stopped100']}, n={f853['stopped_n']} of {f853['stopped_runs']}.", limit=760)
    # exploratory block: equal path
    heads = ["ASP, Nov · 50 m", "Frontier · 50 m", "ASP, Nov · 100 m", "Frontier · 100 m"]
    lw, cw = 360, 330
    y += 10
    text(s, 120, y, lw, 34, [run("Exploratory · equal path", NT, ACCENT, SANS, True)])
    for j, hd in enumerate(heads):
        text(s, 120 + lw + j * cw, y, cw, 34, [run(hd, NT, MID, SANS, True)], PP_ALIGN.CENTER)
    y += 36
    hline(s, 120, y, 120 + lw + 4 * cw, y, LINE)
    for ref, name in (("apr", "Scripted reference"), ("hm3d", "Human labels")):
        text(s, 128, y + 12, lw - 10, 36, [run(name, 28, INK)], line=1.2)
        for j, (arm, Lm) in enumerate((("official_nov", 50), ("frontier_end", 50), ("official_nov", 100),
                                       ("frontier_end", 100))):
            main, sub = cell_str(ecell(ep, "00853", ref, arm, Lm))
            cx = 120 + lw + j * cw
            text(s, cx, y + 2, cw, 40, [run(main, 30, INK, MONO)], PP_ALIGN.CENTER, 1.2)
            text(s, cx, y + 36, cw, 30, [run(sub, NT, MID)], PP_ALIGN.CENTER, 1.2)
        y += 68
        hline(s, 120, y, 120 + lw + 4 * cw, y, RULE)
    Nq(s, 120, y + 6, 1680,
       "Not registered. Two control arms that share ASP's clock are registered and running (Amendment 5).",
       limit=1010)


WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
ASP_ARMS = ("official", "filter_only")      # the arms that run ASP; both stop at 60 m of path
FOUR_ARMS = ("official", "filter_only", "placebo", "frontier_end")


def printed(v, what):
    """A value as the slide prints it (one decimal, half up). A null stops the build."""
    if v is None:
        fail(f"{what} is null, and slide 10 needs it")
    return rnd(v, 1)


def gaps(C, scene, C08=None):
    """Ours minus the paper, in points of F1 x 100, for each ASP and frontier cell the table shows. Both sides are
    taken as printed, so the slide's own numbers subtract. Also: the same gap at 0.8 B (the registered sensitivity
    check, from C08), and whether the paper's value lies inside our printed min-max."""
    out = []
    for arm in ("official", "official_nov", "frontier_end"):      # official_nov: 853 only
        for f in ("10", "50", "100"):
            if (scene, arm, f) not in C or stat_cell(C, scene, arm, f)[0] is None:
                continue
            tag = f"{scene} {arm} {f}%"
            c = C[(scene, arm, f)]
            sv = c["stage_value_x100"]
            paper = printed(c["paper_f1_x100"], f"the paper's value for {tag}")
            row = {"arm": arm, "f": f, "gap": printed(sv["mean"], f"the mean of {tag}") - paper,
                   "inside": printed(sv["min"], f"the minimum of {tag}") <= paper
                   <= printed(sv["max"], f"the maximum of {tag}"), "gap08": None}
            if C08 is not None:
                row["gap08"] = printed(C08[(scene, arm, f)]["stage_value_x100"]["mean"],
                                       f"the 0.8 B mean of {tag}") - paper
            out.append(row)
    return out


def facts871(C, C08):
    """Every number in slide 10's title and body. Stops the build if the wording would claim more than the cells."""
    g = gaps(C, "00871", C08)
    if not g:
        fail("slide 10: no 871 cell has both a value of ours and the paper's")
    diffs = [x["gap"] for x in g]
    if min(diffs) <= 0:
        fail("slide 10 says ours are higher than the paper's, but a gap is not positive: "
             + ", ".join(f"{x['arm']} {x['f']}% {x['gap']:+}" for x in g))
    for arm in ASP_ARMS:
        for f in ("50", "100"):
            n = C[("00871", arm, f)]["stage_value_x100"]["n"]
            if n:
                fail(f"slide 10 says no ASP run of ours reaches 50% of the budget, but {arm} has n={n} at {f}%")
    neg = sum(1 for x in g if x["gap08"] < 0)
    if not neg:
        fail("slide 10 and the script say some gaps turn negative at 0.8 B, but none does")
    mins, maxs, means = [], [], []
    for arm in FOUR_ARMS:
        sv = C[("00871", arm, "10")]["stage_value_x100"]
        means.append(printed(sv["mean"], f"the mean of 871 {arm} 10%"))
        mins.append(printed(sv["min"], f"the minimum of 871 {arm} 10%"))
        maxs.append(printed(sv["max"], f"the maximum of 871 {arm} 10%"))
    if max(mins) > min(maxs):
        fail("slide 10 says the four arms' ranges overlap at 10%, but they do not")
    return {"lo": min(diffs), "hi": max(diffs), "max_gap": max(abs(d) for d in diffs), "m": len(g),
            "inside": sum(1 for x in g if x["inside"]), "neg": neg, "arm_lo": min(means), "arm_hi": max(means)}


FROM_PC = "from paper_compare.json (arm official_nov)"   # slots.json asp853_full_budget: the row has no typed numbers
DEV_SEED = 64                                           # DEVIATIONS_NOVEMBER.md item 64 (the seed 43 memory dip)
ASP_OCT_M = 60                                          # October ASP runs stop at this path length (WRITEUP section 2)


def lead(a, b):
    """A lead in points, from the two means as printed (one decimal, half up), as for every other gap in the deck:
    the numbers on a slide, and in paper_compare.md, subtract to it. (The unrounded difference can differ by 0.1.)"""
    return rnd(a, 1) - rnd(b, 1)


def sg1(d):
    """A signed difference for slide text, with the deck's minus sign."""
    return f"{d}".replace("-", MINUS)


def facts853(C, slots):
    """Every number in slide 9's title, body and note, and the figures the script and README repeat. Stops the build
    if the wording (a lead; smaller than the paper's; October's two signs; the batch gap) would claim more than
    the cells."""
    sc = "00853"
    f3 = ("10", "50", "100")

    def mean(CC, arm, f, what):
        v = CC[(sc, arm, f)]["stage_value_x100"]["mean"]
        if v is None:
            fail(f"slide 9 needs the mean of {what} {arm} {f}%, which is null")
        return v
    for f in f3:
        for arm in ("official_nov", "frontier_end"):
            if stat_cell(C, sc, arm, f)[0] is None:
                fail(f"slide 9 needs a shown value for {arm} {f}% on 853, and the table does not show one")
    nov = {f: mean(C, "official_nov", f, "ours") for f in f3}
    fr = {f: mean(C, "frontier_end", f, "ours") for f in f3}
    leads = {f: lead(nov[f], fr[f]) for f in f3}
    if min(leads.values()) <= 0:
        fail("slide 9 says November's ASP leads our frontier, but a lead is not positive: " + str(leads))
    pv = {}
    for f in f3:
        pa, pf = C[(sc, "official_nov", f)]["paper_f1_x100"], C[(sc, "frontier_end", f)]["paper_f1_x100"]
        if pa is None or pf is None:
            fail(f"slide 9 needs the paper's ASP and frontier values at {f}%, and one is null")
        pv[f] = rnd(pa, 1) - rnd(pf, 1)
    if not all(leads[f] < pv[f] for f in f3):
        fail("slide 9 says November's leads are smaller than the paper's, but not in every cell: ours "
             + str(leads) + ", the paper's " + str(pv))
    short = {f: pv[f] - leads[f] for f in f3}
    if not (short["10"] > short["50"] and short["10"] > short["100"]):
        fail("the script and README say the shortfall is largest at 10%, but it is not: " + str(short))
    for f in ("10", "50"):
        if stat_cell(C, sc, "official", f)[0] is None:
            fail(f"slide 9 needs a shown October ASP value at {f}%")
    oct_ = {f: mean(C, "official", f, "ours") for f in ("10", "50")}
    oct10, oct50 = lead(oct_["10"], fr["10"]), lead(oct_["50"], fr["50"])
    if not (oct10 > 0 > oct50):
        fail(f"slide 9 says October led at 10% and trailed at 50%, but the leads are {oct10} and {oct50}")
    if C[(sc, "official", "100")]["stage_value_x100"]["n"]:
        fail("slides 9 and 12 say October's ASP runs have no value at 100%, but one has")
    batch50 = lead(nov["50"], oct_["50"])
    if batch50 < leads["50"]:
        fail(f"slides 9 and 12 say the two ASP batches differ by as much as the lead at 50%: {batch50} against "
             f"{leads['50']}")
    ns = {f: (C[(sc, "official_nov", f)]["stage_value_x100"]["n"], C[(sc, "official_nov", f)]["n_runs"]) for f in f3}
    others = {}
    for ref in ("hm3d", "frontier_made"):
        Cr = paper_cells(slots, "B", ref)[0]
        others[ref] = lead(mean(Cr, "official_nov", "100", ref), mean(Cr, "frontier_end", "100", ref))
        if others[ref] >= leads["100"]:
            fail(f"slides 9 and 12 say the 100% lead is smaller under {ref} than under apr, but it is "
                 f"{others[ref]} against {leads['100']}")
    summ = json.load(open(os.path.join(R1113, "rescore_summary.json")))["nov"]
    if "alternatives" not in summ:
        fail("rescore_summary.json nov has no 'alternatives' key (the file's shape changed again): slide 9 reads "
             "seed 43's readings from nov.alternatives.rows")
    rows = {r["kind"]: r for r in summ["alternatives"]["rows"]}
    if set(rows) != {"stopped", "without"}:
        fail("rescore_summary.json nov.alternatives.rows should hold a 'stopped' and a 'without' row: "
             + str(sorted(rows)))
    st, ww = rows["stopped"], rows["without"]
    seed = re.search(r"_s(\d+)_", st["run"]).group(1)
    if re.search(r"_s(\d+)_", ww["run"]).group(1) != seed:
        fail("the 'stopped' and 'without' rows are about different runs")
    if st["end_s"] >= summ["B_s"]:
        fail(f"slide 9 says seed {seed} loses its 100% value, but its stop at {st['end_s']:.1f} s is not before B")

    def alt_cells(row):
        CC = paper_cells(slots, "B", "apr", os.path.join(R1113, row["folder"], "paper_compare.json"))[0]
        out = {}
        for f in f3:
            sv = CC[(sc, "official_nov", f)]["stage_value_x100"]
            if sv["mean"] is None and f != "100":
                fail(f"the '{row['kind']}' row has no value at {f}%")
            out[f] = (sv, CC[(sc, "official_nov", f)]["n_runs"])
        return out
    stopped, without = alt_cells(st), alt_cells(ww)
    for f in ("10", "50"):      # the rule's reading keeps seed 43 at 10% and 50%: those cells must equal the as-run ones
        a, b = stopped[f][0], C[(sc, "official_nov", f)]["stage_value_x100"]
        if any(a[k] != b[k] for k in ("mean", "min", "max", "n")):
            fail(f"the 'stopped' row differs from the as-run row at {f}%, but slide 9 says seed {seed} keeps its "
                 "10% and 50% values")
    sv100 = stopped["100"][0]
    if sv100["mean"] is None or sv100["n"] >= ns["100"][0]:
        fail(f"slide 9 says seed {seed} loses its 100% value, but the 'stopped' row's 100% n is {sv100['n']} "
             f"against {ns['100'][0]} as run")
    dev = open(os.path.join(LP, "DEVIATIONS_NOVEMBER.md"), encoding="utf-8").read()
    item = re.search(rf"^{DEV_SEED}\. .*$", dev, flags=re.M)
    if not item or set(re.findall(r"seed (\d+)", item.group(0))) != {seed}:
        fail(f"slide 9 cites deviation {DEV_SEED} for seed {seed}, but that item does not name that seed alone")
    alt = {f: (num(without[f][0]["mean"]), without[f][0]["n"]) for f in f3 if without[f][0]["mean"] is not None}
    if len(alt) != 3:
        fail(f"the row without seed {seed} has no value at 100%")
    if min(pv.values()) <= 0:
        fail("slide 9 says 'as in the paper' (ASP above frontier), but the paper's ASP is not above its frontier "
             "in every cell: " + str(pv))
    ends = {int(re.search(r"_(\d+)m$", r["run"]).group(1)) for r in summ["runs"]}
    if len(ends) != 1:
        fail("the November runs have different target path lengths: " + str(ends))
    g = gaps(C, sc)
    if not g or max(x["gap"] for x in g) >= 0:
        fail("the script and README say ours are lower than the paper's on 853, but a gap is not negative")
    d = [abs(x["gap"]) for x in g]
    for f in ("50",):           # slide 12: October's random-guess runs read between the two ASP batches at 50%
        if (sc, "placebo", f) not in C or stat_cell(C, sc, "placebo", f)[0] is None:
            fail("slide 12 needs a shown value for October's random-guess runs at 50% on 853")
    spm = {r["arm"]: r for r in json.load(open(os.path.join(PROJECT, slots["paper_compare_json"])))
           ["seconds_per_metre"] if r["scene"] == sc}
    for arm in ("official_nov", "frontier_end"):
        if arm not in spm or spm[arm]["sec_per_m"]["mean"] is None:
            fail(f"slides 9 and 12 need seconds per metre for {arm} on 853, and paper_compare.json has none")
    sp_a, sp_f = spm["official_nov"]["sec_per_m"], spm["frontier_end"]["sec_per_m"]
    if not (sp_a["mean"] < sp_f["mean"] and rnd(sp_a["mean"], 1) < rnd(sp_f["mean"], 1)):
        fail("slides 9 and 12 say that at a given time November's ASP has gone farther than frontier (fewer "
             f"seconds per metre), but ASP logs {sp_a['mean']:.2f} against frontier's {sp_f['mean']:.2f}")
    plc50 = mean(C, "placebo", "50", "ours")
    if not rnd(oct_["50"], 1) < rnd(plc50, 1) < rnd(nov["50"], 1):
        fail("slide 12 says October's random-guess runs read between the two ASP batches at 50%, but "
             f"{num(plc50)} is not between {num(oct_['50'])} and {num(nov['50'])}")
    return {"lo": min(d), "hi": max(d), "leads": leads, "paper_leads": pv, "oct10": oct10, "oct50": oct50,
            "batch50": batch50, "ns": ns, "hm3d100": others["hm3d"], "fm100": others["frontier_made"],
            "seed": seed, "alt": alt, "nov_m": ends.pop(), "oct_m": ASP_OCT_M,
            "oct50_mean": num(oct_["50"]), "nov50_mean": num(nov["50"]), "plc50": num(plc50),
            "nov100": num(nov["100"]), "fr100": num(fr["100"]),
            "n_fr100": C[(sc, "frontier_end", "100")]["stage_value_x100"]["n"],
            "paper_asp100": num(C[(sc, "official_nov", "100")]["paper_f1_x100"]),
            "paper_fr100": num(C[(sc, "frontier_end", "100")]["paper_f1_x100"]),
            "stopped100": num(sv100["mean"]), "stopped_n": sv100["n"], "stopped_runs": stopped["100"][1],
            "nov_runs": C[(sc, "official_nov", "10")]["n_runs"], "fr_runs": C[(sc, "frontier_end", "10")]["n_runs"],
            "oct_runs": C[(sc, "official", "10")]["n_runs"],
            "spm_asp": num(sp_a["mean"]), "spm_fr": num(sp_f["mean"]), "spm_n_asp": sp_a["n"], "spm_n_fr": sp_f["n"]}


def need(text, needles, where):
    miss = [n for n in needles if n not in text]
    if miss:
        fail(f"{where} lacks " + "; ".join(repr(n) for n in miss) + ". The builder computed these from the cells; "
             "edit the text to match them.")


def spoken(d):
    """A signed difference as the script says it."""
    return f"minus {abs(d)}" if d < 0 else f"{d}"


def pm(v, nd=3):
    """A signed value as the script says it: 'plus 0.013' or 'minus 0.012'."""
    return f"plus {num(abs(v), nd)}" if rnd(v, nd) >= 0 else f"minus {num(abs(v), nd)}"


def check_text(C, f9, f853, budgets, slots, Nn):
    """The script and README finding 3 hold typed figures. Check each against the cells and the slots."""
    md = open(SCRIPT).read()

    def section(n):
        m = re.search(rf"^## Slide {n}:.*?(?=\n---)", md, flags=re.M | re.S)
        if not m:
            fail(f"ENDSEM_Script.md has no 'Slide {n}' section")
        return m.group(0)

    def body(n):
        return section(n).split("\n", 1)[1]
    k, mm, w = f9["neg"], f9["m"], WORDS
    L, PL = f853["leads"], f853["paper_leads"]
    alt = f853["alt"]
    eq, sn = f853["equal"], f9["sens"]
    n100, nr = f853["ns"]["100"]
    b3, b8, sl = slots["blind"]["models"], slots["ceiling"], slots
    if not (f853["hm3d100"] > 0 > f853["fm100"]):
        fail("the README gives the 100% gap as positive under the human labels and negative under the "
             f"frontier-made map, but they are {f853['hm3d100']} and {f853['fm100']}")

    def pct(v, nd=1):
        return num(100 * v, nd)

    def pct0(v):
        t = pct(v)
        return t[:-2] if t.endswith(".0") else t
    # slide 1: nothing typed. slide 2: the proposal
    pn, e2 = slots["pinned"]["proposal"], (-Nn["E2:hm3d:60m:statistic"], -Nn["E2:hm3d:60m:permutation_hi"],
                                          -Nn["E2:hm3d:60m:permutation_lo"])
    need(body(2), [f"{pm(e2[0])}, from {pm(e2[1])} to {pm(e2[2])}",
                   f"gains of {num(Nn['E2:hm3d:60m:mde'], 3)} or more", f"{pn['kept']} of {pn['of']:,} guesses"],
         "script slide 2")
    need(body(4), [f"{pm(Nn['E1:hm3d:60m:statistic'])}, from {pm(Nn['E1:hm3d:60m:permutation_lo'])} to "
                   f"{pm(Nn['E1:hm3d:60m:permutation_hi'])}", "DeepSeek V4.1 Flash at low effort"], "script slide 4")
    need(body(8), [f"{budgets['00853']:.0f} seconds on 853, {budgets['00871']:.0f} on 871", "about twice 853's"],
         "script slide 8")
    # slide 9: November's ASP on 853, by the clock and by the metre
    need(body(9), [f"November's {w[f853['nov_runs']]} ASP runs sit above our {w[f853['fr_runs']]} frontier runs "
                   f"at 10%, 50% and 100%, by {L['10']}, {L['50']} and {L['100']} points, against the paper's "
                   f"{PL['10']}, {PL['50']} and {PL['100']}",
                   f"October's {w[f853['oct_runs']]} runs trailed by {abs(f853['oct50'])} at 50%; the batches "
                   f"differ by {f853['batch50']}",
                   f"at 50 metres ASP is {eq[('apr', 50)]} ahead under the scripted reference and "
                   f"{abs(eq[('hm3d', 50)])} behind under the human labels. At 100 metres, {eq[('apr', 100)]} ahead "
                   f"and {abs(eq[('hm3d', 100)])} behind",
                   "not a test of the paper's claim"], "script slide 9")
    # slide 10: 871
    st, pc = PINNED["paper"]["steps"], f853["pc871"]
    need(body(10), [f"{budgets['00871']:.0f} seconds, ours are {f9['lo']} to {f9['hi']} points above the paper's",
                    f"{st[0]} to {st[1]} steps", f"{int(SENS_B)} seconds our frontier is {sn['gap_lo']} to "
                    f"{sn['gap_hi']} points below the paper's",
                    f"exact objects {pc['oracle_visible']}, ASP {pc['official']}, November's frontier "
                    f"{pc['frontier_end']}, random guesses {pc['placebo']}, October's frontier {pc['frontier_60m']}",
                    f"differ by {sn['batch']}", "that budget is twice 853's"], "script slide 10")
    # slide 12: the runs and the clock
    fr50 = {k_: num(C[("00853", k_, "50")]["stage_value_x100"]["mean"]) for k_ in ("frontier_60m", "frontier_end")}
    ck = PINNED["clock"]
    need(body(12), [f"stop at {f853['oct_m']} metres", f"go to {f853['nov_m']}",
                    f"{w[n100]} of {w[nr]} reach the full budget",
                    f"{f853['oct50_mean']} and {f853['nov50_mean']}",
                    f"ASP logs {f853['spm_asp']} seconds a metre against frontier's {f853['spm_fr']}",
                    ], "script slide 12")
    # slide 16: the blind table; slide 17: two facts; slide 18: the ceiling
    o, h = b3["opus"], b3["haiku"]
    need(body(16), [f"Opus scores {pct(o['L1']['score'])}% and the prior "
                    f"{pct(b8['opus']['L1']['B3']['comparator_score'])}%; Haiku {pct(h['L1']['score'])}% and "
                    f"{pct0(b8['haiku']['L1']['B3']['comparator_score'])}%",
                    f"At L2, Opus {pct(o['L2']['score'])}% against {pct(b8['opus']['L2']['B3']['comparator_score'])}%; "
                    f"Haiku {pct(h['L2']['score'])}% against {pct(b8['haiku']['L2']['B3']['comparator_score'])}%",
                    f"plus {pct(o['L3']['hi'], 2)} points for Opus and {pct(h['L3']['hi'])} for Haiku, under the "
                    f"{pct(o['L3']['margin'], 0)}-point margin", "The registered line is: the claim fails"],
         "script slide 16")
    chk = sl["blind"]["opus_l3_check"]
    reruns = {15: "fifteen"}.get(chk["runs"])
    if reruns is None:
        fail(f"script slide 17 says fifteen reruns, but there are {chk['runs']}")
    need(body(17), [f"{pct(chk['registered_upper'], 2)} points, the margin {pct(chk['margin'], 0)}",
                    f"{reruns} times", f"from {pct(chk['rerun_min'], 2)} to {pct(chk['rerun_max'], 2)}",
                    f"{pct(h['L2']['placebo']['diff'])} points above random guesses, p "
                    f"{num(h['L2']['placebo']['p'], 3)}"], "script slide 17")
    c1, c2 = b8["opus"], b8["haiku"]
    need(body(18), [f"{pct(c1['L1']['B3']['comparator_score'])}% on Opus's L1 rows and "
                    f"{pct0(c2['L1']['B3']['comparator_score'])}% on Haiku's; at L2, "
                    f"{pct(c1['L2']['B3']['comparator_score'])}% and {pct(c2['L2']['B3']['comparator_score'])}%",
                    f"{num(c1['L1']['B3']['perfect']['p_min_holm6'], 3)} and "
                    f"{num(c2['L1']['B3']['perfect']['p_min_holm6'], 3)} at L1; "
                    f"{num(c1['L2']['B3']['perfect']['p_min_holm6'], 3)} and "
                    f"{num(c2['L2']['B3']['perfect']['p_min_holm6'], 3)} at L2",
                    "at L2 only for Opus",
                    f"ends at {pct(o['L3']['hi'], 2)} against a margin of {pct(o['L3']['margin'], 0)}; Haiku's at "
                    f"{pct(h['L3']['hi'], 2)}"], "script slide 18")
    # slides 19 and 20: the registered Gemini replay
    gr = sl["gemini_replay"]
    fm = gr["family"]
    o2, o3, h2, h3 = (fm["claude-opus-5-5|L2"], fm["claude-opus-5-5|L3"], fm["claude-haiku-5-5|L2"],
                      fm["claude-haiku-5-5|L3"])
    need(body(19), [f"on the {gr['rows']} inputs Claude saw: four members each, {gr['ok']} of {gr['members']} parsed",
                    "no longer offered to new users",
                    f"October's lead on {sl['common']['anchor_rows']} rows repeated on {gr['rows']} new ones",
                    f"Gemini minus Opus at L2: {pm(100 * o2['diff'], 1)} points, from {pm(100 * o2['lo'], 1)} to "
                    f"{pm(100 * o2['hi'], 1)}, Holm p {num(o2['p_holm'], 4)}",
                    f"At L3: {pm(100 * o3['diff'], 1)}, from {pm(100 * o3['lo'], 1)} to {pm(100 * o3['hi'], 1)}, p "
                    f"{num(o3['p_holm'], 4)}", f"Minus Haiku: {pm(100 * h2['diff'], 1)} at L2, {pm(100 * h3['diff'], 1)} "
                    "at L3", "All four found, 12 clusters", "So the Claude result does not carry over",
                    "model and loop come together", "found under the registered one-sided test"], "script slide 19")
    r3, r2g = gr["rule"]["L3"], gr["rule"]["L2"]["comparators"]
    c3 = r3["comparators"]
    need(body(20), [f"Gemini scores {pct(r3['own'])}%, below all three controls: {pct(c3['B5']['own'])}%, "
                    f"{pct(c3['D']['own'])}% for the trade of regions, {pct(c3['B3L']['own'])}%",
                    f"ends at {pm(100 * r3['upper_named'], 1)}, under the margin of {pct(r3['delta'], 0)}",
                    f"{pct(r3['own'])}% against {pct(o3['other'])}% and {pct(h3['other'])}%",
                    "against Opus the interval includes zero",
                    f"at L2 Gemini scores {pct(gr['rule']['L2']['own'])}%, below the prior's "
                    f"{pct(r2g['B3']['own'])}%, about {pct(abs(r2g['B3']['diff']), 0)} points",
                    f"above random guesses' {pct(r2g['B1']['own'])}%", "wrong-house check at L1 and L2",
                    "Gemini also made more guesses per member; 5a does not adjust for that"], "script slide 20")
    rr, rf, pp = sl["room_runs"], sl["rooms_fit"], sl["room_test"]["paper"]
    e8, ea = rr["eight_member_stages"], rr["all_stages"]
    need(body(21), [f"{pp['hit']} of {pp['of']} rooms",
                    f"it predicts {e8['pooled']['official']['predicted']} of {e8['pooled']['official']['of']} "
                    f"rooms, random guesses {e8['pooled']['placebo']['predicted']} of {e8['pooled']['placebo']['of']}",
                    f"{pct(e8['pooled']['official']['rate'])}% against {pct(e8['pooled']['placebo']['rate'])}%, p "
                    f"{num(e8['tests']['official_vs_placebo']['p'], 3)}",
                    f"{ea['pooled']['official']['predicted']} of {ea['pooled']['official']['of']}, "
                    f"{pct(ea['pooled']['official']['rate'])}%, p {num(ea['tests']['official_vs_placebo']['p'], 3)}",
                    f"{pct(e8['pooled']['filter_only']['rate'])}% and {pct(ea['pooled']['filter_only']['rate'])}%, "
                    f"p {num(e8['tests']['filter_only_vs_placebo']['p'], 3)} and "
                    f"{num(ea['tests']['filter_only_vs_placebo']['p'], 3)}",
                    "by the count in registration §11",
                    f"{pct(rf['model'])}% of its rooms land in a fitting unobserved region, against "
                    f"{pct(rf['placebo'])}% for random guesses; p {num(rf['p'], 3)}"], "script slide 21")
    m2 = sl["m2"]
    f3 = [m2["rho"][a]["mean"] for a in ("F3-deepseek", "F3-haiku", "F3-opus")]
    need(body(22), [f"{m2['n_stages']} stages",
                    f"True objects give {num(m2['rho']['F1']['mean'], 3)}, random guesses "
                    f"{num(m2['rho']['F5']['mean'], 3)}: a gap of {num(m2['diff']['A']['mean'], 3)}, and half is "
                    f"{num(m2['diff']['A']['mean'] / 2, 3)}",
                    f"give {num(min(f3), 3)} to {num(max(f3), 3)}", f"gives {num(m2['rho']['F0']['mean'], 3)}",
                    f"never passes {num(sl['all_true']['bits_cap'], 1)} bits",
                    f"correlate at {num(sl['all_true']['spearman_mean'], 2)}", "reads mainly where"],
         "script slide 22")
    need(body(25), ["not detectably more often than a trade of regions",
                    "at L1 no model could have been Supported, and at L2 only a perfect Opus"],
         "script slide 25")
    need(body(26), [f"{pct(h['L2']['placebo']['diff'])} points above"], "script slide 26")
    banned = ("leads", "does not appear", "did not appear", "beats", "reproduce")
    for n in (9, 10, 12, 24):
        hit = [b_ for b_ in banned if b_ in body(n).lower()]
        if hit:
            fail(f"script slide {n} uses wording the data do not carry: {hit}")
    rd = open(os.path.join(PROJECT, "README.md")).read()
    m = re.search(r"^3\. \*\*November paper-scale.*?(?=^4\. \*\*)", rd, flags=re.M | re.S)
    if not m:
        fail("README.md has no finding 3")
    cells = []
    for sc in ("00853", "00871"):
        for arm in ("official", "official_nov", "filter_only", "frontier_end"):
            if (sc, arm, "10") not in C:
                continue
            for f in ("10", "50", "100"):
                main, sub = stat_cell(C, sc, arm, f)
                if main:
                    cells.append(f"{main.split(' ')[0]} ({sub})")
    need(m.group(0), [f"within {f9['lo']} to {f9['hi']} points of the paper's",
                      f"{w[k]} of the {w[mm]} gaps turn negative at 0.8 B", f"{f9['inside']} of {mm} cells",
                      f"{f853['lo']} to {f853['hi']} below",
                      f"ASP reads {f853['nov100']} (n={n100}) and our frontier {f853['fr100']} (n={f853['n_fr100']})",
                      f"the paper's {f853['paper_asp100']} and {f853['paper_fr100']}",
                      f"{L['10']}, {L['50']} and {L['100']} points against the paper's "
                      f"{PL['10']}, {PL['50']} and {PL['100']}",
                      f"led by {f853['oct10']} at 10% and trailed by {abs(f853['oct50'])} at 50%",
                      f"{f853['batch50']} points at 50%", f"read {f853['plc50']} at 50%",
                      f"{f853['hm3d100']} under `hm3d` and {f853['fm100']} under `frontier_made`",
                      f"November's ASP logs {f853['spm_asp']} s per metre (n={f853['spm_n_asp']}) and our frontier "
                      f"{f853['spm_fr']} (n={f853['spm_n_fr']}), and frontier's clock also counts its waits for a path, "
                      "so part of each gap may come from the clock",
                      f"seed {f853['seed']}", f"which then reads {f853['stopped100']} (n={f853['stopped_n']} of "
                      f"{f853['stopped_runs']})", f"{alt['10'][0]} / {alt['50'][0]} / {alt['100'][0]}",
                      "does not test the paper's claim"] + cells, "README finding 3")
    hit = [b for b in banned if b in m.group(0).lower()]
    if hit:
        fail(f"README finding 3 uses wording the data do not carry: {hit}")
    em, pc = f853["eqm"], f853["pc871"]
    need(m.group(0), [f"at 50 m ASP reads {em[('apr', 50, 'official_nov')]} (n=3) and our frontier "
                      f"{em[('apr', 50, 'frontier_end')]} (n=5) against the scripted reference, {eq[('apr', 50)]} "
                      f"ahead, and {em[('hm3d', 50, 'official_nov')]} against {em[('hm3d', 50, 'frontier_end')]} under "
                      f"the human labels (`hm3d`), {abs(eq[('hm3d', 50)])} behind; at 100 m, "
                      f"{em[('apr', 100, 'official_nov')]} (n=3) against {em[('apr', 100, 'frontier_end')]} (n=2 of 5), "
                      f"{eq[('apr', 100)]} ahead, and {em[('hm3d', 100, 'official_nov')]} against "
                      f"{em[('hm3d', 100, 'frontier_end')]}, {abs(eq[('hm3d', 100)])} behind",
                      "registered and running",
                      f"is about twice 853's, {budgets['00853']:.0f} s",
                      f"our frontier reads {' / '.join(sn['f750'])} against the paper's {' / '.join(sn['paper'])}, "
                      f"{sn['gap_lo']} to {sn['gap_hi']} points below it",
                      f"exact objects {pc['oracle_visible']} (n=3), ASP {pc['official']} (n=3), November's frontier "
                      f"{pc['frontier_end']} (n=5), random guesses {pc['placebo']} (n=3), October's frontier "
                      f"{pc['frontier_60m']} (n=3)",
                      f"differ by {sn['batch']}, more than ASP differs from November's frontier ({sn['asp_fr']}) or "
                      f"from random guesses ({sn['asp_pl']})"], "README finding 3 (equal path, budget)")
    m4 = re.search(r"^4\. \*\*November semantic test.*?(?=^5\. \*\*)", rd, flags=re.M | re.S)
    m5 = re.search(r"^5\. \*\*Would right meaning.*?(?=^## )", rd, flags=re.M | re.S)
    if not m4 or not m5:
        fail("README.md lacks finding 4 or finding 5")
    o, h, b8 = slots["blind"]["models"], slots["blind"]["models"]["haiku"], slots["ceiling"]
    o = o["opus"]
    cm = slots["common"]["levels"]
    l2, l3 = cm["L2"]["mean_row_score"], cm["L3"]["mean_row_score"]
    rr, rf = slots["room_runs"], slots["rooms_fit"]
    e8, ea = rr["eight_member_stages"], rr["all_stages"]
    need(m4.group(0), [f"the other-house prior scores {pct(b8['opus']['L1']['B3']['comparator_score'])}% and "
                       f"{pct(b8['haiku']['L1']['B3']['comparator_score'])}% at L1 and "
                       f"{pct(b8['opus']['L2']['B3']['comparator_score'])}% and "
                       f"{pct(b8['haiku']['L2']['B3']['comparator_score'])}% at L2",
                       f"Opus's interval ends at {pct(o['L3']['hi'], 2)} against a margin of {pct(o['L3']['margin'], 0)}",
                       "as the author put it to us", "not checked before the test was frozen",
                       f"Gemini scores {pct(l2['gemini'])}% at L2 against DeepSeek {pct(l2['deepseek'])}%, Haiku "
                       f"{pct(l2['claude-haiku-5-5'])}%, Opus {pct(l2['claude-opus-5-5'])}% and random guesses "
                       f"{pct(l2['placebo'])}%, and {pct(l3['gemini'])}% at L3 against {pct(l3['deepseek'])}%, "
                       f"{pct(l3['claude-haiku-5-5'])}%, {pct(l3['claude-opus-5-5'])}% and {pct(l3['placebo'])}%",
                       f"DeepSeek's live runs predict {e8['pooled']['official']['predicted']} of "
                       f"{e8['pooled']['official']['of']} rooms and random guesses {e8['pooled']['placebo']['predicted']} "
                       f"of {e8['pooled']['placebo']['of']} (p {num(e8['tests']['official_vs_placebo']['p'], 3)}); on "
                       f"all stages, {ea['pooled']['official']['predicted']} of {ea['pooled']['official']['of']} "
                       f"(p {num(ea['tests']['official_vs_placebo']['p'], 3)})",
                       f"{e8['pooled']['filter_only']['predicted']} of {e8['pooled']['filter_only']['of']} (p "
                       f"{num(e8['tests']['filter_only_vs_placebo']['p'], 3)}) on 8-member stages, "
                       f"{ea['pooled']['filter_only']['predicted']} of {ea['pooled']['filter_only']['of']} (p "
                       f"{num(ea['tests']['filter_only_vs_placebo']['p'], 3)}) on all stages",
                       f"places {pct(rf['model'])}% of its rooms in a fitting unobserved region against "
                       f"{pct(rf['placebo'])}% for random guesses (p {num(rf['p'], 3)}"], "README finding 4")
    gq = slots["gemini_replay"]
    gf, g3 = gq["family"], gq["rule"]["L3"]
    need(m4.group(0), [t.replace("−", "-") for t in [f"{gq['ok']} of {gq['members']} parsed",
                       f"Gemini minus Opus +{pct(gf['claude-opus-5-5|L2']['diff'])} points at L2 (95% interval "
                       f"+{pct(gf['claude-opus-5-5|L2']['lo'])} to +{pct(gf['claude-opus-5-5|L2']['hi'])}, Holm p "
                       f"{num(gf['claude-opus-5-5|L2']['p_holm'], 4)})",
                       f"+{pct(gf['claude-opus-5-5|L3']['diff'])} at L3 ({pct(gf['claude-opus-5-5|L3']['lo'])} to "
                       f"+{pct(gf['claude-opus-5-5|L3']['hi'])}, p {num(gf['claude-opus-5-5|L3']['p_holm'], 4)})",
                       f"Haiku +{pct(gf['claude-haiku-5-5|L2']['diff'])} at L2", f"+{pct(gf['claude-haiku-5-5|L3']['diff'])} at L3",
                       gq["wording"][0], gq["wording"][5],
                       f"Its L3 score is {pct(g3['own'])}%, below all three controls ({pct(g3['comparators']['B5']['own'])}%, "
                       f"{pct(g3['comparators']['D']['own'])}% for the trade of regions, "
                       f"{pct(g3['comparators']['B3L']['own'])}%)",
                       "the contrast is of model and loop together", "the interval includes zero",
                       "Gemini also made more guesses per member, and 5a does not adjust for that",
                       "Note 3, after this result was seen) and running"]], "README finding 4 (Gemini)")
    at = slots["all_true"]
    need(m5.group(0), [f"never passes {num(at['bits_cap'], 1)} bits", f"correlate at {num(at['spearman_mean'], 2)}",
                       "M2 varied place, not meaning"], "README finding 5")


SENS_B = "750"      # the shorter budget slide 10 shows beside the registered one (a key of budget_sensitivity.json)


def sens_cell(bs, sc, arm, bkey, f):
    return bs["scenes"][sc]["tables"]["apr"][arm][bkey][f]


def facts_sens871(bs, ep, C):
    """Slide 10's second row, the equal-path strip and the sentences about them. Stops the build if the sentences
    would say more than the cells."""
    sc = "00871"
    S = bs["scenes"][sc]
    reg = S["registered_B_label"]
    if SENS_B not in S["budgets_s"] or abs(S["registered_B_s"] - BUDGETS_NOW[sc]) > 0.01:
        fail("budget_sensitivity.json lacks the 750 s budget, or its registered B differs from paper_compare.json")
    for arm in ("official", "frontier_end"):          # the registered row must equal the registered cells
        for f in ("10", "50", "100"):
            a, b = sens_cell(bs, sc, arm, reg, f), C[(sc, arm, f)]["stage_value_x100"]
            same = (a["mean"] is None and b["mean"] is None) or (
                a["mean"] is not None and b["mean"] is not None and abs(a["mean"] - b["mean"]) < 1e-6)
            if not same or a["n"] != b["n"]:
                fail(f"budget_sensitivity.json's registered row differs from paper_compare.json for {arm} {f}%")
    gaps750 = []
    for f in ("10", "50", "100"):
        c = sens_cell(bs, sc, "frontier_end", SENS_B, f)
        if not c["n"] or c["n"] != c["n_runs"]:
            fail(f"slide 10 needs all frontier runs to have a value at {f}% of 750 s")
        gaps750.append(rnd(c["mean"], 1) - rnd(C[(sc, "frontier_end", f)]["paper_f1_x100"], 1))
    if max(gaps750) >= 0:
        fail("slide 10 says our frontier is below the paper's at every fraction of 750 s, but " + str(gaps750))
    a50 = ecell(ep, sc, "apr", "official", 50)
    fn, fo = ecell(ep, sc, "apr", "frontier_end", 50), ecell(ep, sc, "apr", "frontier_60m", 50)
    pl = ecell(ep, sc, "apr", "placebo", 50)
    if not all(c["n"] for c in (a50, fn, fo, pl)):
        fail("slide 10 needs equal-path values at 50 m for ASP, both frontier batches and random guesses")
    batch = lead(fn["mean"], fo["mean"])
    asp_fr, asp_pl = abs(lead(a50["mean"], fn["mean"])), lead(a50["mean"], pl["mean"])
    if not (batch > asp_fr and batch > asp_pl):
        fail("slide 10 says our two frontier batches differ by more than ASP differs from November's frontier or from "
             f"random guesses at 50 m, but {batch} is not above {asp_fr} and {asp_pl}")
    return {"gap_lo": min(abs(g) for g in gaps750), "gap_hi": max(abs(g) for g in gaps750), "batch": batch,
            "asp_fr": asp_fr, "asp_pl": asp_pl, "fn": fn, "fo": fo,
            "f750": [num(sens_cell(bs, sc, "frontier_end", SENS_B, f)["mean"]) for f in ("10", "50", "100")],
            "paper": [num(C[(sc, "frontier_end", f)]["paper_f1_x100"]) for f in ("10", "50", "100")]}


BUDGETS_NOW = {}     # filled in main(): the registered budgets of paper_compare.json
PINNED = {}          # filled in main(): slots.json "pinned", facts read from files that are not result tables


def sens_row(bs, sc, arm, bkey):
    """Cells (main, sub, colour, colour) of one budget-sensitivity row, with the table's rule (a time shows only if
    at least half the runs reach it)."""
    cells = []
    for f in ("10", "50", "100"):
        c = sens_cell(bs, sc, arm, bkey, f)
        if not c["n"] or c["n"] * 2 < c["n_runs"]:
            cells.append(("none", "no run reaches it" if not c["n"] else f"{c['n']} of {c['n_runs']} runs", FAINT, MID))
        else:
            main, sub = cell_str(c)
            cells.append((main, sub, INK, MID))
    return cells


def table871(prs, C, budgets, slots, f9, bs, ep):
    if not slots["table871_updated"]:
        fail("slots.json table871_updated is not true: the 871 rescore is not marked final")
    sn = f9["sens"]
    s = frame(prs, 10, f"Part 2 · Home 871 · object F1 × 100, mean [min{DASH}max] · registered budget "
                        f"{budgets['00871']:.0f} s", "How close we are to the paper on 871 depends on the budget")
    paper_rows = table_rows(C, "00871", ())
    reg = bs["scenes"]["00871"]["registered_B_label"]
    rows = paper_rows + [
        (f"Ours · ASP, {budgets['00871']:,.0f} s", sens_row(bs, "00871", "official", reg), "ours"),
        (f"Ours · frontier, {budgets['00871']:,.0f} s", sens_row(bs, "00871", "frontier_end", reg), "ours"),
        ("Exploratory · ASP, 750 s", sens_row(bs, "00871", "official", SENS_B), "ours", True),
        ("Exploratory · frontier, 750 s", sens_row(bs, "00871", "frontier_end", SENS_B), "ours")]
    y = table(s, 120, 232, 440, 400, rows, {"paper": 40, "ours": 52})
    y += 14
    y = lab(s, 120, y, 1680, f"Exploratory · equal path, 50 m · scripted reference · F1 × 100, mean [min{DASH}max]")
    grid = [("oracle_visible", "Exact objects"), ("official", "ASP"), ("filter_only", "ASP + filter"),
            ("placebo", "Random guesses"), ("frontier_end", "Frontier, Nov"), ("frontier_60m", "Frontier, Oct"),
            ("crashed_frontier_1st", "Frontier, crashed 1st tries"), ("crashed_frontier_rerun", "Frontier, reruns")]
    for i, (arm, name) in enumerate(grid):
        main, sub = cell_str(ecell(ep, "00871", "apr", arm, 50))
        if main is None:
            fail(f"slide 10's equal-path grid has no value at 50 m for {arm}")
        gx, gy = 120 + (i % 4) * 420, y + (i // 4) * 66
        dim = arm in ("filter_only", "crashed_frontier_1st", "crashed_frontier_rerun")   # not read aloud
        text(s, gx, gy, 410, 30, [run(name, NT, FAINT if dim else MID, SANS, True)], line=1.2)
        text(s, gx, gy + 28, 410, 34, [run(f"{main} {sub}", 26, MID if dim else INK, MONO)], line=1.2)
    y += 2 * 66 + 6
    y = P(s, 120, y, 1680,
          f"At {budgets['00871']:,.0f} s ours are {f9['lo']}{DASH}{f9['hi']} points above the paper's. At "
          f"{int(SENS_B)} s our frontier is "
          f"{sn['gap_lo']}{DASH}{sn['gap_hi']} below it. Our two frontier batches differ by {sn['batch']} at 50 m, "
          f"more than ASP differs from November's frontier ({sn['asp_fr']}) or from random guesses ({sn['asp_pl']}).",
          B, BODY, 1.35, limit=960, tag="slide 10 body")
    st = PINNED["paper"]["steps"]
    Nq(s, 120, y + 2, 1680,
       f"{int(SENS_B)} s: the paper says a run has {st[0]} to {st[1]} steps, which suggests a shorter budget than "
       f"our {budgets['00871']:,.0f} s. Our inference, not its figure. Paper: Fig. 4 (left), one run each.",
       limit=1012)


# ---------------------------------------------------------------- 10. Part 2, limits of the reference

def limits_reference(prs, checks, f1, frozen):
    """f1: C2 per scene, {"00853": ..., "00871": ...}. frozen: whether each repeat tour is frozen (None: not known)."""
    if any(v is True for v in frozen.values()):
        fail("slide 11 says the repeat tour is not frozen in either home, but c2_*.json says it is frozen in "
             + ", ".join(sc for sc, v in frozen.items() if v is True))
    if any(v is None for v in frozen.values()):
        print("NOTE: no c2_*.json value for 'frozen'; slide 11's 'not frozen' is not tested", file=sys.stderr)
    if max(f1.values()) >= 0.90:
        fail("slide 11 says both C2 values are below 0.90, but one is not: " + str(f1))
    s = frame(prs, 11, "Part 2 · Limits of the reference", "The reference is rebuilt, and it moves")
    rec = [checks[sc]["C3"]["apr_a_recall_vs_hm3d"] for sc in ("00853", "00871")]
    c1t = json.load(open(C1_TABLE))
    L, w = 120, 900
    y = P(s, L, 262, w, [("Rebuilt. ", "b"), (f"It holds {100 * rec[0]:.0f}% and {100 * rec[1]:.0f}% of the "
                                                "human-labelled objects (853, 871).", "n")], B, BODY, 1.4)
    y = P(s, L, y + 24, w, [("Repeat tour. ", "b"),
                            (f"In both homes it is not frozen. The two tours agree at F1 {f1['00853']:.3f} on 853 and "
                             f"{f1['00871']:.3f} on 871 (C2). Both are below the 0.90 line: the reference itself moves "
                             "by more than the paper's margins. The first tours' damage is mixed in.", "n")],
          B, BODY, 1.4, limit=960)
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

def limits_runs(prs, C, budgets, slots, f853):
    s = frame(prs, 12, "Part 2 · Limits of the runs", "What limits the runs")
    ck = PINNED["clock"]
    # Guards for the sentences below: October's ASP runs have no value past 60 m (853 at 100%, 871 at 50%), and the
    # two frontier batches' ranges overlap. (facts853 guards the batch gap and the November row.)
    for sc, f in (("00853", "100"), ("00871", "50")):
        for arm in ASP_ARMS:
            n = C[(sc, arm, f)]["stage_value_x100"]["n"]
            if n:
                fail(f"slide 12 says October's ASP runs have no value at {f}% on {sc[-3:]}, but {arm} has n={n}")
    for f in ("10", "50"):
        a, b = (C[("00853", arm, f)]["stage_value_x100"] for arm in ("frontier_60m", "frontier_end"))
        if max(a["min"], b["min"]) > min(a["max"], b["max"]):
            fail(f"slide 12 says the two frontier batches' ranges overlap at {f}%, but they do not")
    if C[("00871", "official", "50")]["stage_value_x100"]["n"]:
        fail("slide 12 says no ASP run reaches 50% of the 871 budget, but one does")
    first_871 = f"{0.1 * budgets['00871']:.0f}"       # 10% of the 871 budget: the one ASP-frontier cell there

    def rng(arm, frac):
        sv = C[("00853", arm, frac)]["stage_value_x100"]
        return f"{num(sv['mean'])} [{num(sv['min'])}{DASH}{num(sv['max'])}]"
    n100, nruns = f853["ns"]["100"]
    L, w = 120, 1680
    y = P(s, L, 262, w, [("Two batches of ASP. ", "b"),
                         (f"October's runs stop at {f853['oct_m']} m; November's go to {f853['nov_m']} m, and "
                          f"{n100} of {nruns} reach 100% of the 853 budget. At 50% on 853 they score "
                          f"{rng('official', '50')} and {rng('official_nov', '50')}, and October's random-guess runs "
                          f"{f853['plc50']}, between the two: the batches differ by as much as the gap between "
                          "ASP and frontier.", "n")], B, BODY, 1.3)
    y = P(s, L, y + 20, w, [("Two batches of one frontier explorer. ", "b"),
                            (f"On 853 at 50% of the budget: {rng('frontier_60m', '50')} in October (3 runs, cut at "
                             f"60 m) and {rng('frontier_end', '50')} in November (5 runs, to the natural end). At "
                             f"10%: {rng('frontier_60m', '10')} and {rng('frontier_end', '10')}. The ranges "
                             "overlap.", "n")], B, BODY, 1.3)
    y = P(s, L, y + 20, w, [("The clocks differ. ", "b"),
                            ("In the authors' code, frontier's clock starts when planning ends, before the path "
                             "arrives, so it counts the wait for a path; ASP's starts as the robot begins to move. "
                             f"On 853 November's ASP logs {f853['spm_asp']} s per metre and our frontier "
                             f"{f853['spm_fr']}, so part of the gaps on slide 9 may come from the clock. "
                             f"On 871 the only ASP–frontier comparison at the registered budget is at "
                             f"{first_871} s.", "n")], B, BODY, 1.3)
    Nq(s, L, y + 8, w, f"Checked on {ck['date']} in the authors' commit {ck['commit']}: {ck['frontier']['file']} "
                       f"starts the clock at lines {ck['frontier']['start']}, stops it at {ck['frontier']['stop']}; "
                       f"{ck['asp']['file']} starts it at {ck['asp']['start']}.")
    box_bottom(s, "Reading.", "We read the table as a check on scale. It does not test the paper's claim.")


# ---------------------------------------------------------------- 12. Part 3, the defense

def defense(prs):
    s = frame(prs, 13, "Part 3", "The author's claim, in three questions")
    pn = PINNED["paper"]
    y = P(s, 120, 262, 1680, "As the author put it to us, the guesses are often wrong in place but right in "
                             "meaning, and that is enough.", B, INK, 1.4)
    y = P(s, 120, y + 10, 1680, "Not in the paper. It comes from the author's demo and from what the author told "
                                "the student when they met. The paper's nearest text, in section IV-B, calls a "
                                f"{pn['bathroom']} a failure that {pn['revisit']}.", B, MID, 1.35, limit=620)
    steps = [("Is the meaning right?", "Beat the controls: baselines that see the same map."),
             ("Is it enough for ASP?", "Give ASP true labels, moved by real error."),
             ("Is it the model?", "Replay Claude on 44 saved inputs, and Gemini on 36 of them.")]
    for i, (name, what) in enumerate(steps):
        x = 120 + i * 580
        hline(s, x, 640, x + 520, 640, INK, 2)
        y = P(s, x, 660, 520, [(name, "b")], B, line=1.3)
        P(s, x, y + 12, 520, what, B, BODY, 1.35, limit=900)
    box_bottom(s, "Blind test:", "the scorer was frozen first.")


# ---------------------------------------------------------------- 13. Part 3, a hit and a miss on one real stage

def picture_levels(prs, slots):
    n = json.load(open(STAGE_JSON))
    chance = slots["blind"]["models"]["opus"]
    s = frame(prs, 14, "Part 3", "A hit and a miss, on one stage")
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
    s = frame(prs, 15, "Part 3", "What each guess is compared with")
    mtxt = ", ".join(num(100 * mg[lv]["margin"], 0) for lv in ("L1", "L2", "L3"))
    y = P(s, 120, 252, 1680, f"A control sees the same map. Margin: the gain over it we would count ({mtxt} "
                             "points at L1, L2, L3). Named: the control the verdict uses.", B, BODY, 1.4)
    items = [("Prior from 179 other houses", "L1, L2 · named"), ("Random guesses", "L1, L2"),
             ("Own labels, swapped among guesses", "L3"), ("Regions, trading contents", "L3 · named"),
             ("Prior's labels at the model's places", "L3")]
    y += 14
    for txt, lv in items:
        y0 = y
        y = P(s, 120, y, 1280, txt, B, BODY, 1.35)
        text(s, 1400, y0 + 4, 400, 40, [run(lv, 28, MID, MONO)], PP_ALIGN.RIGHT, 1.2)
        hline(s, 120, y + 8, 1800, y + 8, RULE)
        y += 20
    box_bottom(s, "Not checked before the freeze:", "what the comparators themselves score. The power check asked only "
                                                    "whether “Rejected” was within reach, never whether "
                                                    "“Supported” was. Slide 18 shows what they score.")


# ---------------------------------------------------------------- 15. Part 3, the blind test

def pts(v, nd=1):
    """A fraction as signed points (x100)."""
    return sg(100 * v, nd)


def blind_facts(slots):
    """Guards for the words on slides 16, 18 and 24: all six registered verdicts Rejected (so the registered line is
    'The claim fails'), no detectable gain (every interval reaches 0 or below), and the ceiling flags the title,
    slide 18 and the script rely on."""
    b, ce = slots["blind"]["models"], slots["ceiling"]
    for m in ("opus", "haiku"):
        for lv in ("L1", "L2", "L3"):
            if b[m][lv]["verdict"] != "Rejected":
                fail(f"slides 16 and 24 say all six verdicts are Rejected, but {m} {lv} is {b[m][lv]['verdict']}")
            if b[m][lv]["lo"] > 0:
                fail(f"slide 16's title says no detectable gain, but {m} {lv} has an interval wholly above 0")
        if b[m]["L2"]["hi"] >= 0:
            fail(f"slide 16's title says both models are detectably below the prior at L2, but {m}'s interval "
                 "reaches 0")
    if slots["outcome"] != "fails" or slots["thesis"] != "The claim fails":
        fail("slides 16 and 24 give the registered line as 'The claim fails', but slots.json says "
             + repr(slots["thesis"]))
    can = {(m, lv): ce[m][lv]["B3"]["perfect"]["can_reach_alpha"] for m in ("opus", "haiku") for lv in ("L1", "L2")}
    if can != {("opus", "L1"): False, ("haiku", "L1"): False, ("opus", "L2"): True, ("haiku", "L2"): False}:
        fail("slides 16 and 18 say a perfect score could not have been Supported at L1 for either model, and at L2 "
             "only for Opus, but the ceiling file says " + str(can))
    for m in ("opus", "haiku"):
        for lv, c in (("L1", "B3"), ("L2", "B3")):
            if ce[m][lv][c]["comparator_score"] < 0.9:
                fail(f"slide 18 says the prior scores 90% or more at L1 and L2, but {m} {lv} is "
                     f"{ce[m][lv][c]['comparator_score']}")
        for c in ("D",):
            if ce[m]["L3"][c]["max_gain_perfect_model"] < b[m]["L3"]["margin"]:
                fail("slide 18 says Supported was within reach at L3, but the region trade scores too high")
    chk = slots["blind"]["opus_l3_check"]
    if not (b["opus"]["L3"]["hi"] < b["opus"]["L3"]["margin"] and chk["rerun_max"] < chk["margin"]):
        fail("slides 16, 17 and 18 say Opus's L3 interval ends just under its margin in the registered run and in "
             "every rerun, but it does not")
    return {"c": ce}


def blind_table(prs, slots):
    b = slots["blind"]["models"]
    ce = slots["ceiling"]
    s = frame(prs, 16, "Part 3 · Blind test",
              "Naming: no detectable gain over base rates, below them at L2. Placing: none over a region trade")
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
            own = f"score {num(100 * e['score'], 1)}%"
            if key in ce:       # the comparator's own score on the same rows (ceiling.json); DeepSeek has none
                cname = "region trade" if lv == "L3" else "prior"
                cc = ce[key][lv][e["named"]]
                # at L3 the model's score on the trade's own rows (43 of 44), so the two scores are on the same rows
                own = f"score {num(100 * (cc['model_score'] if lv == 'L3' else e['score']), 1)}%"
                tail = f"{own} · {cname} {num(100 * cc['comparator_score'], 1)}%"
            else:
                tail = own
            text(s, x, y + 76, cw - 20, 32, [run(tail, NT, MID)], line=1.2)
        y += 118
        hline(s, X, y, X + lw + 3 * cw, y, RULE)
    N(s, X, y + 6, 1680,
      "Difference = model minus comparator, in points. Score = the share of named room types (L1) or object classes "
      "(L2) that are there, or L3 hits; mean over 12 clusters (home, seed, arm). Opus and Haiku L3 scores are on the "
      f"region trade's {ce['opus']['L3']['D']['n_rows']} rows. One run with the frozen scorer; no other run is "
      "recorded. Opus L3 shows two decimals: its upper end, 2.95, is just under the margin, 3.",
      limit=905)
    box_bottom(s, "The registered line,", f"“{slots['thesis']}”, says less than it seems to. Rejected means the "
                                          "interval rules out a gain as large as the margin. At L1 no model could have "
                                          "been Supported, and at L2 only a perfect Opus could (slide 18), so the line "
                                          "rests on L3.")


# ---------------------------------------------------------------- 16. Part 3, two facts against the headline

def facts(prs, slots):
    b = slots["blind"]["models"]
    chk = slots["blind"]["opus_l3_check"]
    hh = b["haiku"]["L2"]["placebo"]
    s = frame(prs, 17, "Part 3", "Two facts that cut against the registered line")
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
    ce = slots["ceiling"]
    s = frame(prs, 18, "Part 3 · Exploratory, made after the result",
              "What a perfect score could have shown: a ceiling at L1 and L2")
    L = 120
    heads = [("Prior's own score", 330), ("Most a model could gain", 360), ("Best p after Holm", 300),
             ("Supported possible?", 300)]
    x = L + 380
    for hd, w in heads:
        text(s, x, 246, w, 34, [run(hd, NT, MID, SANS, True)])
        x += w
    hline(s, L, 286, L + 380 + sum(w for _, w in heads), 286, LINE)
    y = 292
    for lv in ("L1", "L2"):
        for key, name in (("opus", "Opus"), ("haiku", "Haiku")):
            d = ce[key][lv]["B3"]
            vals = [f"{num(100 * d['comparator_score'], 1)}%", f"{num(100 * d['max_gain_perfect_model'], 1)} points",
                    num(d["perfect"]["p_min_holm6"], 3), "yes" if d["perfect"]["can_reach_alpha"] else "no"]
            text(s, L, y + 10, 370, 40, [run(f"{lv} · {name}", 28, INK, SANS, True)], line=1.2)
            x = L + 380
            for (hd, w), v in zip(heads, vals):
                text(s, x, y + 10, w - 10, 40, [run(v, 30, INK, MONO)], line=1.2)
                x += w
            y += 54
            hline(s, L, y, L + 380 + sum(w for _, w in heads), y, RULE)
    y = P(s, L, y + 18, 1680, "The prior is the comparator at L1 and L2. A model that scores 100% in every member "
                              "could have gained only this much over it, with the smallest p the test could return "
                              "after Holm's correction for six tests.", B, BODY, 1.35, limit=960)
    y = P(s, L, y + 14, 1680, [("So the registered line rests on L3. ", "b"),
                               (f"There a perfect model could gain "
                                f"{num(100 * ce['opus']['L3']['D']['max_gain_perfect_model'], 0)} points over the "
                                f"region trade, and Opus's "
                                f"interval ends at {num(100 * ops['opus']['L3']['hi'], 2)} against a margin of "
                                f"{num(100 * ops['opus']['L3']['margin'], 0)}. For Haiku it ends at "
                                f"{num(100 * ops['haiku']['L3']['hi'], 2)}.", "n")], B, BODY, 1.35, limit=960)
    Nq(s, L, y + 8, 1680,
       f"At L1 and L2 the detectable difference is {num(100 * m['L1']['mdd'], 1)} and {num(100 * m['L2']['mdd'], 1)} "
      f"points, above the {num(100 * m['L1']['margin'], 0)}-point margin, so a true gain equal to the margin would be "
      f"found less than 80% of the time; Rejected was within reach. No L3 row: its registered figure, "
      f"{num(100 * m['L3']['mdd'], 1)} points, comes from the random guesses' contrast.", limit=1012)


# ---------------------------------------------------------------- 18. Part 3, the wrong-house check

def wrong_house(prs, slots):
    w = slots["blind"]["wrong_house"]
    s = frame(prs, 26, "Backup · Part 3 · Controls", "The wrong-house check", backup=True)
    y = P(s, 120, 252, 1680, "We score the model's guesses for the other home against this home. Right guesses "
                             "should beat them.", B, BODY, 1.4)
    X = 120
    for j, hd in enumerate(("L1", "L2")):
        text(s, X + 520 + j * 300, y + 24, 280, 34, [kick(hd, NT, 0.06)])
    hline(s, X, y + 62, X + 1100, y + 62, LINE)
    yy = y + 70
    gw = slots["gemini_replay"]["wrong_house"]
    rows = [("Opus", w["opus"]), ("Haiku", w["haiku"]), ("DeepSeek, exploratory", w["deepseek"]),
            ("Gemini 3.8 Flash, replay", gw)]
    for name, d in rows:
        text(s, X, yy + 12, 500, 44, [run(name, 28, INK, SANS, True)], line=1.2)
        for j, lv in enumerate(("L1", "L2")):
            text(s, X + 520 + j * 300, yy + 12, 280, 44, [run("p " + num(d[lv]["p"], 3), 32, INK, MONO)], line=1.2)
        yy += 64
        hline(s, X, yy, X + 1100, yy, RULE)
    if any(w[k][lv]["pass"] for k in ("opus", "haiku") for lv in ("L1", "L2")):
        fail("backup 1 says no Claude model passes the wrong-house check, but one does")
    if not all(gw[lv]["pass"] for lv in ("L1", "L2")):
        fail("backup 1 says Gemini 3.8 Flash passes the wrong-house check at L1 and L2, but it does not")
    N(s, X, yy + 16, 1680, "Haiku L1 has 5 pairs, the rest 6. Gemini 3.8 Flash passes at L1 and L2 (registered "
                           "replay, reported with no verdict). October's 8 rows had no partner.", limit=900)
    box_bottom(s, "No Claude model passes:", "a pass needs p below 0.05 over 6 pairs.")


# ---------------------------------------------------------------- 19. Part 3, how far a guess sits from an object it could name

def placement_slide(prs, slots):
    p = slots["placement"]
    s = frame(prs, 27, "Backup · Part 3", "How far a guess is from an object it could name", backup=True)
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


# ---------------------------------------------------------------- 19 and 20. Part 3, is it the model? (registered replay)

G_MODELS = (("claude-opus-5-5", "Opus"), ("claude-haiku-5-5", "Haiku"))


def gemini_facts(slots):
    """Guards for slides 19 and 20, the script, README and docs/RESULTS.md: the registration's section 6 lets the
    sentence 'does not carry over' stand only if all four hypotheses of 5a are found with Gemini above, and lets
    'did not beat a trade of region contents' stand only if the L3 verdict is Rejected."""
    g, c = slots["gemini_replay"], slots["common"]
    if g.get("status") != "filled" or g["model"] != "gemini-3.8-flash" or not g["confirmatory"]:
        fail("slots.json gemini_replay is not the filled, confirmatory result of gemini-3.8-flash")
    fam = g["family"]
    if sorted(fam) != sorted(f"{m}|{L}" for m, _ in G_MODELS for L in ("L2", "L3")):
        fail("slides 19 and 20 need the four hypotheses of 5a (Opus and Haiku, L2 and L3); the file has "
             + str(sorted(fam)))
    for k, h in fam.items():
        if not (h["found"] and h["diff"] > 0 and h["p_holm"] < 0.05 and h["n_clusters"] == g["clusters"] == 12):
            fail(f"slide 19 says Gemini is above Claude in all four hypotheses of 5a (Holm p below 0.05, 12 clusters), "
                 f"but {k} reads otherwise")
    if g["wording"][0].split(":")[0] != "The Claude result does not carry over to Gemini 3.8 Flash":
        fail("slide 19 gives the registered sentence for 'above both Claude models at L2 and L3', but the file's first "
             "sentence is another outcome's: " + g["wording"][0][:80])
    r3 = g["rule"]["L3"]
    if not (r3["confirmatory"] and r3["verdict"] == "Rejected" and r3["named"] == "D" and r3["upper_named"] < r3["delta"]):
        fail("slide 20 says the registered rule at L3 reads Rejected against the region trade, but it does not")
    if not g["wording"][5].startswith("Gemini 3.8 Flash did not beat a trade of region contents by the 3-point margin."):
        fail("slide 20 gives the registered sentence for a Rejected L3 verdict, but the file's sentence differs: "
             + g["wording"][5][:80])
    d3 = r3["comparators"]
    if not (g["rule"]["L3"]["own"] > max(fam[f"{m}|L3"]["other"] for m, _ in G_MODELS)
            and d3["D"]["own"] > r3["own"] and d3["D"]["diff"] < 0):
        fail("slide 20 says Gemini's L3 score is above both Claude models' and below the region trade's, but not so")
    if not (d3["B5"]["own"] > r3["own"] and d3["B3L"]["own"] > r3["own"]):
        fail("slide 20 says Gemini's L3 score is below all three of its controls, but it is not")
    if not fam["claude-opus-5-5|L3"]["lo"] < 0 < fam["claude-opus-5-5|L3"]["hi"]:
        fail("slides 19 and 20 say the 95% interval against Opus at L3 includes zero, but it does not")
    if not -0.135 < g["rule"]["L2"]["comparators"]["B3"]["diff"] < -0.115:
        fail("slide 20 says the prior scores about 12 points above Gemini at L2, but the file says "
             f"{g['rule']['L2']['comparators']['B3']['diff']:.3f}")
    r2 = g["rule"]["L2"]["comparators"]
    if not (r2["B3"]["hi"] < 0 and r2["B1"]["lo"] > 0):
        fail("slide 20 says that at L2 Gemini is below the prior and above random guesses (intervals off 0), but not so")
    if not all(g["wrong_house"][L]["pass"] and g["wrong_house"][L]["n_pairs"] == 6 for L in ("L1", "L2")):
        fail("slide 20 says Gemini passes the wrong-house check at L1 and L2 over 6 pairs, but it does not")
    if g["drop_rate_above_25"] or g["drop_rate"] >= 0.25 or (g["rows"], g["members"], g["ok"]) != (36, 144, 137):
        fail("slide 19 says 36 inputs, 4 members each, 137 of 144 parsed and a drop rate under 25%, but the file says "
             f"{g['rows']}, {g['members']}, {g['ok']}, {g['drop_rate']:.3f}")
    if not (g["members_per_row"] == 4 and g["finished_rounds"] == [1, 2, 3]):
        fail("slide 19 says all three rounds finished with 4 members a row, but the file says otherwise")
    if not all(c["levels"]["L2"]["mean_row_score"]["gemini"] > c["levels"]["L2"]["mean_row_score"][m] for m, _ in G_MODELS):
        fail("slide 19 says October's lead on 8 rows repeated on the new rows, but Gemini was not above Claude in "
             "October's 8 rows at L2")
    return g


def gpts(v, nd=1):
    return sg(100 * v, nd)


def gint(lo, hi):
    return f"[{gpts(lo)}, {gpts(hi)}]"


def gemini_slide(prs, slots):
    g = gemini_facts(slots)
    fam = g["family"]
    s = frame(prs, 19, "Part 3 · Is it the model? · registered replay",
              "Is it the model? In the author's loop Gemini 3.8 Flash scored above Claude", pending="registered")
    y = P(s, 120, 252, 1680, [("What ran. ", "b"),
                              (f"Gemini 3.8 Flash, in the author's own loop, on the {g['rows']} inputs Claude saw: "
                               f"{g['members_per_row']} members each, {g['ok']} of {g['members']} parsed. The paper's "
                               "Gemini 2.5 Pro is no longer offered to new users.", "n")], B, BODY, 1.3)
    y = lab(s, 120, y + 16, 1680, f"Confirmatory · Gemini minus Claude · {g['clusters']} clusters · one-sided, Holm over 4")
    cws = (440, 200, 200, 260, 330, 250)
    heads = ("Contrast", "Gemini", "Claude", "Difference", "95% interval", "Holm p")
    x = 120
    for hd, w in zip(heads, cws):
        text(s, x, y, w, 30, [run(hd, NT, MID, SANS, True)])
        x += w
    y += 34
    hline(s, 120, y, 120 + sum(cws), y, LINE)
    for m, name in G_MODELS:
        for L in ("L2", "L3"):
            h = fam[f"{m}|{L}"]
            vals = (f"Gemini minus {name} · {L}", f"{num(100 * h['gemini'], 1)}%", f"{num(100 * h['other'], 1)}%",
                    gpts(h["diff"]), gint(h["lo"], h["hi"]), num(h["p_holm"], 4))
            x = 120
            for j, (v, w) in enumerate(zip(vals, cws)):
                text(s, x, y + 6, w - 8, 38, [run(v, 28, INK, SANS if j == 0 else MONO, j == 0)], line=1.2)
                x += w
            y += 48
            hline(s, 120, y, 120 + sum(cws), y, RULE)
    y = box(s, 120, y + 14, 1680, "The registered sentence:", f"“{g['wording'][0]}”", B)
    Nq(s, 120, y + 8, 1680,
       f"October's lead on {slots['common']['anchor_rows']} rows repeated on {g['rows']} new ones. Not the paper's "
       "model. Gemini ran the author's loop and Claude our port of it, so this compares model and loop together. "
       "At L3 against Opus the interval reaches below zero: the lead is found under the registered one-sided test "
       "(Holm p " + num(fam["claude-opus-5-5|L3"]["p_holm"], 3) + "). Saved inputs from two homes; no robot acted "
       "on these guesses.", limit=1010)


def gemini_rule_slide(prs, slots):
    g = gemini_facts(slots)
    r3, r2, fam = g["rule"]["L3"], g["rule"]["L2"]["comparators"], g["family"]
    s = frame(prs, 20, "Part 3 · Is it the model? · registered rule at L3",
              "At L3 Gemini 3.8 Flash is above Claude, but not above a trade of regions", pending="registered")
    y = lab(s, 120, 244, 1680, "Gemini's own L3 score beside its three controls · rule of registration §10")
    cws = (700, 260, 250, 470)
    x = 120
    for hd, w in zip(("Control", "Its score", "Gemini", "Gemini minus control"), cws):
        text(s, x, y - 4, w, 30, [run(hd, NT, MID, SANS, True)])
        x += w
    y += 32
    hline(s, 120, y, 120 + sum(cws), y, LINE)
    names = {"B5": "Own labels, swapped among guesses", "D": "Regions, trading contents (named)",
             "B3L": "Prior's labels at its places"}
    for c in ("B5", "D", "B3L"):
        d = r3["comparators"][c]
        vals = (names[c], f"{num(100 * d['own'], 1)}%", f"{num(100 * r3['own'], 1)}%",
                f"{gpts(d['diff'])} {gint(d['lo'], d['hi'])}")
        x = 120
        for j, (v, w) in enumerate(zip(vals, cws)):
            text(s, x, y + 6, w - 8, 38, [run(v, 28, INK, SANS if j == 0 else MONO, c == "D" and j == 0)], line=1.2)
            x += w
        y += 48
        hline(s, 120, y, 120 + sum(cws), y, RULE)
    y = box(s, 120, y + 12, 1680, f"Registered rule at L3: {r3['verdict']}.",
            f"“{g['wording'][5]}” "
            f"Against the trade the upper end is {gpts(r3['upper_named'])} points; the margin is "
            f"{num(100 * r3['delta'], 0)}.", NQ)
    y = P(s, 120, y + 14, 1680, [("Both hold. ", "b"),
                                 (f"Gemini reaches fitting regions more often than Claude does ("
                                  f"{num(100 * r3['own'], 1)}% against {num(100 * fam['claude-opus-5-5|L3']['other'], 1)}% "
                                  f"and {num(100 * fam['claude-haiku-5-5|L3']['other'], 1)}%), yet no more often than a "
                                  f"trade of regions gives for its own guesses ({num(100 * r3['comparators']['D']['own'], 1)}%). "
                                  "So its lead is in the raw rate only; it does not show that its labels fit their "
                                  "regions. Against Opus the 95% interval includes zero.", "n")], B, BODY, 1.25)
    wh = g["wrong_house"]
    y = P(s, 120, y + 10, 1680, [("Exploratory. ", "a"),
                                 (f"At L2 Gemini scores {num(100 * g['rule']['L2']['own'], 1)}%. The prior, making as many "
                                  f"claims, scores about {num(100 * abs(r2['B3']['diff']), 0)} points above it "
                                  f"({num(100 * r2['B3']['own'], 1)}%; {gpts(r2['B3']['diff'])} {gint(r2['B3']['lo'], r2['B3']['hi'])}), "
                                  f"and it is above random guesses ({num(100 * r2['B1']['own'], 1)}%; {gpts(r2['B1']['diff'])} "
                                  f"{gint(r2['B1']['lo'], r2['B1']['hi'])}). It passes the wrong-house check at L1 "
                                  f"(p {num(wh['L1']['p'], 3)}) and L2 (p {num(wh['L2']['p'], 3)}), {wh['L1']['n_pairs']} "
                                  "pairs.", "n")], NQ, BODY, 1.3)
    Nq(s, 120, y + 6, 1680, "Gemini also made more guesses per member; 5a does not adjust for that. Same limits as "
                            "slide 19. At L1 and L2 the prior sits at the ceiling.", limit=1010)


# ---------------------------------------------------------------- 20. Part 3, the paper's room test

def room_slide(prs, slots):
    rr, rf, pp = slots["room_runs"], slots["rooms_fit"], slots["room_test"]["paper"]
    e, a = rr["eight_member_stages"], rr["all_stages"]
    for v in (e, a):
        if v["pooled"]["official"]["rate"] <= v["pooled"]["placebo"]["rate"]:
            fail("slide 21 says DeepSeek's room rate is above random guesses' on both counts, but it is not")
    pe, pa = e["tests"]["official_vs_placebo"]["p"], a["tests"]["official_vs_placebo"]["p"]
    fe, fa = e["tests"]["filter_only_vs_placebo"], a["tests"]["filter_only_vs_placebo"]
    if not (pe > 0.05 > pa):
        fail(f"slide 21 and the script say p is above 0.05 on the 8-member count of registration section 11 ({pe}) and "
             f"below it on all stages ({pa}), but they do not read so")
    if min(fe["p"], fa["p"]) <= 0.05 or fe["observed_diff"] >= 0.05 or fa["observed_diff"] >= 0.05:
        fail("slide 21 says the filter arm is not ahead of random guesses (p above 0.05 on both counts), but it reads "
             "otherwise")
    if not (rf["lo"] > 0):
        fail("slide 21 says Opus places rooms in fitting regions above random guesses, but its interval reaches 0")
    s = frame(prs, 21, "Part 3 · The paper's room test · exploratory",
              f"Paper's room test: ahead of random guesses; p is {num(pe, 3)} on the §11 count")
    X, cws = 120, (460, 330, 330, 330, 230)
    heads = ("Count", f"DeepSeek ({e['pooled']['official']['runs']} runs)",
             f"+ filter ({e['pooled']['filter_only']['runs']} runs)", f"Random ({e['pooled']['placebo']['runs']} runs)",
             "p v random")
    x = X
    for hd, w in zip(heads, cws):
        text(s, x, 246, w, 34, [run(hd, NT, MID, SANS, True)])
        x += w
    hline(s, X, 286, X + sum(cws), 286, LINE)
    y = 292
    for name, sub, v in (("8-member stages", "the rule of registration §11", e), ("All stages", "", a)):
        text(s, X, y + 6, cws[0] - 10, 40, [run(name, 28, INK, SANS, True)], line=1.2)
        if sub:
            text(s, X, y + 42, cws[0] - 10, 30, [run(sub, NT, MID)], line=1.2)
        x = X + cws[0]
        for arm in ("official", "filter_only", "placebo"):
            d = v["pooled"][arm]
            text(s, x, y + 16, cws[1] - 10, 40, [run(f"{d['predicted']} of {d['of']} · {num(100 * d['rate'], 1)}%", 28,
                                                  INK, MONO)], line=1.2)
            x += cws[1]
        t = v["tests"]
        text(s, x, y + 16, cws[4], 40, [run(f"{num(t['official_vs_placebo']['p'], 3)} · "
                                            f"{num(t['filter_only_vs_placebo']['p'], 3)}", 28, INK, MONO)], line=1.2)
        y += 80
        hline(s, X, y, X + sum(cws), y, RULE)
    lo8, hi8 = e["official_stages_8"]
    n_lo, n_hi = e["official_stages"]
    y = P(s, X, y + 22, 1680, [("Caution. ", "b"), (f"DeepSeek's runs hold {lo8} to {hi8} stages with 8 members, out of "
                                                   f"{n_lo} to {n_hi}; the random runs hold all theirs. Under the "
                                                   "8-member rule the arms do not have equal chances.", "n")],
          B, BODY, 1.3)
    y = P(s, X, y + 8, 1680, [("Filter arm. ", "b"),
                              ("Also built from DeepSeek's guesses, it is not ahead of random guesses: "
                               f"{sg(100 * fe['observed_diff'], 1)} points on 8-member stages (p {num(fe['p'], 3)}), "
                               f"{sg(100 * fa['observed_diff'], 1)} on all stages (p {num(fa['p'], 3)}).", "n")],
          B, BODY, 1.3)
    y = P(s, X, y + 8, 1680, [("Opus, replayed. ", "b"),
                               (f"Rooms placed in a fitting unobserved region: {num(100 * rf['model'], 1)}% against "
                                f"{num(100 * rf['placebo'], 1)}% for random guesses, {sg(100 * rf['diff'], 1)} points "
                                f"({sg(100 * rf['lo'], 1)} to {sg(100 * rf['hi'], 1)}), p {num(rf['p'], 3)}; one "
                                "contrast, not adjusted.", "n")], B, BODY, 1.3)
    y = P(s, X, y + 8, 1680, [("The paper ", "b"),
                               (f"reports {pp['hit']} of {pp['of']} rooms ({num(100 * pp['hit'] / pp['of'], 0)}%) with "
                                "no chance rate. Random guesses give one.", "n")], B, BODY, 1.3)
    nrel = e["tests"]["official_vs_placebo"]["relabelings"]
    N(s, X, y + 6, 1680,
      f"Exploratory. The unit is the run. A room counts if at least 2 of 8 members place one of its type within 2.5 m "
      f"before the region is seen. p: exact permutation of arm labels within a scene, {nrel} relabelings; DeepSeek, "
      f"then the filter arm.", limit=1012)


# ---------------------------------------------------------------- 21. Part 3, M2

def factorial(prs, slots):
    m = slots["m2"]
    rho, dif = m["rho"], m["diff"]
    at = slots["all_true"]
    if at["F0_above_cap"] or at["F6_above_cap"]:
        fail("slide 22 and backup 5 say the all-true arm's gain never passes 2.0, like the no-guess arm's, but one does")
    if not all(dif[d]["lo"] < 0 for d in ("B_deepseek", "B_haiku", "B_opus")):
        fail("slide 22's title says moved true objects show no detectable gain over random guesses, but one does")
    s = frame(prs, 22, "Part 3 · M2 · offline, provisional yardstick",
              "M2 varied place, not meaning: moved true objects show no detectable gain")
    R, W = 120, 1680
    lab(s, R, 244, W, "Spearman rho: ASP's view score vs unmapped objects in view (the yardstick)")
    x0, x1, lo, hi = R + 560, R + 1400, -0.1, 0.35

    def dx(v):
        return x0 + (min(max(v, lo), hi) - lo) / (hi - lo) * (x1 - x0)

    rows = [("True objects", rho["F1"]), ("Room type only", rho["F-room"]),
            ("Moved: DeepSeek (expl.)", rho["F3-deepseek"]), ("Moved: Haiku", rho["F3-haiku"]),
            ("Moved: Opus", rho["F3-opus"]), ("Random guesses", rho["F5"]), ("No guesses", rho["F6"]),
            ("All true objects", rho["F0"])]
    top, step = 296, 42
    for v in (0.0, 0.1, 0.2, 0.3):
        hline(s, dx(v), top - 14, dx(v), top + step * len(rows) - 18, MID if v == 0 else LINE, 2 if v == 0 else 1,
              dash=bool(v))
        svg_text(s, dx(v), top + step * len(rows) + 8, num(v, 1), NT, FAINT, anchor="middle", w=80)
    for i, (name, d) in enumerate(rows):
        yy = top + i * step + 12
        text(s, R, yy - 18, 530, 36, [run(name, 28, BODY)], line=1.2)
        hline(s, dx(d["lo"]), yy, dx(d["hi"]), yy, INK, 3)
        oval(s, dx(d["mean"]), yy, 10, INK, WHITE, 3)
        svg_text(s, x1 + 40, yy + 8, sg(d["mean"], 3), NT, INK, MONO, w=120)
    A = dif["A"]
    y = P(s, R, top + step * len(rows) + 44, W,
          f"True objects beat random guesses by {num(A['mean'], 3)}. Enough: keep half of that, "
          f"{num(A['mean'] / 2, 3)}. No arm does. Not shown sufficient; yardstick provisional.",
          B, BODY, 1.35, limit=900)
    box(s, R, y + 12, W, "All true objects (exploratory):",
        f"every member holds every true object, so the score reads mainly where the two observed maps disagree. This "
        f"arm's gain never passes {num(at['bits_cap'], 1)} bits, like the no-guess arm's, where other arms reach "
        f"{num(at['F3_max_lo'], 2)} to {num(at['F5_max'], 1)}; the two correlate at "
        f"{num(at['spearman_mean'], 2)} ({at['spearman_stages']} stages).", NQ)


# ---------------------------------------------------------------- 21. Limits of scope

def limits(prs, slots):
    s = frame(prs, 23, "Limits", "What this talk cannot show")
    items = [("Two houses.", "Every result holds for 853 and 871 only, not other houses."),
             ("A small model in Part 1.", "The live arm is DeepSeek V4.1 Flash at low reasoning effort. The paper "
                                          f"(§IV) says “{PINNED['paper']['small_model']}”. Part 1's null is a "
                                          "result about ASP with a cheap model."),
             ("Proxy truth.", "Human labels stand in for what the camera saw."),
             ("Static replays.", "Claude and Gemini saw saved inputs; no robot acted on their guesses."),
             ("One more model.", "Another Gemini model is registered (Note 3, after the Flash result was seen) and "
                                 "running. No result of it exists."),
             ("Not the paper's model.", "The paper used Gemini 2.5 Pro, no longer offered to new users (11-19, "
                                        "Note 1). We ran Claude in our port of the author's loop and Gemini 3.8 Flash "
                                        "in the author's own, so that contrast has two differences.")]
    y = 250
    for head, body in items:
        y = P(s, 120, y, 1680, [(head + " ", "b"), (body, "n")], B, BODY, 1.35, limit=1000) + 18


# ---------------------------------------------------------------- 22. Limits of method

def limits_method(prs, slots):
    m = slots["blind"]["members"]
    s = frame(prs, 24, "Limits", "How the test was made")
    items = ["We wrote the scorer after we saw DeepSeek's numbers.",
             "We set the L3 margin knowing the Gemini–DeepSeek gap.",
             "We did not check what the comparators themselves score before freezing the test.",
             "M2 is provisional: its yardstick failed part of an October check.",
             f"One Haiku member stopped at the token limit and its text did not parse "
             f"({m['haiku']['parsed']} of {m['haiku']['members']} did)."]
    y = 256
    for t in items:
        y = P(s, 120, y, 1680, t, B, BODY, 1.4, limit=1000) + 26


# ---------------------------------------------------------------- 23. The answer

def answer(prs, slots):
    ce, b = slots["ceiling"], slots["blind"]["models"]
    s = frame(prs, 25, "Answer", "For Claude, in our port, on saved inputs: no detectable gain over base rates")
    y = P(s, 120, 252, 1680, [("In two houses, Claude's guesses carried no detectable information beyond house base "
                               "rates, and put content in fitting regions not detectably more often than a "
                               "trade of regions (gains under 3 points not ruled out).", "b")], 40, INK, 1.2)
    y = P(s, 120, y + 18, 1680, f"Both models scored far below the other-house prior at naming objects. At L3 a gain "
                                f"under {num(100 * b['opus']['L3']['margin'], 0)} points is not ruled out. M2, "
                                "offline: true objects moved by a model's error showed no detectable gain.",
          B, BODY, 1.4)
    y = P(s, 120, y + 18, 1680, [("The registered line, second: ", "b"),
                                 (f"“{slots['thesis']}”, for the first half of the claim as the author put it to us "
                                  "(that the guesses are right in meaning). It says less than it seems to: at L1 no "
                                  "model could have been Supported, and at L2 only a perfect Opus, so it rests on L3, "
                                  "where Opus's interval "
                                  f"ends at {num(100 * b['opus']['L3']['hi'], 2)} against a margin of "
                                  f"{num(100 * b['opus']['L3']['margin'], 0)}.", "n")], B, BODY, 1.4)
    box(s, 120, y + 24, 1680, "Not the paper's model:",
        "Claude, in our port of the author's loop. In the author's loop Gemini 3.8 Flash scored above Claude at L2 and "
        "L3, and not above a trade of regions at L3 (registered). The Claude result does not carry over.")


# ---------------------------------------------------------------- 24. What the answer does not say

def not_shown(prs, slots):
    hh = slots["blind"]["models"]["haiku"]["L2"]["placebo"]
    s = frame(prs, 26, "The answer", "What the answer does not say")
    mg = num(100 * slots["blind"]["models"]["opus"]["L3"]["margin"], 0)
    items = [f"It does not say the guesses carry nothing: it says no gain was found. At L3 a gain under {mg} points "
             "is not ruled out, and the prior's near-perfect score left little room for a gain at L1 and L2.",
             f"It does not say the models are no better than random guesses: Haiku is "
             f"{num(100 * hh['diff'], 1)} points above at L2 (one contrast, not adjusted).",
             "It does not carry over to Gemini 3.8 Flash: in the author's loop it scored above Claude at L2 and L3 "
             "(registered). That is not the paper's model, and the two loops differ.",
             "It does not say the guesses reach the map, or where they sit. It says nothing about live runs with a "
             "strong model, or the paper's scale.",
             "It does not show that a language model cannot help exploration."]
    y = 256
    for t in items:
        y = P(s, 120, y, 1680, t, B, BODY, 1.4, limit=1000) + 26


# ---------------------------------------------------------------- Backup 1. The paper's room test

def room_test(prs, slots):
    rt, h = slots["room_test"], slots["hint"]
    s = frame(prs, 28, "Backup · The paper's room test",
              "The paper's room test: other counts, Claude replays, prompt hint", backup=True)
    X = 120
    lv = rt["live"]
    y = P(s, X, 262, 1680, [("DeepSeek's live runs, other counts (slide 21 has the main two): ", "b"),
                            (f"with no type match, {lv['llm']['untyped_all']} of {lv['llm']['of']} rooms on all stages "
                             f"and {lv['llm']['untyped_8']} on 8-member stages, against {lv['placebo']['untyped_all']} "
                             f"and {lv['placebo']['untyped_8']} of {lv['placebo']['of']} for random guesses; with our "
                             f"filter, type matched, {lv['filter']['typed_all']} of {lv['filter']['of']} on all stages "
                             f"and {lv['filter']['typed_8']} on 8-member stages. Exploratory.", "n")], B, BODY, 1.3)
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
    s = frame(prs, 29, "Backup · Our filter and vote", "Do the filter and the vote keep right guesses?",
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
    z, at = m["f0_ig_zero"], slots["all_true"]
    if at["F0_above_cap"] or at["F6_above_cap"]:
        fail("backup 5 says the all-true arm's gain never passes 2.0, like the no-guess arm's, but one does")
    s = frame(prs, 30, "Backup · A likely question", "Why does ASP not gain from all true objects?",
              backup=True)
    y = P(s, 120, 256, 1680, "If every member holds every true object, why does ASP's score not rise?", B, INK, 1.4)
    y = P(s, 120, y + 24, 1680, [("What we found: ", "b"),
                                 (f"all true objects for every member scored {sg(d['mean'])} "
                                  f"({sg(d['lo'])} to {sg(d['hi'])}) against random guesses. True objects in "
                                  f"differing subsets scored {sg(a['mean'])} above them.", "n")], B, BODY, 1.4)
    y = P(s, 120, y + 24, 1680, [("Why it should not rise: ", "b"),
                                 ("the score counts disagreement between members. We registered that before the "
                                  "run (M2, section 7).", "n")], B, BODY, 1.4)
    P(s, 120, y + 24, 1680, [("What the saved arrays show (exploratory): ", "b"),
                             (f"with identical members the score reads mainly where the two observed maps disagree. "
                              f"This arm's gain never passes {num(at['bits_cap'], 1)} bits over {z['of']} stages, like "
                              f"the no-guess arm's, where other arms reach {num(at['F3_max_lo'], 2)} to "
                              f"{num(at['F5_max'], 1)}. The two correlate at {num(at['spearman_mean'], 2)} "
                              f"({at['spearman_stages']} stages). The gain is zero for every candidate in only "
                              f"{z['stages']} of {z['of']} stages.", "n")], B, BODY, 1.4, limit=990)


# ---------------------------------------------------------------- Backup 4. The four outcomes

def outcomes(prs, slots):
    h = slots["blind"]["models"]
    s = frame(prs, 31, "Backup · The four outcomes", "The four outcomes, and the rule that picked one",
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


def script_times():
    """The times in the slide headings of ENDSEM_Script.md: one per main slide, and they must add to 900 s."""
    md = open(SCRIPT).read()
    ts = [int(t) for t in re.findall(r"^## Slide \d+:.*\(about (\d+) s\)$", md, flags=re.M)]
    if len(ts) != TOTAL:
        fail(f"ENDSEM_Script.md has {len(ts)} timed main slides, not {TOTAL}")
    if sum(ts) != 900:
        fail(f"the times in ENDSEM_Script.md add to {sum(ts)} s, not 900")
    nback = len(re.findall(r"^## Backup \d+:", md, flags=re.M))
    if nback != BACKUPS:
        fail(f"ENDSEM_Script.md has {nback} backup sections, not {BACKUPS}")


def main():
    Nn = numbers()
    slots = json.load(open(SLOTS))
    PINNED.update(slots["pinned"])
    C, budgets = paper_cells(slots)
    BUDGETS_NOW.update(budgets)
    checks = json.load(open(CHECKS))
    c2d = {sc: c2_data(sc) for sc in ("00853", "00871")}
    c2, frozen = {sc: v[0] for sc, v in c2d.items()}, {sc: v[1] for sc, v in c2d.items()}
    bf = budget_runs()
    C08 = paper_cells(slots, "0.8B")[0]
    ep, bs = read_equal_path(), read_sensitivity()
    f9, f853 = facts871(C, C08), facts853(C, slots)
    f853["equal"] = facts_equal853(ep)
    f9["sens"] = facts_sens871(bs, ep, C)
    f853["pc871"] = {arm: num(ecell(ep, "00871", "apr", arm, 50)["mean"])
                     for arm in ("oracle_visible", "official", "frontier_end", "placebo", "frontier_60m")}
    f853["eqm"] = {(ref, Lm, arm): num(ecell(ep, "00853", ref, arm, Lm)["mean"])
                   for ref in ("apr", "hm3d") for Lm in (50, 100) for arm in ("official_nov", "frontier_end")}
    blind_facts(slots)
    script_times()
    check_text(C, f9, f853, budgets, slots, Nn)
    prs = Presentation()
    prs.slide_width, prs.slide_height = px(1920), px(1080)
    cover(prs, f853)
    proposal(prs, Nn, slots)
    asp_picture(prs)
    live_test(prs, Nn)
    why(prs, Nn)
    land(prs, Nn)
    live_limits(prs, Nn)
    paper_rules(prs, budgets, checks, bf)
    table853(prs, C, budgets, slots, f853, ep)
    table871(prs, C, budgets, slots, f9, bs, ep)
    limits_reference(prs, checks, c2, frozen)
    limits_runs(prs, C, budgets, slots, f853)
    defense(prs)
    picture_levels(prs, slots)
    controls(prs, slots)
    blind_table(prs, slots)
    facts(prs, slots)
    detect(prs, slots)
    gemini_slide(prs, slots)
    gemini_rule_slide(prs, slots)
    room_slide(prs, slots)
    factorial(prs, slots)
    limits(prs, slots)
    limits_method(prs, slots)
    answer(prs, slots)
    not_shown(prs, slots)
    wrong_house(prs, slots)
    placement_slide(prs, slots)
    room_test(prs, slots)
    validity(prs, slots)
    f0_slide(prs, slots)
    outcomes(prs, slots)
    assert len(prs.slides) == TOTAL + BACKUPS, len(prs.slides)
    notes = speaker_notes()
    assert len(notes) == TOTAL + BACKUPS, len(notes)
    for slide, n in zip(prs.slides, notes):
        slide.notes_slide.notes_text_frame.text = n
    prs.core_properties.title = "Right in meaning, wrong in place?"
    prs.core_properties.author = "ASP replication, end-sem"
    prs.core_properties.last_modified_by = "ASP replication, end-sem"
    prs.save(OUT)
    print(OUT, len(prs.slides), "slides (", TOTAL, "main +", BACKUPS, "backup )")
    for w in WARN:
        print("FIT WARNING:", w)


if __name__ == "__main__":
    main()
