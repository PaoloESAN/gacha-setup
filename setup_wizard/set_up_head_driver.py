# Author: michael-gh1

import bpy
from bpy.types import Operator

from setup_wizard.import_order import NextStepInvoker
from setup_wizard.setup_wizard_operator_base_classes import CustomOperatorProperties

HEAD_DRIVER_OBJECT_NAME = "Head Driver"
HEAD_ORIGIN_OBJECT_NAME = "Head Origin"


class GI_OT_SetUpHeadDriver(Operator, CustomOperatorProperties):
    """Sets up Head Driver"""

    bl_idname = "genshin.setup_head_driver"
    bl_label = "Genshin: Setup Head Driver"

    def execute(self, context):
        # Try to find the correct armature
        armatures = [
            obj for obj in bpy.context.selected_objects if obj.type == "ARMATURE"
        ]
        if not armatures:
            armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]

        if not armatures:
            self.report({"ERROR"}, "No armature found")
            return {"CANCELLED"}

        armature = armatures[0]
        char_name = (
            armature.name.replace("Rig", "")
            if "Rig" in armature.name
            else armature.name
        )

        head_driver_object = (
            bpy.data.objects.get(f"{HEAD_DRIVER_OBJECT_NAME}_{char_name}")
            or bpy.data.objects.get(f"{HEAD_ORIGIN_OBJECT_NAME}_{char_name}")
            or bpy.data.objects.get(f"Head Direction_{char_name}")
            or bpy.data.objects.get(f"{char_name}Head Direction")
            or bpy.data.objects.get(f"{char_name} Head Direction")
            or bpy.data.objects.get(HEAD_DRIVER_OBJECT_NAME)
            or bpy.data.objects.get(HEAD_ORIGIN_OBJECT_NAME)
            or bpy.data.objects.get("Head Direction")
        )

        if not head_driver_object:
            self.report({"ERROR"}, "Head Driver / Head Direction not found")
            return {"CANCELLED"}

        child_of_constraint = self._get_child_of_constraint(head_driver_object)

        if not child_of_constraint:
            self.report(
                {"WARNING"},
                f"No Child Of constraint found on '{head_driver_object.name}'. Skipping head-driver inverse setup.",
            )
        else:
            armature_bones = armature.data.bones
            head_bone_names = [
                b for b in ["head", "Head", "DEF-head", "DEF-spine.006"]
                if b in armature_bones
            ] or [
                bone_name
                for bone_name in armature_bones.keys()
                if "Head" in bone_name or "head" in bone_name or bone_name == "DEF-spine.006"
            ]
            if head_bone_names:
                head_bone_name = head_bone_names[0]  # expecting 1 Head bone
                saved_matrix = head_driver_object.matrix_world.copy()
                self.set_contraint_target_and_bone(
                    child_of_constraint, armature, head_bone_name
                )
                self.set_inverse(head_driver_object, child_of_constraint.name)
                head_driver_object.matrix_world = saved_matrix
            else:
                self.report({"WARNING"}, "No head bone found for head-driver setup.")

        # Mover Head Direction, Lighting Panel y widgets a 'lights' solo si es ZZZ, si no a 'wgt'
        if self.game_type == "ZENLESS_ZONE_ZERO":
            self._move_head_driver_system_to_lights(head_driver_object)
        else:
            self._move_head_driver_system_to_wgt(head_driver_object)

        if self.next_step_idx:
            NextStepInvoker().invoke(
                self.next_step_idx,
                self.invoker_type,
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
            )
        return {"FINISHED"}

    def _get_child_of_constraint(self, obj):
        for constraint in obj.constraints:
            if constraint.type == "CHILD_OF":
                return constraint
        return None

    def set_contraint_target_and_bone(self, constraint, armature, bone_name):
        constraint.target = armature
        constraint.subtarget = bone_name

    def _move_head_driver_system_to_wgt(self, main_obj):
        wgt_coll = bpy.data.collections.get("wgt")
        if not wgt_coll:
            wgt_coll = bpy.data.collections.new("wgt")
            bpy.context.scene.collection.children.link(wgt_coll)

        def get_all_children(obj):
            children = []
            for child in obj.children:
                children.append(child)
                children.extend(get_all_children(child))
            return children

        all_objects = [main_obj] + get_all_children(main_obj)
        for obj in all_objects:
            if obj.name not in wgt_coll.objects:
                wgt_coll.objects.link(obj)
            for coll in list(obj.users_collection):
                if coll != wgt_coll:
                    try:
                        coll.objects.unlink(obj)
                    except Exception:
                        pass
            try:
                obj.hide_viewport = True
                obj.hide_render = True
            except Exception:
                pass

        try:
            wgt_coll.hide_viewport = True
            wgt_coll.hide_render = True
        except Exception:
            pass

    def _move_head_driver_system_to_lights(self, main_obj=None):
        move_lighting_and_head_driver_to_lights(main_obj)

    def set_inverse(self, obj, constraint_name):
        previous_hide_viewport = getattr(obj, "hide_viewport", False)
        obj.hide_viewport = False

        changed_lcs = []
        def enable_layer_colls(lc, target_name):
            if lc.exclude:
                lc.exclude = False
                changed_lcs.append(lc)
            for child in lc.children:
                if target_name in child.collection.objects or child.name == "wgt":
                    if child.exclude:
                        child.exclude = False
                        changed_lcs.append(child)
                    enable_layer_colls(child, target_name)

        try:
            enable_layer_colls(bpy.context.view_layer.layer_collection, obj.name)
        except Exception:
            pass

        previous_active = bpy.context.view_layer.objects.active
        previous_selected = list(bpy.context.selected_objects)

        try:
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.constraint.childof_set_inverse(
                constraint=constraint_name, owner="OBJECT"
            )
        except Exception as err:
            self.report(
                {"WARNING"}, f"Could not set Child Of inverse on '{obj.name}': {err}"
            )
        finally:
            try:
                bpy.ops.object.select_all(action="DESELECT")
                for selected in previous_selected:
                    if selected and selected.name in bpy.context.view_layer.objects:
                        selected.select_set(True)
                if (
                    previous_active
                    and previous_active.name in bpy.context.view_layer.objects
                ):
                    bpy.context.view_layer.objects.active = previous_active
            except Exception:
                pass
            
            try:
                obj.hide_viewport = previous_hide_viewport
            except Exception:
                pass
            for lc in changed_lcs:
                try:
                    lc.exclude = True
                except Exception:
                    pass


class ZZZ_OT_SetUpHeadDriver(Operator, CustomOperatorProperties):
    """Sets up Head Driver specifically for Zenless Zone Zero"""

    bl_idname = "zenless_zone_zero.setup_head_driver"
    bl_label = "ZZZ: Setup Head Driver"

    def execute(self, context):
        armatures = [
            obj for obj in bpy.context.selected_objects if obj.type == "ARMATURE"
        ]
        if not armatures:
            armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE" and obj.name not in ["metarig", "rig"]]
        if not armatures:
            armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]

        if not armatures:
            self.report({"ERROR"}, "No armature found")
            return {"CANCELLED"}

        armature = armatures[0]
        char_name = (
            armature.name.replace("Rig", "").replace("_UI", "")
            if "Rig" in armature.name
            else armature.name.replace("_UI", "")
        )

        head_driver_object = (
            bpy.data.objects.get(f"{HEAD_DRIVER_OBJECT_NAME}_{char_name}")
            or bpy.data.objects.get(f"{HEAD_ORIGIN_OBJECT_NAME}_{char_name}")
            or bpy.data.objects.get(f"Head Direction_{char_name}")
            or bpy.data.objects.get(f"{char_name}Head Direction")
            or bpy.data.objects.get(f"{char_name} Head Direction")
            or bpy.data.objects.get(HEAD_DRIVER_OBJECT_NAME)
            or bpy.data.objects.get(HEAD_ORIGIN_OBJECT_NAME)
            or bpy.data.objects.get("Head Direction")
        )

        if head_driver_object:
            child_of_constraint = self._get_child_of_constraint(head_driver_object)
            if child_of_constraint:
                armature_bones = armature.data.bones
                head_bone_names = [
                    b for b in ["head", "Head", "DEF-head", "DEF-spine.006"]
                    if b in armature_bones
                ] or [
                    bone_name
                    for bone_name in armature_bones.keys()
                    if "Head" in bone_name or "head" in bone_name or bone_name == "DEF-spine.006"
                ]
                if head_bone_names:
                    head_bone_name = head_bone_names[0]
                    saved_matrix = head_driver_object.matrix_world.copy()
                    self.set_contraint_target_and_bone(
                        child_of_constraint, armature, head_bone_name
                    )
                    self.set_inverse(head_driver_object, child_of_constraint.name)
                    head_driver_object.matrix_world = saved_matrix

        move_lighting_and_head_driver_to_lights(head_driver_object)

        if self.next_step_idx:
            NextStepInvoker().invoke(
                self.next_step_idx,
                self.invoker_type,
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
            )
        return {"FINISHED"}

    def _get_child_of_constraint(self, obj):
        for constraint in obj.constraints:
            if constraint.type == "CHILD_OF":
                return constraint
        return None

    def set_contraint_target_and_bone(self, constraint, armature, bone_name):
        constraint.target = armature
        constraint.subtarget = bone_name

    def set_inverse(self, obj, constraint_name):
        previous_hide_viewport = getattr(obj, "hide_viewport", False)
        obj.hide_viewport = False
        previous_active = bpy.context.view_layer.objects.active
        previous_selected = list(bpy.context.selected_objects)

        try:
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.constraint.childof_set_inverse(
                constraint=constraint_name, owner="OBJECT"
            )
        except Exception as err:
            self.report(
                {"WARNING"}, f"Could not set Child Of inverse on '{obj.name}': {err}"
            )
        finally:
            try:
                bpy.ops.object.select_all(action="DESELECT")
                for selected in previous_selected:
                    if selected and selected.name in bpy.context.view_layer.objects:
                        selected.select_set(True)
                if previous_active and previous_active.name in bpy.context.view_layer.objects:
                    bpy.context.view_layer.objects.active = previous_active
            except Exception:
                pass
            try:
                obj.hide_viewport = previous_hide_viewport
            except Exception:
                pass


def move_lighting_and_head_driver_to_lights(main_obj=None):
    lights_coll = bpy.data.collections.get("lights")
    if not lights_coll:
        lights_coll = bpy.data.collections.new("lights")
        bpy.context.scene.collection.children.link(lights_coll)

    def get_all_children(obj):
        children = []
        for child in obj.children:
            children.append(child)
            children.extend(get_all_children(child))
        return children

    target_objs = set()
    if main_obj:
        target_objs.add(main_obj)
        for child in get_all_children(main_obj):
            target_objs.add(child)

    target_names = [
        "head direction", "head driver", "head origin",
        "lighting panel", "lightpanelselectorwgt", "lightpanelwgtplane"
    ]

    for obj in bpy.data.objects:
        o_lower = obj.name.lower()
        if "light direction" in o_lower:
            continue
        for t_name in target_names:
            if t_name in o_lower:
                target_objs.add(obj)
                for child in get_all_children(obj):
                    if "light direction" not in child.name.lower():
                        target_objs.add(child)
                break

    target_objs = {obj for obj in target_objs if "light direction" not in obj.name.lower()}

    for obj in target_objs:
        if obj.name not in lights_coll.objects:
            lights_coll.objects.link(obj)
        for coll in list(obj.users_collection):
            if coll != lights_coll:
                try:
                    coll.objects.unlink(obj)
                except Exception:
                    pass


register, unregister = bpy.utils.register_classes_factory([
    GI_OT_SetUpHeadDriver,
    ZZZ_OT_SetUpHeadDriver,
])
