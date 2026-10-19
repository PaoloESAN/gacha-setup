"""Run in Blender with --python-exit-code 1; optional -- <character-folder>."""
import sys, math, zipfile
from pathlib import Path
import bpy, addon_utils
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
folder_name = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'Avatar_Female_Size03_Sunbringer_UI'
original_resource = bpy.utils.user_resource
def isolated_resource(kind, path='', create=False):
    if kind in {'SCRIPTS','CONFIG'}:
        target = ROOT / '.tmp/zzz-hip-rig-tests' / folder_name / kind.lower() / path
        target.mkdir(parents=True, exist_ok=True)
        return str(target)
    return original_resource(kind, path=path, create=create)
bpy.utils.user_resource = isolated_resource
bpy.ops.wm.read_factory_settings(use_empty=True)

dependencies = ROOT/'.tmp/zzz-hip-rig-tests/dependencies'
with zipfile.ZipFile(ROOT/'setup_wizard/dependencies/Expy-Kit-v052.zip') as archive:
    archive.extractall(dependencies)
sys.path.insert(0, str(dependencies))
module = next(p.name for p in dependencies.iterdir() if p.is_dir() and (p/'__init__.py').exists())
__import__(module).register()
addon_utils.enable('rigify', default_set=True)
from setup_wizard.genshin_import_character_model import _execute_fbx_import, reorient_armature_bones
from setup_wizard.character_rig_setup.zzz_rig_script import rig_character
from setup_wizard.utils.zzz_hip_follow import setup_zzz_hip_follow

folder = ROOT/'chars/zzz'/folder_name
_execute_fbx_import(str(next(folder.glob('*.fbx'))))
source = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.endswith(('Body_1','Body')))
coincident = {}
seam_pairs = []
hip_groups = {g.index for g in body.vertex_groups if g.name == 'Bip001 Pelvis'
              or g.name.startswith(('Skn_L_Thigh','Skn_R_Thigh','Skn_L_Pelvis','Skn_R_Pelvis','Skn_L_RouTui','Skn_R_RouTui'))}
for vertex in body.data.vertices:
    weights = {g.group:g.weight for g in vertex.groups}
    if sum(w for group,w in weights.items() if group in hip_groups) < .9:
        continue
    for other, previous in coincident.get(tuple(vertex.co), []):
        if all(abs(previous.get(g,0)-weights.get(g,0)) < 1e-5 for g in previous.keys() | weights.keys()):
            seam_pairs.append((vertex.index,other))
    coincident.setdefault(tuple(vertex.co), []).append((vertex.index,weights))
assert seam_pairs
def assert_closed_seams():
    mesh = body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    gap = max((mesh.vertices[a].co-mesh.vertices[b].co).length for a,b in seam_pairs)
    assert gap < 1e-6, (folder_name,'opened skin seam',gap)
reorient_armature_bones(source)
bpy.context.view_layer.objects.active = source
source.select_set(True)
rig_character(str(ROOT/'setup_wizard/character_rig_setup/RootShape.blend'), 0, True, True, True, True, False, False)
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.data.get('rig_id'))
for side in ('L','R'):
    pivot = rig.pose.bones[f'MCH-ZZZ-HipFollow.{side}']
    constraint = pivot.constraints['ZZZ Hip Follow']
    assert constraint.target == rig and constraint.subtarget == f'DEF-thigh.{side}'
    rig.pose.bones[f'thigh_parent.{side}']['IK_FK'] = 1.0
    control = rig.pose.bones[f'thigh_fk.{side}']
    control.rotation_mode = 'QUATERNION'
    control.rotation_quaternion.identity()
    rig.update_tag(); bpy.context.view_layer.update()
    rest = pivot.matrix.to_quaternion()
    thigh_rest = rig.pose.bones[f'DEF-thigh.{side}'].matrix.to_quaternion()
    axis = (rig.matrix_world @ control.bone.matrix_local).to_3x3().inverted() @ Vector((1,0,0))
    control.rotation_quaternion = Matrix.Rotation(math.radians(-90), 4, axis).to_quaternion()
    rig.update_tag(); bpy.context.view_layer.update()
    angle = rest.rotation_difference(pivot.matrix.to_quaternion()).angle
    thigh_angle = thigh_rest.rotation_difference(rig.pose.bones[f'DEF-thigh.{side}'].matrix.to_quaternion()).angle
    thigh_angle = min(thigh_angle, 2 * math.pi - thigh_angle)
    assert .6 < angle < 1.0, (side, angle)
    assert_closed_seams()
    assert abs(angle - thigh_angle * .5) < .05, (side, angle, thigh_angle)
    count = len(rig.data.bones)
    assert setup_zzz_hip_follow(rig) == 8
    assert len(rig.data.bones) == count
    assert abs(angle - rest.rotation_difference(pivot.matrix.to_quaternion()).angle) < 1e-4
    control.rotation_quaternion.identity()
    rig.update_tag(); bpy.context.view_layer.update()
    assert rest.rotation_difference(pivot.matrix.to_quaternion()).angle < 1e-3
    print('PASS generated rig:', folder_name, side, 'FK thigh', round(math.degrees(thigh_angle)), 'hip follow', round(math.degrees(angle)), 'degrees; no cycle or duplicate repair')
    rig.pose.bones[f'thigh_parent.{side}']['IK_FK'] = 0.0
    rig.update_tag(); bpy.context.view_layer.update()
    foot = rig.pose.bones[f'foot_ik.{side}']
    original = foot.matrix.copy()
    pivot_rest = pivot.matrix.to_quaternion()
    thigh_rest = rig.pose.bones[f'DEF-thigh.{side}'].matrix.to_quaternion()
    moved = original.copy()
    moved.translation += Vector((0,-.25,.2))
    foot.matrix = moved
    rig.update_tag(); bpy.context.view_layer.update()
    thigh_angle = thigh_rest.rotation_difference(rig.pose.bones[f'DEF-thigh.{side}'].matrix.to_quaternion()).angle
    thigh_angle = min(thigh_angle, 2*math.pi-thigh_angle)
    follow_angle = pivot_rest.rotation_difference(pivot.matrix.to_quaternion()).angle
    follow_angle = min(follow_angle, 2*math.pi-follow_angle)
    assert thigh_angle > .1 and abs(follow_angle - thigh_angle*.5) < .08, (side, thigh_angle, follow_angle)
    assert_closed_seams()
    foot.matrix = original
    rig.update_tag(); bpy.context.view_layer.update()
    print('PASS IK foot lift follows the deforming thigh:',folder_name,side)
