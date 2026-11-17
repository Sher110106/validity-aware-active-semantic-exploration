"""Tests for tools/live_policy/host/compress_old_dsg.sh, run in its plain-shell mode on a made-up tree."""
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "live_policy" / "host" / "compress_old_dsg.sh"
pytestmark = pytest.mark.skipif(
    not all(shutil.which(t) for t in ("bash", "zstd", "sha256sum", "xargs")),
    reason="needs bash, zstd, sha256sum and xargs")


def make_tree(tmp_path):
    files = {
        "frontier_seeds/e4_00853_s42_frontier_60m/stages/0/graph0_dsg.json": b'{"nodes": [1, 2, 3]}' * 400,
        "frontier_seeds/e7_00871_s42_frontier_end/stages/0/graph0_dsg.json": b'{"kept": true}' * 300,
        "frontier_seeds/e7_00871_s42_frontier_end_FAILED_ATTEMPT_1213/stages/0/graph1_dsg.json": b'{"old": 1}' * 500,
        "live_campaign/e1_00853_s42_official_60m/stages/3/graph1_dsg.json": b'{"edges": []}' * 700,
        "live_campaign/e1_00853_s42_official_60m/stages/4/graph1_dsg.json": b'{"clash": 0}' * 200,
        "live_campaign/e1_00853_s42_official_60m/stages/4/graph1_dsg.json.zst": b"not a real archive",
        "live_campaign/e1_00853_s42_official_60m/stages/3/habitat_scene_graph_new_graph_0.yaml": b"rooms: []\n",
    }
    for rel, data in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    (tmp_path / "scratch").mkdir()
    return files


def run(tmp_path, mode):
    env = dict(os.environ,
               COMPRESS_LOCAL_ROOTS=f"{tmp_path / 'frontier_seeds'} {tmp_path / 'live_campaign'}",
               COMPRESS_SCRATCH=str(tmp_path / "scratch"))
    return subprocess.run(["bash", str(SCRIPT), mode], env=env, capture_output=True, text=True, timeout=120)


def snapshot(tmp_path):
    return {str(p.relative_to(tmp_path)): p.read_bytes() for p in sorted(tmp_path.rglob("*")) if p.is_file()}


def test_dry_run_counts_and_changes_nothing(tmp_path):
    make_tree(tmp_path)
    before = snapshot(tmp_path)
    r = run(tmp_path, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "raw graph files to compress: 4," in r.stdout
    assert "compressed files there already: 1" in r.stdout
    assert "dry run: nothing changed" in r.stdout
    assert snapshot(tmp_path) == before


def test_go_compresses_checks_and_keeps_what_it_must(tmp_path):
    files = make_tree(tmp_path)
    r = run(tmp_path, "--go")
    assert r.returncode == 0, r.stderr
    assert "compressed and checked: 3 files" in r.stdout
    assert "not compressed: 1 files" in r.stdout
    assert "raw graph files left: 1" in r.stdout

    done = ["frontier_seeds/e4_00853_s42_frontier_60m/stages/0/graph0_dsg.json",
            "frontier_seeds/e7_00871_s42_frontier_end_FAILED_ATTEMPT_1213/stages/0/graph1_dsg.json",
            "live_campaign/e1_00853_s42_official_60m/stages/3/graph1_dsg.json"]
    for rel in done:
        raw, packed = tmp_path / rel, tmp_path / (rel + ".zst")
        assert not raw.exists() and packed.exists()
        back = subprocess.run(["zstd", "-dc", str(packed)], capture_output=True, check=True).stdout
        assert back == files[rel]

    # The November queue's own folder is left alone.
    kept = tmp_path / "frontier_seeds/e7_00871_s42_frontier_end/stages/0/graph0_dsg.json"
    assert kept.read_bytes() == files["frontier_seeds/e7_00871_s42_frontier_end/stages/0/graph0_dsg.json"]
    assert not Path(str(kept) + ".zst").exists()

    # A file whose .zst is there already keeps its raw copy, and the old .zst is not overwritten.
    clash = tmp_path / "live_campaign/e1_00853_s42_official_60m/stages/4/graph1_dsg.json"
    assert clash.exists()
    assert Path(str(clash) + ".zst").read_bytes() == b"not a real archive"

    # Other files are untouched.
    yaml = tmp_path / "live_campaign/e1_00853_s42_official_60m/stages/3/habitat_scene_graph_new_graph_0.yaml"
    assert yaml.read_bytes() == b"rooms: []\n"

    # The hash list names each compressed file with the sha256 of its raw bytes.
    lists = list((tmp_path / "scratch").glob("dsg_compress_*.sha256"))
    assert len(lists) == 1
    got = dict(reversed(line.split("  ", 1)) for line in lists[0].read_text().splitlines())
    assert got == {str(tmp_path / rel): hashlib.sha256(files[rel]).hexdigest() for rel in done}
    failed = list((tmp_path / "scratch").glob("dsg_compress_*.failed"))[0].read_text()
    assert "exists already" in failed and "stages/4/graph1_dsg.json.zst" in failed
    assert not list((tmp_path / "scratch").glob("*.part.*"))


def test_a_second_go_finds_nothing_new(tmp_path):
    make_tree(tmp_path)
    assert run(tmp_path, "--go").returncode == 0
    after_first = {k: v for k, v in snapshot(tmp_path).items() if not k.startswith("scratch/")}
    r = run(tmp_path, "--go")
    assert r.returncode == 0, r.stderr
    assert "compressed and checked: 0 files" in r.stdout
    assert {k: v for k, v in snapshot(tmp_path).items() if not k.startswith("scratch/")} == after_first


def test_a_part_file_left_by_a_killed_run_does_not_block(tmp_path):
    files = make_tree(tmp_path)
    rel = "live_campaign/e1_00853_s42_official_60m/stages/3/graph1_dsg.json"
    (tmp_path / (rel + ".zst.part")).write_bytes(b"half an archive")
    r = run(tmp_path, "--go")
    assert r.returncode == 0, r.stderr
    assert "compressed and checked: 3 files" in r.stdout
    assert not (tmp_path / (rel + ".zst.part")).exists() and not (tmp_path / rel).exists()
    back = subprocess.run(["zstd", "-dc", str(tmp_path / (rel + ".zst"))], capture_output=True, check=True).stdout
    assert back == files[rel]


def stub(dirpath, name, body):
    p = dirpath / name
    p.write_text("#!/bin/bash\n" + body + "\n")
    p.chmod(0o755)


def test_a_bad_compressed_copy_keeps_the_raw_file(tmp_path):
    files = make_tree(tmp_path)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    # A zstd that unpacks to the wrong bytes: every round trip must fail.
    stub(bindir, "zstd", f'for a in "$@"; do [ "$a" = "-dc" ] && {{ "{shutil.which("zstd")}" "$@" | tr a-z b-za; exit 0; }}; done\n'
                         f'exec "{shutil.which("zstd")}" "$@"')
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}",
               COMPRESS_LOCAL_ROOTS=f"{tmp_path / 'frontier_seeds'} {tmp_path / 'live_campaign'}",
               COMPRESS_SCRATCH=str(tmp_path / "scratch"))
    r = subprocess.run(["bash", str(SCRIPT), "--go"], env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    assert "compressed and checked: 0 files" in r.stdout and "not compressed: 4 files" in r.stdout
    for rel, data in files.items():
        assert (tmp_path / rel).read_bytes() == data            # every file is as it was
    assert not [p for p in tmp_path.rglob("*.zst.part")]
    assert len([p for p in tmp_path.rglob("*_dsg.json.zst")]) == 1   # only the one that was there before
    failed = list((tmp_path / "scratch").glob("dsg_compress_*.failed"))[0].read_text()
    assert failed.count("round trip differs") == 3 and failed.count("exists already") == 1


@pytest.mark.parametrize("roots", ["/etc", "/workspace/runs/live_campaign/../../etc", "/workspace/runs/live_campaign /tmp",
                                   "/workspace/runs/live_campaign/x", "/workspace/runs/apr"])
def test_container_mode_refuses_any_folder_but_the_two(tmp_path, roots):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    stub(bindir, "docker", f'touch "{tmp_path}/docker_was_called"; exit 1')
    env = {k: v for k, v in os.environ.items() if not k.startswith("COMPRESS_")}
    env.update(PATH=f"{bindir}:{os.environ['PATH']}", COMPRESS_ROOTS=roots)
    for mode in ("--dry-run", "--go"):
        r = subprocess.run(["bash", str(SCRIPT), mode], env=env, capture_output=True, text=True, timeout=60)
        assert r.returncode == 2 and "REFUSED" in r.stdout and "not one of the two run folders" in r.stdout
    assert not (tmp_path / "docker_was_called").exists()


@pytest.mark.parametrize("live", ["queue", "queue_process", "runner", "container"])
def test_go_refuses_while_anything_is_live(tmp_path, live):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    stub(bindir, "systemctl", 'echo "paper-queue-rerun9.scope loaded active running x"' if live == "queue" else "exit 0")
    stub(bindir, "pgrep", {"queue_process": 'case "$*" in *paper_queue*) echo 123; exit 0;; esac; exit 1',
                           "runner": 'case "$*" in *live_runner*) echo 123; exit 0;; esac; exit 1'}.get(live, "exit 1"))
    stub(bindir, "docker", ('case "$*" in *"ps -eo"*) echo "    1 sleep infinity"; '
                            + ('echo "   77 python3 run_pipeline_with_policy.py"; ' if live == "container" else "")
                            + f'exit 0;; esac; touch "{tmp_path}/docker_did_work"; exit 1'))
    env = {k: v for k, v in os.environ.items() if not k.startswith("COMPRESS_")}
    env.update(PATH=f"{bindir}:{os.environ['PATH']}")
    r = subprocess.run(["bash", str(SCRIPT), "--go"], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 1 and "REFUSED" in r.stdout, r.stdout + r.stderr
    assert not (tmp_path / "docker_did_work").exists()


def test_the_test_mode_refuses_the_workspace(tmp_path):
    env = dict(os.environ, COMPRESS_LOCAL_ROOTS="/workspace/runs/live_campaign", COMPRESS_SCRATCH=str(tmp_path))
    r = subprocess.run(["bash", str(SCRIPT), "--go"], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 2 and "REFUSED" in r.stdout
    env = dict(os.environ, ASP_WS=str(tmp_path), COMPRESS_LOCAL_ROOTS=str(tmp_path / "runs"), COMPRESS_SCRATCH=str(tmp_path))
    r = subprocess.run(["bash", str(SCRIPT), "--go"], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 2 and "REFUSED" in r.stdout


def test_it_wants_a_mode(tmp_path):
    make_tree(tmp_path)
    assert run(tmp_path, "--now").returncode == 2
