"""Minimal HNA Character Settings: physics and rim intensity only."""
import bpy
from bpy.props import FloatProperty
from bpy.types import Panel
from setup_wizard.domain.game_types import GameType
from setup_wizard.ui.character_settings_utils import (
    get_character_materials, is_game_armature, _iter_rig_meshes,
)
from setup_wizard.utils.modifier_utils import get_modifier_property, set_modifier_property


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
    _, materials = get_character_materials(arm=arm)
    others = {mat for obj in bpy.data.objects if obj.type == 'ARMATURE' and obj != arm
              for mat in get_character_materials(arm=obj)[1]}
    remap = {mat: mat.copy() for mat in materials if mat in others and rim_sockets(mat)}
    for mesh in _iter_rig_meshes(arm):
        for slot in mesh.material_slots:
            if slot.material in remap:
                slot.material = remap[slot.material]
        # Outline mask inputs must follow a copied material, too.
        for mod in mesh.modifiers:
            if mod.type != 'NODES' or not mod.node_group:
                continue
            for item in mod.node_group.interface.items_tree:
                if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.socket_type == 'NodeSocketMaterial':
                    original = get_modifier_property(mod, item.identifier)
                    if original in remap:
                        set_modifier_property(mod, item.identifier, remap[original])
    _, materials = get_character_materials(arm=arm)
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
