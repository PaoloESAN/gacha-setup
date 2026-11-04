"""HSR hair cleanup must preserve the authored outline-width mask.

blender --background --factory-startup --python-exit-code 1 \
    --python tests/hsr_hair_outline_alpha_blender.py
Optional: -- Stelle-setup.blend Robin-setup.blend (in fixture order).
"""
from collections import Counter
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'tests/.runtime/hsr-hair-alpha'
original_resource = bpy.utils.user_resource


def resource(kind, path='', create=False):
    if kind in {'CONFIG', 'SCRIPTS'}:
        destination = RUNTIME / kind / path
        destination.mkdir(parents=True, exist_ok=True)
        return str(destination)
    return original_resource(kind, path=path, create=create)


bpy.utils.user_resource = resource
sys.path.insert(0, str(ROOT))
from setup_wizard.geometry_nodes_setup.geometry_nodes_setups import HonkaiStarRailGeometryNodesSetup

setup = HonkaiStarRailGeometryNodesSetup.__new__(HonkaiStarRailGeometryNodesSetup)
results = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
fixtures = [
    ROOT / 'chars/hsr/Trailblazer (Stelle) - Elation/Trailblazer (Stelle) - Elation.fbx',
    ROOT / 'chars/hsr/robin-summeretto-remembrance/Art_RobinS_00.fbx',
]


def alpha_counts(obj):
    layer = obj.data.color_attributes.get('Col') or obj.data.color_attributes[0]
    return Counter(round(element.color[3], 6) for element in layer.data)


for index, model in enumerate(fixtures):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.wm.fbx_import(filepath=str(model))
    hair = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and 'hair' in o.name.lower())
    layer = hair.data.color_attributes[0]
    layer.name = 'Col'
    expected = alpha_counts(hair)
    assert len(expected) > 5 and expected.get(0), 'Fixture needs variable widths and suppressed outlines'
    bpy.ops.object.select_all(action='DESELECT')
    hair.select_set(True)
    bpy.context.view_layer.objects.active = hair
    for repeat in range(2):
        setup.apply_hsr_hair_cleanup_and_vertex_paint()
        actual = alpha_counts(hair)
        # Welding Robin's degenerate triangles removes six corners. It may
        # remove samples, but must never replace widths on surviving corners.
        assert not (actual - expected), (model.name, repeat, expected, actual)
        assert sum(expected.values()) - sum(actual.values()) <= 6
        if model == fixtures[0] or repeat:
            assert actual == expected, (model.name, repeat)
        expected = actual
    if results:
        bpy.ops.wm.open_mainfile(filepath=str(Path(results[index]).resolve()))
        assert alpha_counts(bpy.data.objects['Hair']) == expected, model.name
    print('HSR_HAIR_AUTHORED_ALPHA_PASS', model.name, flush=True)

# POINT colors and distinct corner alpha values on a shared position must also
# survive RGB cleanup, including the upper region restored from the position map.
for domain in ('POINT', 'CORNER'):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    mesh = bpy.data.meshes.new('Hair')
    mesh.from_pydata([(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)], [], [(0, 1, 2), (0, 2, 3)])
    hair = bpy.data.objects.new('Hair', mesh)
    bpy.context.scene.collection.objects.link(hair)
    hair.select_set(True)
    bpy.context.view_layer.objects.active = hair
    layer = mesh.color_attributes.new(name='Col', type='FLOAT_COLOR', domain=domain)
    for index, element in enumerate(layer.data):
        element.color = (.2, .3, .4, (index + 1) / 10)
    expected = alpha_counts(hair)
    setup.apply_hsr_hair_cleanup_and_vertex_paint()
    assert alpha_counts(hair) == expected, domain
    layer = hair.data.color_attributes['Col']
    assert any(all(abs(e.color[i] - 1) < 1e-6 for i in range(3)) for e in layer.data), 'RGB cleanup did not run'
    print('HSR_HAIR_ALPHA_DOMAIN_PASS', domain, flush=True)
