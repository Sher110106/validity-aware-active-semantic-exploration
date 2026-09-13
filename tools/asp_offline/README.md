# Offline ASP extension tools

These modules implement the locked Phase 8 contract without ROS, Habitat, or
an LLM. They are intended to run on cached artifacts exported by the Linux
simulation host.

```sh
PYTHONPATH=tools python tools/validate_fixture_graph.py completion.txt --observed observed.json
PYTHONPATH=tools python tools/evaluate_cached_run.py --run runs/scene00069_seed42_author --reference reference.json
PYTHONPATH=tools python tools/replay_cached_validation.py \
  --completions-dir runs/scene00069_seed42_author/stages/0 \
  --observed runs/scene00069_seed42_author/stages/0/habitat_scene_graph_original_graph0.yaml \
  --reference reference.yaml --expected-count 8 --output offline_validation.json
```

Completions must contain exactly one fenced `yaml`/`yml` block. JSON inside that
block is accepted because JSON is valid YAML and keeps replay jobs dependency
free. Install `PyYAML` when replaying native YAML responses.

The validator rejects parsed Python mappings by default so replayed data follows
the same wire contract as an LLM response; callers that already own a parsed
mapping must opt in with `ValidationConfig(allow_parsed_mapping=True)`. Online
validation never receives a reference graph. Use `label_against_reference()`
after validation when adding evaluator labels for diagnostics. If every
ensemble member is rejected, the returned observed graph carries a
`frontier_fallback` record with deterministic horizontal faces of observed
`nothing` cuboids for the navigation layer to consume.
