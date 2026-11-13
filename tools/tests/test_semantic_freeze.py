"""Tests for freeze.py: write and check the sha256 list of the scorer files (PREREGISTRATION_SEMANTIC.md §14)."""
import hashlib
import importlib.util
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
SEM = os.path.abspath(os.path.join(HERE, "..", "live_policy", "semantic"))


def load(name):
    key = f"_semantic_sibling_{name}"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, os.path.join(SEM, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod
    spec.loader.exec_module(mod)
    return mod


fz = load("freeze")


def sha(b):
    return hashlib.sha256(b).hexdigest()


@pytest.fixture
def tree(tmp_path):
    repo = tmp_path / "repo"
    sem = repo / "tools" / "live_policy" / "semantic"
    (sem / "truth").mkdir(parents=True)
    (sem / "__pycache__").mkdir()
    (sem / "a.py").write_text("A = 1\n")
    (sem / "b.py").write_text("B = 2\n")
    (sem / "canon_labels.json").write_text("{}")
    (sem / "sample_frame.txt").write_text("row\n")
    (sem / "README.md").write_text("notes")                      # not a scorer file
    (sem / "__pycache__" / "a.cpython.pyc").write_bytes(b"x")
    (sem / "truth" / "t1.json").write_text("1")
    (sem / "truth" / "sub").mkdir()
    (sem / "truth" / "sub" / "t2.npz").write_bytes(b"2")
    (repo / "extra.md").write_text("cost")
    return repo, sem


def test_write_lists_every_scorer_file_and_check_passes(tree):
    repo, sem = tree
    path = sem / "FREEZE.sha256"
    listed = fz.write(path, sem, repo, extras=[repo / "extra.md"])
    names = sorted(listed)
    assert names == ["extra.md", "tools/live_policy/semantic/a.py", "tools/live_policy/semantic/b.py",
                     "tools/live_policy/semantic/canon_labels.json", "tools/live_policy/semantic/sample_frame.txt",
                     "tools/live_policy/semantic/truth/sub/t2.npz", "tools/live_policy/semantic/truth/t1.json"]
    assert listed["tools/live_policy/semantic/a.py"] == sha(b"A = 1\n")
    lines = [l for l in path.read_text().splitlines() if l and not l.startswith("#")]
    assert len(lines) == 7 and lines[0].split()[0] == listed[lines[0].split(None, 1)[1]]
    assert fz.check(path, sem, repo) == []


def test_check_names_a_changed_missing_and_unlisted_file(tree):
    repo, sem = tree
    path = sem / "FREEZE.sha256"
    fz.write(path, sem, repo, extras=[repo / "extra.md"])
    (sem / "a.py").write_text("A = 2\n")
    (sem / "truth" / "t1.json").unlink()
    (sem / "c.py").write_text("C = 3\n")                           # a new scorer file after the freeze
    (repo / "extra.md").write_text("cost changed")
    problems = " | ".join(fz.check(path, sem, repo))
    for name in ("a.py", "truth/t1.json", "c.py", "extra.md"):
        assert name in problems
    assert "b.py" not in problems


def test_check_refuses_a_missing_or_malformed_freeze_file(tree):
    repo, sem = tree
    assert "FREEZE.sha256" in " ".join(fz.check(sem / "FREEZE.sha256", sem, repo))
    (sem / "FREEZE.sha256").write_text("x\n")
    assert fz.check(sem / "FREEZE.sha256", sem, repo)


def test_a_missing_extra_file_is_an_error(tree):
    repo, sem = tree
    with pytest.raises(FileNotFoundError):
        fz.write(sem / "FREEZE.sha256", sem, repo, extras=[repo / "nope.md"])


def test_main_write_and_check(tree, capsys):
    repo, sem = tree
    assert fz.main(["write", "--extra", str(repo / "extra.md")], semantic_dir=sem, repo=repo) == 0
    assert (sem / "FREEZE.sha256").is_file()
    assert fz.main(["check"], semantic_dir=sem, repo=repo) == 0
    (sem / "b.py").write_text("B = 3\n")
    assert fz.main(["check"], semantic_dir=sem, repo=repo) == 1
    assert "b.py" in capsys.readouterr().out


def test_the_real_folder_lists_this_scorer_and_the_truth():
    real_sem = fz.SEMANTIC_DIR
    files = fz.collect(real_sem, fz.REPO, [])
    names = set(files)
    assert "tools/live_policy/semantic/run_semantic.py" in names and "tools/live_policy/semantic/canon_labels.json" in names
    assert "tools/live_policy/semantic/sample_frame.txt" in names and "tools/live_policy/semantic/freeze.py" in names
    assert any(n.startswith("tools/live_policy/semantic/truth/") for n in names)
    assert not any("__pycache__" in n or n.endswith("FREEZE.sha256") for n in names)


def test_driver_claude_guard_calls_check_and_names_the_file(monkeypatch, tmp_path):
    rs = load("run_semantic")
    repo = tmp_path / "repo"
    sem = repo / "tools" / "live_policy" / "semantic"
    sem.mkdir(parents=True)
    (sem / "a.py").write_text("A = 1\n")
    (sem / "canon_labels.json").write_text("{}")
    (sem / "sample_frame.txt").write_text("x")
    (sem / "truth").mkdir()
    fz.write(sem / "FREEZE.sha256", sem, repo)
    prereg = tmp_path / "PRE.md"
    prereg.write_text("text")
    hashfile = tmp_path / "PRE.sha256"
    hashfile.write_text(sha(b"text") + "  PRE.md\n")
    monkeypatch.setattr(rs, "PREREG_HASH_PATH", hashfile)
    monkeypatch.setattr(rs, "FREEZE_PATH", sem / "FREEZE.sha256")
    monkeypatch.setattr(rs, "FREEZE_SEMANTIC_DIR", sem)
    monkeypatch.setattr(rs, "FREEZE_REPO", repo)
    rs.check_guards(["claude-opus-5-5"], sha(b"text"))                # intact: passes
    rs.check_guards(["deepseek"], sha(b"text"))
    (sem / "a.py").write_text("A = 99\n")
    with pytest.raises(SystemExit) as e:
        rs.check_guards(["claude-opus-5-5"], sha(b"text"))
    assert "a.py" in str(e.value) and "freeze" in str(e.value).lower()
    rs.check_guards(["deepseek"], sha(b"text"))                       # an exploratory run does not need the freeze


def test_truth_only_hash_leaves_the_code_out(tree):
    repo, sem = tree
    assert fz.main(["write", "--truth-only"], semantic_dir=sem, repo=repo) == 0
    listed = fz.read(sem / "TRUTH.sha256")
    assert set(listed) == {"tools/live_policy/semantic/canon_labels.json", "tools/live_policy/semantic/sample_frame.txt",
                           "tools/live_policy/semantic/truth/sub/t2.npz", "tools/live_policy/semantic/truth/t1.json"}
    (sem / "a.py").write_text("A = 5\n")                           # code may change; the truth hash does not care
    assert fz.main(["check", "--truth-only"], semantic_dir=sem, repo=repo) == 0
    (sem / "truth" / "t1.json").write_text("changed")
    assert fz.main(["check", "--truth-only"], semantic_dir=sem, repo=repo) == 1
