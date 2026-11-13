# Truth files from the HM3D semantic annotations

These files describe the houses only. No model output and no score went into them.
Plan refs: Section A item 18 (region footprints), M0b item 1 (truth), M1 comparator B3b.

Made on 2026-11-13 on the GPU host, inside the `asp-noetic` container, with one process at
`nice -n 19`, no GPU, under an 8 GB memory cap. Scripts: `../host/`.

## Files

| file | what it holds |
|---|---|
| `00853_region_footprints.npz`, `00871_region_footprints.npz` | Boolean masks on a 0.05 m grid, one `floor` and one `any` mask per region. |
| `00853_regions.json`, `00871_regions.json` | Per region: object count, category counts, areas, z ranges, centroid, floor overlaps. Also the transform, grid and check results. |
| `hm3d_semantic_summary.json` | Label counts per region for every house that has a `semantic.txt` (185 houses). |
| `*.log` | Stdout of each run. |

### npz keys
`origin_xy` (x, y of the lower-left corner of cell 0,0), `cell_size` (0.05), `axis_names` (`x`, `y`),
`vertical_axis` (`z`), `region_ids`, `floor_masks` and `any_masks` (shape `[region, iy, ix]`),
`habitat_to_world_R`, `habitat_to_world_t`. Cell `(ix, iy)` covers x from `origin_x + ix*0.05`
and y from `origin_y + iy*0.05`.
Region id -1 would hold objects with no region. Neither scene's `semantic.txt` has one, so the masks hold only ids 1-12 (00853) and 0-15 (00871). (`00853_raw_objects.json` lists one extra Unknown object with region -1; it is not in `semantic.txt`.)

### regions.json fields
`region_id`, `n_objects`, `n_objects_with_geometry`, `n_floor_objects`, `categories` (name: count),
`floor_area_m2`, `any_area_m2`, `has_floor_triangles`, `n_floor_triangles`, `floor_z_range`, `z_range`,
`centroid_xy` (of the floor mask, or of the `any` mask if the region has no floor), `centroid_source`,
`centroid_z`, `floor_overlap_m2` (with each other region's floor mask), pinholes filled.

## Method

1. Read `<scene>.semantic.txt` and `<scene>.semantic.glb`.
2. Give each triangle to an object by the semantic texture colour at its UV centroid, with the
   vertex-texel fallback of `extract_semantic_aabb.py`.
3. Move vertices from the asset frame to the habitat frame, `(x, y, z) -> (x, z, -y)`, then to the
   pipeline frame with `code_transform(pipeline_initial_agent_state)`. The transform is printed in each log
   and saved in the npz. Both scenes share the same rotation:
   `R = [[-0.041067, 0, -0.999156], [-0.999156, 0, 0.041067], [0, 1, 0]]`.
   Translation: 00853 `(4.636027, -4.949742, 0)`; 00871 `(-3.245202, 2.037517, 0)`.
4. **Horizontal axes are pipeline x and y; vertical is z.** Row 3 of R is (0, 1, 0), so world z is
   habitat y (up). Floor triangles sit at z about 0 (median 0.00) and ceiling triangles at z about 2.4 to 2.7,
   in both scenes. The reference `*_semantic_geometry.json` heights agree.
5. Mark the cells of each triangle's three vertices and its centroid. For any triangle with an edge
   longer than one cell, add a barycentric lattice with spacing of at most half a cell.
6. Fill one-cell pinholes: an empty cell with all four edge neighbours set. One pass. This does not
   merge neighbouring regions.
7. `floor` mask: triangles of objects named exactly `floor` (any case). `any` mask: all triangles of the region.

## Commands

On the host, in `/workspace/runs/endsem_semantic` inside the container:

```
docker exec asp-noetic bash -c "cd /workspace/runs/endsem_semantic && ulimit -v 8388608 && nice -n 19 /workspace/environments/semantic_perception/bin/python extract_region_footprints.py 00853 > extract_region_footprints_00853.log 2>&1"
docker exec asp-noetic bash -c "cd /workspace/runs/endsem_semantic && ulimit -v 8388608 && nice -n 19 /workspace/environments/semantic_perception/bin/python extract_region_footprints.py 00871 > extract_region_footprints_00871.log 2>&1"
docker exec asp-noetic bash -c "cd /workspace/runs/endsem_semantic && nice -n 19 /workspace/environments/semantic_perception/bin/python summarise_semantic_txt.py > summarise_semantic_txt.log 2>&1"
```

Copy to the Mac with `scp`. The sha256 of every file matched on both sides.

## Checks

**Extraction matches the earlier one.** For every object with geometry, the triangle count and the
world AABB equal those in `<scene>_semantic_geometry.json`: 525 objects (00853) and 833 (00871),
0 count mismatches, 0.00 m largest difference.

**(a) Floor area.**

| scene | regions with floor | sum of region floor areas | union |
|---|---|---|---|
| 00853 | 12 of 12 (ids 1-12) | 103.24 m² | 102.42 m² |
| 00871 | 15 of 16 (ids 0-15; region 9 has none) | 105.69 m² | 104.89 m² |

00871 region 9 has no `floor` object. Its `any` mask is 17.54 m². Use the `any` mask for it.
Small regions have thin floors: the mesh has no floor under furniture or walls, so a region's
floor area is often well below its `any` area (see the per-region lines in the logs).

**(b) Object centres against their own region's `any` mask.** Centres are the world AABB centres from
this extraction, because `<scene>_raw_objects.json` holds zero for every centre (its own field
`habitat_objects_with_nonzero_aabb` is 0). Objects with region id -1 and objects with no geometry are skipped.

| scene | objects | inside | inside or within 0.5 m |
|---|---|---|---|
| 00853 | 525 | 522 (0.9943) | 525 (1.0000) |
| 00871 | 833 | 820 (0.9844) | 832 (0.9988) |

No frame error. One miss: 00871 object 582, a door frame in region 10, centre at (2.99, -3.19).
Extra, not asked for: against the `floor` mask the shares are 0.4267 and 0.2833 inside, and 0.8648 and
0.8415 inside or within 0.5 m. Object centres often sit over furniture, where the floor mesh has gaps.
Do not use the floor mask alone to place objects.

**(c) Floor area in more than one region's floor mask.** 00853: 0.820 m², 0.0080 of the union.
00871: 0.800 m², 0.0076 of the union. The plan quotes 15-26% overlap for AABBs.

## Summary file

`hm3d_semantic_summary.json` (737,547 bytes, not gzipped). Per house: `house_id`, `number`, `name`,
`split`, `n_objects`, `n_regions` (ids 0 and up), `n_objects_unassigned`, `mark`, and
`regions` (region id: category: count).

- 185 houses: 36 val, 145 train, 4 minival. The other 725 house folders have no `semantic.txt`.
- `mark` is `ours` for 00853 and 00871.
- Scenes 00069 and 00573 have house folders under `train` but no `semantic.txt`, so they are not in the summary
  (`named_not_found` lists them).
