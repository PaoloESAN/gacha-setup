"""Per-character settings and lighting controls for Neverness to Everness (NTE)."""
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty
from bpy.types import Operator

from setup_wizard.domain.game_types import GameType
from setup_wizard.ui.character_settings_utils import (
    ensure_character_node_trees_isolated,
    get_character_materials,
    is_game_armature,
    resolve_settings_armature,
    _iter_rig_meshes,
)
from setup_wizard.utilites.new_lights import draw_lights_plus

NTE_PRESETS = (
    ("0", "Default", "Default NTE Shader Lighting"),
    ("1", "Sunrise", "Warm Sunrise Tone"),
    ("2", "Day", "Bright Daylight"),
    ("3", "Sunset", "Golden Sunset Tone"),
    ("4", "Night", "Cool Night Tone"),
    ("5", "Rainy", "Soft Overcast / Rainy Tone"),
    ("6", "Custom", "Custom Colors"),
)

# (Ambient, Light, Shadow, Rim Lit, Rim Shadow)
NTE_PRESET_COLORS = {
    "0": (
        (1.0, 1.0, 1.0, 1.0),
        (1.0, 1.0, 1.0, 1.0),
        (1.0, 1.0, 1.0, 1.0),
        (1.0, 1.0, 1.0, 1.0),
        (1.0, 1.0, 1.0, 1.0),
    ),
    "1": (
        (1.0, 0.88, 0.80, 1.0),
        (1.0, 0.86, 0.72, 1.0),
        (0.76, 0.70, 0.84, 1.0),
        (1.0, 0.82, 0.65, 1.0),
        (0.80, 0.72, 0.88, 1.0),
    ),
    "2": (
        (1.0, 1.0, 1.0, 1.0),
        (1.05, 1.03, 0.98, 1.0),
        (0.88, 0.92, 1.0, 1.0),
        (1.0, 1.0, 0.96, 1.0),
        (0.86, 0.92, 1.0, 1.0),
    ),
    "3": (
        (0.96, 0.78, 0.66, 1.0),
        (1.0, 0.72, 0.52, 1.0),
        (0.62, 0.50, 0.72, 1.0),
        (1.0, 0.68, 0.44, 1.0),
        (0.66, 0.52, 0.76, 1.0),
    ),
    "4": (
        (0.68, 0.76, 0.94, 1.0),
        (0.74, 0.82, 1.0, 1.0),
        (0.42, 0.50, 0.74, 1.0),
        (0.66, 0.80, 1.0, 1.0),
        (0.45, 0.56, 0.82, 1.0),
    ),
    "5": (
        (0.84, 0.88, 0.94, 1.0),
        (0.86, 0.90, 0.95, 1.0),
        (0.68, 0.74, 0.84, 1.0),
        (0.84, 0.90, 0.96, 1.0),
        (0.66, 0.74, 0.86, 1.0),
    ),
}

_is_syncing_nte_props = False


def _redraw_view3d():
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def _global_nodes(materials):
    return [
        node
        for mat in materials
        if mat and mat.use_nodes and mat.node_tree
        for node in mat.node_tree.nodes
        if node.type == 'GROUP'
        and node.node_tree
        and 'global material properties' in node.node_tree.name.lower()
    ]


def _get_gmp_output(tree):
    if not tree:
        return None
    return tree.nodes.get('Global Properties') or tree.nodes.get('Group Output')


def prepare_nte_character_settings(arm, materials):
    if not arm or not materials:
        return None
    ensure_character_node_trees_isolated(arm, materials)
    nodes = _global_nodes(materials)
    if not nodes:
        return None
    tree = nodes[0].node_tree
    for n in nodes:
        n.node_tree = tree
    return tree


def _apply_nte_preset(tree, preset_key):
    colors = NTE_PRESET_COLORS.get(str(preset_key))
    if not colors or not tree:
        return
    out = _get_gmp_output(tree)
    if not out:
        return
    socket_names = ("Ambient Colour", "Light Colour", "Shadow Colour", "Rim Lit", "Rim Shadow")
    for s_name, col in zip(socket_names, colors):
        sock = out.inputs.get(s_name)
        if sock and not sock.is_linked:
            sock.default_value = col
    tree.update_tag()


def _get_use_fresnel(tree):
    out = _get_gmp_output(tree)
    sock = out.inputs.get('Use Fresnel') if out else None
    return bool(sock and sock.default_value > 0.5)


def _set_use_fresnel(tree, enabled):
    out = _get_gmp_output(tree)
    sock = out.inputs.get('Use Fresnel') if out else None
    if sock and not sock.is_linked:
        sock.default_value = 1.0 if enabled else 0.0


def _get_fresnel_strength(tree):
    """Inverted Fresnel exponent: higher UI value = stronger/wider Fresnel (30.0 - power)."""
    out = _get_gmp_output(tree)
    sock = out.inputs.get('Fresnel Strength') if out else None
    return max(0.0, min(29.0, 30.0 - sock.default_value)) if sock else 5.0


def _set_fresnel_strength(tree, value):
    out = _get_gmp_output(tree)
    sock = out.inputs.get('Fresnel Strength') if out else None
    if sock and not sock.is_linked:
        sock.default_value = max(1.0, 30.0 - float(value))


def _get_rim_x(tree):
    out = _get_gmp_output(tree)
    sock = out.inputs.get('Rim Scale') if out else None
    return float(sock.default_value[0]) if sock else 0.75


def _set_rim_x(tree, value):
    out = _get_gmp_output(tree)
    sock = out.inputs.get('Rim Scale') if out else None
    if sock and not sock.is_linked:
        cur = tuple(sock.default_value)
        sock.default_value = (float(value), cur[1], cur[2])


def _get_rim_y(tree):
    out = _get_gmp_output(tree)
    sock = out.inputs.get('Rim Scale') if out else None
    return float(sock.default_value[1]) if sock else 0.5


def _set_rim_y(tree, value):
    out = _get_gmp_output(tree)
    sock = out.inputs.get('Rim Scale') if out else None
    if sock and not sock.is_linked:
        cur = tuple(sock.default_value)
        sock.default_value = (cur[0], float(value), cur[2])


def _outline_inputs(arm):
    for mesh in _iter_rig_meshes(arm):
        for modifier in mesh.modifiers:
            if modifier.type != 'NODES' or not modifier.node_group:
                continue
            if not any(k in modifier.node_group.name.lower() for k in ('描边', 'outline')):
                continue
            if hasattr(modifier.node_group, 'interface'):
                for socket in modifier.node_group.interface.items_tree:
                    if (
                        socket.item_type == 'SOCKET'
                        and socket.in_out == 'INPUT'
                        and socket.name in ('描边宽度', 'Outline Width', 'Outline Thickness', 'Width')
                    ):
                        yield mesh, modifier, socket


def _get_outline_thickness(arm):
    from setup_wizard.utils.modifier_utils import get_modifier_property
    for _, modifier, socket in _outline_inputs(arm):
        val = get_modifier_property(modifier, socket.identifier)
        return float(val) if val is not None else float(getattr(socket, 'default_value', 0.0003))
    return 0.0003


def _set_outline_thickness(arm, value):
    from setup_wizard.utils.modifier_utils import set_modifier_property
    for mesh, modifier, socket in _outline_inputs(arm):
        set_modifier_property(modifier, socket.identifier, float(value))
        mesh.update_tag()


def _update_nte_lighting_control_type(self, context):
    global _is_syncing_nte_props
    if _is_syncing_nte_props:
        return
    arm, mats = get_character_materials(context)
    if not arm:
        return
    ctrl_type = getattr(self, 'nte_lighting_control_type', 'PANEL')
    arm['nte_lighting_control_type'] = ctrl_type

    from setup_wizard.character_rig_setup.lighting_panel_setup import (
        connect_nte_lighting_panel,
        disconnect_nte_lighting_panel,
        set_lighting_panel_visibility,
    )
    if ctrl_type == 'PANEL':
        prepare_nte_character_settings(arm, mats)
        connect_nte_lighting_panel(target_materials=mats or None)
        set_lighting_panel_visibility(arm, True)
    else:
        set_lighting_panel_visibility(arm, False)
        disconnect_nte_lighting_panel(target_materials=mats or None)
        tree = prepare_nte_character_settings(arm, mats)
        if tree:
            mode = str(arm.get('nte_light_mode', getattr(self, 'nte_light_mode', '0')))
            if mode != '6':
                _apply_nte_preset(tree, mode)
    _redraw_view3d()


def _update_nte_light_mode(self, context):
    global _is_syncing_nte_props
    if _is_syncing_nte_props:
        return
    arm, mats = get_character_materials(context)
    if not arm:
        return
    mode = getattr(self, 'nte_light_mode', '0')
    arm['nte_light_mode'] = mode
    tree = prepare_nte_character_settings(arm, mats)
    if tree and mode != '6':
        _apply_nte_preset(tree, mode)
    _redraw_view3d()


def _sync_nte_scene_props(scene, context, arm, mats):
    global _is_syncing_nte_props
    if not arm:
        return
    _is_syncing_nte_props = True
    try:
        from setup_wizard.character_rig_setup.lighting_panel_setup import (
            armature_has_lighting_panel,
            is_nte_lighting_panel_connected,
        )
        has_lp = armature_has_lighting_panel(arm)
        if has_lp:
            stored = arm.get('nte_lighting_control_type')
            if stored not in ('PANEL', 'THIS_PANEL'):
                stored = 'PANEL' if is_nte_lighting_panel_connected(target_materials=mats) else 'THIS_PANEL'
            if getattr(scene, 'nte_lighting_control_type', None) != stored:
                scene.nte_lighting_control_type = stored
        stored_mode = str(arm.get('nte_light_mode', '0'))
        if stored_mode in NTE_PRESET_COLORS or stored_mode == '6':
            if getattr(scene, 'nte_light_mode', None) != stored_mode:
                scene.nte_light_mode = stored_mode
    except Exception:
        pass
    finally:
        _is_syncing_nte_props = False


class NTE_OT_SelectLightingPanel(Operator):
    bl_idname = "neverness_to_everness.select_lighting_panel"
    bl_label = "Select 3D Lighting Panel"
    bl_description = "Selects the Lighting Panel controls in Pose Mode in the 3D viewport"

    @classmethod
    def poll(cls, context):
        try:
            from setup_wizard.character_rig_setup.lighting_panel_setup import armature_has_lighting_panel
            arm = resolve_settings_armature(context)
            return bool(arm and armature_has_lighting_panel(arm))
        except Exception:
            return False

    def execute(self, context):
        from setup_wizard.geometry_nodes_setup.lighting_panel_names import LightingPanelNames
        arm = resolve_settings_armature(context)
        if not arm:
            return {'CANCELLED'}
        try:
            if context.object and context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            for o in context.selected_objects:
                o.select_set(False)
            arm.select_set(True)
            context.view_layer.objects.active = arm
            bpy.ops.object.mode_set(mode='POSE')
            for pb in arm.pose.bones:
                pb.bone.select = False
            lp_b = arm.data.bones.get(LightingPanelNames.Bones.LIGHTING_PANEL)
            if lp_b:
                lp_b.select = True
                arm.data.bones.active = lp_b
        except Exception:
            pass
        return {'FINISHED'}


class NTE_OT_ToggleLightingPanelVisibility(Operator):
    bl_idname = "neverness_to_everness.toggle_lighting_panel_visibility"
    bl_label = "Toggle Lighting Panel Visibility"
    bl_description = "Shows or hides the Lighting Panel controls in the viewport"

    @classmethod
    def poll(cls, context):
        try:
            from setup_wizard.character_rig_setup.lighting_panel_setup import armature_has_lighting_panel
            arm = resolve_settings_armature(context)
            return bool(arm and armature_has_lighting_panel(arm))
        except Exception:
            return False

    def execute(self, context):
        from setup_wizard.character_rig_setup.lighting_panel_setup import (
            is_lighting_panel_visible,
            set_lighting_panel_visibility,
        )
        arm = resolve_settings_armature(context)
        if not arm:
            return {'CANCELLED'}
        vis = is_lighting_panel_visible(arm)
        set_lighting_panel_visibility(arm, not vis)
        _redraw_view3d()
        return {'FINISHED'}


def _draw_sockets(layout, node, names):
    if not node:
        return
    for name in names:
        sock = node.inputs.get(name)
        if sock and not sock.is_linked:
            layout.prop(sock, 'default_value', text=name, slider=(sock.type == 'VALUE'))


def draw_nte_character_settings(layout, context):
    scene = context.scene
    arm, mats = get_character_materials(context)
    _sync_nte_scene_props(scene, context, arm, mats)

    # 0. Animate Mode (fast playback: lightweight materials, no outlines)
    from setup_wizard.genshin_animate_mode import is_genshin_animate_mode
    is_anim = is_genshin_animate_mode(arm, context=context)
    layout.operator(
        "genshin.toggle_animate_mode",
        text="Disable Animate Mode" if is_anim else "Enable Animate Mode",
        icon="SHADING_TEXTURE" if is_anim else "RESTRICT_RENDER_OFF",
    )

    nodes = _global_nodes(mats)
    tree = nodes[0].node_tree if nodes else None
    out = _get_gmp_output(tree)

    # 1. Lighting Type (Light Panel vs This Panel) & Lighting Mode Presets
    from setup_wizard.character_rig_setup.lighting_panel_setup import armature_has_lighting_panel
    has_lp = bool(arm and armature_has_lighting_panel(arm))
    is_lp_mode = False

    if has_lp:
        col_type = layout.column(align=False)
        col_type.label(text="Lighting Type:")
        row_btn = col_type.row(align=True)
        row_btn.prop(scene, "nte_lighting_control_type", expand=True)
        is_lp_mode = getattr(scene, "nte_lighting_control_type", "PANEL") == "PANEL"

    if tree and out and not is_lp_mode:
        col_light = layout.column(align=True)
        col_light.label(text="Lighting Mode:")
        col_light.prop(scene, "nte_light_mode", text="")
        if getattr(scene, "nte_light_mode", "0") == "6":
            box_col = col_light.box()
            box_col.label(text="Custom Colors", icon="COLOR")
            _draw_sockets(
                box_col.column(align=True),
                out,
                ("Ambient Colour", "Light Colour", "Shadow Colour", "Rim Lit", "Rim Shadow"),
            )

    # 2. Lights+
    draw_lights_plus(layout, context)

    # Ensure Rim Light patch is applied on official Blender (no-op on Goo Engine, cached after first run)
    try:
        from setup_wizard.optimization.blender_rimlight_patch import patch_all_rimlight_groups_for_blender
        patch_all_rimlight_groups_for_blender()
    except Exception:
        pass

    # 3. Shadow Position, Rim Light, Fresnel
    if tree and out:
        _draw_sockets(layout.column(align=True), out, ("Shadow Position",))

        box_rim = layout.box()
        box_rim.label(text="Rim Light", icon="LIGHT_SUN")
        col_rim = box_rim.column(align=True)
        _draw_sockets(col_rim, out, ("Rim Intensity",))
        if not is_lp_mode:
            col_rim.prop(tree, "nte_rim_x", text="Rim Light X", slider=True)
            col_rim.prop(tree, "nte_rim_y", text="Rim Light Y", slider=True)
            _draw_sockets(col_rim, out, ("Rim Lit", "Rim Shadow"))

        box_fresnel = layout.box()
        box_fresnel.label(text="Fresnel", icon="SHADING_RENDERED")
        box_fresnel.prop(tree, "nte_use_fresnel", text="Use Fresnel")
        if getattr(tree, "nte_use_fresnel", False):
            col_fres = box_fresnel.column(align=True)
            _draw_sockets(col_fres, out, ("Fresnel Color",))
            col_fres.prop(tree, "nte_fresnel_strength", text="Fresnel Strength", slider=True)
            _draw_sockets(col_fres, out, ("Fresnel Scale",))

        # 4. Outlines
        box_ol = layout.box()
        box_ol.label(text="Outlines", icon="STROKE")
        col_ol = box_ol.column(align=True)
        _draw_sockets(col_ol, out, ("Outline Color",))
        if arm:
            col_ol.prop(arm, "nte_outline_thickness", text="Outline Thickness", slider=True)

    # 5. Hair & Clothes Physics
    from setup_wizard.ui.hi3_character_settings import _draw_physics
    _draw_physics(layout, context)


def register_nte_properties():
    for cls in (NTE_OT_SelectLightingPanel, NTE_OT_ToggleLightingPanelVisibility):
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass

    bpy.types.Scene.nte_lighting_control_type = EnumProperty(
        name="Lighting Control",
        description="Choose how lighting colors and tints are controlled for NTE",
        items=[
            ("PANEL", "Light Panel", "Use 3D Lighting Panel in viewport"),
            ("THIS_PANEL", "This Panel", "Use Character Settings panel controls"),
        ],
        default="PANEL",
        update=_update_nte_lighting_control_type,
    )

    bpy.types.Scene.nte_light_mode = EnumProperty(
        name="Light Mode",
        description="Lighting preset mode for Neverness to Everness shader",
        items=NTE_PRESETS,
        default="0",
        update=_update_nte_light_mode,
    )

    bpy.types.Object.nte_outline_thickness = FloatProperty(
        name="Outline Thickness",
        min=0.0,
        soft_max=0.01,
        precision=5,
        step=0.01,
        get=_get_outline_thickness,
        set=_set_outline_thickness,
    )

    bpy.types.ShaderNodeTree.nte_use_fresnel = BoolProperty(
        name="Use Fresnel",
        get=_get_use_fresnel,
        set=_set_use_fresnel,
    )

    bpy.types.ShaderNodeTree.nte_fresnel_strength = FloatProperty(
        name="Fresnel Strength",
        min=0.0,
        max=29.0,
        get=_get_fresnel_strength,
        set=_set_fresnel_strength,
    )

    bpy.types.ShaderNodeTree.nte_rim_x = FloatProperty(
        name="Rim Light X",
        min=0.0,
        soft_max=2.0,
        get=_get_rim_x,
        set=_set_rim_x,
    )

    bpy.types.ShaderNodeTree.nte_rim_y = FloatProperty(
        name="Rim Light Y",
        min=0.0,
        soft_max=2.0,
        get=_get_rim_y,
        set=_set_rim_y,
    )


def unregister_nte_properties():
    for cls in (NTE_OT_ToggleLightingPanelVisibility, NTE_OT_SelectLightingPanel):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass

    for prop in ("nte_lighting_control_type", "nte_light_mode"):
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)
    if hasattr(bpy.types.Object, "nte_outline_thickness"):
        delattr(bpy.types.Object, "nte_outline_thickness")
    for prop in ("nte_use_fresnel", "nte_fresnel_strength", "nte_rim_x", "nte_rim_y"):
        if hasattr(bpy.types.ShaderNodeTree, prop):
            delattr(bpy.types.ShaderNodeTree, prop)
