# Data inventory for the semantic test

Written 2026-11-13 for the pre-registration (M0b) and the scorer (M1). It holds facts: paths, schemas, counts. It holds no score that compares LLM guesses with truth or with a baseline. Items marked **inferred** were deduced, not read from a file or from code.

## 0. Conventions

| Short name | Path |
|---|---|
| `LC` | `/Users/sher/cvp_live_campaign_copy/runs/live_campaign` (laptop copy of the host `/workspace/runs/live_campaign`) |
| `HW` | `/Users/sher/cvp_live_campaign_copy/runs/live_campaign/hm3d_refs_work` (truth files, Gemini output, label tables) |
| `PS` | `/Users/sher/cvp_paper_scale_copy/runs` (paper-scale runs; no LLM completions) |
| `REPO` | `/Users/sher/project/cvp/project` |
| `LP` | `REPO/tools/live_policy` |
| `ASP` | `REPO/tools/asp_offline` |

- **Python.** Use `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3`. It has yaml (with `CSafeLoader`), numpy, scipy, networkx, scikit-learn, PIL, cv2, matplotlib. It has no shapely, trimesh, gmatch4py or habitat_sim. The Homebrew `python3` and `/Users/sher/project/cvp/.venv` lack yaml or networkx.
- **Member.** One completion file `habitat_scene_graph_new_graph_<id>.yaml`. `LLM_ENSEMBLE_COUNT` is 4 (`LC/<run>/config/pipeline_config.yaml:106`). Track = id // 4 (`live_policy.py:156`). **Track 0 = ids 0-3, scored against `habitat_scene_graph_original_graph0.yaml`. Track 1 = ids 4-7, against `..._original_graph1.yaml`.** A member file is missing when the parse failed; no file means no member.
- **Stage folder.** `LC/<run>/stages/<k>`. The pipeline writes the observed graphs first, then the members (`ep_orig.py:742-756`, `REPO/tools/live_policy/review_2026-10-29/final_review_scripts/claims/ep_orig.py`).
- **Counts** come from scratch scripts in `/tmp` (not saved in the repo). Every count below was run, not copied from the plan.

## 1. The sample frame (44 rows)

The other worker's `tools/live_policy/semantic/sample_frame.txt` lists the same 44 (run, stage) pairs; I checked it against this table (same pairs).

Run names for the short ids:

| Short id | Run folder under `LC` | Kind |
|---|---|---|
| O-00853-s42 | `e1_00853_s42_official_60m` | official |
| O-00853-s43 | `e1_00853_s43_official_60m` | official |
| O-00853-s44 | `e1_00853_s44_official_60m` | official |
| F-00853-s42 | `e2_00853_s42_filter_only_60m` | filter_only |
| F-00853-s43 | `e2_00853_s43_filter_only_60m` | filter_only |
| F-00853-s44 | `e2_00853_s44_filter_only_60m` | filter_only |
| O-00871-s42 | `e1_00871_s42_official_60m` | official |
| O-00871-s43 | `e1_00871_s43_official_60m` | official |
| O-00871-s44 | `e1_00871_s44_official_60m` | official |
| F-00871-s42 | `e2_00871_s42_filter_only_60m` | filter_only |
| F-00871-s43 | `e2_00871_s43_filter_only_60m` | filter_only |
| F-00871-s44 | `e2_00871_s44_filter_only_60m` | filter_only |
| FA1-00871-s42 | `e1_00871_s42_official_60m_FAILED_ATTEMPT1_false_exit_host_oom` | official, failed attempt 1 (FA1) |
| FA1-00853-s42 | `e1_00853_s42_official_60m_FAILED_ATTEMPT1_false_exit_host_oom` | official, failed attempt 1 (FA1) |
| FA1-00853-s43 | `e1_00853_s43_official_60m_FAILED_ATTEMPT1_false_exit_host_oom` | official, failed attempt 1 (FA1) |

Stage folder path = `LC/<run folder>/stages/<k>`.

Columns: `obs0` = rooms/objects in `original_graph0` (the input to track-0 members). `t0` and `t1` = member ids on disk for track 0 and track 1. `raw` = ids under `live_policy_raw/attempt_0` (filter_only only). `Gem` = Gemini member ids for FA1 rows (see section 4).

| # | Run | Stage | obs0 | t0 | t1 | raw | Gem | Flag |
|---|---|---|---|---|---|---|---|---|
| 1 | O-00853-s42 | 3 | 10/10 | 0,1,2,3 | 4,5,6,7 |  |  |  |
| 2 | O-00853-s42 | 8 | 10/18 | 0,1,2,3 | 4,5,6 |  |  |  |
| 3 | O-00853-s42 | 13 | 8/32 | 0,1,2 | 4,5,6 |  |  | t0 has 3 of 4 |
| 4 | O-00853-s43 | 3 | 9/14 | 0,1,2,3 | 4,5,6,7 |  |  |  |
| 5 | O-00853-s43 | 8 | 8/17 | 0,1,2,3 | 4,5,6 |  |  |  |
| 6 | O-00853-s43 | 13 | 6/31 | 0,1,2,3 | 4,5,6,7 |  |  |  |
| 7 | O-00853-s44 | 3 | 9/10 | 0,1,2,3 | 4,5,6,7 |  |  |  |
| 8 | O-00853-s44 | 8 | 7/15 | 1,2,3 | 4,5,6,7 |  |  | t0 has 3 of 4 |
| 9 | O-00853-s44 | 13 | 6/34 | 0,1,2,3 | 5,6,7 |  |  |  |
| 10 | F-00853-s42 | 3 | 7/13 | 0,1,2,3 | 5,6,7 | 0: 0,1,2,3,5,6,7 |  |  |
| 11 | F-00853-s42 | 8 | 8/39 | 0,2,3 | 4,5,6,7 | 0: 0,2,3,4,5,6,7 |  | t0 has 3 of 4 |
| 12 | F-00853-s42 | 13 | 9/54 | 0,1,2,3 | 4,5,6,7 | 0: 0,1,2,3,4,5,6,7 |  |  |
| 13 | F-00853-s43 | 3 | 10/12 | 1,2,3 | 4,5,6,7 | 0: 1,2,3,4,5,6,7 |  | t0 has 3 of 4 |
| 14 | F-00853-s43 | 8 | 12/19 | 0,1,2,3 | 4,5,6,7 | 0: 0,1,2,3,4,5,6,7 |  |  |
| 15 | F-00853-s43 | 13 | 9/40 | 0,1,2,3 | 4,5,6 | 0: 0,1,2,3,4,5,6 |  |  |
| 16 | F-00853-s44 | 3 | 7/15 | 0,1,2,3 | 4,5 | 0: 0,1,2,3,4,5 |  |  |
| 17 | F-00853-s44 | 8 | 9/37 | 1,2 | 4,5,7 | 0: 1,2,4,5,7 |  | t0 has 2 of 4 |
| 18 | F-00853-s44 | 13 | 11/59 | 0,1,2,3 | 4,5 | 0: 0,1,2,3,4,5 |  |  |
| 19 | O-00871-s42 | 3 | 13/22 | 1,2 | 4,5,6,7 |  |  | t0 has 2 of 4 |
| 20 | O-00871-s42 | 8 | 12/47 | 0,1,2 | 4,5,6,7 |  |  | t0 has 3 of 4 |
| 21 | O-00871-s42 | 13 | 16/61 | 0,1,2,3 | 4,5,6 |  |  |  |
| 22 | O-00871-s43 | 3 | 7/25 | 0,1,2,3 | 4,5,6,7 |  |  |  |
| 23 | O-00871-s43 | 8 | 10/50 | 0,1,2,3 | 4,5,6,7 |  |  |  |
| 24 | O-00871-s43 | 13 | 13/61 | 0,1,3 | 4,5,6,7 |  |  | t0 has 3 of 4 |
| 25 | O-00871-s44 | 3 | 11/19 | 0,1,2 | 4,5,6,7 |  |  | t0 has 3 of 4 |
| 26 | O-00871-s44 | 8 | 9/34 | 0,1,2,3 | 4,6,7 |  |  |  |
| 27 | O-00871-s44 | 13 | 14/54 | 1,2,3 | 4,5,6,7 |  |  | t0 has 3 of 4 |
| 28 | F-00871-s42 | 3 | 11/21 | 0,1,2,3 | 4,5,6,7 | 0: 0,1,2,3,4,5,6,7 |  |  |
| 29 | F-00871-s42 | 8 | 10/42 | 0,1,2,3 | 4,5,6,7 | 0: 0,1,2,3,4,5,6,7 |  |  |
| 30 | F-00871-s42 | 13 | 11/55 | 0,1 | 4,5,6,7 | 0: 0,1,4,5,6,7 |  | t0 has 2 of 4 |
| 31 | F-00871-s43 | 3 | 12/18 | 0,1,2,3 | 4,5,6 | 0: 0,1,2,3,4,5,6 |  |  |
| 32 | F-00871-s43 | 8 | 9/31 | 1,2,3 | 4,5,6,7 | 0: 1,2,3,4,5,6,7 |  | t0 has 3 of 4 |
| 33 | F-00871-s43 | 13 | 8/35 | 0,1,2,3 | 4,5,6 | 0: 0,1,2,3,4,5,6 |  |  |
| 34 | F-00871-s44 | 3 | 8/30 | 1,2,3 | 4,5,6,7 | 0: 1,2,3,4,5,6,7 |  | t0 has 3 of 4 |
| 35 | F-00871-s44 | 8 | 8/33 | 0,1,2,3 | 4,5,6,7 | 0: 0,1,2,3,4,5,6,7 |  |  |
| 36 | F-00871-s44 | 13 | 9/40 | 0,1,2,3 | 4,5,6,7 | 0: 0,1,2,3,4,5,6,7 |  |  |
| 37 | FA1-00871-s42 | 2 | 9/18 | 0,1,2,3 | 5,6,7 |  | 0,1,2,3 |  |
| 38 | FA1-00871-s42 | 3 | 8/23 | 0,1,2,3 | 5,6,7 |  | 0,1,2 | Gemini has 3 of 4 |
| 39 | FA1-00871-s42 | 5 | 9/42 | 0,1,2,3 | 5,7 |  | 0,1,2,3 |  |
| 40 | FA1-00871-s42 | 6 | 11/45 | 0,1,2,3 | 4,5,6,7 |  | 0,1,3 | Gemini has 3 of 4 |
| 41 | FA1-00853-s42 | 4 | 10/12 | 0,1,2,3 | 4,5,7 |  | 0,1,2,3 |  |
| 42 | FA1-00853-s43 | 1 | 6/8 | 0,1,2,3 | 4,5,6,7 |  | 0,1,2,3 |  |
| 43 | FA1-00853-s43 | 2 | 6/10 | 0,1,2,3 | 4,5,6,7 |  | 0,2,3 | Gemini has 3 of 4 |
| 44 | FA1-00853-s43 | 5 | 7/22 | 0,1,2,3 | 4,6 |  | 0,1,2,3 |  |

**What every row has.** `original_graph0.yaml`, `original_graph1.yaml`, `executed_path.json` (also for every stage 1..k), `navigation_stats.json`, `live_policy.jsonl`, `node_mapping_graph0/1.yaml`, `path_log.json`, `pose_log.json`. Checked by script: no row lacks any of them.

**Member counts.**
- 36 DeepSeek rows: 128 track-0 members of 144 possible (23 rows with 4, 10 with 3, 3 with 2); 129 track-1 members.
- 8 FA1 rows: 32 of 32 DeepSeek track-0 members (all rows have 4).
- **13 of 44 rows have fewer than 4 track-0 members** (the 13 rows flagged above). The paper-style "1-of-4 / 2-of-4" test has fewer than 4 members on 10 DeepSeek rows (3 members) and 3 rows (2 members).
- filter_only: the raw ids equal the on-disk ids in all 18 rows. The on-disk file is the raw file minus the nodes the validator removed (section 2.3). All 18 filter_only rows have one attempt only (`attempt_0`).
- Stage k+1 has an observed graph on disk for 44 of 44 rows (missing: none); stage k+2 for 40 of 44 (missing: [('O-00853-s44', 13), ('F-00871-s44', 13), ('FA1-00853-s42', 4), ('FA1-00853-s43', 5)]).

**Flags.** No row lacks a file. The flags are member shortfalls only:

| # | Run | Stage | Flag |
|---|---|---|---|
| 3 | O-00853-s42 | 13 | t0 has 3 of 4 |
| 8 | O-00853-s44 | 8 | t0 has 3 of 4 |
| 11 | F-00853-s42 | 8 | t0 has 3 of 4 |
| 13 | F-00853-s43 | 3 | t0 has 3 of 4 |
| 17 | F-00853-s44 | 8 | t0 has 2 of 4 |
| 19 | O-00871-s42 | 3 | t0 has 2 of 4 |
| 20 | O-00871-s42 | 8 | t0 has 3 of 4 |
| 24 | O-00871-s43 | 13 | t0 has 3 of 4 |
| 25 | O-00871-s44 | 3 | t0 has 3 of 4 |
| 27 | O-00871-s44 | 13 | t0 has 3 of 4 |
| 30 | F-00871-s42 | 13 | t0 has 2 of 4 |
| 32 | F-00871-s43 | 8 | t0 has 3 of 4 |
| 34 | F-00871-s44 | 3 | t0 has 3 of 4 |
| 38 | FA1-00871-s42 | 3 | Gemini has 3 of 4 |
| 40 | FA1-00871-s42 | 6 | Gemini has 3 of 4 |
| 43 | FA1-00853-s43 | 2 | Gemini has 3 of 4 |

**Official stages 3, 8, 13 in `O-00853-s44`.** The run `e1_00853_s44_official_60m` is the excluded attempt (stopped at 46.8 m; `LP/results_2026-10-31/run_table.csv`). Its `_rerun1` folder also exists and is not in the frame.

## 2. File schemas (one real example each)

### 2.1 Observed scene graph: `habitat_scene_graph_original_graph{0,1}.yaml`

Top-level keys: `edges`, `nodes`. Example: `LC/e1_00853_s42_official_60m/stages/3/habitat_scene_graph_original_graph0.yaml` (35 nodes, 30 edges). Saved with `yaml.safe_dump`, so keys are in alphabetical order. One node of each type:

```yaml
- dimension: '[0.774, 1.151, 0.323]'
  id: 0
  is_predicted: false
  name: duvet
  node_type: object
  orientation: '[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]'
  position: '[0.422, -5.243, 0.682]'
- id: 25
  name: an image of a bedroom
  node_type: room
  position: '[2.127, -4.476, 1.315]'
- dimension: '[0.407, 0.118, 2.461]'
  id: 18
  is_predicted: false
  name: Wall
  node_type: structure
  orientation: '[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]'
  position: '[0.294, -1.032, 1.076]'
- dimension: '[1.7, 1.6, 0.9]'
  id: 4
  is_predicted: false
  name: Nothing
  node_type: nothing
  orientation: '[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]'
  position: '[2.25, -3.9, 1.45]'
```

Edges are `[a, b]` pairs of node ids, for example `[[0, 30], [1, 30], [2, 25], [3, 25]]`. In the example, the first id is an object and the second a room, or both ids are rooms (**inferred** from the examples; no edge type field).

| Field | Type | Meaning |
|---|---|---|
| `id` | int | Unique in the graph. New nodes in a completion take ids above the observed maximum. |
| `node_type` | str | `object`, `room`, `structure`, `nothing`. Counts over all observed graphs of the counted e1 official runs: object 6,964; structure 5,555; nothing 4,513; room 2,128 (graph0 and graph1 of every stage of the 7 `e1_*_official_60m` folders). |
| `name` | str | Objects: a detector label (33 of the 34 distinct observed labels are in the 52-word vocabulary; the other is `door`). Rooms: `an image of a <type>`. Structure: `Wall`, `Window`, `Curtain`, `Blind`. Nothing: `Nothing`. |
| `position` | str `"[x, y, z]"` | Centre, metres, **pipeline frame** (z up; camera at z = 1.1; floor near the start at z = 0). Stored as a string; parse with `ast.literal_eval` (`live_policy._vec`, line 174). |
| `dimension` | str `"[dx, dy, dz]"` | Full extents in the world axes. Present on object, structure, nothing. Absent on rooms. |
| `orientation` | str 3x3 | Identity matrix in every example. Present where `dimension` is present. |
| `is_predicted` | bool | `false` on every observed object, structure and nothing node. Absent on rooms. |
| parent room | edge | No parent field. The parent of an object is the room at the other end of its edge. |

Rooms carry only `id`, `name`, `node_type`, `position`. Observed room names (both tracks, counted e1 official and e2 stages): `an image of a` bedroom, hallway, bathroom, closet, laundry room, living room, dining room, kitchen. The prompt says "Scene has no outdoor space or dining room", yet the detector produced 11 dining-room nodes.

`node_mapping_graph{0,1}.yaml` maps each graph id to a Hydra node symbol (`0: 7998392938210001101`, ...). It carries no semantics.

### 2.2 Member completion: `habitat_scene_graph_new_graph_<id>.yaml`

Same schema as the observed graph. Example: `LC/e1_00853_s42_official_60m/stages/3/habitat_scene_graph_new_graph_0.yaml` has 49 nodes and 44 edges: the 35 observed nodes, 14 new nodes, and new edges. Some new nodes:

```yaml
- dimension: '[1.0, 0.5, 1.0]'
  id: 35
  is_predicted: true
  name: dresser
  node_type: object
  orientation: '[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]'
  position: '[3.5, -5.0, 0.5]'
- dimension: '[1.5, 1.5, 0.04]'
  id: 36
  is_predicted: true
  name: rug
  node_type: object
  orientation: '[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]'
  position: '[2.5, -5.0, 0.02]'
- id: 42
  name: an image of a bedroom
  node_type: room
  position: '[5.5, -4.5, 1.3]'
```
New edges: `[[35, 25], [36, 25], [37, 29], [38, 29], [39, 30], [40, 27]]` (new object -> room).

**Telling new from observed.** Counts over every member on disk of the e1 official runs (1,043 members, both tracks, failed and aborted runs included), the filter_only raw members (753), and Gemini (29 members, track 0). "Far" = more than 0.5 m in xy from every observed *object* node of the member's own track.

| Rule | official | filter_only raw | Gemini |
|---|---|---|---|
| Members counted | 1043 | 753 | 29 |
| New room: id not in observed graph | 1353 | 917 | 44 |
| New object, rule B: id not in observed and far | 12175 | 8714 | 350 |
| New object, plan rule A: `is_predicted` true and far | 12179 | 8648 | 0 |
| A and B agree (new id, flagged, far) | 12119 | 8638 | 0 |
| A only: flagged and far, but the id is an observed id | 60 | 10 | 0 |
| B only: new id, far, `is_predicted` not true | 56 | 76 | 350 |
| Room nodes that carry `is_predicted: true` | 26 | 27 | 0 |
| Observed id reused by a node of another type | 20 | 6 | 0 |
| Observed id kept, name differs (includes the type changes) | 63 | 11 | 0 |

- **Gemini sets `is_predicted: false` on every new object** (example: `HW/gemini_static/<FA1 871 s42>/2/gemini_new_graph_0.yaml`, node 49 `nightstand`). Rule A finds no Gemini object. Use rule B (id based) for Gemini.
- DeepSeek sets `is_predicted: true` on new objects. Even so, 60 official and 10 filter_only members hold a flagged object that reuses an observed id (rule A counts it, rule B does not), and 56 official and 76 filter_only members hold a new-id object without the flag. When a member reuses an observed id for another node type, the new node is an object: 20 official cases (13 over a `nothing`, 7 over a `structure`) and 6 filter_only cases (3 `nothing`, 1 `structure`, 2 `room`). Same-type renames of an observed object or room: 43 official, 5 filter_only. No room node reused an observed non-room id.
- Rooms: the plan says rooms carry no `is_predicted`. 26 official and 27 filter_only room nodes carry `is_predicted: true`. The id rule for rooms is unaffected.
- A union rule (new id OR flagged) is the only one that sees all three models; the choice belongs in the pre-registration.

### 2.3 Raw completions for filter_only: `live_policy_raw/attempt_<n>/habitat_scene_graph_new_graph_<id>.yaml`

Same schema as 2.2. The policy copies the member as the model produced it into `attempt_<n>` (`live_policy.py:125-131, 164-165`), then rewrites the stage file with the validator's keep-set (`write_keep_set_yaml`, `live_policy.py:83-91`). Edges that touch a removed node are dropped. Example: `LC/e2_00853_s42_filter_only_60m/stages/3`, member 0: raw 56 nodes and 47 edges; on disk 54 nodes and 45 edges; removed nodes: id 50 object `dresser` at [-0.1, -3.1, 0.5]; id 51 object `chair` at [0.3, -3.5, 0.4].

- 109 filter_only stages have a `live_policy_raw` folder. 108 have one attempt. `e2_00871_s43_filter_only_60m` stage 15 has five (`attempt_0`..`attempt_4`; the planning step retried). In every stage the last attempt holds the same member ids as the stage files. `stage_precision.py:59-60, 70` also uses the last attempt. **inferred:** the last attempt is the one the planner used.
- Official, placebo and oracle runs have no `live_policy_raw` (the policy keeps everything or makes the files itself); their stage files are the raw completions.

### 2.4 Robot positions and path files

**`executed_path.json`** (`ep_orig.py:877-899`): keys `habitat_frame_path` and `world_frame_path`, two lists of `[x, y, z]` with the same length. Example (`e1_00853_s42_official_60m/stages/3`): 20 points; first point habitat `[-3.473, 1.1, 4.215]`, world `[0.567, -1.307, 1.1]`.
- **Robot positions: `world_frame_path`, in the pipeline frame** (z = 1.1 is the camera). `habitat_frame_path` is the habitat frame (y up).
- The file in stage k holds the walk that ended at stage k (the code writes it to stage k+1 when the walk after stage k's plan ends). **Checked on the 15 run folders of the frame (216 consecutive stage pairs):** the first point of stage k+1's file equals the last point of stage k's file (largest gap 0.000 m). Every row of the frame has a non-empty file in each of stages 1..k. At stage 3 of `e1_00853_s42_official_60m`, `path_log.json` `final_path[0]` equals the last point of the file. `stage_diagnostics.py:4-9` states the same alignment.
- So the robot is at the last point of stage k's file when stage k's members are made. Positions up to stage k = the files of stages 1..k joined. **Stage 0 has no file**; its start point is the first point of stage 1's file (**inferred**). Points are about 0.075 m apart (`MOVE_STEP_M`), not stops. For "stops up to k" the plan can use the last point of each file 1..k plus the start.

**`navigation_stats.json`**: `{"total_path_length_meters": 4.5750000000000055, "total_navigation_time_seconds": 32.55266714096069}` (cumulative path length in metres and navigation time in seconds). In all 216 checked stages the length at stage k equals the summed 3D length of the `world_frame_path` files of stages 1..k (largest difference 0.000 m). The last stage of a run has no file.

**`path_log.json`**: `{"timestamp", "final_path", "final_path_name"}`. Example: `final_path` = two points, `final_path_name` = `["start_position", "semantic uncertain region"]`. `final_path[0]` is the robot at stage k; `final_path[-1]` is the next target.

**`pose_log.json`** is JSON lines (two records in the example, not one object): the first has `timestamp`, `best_sample_poses` (candidate viewpoints `[x, y, z, yaw_deg]`), `best_filtered_poses`; the second has `final_pose`, `new_pose`, `best_ig`.

**`live_policy.jsonl`** (`live_policy.py:146-171`): one JSON line per planning attempt: `ts`, `policy`, `working_dir`, `tracks.<t>.available` (members that survived parsing) and `tracks.<t>.members[]` with `graph_id`, `nodes`, `predicted`, `kept_nodes`, `kept_predicted`, and `llm_wait_s`; filter_only adds `raw_archive`. Example, official stage 3: track 0 has 4 members, track 1 has 4. It counts `is_predicted` nodes, not new ids.

**Run-level files** under `LC/<run>/`: `config/pipeline_config.yaml` (holds `LLM_COMPLETION_PROMPT`, line 68; the room-type hint "Scene may contain more than one bedroom and more than one bathroom" is line 101), `config/run_manifest.txt` (model, provider, caps, md5 of the pinned code), `prompts/prompts_responses.jsonl` (every LLM call: `call_index`, `timestamp`, `model`, `request_contents`, `duration_s`, `response{text, function_calls, usage_metadata}`; 1,121 lines in `e1_00853_s42_official_60m`), `prompts/usage.jsonl` (cost and tokens per call), `logs/`.

## 3. The wider pool

All runs are under `LC/<run>/stages/<k>`. Counts are stage folders, stages with at least one member file, members on disk (both tracks), track-0 members, and stages with `executed_path.json`.

| Run | Group | Stage folders | With members | Members | Track-0 members | With path file |
|---|---|---|---|---|---|---|
| `dryrun_00069_s42_filter_only_10m` | dry run | 1 | 1 | 8 | 4 | 0 |
| `dryrun_b2_00069_s42_placebo_10m` | dry run | 4 | 3 | 24 | 12 | 3 |
| `dryrun_oracle_00871_s42_10m` | dry run | 4 | 3 | 24 | 12 | 3 |
| `e1_00853_s42_official_60m` | official | 19 | 18 | 110 | 59 | 18 |
| `e1_00853_s42_official_60m_FAILED_ATTEMPT1_false_exit_host_oom` | official (failed/aborted) | 6 | 6 | 40 | 21 | 5 |
| `e1_00853_s42_placebo_60m` | placebo | 17 | 16 | 128 | 64 | 16 |
| `e1_00853_s42_placebo_60m_FAILED_ATTEMPT1_retry_loop` | placebo | 4 | 4 | 32 | 16 | 3 |
| `e1_00853_s42_placebo_60m_FAILED_ATTEMPT2_false_exit` | placebo | 2 | 2 | 16 | 8 | 1 |
| `e1_00853_s43_official_60m` | official | 21 | 21 | 151 | 77 | 20 |
| `e1_00853_s43_official_60m_ABORTED_memory` | official (failed/aborted) | 2 | 2 | 13 | 8 | 1 |
| `e1_00853_s43_official_60m_FAILED_ATTEMPT1_false_exit_host_oom` | official (failed/aborted) | 7 | 7 | 48 | 26 | 6 |
| `e1_00853_s43_placebo_60m` | placebo | 18 | 18 | 144 | 72 | 17 |
| `e1_00853_s43_placebo_60m_ABORTED_memory` | placebo | 2 | 2 | 16 | 8 | 1 |
| `e1_00853_s43_placebo_60m_FAILED_ATTEMPT1_false_exit_host_oom` | placebo | 8 | 8 | 60 | 32 | 7 |
| `e1_00853_s44_official_60m` | official | 16 | 15 | 106 | 53 | 15 |
| `e1_00853_s44_official_60m_rerun1` | official | 15 | 14 | 96 | 51 | 14 |
| `e1_00853_s44_placebo_60m` | placebo | 22 | 21 | 168 | 84 | 21 |
| `e1_00871_s42_official_60m` | official | 18 | 17 | 117 | 60 | 17 |
| `e1_00871_s42_official_60m_ABORTED_memory` | official (failed/aborted) | 4 | 4 | 29 | 16 | 3 |
| `e1_00871_s42_official_60m_FAILED_ATTEMPT1_false_exit_host_oom` | official (failed/aborted) | 9 | 9 | 65 | 34 | 8 |
| `e1_00871_s42_placebo_60m` | placebo | 16 | 15 | 120 | 60 | 15 |
| `e1_00871_s42_placebo_60m_ABORTED_memory` | placebo | 7 | 7 | 52 | 28 | 6 |
| `e1_00871_s42_placebo_60m_FAILED_ATTEMPT1_false_exit_host_oom` | placebo | 8 | 8 | 64 | 32 | 7 |
| `e1_00871_s43_official_60m` | official | 19 | 18 | 131 | 63 | 18 |
| `e1_00871_s43_placebo_60m` | placebo | 2 | 2 | 16 | 8 | 1 |
| `e1_00871_s43_placebo_60m_rerun1` | placebo | 13 | 12 | 96 | 48 | 12 |
| `e1_00871_s44_official_60m` | official | 20 | 19 | 137 | 68 | 19 |
| `e1_00871_s44_placebo_60m` | placebo | 29 | 28 | 224 | 112 | 28 |
| `e2_00853_s42_filter_only_60m` | filter_only | 17 | 16 | 111 | 55 | 16 |
| `e2_00853_s42_filter_only_60m_ABORTED_memory` | filter_only (aborted) | 3 | 3 | 22 | 10 | 2 |
| `e2_00853_s43_filter_only_60m` | filter_only | 20 | 19 | 135 | 66 | 19 |
| `e2_00853_s44_filter_only_60m` | filter_only | 21 | 20 | 138 | 76 | 20 |
| `e2_00871_s42_filter_only_60m` | filter_only | 21 | 20 | 138 | 70 | 20 |
| `e2_00871_s43_filter_only_60m` | filter_only | 16 | 16 | 108 | 57 | 15 |
| `e2_00871_s44_filter_only_60m` | filter_only | 16 | 15 | 101 | 48 | 15 |
| `e3_00853_s42_oracle_visible_60m_FAILED_ATTEMPT1_gate` | oracle_visible | 16 | 15 | 120 | 60 | 15 |
| `e3_00853_s42_oracle_visible_60m_rerun1` | oracle_visible | 18 | 17 | 136 | 68 | 17 |
| `e3_00853_s43_oracle_visible_60m` | oracle_visible | 17 | 17 | 136 | 68 | 16 |
| `e3_00871_s42_oracle_visible_60m` | oracle_visible | 14 | 13 | 104 | 52 | 13 |
| `e3_00871_s43_oracle_visible_60m` | oracle_visible | 13 | 12 | 96 | 48 | 12 |
| `e3_00871_s44_oracle_visible_60m` | oracle_visible | 18 | 17 | 136 | 68 | 17 |
| `e5_00853_s42_placebo_15m_q1` | placebo 15 m | 13 | 13 | 104 | 52 | 12 |
| `e5_00853_s42_placebo_15m_q2` | placebo 15 m | 7 | 6 | 48 | 24 | 6 |
| `e5_00853_s42_placebo_15m_q3` | placebo 15 m | 7 | 6 | 48 | 24 | 6 |

Other folders in `LC`: `hm3d_refs_work` (section 4, 5), `EXCLUDED_*.json` markers, `sched*.json`, `runner_*.log`, `DEVIATIONS.md`, the E1-E3 pre-registrations.

**DeepSeek totals** (stages with at least one member; members counted from the last attempt for filter_only):

| Group | Stages | Members | Track 0 | Track 1 | New objects (rule B, all members) | New rooms |
|---|---|---|---|---|---|---|
| official, 7 main folders | 122 | 848 | 431 | 417 | 10336 | 1082 |
| official, failed/aborted folders (5) | 28 | 195 | 105 | 90 | 2271 | 271 |
| **official total** | 150 | 1043 | 536 | 507 | 12607 | 1353 |
| filter_only, 6 main folders (raw) | 106 | 731 | 372 | 359 | 8840 | 889 |
| filter_only, 1 aborted folder (raw) | 3 | 22 | 10 | 12 | 265 | 28 |
| **filter_only total** | 109 | 753 | 382 | 371 | 9105 | 917 |
| placebo (e1, all folders) | 143 | 1136 | 572 | 564 | 11468 | 1851 |
| placebo 15 m (e5) | 25 | 200 | 100 | 100 | 1988 | 324 |
| oracle_visible (e3, all folders) | 91 | 728 | 364 | 364 | 7324 | 1179 |

**Do the plan's counts hold?** Yes. 150 official + 109 filter_only = 259 stage folders that hold at least one member file. There are 270 stage folders in all: the last stage of 11 runs holds an observed graph and a path but no completion. Of the 259, one official stage has no track-0 member (`e1_00853_s42_official_60m` stage 7: ids 5 and 7 only).

**Placebo.** Runs `LC/e1_*_placebo_60m*` (and `e5_*`) hold members made by `live_policy.no_llm_completions` (`live_policy.py:385-442`): `placebo_graph(observed, rng, calib)` (`live_policy.py:203-277`), calibration `LP/placebo_calibration.json` (version 2; 20 raw DeepSeek completions from a 00069 dry run `dryrun2_00069_s42_filter_only_10m`, which is not in the copy; keys `labels` (30 strings), `room_names` (3), `dims_pool`, radii). The rng seed is `[SEED, stage, graph_id]`, plus `[attempt]` or `[attempt, rerun]` on a retry. So placebo draws for any observed graph can be regenerated with recorded seeds. Placebo members sit on the placebo run's own observed graphs, not on the DeepSeek inputs.
**Oracle.** `LC/e3_*_oracle_visible_*`: `oracle_graph` (`live_policy.py:315-360`) draws true unmapped objects from `LP/oracle_sets.json`; rooms come from the placebo code. 6 folders, 91 stages with members; `run_table.csv` marks which counted.
**Frontier.** No LLM members. `LC/frontier_seeds/e4_*_frontier_60m` (6 runs, 22-46 stage folders each); `PS/frontier_seeds/e7_*_frontier_end` (14 folders, 11-80 stages, including 5 FAILED_ATTEMPT folders); `PS/scene00853_frontier_reference/stages` (35 stages) and `PS/scene00871_frontier_reference/stages` (56); `LC` keeps only the final reference stage (33 and 54). They hold observed graphs (graph0 and graph1) and paths. `PS/apr/apr_*` (4 tour runs, 67-86 stage folders) hold no members; paths and graphs only on some stages.
**Dry runs** (scene 00069, not in the frame): `dryrun_00069_s42_filter_only_10m` (1 stage, 8 members, with raw), `dryrun_b2_00069_s42_placebo_10m`, `dryrun_oracle_00871_s42_10m`; `dryrun_b_...` has no stages.
**September Gemini campaign** (scene 00069): stage graphs stayed on the host; the repo mirrors only derived JSON (`docs/RESULTS.md` lines 24, 147, 200). Not usable for this test.

## 4. Gemini

**Code.** `LP/gemini_static.py` ran on the host. For each (run, stage) it copies `habitat_scene_graph_original_graph0.yaml` and DeepSeek members 0-3, renders slices with `create_scene_slices` from the observed graph (lines 112-118; the slices saved in the run were overwritten), and runs 4 Gemini members (`gemini-3.8-flash`, seed = run seed + member, prompt = the run's `LLM_COMPLETION_PROMPT`; lines 93-122). Track 0 only. `LP/gemini_static_score.py` scores them (`score`, lines 60-70).

**Where.** `HW/gemini_static` ($9.79; cap $10), `HW/gemini_static2` ($29.81; cap $30), `HW/gemini_static_test` ($0.24; no completions). Layout: `<folder>/<run>/<stage>/` with `habitat_scene_graph_original_graph0.yaml`, `deepseek_new_graph_{0..3}.yaml`, `gemini_new_graph_{0..3}.yaml`, `input_slices/`. Also `llm_log/prompts_responses.jsonl` (all calls: `call_index`, `timestamp`, `model`, `provider`, `request_contents[]` with a text `repr`, `duration_s`, `response{text, function_calls[], usage_metadata}`; 277 lines in `gemini_static`), `gemini_calls.jsonl` (per call: latency, tokens, cost), `summary.json`.

**Completion format.** Same YAML schema as section 2.2, saved after the author's `parse_response`. New nodes take ids above the observed maximum, rooms are `an image of a <type>`, new objects have `is_predicted: false` (section 2.2), no `live_policy.jsonl`.

**Inputs and members (8 frame inputs).** Use `gemini_static2` for 00871 s42 stage 5; in `gemini_static` that stage has no Gemini members (every call hit the $10 cap).

| Folder | Run | Stage | Gemini members | Slices (.jpg) | Note |
|---|---|---|---|---|---|
| `gemini_static` | FA1-00871-s42 | 2 | 0,1,2,3 | 6 |  |
| `gemini_static` | FA1-00871-s42 | 3 | 0,1,2 | 6 | member(s) failed with `TypeError` in `parse_response` |
| `gemini_static` | FA1-00871-s42 | 5 | - | 6 | cap hit; use `gemini_static2` |
| `gemini_static2` | FA1-00853-s42 | 4 | 0,1,2,3 | 6 |  |
| `gemini_static2` | FA1-00853-s43 | 1 | 0,1,2,3 | 6 |  |
| `gemini_static2` | FA1-00853-s43 | 2 | 0,2,3 | 6 | member(s) failed with `TypeError` in `parse_response` |
| `gemini_static2` | FA1-00853-s43 | 5 | 0,1,2,3 | 6 |  |
| `gemini_static2` | FA1-00853-s43 | 6 | - | 6 | cap hit; no Gemini members; not in the frame |
| `gemini_static2` | FA1-00871-s42 | 5 | 0,1,2,3 | 6 |  |
| `gemini_static2` | FA1-00871-s42 | 6 | 0,1,3 | 6 | member(s) failed with `TypeError` in `parse_response` |

Frame totals: 8 inputs, 29 Gemini members of 32 (stages 3 and 6 of FA1-871-s42 and stage 2 of FA1-853-s43 have 3). The 6 slices per stage are `scene_z_<lo>_to_<hi>.jpg` for z bands 0.0-0.3, 0.3-0.5, 0.5-1.5, 1.5-2.0, 2.0-2.5, 2.5-3.0 m (about 0.5-0.6 MB each). **The 66 slices are on the laptop** (11 stage folders x 6), though the brief said no image slices.

## 5. Truth files

All in `HW` (the repo holds none of them except `oracle_sets.json` and the wall maps). Built on the host by `HW/extract_objects.py`, `extract_semantic_aabb.py`, `build_reference.py` from HM3D `00853-5cdEh9F2hJL` and `00871-VBzV5z6i1WS` (val split, hm3d-0.2). sha256 (first 16 hex) in the last column.

| File | Content and schema | 00853 | 00871 | sha256 |
|---|---|---|---|---|
| `<scene>_raw_objects.json` | keys `scene, source, objects, regions, navmesh_bounds, habitat_objects_with_nonzero_aabb, pipeline_initial_agent_state`. `objects[]`: `id, raw_id, category, habitat_aabb_center, habitat_aabb_size, region_id`. **Every object has `category` and `region_id`** (string `_<n>`; `_-1` for `Unknown_0`). All AABB fields are 0 (habitat_sim 0.3.3 gives none). `regions[]`: `id, n_objects`. | 529 objects, 124 categories, 13 region ids (12 real + `_-1`) | 850 objects, 140 categories, 17 region ids (16 real + `_-1`) | d391ee818378191f / 99cc24ecd4abe211 |
| `<scene>_semantic_geometry.json` | keys `scene, n_objects, duplicate_colour_groups, unmatched_tri, total_tri, objects`. `objects{id: {id, name, region (int), n_tri, area, hab_min, hab_max, world_min, world_max}}`; 3 or 16 objects have only `id, name, region, n_tri` (0 triangles). `world_*` are in the pipeline frame (axis-aligned box of the object's own vertices). Ids start at 1. | 528 objects, 525 with geometry, 4,251 of 385,691 triangles unmatched | 849 objects, 833 with geometry, 19,459 of 398,937 unmatched, 1 duplicate colour group | 72d8b210afae6200 / c3feb2c924a62064 |
| `<scene>_semantic_vertices_hab.npy` | float32 `(N, 3)`, mesh vertices per primitive in the **habitat frame**. No faces, no object id, no region id (`extract_semantic_aabb.py:115, 141`). It cannot give a floor polygon. | (1,156,876, 3) | (1,196,579, 3) | 0ca88990d48711b1 / 9fada603c8391584 |
| `<scene>_hm3d_reference.yaml` | Author-format graph in the pipeline frame. Objects: only categories that map into the 52-word vocabulary (primary tier), `position` = centre of the world box, `dimension` = its extents. Rooms: one per region, `name: hm3d region <n> (untyped)`, `position` = centre of the box that unions **all** objects of the region with geometry. Edges: `[object, room]`. | 180 objects, 12 rooms, 180 edges | 232 objects, 16 rooms, 232 edges | bf3e326259832195 / f0ce2ddfd0bed4e6 |
| `<scene>_hm3d_reference_extended.yaml` | Same, plus the extended tier (e.g. `bed` -> `duvet`). Sensitivity only. | 225 objects, 12 rooms | 290 objects, 16 rooms | - |
| `<scene>_hm3d_reference_summary.json` | Provenance. `variants.primary.node_provenance[str(i)]` = `{hm3d_id, raw_category, label, tier, hm3d_region, n_tri, within_3m_xy_of_run_path}` for reference object i. **This gives a region id per reference object.** Also `frame`, `excluded_door_objects`, `annotation_objects_without_geometry`. It also holds pipeline-versus-reference scores (not read here). | tier counts: 102 exact, 78 synonym | 149 exact, 83 synonym | 9cd17f3d5e3f8e5c / 36955bd0a65af1c2 |
| `label_mapping.json` | keys `vocab_path, vocab, n_vocab, tables, notes, scenes`. `vocab` = the 52 detector labels (section 6.1). `tables`: `synonym_primary` (42), `extended_sensitivity_only` (25), `door_excluded` (4), `structural_never_mapped` (25). `scenes.<s>.mapping_table[]`: `raw, count, count_with_geometry, primary_label, primary_tier, extended_label, extended_tier`. | 123 distinct raw names; 180 mapped (primary, with geometry); 346 unmapped | 139 distinct names; 232 mapped; 615 unmapped | 6035b772d0bf04e3 |
| `frame_transform.json` | per scene `code_R` (3x3), `code_t` (3), `init`, `runs{...fit_R, fit_t, code_resid_max}`. | t = (4.636, -4.950, 0) | t = (-3.245, 2.038, 0) | 679b224c7c523b4e |
| `LP/oracle_sets.json` | keys `source, scenes`; `scenes["853"|"871"]` = `{scene, file, sha256, n_objects, objects[]}`; object = `{name, position[3], dimension[3]}` in the pipeline frame. **No region id and no raw category.** Same order as the reference objects (**inferred** from `build_oracle_sets.py:28-38`). Three identical copies (`LP`, `LP/results_2026-10-31`, off-host `tools/live_policy`). | 180 objects, 29 labels | 232 objects, 34 labels | a7b35313bb9c0f9e |
| `REPO/tools/live_policy/review_2026-10-29/bench/walls/<scene>_walls.npz` | Wall maps, **not** region footprints: `occ` uint8 `(3, nx, ny)` for planes z = 0.6, 1.1, 1.6 m; `heights`, `origin` (x, y of cell 0), `res` 0.05. Index `occ[k, i, j]`: `i = floor((x - origin_x) / res)`, `j = floor((y - origin_y) / res)` (`slice_walls.py:88-89`). Pipeline frame. Made from the semantic mesh by `slice_walls.py`. | (3, 323, 422); origin (-2.9, -18.25) | (3, 379, 504); origin (-7.8, -8.45) | - |

**Other files.** No separate walls file exists beyond the `.npz` maps. The 52-word vocabulary file `objects_habitat_apartment.yaml` is **only on the host** (`/workspace/catkin_ws/src/active_semantic_perception/task_def/`); its 52 words are copied into `label_mapping.json` `vocab`. `synonym_primary` is the table of raw HM3D names that name the same concept as a vocabulary label, or an unambiguous sub-type (`couch` -> `sofa`, `kitchen cabinet` -> `cabinet`, `tv` -> `television`); the primary reference uses exact + synonym (`hm3d_labels.py:13-36`). `extended_sensitivity_only` holds looser pairs (`bed` -> `duvet`); `STRUCTURAL` names (`wall`, `floor`, `ceiling`, ...) never map; `door` is excluded.

### 5.1 Regions

Regions are numbers only. HM3D `semantic.txt` carries no region names; habitat gives no region category or box (`extract_objects.py` header). The reference rooms are named `hm3d region <n> (untyped)`. **00853 has 12 regions (ids 1-12); 00871 has 16 (ids 0-15)**, plus the sentinel `_-1` that holds only `Unknown_0` (no geometry).

**Footprints on the laptop: boxes only, no polygons and no triangles.** Per region, `semantic_geometry.json` gives: a box per object (world frame), so a union box per region (the reference room centre uses this and includes walls and ceilings); and one object named `floor` per region (two in 00871 regions 6 and 7), with `n_tri`, `area` (summed triangle area, m2) and its own box. **00871 region 9 has no floor object with geometry.** The floor `area` can be below the box area because some triangles are unmatched (**inferred**). A true floor polygon needs the semantic mesh (host).

**Scene 00853** (boxes in the pipeline frame, metres; "all-object box" includes walls):

| Region | Objects | With geometry | All-object box | Floor box | Floor area m2 | Whole-token marker matches (plan list) |
|---|---|---|---|---|---|---|
| 1 | 51 | 51 | x[-1.3,2.7] y[-0.6,1.8] | x[-0.4,1.7] y[-0.6,1.5] | 2.6 | bathroom: bathtub, shower floor, shower knob, shower wall, shower wall cubby, toilet, toilet brush holder, wall toilet paper |
| 2 | 25 | 25 | x[-1.4,0.6] y[-2.4,-0.1] | x[-0.9,0.5] y[-2.4,-0.1] | 2.4 | - |
| 3 | 71 | 70 | x[0.5,2.6] y[-2.5,-0.3] | x[0.5,2.5] y[-2.3,-0.7] | 1.0 | - |
| 4 | 45 | 45 | x[-0.9,3.9] y[-6.8,-2.3] | x[-0.8,3.9] y[-6.5,-2.3] | 11.1 | bedroom: bed |
| 5 | 81 | 81 | x[-1.9,5.6] y[-14.3,-3.8] | x[-1.9,5.5] y[-14.2,-3.9] | 29.7 | living: l-shaped sofa; dining: dining table |
| 6 | 11 | 11 | x[4.9,7.1] y[-12.9,-10.0] | x[4.9,7.1] y[-12.9,-10.0] | 3.6 | - |
| 7 | 58 | 58 | x[3.1,7.6] y[-16.9,-12.0] | x[3.2,7.5] y[-16.9,-12.2] | 12.3 | kitchen: oven and stove |
| 8 | 64 | 64 | x[6.8,11.9] y[-17.2,-12.8] | x[7.0,11.5] y[-17.0,-12.8] | 9.7 | living: sofa |
| 9 | 17 | 17 | x[5.0,7.9] y[-10.3,-8.2] | x[5.9,7.9] y[-10.2,-8.2] | 3.3 | laundry: washing machine |
| 10 | 39 | 38 | x[5.4,7.5] y[-8.3,-4.9] | x[5.6,7.2] y[-8.3,-5.9] | 1.7 | bathroom: shower bar, shower door frame, shower floor, shower wall, shower wall cubby, toilet, toilet brush, wall toilet paper |
| 11 | 26 | 26 | x[7.8,12.2] y[-9.4,-5.2] | x[7.9,11.8] y[-9.2,-5.2] | 12.3 | - |
| 12 | 40 | 39 | x[7.8,11.8] y[-12.9,-9.3] | x[7.8,11.7] y[-12.8,-9.4] | 6.9 | bedroom: bed |

**Scene 00871** (boxes in the pipeline frame, metres; "all-object box" includes walls):

| Region | Objects | With geometry | All-object box | Floor box | Floor area m2 | Whole-token marker matches (plan list) |
|---|---|---|---|---|---|---|
| 0 | 93 | 91 | x[-2.2,2.8] y[5.9,10.4] | x[-2.2,2.7] y[6.1,10.3] | 10.6 | bedroom: bed, bed stand |
| 1 | 9 | 9 | x[-3.8,-1.3] y[6.9,8.1] | x[-3.7,-1.3] y[6.9,8.1] | 1.8 | - |
| 2 | 9 | 9 | x[-3.7,-2.1] y[6.1,7.1] | x[-3.6,-2.4] y[6.2,6.9] | 0.4 | - |
| 3 | 35 | 35 | x[-3.6,-2.1] y[7.8,9.9] | x[-3.3,-2.1] y[7.8,9.5] | 1.0 | - |
| 4 | 103 | 94 | x[-6.6,-3.6] y[6.2,10.0] | x[-5.7,-3.6] y[7.0,9.5] | 1.9 | bathroom: bathtub, bathtub utensil, shower ceiling, shower dial, shower door, shower door frame, shower floor, shower tap, shower wall |
| 5 | 5 | 5 | x[-6.3,-4.8] y[7.1,8.1] | x[-6.2,-5.3] y[7.1,7.7] | 0.2 | - |
| 6 | 111 | 111 | x[-6.8,2.6] y[-1.2,6.1] | x[-5.2,2.6] y[-1.2,6.1] | 31.4 | living: couch, sofa chair |
| 7 | 110 | 110 | x[-2.4,4.3] y[-7.1,2.8] | x[-2.4,4.2] y[-7.1,2.7] | 31.2 | kitchen: oven, stovetop; laundry: washing machine |
| 8 | 37 | 37 | x[-2.2,-0.2] y[-7.1,-3.4] | x[-1.9,-0.3] y[-7.0,-3.4] | 2.7 | - |
| 9 | 59 | 59 | x[-0.3,4.3] y[-7.2,-2.4] | none | - | living: couch, sofa chair |
| 10 | 18 | 18 | x[-0.7,6.7] y[-3.8,-2.5] | x[4.1,6.7] y[-3.8,-2.5] | 1.4 | - |
| 11 | 68 | 63 | x[4.4,6.6] y[-2.6,0.3] | x[4.4,5.9] y[-2.6,0.2] | 1.6 | bathroom: shower bench, shower ceiling, shower dial, shower floor, shower glass, shower hose/head, shower rail, shower soap shelf, shower stall, shower wall, toilet, toilet paper dispenser |
| 12 | 93 | 93 | x[4.1,7.9] y[-7.3,-3.5] | x[4.2,7.8] y[-7.3,-3.5] | 6.6 | bedroom: bed, bed stand |
| 13 | 28 | 28 | x[7.7,9.6] y[-7.4,-5.7] | x[7.7,9.3] y[-7.2,-6.1] | 0.7 | - |
| 14 | 40 | 40 | x[6.3,10.1] y[-4.0,4.7] | x[6.5,9.8] y[-4.0,0.0] | 5.2 | bedroom: bed, bed stand |
| 15 | 31 | 31 | x[7.9,9.7] y[-5.6,-3.8] | x[8.0,9.6] y[-5.6,-3.8] | 1.7 | - |

Two traps for the marker rule: it matches composite names (`bed stand` and `bed` both match "bed"; `sofa chair`, `l-shaped sofa`, `oven and stove`, `bathtub utensil`, `shower wall`, `wall toilet paper`, `toilet brush`). 00871 has no `dining table`. 00853 region 5 matches living and dining; 00871 region 7 matches kitchen and laundry (as the plan says).

### 5.2 Frame conversion (habitat <-> pipeline)

Pipeline frame = "world" frame: metres, z up, floor near the start at z = 0. **`p_world = R @ p_habitat + t`**, `R = code_R`, `t = code_t` from `frame_transform.json[scene]`. `R` is the same in both scenes (yaw -92.354 deg about z, with the y-up to z-up swap); `t` differs (table above). The matrix is the inverse of `T = M_init @ Rx(-pi/2) @ Rz(pi/4)`, where `M_init` is the habitat agent start in `raw_objects.json` `pipeline_initial_agent_state` (`HW/frame_transform.py:15-18`, `code_transform`). Checked here: it maps `habitat_frame_path` to `world_frame_path` of `e1_00853_s42_official_60m` and `e1_00871_s42_official_60m` with a largest error of 8.6e-8 m (904 and 1,021 points). Asset (glb) frame to habitat: `(x, z, -y)` (`extract_semantic_aabb.py:78`). Which file is in which frame:

| File | Frame |
|---|---|
| `semantic_geometry.json` `hab_*` | habitat |
| `semantic_geometry.json` `world_*` | pipeline |
| `semantic_vertices_hab.npy` | habitat (apply `R`, `t`) |
| `raw_objects.json` `habitat_aabb_*`, `navmesh_bounds`, `pipeline_initial_agent_state` | habitat |
| reference YAMLs, `oracle_sets.json`, walls `.npz`, observed graphs, completions, `world_frame_path` | pipeline |
| `habitat_frame_path` | habitat |

Reusable code: `HW/hm3d_ref_lib.py:7-23` `load_scene` (returns each object with `world_center_A = R @ hab_center + t` and `world_center_B` = centre of the world box; the reference uses B). These files hard-code `/work` and `/workspace` paths; they run on the host.

## 6. Label vocabularies (strings and counts only)

### 6.1 The 52 detector labels

`television`, `bicycle`, `garment`, `tree`, `sofa`, `pillow`, `umbrella`, `chair`, `fridge`, `washing machine`, `plates`, `cabinet`, `curtain`, `blinds`, `mirror`, `dishes`, `gas stove`, `table`, `duvet`, `lamp`, `toilet`, `shower`, `bathtub`, `wardrobe`, `dresser`, `countertop`, `dishwasher`, `microwave`, `flower`, `nightstand`, `rug`, `waste bin`, `picture frame`, `toaster`, `towel bar`, `oven`, `computer`, `sink`, `piano`, `drain`, `shampoo`, `faucet`, `ceiling fan`, `window`, `exhaust hood`, `towel`, `printing`, `laptop`, `document`, `clock`, `toilet paper`, `glass table`.

### 6.2 Object labels in completions

Counts are occurrences of new objects by rule B (id not in the observed graph), over all members of: DeepSeek official (1,043 members, both tracks, failed runs included), DeepSeek filter_only **raw** (753), Gemini (29, track 0), placebo (e1 and e5), oracle. One object that four members propose counts four times. "In 52" = after lower case and `_` -> space. "Syn" = a `synonym_primary` key.

| Label (exact string) | DeepSeek official | DeepSeek filter_only raw | Gemini | Placebo | Oracle | In 52 | Syn |
|---|---|---|---|---|---|---|---|
| `nightstand` | 1334 | 873 | 38 | 1351 | 55 | yes |  |
| `lamp` | 1053 | 855 | 43 | 194 | 1057 | yes |  |
| `chair` | 964 | 745 | 26 | 81 | 317 | yes |  |
| `bed` | 1018 | 594 | 22 | 1457 |  |  |  |
| `dresser` | 978 | 609 | 1 | 790 | 33 | yes |  |
| `plant` | 837 | 684 | 3 | 1170 |  |  |  |
| `sink` | 790 | 484 | 18 | 561 | 192 | yes |  |
| `rug` | 750 | 515 | 20 | 269 | 397 | yes |  |
| `toilet` | 482 | 427 | 23 | 673 | 73 | yes |  |
| `wardrobe` | 539 | 354 | 16 | 1391 | 235 | yes |  |
| `cabinet` | 426 | 362 | 18 |  | 1012 | yes |  |
| `bookshelf` | 422 | 333 |  | 784 |  |  |  |
| `coffee table` | 374 | 309 | 9 | 281 |  |  | yes |
| `armchair` | 293 | 238 | 6 | 448 |  |  |  |
| `table` | 253 | 218 | 33 |  | 219 | yes |  |
| `desk` | 213 | 175 | 5 |  |  |  |  |
| `bathtub` | 208 | 156 | 6 | 392 | 23 | yes |  |
| `sofa` | 201 | 136 | 15 | 925 | 85 | yes |  |
| `bench` | 212 | 119 | 1 |  |  |  |  |
| `shelf` | 206 | 115 |  |  |  |  |  |
| `tv stand` | 101 | 97 | 8 |  |  |  |  |
| `floor lamp` | 96 | 74 | 2 | 90 |  |  | yes |
| `console table` | 116 | 53 | 2 | 135 |  |  |  |
| `towel rack` | 84 | 62 |  |  |  |  |  |
| `side table` | 69 | 64 |  | 59 |  |  |  |
| `mirror` | 58 | 64 | 15 | 134 | 329 | yes |  |
| `stool` | 50 | 68 |  |  |  |  |  |
| `duvet` | 65 | 35 | 2 |  |  | yes |  |
| `flower` | 38 | 54 | 10 |  | 30 | yes |  |
| `vanity` | 53 | 11 | 1 | 172 |  |  |  |
| `shower` | 29 | 30 | 1 |  |  | yes |  |
| `washer` | 26 | 10 |  |  |  |  |  |
| `coffee_table` | 27 | 6 |  | 712 |  |  | yes |
| `microwave` | 4 | 23 | 5 |  | 43 | yes |  |
| `stove` | 4 | 18 | 3 |  |  |  |  |
| `floor_lamp` | 16 | 2 |  | 532 |  |  | yes |
| `towel` | 13 | 2 |  |  | 404 | yes |  |
| `tv_stand` | 11 | 4 |  | 329 |  |  |  |
| `refrigerator` | 9 | 6 | 1 | 147 |  |  | yes |
| `dryer` | 8 | 7 |  |  |  |  |  |
| `waste bin` | 2 | 12 | 4 |  | 51 | yes |  |
| `counter` | 7 | 7 |  |  |  |  |  |
| `tv` | 4 | 8 |  | 68 |  |  | yes |
| `vase` | 5 | 7 | 1 |  |  |  |  |
| `towel_rack` | 12 |  |  |  |  |  |  |
| `television` | 6 | 4 | 14 |  | 47 | yes |  |
| `console` | 9 | 1 |  |  |  |  |  |
| `console_table` | 9 | 1 |  |  |  |  |  |
| `ottoman` | 6 | 4 |  |  |  |  |  |
| `shoe rack` | 5 | 5 |  |  |  |  |  |
| `box` | 5 | 4 |  |  |  |  |  |
| `storage box` | 8 |  |  |  |  |  |  |
| `kitchen table` | 6 | 1 |  |  |  |  |  |
| `washing machine` | 1 | 5 | 1 |  | 122 | yes |  |
| `dining table` | 4 | 2 |  |  |  |  | yes |
| `hamper` | 5 | 1 |  |  |  |  |  |
| `mirror cabinet` | 3 | 3 |  |  |  |  |  |
| `office chair` | 4 | 2 |  |  |  |  | yes |
| `pillow` | 1 | 4 | 5 |  | 759 | yes |  |
| `fridge` | 1 | 4 |  |  | 67 | yes |  |
| `bath mat` | 4 | 1 |  |  |  |  |  |
| `dining chair` | 1 | 4 |  |  |  |  | yes |
| `glass table` | 4 | 1 |  |  |  | yes |  |
| `kitchen island` |  | 5 |  |  |  |  |  |
| `kitchen counter` | 2 | 2 | 1 | 74 |  |  | yes |
| `mirror_cabinet` | 2 | 2 |  |  |  |  |  |
| `side_table` | 3 | 1 |  |  |  |  |  |
| `bathroom sink` | 2 | 1 |  |  |  |  |  |
| `closet shelf` |  | 3 |  |  |  |  |  |
| `sink cabinet` | 2 | 1 |  |  |  |  |  |
| `towel cabinet` | 1 | 2 |  |  |  |  |  |
| `picture frame` | 1 | 1 |  |  | 424 | yes |  |
| `table_lamp` | 1 | 1 |  | 66 |  |  |  |
| `table lamp` | 2 |  | 1 |  |  |  |  |
| `trash can` | 1 | 1 | 1 |  |  |  | yes |
| `bathmat` | 2 |  |  |  |  |  |  |
| `bin` | 2 |  |  |  |  |  |  |
| `closet_shelf` | 2 |  |  |  |  |  |  |
| `desk lamp` | 1 | 1 |  |  |  |  |  |
| `desk_chair` | 1 | 1 |  |  |  |  | yes |
| `garment` | 1 | 1 |  |  |  | yes |  |
| `potted plant` | 2 |  |  |  |  |  |  |
| `soap` | 1 | 1 |  |  |  |  |  |
| `storage shelf` | 2 |  |  |  |  |  |  |
| `television stand` | 2 |  |  |  |  |  |  |
| `workbench` | 2 |  |  |  |  |  |  |
| `ceiling fan` |  | 1 | 1 |  | 109 | yes |  |
| `Bed` | 1 |  |  |  |  |  |  |
| `Bookshelf` | 1 |  |  |  |  |  |  |
| `Coffee table` | 1 |  |  |  |  |  | yes |
| `Console table` | 1 |  |  |  |  |  |  |
| `Dresser` | 1 |  |  |  |  | yes |  |
| `Floor lamp` | 1 |  |  |  |  |  | yes |
| `Nightstand` | 1 |  |  |  |  | yes |  |
| `Plant` | 1 |  |  |  |  |  |  |
| `Sofa` | 1 |  |  |  |  | yes |  |
| `TV stand` | 1 |  |  |  |  |  |  |
| `Wardrobe` | 1 |  |  |  |  | yes |  |
| `basket` |  | 1 |  |  |  |  |  |
| `bathroom cabinet` |  | 1 |  |  |  |  | yes |
| `bed_frame` | 1 |  |  |  |  |  |  |
| `bedroom rug` | 1 |  |  |  |  |  |  |
| `boxes` |  | 1 |  |  |  |  |  |
| `chest` | 1 |  |  |  |  |  |  |
| `coat rack` | 1 |  |  |  |  |  |  |
| `desk chair` | 1 |  |  |  |  |  | yes |
| `hall tree` |  | 1 |  |  |  |  |  |
| `hallway bench` | 1 |  |  |  |  |  |  |
| `kettle` |  | 1 |  |  |  |  |  |
| `kitchen sink` | 1 |  |  |  |  |  |  |
| `laundry basket` | 1 |  |  |  |  |  |  |
| `mirror stand` |  | 1 |  |  |  |  |  |
| `pouf` |  | 1 |  |  |  |  |  |
| `runner rug` | 1 |  |  |  |  |  |  |
| `shoe cabinet` | 1 |  |  |  |  |  |  |
| `shower caddy` | 1 |  |  |  |  |  |  |
| `sideboard` | 1 |  |  |  |  |  |  |
| `sidechair` | 1 |  |  |  |  |  |  |
| `sink vanity` | 1 |  |  |  |  |  |  |
| `soap dispenser` | 1 |  |  |  |  |  |  |
| `toolbox` | 1 |  |  |  |  |  |  |
| `vanity sink` | 1 |  |  |  |  |  |  |
| `wall art` |  | 1 |  |  |  |  |  |
| `wall cabinet` | 1 |  |  |  |  |  | yes |
| `wall_art` | 1 |  |  |  |  |  |  |
| `shampoo` |  |  |  |  | 407 | yes |  |
| `curtain` |  |  |  |  | 272 | yes |  |
| `clock` |  |  |  |  | 133 | yes |  |
| `window` |  |  |  |  | 96 | yes |  |
| `faucet` |  |  |  |  | 72 | yes |  |
| `kitchen_table` |  |  |  | 62 |  |  |  |
| `kitchen_counter` |  |  |  | 56 |  |  | yes |
| `bedside_lamp` |  |  |  | 53 |  |  | yes |
| `towel bar` |  |  |  |  | 50 | yes |  |
| `toilet paper` |  |  |  |  | 39 | yes |  |
| `countertop` |  |  |  |  | 36 | yes |  |
| `dishwasher` |  |  |  |  | 30 | yes |  |
| `exhaust hood` |  |  |  |  | 28 | yes |  |
| `plates` |  |  |  |  | 28 | yes |  |
| `gas stove` |  |  |  |  | 21 | yes |  |
| `oven` |  |  |  |  | 15 | yes |  |
| `laptop` |  |  | 5 |  | 7 | yes |  |
| `piano` |  |  |  |  | 7 | yes |  |
| `trash bin` |  |  | 7 |  |  |  |  |
| `mat` |  |  | 1 |  |  |  |  |
| `storage bin` |  |  | 1 |  |  |  |  |

146 distinct strings; 122 after lower case and `_` -> space. Strings with `_` (15) such as `coffee_table`, `floor_lamp`, `bed_frame`; with capitals (11) such as `Bed`, `TV stand`. Share of DeepSeek new-object occurrences outside the 52 words: **34.7%** by exact match, **30.3%** if `synonym_primary` keys also count as mapped. The plan's 29.5% is close to the second figure but not equal; I could not reproduce it exactly (definition unknown). Oracle labels are all in the 52. Placebo labels come from `placebo_calibration.json` `labels` and include out-of-vocabulary words (`bed`, `coffee table`, `bookshelf`).

### 6.3 Room names in completions

| Room name | DeepSeek official | DeepSeek filter_only raw | Gemini | Placebo | Oracle |
|---|---|---|---|---|---|
| `an image of a bedroom` | 922 | 602 | 12 | 1438 | 790 |
| `an image of a bathroom` | 312 | 212 | 12 | 628 | 327 |
| `an image of a study` | 36 | 55 |  |  |  |
| `an image of a living room` | 40 | 22 | 11 |  |  |
| `an image of a closet` | 13 | 11 |  |  |  |
| `an image of a storage room` | 10 | 3 |  |  |  |
| `an image of an office` | 6 | 3 |  |  |  |
| `an image of a laundry room` | 3 | 3 |  |  |  |
| `an image of a hallway` | 1 | 4 | 8 |  |  |
| `an image of a kitchen` | 4 | 1 | 1 | 109 | 62 |
| `an image of a home office` | 4 |  |  |  |  |
| `an image of a garage` | 1 |  |  |  |  |
| `an image of a second bedroom` | 1 |  |  |  |  |
| `an image of a walk-in closet` |  | 1 |  |  |  |

Prompt-hint check (plan A3): of 1,353 official new-room occurrences, 68.1% are bedroom and 23.1% bathroom (official main folders only: 71.9% and 19.5% of 1,082). The plan quotes 69% / 21% of 724 rooms; the shares are close and the 724 did not reproduce under any counting I tried.

### 6.4 Observed labels (detector)

Object labels in observed graphs (counted official and filter_only main stages, both tracks): `cabinet` (2,925), `chair` (1,515), `sofa` (1,048), `mirror` (1,039), `door` (867), `lamp` (809), `ceiling fan` (800), `duvet` (755), `nightstand` (638), `table` (549), `rug` (471), `bathtub` (432), `flower` (395), `television` (355), `pillow` (317), `glass table` (315), `fridge` (252), `blinds` (223), `curtain` (215), `window` (155), `exhaust hood` (149), `toilet` (142), `waste bin` (116), `piano` (115), `garment` (104), `towel` (87), `washing machine` (64), `oven` (62), `wardrobe` (50), `tree` (28), `umbrella` (26), `shower` (5), `bicycle` (4), `picture frame` (2). Observed room names: `an image of a living room` (1,227), `an image of a bedroom` (1,222), `an image of a hallway` (690), `an image of a bathroom` (580), `an image of a closet` (275), `an image of a kitchen` (250), `an image of a laundry room` (102), `an image of a dining room` (11).

### 6.5 Raw HM3D category names

From `label_mapping.json` (`scenes.<s>.mapping_table`, objects of `semantic.txt` ids 1..N). `raw_objects.json` adds `Unknown` (id 0), so it shows 124 and 140 categories. "Tier": exact, synonym, extended-candidate (`unmapped_extended_candidate`), structural, door, unmapped.

| Raw category | 00853 | 00871 | Tier | Primary label |
|---|---|---|---|---|
| `wall` | 75 | 104 | structural |  |
| `unknown` |  | 92 | structural |  |
| `bathroom utensil` |  | 47 | unmapped |  |
| `pillow` | 26 | 16 | exact | `pillow` |
| `shoe` | 29 | 9 | unmapped |  |
| `ceiling` | 19 | 18 | structural |  |
| `lamp` | 5 | 30 | exact | `lamp` |
| `decoration` | 9 | 22 | unmapped |  |
| `floor` | 12 | 17 | structural |  |
| `book` | 4 | 24 | unmapped |  |
| `door frame` | 13 | 14 | structural |  |
| `kitchen cabinet` | 16 | 11 | synonym | `cabinet` |
| `clothes` |  | 26 | unmapped_extended_candidate |  |
| `picture` |  | 25 | synonym | `picture frame` |
| `door` | 9 | 13 | door_excluded |  |
| `curtain` | 9 | 12 | exact | `curtain` |
| `painting` | 19 |  | unmapped_extended_candidate |  |
| `box` | 14 | 4 | unmapped |  |
| `ceiling lamp` | 17 | 1 | synonym | `lamp` |
| `ventilation` |  | 18 | unmapped |  |
| `rug` | 5 | 12 | exact | `rug` |
| `clutter` |  | 16 | unmapped |  |
| `mirror` | 7 | 9 | exact | `mirror` |
| `shower wall` | 6 | 10 | structural |  |
| `cabinet` | 5 | 7 | exact | `cabinet` |
| `chair` |  | 12 | exact | `chair` |
| `shelf` | 10 | 2 | unmapped |  |
| `ceiling fan` | 5 | 6 | exact | `ceiling fan` |
| `towel` | 2 | 9 | exact | `towel` |
| `bathroom cabinet` | 5 | 5 | synonym | `cabinet` |
| `hanger` | 2 | 8 | unmapped |  |
| `sink` | 4 | 6 | exact | `sink` |
| `device` |  | 9 | unmapped |  |
| `plant` | 1 | 8 | unmapped |  |
| `shower floor` | 7 | 2 | structural |  |
| `shampoo` | 8 |  | exact | `shampoo` |
| `table` | 1 | 7 | exact | `table` |
| `wardrobe` | 6 | 2 | exact | `wardrobe` |
| `window` | 6 | 2 | exact | `window` |
| `bag` | 2 | 5 | unmapped |  |
| `bath towel` |  | 7 | synonym | `towel` |
| `cloth` |  | 7 | unmapped |  |
| `dresser` |  | 7 | exact | `dresser` |
| `basket` |  | 6 | unmapped |  |
| `blanket` |  | 6 | unmapped_extended_candidate |  |
| `cardboard box` |  | 6 | unmapped |  |
| `casket` | 2 | 4 | unmapped |  |
| `dining chair` | 6 |  | synonym | `chair` |
| `flowerpot` | 1 | 5 | unmapped_extended_candidate |  |
| `hanging clothes` | 6 |  | unmapped_extended_candidate |  |
| `bed` | 2 | 3 | unmapped_extended_candidate |  |
| `window shutter` |  | 5 | unmapped_extended_candidate |  |
| `bathroom towel` | 2 | 2 | synonym | `towel` |
| `calendar` | 4 |  | unmapped |  |
| `case` |  | 4 | unmapped |  |
| `container` |  | 4 | unmapped |  |
| `flower vase` | 4 |  | unmapped_extended_candidate |  |
| `mirror frame` | 4 |  | structural |  |
| `newspaper` |  | 4 | unmapped |  |
| `shower wall cubby` | 4 |  | structural |  |
| `sliding door` | 4 |  | door_excluded |  |
| `stand` |  | 4 | unmapped |  |
| `tray` | 1 | 3 | unmapped |  |
| `tv` |  | 4 | synonym | `television` |
| `vase` | 3 | 1 | unmapped_extended_candidate |  |
| `wall hanging decoration` | 4 |  | unmapped |  |
| `window frame` | 3 | 1 | structural |  |
| `appliance` | 3 |  | unmapped |  |
| `basket of something` |  | 3 | unmapped |  |
| `bed stand` |  | 3 | synonym | `nightstand` |
| `bottle` |  | 3 | unmapped |  |
| `clothes container` | 3 |  | unmapped |  |
| `cosmetic` | 3 |  | unmapped |  |
| `couch` |  | 3 | synonym | `sofa` |
| `cup` |  | 3 | unmapped_extended_candidate |  |
| `display cabinet` | 2 | 1 | synonym | `cabinet` |
| `door/window frame` |  | 3 | structural |  |
| `end table` | 3 |  | synonym | `table` |
| `flower` |  | 3 | exact | `flower` |
| `kitchen decoration` | 3 |  | unmapped |  |
| `kitchen shelf` | 3 |  | unmapped |  |
| `kitchen utensil` |  | 3 | unmapped |  |
| `monitor` | 2 | 1 | unmapped_extended_candidate |  |
| `parapet` |  | 3 | structural |  |
| `refrigerator` | 1 | 2 | synonym | `fridge` |
| `shower door frame` | 2 | 1 | structural |  |
| `sliding glass door` | 3 |  | door_excluded |  |
| `sofa chair` |  | 3 | unmapped_extended_candidate |  |
| `speaker` | 3 |  | unmapped |  |
| `table stand` |  | 3 | unmapped |  |
| `tap` |  | 3 | synonym | `faucet` |
| `toilet` | 2 | 1 | exact | `toilet` |
| `wall lamp` | 3 |  | synonym | `lamp` |
| `washing machine` | 2 | 1 | exact | `washing machine` |
| `alarm clock` |  | 2 | synonym | `clock` |
| `armchair` | 2 |  | unmapped_extended_candidate |  |
| `bar chair` | 2 |  | synonym | `chair` |
| `bathroom accessory` |  | 2 | unmapped |  |
| `bathroom art` |  | 2 | unmapped |  |
| `bathtub` | 1 | 1 | exact | `bathtub` |
| `bedside lamp` | 2 |  | synonym | `lamp` |
| `bowl of fruit` |  | 2 | unmapped |  |
| `carpet` | 2 |  | synonym | `rug` |
| `ceiling dome` |  | 2 | structural |  |
| `chest drawer` | 2 |  | unmapped |  |
| `clock` |  | 2 | exact | `clock` |
| `closet door` | 2 |  | door_excluded |  |
| `clothes hanger` | 2 |  | unmapped |  |
| `coffee table` | 2 |  | synonym | `table` |
| `cutting board` |  | 2 | unmapped |  |
| `decorative bowl` | 1 | 1 | unmapped |  |
| `desk chair` |  | 2 | synonym | `chair` |
| `desk clutter` |  | 2 | unmapped |  |
| `door/window` |  | 2 | structural |  |
| `faucet` | 2 |  | exact | `faucet` |
| `floor lamp` | 2 |  | synonym | `lamp` |
| `holy cross` | 1 | 1 | unmapped |  |
| `kitchen counter` | 2 |  | synonym | `countertop` |
| `kitchen wall` |  | 2 | structural |  |
| `liquid soap` |  | 2 | unmapped |  |
| `microwave` | 1 | 1 | exact | `microwave` |
| `nightstand` | 2 |  | exact | `nightstand` |
| `pc tower` | 2 |  | unmapped_extended_candidate |  |
| `plush toy` |  | 2 | unmapped |  |
| `shower ceiling` |  | 2 | structural |  |
| `shower dial` |  | 2 | unmapped |  |
| `smoke detector` | 2 |  | unmapped |  |
| `soap` |  | 2 | unmapped |  |
| `sofa` | 2 |  | exact | `sofa` |
| `step stool` | 2 |  | unmapped |  |
| `storage box` | 2 |  | unmapped |  |
| `telephone` |  | 2 | unmapped |  |
| `toilet brush holder` | 2 |  | unmapped |  |
| `trash can` | 1 | 1 | synonym | `waste bin` |
| `vent` | 2 |  | unmapped |  |
| `wall cabinet` |  | 2 | synonym | `cabinet` |
| `wall clock` | 1 | 1 | synonym | `clock` |
| `wall toilet paper` | 2 |  | synonym | `toilet paper` |
| `wall tv` | 2 |  | synonym | `television` |
| `washer-dryer` |  | 2 | synonym | `washing machine` |
| `air conditioner` | 1 |  | unmapped |  |
| `antique clock` |  | 1 | synonym | `clock` |
| `bath faucet` | 1 |  | synonym | `faucet` |
| `bath wall` | 1 |  | structural |  |
| `bathroom counter` | 1 |  | synonym | `countertop` |
| `bathtub utensil` |  | 1 | unmapped |  |
| `bowl` |  | 1 | unmapped_extended_candidate |  |
| `bucket` | 1 |  | unmapped |  |
| `carpet roll` | 1 |  | unmapped |  |
| `ceiling fixture` |  | 1 | structural |  |
| `chair stand` |  | 1 | unmapped |  |
| `closet storage area` | 1 |  | unmapped |  |
| `clothes hanger rod` | 1 |  | unmapped |  |
| `clothes rack` |  | 1 | unmapped |  |
| `coffee machine` |  | 1 | unmapped |  |
| `computer` |  | 1 | exact | `computer` |
| `computer desk` | 1 |  | unmapped_extended_candidate |  |
| `computer mouse` |  | 1 | unmapped |  |
| `cosmetics` | 1 |  | unmapped |  |
| `curtain rod` | 1 |  | structural |  |
| `desk` |  | 1 | unmapped_extended_candidate |  |
| `dining table` | 1 |  | synonym | `table` |
| `dishwasher` | 1 |  | exact | `dishwasher` |
| `fireplace` | 1 |  | unmapped |  |
| `firewood holder` | 1 |  | unmapped |  |
| `folding chair` |  | 1 | synonym | `chair` |
| `fume cupboard` | 1 |  | unmapped |  |
| `island` | 1 |  | unmapped |  |
| `l-shaped sofa` | 1 |  | synonym | `sofa` |
| `laptop` |  | 1 | exact | `laptop` |
| `office chair` | 1 |  | synonym | `chair` |
| `oven` |  | 1 | exact | `oven` |
| `oven and stove` | 1 |  | unmapped_extended_candidate |  |
| `paper towel dispenser` |  | 1 | unmapped |  |
| `piano` |  | 1 | exact | `piano` |
| `piano bench` |  | 1 | unmapped |  |
| `plate` |  | 1 | synonym | `plates` |
| `printer` |  | 1 | unmapped_extended_candidate |  |
| `recessed wall` |  | 1 | structural |  |
| `rocking chair` |  | 1 | synonym | `chair` |
| `roomba` | 1 |  | unmapped |  |
| `scale` |  | 1 | unmapped |  |
| `seat` | 1 |  | unmapped |  |
| `shelf with clutter` | 1 |  | unmapped |  |
| `shower bar` | 1 |  | unmapped |  |
| `shower bench` |  | 1 | unmapped |  |
| `shower door` |  | 1 | structural |  |
| `shower glass` |  | 1 | structural |  |
| `shower hose/head` |  | 1 | unmapped_extended_candidate |  |
| `shower knob` | 1 |  | unmapped |  |
| `shower rail` |  | 1 | unmapped |  |
| `shower soap shelf` |  | 1 | unmapped |  |
| `shower stall` |  | 1 | unmapped_extended_candidate |  |
| `shower tap` |  | 1 | unmapped_extended_candidate |  |
| `showerhead` | 1 |  | unmapped_extended_candidate |  |
| `soap dispenser` | 1 |  | unmapped |  |
| `storage shelving` | 1 |  | unmapped |  |
| `stovetop` |  | 1 | synonym | `gas stove` |
| `support beam` | 1 |  | structural |  |
| `table cloth` |  | 1 | unmapped |  |
| `thermostat` | 1 |  | unmapped |  |
| `throw blanket` | 1 |  | unmapped_extended_candidate |  |
| `toilet brush` | 1 |  | unmapped |  |
| `toilet paper dispenser` |  | 1 | unmapped_extended_candidate |  |
| `tool` |  | 1 | unmapped |  |
| `towel bar` | 1 |  | exact | `towel bar` |
| `toy` |  | 1 | unmapped |  |
| `trashcan` |  | 1 | synonym | `waste bin` |
| `unknown/remove` |  | 1 | structural |  |
| `vacuum cleaner` |  | 1 | unmapped |  |
| `ventilation hood` |  | 1 | synonym | `exhaust hood` |
| `window curtain` | 1 |  | synonym | `curtain` |
| `wine` |  | 1 | unmapped |  |

213 distinct names across the two scenes. Names such as `bed_bedroom21` (plan M0b item 3) do **not** occur in these files; the raw names are plain words (`bed`, `bed stand`). I found no suffixed names (**checked**: no name in the table contains `_`+digits).

## 7. Code to reuse

"Imports" = `import` works on this laptop with the 3.11 framework Python and the repo on `sys.path` (tested, bytecode off).

| Module | Function or item | File:line | Notes | Imports |
|---|---|---|---|---|
| `live_policy` | `track_keep_sets` | `LP/live_policy.py:94-122` | Keep-sets per policy. `official` keeps all. `filter_only` calls `validate_completion` only. **`support_filtered_graph` runs only in the `unanimity` policy**, which no live run used. | yes |
| `live_policy` | `apply_policy`, `write_keep_set_yaml` | `:146-171`, `:83-91` | Archive raw to `live_policy_raw/attempt_n`, rewrite stage file. | yes |
| `live_policy` | `placebo_graph` | `:203-277` | `(observed, rng, calib)` -> graph. Needs numpy `Generator`. Seeds: `no_llm_completions` `:385-442`. | yes |
| `live_policy` | `oracle_eligible`, `oracle_graph`, `load_oracle_set` | `:289-312`, `:315-360`, `:284-287` | `ORACLE_REACH_M` 5.0, `ORACLE_NEW_M` 0.5 (`:187-188`). | yes |
| `live_policy` | `_vec`, `_label`, `load_calibration` | `:174-177`, `:280-281`, `:191-193` | Parse position strings; label = lower case, `_` -> space. | yes |
| `asp_offline.validator` | `ValidationConfig`, `validate_completion` | `ASP/validator.py:16-22`, `:116-` | E2 used `ValidationConfig(allow_parsed_mapping=True)`. Returns `ValidationResult(graph, accepted, rejected, issues, removed_nodes)`. | yes |
| `asp_offline.validator` | `label_against_reference`, `validate_ensemble` | `:335`, `:392` | Post-hoc reference labelling; ensemble wrapper. | yes |
| `asp_offline.support_policy` | `support_filtered_graph`, `support_scores` | `ASP/support_policy.py:53`, `:125` | Support = agreement within 0.5 m (objects) / 4.0 m (rooms) over the track's members; `expected_size=4`. | yes |
| `asp_offline.support_policy` | `fit_loso_calibrator`, `collect_calibration_samples` | `:190`, `:161` | Leave-one-scene-out isotonic calibrator (`calibration.py:130 IsotonicCalibrator`, `:188 fit_leave_one_scene_out`). | yes |
| `asp_offline.author_io` | `load_author_graph`, `normalize_author_graph` | `ASP/author_io.py:113`, `:48` | Parses the string vectors; builds `room_id` from edges. | yes |
| `asp_offline.evaluator` | `area_under_curve` | `ASP/evaluator.py:14` | Used by E1 scoring. | yes |
| `gemini_static_score` | `norm`, `xy`, `objects`, `greedy`, `score` | `LP/gemini_static_score.py:34, 38, 44, 48, 60` | "New" = more than 0.5 m xy from every observed object (`:64`). Hits at 0.5/1/2 m by greedy same-label match. | **no**: opens the host vocabulary path at import (`:30-31`) and `REFS` (`:28`) are `/workspace` paths |
| `stage_precision` | `main`, `arm_of` | `LP/stage_precision.py:42-92`, `:30` | Per member, with the member's own track; filter_only raw uses the last attempt and splits kept and removed (`:69-77`). | **no** (imports `gemini_static_score`) |
| `stage_diagnostics` | `is_mapped`, `map_points`, `path_xy`, `run_diagnostics` | `LP/stage_diagnostics.py:82-84`, `:76-79`, `:87-92`, `:127` | **"mapped"**: a same-label object or structure node of the next map (stage k+1; k+2 as lag; either track) within 0.5 m xy (`MAPPED_M`, `:45`). **"approached"**: candidate within 3.5 m xy of the last point of stage k+1's `world_frame_path` (`APPROACH_M`; `:164`). "Scanned": within 3.0 m of the path walked in stages 1..k (`:167`). Candidates come from `oracle_eligible`. | yes |
| `later_found` | `main` | `LP/later_found.py:29-72` | Hypothesis = (label, 0.5 m cell), new = more than 0.5 m from observed objects (`:62`), found = same-label object or structure within 0.5 m in the last map (`:67-68`). | yes |
| `e1_analysis` | `paired_signflip`, `blocked_permutation`, `permutation_ci`, `bootstrap_ci`, `mde`, `parse` | `LP/e1_analysis.py:77-84`, `:55-74`, `:97-109`, `:87-94`, `:112-127`, `:45-47` | Exact sign-flip over cells (`2**n`; 12 clusters give 4,096), returns p only. `permutation_ci` inverts the **blocked permutation**, not the sign-flip test. Std-lib only. | yes |
| `paper_compare` | `f1_score` | `LP/paper_compare.py:132` | Paper-style F1. Uses `CSafeLoader` when present. | not tested |
| `extract_semantic_aabb.py` | script | `HW/extract_semantic_aabb.py` (host; reads glb + `semantic.txt`) | Per-object boxes. Outputs `semantic_geometry.json` and the `.npy` (`:129-141`). | host only |
| `slice_walls.py` | script | `LP/review_2026-10-29/bench/walls/slice_walls.py` | Mesh slices at z = 0.6/1.1/1.6 -> `.npz`; same glb parser. | host only |
| slice renderer | `scene_graph_visualize_2d.create_scene_slices(yaml_path, scene_slice_folder_name=...)` | **not in this checkout.** Called at `gemini_static.py:117`, `prospective_integration/overlay/.../llm_completion.py:13, 502` | Source lives only in the host `exploration/scripts` folder. **Cannot be imported here.** Output: six `scene_z_<lo>_to_<hi>.jpg`. | **no** |
| `llm_completion.py` | `LLMCompletion`, `LLMManager`, `check_collision` | `REPO/tools/prospective_integration/overlay/pinned_reference/llm_completion.py` | md5 `dc70801e...` equals the pinned file in the run manifests (the exact live code is here). The sibling `overlay/exploration/scripts/llm_completion.py` (md5 `f5697ecc...`) is a different version. `decision_replay_reference/calculate_uncertainty.py` (md5 `086515b7...`) does not match the run manifest (`9cec96c6...`). | needs `scene_graph_visualize_2d` |

## 8. What is not on the laptop

- **HM3D semantic mesh and annotations** for 00853 and 00871: `.semantic.glb`, `.semantic.txt`, `.basis.glb`, navmesh, under `/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d/val/<scene dir>/` (paths read from `extract_objects.py:9-10`; not checked on the host). Needed for floor triangles per region (plan A18), and for any region polygon.
- **Other houses' `*.semantic.txt`** (B3b prior): which exist is unknown; the M0b host check answers it. The laptop has two houses only.
- **Image slices** for the 36 DeepSeek rows and for the smoke test. Only the 66 Gemini slices exist. Slices the runs saved were overwritten with the completed graph (`gemini_static.py:5-6`), so render them again from `original_graph{0,1}.yaml` with `create_scene_slices` on the host.
- **`scene_graph_visualize_2d.py`**, the pinned `exploration_pipeline.py`, `calculate_uncertainty.py` of the live run, and `objects_habitat_apartment.yaml`: host only (the last is mirrored as the 52-word list).
- **Mapper dumps** (DSG files): never copied, by rule. Observed graphs are the YAML graphs in each stage folder.
- **`placebo_calibration.json` source** `dryrun2_00069_s42_filter_only_10m`: not in the copy.
- **Per-stage raw LLM text for official stages** is in `prompts/prompts_responses.jsonl` (call level, no stage or member tag; match by `timestamp` and `live_policy.jsonl` `ts`, **inferred**), not per member.
- **To compute on the host or later:** region floor footprints from mesh triangles; whatever Claude outputs. Everything else in M0b and M1 can run on the laptop from the files above.

## 9. The 12 clusters

Cluster = scene x seed x arm. FA1 rows join the official cluster with the same scene and seed. Row numbers refer to the table in section 1.

| Cluster | Scene | Seed | Arm | Rows | Frame rows |
|---|---|---|---|---|---|
| 1 | 00853 | 42 | official | 4 | #1 O-00853-s42 st3; #2 O-00853-s42 st8; #3 O-00853-s42 st13; #41 FA1-00853-s42 st4 |
| 2 | 00853 | 43 | official | 6 | #4 O-00853-s43 st3; #5 O-00853-s43 st8; #6 O-00853-s43 st13; #42 FA1-00853-s43 st1; #43 FA1-00853-s43 st2; #44 FA1-00853-s43 st5 |
| 3 | 00853 | 44 | official | 3 | #7 O-00853-s44 st3; #8 O-00853-s44 st8; #9 O-00853-s44 st13 |
| 4 | 00871 | 42 | official | 7 | #19 O-00871-s42 st3; #20 O-00871-s42 st8; #21 O-00871-s42 st13; #37 FA1-00871-s42 st2; #38 FA1-00871-s42 st3; #39 FA1-00871-s42 st5; #40 FA1-00871-s42 st6 |
| 5 | 00871 | 43 | official | 3 | #22 O-00871-s43 st3; #23 O-00871-s43 st8; #24 O-00871-s43 st13 |
| 6 | 00871 | 44 | official | 3 | #25 O-00871-s44 st3; #26 O-00871-s44 st8; #27 O-00871-s44 st13 |
| 7 | 00853 | 42 | filter_only | 3 | #10 F-00853-s42 st3; #11 F-00853-s42 st8; #12 F-00853-s42 st13 |
| 8 | 00853 | 43 | filter_only | 3 | #13 F-00853-s43 st3; #14 F-00853-s43 st8; #15 F-00853-s43 st13 |
| 9 | 00853 | 44 | filter_only | 3 | #16 F-00853-s44 st3; #17 F-00853-s44 st8; #18 F-00853-s44 st13 |
| 10 | 00871 | 42 | filter_only | 3 | #28 F-00871-s42 st3; #29 F-00871-s42 st8; #30 F-00871-s42 st13 |
| 11 | 00871 | 43 | filter_only | 3 | #31 F-00871-s43 st3; #32 F-00871-s43 st8; #33 F-00871-s43 st13 |
| 12 | 00871 | 44 | filter_only | 3 | #34 F-00871-s44 st3; #35 F-00871-s44 st8; #36 F-00871-s44 st13 |

Sizes: official clusters 4, 6, 3, 7, 3, 3 rows; filter_only clusters 3 rows each (18). Total 44. The two largest clusters (`853 s43` with 6 rows and `871 s42` with 7) hold the FA1 rows.

## 10. Where the plan and the data differ

- **New-object rule (M1 extraction).** The plan says a new object has `is_predicted` set. Gemini sets `is_predicted: false` on all 396 of its new objects, so the rule finds none. DeepSeek: 60 official and 10 filter_only members hold a flagged object on an observed id, and 56 / 76 new-id objects lack the flag (section 2.2). Rule B (id based) works for all three models.
- **New-room rule.** The plan says rooms carry no `is_predicted`. 26 official and 27 filter_only room nodes carry `is_predicted: true`. The id rule is still sound (no room reused an observed non-room id).
- **4 members per track.** The plan assumes 4. In the frame, 13 of 44 rows have 2 or 3 track-0 members; Gemini gives 29 of 32 members (3 stages have 3).
- **Image slices.** The brief says none are on the laptop. 66 Gemini input slices are (11 folders x 6 `.jpg`).
- **Gemini data.** Stage 5 of 00871 s42 is in two folders; only `gemini_static2` has members. One more stage (00853 s43 stage 6) was run and failed on the cap. They are not in the frame.
- **B4 / `track_keep_sets`.** The plan says E2 ran the layer through `validate_completion` then `support_filtered_graph`. `filter_only` calls `validate_completion` only; `support_filtered_graph` is called only for `unanimity`, which no live run used.
- **Confidence intervals.** The plan says to invert the sign-flip test. `e1_analysis.permutation_ci` inverts the blocked permutation test; `paired_signflip` returns a p-value only.
- **Label-map input (M0b item 3).** Suffixed names such as `bed_bedroom21` do not occur in the two scenes' raw names. Underscore variants occur only in DeepSeek output (`coffee_table`, `floor_lamp`, 15 strings).
- **29.5% outside the vocabulary (plan A5).** I get 34.6% (exact) and 30.2% (with `synonym_primary`). **69% / 21% of 724 rooms (plan A3).** I get 68.1% / 23.1% of 1,353 official room occurrences (71.9% / 19.5% of 1,082 in the main folders); 724 did not reproduce.
- **Region footprints (plan A18).** Only boxes exist on the laptop: per-object boxes, one floor box per region (none for 00871 region 9), no polygons. The `.npy` has no faces or labels.
- **Region types.** `region_id` exists per object in `raw_objects.json`, as the plan says, and `category` too. The marker rule on whole tokens also matches `bed stand`, `sofa chair`, `l-shaped sofa`, `oven and stove`, `shower wall` (section 5.1).
- **Plan counts that hold.** 259 stages (150 + 109); the 44-row frame; the 12 clusters; `track_keep_sets` at `live_policy.py:94-122`; `pipeline_config.yaml:101`; `oracle_sets.json` 180 / 232 objects; 12 and 16 regions.

