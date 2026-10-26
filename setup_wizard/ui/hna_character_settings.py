from setup_wizard.utilites.new_lights import draw_lights_plus
"""Minimal HNA Character Settings: physics and rim intensity only."""
import bpy
from bpy.props import FloatProperty
from bpy.types import Panel
from setup_wizard.domain.game_types import GameType
from setup_wizard.ui.character_settings_utils import (
    get_character_materials, is_game_armature,
)


def rim_sockets(material):
    if not material.node_tree:
        return []
    return [node.inputs['_Rimintensity'] for node in material.node_tree.nodes
            if node.type == 'GROUP' and '_Rimintensity' in node.inputs]


def get_rim_intensity(arm):
    _, materials = get_character_materials(arm=arm)
    socket = next((s for mat in materials for s in rim_sockets(mat)), None)
    return socket.default_value if socket else float(arm.get('_hna_rim_intensity', 0.0))


def set_rim_intensity(arm, value):
    from setup_wizard.ui.character_settings_utils import ensure_character_node_trees_isolated
    _, materials = get_character_materials(arm=arm)
    ensure_character_node_trees_isolated(arm, materials)
    arm['_hna_rim_intensity'] = value
    for mat in materials:
        for socket in rim_sockets(mat):
            socket.default_value = value


def register_hna_properties():
    bpy.types.Object.hna_rim_intensity = FloatProperty(
        name='Rim Intensity', description='Rim intensity for this HNA character',
        min=0.0, max=10.0, soft_max=5.0,
        get=get_rim_intensity, set=set_rim_intensity,
    )


def unregister_hna_properties():
    if hasattr(bpy.types.Object, 'hna_rim_intensity'):
        del bpy.types.Object.hna_rim_intensity


class HNA_PT_CharacterSettings(Panel):
    bl_label = 'Character Settings'
    bl_idname = 'HNA_PT_CharacterSettings'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return is_game_armature(context, GameType.HONKAI_NEXUS_ANIMA.name)

    def draw(self, context):
        arm, materials = get_character_materials(context)
        draw_lights_plus(self.layout, context)
        rim = self.layout.box()
        rim.label(text='Rim', icon='SHADING_RENDERED')
        if any(rim_sockets(mat) for mat in materials):
            rim.prop(arm, 'hna_rim_intensity', text='Rim Intensity', slider=True)
        else:
            rim.label(text='Set up HNA materials first', icon='INFO')
        box_physics = self.layout.box()
        box_physics.label(text='Hair & Clothes Physics', icon='PHYSICS')
        col_physics = box_physics.column(align=True)
        from setup_wizard.character_rig_setup.rig_ui_utils import has_hair_clothes_physics
        if has_hair_clothes_physics(context):
            col_physics.prop(context.scene, 'gi_hair_physics_influence', text='Hair Physics', slider=True)
            col_physics.prop(context.scene, 'gi_clothes_physics_influence', text='Clothes Physics', slider=True)
            box_physics.column(align=True).operator('hoyoverse.remove_hair_clothes_physics', text='Remove Physics', icon='PANEL_CLOSE')
        else:
            col_physics.operator('hoyoverse.apply_hair_clothes_physics', text='Apply Physics', icon='FILE_REFRESH')
