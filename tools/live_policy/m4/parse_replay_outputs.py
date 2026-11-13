"""Turn replayed members' final texts into scene graphs with the author's own parse_response.

Runs inside the asp-noetic container, CPU only. It calls no model and needs no key.

For each `<outputs>/<model>/<row_id>/member_<k>/final.txt` it runs, exactly as
tools/live_policy/gemini_static.py does for Gemini:

    worker = llm_completion.LLMCompletion(base_path=<member folder>, file_to_analyze=None,
                                          model_name=<model>, user_prompt=<prompt>, seed=0)
    ok = worker.parse_response(text, <observed graph>, "parsed_graph.yaml")

and writes `parse.json` ({"ok": bool, "error": str or null}) beside the result. A member whose
text does not parse is a dropped member (PREREGISTRATION_SEMANTIC.md §12); nothing is repaired.

Usage:
    python -B parse_replay_outputs.py <inputs_root> <outputs_root>
inputs_root holds `<row_id>/graph.yaml` and `<row_id>/prompt.txt` (export_replay_inputs.py).
"""
import json
import os
import shutil
import sys
import traceback

SCRIPTS = "/workspace/catkin_ws/src/active_semantic_perception/exploration/scripts"
OBSERVED = "habitat_scene_graph_original_graph0.yaml"


def main():
    inputs_root, outputs_root = sys.argv[1], sys.argv[2]
    os.environ.setdefault("GOOGLE_API_KEY", "unused-no-call-is-made")
    sys.path.insert(0, SCRIPTS)
    import llm_completion as lc  # noqa: E402

    counts = {"ok": 0, "failed": 0, "no_text": 0}
    for model in sorted(os.listdir(outputs_root)):
        mroot = os.path.join(outputs_root, model)
        if not os.path.isdir(mroot):
            continue
        for row_id in sorted(os.listdir(mroot)):
            rroot = os.path.join(mroot, row_id)
            src = os.path.join(inputs_root, row_id)
            if not os.path.isdir(rroot) or not os.path.exists(os.path.join(src, "graph.yaml")):
                continue
            prompt = open(os.path.join(src, "prompt.txt")).read()
            for member in sorted(os.listdir(rroot)):
                work = os.path.join(rroot, member)
                text_path = os.path.join(work, "final.txt")
                if not os.path.isdir(work) or not member.startswith("member_"):
                    continue
                if not os.path.exists(text_path):
                    counts["no_text"] += 1
                    continue
                observed = os.path.join(work, OBSERVED)
                shutil.copy(os.path.join(src, "graph.yaml"), observed)
                out = os.path.join(work, "parsed_graph.yaml")
                if os.path.exists(out):
                    os.remove(out)
                rec = {"ok": False, "error": None}
                try:
                    worker = lc.LLMCompletion(base_path=work, file_to_analyze=None, model_name=model,
                                              user_prompt=prompt, seed=0)
                    rec["ok"] = bool(worker.parse_response(open(text_path).read(), observed, "parsed_graph.yaml"))
                    if rec["ok"] and not os.path.exists(out):
                        rec = {"ok": False, "error": "parse_response returned true but wrote no file"}
                except Exception as e:  # the author's parser raised: the member does not parse
                    rec["error"] = repr(e)[:300] + " | " + traceback.format_exc(limit=1)[-200:]
                json.dump(rec, open(os.path.join(work, "parse.json"), "w"))
                counts["ok" if rec["ok"] else "failed"] += 1
                print(json.dumps({"model": model, "row": row_id, "member": member, **rec}), flush=True)
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
