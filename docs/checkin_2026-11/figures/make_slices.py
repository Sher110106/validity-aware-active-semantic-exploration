"""Top-down slices for slide 5 of check-in 2: what end-sem will measure, on one stage of one run.

Reads the YAML graphs of one live DeepSeek stage and the human HM3D reference, draws three panels
(mapped, guessed, real + matched) and writes slices_*.png and slices_numbers.json next to this file.
Every number on the slide is read from that JSON.

Rules (from the end-sem plan):
  new guess = object node with is_predicted set, more than 0.5 m (x/y) from every observed object;
  right in place = a real HM3D object with the same lower-case name within 0.5 m (x/y); also within 2 m.
Counts are (member, guess) instances over the 8 completions of the stage.

Usage: uv run --with matplotlib --with pyyaml --with numpy python make_slices.py
"""
import ast
import json
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CAMPAIGN = "/Users/sher/cvp_live_campaign_copy/runs/live_campaign/"
RUN, SCENE, STAGE = "e1_00853_s42_official_60m", "00853", 3
COUNTED = [("e1_00853_s42_official_60m", "00853"), ("e1_00853_s43_official_60m", "00853"),
           ("e1_00871_s42_official_60m", "00871"), ("e1_00871_s43_official_60m", "00871"),
           ("e1_00871_s44_official_60m", "00871")]
SAMPLE_STAGES = (3, 8, 13)
MEMBERS = 8
ZLO, ZHI = 0.5, 1.5
NEAR, FAR = 0.5, 2.0

INK, BODY, MID, FAINT, LINE, WASH = "#111111", "#374151", "#6b7280", "#9ca3af", "#d1d5db", "#f7f7f7"
ACCENT = "#c2410c"
PANEL_W, PANEL_H = 4.4, 5.0  # inches, drawn at 200 dpi -> 880 x 1000 px
FONT = 15


def load(path):
    return yaml.safe_load(open(path))["nodes"]


def pos(n):
    return ast.literal_eval(n["position"])


def dim(n):
    return ast.literal_eval(n["dimension"])


def objects(nodes):
    return [n for n in nodes if n["node_type"] == "object"]


def d_xy(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def new_guesses(stage_dir, observed):
    """New guessed objects of every member: (member, name, [x, y, z])."""
    obs_xy = [pos(o) for o in objects(observed)]
    out = []
    for m in range(MEMBERS):
        path = os.path.join(stage_dir, f"habitat_scene_graph_new_graph_{m}.yaml")
        if not os.path.exists(path):
            continue
        for n in objects(load(path)):
            if not n.get("is_predicted"):
                continue
            p = pos(n)
            if all(d_xy(p, q) > NEAR for q in obs_xy):
                out.append((m, str(n["name"]).lower(), p))
    return out


def match(guess, truth):
    """Nearest same-name real object: (distance, truth name, position) or None."""
    best = None
    for t in truth:
        if str(t["name"]).lower() != guess[1]:
            continue
        d = d_xy(guess[2], pos(t))
        if best is None or d < best[0]:
            best = (d, pos(t))
    return best


def truth_of(scene):
    return objects(load(os.path.join(CAMPAIGN, "hm3d_refs_work", f"{scene}_hm3d_reference.yaml")))


def tally(guesses, truth):
    ms = [match(g, truth) for g in guesses]
    return (len(guesses), sum(1 for m in ms if m and m[0] <= NEAR), sum(1 for m in ms if m and m[0] <= FAR))


def stage_box(x, y, ax, **kw):
    ax.add_patch(Rectangle((x[0], y[0]), x[1] - x[0], y[1] - y[0], **kw))


def in_band(n):
    z, dz = pos(n)[2], dim(n)[2]
    return z + dz / 2 >= ZLO and z - dz / 2 <= ZHI


def base_map(ax, observed, label_objects):
    """Structure and objects of the mapped graph, in the 0.5 to 1.5 m band, boxes seen from above."""
    for n in observed:
        if n["node_type"] not in ("structure", "object") or not in_band(n):
            continue
        (x, y, _), (dx, dy, _) = pos(n), dim(n)
        if n["node_type"] == "structure":
            stage_box((x - dx / 2, x + dx / 2), (y - dy / 2, y + dy / 2), ax, fc=MID, ec=MID, lw=0.8)
        else:
            stage_box((x - dx / 2, x + dx / 2), (y - dy / 2, y + dy / 2), ax, fc=LINE, ec=MID, lw=0.8)
    if label_objects:
        placed = []
        for n in sorted(objects(observed), key=lambda n: pos(n)[0]):
            x, y, _ = pos(n)
            while any(abs(x - a) < 1.3 and abs(y - b) < 0.3 for a, b in placed):
                y += 0.38
            placed.append((x, y))
            ax.annotate(str(n["name"]).lower(), (x, y), xytext=(0, 0), textcoords="offset points", ha="center",
                        va="center", fontsize=FONT - 5, color=BODY, zorder=5,
                        bbox=dict(boxstyle="square,pad=0.08", fc="white", ec="none", alpha=0.75))


def style(ax, win, scale_bar=True):
    x0, x1, y0, y1 = win
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor(LINE)
        s.set_linewidth(1)
    if scale_bar:
        ax.plot([x0 + 0.4, x0 + 2.4], [y0 + 0.45, y0 + 0.45], color=INK, lw=2.5, solid_capstyle="butt")
        ax.text(x0 + 1.4, y0 + 0.65, "2 m", ha="center", va="bottom", fontsize=FONT - 3, color=BODY)


def new_ax():
    fig = plt.figure(figsize=(PANEL_W, PANEL_H), dpi=200)
    ax = fig.add_axes([0.01, 0.01, 0.98, 0.98])
    return fig, ax


def save(fig, name):
    fig.savefig(os.path.join(HERE, name), dpi=200, facecolor="white")
    plt.close(fig)


def pick_examples(rows, inside):
    """One right-in-place guess, one near miss, one far miss, chosen by rule, preferring common furniture."""
    prefer = ["bed", "sofa", "couch", "toilet", "table", "chair", "cabinet", "tv", "desk", "plant"]

    def rank(r):
        return (prefer.index(r["name"]) if r["name"] in prefer else len(prefer), r["name"])

    hit = sorted([r for r in rows if r["dist"] is not None and r["dist"] <= NEAR], key=lambda r: (rank(r), r["dist"]))
    near = sorted([r for r in rows if r["dist"] is not None and NEAR < r["dist"] <= FAR], key=lambda r: (rank(r), r["dist"]))
    far = sorted([r for r in rows if r["dist"] is not None and 3.0 <= r["dist"] <= 6.0 and inside(r["real"])], key=lambda r: (rank(r), r["dist"]))
    out, used = [], set()
    for kind, pool in (("hit", hit), ("near", near), ("far", far)):
        for r in pool:
            if r["name"] not in used:
                used.add(r["name"])
                out.append((kind, r))
                break
    return out


def main():
    stage_dir = os.path.join(CAMPAIGN, RUN, "stages", str(STAGE))
    observed = load(os.path.join(stage_dir, "habitat_scene_graph_original_graph0.yaml"))
    truth = truth_of(SCENE)
    guesses = new_guesses(stage_dir, observed)
    rows = []
    for g in guesses:
        m = match(g, truth)
        rows.append({"member": g[0], "name": g[1], "pos": g[2], "dist": m[0] if m else None,
                     "real": m[1] if m else None})
    n_new, n_near, n_far = tally(guesses, truth)

    # Window: mapped graph and all guesses, padded; real objects inside it are drawn.
    xs = [pos(n)[0] for n in observed if n["node_type"] in ("structure", "object")] + [r["pos"][0] for r in rows]
    ys = [pos(n)[1] for n in observed if n["node_type"] in ("structure", "object")] + [r["pos"][1] for r in rows]
    pad = 1.0
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    half_w = max((x1 - x0) / 2, (y1 - y0) / 2 * PANEL_W / PANEL_H)
    half_h = half_w * PANEL_H / PANEL_W
    win = (cx - half_w, cx + half_w, cy - half_h, cy + half_h)
    inside = lambda p: win[0] <= p[0] <= win[1] and win[2] <= p[1] <= win[3]  # noqa: E731
    truth_in = [t for t in truth if inside(pos(t))]

    # Panel 1: what the robot had mapped.
    fig, ax = new_ax()
    base_map(ax, observed, label_objects=True)
    style(ax, win)
    save(fig, "slices_1_mapped.png")

    # Panel 2: all new guesses of the 8 members over the faint map.
    fig, ax = new_ax()
    base_map(ax, [n for n in observed], label_objects=False)
    for a in ax.patches:
        a.set_alpha(0.35)
    gx = [r["pos"][0] for r in rows]
    gy = [r["pos"][1] for r in rows]
    ax.scatter(gx, gy, s=34, c=INK, alpha=0.45, linewidths=0, zorder=3)
    style(ax, win)
    save(fig, "slices_2_guessed.png")

    # Panel 3: real objects, each guess marked by its nearest same-name real object.
    fig, ax = new_ax()
    base_map(ax, observed, label_objects=False)
    for a in ax.patches:
        a.set_alpha(0.2)
    tx = [pos(t)[0] for t in truth_in]
    ty = [pos(t)[1] for t in truth_in]
    ax.scatter(tx, ty, s=16, marker="s", c="#bdbdbd", linewidths=0, zorder=2)
    for r in rows:
        if r["dist"] is not None and r["dist"] <= FAR:
            ax.plot([r["pos"][0], r["real"][0]], [r["pos"][1], r["real"][1]], color=ACCENT, lw=0.8, alpha=0.6,
                    zorder=3)
    far_r = [r for r in rows if r["dist"] is None or r["dist"] > FAR]
    near_r = [r for r in rows if r["dist"] is not None and NEAR < r["dist"] <= FAR]
    hit_r = [r for r in rows if r["dist"] is not None and r["dist"] <= NEAR]
    ax.scatter([r["pos"][0] for r in far_r], [r["pos"][1] for r in far_r], s=20, marker="x", c=FAINT, linewidths=0.9,
               zorder=4)
    ax.scatter([r["pos"][0] for r in near_r], [r["pos"][1] for r in near_r], s=60, facecolors="white",
               edgecolors=ACCENT, linewidths=1.8, zorder=5)
    ax.scatter([r["pos"][0] for r in hit_r], [r["pos"][1] for r in hit_r], s=70, c=ACCENT, linewidths=0, zorder=6)
    examples = []
    for kind, r in pick_examples(rows, inside):
        if kind == "far":
            # a far miss is drawn to its real object, so the gap is visible
            ax.plot([r["pos"][0], r["real"][0]], [r["pos"][1], r["real"][1]], color=MID, lw=1, ls=(0, (3, 3)),
                    zorder=3)
            ax.scatter([r["real"][0]], [r["real"][1]], s=60, marker="s", facecolors="white", edgecolors=INK,
                       linewidths=1.4, zorder=7)
        txt = f"{r['name']} {r['dist']:.1f} m"
        px_, py_ = r["pos"][0], r["pos"][1]
        left = px_ > cx
        ax.annotate(txt, (px_, py_), xytext=(14 if kind == "near" else (-14 if left else 14), -34 if kind == "near" else 18), textcoords="offset points",
                    ha="left" if (kind == "near" or not left) else "right", fontsize=FONT - 3, color=INK,
                    fontweight="bold", zorder=9,
                    bbox=dict(boxstyle="square,pad=0.15", fc="white", ec=LINE, lw=0.6, alpha=0.95),
                    arrowprops=dict(arrowstyle="-", color=INK, lw=0.8))
        examples.append({"kind": kind, "name": r["name"], "distance_m": round(r["dist"], 2),
                         "guess_xy": [round(v, 2) for v in r["pos"][:2]],
                         "real_xy": [round(v, 2) for v in r["real"][:2]]})
    style(ax, win)
    save(fig, "slices_3_real.png")

    # The same rule over all sample stages of the five counted runs.
    pooled = {"stage_runs": 0, "new": 0, "within_0.5m": 0, "within_2m": 0}
    per = []
    for run, scene in COUNTED:
        tr = truth_of(scene)
        for k in SAMPLE_STAGES:
            d = os.path.join(CAMPAIGN, run, "stages", str(k))
            if not os.path.exists(os.path.join(d, "habitat_scene_graph_original_graph0.yaml")):
                continue
            n, a, b = tally(new_guesses(d, load(os.path.join(d, "habitat_scene_graph_original_graph0.yaml"))), tr)
            pooled["stage_runs"] += 1
            pooled["new"] += n
            pooled["within_0.5m"] += a
            pooled["within_2m"] += b
            per.append({"run": run, "stage": k, "new": n, "within_0.5m": a, "within_2m": b})

    obs_objs = objects(observed)
    out = {
        "run": RUN, "scene": SCENE, "stage": STAGE, "members": len({r["member"] for r in rows}) or MEMBERS,
        "frame": "habitat world frame, x/y top-down, z band %.1f to %.1f m" % (ZLO, ZHI),
        "rule": {"new_guess": "is_predicted object, > 0.5 m (x/y) from every observed object",
                 "right_in_place": "same lower-case name, real object within 0.5 m (x/y); also within 2 m"},
        "observed_objects": len(obs_objs), "real_objects_in_house": len(truth), "real_objects_in_view": len(truth_in),
        "new_guesses": n_new, "within_0.5m": n_near, "within_2m": n_far,
        "same_name_exists_anywhere": sum(1 for r in rows if r["dist"] is not None),
        "no_same_name_object_in_house": sum(1 for r in rows if r["dist"] is None),
        "examples": examples, "all_sample_stages": pooled, "per_stage_run": per,
        "window_xy": [round(v, 2) for v in win],
    }
    json.dump(out, open(os.path.join(HERE, "slices_numbers.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "per_stage_run"}, indent=1))


if __name__ == "__main__":
    main()
