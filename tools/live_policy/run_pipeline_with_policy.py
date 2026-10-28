"""Run the pinned exploration_pipeline.py with a live completion policy.

Usage (from any directory):
    ASP_LIVE_POLICY=filter_only python run_pipeline_with_policy.py

The pinned checkout is not edited. This wrapper patches
llm_completion.LLMManager.complete_scene_graph (see live_policy.install) and
then runs exploration_pipeline.py as __main__ from its own directory, so its
relative config path and the spawn workers behave exactly as in a direct run.
"""
import os
import runpy
import sys

SCRIPTS = os.environ.get(
    "ASP_PIPELINE_SCRIPTS",
    "/workspace/catkin_ws/src/active_semantic_perception/exploration/scripts",
)
OFFLINE_TOOLS = os.environ.get("ASP_OFFLINE_TOOLS", "/workspace/tools")
HERE = os.path.dirname(os.path.abspath(__file__))

sys.path[:0] = [SCRIPTS, OFFLINE_TOOLS, HERE]

import live_policy  # noqa: E402

policy = live_policy.policy_from_env()

# Same first three imports, in the same order, as exploration_pipeline.py,
# so native libraries load as they do in a direct run.
from graph_planning import GraphPlanner  # noqa: F401,E402
from mid_planning import MidPlanner  # noqa: F401,E402
import llm_completion  # noqa: E402

if policy != "official":
    # Import the offline modules now so a broken path fails before the robot
    # moves, not at the first planning step.
    import asp_offline.support_policy  # noqa: F401,E402
    import asp_offline.validator  # noqa: F401,E402

live_policy.install(llm_completion.LLMManager, policy)
print(f"[live_policy] installed policy={policy}", flush=True)

os.chdir(SCRIPTS)
runpy.run_path(os.path.join(SCRIPTS, "exploration_pipeline.py"), run_name="__main__")
