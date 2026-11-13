"""Label layer of the semantic test (PREREGISTRATION_SEMANTIC.md, §5.2 and §6).

One frozen normaliser, the synonym table `canon_labels.json`, the room-type rule and the
marker rule. Standard library only. Everything here works on strings.

The normaliser (§6), in order:
  1 lower case; 2 "_", "-", "/" become spaces; 3 digits go; 4 spaces collapse;
  5 the whole string is looked up in the table;
  6 failing that, a plural ending is stripped from the last word and the string is looked up again;
  7 failing that, the last word alone is looked up;
  8 failing that, the label is "other" (None).

Two readings, both noted in LABELS_NOTES.md:
  * The table that steps 5-7 look up is every class (it maps to itself) plus every key of
    `synonyms`.
  * Step 7 tries the last word as stripped in step 6 and then as written, so that an irregular
    plural that the table lists ("shelves") still works at the end of a phrase ("wall shelves").
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
import re
from typing import Dict, FrozenSet, Optional, Tuple

_DIR = os.path.dirname(os.path.abspath(__file__))
TABLE_PATH = os.path.join(_DIR, "canon_labels.json")

# ------------------------------------------------------------------------------ the table

with open(TABLE_PATH, "rb") as _f:
    _TABLE_BYTES = _f.read()
_TABLE_SHA256 = hashlib.sha256(_TABLE_BYTES).hexdigest()
_TABLE = json.loads(_TABLE_BYTES.decode("utf-8"))

_CLASSES: FrozenSet[str] = frozenset(_TABLE["classes"])
_STRUCTURE: FrozenSet[str] = frozenset(_TABLE["structure"])
_DETECTOR: FrozenSet[str] = frozenset(_TABLE["detector_vocab"])
_CANONICAL: FrozenSet[str] = _CLASSES - _STRUCTURE

_LOOKUP: Dict[str, str] = {c: c for c in _CLASSES}
_LOOKUP.update(_TABLE["synonyms"])
_DETECTOR_LABEL: Dict[str, str] = dict(_TABLE["detector_label"])   # raw name (lower case) -> detector word


def table_sha256() -> str:
    """sha256 of canon_labels.json, as it was read when this module loaded."""
    return _TABLE_SHA256


def is_structure(canon: str) -> bool:
    return canon in _STRUCTURE


def detector_vocab() -> FrozenSet[str]:
    """The canonical classes that stand for the detector words: 51 classes, for 52 words. "Window"
    is a detector word but is structure here (§6, rule 4), so it is not in this set."""
    return _DETECTOR


def canonical_classes() -> FrozenSet[str]:
    """All canonical classes that are not structure classes."""
    return _CANONICAL


# ------------------------------------------------------------------------------ normaliser

_SEP = re.compile(r"[_\-/]")
_DIGITS = re.compile(r"[0-9]")


def _steps_1_to_4(label: str) -> str:
    s = label.lower()
    s = _SEP.sub(" ", s)
    s = _DIGITS.sub("", s)
    return " ".join(s.split())


def _strip_plural(word: str) -> str:
    """Step 6: "ies" to "y"; "es" after s, x, z, ch or sh; else a final "s" that is not "ss"."""
    if word.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"
    if word.endswith("es") and word[:-2].endswith(("s", "x", "z", "ch", "sh")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 1:
        return word[:-1]
    return word


@functools.lru_cache(maxsize=65536)
def normalise(label: str) -> Optional[str]:
    """The eight steps of §6. Returns a canonical class (structure classes included), or None
    for "other"."""
    if not isinstance(label, str):
        return None
    s = _steps_1_to_4(label)
    if not s:
        return None
    hit = _LOOKUP.get(s)                                   # step 5
    if hit is not None:
        return hit
    words = s.split(" ")
    last = words[-1]
    stripped = _strip_plural(last)
    if stripped != last:                                   # step 6
        hit = _LOOKUP.get(" ".join(words[:-1] + [stripped]))
        if hit is not None:
            return hit
    for w in ((stripped, last) if stripped != last else (last,)):   # step 7
        hit = _LOOKUP.get(w)
        if hit is not None:
            return hit
    return None                                            # step 8


# ------------------------------------------------------------------------------ room type

def room_type(name: str) -> Optional[str]:
    """§6: the type of a predicted or observed room, from its name after steps 1-4, by the first
    rule that matches. One of bathroom, bedroom, kitchen, laundry, living, dining, or None."""
    if not isinstance(name, str):
        return None
    s = _steps_1_to_4(name)
    if not s:
        return None
    if any(k in s for k in ("bath", "toilet", "restroom", "washroom", "shower")) or "wc" in s.split(" "):
        return "bathroom"
    if "bed" in s:
        return "bedroom"
    if "kitchen" in s:
        return "kitchen"
    if "laundry" in s or "utility" in s:
        return "laundry"
    if any(k in s for k in ("living", "lounge", "family", "sitting")):
        return "living"
    if "dining" in s:
        return "dining"
    return None


# ------------------------------------------------------------------------------ markers (§5.2)

_MARKERS: Tuple[Tuple[str, Tuple[Tuple[str, ...], ...]], ...] = (
    ("bathroom", (("toilet",), ("bathtub",), ("bath", "tub"), ("shower",))),
    ("bedroom", (("bed",),)),
    ("kitchen", (("oven",), ("stove",), ("stovetop",))),
    ("laundry", (("washing", "machine"), ("laundry", "machine"), ("washer",), ("dryer",))),
    ("living", (("couch",), ("sofa",))),
    ("dining", (("dining", "table"),)),
)

# A name that holds one of these marks nothing, whatever else it holds (§5.2).
_EXCLUSIONS: Tuple[Tuple[str, ...], ...] = (
    ("hair", "dryer"), ("hand", "dryer"), ("dish", "dryer"),
    ("dog", "bed"), ("cat", "bed"), ("pet", "bed"), ("massage", "bed"),
    ("toaster", "oven"), ("sauna", "oven"),
)


def _holds(words, phrase: Tuple[str, ...]) -> bool:
    n = len(phrase)
    return any(tuple(words[i:i + n]) == phrase for i in range(len(words) - n + 1))


def marker_types(raw_name: str) -> FrozenSet[str]:
    """§5.2: the room types a raw HM3D object name marks. A marker matches when its words appear
    in the name as whole words, in order and next to each other, after lower-casing and turning
    "_", "-" and "/" into spaces. Digits are kept. A name that holds an exclusion phrase (hair
    dryer, dog bed, toaster oven, ...) marks nothing."""
    if not isinstance(raw_name, str):
        return frozenset()
    words = _SEP.sub(" ", raw_name.lower()).split()
    if any(_holds(words, e) for e in _EXCLUSIONS):
        return frozenset()
    return frozenset(rtype for rtype, markers in _MARKERS if any(_holds(words, m) for m in markers))


# ------------------------------------------------------------------------------ answers_to (§5.3)

def answers_to(raw_name: str) -> FrozenSet[str]:
    """§5.3: the non-structure canonical classes an annotated object answers to. These are
    normalise(raw_name), and normalise of the detector's label for the lower-cased raw name
    (`detector_label` in the table: label_mapping.json's synonym_primary and
    extended_sensitivity_only), each kept only if it is not a structure class."""
    if not isinstance(raw_name, str):
        return frozenset()
    out = set()
    own = normalise(raw_name)
    if own is not None and own not in _STRUCTURE:
        out.add(own)
    label = _DETECTOR_LABEL.get(raw_name.lower())
    if label is not None:
        c = normalise(label)
        if c is not None and c not in _STRUCTURE:
            out.add(c)
    return frozenset(out)
