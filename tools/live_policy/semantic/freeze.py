"""The freeze of the semantic scorer (PREREGISTRATION_SEMANTIC.md §14).

    python freeze.py write [--extra FILE ...]    write FREEZE.sha256
    python freeze.py check                       verify it; exit 1 and name every file that differs
    python freeze.py write --truth-only          write TRUTH.sha256: only canon_labels.json, sample_frame.txt and
                                                 truth/ (§14: hashed before the first exploratory score)
    python freeze.py check --truth-only          verify it

FREEZE.sha256 lists the sha256 of: every `*.py` in this folder, canon_labels.json, sample_frame.txt, every
file under truth/, and each extra file given on the command line (the table of detectable differences, the
cost addendum). Paths are relative to the repo root; a file outside the repo is listed by its absolute path.
`check` also names a scorer file that exists but is not listed. Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

SEMANTIC_DIR = Path(__file__).resolve().parent
REPO = SEMANTIC_DIR.parent.parent.parent
FREEZE_NAME = "FREEZE.sha256"
TRUTH_NAME = "TRUTH.sha256"
HEADER = "# sha256 of every file the semantic scorer is frozen on (freeze.py write). Verify with: freeze.py check"


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _rel(path: Path, repo: Path) -> str:
    path = Path(path).resolve()
    try:
        return path.relative_to(Path(repo).resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _abs(name: str, repo: Path) -> Path:
    p = Path(name)
    return p if p.is_absolute() else Path(repo) / p


def scorer_files(semantic_dir: Path, truth_only: bool = False) -> List[Path]:
    """The files that are always frozen: *.py, canon_labels.json, sample_frame.txt, everything in truth/.
    With truth_only, the *.py files are left out."""
    sem = Path(semantic_dir)
    files = [] if truth_only else sorted(sem.glob("*.py"))
    for name in ("canon_labels.json", "sample_frame.txt"):
        files.append(sem / name)
    truth = sem / "truth"
    if truth.is_dir():
        files += sorted(p for p in truth.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.name != ".DS_Store")
    return files


def collect(semantic_dir: Path, repo: Path, extras: Iterable[Path], truth_only: bool = False) -> Dict[str, str]:
    """{path: sha256} for the scorer files and the extras. A missing file is an error."""
    out: Dict[str, str] = {}
    for p in list(scorer_files(semantic_dir, truth_only)) + [Path(e) for e in extras]:
        if not Path(p).is_file():
            raise FileNotFoundError(f"cannot freeze {p}: no such file")
        out[_rel(p, repo)] = _sha(p)
    return out


def write(freeze_path: Path, semantic_dir: Path = SEMANTIC_DIR, repo: Path = REPO, extras: Sequence[Path] = (),
          truth_only: bool = False) -> Dict[str, str]:
    listed = collect(semantic_dir, repo, extras, truth_only)
    lines = [HEADER] + [f"{h}  {name}" for name, h in sorted(listed.items())]
    Path(freeze_path).write_text("\n".join(lines) + "\n")
    return listed


def read(freeze_path: Path) -> Dict[str, str]:
    """{path: sha256} from FREEZE.sha256. Raises ValueError on a malformed line."""
    out: Dict[str, str] = {}
    for n, line in enumerate(Path(freeze_path).read_text().splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or len(parts[0]) != 64 or any(c not in "0123456789abcdef" for c in parts[0].lower()):
            raise ValueError(f"{freeze_path} line {n} is not '<sha256>  <path>'")
        out[parts[1].strip()] = parts[0].lower()
    return out


def check(freeze_path: Path, semantic_dir: Path = SEMANTIC_DIR, repo: Path = REPO, truth_only: bool = False) -> List[str]:
    """Problems found, one string per file, each naming the file. An empty list means the freeze holds."""
    freeze_path = Path(freeze_path)
    if not freeze_path.is_file():
        return [f"{freeze_path.name} does not exist"]
    try:
        listed = read(freeze_path)
    except ValueError as exc:
        return [str(exc)]
    if not listed:
        return [f"{freeze_path.name} lists no file"]
    problems: List[str] = []
    for name, want in sorted(listed.items()):
        p = _abs(name, repo)
        if not p.is_file():
            problems.append(f"{name}: missing")
        elif _sha(p) != want:
            problems.append(f"{name}: changed since the freeze")
    for p in scorer_files(semantic_dir, truth_only):
        if p.is_file() and _rel(p, repo) not in listed:
            problems.append(f"{_rel(p, repo)}: not in the freeze")
    return problems


def main(argv: Optional[Sequence[str]] = None, semantic_dir: Path = SEMANTIC_DIR, repo: Path = REPO) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("--extra", action="append", default=[], help="another file to freeze (repeat the flag)")
    w.add_argument("--truth-only", action="store_true", help="hash only the label table, the frame and truth/")
    c = sub.add_parser("check")
    c.add_argument("--truth-only", action="store_true")
    args = ap.parse_args(argv)
    path = Path(semantic_dir) / (TRUTH_NAME if args.truth_only else FREEZE_NAME)
    if args.cmd == "write":
        listed = write(path, semantic_dir, repo, [Path(e) for e in args.extra], args.truth_only)
        print(f"wrote {path} ({len(listed)} files)")
        return 0
    problems = check(path, semantic_dir, repo, args.truth_only)
    if problems:
        print("freeze check FAILED:")
        for p in problems:
            print("  " + p)
        return 1
    print(f"freeze check ok ({len(read(path))} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
