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
                bone_name
                for bone_name in armature_bones.keys()
                if "Head" in bone_name or bone_name == "DEF-spine.006"
            ]
            if head_bone_names:
                head_bone_name = head_bone_names[0]  # expecting 1 Head bone
                self.set_contraint_target_and_bone(
                    child_of_constraint, armature, head_bone_name
                )
                self.set_inverse(head_driver_object, child_of_constraint.name)
            else:
                self.report({"WARNING"}, "No head bone found for head-driver setup.")

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

    def _is_in_active_view_layer(self, obj):
        return obj.name in bpy.context.view_layer.objects

    def set_inverse(self, obj, constraint_name):
        # This can fail when the object exists in bpy.data but is excluded from current ViewLayer.
        if not self._is_in_active_view_layer(obj):
            self.report(
                {"WARNING"},
                f"'{obj.name}' is not in active ViewLayer. Skipping Child Of inverse.",
            )
            return

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


register, unregister = bpy.utils.register_classes_factory(GI_OT_SetUpHeadDriver)
