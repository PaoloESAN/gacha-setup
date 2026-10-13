"""Run with Blender --background --python tests/genshin_outline_colors_blender.py."""
import sys
from pathlib import Path
from types import SimpleNamespace
import bpy, addon_utils

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE))
original_resource = bpy.utils.user_resource
def isolated_resource(kind, path='', create=False):
    if kind in {'SCRIPTS', 'CONFIG'}:
        target = WORKSPACE / '.tmp/outline-blender' / kind.lower() / path
        target.mkdir(parents=True, exist_ok=True)
        return str(target)
    return original_resource(kind, path=path, create=create)
bpy.utils.user_resource = isolated_resource
addon_utils.enable('setup_wizard', default_set=True)
from setup_wizard.material_data_import_setup.material_data_applier import MaterialDataApplier, V4_MaterialDataApplier
from setup_wizard.material_data_import_setup.game_material_data_importers import GameMaterialDataImporter
from setup_wizard.parsers.material_data_json_parsers import HoyoStudioMaterialDataJsonParser
from setup_wizard.domain.outline_material_data import OutlineMaterialGroup

with bpy.data.libraries.load(str(WORKSPACE / 'setup_wizard/shaders/gi/HoYoverse - PrimoToon v4.0.blend'), link=False) as (src, dst):
    dst.materials = ['HoYoverse - Genshin Body', 'HoYoverse - Genshin Outlines']
body_template, outline_template = dst.materials
image = bpy.data.images.new('OutlineColorTestDiffuse', width=2, height=2)

def create(colors):
    body, outline = body_template.copy(), outline_template.copy()
    body.name = 'Outline test Body'
    outline.name = 'Outline test Body Outlines'
    parser = HoyoStudioMaterialDataJsonParser({'m_SavedProperties': {'m_Floats': {}, 'm_TexEnvs': {},
        'm_Colors': {key: dict(zip('rgba', value)) for key, value in colors.items()}}})
    parser.parse()
    applier = V4_MaterialDataApplier(parser, OutlineMaterialGroup(body, outline))
    shader = applier._get_outline_shader_node()
    slots = applier._get_indexed_outline_color_inputs(shader)
    assert all(i in slots for i in range(1, 6))
    for i in range(1, 6):
        for link in list(slots[i].links):
            outline.node_tree.links.remove(link)
        slots[i].default_value = MaterialDataApplier.OUTLINE_SENTINEL_RAW_LINEAR[i - 1]
    applier._find_outline_diffuse_node(outline.node_tree).image = image
    return applier, shader, slots

def apply(applier):
    GameMaterialDataImporter.apply_material_data(None, 'Body', [applier], SimpleNamespace(name='Body.json'))

colors = {('_OutlineColor' if i == 1 else f'_OutlineColor{i}'): (.02*i, .03*i, .04*i, 1)
          for i in range(1, 6)}
for old_fallback in (False, True):
    applier, shader, slots = create(colors)
    if old_fallback:
        applier._apply_diffuse_outline_color_fallback(shader, list(slots.values()))
    apply(applier)
    for i in range(1, 6):
        assert not slots[i].is_linked, (old_fallback, i)
        key = '_OutlineColor' if i == 1 else f'_OutlineColor{i}'
        assert max(abs(a-b) for a,b in zip(slots[i].default_value, colors[key])) < 1e-6
    assert not applier.outline_material.get(applier.OUTLINE_DIFFUSE_FALLBACK_TAG)
    print('PASS: JSON colors applied without diffuse links; old fallback:', old_fallback)

# Authored colors identical to the template still belong to the JSON.
sentinels = {('_OutlineColor' if i == 1 else f'_OutlineColor{i}'):
             MaterialDataApplier.OUTLINE_SENTINEL_RAW_LINEAR[i-1] for i in range(1, 6)}
applier, shader, slots = create(sentinels)
apply(applier)
assert all(not slot.is_linked for slot in slots.values())
print('PASS: authored sentinel colors do not trigger fallback')

# A partial JSON, including black, must not color every other outline via diffuse.
applier, shader, slots = create({'_OutlineColor': (0, 0, 0, 1)})
apply(applier)
assert all(not slot.is_linked for slot in slots.values())
assert tuple(slots[1].default_value) == (0, 0, 0, 1)
print('PASS: partial and black JSON outline colors take precedence')

# Missing colors get a fallback only at the final application stage.
applier, shader, slots = create({})
applier.set_up_mesh_material_data()
assert all(not slot.is_linked for slot in slots.values())
applier.set_up_outline_colors()
assert all(slot.is_linked for slot in slots.values())
counts = len(applier.outline_material.node_tree.links)
applier.set_up_outline_colors()
assert len(applier.outline_material.node_tree.links) == counts
print('PASS: missing JSON colors get a repeatable fallback after application')

# Keep a user's replacement texture link while removing old automatic diffuse links.
applier, shader, slots = create(colors)
applier._apply_diffuse_outline_color_fallback(shader, list(slots.values()))
manual = applier.outline_material.node_tree.nodes.new('ShaderNodeTexImage')
manual.name = 'Custom user outline color'
applier.outline_material.node_tree.links.new(manual.outputs['Color'], slots[1])
apply(applier)
assert slots[1].links[0].from_node == manual
assert all(not slots[i].is_linked for i in range(2, 6))
assert not applier.outline_material.get(applier.OUTLINE_DIFFUSE_FALLBACK_TAG)
print('PASS: manual color links are preserved')
