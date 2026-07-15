# Author: michael-gh1

# Kudos to M4urlcl0 for bringing up adding the UV map (UV1) and 
# the armature bone settings when importing the FBX model

import bpy
import pathlib

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator
import os

from setup_wizard.domain.game_types import GameType
from setup_wizard.import_order import NextStepInvoker, cache_using_cache_key
from setup_wizard.import_order import get_cache, CHARACTER_MODEL_FOLDER_FILE_PATH
from setup_wizard.setup_wizard_operator_base_classes import BasicSetupUIOperator, CustomOperatorProperties
from setup_wizard.utils import material_utils


SHADER_COLOR_ATTRIBUTE_NAME = 'Col'


class GI_OT_SetUpCharacter(Operator, BasicSetupUIOperator):
    '''Sets Up Character'''
    bl_idname = 'genshin.set_up_character'
    bl_label = 'Genshin: Set Up Character (UI)'


class HSR_OT_SetUpCharacter(Operator, BasicSetupUIOperator):
    '''Sets Up Character'''
    bl_idname = 'honkai_star_rail.set_up_character'
    bl_label = 'Honkai Star Rail: Set Up Character (UI)'


class ZZZ_OT_SetUpCharacter(Operator, BasicSetupUIOperator):
    '''Sets Up Character'''
    bl_idname = 'zenless_zone_zero.set_up_character'
    bl_label = 'Zenless Zone Zero: Set Up Character (UI)'


class GI_OT_GenshinImportModel(Operator, ImportHelper, CustomOperatorProperties):
    """Select the folder with the desired model to import"""
    bl_idname = "genshin.import_model"  # important since its how we chain file dialogs
    bl_label = "Select Character Folder"

    # ImportHelper mixin class uses this
    filename_ext = "*.*"

    import_path: StringProperty(
        name="Path",
        description="Path to the folder of the Model",
        default="",
        subtype='DIR_PATH'
    )

    filter_glob: StringProperty(
        default="*.*",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )



    def execute(self, context):
        is_character_model_file = not os.path.isdir(self.filepath) and self.filepath
        character_model_directory = os.path.dirname(self.filepath) or self.file_directory
        character_model_file_path_or_directory = self.filepath if is_character_model_file else \
            (self.file_directory or character_model_directory)

        if not character_model_file_path_or_directory:
            bpy.ops.genshin.import_model(
                'INVOKE_DEFAULT',
                next_step_idx=self.next_step_idx, 
                file_directory=self.file_directory,
                invoker_type=self.invoker_type,
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
                )
            return {'FINISHED'}

        existing_materials = bpy.data.materials.values()  # used to track materials before and after importing character model
        try:
            self.import_character_model(character_model_file_path_or_directory, is_character_model_file)
            self.reset_pose_location_and_rotation()
            self.rename_mesh_color_attribute_name(SHADER_COLOR_ATTRIBUTE_NAME)  # Blender 3.4 changed default name to 'Attribute', revert it

            if context.window_manager.cache_enabled and character_model_directory:
                cache_using_cache_key(get_cache(), CHARACTER_MODEL_FOLDER_FILE_PATH, character_model_directory)

            # Add fake user to all materials that were added when importing character model (to prevent unused materials from being cleaned up)
            materials_imported_from_character_model = [material for material in bpy.data.materials.values() if material not in existing_materials]
            material_utils.add_fake_user_to_materials(materials_imported_from_character_model)

            NextStepInvoker().invoke(
                self.next_step_idx, 
                self.invoker_type, 
                file_path_to_cache=character_model_directory,
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
            )
        finally:
            super().clear_custom_properties()
        return {'FINISHED'}

    def import_character_model(self, character_model_file_path_or_directory, is_character_model_file):
        character_model_file_path = character_model_file_path_or_directory if is_character_model_file else \
            self.__find_fbx_file(character_model_file_path_or_directory)

        # Ensure clean context for import (no active/selected objects to interfere)
        try:
            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = None
        except Exception as e:
            self.report({'WARNING'}, f"Failed to clear selection context: {e}")

        # Keep track of existing objects to see if anything gets imported even if an exception is raised
        existing_objects = set(bpy.data.objects.keys())

        if self.game_type == GameType.ZENLESS_ZONE_ZERO.name:
            try:
                bpy.ops.import_scene.better_fbx(filepath=character_model_file_path)
                self.report({'INFO'}, 'Imported character model using Better FBX Importer')
                return
            except AttributeError:
                pass
            except Exception as e:
                pass

        # Fallback sequence for standard FBX importer
        fallbacks = [
            # 1. Recommended settings
            {"force_connect_children": True, "automatic_bone_orientation": True},
            # 2. Plain import (uses last used UI settings or defaults)
            {},
            # 3. No automatic bone orientation / connect children
            {"force_connect_children": False, "automatic_bone_orientation": False},
            # 4. Disable animations (very common cause of KeyError in rig mapping)
            {"force_connect_children": False, "automatic_bone_orientation": False, "use_anim": False},
            # 5. Ignore leaf bones
            {"force_connect_children": False, "automatic_bone_orientation": False, "ignore_leaf_bones": True},
        ]

        import_success = False
        last_error = None

        for i, settings in enumerate(fallbacks):
            try:
                bpy.ops.import_scene.fbx(filepath=character_model_file_path, **settings)
                import_success = True
                self.report({'INFO'}, f"Imported character model successfully on attempt {i+1}")
                break
            except Exception as e:
                last_error = e
                # Check if objects were successfully imported to the scene despite the importer error
                new_objects = [bpy.data.objects[name] for name in bpy.data.objects.keys() if name not in existing_objects]
                has_imported_assets = any(ob.type in ['ARMATURE', 'MESH'] for ob in new_objects)
                
                if has_imported_assets:
                    self.report({'WARNING'}, f"FBX importer reported an error ({e}) on attempt {i+1}, but the model was successfully loaded. Continuing...")
                    import_success = True
                    break
                else:
                    self.report({'WARNING'}, f"FBX import attempt {i+1} failed: {e}")

        if not import_success:
            error_message = (
                "El importador FBX por defecto de Blender no pudo cargar este modelo debido a un error de jerarquía (KeyError: Bone_Root).\n"
                "Para solucionar esto, puedes:\n"
                "1. Instalar el addon comercial 'Better FBX Importer' en Blender.\n"
                "2. O bien, abrir y volver a exportar el FBX usando una herramienta gratuita como 'Noesis' para limpiar la jerarquía."
            )
            self.report({'ERROR'}, error_message)
            raise RuntimeError(error_message)

        if self.game_type == GameType.ZENLESS_ZONE_ZERO.name:
            obj = None
            for ob in bpy.data.objects:
                if ob.type == 'ARMATURE' and ("avatar" in ob.name.lower() or "npc" in ob.name.lower()):
                    obj = ob
                    break
            if not obj:
                armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
                if armatures:
                    obj = armatures[0]
            if not obj:
                obj = bpy.data.objects.get('Armature')

            if obj:
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                
                # Standard FBX importer imports ZZZ models lying down (0,0,0 rotation).
                # Rotate 90 degrees in X to make it stand upright.
                import math
                obj.rotation_euler[0] = math.radians(90)
                
                # Select children to apply transform to mesh objects as well
                for child in obj.children:
                    child.select_set(True)
                    
                bpy.context.view_layer.objects.active = obj
                try:
                    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
                except Exception as e:
                    print("Failed to apply rotation/scale transforms:", e)

                try:
                    for mesh_obj in bpy.data.objects:
                        if mesh_obj.type == 'MESH' and ("eyebrow" in mesh_obj.name.lower() or "brow" in mesh_obj.name.lower()):
                            mesh_obj.parent = obj
                            mesh_obj.parent_type = 'BONE'
                            mesh_obj.parent_bone = "Bone_Root"
                except:
                    pass

                if obj.parent and obj.parent.type == 'EMPTY' and obj.parent.name == obj.name:
                    empty_parent = obj.parent
                    matrix_world = obj.matrix_world.copy()
                    obj.parent = None
                    obj.matrix_world = matrix_world
                    bpy.data.objects.remove(empty_parent)

                for mesh_obj in bpy.data.objects:
                    if mesh_obj.type == 'MESH' and ("hairshadow" in mesh_obj.name.lower() or "fx" in mesh_obj.name.lower()):
                        mesh_obj.hide_viewport = True
                        mesh_obj.hide_render = True

                self.fix_zzz_eye_shadow()

        for object in bpy.data.objects:
            if object.type == 'MESH' and not object.data.uv_layers.get('UV1'):
                object.data.uv_layers.new(name='UV1')
        # Quick-fix, just want to shove this in here for now...
        # Hide EffectMesh (gets deleted later on) and EyeStar
        for object in bpy.data.objects:
            if 'EffectMesh' in object.name or 'EyeStar' in object.name:
                try:
                    bpy.data.objects[object.name].hide_set(True)
                except RuntimeError:
                    # Object is not in the active View Layer, use hide_viewport instead
                    bpy.data.objects[object.name].hide_viewport = True
                bpy.data.objects[object.name].hide_render = True

    def fix_zzz_eye_shadow(self):
        faceobj = None
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and "face" in obj.name.lower():
                faceobj = obj
                break
        if faceobj:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            faceobj.select_set(True)
            bpy.context.view_layer.objects.active = faceobj
            try:
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='DESELECT')
                if 'Eye Transparent' in faceobj.vertex_groups:
                    faceobj.vertex_groups.active = faceobj.vertex_groups['Eye Transparent']
                    bpy.ops.object.vertex_group_select()
                    for group in faceobj.vertex_groups:
                        if "highlight" in group.name.lower():
                            faceobj.vertex_groups.active = group
                            bpy.ops.object.vertex_group_deselect()
                    bpy.ops.mesh.separate(type='SELECTED')
                bpy.ops.object.mode_set(mode='OBJECT')
                
                eye_obj = None
                for ob in bpy.context.selected_objects:
                    if ob != faceobj and ob.type == 'MESH':
                        eye_obj = ob
                        break
                if eye_obj:
                    eye_obj.name = "EyeTransparent"
            except Exception as e:
                print("fixeyeshadow error:", e)
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                except:
                    pass

    def reset_pose_location_and_rotation(self):
        try:
            armature = [object for object in bpy.data.objects if object.type == 'ARMATURE'][0]  # expecting 1 armature
        except IndexError as err:
            self.report(
                {'ERROR'}, 
                'Attempted to import model, but no armature found after import. Likely failed to import from FBX file.\n'
                "- Try renaming and removing any special characters (like star symbols) from any folders in the filepath"
            )
            raise err
        bpy.context.view_layer.objects.active = armature

        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.loc_clear()
        bpy.ops.pose.rot_clear()
        bpy.ops.object.mode_set(mode='OBJECT')

    '''
        NOTE: This will rename the Color Attributes for ALL meshes
        Currently expecting character setup to be performed in a fresh (new) file
    '''
    def rename_mesh_color_attribute_name(self, name):
        meshes = [mesh for mesh_name, mesh in bpy.data.meshes.items()]

        for mesh in meshes:
            if len(mesh.color_attributes) == 1:
                mesh.color_attributes[0].name = name  # PGR: Named "VertexColors" and may not be the active color
            else:
                if mesh.color_attributes.active_color:
                    mesh.color_attributes.active_color.name = name

    def __find_fbx_file(self, directory):
        for root, folder, files in os.walk(directory):
            for file_name in files:
                if '.fbx' in pathlib.Path(file_name).suffix:
                    return os.path.join(root, file_name)


'''
    This Operator should be executed AFTER importing the character model and 
    BEFORE importing Genshin materials.
    That way there is no chance of deleting empties used by Festivity's shaders.
'''
class GI_OT_DeleteEmpties(Operator, CustomOperatorProperties):
    '''Deletes Empties (except Head Driver's empties)'''
    bl_idname = 'genshin.delete_empties'
    bl_label = "Genshin: Delete empties (except Head Driver's empties)"

    def execute(self, context):
        scene = bpy.context.scene
        empties_to_not_delete = [
            'Head Forward',
            'Head Up',
            'Light Direction',
            'Main Light Direction',
            'Face Light Direction',
            'Head Driver',
            'Head Origin'
        ]
        for object in scene.objects:
            if object.type == 'EMPTY':
                should_delete = True
                for name_to_keep in empties_to_not_delete:
                    if object.name.startswith(name_to_keep):
                        should_delete = False
                        break
                if should_delete:
                    # Unparent any children of this empty, keeping their world transforms
                    for child in object.children:
                        matrix_world = child.matrix_world.copy()
                        child.parent = None
                        child.matrix_world = matrix_world
                    bpy.data.objects.remove(object)

        self.report({'INFO'}, 'Deleted Empties')
        if self.next_step_idx:
            NextStepInvoker().invoke(
                self.next_step_idx, 
                self.invoker_type, 
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
            )
        return {'FINISHED'}


register, unregister = bpy.utils.register_classes_factory([
    GI_OT_GenshinImportModel,
    GI_OT_DeleteEmpties,
    GI_OT_SetUpCharacter,
    HSR_OT_SetUpCharacter,
    ZZZ_OT_SetUpCharacter,
])
