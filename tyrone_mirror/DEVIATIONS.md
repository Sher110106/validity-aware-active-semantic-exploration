# Deviations from the author's documented setup

Environment: Docker (Ubuntu 20.04 + ROS Noetic, CUDA 11.8 devel base) on tyrone
(host is Ubuntu 24.04, no native ROS Noetic packages). Image: `docker/Dockerfile`.
Container: `asp-noetic`, workspace bind-mounted at `/workspace`.

1. **HEADLESS=1, not HEADLESS=0.** tyrone is an SSH-only server with no
   attached display for the container. habitat-sim was built and should be
   run with `HEADLESS=1`, not the author's default `HEADLESS=0`.

2. **`vs_graphs` (visual_sgraphs) is skiplisted.** It requires `aruco_ros`,
   which active_semantic_perception's own rosinstall does not provide.
   Verified nothing in the tree depends on vs_graphs and it is not part of
   the Habitat exploration pipeline (README's `roslaunch clio_ros
   realsense.launch` + `exploration_pipeline.py`), so it's excluded rather
   than pulling in an unrelated upstream repo.

3. **GTSAM built from source**, at the commit Kimera-RPGO's own README says
   it tested against (`686e16aaae26c9a4f23d4af7f2d4a504125ec9c3`), with the
   `GTSAM_POSE3_EXPMAP=ON`/`GTSAM_ROT3_EXPMAP=ON` flags that same README
   calls load-bearing for correct Jacobians. No `ros-noetic-gtsam` apt
   package exists and rosdep has no rule for the `gtsam` key on this
   rosdistro snapshot (verified via `rosdep resolve gtsam`).

4. **Eigen unified to 3.4.0 system-wide**, replacing focal's apt
   `libeigen3-dev` (3.3.7). Root cause: `nvblox` (a submodule under
   `mapping/nvblox_ros1/nvblox`) hard-pins Eigen 3.4.0 via its own
   `ExternalProject_Add` and that copy lands in the shared catkin devel
   space, shadowing whatever "system" Eigen everything else built against.
   GTSAM static-asserts on an exact Eigen version match, so kimera_pgmo /
   kimera_pgmo_ros failed to compile against a 3.3.7-built GTSAM. Building
   Eigen 3.4.0 from source (same version, same source URL nvblox's own
   `eigen.cmake` uses) and symlinking `/usr/include/eigen3` to it — rather
   than patching nvblox's vendored CMake or `apt remove`-ing
   `libeigen3-dev` (which would cascade-remove `libpcl-dev` and other
   packages this stack needs) — made every consumer agree on one version.

5. **Three apt packages installed directly, bypassing `rosdep install`:**
   `libzmqpp-dev`, `nlohmann-json3-dev`, `ros-noetic-rviz-visual-tools`.
   Each has an apt/ROS package available, but rosdep has no rule for their
   keys on this machine (confirmed via `rosdep resolve <key>` returning
   "no rosdep rule"). `rosdep install ... --skip-keys` is used for
   `gtsam rviz_visual_tools gflags_catkin voxblox_msgs nvblox` at build
   time so rosdep doesn't error out re-attempting them (`gflags_catkin` is
   khronos_eval-only, already skiplisted; `voxblox_msgs` is kimera_pgmo_ros's
   legacy voxblox integration per Hydra's own README note about replacing
   voxblox with spatial_hash; `nvblox` itself is built from the vendored
   submodule via nvblox_ros's own CMake, not apt).

6. **`ros-noetic-vision-msgs` installed directly.**
   `hydra_ros/src/active_window/nothing_bbox_extractor.h` includes
   `<vision_msgs/Detection3DArray.h>` but `hydra_ros`'s package.xml never
   declares a `vision_msgs` dependency at all — a genuine upstream omission,
   not a rosdep gap.

7. **`importlib_metadata` upgraded inside the Python 3.9 venv.**
   `--system-site-packages` leaks in focal's ancient `importlib-metadata`
   (1.5.0), which lacks `EntryPoints` and breaks any build backend that
   imports a modern `setuptools` — surfaced when detectron2's
   `pyproject.toml` metadata step ran. `pip install -U "importlib_metadata>=6"`
   inside the venv shadows the system one without touching anything
   system-wide.

8. **torch/torchvision pinned to the cu118 build**
   (`torch==2.0.1 torchvision==0.15.2 --index-url
   https://download.pytorch.org/whl/cu118`) before installing
   `scene_segment_ros/src/requirements.txt`. That file's unpinned
   `torch>=1.7.0` otherwise resolves to a recent wheel built for CUDA 12.8,
   which mismatches this container's CUDA 11.8 toolchain and fails
   detectron2's CUDA extension build. This is the exact pin
   `mapping/visual_sgraphs/docker/Noetic.Dockerfile` (a sibling submodule
   building the same detectron2 dependency against the same CUDA 11.8 base)
   already uses, so it's precedent from this repo tree, not a new choice.

None of these change the pinned commit of active_semantic_perception itself,
any of its own source files, or the scenes/seeds/model the plan specifies —
they are build-environment fixes only.

## Post-build deviations (Phase 4)

9. **Scenes 00069 and 00573 replaced with 00006 and 00023.** HM3D v0.2 only
   released semantic annotations for 145 of 800 train scenes; 00069 and
   00573 (the plan's original train scenes) are not among them, so
   Phase 10's evaluator (GED, room/object precision-recall against ground
   truth) would have nothing to score them against. Replacements were
   picked from the annotated set, matched in object-count scale to the
   original val scenes (00853: 529 objects/29MB mesh, 00871: 849
   objects/29MB mesh): 00006-HkseAnWCgqk (453 objects/25MB) and
   00023-zepmXAdrpjR (572 objects/33MB). Final scene set: 00006, 00023
   (train), 00853, 00871 (val). Confirmed by user decision on 2026-09-13.

10. **`vs_graphs` un-skiplisted and built; the earlier skiplist decision
    was wrong.** `realsense.launch` (exactly what the README's
    `roslaunch clio_ros realsense.launch` runs) unconditionally includes
    `$(find vs_graphs)/launch/vs_graphs.launch`, so vs_graphs cannot be
    skipped. Fixed by:
    - `ros-noetic-backward-ros` installed via apt (it IS available —
      the original "not available" finding was from a stale apt cache
      that hadn't run `apt-get update`; confirmed available at
      0.1.7-1focal once refreshed). Added as its own Dockerfile layer at
      the end of the file, not merged into the earlier apt block, so it
      didn't invalidate the cache for the expensive GTSAM/Eigen/Pangolin/
      PyKDL builds above it.
    - `aruco_ros` (which bundles `aruco`, `aruco_msgs`, and the `aruco_ros`
      wrapper package) cloned from source at the `noetic-devel` branch —
      the same branch `mapping/visual_sgraphs/docker/Noetic.Dockerfile`
      (this repo's own sibling submodule Dockerfile) uses — into
      `catkin_ws/src/aruco_ros`, as a sibling package to
      `active_semantic_perception`, not inside its pinned checkout.
    - `vs_graphs` removed from `catkin config --skiplist` in
      `docker/setup_catkin_ws.sh` (only `khronos_eval` remains skiplisted,
      per the plan).
    - One-time ordering glitch: in the same `catkin build` invocation that
      newly discovered `aruco_ros`/`aruco_msgs`/`aruco`, vs_graphs's CMake
      configure step ran before `aruco_ros` had finished (build log shows
      `aruco_ros` finishing at position 32/34, after vs_graphs's failed
      configure), so `find_package(catkin REQUIRED COMPONENTS ...
      aruco_ros ...)` couldn't find it yet — a build-scheduling race, not
      a real absence. A second `catkin build vs_graphs` (with aruco_ros
      now already in the devel space from the first pass) succeeded
      cleanly in 43.8s with 0 errors.
    Verified: `rospack find vs_graphs` resolves; `rospack find clio_ros`
    and `rospack find nvblox_ros` still resolve (no regression);
    `roslaunch --files clio_ros realsense.launch` exits 0 and lists all
    five launch files in the include chain (openset_detection.launch,
    nvblox_ros_panopt.launch, clio.launch, vs_graphs.launch,
    realsense.launch itself) with no "package not found" errors; the
    Python dependency gate (`import habitat_sim; import PyKDL; import
    spark_dsg`) still passes unchanged. Phase 2's build gate is now fully
    closed.

## Correction (Phase 4, same evening)

**Deviation #9 REVERTED.** The scene substitution (00069→00006, 00573→00023)
was based on a wrong assumption: that Phase 10's evaluator needs HM3D's
official semantic-annotation files (.semantic.glb/.semantic.txt) as its
ground truth. Investigation of the author's own scripts
(exploration/scripts/ged_score_plot.py, llm_completion.py) shows the
"ground truth" / "fully explored reference graph" is `habitat_scene_graph_
original_graph{i}.yaml` — the exact same DSG YAML format the pipeline
itself writes at every stage — read from a `GT_<scene>` folder. That file
is generated by running the ASP pipeline itself to exhaustive coverage, not
derived from HM3D's official semantic files. Confirmed the live pipeline
also never calls habitat_sim's SemanticScene API (own open-vocab
detection via YOSO/CLIP) — so HM3D's semantic annotations are not used
anywhere in this pipeline, online or offline.

The only real constraint was that pipeline_config.yaml's
SCENE_DATASET_CONFIG pointed at "hm3d_annotated_basis.scene_dataset_
config.json", which enumerates only the 221 scenes that DO have semantic
annotations (00069/00573 excluded) — a scene-loading concern, not an
evaluation one. Fixed by switching to the plain
"hm3d_basis.scene_dataset_config.json" (glob-pattern based, matches any
scene, only needs .basis.glb/.navmesh which all 4 plan scenes have).

**Reverted to the plan's original scene set: 00069, 00573, 00853, 00871.**
Scene 00069 is active by default in pipeline_config.yaml / realsense.launch,
matching the plan's Phase 5 default. 00006/00023 data remains downloaded
on disk (harmless, part of the full train split) but is not used.

Lesson: should have checked the evaluator's actual ground-truth source
before treating a missing-annotation gap as blocking. Caught before any
scored run existed, so no wasted compute — only a few minutes of config
churn.

## Headless EGL rendering fix (preflight check before Phase 5)

11. **`docker/run.sh` needed two additions for GPU-accelerated headless
    rendering to actually work, not just avoid errors.** Habitat-Sim's
    windowless EGL context creation failed with "unable to find CUDA
    device 0 among 1 EGL devices in total" using the original `--gpus all`
    only setup. Root cause: (a) `NVIDIA_DRIVER_CAPABILITIES` defaulted to
    `compute,utility`, missing `graphics`/`display` needed for EGL; (b)
    even after adding `-e NVIDIA_DRIVER_CAPABILITIES=all`, the container
    still only had Mesa's software EGL vendor registered
    (`/usr/share/glvnd/egl_vendor.d/50_mesa.json`) — the NVIDIA EGL vendor
    JSON (`10_nvidia.json`) exists on the host and is even listed in the
    host's CDI spec (`/var/run/cdi/nvidia.yaml`), but Docker's `--gpus all`
    path here uses the legacy (non-CDI) nvidia-container-runtime discovery,
    which mounts NVIDIA's `.so` libraries by pattern but not this vendor
    JSON file. Fixed by explicitly bind-mounting it:
    `-v /usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro`.
    Both additions are now in `docker/run.sh`.

    **Verified, not just assumed fixed**: `test_render.py` (workspace root)
    loads scene 00069 via habitat-sim, renders 5 RGB-D frames from random
    navigable points, and asserts RGB pixel variance > 5.0 per frame (real
    frames were 3000-4000; a black/blank frame would read ~0). Confirmed
    PASS in the actual persistent `asp-noetic` container after recreating
    it with the `docker/run.sh` fix. Re-run this script after any future
    container recreation before trusting a live run's visual input.

    Also confirms (harmlessly): scene 00069 logs a "SemanticScene ... SSD
    Load Failure" warning (no `.basis.scn`/`info_semantic.json`, since HM3D
    only ships those for the 221 annotated scenes) but rendering and
    simulation continue normally — consistent with deviation #9's finding
    that the pipeline doesn't use habitat_sim's SemanticScene API.

## LLM call logging + hard cap (preflight check before Phase 5)

12. **`llm_completion.py` never persists raw prompts or responses to disk
    anywhere** (confirmed by grep - only pose/IG candidate logging exists,
    e.g. `pose_log.json`). This breaks the "run is replayable from saved
    artifacts" gate criterion, and means a failed/misbehaving run can't be
    inspected without re-paying for the API calls. Also, nothing in the
    pipeline bounds total Gemini API calls - an unsupervised run with a
    bug could retry unboundedly against a paid API.

    Fixed via a wrapper **outside the pinned checkout**: installed into the
    Python venv's site-packages
    (`environments/semantic_perception/lib/python3.9/site-packages/
    _asp_llm_logger.py` + `_asp_llm_logger.pth`), not by editing
    `llm_completion.py`. It patches `google.genai.models.Models.
    generate_content` (the single underlying call both `client.models.
    generate_content()` and `chat.send_message()` delegate to - verified
    by reading `google/genai/chats.py`) to: (a) log every call's model
    name, request contents (text in full; image parts as type/size only,
    since the actual image files are already saved separately on disk by
    the pipeline) and response (text, function calls, token usage) to
    `$ASP_LLM_LOG_DIR/prompts_responses.jsonl`; (b) enforce a hard
    `$ASP_LLM_MAX_CALLS` ceiling, raising before the network call once
    exceeded rather than after.

    Patching is deferred via a `builtins.__import__` hook until
    `google.genai.models.Models` is fully defined (not attempted eagerly
    at `.pth`-load time, which is too early in interpreter startup for
    this `--system-site-packages` venv and fails on `typing_extensions`).
    Hit and fixed one real bug during testing: the first patch attempt
    can see the module mid-initialization (registered in `sys.modules`
    per Python's circular-import handling, but before its `Models` class
    is defined) - the original code treated that as "already patched" and
    gave up permanently; fixed to only give up once the class is
    confirmed either freshly patched or already carrying the patch
    marker. Verified end-to-end with a dummy API key: 2/2 calls under
    cap went through and logged (with the real "API key not valid"
    error), calls 3/4 were correctly refused before hitting the network.

    Must be set before launching `exploration_pipeline.py` or
    `frontier_baseline.py`:
    `ASP_LLM_LOG_DIR=<run artifact dir>`, `ASP_LLM_MAX_CALLS=<budget>`.
    Defaults (if unset): `/workspace/runs/_unrouted_llm_log`, 500 calls.

## Phase 6 evaluator (built in parallel with Phase 5, per Opus advisor's
## suggestion that this is pure offline code safe to build regardless of
## Phase 5's outcome)

13. **Independent evaluator implemented and unit-tested**, at
    `tools/evaluator/` (outside the pinned checkout, per plan section 15's
    `tools/evaluate_cached_run.py` naming). Modules: `graph_io.py` (loads
    `habitat_scene_graph_original_graph{i}.yaml`, replicating the author's
    exact door/structure/nothing exclusion from
    `exploration/scripts/ged_score_plot.py` and `f1_score_plot.py`),
    `matching.py` (greedy same-name nearest-neighbor object matching within
    0.5m, one-to-one, exactly replicating `f1_score_plot.py`'s
    `calculate_f1_score` - deliberately NOT parent-room-aware, matching the
    source), `ged.py` (graph edit distance via networkx's built-in
    `graph_edit_distance` with a custom substitution cost replicating
    `ged_score_plot.py`'s `custom_node_cost`: free substitution only for
    same type+name+position-within-threshold, and for objects also same
    parent room; forbidding penalty otherwise, so the optimal edit always
    prefers plain node insert/delete). Deliberately uses networkx instead
    of the author's `gmatch4py` dependency - same cost semantics, avoids an
    extra third-party package, consistent with IMPLEMENTATION_RESEARCH.md
    section 3.3's decision that this must be our own implementation, not a
    reuse of the released (hard-coded-path) scripts.

    9 unit tests against hand-made fixture graphs
    (`tools/evaluator/tests/`), including two GED values verified by hand
    calculation (3.0 and 4.0 for two deliberately constructed
    parent-mismatch/no-match cases) and one full CLI smoke test (GED=8.0,
    also hand-verified). All pass in both a local dev venv and the actual
    project venv on tyrone (Python 3.9.5). CLI: `python evaluate_run.py
    --run <run_dir> --gt <ground_truth.yaml>`.

    **Not yet run against any real captured data** - built and tested
    against synthetic fixtures only, since no live run had produced real
    artifacts yet at the time this was written. Run it against the first
    real Phase 5 output before trusting its numbers on a real scene; the
    file-format assumptions (stage directory layout, navigation_stats.json
    keys) are inferred from the author's own evaluation scripts and have
    not been cross-checked against actual pipeline output yet.

## Phase 5 first-run debugging (fork session)

14. **`setup_keyboard_listener` requires a virtual X display.**
    `exploration_pipeline.py` imports `pynput.keyboard` at module level and
    calls `setup_keyboard_listener(pipeline)` before the main loop, to let a
    human press 's' to start / double-Esc to stop. pynput's Linux backend
    refuses to initialize at all without a real or virtual X11 display,
    crashing the whole script on import even though the automated
    official-ASP policy never needs actual keyboard input. Fixed with
    Xvfb (virtual framebuffer X server) - `apt-get install xvfb` (now in
    `docker/Dockerfile`), started via `Xvfb :99 -screen 0 1024x768x24 &`
    before launching the pipeline with `DISPLAY=:99` set. This also
    resolves the earlier `/usr/bin/env: 'python': No such file` and
    `ModuleNotFoundError: No module named 'semantic_inference'` errors on
    two ROS nodes (`segmenter_ros`, `semantic_inference`) - both were
    actually caused by Terminal 1 (`roslaunch clio_ros realsense.launch`)
    not having the Python venv activated, which the plan's own Phase 5
    instructions specify but which was missed in this session's first
    launch attempt.

15. **The pipeline needs an actual 's' keypress to leave its IDLE state**
    (`start_pipeline()` only fires from the keyboard listener's `on_press`
    callback) - it will otherwise sit idle forever, publishing TF only,
    never touching sensors or the LLM. This is intentional interactive
    control, not a bug. Automated with `xdotool key s` targeting the Xvfb
    display (`apt-get install xdotool`, added to `docker/Dockerfile`) -
    this drives the exact control mechanism the author built, rather than
    changing any behavior. A `pynput.keyboard.Controller`-based self-press
    from a separate process did NOT register with the running listener
    (unclear why - possibly an XRecord vs XTEST discrepancy); xdotool
    worked on the first attempt.

16. **`cv_bridge` / `opencv-python` version conflict crashes every
    `cv2_to_imgmsg()` call with `KeyError: 16`.** Root cause: `mapping/
    scene_segment_ros/src/requirements.txt` pulls in `ultralytics` (YOLOE),
    whose unpinned `opencv-python` dependency resolved to 5.0.0 at install
    time - a major version that changed internal Mat type constants
    (`cv2.CV_8UC3 == 64` instead of the standard `16`) relative to what
    ROS Noetic's apt-installed `cv_bridge` (compiled years earlier,
    expecting the traditional numbering) relies on. `cv_bridge`'s Python
    `core.py` builds its `cvtype_to_name` lookup dict from whatever `cv2`
    is importable at runtime, but `encoding_to_cvtype2()` computes the
    expected type code independently/statically - under opencv-python 5.x
    these two disagree, and every `publish_sensor_images()` call (i.e.
    every attempt to actually feed Habitat's RGB-D into ROS/Clio) crashed
    immediately with an unhelpful bare `KeyError: 16` (the pipeline's own
    top-level exception handler only logs `str(e)`, discarding the
    traceback - diagnosed the real cause with a temporary external
    debug wrapper, `debug_traceback_wrapper.py`, that monkeypatches
    `rospy.logfatal` to also print `traceback.format_exc()`; not part of
    the permanent toolchain, deleted after use).
    Fixed by re-pinning `opencv-python==4.10.0.84` (installed after
    `requirements.txt`, so it overrides ultralytics's resolution) in
    `docker/setup_python_env.sh`. Verified: `cv2.CV_8UC3` now reads `16`,
    matching `encoding_to_cvtype2`, and a manual `cv2_to_imgmsg` call
    succeeds. This is a straightforward dependency-version pin, not a
    numeric/science-affecting change - doesn't touch anything about the
    actual RGB-D content, only which library encodes it into a ROS message.

## Phase 5 BLOCKED: segfault in core graph-merging logic (not yet resolved)

17. **`clio_node` (hydra_ros_node) segfaults inside the pinned checkout's own
    core scene-graph-merging logic**, not an environment/plumbing issue.
    Two distinct crashes observed across two attempts:

    - Attempt 1 (visualizer enabled): SIGSEGV in
      `hydra::visualizer::DsgVisualizer::spinOnce()` ->
      `SceneGraphRenderer::draw()` -> `makeLayerNodeMarkers()` ->
      `hydra::NearestFeatureColor::getColor()` -> Eigen
      `PlainObjectBase` constructor, immediately preceded by
      `ros_embedding_group.cpp:57] Failed to get embeddings from
      '/task_server/places'`. Also saw `rviz` crash separately (SIGABRT,
      exit -6) - expected in this headless setup.
    - Attempt 2 (`start_visualizer:=false start_rviz:=false`, ruling out
      the above): **clio_node still segfaults**, this time in a genuinely
      different, more serious place - the core frontend thread:
      `hydra::GraphBuilder::dispatchSpin()` -> `spinOnce()` ->
      `spark_dsg::DynamicSceneGraph::mergeGraph()` -> `removeNode()` ->
      `SceneGraphLayer::removeNode()` -> `std::_Rb_tree<>::erase()` ->
      `SceneGraphNode::~SceneGraphNode()` ->
      `PlaceNodeAttributes::~PlaceNodeAttributes()` -> `cfree` -> SIGSEGV.
      This is a double-free/use-after-free pattern in the pinned
      checkout's own C++ merge logic, not a headless-environment artifact,
      not a launch-config issue, and not something disabling
      visualization changes. It reproduces at the same point both times:
      right as the first real object/place detections would be merged
      into the graph after the initial 360-degree scan (the DSG JSON
      files were confirmed being written with valid structure but 0
      nodes/edges immediately before each crash - consistent with the
      crash happening exactly when the *first* nodes get added).

    **Not attempted**: patching spark_dsg/hydra's C++ source. Per the
    plan's own rule (Section 5: the author checkout is the immutable
    baseline) and this session's explicit debugging boundary, a crash
    inside the pinned checkout's actual merge/graph algorithm is
    stop-and-report territory, not something to patch blind. Two
    independent crash signatures in two attempts (not the same repeated
    failure) both hit shortly after real perception data starts flowing,
    which is at least consistent with - though not proof of - a version
    mismatch somewhere in the spark_dsg/Eigen/hydra dependency chain that
    the environment-level Eigen-unification fix (deviation #4) didn't
    fully resolve for this specific code path, or a genuine upstream bug
    exposed by this specific scene/detection-timing combination that the
    authors may not have hit in their own environment. Needs either (a)
    a debug build with symbols + full backtrace/valgrind analysis to
    pin down the exact memory-safety bug, or (b) reaching out to the
    upstream Kimera-PGMO/Hydra/spark_dsg maintainers, or (c) the user's
    own judgment on whether to attempt a careful, reviewed patch to the
    checkout (would need its own branch + explicit sign-off, not
    something to do unsupervised).

    **Phase 5 gate status**: items 2 (Habitat RGB-D/pose - CONFIRMED
    working, ~10Hz RGB) and partially 7 (config/manifest artifacts saved)
    are the only ones cleanly met. Items 1, 3, 4, 5, 6 are NOT met - the
    required mapping node crashes before a populated scene graph, LLM
    query, or viewpoint selection is ever reached. Gate does not pass.

## Small hardening (after Opus advisor review)

18. **LLM logger shim (deviation #12) moved to workspace-tracked source.**
    Was only in the venv's site-packages directly, which a future `pip
    install` in that venv could silently overwrite (confirmed it survived
    tonight's opencv pin, but that was luck, not a guarantee). Source of
    truth now at `tools/llm_logger/{_asp_llm_logger.py,.pth}`, installed
    into site-packages via `tools/llm_logger/install.sh` - re-run that
    after any venv rebuild or pip install.

## Phase 5 segfault: ROOT CAUSE FOUND AND FIXED

19. **The clio_node segfault (item 16) was a real, confirmed ABI mismatch
    from GTSAM's `-march=native` build flag propagating transitively via
    CMake's exported interface, RESOLVED by rebuilding GTSAM without it.**
    Root cause, found via the staged, cheapest-first investigation:

    - `hydra_ros`'s build used `Eigen3_DIR=/usr/local/share/eigen3/cmake`
      while `spark_dsg`/`hydra_visualizer` used `Eigen3_DIR=/usr/lib/cmake/
      eigen3`. These two CMake package configs report different version
      *strings* (3.3.7 vs 3.4.0) but were confirmed to resolve to
      byte-identical header content (`/usr/include/eigen3` is a symlink
      to `/usr/local/include/eigen3`, both show `EIGEN_MAJOR_VERSION 4
      EIGEN_MINOR_VERSION 0` in the actual macros) - this specific
      disagreement was a red herring, not the cause.
    - The actual cause: `GTSAM_BUILD_WITH_MARCH_NATIVE:BOOL=ON` (set in
      the original GTSAM build per deviation #3) causes GTSAM's exported
      `GTSAM-exports.cmake` to carry
      `INTERFACE_COMPILE_OPTIONS "-march=native"` - this propagates to
      *every* package that links against GTSAM (hydra_ros, via
      kimera_pgmo/kimera_rpgo), while `spark_dsg` (no GTSAM dependency)
      never gets it.
    - **Decisive proof**: a standalone probe program
      (`sizeof(spark_dsg::PlaceNodeAttributes)` /
      `alignof(...)`, compiled against the real installed spark_dsg
      header) gave **416 bytes / 16-byte align** without `-march=native`,
      and **448 bytes / 32-byte align** with it - the exact same struct,
      two different binary layouts, depending only on this one flag.
      `PlaceNodeAttributes` holds `Eigen::Vector3d` members; on this CPU,
      `-march=native` enables wider AVX registers that change Eigen's
      alignment requirements for such members. `spark_dsg` allocates
      `PlaceNodeAttributes` objects using the 416/16 layout; `hydra_ros`
      (inheriting `-march=native` from GTSAM) was freeing/destructing the
      *same* object type assuming the 448/32 layout - a textbook
      cross-translation-unit ABI mismatch, producing exactly the
      double-free/heap-corruption crash observed (and why the crash
      signature differed slightly between the two earlier attempts:
      corrupted-heap crashes are inherently nondeterministic in exact
      manifestation).

    **Fix**: rebuilt GTSAM (`/opt/gtsam/build`) with
    `-DGTSAM_BUILD_WITH_MARCH_NATIVE=OFF` (all other flags, including the
    load-bearing `GTSAM_POSE3_EXPMAP=ON`/`GTSAM_ROT3_EXPMAP=ON`/
    `GTSAM_USE_SYSTEM_EIGEN=ON` from deviation #3, unchanged), then
    `catkin clean` + rebuilt every GTSAM-dependent package (hydra,
    hydra_ros, kimera_rpgo, kimera_pgmo, kimera_pgmo_ros, clio, clio_ros,
    hydra_visualizer, vs_graphs) - **34/34 packages succeeded, 0
    failures**. This is a build-configuration change (a compiler
    optimization flag, same category as the Eigen-unification fix in
    deviation #4), not an edit to any algorithm/source file - GTSAM's own
    correctness (governed by the separate EXPMAP flags) is unaffected;
    the tradeoff is giving up some AVX-specific performance on this CPU
    in exchange for a workspace-wide consistent ABI.

    **Verified working, not just plausible**: reran the Phase 5 smoke
    test after the rebuild. `clio_node` survived past the point of both
    previous crashes. The DSG file went from empty (`"nodes":[]`) to
    populated with real nodes and weighted edges. State machine
    progressed SCANNING -> PLANNING correctly, `_wait_for_and_copy_dsg_
    files` succeeded (previously timed out every time):
    `Copied file to .../stages/0/graph0_dsg.json` /
    `graph1_dsg.json`. **Gate items 1 (no crash), 2 (RGB-D/pose), and 3
    (non-empty scene graph) are now all satisfied** - this was not true
    before this fix.

    GTSAM was rebuilt in-place inside the running `asp-noetic` container
    (not yet baked into `docker/Dockerfile`) - the change lives in the
    container's writable layer only right now. **Next step before this
    is durable**: add `-DGTSAM_BUILD_WITH_MARCH_NATIVE=OFF` to the GTSAM
    cmake invocation in `docker/Dockerfile` so a future image rebuild
    doesn't regress this.

## Phase 5 NEW blocker: Gemini model retirement (external, needs a decision)

20. **`gemini-2.5-pro` (the model pinned in `pipeline_config.yaml`'s
    `LLM_MODEL_NAME`) returns `404 NOT_FOUND: This model models/gemini-
    2.5-pro is no longer available to new users`** when actually called
    via `generate_content`, even though it still appears in
    `client.models.list()` - an availability restriction tied to this
    API key/project, not a full catalog removal. This is an external,
    upstream API change, not anything in this environment or the pinned
    checkout - confirmed by getting past the segfault and reaching a
    real (if failed) API call, logged correctly by the `_asp_llm_logger`
    wrapper (5 calls attempted, all identical 404, well under the 60-call
    smoke-test cap - no cost incurred, these are all rejected before
    generating any tokens).

    Available replacement candidates from `client.models.list()`
    (filtered to gemini pro/flash-tier, as of 2026-09-13): `gemini-2.5-
    flash`, `gemini-2.5-flash-lite`, `gemini-3-flash-preview`, `gemini-
    3.1-pro-preview` (what the 404 error itself suggests), `gemini-3.1-
    flash-lite`, `gemini-3.5-flash`, `gemini-3.6/3.7/3.8-flash`, plus
    floating aliases `gemini-flash-latest`/`gemini-pro-latest` (avoid
    per the plan's own model-freeze requirement, IMPLEMENTATION_RESEARCH.md
    S4.7 - a floating alias breaks exact reproducibility across runs).

    **Not changed** - this is a "number that ends up in a result" per
    this session's debugging boundary, and picking a replacement changes
    what "replicating the paper with the pinned model" means (the "-pro"
    vs "-flash" tier is a real capability difference for the ensemble
    completion task, not just a version bump). Needs the user's/
    coordinator's explicit choice of replacement model before the next
    live-run attempt, per IMPLEMENTATION_RESEARCH.md's model-freeze
    requirement (S4.7: model name frozen before any comparison).

## Model deprecation evidence (captured verbatim per Opus advisor - external
## API state is ephemeral, won't be reconstructable later)

21. **`gemini-2.5-pro` deprecated mid-session, 2026-09-13.** Exact error
    text from a real API call attempt (captured automatically by the LLM
    logger wrapper, deviation #12, in
    `runs/scene00069_seed42_author/prompts/prompts_responses.jsonl`):

    ```
    404 NOT_FOUND. {'error': {'code': 404, 'message': 'This model
    models/gemini-2.5-pro is no longer available to new users. Please
    update your code to use models/gemini-3.1-pro-preview for the latest
    features and improvements. We recommend you to use the Interactions
    API.', 'status': 'NOT_FOUND'}}
    ```

    `client.models.list()` (same date) still returns `models/gemini-2.5-
    pro` in the catalog - this is a new-user/new-project access
    restriction, not a full model removal. Google's own error message
    names `models/gemini-3.1-pro-preview` as the migration target.

    **Opus advisor's verdict** (consulted since this affects the plan's
    section 4.7 model-freeze rule): proceed with `gemini-3.1-pro-preview`
    for tonight's Phase 5 smoke run specifically, but this is
    **PROVISIONAL, not frozen** - the freeze rule binds the *scored*
    12-run matrix (plan section 11: freeze "before collecting comparison
    results"), not a run whose only job is closing the Phase 5 gate.
    Ruled out: `gemini-pro-latest` (floating alias, same objection as
    IMPLEMENTATION_RESEARCH.md section 3.3's drift concern), the
    "Nano Banana"/image-gen model variants (no function-calling support,
    needed for `check_collision`), and the flash tier (materially weaker
    capability class than the paper's own "pro" tier choice - a tier
    swap would confound the actual research question, not just the API
    surface, so preview-instability risk was judged the smaller of the
    two risks).

    **This is a live instance of a risk IMPLEMENTATION_RESEARCH.md already
    flagged** (section 3.3: hosted model drift; section 4.7/8: cached
    completions chosen partly because of it) - the model didn't drift,
    it disappeared outright. **Planning implication for the user**: if a
    model can vanish mid-project, the eventual 12-run matrix should be
    collected in as tight a window as practical, with aggressive caching
    as results are produced - a preview-tagged model disappearing halfway
    through would strand the corpus under two different models, which is
    exactly the comparability failure the freeze rule exists to prevent.

    **This substitution needs the user's explicit confirmation before any
    scored/comparison data is collected under it** - flagged prominently
    in the final handoff, not just here.

## Model-choice probes: HARD BLOCKER hit (billing, not code) — stopped before the 3 probes ran

22. **Before running the 3 planned probes (function calling, multimodal,
    YAML-parsing), the first real call to `gemini-3.1-pro-preview`
    failed with `429 RESOURCE_EXHAUSTED`**, not a prompt/capability
    issue: `Quota exceeded ... limit: 0, model: gemini-3.1-pro ...
    GenerateContentInputTokensPerModelPerDay-FreeTier`. This API key/
    project has **zero free-tier quota for any "-pro" tier model** -
    this is an account/billing limitation, unrelated to the prompt,
    the tool-calling setup, or anything in this session's debugging.

    Characterized the actual boundary with a quick 3-model check (used
    the real `LLMCompletion.generate_completion_response()` code path
    and real scene-graph YAML + image slices from tonight's successful
    smoke run at `runs/scene00069_seed42_author/stages/0/` - not
    synthetic test data):
    - `gemini-3.1-pro-preview` -> 429 RESOURCE_EXHAUSTED (0 free-tier quota)
    - `gemini-2.5-flash` -> **SUCCESS** (flash tier has free-tier quota)
    - `gemini-2.5-flash-lite` -> 404 NOT_FOUND (also retired, same as 2.5-pro)

    So: every currently-callable model on this key is flash-tier, and
    flash-tier was **already explicitly ruled out** earlier tonight (see
    deviation #21) for being a weaker capability class that would
    confound the actual research question (ensemble scene-graph
    completion + function-calling + multimodal reasoning is what the
    paper's method depends on). The one model actually chosen for
    research validity (`gemini-3.1-pro-preview`) is not usable without
    enabling billing on this Google AI Studio/Cloud project.

    **Did not proceed with flash-tier as a substitute** - that would
    silently reverse an already-made research-validity decision, not
    something to do unilaterally mid-probing. **Did not run the 3
    planned probes** (function calling / multimodal / YAML-parsing)
    since there is currently no usable pro-tier model to probe.

    **This needs the user's decision, not more debugging**: (a) enable
    billing on the API key's Google AI Studio/Cloud project (the
    straightforward fix, if acceptable), (b) accept flash-tier as a
    deliberate capability-scope change for tonight's smoke gate only,
    (c) supply a different Gemini API key that already has billing
    enabled, or (d) use the OpenRouter fallback key on hand - but that
    was scoped by the user to "cheap vision-capable models" (their
    words), which is the same flash-tier-equivalent capability class
    already ruled out, so it doesn't obviously resolve the underlying
    tension either.

    0 cost incurred: the 429s are rejected before any token generation
    (confirmed no charges appear possible on a request that never
    executes). Total probe calls used: 2 (well under any cap).

## Planning gap surfaced by Opus advisor review (not a bug, a scope/cost
## finding the user should see before scheduling anything)

23. **The plan does not budget compute/API cost for generating the
    ground-truth reference graphs.** Deviation #9 established that each
    scene's "ground truth" / "fully explored reference graph" (used by
    Phase 6's evaluator for GED/precision/recall) is not sourced from
    HM3D's data at all - it's self-generated by running the ASP pipeline
    itself to exhaustive coverage of the scene. That means **each of the
    4 scenes needs its own dedicated exhaustive-coverage run**, almost
    certainly longer than the 120m budget used for the actual scored
    policy runs (a policy stops at 120m; exhaustive coverage of a whole
    apartment-scale scene needs more path length and more LLM queries to
    guarantee full coverage). This is on top of the 12 scored runs in
    plan section 13, and IMPLEMENTATION_PLAN.md / IMPLEMENTATION_RESEARCH.md
    do not mention or budget it anywhere. Real cost implication (API
    spend + wall-clock time) the user should see before scheduling the
    matrix, not just a technical note.

## Mechanical wiring check under gemini-2.5-flash (NOT a gate pass, NOT scored)

24. **Isolated, clearly-labeled check** at `runs/wiring_check_flash_
    NOTSCORED_2026-09-13/` (marker file `NOT_A_GATE_PASS.md` explains
    scope). Purpose: confirm the prompt/tool-calling/parsing wiring
    still works mechanically with *some* model, since it was tuned
    against `gemini-2.5-pro` and might not transfer - NOT a capability
    or research-validity claim about flash-tier, which was already
    correctly ruled out (deviation #21) for scored comparisons.

    **Isolation held**: `pipeline_config.yaml` was backed up, temporarily
    edited (model -> `gemini-2.5-flash`, `BASE_DIRECTORY` -> the isolated
    dir), then restored via a bash `trap ... EXIT` guaranteeing restore
    even on error/kill. Verified restored correctly afterward
    (`LLM_MODEL_NAME: "gemini-2.5-pro"`, `BASE_DIRECTORY` back to
    `scene00069_seed42_author/stages`). `ASP_LLM_LOG_DIR` pointed at the
    isolated `prompts/` dir throughout. Confirmed nothing under
    `runs/scene00069_seed42_author/` was modified during this check.

    **No completion-cache contamination risk found**: grepped the entire
    workspace (author's pinned code, `tools/evaluator/`, `tools/
    llm_logger/`) for any cache-read/reuse mechanism - **none exists
    anywhere yet**. The "shared cached completions across policies"
    described in IMPLEMENTATION_RESEARCH.md S4.7 is planned future
    infrastructure (part of this course project's own proposed Phase 6+
    work), not implemented in the author's current pipeline or anything
    built tonight. So there is no cache-key bug to have *found* - but
    this is a forward-looking design note worth keeping: **when that
    caching layer gets built, the key must include model version**
    (per plan section 14's own "scene, checkpoint, model version, seed"
    spec), or a stale completion from one model could silently get
    reused as if it were another's.

    **Results (mechanical only, not scored)**:
    - **Full pipeline run** (8 parallel LLM workers per
      `MAX_PARALLEL_WORKERS: 8`) immediately hit the free-tier's
      5-requests/minute-per-model rate limit every cycle - 8 concurrent
      workers structurally exceed a 5/minute allowance regardless of
      which model is chosen, so this specific failure mode is a rate-limit/
      concurrency issue, not evidence about flash-tier itself. Also
      surfaced a real limitation of tonight's `_asp_llm_logger` wrapper:
      its `ASP_LLM_MAX_CALLS` cap is **per-process**, not global - each
      of the pipeline's parallel worker processes gets its own
      independent counter (confirmed: multiple `call_index: 1` entries
      logged simultaneously). Worth fixing (e.g. a shared counter file)
      before relying on this cap during any future multi-worker run.
    - **Single direct call** (bypassing the parallel-worker path, calling
      `LLMCompletion.generate_completion_response()` once, serially,
      against real scene-graph YAML + images from tonight's segfault-fix
      run): **function calling confirmed working** - the model made 7
      well-formed, semantically sensible `check_collision` calls (bed,
      nightstand, wardrobe, sofa, coffee table, tv stand, tv - a
      plausible bedroom/living-area layout extension) under the exact
      real `ToolConfig`/`FunctionCallingConfig(mode="VALIDATED")` setup.
      **Multimodal input confirmed working** - real JPEG scene-slice
      images accepted with no image-handling error, and the response
      reasoning was spatially coherent with them.
    - **YAML-parsing question: NOT ANSWERED** - the model's first turn
      took 70.7s (unlimited thinking budget) and produced only function
      calls, no final text yet (still mid-conversation per the code's
      own multi-turn loop design). A retry to let the loop complete hit
      the free tier's **daily** request quota (20/day for
      `gemini-2.5-flash`, separate from the per-minute one) before it
      could finish - now exhausted for today regardless of model choice.
      This is an open question for whoever resumes, not a wiring failure.

    **Gate status unchanged: still 3 of 7.** Nothing here ticks Phase 5's
    gate - items 4-7 remain unmet pending either billing being enabled
    for the real model, or tomorrow's quota reset to finish this check.

## LLM logger cross-process fix (found by tonight's wiring check)

25. **`_asp_llm_logger`'s call cap was per-process, not global** - found
    during the flash-tier wiring check: the real pipeline generates
    completions via a `ProcessPoolExecutor` (`MAX_PARALLEL_WORKERS: 8` in
    `pipeline_config.yaml`), and each worker is a separate OS process that
    re-imports the module fresh with its own in-memory counter. N workers
    therefore each got an independent budget, silently multiplying the
    real cap by the worker count - e.g. `ASP_LLM_MAX_CALLS=60` with 8
    workers could actually allow up to 480 calls before anything stopped.

    Fixed: the counter is now a file
    (`$ASP_LLM_LOG_DIR/_call_counter`) incremented under an `fcntl.flock`
    exclusive lock, so every process sharing one `ASP_LLM_LOG_DIR` shares
    one real budget regardless of how many workers are spawned. Verified
    locally with 4 real concurrent subprocesses each attempting 5 calls
    against a cap of 12: exactly 12 unique, sequential, non-duplicate
    call indices granted (1-12) and the remaining 8 correctly refused -
    no race let two processes both grab the same number. Deployed via
    `tools/llm_logger/install.sh` (source of truth at
    `tools/llm_logger/_asp_llm_logger.py`, same durable-install pattern
    as deviation #18).

    This matters for any future run that actually uses parallel workers -
    tonight's smoke-test and wiring-check calls were mostly sequential/
    single-worker debugging calls, so the old per-process cap happened
    not to bite, but it would have on a real multi-worker run.

## End-of-night cleanup

26. **Stopped the idle ROS/mapping session** that had been left running
    since the segfault fix was verified (clio_node, vs_graphs, nvblox_node,
    task_server) - it was consuming ~30% CPU continuously and 5.5GB GPU
    memory for no benefit while blocked on the model/billing decision,
    on a machine other people also use. Restarting is a single command
    (`roslaunch clio_ros realsense.launch start_visualizer:=false
    start_rviz:=false`, same as tonight) once a model is confirmed - no
    state was lost, nothing here needs redoing.

## OpenRouter/DeepSeek backend added (user's explicit decision)

27. **Added an OpenRouter backend as an alternative to Google Gemini**,
    per the user's direct instruction after reviewing the billing/model
    findings in #20-22 (tried `gemini-3.8-flash` first per an initial
    instruction - real model, but 4/4 real-workload attempts hit `503
    UNAVAILABLE` even though trivial text-only calls succeeded; then
    `gemini-2.5-flash` hit its **daily** free-tier quota, 20 requests/day,
    confirming this key is entirely on the free tier and no flash model
    would have enough quota for even one real query - so a provider
    change was the only path forward tonight without billing).

    Model: `deepseek/deepseek-v4.1-flash` - confirmed via OpenRouter's
    `/models` endpoint to be the cheapest non-experimental DeepSeek model
    with vision input and `tools`/`tool_choice` support (text+image
    input, $0.00000015/prompt token, 1M context), matching the user's
    explicit "cheap models... support visual input" requirement.

    **Implementation, kept outside the pinned checkout** (same pattern as
    the LLM logger, deviation #12/18): `tools/llm_openrouter/
    _asp_openrouter_shim.py` translates between google.genai's Content/
    Part objects (which llm_completion.py's tool-calling loop is written
    against) and OpenRouter's OpenAI-compatible chat-completions format,
    then fabricates a response object that duck-types as a google.genai
    response (`.text`, `.candidates[0].content.parts[].function_call`) so
    llm_completion.py needs zero changes and doesn't know a swap
    happened. `_asp_llm_logger.py` (deviation #12) gained an
    `ASP_LLM_PROVIDER` switch ("google" default, "openrouter" to route
    through the shim) at the same single interception point it already
    used for logging - logging and the hard-call-cap apply identically
    regardless of provider.

    Three real bugs found and fixed while building this against the
    actual prompt/tools/images (not synthetic toy data):
    - `_FakeContent` never set a `.role` attribute, so the "is this a
      real Content object" detection silently misfired on the SECOND
      turn of any tool-calling loop (found by dumping the actual history
      structure at the failure point - `role=<none>` gave it away).
    - DeepSeek v4.1-flash defaults to "high" reasoning effort, which
      burned an entire 8000-token completion budget on chain-of-thought
      alone for this task (`finish_reason: "length"`, zero actual
      output) - fixed by explicitly requesting `reasoning: {effort:
      "low"}` (also cuts cost, since reasoning tokens bill the same as
      real output) and raising the ceiling to 16000 as margin.
    - OpenRouter intermittently returns `finish_reason: "error"` with
      null content for this model/workload (observed 2 of 6 real
      attempts) - looks like a transient provider-side issue, not
      request-shape-specific (retrying the identical payload succeeded).
      Added automatic retry (3 attempts) inside the shim itself, since
      manual retries won't scale to a real multi-query run; if all
      retries are exhausted, returns an empty response rather than
      crashing the pipeline, so it's handled the same way an ordinary
      empty completion would be.

    **Verified end-to-end against the real prompt/tools/real scene
    images** (not synthetic): function calling confirmed (real
    `check_collision` tool calls, correct retry-on-collision behavior
    matching the prompt's own IoU>0 rule), multimodal input confirmed
    (real JPEG scene slices accepted), and the output-parsing question
    left open by the earlier flash wiring check (#24) is now **answered:
    YES** - a full successful run produced exactly one fenced YAML block
    that parsed cleanly (11 new nodes, 11 new edges).

    To use: set `ASP_LLM_PROVIDER=openrouter` and source
    `.openrouter_credentials` before launching `exploration_pipeline.py`,
    alongside the usual `ASP_LLM_LOG_DIR`/`ASP_LLM_MAX_CALLS`.
    `pipeline_config.yaml`'s `LLM_MODEL_NAME` is set to
    `"openrouter:deepseek/deepseek-v4.1-flash"` for manifest clarity, but
    is functionally ignored by the shim (OpenRouter has no use for a
    Gemini model string) - the actual model is
    `tools/llm_openrouter/_asp_openrouter_shim.py`'s `OPENROUTER_MODEL`
    constant (overridable via `ASP_OPENROUTER_MODEL`).

    **Research-validity note carried forward from #20-22**: this is
    still a capability-tier substitution away from the paper's own
    "pro"-class Gemini model, now compounded by a full provider change
    (different model family entirely). Fine for closing the Phase 5
    mechanical gate and for further infrastructure work, but should not
    be treated as equivalent to the frozen model for any actually scored
    comparison run without the user's explicit confirmation at that
    point too.

## Shim unit tests + a real bug they caught (per Opus advisor: "it's now
## load-bearing, unit-test it")

28. **Wrote unit tests for `_asp_openrouter_shim.py`** at
    `tools/llm_openrouter/tests/test_shim.py` (8 tests, mock Content/Part
    objects duck-typing google.genai's shapes, no real API calls). Caught
    a real bug immediately: `_translate_to_openai_messages`'s tool-call
    ID assignment incremented the same counter for both function_calls
    AND function_responses, so a single turn with N function_calls
    followed by a turn with N function_responses produced completely
    non-matching ids (e.g. calls get call_1..call_6, but by the time the
    response turn is reached the counter has kept going and responses
    get call_7..call_12 - looked up against a lookup table that only had
    entries for indices 0-5, always missing, always falling through to a
    fresh unmatched id). This affected every real multi-object turn
    tonight (the successful 10-object placement run included) - it
    happened not to break anything because DeepSeek's API is apparently
    lenient about tool_call_id correctness (doesn't reject mismatched
    ids the way OpenAI's own API would), but it was silently wrong the
    whole time and would be a real risk switching to a stricter provider
    later. Fixed with a FIFO queue: each function_call enqueues its id,
    each function_response dequeues the next pending id in arrival order
    (matches how llm_completion.py's own loop always sends responses
    back in the same order the calls were made). Verified: all 8 tests
    pass, including one specifically constructed to catch this exact
    class of mismatch (asserts a response turn's tool_call_id equals the
    matching call's id when the full history is reprocessed with the
    response turn appended, mirroring how the real Chat object re-sends
    full curated history on every call).

## Phase 5 first-run success gate: PASSED

29. **All 7 gate items verified for real, scene 00069/seed 42/official
    ASP policy, LLM backend = OpenRouter/deepseek-v4.1-flash.** Relaunched
    Terminal 1 (roslaunch clio_ros realsense.launch, headless flags) and
    Terminal 2 (exploration_pipeline.py with ASP_LLM_PROVIDER=openrouter,
    ASP_LLM_MAX_CALLS=150) against the already-fixed environment (segfault
    fix from #17/#19, EGL fix from #11, OpenRouter shim from #27). No new
    environment bugs hit this time - everything needed was already fixed.

    Verified concretely, not just assumed:
    1. ROS starts without crash - `clio_node` alive throughout (checked
       repeatedly during the run), zero node deaths in roslaunch.log.
    2. Habitat RGB-D/pose - confirmed via real scene-slice JPEGs generated
       and consumed by the LLM calls.
    3. Non-empty scene graph - `stages/0/habitat_scene_graph_original_
       graph{0,1}.yaml`: 24 nodes, 22 edges.
    4. 8-sample LLM query completed - 34 successful OpenRouter calls (0
       errors reaching the wrapper level - the shim's internal retry
       logic from #27 absorbed transient provider errors transparently),
       across 8 parallel worker processes, correctly sharing one global
       call-index sequence (cross-process counter fix from #25 confirmed
       working under real parallel load, not just the synthetic test).
    5. Viewpoint selected and sent to planner - `stages/0/pose_log.json`:
       10 sampled candidate poses -> 5 filtered -> 1 final pose selected
       (best_ig=3.68).
    6. No uncaptured exception - zero "Traceback" occurrences in
       exploration_pipeline.log.
    7. Replayable from artifacts - `runs/scene00069_seed42_author/
       config/` snapshot was STALE (from an earlier segfault-debugging
       session, still showed `gemini-2.5-pro`) - refreshed with the
       actual pipeline_config.yaml/realsense.launch/commit hash used for
       this run, plus a `run_manifest.txt` recording the exact
       ASP_LLM_PROVIDER/ASP_OPENROUTER_MODEL/ASP_LLM_MAX_CALLS env vars
       (not captured by the yaml/launch files themselves, but essential
       for replay).

    Run stopped cleanly after the gate passed (pkill on exploration_
    pipeline.py, roslaunch, and the ROS node processes) - this was a
    smoke test of stage 0 only, not the full 120m budget or the scored
    matrix. Total cost: well under $1 (34 cheap DeepSeek calls).

    **Phase 5 of IMPLEMENTATION_PLAN.md is complete.** Next step per the
    plan is Phase 6: validate the already-built independent evaluator
    (`tools/evaluator/`, deviation #13) against this real run's output
    (`stages/0/habitat_scene_graph_original_graph0.yaml` as a first data
    point) instead of only the synthetic fixtures it's been tested
    against so far - not started in this session, left for the next one.

## Phase 6: evaluator validated against real data

30. **Ran `tools/evaluator/` against the real Phase 5 output** (stage 0,
    `habitat_scene_graph_original_graph{0,1}.yaml` plus the 8 individual
    K=8 completions `habitat_scene_graph_new_graph_{0-7}.yaml`) instead
    of only the synthetic fixtures it was built against. All 10 real
    files load without error via `graph_io.load_eval_graph`. Ran the
    full `evaluate_run.py` CLI using graph0 as a self-comparison
    reference: F1/precision/recall = 1.0 (graph0 matches itself and
    graph1 shares its one detected object), GED = 12.5 normalized 0.43
    (graph1 has 6 rooms vs graph0's 13 - a real, sensible non-zero
    difference, not a trivial/degenerate result). This is not yet a real
    scored evaluation (no ground-truth reference graph exists - that
    still needs the exhaustive-coverage run from deviation #23) but
    confirms the evaluator's mechanics are sound against real pipeline
    output, not just hand-built fixtures.

## Provenance check + a major cost finding (per Opus advisor review)

31. **Confirmed the Phase 5 gate-passing run (deviation #29) was
    contaminated by the mid-run shim fix (deviation #28).** Cross-
    referenced call timestamps in `prompts_responses.jsonl` against the
    shim fix deployment time (2026-09-13 05:09:52 UTC, from file mtime):
    calls 1-23 (05:06:51-05:09:40 UTC) ran under the buggy tool_call_id
    logic, calls 24-36 (05:09:56 onward) ran under the fixed version -
    the deployment landed mid-run. DeepSeek tolerated the mismatched ids
    throughout (no errors), so the gate still passed mechanically, but
    roughly two-thirds of that run's calls have technically-incorrect
    request/response correlation. Re-running Phase 5's stage-0 smoke
    test cleanly (cost: well under $1) rather than trusting this mixed
    baseline.

32. **`exploration/scripts/frontier_baseline.py` is a fully independent,
    LLM-free exploration policy** - confirmed by reading it directly: no
    `google.genai`/`llm_completion` import, no API key reference
    anywhere, uses its own `frontier_config.yaml` (not
    `pipeline_config.yaml`). Its state machine has a `FINISHED` state
    reached specifically when "No more frontiers found" - i.e. it
    terminates on genuine exhaustive coverage of the scene, not a fixed
    path-budget cutoff.

    This directly solves deviation #23 (the plan's unbudgeted cost for
    generating each scene's ground-truth reference graph): running this
    script to its natural FINISHED state, rather than the LLM-based
    exploration policy, produces exactly the kind of "fully explored
    reference graph" the evaluator needs (deviation #9's finding: ground
    truth = self-generated via exhaustive pipeline coverage, not sourced
    from HM3D data) - **at zero API cost**, since it never touches
    Gemini/OpenRouter at all. This is also methodologically more correct
    than using an LLM-based exploration run for ground truth: the LLM
    step predicts *unobserved* structure, which is precisely what a
    ground-truth reference should not contain.

    Practical implication: the 4 reference-graph generation runs (one
    per scene) can run unattended on tyrone with zero LLM API spend,
    fully in parallel with any OpenRouter-dependent work, since they
    don't compete for the same rate limits or budget at all. Should be
    scheduled early rather than treated as a blocking cost concern.

## Clean Phase 5 re-run attempted; hit a worker-pool crash (not yet root-caused)

33. **`frontier_config.yaml` had the same stale author paths as
    `pipeline_config.yaml` originally did** - `SCENE_DATASET_CONFIG`
    pointed at `hm3d_annotated_basis` (only 221 annotated scenes, doesn't
    include 00069, same issue as deviation #9) and `SCENE_ID`/
    `BASE_DIRECTORY`/`MAPPING_DIRECTORY` used the author's original
    `/home/apple/Work/...` paths. Fixed the same way: plain
    `hm3d_basis.scene_dataset_config.json`, `/workspace/...` paths,
    `BASE_DIRECTORY` -> `runs/scene00069_frontier_reference/stages`,
    `MAPPING_DIRECTORY` -> a separate `realsense_frontier` output dir (via
    `roslaunch ... dataset_name:=realsense_frontier`) so a future
    frontier_baseline.py run doesn't collide with the LLM-policy run's
    own Clio/Hydra output.

34. **Clean re-run of Phase 5 stage 0 (new run dir
    `runs/scene00069_seed42_v2/`, fresh `ASP_LLM_LOG_DIR`, so every call
    is guaranteed post-shim-fix by construction) made real progress but
    did not reach the gate**: LLM calls proceeded normally (48 calls
    logged, matching the previous run's pace), the DSG conversion and
    per-completion YAML/scene-slice outputs were all produced correctly
    (`graph{0,1}_dsg.json`, `habitat_scene_graph_original_graph{0,1}.yaml`,
    `node_mapping_graph{0,1}.yaml`, all 8 `scene_slices_N/` dirs) - then
    the pipeline log shows:
    ```
    [ERROR] Error during planning: 'NoneType' object is not iterable. Retrying...
    ERROR: A parallel job failed: A process in the process pool was terminated abruptly while the future was running or pending.
    Starting uncertainty calculation to select next target...
    [INFO] Shutdown requested, stopping any active rosbag recording...
    [INFO] Pipeline shutdown.
    ```
    i.e. a `ProcessPoolExecutor` worker died mid-task during the
    viewpoint/uncertainty-scoring stage (after the LLM completions
    finished, no more API calls involved), the code's own retry for the
    planning error didn't have a live worker pool to retry into, and the
    whole pipeline shut down before `pose_log.json`/`path_log.json` were
    written. **No `pose_log.json` this run - gate items 5 (viewpoint
    selected) and 7 (fully replayable) not met.**

    **Not root-caused.** Checked and ruled out the obvious cause: no OOM
    kills in `dmesg`, 108GB memory available at the time. This session
    also experienced severe, unexplained SSH connectivity instability to
    tyrone throughout (dozens of `Connection refused`/`timed out` errors
    interspersed with working connections, confirmed present from a
    completely separate terminal too, so not purely a client-side
    artifact) - possible but unconfirmed that whatever is causing that
    also disrupted the container's own outbound network calls or process
    scheduling around the same time. This is exactly the class of
    "pinned algorithm/multiprocessing code" issue that should be
    stop-and-report rather than patched blind, per this session's
    debugging boundaries - especially since the previous otherwise-
    identical run (deviation #29) did not hit this failure, suggesting
    it's likely non-deterministic/environmental rather than a
    deterministic bug in `execute_planning`'s multiprocessing code.

    **Not attempted this session** (ran out of time fighting connectivity,
    not a technical blocker): frontier_baseline.py reference-graph
    generation for scene 00069 (config now fixed, ready to run), scoring
    the (still-incomplete) clean run against a reference graph once one
    exists, and the 25m-checkpoint instrumented cost/timing run. All
    three remain queued.

## Local offline-track fixes (Mac side, while tyrone connectivity was down)

35. **Fixed a real bug in `tools/asp_offline/validator.py`** (local Mac
    checkout, not tyrone): `fail()` referenced an undefined `reference_graph`
    name, causing a `NameError` on the two test cases that actually hit
    that code path (`test_forbidden_new_structure_is_removed`,
    `test_invalid_prediction_is_removed_without_losing_observed_graph`) -
    contradicting an earlier claim that "ten tests pass." Fixed correctly
    per the integrity constraint IMPLEMENTATION_RESEARCH.md section 4.1
    requires: `validate_completion`/`validate_ensemble` now take no
    reference-graph parameter at all (removed the broken reference
    comparison from the decision path entirely, `reference_match` always
    None from there). Added a new, explicitly-separate
    `label_against_reference(completion, issues, reference_graph)`
    function for post-hoc-only labeling, called nowhere from the decision
    path. Added two tests: one asserting via `inspect.signature` that
    neither validation entry point ever gains a reference/ground-truth-
    shaped parameter (fails immediately if anyone adds one back), and one
    confirming `label_against_reference` doesn't mutate the original
    issues or change the accept/reject outcome. Also added an explicit
    test for the leave-one-scene-out fold discipline (already correct by
    construction in `calibration.py`, but per outside review, worth
    testing by name: a held-out scene's own samples must never influence
    its own calibrator).

36. **Fixed `score_viewpoint`'s `lambda_distance` default**: was `1.0`
    (an invented placeholder), should be `0.2` - the author's actual
    `MOVE_COST_LAMBDA` value from `pipeline_config.yaml` (verified once
    tyrone connectivity briefly returned). `lambda_room=1.0` was already
    correct (matches `UNCERTAINTY_ROOM_WEIGHT`). Per outside review's
    "read them from the author code; do not pick them" - this was
    exactly the kind of silent-invention risk that guidance was for.

All 13 `tools/tests/test_asp_offline.py` tests pass after these fixes
(`PYTHONPATH=tools python3 -m unittest tools.tests.test_asp_offline -v`,
run locally on the Mac, no tyrone dependency).

## Root-caused the ProcessPoolExecutor crash from deviation #34 (diagnosis only, not patched - inside pinned algorithm code)

37. **Found the real bug behind deviation #34's crash**, in
    `exploration/scripts/llm_completion.py`'s `LLMManager.complete_scene_
    graph()` (~line 438-452), inside the pinned checkout:

    ```python
    with ProcessPoolExecutor(max_workers=max_workers, mp_context=mp.get_context("spawn")) as executor:
        futures = [...]
        for future in as_completed(futures):
            try:
                result_path = future.result()
                if result_path:
                    all_generated_files.append(result_path)
            except Exception as e:
                print(f"ERROR: A parallel job failed: {e}")
                return None          # <-- abandons every other pending/completed future
    return all_generated_files
    ```

    If **any single** one of the 8 parallel ensemble-member worker
    processes fails - raises inside `future.result()`, or the pool itself
    reports `BrokenProcessPool` because a worker died as an OS process
    rather than raising a catchable exception - this handler immediately
    `return None`s, discarding every other worker's results, including
    ones that may have already completed successfully. The caller (later
    in `exploration_pipeline.py`, during the planning/uncertainty stage)
    does not null-check this return value before iterating over it,
    producing exactly the observed
    `[ERROR] Error during planning: 'NoneType' object is not iterable`.

    **Root cause of why a worker died in the first place is still
    open** - could be genuinely environmental (this session's
    unexplained connectivity/system flakiness disrupting a subprocess),
    or a rarer real bug inside `_run_single_ensemble_member`/
    `LLMCompletion` that only manifests occasionally. Did not attempt to
    reproduce further or patch - this is inside the pinned checkout's own
    control flow, and the fix (e.g., collecting partial results instead
    of discarding them, or retrying the specific failed ensemble member
    instead of aborting the whole batch) is a real behavior change to
    author code, not a build/config deviation, so it needs the user's
    explicit sign-off per tonight's standing rule, not a blind patch.

    **Practical mitigation if this keeps recurring without a code fix**:
    any given run has a `1 - (1-p)^N` chance of hitting this where p is
    the single-worker failure rate and N is the number of parallel
    workers per query (8) - so it may be worth simply retrying the whole
    stage/query on this specific failure signature rather than treating
    every occurrence as a fresh investigation, until the actual root
    cause (or a sanctioned code fix) is confirmed.

## Frontier reference-graph generation actually launched

38. **Two real launch bugs found and fixed while getting `frontier_baseline.py`
    running**: (a) `runs/scene00069_frontier_reference/{logs,stages}/`
    were never created on disk, so the roslaunch log redirect silently
    failed and Terminal 1 never actually started in earlier attempts
    (fixed: created the directories); (b) `dataset_name:=realsense_frontier`
    is not just an output-path label - `realsense.launch` uses it to look
    up `mapping/clio/clio_ros/config/<dataset_name>/pipeline.yaml`, which
    only existed for `realsense`, causing an `RLException: file does not
    exist` that killed roslaunch immediately (fixed: copied
    `config/realsense/` to `config/realsense_frontier/`, a plain config
    duplication, not a pinned-algorithm-code change - same three files,
    same content, just addressable under the frontier-specific dataset
    name so its mapping output doesn't collide with any LLM-policy run's
    output directory).

    With both fixed: Terminal 1 (roslaunch, `dataset_name:=realsense_frontier`)
    is up, `clio_node` alive. Terminal 2 (`frontier_baseline.py`, via the
    same Xvfb+xdotool 's' keypress pattern the LLM pipeline needs) is
    running (confirmed via `ps aux`, actively using CPU). Left running to
    reach its natural `FINISHED` state ("no more frontiers found") - zero
    API cost, no tight time budget, just needs patience. Check
    `runs/scene00069_frontier_reference/logs/frontier_baseline.log` and
    `stages/` for progress.

## First real ground-truth reference graph generated (major milestone)

39. **Scene 00069's ground-truth reference graph is done.**
    `frontier_baseline.py` reached genuine `FINISHED` state ("Exploration
    complete. No more frontiers found. Stopping.") after 26 stages.
    Confirmed genuine completion by reading the source directly (not just
    inferring from a log message that could have been ambiguous):
    `execute_planning()` sets `self.state = "FINISHED"` immediately after
    `frontier_planner.plan()` returns `None`, which only happens when no
    reachable frontier target remains - this is real exhaustive coverage,
    not a crash or premature stop (the sequence of A*/mid-path warnings
    right before it just reflects the planner exhausting hard-to-reach
    candidates before correctly concluding none are left).

    **Real numbers, zero API cost:**
    - Total duration: 3166.28 seconds (52.8 minutes)
    - Total path length: 96.53 meters
    - 26 exploration stages
    - Final reference graph (after converting `graph{0,1}_dsg.json` to
      the evaluator's YAML format via the author's own
      `f1_score_plot.py:convert_dsg_to_yaml`): **67 objects, 9 rooms**

    Saved at `runs/scene00069_frontier_reference/stages/25/
    habitat_scene_graph_original_graph{0,1}.yaml`.

    **Sizing implication for the other 3 scenes' reference graphs**: if
    comparable in complexity, budget roughly 50-60 minutes wall-clock
    each, zero API cost, can run sequentially or in parallel on tyrone
    without touching any LLM rate limit or budget.

    **Still needed**: a clean, complete LLM-policy run to actually score
    against this reference (the clean re-run in `scene00069_seed42_v2`
    crashed during viewpoint scoring per deviation #34/#37 before
    producing scoreable stage output).

## OpenRouter provider-routing bug found and fixed

40. **Real (image + tool-schema) OpenRouter calls were failing 100% of the
    time under the pipeline's actual `ProcessPoolExecutor` concurrent
    load, silently.** Symptom: every worker's every call returned
    `finish_reason: "error"` after burning 300-2700 reasoning tokens
    (billed `cost: 0`, so no money lost, but the pipeline's
    `_openrouter_generate_content_once` retry wrapper (added earlier,
    deviation context around the reasoning-effort fix) was exhausting
    all 3 attempts and gracefully falling back to an empty completion
    every single time - not a crash, but a silently worthless run (the
    LLM never actually contributed a single real completion the entire
    time, since every call degraded to empty text).

    **Diagnosis**: reproduced the exact payload shape (multi-image +
    tool schema, ~10k prompt tokens) directly against OpenRouter outside
    the pipeline. A single ad-hoc request landed on the "Together"
    backing provider and succeeded every time (multiple repro attempts,
    including under 9-way concurrent load via ThreadPoolExecutor - 9/9
    succeeded). The very first, unrelated plain-text/no-tools smoke test
    happened to land on a different provider ("Morph") and also
    succeeded, but no image+tools reproduction ever landed there to
    confirm/deny it as the culprit - OpenRouter's automatic routing is
    the suspect, not the model or the account.

    **Fix** (`tools/llm_openrouter/_asp_openrouter_shim.py`,
    `_openrouter_generate_content_once`): added a `provider` field to
    the request payload - `{"order": ["Together"], "allow_fallbacks":
    true, "require_parameters": true}`. `require_parameters: true` is
    OpenRouter's documented mechanism for excluding providers that don't
    actually support every field used in the request (tools, here) from
    routing consideration, which is the generically-correct fix for this
    class of bug; pinning `order` to the provider that's been reliable
    in testing is the pragmatic addition on top. Configurable via
    `ASP_OPENROUTER_PROVIDER_ORDER` env var (comma-separated) if
    "Together" ever degrades. Also added `provider=...` to the existing
    empty-response stderr log line so any recurrence is immediately
    diagnosable from the pipeline log alone, without needing to
    reproduce externally again.

    Verified: shim's 8 unit tests still pass after the change
    (`tools/llm_openrouter/tests/test_shim.py`); a 9-worker concurrent
    reproduction of the real payload shape got 9/9 `finish_reason:
    "tool_calls"` with the fix applied, versus the pipeline's observed
    0/N success rate before it. Relaunched the clean LLM-policy run
    (`scene00069_seed42_v2`, Terminal 1/2 v3) with the fix in place.

    Logging-only/infrastructure change to the OpenRouter translation
    shim (not pinned algorithm code) - within the established "fix
    plumbing freely" boundary.

## Exact root cause of the ProcessPoolExecutor crash found (pinned code, needs sign-off)

41. **Fully diagnosed DEVIATIONS #37's `'NoneType' object is not iterable'`
    crash down to the exact line.** `exploration/scripts/llm_completion.py`,
    `LLMCompletion.parse_response()` (~line 350-352):

    ```python
    match = re.search(r"```(yaml\n)?(.*)```", response_text, re.DOTALL)
    clean_yaml_text = match.group(2).strip()
    ```

    No null-check on `match`. When a worker's final LLM response text does
    not contain a fenced code block matching this exact pattern, `match`
    is `None` and `.group(2)` raises `AttributeError: 'NoneType' object
    has no attribute 'group'` inside that worker process. This propagates
    up through `future.result()` in `LLMManager.complete_scene_graph()`
    (~line 445-450), whose `except Exception as e: print(...); return
    None` discards the results of ALL OTHER ensemble members in the
    batch (not just the one that failed to parse) and returns `None` -
    which the caller then tries to iterate, producing the
    `'NoneType' object is not iterable'` error seen upstream in
    `exploration_pipeline.py`'s planning loop. Confirmed via the exact
    joblib/pool error text captured earlier: `ERROR: A parallel job
    failed: 'NoneType' object has no attribute 'group'`.

    **Observed behavior on `scene00069_seed42_v2` (v3 run, with the
    OpenRouter provider-routing fix from deviation #40 already applied,
    so this is NOT the same failure mode)**: after the OpenRouter fix,
    the LLM call success rate is high (94 real calls, only 1 isolated
    `finish_reason=error`) - but this regex-based parse failure hit 4
    times over the run, the last two only ~40 seconds apart, each time
    forcing the pipeline's own outer retry to re-run the entire
    stage-2 planning step (re-spawning a fresh 8-worker pool, re-billing
    real LLM calls) from scratch rather than just re-trying or skipping
    the one ensemble member whose text didn't parse. Stages 0 and 1 both
    completed with real output before this started recurring at stage 2;
    the run was consuming call budget (94/200) without producing further
    stage output, so it was stopped (killed only the
    `exploration_pipeline.py` PID, left Terminal 1's ROS/mapping session
    running in case of a resume) rather than let it keep burning budget
    in place.

    **Why this is a STOP-AND-REPORT item, not a plumbing fix**: the fix
    touches pinned algorithm code (`llm_completion.py`) and changes
    failure-handling behavior that affects which/how many ensemble
    members contribute to a scene graph completion - a research-validity-
    relevant behavior, not just infrastructure. Plausible fixes range
    from conservative (catch the parse failure per-worker and treat only
    that one ensemble member as a dropped/failed proposal, matching how
    the offline validator already treats a whole-completion parse
    failure - see `tools/asp_offline/validator.py`'s
    `test_parse_failure_is_rejected_and_ensemble_falls_back`) to more
    invasive (loosen the regex to tolerate more response formats). Also
    worth noting: this may be genuinely more frequent under DeepSeek than
    it would be under the original Gemini backend, since different model
    families have different fence-formatting habits under the "low"
    reasoning effort setting used here - another data point for the
    "reimplementation with a substitute backend, not a byte-for-byte
    replication" framing already flagged in the plan's progress log.

    Consulting the Opus advisor per the user's standing instruction
    before deciding whether/how to patch this.

## Patched the parse_response() crash (pinned code, Opus-advised)

42. **Patched `exploration/scripts/llm_completion.py` after consulting the
    Opus advisor on deviation #41's diagnosis.** The advisor's
    recommendation (summarized): patch it now, scoped to the crash path
    only (null-check `match` in `parse_response()`, drop only the one
    unparseable ensemble member rather than crashing the whole batch,
    but preserve the original all-members-failed behavior so the
    pipeline's outer retry loop still fires); log dropped-member counts
    as a research-relevant number (effective ensemble size); do NOT
    widen the regex itself (that could change results on inputs that
    already parsed correctly, which is a real behavioral deviation,
    unlike a pure crash-path guard); push any input-format tolerance
    improvements into the OpenRouter shim (outside the pin) rather than
    into pinned code; proceed without waiting on the human user, since
    it's a few lines against a commit-pinned checkout and fully
    revertable via `git diff`/the saved patch; log it thoroughly.

    **Exact change** (full diff saved at
    `runs/environment/llm_completion_parse_failure_fix.patch`; unpatched
    original preserved at
    `runs/environment/llm_completion.py.orig_f1ea141` for a one-command
    revert): three functions touched, all in `LLMManager`/`LLMCompletion`:
    - `parse_response()`: if the fenced-block regex doesn't match,
      write the raw response text to
      `<stage_dir>/unparsed_responses/<name>.unparsed.txt` for audit,
      print a warning, and `return False` instead of raising
      `AttributeError`. Every branch where the regex DOES match is
      byte-for-byte unchanged, just now ends with an explicit
      `return True`.
    - `_run_single_ensemble_member()`: checks `parse_response()`'s
      return value; on failure, skips `create_scene_slices()` (which
      would otherwise crash on a file that was never written) and
      returns `None` for that one ensemble member instead of a filepath.
    - `complete_scene_graph()`: `future.result()` already returns
      `None` gracefully now instead of raising, so `if result_path:`
      already drops it. Added: a count/print of how many of the
      submitted futures were dropped, and an explicit guard restoring
      the ORIGINAL behavior when every member of the batch failed
      (`if not all_generated_files: return None`) - so a total-batch
      failure still triggers the pipeline's own outer retry exactly as
      before; only a PARTIAL failure now degrades gracefully instead of
      destroying the whole batch.

    Verified: `ast.parse()` syntax-checks clean in the container's
    Python. Deployed to both the host checkout and the running
    container's bind-mounted copy (same file, `/workspace` is the bind
    mount, so this is really one file, copied via `docker cp` as a
    belt-and-suspenders confirmation).

    **Not done** (deliberately, per the advisor): did not widen the
    regex itself, and did not add proactive fence-format retry logic
    to the OpenRouter shim yet (the advisor's optional "(c) in the
    shim" suggestion) - the crash-path fix alone is sufficient to
    unblock the run; the shim-side optimization is a nice-to-have for
    reducing HOW OFTEN members get dropped, not a requirement for
    correctness, and was skipped to avoid scope creep under time
    pressure.

    **Disclosure for any report**: this is a deviation from the
    author's exact pinned implementation - a robustness fix to the
    author's own harness code (not a change to ASP's algorithm/method),
    made necessary because the substitute LLM backend (DeepSeek via
    OpenRouter, see #40) appears to hit a code-fence-formatting edge
    case the author's regex didn't anticipate. Effective-ensemble-size
    impact should be measured and reported once enough drop-count data
    exists (see the new `[complete_scene_graph] N/M ensemble members
    were dropped` log lines).

    Resuming the `scene00069_seed42_v2` run (stage 2 onward) with this
    patch in place.

## Root cause of session's SSH instability found: tyrone is rebooting periodically

43. **tyrone rebooted at 2026-09-13 15:32 UTC, killing the `asp-noetic`
    container mid-run** (this is what ended the `scene00069_seed42_v4`
    run's `exploration_pipeline.py`, not a pipeline bug - container exit
    code 137/SIGKILL, `OOMKilled=false`, consistent with the whole host
    going down). `last reboot` shows this was the **4th reboot in
    roughly 2 days** (Sep 11 21:35, Sep 11 22:36, Sep 12 08:34, Sep 13
    15:32) - this is almost certainly the actual explanation for the
    "severely unstable SSH connectivity, no obvious cause" problem noted
    earlier in this session (system health checks at the time - load,
    free memory - looked fine because they were checking a HEALTHY,
    freshly-booted machine each time, not catching an in-progress
    reboot). `dmesg`/kernel reboot-cause logs aren't readable with this
    account's permissions, so the actual trigger is still unknown -
    flagged to the user directly, since it's outside anything fixable
    from this session (could be scheduled maintenance, auto-updates, or
    something else specific to how tyrone is administered).

    **Recovery**: `docker/run.sh`'s existing `docker start` fallback
    (for "container exists but stopped") worked cleanly - the
    bind-mounted `/workspace` (including the `environments/` venv, so
    all prior pip installs/patches, e.g. the OpenRouter shim and the
    llm_completion.py patch from #42, survived untouched) and GPU
    passthrough (`nvidia-smi` confirmed working) both came back with no
    reinstallation needed. ROS processes do NOT survive a container
    restart, so a completely fresh Terminal 1 + Terminal 2 launch was
    needed - but this is actually simpler than the manual PID-hunting
    cleanup used earlier in this session for ROS session conflicts,
    since a full container restart guarantees zero zombie/orphan
    processes left over.

    **Practical implication going forward**: any run on tyrone can be
    silently killed by a host reboot at any time, unrelated to anything
    in the pipeline or this project's code. A monitor loop watching a
    long run should treat a sudden, total loss of SSH reachability
    (not just a `ps aux` miss) as a signal to check `docker ps -a`/
    `uptime` for a reboot before assuming a pipeline-level crash.

## Loosened the OpenRouter provider pin (single provider under sustained load)

44. **Revised deviation #40's provider pin.** Hard-pinning to a single
    backing provider (`"order": ["Together"]`) traded the original bug
    (an incapable provider silently mishandling image+tools) for a new
    one under real sustained load: the `scene00069_seed42_v4` "v5"
    attempt (post-reboot relaunch) accumulated 19 `finish_reason=error`
    empty responses and 4 whole-batch `Error during planning` failures
    over ~15 minutes, still stuck on stage 0. Confirmed this was NOT
    general network flakiness (a leftover concern from deviation #43's
    reboot): a direct `curl https://openrouter.ai/api/v1/models` from
    inside the container, run WHILE the pin was still active and errors
    were ongoing, returned `200 OK in 0.136s` - fast and healthy.
    Concentrating every one of the pipeline's 8-9 concurrent workers'
    traffic onto one named provider, repeated across many planning
    cycles, is a plausible way to hit that provider's own per-key
    rate/capacity limits that a load-balanced pool wouldn't.

    **Fix**: dropped the hard `"order": ["Together"]` /
    `"allow_fallbacks"` pin from `_asp_openrouter_shim.py`'s
    `_openrouter_generate_content_once`. Kept `"require_parameters":
    true` - this alone is OpenRouter's documented fix for the ORIGINAL
    bug (excludes providers that don't support every field in the
    payload, i.e. tools), and doesn't depend on which specific capable
    provider ends up serving a given request. `ASP_OPENROUTER_
    PROVIDER_ORDER` env var still works if a hard pin is ever wanted
    again (e.g. if a different specific provider is later found to be
    the true culprit), just no longer defaults to one.

    Verified: shim's 8 unit tests still pass. Relaunched the
    `scene00069_seed42_v4` run (killed the "v5" attempt, launched "v6")
    with this change; only stage 0 existed at kill time, so minimal
    progress lost. Documenting the reasoning trail (pin → single-
    provider overload → unpin) in full rather than silently swapping,
    since a future session hitting the ORIGINAL bug again should
    understand why the fix isn't "just re-add a hard pin."

## Fixed: connection errors bypassed the shim's own retry loop entirely

45. **Found a real bug in `_asp_openrouter_shim.py`'s own retry
    wrapper** while investigating why the v6 run (deviation #44's
    loosened-provider-pin attempt) still hit occasional whole-batch
    `Error during planning` failures despite 0 empty-responses/0
    giving-up/0 dropped-member counts - the LLM calls that got through
    were succeeding cleanly, but something was still killing entire
    batches. Root cause: `openrouter_generate_content`'s retry loop
    (`for attempt in range(1, _max_retries+1): response =
    _openrouter_generate_content_once(...)`) had NO try/except around
    that call. `_openrouter_generate_content_once` calls
    `requests.post(...)` with no try/except of its own either - so a
    raw connection-level exception (confirmed in the wild:
    `requests.exceptions.ConnectionError`/`"Max retries exceeded with
    url: /api/v1/chat/completions"`, consistent with tyrone's already-
    documented flaky outbound connectivity, deviation #43) propagated
    straight out on the FIRST attempt, never reaching the retry logic
    that exists specifically for "transient provider hiccup" (per that
    function's own docstring/comment). This bypassed the ENTIRE retry
    mechanism this function was built for, and - same mechanism as
    deviation #41/#42 - propagated up through `future.result()` in the
    pinned `complete_scene_graph()`, discarding an otherwise-healthy
    7-8-worker batch over what should have been a retryable transient
    network blip.

    **Fix**: wrapped the `_openrouter_generate_content_once(...)` call
    inside `openrouter_generate_content`'s retry loop in a
    `try/except Exception`, treating any exception exactly like an
    empty response (`response = None`, same retry/give-up path already
    in place and already tested). This is entirely inside my own
    shim/infrastructure code, not pinned code - no advisor consultation
    needed, same as any other plumbing fix.

    Verified: shim's 8 unit tests still pass. Deployed to both the host
    checkout and both container copies (source + venv site-packages).
    The already-running "v6" attempt has the OLD shim loaded in its
    live worker processes (a running Python process doesn't pick up an
    on-disk file change), so this fix won't help v6 retroactively - it
    takes effect on the next fresh launch.

## tyrone rebooted again (5th reboot in ~2 days)

46. **tyrone rebooted again at approximately 2026-09-13 17:19 UTC**,
    killing the `asp-noetic` container mid-run (same exit code 137/
    SIGKILL pattern as deviation #43's reboot). This ended the "v7"
    attempt (scene00069_seed42_v4/llm_log_v7: 32/200 calls used, 0
    completed stages) while an Opus-advisor-assisted investigation into
    a recurring, unexplained `"ERROR: A parallel job failed: None:
    None"` batch-kill exception was still in progress (advisor's
    leading hypothesis: a pickling/reconstruction issue losing an
    exception's fields when it crosses the `ProcessPoolExecutor`
    process boundary back to the parent - diagnostic worker-side
    instrumentation was being drafted, not yet deployed, when the
    reboot hit).

    This is now the **5th reboot in roughly 2 days** on tyrone (Sep 11
    21:35, Sep 11 22:36, Sep 12 08:34, Sep 13 15:32, Sep 13 ~17:19) -
    the pattern is frequent enough (multiple times per day at this
    point) that it should be treated as an expected, recurring
    operational hazard for any run on this machine, not a one-off. Root
    cause remains unknown (no `dmesg`/kernel-log access with this
    account) - flagged to the user again; this is now clearly worth
    them checking with whoever administers tyrone, given the frequency.

    **Recovery** (same mechanical process as #43): `docker start
    asp-noetic`, verified GPU passthrough (`nvidia-smi` OK) and
    workspace integrity (`DEVIATIONS.md` at 1475 lines, all `runs/`
    subdirectories present) - both clean, no data loss, since
    `/workspace` is host-disk bind-mounted. Relaunching Terminal 1 +
    Terminal 2 fresh for a "v8" attempt with a new
    `ASP_LLM_LOG_DIR` (fresh call budget) and all three shim fixes
    (#42 parse-failure per-member drop, #44 loosened provider pin, #45
    connection-error retry coverage) already in place from before this
    reboot - none of that work was lost, only the in-progress run
    itself and the not-yet-deployed "None: None" diagnostic
    instrumentation (which needs to be re-drafted/deployed fresh).

## Deviation #45's fix was never actually deployed (silent scp failure) - revises the "None: None" diagnosis

47. **Discovered while recovering from the #46 reboot: deviation #45's
    connection-retry fix (catching exceptions from
    `_openrouter_generate_content_once` inside `openrouter_generate_
    content`'s retry loop) was NEVER actually live during the entire
    "v7" run**, despite the deployment sequence at the time appearing
    to succeed (unit tests reported "8 passed"). Root cause: the `scp`
    that was supposed to overwrite the host checkout's
    `_asp_openrouter_shim.py` with the fixed version silently did not
    take effect (most likely a casualty of the severe SSH flakiness
    documented throughout this session, possibly an interrupted/
    partial transfer or a race with a reconnect) - and because the
    existing 8-test unit suite has no test covering "an exception from
    `_openrouter_generate_content_once` gets retried, not raised",
    the test run passed against what was actually still the UNFIXED
    file, giving false confidence the deploy worked.

    **This means the "v7" run's recurring `"ERROR: A parallel job
    failed: None: None"` failures were very likely the SAME unretried-
    connection-exception issue as before (not a new, different
    mystery)** - the Opus advisor consultation's leading hypothesis
    (a pickling/reconstruction issue losing exception fields, e.g. a
    `urllib3`/`requests` exception like `MaxRetryError` not
    surviving the `ProcessPoolExecutor` pickle round-trip cleanly)
    remains plausible and consistent with this: an unretried
    `ConnectionError` propagating raw from the shim, through
    `generate_completion_response`, through `_run_single_ensemble_
    member`, through `future.result()`, could very well lose its
    detailed message on the way, rendering as the uninformative
    "None: None" by the time it reaches the parent's `print(f"...
    {e}")`. The worker-side diagnostic instrumentation the advisor
    recommended (log real exception info in the CHILD process before
    it crosses the pickle boundary) is still valuable to pursue if
    "None: None" recurs even with the fix genuinely deployed - but the
    fix should be tried first now that it's actually live.

    **Redeployed properly this time, with explicit verification at
    every step** (not just "the command didn't error"): synced local
    scratchpad copy -> host checkout via `scp`, then **`diff`'d the
    host file against the local source and confirmed byte-identical**
    before proceeding; `docker cp`'d to both container locations, then
    **grepped each container copy directly** (not just the host file)
    to confirm the fix text is actually present in each; then ran the
    unit test suite (8/8 still pass). This three-step verify-after-
    each-deploy pattern (diff after scp, grep after docker cp, tests
    last) is now the standard for any future shim/pinned-code deploy
    on tyrone, specifically because of this silent-failure incident -
    a clean test pass alone is not sufficient evidence a deploy landed
    when the test suite doesn't cover the specific change.

## Root-caused and fixed the actual source of most "OpenRouter flakiness" (broken IPv6)

48. **Found the real root cause behind most of today's OpenRouter call
    failures**: `curl -4 https://openrouter.ai/...` from inside the
    container succeeds instantly and consistently (~0.07-0.08s every
    time); `curl -6` to the same host fails IMMEDIATELY (`HTTP 000`,
    curl exit code 7, "Couldn't connect to server") - **this container
    (and likely the tyrone host itself) has no working outbound IPv6
    route at all.** `openrouter.ai`'s DNS intermittently returns an
    IPv6 (AAAA) address (confirmed: `getent hosts openrouter.ai`
    returned a Cloudflare-range IPv6 address at least once), and plain
    `requests`/`urllib3` has no Happy-Eyeballs-style dual-stack
    fallback - it just attempts whichever address family
    `socket.getaddrinfo()` hands back first, so any call unlucky enough
    to get routed over IPv6 hangs until timeout (`ReadTimeout`) or fails
    outright (`ConnectionError` / "Failed to establish a new
    connection" / even a spurious "Temporary failure in name
    resolution" - that specific message is really urllib3's own error
    text for a failed *connection* attempt after DNS already succeeded,
    not an actual DNS failure, which was momentarily confusing during
    diagnosis).

    This explains essentially ALL the "ReadTimeout"/"ConnectionError"/
    "MaxRetryError" noise seen throughout deviations #40, #44, #45, and
    the "v7"/"v9" runs' timeout bursts - not OpenRouter being slow, not
    provider-specific rate-limiting, not tyrone's general network
    instability (that's a separate, still-unexplained issue tied to the
    SSH outages and reboots) - just a fraction of every batch of calls
    landing on a route that was never going to work.

    **Fix**: in `_asp_openrouter_shim.py`, monkeypatch
    `urllib3.util.connection.allowed_gai_family` (the function urllib3
    calls to pick a socket address family) to unconditionally return
    `socket.AF_INET`, forcing every `requests` call in this process
    onto IPv4 only. This is the standard, minimal, well-known pattern
    for this exact problem. Scoped entirely to this module (own
    infrastructure code, not pinned) - applied at import time, so it
    takes effect for every worker process that imports the shim
    (matches the same "fresh import per spawned worker" pattern already
    relied on for the LLM call cap and logger).

    **Verified**: 5/5 consecutive direct requests through a freshly-
    imported shim module all succeeded in ~0.06-0.08s (versus the
    previous pattern of some fraction of calls hanging for the full
    180s timeout or failing outright). Unit tests still pass (8/8).
    Deployed with the full verify-at-every-step procedure established
    after deviation #47's silent-deploy-failure lesson: `scp` then
    `diff` against the local source (byte-identical confirmed), `docker
    cp` to both container locations then `grep` each copy directly to
    confirm the new code is actually present (not just "the command
    didn't error").

    **Expectation going forward**: this should substantially reduce
    (not necessarily eliminate - tyrone's own SSH/reboot instability is
    a separate, unrelated layer) the OpenRouter-side failure rate for
    any future run. Worth flagging to the user as a real, useful
    finding about the tyrone environment itself (broken IPv6), not just
    a pipeline workaround - if IPv6 is expected to work on this host,
    that's worth them checking independently of anything in this
    project.

## Root cause of the extended (~1hr35min) SSH outage found: two more tyrone reboots, AND the real underlying cause of the session's connectivity pattern

49. **tyrone rebooted twice more during the extended outage that started
    around v10's later stages**: `last reboot` shows boots at 15:32 (already
    known, #46), then again at **17:18** and **19:47** - meaning the ~1hr35min
    SSH outage fought through starting around 18:41 wasn't one continuous
    network blip; it spanned at least one more reboot (19:47) on top of
    whatever caused the initial drop. The `asp-noetic` container was found
    `Exited (137)` (SIGKILL, consistent with host shutdown, same pattern as
    every prior reboot this session) when connectivity finally returned.

    **More importantly, the likely ROOT CAUSE of this session's SSH
    instability pattern was found, separate from the reboots themselves**:
    the local SSH config's `Host tyrone` entry had a **temporary override**
    (dated 2026-09-12, at the very start of this session) pointing at a
    direct LAN address (`10.1.24.188`) instead of the normal Tailscale
    address, because the Tailscale node (`sunitaa4`) was offline on the
    tailnet at that time. That LAN path is very likely what was
    unreliable all session - not tyrone's network stack itself, and not
    purely the reboots (which are a real, separate, still-unexplained
    problem). The user re-established Tailscale connectivity directly
    (manual `ssh 100.109.75.117` login, confirmed working instantly and
    repeatedly) partway through this outage, and the SSH config was
    updated to restore the Tailscale address
    (`~/.ssh/config`, `Host tyrone` -> `HostName 100.109.75.117`,
    replacing the temporary LAN override).

    **Practical effect going forward**: SSH connections via `tyrone` should
    now be dramatically more reliable than they were for the bulk of this
    session, IF the Tailscale-instability theory is correct - this should
    be treated as a testable hypothesis (watch whether the "Connection
    refused"/"Operation timed out" pattern recurs going forward), not a
    certainty, since the reboots are a confirmed-real, independent problem
    that Tailscale does nothing to fix (a reboot still kills the container
    and any in-flight run regardless of which network path reaches the
    host). Reboot count is now at least 7 in roughly 2.5 days, with the
    two most recent only ~2.5 hours apart - tighter than the roughly
    once-daily-to-twice-daily cadence noted earlier, worth flagging to the
    user as escalating, not just recurring, and worth checking with
    whoever administers tyrone.

    **Recovery**: same mechanical process as every prior reboot recovery
    (`docker start asp-noetic`, verified GPU passthrough and workspace
    integrity, both clean) - relaunching Terminal 1 + Terminal 2 fresh.

---

## Follow-up: preserve successful workers after a process-pool failure (2026-09-13)

The bounded clean run `scene00069_seed42_clean_20260913_v3` exposed one
remaining failure path in `exploration/scripts/llm_completion.py`: one
`ProcessPoolExecutor` future terminated abruptly after seven ensemble members
had already written valid YAML files, and `complete_scene_graph()` returned
`None` from its exception handler, discarding those seven results. The handler
now logs the worker exception and continues collecting futures; the existing
all-members-failed branch still returns `None` so the outer retry remains the
last resort. The pre-change file is preserved as
`runs/environment/llm_completion.py.before_worker_exception_fix`, and the
minimal diff is `runs/environment/llm_completion_worker_exception_fix.patch`.

This is a pinned-code deviation, disclosed here because it changes failure
handling while leaving successful completions unchanged. The same run's stage
0 was scored and replayed offline; it was stopped before a completed stage 1
to cap API use. A stage-1 planning failure (`'NoneType' object is not
iterable`) remains an open diagnostic item before any 25 m or matrix run.

The same 25 m probe showed four workers raising `KeyError: 'label'` when the
substitute backend returned an incomplete `check_collision` tool call. The
tool loop now returns a structured error to the model for missing arguments,
allowing that ensemble member to recover or be dropped without taking down
the pool. Valid calls use the unchanged collision function. This second
failure-handling change is included in `llm_completion_resilience_fixes.patch`.

## Follow-up: bounded 25 m probe completed on the substitute backend (2026-09-14)

The final frozen-config probe `scene00069_seed42_25m_20260914_v3` used the same pinned checkout, OpenRouter/DeepSeek shim, and deployed resilience fixes, with a 1,000-call ceiling. An in-container watcher stopped after the first completed checkpoint beyond the 25 m target: stages 0-4 reached cumulative path lengths 0, 7.575, 12.300, 16.500, and 25.275 m using 250 calls. The original pipeline configuration was restored on exit. No worker death, traceback, or provider-error pattern occurred in the pipeline log. The author parser produced eight completions at stages 0-1 and 5, 7, and 6 at stages 2-4; dropped members were retained as a diagnostic rather than manually repaired.

The independent evaluator scored all five checkpoints against the existing exhaustive 00069 frontier reference. The run and its evaluator JSON, per-stage navigation/path/validation JSON, call counter, watcher log, and manifest are mirrored locally under `tyrone_mirror/runs/scene00069_seed42_25m_20260914_v3/`. This is a bounded substitute-backend probe, not a current-backend full gate, 120 m run, or matrix result. The next authorized step is to integrate the offline validator/calibration/risk seams against this frozen cache before scaling to other scenes or seeds.

## Linux integration of the offline extension track (Phase 8) - first real ablation result

50. **Mounted `tools/asp_offline/` (the offline validator/calibration/
    scoring extension, previously Mac-only) into the Linux checkout and
    ran it for real, per IMPLEMENTATION_PLAN.md section 17 step 1.**
    27/27 tests pass live inside the container's real Python 3.9/ROS
    environment (not just the Mac's Python 3.14) - `cd /workspace/tools
    && PYTHONPATH=/workspace/tools python3 -m pytest tests/
    test_asp_offline.py -v`. This closes the "ROS/ASP integration is
    pending on tyrone" gap noted in the plan's completion checklist.

    **First real extension-replay ablation** (`tools/
    extension_policy_replay.py`, new): compares four policies - official
    ASP (raw LLM predictions, unfiltered), filter-only (the structural
    validator), support-threshold-only, and filter+support-threshold -
    on the SAME cached ensemble completions from the `v3` 25m run,
    scored against the real scene-00069 ground-truth reference graph.

    **Important mechanism finding, confirmed by reading
    `llm_completion.py` directly rather than guessing**: the pipeline's
    tracked/scored graph (`habitat_scene_graph_original_graph{0,1}.yaml`)
    is produced by `_preprocess_dsg()` converting the raw SLAM/DSG
    output BEFORE any LLM completion runs - it is NEVER a merge of the
    LLM's proposed completions. The 8 raw completions per stage feed
    only `uncertainty_calc.select_next_target()` for viewpoint scoring.
    So this ablation compares four ways of filtering the LLM's raw
    predictions before scoring them against ground truth (a prediction-
    quality question), not four navigation trajectories (that would
    need a live re-run per policy, which step 1 explicitly does not do).

    ~~**Result** (path-normalized AUC, 0-25.275m, scene 00069):
    - official (unfiltered): F1=0.326, P=0.490, R=0.246, GED=1.012
    - filter-only (structural validator): F1=0.342, P=0.582, R=0.246,
      GED=0.976
    - support-threshold-only at tau=0.75 (**uncalibrated** - see below):
      F1=0.357, P=0.677, R=0.245, GED=0.949
    - filter+support-threshold at tau=0.75: F1=0.357, P=0.681, R=0.245,
      GED=0.948~~

    **2026-09-15 correction (Opus audit finding M5): the GED column
    above predates deviation #56's GED-canonicalization fix, and the
    filter-only row also predates deviation #63's validator room-
    dimension fix - neither was ever re-applied back to this entry's own
    table.** Re-scored with the current code
    (`extension_policy_replay_v2_realcalib.json`, same 00069 cache):

    - official (unfiltered): F1=0.326, P=0.490, R=0.246, GED=0.961
    - filter-only (structural validator): F1=0.332, P=0.526, R=0.246,
      GED=0.947
    - support-threshold-only at tau=0.75 (**uncalibrated**): F1=0.357,
      P=0.677, R=0.245, GED=0.898
    - filter+support-threshold at tau=0.75: F1=0.357, P=0.679, R=0.245,
      GED=0.897

    F1/precision/recall for official and both support-threshold rows are
    essentially unchanged (within rounding) - only GED moved for those
    (the canonicalization bug affected GED computation only, not
    matching). filter-only's precision drop (0.582->0.526) is real: the
    validator fix stopped over-rejecting predicted rooms, which changes
    which nodes survive filter-only specifically.

    Precision climbs monotonically with the support threshold
    (0.490->0.680 across the tau sweep) while recall stays essentially
    flat (0.246->0.245) - both filters remove wrong predictions without
    meaningfully removing correct ones, and are complementary (combined
    is best or tied-best at every tau tested). This is a real, coherent
    signal in the expected direction, not noise - the first genuine
    ablation evidence for the proposed extension's value. (See deviation
    #67 for the held-out-selected version of this same finding, which
    supersedes the in-sample tau=0.75 choice used throughout this entry.)

    **Explicit calibration caveat (Opus advisor review, 2026-09-14)**:
    "support-threshold-only" and "filter+support-threshold" are
    UNCALIBRATED (`calibrator=None` throughout - raw cross-ensemble
    agreement s_j, no monotone map fitted). Real leave-one-scene-out
    calibration per IMPLEMENTATION_RESEARCH.md section 4.2 needs
    reference graphs for at least 4 scenes rotated 3-vs-1; only scene
    00069 has one so far. Every output record carries an explicit
    `"calibration": {"status": "UNCALIBRATED_PROVISIONAL", ...}` block.
    Rejected two alternatives before settling on this: (a) skip these
    two policy variants entirely - rejected, stalls the plan's own
    critical path for no real gain in honesty; (b) fit isotonic
    in-sample on the single scene - rejected as leaked/overfit, would
    look artificially excellent and prove nothing; demoted to a
    test-only mechanism check instead (not in the results table).

    **Cross-validated**: ran the same tool against the same cache on
    both the Mac (local `tyrone_mirror/` copy) and tyrone itself
    (the real Linux checkout) - identical results up to floating-point
    repr differences between Python 3.9 and 3.14.

    Committed locally (`Add uncalibrated support-threshold policy for
    the extension ablation` + a follow-up commit for
    `extension_policy_replay.py`); artifacts at
    `runs/scene00069_seed42_25m_20260914_v3/extension_policy_replay.json`
    on tyrone and mirrored locally.

    **Still open**: the plan's step 3 ("only after that replay is
    checkable, generate the other three reference graphs and decide
    whether the four-scene matrix is justified") - this replay is now
    checkable and shows a real, sensible signal, so generating
    reference graphs for 00573/00853/00871 (proven zero-cost method,
    ~50-60 min each via `frontier_baseline.py`) is the next reasonable
    step, followed by real leave-one-scene-out calibration once enough
    scenes exist.

## Paper audit: verified methodology/parameters, one confirmed unfixable gap, reasoning effort raised to max

51. **Loaded and read the full ASP paper (arXiv:2510.05430v2, HTML + PDF,
    all sections and footnotes) end-to-end and systematically audited
    this replication against it**, per explicit user request to "miss
    no issues and verify each thing."

    **Parameters - all confirmed matching, no fix needed**: λr=1,
    λd=0.2 (paper) = UNCERTAINTY_ROOM_WEIGHT=1.0, MOVE_COST_LAMBDA=0.2
    (pipeline_config.yaml); m=4 completions x 2 scene graphs = 8 samples
    (paper) = LLM_ENSEMBLE_COUNT=4, SCENE_GRAPH_COUNT=2 (config); 300
    candidate viewpoints (paper) = UNCERTAINTY_SAMPLES=300 (config).
    One benign, pre-existing (not introduced by this session) wording
    nuance in the pinned code itself: paper says "perturb each graph
    N=4 times," config's UNCERTAINTY_PERTURBATIONS=3 with its own
    comment "total graphs = perturbations + original" (3+1=4) - same
    total sample count, slightly different composition (3 perturbed +
    1 exact vs. the paper's implied 4 perturbed). This is the pinned
    author's own code, not something to "fix."

    **Confirmed unfixable gap, exhaustively searched, not guessed**:
    the paper's F1 metric restricts to "61 common indoor object
    categories" but never enumerates them, and this project's evaluator
    has no category restriction at all. Searched for the actual list
    across: the full paper text (no enumeration given anywhere,
    including all footnotes); the pinned repo at its true HEAD (multiple
    targeted greps for category-list-shaped files/content - confirmed
    via `git fetch origin` that f1ea141 already IS origin/main's tip,
    nothing newer exists); the GitHub repo's README and Issues (empty -
    no discussions exist on the repo at all); and general web search for
    author blogs/project pages/any external mention of "61 object
    categories" tied to this paper. Found nothing. This list is
    genuinely not published anywhere publicly accessible - not
    something recoverable by more searching. Documented as a disclosed,
    permanent limitation rather than invented.

    **Ground-truth generation methodology - mechanism matches, driver
    differs, doesn't explain the direction of the observed gap**: the
    paper generates ground truth via a human manually piloting the
    camera to ensure exhaustive coverage; this project used the
    automated `frontier_baseline.py` policy instead (verified via
    `ged_score_plot.py`'s own GT-loading code: both approaches produce
    the SAME file format via the SAME `_preprocess_dsg()` conversion
    mechanism - only the exploration driver, human vs. automated
    frontier algorithm, differs). Reasoned through the direction of any
    resulting bias: if the automated GT is *less* complete than a
    human's, that shrinks the recall denominator, which would tend to
    inflate (not deflate) measured recall - the opposite of the actual
    observed gap - so this is very unlikely to be the explanation for
    why this project's numbers ran below the paper's trajectory.
    Disclosed as a real methodology difference regardless.

    **User-directed change: reasoning effort raised to DeepSeek's
    maximum ("high") setting.** Re-tested against the exact real
    payload shape (multi-image + tool schema, ~9.6k prompt tokens)
    before deploying anything live, given this exact setting was the
    original cause of a 100%-empty-completion failure earlier this
    session (deviation context around the "low"-effort fix). At the
    SAME max_tokens ceiling (16000) already in use, "high" no longer
    reproduces that failure - it was faster (27.6s vs 48.7s for "low")
    and produced MORE tool calls and content (6 calls/2750 chars vs 4
    calls/1959 chars), not less. Strong evidence the original failure
    was actually the provider-routing problem fixed in deviations
    #40/#48, not something inherent to "high" itself. Tested raising
    max_tokens further (32000, 65000): no quality gain, and 65000 routed
    to a much slower provider (188s). Deployed `effort: "high"` as the
    new default (max_tokens unchanged at 16000), verified byte-identical
    on both container copies after deploy, 8/8 shim unit tests still
    pass. Overridable via `ASP_OPENROUTER_REASONING_EFFORT`/
    `ASP_OPENROUTER_MAX_TOKENS` if a future payload shape needs
    different values.

    **Next**: launch a fresh real run with the new reasoning-effort
    setting (and all prior fixes still in place) to get updated,
    comparable ablation numbers.

## High reasoning effort's length-limit failures persist under real load - max_tokens raised to 24000

52. **Under the real pipeline's sustained 8-worker concurrent load, "high"
    reasoning effort's original failure mode (finish_reason="length",
    the whole 16000-token budget spent on chain-of-thought before any
    real output) still occurred - at ~10% of calls (3/29), across two
    different providers in sequence (DeepInfra, then Alibaba).** This
    contradicts what the isolated pre-deployment test (deviation #51)
    showed - that test was sequential single calls, not realistic
    concurrent load, and evidently understated the real failure rate.
    The per-member drop/give-up logic (deviation #42) correctly absorbed
    this without crashing any batch (0 "Error during planning" the whole
    time), but a ~10% silent-waste rate on a run specifically meant to
    exercise DeepSeek's maximum reasoning setting is worth reducing.

    Stopped the affected run (`scene00069_seed42_25m_20260914_v4`,
    minimal loss - no stages had completed yet) rather than let the
    waste continue for the full run. Raised `max_tokens` default from
    16000 to 24000 (a deliberate middle ground - the earlier isolated
    test already showed 65000 has diminishing/negative returns: no
    quality gain, and it routed to a much slower provider). Verified
    with the full deploy-then-diff-then-grep-then-test procedure
    established after deviation #47's silent-deploy-failure lesson.
    8/8 shim unit tests still pass.

    Relaunching the same run fresh with the new ceiling. If the
    length-limit rate is still meaningfully above baseline at 24000,
    the next lever to pull is NOT a further max_tokens increase (already
    shown to have poor returns past this point) but reconsidering
    whether "high" effort is worth its real, measured cost on this
    specific task versus a middle setting ("medium", untested so far).

53. **The `max_tokens=24000` relaunch after deviation #52 (run
    `scene00069_seed42_25m_20260914_v4`, manually launched with
    `ASP_LLM_MAX_CALLS=250` as a smaller test budget rather than via a
    saved launcher script) used a stale `BASE_DIRECTORY`.** The launch
    correctly pointed `ASP_LLM_LOG_DIR` (and therefore the call-count
    logger and cap) at the new `.../scene00069_seed42_25m_20260914_v4/`
    run folder, but `pipeline_config.yaml`'s `BASE_DIRECTORY` - which
    controls where the pipeline itself writes stage output
    (`habitat_scene_graph_original_graph*.yaml`, `navigation_stats.json`,
    the raw ensemble completions) - was never updated and still pointed
    at an older path, `/workspace/runs/scene00069_seed42_v4/stages`,
    left over from an earlier attempt in this session. These are two
    separate mechanisms (log/call-budget location vs. stage-output
    location) that must each be set correctly; setting one does not
    imply the other. `run_asp_25m_v3.sh` (the v3 launcher) avoids this
    class of mistake entirely by `sed`-rewriting `BASE_DIRECTORY` in
    `pipeline_config.yaml` from the same `$RUN` variable used for
    everything else in the script, rather than relying on it being set
    by hand; the v4 launch was done manually and skipped that step.

    No data was lost - real stage output for this run (3 complete
    stages, 1 partial) was found intact at the old path, confirmed via
    `ls -la` timestamps (all Sep 14, 05:59-06:24, cleanly attributable
    to this run and not mixed with older data at that same reused
    path) - but it was not where anyone would have looked for it.
    Recovery: copied the 4 stage directories to a clean, correctly
    named location (`scene00069_seed42_high_effort_20260914/stages/`)
    before running the extension-replay ablation against them.

    Lesson applied going forward: use a `sed`-based launcher script
    (`run_asp_25m_v3.sh` as the template) for every future launch,
    never a hand-assembled one-off command, specifically because it
    makes this class of mistake structurally impossible rather than
    relying on remembering to update every path by hand.

54. **`ASP_LLM_MAX_CALLS` cap exhaustion does not stop the pipeline -
    it loops indefinitely, re-attempting and immediately failing.**
    Once the hard cap (250, for the run in deviation #53) was
    exceeded, the pipeline's outer retry loop kept re-attempting the
    same planning step forever, each attempt immediately erroring with
    `"ERROR: A parallel job failed: ASP_LLM_MAX_CALLS hard cap (250)
    exceeded on call #N..."`, with N climbing without bound and no
    further progress possible. This is outer retry logic in the pinned
    pipeline code, not something introduced by the OpenRouter shim; no
    fix was attempted (would need the same Opus-consult-before-touching-
    pinned-code discipline as any other pinned-code change), it is
    documented here as an operating characteristic. Detected via a
    Monitor watch on the run's log for the cap-exceeded string, not by
    the process exiting - it never would have. Fixed by manually
    killing the stuck process (`docker exec asp-noetic kill -9
    <pipeline_pid> <xvfb_pid>`) and confirming, separately, that
    Terminal 1's ROS/hydra session was unaffected and still healthy.

    Practical takeaway: size `ASP_LLM_MAX_CALLS` generously up front
    (per-stage call count under "high" reasoning effort runs roughly
    15-17x higher than under "low" - one stage alone used ~130 calls
    vs. ~8 under "low"), and treat a Monitor watch for the cap-exceeded
    string as mandatory on any "high effort" launch, since the process
    will not sound its own alarm.

    Follow-up: relaunched via a proper `sed`-based script
    (`run_asp_25m_high_effort.sh`, modeled directly on `run_asp_25m_v3.sh`
    to avoid deviation #53's mistake), reasoning effort=high,
    max_tokens=24000 (deviation #52's fix), `ASP_LLM_MAX_CALLS=1500`
    (sized for roughly 5 full stages at the observed high-effort
    per-stage call rate, with margin), run directory
    `scene00069_seed42_25m_20260914_high_effort_v5`. Monitoring for
    completion or a repeat of any known failure mode (cap exhaustion,
    length-limit finish_reason, crash/traceback).

55. **Final result of the "high" reasoning-effort experiment (deviations
    #51-54): it made the replication WORSE, not better, on the tracked-
    graph score - the actual quantity comparable to the paper's own
    reported numbers.** Run `scene00069_seed42_25m_20260914_high_effort_v5`
    reached 7 complete navigation checkpoints (0, 0, 6.3, 8.325, 14.7,
    20.325, 23.4, 30.525 m) using 412 of its 1500-call budget before
    being stopped manually (no automatic path-budget termination exists
    in the pinned pipeline - `PATH_LENGTH_FACTOR` is explicitly unused -
    so it would have kept running indefinitely past any comparison point
    otherwise).

    ~~Scored the pipeline's actual tracked graph (habitat_scene_graph_
    original_graph{0,1}.yaml, no completion merging - the same quantity
    `evaluate_run.py` computed for v3, and the one comparable to the
    paper's own methodology) with the same path-normalized-AUC machinery
    used throughout this session:

    - v3 (low effort), 0-25.275 m: P=0.681, R=0.245, **F1=0.357**,
      normalized GED=0.948
    - v5 (high effort), budget-matched subset 0-23.4 m (closest
      available undershoot of v3's endpoint): P=0.682, R=0.197,
      **F1=0.303**, normalized GED=0.981
    - v5 (high effort), full available data 0-30.5 m (exceeds v3's
      budget by ~5 m, so if anything favors v5): P=0.682, R=0.221,
      **F1=0.330**, normalized GED=0.970

    High effort loses on F1 under BOTH comparisons, including the one
    that gives it more exploration distance to work with. Precision is
    essentially unchanged (~0.68 in every case) - the entire gap is
    recall (0.245 -> 0.197-0.221).~~

    **2026-09-14 correction (deviation #56, mislabel bug - already
    corrected in SESSION_REPORT_2026-09-13.md §11 at the time, missed
    here until the 2026-09-15 Opus audit, finding M4, caught it):** the
    table above was computed with an ad hoc script using the same
    non-author-faithful matching algorithm the extension ablation uses -
    it was measuring the ablation's filtered/merged graph
    (`filter_plus_support_threshold_tau_0.75`), not the pipeline's real
    unmerged tracked graph, despite the caption. Real numbers, from
    `tools/evaluator/evaluate_run.py` (the author-faithful tool):

    - v3 (low effort), 0-25.275 m: P=0.671, R=0.241, **F1=0.352**,
      normalized GED=1.075
    - v5 (high effort), budget-matched subset 0-23.4 m: P=0.655,
      R=0.198, **F1=0.302**, normalized GED=1.189
    - v5 (high effort), full available data 0-30.5 m: P=0.659, R=0.223,
      **F1=0.329**, normalized GED=1.188

    The finding survives and is if anything sharper: high effort still
    loses on F1 under both comparisons (a larger gap), and GED is
    genuinely worse too (the mislabeled table had GED backwards, showing
    v5 as better - an artifact of scoring the wrong graphs).

    **Root cause, confirmed by direct log comparison, not guessed**:
    grepped "ensemble members were dropped" across both full pipeline
    logs. v3: drops of 3, 1, 2 out of 8 per round (mean 2.0/8 dropped =
    75% survival). v5: drops of 7, 3, 1, 3, 2, 4 out of 8 per round
    (mean 3.33/8 dropped = 58% survival) - one round lost 7 of 8
    members entirely. "High" effort makes DeepSeek more likely to wrap
    its YAML output in markdown code fences or otherwise deviate from
    the bare-YAML format the pipeline's parser requires, so the
    existing per-worker drop/give-up guard (deviation #42) discards
    more completions before they can contribute any predictions. Fewer
    surviving completions per round means less object coverage in the
    merged graph, which drags recall down - this is a real, mechanistic
    explanation, not a coincidence attributed after the fact.

    **Comparison against the paper's own numbers** (arXiv:2510.05430v2,
    Fig. 4's table, "Semantic (Ours)" row for Scene: 69): F1 = 25.8% at
    10% of the paper's own exploration budget, 60.1% at 50%, 62.2% at
    100% (raw, non-normalized GED 266.3 -> 147.0 -> 148.0 over the same
    checkpoints). ~~Both of this project's runs (35.7% best case, low
    effort)~~ Both of this project's runs (35.2% best case, low effort,
    corrected above) sit between the paper's 10%-budget and 50%-budget checkpoints
    - meaningfully below where a fully-scaled run would be expected to
    land, but the exact fraction of the paper's own budget that our
    ~25-30 m represents isn't known precisely (the paper doesn't give an
    absolute total path length for scene 69, only a mean per-step travel
    distance of 3.74 m for its own method). The two limitations disclosed
    in deviation #51 - the unpublished 61-category F1 restriction (not
    applied here) and the DeepSeek Flash vs. Gemini Pro capability gap -
    remain the leading candidate explanations for the residual gap, not
    anything newly found in this run.

    **Recommendation, not yet acted on**: revert the shim's reasoning-
    effort default from "high" back to "low" (`ASP_OPENROUTER_REASONING_
    EFFORT`) for any future run on this pipeline - "high" costs more
    (calls, tokens, wall time) and measurably hurts the one thing it was
    meant to help. This is a disclosed, evidence-based finding about
    this specific pipeline's strict-YAML parsing architecture, not a
    general claim about reasoning effort settings elsewhere.

    All artifacts mirrored: v5's raw stages at
    `scene00069_seed42_25m_20260914_high_effort_v5/stages/`, the two
    comparison subsets at `scene00069_seed42_high_effort_v5_full/` and
    `scene00069_seed42_high_effort_v5_matched/`, both with their own
    `extension_policy_replay.json` (ablation policies) alongside the
    tracked-graph AUC computed separately (the ablation tool's own
    "official" row is a different, documented quantity - raw unmerged
    completions - not the tracked graph the paper's own number matches).

56. **An independent review (REVIEW_2026-09-14.md) found a real support-
    denominator bug in the extension ablation and a real provenance
    mislabel in both report files' "tracked graph" numbers. Both are now
    fixed; every affected number is corrected below.** Full review
    consulted with an Opus advisor on the exact fix (K=4 vs. pooled K=8)
    before touching code that generates already-published numbers, per
    this session's standing practice for research-validity-affecting
    changes.

    **Bug 1 - support denominator used surviving completions, not the
    intended ensemble size.** `tools/asp_offline/calibration.py`'s
    `match_hypotheses` computed `support = hits / len(completions)`,
    where `completions` is whatever survived upstream parse-failure
    drops - frequently fewer than the pipeline's actual per-scene-track
    ensemble size. A hypothesis in 1 of 1 surviving completions scored
    support 1.0, though the intended claim ("1 of the real ensemble
    agrees") is a much weaker one. Advisor-confirmed expected size is
    **4, per scene-track, not a pooled 8**: the pipeline tracks graph0
    and graph1 as two independently-scored instances (LLM_ENSEMBLE_
    COUNT=4, SCENE_GRAPH_COUNT=2 - the paper's stated "8 samples" is
    exactly 4-per-track x 2 tracks). Pooling would also be actively
    wrong, not just untidy: room ids are a raw per-graph integer
    namespace assigned independently per track, so the same id in
    graph0 and graph1 can name two unrelated rooms - a pooled match on
    `parent_room` would silently compare across them.

    Fixed: `match_hypotheses` now takes a required, keyword-only
    `expected_size` (no default, no fallback to `len(completions)`,
    raises if `len(completions) > expected_size` as an upstream-bug
    guard), threaded through `support_policy.py` and set to
    `LLM_ENSEMBLE_COUNT` at every call site in
    `extension_policy_replay.py`. `Hypothesis` gained a `hits: int`
    field (the numerator - unrecoverable from a bare support float
    later). Every `support_threshold` output block now records
    `expected_size`/`available`/`missing` alongside `kept`/`dropped`,
    and the top-level replay payload gained a `support_denominator`
    block naming the mode explicitly, so an old JSON and a corrected
    one are tellable apart at a glance.

    **Side effect the advisor caught before it shipped silently**: under
    the old denominator, at n=2 surviving completions the only reachable
    support values are {0, 0.5, 1.0}, so tau=0.75 and tau=1.0 were the
    SAME policy at most stages (confirmed in the old v3 JSON: byte-
    identical results at those two tau values for 4 of 5 stages). The
    "precision climbs monotonically with tau" claim already reported was
    partly this quantization artifact, not a clean dose-response curve.
    With a fixed K=4 denominator, support only ever takes 5 values
    (0, .25, .5, .75, 1.0), and since a completion is always in its own
    denominator, tau in [0, .25] is always a no-op. Collapsed
    `DEFAULT_TAU_GRID` from the old 9-point sweep to `[0.0, 0.5, 0.75,
    1.0]` (the old grid kept as `DEFAULT_TAU_GRID_LEGACY` for
    reproducing pre-correction numbers only).

    Added 2 new tests (`test_missing_completions_do_not_inflate_support`,
    `test_more_completions_than_expected_size_raises`) and fixed 2
    existing ones to pass `expected_size` explicitly, preserving their
    original 3-completion-ensemble intent rather than silently changing
    what they tested. 30/30 tests pass, live-verified on tyrone.

    **Bug 2 - edge comparison after ID-remapping wasn't re-canonicalized**
    (found independently while investigating Bug 3 below, in
    `tools/asp_offline/evaluator.py`'s `evaluate_graph`, NOT in the
    author-faithful `tools/evaluator/ged.py`, which uses networkx's real
    `graph_edit_distance` directly on node attributes and has no manual
    ID-remapping step - confirmed this bug class structurally cannot
    occur there). `mapped_pred_edges` built `(all_map[a], all_map[b])`
    tuples without re-sorting after mapping predicted-space ids into
    reference-space ids; `ref_edges` WAS sorted (in reference-space).
    Whenever a mapped edge's endpoints happened to reverse lexical order
    between the two id spaces, a real shared edge was double-counted as
    one spurious insertion plus one spurious deletion. Fixed with
    `tuple(sorted(...))` after mapping, not before. Regression test
    added (`test_edge_match_survives_reversed_lexical_order_after_id_
    mapping`) - confirmed it fails (GED 2.0 instead of 0.0) against the
    pre-fix code and passes against the fix. This only affects the
    offline extension's own ablation GED numbers, never the author-
    faithful evaluator's GED (used for any paper comparison).

    **Bug 3 - the biggest one: both report files' "tracked graph, no
    completion merging, the same quantity the paper reports" numbers
    were mislabeled.** They were actually computed with an ad hoc script
    (`tracked_graph_auc.py`, written this session, never committed to
    `tools/`) that used `asp_offline.evaluator.evaluate_graph` - the
    SAME non-author-faithful matching algorithm the ablation itself
    uses, not the author-faithful `tools/evaluator/matching.py`+`ged.py`
    (which exactly replicates `f1_score_plot.py`/`ged_score_plot.py`).
    The mislabeled v3 number (P=0.681/R=0.245/F1=0.357/GED=0.948)
    matches `extension_policy_replay.json`'s `filter_plus_support_
    threshold_tau_0.75` almost exactly - it was measuring the merged,
    filtered ablation graph, not the pipeline's real unmerged tracked
    graph.

    The REAL tracked-graph number, recomputed via `tools/evaluator/
    evaluate_run.py` (the same tool and the same command that correctly
    produced the ORIGINAL v3 headline reported in DEVIATIONS/SESSION_
    REPORT section 10 - P=0.671/R=0.241/F1=0.352/GED_normalized=1.075 -
    which was right all along and is now reconfirmed byte-for-byte
    reproducible):

    | Run | Budget | P | R | F1 | norm. GED |
    |---|---|---|---|---|---|
    | v3, low effort | 0-25.275 m | 0.671 | 0.241 | 0.352 | 1.075 |
    | v5, high effort (budget-matched) | 0-23.4 m | 0.655 | 0.198 | 0.302 | 1.189 |
    | v5, high effort (full data) | 0-30.5 m | 0.659 | 0.223 | 0.329 | 1.188 |

    (v5's numbers computed the same way: `evaluate_run.py` per-stage,
    then the same `area_under_curve` trapezoidal utility already used
    throughout - `tools/evaluator/` and `tools/asp_offline/evaluator.py`
    are independent matching implementations, but the AUC integration
    step is evaluator-agnostic and shared correctly.)

    The core finding survives and is if anything slightly sharper with
    the correct evaluator: high effort still scores meaningfully worse
    than low effort (F1 0.302 vs. 0.352 on the budget-matched
    comparison, a larger gap than the mislabeled numbers showed), GED
    is worse too (1.189 vs. 1.075 - the previous mislabeled numbers had
    GED backwards, showing v5 as BETTER on GED, an artifact of comparing
    the wrong graphs). The root-cause mechanism (higher ensemble-drop
    rate under high effort) is unaffected by this correction - that
    evidence came from direct log greps, not either evaluator.

    **One more open item, not yet fixed**: tau=0.75 was picked by eye
    from a sweep scored against the only reference graph that exists -
    in-sample selection bias, flagged by the review and not resolved by
    the denominator fix. Treat every reported tau=0.75 number as an
    exploratory best-point-on-one-scene, not a preregistered or
    held-out-validated choice, until reference graphs exist for the
    other 3 scenes and a real leave-one-scene-out selection is run.

    All corrected outputs written to new-suffixed files, originals left
    untouched (`extension_policy_replay_k4.json` alongside the original
    `extension_policy_replay.json`, both on tyrone and mirrored locally)
    - `tyrone_mirror/` has no git history behind it, so overwriting
    would have destroyed the pre-correction evidence with no way back.
    Also mirrored this pass, previously missing per the review's
    evidence-completeness finding: `tools/evaluator/` (the author-
    faithful evaluator, was on tyrone only), v5's full run manifest/
    config/pipeline log/call counter/deployed shim revision, and a new
    `tools/run_manifest.py` that content-hashes every input a reported
    number depends on (config, commit, reference graph, evaluator
    source, result JSON) into one `run_manifest_hashes.json` per run -
    generated for both v3 and v5 this pass.

57. **Second reference-graph generation started: scene 00573's exhaustive
    frontier-baseline reference graph is done** (Step 3 of REVIEW_2026-09-
    14.md's recommended sequence, following the fully-corrected extension
    ablation - see #56). **Real numbers, zero API cost**: 3483.89 seconds
    (58.1 minutes), 178.05 meters total path, 53 stages, final reference
    graph 81/85 objects (graph0/graph1) and 17/18 rooms - roughly double
    scene 00069's 67 objects/9 rooms/96.5 m, consistent with a larger
    scene needing proportionally more stages.

    **First launch attempt failed - real root cause, not scene-related**:
    the original scene-00069 LLM-pipeline ROS session (Terminal 1,
    `dataset_name:=realsense`) was killed with `kill -9` on specific PIDs
    to free the GPU/ROS stack for this work, but that kill list was
    incomplete - `segmenter_yoso.py` (the YOSO/CLIP segmentation node),
    `rosmaster`, and `rosout` were never identified as needing cleanup and
    stayed alive. When the new roslaunch (`dataset_name:=realsense_
    frontier`) started, its `semantic_inference` node had to load its own
    YOLOE/CLIP model fresh (~10s) while a node with a colliding name was
    already registered under the stale `rosmaster` - `task_server` (a
    REQUIRED node) queried `/semantic_inference/embed` about 1 second
    after its own init, before the new `semantic_inference` had finished
    registering the service, got "no provider", and died immediately -
    cascading roslaunch's automatic full-group shutdown per ROS's
    required-node semantics. Fixed by identifying and killing the three
    stale survivors with targeted PID kills (verified via `ps aux`, not a
    broad `pkill` pattern - one earlier attempt at broad `pkill -9 -f
    rosmaster` inside a compound command produced exit code 137,
    suggesting the calling shell itself got caught by an overly broad
    pattern; switched to explicit PIDs after that). Lesson: a full ROS
    session teardown must account for every node the launch file starts,
    not just the ones with obviously matching names - `ps aux | grep -i
    ros` before any new roslaunch is now the standing check, not just
    checking for `hydra_ros_node`/`task_server`/`roslaunch` by name.

    **Real, non-fatal errors during the run, all self-recovered - worth
    disclosing since they're pinned-code robustness gaps, though none
    stopped progress**:
    - A caught `TypeError: object of type 'NoneType' has no len()` in
      `frontier_baseline.py`'s `mid_path_callback` (`self.local_path` was
      `None` when a mid-path message arrived) - rospy's own callback
      dispatcher isolates exceptions per-callback, so this just dropped
      one path update and the pipeline continued normally afterward.
      Real bug in the pinned script, not touched (out of scope - not on
      the crash path this session's earlier `llm_completion.py` patch
      addressed, and not blocking).
    - Repeated `Timeout! Did not find an updated/stable file at
      .../graph{0,1}_dsg.json` (both tracks, multiple times) and `A*
      search failed to find a mid path` / `Received empty mid-level
      path.` cycles, most densely clustered in an extended ~7-minute
      stretch right before genuine completion (stages 49-53) - this
      matches scene 00069's own documented pre-completion pattern
      exactly (deviation #39: "the sequence of A*/mid-path warnings
      right before it just reflects the planner exhausting hard-to-reach
      candidates before correctly concluding none are left"). Watched
      carefully rather than assumed benign, given it initially looked
      like it could be a stall (stage count briefly static for a few
      minutes) - confirmed genuine by checking stage-directory timestamps
      for continued activity and letting it run rather than killing it
      prematurely; it resolved into real further progress (stages 50-53)
      and then the correct `Frontier planner returned no target.
      Exploration finished.` log line.

    **A real gap in the launcher script, found and fixed for future
    scenes**: `frontier_baseline.py` never writes `habitat_scene_graph_
    original_graph{0,1}.yaml` itself (confirmed by grep - zero matches in
    the script) - it only writes the raw `graph{0,1}_dsg.json`. Scene
    00069's reference YAML files (deviation #39) were produced by a
    manual post-processing step this session hadn't re-documented as a
    reusable procedure: calling `exploration/scripts/f1_score_plot.py`'s
    own `convert_dsg_to_yaml(dsg_filepath)` directly on the final stage's
    two DSG files. Wrote a small, reusable wrapper,
    `tools/convert_frontier_reference.py` (imports `convert_dsg_to_yaml`
    from the author's script directly rather than reimplementing it -
    same fidelity guarantee as the rest of this project's evaluator
    work), and ran it on stage 53 to produce the actual reference YAMLs
    used above. This step must be run for every future frontier-baseline
    scene; it does not happen automatically.

    Process cleanly stopped via `stop_frontier_reference.sh` (SIGTERM to
    `frontier_baseline.py`, which correctly prints its own exploration
    summary and calls `sim.close()` before exiting - confirmed genuine,
    not a forced kill mid-state). Final-stage YAML/nav-stats/path-log
    mirrored to `tyrone_mirror/runs/scene00573_frontier_reference/`
    (small files only - the raw `graph{0,1}_dsg.json` dumps are ~55 MB
    each and were left on tyrone only, same size-based decision as the
    v5 raw stages in deviation #53).

    Next: scene 00853 (val split), same procedure, same thorough
    pre-launch process cleanup applied from the start this time.

58. **Third reference-graph generation complete: scene 00853's exhaustive
    frontier-baseline reference graph is done**, no repeat of the earlier
    process-cleanup issue (deviation #57's thorough-cleanup lesson applied
    from the start this time - clean launch, no startup race). **Real
    numbers, zero API cost**: 2909.80 seconds (48.5 minutes), 99.98 meters
    total path, 34 stages attempted (33 fully complete with both DSG
    snapshots - stage 34 only got as far as `executed_path.json` before
    "Frontier planner returned no target" fired, so stage 33 is the
    reference). Final reference graph 82/78 objects (graph0/graph1) and
    15/17 rooms - close in scale to scene 00069 (67 objects/9 rooms/96.5m)
    despite being the val-split scene, not the train-split one.

    Applied the conversion-step lesson from #57 immediately:
    `tools/convert_frontier_reference.py` run directly on stage 33 to
    produce `habitat_scene_graph_original_graph{0,1}.yaml` (confirmed
    again this is a required manual step - `frontier_baseline.py` never
    writes these itself).

    No notable transient errors this run beyond the same routine "No
    local path available" warnings already characterized as normal in
    #57 - a cleaner run than scene 00573's.

    Final-stage YAML/nav-stats/path-log mirrored to `tyrone_mirror/runs/
    scene00853_frontier_reference/` (small files only, per the same
    size-based decision as #53/#57 - raw `graph{0,1}_dsg.json` dumps
    left on tyrone only).

    Next: scene 00871 (val split, the last of the three remaining
    scenes), same procedure, same pre-launch cleanup discipline.

59. **Fourth and final reference-graph generation complete: scene
    00871's exhaustive frontier-baseline reference graph is done.** All
    four planned scenes (00069, 00573, 00853, 00871) now have exhaustive,
    zero-API-cost reference graphs - closes REVIEW_2026-09-14.md's Step 3
    and unblocks Step 4 (real leave-one-scene-out calibration, previously
    impossible with only 1 of 4 references).

    **Real numbers**: 3772.67 seconds (62.9 minutes), 120.38 meters total
    path, 55 stages attempted (54 fully complete with both DSG snapshots
    - stage 55 only reached `executed_path.json` before "Frontier planner
    returned no target" fired, same pattern as scene 00853's final
    stage). Final reference graph 101/100 objects (graph0/graph1) and
    15/13 rooms - the largest of the four scenes by object count.

    Conversion step (`tools/convert_frontier_reference.py`, per the
    lesson from #57) applied immediately, no gap this time. No process-
    cleanup issues (thorough cleanup discipline from #57 held for all
    three of this session's launches after the first). Only the same
    routine, self-recovering navigation warnings already characterized
    in #57 - no notable new error types this run.

    Final-stage YAML/nav-stats/path-log mirrored to `tyrone_mirror/runs/
    scene00871_frontier_reference/` (small files only, raw DSG dumps
    left on tyrone per the established size-based decision).

    **All four scenes' reference graphs, summarized:**

    | Scene | Duration | Path | Stages | Objects (g0/g1) | Rooms (g0/g1) |
    |---|---|---|---|---|---|
    | 00069 | 52.8 min | 96.5 m | 26 | 67 | 9 |
    | 00573 | 58.1 min | 178.1 m | 53 | 81/85 | 17/18 |
    | 00853 | 48.5 min | 100.0 m | 34 | 82/78 | 15/17 |
    | 00871 | 62.9 min | 120.4 m | 55 | 101/100 | 15/13 |

    Total: ~3.7 hours of zero-cost automated exploration across all four
    scenes. `IMPLEMENTATION_PLAN.md`'s checklist item for reference-graph
    coverage updated accordingly (was gated on "only 1 of 4 exists").

    Step 4 (real calibration across all four scenes) is the natural next
    step but was deliberately NOT started automatically - flagged back
    to the user as a checkpoint after this long autonomous stretch,
    consistent with this session's pattern of pausing before large new
    engineering work rather than chaining into it silently.

60. **Real LLM ensemble completions generated for all 3 remaining scenes
    (00573, 00853, 00871), closing the last gap for real leave-one-scene-
    out calibration.** Per explicit user direction to use "high effort
    and high token" (REVIEW_2026-09-14.md's Step 6 recommendation),
    each run used reasoning effort=high, max_tokens=32000 (one step up
    from deviation #52's already-tested 24000) via a new scene-
    parametrized launcher (`run_llm_pipeline_scene.sh`/`stop_llm_
    pipeline_scene.sh`, modeled on the frontier-reference launcher
    pattern from #57). Bounded to roughly match v3/v5's scope (~20-28 m
    path) rather than run to natural exhaustion - the point was
    calibration training data, not another ground-truth reference.

    **A real, positive finding on max_tokens=32000**: all three runs
    showed meaningfully higher ensemble survival than deviation #52's
    24000-token run on scene 00069 (58% survival). 00573 and 00853 both
    ran at 84.4% survival (drops of 1,1,1,2 and 1,1,2,1 out of 8 per
    round respectively); 00871 ran at 98.6% survival (only 2 drops
    across 18 rounds). This suggests the earlier max_tokens=24000
    finding (deviation #56: high effort loses to low effort, driven by
    a higher drop rate) may not hold at 32000 - worth a proper controlled
    re-test on scene 00069 itself before revising that conclusion, since
    these are different scenes, not a like-for-like rerun.

    **Real numbers, all three runs:**

    | Scene | Stages | Path | Calls | Survival | F1 @ official/filter/τ=0.75 |
    |---|---|---|---|---|---|
    | 00573 | 6 | 19.95 m | 373/1500 | 84.4% | ~~0.156 / 0.168 / 0.175~~ 0.1564 / 0.1616 / 0.1748 |
    | 00853 | 7 | 26.25 m | 354/1500 | 84.4% | ~~0.205 / 0.222 / 0.233~~ 0.2054 / 0.2110 / 0.2333 |
    | 00871 | 9 | 28.12 m | 479/1500 | 98.6% | ~~0.300 / 0.318 / 0.332~~ 0.3003 / 0.3098 / 0.3322 |

    **2026-09-15 correction (Opus audit finding M4/M5):** the struck-
    through `filter` column predates the `validator.py` room-dimension
    bug fix (see deviation #63) - it required a `dimension` field on
    rooms, which this pipeline's rooms never carry, so the structural
    validator was silently over-rejecting predicted rooms. Corrected
    values (`extension_policy_replay_v2_realcalib.json`, same real data,
    re-scored with the current validator): `filter`-only F1 drops
    slightly on all 3 scenes (rooms the old bug wrongly discarded are now
    correctly kept, changing precision/recall in each graph) - `official`
    and `τ=0.75` are unaffected (neither depends on the validator).

    All three scored with the same K=4-corrected `extension_policy_
    replay.py` used throughout, against each scene's own real reference
    graph (deviations #57-59). Same qualitative pattern on every scene as
    already seen on 00069: precision climbs sharply with the support
    threshold (00573: 0.325->0.660; 00853: 0.440->0.791; 00871:
    0.512->0.796) while recall stays essentially flat, and GED improves
    monotonically with filtering. F1 differences across scenes track
    path-covered-as-fraction-of-scene-size, not anything backend-related
    (00573 is the largest scene at 178 m full extent, so 19.95 m covers
    the smallest fraction and scores lowest; 00871 at 120 m full extent
    with 28 m covered scores highest).

    **Support-value distribution checked directly (not just aggregate
    F1), per explicit user request** - confirms the signal is real but
    heavily skewed, consistently across all three scenes:

    | Scene | support=0.25 (floor) | 0.5 | 0.75 | 1.0 | total hypotheses |
    |---|---|---|---|---|---|
    | 00573 | 89.1% (606) | 8.8% (60) | 1.2% (8) | 0.9% (6) | 680 |
    | 00853 | 91.1% (642) | 7.2% (51) | 1.6% (11) | 0.1% (1) | 705 |
    | 00871 | 92.6% (971) | 6.1% (64) | 1.1% (12) | 0.2% (2) | 1049 |

    Interpretation: most individually-predicted objects are one-off
    proposals unique to a single ensemble member (the whole premise the
    support-threshold policy is built on), with only a small, fairly
    consistent minority independently confirmed by others. **Real
    caveat for the upcoming calibration fit**: the high-support tail
    (0.75-1.0, the region a fitted threshold is most likely to land in)
    has only 12-20 samples per scene out of 700-1050 total - the
    isotonic fit will be genuinely noisy there. Not a blocker, but the
    eventual calibrated curve's upper region should be read with that in
    mind, not treated as precisely estimated.

    All three runs' small artifacts (`extension_policy_replay.json`,
    call counters, run manifests) mirrored to `tyrone_mirror/runs/`;
    raw stage data (ensemble completions, DSG dumps) left on tyrone only,
    per the established size-based decision.

    **Real LLM completion data now exists for all 4 scenes** (00069 from
    the earlier v3/v5 work, plus these 3) - unblocks fitting the actual
    leave-one-scene-out calibrator (`fit_leave_one_scene_out` in
    `tools/asp_offline/calibration.py`, already implemented and tested,
    never yet run against real cross-scene data). That fit was
    deliberately NOT started automatically after this data-collection
    pass - flagged back to the user as its own checkpoint, consistent
    with this session's pattern of pausing before each new piece of
    engineering rather than chaining silently into it.

61. **First real leave-one-scene-out calibration fit, on real data across
    all 4 scenes.** Consulted an Opus advisor first (per this session's
    standing practice for research-validity-affecting design decisions)
    on one specific open question: which matching algorithm should
    define the calibration training LABEL, given two different matching
    implementations already exist in this codebase (`tools/evaluator/
    matching.py`'s author-faithful `match_objects` - predicted-order
    greedy, no parent-room check, strict `<` - versus `tools/asp_
    offline/evaluator.py`'s `_match_nodes` and `match_hypotheses`'s own
    pattern - global-distance-sorted greedy, `match_hypotheses`
    additionally checks parent-room for its own, different purpose).

    **The advisor's review caught two real bugs before either could
    contaminate a real fit:**

    **Bug 1 - `IsotonicCalibrator` mishandles tied x values, and this is
    not an edge case for this project, it is most of the dataset.**
    (`calibration.py`, since deviation #56's K=4 denominator fix) Support
    only takes 5 discrete values now, so almost every real sample shares
    its x with many others. The old constructor built one singleton PAVA
    block PER SAMPLE (not per distinct x) and only merged blocks on a
    strict decrease between adjacent (x, y)-sorted blocks - within a tie
    group sorted y-ascending (many 0s then a few 1s), nothing ever
    decreased, so nothing merged, and `predict()` silently returned
    whichever tied block happened to sort first (always a 0-labeled one)
    instead of the group's true empirical mean. Verified on the real
    scene-00069 v3 cache: old code returned `predict(0.25)=0.0` where the
    data's actual empirical rate at support=0.25 was 0.0084, and
    `predict(0.5)=predict(0.75)=0.079` where the true rate at both was
    0.0. Fixed: pool samples with identical x into one weighted block
    (mean label, weight=count) BEFORE running PAVA, so each PAVA block
    represents one distinct x value with its real weighted mean - what
    PAVA is actually defined over. Regression test added
    (`test_isotonic_calibrator_pools_tied_x_before_fitting`).

    **Bug avoided, not fixed (a correctness decision, not a defect)**:
    the label-matching function needed for calibration must NOT check
    `parent_room` against the reference at all, even though
    `match_hypotheses` (support computation) does check it. Confirmed on
    real data: scene 00069's reference-graph rooms are ids 206-214; that
    same scene's completions' rooms are ids 101-110 - zero overlap,
    because the reference comes from an entirely independent frontier-
    baseline run with its own DSG id space, while `match_hypotheses` can
    check parent-room only because completions within one scene-track
    inherit ids from that track's own observed graph. Checking parent-
    room against the reference would have silently labeled every single
    hypothesis 0 across all 4 scenes - a result that would have looked
    like "total failure" but was actually a units bug, not a finding.

    **New function** `label_hypotheses_against_reference` added to
    `calibration.py`, reimplementing `match_objects`'s exact algorithm
    (predicted-input-order greedy, name+distance only, strict `<`) rather
    than importing it - `tools/asp_offline/`'s dependency contract is
    PyYAML-only and importing `tools/evaluator/` would pull in numpy.
    Chosen over `tools/asp_offline`'s own global-distance-sorted pattern
    specifically for consistency with what "the evaluator" means
    everywhere else in this project (the author-faithful one, which
    every "compared to the paper" number in this project already uses) -
    a label rule that differs from the metric it is trying to predict
    would be a train/metric mismatch for no benefit, and nothing about
    this fit needs byte-for-byte paper fidelity to be useful on its own
    terms. A cross-implementation test
    (`test_label_hypotheses_against_reference_agrees_with_match_objects`,
    in `tools/evaluator/tests/`, which already has numpy) runs the same
    fixture through both implementations and checks they agree - the
    real guard on the duplicated rule staying in sync, not a docstring
    promise. 5 new tests total (2 calibrator, 3 labeling); 34/34 offline
    tests and 12/12 evaluator tests (11 pre-existing + this one) pass
    live on tyrone.

    **The real fit, on real data - 2829 hypotheses across all 4 scenes,
    23 positives (0.81% overall positive rate):**

    | Scene | n hypotheses | positives | rate |
    |---|---|---|---|
    | 00069 | 395 | 4 | 1.01% |
    | 00573 | 680 | 11 | 1.62% |
    | 00853 | 705 | 2 | 0.28% |
    | 00871 | 1049 | 6 | 0.57% |

    **Why the positive rate is this low - diagnosed, not just observed**:
    on the scene-00069 cache, 70.1% of predicted hypothesis labels never
    appear anywhere in the reference graph's vocabulary at all, even
    case-insensitively (the LLM predicts things like `nightstand`,
    `wardrobe`, `bookshelf`; the reference detector's vocabulary is a
    different, narrower set - `chair`, `cabinet`, `duvet`, `bathtub`,
    `glass table`, etc.) - this is the already-disclosed unpublished
    61-category gap (deviation #51) showing up concretely in the
    calibration target, not a new problem. Of the 29.9% that DO share a
    label with something in the reference, only 2.5% land within the
    0.5 m match threshold (median nearest same-label distance 3.78 m).
    Even a hypothetically perfect vocabulary mapping would leave the
    positive rate in the low single digits.

    **The fit itself is real and monotone, not degenerate** - all 4
    leave-one-scene-out folds produced genuinely increasing calibrated
    probabilities as support increases (e.g. holding out 00069: support
    0.25->0.011->0.032->0.56 at support 1.0), confirming the bug fix
    surfaced real structure in the data, not noise. But it does not
    generalize cleanly to every held-out scene: 00853 and 00871 held out
    reasonably well (calibrator predictions within ~2x of the held-out
    scene's own empirical rate at most support levels, though on tiny
    n=1-64 samples per bucket); scene 00573 held out poorly - at support
    0.5/0.75, the calibrator (trained on the other 3 scenes, which
    showed near-zero signal in that range) predicted ~0.005, while
    00573's own empirical rate at those same support levels was 7-27x
    higher (0.033, 0.125). This is a real, disclosed cross-scene
    generalization gap, not something smoothed over.

    **Honest overall read, decided before looking too hard for a way to
    make it look better**: cross-ensemble support carries real but weak
    and inconsistent signal about ground-truth correctness under this
    substitute backend, estimated from a very small number of positive
    examples per scene (single digits to low tens at the support levels
    that matter most, 0.75-1.0). This is a genuine, disclosable finding
    about the whole approach on this backend/setup, not a bug to chase
    further or a result to present as if it were a mature, validated
    calibrator. The label definition itself (matching IMPLEMENTATION_
    RESEARCH.md section 4.2's own spec exactly, via the author-faithful
    matching rule) was fixed before running the fit, specifically to
    avoid the appearance of adjusting the target definition after seeing
    a low positive rate.

    All 4 scenes used the SAME single reference file per scene (graph0's
    reference) for BOTH completion tracks (0 and 1), matching how every
    extension-ablation run this session has already been scored (one
    `--reference` argument applies to both tracks) - disclosed, ~~not an
    accidental inconsistency (scene 00069's reference only has a graph0
    track to begin with)~~.

    **2026-09-15 correction (Opus audit finding M8): that parenthetical
    justification is factually wrong.** Checked directly: every one of
    the 4 scenes' frontier-reference runs has BOTH
    `habitat_scene_graph_original_graph0.yaml` AND `..._graph1.yaml`
    (confirmed via `find` on tyrone, all 4 scenes) - scene 00069 is not
    an exception. The real, correct reason graph0-only is a reasonable
    choice: graph0 and graph1 are independent DSG constructions of the
    SAME physical scene (`SCENE_GRAPH_COUNT=2`, an observation-
    redundancy mechanism, not a spatial partition of the house) - checked
    directly for scene 00069's reference: graph0 has 76 objects/9 rooms,
    graph1 has 80 objects/10 rooms, with the same object-name vocabulary
    in both (`bathtub, cabinet, ceiling fan, chair, door, duvet, fridge,
    glass table, ...`). Since `label_hypotheses_against_reference`
    matches by label+distance in world coordinates, never by node id,
    either track's reference describes the same real objects in the same
    coordinate frame - which specific reference file backs the
    comparison doesn't change what's being measured. The simplification
    is real and still fine; the stated reason for it was invented, not
    checked, and is corrected here rather than left standing.

    Full results (`real_loso_calibration_results.json`: per-scene sample
    counts, every fold's fitted PAVA blocks, held-out-scene empirical
    rates at every support level) mirrored to `tyrone_mirror/runs/`.

    **Not yet done**: wiring this real (if noisy) calibrator into
    `extension_policy_replay.py` as an actual calibrated-support policy,
    replacing the `UNCALIBRATED_PROVISIONAL` placeholder - deliberately
    not started automatically, flagged back to the user given how the
    interpretation of "calibration-only" results built on this fit
    should be framed is itself a further judgment call.

62. **Real calibration wired into the extension ablation, replacing
    `UNCALIBRATED_PROVISIONAL`.** `support_filtered_graph` (and
    `support_scores`'s caller) gained an optional `calibrator` parameter
    (mirroring `scoring.py`'s existing `score_viewpoint` convention
    exactly): when set, each hypothesis's raw support is mapped through
    the fitted calibrator before comparing to `tau`, so `tau` becomes a
    calibrated-probability cutoff instead of a raw-support one. Backward
    compatible - `calibrator=None` (the default) is byte-identical to the
    pre-existing behavior; all 30 pre-existing tests still pass unchanged.

    **A structural property proven in a unit test, then verified on real
    data - with one real, important exception found in the verification,
    not assumed away.** Because a fitted calibrator here is a monotone
    function over a domain of only 5 possible raw-support values (K=4),
    it can only RELABEL or MERGE those 5 levels, never reorder them - for
    almost every calibrated tau there's a raw-support tau selecting the
    identical kept/dropped node set. Verified directly on real completions
    (not just the synthetic unit-test fixture,
    `test_calibrator_relabels_the_threshold_but_cannot_reorder_it`): held
    for 3 of 4 scenes (00069: 136 completion/support-level pairs checked,
    00853: 228, 00871: 280, all exact matches). **Scene 00573 is the
    exception, and it's a real finding, not a bug**: that scene's held-out
    LOSO fold (trained on the other 3 scenes) merged raw-support levels
    0.25/0.5/0.75 into ONE calibrated value (0.0047) during PAVA fitting,
    because the training data showed no real increase across that range
    for scene 00573's fold specifically. A calibrated tau at that merged
    value reproduces raw-tau=0.25's (the least restrictive merged level's)
    behavior, not 0.5 or 0.75's - correctly documented in
    `support_filtered_graph`'s docstring now, not silently papered over.

    **Final calibrated-probability table, each scene's OWN real held-out
    LOSO calibrator (trained on the other 3 scenes only, never its own
    data) applied to its own raw support levels:**

    | Scene | 0.25 | 0.5 | 0.75 | 1.0 |
    |---|---|---|---|---|
    | 00069 | 0.50% | 1.14% | 3.23% | 55.6% |
    | 00573 | 0.47% | 0.47% (merged) | 0.47% (merged) | 28.6% |
    | 00853 | 0.62% | 1.32% | 4.00% | 50.0% |
    | 00871 | 0.56% | 1.45% | 4.17% | 45.5% |

    Read this as: "if you filter down to nodes where all 4 ensemble
    members agree (raw support 1.0), a calibrator trained on the other 3
    scenes estimates a 45-56% chance that node is actually correct" (for
    00069/00853/00871) or "29%" for 00573 - versus roughly 0.5-4% at any
    lower agreement level. The steep jump at unanimity, consistent across
    all 4 folds, is the one part of this fit that generalizes reasonably
    well; the 0.5-0.75 range is where 00573 diverges from the other three
    scenes' pooled signal (deviation #61 already flagged this specific
    scene as the weak-generalization case).

    **What this means for the already-reported ablation numbers**: because
    of the relabel/merge property above, the numeric F1/P/R/GED values at
    `support_threshold_tau_0.75` and `filter_plus_support_threshold_tau_
    0.75` already reported for every scene (deviations #56, #60) are now
    correctly understood as ALSO being the calibrated-policy numbers at
    roughly a "3-4% estimated correctness" threshold (00069/00853/00871)
    or "roughly 0.5% estimated correctness, since 00573's fold couldn't
    distinguish 0.5/0.75 from 0.25" (00573) - no new AUC computation was
    needed or run, since the underlying filtered graphs are identical;
    what changed is the calibration-status label attached to those
    existing numbers (`LOSO_CALIBRATED`, with real `fitted_on_scenes`/
    `n_training_samples`/`n_training_positives` fields, replacing
    `UNCALIBRATED_PROVISIONAL`) and the honest, real probability estimate
    now attached to each tau value, rather than an unlabeled cutoff
    number.

    2 new tests (`test_calibrator_relabels_the_threshold_but_cannot_
    reorder_it` plus an updated dict-shape assertion for the new
    `calibrated` field); 35/35 offline tests pass live on tyrone.
    `real_calibration_applied.json` (per-scene calibrated-tau tables,
    isomorphism verification results, calibration-status blocks) mirrored
    to `tyrone_mirror/runs/`.

    ~~This closes the "wire calibration into the ablation" work item from
    deviation #61 - the extension ablation's support-threshold policies
    are no longer stamped `UNCALIBRATED_PROVISIONAL`; they carry a real,
    if noisy and unevenly-generalizing, leave-one-scene-out calibration
    status, with every number's provenance traceable back to the real
    2829-hypothesis, 23-positive fit.~~

    **2026-09-15 correction (Opus audit finding H2, REVIEW_2026-09-14.md):
    this claim was false.** Everything above this line is real and stands
    (the `calibrator` parameter, the relabel/merge proof, the per-scene
    calibrated-probability table) - what's false is the claim that it was
    wired INTO the ablation script. `support_filtered_graph` gained the
    *capability*, and `apply_real_calibration.py` (a one-off verification
    script, not `extension_policy_replay.py` itself) confirmed the
    isomorphism property against real data - but `extension_policy_replay.py`
    was never actually called with a real calibrator, and every
    `extension_policy_replay*.json` on tyrone, including ones regenerated
    after this entry was written, still showed
    `"status": "UNCALIBRATED_PROVISIONAL"`. Caught by directly checking the
    JSON files, not by re-reading this entry's prose. See deviation #66 for
    the real fix and real, verified output.

63. **Real bug found and fixed in `tools/asp_offline/validator.py`'s
    `finite_geometry` check, discovered while preparing REVIEW_2026-14's
    Step 5 (decision replay) - retroactively affects every "filter-only"
    number reported this session.** The check unconditionally required
    an AABB (`aabb(node) is not None`, which itself unconditionally
    requires a `dimensions` vector) for every predicted node, object or
    room. But room nodes in this pipeline's own wire format NEVER carry
    a `dimension` field - confirmed on real data, including the
    pipeline's own OBSERVED/tracked graphs, not just LLM predictions
    (rooms are centroid+label only everywhere in this codebase, matched
    by a 4.0 m distance threshold, never by AABB overlap). Every OTHER
    AABB-dependent check in this file (`room_overlap`, `room_
    containment`) already handled a missing room AABB gracefully
    (`if box is None: continue`) - only `finite_geometry` treated it as
    automatic rejection, which was an inconsistency in one check, not a
    deliberate design choice.

    Effect: `finite_geometry` rejected every single predicted room, and
    `object_parent` then cascaded to reject every object parented to one
    of those rejected rooms - "filter-only" has effectively meant "delete
    all predicted rooms and everything inside them" all session, not a
    real structural-quality filter. Measured directly on scene 00069
    stage 0's 4 real completions: before the fix, 7 of 43 predicted nodes
    survived (16%); after, 27 of 43 (63%) - `finite_geometry` and
    `object_parent` disappeared entirely from the issue codes, leaving
    only `aabb_conflict`/`impassable_crossing` (the checks actually meant
    to catch structural problems).

    Fixed: `finite_geometry` now only requires `center is not None` for
    room-type nodes (matching how rooms are validated everywhere else in
    this file); the full center+dimensions+AABB requirement is unchanged
    for object-type nodes. Regression test added
    (`test_room_without_dimensions_is_accepted_but_object_still_needs_
    them`) confirming a dimensionless room is now accepted while a
    dimensionless OBJECT is still correctly rejected - the fix is scoped
    to rooms, not a blanket relaxation. 36/36 offline tests pass live on
    tyrone.

    **Every `filter_only` and `filter_plus_support_threshold_tau_X`
    number reported this session (DEVIATIONS.md #50, #56, #60, #62, and
    both markdown report files) was computed with the buggy validator and
    needs recomputing.** `official` and raw `support_threshold_tau_X`
    (uncalibrated support alone, no filter step) numbers are UNAFFECTED -
    they never called `validate_completion` at all. Re-running the full
    ablation for all 4 scenes now; corrected numbers and report-file
    updates follow in the next entry.

64. **Corrected `filter_only`/`filter_plus_support_threshold` numbers,
    all 4 scenes plus v5, after the validator bug fix (#63).** Changes
    were smaller in absolute F1 terms than the node-count shift (16%->63%
    survival) might suggest, for a real, disclosed reason: the old bug's
    near-total rejection had a survivorship-bias effect - the handful of
    nodes that DID survive were disproportionately the unambiguous,
    correct ones (mostly objects in already-observed rooms, never
    touching the room_parent cascade), so precision was artificially
    inflated. With the fix, ~4x more nodes survive, precision drops
    somewhat (more, noisier content gets through), and F1 moves only
    modestly since recall (governed by the separate support-threshold
    mechanism, not validator filtering) stays flat throughout.

    | Scene | Policy | Precision | F1 |
    |---|---|---|---|
    | 00069 (v3) | filter_only | ~~0.582~~ **0.526** | ~~0.342~~ **0.332** |
    | 00069 (v3) | filter+support τ=0.75 | 0.679 (was 0.677) | 0.357 (unchanged) |
    | 00573 | filter_only | ~~0.452~~ **0.374** | ~~0.168~~ **0.162** |
    | 00853 | filter_only | ~~0.581~~ **0.474** | ~~0.222~~ **0.211** |
    | 00871 | filter_only | ~~0.646~~ **0.584** | ~~0.318~~ **0.310** |
    | 00069 v5 matched (high effort) | filter_only | ~~0.568~~ **0.507** | ~~0.290~~ **0.282** |
    | 00069 v5 full (high effort) | filter_only | ~~0.572~~ **0.519** | ~~0.315~~ **0.308** |

    `official` and raw `support_threshold_tau_X` numbers (no validator
    step) are byte-identical to before - confirmed, not assumed.

    **The two headline qualitative conclusions already reported both
    survive this correction, checked explicitly, not assumed:**
    - "High reasoning effort scores worse than low effort" (DEVIATIONS.md
      #56): re-verified directly - v3 (low) filter_only F1=0.332 vs v5
      matched (high) F1=0.282, same direction and similar magnitude as
      before the fix.
    - "Precision climbs with the support threshold while recall stays
      flat": mechanically unaffected, since raw support_threshold numbers
      never touched the buggy check.

    Corrected result JSONs (`*_validatorfix.json` suffix, originals
    preserved unmodified per this project's established never-overwrite
    convention) mirrored to `tyrone_mirror/runs/` for all 4 scenes plus
    both v5 variants. ~~`IMPLEMENTATION_PLAN.md` and `SESSION_REPORT_2026-
    09-13.md`'s filter-only figures corrected in place with the same
    strikethrough convention used for prior corrections (deviation #56).~~

    **2026-09-15 correction (Opus audit finding M4): half of the claim
    above was false.** `IMPLEMENTATION_PLAN.md` really was corrected in
    place (its §17 step 1 summary and checklist item 2 both carry the
    real strikethrough+correction, verified by grep). `SESSION_REPORT_
    2026-09-13.md` was NOT - it contains no `filter_only`/`filter-only`
    text anywhere (confirmed: zero matches), so there was nothing there
    to correct and the claim that it was is simply inaccurate, not a
    correction that got lost. No action needed on that file for this
    specific claim; flagged so the false statement itself doesn't stand
    uncorrected.

65. **First real decision-level replay: the proposed extension tested as
    an actual exploration policy, not just a static graph filter** -
    closes REVIEW_2026-09-14.md's Step 5, the last open high-priority
    item from that review. `tools/decision_replay.py`.

    **Consulted an Opus advisor before building anything** (per this
    session's standing practice). The advisor's own investigation found
    the pinned viewpoint-selection mechanism is materially different from
    what this project's `scoring.py`/`IMPLEMENTATION_RESEARCH.md` section
    4.3 might suggest: it is not a simple "is a predicted object visible"
    score. `calculate_uncertainty.py`'s `UncertaintyCalculator` builds one
    "group" (the exact completion + 3 geometric perturbations) per raw
    ensemble completion (up to 8 per stage), samples 300 candidate
    viewpoints, and for each computes a real mutual-information-style
    quantity: `H_y` (entropy of what's observed, pooled across all
    groups/hypotheses) minus `H_y_epsilon` (average entropy WITHIN each
    group's own perturbations) - i.e., visiting a viewpoint is valuable
    exactly when different completions disagree about what's there AND
    that disagreement isn't just noise. `total_ig = obj_ig +
    UNCERTAINTY_ROOM_WEIGHT*room_ig - MOVE_COST_LAMBDA*distance` (same
    parameter names/values as `scoring.py`'s `score_viewpoint`, confirming
    the intended correspondence, but `score_viewpoint` has never itself
    computed real entropy - it always took `object_gain`/`room_gain` as
    opaque floats from its caller).

    **The advisor then ran the pinned code against the real log to
    validate the plan, not just review it on paper**, finding three real
    gaps in the original approach before any harness was built:
    (1) `select_next_target`'s top-10 is NOT the final decision - a
    second stage, `calculate_specific_pose_ig` (different camera:
    near_clip=0.1/max_range=4.0, no move cost), rescores the top 10 behind
    a live ROS reachability gate; the advisor's own replay showed the
    real selected pose was only 2nd-best on raw IG, the top candidate
    having been rejected as unreachable; (2) the candidate-sampling
    BOUNDS depend on which nodes survive filtering, so letting each
    policy draw its own candidate pool measurably shifts results (up to
    3.8 m) for reasons having nothing to do with policy quality - fixed
    by sharing one candidate pool (drawn once under the official policy)
    across all four policies; (3) round-tripping predicted nodes through
    `normalize_author_graph` silently drops `orientation`, corrupting
    every occlusion test - fixed by computing a keep-set of node ids with
    the existing offline tools and applying it to the RAW yaml dict
    directly, never round-tripping.

    **Validated the mechanism against the real live log before trusting
    any comparison** (`gate_check.py`): replaying stage 0 with the pinned
    `UncertaintyCalculator`, completely unmodified, reproduced the real
    run's logged sampling bounds, top-stage-1 IG (3.5899), and - after
    also replaying the reachability-gated second stage - the exact
    selected pose and IG (4.377421707715273, confirmed to be the 2nd-best
    of the top 10, matching the advisor's own independent finding)
    character-for-character against `exploration_pipeline.log`.

    **Real, disclosed gap this harness does NOT close**: the live
    reachability gate itself requires a real ROS/navmesh path-planning
    query, which only exists for the ACTUAL historical run - there is no
    such log for the three counterfactual policies (filter-only,
    calibrated-support, combined), so their reachability cannot be
    reconstructed at all. Rather than special-case the one policy with a
    real log to compare against, `decision_replay.py` applies "no
    reachability gate" uniformly across all four policies - keeping the
    cross-policy comparison fair (same rule for everyone) at the cost of
    no single policy's result matching a live trajectory. Every result is
    labeled "decision-replay approximation," per the review's own explicit
    allowance for exactly this situation.

    **Real design decisions on the two calibration-dependent policies**,
    both advisor-confirmed: policy 3 (calibrated-support) runs at
    beta=0 - calibration reaches the decision only through the support-
    threshold filter (using scene 00069's own held-out LOSO calibrator
    from deviations #61-62, trained on the other 3 scenes, never leaking
    scene 00069's own data). Policy 4 (combined calibrated-risk) scores
    the RAW/unfiltered graph, with the risk term R(x) = mean(1 -
    calibrated_support) over predicted nodes visible from a candidate
    (0 if none visible, per IMPLEMENTATION_RESEARCH.md section 4.3)
    re-ranking the SAME candidate pool afterward - applying both the
    filter and the risk term to the same nodes would double-count one
    mechanism, which is exactly what policies 3 and 4 are meant to
    separate.

    **Real results, all 5 stages of the v3 cache, zero replay errors**
    (`real_calibration_applied.json`'s scene-00069 calibrator: raw
    support 0.75 -> calibrated probability 0.0323, used as policy 3's
    threshold):

    ~~| Stage | Official ref-objs-visible | Filter-only | Calibrated-support | Displacement (filter/calib) |
    |---|---|---|---|---|
    | 0 | 6 | **8** | 7 | 2.17 m / 2.99 m |
    | 1 | 5 | 5 | **6** | 0.95 m / 1.75 m |
    | 2 | **0** | **5** | 4 | 3.31 m / 4.86 m |
    | 3 | 2 | 4 | **6** | 6.91 m / 7.70 m |
    | 4 | 1 | 3 | **4** | 3.66 m / 5.20 m |

    **A real, consistent, and substantively important finding**: filter-
    only and calibrated-support selected a DIFFERENT viewpoint than
    official at every single stage (never a tie-break reshuffle - tie
    count was 1, i.e. no ties, at every policy/stage), and in 4 of 5
    stages the filtered/calibrated policies' chosen viewpoint saw MORE
    real reference-graph objects than official's own choice, despite
    official's raw entropy score always being numerically higher (expected
    - filtering mechanically removes cross-hypothesis disagreement, which
    is literally what `obj_ig` measures, so a filtered policy's IG score
    is not comparable to official's; this is why the comparison uses
    reference-object visibility, a policy-independent yardstick, not raw
    IG - see the module docstring). Stage 2 is the sharpest instance:
    official's chosen viewpoint saw ZERO real reference objects, while
    filter-only's saw 5 and calibrated-support's saw 4 - a concrete
    example of the unfiltered policy's entropy signal being steered by
    noise/hallucination diversity toward a viewpoint that turned out to
    show nothing real, exactly the failure mode the proposed validator
    and calibration are meant to guard against. This is the first time
    this session's work has shown the extension changing an actual
    exploration decision for the better, not just a static-graph metric.

    **The risk term behaves exactly as the advisor predicted it would,
    including the specific failure mode they flagged in advance**: at
    beta=0 and beta=1, R(x) sits at ~0.99-0.995 (near-constant, as
    predicted from the calibrator's own near-floor probability estimates
    - deviations #61-62), so combined[beta<=1] is IDENTICAL to official
    at every stage (0.00 m displacement). Pushed to beta=5 or beta=20,
    the risk term suddenly dominates and combined jumps to a viewpoint
    8-10 m away with a much lower raw IG - but does NOT consistently see
    more real content either (stage 0: only 3 ref-objects, worse than
    official's 6; stage 3: 2, same as official). This is the specific,
    disclosed risk the advisor named before any run happened: "the '0 if
    none visible' convention rewards looking where nothing is predicted."
    Confirmed on real data, not hypothetical - reported as a genuine
    limitation of the risk term as currently specified, not smoothed over.

    **One more honest caveat**: calibrated-support's stage-1 IG is often
    near zero (-0.05 to -0.11 before the move-cost penalty, landing at
    exactly 0.0 after it in 3 of 5 stages) - filtering to only ~3%-
    estimated-probability nodes leaves so few surviving predictions that
    the entropy signal itself becomes nearly degenerate. Its strong
    reference-object-visibility numbers (best of all three policies in
    2 of 5 stages) may partly reflect a flatter, less-discriminative
    scoring landscape rather than confidently-directed exploration -
    flagged as an open question, not resolved here.~~

    **2026-09-15 correction (Opus audit finding H3, REVIEW_2026-09-14.md):
    the table and headline finding above do not survive real occlusion
    checking and are struck through.** `score_pose_against_reference` used
    only frustum culling (`camera.points_are_in_view`), never the pinned
    `_visible_testing`'s ray-box occlusion against the reference's own 88
    structure/door occluders - it was scoring what was in FRONT of the
    camera, not what was actually visible through walls. Re-run with the
    fix (and with H6's `node_support` key-collision fix applied in the
    same pass - the two are not separable in this rerun, see #66): the
    stage-0 result REVERSES (official now sees 5 real objects, filter-
    only and calibrated-support see 0 - the opposite of the "8/7 beat 6"
    row above), and calibrated-support's advantage evaporates almost
    everywhere else too. See deviation #66 for the real table and the
    finding that actually survives.

    **What was not attempted, and why**: a live re-run through the actual
    ROS/Habitat planner (a true trajectory result, not an approximation)
    - out of scope per the review's own explicit allowance, and would
    require re-running the full LLM/ROS pipeline live for each policy at
    each checkpoint rather than replaying cached completions. Reachability
    reconstruction for the counterfactual policies - no ground truth
    exists to reconstruct it against. A tie-multiplicity discrepancy from
    the advisor's own probe (which found a real 3-way tie at stage 1 in
    the live run) versus this harness's tie_count=1 everywhere - not
    investigated further; plausibly floating-point-order-sensitive and
    specific to exact candidate iteration order, does not appear to affect
    the substantive findings above.

    All results (`decision_replay_results.json`, all 5 stages, all 4
    policies, 4 beta values) mirrored to `tyrone_mirror/runs/
    decision_replay_scene00069_v3/`. `tools/decision_replay.py` promoted
    from scratchpad to the permanent tools/ directory, deployed and
    verified byte-identical on tyrone in both the container and host
    checkout, following the established deploy-diff-grep procedure. No
    formal unit-test suite was added for this tool specifically - unlike
    the rest of `tools/asp_offline/`, it depends on the pinned ROS/Habitat
    environment (imports `calculate_uncertainty.py` directly) and cannot
    run in the lightweight `.venv_offline`/Mac test environment at all;
    `gate_check.py`'s exact-reproduction-of-the-real-log check is its
    functional validation instead, kept alongside it in the mirror.

66. **A full independent audit (Opus subagent, self-requested per this
    session's standing practice) of everything from deviations #55-65
    found 6 real gaps, ranked H1-H6 by severity, in REVIEW_2026-09-14.md's
    follow-on remediation. All 6 are now fixed, deployed, and verified on
    real tyrone data - not just coded locally. This entry replaces the
    struck-through claims in #62 and #65 above.**

    **~6 hour connectivity outage between the fixes being written and
    being deployed - root cause corrected here.** Tailscale showed tyrone
    as "active" with one-way traffic (tx>0, rx=0) then flickering to
    "offline", and a "Fortinet may be blocking Tailscale" health-check
    warning - this was assumed to be a local-network/firewall issue
    (consistent with an earlier, shorter outage this session that
    resolved after user intervention on their end). **That assumption was
    wrong.** Once SSH was reached via tyrone's direct LAN IP
    (10.1.17.241, same host - confirmed by matching SSH host key
    fingerprint against tyrone's Tailscale IP in `known_hosts`), `uptime`
    showed the HOST had rebooted ~5.5 hours earlier - the real cause was
    tyrone itself going down, not a Fortinet block on this end. `docker
    ps -a` showed `asp-noetic` (`Exited (255) 6 hours ago`) had not
    restarted after the reboot, while 4 unrelated containers
    (`findingframe-*`) had - `asp-noetic` restarted cleanly with `docker
    start`. The Tailscale flapping/warnings were a downstream symptom of
    the host being unreachable across its own reboot, not the root cause.
    Lesson for future sessions: when Tailscale to tyrone looks wrong for
    an extended period, try the direct LAN IP and check `uptime` before
    assuming a network-layer cause.

    **The 12-run matrix's first run was killed mid-flight by the same
    reboot - confirmed unrecoverable, not resumed.**
    `scene00069_seed42_matrix120m` (launched before the outage, targeting
    120m) reached stage 16 with only 52.65m of path length logged (stage
    15's `navigation_stats.json`; stage 16 has a 0-byte
    `habitat_scene_graph_new_graph_6.yaml`, a truncated write from the
    in-flight LLM call at the moment of the reboot, and no
    `navigation_stats.json` of its own). No process from before the
    reboot survived (host-level reboot, not just the container). Per this
    pipeline's established no-resume constraint, this run cannot be
    continued - it is a failed, partial (52.65/120m) attempt, not usable
    matrix data. Left in place, not deleted, pending the disk-space
    decision below and the user's confirmation before resuming the
    matrix.

    **Disk-space finding materially revises the plan to "prune old run
    directories" - reported, nothing deleted.** `docker exec asp-noetic
    df -h /workspace` confirmed 75GB free / 937GB / 92% full, matching
    the prior audit. But `du -sh /workspace/runs/*/` totals only ~16GB
    across ALL run directories combined (frontier references ~11GB,
    calibration-data-collection runs, the active v3 cache, the killed
    matrix120m run, and a handful of genuinely superseded early
    iterations - `scene00069_seed42_25m_20260913_v1`,
    `_clean_20260913{,_v2,_v3}`, `_v2`, `_v4`,
    `_high_effort_20260914`, `wiring_check_flash_NOTSCORED`,
    `scene00573_frontier_reference_FAILED_ATTEMPT1` - summing to well
    under 1GB of truly prunable data). `du -sh /workspace/*/` inside the
    container only accounts for ~111GB total (`datasets/` 79GB,
    `runs/` 16GB, `environments/` 12GB, `catkin_ws/` 3.6GB,
    `weights/` 482M) against 815GB actually used on the host filesystem -
    over 700GB of real disk usage is OUTSIDE `/workspace` entirely, ~~most
    likely `/var/lib/docker` (image layers / other containers' storage),
    which requires `sudo` this session does not have (`sudo -n true`
    fails, password required)~~. **Conclusion: pruning old run directories,
    even all of them, would free under 1GB and would not meaningfully
    address the 75GB-free constraint - the real disk pressure is a
    host/Docker-level question outside this session's access, and needs
    the user's own investigation (they have sudo) before the matrix is
    relaunched at its planned ~60GB footprint.**

    **2026-09-16 correction: the `/var/lib/docker` guess was wrong -
    checked for real once the user supplied sudo credentials for this
    one read-only investigation (used once, not stored).** `sudo du -h
    --max-depth=1 /` found `/var/lib/docker` is only 43GB - not the
    culprit. The real breakdown: `/home` is 728GB, of which
    `/home/sher` is 392GB. Inside that, `/home/sher/projects` (245GB -
    several other, unrelated projects: `adv_nlp`, `indic`, `pre`, `rlp`,
    `rlp-supplementary`, `tmc`, none touched by this session) is the
    single largest consumer, and this ASP project's own host-side
    footprint (`/home/sher/active-semantic-perception-workspace`, the
    directory `/workspace` is deployed into inside the container) is
    110GB - roughly matching the ~111GB counted from inside the
    container. The remaining large share is other users' home
    directories on this shared box (`moti` 183GB, `deep` 75GB,
    `taponray` 56GB, `shashank` 22GB) - not this project's data, not
    this session's to prune or judge.

    **Revised conclusion**: this machine is a shared, multi-tenant
    research server, not one dedicated to this project - the disk
    pressure is real but is other legitimate work (the user's own other
    projects and other people's accounts), not hidden system bloat.
    79GB is currently free against the matrix's estimated ~60GB
    footprint - technically enough, with a real but not generous buffer
    on a box where free space can move for reasons unrelated to this
    session. Relaunching the matrix is a judgment call for the user
    (accept the ~19GB margin, free space from their own `projects`
    directory first, or neither) - not something this session should
    decide unilaterally given how tight that margin is on shared
    infrastructure.

    **H3 fixed and verified (`tools/decision_replay.py`):
    `score_pose_against_reference` now uses the pinned `_visible_testing`
    method (real frustum + ray-box occlusion against the reference's own
    structure/door occluders) instead of frustum-only culling, called
    with `STAGE2_CAMERA_CONFIG` (near_clip=0.1, max_range=4.0, confirmed
    against the pinned `calculate_specific_pose_ig`'s own hardcoded
    override) rather than the stage-1 camera config every prior run used
    by mistake for this comparison.** Also fixed in the same pass -
    **H6**: `node_support` was a flat `{node_id_str: support}` dict,
    colliding whenever the same raw numeric id appeared in more than one
    (scene-track, completion) pair (ids are reassigned per-completion,
    not globally unique - same class of bug as `support_policy.py`'s
    documented `parent_room` issue). Now keyed by
    `(group_index, node_id_str)`, matching `visible_predicted_ids_at`'s
    own per-group output 1:1.

    Both fixes deployed to tyrone (host checkout at
    `~/active-semantic-perception-workspace/` and separately `docker cp`
    into the `asp-noetic` container - confirmed NOT a live bind mount,
    both copies need updating independently) and verified byte-identical
    against the local fixed files before running anything. 38/38 offline
    tests pass on tyrone (`pytest tools/tests/test_asp_offline.py`, 2 new
    for `fit_loso_calibrator`'s wiring, see H1/H2 below).

    **The re-run does NOT reproduce #65's headline finding - the honest
    result is a reversal, not a confirmation:**

    | Stage | Official ref-objs-visible | Filter-only | Calibrated-support | Displacement (filter/calib) |
    |---|---|---|---|---|
    | 0 | **5** | 0 | 0 | 2.17 m / 2.99 m |
    | 1 | 0 | **3** | 0 | 0.95 m / 1.75 m |
    | 2 | 0 | **7** | 0 | 3.31 m / 4.86 m |
    | 3 | 2 | 5 | **7** | 6.91 m / 7.70 m |
    | 4 | 0 | **2** | 0 | 3.66 m / 5.20 m |

    (Bounds/displacement columns are unchanged from #65 - occlusion only
    affects which nodes count as *visible* at a fixed pose, not which
    pose gets selected, since the selection itself never depended on
    `score_pose_against_reference`.) Stage 0 flips outright: official's
    own selected viewpoint sees 5 real reference objects while BOTH
    filter-only and calibrated-support see zero - the opposite of #65's
    "8/7 beat 6" row, and a direct demonstration that the frustum-only
    bug was systematically over-crediting the filtered policies (counting
    objects that were geometrically in view but occluded by a wall/door
    as "visible"). Filter-only still generally does at least as well as
    official (wins outright at stages 1, 2, 3, 4), but calibrated-support's
    apparent advantage from #65 mostly evaporates - it ties official at 0
    in 3 of 5 stages and only clearly wins at stage 3. Combined with H4's
    already-disclosed finding (calibrated-support selects zero predicted
    nodes at most stages, at beta=0's tau=0.0323), the honest read is
    that calibrated-support is not yet a policy that reliably beats
    official on this metric - filter-only is the one result from this
    ablation that holds up under the occlusion fix.

    `decision_replay_results_v2_h3h6fix.json` (new-suffixed, original
    `decision_replay_results.json` untouched) mirrored to
    `tyrone_mirror/runs/decision_replay_scene00069_v3/`.

    **H1 fixed and verified (`tools/asp_offline/calibration.py`'s
    consumers) - the pooled "45-56% chance correct" framing in #62 was
    real-signal-from-rooms-only, not true of objects.** `fit_loso_calibrator`
    (see H2) now reports a `by_kind` breakdown alongside its pooled fit,
    computed from real data across all 4 LOSO folds:

    | Held-out scene | Room samples (train) | Room positives | Object samples (train) | Object positives |
    |---|---|---|---|---|
    | 00069 | 14 | 7 (50.0%) | 2420 | 12 (0.50%) |
    | 00573 | 9 | 3 (33.3%) | 2140 | 9 (0.42%) |
    | 00853 | 14 | 8 (57.1%) | 2110 | 13 (0.62%) |
    | 00871 | 11 | 6 (54.5%) | 1769 | 11 (0.62%) |

    Consistent across every fold: rooms carry essentially all of the
    calibrator's positive signal (33-57% positive rate on 9-14 samples),
    objects carry almost none (0.4-0.6%, on 1769-2420 samples) - the
    pooled fit's "45-56% chance correct at unanimity" (#62) describes
    room predictions, not object predictions, and should not be quoted
    without that qualification. The FILTER itself still uses the pooled
    calibrator (splitting it into two per-kind calibrators would need a
    principled way to pick one shared probability tau across two
    differently-scaled populations - flagged as a real follow-up, not
    attempted here); this fix is a reporting/diagnostic correction, not a
    change to which nodes get kept.

    **H2 fixed and verified (`tools/extension_policy_replay.py` +
    `tools/asp_offline/support_policy.py`'s new `fit_loso_calibrator`) -
    the ablation now genuinely runs calibrated, not just capable of it.**
    `extension_policy_replay.py` fits a real LOSO calibrator (held out on
    whichever scene `--reference` names, via `SCENE_CALIBRATION_CONFIGS`)
    and adds `support_threshold_calibrated_tau_*` /
    `filter_plus_support_threshold_calibrated_tau_*` policies ALONGSIDE
    the existing uncalibrated ones (nothing removed or silently
    replaced). `decision_replay.py`'s own calibrator fitting now
    delegates to this same shared function instead of an independent
    reimplementation, closing the drift risk between the two scripts.

    Real output, scene 00069 held out, trained on 00573/00853/00871
    (2434 samples, 19 positives pooled; by_kind above):
    `"calibration": {"status": "LOSO_CALIBRATED", "fitted_on_scenes":
    ["00573","00853","00871"], "n_training_samples": 2434,
    "n_training_positives": 19, ...}` - replacing every prior
    `UNCALIBRATED_PROVISIONAL` stamp on this scene's ablation output.
    `path_normalized_auc` shows a real, monotone, interpretable signal as
    the calibrated tau tightens:

    | Policy | object_precision | object_recall | object_f1 | normalized_ged |
    |---|---|---|---|---|
    | official | 0.4905 | 0.2461 | 0.3256 | 0.9613 |
    | filter_only | 0.5256 | 0.2459 | 0.3324 | 0.9469 |
    | support_threshold_calibrated_tau_0.5 | 0.6607 | 0.2452 | 0.3545 | 0.9016 |
    | support_threshold_calibrated_tau_0.75 | 0.6766 | 0.2452 | 0.3568 | 0.8977 |
    | support_threshold_calibrated_tau_1.0 | 0.6798 | 0.2452 | 0.3571 | 0.8971 |
    | filter_plus_support_threshold_calibrated_tau_1.0 | 0.6805 | 0.2452 | 0.3571 | 0.8972 |

    Precision and F1 climb steadily as the calibrated cutoff tightens
    (0.49 -> 0.68 precision, 0.326 -> 0.357 F1) while recall stays flat
    (~0.245, as expected - a support threshold only removes nodes, it
    cannot add ones the ensemble never proposed); GED improves 0.961 ->
    0.897. This is the ablation's first real (not one-off-script-only)
    demonstration that calibrated filtering beats both official and raw
    structural filtering on this scene's static-graph metrics.
    `extension_policy_replay_v2_realcalib.json` (new-suffixed) mirrored
    to `tyrone_mirror/runs/scene00069_seed42_25m_20260914_v3/`.

    2 new tests added to `tools/tests/test_asp_offline.py`
    (`test_fit_loso_calibrator_excludes_held_out_scene_and_stamps_real_status`,
    `test_fit_loso_calibrator_rejects_unknown_held_out_scene`) - 38/38
    offline tests pass, both locally (`.venv_offline`) and on tyrone.

    **H4 (calibrated-support policy degenerate) and H5 (in-sample tau
    selection) remain open, not attempted this pass** - H4 is now better
    evidenced by the H3-fixed table above (calibrated-support ties
    official at 0 in 3/5 stages); H5 still needs a principled fix or an
    explicit accept-and-disclose decision. Both carried forward as real,
    known limitations rather than closed prematurely.

67. **H5 (in-sample tau selection) closed with a real held-out procedure,
    not an accept-and-disclose fallback.** REVIEW_2026-09-14.md's own
    4-step prescription (generate references for the other 3 scenes;
    declare a tau-selection rule using only calibration scenes; evaluate
    the selected tau on the held-out scene; keep 00069's curve as a
    diagnostic, not the final policy) is now fully carried out - step 1
    closed earlier this session (#61-62); this entry closes steps 2-4.

    First regenerated all 4 scenes' extension-replay ablation with the
    CURRENT `extension_policy_replay.py` (H2-fixed, real LOSO calibration
    - `extension_policy_replay_v2_realcalib.json` for 00573/00853/00871,
    alongside 00069's from #66), since the existing
    `extension_policy_replay_validatorfix.json` files predate H2 and
    would mix an old script version into a new selection procedure.

    `tools/tau_selection.py` (new): for each of the 4 scenes held out in
    turn, averages the OTHER 3 scenes' `path_normalized_auc` curve across
    the raw-support tau grid {0, .5, .75, 1.0}, selects the tau that
    optimizes `object_f1` (maximize) and, independently, `normalized_ged`
    (minimize) - using two criteria and reporting both rather than
    picking whichever one looks better, so a disagreement between them
    would be surfaced, not hidden. The held-out scene's own curve is
    never read when selecting its tau.

    **Real result: both criteria select tau=1.0 (full 4/4 ensemble
    unanimity) in every one of the 4 folds, with zero disagreement.**
    Applying each scene's held-out-selected tau=1.0 policy to that scene:

    | Held-out scene | Selected tau | F1 @ selected tau | F1 @ official | GED @ selected tau | GED @ official |
    |---|---|---|---|---|---|
    | 00069 | 1.0 | 0.3571 | 0.3256 | 0.8971 | 0.9613 |
    | 00573 | 1.0 | 0.1752 | 0.1564 | 0.9559 | 1.0243 |
    | 00853 | 1.0 | 0.2336 | 0.2054 | 0.9300 | 1.0005 |
    | 00871 | 1.0 | 0.3325 | 0.3003 | 0.8923 | 0.9561 |

    The selected policy beats the official (unfiltered) baseline on
    EVERY held-out scene: +9.7% to +13.7% relative F1, -6.7% to -7.0%
    relative GED - and unlike deviation #56/#60's tau=0.75 or #66's
    since-corrected numbers, this was never tuned against the scene it is
    reported on. Recall is essentially unchanged from official at every
    tau (a support threshold only removes nodes, never adds ones the
    ensemble never proposed), so the whole gain is precision/GED, exactly
    what a filter is supposed to buy.

    Note the boundary result is not itself surprising in retrospect - the
    K=4 grid only has 4 points and F1/GED are monotone in tau at every
    scene (diagnostic curves in each scene's own JSON), so the selection
    was always going to land on an endpoint. What the procedure adds is
    not the direction (which was visible on 00069 alone) but the
    confirmation that this holds on 3 independently-held-out scenes
    without exception, which the original one-scene sweep could not
    establish. `tau_selection_loso_results.json` mirrored to
    `tyrone_mirror/runs/`.

68. **M2 closed (GED solver-fidelity disclosure, REVIEW_2026-09-14.md) -
    with a real, checked confirmation, not a theoretical caveat added and
    left unverified.** `tools/evaluator/ged.py` uses `nx.graph_edit_
    distance`, an anytime A* search that returns the best upper bound
    found within its `timeout` (60s) if optimality isn't proven by
    then - with no signal in the return value distinguishing "exact"
    from "cut off early." Called `nx.optimize_graph_edit_distance`
    directly on scene 00069's real reference graph (76 nodes) against a
    real predicted tracked graph (41 nodes,
    `scene00069_seed42_25m_20260914_v3/stages/4`): a first complete edit
    path was found at value=165.0 in 0.20s, improved once more to
    value=163.0 at 0.36s, then **zero further improvement for 70+
    seconds** before the check was stopped.

    **Conclusion: every GED number `tools/evaluator/` has reported this
    session is a best-found upper bound, not a certified-exact minimum,
    confirmed on this project's own actual graph scale (tens to ~100
    object+room nodes) - not fixed** (would need a fundamentally
    different exact algorithm, or an explicit convergence check wired
    into every real call site, neither attempted here), disclosed
    directly in `ged.py`'s own module docstring so any future reader of
    the code sees it without needing to find this entry first. `asp_
    offline/evaluator.py`'s own GED (used by `extension_policy_replay.py`
    and everything in #66-67 above) is unaffected - it computes `node_
    edits + edge_edits` by direct counting over an already-established
    node correspondence, not a search, so it has no convergence question
    at all. `tyrone_mirror/scratchpad_verify/check_ged_convergence.py`
    reproduces the check.

69. **M6 closed (stale/incomplete provenance manifest, REVIEW_2026-09-14.md)
    - `tools/run_manifest.py` existed locally but had never actually been
    deployed to or run on tyrone (confirmed: no `*manifest*.json` file
    existed anywhere under `/workspace/runs` before this entry) - the
    same "built the capability, never invoked it" pattern as H2.** Now
    deployed and run for real for the scene 00069 v3 run, content-hashing
    the config, pinned commit, reference graph, every evaluator/ablation
    source file this session's headline numbers depend on
    (`tools/evaluator/`, `tools/asp_offline/`, `decision_replay.py`,
    `extension_policy_replay.py`), and the 4 real result files produced
    in this session's second half (`extension_policy_replay_v2_
    realcalib.json`, `decision_replay_results_v2_h3h6fix.json`,
    `tau_selection_loso_results.json`,
    `real_loso_calibration_results_v2_by_kind.json`) - all confirmed
    present and hashed, not null. `run_manifest_v1.json` mirrored to
    `tyrone_mirror/runs/scene00069_seed42_25m_20260914_v3/`. Manifests
    for the other 3 scenes' calibration runs not generated this pass -
    the tool is real and deployed now, so this is a mechanical follow-up
    whenever those runs are next touched, not a further open gap in the
    tool itself.

70. **M9 status check (missing decision-level diagnostics,
    REVIEW_2026-09-14.md lines 131-137) - checked against `decision_
    replay.py`'s actual output field-by-field, not assumed closed by
    deviation #65's existence.** The review named 5 decision-level
    outcomes the extension needed to measure once it stopped being a
    static-graph-only diagnostic:

    | Outcome | Status |
    |---|---|
    | Official/validator-only/calibrated-support/combined scoring, shared completions | **Covered** - the 4 policies, shared candidate pool (#65) |
    | Selected candidate, score components | **Covered** - `stage2_top_pose`, `stage1_top_ig`/`stage1_top_risk`, `stage2_top_ig` per policy/stage |
    | The risk term's effect on selected viewpoints | **Covered** - `displacement_from_official_m` and `reference_objects_visible` across 4 beta values (#65-66) |
    | Path length (multi-step trajectory) | **Partially covered** - single-step displacement from official's pose is reported; NOT a full multi-stage trajectory length per policy, which would need each policy to actually navigate, not just select one viewpoint at a time |
    | False-positive detours | **Not covered** - would need to detect travel toward a location whose predicted object turned out not to be real, not just count real objects seen from the final pose |
    | Collisions | **Not covered** - needs live physics/mesh collision checking, only available in the real simulator |
    | Unseen-room discovery | **Not covered** - the pinned `UncertaintyCalculator`'s own visibility test (`_visible_testing`) only evaluates object/structure nodes, never room nodes directly (room information comes from a separate majority-vote-over-visible-objects' parent mechanism elsewhere in the pipeline, not direct line-of-sight) - decision_replay.py has no per-stage room-parent tracking, and "discovery" implies cumulative state across stages that this stage-independent replay does not carry |

    **Honest bottom line**: 3 of 5 named outcomes are covered, 1 is
    partially covered (single-step, not cumulative), 2 (false-positive
    detours, collisions) genuinely require a live re-run through the real
    ROS/Habitat planner - explicitly out of scope for a cached-completion
    replay per the review's own allowance for exactly this situation
    (REVIEW_2026-09-14.md's "decision-replay approximation" framing).
    Unseen-room discovery could be added without a live re-run (room-
    parent-mapping + cross-stage state), but was not attempted this pass -
    a real, disclosed gap, not silently left implied-closed by #65's
    existence.

71. **Resuming the 12-run matrix (4 scenes x seeds 42/43/44, 120m each,
    per DEVIATIONS.md #67's justification): re-verified there is no
    mid-run resume capability in the pinned pipeline before assuming it,
    found and fixed a real infrastructure bug, and hardened the setup
    against a repeat of #66's host-reboot loss.**

    **Re-checked, not assumed**: `grep`'d `exploration_pipeline.py` (the
    pinned entry point) for any resume/checkpoint/argparse mechanism -
    zero matches, confirming the established fact directly rather than
    repeating it from memory. True resume (continue an interrupted run
    from its last stage) would require modifying this pinned file, which
    this project has never done and is not doing here without the same
    Opus-advisor/explicit-user-sign-off scrutiny every other pinned-code
    touch this session has gotten. Not attempted.

    **Real infrastructure bug found while relaunching run 1**: `docker
    start asp-noetic` (on the container left `Exited` by #66's host
    reboot) did NOT restore GPU access - `nvidia-smi` inside the
    container failed (`Failed to initialize NVML: Unknown Error`) and
    the pipeline died immediately on habitat-sim context creation ("no
    EGL devices found"), even though the HOST's own `nvidia-smi` was
    completely healthy. A full `docker stop` then `docker start` cycle
    (not just `start` on an already-exited container) fixed it - this is
    a known class of Docker+NVIDIA issue where the container's device
    cgroup bindings go stale across a host-level GPU/driver event and
    aren't always reapplied by starting an already-stopped container.

    **What actually reduces future loss, since true resume isn't
    available**: the real problem in #66 wasn't the pipeline's lack of
    checkpointing - it was that the container didn't come back up on its
    own, and this session's own monitoring was separately down for ~6
    hours (the Tailscale outage), so nobody noticed for a long time. Two
    real fixes, neither touching pinned code:
    1. `docker update --restart=unless-stopped asp-noetic` - the
       container now restarts itself automatically on a host reboot or
       Docker daemon restart, without needing manual intervention.
    2. Every subsequent matrix-monitoring check now verifies `docker exec
       asp-noetic nvidia-smi` succeeds before trusting run progress, and
       runs the stop/start GPU-fix automatically if it doesn't - since
       it's untested whether a daemon-triggered auto-restart (from fix 1)
       hits the same stale-binding issue as a manual `docker start` did.

    Net effect: a repeat of #66's exact failure mode would now be caught
    and relaunched within roughly one monitoring interval (~30-40 min)
    instead of persisting silently for 6+ hours - bounding future loss to
    a few stages/~10m of path rather than a run's full progress. This is
    a real mitigation of the SYMPTOM (slow detection, manual recovery),
    not a fix for the underlying limitation (no mid-run resume), which
    remains real and disclosed.

    Run 1 (00069/seed42) relaunched clean after the GPU fix, confirmed
    healthy (stage 0 at 0m, stage 1 in progress, `exploration_pipeline.py`
    alive and consuming CPU normally). The failed first attempt is
    preserved, not deleted:
    `scene00069_seed42_matrix120m_FAILED_ATTEMPT1_hostreboot/`.

72. **Matrix supervision handed off from this session's manual
    ScheduleWakeup polling loop (#71) to a real, persistent, host-side
    systemd service, `tools/matrix_supervisor/`
    (`~/.config/systemd/user/asp-matrix-supervisor.service`, user-level
    systemd, `Linger=yes` so it survives logout and a host reboot without
    this session or any SSH connection being open) - built and installed
    outside this conversation and reported back to it. Verified
    independently before trusting it, same standard as every other claim
    this session, not accepted on the report's word alone:**

    - Service genuinely active: `systemctl --user status` shows `active
      (running)`, real PID, correct `ExecStart` pointing at `supervisor.py
      --daemon`. (First check used system-level `systemctl status` and
      wrongly found nothing - the unit is user-level; re-checked with
      `--user` and found it immediately.)
    - `runs/matrix_supervisor/status.json` (live) and `state.json`
      cross-checked against each other and against a direct
      `docker exec`/`ps` check of the actual run - all agreed:
      `active_run: scene00069_seed42_matrix120m`, `path_m` matching this
      session's own last manual check within the expected few-minutes'
      drift, `pipeline_pids: [933]` (the same PID this session's own
      manual launch produced), `container_gpu_ok/host_gpu_ok: true`.
    - `events.jsonl` shows one `adopt_run` event at supervisor startup,
      `path_m=52.425` at that moment - confirms the supervisor picked up
      this session's already-running attempt-2 launch and started
      tracking it rather than killing/restarting it, matching the
      report's "without altering or restarting the active experiment"
      claim exactly.
    - 36/36 supervisor tests pass (`pytest tools/matrix_supervisor/tests/`
      on tyrone, run directly, not taken on faith).
    - `CONTROL.json`'s live config matches this session's own launch
      config exactly: `reasoning_effort: low`, `max_tokens: 16000`,
      `target_path_m: 120.0`, `min_free_disk_gb: 25.0`, `max_attempts: 2`,
      `poll_seconds: 60`, `display: 99`.
    - `matrix_plan.json`'s real sequence is **seed-major**
      (00069/42, 00573/42, 00853/42, 00871/42, 00069/43, ...), not the
      scene-major order (00069/42,43,44 then 00573/42,43,44, ...) this
      session had been executing manually - a real, deliberate difference
      from what #71's wakeup-loop instructions assumed, not an error:
      seed-major means all 4 scenes get a seed=42 pass before any scene
      goes deeper, a defensible and arguably better design for interim
      analysis. Noting the difference rather than silently treating the
      two plans as identical.
    - No hash/checksum verification of the pinned checkout appears
      anywhere in the supervisor's own code (`grep`'d for
      hash/sha256/commit across all 3 modules - one incidental match, a
      `config/commit.txt` path in an artifact-completeness check, not a
      pinned-tree integrity check) - the report's "before/after hashes
      match exactly" claim is very likely a real, one-time check someone
      ran at setup time, not something this running service continuously
      enforces. Not alarming (nothing in normal operation would modify
      the pinned tree), but distinct from an ongoing guarantee - flagged
      for accuracy.

    **This session's own manual polling loop (#71's ScheduleWakeup-based
    30-minute check-ins) is now stood down** (`ScheduleWakeup stop:true`)
    to avoid two independent supervisors racing to stop/launch the same
    run. Future check-ins from this session, if any, should read
    `runs/matrix_supervisor/status.json` and `journalctl --user -u
    asp-matrix-supervisor.service` rather than re-implementing the polling
    logic - the README's own words: "Human or agent check-ins may remain
    at a 30-minute cadence because they are reporting only; safety does
    not depend on their SSH connection." This is a materially better
    setup than #71's mitigation: the earlier fix bounded loss to ~30 min
    by making THIS SESSION'S monitoring loop reasonably tight; the real
    exposure was always that the loop lived inside a conversation that
    could itself go quiet (as it did for 6 hours in #66). A `Linger=yes`
    user systemd service has no such dependency.

73. **Run 3 (00853/seed42) reached budget but the supervisor's completion
    validation paused on a second, different uncaptured-traceback pattern
    - analyzed, NOT patched tonight (Opus-advisor-reviewed, 2026-09-17).**
    Path reached 126.075 m (stage 31), past the 120 m target, and the
    supervisor correctly proposed `stop_at_budget`; `validate_completed_run`
    then found `Traceback (most recent call last)` later in the cumulative
    log and paused with blocker "completion validation failed: uncaptured
    traceback in pipeline log" - NOT the rospy `bad callback:` pattern
    fixed earlier tonight (see the matrix-supervisor traceback-detection
    fix, same date), a different trigger.

    **Per-stage path is cleanly monotonic to the end - no corruption risk:**
    stage 29 = 115.275 m, stage 30 = 116.175 m, stage 31 = 126.075 m, stage
    32 has **no `navigation_stats.json` at all** (an earlier hypothesis
    that stage 32 recorded 22.425 m was checked directly and is wrong -
    no file, no such value anywhere in this run's stage directories).

    **Stage 31 (the max-path, target-reaching stage) has complete
    artifacts**, verified directly: both `habitat_scene_graph_original_
    graph{0,1}.yaml` present (~50 KB each, non-trivial), 7 of 8
    `habitat_scene_graph_new_graph_*.yaml` completions present and
    substantial (51-55 KB each; ensemble member 1 absent - ordinary
    fail-soft, not a stage-31 problem). The scored, budget-reaching data
    is intact regardless of anything that happened afterward.

    **The flagged traceback is in stage 32, which began after the budget
    was already met and produced zero scored artifacts** (original graphs
    and scene slices written, zero completions, no nav stats). Full
    sequence from `exploration_pipeline.log` (~line 40700-40754, this
    run's last activity): 6 `ProcessPoolExecutor` workers spawn for a new
    ensemble-scoring batch; one hits `ImportError: this platform is not
    supported: ('failed to acquire X connection: Display connection closed
    by server: [Errno 32] Broken pipe'...)` from `pynput`'s X-connection
    check - consistent with a race against the supervisor's own graceful-
    shutdown sequence tearing down Xvfb once the budget was reached, not
    an unprovoked crash; all 8 workers then report terminated; the
    pipeline's own existing fail-soft path logs "8/8 ensemble members were
    dropped" and "ALL ensemble members failed - returning None so the
    caller's outer retry fires (matches original crash-path behavior)"
    (this project's own established #37-class tolerance, not new code);
    one retry-logged planning error; then "Starting uncertainty
    calculation to select next target..." (pipeline visibly continuing);
    then "Shutdown requested..." and "Pipeline shutdown." - a clean,
    intentional exit, nothing after it in the log.

    **Decision (advisor sign-off): do not widen `_fatal_traceback()`
    tonight, and do not hand-edit the supervisor's persisted state
    either.** Reasoning: (1) `CONTROL.json`'s `max_completed_runs: 3`
    means the supervisor has nowhere to go on either path - even a
    "complete" run 3 just advances `queue_index` to 3, which the same
    control converts the next `LAUNCH_RUN` into a `PAUSE` for ("run limit
    reached") - no run launches, no file changes, regardless of how this
    is resolved tonight. The expected benefit of touching a safety-
    critical detector unsupervised, on a single observed instance (n=1),
    at 1 AM, is zero. (2) A workable exemption for this pattern would
    need to check "did the run end cleanly with nothing after this
    traceback" - a whole-log property, which belongs in
    `validate_completed_run`'s own logic, not folded into
    `_fatal_traceback`'s "is this one traceback fatal" contract. (3) A
    safety detector widened twice in one unsupervised night is one a
    future reviewer should stop trusting by default. (4) Hand-editing
    `state.json` to mark the run complete would race the live systemd
    service for control of its own state file and would replace an
    independently-certified record (the whole point of #72's handoff)
    with a session's own assertion.

    **This is left exactly as the supervisor paused it** - a true record
    that the detector met something it did not recognize and refused to
    certify, which is the detector doing its job (conservative by design),
    not a bug to route around. **Proposed for the user's own review, not
    implemented:** a second, narrowly-scoped `_fatal_traceback` exemption
    for this exact signature (a `pynput`/X-connection `ImportError`
    immediately followed by this pipeline's own "ALL ensemble members
    failed - returning None" log line, with nothing but a clean shutdown
    after) - or, better per the layering objection above, a check inside
    `validate_completed_run` for "did the run's last activity end in
    `Pipeline shutdown.` with no further lines."

    **Scoring proceeds regardless**: `extension_policy_replay.py` and
    `decision_replay.py` read stage artifacts directly and were never
    gated on the supervisor's own completion certification - stage 31's
    complete, budget-reaching data is fully scoreable as-is.

74. **Real bug found in `decision_replay.py`: alternative policies silently
    lose every observed node, confounding every alternative-vs-official
    comparison in this tool - including the standing #65/#66 tables, not
    just tonight's data (found and analyzed, NOT fixed, Opus-advisor-
    reviewed, 2026-09-17).** Found while checking why scene 00573's
    calibrated-support decision-replay showed large displacement from
    official instead of the near-no-op predicted from its degenerate
    calibrator (deviation #73's session, same night) - the prediction's
    threshold arithmetic was right, but irrelevant to the real cause.

    **Mechanism, traced directly** (00573 stage 5): a raw completion file
    contains the observed graph plus the LLM's predictions - `original_
    graph0.yaml` has 45 nodes, `new_graph_0.yaml` has 65 (20 `is_predicted:
    true`, 34 `is_predicted: false` i.e. observed, 11 with no `is_predicted`
    field). `build_policy_files` computes each alternative policy's keep
    set from PREDICTED nodes only (`filter_only`: `not n.get("observed",
    False)`; `calibrated_support`: `_hypotheses(completion, include_
    observed=False)`), then `write_keep_set_yaml` keeps ONLY ids in that
    keep set - dropping all ~45 observed nodes (walls, doors, structures,
    everything the robot has actually seen) from every non-official
    policy's file. `official` gets `write_keep_set_yaml(raw_graph, None,
    ...)` - all 65 nodes, unfiltered. Nothing downstream restores the
    observed nodes for the alternatives; `_build_scene_graph_groups`
    reads each policy's YAML as its complete world model.

    **Result: `official` is scored on a ~65-node world; every alternative
    is scored on a ~20-node, predictions-only world.** This is not
    primarily a policy comparison (unfiltered vs. filtered vs. calibrated
    predictions) - it is mostly "has the observed map" vs. "does not have
    the observed map." Confirmed asymmetric: `filter_only` vs.
    `calibrated_support` are stripped equally and may still be comparable
    to each other; every comparison AGAINST `official` is confounded -
    which is exactly the comparison #65's and #66's headline ("filter-only
    wins outright at 4 of 5 stages") rests on.

    **The static-graph ablation (`tools/asp_offline/support_policy.py`'s
    `support_filtered_graph`) does this correctly** - it explicitly unions
    the observed ids back in: `kept_node_ids = {n.id for n in
    observed_nodes} | kept_ids`. `extension_policy_replay.py` and
    tonight's full-budget scoring (deviations noted elsewhere this
    session) go through that correct path and are NOT affected by this
    bug - only `decision_replay.py`'s own separate keep-set construction
    is wrong.

    **Root cause traced to #65's own fix**: to stop `normalize_author_
    graph` from silently dropping `orientation` (breaking every occlusion
    test), #65 switched decision_replay.py to "compute a keep-set with the
    offline tools, apply it directly to the raw YAML dict, never round-
    trip through the offline Node/Graph schema." That keep-set is a
    predicted-node set by construction (from `support_scores`/
    `_hypotheses`); applying it to the raw dict without also unioning the
    observed node ids is exactly where the observed nodes vanish. The fix
    for one silent corruption (orientation) introduced a second, different
    one (missing observed context) - not caught until real full-budget
    data ran through it for a second and third scene.

    **Not fixed tonight - every stop-line trigger from tonight's own
    working rules fires at once**: the fix would move numbers already
    reported (#65, #66); it contradicts standing DEVIATIONS findings
    outright rather than just refining them; it changes how policy graphs
    are constructed (a mechanism change, not data hygiene); and it was
    found because a result looked wrong, not because of a forced, no-
    free-parameters correction. This is the user's decision, in daylight,
    with a corrected re-run - not a 2 AM unsupervised call.

    **Actions taken**: stopped the decision-replay track entirely for
    tonight; killed the in-progress 00853 decision-replay run rather than
    let it finish on a confirmed-buggy harness; preserved 00573's
    already-completed output (`decision_replay_scene00573_matrix120m.json`)
    untouched, since it is the evidence that surfaced this, not a result
    to report. **#65's and #66's decision-level tables are flagged suspect
    pending review - not struck, since correcting or retracting them is
    the user's call, not this session's.** The corrected fix, proposed but
    NOT implemented: union each policy's kept predicted-node ids with the
    full set of observed node ids before calling `write_keep_set_yaml`,
    matching `support_filtered_graph`'s existing, correct pattern exactly.

    **What survives untouched**: everything that runs through
    `extension_policy_replay.py`/`support_filtered_graph` - the full-
    budget triple replication of the tau=1.0 unanimity result, its
    mechanism (removes ~27% of predicted nodes, keeps ~99.7% of true
    positives), the validator-subsumed-by-unanimity finding, the held-out
    tau-selection result, and the calibration findings (equivalent at
    unanimity, worse than raw thresholding at intermediate taus on 00573).
    None of these construct policy graphs the way `decision_replay.py`
    does, and none are affected by this bug.

75. **Two process issues found while re-running decision_replay.py's fix
    (#74) against all 3 full-budget scenes, one attribution in this entry
    corrected in place rather than silently (Opus-advisor-reviewed,
    2026-09-17, same day, user now awake and directing the fix).**

    **(a) Added fault-tolerance to `main()`'s per-stage loop.** Before
    this, one stage raising an exception crashed the entire run and
    discarded every already-replayed stage before it (results are only
    written to disk at the very end). Forced, no-free-parameters fix,
    same spirit as the two existing skip-conditions immediately above it
    in the loop (missing `path_log.json` / no completions): wrapped the
    single `replay_stage(...)` call in `try/except Exception`, recording
    `{"stage": N, "error": "..."}` and continuing rather than crashing.
    Does not change how any SUCCEEDING stage is scored. Standing policy
    for using this safely, going forward: the skip count must travel
    next to every reported total (e.g. "32 of 32 stages", not just a
    bare total); a skipped stage is missing data, never counted as a tie
    or a zero; and any scene where skips exceed ~10% of its stages, or
    cluster (consecutive, or all late), should be stopped and reported
    rather than aggregated - a scattered skip is noise, a clustered one
    means the retained sample is biased.

    **(b) Real race condition found and fixed before it could corrupt
    results**: `decision_replay.py`'s per-stage work directories are keyed
    by stage number only (`OUT_DIR / f"stage{N}_files"`), with no notion
    of which scene is running - nothing documented this as a constraint.
    Running 00573 and 00853 concurrently with the SAME `--out-dir`
    (`matrix120m_scoring/`) meant both processes wrote to and read from
    identical paths for overlapping stage numbers at the same time. Both
    runs were killed (100+ CPU-minutes each, discarded) and relaunched
    with scene-specific `--out-dir` subdirectories, which make the
    collision structurally impossible rather than merely avoided by
    convention. The durable fix - keying the work dir by scene as well as
    stage - is proposed, not implemented, alongside this note.

    **Audited backwards, not just forwards**: the earlier scene-00069
    FIXED run (this same session, used to verify #74's fix) had ALSO used
    the shared `matrix120m_scoring/` directory during the same collision
    window, discovered only after the fact. Re-ran it in full isolation
    and diffed the two outputs by exact dict equality: byte-for-byte
    identical. The result stands as verified, not merely probably-clean -
    the 00069 finding below is confirmed, not provisional.

    **(c) Correction to this same session's attribution of 00853's
    stage-1 crash.** When #74's fix was first tested against 00853 (in
    the collision window, before (b) was found), stage 1 crashed with
    `AttributeError: 'NoneType' object has no attribute 'get'` inside the
    pinned `calculate_uncertainty.py`'s `_perturb_scene_graph`. This was
    recorded in conversation as likely pre-existing pinned-code fragility
    unrelated to the fix, reasoned from the raw completion files for that
    stage all being individually well-formed. ~~That reasoning was
    incomplete.~~ **The isolated, collision-free re-run of the identical
    stage 1 data completed with zero errors** (0 of 32 stages skipped,
    full results below) - a genuinely data-dependent crash in pinned code
    would have recurred on the same data, and it did not. The far more
    likely explanation is that the crash was itself a symptom of (b): a
    partially-written or wrong-scene YAML read during the collision, not
    an independent pinned-code defect. The try/except from (a) is kept as
    a defensive guard regardless (a real, if rarer, class of failure it
    would still catch), but should not be read as working around a known
    pinned-code bug - there is no confirmed pinned-code bug here, only a
    process-isolation one that has since been fixed.

    **Results, all 3 scenes now scored with #74's fix, fully isolated,
    no skipped stages anywhere:**

    00069 (25m short run, 5 stages - the harness-verification diagnostic,
    NOT full budget, see the budget-asymmetry note below): official=7,
    filter_only=5 (2 wins/2 losses/1 tie@0), calibrated_support=12 (3
    wins/1 loss/1 tie@0) total reference objects visible across stages.
    **The standing "filter-only wins outright at 4 of 5 stages" claim
    (#65/#66) is refuted on this scene under the corrected harness, not
    merely confounded** - filter_only now sees FEWER reference objects
    than official overall. Do not read this as "calibrated_support wins"
    either: 5 stages, integer counts of 0-7, official at zero in 3 of 5 -
    this sample size cannot support ranking either alternative, and the
    honest statement is about the metric's fragility here, not a new
    winner.

    00853 (full 120m matrix run, 32 stages): official=66, filter_only=109
    (16 wins/4 losses/6 tie@0/6 tie@nonzero), calibrated_support=104 (20
    wins/5 losses/2 tie@0/5 tie@nonzero). Both alternatives clearly ahead
    of official here, a real reversal of 00069's picture. **Do not compute
    a p-value from the 20-32 non-tied stages per scene**: stages are one
    sequential trajectory, not independent trials (stage N's candidate
    pool and geometry depend on stage N-1's position), so a naive sign
    test overstates significance the same way pooling scenes would -
    report win/loss counts as descriptive, per scene, not as a
    significance claim.

    **Budget asymmetry, flagged before drawing any cross-scene
    conclusion**: 00069's result above used its 25m short run (5 stages);
    00853's used the full 120m matrix run (32 stages) - not a comparable
    sample, and the apparent disagreement between them is confounded with
    a ~6x difference in trajectory length and exploration phase, the
    exact same class of error already caught and fixed in the static-graph
    table (00573's row briefly used an uncapped AUC while the others used
    the pre-registered 120m cap). Re-running 00069's own full 120m matrix
    run (29 stages, same cost class as 00853's, no API cost) rather than
    reporting the 5-stage short run as a cross-scene data point.

    One genuine improvement worth recording on its own: zero-inflation
    drops sharply at full budget - 6 of 32 stages tied at zero on 00853
    versus 3 of 5 on 00069's short run. The decision-level metric has real
    discriminating power at 120m that it did not have at 25m - a second,
    independent reason (besides comparability) to base any decision-level
    reading on full-budget runs only.

    00573's full-budget result and 00069's full-budget re-run are still
    running as of this entry; results to follow in a subsequent entry
    once both land.

76. **The corrected full-budget decision replay is complete after a second
    keep-set defect was fixed subtractively; the static-graph GED result is
    not confounded by that defect; and a novelty-only audit narrows the
    decision-level result to a provisional two-scene signal pending a null
    control (Opus-advisor-reviewed, 2026-09-17).** This entry supersedes
    #75's closing sentence that 00573 and full-budget 00069 were still
    running. All three corrected outputs finished in isolated workdirs with
    zero skipped/error stages and are preserved under new `v2_` paths:
    `runs/matrix120m_scoring/v2_{00069,00573,00853}_workdir/`.

    **A second keep-set defect was found in the first #74 correction.** The
    first correction unioned nodes classified as observed into both
    alternative policies. That repaired the known loss of the dedicated
    observed graph, but `calibrated_support` was still constructed
    additively: start from an empty set and add nodes visible to either the
    observed-node classifier or the predicted-hypothesis extractor. Real
    completions contain some LLM-invented rooms with no `is_predicted` tag.
    Direct comparison against the dedicated observed graph confirmed these
    rooms were NOT observed; they were simply untagged predictions. Because
    `validate_completion` and the hypothesis extractor classified that
    malformed case differently, such a room could fall through both sides
    and disappear from `calibrated_support` even when the calibrator intended
    to remove nothing. A coincidentally reused numeric id in the observed
    file was also checked and names a different room: ids are local to one
    completion and cannot establish identity across files.

    **Forced, no-free-parameter correction:** `calibrated_support` now starts
    from `official`'s complete raw node set and SUBTRACTS only predicted nodes
    that the support scorer explicitly sees and places below threshold. A node
    the classifier cannot see is never subtracted and therefore survives
    exactly as `official` treats it. This removes the need to infer
    observed-vs-predicted status for this policy and closes the same failure
    mode at its source: additive keep sets silently omit whatever their
    classifier cannot represent. The deployed `tools/decision_replay.py` was
    verified byte-identical on the Mac, tyrone host, and `asp-noetic`
    container (SHA-256
    `8ea58f0fbc187fb2ee77db659b6f5c6c60b9a582a8cf091657882ebb503e86ef`).

    **Two pre-registered gates passed on full real runs, not spot checks.**
    (1) Scene 00573's held-out calibrator maps every reachable non-unanimous
    support level to the same value, so the corrected calibrated-support
    policy must be a no-op relative to official. It is: 34/34 stages have
    exactly `0.0` m displacement, and its total visible-reference count is
    exactly 17 versus official's 17. (2) `filter_only` was not changed by the
    subtractive correction, so 00853's filter-only stage records had to remain
    exact across the pre- and post-correction isolated runs. They are exactly
    equal as Python dictionaries for all 32 stages. The corrected totals are:

    | scene | stages/errors | official | filter_only | calibrated_support |
    |---|---:|---:|---:|---:|
    | 00069 | 28 / 0 | 39 | 78 | 52 |
    | 00573 | 34 / 0 | 17 | 62 | 17 |
    | 00853 | 32 / 0 | 66 | 109 | 87 |

    The earlier 00853 calibrated-support total of 104 came from the additive,
    pre-correction policy and is superseded by 87. All non-`v2_` full-budget
    workdirs are retained as evidence but must not supply reported numbers.

    **The same untagged-room condition does NOT confound the static-graph
    triple-replication result.** Tracing `extension_policy_replay.py` through
    `asp_offline/author_io.py` showed that a completion is normalized with
    `observed=None`, so a missing `is_predicted` field defaults to
    `predicted=False` and therefore `observed=True`. `_official_graph` keeps
    only completion nodes marked non-observed, and `support_filtered_graph`'s
    hypothesis path likewise excludes the same normalized-as-observed
    untagged room. Both policies omit it symmetrically; there is no
    alternative-vs-baseline graph asymmetry and the reported GED result
    stands. The honest scope note is narrower: this ablation evaluates
    object-level filtering. Predicted rooms that lack the author tag are
    invisible to both the baseline and filtering policy, so it makes no
    room-level filtering claim.

    **A pre-registered novelty split changed the interpretation of the raw
    decision totals.** `reference_objects_visible` counts every visible
    reference object, including objects already represented in that stage's
    observed map, so a higher total can reward revisiting dense mapped areas
    rather than exploration. A read-only identity-level rescore of the exact
    already-chosen poses separated visible reference objects into
    already-observed versus novel; it made no new pose samples, planner calls,
    or LLM/API calls and asserted that every recomputed visibility count
    matched the stored count before classifying identity. Results:

    | scene | novel official -> filter | filter wins-losses | tie@0 | tie@nonzero | non-blind coverage |
    |---|---:|---:|---:|---:|---:|
    | 00069 | 25 -> 50 | 12-4 | 7 | 5 | 75% |
    | 00573 | 15 -> 23 | 7-4 | 20 | 3 | 41% |
    | 00853 | 40 -> 64 | 13-4 | 9 | 6 | 72% |

    Direction is consistent: filter-only is ahead on novel objects in all
    three scenes. Strength is not. 00069 and 00853 have a moderate descriptive
    per-stage margin; 00573 is blind at 20/34 stages (59%), and the remaining
    7-4 record is close to indistinguishable from noise. This is the opposite
    of the raw-total impression: 00573 looked strongest at 62 versus 17, but
    39 of filter-only's 62 visible objects were already observed, versus only
    2 of official's 17. `calibrated_support` supports no coherent claim:
    00069 is even (8-8), 00573 is identical to official by construction, and
    00853 alone is favorable (14-7).

    **Interpretation boundary:** stages within one scene are sequential and
    autocorrelated, so win/loss counts are descriptive, not independent trials
    and not inputs to a naive sign-test p-value. More importantly, the
    alternatives use fresh `PoolReplayCalculator` instances while official
    uses its own calculator. Identical graphs can therefore consume the
    perturbation RNG stream differently. No identical-graph null policy has
    yet measured that harness variation, so none of the observed margins can
    currently be separated from the replay noise floor. The corrected honest
    claim is: on a metric validated to measure novel exploration rather than
    object density, the structural filter leads in direction on all three
    full-budget scenes, with a moderate per-stage margin on two and no usable
    signal on the third; this remains provisional until compared with an
    identical-graph, fresh-calculator null control.

    **What survives untouched:** the static-graph unanimity result remains a
    complete, triple-replicated, mechanistically understood backend finding;
    its GED comparison is clean subject to the object-level scope note above.
    Calibration remains non-beneficial, and the risk-sensitive term's negative
    result remains unchanged. The old #65/#66 five-stage claim is no longer
    merely suspect: under the corrected short-run harness filter-only totals 5
    versus official's 7 (2 wins, 2 losses, 1 tie@0), so “wins outright at 4 of
    5 stages” is refuted and must not be carried forward.

    **Next approved step, not part of the results above:** add a null-control
    policy whose graph is exactly identical to `official` but which traverses
    the same fresh-calculator/fixed-pose path as the alternative policies.
    Pre-register exact graph/file identity and treat every null-vs-official
    decision difference as harness variation, then run all three scenes again
    in separate new output directories. No prior JSON will be overwritten.

77. **Identical-graph null control implemented test-first and launched on all
    three full-budget scenes; exact-zero outcome pre-registered before the
    full outputs exist (2026-09-17).** This is the approved follow-up to #76,
    designed to isolate one remaining question: can the fresh-calculator,
    fixed-candidate-pool path used by `filter_only` and
    `calibrated_support` diverge from official even when its input graph is
    exactly identical?

    **Construction is identical by reference, not reconstructed
    equivalence.** `build_policy_files` adds `null_control` by appending the
    very same `official_out` `Path` objects used by `official`; no second YAML
    serialization exists. `replay_stage` then instantiates a fresh
    `PoolReplayCalculator` for the null and sends it the exact official
    candidate-pose array through `gather_observations_for_fixed_poses`, the
    same route as the two filtering alternatives. A runtime guard refuses the
    stage unless the null and official input-path lists are exactly equal, and
    each output stage records `input_files_shared_with_official: true`.

    **Red-green verification before the full launch:** a new real-parser
    integration test first failed because `null_control` was absent, then
    passed after exact file aliasing was added. A second test first failed
    because `replay_stage` did not score the null, then passed after adding
    the fresh calculator path; it tracks constructor instances, requiring
    four distinct calculators (official, null, filter-only,
    calibrated-support), and checks exact official/null scores, selected pose,
    reference count, and zero displacement on a deterministic synthetic
    stage. The complete offline suite passes 41/41 and the author-faithful
    evaluator suite remains 11/11. The real 00573 stage-0 smoke check also
    passed exactly: identical stage-1 IG, tie count, stage-2 pose/IG, and
    visible-reference count, with `0.0` m displacement.

    **Full-run prediction sharpened before completion: every null stage must
    be exactly identical to official, not merely close.** Source inspection
    after the smoke check but before any full result JSON existed showed why.
    A calculator's `self.rng` samples candidate poses only inside official's
    `_gather_sample_observations`; the null receives those already-sampled
    poses and its fixed-pose path never consumes `self.rng`. Scene-graph
    perturbations also do not consume an instance-dependent stream:
    `_build_scene_graph_groups` calls `_perturb_scene_graph` with
    `config.SEED + k`, and that method creates a new local
    `np.random.default_rng(seed)` for each perturbation. Calculator creation
    order therefore cannot alter either poses or perturbed graphs. For every
    stage, the pre-registered acceptance condition is exact equality of
    stage-1 IG/tie count, stage-2 pose/IG, visible-reference count, and
    displacement `0.0`. Any nonzero difference is a new harness defect and
    stops interpretation; it is not a noise estimate to explain away.

    Three full replays were launched concurrently with structurally isolated
    directories and never-reused output names:

    - `null_v3_00069_workdir/decision_replay_scene00069_matrix120m_null_v3.json`
    - `null_v3_00573_workdir/decision_replay_scene00573_matrix120m_null_v3.json`
    - `null_v3_00853_workdir/decision_replay_scene00853_matrix120m_null_v3.json`

    The exact tool deployed on the Mac, tyrone host, and container is SHA-256
    `a292e73093c01ec2aecd7def439647411dfcdb11ce2b9ea652715184b5d59cf3`.
    Existing `v2_` JSONs are untouched. The full outputs were still running
    when this entry was written; their result belongs in the next entry, not
    retrofitted here.

    **Separate deployment hazard found by the test command, with no result
    impact:** the container mount also contains an old
    `/workspace/decision_replay.py` (Sept 15, SHA-256
    `03d0f675e3bf257b06658c27a80ffbfd149963177b9154d87f7f9e7507e3c67d`).
    Python launched from `/workspace` resolves its empty-string current-dir
    entry before `PYTHONPATH=/workspace/tools`, so a bare
    `import decision_replay` can silently load that stale root copy. No scored
    run is affected: all v2/v3 commands execute
    `/workspace/tools/decision_replay.py` explicitly, and the novelty script
    inserts `/workspace/tools` ahead of the working directory. The new test
    now pins and asserts the sibling tools copy so this cannot silently
    invalidate future test runs. The unfamiliar root file was preserved, not
    deleted or overwritten.

78. **The full identical-graph null control passed exactly on all 94
    stages; fresh-calculator/fixed-pose replay contributes zero variation,
    and every pre-existing policy is unchanged from the corrected v2 outputs
    (2026-09-17).** This resolves #76-#77's final open validity check. All
    three new-suffixed runs completed in isolated workdirs, with no skipped or
    error stages and no logged traceback/raised-stage pattern:

    | scene | stages | null exact vs official | official | null | filter_only | calibrated_support |
    |---|---:|---:|---:|---:|---:|---:|
    | 00069 | 28 | 28/28 | 39 | 39 | 78 | 52 |
    | 00573 | 34 | 34/34 | 17 | 17 | 62 | 17 |
    | 00853 | 32 | 32/32 | 66 | 66 | 109 | 87 |

    “Exact” here is not rounded displacement alone. At every stage the null
    recorded `input_files_shared_with_official: true` and matched official's
    stage-1 IG, stage-1 top-tie count, stage-2 pose, stage-2 IG, and visible-
    reference-object count as exact Python values, with displacement exactly
    `0.0`. The pre-registered prediction in #77 therefore passes 94/94.

    **Regression gate also passes completely:** for every one of the 94
    stages, each v3 policy dictionary for `official`, `filter_only`,
    `calibrated_support`, and every `combined` beta is exactly equal to the
    corresponding authoritative v2 dictionary. Top-level calibration
    metadata, held-out training scenes, support tau, beta grid, reference,
    and run path are also exact; per-policy input-file counts are unchanged,
    with the null count equal to official. Adding the diagnostic policy did
    not perturb any previously reported result.

    Authoritative result artifacts and hashes:

    - `null_v3_00069_workdir/decision_replay_scene00069_matrix120m_null_v3.json`
      — SHA-256 `2bf723835ba79c309b31224eabd7948c52ef2e96eb91b57768747157e6051417`
    - `null_v3_00573_workdir/decision_replay_scene00573_matrix120m_null_v3.json`
      — SHA-256 `50dff66df993a0051ac8d53203c19bc44f9a1f74decd2f9748886eb920286d79`
    - `null_v3_00853_workdir/decision_replay_scene00853_matrix120m_null_v3.json`
      — SHA-256 `3e475f5086be2b4e5d0309c9be47bc9d592f1eb8725a4f64ace9bd166752c3cb`

    The deployed tool hash remains the pre-registered #77 value,
    `a292e73093c01ec2aecd7def439647411dfcdb11ce2b9ea652715184b5d59cf3`.
    The complete offline suite passes 41/41 and the independent
    author-faithful evaluator suite passes 11/11.

    **Interpretation: the proposed calculator-path noise floor is exactly
    zero under this replay implementation.** This is mechanistically
    consistent with the source audit in #77: candidate poses are sampled once
    by official; fixed-pose alternatives never consume their instance RNG;
    and each graph perturbation starts a new local RNG from the same explicit
    `SEED + k`. The earlier possibility that fresh calculators consume one
    random stream in different orders is falsified for this code path. This
    null is a structural invariance check, not an estimate of seed-to-seed or
    trajectory noise. It removes one confound; it does not create missing
    independent seeds.

    **Final decision-level result, using the pre-registered novel-object
    metric rather than raw object density:** filter-only leads official in
    direction on all three full-budget scenes. The per-stage record is 12-4
    on 00069, 7-4 on 00573, and 13-4 on 00853. The margin is descriptively
    moderate on 00069 and 00853. It is effectively absent on 00573, where
    20/34 stages (59%) are blind tie-at-zero stages and only 41% of stages
    carry any nonzero novel-object signal. Stages remain autocorrelated, so
    these records are descriptive and no per-stage p-value is valid.

    The defensible claim is therefore narrower than both the old #65/#66
    headline and the raw totals: **within this deterministic decision-replay
    approximation, structural filtering changes selected viewpoints in a
    direction that exposes more novel reference objects on all three fixed
    full-budget runs, with a moderate margin on two and no useful signal on
    one; the effect is not an artifact of the fresh-calculator path.** It is
    not evidence of cross-scene generalization, seed robustness, or live-
    trajectory improvement. Only one seed exists, the three scenes are not
    independent confirmations of a backend-driven mechanism, and the live ROS
    reachability gate cannot be replayed for counterfactual policies.

    `calibrated_support` still supports no coherent decision-level claim:
    even on 00069 (8-8 novel-stage wins/losses), exactly official on 00573 by
    construction, and favorable only on 00853 (14-7). The risk-sensitive
    `combined` policy remains the same mechanistically explained negative.
    The static-graph unanimity result remains the strongest finding: clean
    triple replication, GED unaffected by the untagged-room issue, explicitly
    scoped to object-level filtering.

    **Code-review disposition:** no blocker was found in the null-control
    implementation. The stale `/workspace/decision_replay.py` import shadow
    documented in #77 did not affect any run and is guarded in tests. Two
    pre-existing operational risks remain disclosed rather than expanded into
    this result: callers can still collide if they deliberately reuse one
    `--out-dir` across scenes (all authoritative runs use isolated dirs), and
    results are committed only at the end of a scene rather than atomically
    per stage. Neither moved these outputs. The temporary LAN loss during the
    runs did not stop tyrone, the container, or any replay process; host uptime
    was continuous and all three jobs completed normally.


79. **Phase 13 diagnostics closeout: v4 authoritative; static gates pass, trajectory outcomes remain unavailable (2026-09-17).** The diagnostic tool and tests were reviewed against the frozen corpus; no correction was needed, so v4 remains authoritative and v1-v3 remain preserved audit iterations. The exact completion boundary is 94 completed stage directories, 752 expected slots (94 × 2 tracks × 4 ensemble members), with post-shutdown partial/empty stage directories excluded.

    Authoritative directory: `runs/matrix120m_scoring/phase13_v4_20260917/`

    - `phase13_diagnostics_v4.json` — SHA-256 `30c06d028144142eb57912f302e5fc6a95a38feecd97bbffaa2b63ecd348d1ce`
    - `reliability_overall.svg` — SHA-256 `d8fb3c6ae2bbdf625066661829d7827412ec41c7d2e476343c1f1ae1d5cb7375`
    - `reliability_object.svg` — SHA-256 `2421f461df44b06d38c68172755ad056f3ec46cf75f9412df6718e6c57a72724`
    - `reliability_room.svg` — SHA-256 `ceb340fde1fcff6a3ed790761cc8b796e67815a6b6830192e71c478b66435550`

    Calibration is pooled room/object LOSO with ten equal-width ECE bins. The held-out baseline uses only matching-subset prevalence from the other three scenes. Pooled overall: n=2829, positives=23, raw/calibrated/train-rate Brier 0.0867356/0.0074422/0.0080843 and raw/calibrated ECE 0.269530/0.001575. Objects: n=2813, positives=15, Brier 0.0857847/0.0056800/0.0053089; calibration is worse than baseline by 0.0003710. Rooms: n=16, positives=8, Brier 0.2539063/0.3172638/0.3064557; calibration is harmful. The low pooled ECE is dominated by extreme imbalance and object rows, not evidence of room calibration. Per-scene calibrated-vs-baseline Brier is better on 00573 and 00871, worse on 00069 and 00853.

    Validator diagnostics preserve the exact denominator: 752 expected, 686 available, 667 accepted, 19 rejected, 66 missing. Of 10,362 predicted-only nodes, 3,589 are excluded and 6,773 survive (65.36%). Predicted-only evaluator matching is recomputed after filtering with the observed map excluded: object TP 61→45 (73.77% retention), room TP 313→138 (44.09%); object/room false-positive removal is 31.57%/59.70%. Semantic-set Jaccard distance rises 0.6360→0.7556; this means survivors are less similar, not that diversity was preserved. This directly contradicts using the old full-graph, observed-map-dominated “~99.7% true positives” phrase as predicted-only retention.

    Static policy `filter_plus_support_threshold_calibrated_tau_1.0` passes every scene's 120m-capped guardrails: F1 0.478938→0.521794 and GED 0.896941→0.825383 on 00069; F1 0.397964→0.434966 and GED 0.957558→0.887629 on 00573; F1 0.457820→0.495655 and GED 0.856089→0.792967 on 00853. The invalid-hypothesis gate passes with 3,589 exclusions. The false-positive detour gate is **NOT IDENTIFIABLE**: counterfactual replay selects stage-local poses but never navigates them, and records neither live reachability nor cumulative counterfactual paths. Selected-pose displacement, novel objects at a pose, and official A* failures are prohibited substitutes. Thus combined usefulness is **NOT ESTABLISHED** despite static gates passing.

    Robot collision count is **NOT INSTRUMENTED**, not zero. The pinned controller uses `agent.set_state` and unconditionally increments path length; no contact, blocked-step, or collision sensor artifacts exist. LLM `check_collision` is object-box overlap, not robot motion. Official A* failures are planner failures (13/10/15), not collisions. API counters are 1922/2445/2053; costs/token usage are unavailable, and summed request seconds are concurrency-inflated rather than wall time.

    The closeout report is `PHASE13_DIAGNOSTICS_2026-09-17.md`. The local mirror is `tyrone_mirror/runs/matrix120m_scoring/phase13_v4_20260917/`, verified byte-identical. Focused Phase 13 tests pass 11/11 in the real container (local Mac run has 10 pass and one PyYAML-dependent skip); complete offline and author-faithful evaluator counts are reported in the final execution report. Phase 13 is evaluated and closed for the frozen corpus, but no live counterfactual or collision-instrumentation experiment was launched.


80. **Primary review correction: v4 diversity weighting defect fixed; v5 is authoritative (2026-09-17).** After #79, primary review found that `aggregate_validation_diagnostics` weighted each scene's mean pairwise semantic diversity by all `stage_tracks`, although `collect_validation_diagnostics` omits a track from its mean when fewer than two completions are available. Frozen availability is 00069: 56/56 defined tracks, 00573: 67/68, and 00853: 64/64. The defect affected only the cross-scene diversity aggregate, not per-scene values or any other diagnostic.

    v4 and #79 are preserved unchanged. The corrected tool source is SHA-256 `d68833fbe1a50b1332fea0e1be946b86a2727696997f50538368f42773fc0176` and the regression-test source is SHA-256 `14f34d6d114badf76bf3a58e2c03fc6cb298e054bbd6aab554fb6fbb48def407`; both hashes match on the Mac, tyrone host, and `/workspace/tools`. The new regression tests cover (a) unequal defined-track weights and (b) evaluator rematching after removal of a closest invalid duplicate: an invalid exact-position chair is removed while a valid 0.4 m duplicate survives, preserving predicted-only TP 1→1 and removing the one false positive.

    A new isolated run completed without overwriting v4:
    `runs/matrix120m_scoring/phase13_v5_20260917/phase13_diagnostics_v5.json` and the three reliability SVGs. Schema is `asp_phase13_diagnostics_v5`; output refusal remains enabled for any existing output path. The v5 aggregate diversity is correctly weighted over 187 defined tracks:
    `0.6360903078259732 → 0.7556307279246379`, replacing v4's `0.6360473977461963 → 0.7555852798134879`. Explicit `defined_diversity_tracks_before/after` fields are present per scene and aggregate. Calibration, static guardrails, trajectory diagnostics, per-scene validator metrics, and plots are unchanged from v4; the plots are byte-identical.

    v5 hashes:
    - JSON: `8f99132b8955c48f6f5e05f4de865ceb3dacfc697b2087800a84ab491d318036`
    - `reliability_overall.svg`: `d8fb3c6ae2bbdf625066661829d7827412ec41c7d2e476343c1f1ae1d5cb7375`
    - `reliability_object.svg`: `2421f461df44b06d38c68172755ad056f3ec46cf75f9412df6718e6c57a72724`
    - `reliability_room.svg`: `ceb340fde1fcff6a3ed790761cc8b796e67815a6b6830192e71c478b66435550`

    The expanded closeout is `PHASE13_DIAGNOSTICS_2026-09-17.md`, with complete per-scene overall/object/room calibration rows and per-scene plus aggregate validator rows. It explicitly preserves the exact 94-stage/752-slot denominator, other-scene LOSO baseline, predicted-only rematching definition, and candid interpretation: pooled ECE is imbalance-dominated, room sample size is tiny, detours remain **NOT IDENTIFIABLE**, collisions remain **NOT INSTRUMENTED** (not zero), and combined usefulness remains **NOT ESTABLISHED**.

    Verification: focused Phase 13 tests are 13 passed in the container (13 collected; local Mac has 11 passed / 2 PyYAML-dependent skipped); complete offline suite is 54 passed; author-faithful evaluator suite is 11 passed; compileall and `git diff --check` pass; all three v5 SVGs parse as XML and end with valid `</svg>`; v5 mirror is byte-identical. No live run or Tailscale was launched.
