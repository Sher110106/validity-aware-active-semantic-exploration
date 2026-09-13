# Offline ASP extension tools

These modules implement the locked Phase 8 contract without ROS, Habitat, or
an LLM. They are intended to run on cached artifacts exported by the Linux
simulation host.

```sh
PYTHONPATH=tools python tools/validate_fixture_graph.py completion.txt --observed observed.json
PYTHONPATH=tools python tools/evaluate_cached_run.py --run runs/scene00069_seed42_author --reference reference.json
```

Completions must contain exactly one fenced `yaml`/`yml` block. JSON inside that
block is accepted because JSON is valid YAML and keeps replay jobs dependency
free. Install `PyYAML` when replaying native YAML responses.
