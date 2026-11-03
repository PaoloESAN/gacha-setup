"""Real VMD integration: one prepared character per supported game (Blender 5+).

Set GACHA_TEST_MMD_DIR to an installed mmd_tools package when needed.
Optional arguments: -- GAME [--save-blend]. Outputs tests/.runtime/vmd-games.
"""
import json
import math
import os
from pathlib import Path
import sys
import zipfile

import addon_utils
import bpy


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'tests/.runtime'
sys.path.insert(0, str(ROOT))
if os.environ.get('GACHA_TEST_MMD_DIR'):
    mmd = Path(os.environ['GACHA_TEST_MMD_DIR'])
    sys.path.insert(0, str(mmd.parent))
    wheels = RUNTIME / 'wheels'
    for wheel in (mmd / 'wheels').glob('*.whl'):
        with zipfile.ZipFile(wheel) as archive:
            archive.extractall(wheels)
    sys.path.insert(0, str(wheels))
    addon_utils.enable('mmd_tools', default_set=False)
os.environ['GACHA_SETUP_ISOLATED_WORKER'] = '1'
addon_utils.enable('setup_wizard', default_set=False)
from setup_wizard.utilites.vmd_motion import apply_vmd, bone_map, mmd_modules
from setup_wizard.utils.optional_addons import temporary_addon

CHARACTERS = {
    'genshin': RUNTIME / 'genshin-metarig/Amber.blend',
    'zzz': RUNTIME / 'zzz-kythera-v2/Alice.blend',
    'ake': ROOT / 'output/ake-endministrator-male/Endministrator Male.blend',
    **{game: RUNTIME / f'finger-ik/5.2.3/{game}/character.blend'
       for game in ('hsr', 'wuwa', 'nte', 'pgr', 'hi3', 'hna')},
}


def curves(action):
    return [c for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags for c in bag.fcurves]


def check(game, source, save=False, body_only=False):
    assert source.is_file(), f'Prepare a {game} rig first: {source}'
    bpy.ops.wm.open_mainfile(filepath=str(source))
    rig = next(o for o in bpy.context.scene.objects
               if o.type == 'ARMATURE' and 'upper_arm_fk.L' in o.pose.bones)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    motion = Path(os.environ.get('GACHA_TEST_VMD', ROOT / 'chars/vmdmotion/Motion & Facials.vmd'))
    with temporary_addon('mmd_tools'):
        vmd, _ = mmd_modules()
        tracks = vmd.File()
        tracks.load(filepath=str(motion))
        mapping = bone_map(rig, tracks.boneAnimation)
    # These tracks must drive the visible character, including WuWa's chest.
    for jp in ('センター', '下半身', '上半身', '上半身2', '頭', '左腕', '右腕'):
        if jp in tracks.boneAnimation:
            assert jp in mapping, (game, jp, 'missing body mapping')
    for bone in rig.pose.bones:
        if 'FK_IK' in bone and '_ik.' in bone.name:
            bone['FK_IK'] = 1.0
    counts = apply_vmd(bpy.context, rig, str(motion), start=11, facial=not body_only)
    assert counts[0] >= 20, counts
    action = rig.animation_data.action
    assert action and len(curves(action)) > 100
    for bone in mapping.values():
        if bone.name.startswith(('thumb.', 'f_index.', 'f_middle.', 'f_ring.', 'f_pinky.')):
            finger = bone.name.split('.')[0]
            control = rig.pose.bones.get(f'{finger}.01_ik.{bone.name[-1]}')
            if control and 'FK_IK' in control:
                assert control['FK_IK'] == 0.0, (game, control.name)
    assert min(p.co.x for c in curves(action) for p in c.keyframe_points) == 11
    if 'グルーブ' in tracks.boneAnimation and 'センター' in mapping:
        with temporary_addon('mmd_tools'):
            _, importer = mmd_modules()
            torso = mapping['センター']
            converter = importer.BoneConverter(torso, .08)
            first_center = min(tracks.boneAnimation['センター'], key=lambda f: f.frame_number)
            first_groove = min(tracks.boneAnimation['グルーブ'], key=lambda f: f.frame_number)
            assert first_center.frame_number == first_groove.frame_number == 0
            expected = (converter.convert_location(first_center.location)
                        + converter.convert_rotation(first_center.rotation) @ converter.convert_location(first_groove.location))
            channels = {c.array_index: c for c in curves(action) if c.data_path == torso.path_from_id('location')}
            assert all(abs(channels[i].evaluate(11)-expected[i]) < 1e-5 for i in range(3))
    samples = []
    # Verify evaluated deformation bones, not just keys on unused controls.
    names = ['DEF-upper_arm.L', 'DEF-upper_arm.R', 'DEF-thigh.L',
             'DEF-thigh.R', 'DEF-spine.001', 'DEF-spine.006', 'DEF-Spine', 'DEF-head']
    names = [n for n in names if n in rig.pose.bones]
    assert len(names) >= 4, (game, names)
    for frame in (11, 41, 101, 201):
        bpy.context.scene.frame_set(frame)
        evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
        pose = {n: tuple(v for row in evaluated.pose.bones[n].matrix for v in row) for n in names}
        assert all(math.isfinite(v) for values in pose.values() for v in values)
        samples.append(pose)
    for name in names:
        assert any(max(abs(a-b) for a, b in zip(samples[0][name], s[name])) > 1e-4
                   for s in samples[1:]), (game, name, 'deformation does not move')
    body_paths = {b.path_from_id(prop) for b in mapping.values()
                  for prop in ('location', 'rotation_quaternion', 'rotation_euler')}
    body = {(c.data_path, c.array_index): [tuple(p.co) for p in c.keyframe_points]
            for c in curves(action) if c.data_path in body_paths}
    fps = bpy.context.scene.render.fps
    has_face = any(o.type == 'MESH' and o.find_armature() == rig and o.data.shape_keys
                   for o in bpy.context.scene.objects)
    face_counts = None
    if has_face and not body_only:
        face_counts = apply_vmd(bpy.context, rig, str(ROOT / 'chars/vmdmotion/FACIAL_Hiasobi.vmd'),
                                start=11, face_only=True)
        assert face_counts[0] == 0 and face_counts[1] > 0, face_counts
    after = {(c.data_path, c.array_index): [tuple(p.co) for p in c.keyframe_points]
             for c in curves(rig.animation_data.action) if (c.data_path, c.array_index) in body}
    assert body == after, 'Facial overlay changed body animation'
    assert bpy.context.scene.render.fps == fps
    report = dict(game=game, source=str(source), rig=rig.name, body=counts,
                  face=face_counts, deformation_bones=names, result='PASS')
    dest = RUNTIME / 'vmd-games'
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f'{game}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if save:
        bpy.ops.wm.save_as_mainfile(filepath=str(dest / f'{game}.blend'))
    print('VMD_GAME_PASS', json.dumps(report), flush=True)


args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
games = [a for a in args if not a.startswith('--')] or list(CHARACTERS)
for game in games:
    check(game, CHARACTERS[game], '--save-blend' in args, '--body-only' in args)
