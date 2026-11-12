"""Tests for tools/live_policy/live_policy.py (2026-10-28 live campaign)."""
import json
import os
import sys
from types import SimpleNamespace

import pytest
import yaml

TOOLS = os.path.join(os.path.dirname(__file__), "..")
sys.path[:0] = [TOOLS, os.path.join(TOOLS, "live_policy")]

import live_policy  # noqa: E402

ROOM = {"id": 1, "name": "an image of a bedroom", "node_type": "room", "position": "[0.0, 0.0, 1.3]"}
BED = {
    "id": 2, "name": "bed", "node_type": "object", "position": "[1.0, 1.0, 0.5]",
    "dimension": "[2.0, 1.5, 0.6]", "orientation": "[[1,0,0],[0,1,0],[0,0,1]]",
}
OBSERVED = {"nodes": [ROOM, BED], "edges": [[2, 1]]}


def lamp(node_id, x):
    return {
        "id": node_id, "name": "lamp", "node_type": "object", "is_predicted": True,
        "position": f"[{x}, -2.0, 0.6]", "dimension": "[0.3, 0.3, 1.2]",
        "orientation": "[[1,0,0],[0,1,0],[0,0,1]]",
    }


BAD = {"id": 11, "name": "wall", "node_type": "structure", "is_predicted": True,
       "position": "[5.0, 5.0, 1.0]", "dimension": "[0.1, 3.0, 2.0]"}


def completion(extra_nodes, extra_edges):
    return {"nodes": [ROOM, BED] + extra_nodes, "edges": [[2, 1]] + extra_edges}


def write(path, graph):
    path.write_text(yaml.safe_dump(graph))
    return str(path)


def stage(tmp_path, members):
    """members: list of completion graphs for track 0 (graph ids 0..)."""
    write(tmp_path / "habitat_scene_graph_original_graph0.yaml", OBSERVED)
    return [write(tmp_path / f"habitat_scene_graph_new_graph_{i}.yaml", g) for i, g in enumerate(members)]


def ids(path):
    return sorted(n["id"] for n in yaml.safe_load(open(path))["nodes"])


@pytest.mark.parametrize("value", ["", "Official", "tau_1"])
def test_policy_from_env_fails_closed(monkeypatch, value):
    monkeypatch.setenv(live_policy.ENV_VAR, value)
    with pytest.raises(SystemExit):
        live_policy.policy_from_env()


def test_official_is_a_no_op_and_logs(tmp_path):
    files = stage(tmp_path, [completion([lamp(10, 3.0), BAD], [[10, 1], [11, 1]])] * 4)
    before = [open(f).read() for f in files]
    live_policy.apply_policy("official", str(tmp_path), files, 4)
    assert [open(f).read() for f in files] == before
    assert not (tmp_path / live_policy.RAW_DIR_NAME).exists()
    record = json.loads((tmp_path / live_policy.SUMMARY_NAME).read_text())
    assert record["tracks"]["0"]["members"][0]["kept_predicted"] == 2


def test_filter_only_drops_invalid_nodes_and_archives_raw(tmp_path):
    files = stage(tmp_path, [completion([lamp(10, 3.0), BAD], [[10, 1], [11, 1]])] * 4)
    raw_text = open(files[0]).read()
    live_policy.apply_policy("filter_only", str(tmp_path), files, 4)
    assert ids(files[0]) == [1, 2, 10]
    graph = yaml.safe_load(open(files[0]))
    assert [11, 1] not in graph["edges"] and [10, 1] in graph["edges"]
    lamp_node = next(n for n in graph["nodes"] if n["id"] == 10)
    assert lamp_node["orientation"] == "[[1,0,0],[0,1,0],[0,0,1]]"  # pinned fields survive
    archived = tmp_path / live_policy.RAW_DIR_NAME / "attempt_0" / os.path.basename(files[0])
    assert archived.read_text() == raw_text


def test_unanimity_keeps_only_nodes_all_four_members_propose(tmp_path):
    shared = lamp(10, 3.0)
    lone = lamp(12, -4.0)
    members = [completion([shared, lone], [[10, 1], [12, 1]])] + [completion([shared], [[10, 1]])] * 3
    files = stage(tmp_path, members)
    live_policy.apply_policy("unanimity", str(tmp_path), files, 4)
    assert ids(files[0]) == [1, 2, 10]
    assert all(ids(f) == [1, 2, 10] for f in files[1:])


def test_unanimity_with_a_dropped_member_keeps_no_predictions(tmp_path):
    files = stage(tmp_path, [completion([lamp(10, 3.0)], [[10, 1]])] * 3)
    live_policy.apply_policy("unanimity", str(tmp_path), files, 4)
    assert all(ids(f) == [1, 2] for f in files)


def test_tracks_are_grouped_by_graph_id(tmp_path):
    write(tmp_path / "habitat_scene_graph_original_graph1.yaml", OBSERVED)
    files = stage(tmp_path, [completion([BAD], [[11, 1]])] * 4)
    files.append(write(tmp_path / "habitat_scene_graph_new_graph_5.yaml", completion([BAD], [[11, 1]])))
    record = live_policy.apply_policy("filter_only", str(tmp_path), files, 4)
    assert record["tracks"]["0"]["available"] == 4
    assert record["tracks"]["1"]["available"] == 1


def test_repeat_attempts_archive_separately(tmp_path):
    files = stage(tmp_path, [completion([BAD], [[11, 1]])] * 4)
    live_policy.apply_policy("filter_only", str(tmp_path), files, 4)
    live_policy.apply_policy("filter_only", str(tmp_path), files, 4)
    assert sorted(os.listdir(tmp_path / live_policy.RAW_DIR_NAME)) == ["attempt_0", "attempt_1"]


class _Manager:
    def __init__(self, working_dir):
        self.config = SimpleNamespace(WORKING_DIRECTORY=working_dir, LLM_ENSEMBLE_COUNT=4)
        self.calls = 0

    def _preprocess_dsg(self, dsg_path, scene_index):
        dst = os.path.join(self.config.WORKING_DIRECTORY, f"habitat_scene_graph_original_graph{scene_index}.yaml")
        with open(dst, "w") as f:
            yaml.safe_dump(OBSERVED, f)
        return dst

    def complete_scene_graph(self, initial_dsg_paths):
        self.calls += 1
        return stage(__import__("pathlib").Path(self.config.WORKING_DIRECTORY),
                     [completion([lamp(10, 3.0), BAD], [[10, 1], [11, 1]])] * 4)


def test_install_observed_only_makes_no_llm_call(tmp_path):
    cls = type("M", (_Manager,), {})
    live_policy.install(cls, "observed_only")
    manager = cls(str(tmp_path))
    files = manager.complete_scene_graph(["dsg0.json", "dsg1.json"])
    assert manager.calls == 0
    assert len(files) == 8
    assert all(yaml.safe_load(open(f)) == OBSERVED for f in files)


def test_install_filter_only_calls_original_then_filters(tmp_path):
    cls = type("M", (_Manager,), {})
    live_policy.install(cls, "filter_only")
    manager = cls(str(tmp_path))
    files = manager.complete_scene_graph(["dsg0.json"])
    assert manager.calls == 1
    assert all(ids(f) == [1, 2, 10] for f in files)


def test_install_passes_none_through(tmp_path):
    cls = type("M", (_Manager,), {"complete_scene_graph": lambda self, paths: None})
    live_policy.install(cls, "filter_only")
    assert cls(str(tmp_path)).complete_scene_graph(["d"]) is None


CALIB = {
    "objects_poisson_mean": 10, "objects_min": 6, "objects_max": 16, "rooms_p2": 0.6,
    "labels": {"bed": 5, "nightstand": 3, "coffee_table": 2}, "room_names": {"an image of a bedroom": 2, "an image of a bathroom": 1},
    "dims_pool": [[0.6, 0.6, 0.8], [2.0, 1.5, 0.6]],
    "room_radius_m": [1.5, 3.5], "room_min_clearance_m": 1.0, "room_second_link_p": 0.32,
    "object_new_room_frac": 0.54, "object_new_room_radius_m": [0.3, 1.5], "object_observed_room_radius_m": [0.5, 2.5],
    "object_min_clearance_m": 0.3,
}


def _placebo(seed):
    import numpy as np

    return live_policy.placebo_graph(OBSERVED, np.random.default_rng(seed), CALIB)


def test_placebo_matches_the_calibrated_shape():
    graph = _placebo([42, 3, 0])
    observed_ids = {n["id"] for n in OBSERVED["nodes"]}
    new = [n for n in graph["nodes"] if n["id"] not in observed_ids]
    assert [n for n in graph["nodes"] if n["id"] in observed_ids] == OBSERVED["nodes"]
    rooms = [n for n in new if n["node_type"] == "room"]
    objects = [n for n in new if n["node_type"] == "object"]
    assert 1 <= len(rooms) <= 2 and 6 <= len(objects) <= 16
    assert all("is_predicted" not in r for r in rooms)  # LLM rooms are unflagged
    assert all(o["is_predicted"] is True and o["name"] in CALIB["labels"] for o in objects)
    rx, ry, _ = live_policy._vec(ROOM["position"])
    for r in rooms:
        x, y, _ = live_policy._vec(r["position"])
        assert 1.5 - 1e-6 <= ((x - rx) ** 2 + (y - ry) ** 2) ** 0.5 <= 3.5 + 1e-6
        assert [r["id"], ROOM["id"]] in graph["edges"]
    bx, by, _ = live_policy._vec(BED["position"])
    for o in objects:
        x, y, _ = live_policy._vec(o["position"])
        assert (x - bx) ** 2 + (y - by) ** 2 >= 0.3 ** 2 - 1e-9
        assert any(o["id"] == e[0] for e in graph["edges"])
    ids = {n["id"] for n in graph["nodes"]}
    assert all(a in ids and b in ids for a, b in graph["edges"])
    assert len(ids) == len(graph["nodes"])


def test_placebo_is_seeded_and_members_differ():
    assert _placebo([42, 3, 0]) == _placebo([42, 3, 0])
    assert _placebo([42, 3, 0]) != _placebo([42, 3, 1])


def test_placebo_output_passes_the_validator_schema():
    from asp_offline.author_io import normalize_author_graph
    from asp_offline.validator import ValidationConfig, validate_completion

    graph = _placebo([7, 1, 2])
    result = validate_completion(normalize_author_graph(graph), normalize_author_graph(OBSERVED, observed=True),
                                 ValidationConfig(allow_parsed_mapping=True))
    assert not result.rejected


def test_real_calibration_file_loads():
    calib = live_policy.load_calibration()
    assert sum(calib["labels"].values()) > 100 and len(calib["dims_pool"]) > 100


def test_pacing_schedule_repeats_last_value(monkeypatch):
    monkeypatch.setenv(live_policy.SCHEDULE_ENV_VAR, "260,400,500")
    assert [live_policy.pacing_delay(k) for k in (0, 1, 2, 9)] == [260, 400, 500, 500]
    monkeypatch.delenv(live_policy.SCHEDULE_ENV_VAR)
    monkeypatch.setenv(live_policy.DELAY_ENV_VAR, "30")
    assert live_policy.pacing_delay(4) == 30


def test_install_placebo_makes_no_llm_call_and_waits(tmp_path, monkeypatch):
    sleeps = []
    monkeypatch.setattr(live_policy.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(live_policy, "load_calibration", lambda: CALIB)
    monkeypatch.setenv(live_policy.SCHEDULE_ENV_VAR, "120,240")
    cls = type("M", (_Manager,), {})
    live_policy.install(cls, "placebo")
    manager = cls(str(tmp_path))
    manager.config.SEED = 42
    files = manager.complete_scene_graph(["dsg0.json", "dsg1.json"])
    assert manager.calls == 0 and len(files) == 8
    graphs = [yaml.safe_load(open(f)) for f in files]
    assert all(len(g["nodes"]) > len(OBSERVED["nodes"]) for g in graphs)
    assert graphs[0] != graphs[1]
    assert len(sleeps) == 1 and 119 < sleeps[0] <= 120  # tmp_path is not a numbered stage: stage 0
    record = json.loads((tmp_path / live_policy.SUMMARY_NAME).read_text())
    assert record["policy"] == "placebo" and record["delay_s"] == 120.0


def test_placebo_retry_draws_fresh_hypotheses(tmp_path, monkeypatch):
    monkeypatch.setattr(live_policy.time, "sleep", lambda s: None)
    monkeypatch.setattr(live_policy, "load_calibration", lambda: CALIB)
    cls = type("M", (_Manager,), {})
    live_policy.install(cls, "placebo")
    manager = cls(str(tmp_path))
    manager.config.SEED = 42
    first = [yaml.safe_load(open(f)) for f in manager.complete_scene_graph(["dsg0.json"])]
    retry = [yaml.safe_load(open(f)) for f in manager.complete_scene_graph(["dsg0.json"])]
    assert first[0] != retry[0]
    import numpy as np
    expected = live_policy.placebo_graph(OBSERVED, np.random.default_rng([42, 0, 0]), CALIB)
    assert first[0] == expected  # first attempt keeps the pre-registered seed
    records = [json.loads(l) for l in (tmp_path / live_policy.SUMMARY_NAME).read_text().splitlines()]
    assert [r["attempt"] for r in records] == [0, 1]


def test_placebo_rerun_draws_a_fresh_stream(tmp_path, monkeypatch):
    monkeypatch.setattr(live_policy.time, "sleep", lambda s: None)
    monkeypatch.setattr(live_policy, "load_calibration", lambda: CALIB)
    import numpy as np
    cls = type("M", (_Manager,), {})
    live_policy.install(cls, "placebo")
    graphs = {}
    for run in ("e1_00871_s43_placebo_60m", "e1_00871_s43_placebo_60m_rerun1"):
        stage = tmp_path / run / "stages" / "1"
        stage.mkdir(parents=True)
        manager = cls(str(stage))
        manager.config.SEED = 43
        graphs[run] = yaml.safe_load(open(manager.complete_scene_graph(["dsg0.json"])[0]))
        record = json.loads((stage / live_policy.SUMMARY_NAME).read_text())
        assert record["rerun"] == (1 if run.endswith("rerun1") else 0)
    original, rerun = graphs.values()
    assert original == live_policy.placebo_graph(OBSERVED, np.random.default_rng([43, 1, 0]), CALIB)
    assert rerun == live_policy.placebo_graph(OBSERVED, np.random.default_rng([43, 1, 0, 0, 1]), CALIB)
    assert original != rerun
    assert live_policy._rerun_index("/w/runs/x_rerun12/stages/3") == 12
    assert live_policy._rerun_index("/w/runs/x_60m/stages/3") == 0


# Oracle arm (E3): reference objects around the fixture map. ROOM is at (0, 0); BED at (1, 1).
ORACLE_SET = [
    {"name": "lamp", "position": [3.0, 0.0, 0.6], "dimension": [0.3, 0.3, 1.2]},       # unseen, in reach
    {"name": "chair", "position": [0.0, -3.0, 0.4], "dimension": [0.5, 0.5, 0.9]},     # unseen, in reach
    {"name": "plant", "position": [-2.0, 2.0, 0.5], "dimension": [0.4, 0.4, 1.0]},     # unseen, in reach
    {"name": "bed", "position": [1.2, 1.1, 0.5], "dimension": [2.0, 1.5, 0.6]},        # within 0.5 m of BED: seen
    {"name": "sofa", "position": [9.0, 9.0, 0.5], "dimension": [2.0, 1.0, 0.8]},       # beyond 5 m: out of reach
]


def _oracle(seed, candidates=ORACLE_SET, calib=CALIB):
    import numpy as np

    return live_policy.oracle_graph(OBSERVED, np.random.default_rng(seed), calib, candidates)


def test_oracle_draws_only_unseen_reference_objects_in_reach():
    calib = dict(CALIB, objects_min=2, objects_max=2)
    for k in range(20):
        graph, info = _oracle([42, 3, k], calib=calib)
        new = [n for n in graph["nodes"] if n.get("node_type") == "object" and n.get("is_predicted")]
        assert info == {"n_candidates_in_reach": 3, "n_drawn": 2, "fallback": False}
        assert len(new) == 2 and len({n["name"] for n in new}) == 2  # without replacement
        for n in new:
            ref = next(c for c in ORACLE_SET if c["name"] == n["name"])
            assert n["name"] in ("lamp", "chair", "plant")
            assert live_policy._vec(n["position"]) == ref["position"]
            assert live_policy._vec(n["dimension"]) == ref["dimension"]
            assert any(e[0] == n["id"] for e in graph["edges"])  # linked to a room
        ids = {n["id"] for n in graph["nodes"]}
        assert len(ids) == len(graph["nodes"]) and all(a in ids and b in ids for a, b in graph["edges"])


def test_oracle_rooms_equal_the_placebo_rooms_and_members_differ():
    graph, _ = _oracle([42, 3, 0])
    placebo = _placebo([42, 3, 0])

    def rooms(g):
        return [n for n in g["nodes"] if n.get("node_type") == "room"]

    assert rooms(graph) == rooms(placebo)
    assert _oracle([42, 3, 0]) == _oracle([42, 3, 0])
    draws = {tuple(sorted(n["name"] for n in _oracle([42, 3, k], calib=dict(CALIB, objects_min=1, objects_max=1))[0]["nodes"]
                          if n.get("is_predicted"))) for k in range(30)}
    assert len(draws) > 1


def test_oracle_takes_all_on_shortfall_and_falls_back_when_empty():
    graph, info = _oracle([1, 0, 0])  # count 6-16 drawn, only 3 eligible
    assert info["n_drawn"] == 3 and not info["fallback"]
    graph, info = _oracle([1, 0, 0], candidates=ORACLE_SET[3:])  # nothing unseen in reach
    assert info == {"n_candidates_in_reach": 0, "n_drawn": 0, "fallback": True}
    assert any(n.get("is_predicted") for n in graph["nodes"])  # the placebo's own objects


def test_oracle_output_passes_the_validator_schema():
    from asp_offline.author_io import normalize_author_graph
    from asp_offline.validator import ValidationConfig, validate_completion

    graph, _ = _oracle([7, 1, 2])
    result = validate_completion(normalize_author_graph(graph), normalize_author_graph(OBSERVED, observed=True),
                                 ValidationConfig(allow_parsed_mapping=True))
    assert not result.rejected


def test_install_oracle_makes_no_llm_call_and_logs_draws(tmp_path, monkeypatch):
    sets = tmp_path / "oracle_sets.json"
    sets.write_text(json.dumps({"scenes": {"871": {"objects": ORACLE_SET}}}))
    monkeypatch.setattr(live_policy, "ORACLE_SETS_PATH", str(sets))
    monkeypatch.setattr(live_policy.load_oracle_set, "__defaults__", (str(sets),))
    monkeypatch.setattr(live_policy.time, "sleep", lambda s: None)
    monkeypatch.setattr(live_policy, "load_calibration", lambda: CALIB)
    cls = type("M", (_Manager,), {})
    live_policy.install(cls, "oracle_visible")
    manager = cls(str(tmp_path))
    manager.config.SEED = 42
    manager.config.SCENE_NUMBER = 871
    files = manager.complete_scene_graph(["dsg0.json", "dsg1.json"])
    assert manager.calls == 0 and len(files) == 8
    record = json.loads((tmp_path / live_policy.SUMMARY_NAME).read_text())
    assert record["policy"] == "oracle_visible"
    members = record["tracks"]["0"]["members"]
    assert all(m["n_candidates_in_reach"] == 3 and m["n_drawn"] == 3 and m["fallback"] is False for m in members)
    import numpy as np
    expected, _ = live_policy.oracle_graph(OBSERVED, np.random.default_rng([42, 0, 0]), CALIB, ORACLE_SET)
    assert yaml.safe_load(open(files[0])) == expected


def test_oracle_treats_same_label_structure_as_mapped():
    window = {"id": 3, "name": "window", "node_type": "structure", "position": "[3.1, 0.1, 1.5]",
              "dimension": "[1.0, 0.1, 1.2]"}
    wall = {"id": 4, "name": "wall", "node_type": "structure", "position": "[0.0, -3.1, 1.5]",
            "dimension": "[4.0, 0.1, 2.5]"}
    observed = {"nodes": [ROOM, BED, window, wall], "edges": [[2, 1]]}
    cands = [{"name": "window", "position": [3.0, 0.0, 1.5], "dimension": [1.0, 0.1, 1.2]},   # mapped as structure
             {"name": "chair", "position": [0.0, -3.0, 0.4], "dimension": [0.5, 0.5, 0.9]}]   # next to a wall: still unmapped
    import numpy as np
    graph, info = live_policy.oracle_graph(observed, np.random.default_rng([1, 0, 0]), CALIB, cands)
    assert info["n_candidates_in_reach"] == 1
    assert [n["name"] for n in graph["nodes"] if n.get("is_predicted")] == ["chair"]
