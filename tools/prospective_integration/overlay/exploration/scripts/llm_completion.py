from google import genai
from google.genai import types
import re,os
import networkx as nx
import spark_dsg as dsg
from pathlib import Path
import spark_dsg.networkx as dsg_nx
from bidict import bidict
import numpy as np
import yaml
import pathlib
import time
from scene_graph_visualize_2d import create_scene_slices
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
import json
import sys

# --- prospective overlay (NOT part of the pinned commit; see
# docs/prospective_overlay/README.md) -------------------------------------
# Routes generate_completion_response/generate_refinement_response through
# the real, audited gemini_campaign ledger via prospective_runtime, instead
# of an unaccounted direct google.genai call. ASP_PROSPECTIVE_TOOLS_PATH
# must point at the prospective_gemini_integration checkout's tools/
# directory; PYTHONPATH is the normal way to provide this, this is a
# defensive fallback for launch scripts that don't set it.
_prospective_tools_path = os.environ.get("ASP_PROSPECTIVE_TOOLS_PATH")
if _prospective_tools_path and _prospective_tools_path not in sys.path:
    sys.path.insert(0, _prospective_tools_path)
from gemini_campaign.errors import AccountingHalt, LedgerError
from prospective_integration.author_overlay import (
    build_completion_contents, build_refinement_contents,
    make_check_collision_executor, run_completion_turns, run_single_turn,
)
from prospective_integration.overlay_runtime import (
    LedgerContext, build_transport, deterministic_seed, make_context, record_race_instrumentation,
)
# --- end prospective overlay imports --------------------------------------

class FlowList(list):
    pass

def flow_list_representer(dumper, data):
    return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)

def validate_feasibility(label, proposed_box, existing_nodes):
    px, py, pz, pw, pd, ph = proposed_box
    p_min = np.array([px - pw/2, py - pd/2, pz - ph/2])
    p_max = np.array([px + pw/2, py + pd/2, pz + ph/2])
    p_vol = pw * pd * ph

    collisions = []
    max_iou = 0.0

    for node in existing_nodes:
        if node.get('node_type') in ['nothing', 'structure', 'object']:
            pos = json.loads(node['position']) if isinstance(node['position'], str) else node['position']
            dim = json.loads(node['dimension']) if isinstance(node['dimension'], str) else node['dimension']

            e_min = np.array([pos[0] - dim[0]/2, pos[1] - dim[1]/2, pos[2] - dim[2]/2])
            e_max = np.array([pos[0] + dim[0]/2, pos[1] + dim[1]/2, pos[2] + dim[2]/2])
            e_vol = dim[0] * dim[1] * dim[2]

            inter_min = np.maximum(p_min, e_min)
            inter_max = np.minimum(p_max, e_max)
            inter_dims = np.maximum(0, inter_max - inter_min)
            inter_vol = np.prod(inter_dims)

            if inter_vol > 0:
                union_vol = p_vol + e_vol - inter_vol
                iou = inter_vol / union_vol
                
                if iou > max_iou:
                    max_iou = iou
                
                # Store details
                collisions.append({
                    "name": node.get('name', 'Unknown'),
                    "id": node['id'],
                    "iou": round(iou, 3),
                    "overlap_percent": round((inter_vol/p_vol)*100, 1)
                })

    if collisions:
        collisions.sort(key=lambda x: x['iou'], reverse=True)
        summary_list = [f"{c['name']} (ID {c['id']}, IoU: {c['iou']})" for c in collisions]
        summary_text = "; ".join(summary_list)
        
        return {
            "name": label,
            "dimension": [pw, pd, ph],
            "position": [px, py, pz],
            "valid": False,
            "collision_count": len(collisions),
            "collisions": collisions,
        }

    return {
        "name": label,
        "dimension": [pw, pd, ph],
        "position": [px, py, pz],
        "valid": True, 
        "collision_count": 0,
        "message": "Placement is clear."
    }

class LLMCompletion:
    def __init__(self, base_path, file_to_analyze, model_name, user_prompt, seed,
                 scene_index=None, ensemble_index=None, ledger_context=None):
        self.base_path = base_path
        yaml.SafeDumper.add_representer(FlowList, flow_list_representer)
        self.file_to_analyze = file_to_analyze
        self.model_name = model_name
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.user_prompt = user_prompt
        self.seed = seed
        # --- prospective overlay: real per-call scene/member ledger
        # attribution, threaded through from LLMManager._run_single_
        # ensemble_member. None/None/None for the non-LLM preprocessing use
        # (_preprocess_dsg never calls a Gemini method, so these are unused
        # there). ledger_context is None whenever the overlay isn't
        # configured (ASP_PROSPECTIVE_LEDGER_PATH unset); the two Gemini
        # methods below fail closed in that case rather than silently
        # falling back to an unaccounted call.
        self.scene_index = scene_index
        self.ensemble_index = ensemble_index
        self.ledger_context = ledger_context

    def search_nearest_room_node(self, G, object_pos):
        room_layer = G.get_layer(dsg.DsgLayers.ROOMS)
        room_nodes = list(room_layer.nodes)
        best_parent = None
        best_distance = float('inf')
        for room_node in room_nodes:
            room_pos = room_node.attributes.position
            distance = np.linalg.norm(np.array(room_pos) - np.array(object_pos))
            if distance < best_distance:
                best_distance = distance
                best_parent = room_node.id.value
        return best_parent


    def preprocess_file(self, original_yaml_filename, node_mapping_filename):
        path_to_dsg = pathlib.Path(self.file_to_analyze).expanduser().absolute()

        # Load the scene graph
        G = dsg.DynamicSceneGraph.load(str(path_to_dsg))
        object_layer = G.get_layer(dsg.DsgLayers.OBJECTS)
        object_nodes = list(object_layer.nodes)
        for node in object_nodes:
            if node.attributes.name != "Nothing":
                place_parent = node.get_parent()
                if place_parent is None:
                    object_pos = node.attributes.position
                    room_parent = self.search_nearest_room_node(G, object_pos)
                else:
                    place_parent_node = G.get_node(place_parent)
                    room_parent = place_parent_node.get_parent()
                if room_parent is None:
                    object_pos = node.attributes.position
                    room_parent = self.search_nearest_room_node(G, object_pos)
                attr = dsg._dsg_bindings.EdgeAttributes()
                attr.weight = 1.0
                attr.weighted = False
                G.insert_edge(node.id.value, room_parent, attr)
            else:
                node.attributes.position = node.attributes.bounding_box.world_P_center

        # Convert the scene graph to a networkx graph
        easier_graph = dsg_nx.graph_to_networkx(G, include_dynamic=False)

        # Process the scene graph to find its minimal representation
        remove_nodes = []
        # Map new node IDs to original node IDs
        mapping = bidict()
        idx = 0

        # These numbers are generated by checking the first 3 digits of the node IDs in the scene graph. It may change if code changes.
        for node, attribute in easier_graph.nodes.items():
            # Segment Node
            if str(node)[:3] == '828':
                remove_nodes.append(node)
                            
            # Object Node
            elif str(node)[:3] == '799':
                new_id = idx
                mapping[new_id] = node
                idx += 1
                bounding_box_dim = attribute['bounding_box'].dimensions
                bounding_box_P = attribute['bounding_box'].world_P_center
                bounding_box_R = attribute['bounding_box'].world_R_center
                attribute['position'] = bounding_box_P
                attribute['dimension'] = bounding_box_dim
                attribute['orientation'] = bounding_box_R
                if attribute['name'] == 'Nothing':
                    attribute['node_type'] = 'nothing'
                elif (attribute['name'] == "Wall" or
                     attribute['name'] == "Window" or
                     attribute['name'] == "Curtain" or
                     attribute['name'] == "Blind" or
                     attribute['name'] == "Door"):
                    attribute['node_type'] = 'structure'
                else:
                    attribute['node_type'] = 'object'
                for key in list(attribute.keys()):
                    # Only preserve these attributes
                    if key == 'position' or key == 'node_type' or key == 'name' or key == 'is_predicted' or key == 'dimension' or key == 'orientation':
                        # Convert incompatible types to strings
                        if type(attribute[key]) == np.ndarray:
                            py_list = attribute[key].tolist()
                            if py_list and isinstance(py_list[0], list):
                                rounded_list = [[round(num, 3) for num in row] for row in py_list]
                            else:
                                rounded_list = [round(x, 3) for x in py_list]
                            attribute[key] = str(rounded_list)
                        elif type(attribute[key]) == list or type(attribute[key]) == dict:
                            attribute[key] = str(attribute[key])
                    else:
                        del attribute[key]

            # Place Node
            elif str(node)[:3] == '807':
                remove_nodes.append(node)

            # Room Node
            elif str(node)[:3] == '778':
                new_id = idx
                mapping[new_id] = node
                idx += 1
                attribute['node_type'] = 'room'
                for key in list(attribute.keys()):
                    # Only preserve these attributes
                    if key == 'name' or key == 'position' or key == 'node_type':
                        # Convert incompatible types to strings
                        if type(attribute[key]) == np.ndarray:
                            attribute[key] = str([round(x,3) for x in attribute[key].tolist()])
                        elif type(attribute[key]) == list or type(attribute[key]) == dict:
                            attribute[key] = str(attribute[key])
                    else:
                        del attribute[key]
            else:
                raise ValueError(f"Unexpected number of attributes for node {node}: {len(attribute)}")

        # Remove the nodes that we don't need
        for node in remove_nodes:
            easier_graph.remove_node(node)

        # Relabel the nodes with new IDs
        orig_to_new = dict(mapping.inverse)  # {orig_id: new_id}
        easier_graph = nx.relabel_nodes(easier_graph, orig_to_new)

        # Create a more compact YAML representation of the scene graph
        # 1. Create the list of nodes
        nodes_for_yaml = []
        for node_id, attributes in easier_graph.nodes(data=True):
            node_dict = {'id': node_id}  # Add the 'id' field
            node_dict.update(attributes) # Add all other attributes
            nodes_for_yaml.append(node_dict)

        # 2. Create the list of edges in the minimal [u, v] format
        edges_for_yaml = [FlowList(edge) for edge in easier_graph.edges()]

        data_to_dump = {
            'nodes': nodes_for_yaml,
            'edges': edges_for_yaml
        }

        # Write the data to a YAML file
        yaml_filepath = os.path.join(self.base_path, original_yaml_filename)
        with open(yaml_filepath, 'w') as yaml_file:
            yaml.safe_dump(data_to_dump, yaml_file, default_flow_style=False)

        mapping_dict = dict(mapping)
        # Define the new filepath for the mapping
        mapping_filepath = os.path.join(self.base_path, node_mapping_filename)
        # Write the mapping dictionary to its own YAML file
        with open(mapping_filepath, 'w') as mapping_file:
            yaml.safe_dump(mapping_dict, mapping_file)
    
    def _get_image_part(self, image_path):
        """Helper to create a Part from local image bytes for Gemini API."""
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        return types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')


    def generate_completion_response(self, yaml_filepath, image_dir):
        # --- prospective overlay: routed through the real gemini_campaign
        # ledger via prospective_runtime instead of a direct, unaccounted
        # google.genai call. Fails closed if the overlay isn't configured --
        # never silently falls back to the original unaccounted path.
        if self.ledger_context is None:
            raise AccountingHalt(
                "prospective overlay is not configured (ASP_PROSPECTIVE_LEDGER_PATH "
                "unset); refusing to make an unaccounted Gemini call"
            )

        with open(yaml_filepath, 'r') as file:
            yaml_content = file.read()
            yaml_data = yaml.safe_load(yaml_content)
            existing_nodes = yaml_data.get('nodes', [])

        def check_collision(label, center_x, center_y, center_z, size_x, size_y, size_z):
            proposed_box = [center_x, center_y, center_z, size_x, size_y, size_z]
            return validate_feasibility(label, proposed_box, existing_nodes)

        transport = build_transport(self.ledger_context)
        context = make_context(self.ledger_context, scene_index=self.scene_index,
                               ensemble_index=self.ensemble_index, call="completion")
        contents = build_completion_contents(self.user_prompt, yaml_content, image_dir)
        execute_tool = make_check_collision_executor(check_collision)
        response_text = run_completion_turns(
            transport, contents, context=context,
            seed_for_turn=lambda turn: deterministic_seed(
                self.ledger_context, self.scene_index, self.ensemble_index, turn, base_seed=self.seed),
            max_output_tokens=self.ledger_context.max_output_tokens,
            execute_tool=execute_tool,
        )
        if response_text is not None:
            print(response_text)
        return response_text

    def parse_response(self, response_text, yaml_filepath, new_yaml_filename):
        # Remove the outside code block markers
        match = re.search(r"```(yaml\n)?(.*)```", response_text, re.DOTALL)
        if match is None:
            # DEVIATIONS.md #41/#42: the author's original code assumed
            # this regex always matches and crashed the whole
            # ProcessPoolExecutor batch (destroying every other
            # ensemble member's already-completed work) when a single
            # response didn't contain a fenced code block. This is a
            # crash-path-only guard - on any response this regex already
            # matched, behavior is byte-identical to before. Persist the
            # raw text for audit (effective-ensemble-size is a
            # research-relevant number) and signal failure to the caller
            # instead of raising.
            audit_dir = os.path.join(os.path.dirname(yaml_filepath), "unparsed_responses")
            os.makedirs(audit_dir, exist_ok=True)
            audit_path = os.path.join(audit_dir, new_yaml_filename + ".unparsed.txt")
            with open(audit_path, 'w') as f:
                f.write(response_text)
            print(f"[parse_response] WARNING: no fenced code block found in response - "
                  f"dropping this ensemble member, raw text saved to {audit_path}")
            return False
        clean_yaml_text = match.group(2).strip()

        clean_yaml_text = clean_yaml_text.replace(u'\xa0', u' ')

        # Fix the indentation of the YAML text (only issue I found)
        if "\n    nodes:" in clean_yaml_text:
            clean_yaml_text = clean_yaml_text.replace("\n    nodes:", "\nnodes:")

        # Load the cleaned YAML text and merge it with the original YAML file
        new_data = yaml.safe_load(clean_yaml_text)
        with open(yaml_filepath, 'r') as file:
            current_data = yaml.safe_load(file)
        current_data['nodes'].extend(new_data.get('nodes', []))
        current_data['edges'].extend(new_data.get('edges', []))
        current_data['edges'] = [FlowList(edge) for edge in current_data['edges']]
        new_yaml_filepath = os.path.join(self.base_path, new_yaml_filename)
        with open(new_yaml_filepath, 'w') as file:
            yaml.safe_dump(current_data, file, default_flow_style=False)
        return True

    def generate_refinement_response(self, user_prompt, new_items_yaml, original_yaml_filepath, image_dir):
        # --- prospective overlay: same routing as generate_completion_response.
        if self.ledger_context is None:
            raise AccountingHalt(
                "prospective overlay is not configured (ASP_PROSPECTIVE_LEDGER_PATH "
                "unset); refusing to make an unaccounted Gemini call"
            )

        with open(original_yaml_filepath, 'r') as file:
            original_scene_content = file.read()

        transport = build_transport(self.ledger_context)
        context = make_context(self.ledger_context, scene_index=self.scene_index,
                               ensemble_index=self.ensemble_index, call="refinement")
        contents = build_refinement_contents(user_prompt, new_items_yaml, original_scene_content, image_dir)
        seed = deterministic_seed(self.ledger_context, self.scene_index, self.ensemble_index, 0, base_seed=self.seed)
        return run_single_turn(
            transport, contents, context=context, seed=seed,
            max_output_tokens=self.ledger_context.max_output_tokens,
        )
    

class LLMManager:
    """
    A self-contained class to manage scene graph completion using parallel processing.
    """
    def __init__(self, config):
        """Initializes the manager with a configuration object from the main pipeline."""
        self.config = config
        yaml.SafeDumper.add_representer(FlowList, flow_list_representer)
        self.user_prompt = config.LLM_COMPLETION_PROMPT

    def complete_scene_graph(self, initial_dsg_paths):
        """
        Preprocesses the scene graph and runs the ensemble
        predictions in parallel.
        """
        # 1. Preprocess all DSG files sequentially first
        processed_yaml_paths = [
            self._preprocess_dsg(dsg_path, scene_index=i)
            for i, dsg_path in enumerate(initial_dsg_paths)
        ]

        # 2. Run all ensemble predictions in a single parallel pool
        all_generated_files = []
        # The total number of jobs we need to run
        total_jobs = len(initial_dsg_paths) * self.config.LLM_ENSEMBLE_COUNT
        max_workers = min(total_jobs, self.config.MAX_PARALLEL_WORKERS)
        
        with ProcessPoolExecutor(max_workers=max_workers, mp_context=mp.get_context("spawn")) as executor:
            futures = []
            for i, processed_yaml_path in enumerate(processed_yaml_paths):
                for j in range(self.config.LLM_ENSEMBLE_COUNT):
                    future = executor.submit(
                        self._run_single_ensemble_member,
                        i,  # The index of the initial scene graph
                        j,  # The index of the ensemble member
                        processed_yaml_path
                    )
                    futures.append(future)

            for future in as_completed(futures):
                try:
                    result_path = future.result()
                    if result_path:
                        all_generated_files.append(result_path)
                except (AccountingHalt, LedgerError):
                    # --- prospective overlay: a real ledger halt (budget
                    # exhausted, misconfigured overlay, accounting failure)
                    # must actually stop the run, never be absorbed as "just
                    # another dropped member" -- that would silently let
                    # other in-flight/future workers keep spending. Cancel
                    # what hasn't started yet and propagate immediately.
                    for pending in futures:
                        pending.cancel()
                    raise
                except Exception as e:
                    print(f"ERROR: A parallel job failed: {e}")
                    # A single worker can die at the process boundary (for
                    # example during image/YAML serialization). Preserve the
                    # other completed ensemble members; the all-failed case
                    # below still returns None and triggers the outer retry.
                    continue

        # DEVIATIONS.md #41/#42: an individual dropped ensemble member
        # (unparseable response, see parse_response()/_run_single_ensemble_member())
        # no longer crashes this whole batch - futures.result() simply
        # returns None for it, same as any other "no result" case. But if
        # EVERY member of this batch failed, preserve the original
        # all-or-nothing behavior (return None) so the pipeline's own
        # outer retry loop still fires, instead of silently planning on
        # zero proposals.
        dropped = len(futures) - len(all_generated_files)
        if dropped:
            print(f"[complete_scene_graph] {dropped}/{len(futures)} ensemble members "
                  f"were dropped (unparseable response or other per-worker failure)")
        if not all_generated_files:
            print("[complete_scene_graph] ALL ensemble members failed - returning None "
                  "so the caller's outer retry fires (matches original crash-path behavior).")
            return None

        return all_generated_files

    def _run_single_ensemble_member(self, scene_index, ensemble_index, initial_yaml_filepath):
        graph_id = scene_index * self.config.LLM_ENSEMBLE_COUNT + ensemble_index
        print(f"[Scene {scene_index}, Ensemble {ensemble_index}, GraphID {graph_id}] Starting process.")

        llm_worker = LLMCompletion(
            base_path=self.config.WORKING_DIRECTORY,
            file_to_analyze=None,
            model_name=self.config.LLM_MODEL_NAME,
            user_prompt=self.user_prompt,
            seed=self.config.SEED + graph_id,
            # --- prospective overlay: real per-call scene/member ledger
            # attribution. LedgerContext.from_env() re-reads the environment
            # in THIS worker process (spawned fresh; a Ledger's sqlite3
            # connection can't be pickled from the parent), and is None
            # (fields left as defaults) whenever the overlay isn't
            # configured for this run.
            scene_index=scene_index, ensemble_index=ensemble_index,
            ledger_context=LedgerContext.from_env(),
        )

        images_dir = os.path.join(self.config.WORKING_DIRECTORY, f"scene_slices_{graph_id}")
        new_yaml_filename = f"habitat_scene_graph_new_graph_{graph_id}.yaml"
        new_yaml_filepath = os.path.join(self.config.WORKING_DIRECTORY, new_yaml_filename)

        # Create scene slice for original scene
        create_scene_slices(initial_yaml_filepath, scene_slice_folder_name=images_dir)

        start_time = time.time()
        generated_response = llm_worker.generate_completion_response(initial_yaml_filepath, images_dir)
        print(f"[Scene {scene_index}, Ensemble {ensemble_index}, GraphID {graph_id}] Generation took {time.time() - start_time:.2f}s")
        parsed_ok = llm_worker.parse_response(generated_response, initial_yaml_filepath, new_yaml_filename)
        if not parsed_ok:
            # DEVIATIONS.md #41/#42: drop only this ensemble member rather
            # than letting the AttributeError propagate and crash the
            # whole ProcessPoolExecutor batch (see parse_response()).
            print(f"[Scene {scene_index}, Ensemble {ensemble_index}, GraphID {graph_id}] "
                  f"DROPPED (unparseable response)")
            # --- prospective overlay: pure instrumentation, no behavior
            # change. See race_instrumentation.py -- complete_scene_graph()'s
            # as_completed() loop yields in completion order, so
            # generated_graphs[0] is whichever member finishes first, not
            # "ensemble member 0". No-op unless ASP_PROSPECTIVE_RACE_LOG is set.
            record_race_instrumentation(scene_index=scene_index, ensemble_index=ensemble_index,
                                        graph_id=graph_id, result_path=None)
            return None

        # Create scene slice for initial completion
        create_scene_slices(new_yaml_filepath, scene_slice_folder_name=images_dir)


        print(f"[Scene {scene_index}, Ensemble {ensemble_index}, GraphID {graph_id}] Done")
        # --- prospective overlay: pure instrumentation, see above.
        record_race_instrumentation(scene_index=scene_index, ensemble_index=ensemble_index,
                                    graph_id=graph_id, result_path=new_yaml_filepath)
        return new_yaml_filepath

    def _preprocess_dsg(self, dsg_path, scene_index):
        # TODO(huayi): We should separate the preprocessor from LLMCompletion class
        preprocessor = LLMCompletion(
            base_path=self.config.WORKING_DIRECTORY,
            file_to_analyze=dsg_path,
            model_name="", user_prompt="", seed=0
        )
        
        original_yaml_filename = f"habitat_scene_graph_original_graph{scene_index}.yaml"
        node_mapping_filename = f"node_mapping_graph{scene_index}.yaml"

        preprocessor.preprocess_file(original_yaml_filename, node_mapping_filename)
        
        processed_yaml_path = os.path.join(self.config.WORKING_DIRECTORY, original_yaml_filename)
        return processed_yaml_path
