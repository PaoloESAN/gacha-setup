# Author: michael-gh1

import os
import re

import bpy
from bpy.types import Armature, Operator

from setup_wizard.domain.game_types import GameType
from setup_wizard.import_order import (
    CHARACTER_MODEL_FOLDER_FILE_PATH,
    NEVERNESS_TO_EVERNESS_SHADER_FILE_PATH,
    NEVERNESS_TO_EVERNESS_ROOT_FOLDER_FILE_PATH,
    NextStepInvoker,
    get_cache,
    get_shader_file_path,
)
from setup_wizard.setup_wizard_operator_base_classes import (
    BasicSetupUIOperator,
    CustomOperatorProperties,
)


class GI_OT_FinishSetup(Operator, BasicSetupUIOperator, CustomOperatorProperties):
    """Finish Setup"""

    bl_idname = "genshin.finish_setup"
    bl_label = "Genshin: Finish Setup (UI)"

    def execute(self, context):
        result = BasicSetupUIOperator.execute(self, context)

        # Genshin-only: optionally run Advanced post-processing steps from Finish Setup.
        should_run_post_processing = (
            self.game_type == GameType.GENSHIN_IMPACT.name
            and context.window_manager.post_processing_setup_enabled
        )
        if should_run_post_processing:
            NextStepInvoker().invoke(
                0,
                "invoke_next_step_ui",
                high_level_step_name="HOYOVERSE_OT_post_processing_compositing_setup",
                game_type=self.game_type,
            )

        try:
            from setup_wizard.ui.gi_ui_setup_wizard_menu import sync_genshin_shader_properties
            sync_genshin_shader_properties(context.scene)
        except Exception as e_sync:
            print(f"[GI FINISH] Notice syncing shader properties: {e_sync}")

        return result


def setup_wuwa_compositor_nodes(context):
    """Sets up the Compositor post-processing node tree for Wuthering Waves using GranTurismoWrapper."""
    scene = context.scene
    addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_blend = os.path.join(addon_dir, "setup_wizard", "shaders", "wuwa", "Gustling Waters.blend")
    if not os.path.exists(target_blend):
        target_blend = os.path.join(addon_dir, "shaders", "wuwa", "Gustling Waters.blend")

    # Load GranTurismoWrapper and its dependency node groups from blend if not already in data
    if os.path.exists(target_blend):
        try:
            with bpy.data.libraries.load(target_blend, link=False) as (data_from, data_to):
                data_to.node_groups = [
                    g for g in data_from.node_groups
                    if g not in bpy.data.node_groups and ('GranTurismo' in g or 'Compositing' in g or g in ('H_f', 'W_f', 'smoothstep'))
                ]
        except Exception as e_load:
            print(f"[WUWA COMPOSITING] Notice loading node groups: {e_load}")

    # Access or create compositor tree
    tree = None
    if hasattr(scene, "compositing_node_group"):
        if not scene.compositing_node_group:
            scene.compositing_node_group = bpy.data.node_groups.new("Compositing Nodetree", "CompositorNodeTree")
        tree = scene.compositing_node_group
    else:
        scene.use_nodes = True
        tree = getattr(scene, "node_tree", None)

    if not tree:
        return

    tree.nodes.clear()

    rl = tree.nodes.new(type="CompositorNodeRLayers")
    rl.location = (-300, 0)

    gt_group = bpy.data.node_groups.get("GranTurismoWrapper [APPEND]")
    if gt_group:
        grp_node = tree.nodes.new(type="CompositorNodeGroup")
        grp_node.node_tree = gt_group
        grp_node.location = (0, 0)
        tree.links.new(rl.outputs["Image"], grp_node.inputs["Image"])

        out_type = "NodeGroupOutput" if bpy.app.version >= (5, 0, 0) else "CompositorNodeComposite"
        comp = tree.nodes.new(type=out_type)
        comp.location = (300, 100)

        if hasattr(tree, "interface") and not tree.interface.items_tree:
            try:
                tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
            except Exception:
                pass

        out_socket = comp.inputs.get("Image") or (comp.inputs[0] if comp.inputs else None)
        if out_socket:
            tree.links.new(grp_node.outputs["Result"], out_socket)

        try:
            viewer = tree.nodes.new(type="CompositorNodeViewer")
            viewer.location = (300, -100)
            tree.links.new(grp_node.outputs["Result"], viewer.inputs["Image"])
        except Exception:
            pass

    # Clean up any duplicate or leftover scenes so only the active scene remains
    current_scene = context.scene
    for sc in list(bpy.data.scenes):
        if sc != current_scene and (sc.name.startswith("Scene.") or "Scene.001" in sc.name or sc.name in ["Scene.001", "Scene.002", "Preview"]):
            try:
                bpy.data.scenes.remove(sc, do_unlink=True)
            except Exception:
                pass


class WW_OT_SetupCompositorNodes(Operator, CustomOperatorProperties):
    """Setup Wuthering Waves Compositor Post-Processing Nodes"""

    bl_idname = "wuthering_waves.setup_compositor_nodes"
    bl_label = "Wuthering Waves: Setup Compositor Nodes"

    def execute(self, context):
        try:
            setup_wuwa_compositor_nodes(context)
            self.report({'INFO'}, "Wuthering Waves compositor nodes configured.")
        except Exception as ex:
            self.report({'WARNING'}, f"Compositor setup notice: {ex}")
        return {'FINISHED'}


def setup_ake_compositor_nodes(context):
    """Sets up the Compositor post-processing node tree for Arknights: Endfield."""
    scene = context.scene
    addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_blend = os.path.join(addon_dir, "setup_wizard", "shaders", "ake", "AKE.blend")
    if not os.path.exists(target_blend):
        target_blend = os.path.join(addon_dir, "shaders", "ake", "AKE.blend")

    if os.path.exists(target_blend):
        try:
            with bpy.data.libraries.load(target_blend, link=False) as (data_from, data_to):
                data_to.node_groups = [
                    g for g in data_from.node_groups
                    if g not in bpy.data.node_groups and 'Compositing' in g
                ]
        except Exception as e_load:
            print(f"[AKE COMPOSITING] Notice loading node groups: {e_load}")

    comp_ng = bpy.data.node_groups.get("Compositing Nodetree")

    if hasattr(scene, "compositing_node_group") and comp_ng:
        scene.compositing_node_group = comp_ng
    else:
        scene.use_nodes = True
        tree = getattr(scene, "node_tree", None)
        if tree and comp_ng:
            tree.nodes.clear()
            rl = tree.nodes.new(type="CompositorNodeRLayers")
            rl.location = (-300, 0)
            grp_node = tree.nodes.new(type="CompositorNodeGroup")
            grp_node.node_tree = comp_ng
            grp_node.location = (0, 0)
            if "Image" in rl.outputs and "Image" in grp_node.inputs:
                tree.links.new(rl.outputs["Image"], grp_node.inputs["Image"])
            elif grp_node.inputs:
                tree.links.new(rl.outputs[0], grp_node.inputs[0])

            out_type = "NodeGroupOutput" if bpy.app.version >= (5, 0, 0) else "CompositorNodeComposite"
            comp = tree.nodes.new(type=out_type)
            comp.location = (300, 100)
            out_socket = comp.inputs.get("Image") or (comp.inputs[0] if comp.inputs else None)
            grp_out = grp_node.outputs.get("Image") or grp_node.outputs.get("Result") or (grp_node.outputs[0] if grp_node.outputs else None)
            if out_socket and grp_out:
                tree.links.new(grp_out, out_socket)


class AKE_OT_SetupCompositorNodes(Operator, CustomOperatorProperties):
    """Setup Arknights: Endfield Compositor Post-Processing Nodes"""

    bl_idname = "arknights_endfield.setup_compositor_nodes"
    bl_label = "Arknights Endfield: Setup Compositor Nodes"

    def execute(self, context):
        try:
            setup_ake_compositor_nodes(context)
            self.report({'INFO'}, "Arknights Endfield compositor nodes configured.")
        except Exception as ex:
            self.report({'WARNING'}, f"Compositor setup notice: {ex}")
        return {'FINISHED'}


class AKE_OT_FinishSetup(Operator, BasicSetupUIOperator, CustomOperatorProperties):
    """Finish Setup for Arknights: Endfield"""

    bl_idname = "arknights_endfield.finish_setup"
    bl_label = "Arknights Endfield: Finish Setup (UI)"

    def execute(self, context):
        result = BasicSetupUIOperator.execute(self, context)
        context.scene.display_settings.display_device = 'sRGB'
        try:
            context.scene.view_settings.view_transform = 'AgX'
            context.scene.view_settings.look = 'AgX - Medium High Contrast'
        except Exception:
            try:
                context.scene.view_settings.view_transform = 'Standard'
            except Exception:
                pass
        context.scene.render.fps = 60

        if hasattr(context.scene, "eevee"):
            if hasattr(context.scene.eevee, "use_ssr"):
                context.scene.eevee.use_ssr = True
            if hasattr(context.scene.eevee, "use_shadows"):
                context.scene.eevee.use_shadows = True

        # Setup World environment nodes
        try:
            world = context.scene.world
            world_ng = bpy.data.node_groups.get("Arknights_Endfield_Env")
            if world and world_ng:
                world.use_nodes = True
                tree = world.node_tree
                if tree:
                    out_node = next((n for n in tree.nodes if n.type == 'OUTPUT_WORLD'), None)
                    if not out_node:
                        out_node = tree.nodes.new('ShaderNodeOutputWorld')
                    for bg in [n for n in tree.nodes if n.type == 'BACKGROUND']:
                        try:
                            tree.nodes.remove(bg)
                        except Exception:
                            pass
                    grp_node = next((n for n in tree.nodes if n.type == 'GROUP' and n.node_tree == world_ng), None)
                    if not grp_node:
                        grp_node = tree.nodes.new('ShaderNodeGroup')
                        grp_node.node_tree = world_ng
                    if grp_node.outputs and out_node.inputs:
                        tree.links.new(grp_node.outputs[0], out_node.inputs[0])
        except Exception as e_w:
            print(f"[AKE FINISH] Notice setting up world nodes: {e_w}")

        # Setup Compositor post-processing nodes
        try:
            setup_ake_compositor_nodes(context)
        except Exception as e_comp:
            print(f"[AKE FINISH] Notice setting up compositor nodes: {e_comp}")

        # Ensure collection organization (Lighting inside WGTS, Light beside rig)
        try:
            from setup_wizard.set_up_head_driver import organize_ake_lighting_collections
            organize_ake_lighting_collections(context)
        except Exception as e_org:
            print(f"[AKE FINISH] Notice organizing Lighting and WGTS collections: {e_org}")

        return result


class WW_OT_FinishSetup(Operator, BasicSetupUIOperator, CustomOperatorProperties):
    """Finish Setup for Wuthering Waves"""

    bl_idname = "wuthering_waves.finish_setup"
    bl_label = "Wuthering Waves: Finish Setup (UI)"

    def execute(self, context):
        result = BasicSetupUIOperator.execute(self, context)
        context.scene.display_settings.display_device = 'sRGB'
        context.scene.view_settings.view_transform = 'Standard'
        context.scene.render.fps = 60

        if hasattr(context.scene, "eevee"):
            if hasattr(context.scene.eevee, "use_ssr"):
                context.scene.eevee.use_ssr = True
            if hasattr(context.scene.eevee, "use_shadows"):
                context.scene.eevee.use_shadows = True

        # Apply bone collection visibility and viewport display settings on rigs
        target_rig = None
        try:
            from setup_wizard.character_rig_setup.wuwa_rig_script import apply_wuwa_bone_collection_visibilities
            for obj in context.scene.objects:
                if obj.type == "ARMATURE" and (obj.name.startswith("RIG-") or "rig" in obj.name.lower()):
                    apply_wuwa_bone_collection_visibilities(obj)
                    if hasattr(obj, "data") and obj.data:
                        obj.data.display_type = 'STICK'
                        obj.data.show_bone_custom_shapes = True
                    obj.show_in_front = True
                    target_rig = obj
        except Exception as e_vis:
            print(f"[WUWA FINISH] Notice applying bone collection visibility: {e_vis}")

        if target_rig:
            try:
                bpy.ops.object.select_all(action='DESELECT')
                target_rig.select_set(True)
                context.view_layer.objects.active = target_rig
                bpy.ops.object.mode_set(mode='POSE')
            except Exception as e_mode:
                print(f"[WUWA FINISH] Notice entering pose mode: {e_mode}")

        # Setup Compositor post-processing nodes
        try:
            setup_wuwa_compositor_nodes(context)
        except Exception as e_comp:
            print(f"[WUWA FINISH] Notice setting up compositor nodes: {e_comp}")

        # Move all objects from default 'Collection' into the character's collection and remove empty 'Collection'
        char_coll = None
        for coll in bpy.data.collections:
            if coll.name not in ("Collection", "Master Collection", "Scene Collection") and not coll.name.startswith("WGTS"):
                if any(obj.type in ("ARMATURE", "MESH") for obj in coll.objects):
                    char_coll = coll
                    break

        if char_coll:
            main_coll = bpy.data.collections.get("Collection")
            if main_coll and main_coll != char_coll:
                for child_c in list(main_coll.children):
                    if child_c != char_coll:
                        if child_c.name not in context.scene.collection.children:
                            context.scene.collection.children.link(child_c)
                        try:
                            main_coll.children.unlink(child_c)
                        except Exception:
                            pass
                for obj_c in list(main_coll.objects):
                    if obj_c.name not in char_coll.objects:
                        char_coll.objects.link(obj_c)
                    try:
                        main_coll.objects.unlink(obj_c)
                    except Exception:
                        pass
                try:
                    context.scene.collection.children.unlink(main_coll)
                except Exception:
                    pass
                try:
                    bpy.data.collections.remove(main_coll, do_unlink=True)
                except Exception:
                    pass

        # Delete rogue Cube objects and duplicate .001 control objects
        for obj in list(bpy.data.objects):
            if obj.name.lower().startswith("cube") and obj.type == 'MESH':
                if not any(k in obj.name.lower() for k in ["body", "cloth", "face", "hair", "eye", "head"]):
                    try:
                        bpy.data.objects.remove(obj, do_unlink=True)
                    except Exception:
                        pass

        for base_name in ['Head Origin', 'Head Forward', 'Head Up', 'Light Direction', 'Sun', 'Eye Highlight', 'Highlight Top', 'Highlight Bottom']:
            orig_obj = bpy.data.objects.get(base_name)
            for obj in list(bpy.data.objects):
                if obj != orig_obj and (obj.name.startswith(f"{base_name}.") or (base_name.lower() in obj.name.lower() and ('.00' in obj.name or '.01' in obj.name))):
                    try:
                        bpy.data.objects.remove(obj, do_unlink=True)
                    except Exception:
                        pass

        # Remove any extra scenes created during append or setup
        current_scene = context.scene
        for sc in list(bpy.data.scenes):
            if sc != current_scene and (sc.name.startswith("Scene.") or "Scene.001" in sc.name or sc.name in ["Scene.001", "Scene.002", "Preview"]):
                try:
                    bpy.data.scenes.remove(sc, do_unlink=True)
                except Exception:
                    pass

        self.report({'INFO'}, "Finished Wuthering Waves setup successfully!")
        return result


class HSR_OT_FinishSetup(Operator, BasicSetupUIOperator, CustomOperatorProperties):
    """Finish Setup"""

    bl_idname = "honkai_star_rail.finish_setup"
    bl_label = "Honkai Star Rail: Finish Setup (UI)"

    def execute(self, context):
        result = BasicSetupUIOperator.execute(self, context)
        try:
            self._rename_hsr_character_collection_and_rig(context)
        except Exception as err:
            self.report({"WARNING"}, f"HSR rename pass skipped: {err}")
        return result

    def _rename_hsr_character_collection_and_rig(self, context):
        armature = self._find_target_armature(context)
        if not armature:
            return

        model_name = self._derive_model_name(context, armature)
        if not model_name:
            return

        new_rig_name = f"{model_name}Rig"
        if armature.name != new_rig_name:
            armature.name = self._unique_object_name(new_rig_name)

        if armature.data:
            armature.data.name = armature.name

        parent_collection = self._find_parent_collection_for_object(armature)
        if parent_collection and parent_collection.name != model_name:
            parent_collection.name = self._unique_collection_name(model_name)

    def _find_target_armature(self, context):
        view_layer_objs = getattr(context.view_layer, "objects", context.scene.objects)

        armatures = [obj for obj in context.selected_objects if obj.type == "ARMATURE"]
        if armatures:
            return armatures[0]

        for obj in view_layer_objs:
            if obj.type == "ARMATURE" and obj.name.endswith("Rig") and not any(ign in obj.name.lower() for ign in ["eyerig", "facerig", "lighting", "metarig"]):
                return obj

        for obj in view_layer_objs:
            if obj.type == "ARMATURE" and not any(ign in obj.name.lower() for ign in ["eyerig", "facerig", "lighting", "metarig"]):
                return obj

        for obj in bpy.data.objects:
            if obj.type == "ARMATURE" and obj.name.endswith("Rig") and not any(ign in obj.name.lower() for ign in ["eyerig", "facerig", "lighting", "metarig"]):
                if obj.name in view_layer_objs:
                    return obj

        return None

    def _derive_model_name(self, context, armature):
        # 1) Prefer the exact FBX directory captured at model import time.
        model_dir = ""
        scene = context.scene
        fbx_dir = scene.get("setup_wizard_imported_model_dir") or ""
        if fbx_dir:
            model_dir = fbx_dir
        else:
            # 2) Fallback to cache value (may sometimes point to Textures in some flows).
            cache = get_cache(context.window_manager.cache_enabled)
            model_dir = cache.get(CHARACTER_MODEL_FOLDER_FILE_PATH, "")

        raw_name = os.path.basename(os.path.normpath(model_dir)) if model_dir else ""

        # If we landed on a generic asset folder, step one directory up.
        generic_dirs = {
            "textures",
            "texture",
            "materials",
            "material",
            "maps",
            "images",
        }
        if raw_name.lower() in generic_dirs and model_dir:
            parent_dir = os.path.dirname(os.path.normpath(model_dir))
            if parent_dir:
                raw_name = os.path.basename(parent_dir)

        if not raw_name:
            raw_name = armature.name.replace("Rig", "")

        # Normalize names such as Art_Sparxie_01 -> Sparxie
        normalized = raw_name.replace("-", "_").replace(" ", "_")
        normalized = re.sub(
            r"^(Avatar|Art|Player)_", "", normalized, flags=re.IGNORECASE
        )
        normalized = re.sub(r"_?\d+$", "", normalized)
        normalized = re.sub(r"^[^A-Za-z]+", "", normalized)

        if "_" in normalized:
            parts = [p for p in normalized.split("_") if p and not p.isdigit()]
            if parts:
                normalized = parts[0]

        normalized = normalized.strip("_")
        return normalized or "Character"

    def _find_parent_collection_for_object(self, obj):
        scene_root = bpy.context.scene.collection
        for coll in bpy.data.collections:
            if obj.name in coll.objects:
                if coll.name.startswith("wgt"):
                    continue
                if coll.name in scene_root.children:
                    return coll
        for coll in bpy.data.collections:
            if obj.name in coll.objects and not coll.name.startswith("wgt"):
                return coll
        return None

    def _unique_object_name(self, desired_name):
        if not bpy.data.objects.get(desired_name):
            return desired_name
        idx = 1
        while bpy.data.objects.get(f"{desired_name}.{idx:03d}"):
            idx += 1
        return f"{desired_name}.{idx:03d}"

    def _unique_collection_name(self, desired_name):
        if not bpy.data.collections.get(desired_name):
            return desired_name
        idx = 1
        while bpy.data.collections.get(f"{desired_name}.{idx:03d}"):
            idx += 1
        return f"{desired_name}.{idx:03d}"


class ZZZ_OT_FinishSetup(Operator, BasicSetupUIOperator, CustomOperatorProperties):
    """Finish Setup"""

    bl_idname = "zenless_zone_zero.finish_setup"
    bl_label = "Zenless Zone Zero: Finish Setup (UI)"


class NTE_OT_SetupCompositorNodes(Operator, CustomOperatorProperties):
    """Setup Neverness to Everness Compositor Post-Processing Nodes"""

    bl_idname = "neverness_to_everness.setup_compositor_nodes"
    bl_label = "Neverness to Everness: Setup Compositor Nodes"

    def execute(self, context):
        scene = context.scene
        try:
            scene.use_nodes = True

            # Get or create compositor node tree (Blender 4.x / 5.x compatible)
            node_tree = getattr(scene, "node_tree", None)
            if not node_tree and hasattr(scene, "compositing_node_group"):
                if not scene.compositing_node_group:
                    scene.compositing_node_group = bpy.data.node_groups.new(
                        "Compositing Nodetree", "CompositorNodeTree"
                    )
                node_tree = scene.compositing_node_group

            if not node_tree:
                node_tree = bpy.data.node_groups.new(
                    "Compositing Nodetree", "CompositorNodeTree"
                )
                if hasattr(scene, "compositing_node_group"):
                    scene.compositing_node_group = node_tree

            # 1. WIPE EXISTING COMPOSITOR NODES CLEANLY
            node_tree.nodes.clear()

            # 2. Locate YH Shader.blend or cached shader blend file
            cache = get_cache(context.window_manager.cache_enabled)
            filepath = cache.get(NEVERNESS_TO_EVERNESS_SHADER_FILE_PATH, "")
            root_dir = cache.get(NEVERNESS_TO_EVERNESS_ROOT_FOLDER_FILE_PATH, "")

            target_blend = get_shader_file_path(GameType.NEVERNESS_TO_EVERNESS.name, 'main')
            if not target_blend or not os.path.isfile(target_blend):
                if filepath and os.path.isfile(filepath):
                    target_blend = filepath
                elif filepath and os.path.isdir(filepath):
                    c = os.path.join(filepath, "YH Shader.blend")
                    if os.path.exists(c):
                        target_blend = c
                if not target_blend and root_dir:
                    c = os.path.join(root_dir, "YH Shader.blend")
                    if os.path.exists(c):
                        target_blend = c

            if not target_blend or not os.path.exists(target_blend):
                addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                for rel_path in [
                    "setup_wizard/shaders/nte/YH Shader.blend",
                    "shaders/nte/YH Shader.blend",
                    "shader/YH Shader.blend",
                    "YH Shader.blend",
                ]:
                    candidate = os.path.join(addon_dir, rel_path)
                    if os.path.exists(candidate):
                        target_blend = candidate
                        break

            source_tree = None
            temp_scenes = []
            if target_blend and os.path.exists(target_blend):
                try:
                    with bpy.data.libraries.load(target_blend) as (data_from, data_to):
                        data_to.scenes = list(data_from.scenes)
                        data_to.node_groups = list(data_from.node_groups)

                    temp_scenes = [sc for sc in data_to.scenes if sc]
                    for sc in temp_scenes:
                        if sc and hasattr(sc, "node_tree") and sc.node_tree and sc.node_tree.nodes:
                            source_tree = sc.node_tree
                            break
                        elif sc and hasattr(sc, "compositing_node_group") and sc.compositing_node_group and sc.compositing_node_group.nodes:
                            source_tree = sc.compositing_node_group
                            break
                except Exception as ex_load:
                    print(f"Notice loading compositor source tree: {ex_load}")

            # 3. IF SOURCE TREE FOUND IN BLEND FILE, CLONE ENTIRE NODE TREE
            if source_tree and source_tree.nodes:
                node_map = {}
                for src_node in source_tree.nodes:
                    # Skip static placeholder image nodes
                    if getattr(src_node, "type", "") == "IMAGE" or "CompositorNodeImage" in src_node.bl_idname:
                        continue

                    new_node = None
                    candidates = [src_node.bl_idname]
                    if 'Composite' in src_node.bl_idname or src_node.type == 'COMPOSITE':
                        candidates.extend(['NodeGroupOutput', 'CompositorNodeGroupOutput', 'NodeComposite', 'CompositorNodeOutput', 'CompositorNodeComposite'])

                    for cand in candidates:
                        try:
                            new_node = node_tree.nodes.new(cand)
                            break
                        except Exception:
                            pass

                    if new_node:
                        node_map[src_node] = new_node
                        new_node.location = src_node.location
                        if hasattr(src_node, "node_tree") and src_node.node_tree:
                            new_node.node_tree = src_node.node_tree

                        # Copy node properties BEFORE creating links
                        for prop in ("data_type", "blend_type", "mode", "use_clamp", "label", "filter_type", "size_x", "size_y"):
                            if hasattr(src_node, prop) and hasattr(new_node, prop):
                                try:
                                    setattr(new_node, prop, getattr(src_node, prop))
                                except Exception:
                                    pass

                        # Explicitly unclamp factor on Mix nodes
                        if "Mix" in new_node.bl_idname or getattr(new_node, "type", "") == "MIX_RGB":
                            if hasattr(new_node, "clamp_factor"):
                                new_node.clamp_factor = False
                            if hasattr(new_node, "use_clamp"):
                                new_node.use_clamp = False
                            if hasattr(new_node, "clamp_result"):
                                new_node.clamp_result = False

                        for i, inp in enumerate(src_node.inputs):
                            if i < len(new_node.inputs) and hasattr(inp, "default_value"):
                                try:
                                    new_node.inputs[i].default_value = inp.default_value
                                except Exception:
                                    pass

                for link in source_tree.links:
                    try:
                        from_node = node_map.get(link.from_node)
                        to_node = node_map.get(link.to_node)
                        if from_node and to_node:
                            from_socket = from_node.outputs.get(link.from_socket.name) or (from_node.outputs[link.from_socket.index] if link.from_socket.index < len(from_node.outputs) else None)
                            to_socket = to_node.inputs.get(link.to_socket.name) or (to_node.inputs[link.to_socket.index] if link.to_socket.index < len(to_node.inputs) else None)
                            if from_socket and to_socket:
                                node_tree.links.new(from_socket, to_socket)
                    except Exception as ex_link:
                        print(f"Notice linking copied compositor node: {ex_link}")
            else:
                # 4. FALLBACK: BUILD CLEAN COMPOSITOR NODES WITHOUT BROKEN SOCKETS
                rl_node = None
                for cand in ["CompositorNodeRLayers", "NodeRLayers", "CompositorNodeRenderLayers"]:
                    try:
                        rl_node = node_tree.nodes.new(cand)
                        break
                    except Exception:
                        pass
                if rl_node:
                    rl_node.location = (-600, 200)

                comp_out = None
                for cand in ["NodeGroupOutput", "CompositorNodeComposite", "CompositorNodeGroupOutput", "NodeComposite", "CompositorNodeOutput"]:
                    try:
                        comp_out = node_tree.nodes.new(cand)
                        break
                    except Exception:
                        pass
                if comp_out:
                    comp_out.location = (650, 300)

                viewer_node = None
                for cand in ["CompositorNodeViewer", "NodeViewer"]:
                    try:
                        viewer_node = node_tree.nodes.new(cand)
                        break
                    except Exception:
                        pass
                if viewer_node:
                    viewer_node.location = (650, 100)

                gt_group = (
                    bpy.data.node_groups.get("GranTurismoWrapper [APPEND]")
                    or bpy.data.node_groups.get("HoYoverse - Post Processing")
                    or bpy.data.node_groups.get("NTE - Post Processing")
                )

                if gt_group:
                    gt_node = node_tree.nodes.new("CompositorNodeGroup")
                    gt_node.node_tree = gt_group
                    gt_node.location = (-100, 200)

                    rl_img = rl_node.outputs.get("Image") if rl_node else None
                    gt_in = gt_node.inputs.get("Image") or (
                        gt_node.inputs[0] if gt_node.inputs else None
                    )
                    gt_out = (
                        gt_node.outputs.get("Result")
                        or gt_node.outputs.get("Image")
                        or (gt_node.outputs[0] if gt_node.outputs else None)
                    )

                    comp_in = comp_out.inputs.get("Image") or (
                        comp_out.inputs[0] if comp_out and comp_out.inputs else None
                    )
                    viewer_in = (
                        viewer_node.inputs.get("Image")
                        if viewer_node and viewer_node.inputs
                        else None
                    )

                    if rl_img and gt_in:
                        node_tree.links.new(rl_img, gt_in)
                    if gt_out and comp_in:
                        node_tree.links.new(gt_out, comp_in)
                    if gt_out and viewer_in:
                        node_tree.links.new(gt_out, viewer_in)
                else:
                    rl_img = rl_node.outputs.get("Image") if rl_node else None
                    comp_in = comp_out.inputs.get("Image") or (
                        comp_out.inputs[0] if comp_out and comp_out.inputs else None
                    )
                    viewer_in = (
                        viewer_node.inputs.get("Image")
                        if viewer_node and viewer_node.inputs
                        else None
                    )
                    if rl_img and comp_in:
                        node_tree.links.new(rl_img, comp_in)
                    if rl_img and viewer_in:
                        node_tree.links.new(rl_img, viewer_in)

            # 5. REMOVE TEMPORARY / DUPLICATE SCENES SO ONLY THE ACTIVE SCENE REMAINS
            for sc in temp_scenes:
                if sc and sc != scene and sc.name in bpy.data.scenes:
                    try:
                        bpy.data.scenes.remove(sc, do_unlink=True)
                    except Exception as ex_sc:
                        print(f"Notice removing temp scene {sc.name}: {ex_sc}")

            for sc in list(bpy.data.scenes):
                if sc != scene and ("Scene.001" in sc.name or sc.name.startswith("Scene.")):
                    try:
                        bpy.data.scenes.remove(sc, do_unlink=True)
                    except Exception:
                        pass

            # 6. ENSURE RENDER LAYERS POINTS TO ACTIVE SCENE
            rl_node = next((n for n in node_tree.nodes if getattr(n, "type", "") in ("R_LAYERS", "RENDER_LAYERS") or "RLayers" in n.bl_idname or "RenderLayers" in n.bl_idname), None)
            if rl_node:
                try:
                    rl_node.scene = scene
                except Exception:
                    pass

            # 7. CONNECT RENDER LAYERS IMAGE DIRECTLY TO BLUR IMAGE INPUT
            blur_node = next((n for n in node_tree.nodes if getattr(n, "type", "") == "BLUR" or "Blur" in n.bl_idname or "blur" in n.name.lower()), None)
            if rl_node and blur_node:
                rl_img = rl_node.outputs.get("Image") or (rl_node.outputs[0] if rl_node.outputs else None)
                blur_in = blur_node.inputs.get("Image") or (blur_node.inputs[0] if blur_node.inputs else None)
                if rl_img and blur_in:
                    for l in list(blur_in.links):
                        node_tree.links.remove(l)
                    node_tree.links.new(rl_img, blur_in)

            # Clean any remaining standalone image nodes
            for n in list(node_tree.nodes):
                if getattr(n, "type", "") == "IMAGE" or "CompositorNodeImage" in n.bl_idname:
                    try:
                        node_tree.nodes.remove(n)
                    except Exception:
                        pass

            # 8. POST-FIX: ENSURE BLENDER 5.x NODE_TREE INTERFACE HAS 'Image' OUTPUT SOCKET FOR Group Output
            if hasattr(node_tree, "interface"):
                try:
                    items = getattr(node_tree.interface, "items_tree", None) or getattr(node_tree.interface, "sockets", [])
                    has_image = any(getattr(item, "name", "") == "Image" and getattr(item, "in_out", "") == "OUTPUT" for item in items)
                    if not has_image:
                        node_tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
                except Exception as ex_iface:
                    print(f"Notice setting compositor interface socket: {ex_iface}")
            elif hasattr(node_tree, "outputs") and not any(s.name == "Image" for s in node_tree.outputs):
                try:
                    node_tree.outputs.new("NodeSocketColor", "Image")
                except Exception:
                    pass

            out_node = next((n for n in node_tree.nodes if getattr(n, "type", "") in ("COMPOSITE", "GROUP_OUTPUT", "OUTPUT_GROUP")), None)
            viewer_node = next((n for n in node_tree.nodes if getattr(n, "type", "") == "VIEWER"), None)

            if out_node and out_node.inputs:
                out_in = out_node.inputs.get("Image") or out_node.inputs[0]
                if viewer_node and viewer_node.inputs and viewer_node.inputs[0].is_linked:
                    v_link = viewer_node.inputs[0].links[0]
                    try:
                        node_tree.links.new(v_link.from_socket, out_in)
                    except Exception as ex_link:
                        print(f"Notice connecting output node image: {ex_link}")

            # NTE Post Processing default render settings
            scene.render.film_transparent = False
            if hasattr(node_tree, "use_two_pass"):
                node_tree.use_two_pass = True

            self.report(
                {"INFO"},
                "Neverness to Everness Compositor nodes cleared and configured successfully.",
            )
        except Exception as e:
            self.report({"ERROR"}, f"Failed setting up NTE Compositor nodes: {e}")

        if self.next_step_idx:
            NextStepInvoker().invoke(
                self.next_step_idx,
                self.invoker_type,
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
            )
        return {"FINISHED"}


class NTE_OT_FinishSetup(Operator, BasicSetupUIOperator, CustomOperatorProperties):
    """Neverness to Everness Finish Setup"""

    bl_idname = "neverness_to_everness.finish_setup"
    bl_label = "Neverness to Everness: Finish Setup (UI)"

    def execute(self, context):
        return BasicSetupUIOperator.execute(self, context)



class GI_OT_FixTransformations(Operator, CustomOperatorProperties):
    """Makes the Character Upright and Fixes Scale"""

    bl_idname = "genshin.fix_transformations"
    bl_label = "Genshin: Makes Character Upright and Fixes Scale"

    def _find_target_armature(self, context):
        view_layer_objs = getattr(context.view_layer, "objects", context.scene.objects)

        armatures = [obj for obj in context.selected_objects if obj.type == "ARMATURE"]
        if armatures:
            return armatures[0]

        for obj in view_layer_objs:
            if obj.type == "ARMATURE" and obj.name.endswith("Rig") and not any(ign in obj.name.lower() for ign in ["eyerig", "facerig", "lighting", "metarig"]):
                return obj

        for obj in view_layer_objs:
            if obj.type == "ARMATURE" and not any(ign in obj.name.lower() for ign in ["eyerig", "facerig", "lighting", "metarig"]):
                return obj

        for obj in bpy.data.objects:
            if obj.type == "ARMATURE" and obj.name.endswith("Rig") and not any(ign in obj.name.lower() for ign in ["eyerig", "facerig", "lighting", "metarig"]):
                if obj.name in view_layer_objs:
                    return obj

        return None

    def execute(self, context):
        if context.object and context.object.mode != "OBJECT":
            try:
                bpy.ops.object.mode_set(mode="OBJECT")
            except Exception:
                pass

        armature = self._find_target_armature(context)

        # Check if weapon / equipment
        fbx_path = context.scene.get("setup_wizard_imported_fbx_path", "")
        fbx_name = os.path.basename(fbx_path) if fbx_path else ""
        is_equip = False
        if fbx_name and not fbx_name.startswith("Avatar_") and (fbx_name.startswith(("Equip_", "EquipSkin_")) or "equip" in fbx_name.lower()):
            is_equip = True
        elif not any(obj.name.startswith("Avatar_") for obj in (context.selected_objects or context.scene.objects)):
            if any(obj.name.startswith(("Equip_", "EquipSkin_")) for obj in (context.selected_objects or context.scene.objects)):
                is_equip = True

        if is_equip or not armature:
            for obj in (context.selected_objects or context.scene.objects):
                if obj.type == 'MESH':
                    try:
                        context.view_layer.objects.active = obj
                        obj.select_set(True)
                        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                    except Exception:
                        pass
            self.report({"INFO"}, "Transformations handled for weapon / model without armature.")
            if self.next_step_idx:
                NextStepInvoker().invoke(
                    self.next_step_idx,
                    self.invoker_type,
                    high_level_step_name=self.high_level_step_name,
                    game_type=self.game_type,
                )
            super().clear_custom_properties()
            return {"FINISHED"}

        for obj in context.selected_objects:
            try:
                obj.select_set(False)
            except Exception:
                pass

        try:
            armature.select_set(True)
            context.view_layer.objects.active = armature
        except Exception as e:
            print(f"Warning setting active armature: {e}")

        # I don't want to modify any characters unless absolutely necessary
        # So, as Dehya comes with keyframes and is not in an A-Pose by default, let's clean her character
        #   - This must be done before the rigging step, otherwise the rig setup will not be upright!
        if "Dehya" in armature.name and armature.animation_data:
            self.clean_character(armature)

        # HSR, ZZZ, NTE, WuWa, and AKE models are typically already oriented correctly; forcing +90° X here breaks them.
        should_force_upright_rotation = self.game_type not in [
            GameType.ZENLESS_ZONE_ZERO.name,
            GameType.HONKAI_STAR_RAIL.name,
            GameType.NEVERNESS_TO_EVERNESS.name,
            GameType.WUTHERING_WAVES.name,
            GameType.ARKNIGHTS_ENDFIELD.name,
        ]

        try:
            if should_force_upright_rotation:
                bpy.ops.object.scale_clear()
                bpy.ops.object.rotation_clear()
                armature.rotation_euler[0] = 1.5708  # x-axis, 90 degrees

            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        except Exception as e:
            print(f"Warning in transform_apply: {e}")

        for obj in context.selected_objects:
            try:
                obj.select_set(False)
            except Exception:
                pass

        is_aranara = [
            material for material in bpy.data.materials if "Aranara" in material.name
        ]
        if is_aranara:
            hat_object: bpy.types.Object = bpy.data.objects.get("Hat")
            if hat_object:
                hat_object.select_set(True)
                try:
                    bpy.ops.transform.rotate(
                        value=-1.5708,
                        orient_axis="X",
                        orient_type="GLOBAL",
                    )
                except Exception as e:
                    print(f"Warning rotating Aranara hat: {e}")

        if self.next_step_idx:
            NextStepInvoker().invoke(
                self.next_step_idx,
                self.invoker_type,
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
            )
        return {"FINISHED"}

    def clean_character(self, armature):
        armature.animation_data_clear()
        self.reset_pose(armature)

    def reset_pose(self, armature):
        pose = armature.pose

        for bone in pose.bones:
            bone: bpy.types.PoseBone
            bone.matrix_basis.identity()


register, unregister = bpy.utils.register_classes_factory([GI_OT_FixTransformations])
