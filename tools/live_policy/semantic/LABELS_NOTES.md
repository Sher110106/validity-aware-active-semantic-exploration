# Label layer: how `canon_labels.json` was built

Spec: `PREREGISTRATION_SEMANTIC.md` §5.2, §5.3 and §6. Code: `labels.py`. Tests: `tools/tests/test_semantic_labels.py`.
The table was built from strings only. No score of a guess against truth was computed, and no mapping was chosen by what it would do to a result. The build script ran outside the repo; the table is the product, and `built_from` holds the hashes of its inputs.

## Inputs

- `truth/hm3d_semantic_summary.json`: every category name in every region of the 185 annotated houses. Four houses sit in two splits, so there are 181 by number; each counts once. 1,542 names.
- `truth/label_mapping.json`: the 52 detector words, `synonym_primary`, `extended_sensitivity_only`, `structural_never_mapped`, `door_excluded`, and the raw names of the two test scenes.
- Saved outputs, strings and counts only: 3,916 stage graphs and 791 raw completions (`habitat_scene_graph_new_graph_*.yaml`, DeepSeek, placebo and the oracle runs), 29 Gemini graphs, 525 observed graphs. I used the object nodes whose id is not in the same stage's observed graph. The oracle runs hold HM3D labels, not a model's, so they are left out of the model counts.

## Size

- 244 classes: 9 structure classes and 235 others.
- 51 detector classes for the 52 words. "Window" is a detector word and is structure, so it is not in `detector_vocab`.
- 71 synonym entries: 33 merges, 30 structure entries, 8 plural entries.
- 67 `detector_label` entries (42 from `synonym_primary`, 25 from `extended_sensitivity_only`). No label in either table is a structure class.

## Building rules (§6) and what they gave

1. The 52 detector words are classes. After steps 1-4 and plural stripping, "plates" is `plate`, "dishes" is `dish`, "blinds" is `blind`. No two detector words are plain synonyms, so none is merged. Close pairs stay apart: `plate` and `dish`, `table` and `glass table`, `towel` and `towel bar`, `shower` and `bathtub`.
2. 250 names are held by at least 20 houses. 215 are classes of their own, 12 are merged (below), 23 are structure. 20 more classes come from the detector words alone: bicycle, blind, computer, dish, document, drain, duvet, exhaust hood, garment, gas stove, glass table, piano, picture frame, printing, shampoo, shower, television, tree, umbrella, waste bin.
3. A merge needs a spelling variant, a plural or a plain synonym. When in doubt I did not merge. A part is never merged into a whole.
4. Structure: see below.

## Merges, with the reason

| string | class | reason |
|---|---|---|
| couch | sofa | same seat, two common words |
| tv | television | short form |
| refrigerator | fridge | full and short form |
| trashcan, trash can, trash bin, dustbin | waste bin | same container; the first is also a spelling variant |
| tap | faucet | British and American word |
| night stand, bed stand, bedside table | nightstand | same table beside a bed |
| range hood, ventilation hood | exhaust hood | same hood over a stove |
| air vent | vent | an air vent is a vent |
| flower pot | flowerpot | spelling |
| book shelf, bookcase | bookshelf | spelling; same furniture |
| stuffed animal, stuffed toy, soft toy, cuddly toy | plush toy | same toy |
| washer | washing machine | same machine; "dish washer" goes to `dishwasher` so the head noun cannot misfire |
| laundry machine | washing machine | same machine |
| tumble dryer | clothes dryer | same machine |
| worktop | countertop | British word |
| coffee maker | coffee machine | same appliance |
| smoke alarm | smoke detector | same device |
| television stand | tv stand | same stand |
| microwave oven | microwave | same appliance; the head noun would say `oven` |
| door mat | doormat | spelling |
| pouf | pouffe | spelling |
| bath tub | bathtub | spelling |
| cosmetics | cosmetic | plural (both names exist) |
| blinds | blind | plural |

Eight plural entries cover words whose plural the stripping rule cannot undo: shelves, bookshelves, vases, cases, flower vases, bathroom shelves, shower soap shelves, computer mouses. Without them "vases" would become "vas".

Two strings are missing from the list on purpose. `dryer` alone is not merged: "hair dryer" would then become a clothes dryer through the head noun. `bath` alone is not merged: it may mean the room.

## Structure

Every string of `structural_never_mapped` and `door_excluded` has its own entry, mapped to the nearest of the nine. The head-noun step would give most of them the same result; the entries make it certain.

- wall: bath wall, kitchen wall, recessed wall, shower wall, shower wall cubby, parapet (a low wall), shower glass (a glass screen that acts as a wall)
- floor: shower floor
- ceiling: ceiling dome, ceiling fixture, shower ceiling, support beam
- door: shower door, closet door, sliding door, sliding glass door
- door frame: shower door frame
- window: door/window (last word, as the rule of the brief)
- window frame: door/window frame (same reason)
- unknown: unknown/remove, curtain rod, mirror frame

I found no good fit for "curtain rod" and "mirror frame", so they go to `unknown`. "Curtain rail" and "curtain bar" (plain synonyms of "curtain rod") go there too. This takes "curtain rod" (65 houses), "mirror frame" (29) and "parapet" (28) out of the object classes.

Beyond the two lists I also treat as structure any name whose last word is wall, floor, ceiling, door, window, stairs, staircase, doorframe, beam, column or pillar. This comes from the first brief; §6 rule 4 does not state it. It matters for attic door, fireplace wall, beam, pillar, stair and staircase. Beam goes to ceiling, column and pillar to wall, stair and staircase to stairs.

## Readings of §6 that I chose

- The table that steps 5-7 search is every class (mapping to itself) plus every key of `synonyms`.
- Step 7 tries the last word as stripped in step 6, then as written. That lets "wall shelves" reach `shelf` through the entry "shelves".
- Room type uses "contains" as a substring (so "bed" is inside "bedroom"), and "wc" as a whole word.
- A marker's words must be next to each other. I checked the multi-word markers and the exclusion phrases against every HM3D name and every model label: no name differs between "next to each other" and "in order with gaps".
- Marker exclusions (hair dryer, hand dryer, dish dryer, dog bed, cat bed, pet bed, massage bed, toaster oven, sauna oven) silence the whole name, even if it holds another marker.
- `answers_to(raw)` is `normalise(raw)` and `normalise` of `detector_label[raw.lower()]`, each if not structure.

## How much maps

"Maps" means the label gets a class or a structure class. Distinct strings are as written (case and `_` count apart). Occurrences are object nodes.

| source | distinct strings | mapped | occurrences | mapped | to a non-structure class |
|---|---|---|---|---|---|
| HM3D names | 1,542 | 730 (47.3%) | 120,292 | 112,531 (93.5%) | 55.0% |
| DeepSeek new objects | 126 | 111 (88.1%) | 27,479 | 27,323 (99.4%) | 99.4% |
| Gemini new objects | 42 | 41 (97.6%) | 396 | 395 (99.7%) | 99.7% |
| Placebo new objects | 71 | 70 (98.6%) | 13,323 | 13,160 (98.8%) | 98.7% |

38.6% of HM3D name occurrences are structure; they are most of the part that does not map to a class. 812 raw HM3D names (811 after steps 1-4) map to nothing: 483 of the 811 are held by one or two houses, 206 by five or more. The model counts are high because the head-noun step takes any "… chair" to `chair`.

The DeepSeek rows count raw completions and the stage graphs beside each other, so a filter_only guess that survived the filter appears twice. Counts of strings only, so this does not bias the shares much, but do not read the occurrence column as a count of distinct guesses.

Room names (share of occurrences that has a type): DeepSeek 85.4%, Gemini 81.8%, placebo 92.3%, observed maps 77.8%. Untyped: hallway, closet, office, study, storage room, garage.

## Unmapped model labels

There are 14, not 40. All 320 occurrences, after steps 1-4:

vanity 235 (DeepSeek 71, placebo 163, Gemini 1); dryer 21; counter 20; ottoman 13; console 12; hamper 7; wall art 3; workbench 2; bathmat 2; toolbox 1; sidechair 1; sideboard 1; shower caddy 1; sink vanity 1.

The placebo's one unmapped label and Gemini's one are both "vanity"; the other 12 are DeepSeek's.

## Head-noun results that are wrong by meaning

The eight steps are the authority, so I left these. Strings only; none of the four is in a test scene.

- dog bed maps to `bed` (11 houses). `marker_types("dog bed")` is empty, but `answers_to("dog bed")` is `{bed}`.
- bed frame maps to `frame` (1 DeepSeek label); "mirror stand" to `stand`.
- hall tree maps to `tree` (1 DeepSeek label).
- toilet bowl would map to `bowl` (no occurrence in any source).

## Not merged, in doubt

dresser and chest of drawers; shower and shower cabin; sink and washbasin; picture and picture frame; carpet and rug; vase and flower vase; hanger and clothes hanger; kitchen counter and countertop; towel bar and towel rack. "Washer dryer" is unmapped by `normalise` (a two-in-one machine); `answers_to("washer-dryer")` is `{washing machine}` through the detector label.

## `answers_to` on the two test scenes

Over the raw names listed in `label_mapping.json`:

| scene | raw names | with a second class | with one | with none |
|---|---|---|---|---|
| 00853 | 123 | 31 (112 of 528 objects) | 61 | 31 |
| 00871 | 139 | 24 (111 of 849 objects) | 84 | 31 |

"None" is structure (wall, floor, ceiling, door, window, shower wall, curtain rod, mirror frame, ...) or a name with no class (casket, holy cross, roomba, thermostat, island, seat, tool, wine, newspaper, ...).
