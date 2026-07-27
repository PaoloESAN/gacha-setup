# Author: michael-gh1

import bpy

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator

from setup_wizard.domain.game_types import GameType
from setup_wizard.import_order import NextStepInvoker
from setup_wizard.character_rig_setup.rigify_character_service import RigifyCharacterService
from setup_wizard.setup_wizard_operator_base_classes import BasicSetupUIOperator, CustomOperatorProperties


class GI_OT_RigCharacter(Operator, BasicSetupUIOperator):
    '''Sets Up Rig for Character'''
    bl_idname = 'hoyoverse.set_up_character_rig'
    bl_label = 'HoYoverse: Set Up Character Rig (UI)'


class GI_OT_CharacterRiggerOperator(Operator, ImportHelper, CustomOperatorProperties):
    """Sets Up Rig for Character"""
    bl_idname = "hoyoverse.rig_character"  # important since its how we chain file dialogs
    bl_label = "Rigs Character"

    # ImportHelper mixin class uses this
    filename_ext = "*.*"

    # DEPRECATED, replaced by GI_OT_RootShape_FilePath_Setter_Operator 
    import_path: StringProperty(
        name="Path",
        description="Root_Shape .blend File",
        default="",
        subtype='DIR_PATH'
    )

    filter_glob: StringProperty(
        default="*.*",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    GAME_TYPES_FULL_SETUP_RIGGING_ENABLED = [
        GameType.GENSHIN_IMPACT.name,
        GameType.HONKAI_STAR_RAIL.name,
        GameType.ZENLESS_ZONE_ZERO.name,
        GameType.NEVERNESS_TO_EVERNESS.name,
    ]

    def execute(self, context):
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
        if not selected_armatures:
            selected_armatures = [obj for obj in context.scene.objects if obj.type == 'ARMATURE']

        if selected_armatures:
            arm_obj = selected_armatures[0]
            b_names = set(arm_obj.data.bones.keys())
            if 'Bip001-Pelvis' in b_names or 'Bip001-Head' in b_names or 'Bip001-Spine' in b_names:
                self.game_type = GameType.NEVERNESS_TO_EVERNESS.name

        is_advanced_setup = self.high_level_step_name != 'GENSHIN_OT_setup_wizard_ui' and \
            self.high_level_step_name != 'GENSHIN_OT_setup_wizard_ui_no_outlines' and \
            self.high_level_step_name != 'HONKAI_STAR_RAIL_OT_setup_wizard_ui' and \
            self.high_level_step_name != 'HONKAI_STAR_RAIL_OT_setup_wizard_ui_no_outlines' and \
            self.high_level_step_name != 'neverness_to_everness.setup_wizard_ui'
        rigging_enabled = is_advanced_setup or \
            (bpy.context.window_manager.setup_wizard_full_run_rigging_enabled and self.game_type in self.GAME_TYPES_FULL_SETUP_RIGGING_ENABLED)

        expy_kit_installed = bpy.context.preferences.addons.get('Expy-Kit-main')
        rigify_installed = bpy.context.preferences.addons.get('rigify')

        if not rigging_enabled:
            self.report(
                {'WARNING'},
                'Rigging skipped. Rigging not enabled on Run Entire Setup.'
            )
            self.invoke_next_step()
            return {'FINISHED'}
        if not expy_kit_installed or not rigify_installed:
            self.report(
                {'WARNING'},
                'Rigging skipped. ExpyKit and Rigify are required.\n'
                f'ExpyKit: {"Installed" if expy_kit_installed else "Missing"}\n'
                f'Rigify: {"Installed" if rigify_installed else "Missing"}'
            )
            self.invoke_next_step()
            return {'FINISHED'}

        try:
            rigify_character_service = RigifyCharacterService(self.game_type, self, context)
            rigify_character_service.rig_character()

            self.invoke_next_step()
        except Exception as ex:
            raise ex
        finally:
            super().clear_custom_properties()
        return {'FINISHED'}

    def invoke_next_step(self):
        if self.next_step_idx:
            NextStepInvoker().invoke(
                self.next_step_idx, 
                self.invoker_type, 
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
            )

class ZZZ_OT_FixBoneChains(Operator):
    '''Fix selected bone chains (tails) parenting and lengths'''
    bl_idname = 'zenless_zone_zero.fix_bone_chains'
    bl_label = 'ZZZ: Fix Selected Bone Chains (Tails)'
    bl_description = "Fix parenting and lengths for selected bone chains (e.g. tails)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Active object is not an Armature")
            return {'CANCELLED'}

        original_mode = obj.mode
        bpy.ops.object.mode_set(mode='EDIT')

        selected_bones = [bone.name for bone in context.selected_bones]
        if not selected_bones:
            self.report({'WARNING'}, "No bones selected")
            bpy.ops.object.mode_set(mode=original_mode)
            return {'CANCELLED'}

        sb = sorted(selected_bones)
        armature = obj.data
        eb = armature.edit_bones

        def attach(foot, toe):
            eb[foot].tail.x = eb[toe].head.x
            eb[foot].tail.y = eb[toe].head.y
            eb[foot].tail.z = eb[toe].head.z

        groups = {}
        for name in sb:
            key = name[:-2]
            groups.setdefault(key, []).append(name)

        for key, group_bones in groups.items():
            if len(group_bones) < 2:
                continue
            for b in range(1, len(group_bones) + 1):
                if b == len(group_bones):
                    if len(group_bones) >= 2:
                        eb[group_bones[b-1]].length = eb[group_bones[b-2]].length + 0.1
                else:
                    bone_name = group_bones[b]
                    parent_name = group_bones[b-1]
                    eb[bone_name].parent = eb[parent_name]
                    attach(parent_name, bone_name)

        bpy.ops.object.mode_set(mode=original_mode)
        self.report({'INFO'}, "Successfully fixed selected bone chains")
        return {'FINISHED'}


register, unregister = bpy.utils.register_classes_factory([
    GI_OT_CharacterRiggerOperator,
    ZZZ_OT_FixBoneChains,
])
