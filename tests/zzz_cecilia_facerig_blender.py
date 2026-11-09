"""Blender -b --factory-startup --python-exit-code 1 --python this_file -- Cecilia.blend."""
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
original_resource = bpy.utils.user_resource


def resource(kind, path='', create=False):
    if kind in {'CONFIG', 'SCRIPTS'}:
        target = ROOT / 'tests/.runtime/cecilia-facerig' / kind / path
        target.mkdir(parents=True, exist_ok=True)
        return str(target)
    return original_resource(kind, path=path, create=create)


bpy.utils.user_resource = resource
import addon_utils
addon_utils.enable('setup_wizard', default_set=False)
from setup_wizard.character_rig_setup.zzz_face_rig import zzz_face_rig_main, shapekeyrename

temporary = bpy.data.objects.new('Facial naming regression', bpy.data.meshes.new('Facial naming regression'))
bpy.context.scene.collection.objects.link(temporary)
temporary.data.from_pydata([(0, 0, 0)], [], [])
for name in ('Basis', 'Fac_Mth_Ii', 'Fac_Mth_Ii_100', 'Fac_Mth_Ii_50', 'Body_100'):
    temporary.shape_key_add(name=name)
before_names = list(temporary.data.shape_keys.key_blocks.keys())
shapekeyrename(temporary.data.shape_keys.key_blocks)
assert list(temporary.data.shape_keys.key_blocks.keys()) == before_names
bpy.data.objects.remove(temporary, do_unlink=True)

path = Path(sys.argv[sys.argv.index('--') + 1])
bpy.ops.wm.open_mainfile(filepath=str(path.resolve()), use_scripts=False)
face = bpy.data.objects['Cecilia_Face']
rig = face.find_armature()
keys = face.data.shape_keys
assert len(keys.key_blocks) == 34
assert all(not key.name.endswith('_100') for key in keys.key_blocks)
# Inspect the skinned surface, excluding outline instances from the vertex test.
for mod in face.modifiers:
    if mod.type != 'ARMATURE':
        mod.show_viewport = False


def update():
    rig.update_tag()
    face.update_tag()
    bpy.context.view_layer.update()


def vertices():
    update()
    return [v.co.copy() for v in face.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]


def reset():
    for bone in rig.pose.bones:
        if bone.name.startswith('CTRL-') or bone.name.endswith(' Bone'):
            bone.location = (0, 0, 0)
    update()


def driver(key):
    return next(fc.driver for fc in keys.animation_data.drivers if fc.data_path == key.path_from_id('value'))


def verify():
    reset()
    neutral = vertices()
    tested = 0
    for key in list(keys.key_blocks)[1:]:
        drv = driver(key)
        panel = [v for v in drv.variables if v.name == 'var_pnl']
        controls = [v for v in drv.variables if v.targets[0].bone_target.startswith('CTRL-')]
        assert panel and controls, ('Missing panel or face control', key.name, drv.expression)
        assert all(v.targets[0].id == rig and v.targets[0].bone_target in rig.pose.bones
                   for v in [*panel, *controls])
        for variable in [*panel, *controls]:
            control = rig.pose.bones[variable.targets[0].bone_target]
            assert control.custom_shape and not control.bone.hide, control.name
        pb = rig.pose.bones[panel[0].targets[0].bone_target]
        pb.location.x = 0.2
        update()
        assert abs(key.value - 1.0) < 1e-5, ('Panel', key.name, key.value)
        after = vertices()
        raw_delta = max((v.co - b.co).length for v, b in zip(key.data, keys.key_blocks[0].data))
        if raw_delta > 1e-7:
            assert max((v-b).length for v, b in zip(after, neutral)) > 1e-7, key.name
        pb.location.x = 0
        update()
        moved = False
        for variable in controls:
            target = variable.targets[0]
            control = rig.pose.bones[target.bone_target]
            axis = 'XYZ'.index(target.transform_type[-1])
            limits = [abs(getattr(c, field)) for c in control.constraints if c.type == 'LIMIT_LOCATION'
                      for field in ('min_' + 'xyz'[axis], 'max_' + 'xyz'[axis])]
            amount = max(limits, default=0.01)
            for sign in (1, -1):
                control.location[axis] = sign * amount
                update()
                if key.value > 0.4:
                    moved = True
                    if key.name.startswith('Fac_Eye_'):
                        side = key.name.split('_')[2]
                        other = 'R' if side == 'L' else 'L'
                        assert all(k.value < 1e-5 for k in keys.key_blocks
                                   if k.name.startswith(f'Fac_Eye_{other}_')), key.name
                control.location[axis] = 0
                update()
                if moved:
                    break
            if moved:
                break
        assert moved, ('Face control does not drive expression', key.name, drv.expression)
        assert abs(key.value) < 1e-5
        tested += 1
    assert max((a-b).length for a, b in zip(vertices(), neutral)) < 1e-6
    print('CECILIA_FACE_AND_PANEL_PASS', tested, flush=True)


verify()
before_bones = set(rig.data.bones.keys())
for _ in range(2):
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    zzz_face_rig_main()
    assert set(rig.data.bones.keys()) == before_bones, 'Rebuild changed the rig bone set'
    verify()
filename = ROOT / 'tests/.runtime/cecilia-facerig/reload.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(filename))
bpy.ops.wm.open_mainfile(filepath=str(filename), use_scripts=False)
face = bpy.data.objects['Cecilia_Face']
rig = face.find_armature()
keys = face.data.shape_keys
verify()
