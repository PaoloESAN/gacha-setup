"""Exercise automatic shoulders on real rigs from all supported games.

Optional: -- <GAME> <rig.blend> [--require-generated]. Without arguments,
uses the prepared local regression fixtures and writes a combined report.
"""
import json
import os
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['PYTEST_VERSION'] = 'automatic shoulders across games'
from setup_wizard.utils.auto_shoulders import setup_auto_shoulders, has_auto_shoulders

FIXTURES = {
    'genshin': ROOT / 'tests/.runtime/goo-eye-characters/Furina-Default/Furina-Default.blend',
    'zzz': ROOT / 'tests/.runtime/zzz-compat-setups/lindverne-legacy-panel/character.blend',
    'ake': ROOT / 'tests/.runtime/ake-endministrator-chest/before.blend',
    **{game: ROOT / f'tests/.runtime/finger-ik/5.2.3/{game}/character.blend'
       for game in ('hsr', 'pgr', 'hi3', 'hna', 'nte', 'wuwa')},
}


def check(game, path, require_generated=False):
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
    rig = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE' and obj.data.get('rig_id'))
    plate = rig.pose.bones['plate-settings']
    hands = {side: next(name for name in ('hand-ik-' + side, 'hand_ik.' + side)
                        if name in rig.pose.bones) for side in ('L', 'R')}
    for side in ('L', 'R'):
        rig.pose.bones[hands[side]].matrix_basis.identity()
    rig.update_tag(); bpy.context.view_layer.update()
    rest = {side: rig.pose.bones['shoulder.' + side].matrix.copy() for side in ('L', 'R')}
    deform = {bone.name: bone.matrix_local.copy() for bone in rig.data.bones if bone.use_deform}
    existed = has_auto_shoulders(rig)
    active, selected = bpy.context.view_layer.objects.active, set(bpy.context.selected_objects)
    if require_generated:
        assert existed, (game, 'Generated rig is missing Auto Shoulder')
        assert any(rig.data['rig_id'] in text.as_string() and 'Auto Shoulder Constraints' in text.as_string()
                   for text in bpy.data.texts), (game, 'Missing setting in Rig UI')
    else:
        assert setup_auto_shoulders(rig), (game, 'Unsupported shoulder rig')
    assert has_auto_shoulders(rig)
    assert bpy.context.view_layer.objects.active == active and set(bpy.context.selected_objects) == selected
    for side in ('L', 'R'):
        for bname in ('shoulder_driver.' + side, 'MCH-shoulder_follow.' + side, 'MCH-shoulder_hand.' + side):
            b = rig.data.bones.get(bname)
            if b:
                if hasattr(rig.data, 'collections'):
                    assert [c.name for c in b.collections] == ['Other'], (game, bname, [c.name for c in b.collections])
                else:
                    assert b.layers[25], (game, bname, 'Not on layer 25')
    for name, matrix in deform.items():
        assert max(abs(rig.data.bones[name].matrix_local[i][j] - matrix[i][j])
                   for i in range(4) for j in range(4)) < 2e-6, (game, 'Deform rest changed', name)
    if rig.animation_data:
        for curve in rig.animation_data.drivers:
            if 'MCH-shoulder_hand.' in curve.data_path:
                for variable in curve.driver.variables:
                    for target in variable.targets:
                        target.id.path_resolve(target.data_path)
    plate['Toggle Shoulder Constraints'] = 1.0
    rig.update_tag(); bpy.context.view_layer.update()
    angles = {}
    for side in ('L', 'R'):
        shoulder = rig.pose.bones['shoulder.' + side]
        follow = rig.pose.bones['MCH-shoulder_follow.' + side]
        track = next(c for c in follow.constraints if c.type == 'DAMPED_TRACK')
        assert abs(track.influence - .4) < 1e-6
        assert rest[side].to_quaternion().rotation_difference(shoulder.matrix.to_quaternion()).angle < 1e-3, (game, side, 'Neutral pose changed')
        hand = rig.pose.bones[hands[side]]
        original = hand.matrix.copy()
        distance = max((original.translation - shoulder.matrix.translation).length * .8, .05)
        moved = original.copy(); moved.translation += Vector((0, 0, distance))
        hand.matrix = moved
        rig.update_tag(); bpy.context.view_layer.update()
        angle = rest[side].to_quaternion().rotation_difference(shoulder.matrix.to_quaternion()).angle
        assert .02 < angle < 1.1, (game, side, 'Shoulder did not follow', angle)
        plate['Toggle Shoulder Constraints'] = 0.0
        rig.update_tag(); bpy.context.view_layer.update()
        assert track.influence == 0
        assert rest[side].to_quaternion().rotation_difference(shoulder.matrix.to_quaternion()).angle < 1e-3, (game, side, 'Disable failed')
        plate['Toggle Shoulder Constraints'] = .5
        rig.update_tag(); bpy.context.view_layer.update()
        assert abs(track.influence - .2) < 1e-6
        hand.matrix = original
        plate['Toggle Shoulder Constraints'] = 1.0
        rig.update_tag(); bpy.context.view_layer.update()
        assert rest[side].to_quaternion().rotation_difference(shoulder.matrix.to_quaternion()).angle < 1e-3
        angles[side] = angle
    counts = len(rig.data.bones), sum(len(b.constraints) for b in rig.pose.bones)
    assert setup_auto_shoulders(rig)
    assert counts == (len(rig.data.bones), sum(len(b.constraints) for b in rig.pose.bones))
    print('AUTO_SHOULDERS_GAME_PASS', game, rig.name, angles, flush=True)
    return {'game': game, 'rig': rig.name, 'source': str(path), 'already_present': existed, 'angles': angles}


args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if args:
    results = [check(args[0], Path(args[1]), '--require-generated' in args)]
else:
    results = [check(game, path) for game, path in FIXTURES.items()]
# Special/non-humanoid rigs must remain valid without fabricated shoulders.
empty = bpy.data.objects.new('No shoulder rig', bpy.data.armatures.new('No shoulder data'))
bpy.context.scene.collection.objects.link(empty)
assert setup_auto_shoulders(empty) is False and len(empty.data.bones) == 0
out = ROOT / 'tests/.runtime/auto-shoulders'
out.mkdir(parents=True, exist_ok=True)
(out / ('report-' + bpy.app.version_string.replace(' ', '-') + ('-' + args[0] if args else '') + '.json')).write_text(
    json.dumps({'version': bpy.app.version_string, 'results': results}, indent=2), encoding='utf-8')
print('AUTO_SHOULDERS_ALL_PASS', bpy.app.version_string, len(results), flush=True)
