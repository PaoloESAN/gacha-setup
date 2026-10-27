"""Exercise the bundled V2 through the full isolated Alice setup (Blender 5.2+)."""
import importlib
import json
from pathlib import Path
import runpy
import sys
import zipfile

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
legacy = '--legacy' in sys.argv
runtime = ROOT / 'tests/.runtime/zzz-kythera-v2' / ('legacy' if legacy else 'toon')
runtime.mkdir(parents=True, exist_ok=True)
original_resource = bpy.utils.user_resource
def resource(kind, path='', create=False):
    if kind in {'CONFIG', 'SCRIPTS'}:
        destination = runtime / kind / path
        destination.mkdir(parents=True, exist_ok=True)
        return str(destination)
    return original_resource(kind, path=path, create=create)
bpy.utils.user_resource = resource
sys.path.insert(0, str(ROOT))
dependencies = runtime / 'dependencies'
with zipfile.ZipFile(ROOT / 'setup_wizard/dependencies/retarget.zip') as archive:
    archive.extractall(dependencies)
package = min(dependencies.rglob('__init__.py'), key=lambda p: len(p.parts)).parent
sys.path.insert(0, str(package.parent))
importlib.import_module(package.name)
model = ROOT / 'chars/zzz/alice-celestian-etiquette/Avatar_Female_Size02_Alice_UI.fbx'
job = {'game_type': 'ZENLESS_ZONE_ZERO', 'zzz_shader_type': 'LEGACY' if legacy else 'KYTHERA', 'disable_rigging': False,
       'character_directory': str(model.parent), 'selected_model_file': str(model),
       'gacha_module': 'setup_wizard', 'gacha_addon_parent': str(ROOT),
       'status_path': str(runtime / 'status.json'), 'result_path': str(runtime / 'Alice.blend')}
(runtime / 'job.json').write_text(json.dumps(job), encoding='utf-8')
sys.argv = [sys.argv[0], '--', str(runtime / 'job.json')]
try:
    runpy.run_path(str(ROOT / 'setup_wizard/services/isolation/isolated_runner.py'), run_name='__main__')
except SystemExit as error:
    if error.code not in (None, 0):
        raise
assert json.loads((runtime / 'status.json').read_text(encoding='utf-8'))['state'] == 'SUCCESS'
from setup_wizard.utils.zzz_kythera_lighting import setup_kythera_lighting, _face_material
from setup_wizard.import_order import get_shader_file_path
if legacy:
    assert Path(get_shader_file_path('ZENLESS_ZONE_ZERO')).name == 'ZZZ Setup v7.blend'
    assert not setup_kythera_lighting(bpy.context)
    assert any(mod.type == 'NODES' and mod.name.startswith('Light Vectors')
               for obj in bpy.context.scene.objects if obj.type == 'MESH' for mod in obj.modifiers)
    print('ZZZ_LEGACY_LIGHTING_PASS', flush=True)
    raise SystemExit(0)
assert Path(get_shader_file_path('ZENLESS_ZONE_ZERO')).name == "Kythera's ZZZ Shader V2.blend"
for name in ('ZZZ Shader Eye', "Kythera's ZZZ Eye Highlights"):
    assert bpy.data.materials.get(name), name
rig = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE' and obj.data.get('rig_id'))
face = next(obj for obj in bpy.context.scene.objects if obj.type == 'MESH'
            and obj.find_armature() == rig and any(_face_material(slot.material) for slot in obj.material_slots))
modifier = next(mod for mod in face.modifiers if mod.type == 'NODES' and mod.node_group
                and mod.node_group.get('zzz_kythera_vectors'))
highlight = bpy.data.materials["Kythera's ZZZ Eye Highlights"]
assert any(face.data.materials[polygon.material_index] == highlight for polygon in face.data.polygons), 'Toon must assign Kythera highlights'
assert not any(face.data.materials[polygon.material_index]
               and face.data.materials[polygon.material_index].name.startswith('ZZZ Shader EyeHighlights')
               for polygon in face.data.polygons), 'Legacy highlights assigned to Toon'

tree = modifier.node_group
sun = tree.nodes['Object Info'].inputs['Object'].default_value
basis = tree.nodes['Object Info.001'].inputs['Object'].default_value
assert sun.type == 'LIGHT' and sun.data.type == 'SUN' and not sun.hide_render
assert sun.data.energy > 0
assert face in list(sun.light_linking.receiver_collection.all_objects), 'Final Sun receiver collection is empty'
assert basis.constraints['Kythera Head Follow'].target == rig
assert len(sun.users_collection) == 1 and sun.users_collection[0] in rig.users_collection
assert len(basis.users_collection) == 1 and basis.users_collection[0].name.startswith('WGTS')
assert basis.users_collection[0] in list(sun.users_collection[0].children)
assert [obj for obj in bpy.context.scene.objects if obj.type == 'LIGHT' and obj.data.type == 'SUN'] == [sun], 'Duplicate Sun in scene'
assert not any(obj.type == 'EMPTY' and 'light direction' in obj.name.lower()
               for obj in bpy.context.scene.objects), 'Legacy direction control in Toon scene'
from setup_wizard.utils.modifier_utils import get_modifier_property
panel_vectors = next(mod for mod in face.modifiers if mod.type == 'NODES' and mod.name.startswith('Light Vectors'))
direction_key = next(item.identifier for item in panel_vectors.node_group.interface.items_tree
                     if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.name == 'Light Direction')
assert get_modifier_property(panel_vectors, direction_key) == sun

# The outline group returns instances. Realize only in this test so evaluated
# mesh attributes include the actual geometry used by the renderer.
realize_tree = bpy.data.node_groups.new('Test Realize Face Instances', 'GeometryNodeTree')
realize_tree.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
realize_tree.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
input_node = realize_tree.nodes.new('NodeGroupInput')
output_node = realize_tree.nodes.new('NodeGroupOutput')
realize = realize_tree.nodes.new('GeometryNodeRealizeInstances')
realize_tree.links.new(input_node.outputs['Geometry'], realize.inputs['Geometry'])
realize_tree.links.new(realize.outputs['Geometry'], output_node.inputs['Geometry'])
face.modifiers.new('Test Realize Instances', 'NODES').node_group = realize_tree

def attributes():
    face.update_tag()
    rig.update_tag()
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = face.evaluated_get(graph)
    ambient = evaluated.data.attributes.get('Ambient')
    assert ambient is not None and sum(ambient.data[0].color[:3]) > 0, 'Panel color attributes are missing'
    return {name: Vector(evaluated.data.attributes[name].data[0].vector) for name in ('SUN', 'RIGHT', 'FRONT')}

before = attributes()
assert all(abs(vector.length - 1) < 1e-4 for vector in before.values()), before
expected = sun.matrix_world.to_quaternion() @ Vector((0, 0, 1))
assert (before['SUN'] - expected).length < 1e-4, (before['SUN'], expected)
old_rotation = sun.rotation_euler.copy()
sun.rotation_euler.z += .5
sun.update_tag()
turned_sun = attributes()
assert (turned_sun['SUN'] - before['SUN']).length > .1
assert (turned_sun['FRONT'] - before['FRONT']).length < 1e-5
sun.rotation_euler = old_rotation
sun.update_tag()
attributes()
head = rig.pose.bones[basis.constraints['Kythera Head Follow'].subtarget]
old_mode = head.rotation_mode
head.rotation_mode = 'XYZ'
old_rotation = head.rotation_euler.copy()
head.rotation_euler.y += .3
turned_head = attributes()
assert (turned_head['FRONT'] - before['FRONT']).length > .05
assert (turned_head['SUN'] - before['SUN']).length < 1e-5
head.rotation_euler = old_rotation
head.rotation_mode = old_mode
attributes()
assert setup_kythera_lighting(bpy.context, rig) == [sun]
assert setup_kythera_lighting(bpy.context, rig) == [sun]

# A duplicate character must not reuse the first character's light or basis.
other_rig = rig.copy()
other_rig.data = rig.data.copy()
bpy.context.scene.collection.objects.link(other_rig)
other_face = face.copy()
other_face.data = face.data.copy()
bpy.context.scene.collection.objects.link(other_face)
other_face.parent = other_rig
for mod in other_face.modifiers:
    if mod.type == 'ARMATURE':
        mod.object = other_rig
other_sun = setup_kythera_lighting(bpy.context, other_rig)[0]
assert other_sun != sun and other_sun.data != sun.data
assert other_face not in list(sun.light_linking.receiver_collection.objects)
assert face not in list(other_sun.light_linking.receiver_collection.objects)
assert tree.nodes['Object Info'].inputs['Object'].default_value == sun
print('ZZZ_KYTHERA_V2_PASS', rig.name, sun.name, 'SUN/RIGHT/FRONT respond independently', flush=True)
