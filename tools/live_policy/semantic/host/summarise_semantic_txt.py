"""Label summary of every annotated HM3D house (val, train, minival). Text files only, no geometry.

Runs inside the asp-noetic container (Python 3.9). Usage (cwd = /workspace/runs/endsem_semantic):
    python summarise_semantic_txt.py

semantic.txt lines: id,hexcolour,"name",region_id   (first line is a header).
Output: hm3d_semantic_summary.json  (gzipped to .json.gz when over 5 MB)
"""
import os
import re
import csv
import gzip
import json
import glob
import hashlib
import collections

HM3D = "/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d"
SPLITS = ["val", "train", "minival"]
OURS = {"00853", "00871"}
NAMED = {"00069", "00573"}


def main():
    houses = []
    skipped = []
    for split in SPLITS:
        for d in sorted(glob.glob(f"{HM3D}/{split}/*")):
            hid = os.path.basename(d)
            m = re.match(r"^(\d{5})-(.+)$", hid)
            txts = glob.glob(f"{d}/*.semantic.txt")
            if not m:
                continue
            if not txts:
                skipped.append(f"{split}/{hid}")
                continue
            by_region = collections.defaultdict(collections.Counter)
            n_obj = 0
            with open(txts[0]) as f:
                f.readline()
                for row in csv.reader(f):
                    if len(row) < 4:
                        continue
                    by_region[int(row[3])][row[2]] += 1
                    n_obj += 1
            regions = {str(r): dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))) for r, c in sorted(by_region.items())}
            num = m.group(1)
            houses.append(dict(
                house_id=hid, number=num, name=m.group(2), split=split,
                n_objects=n_obj,
                n_regions=sum(1 for r in by_region if r >= 0),
                n_objects_unassigned=sum(by_region[-1].values()) if -1 in by_region else 0,
                mark="ours" if num in OURS else ("named" if num in NAMED else None),
                regions=regions,
            ))
    out = dict(source=HM3D, splits=SPLITS,
               note="n_regions counts region ids >= 0. Region -1 holds objects with no region and is listed under regions['-1'].",
               n_houses=len(houses),
               n_by_split=dict(collections.Counter(h["split"] for h in houses)),
               marked={h["number"]: h["house_id"] for h in houses if h["mark"]},
               named_not_found=sorted(NAMED - {h["number"] for h in houses}),
               dirs_without_semantic_txt=skipped,
               houses=houses)
    path = "hm3d_semantic_summary.json"
    s = json.dumps(out, indent=None, separators=(",", ":"))
    if len(s) > 5_000_000:
        path += ".gz"
        with gzip.open(path, "wt", compresslevel=9) as f:
            f.write(s)
    else:
        open(path, "w").write(s)
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    print("houses:", len(houses), out["n_by_split"])
    print("marked:", out["marked"], "named not found:", out["named_not_found"])
    print("dirs without semantic.txt:", len(skipped))
    print(f"wrote {path} {os.path.getsize(path)} bytes sha256 {h}")


if __name__ == "__main__":
    main()
