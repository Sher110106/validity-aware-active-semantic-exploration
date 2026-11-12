"""Build ASP_Checkin.pptx: an editable PowerPoint copy of the open-slide deck
slides/asp-checkin (1920 x 1080 canvas), with the speaker script as notes.

Canvas pixels map to slide units at 6350 EMU per px and to type at px / 2 pt.

Usage: uv run --with python-pptx python build_checkin_pptx.py
"""
import os
import re

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "ASP_Checkin.pptx")
SCRIPT = os.path.join(HERE, "ASP_Checkin_Script.md")

INK, BODY, MID, FAINT = "111111", "374151", "6b7280", "9ca3af"
LINE, RULE, WASH, WHITE = "d1d5db", "e5e7eb", "f7f7f7", "ffffff"
SANS, LIGHT, MONO = "Helvetica Neue", "Helvetica Neue Light", "Menlo"
TOTAL = 4


def px(v):
    return Emu(int(round(v * 6350)))


def rgb(h):
    return RGBColor.from_string(h)


def run(text, size, color=BODY, font=SANS, bold=False, spacing=None):
    """One styled run; spacing is letter spacing in em."""
    return dict(text=text, size=size, color=color, font=font, bold=bold, spacing=spacing)


def kick(text, size=22, em=0.18):
    return run(text.upper(), size, FAINT, SANS, spacing=em)


def text(slide, x, y, w, h, paras, align=PP_ALIGN.LEFT, line=1.2, anchor=MSO_ANCHOR.TOP):
    """paras: list of paragraphs, each a run dict or a list of run dicts."""
    tb = slide.shapes.add_textbox(px(x), px(y), px(w), px(h))
    fill_frame(tb.text_frame, paras, align, line, anchor)
    return tb


def fill_frame(tf, paras, align=PP_ALIGN.LEFT, line=1.2, anchor=MSO_ANCHOR.TOP, margins=(0, 0, 0, 0)):
    tf.word_wrap = True
    tf.auto_size = None
    tf.vertical_anchor = anchor
    tf.margin_left, tf.margin_top, tf.margin_right, tf.margin_bottom = (px(m) for m in margins)
    for i, p_runs in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p_runs = p_runs if isinstance(p_runs, list) else [p_runs]
        # Exact spacing, as CSS line-height: font size times the factor.
        p.line_spacing = Pt(max(r["size"] for r in p_runs) / 2 * line)
        for r in p_runs:
            rr = p.add_run()
            rr.text = r["text"]
            f = rr.font
            f.size = Pt(r["size"] / 2)
            f.name = r["font"]
            f.bold = r["bold"]
            f.color.rgb = rgb(r["color"])
            if r["spacing"]:
                rr._r.get_or_add_rPr().set("spc", str(int(r["size"] / 2 * r["spacing"] * 100)))


def svg_text(slide, x, base, s, size, color, font=SANS, anchor="start", bold=False, w=420):
    """Place text the way SVG does: x is the anchor point, base the baseline."""
    top = base - size * 1.02
    left = {"start": x, "middle": x - w / 2, "end": x - w}[anchor]
    align = {"start": PP_ALIGN.LEFT, "middle": PP_ALIGN.CENTER, "end": PP_ALIGN.RIGHT}[anchor]
    text(slide, left, top, w, size * 1.3, [run(s, size, color, font, bold)], align, 1.2)


def plain(shape):
    """Drop the theme style, which adds a shadow and default colours."""
    st = shape._element.find(qn("p:style"))
    if st is not None:
        shape._element.remove(st)
    return shape


def rect(slide, x, y, w, h, fill, line=None, width=1):
    s = plain(slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, px(x), px(y), px(w), px(h)))
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(fill)
    if line:
        s.line.color.rgb = rgb(line)
        s.line.width = px(width)
    else:
        s.line.fill.background()
    return s


def oval(slide, cx, cy, r, fill, line=None, width=0):
    s = plain(slide.shapes.add_shape(MSO_SHAPE.OVAL, px(cx - r), px(cy - r), px(2 * r), px(2 * r)))
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(fill)
    if line:
        s.line.color.rgb = rgb(line)
        s.line.width = px(width)
    else:
        s.line.fill.background()
    return s


def hline(slide, x1, y1, x2, y2, color, width=1, dash=False):
    c = plain(slide.shapes.add_connector(1, px(x1), px(y1), px(x2), px(y2)))
    c.line.color.rgb = rgb(color)
    c.line.width = px(width)
    if dash:
        c.line.dash_style = MSO_LINE.DASH
    return c


def callout(slide, x, y, w, h, head, body, size=25):
    s = rect(slide, x, y, w, h, WASH, RULE)
    fill_frame(s.text_frame, [[run(head + " ", size, INK, SANS, True), run(body, size, BODY)]],
               line=1.5, anchor=MSO_ANCHOR.MIDDLE, margins=(28, 20, 28, 20))
    return s


def stat(slide, x, y, w, value, label, label_lines=2):
    hline(slide, x, y, x + w, y, RULE)
    text(slide, x, y + 12, w, 66, [run(value, 56, INK, LIGHT)], line=1.1)
    text(slide, x, y + 80, w, 31 * label_lines, [run(label, 22, MID)], line=1.4)


def frame(prs, n, k, title):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    text(s, 120, 84, 1680, 30, [kick(k)])
    text(s, 120, 123, 1680, 74, [run(title, 60, INK, LIGHT, spacing=-0.02)], line=1.15)
    hline(s, 120, 222, 1800, 222, RULE)
    text(s, 120, 1010, 1200, 28, [run("Validity-aware active semantic exploration · Check-in", 20, FAINT)])
    text(s, 1500, 1010, 300, 28, [run(f"{n:02d} / {TOTAL}", 20, FAINT)], PP_ALIGN.RIGHT)
    return s


def label(slide, x, y, w, s):
    text(slide, x, y, w, 28, [kick(s, 20, 0.14)])


def note(slide, x, y, w, lines, s):
    text(slide, x, y, w, 33 * lines, [run(s, 22, FAINT)], line=1.5)


# ---------------------------------------------------------------- 1. Problem and recap

def cover(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    text(s, 160, 140, 1600, 30, [kick("Check-in before endsem · Computer vision and perception")])
    text(s, 160, 205, 1600, 250, [run("Validity-aware active", 112, INK, LIGHT, spacing=-0.03),
                                  run("semantic exploration", 112, INK, LIGHT, spacing=-0.03)], line=1.05)
    text(s, 160, 470, 1420, 150, [run(
        "A robot maps an unknown home under a path budget. Active Semantic Perception (ASP) asks a "
        "language model to guess the rooms and objects not yet seen, then drives to where the guesses "
        "disagree.", 32, BODY)], line=1.5)
    cols = [("Midsem finding", "81% of the nodes the LLM added broke simple physical rules (407 of 500)."),
            ("Midsem plan", "A validity layer: validate, vote, calibrate, then score views with risk."),
            ("Since then", "We built and tested the layer, then asked whether the guesses help at all.")]
    for i, (name, body) in enumerate(cols):
        x = 160 + i * 552
        hline(s, x, 688, x + 496, 688, INK, 2)
        text(s, x, 708, 496, 30, [run(f"{i + 1:02d}", 20, FAINT, MONO)], line=1.5)
        text(s, x, 748, 496, 45, [run(name, 30, INK, SANS, True)], line=1.5)
        text(s, x, 803, 496, 80, [run(body, 25, BODY)], line=1.45)
    hline(s, 160, 925, 1760, 925, RULE)
    text(s, 160, 952, 900, 32, [run("Sher Partap Singh · Preesha Katial · Ananya Singla", 24, MID)])
    text(s, 860, 952, 900, 32, [run("Base paper: Tang & Chaudhari, Active Semantic Perception, "
                                    "arXiv:2510.05430", 24, MID)], PP_ALIGN.RIGHT)


# ---------------------------------------------------------------- 2. The validity layer

def layer(prs):
    s = frame(prs, 2, "01 · The validity layer · three homes, 120 m each",
              "Filtering helped only by deleting the guesses")
    L = 120
    label(s, L, 262, 820, "Object F1, area under curve to 120 m")
    cols = [0, 150, 350, 570]
    rows = [(["Scene", "Author's ASP", "Our filter", "No guesses at all"], True),
            (["00069", "0.479", "0.522", "0.522"], False),
            (["00573", "0.398", "0.435", "0.435"], False),
            (["00853", "0.458", "0.496", "0.496"], False)]
    y = 300
    for cells, head in rows:
        h = 52 if head else 64
        for j, c in enumerate(cells):
            if head:
                r = run(c.upper(), 18, MID, SANS, spacing=0.1)
            else:
                r = run(c, 26, INK if j == 2 else BODY, MONO)
            text(s, L + cols[j], y + 12, 250, h - 12, [r])
        y += h
        hline(s, L, y, L + 820, y, LINE if head else RULE)
    note(s, L, 558, 820, 2, "One DeepSeek run per scene; each policy applied to the same saved guesses. "
                               "Scored against the frontier-run map, as at midsem.")
    stat(s, L, 654, 390, "19 of 8,943", "predicted nodes the filter (full agreement) kept")
    stat(s, L + 430, 654, 390, "≤ 0.0002", "F1 gap between our filter and deleting every guess")
    text(s, L, 820, 820, 80, [run("Calibrating the votes did not help. The risk term was nearly inactive, "
                                  "or chose worse views.", 25, BODY)], line=1.45)

    R, T = 1020, 341.5  # chart origin, same coordinates as the deck's SVG
    label(s, R, 262, 780, "Why: how often a predicted object is real")
    for x, shade, name in ((1020, LINE, "Random guesses"), (1240, MID, "DeepSeek V4.1 Flash 1017"),
                           (1544, INK, "Gemini 3.8 Flash")):
        rect(s, x, 311, 18, 18, shade)
        text(s, x + 28, 304, 280, 30, [run(name, 21, MID)], line=1.5)

    def by(v):
        return 300 - v / 20 * 270

    for v in (5, 10, 15, 20):
        hline(s, R + 70, T + by(v), R + 760, T + by(v), RULE)
    hline(s, R + 70, T + 300, R + 760, T + 300, MID)
    for v, lab in ((0, "0%"), (10, "10%"), (20, "20%")):
        svg_text(s, R + 56, T + by(v) + 7, lab, 20, FAINT, anchor="end", w=80)
    for x, v, shade in ((132, 1.5, LINE), (212, 1.7, MID), (292, 7.1, INK),
                        (472, 4.1, LINE), (552, 7.4, MID), (632, 17.1, INK)):
        rect(s, R + x, T + by(v), 76, 300 - by(v), shade)
        svg_text(s, R + x + 38, T + by(v) - 10, f"{v:.1f}%", 22, INK, MONO, "middle", w=120)
    svg_text(s, R + 250, T + 334, "within 0.5 m", 22, BODY, anchor="middle", w=240)
    svg_text(s, R + 590, T + 334, "within 1.0 m", 22, BODY, anchor="middle", w=240)
    note(s, R, 689.5, 780, 3, "New predicted objects that land near a real object with the same label, in the "
                              "human HM3D annotation. 8 saved inputs from our live runs, scenes 00853 and "
                              "00871. Exploratory.")
    callout(s, R, 804.5, 780, 114, "Reading.", "Within 0.5 m, DeepSeek is no better than chance: a filter has "
                                               "little to keep. Gemini is 4–5× chance.", 24)


# ---------------------------------------------------------------- 3. A fairer test

def fair_test(prs):
    s = frame(prs, 3, "02 · A fairer test", "Human labels and a random-guess placebo")
    L = 120
    label(s, L, 262, 600, "New yardstick")
    text(s, L, 294, 600, 150, [run("At midsem, ground truth was the map from a long frontier run. That map "
                                   "favours the frontier robot, so we built reference graphs from the human "
                                   "HM3D annotation.", 25, BODY)], line=1.45)
    stat(s, L, 461, 282, "−21%", "ASP vs frontier, frontier-run map")
    stat(s, L + 318, 461, 282, "+10%", "same runs, human labels")
    note(s, L, 616, 600, 1, "Scene 00853, September run, AUC to 60 m.")
    label(s, L, 680, 600, "Placebo")
    text(s, L, 712, 600, 150, [run("The same live pipeline, but the LLM's guesses are swapped for random ones "
                                   "of the same count and size. If the guesses matter, the placebo should "
                                   "lose.", 25, BODY)], line=1.45)

    R, T = 790, 300  # dot plot origin, same coordinates as the deck's SVG
    label(s, R, 262, 1010, "Live runs, area under object-F1 curve to 50 m, human labels")
    row = [102, 194, 286]

    def dx(x0, v):
        return R + x0 + (v - 0.09) / 0.08 * 300

    oval(s, R + 16, T + row[0] - 10, 10, INK)
    oval(s, R + 16, T + row[1] - 10, 9, WHITE, INK, 3)
    rect(s, R + 7, T + row[2] - 19, 18, 18, BODY)
    for y, name, sub in ((row[0], "Author's ASP", "DeepSeek, live"), (row[1], "Placebo", "random guesses"),
                         (row[2], "Our filter", "validity layer, live")):
        svg_text(s, R + 44, T + y - 2, name, 25, INK, w=260)
        svg_text(s, R + 44, T + y + 26, sub, 19, MID, w=260)
    for x0, scene, frontier in ((320, "00853", 0.1511), (690, "00871", 0.1031)):
        svg_text(s, R + x0, T + 22, f"Scene {scene}", 24, INK, bold=True, w=300)
        for t in (0.10, 0.12, 0.14, 0.16):
            hline(s, dx(x0, t), T + 70, dx(x0, t), T + 326, RULE)
            svg_text(s, dx(x0, t), T + 356, f"{t:.2f}", 20, FAINT, anchor="middle", w=100)
        hline(s, R + x0, T + 326, R + x0 + 300, T + 326, MID)
        hline(s, dx(x0, frontier), T + 58, dx(x0, frontier), T + 326, MID, 2, dash=True)
        svg_text(s, dx(x0, frontier), T + 50, "frontier", 19, MID, anchor="middle", w=140)
    for x0, offi, plac, filt in ((320, (0.1169, 0.1304), (0.1333, 0.1549), 0.1425),
                                 (690, (0.1218, 0.1124), (0.1035,), 0.1240)):
        for v in offi:
            oval(s, dx(x0, v), T + row[0], 11, INK, WHITE, 3)
        for v in plac:
            oval(s, dx(x0, v), T + row[1], 10, WHITE, INK, 3)
        rect(s, dx(x0, filt) - 10, T + row[2] - 10, 20, 20, BODY)
    note(s, R, 674, 1010, 1, "Each mark is one run (seeds 42 and 43). Dashed line: frontier robot, no LLM. "
                             "About $1 per live run.")
    callout(s, R, 725, 1010, 148, "Reading.", "So far random guesses map about as well as the LLM's: ahead on "
                                              "00853, behind on 00871. Our filter is ahead on 00853 (0.143 vs "
                                              "0.117) and level on 00871 (0.124 vs 0.122). Too few runs to call.",
            24)


# ---------------------------------------------------------------- 4. Direction to endsem

def direction(prs):
    s = frame(prs, 4, "03 · Direction to endsem", "Does a better guesser make a better explorer?")
    steps = [("Finish the live test",
              "Two scenes, three seeds: author's ASP, placebo and our filter, scored on human labels.",
              "Running now; about $1 per run, $7.5 of $40 spent."),
             ("Screen guessers",
              "Score two or three affordable models on the same saved inputs, against random guesses.",
              "Gemini 7.1%, DeepSeek 1.7%, chance 1.5%."),
             ("Live-test the best",
              "Run the best affordable guesser live against its own placebo, on the same scenes.",
              "A 60 m Gemini run would cost about $200, so we screen first."),
             ("Re-test the filter",
              "Apply the validity layer where the guesses carry signal, so it has something to keep.",
              "With DeepSeek it deleted 99.8% of the guesses.")]
    for i, (name, what, why) in enumerate(steps):
        x = 120 + i * 430
        hline(s, x, 262, x + 390, 262, INK, 2)
        text(s, x, 282, 390, 30, [run(f"{i + 1:02d}", 20, FAINT, MONO)], line=1.5)
        text(s, x, 324, 390, 45, [run(name, 30, INK, SANS, True)], line=1.5)
        text(s, x, 381, 390, 110, [run(what, 24, BODY)], line=1.45)
        text(s, x, 497, 390, 70, [[run("EVIDENCE · ", 16, FAINT, SANS, spacing=0.18), run(why, 21, MID)]],
             line=1.45)
    callout(s, 120, 622, 947, 115, "Endsem result.", "A placebo-controlled test of LLM-guided exploration, "
                                                     "scored on human labels, with the validity layer as one arm.")
    callout(s, 1107, 622, 693, 115, "Out of scope.", "New perception models, training the LLM, a real robot.")


def speaker_notes():
    """Split the script into one note per slide; drop stage directions in italics."""
    md = open(SCRIPT).read()
    parts = re.split(r"^## Slide \d+:.*$", md, flags=re.M)[1:]
    out = []
    for p in parts:
        p = p.split("\n---")[0]
        lines = [ln.strip() for ln in p.strip().splitlines()]
        out.append("\n".join(ln for ln in lines if ln and not re.fullmatch(r"\*\(.*\)\*", ln)))
    return out


def main():
    prs = Presentation()
    prs.slide_width, prs.slide_height = px(1920), px(1080)
    for build in (cover, layer, fair_test, direction):
        build(prs)
    for slide, notes in zip(prs.slides, speaker_notes()):
        slide.notes_slide.notes_text_frame.text = notes
    prs.core_properties.title = "ASP check-in: does a better guesser make a better explorer?"
    prs.core_properties.author = "Sher Partap Singh, Preesha Katial, Ananya Singla"
    prs.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
