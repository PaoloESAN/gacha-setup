"""Compare full-setup Kinich pupil motion to Starriia - Kinich.blend."""
import json
from pathlib import Path
import sys

import bpy
from mathutils import kdtree

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'tests/.runtime/kinich-eyes'
RUNTIME.mkdir(parents=True, exist_ok=True)
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
path = Path(args[0]) if args else ROOT / 'output/Kinich.blend'
reference = ROOT / 'Starriia - Kinich.blend'
CASES = [('neutral', (0, 0, 0)), ('left', (-.05, 0, 0)),
         ('right', (.05, 0, 0)), ('up', (0, .05, 0)),
         ('down', (0, -.05, 0)), ('diagonal', (.05, .05, 0)),
         ('wide', (.15, 0, 0)), ('extreme', (.3, 0, 0))]


def capture(file):
    bpy.ops.wm.open_mainfile(filepath=str(file.resolve()))
    rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE' and o.data.get('rig_id'))
    sources = [o for o in bpy.context.scene.objects if o.type == 'MESH'
               and o.find_armature() == rig and 'star' not in o.name.casefold()
               and any(o.vertex_groups.get(f'+EyeBoneA02.{s}') for s in ('L', 'R'))]
    clones = []
    for source in sources:
        clone = source.copy()
        clone.animation_data_clear()
        clone.hide_viewport = False
        clone.hide_render = True
        bpy.context.scene.collection.objects.link(clone)
        clone.hide_set(False)
        for modifier in list(clone.modifiers):
            if modifier.type != 'ARMATURE':
                clone.modifiers.remove(modifier)
        indices = {}
        for side in ('L', 'R'):
            vg = clone.vertex_groups.get(f'+EyeBoneA02.{side}')
            indices[side] = [v.index for v in clone.data.vertices if vg and any(
                g.group == vg.index and g.weight > .5 for g in v.groups)]
        clones.append((clone, indices))

    def points():
        rig.update_tag()
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        result = {'L': [], 'R': []}
        for clone, indices in clones:
            evaluated = clone.evaluated_get(dg)
            for side, ids in indices.items():
                result[side].extend(clone.matrix_world @ evaluated.data.vertices[i].co for i in ids)
        assert all(len(p) > 50 for p in result.values())
        return result

    tracker = rig.pose.bones['eyetrack']
    result = {}
    for label, location in CASES:
        tracker.location = location
        result[label] = points()
    tracker.location = (0, 0, 0)
    neutral = result['neutral']
    restored = points()
    assert all(max((a-b).length for a, b in zip(restored[s], neutral[s])) < 1e-5 for s in neutral)
    individual = rig.pose.bones['eyetrack_L']
    individual.location.x = .05
    independent = points()
    assert max((a-b).length for a, b in zip(independent['L'], neutral['L'])) > 1e-4
    assert max((a-b).length for a, b in zip(independent['R'], neutral['R'])) < 1e-5
    individual.location.x = 0
    head = rig.pose.bones['head']
    head.rotation_mode = 'XYZ'
    head.rotation_euler.z = .3
    assert max((a-b).length for a, b in zip(points()['L'], neutral['L'])) > 1e-3
    head.rotation_euler.z = 0
    assert max((a-b).length for a, b in zip(points()['L'], neutral['L'])) < 1e-5
    pivots = {n: (rig.matrix_world @ rig.data.bones[n].head_local).copy()
              for n in ('+EyeBone L A01', '+EyeBone R A01', '+EyeBoneA02.L', '+EyeBoneA02.R')}
    assert not any(c.type == 'LIMIT_ROTATION' for side in ('L', 'R')
                   for c in rig.pose.bones[f'+EyeBone {side} A01.001'].constraints)
    return result, pivots


expected, reference_pivots = capture(reference)
actual, pivots = capture(path)
for name, pivot in pivots.items():
    tolerance = .003 if 'A01' in name else .00003
    assert (pivot - reference_pivots[name]).length < tolerance, (name, tuple(pivot), tuple(reference_pivots[name]))

errors = {}
for side in ('L', 'R'):
    tree = kdtree.KDTree(len(expected['neutral'][side]))
    for i, p in enumerate(expected['neutral'][side]):
        tree.insert(p, i)
    tree.balance()
    matches = [tree.find(p) for p in actual['neutral'][side]]
    assert max(distance for _, _, distance in matches) < .00003
    for label, _ in CASES:
        error = max((p - expected[label][side][i]).length
                    for p, (_, i, _) in zip(actual[label][side], matches))
        assert error < .004, (label, side, error)
        errors[f'{label}.{side}'] = error
report = {'file': str(path), 'reference': str(reference), 'max_vertex_errors': errors,
          'independent_eyes': True, 'head_follow': True, 'neutral_preserved': True, 'artificial_limits': False}
(RUNTIME / (path.stem + '-regression.json')).write_text(json.dumps(report, indent=2))
print('KINICH_REFERENCE_EYES_PASS', json.dumps(report), flush=True)
