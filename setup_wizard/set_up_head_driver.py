# Author: michael-gh1

import bpy
from bpy.types import Operator

from setup_wizard.import_order import NextStepInvoker
from setup_wizard.setup_wizard_operator_base_classes import CustomOperatorProperties

HEAD_DRIVER_OBJECT_NAME = 'Head Driver'
HEAD_ORIGIN_OBJECT_NAME = 'Head Origin'


class GI_OT_SetUpHeadDriver(Operator, CustomOperatorProperties):
    '''Sets up Head Driver'''
    bl_idname = 'genshin.setup_head_driver'
    bl_label = 'Genshin: Setup Head Driver'

    def execute(self, context):
        # Try to find the correct armature
        armatures = [obj for obj in bpy.context.selected_objects if obj.type == 'ARMATURE']
        if not armatures:
            armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
            
        if not armatures:
            self.report({'ERROR'}, "No armature found")
            return {'CANCELLED'}
            
        armature = armatures[0]
        char_name = armature.name.replace("Rig", "") if "Rig" in armature.name else armature.name

        head_driver_object = bpy.data.objects.get(f"{HEAD_DRIVER_OBJECT_NAME}_{char_name}") or \
                             bpy.data.objects.get(f"{HEAD_ORIGIN_OBJECT_NAME}_{char_name}") or \
                             bpy.data.objects.get(HEAD_DRIVER_OBJECT_NAME) or \
                             bpy.data.objects.get(HEAD_ORIGIN_OBJECT_NAME)

        if not head_driver_object:
            self.report({'ERROR'}, "Head Driver not found")
            return {'CANCELLED'}
            
        child_of_constraint = head_driver_object.constraints[0]  # expecting 1 constraint head driver

        armature_bones = armature.data.bones
        head_bone_names = [bone_name for bone_name in armature_bones.keys() if 'Head' in bone_name]
        if head_bone_names:
            head_bone_name = head_bone_names[0]  # expecting 1 Head bone
            self.set_contraint_target_and_bone(child_of_constraint, armature, head_bone_name)
            self.set_inverse(head_driver_object)

        if self.next_step_idx:
            NextStepInvoker().invoke(
                self.next_step_idx, 
                self.invoker_type, 
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
            )
        return {'FINISHED'}

    def set_contraint_target_and_bone(self, constraint, armature, bone_name):
        constraint.target = armature
        constraint.subtarget = bone_name

    def set_inverse(self, object):
        bpy.context.view_layer.objects.active = object
        bpy.ops.constraint.childof_set_inverse(constraint="Child Of", owner='OBJECT')


register, unregister = bpy.utils.register_classes_factory(GI_OT_SetUpHeadDriver)
