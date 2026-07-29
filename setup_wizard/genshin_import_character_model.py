# Author: michael-gh1

# Kudos to M4urlcl0 for bringing up adding the UV map (UV1) and
# the armature bone settings when importing the FBX model

import os
import pathlib

import bpy
from bpy.props import StringProperty
from bpy.types import Operator

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper

from setup_wizard.domain.game_types import GameType
from setup_wizard.import_order import (
    CHARACTER_MODEL_FOLDER_FILE_PATH,
    NEVERNESS_TO_EVERNESS_ROOT_FOLDER_FILE_PATH,
    NEVERNESS_TO_EVERNESS_SHADER_FILE_PATH,
    NextStepInvoker,
    cache_using_cache_key,
    get_cache,
    set_active_character_directory,
)
from setup_wizard.setup_wizard_operator_base_classes import (
    BasicSetupUIOperator,
    CustomOperatorProperties,
)
from setup_wizard.utils import material_utils

SHADER_COLOR_ATTRIBUTE_NAME = "Col"

# Session variable to track if character was imported via the automatic wizard flow in this session
IMPORTED_VIA_WIZARD = False


class GI_OT_SetUpCharacter(Operator, BasicSetupUIOperator):
    """Sets Up Character"""

    bl_idname = "genshin.set_up_character"
    bl_label = "Genshin: Set Up Character (UI)"


class HSR_OT_SetUpCharacter(Operator, BasicSetupUIOperator):
    """Sets Up Character"""

    bl_idname = "honkai_star_rail.set_up_character"
    bl_label = "Honkai Star Rail: Set Up Character (UI)"


class ZZZ_OT_SetUpCharacter(Operator, BasicSetupUIOperator):
    """Sets Up Character"""

    bl_idname = "zenless_zone_zero.set_up_character"
    bl_label = "Zenless Zone Zero: Set Up Character (UI)"


class NTE_OT_SetUpCharacter(Operator, ImportHelper, CustomOperatorProperties):
    """Sets Up Character for Neverness to Everness"""

    bl_idname = "neverness_to_everness.set_up_character"
    bl_label = "Select NTE Character Model (.uemodel)"

    filename_ext = ".uemodel"
    filter_glob: StringProperty(
        default="*.uemodel",
        options={'HIDDEN'},
        maxlen=255,
    )

    def execute(self, context):
        if not self.filepath:
            return {"CANCELLED"}

        folder = os.path.dirname(self.filepath) if os.path.isfile(self.filepath) else self.filepath
        if folder and os.path.isdir(folder):
            set_active_character_directory(folder)
            cache_using_cache_key(get_cache(True), CHARACTER_MODEL_FOLDER_FILE_PATH, folder)
            cache_using_cache_key(get_cache(True), NEVERNESS_TO_EVERNESS_ROOT_FOLDER_FILE_PATH, folder)
            cache_using_cache_key(get_cache(True), NEVERNESS_TO_EVERNESS_SHADER_FILE_PATH, folder)
            context.scene["setup_wizard_imported_model_dir"] = folder
            context.scene["setup_wizard_imported_uemodel_path"] = self.filepath
            print(f"[NTE SETUP] Cached character folder from uemodel selection: {folder}")

        if hasattr(bpy.ops, 'uf') and hasattr(bpy.ops.uf, 'import_uemodel'):
            filename = os.path.basename(self.filepath) if os.path.isfile(self.filepath) else ""
            imported_ok = False

            # Method 1: Pass directory + files collection + filepath (UEFormat ImportHelper standard)
            try:
                bpy.ops.uf.import_uemodel(
                    filepath=self.filepath,
                    directory=folder,
                    files=[{"name": filename}]
                )
                imported_ok = True
            except Exception as e1:
                print(f"[NTE SETUP] Method 1 uf.import_uemodel notice: {e1}")

            # Method 2: Pass filepath only
            if not imported_ok:
                try:
                    bpy.ops.uf.import_uemodel(filepath=self.filepath)
                    imported_ok = True
                except Exception as e2:
                    print(f"[NTE SETUP] Method 2 uf.import_uemodel notice: {e2}")

            # Method 3: Fallback execute
            if not imported_ok:
                try:
                    bpy.ops.uf.import_uemodel('EXEC_DEFAULT', filepath=self.filepath)
                except Exception as e3:
                    self.report({"WARNING"}, f"UEFormat import notice: {e3}")

            self.report({"INFO"}, f"Imported NTE character model: {filename}")
        else:
            self.report({"ERROR"}, "UEFormat add-on is not enabled or available.")
            return {"CANCELLED"}

        return {"FINISHED"}


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
        subtype="DIR_PATH",
    )

    filter_glob: StringProperty(
        default="*.*",
        options={"HIDDEN"},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        is_character_model_file = not os.path.isdir(self.filepath) and self.filepath
        character_model_directory = (
            os.path.dirname(self.filepath) or self.file_directory
        )
        character_model_file_path_or_directory = (
            self.filepath
            if is_character_model_file
            else (self.file_directory or character_model_directory)
        )

        if not character_model_file_path_or_directory:
            bpy.ops.genshin.import_model(
                "INVOKE_DEFAULT",
                next_step_idx=self.next_step_idx,
                file_directory=self.file_directory,
                invoker_type=self.invoker_type,
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
            )
            return {"FINISHED"}

        existing_materials = (
            bpy.data.materials.values()
        )  # used to track materials before and after importing character model
        try:
            self.import_character_model(
                character_model_file_path_or_directory, is_character_model_file
            )
            self.reset_pose_location_and_rotation()
            self.rename_mesh_color_attribute_name(
                SHADER_COLOR_ATTRIBUTE_NAME
            )  # Blender 3.4 changed default name to 'Attribute', revert it

            if character_model_directory:
                set_active_character_directory(character_model_directory)

            global IMPORTED_VIA_WIZARD
            IMPORTED_VIA_WIZARD = True

            # Add fake user to all materials that were added when importing character model (to prevent unused materials from being cleaned up)
            materials_imported_from_character_model = [
                material
                for material in bpy.data.materials.values()
                if material not in existing_materials
            ]
            material_utils.add_fake_user_to_materials(
                materials_imported_from_character_model
            )

            NextStepInvoker().invoke(
                self.next_step_idx,
                self.invoker_type,
                file_path_to_cache=character_model_directory,
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
            )
        finally:
            super().clear_custom_properties()
        return {"FINISHED"}

    def import_character_model(
        self, character_model_file_path_or_directory, is_character_model_file
    ):
        character_model_file_path = (
            character_model_file_path_or_directory
            if is_character_model_file
            else self.__find_fbx_file(character_model_file_path_or_directory)
        )

        # Persist the real FBX path for later steps (e.g. Finish Setup renaming)
        try:
            bpy.context.scene["setup_wizard_imported_fbx_path"] = (
                character_model_file_path
            )
            bpy.context.scene["setup_wizard_imported_model_dir"] = os.path.dirname(
                character_model_file_path
            )
        except Exception:
            pass

        # Ensure clean context for import (no active/selected objects to interfere)
        try:
            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")
            bpy.context.view_layer.objects.active = None
        except Exception as e:
            self.report({"WARNING"}, f"Failed to clear selection context: {e}")

        # Keep track of existing objects to see if anything gets imported even if an exception is raised
        existing_objects = set(bpy.data.objects.keys())

        if self.game_type == GameType.ZENLESS_ZONE_ZERO.name:
            better_fbx_success = False
            try:
                bpy.ops.import_scene.better_fbx(filepath=character_model_file_path)
                self.report(
                    {"INFO"}, "Imported character model using Better FBX Importer"
                )
                better_fbx_success = True
            except AttributeError:
                pass
            except Exception as e:
                pass

            if not better_fbx_success:
                try:
                    bpy.ops.import_scene.fbx(
                        filepath=character_model_file_path,
                        force_connect_children=True,
                        automatic_bone_orientation=True,
                    )
                except Exception as e:
                    # Clean up newly created objects
                    new_objects = [
                        bpy.data.objects[name]
                        for name in bpy.data.objects.keys()
                        if name not in existing_objects
                    ]
                    for ob in new_objects:
                        try:
                            bpy.data.objects.remove(ob)
                        except Exception:
                            pass

                    error_message = "Please reopen Blender and import the FBX manually."
                    self.report({"ERROR"}, error_message)
                    raise RuntimeError(error_message)

            obj = None
            for ob in bpy.data.objects:
                if ob.type == "ARMATURE" and (
                    "avatar" in ob.name.lower() or "npc" in ob.name.lower()
                ):
                    obj = ob
                    break
            if not obj:
                armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
                if armatures:
                    obj = armatures[0]
            if not obj:
                obj = bpy.data.objects.get("Armature")

            if obj:
                bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.select_all(action="DESELECT")
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
                    bpy.ops.object.transform_apply(
                        location=False, rotation=True, scale=True
                    )
                except Exception as e:
                    print("Failed to apply rotation/scale transforms:", e)

                try:
                    for mesh_obj in bpy.data.objects:
                        if mesh_obj.type == "MESH" and (
                            "eyebrow" in mesh_obj.name.lower()
                            or "brow" in mesh_obj.name.lower()
                        ):
                            mesh_obj.parent = obj
                            mesh_obj.parent_type = "BONE"
                            mesh_obj.parent_bone = "Bone_Root"
                except:
                    pass

                if (
                    obj.parent
                    and obj.parent.type == "EMPTY"
                    and obj.parent.name == obj.name
                ):
                    empty_parent = obj.parent
                    matrix_world = obj.matrix_world.copy()
                    obj.parent = None
                    obj.matrix_world = matrix_world
                    bpy.data.objects.remove(empty_parent)

                for mesh_obj in bpy.data.objects:
                    if mesh_obj.type == "MESH" and (
                        "hairshadow" in mesh_obj.name.lower()
                        or "fx" in mesh_obj.name.lower()
                    ):
                        mesh_obj.hide_viewport = True
                        mesh_obj.hide_render = True

                self.fix_zzz_eye_shadow()

            for object in bpy.data.objects:
                if object.type == "MESH" and not object.data.uv_layers.get("UV1"):
                    object.data.uv_layers.new(name="UV1")

            for object in bpy.data.objects:
                if "EffectMesh" in object.name or "EyeStar" in object.name:
                    try:
                        bpy.data.objects[object.name].hide_set(True)
                    except RuntimeError:
                        bpy.data.objects[object.name].hide_viewport = True
                    bpy.data.objects[object.name].hide_render = True

            return

        # Import using recommended settings
        try:
            bpy.ops.import_scene.fbx(
                filepath=character_model_file_path,
                force_connect_children=True,
                automatic_bone_orientation=True,
            )
        except Exception as e:
            # Clean up newly created objects
            new_objects = [
                bpy.data.objects[name]
                for name in bpy.data.objects.keys()
                if name not in existing_objects
            ]
            for ob in new_objects:
                try:
                    bpy.data.objects.remove(ob)
                except Exception:
                    pass

            error_message = "Please reopen Blender and import the FBX manually."
            self.report({"ERROR"}, error_message)
            raise RuntimeError(error_message)

        for object in bpy.data.objects:
            if object.type == "MESH" and not object.data.uv_layers.get("UV1"):
                object.data.uv_layers.new(name="UV1")
        # Quick-fix, just want to shove this in here for now...
        # Hide EffectMesh (gets deleted later on) and EyeStar
        for object in bpy.data.objects:
            if "EffectMesh" in object.name or "EyeStar" in object.name:
                try:
                    bpy.data.objects[object.name].hide_set(True)
                except RuntimeError:
                    # Object is not in the active View Layer, use hide_viewport instead
                    bpy.data.objects[object.name].hide_viewport = True
                bpy.data.objects[object.name].hide_render = True

    def fix_zzz_eye_shadow(self):
        faceobj = None
        for obj in bpy.data.objects:
            if obj.type == "MESH" and "face" in obj.name.lower():
                faceobj = obj
                break
        if faceobj:
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")
            faceobj.select_set(True)
            bpy.context.view_layer.objects.active = faceobj
            try:
                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.mesh.select_all(action="DESELECT")
                if "Eye Transparent" in faceobj.vertex_groups:
                    faceobj.vertex_groups.active = faceobj.vertex_groups[
                        "Eye Transparent"
                    ]
                    bpy.ops.object.vertex_group_select()
                    for group in faceobj.vertex_groups:
                        if "highlight" in group.name.lower():
                            faceobj.vertex_groups.active = group
                            bpy.ops.object.vertex_group_deselect()
                    bpy.ops.mesh.separate(type="SELECTED")
                bpy.ops.object.mode_set(mode="OBJECT")

                eye_obj = None
                for ob in bpy.context.selected_objects:
                    if ob != faceobj and ob.type == "MESH":
                        eye_obj = ob
                        break
                if eye_obj:
                    eye_obj.name = "EyeTransparent"
            except Exception as e:
                print("fixeyeshadow error:", e)
                try:
                    bpy.ops.object.mode_set(mode="OBJECT")
                except:
                    pass

    def reset_pose_location_and_rotation(self):
        try:
            armature = [
                object for object in bpy.data.objects if object.type == "ARMATURE"
            ][0]  # expecting 1 armature
        except IndexError as err:
            self.report(
                {"ERROR"},
                "Attempted to import model, but no armature found after import. Likely failed to import from FBX file.\n"
                "- Try renaming and removing any special characters (like star symbols) from any folders in the filepath",
            )
            raise err
        bpy.context.view_layer.objects.active = armature

        bpy.ops.object.mode_set(mode="POSE")
        bpy.ops.pose.loc_clear()
        bpy.ops.pose.rot_clear()
        bpy.ops.object.mode_set(mode="OBJECT")

    """
        NOTE: This will rename the Color Attributes for ALL meshes
        Currently expecting character setup to be performed in a fresh (new) file
    """

    def rename_mesh_color_attribute_name(self, name):
        meshes = [mesh for mesh_name, mesh in bpy.data.meshes.items()]

        for mesh in meshes:
            if len(mesh.color_attributes) == 1:
                mesh.color_attributes[
                    0
                ].name = (
                    name  # PGR: Named "VertexColors" and may not be the active color
                )
            else:
                if mesh.color_attributes.active_color:
                    mesh.color_attributes.active_color.name = name

    def __find_fbx_file(self, directory):
        for root, folder, files in os.walk(directory):
            for file_name in files:
                if ".fbx" in pathlib.Path(file_name).suffix:
                    return os.path.join(root, file_name)


"""
    This Operator should be executed AFTER importing the character model and
    BEFORE importing Genshin materials.
    That way there is no chance of deleting empties used by Festivity's shaders.
"""


class GI_OT_DeleteEmpties(Operator, CustomOperatorProperties):
    """Deletes Empties (except Head Driver's empties)"""

    bl_idname = "genshin.delete_empties"
    bl_label = "Genshin: Delete empties (except Head Driver's empties)"

    def execute(self, context):
        if self.game_type == GameType.ZENLESS_ZONE_ZERO.name:
            global IMPORTED_VIA_WIZARD
            if not IMPORTED_VIA_WIZARD:
                # Clear character model folder file path from cache to force manual folder selection for textures/outlines
                cache = get_cache()
                if CHARACTER_MODEL_FOLDER_FILE_PATH in cache:
                    cache.pop(CHARACTER_MODEL_FOLDER_FILE_PATH, None)
                    from setup_wizard.import_order import write_to_blender_cache

                    write_to_blender_cache(cache)
            else:
                # Reset the session variable
                IMPORTED_VIA_WIZARD = False

            obj = None
            for ob in bpy.data.objects:
                if ob.type == "ARMATURE" and (
                    "avatar" in ob.name.lower() or "npc" in ob.name.lower()
                ):
                    obj = ob
                    break
            if not obj:
                armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
                if armatures:
                    obj = armatures[0]
            if not obj:
                obj = bpy.data.objects.get("Armature")

            if obj:
                try:
                    for mesh_obj in bpy.data.objects:
                        if mesh_obj.type == "MESH" and (
                            "eyebrow" in mesh_obj.name.lower()
                            or "brow" in mesh_obj.name.lower()
                        ):
                            if (
                                mesh_obj.parent != obj
                                or mesh_obj.parent_type != "BONE"
                                or mesh_obj.parent_bone != "Bone_Root"
                            ):
                                mesh_obj.parent = obj
                                mesh_obj.parent_type = "BONE"
                                mesh_obj.parent_bone = "Bone_Root"
                except Exception as e:
                    print("Failed to parent eyebrows:", e)

                for object in bpy.data.objects:
                    if object.type == "MESH" and not object.data.uv_layers.get("UV1"):
                        object.data.uv_layers.new(name="UV1")

                for object in bpy.data.objects:
                    if object.type == "MESH" and (
                        "EffectMesh" in object.name
                        or "EyeStar" in object.name
                        or "hairshadow" in object.name.lower()
                        or "fx" in object.name.lower()
                    ):
                        try:
                            bpy.data.objects[object.name].hide_set(True)
                        except:
                            bpy.data.objects[object.name].hide_viewport = True
                        bpy.data.objects[object.name].hide_render = True

        scene = bpy.context.scene
        empties_to_not_delete = [
            "Head Forward",
            "Head Up",
            "Light Direction",
            "Main Light Direction",
            "Face Light Direction",
            "Head Driver",
            "Head Origin",
        ]
        for object in scene.objects:
            if object.type == "EMPTY":
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

        self.report({"INFO"}, "Deleted Empties")
        if self.next_step_idx:
            NextStepInvoker().invoke(
                self.next_step_idx,
                self.invoker_type,
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
            )
        return {"FINISHED"}


register, unregister = bpy.utils.register_classes_factory(
    [
        GI_OT_GenshinImportModel,
        GI_OT_DeleteEmpties,
        GI_OT_SetUpCharacter,
        HSR_OT_SetUpCharacter,
        ZZZ_OT_SetUpCharacter,
        NTE_OT_SetUpCharacter,
    ]
)
