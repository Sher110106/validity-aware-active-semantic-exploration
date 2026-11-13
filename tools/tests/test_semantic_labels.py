"""Tests for tools/live_policy/semantic/labels.py (the frozen normaliser, room types, markers).

Strings only; no model output is compared with truth. The module loads by file path because
tools/live_policy also holds a live_policy.py module, and other tests import that under the
same name.
"""
import hashlib
import importlib.util
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(__file__)
SEM = os.path.join(HERE, "..", "live_policy", "semantic")
LABELS = os.path.join(SEM, "labels.py")
_spec = importlib.util.spec_from_file_location("semantic_labels_under_test", LABELS)
lb = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = lb  # dataclasses look the module up by name
_spec.loader.exec_module(lb)

TABLE_PATH = os.path.join(SEM, "canon_labels.json")
with open(TABLE_PATH, encoding="utf-8") as _f:
    TABLE = json.load(_f)
with open(os.path.join(SEM, "truth", "label_mapping.json"), encoding="utf-8") as _f:
    VOCAB = json.load(_f)["vocab"]

STRUCTURE = ["wall", "floor", "ceiling", "door", "door frame", "window", "window frame", "stairs", "unknown"]


def steps_1_to_4(s):
    """Independent copy of steps 1-4 of the spec."""
    s = s.lower()
    s = re.sub(r"[_\-/]", " ", s)
    s = re.sub(r"[0-9]", "", s)
    return " ".join(s.split())


# ---- marker rule (§5.2) -----------------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("oven and stove", {"kitchen"}),
    ("shower floor", {"bathroom"}),
    ("bedside lamp", set()),
    ("bed stand", {"bedroom"}),
    ("washer-dryer", {"laundry"}),
    ("washer dryer", {"laundry"}),
    ("dining table", {"dining"}),
    ("Dining_Table", {"dining"}),
    ("washing machine", {"laundry"}),
    ("washing machine and dryer", {"laundry"}),
    ("toilet", {"bathroom"}),
    ("Toilet_Paper", {"bathroom"}),
    ("bathtub", {"bathroom"}),
    ("bath tub", {"bathroom"}),
    ("Bath_Tub", {"bathroom"}),
    ("bath", set()),
    ("tub", set()),
    ("laundry machine", {"laundry"}),
    ("laundry_machine", {"laundry"}),
    ("laundry", set()),
    ("dryer", {"laundry"}),
    ("washer", {"laundry"}),
    ("showerhead", set()),
    ("shower/tub", {"bathroom"}),
    ("stovetop", {"kitchen"}),
    ("couch", {"living"}),
    ("sofa chair", {"living"}),
    ("L-shaped sofa", {"living"}),
    ("Closet", set()),
    ("table", set()),
    ("dining", set()),
    ("washing", set()),
    ("bedroom", set()),            # a whole word "bed" is needed; "bedroom" is another word
    ("", set()),
])
def test_marker_types(name, expected):
    assert lb.marker_types(name) == frozenset(expected)


def test_marker_types_gives_every_type_a_name_has():
    assert lb.marker_types("bed and sofa") == frozenset({"bedroom", "living"})
    assert lb.marker_types("toilet bed") == frozenset({"bathroom", "bedroom"})


def test_marker_words_must_come_in_order():
    assert lb.marker_types("table dining") == frozenset()
    assert lb.marker_types("machine washing") == frozenset()


@pytest.mark.parametrize("name", [
    "hair dryer", "hand dryer", "dish dryer", "dog bed", "cat bed", "pet bed", "massage bed",
    "toaster oven", "sauna oven",
    "Hair_Dryer", "hand-dryer", "Dog_Bed", "toaster/oven", "dog bed cushion", "small toaster oven",
])
def test_marker_exclusions_mark_nothing(name):
    assert lb.marker_types(name) == frozenset()


def test_an_exclusion_silences_the_whole_name():
    assert lb.marker_types("hair dryer and toilet") == frozenset()
    assert lb.marker_types("dog bed and sofa") == frozenset()


def test_exclusion_words_must_come_in_order_and_be_whole():
    assert lb.marker_types("dryer hair") == frozenset({"laundry"})
    assert lb.marker_types("bed dog") == frozenset({"bedroom"})
    assert lb.marker_types("hair and dryer") == frozenset({"laundry"})
    assert lb.marker_types("hairdryer") == frozenset()          # one word: no "dryer" word, no exclusion
    assert lb.marker_types("oven") == frozenset({"kitchen"})
    assert lb.marker_types("toaster") == frozenset()
    assert lb.marker_types("dog") == frozenset()
    assert lb.marker_types("bed") == frozenset({"bedroom"})


def test_marker_types_returns_frozenset():
    assert isinstance(lb.marker_types("bed"), frozenset)


# ---- room type rule (§6) ----------------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("an image of a living room", "living"),
    ("an image of a bathroom", "bathroom"),
    ("an image of a bedroom", "bedroom"),
    ("an image of a kitchen", "kitchen"),
    ("an image of a laundry room", "laundry"),
    ("an image of a dining room", "dining"),
    ("an image of a second bedroom", "bedroom"),
    ("an image of a hallway", None),
    ("an image of a closet", None),
    ("an image of a walk-in closet", None),
    ("an image of a study", None),
    ("an image of a storage room", None),
    ("Closet", None),
    ("", None),
    ("Bedroom_2", "bedroom"),
    ("an image of a Bathroom_1", "bathroom"),
    ("toilet", "bathroom"),
    ("restroom", "bathroom"),
    ("washroom", "bathroom"),
    ("shower room", "bathroom"),
    ("wc", "bathroom"),
    ("utility room", "laundry"),
    ("family room", "living"),
    ("lounge", "living"),
    ("sitting area", "living"),
])
def test_room_type(name, expected):
    assert lb.room_type(name) == expected


@pytest.mark.parametrize("name,expected", [
    ("master bedroom bathroom", "bathroom"),     # rule 1 before rule 2
    ("bedroom with toilet", "bathroom"),
    ("bedroom kitchen", "bedroom"),              # rule 2 before rule 3
    ("kitchen laundry", "kitchen"),              # rule 3 before rule 4
    ("laundry living room", "laundry"),          # rule 4 before rule 5
    ("living dining room", "living"),            # rule 5 before rule 6
    ("kitchen dining room", "kitchen"),
    ("utility bedroom", "bedroom"),
])
def test_room_type_precedence(name, expected):
    assert lb.room_type(name) == expected


def test_room_type_wc_is_a_whole_word():
    assert lb.room_type("wc") == "bathroom"
    assert lb.room_type("an image of a wc") == "bathroom"
    assert lb.room_type("twcx") is None
    assert lb.room_type("hallway wcs") is None


def test_room_type_uses_only_steps_1_to_4_not_the_table():
    # "couch" is a canonical class, but a room named after it has no type.
    assert lb.room_type("couch room") is None
    # no plural stripping or head noun either
    assert lb.room_type("beds") == "bedroom"   # "bed" is contained
    assert lb.room_type("hall") is None


# ---- normaliser (§6) --------------------------------------------------------------------

def test_dining_chair_with_digits_and_underscores_is_dining_chair():
    got = lb.normalise("Dining_Chair2")
    assert got == lb.normalise("dining chair")
    assert got is not None
    assert lb.normalise("dining-chair 12") == got
    assert lb.normalise("  DINING   CHAIR  ") == got


@pytest.mark.parametrize("label,expected", [
    ("chairs", "chair"),
    ("Chairs", "chair"),
    ("boxes", "box"),
    ("benches", "bench"),
    ("tables", "table"),
    ("vases", "vase"),
    ("dishes", "dish"),
    ("blinds", "blind"),
    ("plates", "plate"),
    ("glass", "glass"),
    ("glasses", "glass"),
    ("shelves", "shelf"),
    ("bookshelves", "bookshelf"),
    ("wardrobes", "wardrobe"),
])
def test_plurals(label, expected):
    assert lb.normalise(label) == expected


def test_ss_is_kept():
    assert lb.normalise("glass") == "glass"


def test_plural_in_phrase_is_stripped_on_the_last_word():
    assert lb.normalise("wooden chairs") == "chair"
    assert lb.normalise("wall shelves") == "shelf"      # irregular plural reached through the table
    assert lb.normalise("coffee tables") == "coffee table"


@pytest.mark.parametrize("label,expected", [
    ("couch", "sofa"),
    ("tv", "television"),
    ("TV", "television"),
    ("refrigerator", "fridge"),
    ("trash can", "waste bin"),
    ("trash_can", "waste bin"),
    ("trashcan", "waste bin"),
    ("waste bin", "waste bin"),
    ("tap", "faucet"),
    ("night stand", "nightstand"),
    ("bed stand", "nightstand"),
    ("bedside table", "nightstand"),
    ("washer", "washing machine"),
    ("range hood", "exhaust hood"),
    ("Bed", "bed"),
    ("closet", "closet"),
])
def test_synonyms(label, expected):
    assert lb.normalise(label) == expected


@pytest.mark.parametrize("label", [
    "shower wall", "shower floor", "bath wall", "kitchen wall", "fireplace wall",
    "attic door", "sliding glass door", "closet door", "garage door",
    "support beam", "beam", "column", "pillar", "staircase", "stair", "stairs", "doorframe",
    "door frame", "Door_Frame", "window frame", "windows", "ceiling", "floor", "wall", "Wall",
    "unknown", "unknown/remove", "shower door frame", "door/window frame",
    "curtain rod", "mirror frame", "parapet", "curtain rail",
])
def test_structure_names_map_to_structure(label):
    got = lb.normalise(label)
    assert got is not None, label
    assert lb.is_structure(got), (label, got)
    assert got in STRUCTURE


def test_every_listed_structure_string_maps_to_one_of_the_nine():
    with open(os.path.join(SEM, "truth", "label_mapping.json"), encoding="utf-8") as f:
        tables = json.load(f)["tables"]
    listed = tables["structural_never_mapped"] + tables["door_excluded"]
    assert len(listed) == 29
    for raw in listed:
        got = lb.normalise(raw)
        assert got in STRUCTURE, (raw, got)
        assert lb.is_structure(got)
        assert lb.answers_to(raw) == frozenset(), raw


@pytest.mark.parametrize("raw,expected", [
    ("shower wall", "wall"), ("shower floor", "floor"), ("shower door", "door"),
    ("sliding glass door", "door"), ("sliding door", "door"), ("closet door", "door"),
    ("support beam", "ceiling"), ("parapet", "wall"), ("curtain rod", "unknown"),
    ("mirror frame", "unknown"), ("bath wall", "wall"), ("kitchen wall", "wall"),
    ("recessed wall", "wall"), ("ceiling dome", "ceiling"), ("ceiling fixture", "ceiling"),
    ("shower ceiling", "ceiling"), ("shower glass", "wall"), ("shower wall cubby", "wall"),
    ("shower door frame", "door frame"), ("door/window", "window"), ("door/window frame", "window frame"),
    ("unknown/remove", "unknown"), ("window frame", "window frame"), ("door frame", "door frame"),
])
def test_listed_structure_strings_go_to_the_fitting_class(raw, expected):
    assert lb.normalise(raw) == expected


def test_window_is_structure_not_a_detector_or_canonical_class():
    assert lb.is_structure("window")
    assert lb.normalise("window") == "window"
    assert "window" not in lb.detector_vocab()
    assert "window" not in lb.canonical_classes()
    assert "window" in TABLE["classes"] and "window" in TABLE["structure"]
    assert "window" not in TABLE["detector_vocab"]


def test_shower_wall_is_wall_not_shower():
    assert lb.normalise("shower wall") == "wall"
    assert lb.normalise("shower floor") == "floor"
    assert lb.normalise("shower") == "shower"
    assert not lb.is_structure("shower")


def test_structure_classes_are_exactly_the_nine_of_the_spec():
    assert sorted(TABLE["structure"]) == sorted(STRUCTURE)
    for s in STRUCTURE:
        assert lb.is_structure(s)
        assert s in TABLE["classes"]
        assert lb.normalise(s) == s
        assert s not in lb.canonical_classes()


def test_is_structure_false_for_object_classes_and_unknown_strings():
    for c in ("chair", "bed", "sofa", "toilet", "waste bin"):
        assert not lb.is_structure(c)
    assert not lb.is_structure("banana")


def test_whole_string_beats_head_noun():
    # "kitchen cabinet" is a class of its own; the head noun would give "cabinet".
    assert lb.normalise("kitchen cabinet") == "kitchen cabinet"
    assert lb.normalise("bedside lamp") == "bedside lamp"
    assert lb.normalise("coffee table") == "coffee table"
    # a synonym entry for the whole string beats the head noun "oven" and "stand"
    assert lb.normalise("microwave oven") == "microwave"
    assert lb.normalise("television stand") == "tv stand"


def test_head_noun_is_used_when_no_whole_string_entry_exists():
    assert lb.normalise("wooden chair") == "chair"
    assert lb.normalise("big red sofa") == "sofa"
    assert lb.normalise("grey fabric armchair") == "armchair"
    assert lb.normalise("wall tv") == "television"      # head noun "tv", then the table maps it


def test_plural_step_comes_before_head_noun():
    # "kitchen cabinets" -> step 6 gives "kitchen cabinet", a class; the head noun would give "cabinet"
    assert lb.normalise("kitchen cabinets") == "kitchen cabinet"


def test_other_is_none():
    for s in ("banana", "", "   ", "1234", "___", "zzzz qqqq", "an image of a bedroom"):
        assert lb.normalise(s) is None, s


def test_normalise_survives_odd_input():
    assert lb.normalise(None) is None
    assert lb.normalise("\t\n") is None


def test_case_and_separators_do_not_matter():
    base = lb.normalise("floor lamp")
    assert base == "floor lamp"
    for s in ("Floor_Lamp", "FLOOR-LAMP", "floor/lamp", "floor  lamp", "Floor_Lamp12", "1floor lamp2"):
        assert lb.normalise(s) == base, s


# ---- the table --------------------------------------------------------------------------

def test_every_detector_word_normalises_into_detector_vocab():
    dv = lb.detector_vocab()
    assert len(VOCAB) == 52
    for w in VOCAB:
        c = lb.normalise(w)
        assert c is not None, w
        if w == "window":
            assert lb.is_structure(c)          # structure here, so not in the detector vocabulary
        else:
            assert c in dv, (w, c)


def test_detector_vocab_has_one_class_per_word_except_window():
    dv = lb.detector_vocab()
    assert len(dv) == 51
    assert len({lb.normalise(w) for w in VOCAB}) == 52     # 52 distinct classes, 51 of them non-structure
    assert set(TABLE["detector_vocab"]) == set(dv)
    assert dv <= set(TABLE["classes"])


def test_detector_vocab_plural_words_are_singular_classes():
    assert {"plate", "dish", "blind"} <= lb.detector_vocab()


def test_canonical_classes_exclude_structure_and_are_in_the_table():
    cc = lb.canonical_classes()
    assert not (cc & set(STRUCTURE))
    assert cc | set(STRUCTURE) == set(TABLE["classes"])
    assert isinstance(cc, frozenset)
    assert isinstance(lb.detector_vocab(), frozenset)


def test_keys_of_synonyms_are_normalised():
    for k in TABLE["synonyms"]:
        assert k == steps_1_to_4(k), k
        assert k, "empty key"


def test_classes_are_normalised_and_unique():
    cl = TABLE["classes"]
    assert len(cl) == len(set(cl))
    for c in cl:
        assert c == steps_1_to_4(c), c


def test_dryer_alone_is_not_merged_but_tumble_dryer_is():
    assert lb.normalise("hair dryer") is None
    assert lb.normalise("dryer") is None
    assert lb.normalise("tumble dryer") == "clothes dryer"
    assert lb.normalise("dish washer") == "dishwasher"
    assert lb.normalise("washer") == "washing machine"


def test_synonym_values_are_classes_and_keys_are_not_identity():
    classes = set(TABLE["classes"])
    for k, v in TABLE["synonyms"].items():
        assert v in classes, (k, v)
        assert k != v, k


def test_a_synonym_key_never_disagrees_with_a_class_of_the_same_name():
    classes = set(TABLE["classes"])
    for k in TABLE["synonyms"]:
        assert k not in classes, f"{k} is both a class and a synonym key"


def test_table_is_idempotent_on_every_class_and_every_key():
    for c in TABLE["classes"]:
        assert lb.normalise(c) == c, c
    for k, v in TABLE["synonyms"].items():
        got = lb.normalise(k)
        assert got == v, (k, v, got)
        assert lb.normalise(got) == got


@pytest.mark.parametrize("s", [
    "chairs", "Dining_Chair2", "shower wall", "wooden chairs", "wall shelves", "banana", "",
    "kitchen cabinets", "TV", "an image of a bedroom", "big red sofa",
])
def test_idempotent_on_assorted_strings(s):
    once = lb.normalise(s)
    if once is None:
        return
    assert lb.normalise(once) == once


def test_built_from_matches_the_truth_files_on_disk():
    bf = TABLE["built_from"]
    for key in ("hm3d_semantic_summary", "label_mapping"):
        entry = bf[key]
        path = os.path.join(SEM, "truth", os.path.basename(entry["path"]))
        with open(path, "rb") as f:
            assert hashlib.sha256(f.read()).hexdigest() == entry["sha256"], key


def test_table_sha256_is_the_file_hash():
    with open(TABLE_PATH, "rb") as f:
        assert lb.table_sha256() == hashlib.sha256(f.read()).hexdigest()


def test_common_hm3d_names_are_classes_of_their_own():
    """Rule 2: names held by at least 20 houses stay classes unless a merge applies."""
    for name in ("chair", "table", "cabinet", "toilet", "bed", "sink", "shelf", "pillow", "lamp",
                 "box", "towel", "book", "curtain", "desk", "microwave", "armchair", "basket",
                 "kitchen cabinet", "bathroom cabinet", "ceiling lamp", "wall lamp", "floor lamp",
                 "table lamp", "bedside lamp", "coffee table", "dining table", "dining chair"):
        assert name in lb.canonical_classes(), name


# ---- answers_to (§5.3) ------------------------------------------------------------------

def test_answers_to_names_the_detector_class_too():
    assert lb.answers_to("bed") == frozenset({"bed", "duvet"})
    assert lb.answers_to("Bed") == frozenset({"bed", "duvet"})
    assert lb.answers_to("armchair") == frozenset({"armchair", "chair"})
    assert lb.answers_to("vase") == frozenset({"vase", "flower"})
    assert "flower" in lb.answers_to("flower vase")
    assert lb.answers_to("tv") == frozenset({"television"})
    assert lb.answers_to("washer-dryer") == frozenset({"washing machine"})
    assert lb.answers_to("kitchen cabinet") == frozenset({"kitchen cabinet", "cabinet"})
    assert lb.answers_to("stovetop") == frozenset({"gas stove"})      # no class of its own
    assert lb.answers_to("L-shaped sofa") == frozenset({"sofa"})


def test_answers_to_a_plain_name_with_no_detector_label_is_its_own_class():
    assert lb.answers_to("wardrobe") == frozenset({"wardrobe"})
    assert lb.answers_to("pillow") == frozenset({"pillow"})
    assert lb.answers_to("toilet") == frozenset({"toilet"})
    assert lb.answers_to("nightstand") == frozenset({"nightstand"})


def test_answers_to_is_empty_for_structure_and_for_unknown_words():
    for raw in ("shower wall", "wall", "floor", "door", "window", "window frame", "ceiling",
                "support beam", "curtain rod", "unknown", "banana", ""):
        assert lb.answers_to(raw) == frozenset(), raw


def test_answers_to_gives_only_non_structure_classes_and_a_frozenset():
    labels = list(TABLE["detector_label"]) + list(TABLE["classes"]) + list(TABLE["synonyms"])
    for raw in labels:
        got = lb.answers_to(raw)
        assert isinstance(got, frozenset)
        assert got <= lb.canonical_classes(), (raw, got)


def test_answers_to_reads_the_two_tables_of_label_mapping():
    with open(os.path.join(SEM, "truth", "label_mapping.json"), encoding="utf-8") as f:
        tables = json.load(f)["tables"]
    expected = {}
    for name in ("synonym_primary", "extended_sensitivity_only"):
        expected.update(tables[name])
    assert TABLE["detector_label"] == expected
    for raw, word in expected.items():
        assert lb.normalise(word) in lb.answers_to(raw), (raw, word)
    assert TABLE["built_from"]["detector_label"]["sha256"] == TABLE["built_from"]["label_mapping"]["sha256"]


def test_detector_label_values_are_detector_words():
    for raw, word in TABLE["detector_label"].items():
        assert word in VOCAB, (raw, word)
        assert raw == raw.lower()
