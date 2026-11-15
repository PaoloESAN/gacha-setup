import glob
import os
import re
import shutil
import tempfile
import zipfile

import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from setup_wizard.domain.game_types import GameType
from setup_wizard.genshin_import_character_model import (
    SHADER_COLOR_ATTRIBUTE_NAME,
    _execute_fbx_import,
    clear_armature_pose,
    is_rigging_disabled,
    reorient_armature_bones,
)
from setup_wizard.import_order import (
    CHARACTER_MODEL_FOLDER_FILE_PATH,
    NextStepInvoker,
    cache_using_cache_key,
    get_cache,
    set_active_character_directory,
)
from setup_wizard.setup_wizard_operator_base_classes import CustomOperatorProperties
from setup_wizard.utils import material_utils


def _get_milastra_assets_dir():
    setup_wizard_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(setup_wizard_root, "assets", "milastra")


def _resolve_selected_folder(filepath: str, directory: str, file_directory: str) -> str:
    for candidate in (filepath, directory, file_directory):
        if not candidate:
            continue
        if os.path.isdir(candidate):
            return os.path.normpath(candidate)
        parent = os.path.dirname(candidate)
        if parent and os.path.isdir(parent):
            return os.path.normpath(parent)
    return ""


def _copy_basebody_assets(extract_dir: str, gender: str):
    assets_dir = _get_milastra_assets_dir()
    prefix = "Beyd_Avatar_Boy_BaseBody_Common" if gender == "BOY" else "Beyd_Avatar_Girl_BaseBody_Common"
    fbx_src = os.path.join(assets_dir, f"{prefix}.fbx")
    tex_src = os.path.join(assets_dir, f"{prefix}_01_Tex_Diffuse.png")

    if not os.path.isfile(fbx_src):
        raise FileNotFoundError(f"Missing Milastra BaseBody FBX: {fbx_src}")

    fbx_dst = os.path.join(extract_dir, f"{prefix}.fbx")
    shutil.copy2(fbx_src, fbx_dst)

    if os.path.isfile(tex_src):
        existing_tex = glob.glob(
            os.path.join(extract_dir, "**", f"{prefix}_01_Tex_Diffuse.png"),
            recursive=True,
        )
        if not existing_tex:
            shutil.copy2(tex_src, os.path.join(extract_dir, f"{prefix}_01_Tex_Diffuse.png"))

    if gender == "GIRL":
        existing_face_fbx = [
            f for f in glob.glob(os.path.join(extract_dir, "**", "*.fbx"), recursive=True)
            if "face" in os.path.basename(f).lower()
        ]
        face_fbx_src = os.path.join(assets_dir, "Face_P0146.fbx")
        if not existing_face_fbx and os.path.isfile(face_fbx_src):
            shutil.copy2(face_fbx_src, os.path.join(extract_dir, "Face_P0146.fbx"))

        existing_face_sdf = glob.glob(
            os.path.join(extract_dir, "**", "*Face*SDF*.png"),
            recursive=True,
        )
        face_sdf_src = os.path.join(assets_dir, "Beyd_Avatar_Girl_Face_Tex_SDF.png")
        if not existing_face_sdf and os.path.isfile(face_sdf_src):
            shutil.copy2(face_sdf_src, os.path.join(extract_dir, "Beyd_Avatar_Girl_Face_Tex_SDF.png"))

    return fbx_dst


def _remove_opposite_gender_files(extract_dir: str, gender: str):
    opposite_prefix = "Beyd_Avatar_Boy_" if gender == "GIRL" else "Beyd_Avatar_Girl_"
    for root, _, files in os.walk(extract_dir):
        for fname in files:
            if fname.startswith(opposite_prefix):
                try:
                    os.remove(os.path.join(root, fname))
                except OSError:
                    pass


def _merge_sub_armature_into_base(base_arm, sub_arm, new_meshes):
    for mesh in new_meshes:
        mesh.parent = base_arm
        for mod in mesh.modifiers:
            if mod.type == "ARMATURE":
                mod.object = base_arm

    bpy.ops.object.select_all(action="DESELECT")
    sub_arm.select_set(True)
    base_arm.select_set(True)
    bpy.context.view_layer.objects.active = base_arm
    bpy.ops.object.join()


def _cleanup_duplicate_bones(base_arm):
    bpy.ops.object.select_all(action="DESELECT")
    base_arm.select_set(True)
    bpy.context.view_layer.objects.active = base_arm
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        edit_bones = base_arm.data.edit_bones
        dup_pattern = re.compile(r"^(.+)\.(\d{3})$")
        to_delete = []
        for bone in list(edit_bones):
            match = dup_pattern.match(bone.name)
            if match and match.group(1) in edit_bones:
                canonical = edit_bones[match.group(1)]
                for child in list(bone.children):
                    child.parent = canonical
                to_delete.append(bone)
        for bone in to_delete:
            edit_bones.remove(bone)
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")


def _rename_mesh_color_attributes(target_name: str):
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.data.color_attributes:
            for attr in obj.data.color_attributes:
                if attr.name in ("Attribute", "Col", "Color"):
                    attr.name = target_name
                    break


class MILASTRA_OT_SetupWizardUI(Operator, ImportHelper, CustomOperatorProperties):
    """Select a folder containing Milastra Wonderland .zip files and choose gender"""
    bl_idname = "milastra_wonderland.setup_wizard_ui"
    bl_label = "Milastra Wonderland: Select .zip Folder"

    filename_ext = ""

    filter_glob: StringProperty(
        default="*.zip",
        options={"HIDDEN"},
        maxlen=255,
    )

    directory: StringProperty(
        name="Directory",
        description="Folder containing Milastra Wonderland .zip files",
        default="",
        subtype="DIR_PATH",
    )

    gender: EnumProperty(
        name="Base Model",
        description="Select Female or Male BaseBody",
        items=[
            ("GIRL", "Female", "Use female BaseBody (Beyd_Avatar_Girl)"),
            ("BOY", "Male", "Use male BaseBody (Beyd_Avatar_Boy)"),
        ],
        default="GIRL",
    )

    def draw(self, context):
        from setup_wizard.ui.unified_ui_setup_wizard_menu import draw_file_browser_setup_settings
        draw_file_browser_setup_settings(
            self.layout,
            context,
            game_type=GameType.MILASTRA_WONDERLAND.name,
            operator=self,
        )

    def execute(self, context):
        selected_folder = _resolve_selected_folder(self.filepath, self.directory, self.file_directory)
        if not selected_folder or not os.path.isdir(selected_folder):
            self.report({"ERROR"}, "Please select a valid folder containing .zip files.")
            return {"CANCELLED"}

        zip_files = sorted(
            os.path.join(selected_folder, f)
            for f in os.listdir(selected_folder)
            if f.lower().endswith(".zip") and not f.startswith("._")
        )
        if not zip_files:
            self.report({"ERROR"}, f"No .zip files found in: {selected_folder}")
            return {"CANCELLED"}

        from setup_wizard.services.isolation import isolation_service
        if (
            os.environ.get("GACHA_SETUP_ISOLATED_WORKER") != "1"
            and isolation_service.is_isolated_mode_enabled()
        ):
            try:
                return isolation_service.launch_job(
                    context,
                    self,
                    character_dir=selected_folder,
                    game_type=GameType.MILASTRA_WONDERLAND.name,
                    high_level_step_name=self.bl_idname,
                    extra_job_data={
                        "milastra_gender": self.gender,
                        "is_archive": True,
                    },
                )
            finally:
                super().clear_custom_properties()

        extract_dir = tempfile.mkdtemp(prefix="milastra_")
        context.scene["setup_wizard_temp_extract_dir"] = extract_dir

        for zpath in zip_files:
            with zipfile.ZipFile(zpath, "r") as zf:
                zf.extractall(extract_dir)

        _remove_opposite_gender_files(extract_dir, self.gender)

        try:
            base_fbx = _copy_basebody_assets(extract_dir, self.gender)
        except Exception as ex:
            self.report({"ERROR"}, str(ex))
            return {"CANCELLED"}

        other_fbxs = [
            f
            for f in sorted(glob.glob(os.path.join(extract_dir, "**", "*.fbx"), recursive=True))
            if os.path.abspath(f) != os.path.abspath(base_fbx)
            and not os.path.basename(f).startswith("._")
        ]

        existing_materials = list(bpy.data.materials.values())
        try:
            _execute_fbx_import(base_fbx)
            base_arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
            if not base_arm:
                self.report({"ERROR"}, f"Failed to import BaseBody armature from {base_fbx}")
                return {"CANCELLED"}

            for fbx_path in other_fbxs:
                before = set(bpy.data.objects)
                _execute_fbx_import(fbx_path)
                new_objs = set(bpy.data.objects) - before
                sub_arms = [o for o in new_objs if o.type == "ARMATURE"]
                new_meshes = [o for o in new_objs if o.type == "MESH"]
                for sub_arm in sub_arms:
                    _merge_sub_armature_into_base(base_arm, sub_arm, new_meshes)

            _cleanup_duplicate_bones(base_arm)

            if not is_rigging_disabled(context):
                clear_armature_pose(base_arm)
                reorient_armature_bones(base_arm)

            _rename_mesh_color_attributes(SHADER_COLOR_ATTRIBUTE_NAME)

            set_active_character_directory(extract_dir)
            if context.window_manager.cache_enabled:
                cache_using_cache_key(
                    get_cache(context.window_manager.cache_enabled),
                    CHARACTER_MODEL_FOLDER_FILE_PATH,
                    extract_dir,
                )

            from setup_wizard.utils.texture_utils import fix_missing_textures
            fix_missing_textures(extract_dir)

            materials_imported = [
                m for m in bpy.data.materials.values() if m not in existing_materials
            ]
            material_utils.add_fake_user_to_materials(materials_imported)

            genshin_step_name = (
                "genshin.setup_wizard_ui"
                if bpy.app.version >= (3, 3, 0)
                else "genshin.setup_wizard_ui_no_outlines"
            )
            NextStepInvoker().invoke(
                1,
                "invoke_next_step_ui",
                file_path_to_cache=extract_dir,
                high_level_step_name=genshin_step_name,
                game_type=GameType.GENSHIN_IMPACT.name,
            )
        finally:
            super().clear_custom_properties()

        return {"FINISHED"}
