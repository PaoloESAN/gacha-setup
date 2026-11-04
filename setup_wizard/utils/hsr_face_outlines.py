"""Camera-free face outlines with view-aware visibility in the material."""
import bpy
from pathlib import Path

from .modifier_utils import get_modifier_property, set_modifier_property

GROUP_NAME = 'StellarToon - Outlines FACE'
VERSION = 3


def configure_face_outline_material(material, view_mask):
    """Wrap only face outline outputs; keep their colors and shadow handling."""
    if not material or not material.use_nodes:
        return
    tree = material.node_tree
    for output in [node for node in tree.nodes if node.type == 'OUTPUT_MATERIAL']:
        surface = output.inputs['Surface']
        if not surface.is_linked:
            continue
        source = surface.links[0].from_socket
        if source.node.type == 'GROUP' and source.node.node_tree and source.node.node_tree.get('gacha_hsr_face_view_mask'):
            if source.node.node_tree != view_mask:
                source.node.node_tree = view_mask
            continue
        wrapper = tree.nodes.new('ShaderNodeGroup')
        wrapper.node_tree = view_mask
        wrapper.name = wrapper.label = 'HSR Face View Mask'
        wrapper.location = (output.location.x - 220, output.location.y)
        tree.links.new(source, wrapper.inputs['Outline'])
        tree.links.new(wrapper.outputs['Outline'], surface)


def configure_face_outlines(context, mesh, modifier):
    if not any(m and 'face' in m.name.lower() and 'mask' not in m.name.lower()
               and 'outline' not in m.name.lower() for m in mesh.data.materials):
        return False
    base = modifier.node_group
    if not base or not (base.name.startswith('StellarToon - Outlines GN') or base.get('gacha_hsr_face_outlines')):
        return False
    # The complete node graph is authored in StellarToonV1.1.blend.
    group = next((g for g in bpy.data.node_groups
                  if g.name.startswith(GROUP_NAME) and g.get('gacha_hsr_face_outlines') == VERSION), None)
    view_mask = next((g for g in bpy.data.node_groups
                      if g.bl_idname == 'ShaderNodeTree' and g.get('gacha_hsr_face_view_mask') == 2), None)
    if group is None or view_mask is None:
        # Upgrade existing characters from the baked asset, preserving their
        # materials and width settings instead of rebuilding the character.
        path = Path(__file__).resolve().parents[1] / 'shaders/hsr/StellarToonV1.1.blend'
        requested = ([] if group else [GROUP_NAME]) + ([] if view_mask else ['StellarToon - Face View Mask'])
        with bpy.data.libraries.load(str(path), link=False) as (available, target):
            target.node_groups = requested
        for loaded in target.node_groups:
            if loaded and loaded.get('gacha_hsr_face_outlines') == VERSION:
                group = loaded
            elif loaded and loaded.get('gacha_hsr_face_view_mask') == 2:
                view_mask = loaded
        if group is None or view_mask is None:
            raise RuntimeError('The bundled HSR face outline template is outdated.')
    colors_attribute = get_modifier_property(modifier, 'Input_3_attribute_name') or 'Col'
    modifier.node_group = group
    # Blender 4.x resets attribute mode when the geometry interface changes.
    # Keep the authored width mask rather than the socket's constant color.
    set_modifier_property(modifier, 'Input_3_attribute_name', colors_attribute)
    set_modifier_property(modifier, 'Input_3_use_attribute', True)
    set_modifier_property(modifier, 'Input_8', 0.)
    set_modifier_property(modifier, group['dynamic_socket'], 1.)
    set_modifier_property(modifier, group['interior_mask_socket'], True)
    for mask_key, outline_key in (
            ('Input_10', 'Input_5'), ('Input_11', 'Input_9'),
            ('Input_14', 'Input_15'), ('Input_18', 'Input_19'), ('Input_24', 'Input_25')):
        material = get_modifier_property(modifier, mask_key)
        if material and 'face' in material.name.lower() and 'mask' not in material.name.lower():
            configure_face_outline_material(get_modifier_property(modifier, outline_key), view_mask)
    return True
