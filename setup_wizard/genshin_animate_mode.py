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


def _ensure_low_material_setup(low_mat, src_mat):
    """Wires the diffuse straight into Material Output Surface (unlit
    passthrough, no BSDF). Idempotent, and upgrades _Low materials created
    by the previous Principled-based version: reuses their image and drops
    the now pointless Principled node."""
    tree = getattr(low_mat, "node_tree", None)
    if not tree:
        return
    output = tree.nodes.get("Material Output")
    if not output or "Surface" not in output.inputs:
        return
    surface = output.inputs["Surface"]

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
    low_name = mat.name + ANIMATE_MODE_SUFFIX
    low_mat = bpy.data.materials.get(low_name)
    if not low_mat:
        low_mat = bpy.data.materials.new(name=low_name)
        low_mat.use_nodes = True
    _ensure_low_material_setup(low_mat, mat)
    return low_mat


def _is_helper_object(obj):
    name_low = obj.name.lower()
    if name_low.startswith('wgt-'):
        return True
    try:
        for coll in obj.users_collection:
            c_low = coll.name.lower()
            if c_low == "wgt" or c_low.startswith("wgts_"):
                return True
    except Exception:
        pass
    return False


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
                        return True
        except Exception:
            pass
        return False

    scene = getattr(bpy.context, "scene", None) if hasattr(bpy, "context") else None
    return bool(scene.get(ANIMATE_MODE_SCENE_KEY, False)) if scene else False


def set_genshin_animate_mode(enable: bool, arm=None, context=None):
    """Swaps materials to lightweight versions and toggles GN modifiers for the selected character."""
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

            if enable:
                if mat.name.endswith(ANIMATE_MODE_SUFFIX):
                    continue
                slot.material = _get_low_material(mat)
            else:
                if mat.name.endswith(ANIMATE_MODE_SUFFIX):
                    orig_name = mat.name[:-len(ANIMATE_MODE_SUFFIX)]
                    orig_mat = bpy.data.materials.get(orig_name)
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
