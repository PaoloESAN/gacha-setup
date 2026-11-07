"""Native Goo eye depth must include both iris and masked highlight materials."""
from pathlib import Path
import os
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['PYTEST_VERSION'] = 'goo eye depth regression'
from setup_wizard.utils import genshin_engine_nodes as engine
from setup_wizard.replace_default_materials_setup.game_default_material_replacers import remove_set_depth_nodes_from_highlight_material

with bpy.data.libraries.load(str(ROOT / 'setup_wizard/shaders/gi/HoYoverse - Genshin Impact v3.4 starriia.blend')) as (source, target):
    target.materials = ['HoYoverse - Genshin New Pupil', 'HoYoverse - Genshin Highlight', 'HoYoverse - Genshin Face']
pupil, highlight, face = target.materials
materials = [pupil, highlight]
if not engine.is_goo_engine():
    counts = [(len(mat.node_tree.nodes), len(mat.node_tree.links)) for mat in materials]
    engine.configure_genshin_engine_nodes(materials)
    assert counts == [(len(mat.node_tree.nodes), len(mat.node_tree.links)) for mat in materials]
    print('GENSHIN_GOO_EYE_PORTABLE_PASS', bpy.app.version_string)
else:
    legacy = pupil.copy()
    legacy.name = 'HoYoverse - Legacy Hair'
    mesh = bpy.data.meshes.new('Legacy iris and body')
    mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0),
                      (2, 0, 0), (3, 0, 0), (2, 1, 0)], [], [(0, 1, 2), (3, 4, 5)])
    mesh.materials.append(legacy)
    obj = bpy.data.objects.new('Legacy Body', mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.vertex_groups.new(name='+EyeBoneA02.L').add([0, 1, 2], 1.0, 'REPLACE')
    star = bpy.data.objects.new('EyeStar', mesh.copy())
    bpy.context.scene.collection.objects.link(star)
    star.vertex_groups.new(name='+EyeBoneA02.L').add([0, 1, 2], 1.0, 'REPLACE')
    legacy_mode = legacy.blend_method
    depth_tree = bpy.data.node_groups['Set Depth']
    mask = next(node for node in depth_tree.nodes if node.bl_idname == 'ShaderNodeVertexColor')
    assert mask.layer_name == 'Eyes'
    mask_targets = [(link.to_socket, link.to_socket.default_value) for link in mask.outputs['Color'].links]
    # Color attributes elsewhere (AO, shading, etc.) must remain available.
    named_mask = pupil.node_tree.nodes.new('ShaderNodeVertexColor')
    named_mask.layer_name = 'Authored depth mask'
    engine.configure_genshin_engine_nodes()
    assert not any(node.bl_idname == 'ShaderNodeVertexColor' for node in depth_tree.nodes)
    assert pupil.node_tree.nodes.get(named_mask.name)
    assert all(not socket.is_linked and socket.default_value == value for socket, value in mask_targets)
    eye_material = mesh.materials[mesh.polygons[0].material_index]
    assert eye_material != legacy and eye_material.get('_gacha_legacy_eye_source') == legacy.name
    assert eye_material.node_tree.nodes.get('Goo Eye Set Depth')
    assert mesh.polygons[1].material_index == 0
    assert all(polygon.material_index == 0 for polygon in star.data.polygons)
    assert legacy.blend_method == legacy_mode, 'Body/hair render mode changed while isolating irises'
    slots = len(mesh.materials)
    engine.configure_genshin_engine_nodes()
    assert len(mesh.materials) == slots, 'Repeated setup duplicates legacy eye materials'
    assert face.use_screen_refraction, 'Native face depth was enabled without its refraction pass'
    assert bpy.context.scene.eevee.use_ssr and bpy.context.scene.eevee.use_ssr_refraction
    remove_set_depth_nodes_from_highlight_material(highlight)
    engine.configure_genshin_engine_nodes(materials)
    depth = pupil.node_tree.nodes['Goo Eye Set Depth']
    assert depth.node_tree != depth_tree, 'Eyes must not reuse the face screen-color blend'
    native_depth = next(node for node in depth.node_tree.nodes if node.bl_idname == 'ShaderNodeSetDepth')
    assert native_depth.inputs['Shader'].links[0].from_node.type == 'MIX'
    strength = depth.node_tree.nodes['Math.001']
    assert strength.inputs[1].links[0].from_socket.name == 'Intensity'
    assert strength.inputs[0].links[0].from_node.operation == 'LESS_THAN'
    assert depth.node_tree.get('_gacha_goo_eye_intensity_v2')
    # Migrate an already-saved opaque v1 group without resetting its control.
    rgb = next(node for node in depth.node_tree.nodes if node.bl_idname == 'ShaderNodeShaderToRGB')
    depth.node_tree.links.new(rgb.outputs['Color'], native_depth.inputs['Shader'])
    del depth.node_tree['_gacha_goo_eye_intensity_v2']
    depth.inputs['Intensity'].default_value = .23
    group_count = len(bpy.data.node_groups)
    engine.configure_genshin_engine_nodes(materials)
    assert native_depth.inputs['Shader'].links[0].from_node.type == 'MIX'
    assert abs(depth.inputs['Intensity'].default_value - .23) < 1e-6
    assert len(bpy.data.node_groups) == group_count
    face_depth = next(node for node in depth_tree.nodes if node.bl_idname == 'ShaderNodeSetDepth')
    assert face_depth.inputs['Shader'].links[0].from_node.type == 'MIX'
    output = next(n for n in pupil.node_tree.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
    assert output.inputs['Surface'].links[0].from_node == depth
    assert depth.inputs['Shader'].is_linked
    assert pupil.use_screen_refraction
    assert pupil.use_backface_culling and highlight.use_backface_culling
    highlight_depth = highlight.node_tree.nodes['Goo Eye Set Depth']
    assert highlight_depth.inputs['Shader'].links[0].from_node.type == 'EMISSION'
    mix = highlight_depth.outputs['Shader'].links[0].to_node
    assert mix.type == 'MIX_SHADER'
    assert mix.inputs[1].links[0].from_node.type == 'BSDF_TRANSPARENT'
    assert mix.inputs[0].is_linked
    remove_set_depth_nodes_from_highlight_material(highlight)
    assert highlight.node_tree.nodes.get('Goo Eye Set Depth')
    counts = [(len(mat.node_tree.nodes), len(mat.node_tree.links)) for mat in materials]
    pupil.blend_method = 'CLIP'
    assert engine.configure_genshin_engine_nodes(materials) == 0
    assert pupil.blend_method == 'CLIP', 'Repeated repairs overwrite authored blend modes'
    assert counts == [(len(mat.node_tree.nodes), len(mat.node_tree.links)) for mat in materials]
    native_detector = engine.is_goo_engine
    engine.is_goo_engine = lambda: False
    engine.configure_genshin_engine_nodes(materials)
    assert output.inputs['Surface'].links[0].from_node != depth
    assert mix.inputs[2].links[0].from_node.type == 'EMISSION'
    remove_set_depth_nodes_from_highlight_material(highlight)
    assert highlight.node_tree.nodes.get('Goo Eye Set Depth')
    engine.is_goo_engine = native_detector
    engine.configure_genshin_engine_nodes(materials)
    assert output.inputs['Surface'].links[0].from_node == depth
    assert mix.inputs[2].links[0].from_node == highlight_depth
    print('GENSHIN_GOO_EYE_DEPTH_PASS', bpy.app.version_string)
