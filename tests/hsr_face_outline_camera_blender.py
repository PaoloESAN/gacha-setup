"""Verify camera-independent HSR outlines on a completed character.

blender -b --factory-startup --python-exit-code 1 --python
tests/hsr_face_outline_camera_blender.py -- character.blend [--save]
"""
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
original_resource = bpy.utils.user_resource


def resource(kind, path='', create=False):
    if kind in {'CONFIG', 'SCRIPTS'}:
        destination = ROOT / 'tests/.runtime/hsr-outline-camera' / kind / path
        destination.mkdir(parents=True, exist_ok=True)
        return str(destination)
    return original_resource(kind, path=path, create=create)


bpy.utils.user_resource = resource
sys.path.insert(0, str(ROOT))
from setup_wizard.utils.hsr_face_outlines import configure_face_outlines
from setup_wizard.utils.modifier_utils import get_modifier_property

args = sys.argv[sys.argv.index('--') + 1:]
path = Path(args[0]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(path))
face = bpy.data.objects['Face']
modifier = next(m for m in face.modifiers if m.type == 'NODES' and m.node_group
                and m.node_group.get('gacha_hsr_face_outlines'))
# These generated fixtures contain only the camera formerly added by setup.
cameras = [obj for obj in bpy.context.scene.objects if obj.type == 'CAMERA']
assert len(cameras) <= 1 and all(obj.name == 'Camera' for obj in cameras)
for camera in cameras:
    data = camera.data
    bpy.data.objects.remove(camera, do_unlink=True)
    if data.users == 0:
        bpy.data.cameras.remove(data)


def check_without_camera():
    counts = len(bpy.data.objects), len(bpy.data.cameras)
    assert configure_face_outlines(bpy.context, face, modifier)
    assert counts == (len(bpy.data.objects), len(bpy.data.cameras))
    assert bpy.context.scene.camera is None
    assert not any(s.item_type == 'SOCKET' and s.name == 'Camera' for s in modifier.node_group.interface.items_tree)
    assert get_modifier_property(modifier, modifier.node_group['dynamic_socket']) == 1
    assert get_modifier_property(modifier, 'Input_8') == 0


check_without_camera()
check_without_camera()
camera = bpy.data.objects.new('Existing User Camera', bpy.data.cameras.new('Existing User Camera'))
bpy.context.scene.collection.objects.link(camera)
for active in (False, True):
    bpy.context.scene.camera = camera if active else None
    counts = len(bpy.data.objects), len(bpy.data.cameras)
    configure_face_outlines(bpy.context, face, modifier)
    assert counts == (len(bpy.data.objects), len(bpy.data.cameras))
    assert bpy.context.scene.camera == (camera if active else None)
    assert not any(s.item_type == 'SOCKET' and s.socket_type == 'NodeSocketObject'
                   for s in modifier.node_group.interface.items_tree)
    assert get_modifier_property(modifier, modifier.node_group['dynamic_socket']) == 1
data = camera.data
bpy.data.objects.remove(camera, do_unlink=True)
bpy.data.cameras.remove(data)
check_without_camera()
if '--save' in args:
    bpy.ops.wm.save_as_mainfile(filepath=str(path), relative_remap=False)
print('HSR_CAMERA_INDEPENDENT_OUTLINES_PASS', bpy.app.version_string, flush=True)
