"""Run with Blender --background --factory-startup --python-exit-code 1
--python tests/zzz_eyeshadow_geometry_blender.py.
"""
import sys
from pathlib import Path
from mathutils import Matrix, Vector
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from setup_wizard.utils.zzz_eyeshadow_geometry import classify_zzz_eyeshadow_faces
from setup_wizard.genshin_import_character_model import setup_zzz_eyeshadow_uv, _execute_fbx_import, reorient_armature_bones

for folder, expected_count in [
    ('wise-default', 44), ('miyabi-dignified-blossom', 40),
    ('belle-summer-skies', 42), ('jane-doe-hidden-nightfade', 134),
    ('evelyn-chevalier-a-moth-to-light', 232), ('seed-flower-in-bloom', 36),
    ('cissia-snake-mouse-game', 204), ('Avatar_Female_Size02_Lindverne_UI', 44),
]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    model = next((ROOT/'chars/zzz'/folder).rglob('*.fbx'))
    # Reproduce the actual wizard importer and bone cleanup. A plain FBX
    # import leaves head tails pointing forward and hid the original bug.
    _execute_fbx_import(str(model))
    face = next(o for o in bpy.data.objects if o.type == 'MESH' and 'face' in o.name.lower())
    reorient_armature_bones(face.find_armature())
    classified = classify_zzz_eyeshadow_faces(face)
    assert len(classified) == expected_count, (folder, len(classified))
    eye_group_indices = {g.index for g in face.vertex_groups if 'eye' in g.name.lower()
                         and not any(k in g.name.lower() for k in ('brow', 'lid', 'lash', 'shadow', 'track', 'ctrl', 'mch', 'org'))}
    eye_vertices = {v.index for v in face.data.vertices if any(g.group in eye_group_indices and g.weight > 0.1 for g in v.groups)}
    assert eye_vertices
    assert not any(v in eye_vertices for index in classified for v in face.data.polygons[index].vertices)
    eye_centers = []
    for side in ('L', 'R'):
        side_groups = {g.index for g in face.vertex_groups if g.index in eye_group_indices
                       and (f'_{side}_' in g.name or g.name.endswith(f'_{side}'))}
        verts = [v.co for v in face.data.vertices if any(g.group in side_groups and g.weight > .1 for g in v.groups)]
        eye_centers.append(sum(verts, Vector()) / len(verts))
    detected_sides = {min(range(2), key=lambda side: (face.data.polygons[index].center - eye_centers[side]).length)
                      for index in classified}
    assert detected_sides == {0, 1}, (folder, 'overlay missing on one eye')

    # The classification does not depend on the atlas, nor FBX orientation/scale.
    for uv in face.data.uv_layers:
        for loop in uv.data:
            loop.uv = (0.95, 0.95)
    assert classify_zzz_eyeshadow_faces(face) == classified
    transform = Matrix.Rotation(0.8, 4, 'X') @ Matrix.Scale(2.5, 4)
    arm = face.find_armature()
    arm.matrix_world = transform @ arm.matrix_world
    face.matrix_world = transform @ face.matrix_world
    bpy.context.view_layer.update()
    assert classify_zzz_eyeshadow_faces(face) == classified, folder
    mirror = Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0))
    arm.matrix_world = mirror @ arm.matrix_world
    face.matrix_world = mirror @ face.matrix_world
    bpy.context.view_layer.update()
    assert classify_zzz_eyeshadow_faces(face) == classified, (folder, 'mirrored import')

    skin = bpy.data.materials.new('Face skin')
    transparent = bpy.data.materials.new('Eye Transparent')
    face.data.materials.clear()
    face.data.materials.append(skin)
    face.data.materials.append(transparent)
    for p in face.data.polygons:
        # Reproduce the old false positive on eye-skinned iris polygons.
        p.material_index = int(any(v in eye_vertices for v in p.vertices))
    assert setup_zzz_eyeshadow_uv(face)
    assigned = {p.index for p in face.data.polygons if p.material_index == 1}
    assert assigned == classified
    slots = len(face.material_slots)
    assert setup_zzz_eyeshadow_uv(face)
    assert len(face.material_slots) == slots
    assert {p.index for p in face.data.polygons if p.material_index == 1} == classified
    print('PASS:', folder, 'overlay faces', len(classified), 'iris protected; UV and transform independent; prior false positives repaired; repeated setup stable')

# Missing eye reference data must preserve an unrelated model unchanged.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object
assert classify_zzz_eyeshadow_faces(obj) == set()
assert not setup_zzz_eyeshadow_uv(obj)
assert len(obj.material_slots) == 0
print('PASS: no eye reference data means no changes')
