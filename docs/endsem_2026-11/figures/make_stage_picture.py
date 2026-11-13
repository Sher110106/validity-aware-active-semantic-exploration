"""Draw one real stage from files: the observed map, the region footprints and their state.

Uses the row's observed graph, the robot's path, and the truth files of
tools/live_policy/semantic/truth/. It draws one saved guess that hits and one that misses (the scorer's own L3 test
says which); it computes no score.
A region is coloured by its state at the stage (seen, partly seen, unobserved; PREREGISTRATION_SEMANTIC.md
section 5.4). The regions that keep a room type open (section 5.5) get a heavy outline and a 0.5 m halo:
a room guess of that type that lands inside the halo reaches the region (L3, section 8).

Run from the project root:
    .venv_offline/bin/python docs/endsem_2026-11/figures/make_stage_picture.py
Writes stage.png and stage_numbers.json beside this file.
"""
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy import ndimage  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(PROJECT, "tools", "live_policy"))
from semantic import extract_preds as E  # noqa: E402
from semantic import score_levels as S  # noqa: E402
from semantic import region_truth as R  # noqa: E402
from semantic.model import REACH_M  # noqa: E402

RUN, STAGE = "e1_00871_s42_official_60m", 8
ROW_ID = "e1_00871_s42_official_st08"
CLAUDE_ROOT = "/Users/sher/project/cvp/replay_outputs/m4"
GUESS_MODEL, GUESS_MEMBER = "claude-opus-5-5", 0
HIT_LABEL, MISS_LABEL = "bed", "toilet"   # one hit and one miss of this member, picked by hand from its items
ACCENT, INK, MID = "#c2410c", "#111111", "#6b7280"
FILL = {"seen": "#e5e7eb", "partly": "#cbd5e1", "unobserved": "#fde8dc"}
SHORT = {"bathroom": "bath", "bedroom": "bed", "kitchen": "kitchen", "laundry": "laundry", "living": "living"}


def main():
    row = E.load_stage_row(RUN, STAGE)
    truth = R.load_scene_truth(row.scene)
    st = R.stage_state(truth, row)
    z = np.load(os.path.join(PROJECT, "tools", "live_policy", "semantic", "truth",
                             f"{row.scene}_region_footprints.npz"))
    cs = float(z["cell_size"])
    ox, oy = float(z["origin_xy"][0]), float(z["origin_xy"][1])
    ids = [int(r) for r in z["region_ids"]]
    masks = z["any_masks"]
    ny, nx = masks.shape[1], masks.shape[2]
    extent = (ox, ox + nx * cs, oy, oy + ny * cs)

    state_of = {}
    for r in ids:
        state_of[r] = "seen" if r in st.seen else "partly" if r in st.partly_seen else "unobserved"
    img = np.ones((ny, nx, 4))
    img[..., 3] = 0.0
    from matplotlib.colors import to_rgb
    for order in ("seen", "partly", "unobserved"):
        for i, r in enumerate(ids):
            if state_of[r] == order:
                m = masks[i]
                img[m, :3] = to_rgb(FILL[order])
                img[m, 3] = 1.0

    fig, ax = plt.subplots(figsize=(7.2, 7.2), dpi=100)
    ax.imshow(img, origin="lower", extent=extent, interpolation="nearest")
    open_regions = sorted({r for v in st.open_type_regions.values() for r in v})
    halo_cells = int(round(REACH_M / cs))
    for i, r in enumerate(ids):
        if r in open_regions:
            m = masks[i]
            halo = ndimage.binary_dilation(m, iterations=halo_cells)
            xs = ox + (np.arange(nx) + 0.5) * cs
            ys = oy + (np.arange(ny) + 0.5) * cs
            ax.contour(xs, ys, halo.astype(float), levels=[0.5], colors=ACCENT, linewidths=1.6, linestyles="--")
            ax.contour(xs, ys, m.astype(float), levels=[0.5], colors=ACCENT, linewidths=3.0)
    for r in ids:
        reg = truth.regions[r]
        if reg.types:
            label = "/".join(SHORT[t] for t in sorted(reg.types))
            ax.text(*reg.centroid_xy, label, ha="center", va="center", fontsize=18, color=INK, zorder=10,
                    path_effects=[pe.withStroke(linewidth=4, foreground="white")])
    path = np.array(row.path_xy)
    ax.plot(path[:, 0], path[:, 1], color=MID, lw=1.2, alpha=0.8)
    ax.plot(*path[0], marker="*", color=INK, ms=16, ls="")
    ax.text(path[0][0] + 0.35, path[0][1] - 0.35, "robot's start and path", ha="left", va="top", fontsize=18,
            color=MID, zorder=10, path_effects=[pe.withStroke(linewidth=4, foreground="white")])
    objs = np.array([n.xy for n in row.observed.objects])
    rooms = np.array([n.xy for n in row.observed.rooms])
    ax.scatter(objs[:, 0], objs[:, 1], s=26, c=INK, zorder=5)
    ax.scatter(rooms[:, 0], rooms[:, 1], s=150, marker="s", facecolors="white", edgecolors=INK, linewidths=2.2,
               zorder=6)
    # one saved guess that hits and one that misses (Opus, member 0): the scorer's own L3 test decides which is which
    from pathlib import Path
    state = st
    member = {m.member: m for m in E.members_for(E.load_row(ROW_ID), GUESS_MODEL, claude_root=Path(CLAUDE_ROOT))}[GUESS_MEMBER]
    guesses = {}
    for item in member.l3_items:
        if item.kind == "object" and item.label in (HIT_LABEL, MISS_LABEL) and item.label not in guesses:
            guesses[item.label] = (item, bool(S.l3_hit(item, truth, state)))
    assert guesses[HIT_LABEL][1] is True and guesses[MISS_LABEL][1] is False, guesses
    hit, miss = guesses[HIT_LABEL][0], guesses[MISS_LABEL][0]
    halo = [pe.withStroke(linewidth=4, foreground="white")]
    ax.scatter([hit.xy[0]], [hit.xy[1]], s=420, marker="*", c=ACCENT, edgecolors=INK, linewidths=1.5, zorder=12)
    ax.text(hit.xy[0] + 0.5, hit.xy[1] - 0.15, f"{hit.label}: hit", ha="left", va="top", fontsize=18, color=INK, zorder=13,
            path_effects=halo)
    ax.scatter([miss.xy[0]], [miss.xy[1]], s=260, marker="X", c=INK, edgecolors="white", linewidths=1.5, zorder=12)
    ax.text(miss.xy[0] + 0.1, miss.xy[1] + 0.95, f"{miss.label}: miss", ha="left", va="bottom", fontsize=18, color=INK,
            zorder=13, path_effects=halo)
    ax.set_aspect("equal")
    ax.set_xlim(extent[0] - 0.3, extent[1] + 0.3)
    ax.set_ylim(extent[2] - 0.3, extent[3] + 0.3)
    bx, by = extent[0] + 0.4, extent[2] + 0.5
    ax.plot([bx, bx + 2.0], [by, by], color=INK, lw=5, solid_capstyle="butt", zorder=11)
    ax.text(bx + 1.0, by + 0.25, "2 m", ha="center", va="bottom", fontsize=18, color=INK, zorder=11,
            path_effects=[pe.withStroke(linewidth=4, foreground="white")])
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(os.path.join(HERE, "stage.png"))

    n = {
        "run": RUN, "stage": STAGE, "scene": row.scene,
        "observed_object_nodes": len(row.observed.objects), "observed_room_nodes": len(row.observed.rooms),
        "regions": len(ids), "seen": len(st.seen), "partly_seen": len(st.partly_seen),
        "unobserved": len(st.unobserved), "open_types": sorted(st.open_types),
        "open_type_regions": {k: sorted(v) for k, v in st.open_type_regions.items()},
        "open_classes": len(st.open_classes), "path_points": len(row.path_xy), "reach_m": REACH_M,
        "guess_model": GUESS_MODEL, "guess_member": GUESS_MEMBER,
        "guess_hit": {"label": hit.label, "xy": list(hit.xy), "l3_hit": True},
        "guess_miss": {"label": miss.label, "xy": list(miss.xy), "l3_hit": False},
    }
    json.dump(n, open(os.path.join(HERE, "stage_numbers.json"), "w"), indent=1)
    print(json.dumps(n))


if __name__ == "__main__":
    main()
