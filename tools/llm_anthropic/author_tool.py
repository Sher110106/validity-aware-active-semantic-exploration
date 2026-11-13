"""The author's `check_collision` tool, as the Claude API sees it, and the callback that answers it.

Everything here comes from the author's file `llm_completion.py` (pinned reference):
- the tool name, the argument names and their order: `generate_completion_response`, the nested
  `check_collision` function and its `required_args` list;
- the description: that function's docstring;
- the answer: the author's own `validate_feasibility`.

`llm_completion.py` does not import on a laptop: it needs google.genai, spark_dsg, bidict and
scene_graph_visualize_2d at module level (see `author_import_report`). `validate_feasibility` itself
needs only numpy and json. We do not copy it. `load_author_feasibility` parses the author's file with
`ast`, takes that one function's source as written, and compiles it in a namespace that holds only
numpy and json. The sha256 of that source goes into every record.
"""
from __future__ import annotations

import ast
import builtins
import hashlib
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import yaml

TOOL_NAME = "check_collision"
# Author's `required_args`, in his order. First is the label; the other six are numbers.
ARG_NAMES = ("label", "center_x", "center_y", "center_z", "size_x", "size_y", "size_z")
NUMERIC_ARGS = ARG_NAMES[1:]
# Docstring of the author's nested check_collision (the genai SDK turns it into the tool description).
CHECK_COLLISION_DESCRIPTION = "Checks collision for a box centered at (center_x, center_y, center_z)."

# strict: true -> the arguments always match the schema (needs additionalProperties false + all required).
TOOL_DEF = {
    "name": TOOL_NAME,
    "description": CHECK_COLLISION_DESCRIPTION,
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {"label": {"type": "string"}, **{n: {"type": "number"} for n in NUMERIC_ARGS}},
        "required": list(ARG_NAMES),
        "additionalProperties": False,
    },
}

DEFAULT_AUTHOR_SOURCE = (
    Path(__file__).resolve().parents[1] / "prospective_integration" / "overlay" / "pinned_reference" / "llm_completion.py"
)


@dataclass
class AuthorFeasibility:
    fn: Callable
    sha256: str  # of the function's source text, as written by the author
    source_path: str


def _parse(path: Path) -> tuple[str, ast.Module]:
    source = Path(path).read_text()
    return source, ast.parse(source, filename=str(path))


def _free_names(fn: ast.FunctionDef) -> set[str]:
    params: set[str] = set()  # every argument name in the function, lambdas included
    loads, stores = set(), set()
    for n in ast.walk(fn):
        if isinstance(n, ast.arg):
            params.add(n.arg)
        elif isinstance(n, ast.Name):
            (loads if isinstance(n.ctx, ast.Load) else stores).add(n.id)
    return loads - stores - params - set(dir(builtins))


def load_author_feasibility(path: Optional[Path] = None) -> AuthorFeasibility:
    """The author's validate_feasibility, taken verbatim from his file. Needs only numpy and json."""
    path = Path(path) if path else DEFAULT_AUTHOR_SOURCE
    source, tree = _parse(path)
    node = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_feasibility"), None)
    if node is None:
        raise ImportError(f"validate_feasibility not found in {path}")
    free = _free_names(node)
    allowed = {"np", "json"}
    if not free <= allowed:
        raise ImportError(f"validate_feasibility in {path} needs names we do not supply: {sorted(free - allowed)}")
    text = ast.get_source_segment(source, node)
    ns: dict = {"np": np, "json": json}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), ns)
    return AuthorFeasibility(ns["validate_feasibility"], hashlib.sha256(text.encode()).hexdigest(), str(path))


def author_tool_signature(path: Optional[Path] = None) -> dict:
    """Read the tool contract from the author's file: argument names, docstring, required_args list."""
    path = Path(path) if path else DEFAULT_AUTHOR_SOURCE
    _, tree = _parse(path)
    gen = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "generate_completion_response")
    inner = next(n for n in ast.walk(gen) if isinstance(n, ast.FunctionDef) and n.name == "check_collision")
    required = None
    for n in ast.walk(gen):
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "required_args" for t in n.targets):
            required = [e.value for e in n.value.elts]
    return {
        "args": [a.arg for a in inner.args.args],
        "annotations": {a.arg: ast.unparse(a.annotation) for a in inner.args.args},
        "doc": ast.get_docstring(inner, clean=True),
        "required_args": required,
    }


def author_import_report(path: Optional[Path] = None) -> dict:
    """Which top-level imports of the author's file resolve in this interpreter."""
    path = Path(path) if path else DEFAULT_AUTHOR_SOURCE
    _, tree = _parse(path)
    mods = []
    for n in tree.body:
        if isinstance(n, ast.Import):
            mods += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.module:
            mods.append(n.module)
    report = {}
    for m in dict.fromkeys(mods):
        try:
            report[m] = importlib.util.find_spec(m) is not None
        except (ImportError, ValueError):
            report[m] = False
    return report


def make_author_callback(yaml_text: str, validate: Callable) -> Callable[[str, dict], dict]:
    """Callback `(tool_name, args) -> dict`. Same dispatch as the author's loop body.

    - an unknown tool name gives {"error": "Unknown function <name>"};
    - missing arguments give {"error": "check_collision missing argument(s): ..."};
    - otherwise `validate(label, [cx, cy, cz, sx, sy, sz], existing_nodes)`.
    The arguments go to his function as the model sent them. We do not turn integers into floats.
    """
    existing_nodes = yaml.safe_load(yaml_text).get("nodes", [])

    def callback(name: str, args: dict) -> dict:
        if name in [TOOL_NAME]:
            missing = [n for n in ARG_NAMES if n not in args]
            if missing:
                return {"error": "check_collision missing argument(s): " + ", ".join(missing)}
            return validate(args["label"], [args[n] for n in NUMERIC_ARGS], existing_nodes)
        return {"error": f"Unknown function {name}"}

    return callback


def default_callback_factory(author_source: Optional[Path] = None) -> tuple[Callable[[str], Callable], AuthorFeasibility]:
    """(factory(yaml_text) -> callback, the loaded author function)."""
    feas = load_author_feasibility(author_source)
    return (lambda yaml_text: make_author_callback(yaml_text, feas.fn)), feas
