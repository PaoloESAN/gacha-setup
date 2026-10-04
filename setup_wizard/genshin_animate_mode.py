# Genshin Impact Animate Mode.
# Mirrors WuWa's `wuthering_waves.toggle_animate_mode` (see wuwa_operations.py):
# swaps full shader materials for lightweight unlit materials (diffuse wired
# straight into Material Output) for smooth animation playback. On top of
# that, Genshin's Geometry Nodes modifiers (Outlines + Light Vectors) are
# hidden while animate mode is on, since they are the main viewport cost
# and useless with flat materials.

import bpy
from bpy.types import Operator


ANIMATE_MODE_SUFFIX = "_Low"
ANIMATE_MODE_SCENE_KEY = "gi_animate_mode"


def _find_diffuse_image(mat):
    """Finds the diffuse/base-color image of a shader material (WuWa logic)."""
    if not getattr(mat, "use_nodes", False) or not mat.node_tree:
        return None
    diff_img = None
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            if any(k in node.image.name.lower() for k in ['_d.', '_d_', 'diff', 'basecolor']):
                diff_img = node.image
                break
    if not diff_img:
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                diff_img = node.image
                break
    return diff_img


def _find_pupilatodo_node(mat):
    """Finds the PupilaTodo node inside a material."""
    if not getattr(mat, "use_nodes", False) or not mat.node_tree:
        return None
    for node in mat.node_tree.nodes:
        if node.type == 'GROUP' and node.node_tree:
            g_name = node.node_tree.name.lower()
            if "pupilatodo" in g_name or "pupila_todo" in g_name:
                return node
        elif "pupilatodo" in node.name.lower() or "pupila_todo" in node.name.lower():
            return node
    return None


def _is_new_pupil(mat) -> bool:
    if not mat:
        return False
    name_low = mat.name.lower()
    return "new pupil" in name_low or "newpupil" in name_low or (_find_pupilatodo_node(mat) is not None)


def _is_color_wheel(obj_or_mat) -> bool:
    if not obj_or_mat:
        return False
    name_low = getattr(obj_or_mat, "name", "").lower()
    return "colorwheel" in name_low or "color-wheel" in name_low or "color_wheel" in name_low


def _ensure_low_material_setup(low_mat, src_mat):
    """Wires the diffuse straight into Material Output Surface (unlit
    passthrough, no BSDF).
    For New Pupil materials, wires PupilaTodo straight into Material Output
    Surface instead of a texture.
    Idempotent, and upgrades _Low materials created previously."""
    tree = getattr(low_mat, "node_tree", None)
    if not tree:
        return
    output = tree.nodes.get("Material Output")
    if not output:
        output = tree.nodes.new("ShaderNodeOutputMaterial")
    if "Surface" not in output.inputs:
        return
    surface = output.inputs["Surface"]

    # Special handling for New Pupil: wire PupilaTodo directly to Material Output Surface
    src_pt = _find_pupilatodo_node(src_mat)
    if src_pt or _is_new_pupil(src_mat):
        for n in list(tree.nodes):
            if n.type in ('TEX_IMAGE', 'BSDF_PRINCIPLED'):
                tree.nodes.remove(n)

        low_pt = _find_pupilatodo_node(low_mat)
        if not low_pt:
            low_pt = tree.nodes.new("ShaderNodeGroup")
            if src_pt and src_pt.node_tree:
                low_pt.node_tree = src_pt.node_tree
            else:
                ng = bpy.data.node_groups.get("PupilaTodo")
                if not ng:
                    for g in bpy.data.node_groups:
                        if "pupilatodo" in g.name.lower():
                            ng = g
                            break
                if ng:
                    low_pt.node_tree = ng
            low_pt.name = "PupilaTodo"

        out_socket = (
            low_pt.outputs.get("Result")
            or low_pt.outputs.get("Color")
            or (low_pt.outputs[0] if low_pt.outputs else None)
        )
        if out_socket:
            for l in list(surface.links):
                if l.from_socket != out_socket:
                    tree.links.remove(l)
            if not any(l.from_socket == out_socket for l in surface.links):
                tree.links.new(out_socket, surface)

        if "Vector" in low_pt.inputs and not low_pt.inputs["Vector"].links:
            uv_lerp_src = src_mat.node_tree.nodes.get("UV Lerp") if (src_mat and src_mat.node_tree) else None
            if uv_lerp_src and uv_lerp_src.node_tree:
                low_uv_lerp = tree.nodes.get("UV Lerp")
                if not low_uv_lerp:
                    low_uv_lerp = tree.nodes.new("ShaderNodeGroup")
                    low_uv_lerp.node_tree = uv_lerp_src.node_tree
                    low_uv_lerp.name = "UV Lerp"
                tree.links.new(low_uv_lerp.outputs["UV"], low_pt.inputs["Vector"])

                uv0 = tree.nodes.get("UV0") or tree.nodes.new("ShaderNodeUVMap")
                uv0.name = "UV0"
                uv0.uv_map = "UV0"
                uv1 = tree.nodes.get("UV1") or tree.nodes.new("ShaderNodeUVMap")
                uv1.name = "UV1"
                uv1.uv_map = "UV1"
                if "UV0" in low_uv_lerp.inputs and not low_uv_lerp.inputs["UV0"].links:
                    tree.links.new(uv0.outputs["UV"], low_uv_lerp.inputs["UV0"])
                if "UV1" in low_uv_lerp.inputs and not low_uv_lerp.inputs["UV1"].links:
                    tree.links.new(uv1.outputs["UV"], low_uv_lerp.inputs["UV1"])
            else:
                uv_node = tree.nodes.get("UV Map") or tree.nodes.new("ShaderNodeUVMap")
                uv_node.name = "UV Map"
                tree.links.new(uv_node.outputs["UV"], low_pt.inputs["Vector"])
        return

    tex_node = None
    try:
        for link in surface.links:
            if getattr(link.from_node, "type", "") == 'TEX_IMAGE':
                tex_node = link.from_node
                break
    except Exception:
        pass
    if tex_node is None:
        for node in tree.nodes:
            if node.type == 'TEX_IMAGE' and getattr(node, "image", None):
                tex_node = node
                break
    if tex_node is None:
        diff_img = _find_diffuse_image(src_mat)
        if not diff_img:
            return  # No diffuse: leave Principled fallback untouched.
        tex_node = tree.nodes.new("ShaderNodeTexImage")
        tex_node.image = diff_img
    if not any(link.from_node == tex_node for link in surface.links):
        try:
            tree.links.new(tex_node.outputs["Color"], surface)
        except Exception:
            pass
    for node in [n for n in tree.nodes if n.type == 'BSDF_PRINCIPLED']:
        try:
            tree.nodes.remove(node)
        except Exception:
            pass


def _get_low_material(mat):
    """Returns (creating if needed) the lightweight counterpart of a material."""
    try:
        mat.use_fake_user = True
    except Exception:
        pass
    low_name = mat.name + ANIMATE_MODE_SUFFIX
    low_mat = bpy.data.materials.get(low_name)
    if not low_mat:
        low_mat = bpy.data.materials.new(name=low_name)
        low_mat.use_nodes = True
    _ensure_low_material_setup(low_mat, mat)
    return low_mat


def _is_exempt_from_animate_mode(mat, obj=None) -> bool:
    """Returns True if the material should NOT be replaced by Animate Mode.
    Exempts eye highlight materials and Color-Wheel objects/materials."""
    if not mat:
        return True
    if _is_color_wheel(mat):
        return True
    if obj is not None and (_is_color_wheel(obj) or _is_helper_object(obj)):
        return True

    name_low = mat.name.lower()
    exempt_keywords = [
        "highlight",
        "eyelight",
        "eye_highlight",
        "eyehighlight",
        "colorwheel",
        "color-wheel",
        "color_wheel",
    ]
    if any(k in name_low for k in exempt_keywords):
        return True

    if obj is not None and getattr(obj, "type", None) == 'MESH':
        obj_name_low = obj.name.lower()
        if any(k in obj_name_low for k in ["highlight", "eyelight"]):
            if any(k in name_low for k in ["highlight", "eye"]):
                return True

    return False


def _is_helper_object(obj):
    if not obj:
        return False
    name_low = obj.name.lower()
    if name_low.startswith('wgt-'):
        return True
    if _is_color_wheel(obj):
        return True
    try:
        for coll in obj.users_collection:
            c_low = coll.name.lower()
            if c_low == "wgt" or c_low.startswith("wgts_") or "wheel" in c_low:
                return True
    except Exception:
        pass
    return False


def _get_mesh_armature(mesh):
    """Finds the armature object associated with a mesh, if any."""
    if not mesh or getattr(mesh, "type", None) != 'MESH':
        return None
    if mesh.get(ANIMATE_MODE_SCENE_KEY) is not None:
        return mesh
    try:
        arm = mesh.find_armature()
        if arm and getattr(arm, "type", None) == 'ARMATURE':
            return arm
    except Exception:
        pass
    for mod in getattr(mesh, "modifiers", []) or []:
        try:
            if mod.type == 'ARMATURE' and getattr(mod, "object", None) and mod.object.type == 'ARMATURE':
                return mod.object
        except Exception:
            continue
    p = getattr(mesh, "parent", None)
    while p:
        if getattr(p, "type", None) == 'ARMATURE':
            return p
        p = getattr(p, "parent", None)
    return None


def _mesh_has_low_materials(mesh) -> bool:
    """Returns True if the mesh has any material ending with _Low."""
    if not mesh or getattr(mesh, "type", None) != 'MESH':
        return False
    for slot in getattr(mesh, "material_slots", []) or []:
        mat = getattr(slot, "material", None)
        if mat and mat.name.endswith(ANIMATE_MODE_SUFFIX):
            return True
    return False


def _restore_mesh_materials(mesh) -> bool:
    """Restores original materials and modifiers for a mesh with _Low materials."""
    if not mesh or getattr(mesh, "type", None) != 'MESH':
        return False
    restored_any = False
    for slot in getattr(mesh, "material_slots", []) or []:
        mat = getattr(slot, "material", None)
        if not mat or not mat.name.endswith(ANIMATE_MODE_SUFFIX):
            continue
        try:
            mat.use_fake_user = False
        except Exception:
            pass
        orig_name = mat.name[:-len(ANIMATE_MODE_SUFFIX)]
        orig_mat = bpy.data.materials.get(orig_name)
        if not orig_mat:
            for m in bpy.data.materials:
                if m.name == orig_name or m.name.startswith(orig_name + "."):
                    orig_mat = m
                    break
        if orig_mat:
            slot.material = orig_mat
            restored_any = True
    if restored_any:
        _set_gn_modifiers_visible(True, meshes=[mesh])
        try:
            from setup_wizard.utils.modifier_utils import set_modifier_property
            for mod in getattr(mesh, "modifiers", []) or []:
                if mod.type == 'NODES' and mod.node_group and "outline" in mod.node_group.name.lower():
                    set_modifier_property(mod, "Socket_24", True)
                    set_modifier_property(mod, "Toggle Outlines", True)
        except Exception:
            pass
    return restored_any


def _redraw_view3d(context=None):
    try:
        ctx = context or getattr(bpy, "context", None)
        if ctx and getattr(ctx, "view_layer", None):
            ctx.view_layer.update()
    except Exception:
        pass
    try:
        wm = getattr(bpy.context, "window_manager", None)
        if wm:
            for win in getattr(wm, 'windows', []) or []:
                screen = getattr(win, 'screen', None)
                if screen:
                    for area in screen.areas:
                        if area.type == 'VIEW_3D':
                            area.tag_redraw()
    except Exception:
        pass



def _set_gn_modifiers_visible(visible, meshes=None):
    """Shows/hides Genshin Geometry Nodes modifiers (Outlines + Light Vectors)."""
    if meshes is None:
        target_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH' and not _is_helper_object(obj)]
    else:
        target_objs = [obj for obj in meshes if getattr(obj, "type", None) == 'MESH' and not _is_helper_object(obj)]
    for obj in target_objs:
        for mod in getattr(obj, "modifiers", []) or []:
            if mod.type != 'NODES' or not mod.node_group:
                continue
            ng_low = mod.node_group.name.lower()
            if "outline" in ng_low or "light vector" in ng_low:
                try:
                    mod.show_viewport = visible
                except Exception:
                    pass
                try:
                    mod.show_render = visible
                except Exception:
                    pass


def is_genshin_animate_mode(arm=None, context=None) -> bool:
    """Returns True if the specified character (or currently selected character) is in animate mode."""
    if arm is None and context is not None:
        try:
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(context)
        except Exception:
            pass
    if arm is None:
        try:
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(getattr(bpy, "context", None))
        except Exception:
            pass

    if arm is not None:
        val = arm.get(ANIMATE_MODE_SCENE_KEY)
        if val is not None:
            return bool(val)
        # Fallback heuristic: check if any material assigned to the character's meshes has the low suffix
        try:
            from setup_wizard.ui.character_settings_utils import _iter_rig_meshes
            for mesh in _iter_rig_meshes(arm):
                if _is_helper_object(mesh):
                    continue
                for slot in getattr(mesh, "material_slots", []) or []:
                    mat = getattr(slot, "material", None)
                    if mat and mat.name.endswith(ANIMATE_MODE_SUFFIX):
                        if not _is_exempt_from_animate_mode(mat, obj=mesh):
                            return True
        except Exception:
            pass
        return False

    scene = getattr(bpy.context, "scene", None) if hasattr(bpy, "context") else None
    return bool(scene.get(ANIMATE_MODE_SCENE_KEY, False)) if scene else False


def set_genshin_animate_mode(enable: bool, arm=None, context=None):
    """Swaps materials to lightweight versions and toggles GN modifiers for the selected character.
    Includes fallback / migration for legacy global animate mode so that props, scenery,
    and legacy characters are not left stuck in _Low forever."""
    if arm is None and context is not None:
        try:
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(context)
        except Exception:
            pass
    if arm is None:
        try:
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(getattr(bpy, "context", None))
        except Exception:
            pass

    if arm is None:
        return False

    from setup_wizard.ui.character_settings_utils import _iter_rig_meshes
    target_meshes = [obj for obj in _iter_rig_meshes(arm) if not _is_helper_object(obj)]
    if not target_meshes:
        return False

    for obj in target_meshes:
        for slot in getattr(obj, "material_slots", []) or []:
            mat = slot.material
            if not mat:
                continue

            if _is_exempt_from_animate_mode(mat, obj=obj):
                # If an exempt material had previously been turned into _Low, restore it
                if mat.name.endswith(ANIMATE_MODE_SUFFIX):
                    orig_name = mat.name[:-len(ANIMATE_MODE_SUFFIX)]
                    orig_mat = bpy.data.materials.get(orig_name)
                    if not orig_mat:
                        for m in bpy.data.materials:
                            if m.name == orig_name or m.name.startswith(orig_name + "."):
                                orig_mat = m
                                break
                    if orig_mat:
                        slot.material = orig_mat
                continue

            if enable:
                if mat.name.endswith(ANIMATE_MODE_SUFFIX):
                    continue
                try:
                    mat.use_fake_user = True
                except Exception:
                    pass
                slot.material = _get_low_material(mat)
            else:
                if mat.name.endswith(ANIMATE_MODE_SUFFIX):
                    try:
                        mat.use_fake_user = False
                    except Exception:
                        pass
                    orig_name = mat.name[:-len(ANIMATE_MODE_SUFFIX)]
                    orig_mat = bpy.data.materials.get(orig_name)
                    if not orig_mat:
                        for m in bpy.data.materials:
                            if m.name == orig_name or m.name.startswith(orig_name + "."):
                                orig_mat = m
                                break
                    if orig_mat:
                        slot.material = orig_mat

    # Outlines (+ Light Vectors, useless with flat materials) are the main
    # viewport cost: hide them in animate mode, restore them afterwards.
    # Restoring re-applies the current Character Settings checkbox state so a
    # toggle changed mid-animate-mode is honoured on exit.
    if enable:
        _set_gn_modifiers_visible(False, meshes=target_meshes)
    else:
        _set_gn_modifiers_visible(True, meshes=target_meshes)
        try:
            from setup_wizard.ui.gi_ui_setup_wizard_menu import _apply_outlines_and_night_soul
            from setup_wizard.utils.modifier_utils import get_modifier_property
            outlines_on = True
            ns_on = False
            found_socket = False
            for mesh in target_meshes:
                for mod in getattr(mesh, "modifiers", []) or []:
                    if mod.type == 'NODES' and mod.node_group and "outlines" in mod.node_group.name.lower():
                        v24 = get_modifier_property(mod, "Socket_24")
                        if v24 is None:
                            v24 = get_modifier_property(mod, "Toggle Outlines")
                        if v24 is not None:
                            outlines_on = bool(v24)
                            found_socket = True
                        v23 = get_modifier_property(mod, "Socket_23")
                        if v23 is None:
                            v23 = get_modifier_property(mod, "Toggle Night Soul State")
                        if v23 is not None:
                            ns_on = bool(v23)
                        break
                if found_socket:
                    break
            if not found_socket:
                scene = getattr(context, "scene", None) if context else getattr(bpy.context, "scene", None)
                if scene:
                    outlines_on = bool(getattr(scene, "gi_enable_outlines", True))
                    ns_on = bool(getattr(scene, "gi_enable_night_soul", False))
            _apply_outlines_and_night_soul(context or getattr(bpy, "context", None), outlines_on, ns_on, arm=arm)
        except Exception:
            pass

        # FALLBACK / MIGRATION FOR LEGACY SCENES & OTHER OBJECTS:
        # If any other mesh in the scene has _Low materials:
        # If it belongs to NO armature, or belongs to an armature where gi_animate_mode is NOT True
        # (e.g. legacy global animate mode file), restore it so it's not stuck in _Low forever!
        target_meshes_set = set(target_meshes)
        for obj in bpy.data.objects:
            if getattr(obj, "type", None) != 'MESH' or _is_helper_object(obj) or obj in target_meshes_set:
                continue
            if _mesh_has_low_materials(obj):
                mesh_arm = _get_mesh_armature(obj)
                if mesh_arm is None or not mesh_arm.get(ANIMATE_MODE_SCENE_KEY, False):
                    _restore_mesh_materials(obj)
                    if mesh_arm is not None:
                        try:
                            mesh_arm[ANIMATE_MODE_SCENE_KEY] = False
                        except Exception:
                            pass

    try:
        arm[ANIMATE_MODE_SCENE_KEY] = bool(enable)
    except Exception:
        pass
    try:
        scene = getattr(context, "scene", None) if context else getattr(bpy.context, "scene", None)
        if scene:
            scene[ANIMATE_MODE_SCENE_KEY] = bool(enable)
    except Exception:
        pass

    _redraw_view3d(context)
    return True


class GI_OT_ToggleAnimateMode(Operator):
    bl_idname = "genshin.toggle_animate_mode"
    bl_label = "Toggle Animate Mode"
    bl_description = "Switch between full shaders and lightweight materials for smooth animation playback (also disables outlines)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context:
            return False
        try:
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            return resolve_settings_armature(context) is not None
        except Exception:
            return False

    def execute(self, context):
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature, resolve_character_name
        arm = resolve_settings_armature(context)
        if not arm:
            self.report({'WARNING'}, "No Genshin character selected for Animate Mode")
            return {'CANCELLED'}

        current = is_genshin_animate_mode(arm, context=context)
        new_val = not current
        success = set_genshin_animate_mode(new_val, arm=arm, context=context)
        if not success:
            self.report({'WARNING'}, "Could not toggle Animate Mode (no meshes found for character)")
            return {'CANCELLED'}

        status = "Enabled (Fast Playback)" if new_val else "Disabled (Full Shaders)"
        char_name = resolve_character_name(arm, getattr(arm, "name", "Character"))
        self.report({'INFO'}, f"Animate Mode {status} for {char_name}")
        return {'FINISHED'}


register, unregister = bpy.utils.register_classes_factory([GI_OT_ToggleAnimateMode])
