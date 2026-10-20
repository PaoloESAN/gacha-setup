"""Blender --background --factory-startup --python tests/new_lights_blender.py."""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import addon_utils
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
addon_utils.enable('setup_wizard', default_set=True)
from setup_wizard.utilites.new_lights import (
    TAG, MODE, supported, draw_lights_plus, character_objects, object_materials, needs_setup,
    is_genshin_highlight,
)
from setup_wizard.utils.modifier_utils import set_modifier_property

class Layout:
    def __init__(self): self.labels = []; self.ops = []; self.props = []; self.prop_labels = []
    def box(self): return self
    def label(self, **kw): self.labels.append(kw['text'])
    def operator(self, identifier, **kw): self.ops.append(identifier)
    def prop(self, obj, name, **kw):
        self.props.append((obj, name))
        self.prop_labels.append(kw.get('text'))

if not supported():
    layout = Layout()
    draw_lights_plus(layout, bpy.context)
    assert not layout.labels and not layout.ops
    assert not bpy.ops.gacha.setup_new_lights.poll()
    assert not any(g.get('_gacha_lights_plus_version') for g in bpy.data.node_groups)
    from setup_wizard.ui.character_settings_utils import resolve_settings_armature, is_game_armature
    arm = bpy.data.objects.new('Selection Test Character', bpy.data.armatures.new('Selection Test'))
    arm['gacha_game'] = 'GENSHIN_IMPACT'
    bpy.context.scene.collection.objects.link(arm)
    light = bpy.data.objects.new('Selection Test Light', bpy.data.lights.new('Selection Test', 'POINT'))
    bpy.context.scene.collection.objects.link(light)
    light.parent = arm
    bpy.context.view_layer.objects.active = light
    assert resolve_settings_armature(bpy.context) is None
    assert not is_game_armature(bpy.context, 'GENSHIN_IMPACT')
    print('PASS: Lights+ hidden and asset not loaded outside Blender 5.3', flush=True)
    raise SystemExit(0)

for obj in list(bpy.data.objects): bpy.data.objects.remove(obj, do_unlink=True)

def material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m

def mesh(name, arm, mat, data=None):
    data = data or bpy.data.meshes.new(name)
    if not data.vertices:
        data.from_pydata([(0, 0, 0), (1, 0, 0), (0, 0, 1)], [], [(0, 1, 2)])
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = arm
    if not obj.material_slots: obj.data.materials.append(mat)
    return obj

def geo_group(name):
    tree = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    for direction in ('INPUT', 'OUTPUT'):
        tree.interface.new_socket(name='Geometry', in_out=direction, socket_type='NodeSocketGeometry')
    inp = tree.nodes.new('NodeGroupInput'); out = tree.nodes.new('NodeGroupOutput')
    tree.links.new(inp.outputs['Geometry'], out.inputs['Geometry'])
    return tree

arm_a = bpy.data.objects.new('Character A', bpy.data.armatures.new('A'))
arm_b = bpy.data.objects.new('Character B', bpy.data.armatures.new('B'))
for arm in (arm_a, arm_b): bpy.context.scene.collection.objects.link(arm)
body, outline, embedded, input_material = [material(n) for n in ('Body', 'Outline', 'Embedded Outline', 'Input Material')]
a = mesh('Body A', arm_a, body)
b = mesh('Body B Linked Mesh', arm_b, body, a.data)
external = mesh('Clothing A', None, material('Clothing'))
modifier = external.modifiers.new('Armature', 'ARMATURE'); modifier.object = arm_a
curve = bpy.data.curves.new('Curve', 'CURVE')
curve_obj = bpy.data.objects.new('Curve A', curve); curve_obj.parent = arm_a
bpy.context.scene.collection.objects.link(curve_obj); curve.materials.append(material('Curve Material'))

# Shared geometry groups, modifier socket overrides, nested Set Material,
# material input node properties, and interface defaults all need isolation.
inner = geo_group('Shared Inner Geometry')
set_material = inner.nodes.new('GeometryNodeSetMaterial')
set_material.inputs['Material'].default_value = embedded
material_node = inner.nodes.new('GeometryNodeInputMaterial'); material_node.material = input_material
outer = geo_group('Shared Outline Geometry')
socket = outer.interface.new_socket(name='Outline', in_out='INPUT', socket_type='NodeSocketMaterial')
socket.default_value = outline
child = outer.nodes.new('GeometryNodeGroup'); child.node_tree = inner
for obj in (a, b):
    mod = obj.modifiers.new('Outlines', 'NODES'); mod.node_group = outer
    set_modifier_property(mod, socket.identifier, outline)
bpy.context.view_layer.objects.active = a
a.select_set(True)
assert bpy.ops.gacha.setup_new_lights('EXEC_DEFAULT') == {'FINISHED'}
assert a.data == b.data and a.material_slots[0].material != b.material_slots[0].material
assert b.material_slots[0].material == body
assert b.modifiers['Outlines'].node_group == outer
assert a.modifiers['Outlines'].node_group != outer
for m in (body, outline, embedded, input_material):
    assert not any(n.get(TAG) for n in m.node_tree.nodes), ('Other character changed', m.name)
owned = {m for obj in character_objects(arm_a) for m in object_materials(obj)}
assert len(owned) == 6, [m.name for m in owned]
for m in owned:
    output = next(n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL')
    node = output.inputs['Surface'].links[0].from_node
    assert node.get(TAG), m.name
    assert node.inputs['Shader'].links[0].is_valid
    assert node.inputs['Shader'].links[0].from_node.type == 'BSDF_PRINCIPLED'
    group = node.node_tree
    assert all(l.is_valid for l in group.links)
    switch = next(n for n in group.nodes if n.bl_idname == 'GeometryNodeIndexSwitch')
    assert switch.inputs[1].links[0].from_node.type == 'GROUP_INPUT', 'Default must preserve original shader'

for identifier, number in (('LIGHT_COLOR', 1), ('DIFFUSE', 2), ('DEFAULT', 0)):
    arm_a.gacha_lights_plus_mode = identifier
    bpy.context.view_layer.update()
    for m in owned:
        value = next(n for n in m.node_tree.nodes if n.get(TAG)).inputs['Index'].default_value
        assert value == number, (m.name, identifier, value, arm_a.get(MODE))
    assert arm_b.get(MODE, 0) == 0

# Re-run after adding a later shader operation: move Lights+ back to the end.
m = a.material_slots[0].material
output = next(n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL')
old = output.inputs['Surface'].links[0].from_node
later = m.node_tree.nodes.new('ShaderNodeMixShader')
m.node_tree.links.new(old.outputs['Shader'], later.inputs[1])
m.node_tree.links.new(later.outputs[0], output.inputs['Surface'])
assert needs_setup(arm_a), 'An effect placed after Lights+ needs setup again'
layout = Layout(); draw_lights_plus(layout, bpy.context)
assert layout.ops == ['gacha.setup_new_lights']
assert bpy.ops.gacha.setup_new_lights('EXEC_DEFAULT') == {'FINISHED'}
for mat in owned:
    assert sum(bool(n.get(TAG)) for n in mat.node_tree.nodes) == 1, mat.name
assert output.inputs['Surface'].links[0].from_node.inputs['Shader'].links[0].from_node == later
layout = Layout(); draw_lights_plus(layout, bpy.context)
assert layout.labels == ['Lights+'] and layout.ops == []
assert layout.props == [(arm_a, 'gacha_lights_plus_mode')]
assert layout.prop_labels == ['Mode']

extra = mesh('New Clothing A', arm_a, material('New Clothing'))
assert needs_setup(arm_a), 'New materials should make setup available again'
assert bpy.ops.gacha.setup_new_lights('EXEC_DEFAULT') == {'FINISHED'}
assert not needs_setup(arm_a)

from setup_wizard.ui.character_settings_utils import resolve_settings_armature, is_game_armature, GACHA_GAME_KEY
from setup_wizard.domain.game_types import GameType
light = bpy.data.objects.new('Selected Light', bpy.data.lights.new('Selected Light', 'POINT'))
bpy.context.scene.collection.objects.link(light)
light.parent = arm_a
# Keep the character selected too: the active light must still hide its panels.
for game in GameType:
    arm_a[GACHA_GAME_KEY] = game.name
    bpy.context.view_layer.objects.active = light
    assert resolve_settings_armature(bpy.context) is None
    assert not is_game_armature(bpy.context, game.name), game.name
    assert not bpy.ops.gacha.setup_new_lights.poll()
    layout = Layout(); draw_lights_plus(layout, bpy.context)
    assert not layout.labels
bpy.context.view_layer.objects.active = a
assert resolve_settings_armature(bpy.context) == arm_a
bpy.context.view_layer.objects.active = None
assert resolve_settings_armature(bpy.context) is None
bpy.context.view_layer.objects.active = a

# Genshin Highlights preserve their transparent shader and are not counted as
# missing setup. Previously wrapped highlights are restored on another setup.
highlight = material('HoYoverse - Genshin Test Highlight')
t = highlight.node_tree
mix = t.nodes.new('ShaderNodeMixShader'); mix.inputs[0].default_value = 0.25
transparent = t.nodes.new('ShaderNodeBsdfTransparent')
t.links.new(transparent.outputs[0], mix.inputs[1])
t.links.new(t.nodes['Principled BSDF'].outputs[0], mix.inputs[2])
out = t.nodes['Material Output']; t.links.new(mix.outputs[0], out.inputs['Surface'])
h_a = mesh('Highlight A', arm_a, highlight)
h_b = mesh('Highlight B', arm_b, highlight)
assert bpy.ops.gacha.setup_new_lights('EXEC_DEFAULT') == {'FINISHED'}
assert h_a.material_slots[0].material == h_b.material_slots[0].material == highlight
assert out.inputs['Surface'].links[0].from_node == mix
assert not any(n.get(TAG) for n in t.nodes)
assert not needs_setup(arm_a)
old = t.nodes.new('ShaderNodeGroup'); old.node_tree = group; old[TAG] = True
t.links.new(mix.outputs[0], old.inputs['Shader'])
t.links.new(old.outputs[0], out.inputs['Surface'])
assert needs_setup(arm_a)
assert bpy.ops.gacha.setup_new_lights('EXEC_DEFAULT') == {'FINISHED'}
local = h_a.material_slots[0].material
assert local != highlight and h_b.material_slots[0].material == highlight
assert not any(n.get(TAG) for n in local.node_tree.nodes)
assert local.node_tree.nodes['Material Output'].inputs['Surface'].links[0].from_node.type == 'MIX_SHADER'
assert out.inputs['Surface'].links[0].from_node == old, 'Do not alter the other character'
assert not needs_setup(arm_a)
renamed = material('HoYoverse - Example Highlight')
arm_a[GACHA_GAME_KEY] = 'GENSHIN_IMPACT'
from setup_wizard.ui.character_settings_utils import invalidate_caches
invalidate_caches()
assert is_genshin_highlight(renamed, arm_a)
arm_b[GACHA_GAME_KEY] = 'HONKAI_STAR_RAIL'
other = material('HSR - Highlight'); mesh('HSR Highlight', arm_b, other)
bpy.context.view_layer.objects.active = arm_b
assert bpy.ops.gacha.setup_new_lights('EXEC_DEFAULT') == {'FINISHED'}
assert any(n.get(TAG) for n in other.node_tree.nodes), 'Other games still get Lights+'
bpy.context.view_layer.objects.active = a

save = Path(tempfile.mkdtemp(prefix='codex-new-lights-')) / 'lights-test.blend'
arm_a.gacha_lights_plus_mode = 'DIFFUSE'
bpy.ops.wm.save_as_mainfile(filepath=str(save))
bpy.ops.wm.open_mainfile(filepath=str(save))
arm_a = bpy.data.objects['Character A']
bpy.context.view_layer.update()
for obj in character_objects(arm_a):
    for mat in object_materials(obj):
        if is_genshin_highlight(mat, arm_a):
            assert not any(n.get(TAG) for n in mat.node_tree.nodes)
            continue
        assert next(n for n in mat.node_tree.nodes if n.get(TAG)).inputs['Index'].default_value == 2
print('PASS: full character coverage, nested modifier materials, shared isolation, three modes, valid shader links, idempotency and save/reopen', flush=True)

# ColorWheel names can belong to the material, its shader group, or just the
# object. Restore older wrappers without removing Lights+ from shared body skin.
arm_b = bpy.data.objects['Character B']
from setup_wizard.utilites.new_lights import light_group
group = light_group()
bpy.context.view_layer.objects.active = arm_a
named = material('Color-Wheel-Ambient')
wheel_named = mesh('Lighting display', arm_a, named)
generic = material('Generic shared display')
body_shared = mesh('Shared body skin', arm_a, generic)
assert bpy.ops.gacha.setup_new_lights('EXEC_DEFAULT') == {'FINISHED'}
wrapped = body_shared.material_slots[0].material
assert any(n.get(TAG) for n in wrapped.node_tree.nodes)
wheel_a = mesh('ColorWheel-Lit.001', arm_a, wrapped)
wheel_b = mesh('Color_Wheel-Lit', arm_b, wrapped)
grouped = material('Renamed display material')
wheel_group = bpy.data.node_groups.new('Color Wheel Shader', 'ShaderNodeTree')
grouped.node_tree.nodes.new('ShaderNodeGroup').node_tree = wheel_group
wheel_by_group = mesh('Renamed lighting display', arm_a, grouped)

# Simulate an earlier setup on a named wheel material.
t = named.node_tree
out = t.nodes['Material Output']
old = t.nodes.new('ShaderNodeGroup'); old.node_tree = group; old[TAG] = True
t.links.new(t.nodes['Principled BSDF'].outputs[0], old.inputs['Shader'])
t.links.new(old.outputs[0], out.inputs['Surface'])
assert needs_setup(arm_a)
assert bpy.ops.gacha.setup_new_lights('EXEC_DEFAULT') == {'FINISHED'}
for wheel in (wheel_named, wheel_a, wheel_by_group):
    mat = wheel.material_slots[0].material
    assert not any(n.get(TAG) for n in mat.node_tree.nodes), wheel.name
    assert mat.node_tree.nodes['Material Output'].inputs['Surface'].links[0].from_node.type == 'BSDF_PRINCIPLED'
assert wheel_a.material_slots[0].material != body_shared.material_slots[0].material
assert any(n.get(TAG) for n in body_shared.material_slots[0].material.node_tree.nodes)
assert any(n.get(TAG) for n in wheel_b.material_slots[0].material.node_tree.nodes), 'Other character changed'
assert not needs_setup(arm_a), 'Excluded wheels must not keep the setup button visible'
for mode in ('DEFAULT', 'LIGHT_COLOR', 'DIFFUSE'):
    arm_a.gacha_lights_plus_mode = mode
    assert all(not any(n.get(TAG) for n in wheel.material_slots[0].material.node_tree.nodes)
               for wheel in (wheel_named, wheel_a, wheel_by_group))
assert bpy.ops.gacha.setup_new_lights('EXEC_DEFAULT') == {'FINISHED'}
assert not needs_setup(arm_a)
print('PASS: ColorWheel materials, groups and objects stay unchanged across all modes; old wrappers restored; shared body materials and other characters isolated', flush=True)
