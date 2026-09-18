from __future__ import annotations

import argparse, json, shutil
from typing import Dict, List, Union
from pathlib import Path
from .manifest import file_sha256


def deploy(source: Union[str, Path], destination: Union[str, Path], files: List[str], expected: Dict[str, str], *, dry_run: bool = True) -> None:
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or destination.is_relative_to(source):
        raise ValueError("destination must be a sibling/outside source tree")
    for rel in files:
        src = (source / rel).resolve()
        if not src.is_file() or not str(src).startswith(str(source) + "/"):
            raise ValueError(f"invalid source file: {rel}")
        actual = file_sha256(src)
        if expected.get(rel) != actual:
            raise ValueError(f"source hash drift: {rel}")
    if dry_run: return
    for rel in files:
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, target)


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe, hash-checked offline overlay deployment")
    parser.add_argument("--source", required=True); parser.add_argument("--destination", required=True)
    parser.add_argument("--files", nargs="+", required=True); parser.add_argument("--hashes", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    deploy(args.source, args.destination, args.files, json.loads(Path(args.hashes).read_text()), dry_run=not args.apply)

if __name__ == "__main__": main()
