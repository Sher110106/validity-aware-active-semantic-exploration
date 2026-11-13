| Measure, m² | 00853 | 00871 |
|---|---|---|
| Navmesh island that holds the start (walkable floor) | 77.0 | 59.3 |
| HM3D labelled floor (all regions' floor triangles) | 102.4 | 104.9 |
| Footprint of all labelled geometry, seen from above | 165.1 | 168.1 |
| Waypoint grid of the tour (cells kept times cell area) | 191.2 | 148.5 |
| Convex hull of the labelled floor | 196.4 | 211.1 |
| Convex hull of all labelled geometry | 213.2 | 252.9 |
| Box around all labelled geometry, along the mesh axes | 268.6 | 301.7 |
| The paper's figure | 207.6 | 235.0 |
| Paper's figure over the navmesh island | 2.70 | 3.97 |
| Paper's figure over the hull of all labelled geometry | 0.97 | 0.93 |

Reading. No measure of floor comes near the paper's figure. It is 2.7 and 4.0 times the navmesh island that holds the start, and 2.0 and 2.2 times the labelled floor. It lies close to the convex hull of all labelled geometry (0.97 and 0.93 of it). We do not know how the paper measured area; the area of the house's outline, with walls and furniture, would fit these figures. Both houses have one level.

Descriptive. C1 as registered compares the navmesh island with the paper's figure; the other rows were added on 11-13, after C1's result was known (DEVIATIONS_NOVEMBER.md, item 59). Built by `tools/live_policy/c1_area.py` from `semantic/truth/` and `results_paper_compare_1112/c_checks.json`.
