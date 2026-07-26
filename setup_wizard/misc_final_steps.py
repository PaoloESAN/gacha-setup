# Author: michael-gh1

import os
import re

import bpy
from bpy.types import Armature, Operator

from setup_wizard.domain.game_types import GameType
from setup_wizard.import_order import (
    CHARACTER_MODEL_FOLDER_FILE_PATH,
    NEVERNESS_TO_EVERNESS_SHADER_FILE_PATH,
    NextStepInvoker,
    get_cache,
)
from setup_wizard.setup_wizard_operator_base_classes import (
    BasicSetupUIOperator,
    CustomOperatorProperties,
)


class GI_OT_FinishSetup(Operator, BasicSetupUIOperator):
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

        return result


class HSR_OT_FinishSetup(Operator, BasicSetupUIOperator):
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


class ZZZ_OT_FinishSetup(Operator, BasicSetupUIOperator):
    """Finish Setup"""

    bl_idname = "zenless_zone_zero.finish_setup"
    bl_label = "Zenless Zone Zero: Finish Setup (UI)"


class NTE_OT_FinishSetup(Operator, BasicSetupUIOperator):
    """Neverness to Everness Finish Setup"""

    bl_idname = "neverness_to_everness.finish_setup"
    bl_label = "Neverness to Everness: Finish Setup (UI)"

    def execute(self, context):
        result = BasicSetupUIOperator.execute(self, context)

        # 1. Color Management -> Standard
        try:
            context.scene.display_settings.display_device = 'sRGB'
            context.scene.view_settings.view_transform = 'Standard'
        except Exception as e:
            print(f"Warning setting Standard View Transform: {e}")

        # 2. Enable Raytracing (Eevee Next / Cycles)
        try:
            if hasattr(context.scene.eevee, "use_raytracing"):
                context.scene.eevee.use_raytracing = True
            if hasattr(context.scene.eevee, "use_ssr"):
                context.scene.eevee.use_ssr = True
                context.scene.eevee.use_ssr_refraction = True
        except Exception as e:
            print(f"Warning enabling Raytracing: {e}")

        # 3. Copy Compositor Post-Processing from Shader blend file (if present)
        try:
            context.scene.use_nodes = True
            cache_enabled = context.window_manager.cache_enabled
            filepath = get_cache(cache_enabled).get(NEVERNESS_TO_EVERNESS_SHADER_FILE_PATH)
            if filepath and os.path.exists(filepath):
                inner_path = 'NodeTree'
                with bpy.data.libraries.load(filepath) as (data_from, data_to):
                    comp_trees = [name for name in data_from.node_groups if any(k in name.lower() for k in ["compositor", "post", "nte", "composite"])]
                    data_to.node_groups = comp_trees

                if data_to.node_groups and context.scene.node_tree:
                    comp_tree = context.scene.node_tree
                    ng = data_to.node_groups[0]
                    existing = next((n for n in comp_tree.nodes if n.type == 'GROUP' and n.node_tree == ng), None)
                    if not existing:
                        grp_node = comp_tree.nodes.new("CompositorNodeGroup")
                        grp_node.node_tree = ng
        except Exception as e:
            print(f"Warning setting up compositor post-processing: {e}")

        self.report({'INFO'}, 'Neverness to Everness Finish Setup completed.')
        return result



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
        armature = self._find_target_armature(context)

        if not armature:
            self.report(
                {"ERROR"}, "No armature found. Please import or select a character."
            )
            return {"CANCELLED"}

        bpy.ops.object.select_all(action="DESELECT")
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

        # HSR models are typically already oriented correctly; forcing +90° X here breaks Finish Setup.
        should_force_upright_rotation = self.game_type not in [
            GameType.ZENLESS_ZONE_ZERO.name,
            GameType.HONKAI_STAR_RAIL.name,
        ]

        if should_force_upright_rotation:
            bpy.ops.object.scale_clear()
            bpy.ops.object.rotation_clear()
            armature.rotation_euler[0] = 1.5708  # x-axis, 90 degrees

        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # clean rotation
        # bpy.ops.transform.rotate(
        #     value=1.5708,
        #     orient_axis='X',
        #     orient_type='GLOBAL',
        #     orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
        #     orient_matrix_type='GLOBAL',
        #     constraint_axis=(True, False, False),
        #     mirror=False,
        #     use_proportional_edit=False,
        #     proportional_edit_falloff='SMOOTH',
        #     proportional_size=0.1,
        #     use_proportional_connected=False,
        #     use_proportional_projected=False
        # )  # from @M4urlcl0

        bpy.ops.object.select_all(action="DESELECT")
        is_aranara = [
            material for material in bpy.data.materials if "Aranara" in material.name
        ]
        if is_aranara:
            hat_object: bpy.types.Object = bpy.data.objects.get("Hat")
            hat_object.select_set(True)
            bpy.ops.transform.rotate(
                value=-1.5708,
                orient_axis="X",
                orient_type="GLOBAL",
            )  # Could not seem to rotate the Mesh using transform_apply()

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


register, unregister = bpy.utils.register_classes_factory(GI_OT_FixTransformations)
