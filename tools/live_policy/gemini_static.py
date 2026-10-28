"""Static "is it the model?" check: re-ask Gemini on the exact inputs the
DeepSeek-1017 official arm saw, through the author's own llm_completion tool
loop, and score both models' predicted objects against the HM3D annotation.

Runs inside a container (read-only /workspace is fine): copies each chosen
stage's observed graph into a scratch dir, renders the input slices from it
(the slices saved in the run were overwritten with the completed graph), runs
4 Gemini members, and writes completions under <out>/<run>/<stage>/.

A hard USD cap is enforced before every call from Gemini usage metadata at
gemini-3.8-flash list price ($0.75 in, $3.75 out per M, thoughts billed as
output). The key is read from /workspace/.cvp-secrets/gemini-auth-key and
never printed.

Usage (the LLM logger reads its env at interpreter start, so set it outside):
    ASP_LLM_PROVIDER=google ASP_LLM_LOG_DIR=<out_dir>/llm_log ASP_LLM_MAX_CALLS=600 \
    python -B gemini_static.py <out_dir> <cap_usd> <run_dir>:<stage>[,<stage>...] ...
"""
import json
import os
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

SCRIPTS = "/workspace/catkin_ws/src/active_semantic_perception/exploration/scripts"
MODEL = "gemini-3.8-flash"
IN_PER_M, OUT_PER_M = 0.75, 3.75
RESERVE_USD = 0.08

out_root, cap = sys.argv[1], float(sys.argv[2])
jobs = []
for arg in sys.argv[3:]:
    run, stages = arg.rsplit(":", 1)
    jobs += [(run, s) for s in stages.split(",")]

os.makedirs(out_root, exist_ok=True)
if os.environ.get("ASP_LLM_PROVIDER") != "google" or not os.environ.get("ASP_LLM_LOG_DIR", "").startswith(out_root):
    sys.exit("set ASP_LLM_PROVIDER=google and ASP_LLM_LOG_DIR=<out_dir>/... before starting python")
with open("/workspace/.cvp-secrets/gemini-auth-key") as f:
    os.environ["GOOGLE_API_KEY"] = f.read().strip()
sys.path.insert(0, SCRIPTS)

import yaml  # noqa: E402
from google.genai import models as genai_models  # noqa: E402
import llm_completion as lc  # noqa: E402
from scene_graph_visualize_2d import create_scene_slices  # noqa: E402

lock = threading.Lock()
state = {"spent": 0.0, "reserved": 0.0, "calls": 0, "stopped": False}
ledger = open(os.path.join(out_root, "gemini_calls.jsonl"), "a")
_inner = genai_models.Models.generate_content


class CapReached(RuntimeError):
    pass


def capped(self, *args, **kwargs):
    with lock:
        if state["stopped"] or state["spent"] + state["reserved"] + RESERVE_USD > cap:
            state["stopped"] = True
            raise CapReached(f"cap {cap} reached: spent {state['spent']:.4f}")
        state["reserved"] += RESERVE_USD
    t0 = time.time()
    cost = RESERVE_USD  # charged if the call raises: it may still be billed
    try:
        resp = _inner(self, *args, **kwargs)
        um = getattr(resp, "usage_metadata", None)
        p = (getattr(um, "prompt_token_count", 0) or 0) if um else 0
        c = (getattr(um, "candidates_token_count", 0) or 0) if um else 0
        th = (getattr(um, "thoughts_token_count", 0) or 0) if um else 0
        cost = (p * IN_PER_M + (c + th) * OUT_PER_M) / 1e6 if um else RESERVE_USD
        rec = {"ts": t0, "latency_s": round(time.time() - t0, 2), "prompt": p, "candidates": c, "thoughts": th, "cost": cost}
        return resp
    except Exception as e:
        rec = {"ts": t0, "error": repr(e)[:300], "cost": cost}
        raise
    finally:
        with lock:
            state["reserved"] -= RESERVE_USD
            state["spent"] += cost
            state["calls"] += 1
            rec["spent"] = round(state["spent"], 5)
            ledger.write(json.dumps(rec) + "\n")
            ledger.flush()


genai_models.Models.generate_content = capped


def run_member(work, prompt, member, seed):
    worker = lc.LLMCompletion(base_path=work, file_to_analyze=None, model_name=MODEL, user_prompt=prompt, seed=seed)
    observed = os.path.join(work, "habitat_scene_graph_original_graph0.yaml")
    t0 = time.time()
    try:
        text = worker.generate_completion_response(observed, os.path.join(work, "input_slices"))
        ok = worker.parse_response(text, observed, f"gemini_new_graph_{member}.yaml")
        return {"member": member, "ok": bool(ok), "wall_s": round(time.time() - t0, 1)}
    except Exception as e:
        return {"member": member, "ok": False, "error": repr(e)[:300], "wall_s": round(time.time() - t0, 1)}


summary = []
for run, stage in jobs:
    if state["stopped"]:
        break
    src = os.path.join(run, "stages", stage)
    work = os.path.join(out_root, os.path.basename(run), stage)
    os.makedirs(work, exist_ok=True)
    shutil.copy(os.path.join(src, "habitat_scene_graph_original_graph0.yaml"), work)
    for k in range(4):  # the DeepSeek completions for the same track, for side-by-side scoring
        p = os.path.join(src, f"habitat_scene_graph_new_graph_{k}.yaml")
        if os.path.exists(p):
            shutil.copy(p, os.path.join(work, f"deepseek_new_graph_{k}.yaml"))
    create_scene_slices(os.path.join(work, "habitat_scene_graph_original_graph0.yaml"),
                        scene_slice_folder_name=os.path.join(work, "input_slices"))
    cfg = yaml.safe_load(open(os.path.join(run, "config", "pipeline_config.yaml")))
    seed0 = int(cfg.get("SEED", 42))
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda m: run_member(work, cfg["LLM_COMPLETION_PROMPT"], m, seed0 + m), range(4)))
    rec = {"run": run, "stage": stage, "members": results, "spent": round(state["spent"], 4)}
    summary.append(rec)
    print(json.dumps(rec), flush=True)

json.dump({"jobs": summary, "spent_usd": state["spent"], "calls": state["calls"], "cap": cap},
          open(os.path.join(out_root, "summary.json"), "w"), indent=1)
print(json.dumps({"spent_usd": round(state["spent"], 4), "calls": state["calls"], "stopped_by_cap": state["stopped"]}))
