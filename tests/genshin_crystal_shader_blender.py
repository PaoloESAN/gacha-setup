"""Crystal transparency selects shader outputs, never custom-pass separators."""
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
original_resource = bpy.utils.user_resource


def resource(kind, path='', create=False):
    if kind in {'CONFIG', 'SCRIPTS'}:
        target = ROOT / 'tests/.runtime/crystal-shader' / str(bpy.app.version[0]) / kind / path
        target.mkdir(parents=True, exist_ok=True)
        return str(target)
    return original_resource(kind, path=path, create=create)


bpy.utils.user_resource = resource
sys.path.insert(0, str(ROOT))
from setup_wizard.replace_default_materials_setup.game_default_material_replacers import GenshinImpactDefaultMaterialReplacer
from setup_wizard.texture_import_setup.texture_importer_types import setup_crystal_material_nodes

builders = [setup_crystal_material_nodes,
            lambda material: GenshinImpactDefaultMaterialReplacer.setup_crystal_material_nodes(None, material)]
checks = 0
for builder in builders:
    for variant in ('Quality', 'Performance', 'Legacy'):
        material = bpy.data.materials.new(f'HoYoverse - Vodyanitsa Crystal01 {variant}')
        material.use_nodes = True
        tree = material.node_tree
        tree.nodes.clear()
        output = tree.nodes.new('ShaderNodeOutputMaterial')
        group = bpy.data.node_groups.new('Crystal ' + variant, 'ShaderNodeTree')
        # Put misleading non-shader sockets first, as in the reported graph.
        group.interface.new_socket(name='---- CUSTOM PASS ----', in_out='OUTPUT', socket_type='NodeSocketFloat')
        if variant == 'Quality':
            group.interface.new_socket(name='PrimoToon', in_out='OUTPUT', socket_type='NodeSocketFloat')
        expected_name = 'PrimoToon' if variant == 'Legacy' else 'BSDF'
        group.interface.new_socket(name=expected_name, in_out='OUTPUT', socket_type='NodeSocketShader')
        node = tree.nodes.new('ShaderNodeGroup')
        node.node_tree = group
        node.name = 'Body Shader' if variant == 'Performance' else 'PrimoToon'
        node.label = variant
        builder(material)
        mix = next(n for n in tree.nodes if n.type == 'MIX_SHADER')
        assert mix.inputs[2].links[0].from_socket == node.outputs[expected_name]
        # Repair an existing bad connection too, rather than keeping it.
        tree.links.new(node.outputs[0], mix.inputs[2])
        counts = (len(tree.nodes), len(tree.links))
        builder(material)
        builder(material)
        assert (len(tree.nodes), len(tree.links)) == counts
        assert mix.inputs[2].links[0].from_socket == node.outputs[expected_name]
        assert mix.inputs[1].links[0].from_node.type == 'BSDF_TRANSPARENT'
        assert output.inputs['Surface'].links[0].from_node == mix
        checks += 1

for asset_name, node_name in (
        ('HoYoverse - PrimoToon v4.0.blend', 'PrimoToon'),
        ('HoYoverse - Genshin Impact v3.4 starriia.blend', 'Body Shader')):
    asset = ROOT / 'setup_wizard/shaders/gi' / asset_name
    with bpy.data.libraries.load(str(asset), link=False) as (source, loaded):
        loaded.materials = [next(n for n in source.materials if 'body' in n.casefold())]
    for builder in builders:
        material = loaded.materials[0].copy()
        material.name = 'HoYoverse - Vodyanitsa Crystal01 Asset'
        builder(material)
        mix = next(n for n in material.node_tree.nodes if n.type == 'MIX_SHADER')
        link = mix.inputs[2].links[0]
        assert link.from_node.name == node_name and link.from_socket.type == 'SHADER'
        builder(material)
        assert mix.inputs[2].links[0].from_socket == link.from_socket
        checks += 1
print('CRYSTAL_SHADER_PASS', checks, 'quality performance legacy repair repeatability asset', flush=True)
