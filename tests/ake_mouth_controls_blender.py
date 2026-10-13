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
        target = WORKSPACE / '.tmp/ake-mouth-blender' / kind.lower() / path
        target.mkdir(parents=True, exist_ok=True)
        return str(target)
    return original_resource(kind, path=path, create=create)
bpy.utils.user_resource = isolated_resource
addon_utils.enable('setup_wizard', default_set=True)
from mathutils import Vector
from setup_wizard.character_rig_setup.ake_face_rig import setup_endfield_isaac_face_rig, ENDFIELD_FACE_MAPPING

for directory in ['chr_0036_jsspsi_postmodel', 'P_npc_major_mon3terhq_01']:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    fbx = next((WORKSPACE / 'chars/ake' / directory).rglob('*.fbx'))
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    setup_endfield_isaac_face_rig(rig)
    lip_height = (rig.data.bones['lipMupJoint'].head_local.z + rig.data.bones['lipMdnJoint'].head_local.z) * .5
    assert abs(rig.data.bones['Mouth-Master'].head_local.z - lip_height) < 1e-5
    panel_rest = {b.name: b.head_local.copy() for b in [rig.data.bones['Mouth-Master'], *rig.data.bones['Mouth-Master'].children_recursive]}
    cases = [('mouthLower_M.001', ['jawJoint', 'faceMdJawDnJoint'])]
    for side, prefix in [('L', 'Lf'), ('R', 'Rt')]:
        cases += [(f'mouthUpper_01_{side}.001', [f'face{prefix}CheekOtInJoint']),
                  (f'mouthUpper_03_{side}.001', [f'face{prefix}CheekOtDnJoint'])]
    bpy.context.view_layer.update()
    neutral = {name: pb.matrix.copy() for name, pb in rig.pose.bones.items() if name in ENDFIELD_FACE_MAPPING}
    for control, names in cases:
        names = [n for n in names if n in rig.pose.bones]
        if not names:
            continue
        pb = rig.pose.bones[control]
        baseline = {name: rig.pose.bones[name].matrix.copy() for name in names}
        weighted = []
        for mesh in bpy.context.scene.objects:
            if mesh.type != 'MESH' or not any(m.type == 'ARMATURE' and m.object == rig for m in mesh.modifiers):
                continue
            groups = {mesh.vertex_groups[n].index for n in names if n in mesh.vertex_groups}
            indices = [v.index for v in mesh.data.vertices if any(g.group in groups and g.weight > .01 for g in v.groups)]
            if indices:
                evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
                weighted.append((mesh, indices, [evaluated.data.vertices[i].co.copy() for i in indices]))
        pb.location.z = .02
        rig.update_tag()
        bpy.context.view_layer.update()
        for name in names:
            assert (rig.pose.bones[name].matrix.translation - baseline[name].translation).length > 1e-5, (control, name)
        if weighted:
            assert any((mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices[i].co - co).length > 1e-6
                       for mesh, indices, positions in weighted for i, co in zip(indices, positions)), control
        pb.location = (0, 0, 0)
        rig.update_tag()
        bpy.context.view_layer.update()
        print('PASS', directory, control, names, 'weighted meshes', len(weighted))
    count = len(rig.data.bones)
    # Simulate old broken bindings and repair an already fused rig.
    for name in ['jawJoint', 'faceLfCheekOtDnJoint', 'faceRtCheekOtDnJoint']:
        bone = rig.pose.bones.get(name)
        if bone:
            for constraint in bone.constraints:
                if constraint.name.startswith('Isaac_Deform_'):
                    constraint.subtarget = 'JawdnEnd_M' if name == 'jawJoint' else ENDFIELD_FACE_MAPPING[name]['deform'].removesuffix('.001')
    setup_endfield_isaac_face_rig(rig)
    assert len(rig.data.bones) == count
    assert all((rig.data.bones[name].head_local - position).length < 1e-6 for name, position in panel_rest.items())
    for name, mapping in ENDFIELD_FACE_MAPPING.items():
        pb = rig.pose.bones.get(name)
        if pb:
            constraints = [c for c in pb.constraints if c.name.startswith('Isaac_Deform_')]
            assert len(constraints) == 1 and constraints[0].subtarget == mapping['deform'], name
            assert (pb.matrix.translation - neutral[name].translation).length < 1e-5, name
    print('PASS repair without duplicate bones or neutral pose displacement', directory)
print('ALL AKE MOUTH TESTS PASSED')
