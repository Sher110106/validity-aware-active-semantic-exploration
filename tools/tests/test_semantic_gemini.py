"""Tests for tools/live_policy/semantic_gemini.py: the wrapper that scores the Gemini replay with the frozen scorer.

The test that matters most builds a fake Gemini folder from real Claude Haiku members and shows that the wrapper
scores each member exactly as the frozen Claude path did (the filed records), and that "fake Gemini minus Haiku"
is zero in every cluster. It skips when the replay outputs or the saved runs are absent.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import sys

import pytest

HERE = os.path.dirname(__file__)
WRAPPER = os.path.abspath(os.path.join(HERE, "..", "live_policy", "semantic_gemini.py"))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CLAUDE_ROOT = "/Users/sher/project/cvp/replay_outputs/m4"
FILED = os.path.join(REPO, "tools", "live_policy", "results_semantic_1113", "claude", "records_claude-haiku-5-5.json")
HAIKU = "claude-haiku-5-5"


def _load():
    key = "_semantic_gemini_under_test"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, WRAPPER)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod
    spec.loader.exec_module(mod)
    return mod


sg = _load()
rs, ep = sg.rs, sg.ep


def _have_data():
    return (os.path.isdir(os.path.join(CLAUDE_ROOT, HAIKU)) and os.path.isfile(FILED)
            and os.path.isdir(str(ep.RUNS_ROOT)))


needs_data = pytest.mark.skipif(not _have_data(), reason="replay outputs or saved runs are absent")

FRAME = ep.parse_frame(rs.FRAME_PATH)
ROUND = {rid: rnd for rid, _r, _s, rnd in FRAME}


def ids_of(rnd):
    return [rid for rid, _r, _s, rd in FRAME if rd == rnd]


MODEL = "gemini-3.8-flash"           # the model that ran (PREREGISTRATION_GEMINI.md, Note 1)


def write_row_json(root, rid, ends, done=True, model=MODEL, numbers=None):
    d = root / rid
    d.mkdir(parents=True, exist_ok=True)
    numbers = list(range(len(ends))) if numbers is None else numbers
    (d / "row.json").write_text(json.dumps({
        "row": rid, "model": model, "done": done,
        "members": [{"member": k, "end": e} for k, e in zip(numbers, ends)]}))


def rows_text():
    """The rows file the tests use: rounds 1, 3, 2, in frame order."""
    return "# test order: rounds 1, 3, 2\n" + "\n".join(ids_of(1) + ids_of(3) + ids_of(2)) + "\n"


def patch_registration(mp, root, rows=None):
    """Point the module at a test registration, its hash file and a rows file with its pinned hash. The command line
    has no flag for any of this; a test changes the module constants. Returns the registration hash."""
    prereg = root / "PREREGISTRATION_GEMINI.md"
    prereg.write_text("a test registration\n")
    h = hashlib.sha256(prereg.read_bytes()).hexdigest()
    hash_file = root / "PREREGISTRATION_GEMINI.sha256"
    hash_file.write_text(f"{h}  PREREGISTRATION_GEMINI.md\n")
    rows_file = root / "rows.txt"
    rows_file.write_text(rows_text() if rows is None else rows)
    mp.setattr(sg, "PREREG_PATH", prereg)
    mp.setattr(sg, "PREREG_HASH_PATH", hash_file)
    mp.setattr(sg, "ROWS_FILE", rows_file)
    mp.setattr(sg, "ROWS_FILE_SHA256", hashlib.sha256(rows_file.read_bytes()).hexdigest())
    mp.setattr(sg, "freeze_problems", lambda: [])
    return h


# ------------------------------------------------------------------------------ the set of rows

def test_row_not_done_is_left_out_and_listed(tmp_path):
    r1, r3 = ids_of(1), ids_of(3)
    for rid in r1:
        write_row_json(tmp_path, rid, ["ok"] * 4)
    write_row_json(tmp_path, r3[0], ["ok", "ok", "stopped", "stopped"], done=False)
    write_row_json(tmp_path, r3[1], ["ok"] * 4)
    rows = r1 + r3
    rep = sg.load_replay(tmp_path, rows, FRAME)
    assert rep["finished_rounds"] == [1]
    assert rep["confirmatory"] == r1
    assert rep["exploratory"] == [r3[1]]                      # finished row of an unfinished round: apart
    assert r3[0] in rep["not_done"] and "not done" in rep["not_done"][r3[0]]
    assert r3[2] in rep["not_done"] and rep["not_done"][r3[2]] == "no row.json"
    assert r3[0] not in rep["confirmatory"] + rep["exploratory"]
    assert rep["model"] == MODEL and rep["members_per_row"] == 4


def test_round_missing_from_the_rows_file_is_not_finished(tmp_path):
    r1 = ids_of(1)
    for rid in r1:
        write_row_json(tmp_path, rid, ["ok"] * 4)
    rep = sg.load_replay(tmp_path, r1[:-1], FRAME)             # the last row of round 1 was never in the file
    assert rep["finished_rounds"] == []
    assert rep["not_done"][r1[-1]] == "not in the rows file"
    assert rep["confirmatory"] == [] and rep["exploratory"] == r1[:-1]


def test_rows_file_with_round_four_or_unknown_row_is_refused(tmp_path):
    write_row_json(tmp_path, ids_of(1)[0], ["ok"] * 4)
    with pytest.raises(sg.Refused):
        sg.load_replay(tmp_path, ids_of(4)[:1], FRAME)
    with pytest.raises(sg.Refused):
        sg.load_replay(tmp_path, ["no_such_row"], FRAME)


def test_models_must_agree_and_be_gemini(tmp_path):
    a, b = ids_of(1)[:2]
    write_row_json(tmp_path, a, ["ok"] * 4, model="gemini-2.5-pro")
    write_row_json(tmp_path, b, ["ok"] * 4, model="gemini-3.8-flash")        # two models: refused
    with pytest.raises(sg.Refused):
        sg.load_replay(tmp_path, [a, b], FRAME)
    write_row_json(tmp_path, b, ["ok"] * 4, model="claude-haiku-5-5")
    write_row_json(tmp_path, a, ["ok"] * 4, model="claude-haiku-5-5")
    with pytest.raises(sg.Refused):
        sg.load_replay(tmp_path, [a, b], FRAME)


def test_drop_rate_counts_both_drops_and_flags_above_a_quarter(tmp_path):
    a, b = ids_of(1)[:2]
    write_row_json(tmp_path, a, ["ok", "ok", "ok", "dropped_parse"])
    write_row_json(tmp_path, b, ["ok", "ok", "ok", "ok"])
    rep = sg.load_replay(tmp_path, [a, b], FRAME)
    c = sg.member_counts(rep, [a, b], {}, flag=True)
    assert (c["members"], c["ok"], c["dropped_parse"], c["dropped_error"], c["dropped"]) == (8, 7, 1, 0, 1)
    assert c["drop_rate"] == 1 / 8 and not c["drop_rate_above_25_percent"]
    write_row_json(tmp_path, b, ["ok", "dropped_error", "dropped_parse", "ok"])
    rep = sg.load_replay(tmp_path, [a, b], FRAME)
    c = sg.member_counts(rep, [a, b], {}, flag=True)
    assert c["dropped"] == 3 and c["drop_rate"] == 3 / 8 and c["drop_rate_above_25_percent"]
    one_in_four = sg.member_counts({"rows": {"x": {"ends": {0: "ok", 1: "ok", 2: "ok", 3: "dropped_error"}}}}, ["x"], {}, flag=True)
    assert one_in_four["drop_rate"] == 0.25 and not one_in_four["drop_rate_above_25_percent"]   # exactly 25% is not above
    assert "drop_rate_above_25_percent" not in sg.member_counts(rep, [a, b], {})                # the flag is asked for, on a total


def test_an_unreadable_ok_member_is_a_drop_and_keeps_its_own_count():
    rep = {"rows": {"x": {"ends": {0: "ok", 1: "ok", 2: "ok", 3: "ok"}}, "y": {"ends": {0: "ok", 1: "ok", 2: "ok", 3: "dropped_parse"}}}}
    c = sg.member_counts(rep, ["x", "y"], {"x": [1, 3]}, flag=True)
    assert c["members"] == 8 and c["ok_but_unreadable"] == 2 and c["dropped_parse"] == 1
    assert c["dropped"] == 3 and c["ok"] == 5 and c["ok"] + c["dropped"] == c["members"]
    assert c["drop_rate"] == 3 / 8 and c["drop_rate_above_25_percent"]


# ------------------------------------------------------------------- members of a done row (item 4)

@pytest.mark.parametrize("numbers", [[0, 1, 3, 4], [1, 2, 3, 4], [0, 1, 2], [0, 1, 1, 2], [0, 1, 2, 3, 4, 5], []])
def test_a_done_row_must_list_members_zero_to_n_minus_one(tmp_path, numbers):
    a = ids_of(1)[0]
    write_row_json(tmp_path, a, ["ok"] * len(numbers), numbers=numbers)
    with pytest.raises(sg.Refused, match=a):
        sg.load_replay(tmp_path, [a], FRAME)


def test_every_done_row_must_list_the_same_number_of_members(tmp_path):
    a, b = ids_of(1)[:2]
    write_row_json(tmp_path, a, ["ok"] * 4)
    write_row_json(tmp_path, b, ["ok"] * 2)
    with pytest.raises(sg.Refused, match=b):
        sg.load_replay(tmp_path, [a, b], FRAME)
    write_row_json(tmp_path, a, ["ok"] * 2)
    assert sg.load_replay(tmp_path, [a, b], FRAME)["members_per_row"] == 2          # two per row is allowed


def test_a_row_not_done_may_list_any_members(tmp_path):
    a, b = ids_of(1)[:2]
    write_row_json(tmp_path, a, ["ok"] * 4)
    write_row_json(tmp_path, b, ["ok", "stopped", "stopped"], done=False)           # cut short: no check
    rep = sg.load_replay(tmp_path, [a, b], FRAME)
    assert b in rep["not_done"] and rep["members_per_row"] == 4


# --------------------------------------------------------------------------------------- guards

def test_refuses_when_the_freeze_check_fails(tmp_path, monkeypatch):
    h = patch_registration(monkeypatch, tmp_path)
    monkeypatch.setattr(sg, "freeze_problems", lambda: ["semantic/stats.py: changed since the freeze"])
    with pytest.raises(sg.Refused, match="freeze"):
        sg.check_guards(h)


def test_refuses_when_the_hash_given_is_not_the_registered_one(tmp_path, monkeypatch):
    h = patch_registration(monkeypatch, tmp_path)
    with pytest.raises(sg.Refused, match="registered hash"):
        sg.check_guards("0" * 64)
    with pytest.raises(sg.Refused):
        sg.check_guards(None)
    assert sg.check_guards(h.upper()) == h                   # case does not matter


def test_refuses_when_the_registration_file_was_edited(tmp_path, monkeypatch):
    h = patch_registration(monkeypatch, tmp_path)
    sg.PREREG_PATH.write_text("a test registration, edited\n")       # the hash file and the hash given still agree
    with pytest.raises(sg.Refused, match="edited"):
        sg.check_guards(h)


def test_refuses_when_the_hash_file_is_missing_or_empty(tmp_path, monkeypatch):
    h = patch_registration(monkeypatch, tmp_path)
    sg.PREREG_HASH_PATH.write_text("")
    with pytest.raises(sg.Refused, match="empty"):
        sg.check_guards(h)
    sg.PREREG_HASH_PATH.unlink()
    with pytest.raises(sg.Refused, match="does not exist"):
        sg.check_guards(h)


def test_refuses_when_the_rows_file_is_not_the_pinned_one(tmp_path, monkeypatch):
    h = patch_registration(monkeypatch, tmp_path)
    assert sg.check_guards(h) == h
    sg.ROWS_FILE.write_text(rows_text().replace(ids_of(1)[0] + "\n", ""))     # a row left out of round 1
    with pytest.raises(sg.Refused, match="pinned"):
        sg.check_guards(h)


def test_main_refuses_before_it_reads_any_output(tmp_path, monkeypatch):
    h = patch_registration(monkeypatch, tmp_path)
    monkeypatch.setattr(sg, "freeze_problems", lambda: ["x: changed since the freeze"])
    with pytest.raises(sg.Refused, match="freeze"):
        sg.main(["--gemini-root", str(tmp_path / "nope"), "--claude-root", str(tmp_path / "nope"),
                 "--prereg-sha256", h, "--out", str(tmp_path / "out")])
    assert not (tmp_path / "out").exists()


def test_the_real_freeze_registration_and_rows_file_hold(monkeypatch):
    assert sg.freeze_problems() == []
    real = sg.HERE / "PREREGISTRATION_GEMINI.sha256"
    if not real.is_file() or not (sg.HERE / "PREREGISTRATION_GEMINI.md").is_file():
        pytest.skip("the registration is not filed on this machine")
    h = real.read_text().split()[0]
    assert sg.check_guards(h) == h                           # the real file, the real hash, the pinned rows file
    assert sg.sha256_file(sg.ROWS_FILE) == sg.ROWS_FILE_SHA256 and sg.ROWS_FILE_SHA256.startswith("e1d05b9c2345192a")


def test_the_command_line_has_no_flag_that_could_change_the_analysis_set_or_the_registration(tmp_path, monkeypatch):
    h = patch_registration(monkeypatch, tmp_path)
    base = ["--gemini-root", str(tmp_path), "--claude-root", str(tmp_path), "--prereg-sha256", h, "--out", str(tmp_path / "o")]
    for flag in (["--rows", "x"], ["--prereg", "x"], ["--frame", "x"], ["--truth-dir", "x"], ["--no-validity"], ["--no-room-test"]):
        with pytest.raises(SystemExit) as e:
            sg.main(base + flag)
        assert not isinstance(e.value, sg.Refused) and e.value.code == 2, flag   # argparse: unknown argument


def test_refuses_paths_under_the_frozen_gemini_folders(tmp_path):
    bad = tmp_path / "hm3d_refs_work" / "gemini_static2" / "run"
    with pytest.raises(sg.Refused):
        sg.check_paths(bad, tmp_path / "out")
    with pytest.raises(sg.Refused):
        sg.check_paths(tmp_path / "in", tmp_path / "hm3d_refs_work" / "gemini_static" / "x")
    sg.check_paths(tmp_path / "in", tmp_path / "hm3d_refs_work" / "other")       # other folders are fine


def test_main_refuses_an_out_folder_that_holds_results(tmp_path, monkeypatch):
    h = patch_registration(monkeypatch, tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "results.json").write_text("{}")
    with pytest.raises(sg.Refused, match="exists"):
        sg.main(["--gemini-root", str(tmp_path), "--claude-root", str(tmp_path), "--prereg-sha256", h, "--out", str(out)])


# ------------------------------------------------------------------------------ 5a, synthetic

def rec(rid, cluster, g, o, b1=0.5):
    """A frozen-shaped record. g and o are Gemini's and the other model's score at L1, L2, L3."""
    def entry(x):
        return {"0": {"L1": x, "L2": x, "L3": x}}
    return {"row_id": rid, "cluster": cluster, "possible": {"L1": True, "L2": True, "L3": True},
            "model": entry(g), "comparators": {"B1": entry(b1)}}, {"row_id": rid, "cluster": cluster, "model": entry(o)}


def make(n, g, o):
    gem, opus, haiku = [], [], []
    for i in range(n):
        a, b = rec(f"r{i}", f"c{i}", g, o)
        gem.append(a)
        opus.append(b)
        haiku.append(dict(b))
    return gem, {"claude-opus-5-5": opus, "claude-haiku-5-5": haiku, "deepseek": opus}


def test_fewer_than_seven_clusters_is_exploratory_and_calls_nothing():
    gem, others = make(6, 0.9, 0.5)                            # Gemini far above, in 6 clusters
    a = sg.five_a(gem, others)
    assert a["exploratory"] and a["label"] == "exploratory: fewer than 7 clusters"
    assert a["n_clusters_min_family"] == 6
    assert all(v["found"] is None for v in a["family"].values())
    lines = sg.wording("gemini-2.5-pro", a, {"levels": {"L3": {"confirmatory": True, "verdict": "Inconclusive",
                                                                "comparators": {"D": {"mean_diff": 0.1}}}},
                                            "analysis": {"levels": {"L3": {"comparators": {"D": {"ci": (0.0, 0.2)}}}}}})
    assert "exploratory: fewer than 7 clusters" in lines[0]
    assert "does not carry over" not in " ".join(lines)


def test_seven_clusters_all_above_finds_all_four_with_holm():
    gem, others = make(7, 0.9, 0.5)
    a = sg.five_a(gem, others)
    assert not a["exploratory"] and a["label"] is None
    for v in a["family"].values():
        assert v["n_clusters"] == 7 and v["p"] == 1 / 128 and v["p_holm"] == pytest.approx(4 / 128)
        assert v["found"] is True
    assert a["tables"]["claude-opus-5-5"]["L1"]["p"] is None              # L1 is reported, not tested
    assert a["tables"]["claude-opus-5-5"]["L2"]["mean_diff"] == pytest.approx(0.4)
    assert a["tables"]["B1"]["L2"]["mean_diff"] == pytest.approx(0.4) and a["tables"]["B1"]["L2"]["p"] == 1 / 128
    b5 = {"levels": {"L3": {"confirmatory": True, "verdict": "Supported", "comparators": {"D": {"mean_diff": 0.1}}}},
          "analysis": {"levels": {"L3": {"comparators": {"D": {"ci": (0.0, 0.2)}}}}}}
    lines = sg.wording("gemini-2.5-pro", a, b5)
    assert lines[0].startswith("The Claude result does not carry over to the paper's model")
    assert any("puts its guesses in fitting regions more often than the controls" in x for x in lines)
    fb = sg.wording("gemini-3.8-flash", a, b5)
    assert all("Gemini 3.8 Flash" in x and "not the paper's model" in x for x in fb)


def test_seven_clusters_no_difference_finds_nothing_and_says_not_detectably_above():
    gem, others = make(7, 0.5, 0.5)
    a = sg.five_a(gem, others)
    assert all(v["found"] is False for v in a["family"].values())
    b5 = {"levels": {"L3": {"confirmatory": True, "verdict": "Rejected", "comparators": {"D": {"mean_diff": 0.0}}}},
          "analysis": {"levels": {"L3": {"comparators": {"D": {"ci": (-0.01, 0.01)}}}}}}
    lines = sg.wording("gemini-2.5-pro", a, b5)
    assert lines[0] == "On the same inputs Gemini 2.5 Pro, in the author's loop, was not detectably above Claude."
    assert any("not detectably above" in x and "95% interval" in x for x in lines[1:5])
    assert any("did not beat a trade of region contents by the 3-point margin" in x for x in lines)


def test_exploratory_set_is_never_called_even_with_many_clusters():
    gem, others = make(8, 0.9, 0.5)
    a = sg.five_a(gem, others, confirmatory=False)
    assert a["exploratory"] and all(v["found"] is None for v in a["family"].values())


def test_row_without_a_score_on_either_side_is_left_out_of_a_contrast():
    gem, others = make(7, 0.9, 0.5)
    gem[0]["model"] = {}                                      # every member of Gemini dropped on this row
    a = sg.five_a(gem, others)
    assert a["tables"]["claude-opus-5-5"]["L2"]["n_clusters"] == 6 and a["exploratory"]


# --------------------------------------------------------------- equality with the frozen Claude path

def build_fake(root, round1, round3_pairs, claude_root=CLAUDE_ROOT):
    """Copy Haiku's parsed graphs to <root>/<row>/gemini_new_graph_<k>.yaml with a matching row.json. A member Haiku
    did not finish ok is a dropped member here. Returns {row_id: ends}."""
    made = {}
    for rid in round1 + round3_pairs:
        status = ep.claude_member_status(claude_root, HAIKU, rid)
        base = ep.claude_row_dir(claude_root, HAIKU, rid)
        ends = []
        os.makedirs(root / rid, exist_ok=True)
        for k in range(4):
            if status[k] == "ok":
                shutil.copy(base / f"member_{k}" / "parsed_graph.yaml", root / rid / f"gemini_new_graph_{k}.yaml")
                ends.append("ok")
            else:
                ends.append("dropped_parse")
        write_row_json(root, rid, ends)
        made[rid] = ends
    return made


@pytest.fixture(scope="module")
def fake_run(tmp_path_factory):
    if not _have_data():
        pytest.skip("replay outputs or saved runs are absent")
    root = tmp_path_factory.mktemp("fake_gemini")
    r1, r3 = ids_of(1), ids_of(3)
    pairs = [x for x in r3 if "_s42_" in x]                    # both scenes, both arms: partners included
    made = build_fake(root, r1, pairs)
    stopped = [x for x in r3 if x not in pairs][0]
    write_row_json(root, stopped, ["ok", "stopped", "stopped", "stopped"], done=False)
    mp = pytest.MonkeyPatch()
    try:
        h = patch_registration(mp, root)
        out = root / "out"
        argv = ["--gemini-root", str(root), "--claude-root", CLAUDE_ROOT, "--prereg-sha256", h, "--out", str(out)]
        code = sg.main(argv)
    finally:
        mp.undo()
    assert code == 0
    return {"root": root, "out": out, "made": made, "r1": r1, "pairs": pairs, "stopped": stopped, "argv": argv,
            "results": json.loads((out / "results.json").read_text()),
            "records": json.loads((out / f"records_{MODEL}.json").read_text()),
            "md": (out / "RESULTS_GEMINI.md").read_text()}


def test_member_scores_equal_the_filed_haiku_records(fake_run):
    filed = {r["row_id"]: r for r in json.load(open(FILED))["records"]}
    mine = {r["row_id"]: r for r in fake_run["records"]["records"]}
    compared_rows = compared_members = compared_values = 0
    for rid in fake_run["r1"] + fake_run["pairs"]:
        a, b = mine[rid], filed[rid]
        assert a["possible"] == b["possible"] and a["n_unobserved"] == b["n_unobserved"]
        assert a["model"] == b["model"]                         # every member: L1, L2, L3, counts, extras
        assert a["comparators"] == b["comparators"]             # B1 B2 B3 B3L B4 B5 D and the B3 sensitivity forms
        assert a.get("validity") == b.get("validity")
        compared_rows += 1
        compared_members += len(a["model"])
        for m in a["model"].values():
            compared_values += sum(1 for lv in ("L1", "L2", "L3") if m[lv] is not None)
        for name, ents in a["comparators"].items():
            for v in ents.values():
                compared_values += sum(1 for lv in ("L1", "L2", "L3") if v.get(lv) is not None)
    assert compared_rows == 16 and compared_members > 40 and compared_values > 300
    print(f"equality test: {compared_rows} rows, {compared_members} members, {compared_values} scores compared")


def test_fake_gemini_minus_haiku_is_zero_in_every_cluster(fake_run):
    conf = fake_run["results"]["confirmatory"]
    t = conf["5a"]["tables"][HAIKU]
    for lv in ("L1", "L2", "L3"):
        # at L1 some rows have no hit possible (§8), so fewer clusters can score there
        assert t[lv]["n_clusters"] >= (1 if lv == "L1" else 7), lv
        assert t[lv]["clusters"] and all(v == 0.0 for v in t[lv]["clusters"].values()), lv
        assert t[lv]["mean_diff"] == 0.0
        assert t[lv]["model_clusters"] == t[lv]["other_clusters"]
    for key, v in conf["5a"]["family"].items():
        if HAIKU in key:
            assert v["found"] is False and v["mean_diff"] == 0.0
    assert not conf["5a"]["exploratory"]                         # 12 clusters in the finished round
    exp = fake_run["results"]["exploratory"]["5a"]["tables"][HAIKU]
    for lv in ("L2", "L3"):
        assert exp[lv]["clusters"] and all(v == 0.0 for v in exp[lv]["clusters"].values())


def test_analysis_set_confirmatory_exploratory_and_not_done(fake_run):
    res = fake_run["results"]
    s = res["analysis_set"]
    assert s["finished_rounds"] == [1]
    assert res["confirmatory"]["rows"] == fake_run["r1"]
    assert res["exploratory"]["rows"] == fake_run["pairs"]       # finished rows of round 3, apart
    assert fake_run["stopped"] in s["not_done"]
    assert s["confirmatory"]["members"] == 48 and s["confirmatory"]["rows"] == 12
    made = fake_run["made"]
    assert s["confirmatory"]["dropped"] == sum(e.count("dropped_parse") for r, e in made.items() if r in fake_run["r1"])
    assert res["confirmatory"]["clusters"] == 12
    assert res["exploratory"]["5a"]["label"].startswith("exploratory")
    md = fake_run["md"]
    assert "Gemini minus Haiku" in md and md.count("### Wording") == 1
    assert res["run_info"]["semantic_gemini_sha256"] == hashlib.sha256(open(WRAPPER, "rb").read()).hexdigest()


def test_drop_rate_is_given_over_all_rows_run_and_the_flag_is_on_the_total(fake_run):
    s = fake_run["results"]["analysis_set"]
    tot, conf, expl = s["all_rows_run"], s["confirmatory"], s["exploratory"]
    assert tot["rows"] == conf["rows"] + expl["rows"] == 16
    assert tot["members"] == conf["members"] + expl["members"] == 64
    assert tot["dropped"] == conf["dropped"] + expl["dropped"]
    assert tot["drop_rate"] == tot["dropped"] / 64
    assert tot["drop_rate_above_25_percent"] == (tot["drop_rate"] > 0.25)
    assert "drop_rate_above_25_percent" not in conf and "drop_rate_above_25_percent" not in expl
    assert "All rows run" in fake_run["md"] and s["members_per_row"] == 4


def test_only_the_confirmatory_set_gets_the_sentences_of_section_6(fake_run):
    res = fake_run["results"]
    assert isinstance(res["confirmatory"]["wording"], list) and len(res["confirmatory"]["wording"]) > 3
    assert res["exploratory"]["wording"] is None
    assert "No sentence of section 6 is written for the exploratory set" in fake_run["md"]
    assert all("Gemini 3.8 Flash" in x and "not the paper's model" in x for x in res["confirmatory"]["wording"][:-1])
    assert "5b" in res["exploratory"] and "5a" in res["exploratory"]                       # its numbers are still there


def test_room_count_label_says_how_many_members_a_row_has(fake_run):
    for key in ("confirmatory", "exploratory"):
        labels = [c["label"] for c in fake_run["results"][key]["5c"]["room_count"]]
        assert labels == ["1 of 4 members, untyped", "1 of 4 members, typed", "2 of 4 members, untyped", "2 of 4 members, typed"]
    assert "1 of 4 members" in fake_run["md"]


def test_room_count_label_follows_the_members_per_row():
    got = sg.room_count_labels({"totals": {"runs": 1, "of": 9, "predicted_1of4_untyped": 3, "predicted_2of4_typed": 1}}, 2)
    assert [c["label"] for c in got] == ["1 of 2 members, untyped", "1 of 2 members, typed", "2 of 2 members, untyped", "2 of 2 members, typed"]
    assert [c["regions_predicted"] for c in got] == [3, 0, 0, 1] and all(c["regions_unseen_at_stage0"] == 9 for c in got)


def test_run_info_records_every_argument_and_path(fake_run):
    info = fake_run["results"]["run_info"]
    assert info["argv"] == fake_run["argv"]
    a = info["arguments"]
    assert a["overwrite"] is False and a["claude_root"] == CLAUDE_ROOT and a["runs_root"] is None
    assert a["gemini_root"] == str(fake_run["root"]) and a["out"] == str(fake_run["out"])
    p = info["paths_used"]
    assert {"prereg", "prereg_hash_file", "rows_file", "frame", "truth_dir", "runs_root", "claude_root"} <= set(p)
    assert p["runs_root"] == str(ep.RUNS_ROOT) and p["frame"] == str(rs.FRAME_PATH)
    assert info["rows_file_sha256"] == info["rows_file_pinned_sha256"] and info["freeze_holds"] is True
    assert info["model"] == MODEL


def test_5b_uses_the_frozen_verdict_and_only_l3_is_confirmatory(fake_run):
    b = fake_run["results"]["confirmatory"]["5b"]["levels"]
    assert b["L3"]["confirmatory"] and not b["L1"]["confirmatory"] and not b["L2"]["confirmatory"]
    for lv in ("L1", "L2", "L3"):
        assert b[lv]["verdict"] in ("Supported", "Rejected", "Inconclusive")
        assert b[lv]["p_holm"] == b[lv]["p"]                     # a family of one: no adjustment
    assert b["L3"]["named"] == "D" and b["L3"]["delta"] == 0.03
    assert set(b["L3"]["comparators"]) >= {"B5", "D", "B3L"}
    assert b["L1"]["comparators"]["B3"]["comparator_own_score"] is not None
    assert fake_run["results"]["confirmatory"]["5c"]["wrong_house_gate"]["L1"]["n_pairs"] > 0


@needs_data
def test_a_dropped_member_is_counted_and_not_scored(tmp_path):
    rid = ids_of(1)[0]
    build_fake(tmp_path, [rid], [])
    # mark member 2 dropped although its file is still on disk: it must not be read
    status = ep.claude_member_status(CLAUDE_ROOT, HAIKU, rid)
    assert status[2] == "ok", "this test needs a row whose member 2 is ok"
    write_row_json(tmp_path, rid, ["ok", "ok", "dropped_error", "ok"])
    assert (tmp_path / rid / "gemini_new_graph_2.yaml").is_file()
    rep = sg.load_replay(tmp_path, [rid], FRAME)
    ctx = rs.build_context(rs.FRAME_PATH, ep.RUNS_ROOT)
    members, docs, unreadable = sg.build_members(ctx, rep, tmp_path)
    assert [m.member for m in members[rid]] == [0, 1, 3] and sorted(docs[rid]) == [0, 1, 3]
    assert unreadable == {}
    c = sg.member_counts(rep, [rid], unreadable)
    assert c["members"] == 4 and c["ok"] == 3 and c["dropped_error"] == 1 and c["drop_rate"] == 0.25
    assert all(not members[r] for r in members if r != rid)      # no other row has members


@needs_data
def test_an_ok_member_with_an_unreadable_file_is_reported(tmp_path):
    rid = ids_of(1)[0]
    write_row_json(tmp_path, rid, ["ok", "ok", "ok", "ok"])
    (tmp_path / rid / "gemini_new_graph_0.yaml").write_text("not: a graph\n")
    rep = sg.load_replay(tmp_path, [rid], FRAME)
    ctx = rs.build_context(rs.FRAME_PATH, ep.RUNS_ROOT)
    members, _d, unreadable = sg.build_members(ctx, rep, tmp_path)
    assert members[rid] == [] and unreadable == {rid: [0, 1, 2, 3]}
    c = sg.member_counts(rep, [rid], unreadable, flag=True)
    assert c["ok_but_unreadable"] == 4 and c["dropped"] == 4 and c["ok"] == 0     # no score, so a drop
    assert c["drop_rate"] == 1.0 and c["drop_rate_above_25_percent"]


@needs_data
def test_an_all_unfinished_round_gives_no_confirmatory_sentence(tmp_path, monkeypatch):
    """Two finished rows of round 3 and nothing else: no round finished, so there is no confirmatory result."""
    pair = [x for x in ids_of(3) if "_s42_official" in x]
    build_fake(tmp_path, [], pair)
    h = patch_registration(monkeypatch, tmp_path)
    out = tmp_path / "out"
    assert sg.main(["--gemini-root", str(tmp_path), "--claude-root", CLAUDE_ROOT, "--prereg-sha256", h, "--out", str(out),
                    "--overwrite"]) == 0
    res = json.loads((out / "results.json").read_text())
    assert res["analysis_set"]["finished_rounds"] == [] and res["confirmatory"]["rows"] == []
    assert res["confirmatory"]["wording"] == ["No round finished, so there is no confirmatory result and no sentence of section 6 applies."]
    assert res["exploratory"]["rows"] == pair and res["exploratory"]["wording"] is None
    assert res["run_info"]["arguments"]["overwrite"] is True


# ----------------------------------------------- the author's own output format (October's Gemini files)

@needs_data
def test_an_october_gemini_file_reads_the_same_through_the_wrapper_and_the_frozen_gemini_reader(tmp_path):
    """The files October's Gemini run saved come from the author's own loop. Read through `build_members` they must
    give the member that the frozen `members_for(row, "gemini", ...)` gives for the same round-4 row."""
    compared = 0
    ctx = rs.build_context(rs.FRAME_PATH, ep.RUNS_ROOT)
    for rid in ids_of(4):
        row = ep.load_row(rid, ep.RUNS_ROOT, rs.FRAME_PATH)
        d = ep.gemini_dir(row, ep.GEMINI_ROOT, rs.FRAME_PATH)
        if d is None:
            continue
        files = ep.member_files(row, "gemini", ep.RUNS_ROOT, ep.GEMINI_ROOT, None, rs.FRAME_PATH)
        frozen = ep.members_for(row, "gemini", ep.RUNS_ROOT, ep.GEMINI_ROOT, None, rs.FRAME_PATH)
        assert files and len(frozen) == len(files)
        os.makedirs(tmp_path / rid)
        for m, f in files:
            shutil.copy(f, tmp_path / rid / f"gemini_new_graph_{m}.yaml")
        ends = {m: ("ok" if m in {k for k, _ in files} else "dropped_parse") for m in range(4)}
        replay = {"rows": {rid: {"finished": True, "ends": ends}}}
        members, docs, unreadable = sg.build_members(ctx, replay, tmp_path)
        assert unreadable == {} and members[rid] == frozen          # equal members: same guesses, same scores
        compared += len(frozen)
    if not compared:
        pytest.skip("no October Gemini file is on this machine (frozen ep.GEMINI_ROOT / ep.gemini_dir)")
    print(f"october test: {compared} members compared")
