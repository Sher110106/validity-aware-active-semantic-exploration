"""Build ASP_Checkin2.pptx: check-in 2 before end-sem, in the style of ../checkin/ASP_Checkin.pptx,
with the speaker script as notes. Chart values are read from the result files, never typed in.

Usage: uv run --with python-pptx --with pyyaml python build_checkin2_pptx.py
"""
import csv
import json
import os
import re
import sys

from pptx import Presentation
from pptx.enum.text import PP_ALIGN

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PROJECT, "docs", "checkin"))
from build_checkin_pptx import (BODY, FAINT, INK, LIGHT, LINE, MID, MONO, RULE, SANS, WHITE,  # noqa: E402
                                callout, hline, kick, label, note, oval, px, rect, run, stat, svg_text, text)

OUT = os.path.join(HERE, "ASP_Checkin2.pptx")
SCRIPT = os.path.join(HERE, "ASP_Checkin2_Script.md")
NUMBERS = os.path.join(PROJECT, "tools", "live_policy", "results_2026-10-31", "numbers.csv")
PAPER_JSON = os.path.join(PROJECT, "tools", "live_policy", "results_paper_compare_1112", "paper_compare.json")
CHECKS = os.path.join(PROJECT, "tools", "live_policy", "results_paper_compare_1112", "c_checks.json")
TOTAL = 5


def numbers():
    with open(NUMBERS, newline="") as f:
        return {row["key"]: float(row["value"]) for row in csv.DictReader(f) if _num(row["value"])}


def _num(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def cells():
    d = json.load(open(PAPER_JSON))
    out = {}
    for c in d["cells"]:
        if c["reference"] == "apr" and c["variant"] == "B":
            out[(c["scene"], c["arm"], c["fraction"])] = c
    return out, d["meta"]["budgets"]


def frame(prs, n, k, title):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    text(s, 120, 84, 1680, 30, [kick(k)])
    text(s, 120, 123, 1680, 74, [run(title, 56, INK, LIGHT, spacing=-0.02)], line=1.15)
    hline(s, 120, 222, 1800, 222, RULE)
    text(s, 120, 1010, 1200, 28, [run("Right in meaning, wrong in place? · Check-in 2", 20, FAINT)])
    text(s, 1500, 1010, 300, 28, [run(f"{n:02d} / {TOTAL}", 20, FAINT)], PP_ALIGN.RIGHT)
    return s


# ---------------------------------------------------------------- 1. Cover

def cover(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    text(s, 160, 140, 1600, 30, [kick("Check-in 2 before end-sem · Computer vision and perception")])
    text(s, 160, 205, 1600, 250, [run("Right in meaning,", 112, INK, LIGHT, spacing=-0.03),
                                  run("wrong in place?", 112, INK, LIGHT, spacing=-0.03)], line=1.05)
    text(s, 160, 470, 1500, 150, [run(
        "ASP asks a language model to guess the rooms and objects a robot has not yet seen, then drives "
        "to where the guesses disagree. Its author says the guesses are often in the wrong place but name "
        "the right things, and that this is enough. We test that claim.", 30, BODY)], line=1.5)
    cols = [("Last check-in", "Does a better guesser make a better explorer? Finish the live test, screen "
                              "models, re-test our filter."),
            ("Since then", "The live test finished. We rebuilt the paper's reference and scored every run "
                           "with the author's own code."),
            ("End-sem", "A pre-registered test of the author's defense, with ASP scored on the paper's "
                        "own scale.")]
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


# ---------------------------------------------------------------- 2. The live test

def live_test(prs, N):
    s = frame(prs, 2, "01 · The live test, finished · 2 homes, seeds 42-44, human labels",
              "Live, no gain over random guesses that we could detect")
    L, W = 120, 1060
    label(s, L, 262, W, "Difference in mapping quality (F1 area to 60 m), with its 95% interval")
    # E2 is registered as official − filter_only; the slide shows filter − LLM, so its sign flips.
    e2 = (-N["E2:hm3d:60m:statistic"], -N["E2:hm3d:60m:permutation_hi"], -N["E2:hm3d:60m:permutation_lo"])
    rows = [("LLM guesses vs random guesses", (N["E1:hm3d:60m:statistic"], N["E1:hm3d:60m:permutation_lo"],
                                                N["E1:hm3d:60m:permutation_hi"])),
            ("LLM + our filter vs LLM", e2),
            ("LLM vs frontier, no LLM", (N["frontier_seeds:official:d60"], N["frontier_seeds:official:ci60_lo"],
                                         N["frontier_seeds:official:ci60_hi"])),
            ("Random guesses vs frontier", (N["frontier_seeds:placebo:d60"], N["frontier_seeds:placebo:ci60_lo"],
                                            N["frontier_seeds:placebo:ci60_hi"])),
            ("Exact objects vs random (871)", (N["E3:hm3d:60m:statistic"], None, None))]
    x0, x1, lo, hi = L + 470, L + W - 20, -0.08, 0.10

    def dx(v):
        return x0 + (min(max(v, lo), hi) - lo) / (hi - lo) * (x1 - x0)

    top, step = 330, 88
    for v in (-0.05, 0.0, 0.05):
        hline(s, dx(v), top - 20, dx(v), top + step * len(rows) - 30, LINE if v else MID, 1 if v else 2,
              dash=bool(v))
        svg_text(s, dx(v), top + step * len(rows) + 6, f"{v:+.2f}" if v else "0", 20, FAINT, anchor="middle",
                 w=100)
    for i, (name, (d, a, b)) in enumerate(rows):
        y = top + i * step + 18
        text(s, L, y - 22, 450, 40, [run(name, 24, INK)], line=1.3)
        if a is None:  # unbounded at 3 v 3: draw to both edges with arrow heads
            hline(s, dx(lo), y, dx(hi), y, INK, 3, dash=True)
            svg_text(s, dx(lo) - 2, y + 9, "◀", 22, INK, anchor="end", w=30)
            svg_text(s, dx(hi) + 2, y + 9, "▶", 22, INK, w=30)
        else:
            hline(s, dx(a), y, dx(b), y, INK, 3)
        oval(s, dx(d), y, 11, INK, WHITE, 3)
        svg_text(s, x1 + 34, y + 8, f"{d:+.3f}", 22, INK, MONO, w=110)
    note(s, L, top + step * len(rows) + 40, W, 3,
         "Registered tests, pilot status. Each interval crosses zero. Exact objects: 871 only, 3 runs v 3; all "
         "3 beat all 3 random runs, but p 0.10 is the floor and the interval is unbounded. The LLM arm has 2 "
         "runs on 853. A secondary test, F1 at 60 m, favoured the LLM (+0.043, p 0.015; 0.09 after correction).")

    R = 1300
    label(s, R, 262, 500, "Where the LLM puts new objects")
    stat(s, R, 310, 230, f"{100 * N['precision_pooled:official:final:0.5m']:.1f}%", "LLM guesses", 2)
    stat(s, R + 270, 310, 230, f"{100 * N['precision_pooled:placebo:final:0.5m']:.1f}%", "random guesses", 2)
    far = 100 * (1 - N["precision_pooled:official:final:2m"])
    note(s, R, 470, 500, 4, "New objects within 0.5 m of a real object with the same name, all counted live "
                            f"runs (not tested). {far:.0f}% of the LLM's are more than 2 m off.")
    note(s, R, 610, 500, 3, "Correction: last time we showed 1.7% vs 1.5%; on the 8 matched saved inputs it "
                            "is 2.1% vs 1.4%.")
    callout(s, R, 740, 500, 200, "Reading.", "The LLM lands near a real object 6× as often as random guesses, "
                                             "but 97% miss by over 0.5 m, and we could not detect a better map.", 23)


# ---------------------------------------------------------------- 3. The paper's scale

def paper_scale(prs, C, budgets, checks):
    s = frame(prs, 3, "02 · Same rules as the paper", "On the paper's scale, his 853 ASP lead does not appear")
    L = 120
    rec = [checks[sc]["C3"]["apr_a_recall_vs_hm3d"] for sc in ("00853", "00871")]
    label(s, L, 262, 520, "Now as in the paper")
    blocks = [("Scoring", "the author's own F1 and GED code, on his time axis."),
              ("Reference", "his protocol, scripted: a tour of every reachable point on the start floor, same "
                            f"mapper (85 and 66 stops). It holds {100 * rec[0]:.0f}% and {100 * rec[1]:.0f}% of "
                            "the human-labelled objects; its repeat tour failed."),
              ("Frontier", "run to its natural end: 5 of 5 runs on 853, 1 of 5 on 871.")]
    y = 300
    for head, body, hgt in [(b[0], b[1], h) for b, h in zip(blocks, (72, 152, 70))]:
        text(s, L, y, 520, hgt, [[run(head + ". ", 22, INK, SANS, True), run(body, 22, BODY)]], line=1.4)
        y += hgt
    label(s, L, y + 10, 520, "Where we differ")
    text(s, L, y + 46, 520, 110, [[run("Budget. ", 22, INK, SANS, True),
                                    run(f"the paper gives none; we use our frontier's median end, "
                                        f"{budgets['00853']:.0f} s (853), and the registered fallback, "
                                        f"{budgets['00871']:.0f} s (871).", 22, BODY)]], line=1.4)
    text(s, L, y + 156, 520, 40, [[run("LLM. ", 22, INK, SANS, True),
                                    run("ours DeepSeek, his Gemini 2.5 Pro.", 22, BODY)]], line=1.4)
    note(s, L, y + 214, 520, 3, "871: 4 frontier runs crashed twice when another user's server took the GPU. "
                                "A third try waits for a free GPU.")

    R = 700
    label(s, R, 262, 1100, "Object F1 × 100 at 10, 50 and 100% of the budget")
    series = [("paper_frontier", "Paper, frontier"), ("paper_asp", "Paper, ASP"),
              ("frontier_end", "Ours, frontier"), ("official", "Ours, ASP"), ("placebo", "Ours, random guesses")]
    legend_x = [R, R + 200, R + 375, R + 570, R + 755, R + 1100]
    for (key, name), lx, nx in zip(series, legend_x, legend_x[1:]):
        mark(s, key, lx + 9, 318, 9)
        text(s, lx + 26, 304, nx - lx - 30, 30, [run(name, 20, MID)], line=1.5)
    T, H, ymax = 400, 340, 75.0

    def by(v):
        return T + H - v / ymax * H

    panel_w = 520
    for p, scene in enumerate(("00853", "00871")):
        x0 = R + 30 + p * (panel_w + 50)
        svg_text(s, x0 + 40, T - 22, f"Home {scene[2:]}", 24, INK, bold=True, w=300)
        for v in (0, 25, 50, 75):
            hline(s, x0 + 40, by(v), x0 + panel_w, by(v), RULE if v else MID)
            if p == 0:
                svg_text(s, x0 + 28, by(v) + 7, f"{v}", 20, FAINT, anchor="end", w=60)
        for g, frac in enumerate(("10", "50", "100")):
            gx = x0 + 40 + (g + 0.5) * (panel_w - 40) / 3
            svg_text(s, gx, T + H + 36, f"{frac}%", 22, BODY, anchor="middle", w=100)
            fr = C[(scene, "frontier_end", frac)]
            for j, (key, _) in enumerate(series):
                xx = gx + (j - 2) * 26
                if key.startswith("paper"):
                    v = fr["paper_f1_x100"] if key == "paper_frontier" else C[(scene, "official", frac)]["paper_f1_x100"]
                    mark(s, key, xx, by(v), 9)
                    continue
                c = C.get((scene, key, frac))
                if not c:
                    continue
                sv = c["stage_value_x100"]
                if not sv["n"] or sv["n"] * 2 < c["n_runs"]:
                    continue
                if sv["max"] > sv["min"]:
                    hline(s, xx, by(sv["max"]), xx, by(sv["min"]), MID, 2)
                mark(s, key, xx, by(sv["mean"]), 9)
    note(s, R, T + H + 52, 1100, 3,
         "Hollow: the paper's single run against its own reference (Fig. 4 left). Filled: our mean against the "
         "rebuilt reference, bars the range; shown where at least half the runs reach that time (our rule). "
         "853 at 100%: 3 of 5 runs. Our ASP runs stop at 60 m and ran in October; frontier ran in November.")
    a, f, r = (C[("00853", k, "50")]["stage_value_x100"]["mean"] for k in ("official", "frontier_end", "placebo"))
    callout(s, R, 900, 1100, 92, "Reading.",
            f"Our frontier ends within about 3 points of his. On 853 his ASP leads frontier by 14 points at 50%; "
            f"our 2 ASP runs are level ({a:.1f} vs {f:.1f}), and random guesses score {r:.1f}.", 22)


def mark(s, key, x, y, r):
    if key == "paper_frontier":
        oval(s, x, y, r, WHITE, INK, 3)
    elif key == "paper_asp":
        rect(s, x - r, y - r, 2 * r, 2 * r, WHITE, INK, 3)
    elif key == "frontier_end":
        oval(s, x, y, r, INK)
    elif key == "official":
        rect(s, x - r, y - r, 2 * r, 2 * r, INK)
    else:
        oval(s, x, y, r, FAINT)


# ---------------------------------------------------------------- 4. The next questions

def questions(prs):
    s = frame(prs, 4, "03 · The author's defense, tested cheapest first",
              "Next: is the meaning right, and would it be enough?")
    steps = [("Right beyond base rates?",
              "Do the rooms and objects named really lie in unexplored space? Compare with controls that see "
              "the same map: house statistics, another house, shuffled guesses.",
              "The prompt says a scene “may contain more than one bedroom”, so naming one proves little."),
             ("Would it be enough?",
              "Offline, give ASP exact labels with the placement error real models make, and see how much of "
              "the oracle's ranking power survives.",
              "ASP rewards disagreement between guesses, so guesses that all agree add nothing to its view score."),
             ("Is it the model?",
              "Replay Claude on the same 44 saved inputs as DeepSeek, so a gap points to the model, not the "
              "inputs.",
              "About $320 expected, capped at $460; we ask before spending."),
             ("Our validity layer, same pass",
              "For every model: what the filter removes, and whether what it keeps is right more often.",
              "Live, the filter made no difference we could detect (−0.003).")]
    for i, (name, what, why) in enumerate(steps):
        x = 120 + i * 430
        hline(s, x, 262, x + 390, 262, INK, 2)
        text(s, x, 282, 390, 30, [run(f"{i + 1:02d}", 20, FAINT, MONO)], line=1.5)
        text(s, x, 324, 390, 90, [run(name, 30, INK, SANS, True)], line=1.3)
        text(s, x, 420, 390, 220, [run(what, 24, BODY)], line=1.45)
        text(s, x, 660, 390, 140, [[run("WHY · ", 16, FAINT, SANS, spacing=0.18), run(why, 21, MID)]],
             line=1.45)
    callout(s, 120, 840, 1680, 110, "Each step is $0 except Claude.",
            "We hash the rules before any new score. DeepSeek results stay exploratory, because we saw pilot "
            "numbers first; the Claude replays are the blind test.", 24)


# ---------------------------------------------------------------- 5. What end-sem will measure

FIG = os.path.join(HERE, "figures")
SLICES = os.path.join(FIG, "slices_numbers.json")
ACCENT = "c2410c"


def slices():
    return json.load(open(SLICES))


def plan(prs):
    Z = slices()
    s = frame(prs, 5, "04 · What end-sem will measure", "What end-sem will test, in one stage of one run")
    PW, PH, GAP, X0, Y0 = 420, 477, 20, 120, 292
    panels = [("1 · Mapped so far", "slices_1_mapped.png"),
              (f"2 · Guessed, all {Z['members']} members", "slices_2_guessed.png"),
              ("3 · Real objects, matched", "slices_3_real.png")]
    for i, (name, png) in enumerate(panels):
        x = X0 + i * (PW + GAP)
        label(s, x, 258, PW, name)
        s.shapes.add_picture(os.path.join(FIG, png), px(x), px(Y0), px(PW), px(PH))

    R = 1470
    label(s, R, 258, 330, "How to read panel 3")
    items = [("hit", f"Same-name real object within 0.5 m"),
             ("near", "Within 2 m"),
             ("far", "Farther, or no such object"),
             ("real", "Real object (human label)")]
    y = 304
    for kind, txt in items:
        cx, cy = R + 14, y + 17
        if kind == "hit":
            oval(s, cx, cy, 9, ACCENT)
        elif kind == "near":
            oval(s, cx, cy, 8, WHITE, ACCENT, 3)
        elif kind == "far":
            svg_text(s, cx, cy + 9, "×", 28, MID, anchor="middle", w=30)
        else:
            rect(s, cx - 6, cy - 6, 12, 12, FAINT)
        text(s, R + 40, y, 290, 66, [run(txt, 20, BODY)], line=1.3)
        y += 40 if kind != "hit" else 68
    text(s, R, y + 6, 330, 100, [run("A label gives the distance to the nearest real object with that name. "
                                      "Darker marks in panel 2: members agree.", 18, FAINT)], line=1.4)

    y = 594
    allst = Z["all_sample_stages"]
    for val, lab in [(Z["new_guesses"], "new guesses"),
                     (Z["within_0.5m"], "within 0.5 m of a real one"),
                     (Z["within_2m"], "within 2 m")]:
        hline(s, R, y, R + 330, y, RULE)
        text(s, R, y + 4, 100, 50, [run(f"{val}", 40, INK, LIGHT)], line=1.1)
        text(s, R + 90, y + 14, 240, 36, [run(lab, 20, MID)], line=1.3)
        y += 56
    note(s, X0, 778, 1320, 2,
         f"DeepSeek, run {Z['run']}, stage {Z['stage']}, {Z['members']} members, home {Z['scene'][2:]}. Top-down, "
         f"z 0.5 to 1.5 m, habitat frame. A new guess lies more than 0.5 m from every mapped object. "
         f"{Z['no_same_name_object_in_house']} of {Z['new_guesses']} have a name no real object in the house has.")
    text(s, R, 774, 330, 66, [run(f"All 15 sample stages: {allst['within_0.5m']} of {allst['new']} within 0.5 m, "
                                   f"{allst['within_2m']} within 2 m.", 18, FAINT)], line=1.4)
    callout(s, 120, 862, 1680, 128, "End-sem question.",
            "Are the names right beyond base rates, even where the places are wrong? We score this on the same "
            "stages, with the validity layer and the Claude replays. Result: a pre-registered test of "
            "“right in meaning, wrong in place?”.", 22)


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
    C, budgets = cells()
    prs = Presentation()
    prs.slide_width, prs.slide_height = px(1920), px(1080)
    cover(prs)
    live_test(prs, N)
    paper_scale(prs, C, budgets, json.load(open(CHECKS)))
    questions(prs)
    plan(prs)
    notes = speaker_notes()
    assert len(notes) == TOTAL, len(notes)
    for slide, n in zip(prs.slides, notes):
        slide.notes_slide.notes_text_frame.text = n
    prs.core_properties.title = "ASP check-in 2: right in meaning, wrong in place?"
    prs.core_properties.author = "Sher Partap Singh, Preesha Katial, Ananya Singla"
    prs.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
