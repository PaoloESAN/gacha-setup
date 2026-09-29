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


def _set_gn_modifiers_visible(visible):
    """Shows/hides Genshin Geometry Nodes modifiers (Outlines + Light Vectors)."""
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or _is_helper_object(obj):
            continue
        for mod in obj.modifiers:
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


def set_genshin_animate_mode(enable: bool):
    """Swaps materials to lightweight versions and toggles GN modifiers."""
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        for slot in obj.material_slots:
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
        _set_gn_modifiers_visible(False)
    else:
        _set_gn_modifiers_visible(True)
        try:
            from setup_wizard.ui.gi_ui_setup_wizard_menu import _apply_outlines_and_night_soul
            scene = getattr(bpy.context, "scene", None)
            outlines_on = bool(getattr(scene, "gi_enable_outlines", True)) if scene else True
            ns_on = bool(getattr(scene, "gi_enable_night_soul", False)) if scene else False
            _apply_outlines_and_night_soul(bpy.context, outlines_on, ns_on)
        except Exception:
            pass

    try:
        bpy.context.view_layer.update()
    except Exception:
        pass
    try:
        for win in getattr(bpy.context.window_manager, 'windows', []) or []:
            screen = getattr(win, 'screen', None)
            if screen:
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
    except Exception:
        pass


class GI_OT_ToggleAnimateMode(Operator):
    bl_idname = "genshin.toggle_animate_mode"
    bl_label = "Toggle Animate Mode"
    bl_description = "Switch between full shaders and lightweight materials for smooth animation playback (also disables outlines)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        current = context.scene.get(ANIMATE_MODE_SCENE_KEY, False)
        new_val = not current
        context.scene[ANIMATE_MODE_SCENE_KEY] = new_val
        set_genshin_animate_mode(new_val)
        status = "Enabled (Fast Playback)" if new_val else "Disabled (Full Shaders)"
        self.report({'INFO'}, f"Animate Mode {status}")
        return {'FINISHED'}


register, unregister = bpy.utils.register_classes_factory([GI_OT_ToggleAnimateMode])
