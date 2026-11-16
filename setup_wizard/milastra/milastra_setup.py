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

        existing_face_diff = glob.glob(
            os.path.join(extract_dir, "**", "*Face*Diffuse*.png"),
            recursive=True,
        )
        face_diff_src = os.path.join(assets_dir, "Beyd_Avatar_Girl_Face_P0144_01_Tex_Diffuse.png")
        if not existing_face_diff and os.path.isfile(face_diff_src):
            shutil.copy2(face_diff_src, os.path.join(extract_dir, "Beyd_Avatar_Girl_Face_P0144_01_Tex_Diffuse.png"))

    return fbx_dst


def _remove_opposite_gender_files(extract_dir: str, gender: str):
    opposite_dir = "boy" if gender == "GIRL" else "girl"
    target_dir = "girl" if gender == "GIRL" else "boy"
    has_target_dir = any(
        d.lower() == target_dir
        for _, dirs, _ in os.walk(extract_dir)
        for d in dirs
    )
    if has_target_dir:
        for root, dirs, _ in os.walk(extract_dir, topdown=True):
            for d in list(dirs):
                if d.lower() == opposite_dir:
                    try:
                        shutil.rmtree(os.path.join(root, d))
                    except OSError:
                        pass
                    dirs.remove(d)

    opposite_prefix = "Beyd_Avatar_Boy_" if gender == "GIRL" else "Beyd_Avatar_Girl_"
    for root, _, files in os.walk(extract_dir):
        for fname in files:
            if fname.startswith(opposite_prefix):
                try:
                    os.remove(os.path.join(root, fname))
                except OSError:
                    pass


def _merge_sub_armature_into_base(base_arm, sub_arm, new_meshes):
    base_scale = base_arm.matrix_world.to_scale()
    sub_scale = sub_arm.matrix_world.to_scale()
    # Some standalone assets (e.g. Face_P0146.fbx, Pupil_P0466.fbx) are exported at 1.0
    # meter scale while BaseBody FBXs are 0.01; align sub_arm scale & head height before join.
    scale_mismatch = (
        abs(base_scale.x) > 1e-6
        and abs(sub_scale.x / base_scale.x) > 10.0
    )
    if scale_mismatch:
        ratio = base_scale.x / sub_scale.x
        base_head = base_arm.data.bones.get("Bip001 Head")
        sub_head = sub_arm.data.bones.get("Bip001 Head")
        if base_head and sub_head:
            base_head_w = base_arm.matrix_world @ base_head.head_local
            sub_head_w = sub_arm.matrix_world @ sub_head.head_local
            sub_arm.scale = (
                sub_arm.scale.x * ratio,
                sub_arm.scale.y * ratio,
                sub_arm.scale.z * ratio,
            )
            sub_arm.location += base_head_w - (sub_head_w * ratio)
        else:
            sub_arm.scale = (
                sub_arm.scale.x * ratio,
                sub_arm.scale.y * ratio,
                sub_arm.scale.z * ratio,
            )
    base_inv = base_arm.matrix_world.inverted()
    for mesh in new_meshes:
        if scale_mismatch:
            mesh.parent = base_arm
        else:
            mw = mesh.matrix_world.copy()
            mesh.parent = base_arm
            mesh.matrix_parent_inverse = base_inv
            mesh.matrix_world = mw
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


def _find_extract_dir_for_milastra():
    scene = getattr(bpy.context, "scene", None)
    if scene and scene.get("setup_wizard_temp_extract_dir"):
        d = scene.get("setup_wizard_temp_extract_dir")
        if d and os.path.isdir(d):
            return d
    for img in bpy.data.images:
        fp = getattr(img, "filepath", "") or ""
        if fp and "milastra_" in fp.lower():
            p = fp
            while p and os.path.basename(p).lower() != "" and not os.path.basename(p).lower().startswith("milastra_"):
                p = os.path.dirname(p)
            if p and os.path.isdir(p):
                return p
    return ""


def _fix_milastra_sub_materials(extract_dir):
    """Give _Sub01 / _Sub02 meshes their own material copy with matching SubXX Diffuse/Lightmap."""
    if not extract_dir or not os.path.isdir(extract_dir):
        return
    sub_re = re.compile(r"^(.*?)_(Sub\d+)(?:_.*)?$", re.IGNORECASE)
    mat_cache = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        m = sub_re.match(obj.name)
        if not m:
            continue
        prefix_part, sub_tag = m.group(1), m.group(2)
        for slot in obj.material_slots:
            mat = slot.material
            if not mat or not getattr(mat, "use_nodes", False) or not mat.node_tree:
                continue
            if "outlines" in mat.name.lower():
                continue
            diff_node = mat.node_tree.nodes.get("Main_Diffuse")
            if not diff_node or not getattr(diff_node, "image", None):
                continue
            if sub_tag.lower() in diff_node.image.name.lower():
                continue
            cache_key = (mat.name, prefix_part.lower(), sub_tag.lower())
            if cache_key in mat_cache:
                slot.material = mat_cache[cache_key]
                continue
            diff_matches = glob.glob(
                os.path.join(extract_dir, "**", f"*{prefix_part}*{sub_tag}*Diffuse*.png"),
                recursive=True,
            )
            lm_matches = glob.glob(
                os.path.join(extract_dir, "**", f"*{prefix_part}*{sub_tag}*Lightmap*.png"),
                recursive=True,
            )
            if not diff_matches:
                continue
            new_mat = mat.copy()
            new_mat.name = f"{mat.name}_{sub_tag}"
            n_diff = new_mat.node_tree.nodes.get("Main_Diffuse")
            if n_diff:
                n_diff.image = bpy.data.images.load(diff_matches[0], check_existing=True)
            n_lm = new_mat.node_tree.nodes.get("Main_Lightmap")
            if n_lm and lm_matches:
                n_lm.image = bpy.data.images.load(lm_matches[0], check_existing=True)
            slot.material = new_mat
            mat_cache[cache_key] = new_mat


def _fix_milastra_missing_mat_json_defaults():
    """Fix orange BaseBody and neon-green Outlines when a Milastra set has no Materials/*.json."""
    extract_dir = _find_extract_dir_for_milastra()
    has_mat_json = bool(
        extract_dir and glob.glob(os.path.join(extract_dir, "**", "*_Mat.json"), recursive=True)
    )
    if has_mat_json:
        return

    skin_rgba = (1.0, 0.76, 0.62, 1.0)
    dark_outline = (0.12, 0.07, 0.07, 1.0)

    for mat in bpy.data.materials:
        if not getattr(mat, "use_nodes", False) or not mat.node_tree:
            continue
        nt = mat.node_tree
        m_low = mat.name.lower()
        pt = nt.nodes.get("PrimoToon")

        # 1. Replace neon-green/placeholder default outlines with Main_Diffuse Color output
        if "outlines" in m_low and "face" not in m_low and pt:
            diff_node = nt.nodes.get("Main_Diffuse")
            is_basebody_mask = (
                "basebody body" in m_low
                and diff_node
                and getattr(diff_node, "image", None)
                and "basebody_common" in diff_node.image.name.lower()
            )
            for inp in pt.inputs:
                if inp.name.startswith("Outline Color") and not inp.links and hasattr(inp, "default_value"):
                    try:
                        if is_basebody_mask:
                            inp.default_value = skin_rgba
                        elif diff_node and getattr(diff_node, "image", None) and "Color" in diff_node.outputs:
                            nt.links.new(diff_node.outputs["Color"], inp)
                        else:
                            inp.default_value = dark_outline
                    except Exception:
                        pass

        # 2. Fix BaseBody orange mask texture when no Mat.json was imported
        if "basebody body" in m_low and "outlines" not in m_low and pt:
            diff_node = nt.nodes.get("Main_Diffuse")
            if diff_node and getattr(diff_node, "image", None) and "basebody_common" in diff_node.image.name.lower():
                diff_in = pt.inputs.get("Diffuse Color")
                if diff_in and not nt.nodes.get("Milastra_Body_Skin_Color"):
                    rgb = nt.nodes.new("ShaderNodeRGB")
                    rgb.name = "Milastra_Body_Skin_Color"
                    rgb.location = (diff_node.location.x + 220, diff_node.location.y)
                    rgb.outputs[0].default_value = skin_rgba
                    for l in list(diff_in.links):
                        nt.links.remove(l)
                    nt.links.new(rgb.outputs[0], diff_in)
            for inp in pt.inputs:
                if inp.name in ("Toggle Lightmap AO", "Toggle Shadow Ramp") and not inp.links:
                    try:
                        inp.default_value = False
                    except Exception:
                        pass


def _restore_milastra_face_shadow():
    """Ensure Shadow Alpha.Face_Shadow uses PrimoToon's Face_Shadow mask rather than an SDF lightmap."""
    shadow_alpha = bpy.data.node_groups.get("Shadow Alpha")
    fs_node = shadow_alpha.nodes.get("Face_Shadow") if shadow_alpha else None
    if not fs_node:
        return
    cur_img = getattr(fs_node, "image", None)
    if cur_img and not any(k in cur_img.name.lower() for k in ("sdf", "facelightmap", "face_lightmap")):
        return

    fs_img = bpy.data.images.get("Avatar_Tex_Face_Shadow.png")
    if fs_img is None:
        shader_blend = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "shaders",
            "gi",
            "HoYoverse - PrimoToon v4.0.blend",
        )
        if os.path.isfile(shader_blend):
            with bpy.data.libraries.load(shader_blend, link=False) as (df, dt):
                if "Avatar_Tex_Face_Shadow.png" in df.images:
                    dt.images = ["Avatar_Tex_Face_Shadow.png"]
            fs_img = bpy.data.images.get("Avatar_Tex_Face_Shadow.png")

    if fs_img:
        try:
            fs_img.colorspace_settings.name = "Non-Color"
        except Exception:
            pass
        fs_node.image = fs_img


def apply_milastra_face_skin_tint():
    """Apply Milastra post-setup material fixes (SubXX split, BaseBody skin, Face tint, Outlines)."""
    extract_dir = _find_extract_dir_for_milastra()
    _fix_milastra_sub_materials(extract_dir)
    _fix_milastra_missing_mat_json_defaults()
    _restore_milastra_face_shadow()
    try:
        from setup_wizard.ui.character_settings_tabs import hide_registered_rig_layers
        hide_registered_rig_layers()
    except Exception:
        pass

    for mat in bpy.data.materials:
        if not getattr(mat, "use_nodes", False) or not mat.node_tree:
            continue
        if "face" not in mat.name.lower():
            continue
        nt = mat.node_tree
        face_diff = nt.nodes.get("Face_Diffuse")
        primotoon = nt.nodes.get("PrimoToon")
        if not face_diff or not primotoon or not getattr(face_diff, "image", None):
            continue
        if "face_p0144" not in face_diff.image.name.lower():
            continue
        if nt.nodes.get("Milastra_Face_Skin_Tint"):
            continue
        diff_in = primotoon.inputs.get("Diffuse Color")
        if not diff_in:
            continue
        mix = nt.nodes.new("ShaderNodeMix")
        mix.name = "Milastra_Face_Skin_Tint"
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.location = (face_diff.location.x + 260, face_diff.location.y)
        mix.inputs[0].default_value = 1.0  # Factor
        # Warm peach skin tint (linear) matching Beyd_Avatar_Girl_BaseBody neck/body
        mix.inputs[7].default_value = (1.0, 0.85, 0.64, 1.0)
        body_mat = next(
            (m for m in bpy.data.materials if "basebody body" in m.name.lower() and "outlines" not in m.name.lower() and getattr(m, "use_nodes", False)),
            None,
        )
        body_pt = body_mat.node_tree.nodes.get("PrimoToon") if body_mat and body_mat.node_tree else None
        if body_pt:
            for sock_name in ("Cold Shadow Color", "Warm Shadow Color"):
                if sock_name in body_pt.inputs and sock_name in primotoon.inputs and not primotoon.inputs[sock_name].links:
                    try:
                        primotoon.inputs[sock_name].default_value = body_pt.inputs[sock_name].default_value
                    except Exception:
                        pass
        for l in list(diff_in.links):
            nt.links.remove(l)
        nt.links.new(face_diff.outputs["Color"], mix.inputs[6])
        nt.links.new(mix.outputs[2], diff_in)


class MILASTRA_OT_SetupWizardUI(Operator, ImportHelper, CustomOperatorProperties):
    """Select a Milastra Wonderland .zip set or folder containing .zip files and choose gender"""
    bl_idname = "milastra_wonderland.setup_wizard_ui"
    bl_label = "Milastra Wonderland: Select .zip or Folder"

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
        description="Select Girl or Boy BaseBody",
        items=[
            ("GIRL", "Girl", "Use Girl BaseBody (Beyd_Avatar_Girl)"),
            ("BOY", "Boy", "Use Boy BaseBody (Beyd_Avatar_Boy)"),
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
        selected_zip = (
            self.filepath
            if self.filepath and os.path.isfile(self.filepath) and self.filepath.lower().endswith(".zip")
            else None
        )
        if selected_zip:
            zip_files = [selected_zip]
            char_target = selected_zip
        else:
            selected_folder = _resolve_selected_folder(self.filepath, self.directory, self.file_directory)
            if not selected_folder or not os.path.isdir(selected_folder):
                self.report({"ERROR"}, "Please select a .zip file or a valid folder containing .zip files.")
                return {"CANCELLED"}

            zip_files = sorted(
                os.path.join(selected_folder, f)
                for f in os.listdir(selected_folder)
                if f.lower().endswith(".zip") and not f.startswith("._")
            )
            if not zip_files:
                self.report({"ERROR"}, f"No .zip files found in: {selected_folder}")
                return {"CANCELLED"}
            char_target = selected_folder

        from setup_wizard.services.isolation import isolation_service
        if (
            os.environ.get("GACHA_SETUP_ISOLATED_WORKER") != "1"
            and isolation_service.is_isolated_mode_enabled()
        ):
            try:
                job_char_dir = os.path.dirname(char_target) if selected_zip else char_target
                return isolation_service.launch_job(
                    context,
                    self,
                    character_dir=job_char_dir,
                    game_type=GameType.MILASTRA_WONDERLAND.name,
                    high_level_step_name=self.bl_idname,
                    extra_job_data={
                        "milastra_gender": self.gender,
                        "milastra_source": char_target,
                        "is_archive": False,
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

            try:
                from setup_wizard.ui.character_settings_utils import tag_armature_game
                tag_armature_game(base_arm, GameType.GENSHIN_IMPACT.name)
            except Exception:
                pass

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
