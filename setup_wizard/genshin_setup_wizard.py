# Author: michael-gh1

import os
import bpy
from bpy.props import StringProperty
from bpy.types import Operator
from setup_wizard.domain.game_types import GameType
from setup_wizard.import_order import NextStepInvoker

from setup_wizard.setup_wizard_operator_base_classes import BasicSetupUIOperator


class GI_OT_GenshinSetupWizardUI(Operator, BasicSetupUIOperator):
    '''Runs through entire setup process'''
    bl_idname = 'genshin.setup_wizard_ui'
    bl_label = 'Genshin: Setup Wizard (UI)'

    def execute(self, context):
        next_step_index = 0

        NextStepInvoker().invoke(
            next_step_index,
            'invoke_next_step_ui', 
            high_level_step_name=self.bl_idname if bpy.app.version >= (3,3,0) >= (3,3,0) \
                else self.bl_idname + '_no_outlines',
            game_type=self.game_type,
        )
        return {'FINISHED'}


class HSR_OT_HonkaiStarRailSetupWizardUI(Operator, BasicSetupUIOperator):
    '''Runs through entire setup process'''
    bl_idname = 'honkai_star_rail.setup_wizard_ui'
    bl_label = 'Honkai Star Rail: Setup Wizard (UI)'

    def execute(self, context):
        next_step_index = 0

        NextStepInvoker().invoke(
            next_step_index,
            'invoke_next_step_ui', 
            high_level_step_name=self.bl_idname if bpy.app.version >= (3,3,0) >= (3,3,0) \
                else self.bl_idname + '_no_outlines',
            game_type=self.game_type,
        )
        return {'FINISHED'}


class PGR_OT_SetupWizardUI(Operator, BasicSetupUIOperator):
    '''Runs through entire setup process'''
    bl_idname = 'punishing_gray_raven.setup_wizard_ui'
    bl_label = 'Punishing Gray Raven: Setup Wizard (UI)'

    def execute(self, context):
        next_step_index = 0

        NextStepInvoker().invoke(
            next_step_index,
            'invoke_next_step_ui', 
            high_level_step_name=self.bl_idname if bpy.app.version >= (3,3,0) >= (3,3,0) \
                else self.bl_idname + '_no_outlines',
            game_type=self.game_type,
        )
        return {'FINISHED'}


class HI3_OT_SetupWizardUI(Operator, BasicSetupUIOperator):
    '''Runs through entire setup process'''
    bl_idname = 'honkai_impact_3rd.setup_wizard_ui'
    bl_label = 'Honkai Impact 3rd: Setup Wizard (UI)'

    def execute(self, context):
        next_step_index = 0

        NextStepInvoker().invoke(
            next_step_index,
            'invoke_next_step_ui', 
            high_level_step_name=self.bl_idname if bpy.app.version >= (3,3,0) >= (3,3,0) \
                else self.bl_idname + '_no_outlines',
            game_type=self.game_type,
        )
        return {'FINISHED'}


class HNA_OT_SetupWizardUI(Operator, BasicSetupUIOperator):
    '''Runs through entire setup process'''
    bl_idname = 'honkai_nexus_anima.setup_wizard_ui'
    bl_label = 'Honkai Nexus Anima: Setup Wizard (UI)'

    def execute(self, context):
        next_step_index = 0

        NextStepInvoker().invoke(
            next_step_index,
            'invoke_next_step_ui', 
            high_level_step_name=self.bl_idname if bpy.app.version >= (3,3,0) >= (3,3,0) \
                else self.bl_idname + '_no_outlines',
            game_type=self.game_type,
        )
        return {'FINISHED'}



class ZZZ_OT_SetupWizardUI(Operator, BasicSetupUIOperator):
    '''Runs through entire setup process'''
    bl_idname = 'zenless_zone_zero.setup_wizard_ui'
    bl_label = 'Zenless Zone Zero: Setup Wizard (UI)'

    def execute(self, context):
        next_step_index = 0

        NextStepInvoker().invoke(
            next_step_index,
            'invoke_next_step_ui', 
            high_level_step_name=self.bl_idname if bpy.app.version >= (3,3,0) \
                else self.bl_idname + '_no_outlines',
            game_type=self.game_type,
        )
        return {'FINISHED'}


class NTE_OT_SetupWizardUI(Operator, BasicSetupUIOperator):
    '''Runs through entire setup process'''
    bl_idname = 'neverness_to_everness.setup_wizard_ui'
    bl_label = 'Neverness to Everness: Setup Wizard (UI)'

    def execute(self, context):
        next_step_index = 0

        NextStepInvoker().invoke(
            next_step_index,
            'invoke_next_step_ui', 
            high_level_step_name=self.bl_idname if bpy.app.version >= (3,3,0) \
                else self.bl_idname + '_no_outlines',
            game_type=self.game_type,
        )
        return {'FINISHED'}


class WW_OT_WutheringWavesSetupWizardUI(Operator, BasicSetupUIOperator):
    '''Runs through entire setup process for Wuthering Waves'''
    bl_idname = 'wuthering_waves.setup_wizard_ui'
    bl_label = 'Wuthering Waves: Setup Wizard (UI)'

    def execute(self, context):
        next_step_index = 0

        NextStepInvoker().invoke(
            next_step_index,
            'invoke_next_step_ui', 
            high_level_step_name=self.bl_idname if bpy.app.version >= (3,3,0) \
                else self.bl_idname + '_no_outlines',
            game_type=self.game_type,
        )
        return {'FINISHED'}


class AKE_OT_ArknightsEndfieldSetupWizardUI(Operator, BasicSetupUIOperator):
    '''Runs through entire setup process for Arknights: Endfield'''
    bl_idname = 'arknights_endfield.setup_wizard_ui'
    bl_label = 'Arknights Endfield: Setup Wizard (UI)'

    def execute(self, context):
        next_step_index = 0

        NextStepInvoker().invoke(
            next_step_index,
            'invoke_next_step_ui', 
            high_level_step_name=self.bl_idname if bpy.app.version >= (3,3,0) \
                else self.bl_idname + '_no_outlines',
            game_type=self.game_type,
        )
        return {'FINISHED'}



class GI_OT_GenshinSetupWizard(Operator):
    """Setup Wizard Process"""
    bl_idname = "genshin.setup_wizard"
    bl_label = "Genshin: Setup Wizard - Select Festivity's Shaders Folder"

    # ImportHelper mixin class uses this
    filename_ext = "*.*"
    
    import_path: StringProperty(
        name = "Path",
        description = "Path to the folder containing the files to import",
        default = "",
        subtype = 'DIR_PATH'
        )

    filter_glob: StringProperty(
        default="*.*",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        invoke_next_step = setup_dependencies()
        NextStepInvoker().invoke(
            1,
            'invoke_next_step'
        )

        return {'FINISHED'}


class CSW_OT_DependencyInstallNotice(Operator):
    bl_idname = 'setup_wizard.dependency_install_notice'
    bl_label = 'Dependencies Installed'
    bl_options = {'INTERNAL'}

    addons: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        self.report({'INFO'}, f'Se instalaron los siguientes addons: {self.addons}. Quedan desactivados hasta que se necesiten.')
        return {'FINISHED'}


def register():
    if not hasattr(bpy.types, 'CSW_OT_DependencyInstallNotice'):
        bpy.utils.register_class(CSW_OT_DependencyInstallNotice)
    if not hasattr(bpy.types, "GI_OT_GenshinSetupWizard"):
        try:
            bpy.utils.register_class(GI_OT_GenshinSetupWizard)
        except ValueError:
            pass
    if not bpy.app.timers.is_registered(on_register):
        try:
            bpy.app.timers.register(on_register, first_interval=1)
        except Exception:
            pass


def unregister():
    if hasattr(bpy.types, 'CSW_OT_DependencyInstallNotice'):
        bpy.utils.unregister_class(bpy.types.CSW_OT_DependencyInstallNotice)
    if hasattr(bpy.types, "GI_OT_GenshinSetupWizard"):
        try:
            bpy.utils.unregister_class(GI_OT_GenshinSetupWizard)
        except Exception:
            pass


def on_register():
    installed = []
    try:
        # Blender 5+ uses Retarget; Blender 4 keeps the bundled ExpyKit.
        addons_to_check = {
            'rigify': ('rigify', ''),
            ('retarget' if bpy.app.version >= (5, 0, 0) else 'expy'): (
                ('retarget', 'retarget.zip') if bpy.app.version >= (5, 0, 0)
                else ('Expy-Kit-main', 'Expy-Kit-v052.zip')
            ),
            'ueformat': ('io_scene_ueformat', 'ueformat-blender.zip'),
        }

        for search_key, (default_module, filename) in addons_to_check.items():
            # Bundled UEFormat supplies fallbacks for Blender 4.1's missing
            # file-drop helpers; their absence must not disable model import.
            if is_addon_enabled_or_installed(search_key):
                if search_key == 'rigify':
                    import addon_utils
                    from setup_wizard.utils.optional_addons import find_addon
                    addon_utils.enable(find_addon('rigify'), default_set=True)
                continue
            if filename:
                name = install_addon(default_module, filename, search_key)
                if name:
                    installed.append(name)
    except Exception as err:
        print(f'Unexpected error when trying to enable/install addons: {err}')
    finally:
        if installed:
            bpy.ops.setup_wizard.dependency_install_notice(addons=', '.join(installed))


def is_addon_enabled_or_installed(search_key):
    """Availability check only; optional dependencies may remain disabled."""
    from setup_wizard.utils.optional_addons import addon_installed
    return addon_installed(search_key)


def install_addon(addon, filename, search_key=""):
    addon_path = os.path.join(os.path.dirname(__file__), 'dependencies', filename)
    if os.path.exists(addon_path):
        print(f'Installing addon: {addon_path}')
        result = bpy.ops.preferences.addon_install(filepath=addon_path, overwrite=False)
        import addon_utils
        addon_utils.modules(refresh=True)
        from setup_wizard.utils.optional_addons import find_addon
        module = find_addon(search_key or addon)
        if result != {'FINISHED'} or module is None:
            raise RuntimeError(f'Could not install dependency: {addon}')
        # A newly installed dependency must never stay enabled by default.
        addon_utils.disable(module, default_set=True)
        metadata = next((mod for mod in addon_utils.modules(refresh=False)
                         if mod.__name__ == module), None)
        name = addon_utils.module_bl_info(metadata).get('name', addon) if metadata else addon
        print(f'Installed optional dependency: {name} (disabled by default)')
        return name
    else:  #  is not standalone version of Setup Wizard
        print(f'Addon file does not exist at {addon_path}. Unable to install {addon}.')


# Legacy import system before this became an Addon. Refactoring necessary.
def setup_dependencies():
    # Really ugly in my opinion, but this let's us reload modules when we make changes to them without
    # having to restart Blender.
    import importlib
    import setup_wizard.import_order
    import setup_wizard.genshin_import_character_model
    import setup_wizard.genshin_import_material_data
    import setup_wizard.genshin_import_materials
    import setup_wizard.genshin_set_up_geometry_nodes
    import setup_wizard.genshin_import_outline_lightmaps
    import setup_wizard.genshin_import_outlines
    import setup_wizard.genshin_import_textures
    import setup_wizard.genshin_replace_default_materials
    import setup_wizard.misc_final_steps
    import setup_wizard.set_up_head_driver
    import setup_wizard.fix_mouth_outlines
    import setup_wizard.misc_operations
    import setup_wizard.join_meshes_on_armature.join_meshes_operator
    import setup_wizard.character_rig_setup.character_rigger_operator
    import setup_wizard.character_rig_setup.rootshape_filepath_setter_operator
    import setup_wizard.optimization.emissive_optimizer
    import setup_wizard.genshin_compositing_node_setup
    import setup_wizard.change_bpy_context
    import setup_wizard.mesh_import_setup.chibi_face_setup

    importlib.reload(setup_wizard.import_order)
    importlib.reload(setup_wizard.genshin_import_character_model)
    importlib.reload(setup_wizard.genshin_import_material_data)
    importlib.reload(setup_wizard.genshin_import_materials)
    importlib.reload(setup_wizard.genshin_set_up_geometry_nodes)
    importlib.reload(setup_wizard.genshin_import_outline_lightmaps)
    importlib.reload(setup_wizard.genshin_import_outlines)
    importlib.reload(setup_wizard.genshin_import_textures)
    importlib.reload(setup_wizard.genshin_replace_default_materials)
    importlib.reload(setup_wizard.misc_final_steps)
    importlib.reload(setup_wizard.set_up_head_driver)
    importlib.reload(setup_wizard.fix_mouth_outlines)
    importlib.reload(setup_wizard.misc_operations)
    importlib.reload(setup_wizard.join_meshes_on_armature.join_meshes_operator)
    importlib.reload(setup_wizard.character_rig_setup.character_rigger_operator)
    importlib.reload(setup_wizard.character_rig_setup.rootshape_filepath_setter_operator)
    importlib.reload(setup_wizard.optimization.emissive_optimizer)
    importlib.reload(setup_wizard.genshin_compositing_node_setup)
    importlib.reload(setup_wizard.change_bpy_context)
    importlib.reload(setup_wizard.mesh_import_setup.chibi_face_setup)

    for class_to_register in [
        setup_wizard.genshin_import_character_model.GI_OT_GenshinImportModel,
        setup_wizard.genshin_import_character_model.GI_OT_DeleteEmpties,
        setup_wizard.genshin_import_material_data.GI_OT_GenshinImportMaterialData,
        setup_wizard.genshin_import_materials.GI_OT_GenshinImportMaterials,
        setup_wizard.genshin_set_up_geometry_nodes.GI_OT_SetUpGeometryNodes,
        setup_wizard.genshin_import_outline_lightmaps.GI_OT_GenshinImportOutlineLightmaps,
        setup_wizard.genshin_import_outlines.GI_OT_GenshinImportOutlines,
        setup_wizard.genshin_import_textures.GI_OT_GenshinImportTextures,
        setup_wizard.genshin_replace_default_materials.GI_OT_GenshinReplaceDefaultMaterials,
        setup_wizard.misc_final_steps.GI_OT_FixTransformations,
        setup_wizard.fix_mouth_outlines.GI_OT_FixMouthOutlines,
        setup_wizard.set_up_head_driver.GI_OT_SetUpHeadDriver,
        setup_wizard.set_up_head_driver.ZZZ_OT_SetUpHeadDriver,
        setup_wizard.set_up_head_driver.WW_OT_SetUpHeadDriver,
        setup_wizard.set_up_head_driver.AKE_OT_SetUpHeadDriver,
        setup_wizard.misc_operations.GI_OT_SetColorManagementToStandard,
        setup_wizard.misc_operations.HYV_OT_SetUpScreenSpaceReflections,
        setup_wizard.misc_operations.HYV_OT_VertexPaintFaceSeeThroughEffect,
        setup_wizard.misc_operations.GI_OT_DeleteSpecificObjects,
        setup_wizard.misc_operations.GI_OT_SetUpArmTwistBoneConstraints,
        setup_wizard.misc_operations.GI_OT_RenameShaderMaterials,
        setup_wizard.misc_operations.ZZZ_OT_RenameCollectionAndRig,
        setup_wizard.misc_operations.ZZZ_OT_MoveLightingPanelToCharacterCollection,
        setup_wizard.misc_operations.PGR_OT_PaintVertexColors,
        setup_wizard.misc_operations.PGR_OT_PaintFaceShadowTexture,
        setup_wizard.misc_operations.PGR_OT_PaintVertexEraseFaceAlpha,

        setup_wizard.join_meshes_on_armature.join_meshes_operator.GI_OT_JoinMeshesOnArmature,
        setup_wizard.character_rig_setup.character_rigger_operator.HOYOVERSE_OT_rig_character,
        setup_wizard.character_rig_setup.character_rigger_operator.HOYOVERSE_OT_apply_hair_clothes_physics,
        setup_wizard.character_rig_setup.character_rigger_operator.HOYOVERSE_OT_remove_hair_clothes_physics,
        setup_wizard.character_rig_setup.character_rigger_operator.HOYOVERSE_OT_apply_hair_dress_physics,
        setup_wizard.character_rig_setup.character_rigger_operator.HOYOVERSE_OT_toggle_weapon_hand,
        setup_wizard.character_rig_setup.rootshape_filepath_setter_operator.GI_OT_RootShape_FilePath_Setter_Operator,
        setup_wizard.optimization.emissive_optimizer.GI_OT_Emissive_Optimizer,
        setup_wizard.genshin_compositing_node_setup.GI_OT_CompositingNodeSetup,
        setup_wizard.genshin_compositing_node_setup.PGR_OT_SetUpCompositor,
        setup_wizard.genshin_compositing_node_setup.HYV_OT_HoyoversePostProcessingDefaultSettings,
        setup_wizard.change_bpy_context.GI_OT_Change_BPY_Context,
        setup_wizard.mesh_import_setup.chibi_face_setup.PGR_OT_SetUpChibiFace,
        setup_wizard.mesh_import_setup.chibi_face_setup.PGR_OT_ImportChibiFaceTexture,
    ]:
        try:
            bpy.utils.unregister_class(class_to_register)
        except Exception:
            pass
        try:
            bpy.utils.register_class(class_to_register)
        except Exception:
            pass
    return setup_wizard.import_order.invoke_next_step


# Need to have run setup_dependencies in order to unregister, otherwise sys.path 
# will be missing the filepath to the scripts folder
def unregister():
    from setup_wizard.genshin_import_materials import GI_OT_GenshinImportMaterials
    from setup_wizard.genshin_import_character_model import GI_OT_GenshinImportModel, GI_OT_DeleteEmpties
    from setup_wizard.genshin_replace_default_materials import GI_OT_GenshinReplaceDefaultMaterials
    from setup_wizard.genshin_import_textures import GI_OT_GenshinImportTextures
    from setup_wizard.genshin_set_up_geometry_nodes import GI_OT_SetUpGeometryNodes
    from setup_wizard.genshin_import_outlines import GI_OT_GenshinImportOutlines
    from setup_wizard.genshin_import_outline_lightmaps import GI_OT_GenshinImportOutlineLightmaps
    from setup_wizard.genshin_import_material_data import GI_OT_GenshinImportMaterialData
    from setup_wizard.misc_final_steps import GI_OT_FixTransformations
    from setup_wizard.set_up_head_driver import GI_OT_SetUpHeadDriver, ZZZ_OT_SetUpHeadDriver, WW_OT_SetUpHeadDriver
    from setup_wizard.misc_operations import GI_OT_SetColorManagementToStandard, HYV_OT_SetUpScreenSpaceReflections, \
        HYV_OT_VertexPaintFaceSeeThroughEffect, GI_OT_DeleteSpecificObjects, GI_OT_SetUpArmTwistBoneConstraints, \
        GI_OT_RenameShaderMaterials, ZZZ_OT_RenameCollectionAndRig, ZZZ_OT_MoveLightingPanelToCharacterCollection, \
        PGR_OT_PaintVertexColors, PGR_OT_PaintFaceShadowTexture, PGR_OT_PaintVertexEraseFaceAlpha
    from setup_wizard.join_meshes_on_armature.join_meshes_operator import GI_OT_JoinMeshesOnArmature
    from setup_wizard.character_rig_setup.character_rigger_operator import (
        GI_OT_CharacterRiggerOperator,
        GI_OT_ApplyHairClothesPhysicsOperator,
        GI_OT_ApplyHairDressPhysicsOperator,
    )
    from setup_wizard.character_rig_setup.rootshape_filepath_setter_operator import GI_OT_RootShape_FilePath_Setter_Operator
    from setup_wizard.optimization.emissive_optimizer import GI_OT_Emissive_Optimizer
    from setup_wizard.genshin_compositing_node_setup import GI_OT_CompositingNodeSetup, \
        HYV_OT_HoyoversePostProcessingDefaultSettings, PGR_OT_SetUpCompositor
    from setup_wizard.change_bpy_context import GI_OT_Change_BPY_Context
    from setup_wizard.mesh_import_setup.chibi_face_setup import PGR_OT_SetUpChibiFace, PGR_OT_ImportChibiFaceTexture

    for class_to_unregister in [
        GI_OT_GenshinImportModel,
        GI_OT_DeleteEmpties,
        GI_OT_GenshinImportMaterials,
        GI_OT_GenshinReplaceDefaultMaterials,
        GI_OT_GenshinImportTextures,
        GI_OT_SetUpGeometryNodes,
        GI_OT_GenshinImportOutlines,
        GI_OT_GenshinImportOutlineLightmaps,
        GI_OT_GenshinImportMaterialData,
        GI_OT_FixTransformations,
        GI_OT_SetUpHeadDriver,
        ZZZ_OT_SetUpHeadDriver,
        WW_OT_SetUpHeadDriver,
        GI_OT_SetColorManagementToStandard,
        HYV_OT_SetUpScreenSpaceReflections,
        HYV_OT_VertexPaintFaceSeeThroughEffect,
        GI_OT_DeleteSpecificObjects,
        GI_OT_RenameShaderMaterials,
        GI_OT_SetUpArmTwistBoneConstraints,
        ZZZ_OT_RenameCollectionAndRig,
        ZZZ_OT_MoveLightingPanelToCharacterCollection,
        PGR_OT_PaintVertexColors,
        PGR_OT_PaintFaceShadowTexture,
        PGR_OT_PaintVertexEraseFaceAlpha,
        GI_OT_JoinMeshesOnArmature,
        setup_wizard.character_rig_setup.character_rigger_operator.HOYOVERSE_OT_rig_character,
        setup_wizard.character_rig_setup.character_rigger_operator.HOYOVERSE_OT_apply_hair_clothes_physics,
        setup_wizard.character_rig_setup.character_rigger_operator.HOYOVERSE_OT_apply_hair_dress_physics,
        setup_wizard.character_rig_setup.character_rigger_operator.HOYOVERSE_OT_toggle_weapon_hand,
        GI_OT_RootShape_FilePath_Setter_Operator,
        GI_OT_Emissive_Optimizer,
        GI_OT_CompositingNodeSetup,
        PGR_OT_SetUpCompositor,
        HYV_OT_HoyoversePostProcessingDefaultSettings,
        GI_OT_Change_BPY_Context,
        PGR_OT_SetUpChibiFace,
        PGR_OT_ImportChibiFaceTexture,
    ]:
        try:
            bpy.utils.unregister_class(class_to_unregister)
        except ValueError:
            pass  # expected if class is already registered


if __name__ == "__main__":
    register()
