"""WuWa V3: on-face expressions, gaze, highlights, outlines and rebuild safety.

blender -b --factory-startup --python-exit-code 1 --python
tests/wuwa_face_on_model_blender.py -- "output/Phoebe - WuWa V3.blend"
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'tests/.runtime/wuwa-v3'
RUNTIME.mkdir(parents=True, exist_ok=True)
original_resource = bpy.utils.user_resource
def resource(kind, path='', create=False):
    if kind in {'CONFIG', 'SCRIPTS'}:
        destination = RUNTIME / kind / path
        destination.mkdir(parents=True, exist_ok=True)
        return str(destination)
    return original_resource(kind, path=path, create=create)
bpy.utils.user_resource = resource
sys.path.insert(0, str(ROOT))
from setup_wizard.character_rig_setup.wuwa_face_panel import wuwa_face_rig_main
from setup_wizard.character_rig_setup.wuwa_face_on_model import CONTROLS, HELPERS, GAZE, HIGHLIGHTS

args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
path = Path(args[0]) if args else ROOT / 'output/Phoebe - WuWa V3.blend'
bpy.ops.wm.open_mainfile(filepath=str(path.resolve()))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE' and o.data.get('rig_id'))
if '--upgrade' in args:
    assert wuwa_face_rig_main(rig)
    from setup_wizard.character_rig_setup.wuwa_rig_script import organize_rigify_bone_collections
    organize_rigify_bone_collections(rig)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.data.shape_keys
          and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)]
face = max(meshes, key=lambda m: sum(k in m.data.shape_keys.key_blocks for k in ('E_Close','B_Anger','M_OpenSmall','Aa')))
keys = face.data.shape_keys
unit = rig['ww_face_control_unit']
assert rig.get('ww_face_widget_version') == 2, 'Rebuild the rig to install the reference widgets'
# The WuWa shader emits instances; realize them so deformation checks inspect
# the visible face instead of the empty evaluated mesh component.
realize_group = bpy.data.node_groups.new('Test WuWa Realize', 'GeometryNodeTree')
realize_group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
realize_group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
ni = realize_group.nodes.new('NodeGroupInput')
no = realize_group.nodes.new('NodeGroupOutput')
nr = realize_group.nodes.new('GeometryNodeRealizeInstances')
realize_group.links.new(ni.outputs[0], nr.inputs[0])
realize_group.links.new(nr.outputs[0], no.inputs[0])
realize = face.modifiers.new('Test Realize', 'NODES')
realize.node_group = realize_group
assert rig.get('ww_face_rig_version') == 'WuWaRigify V3 on-face'
assert not any(b.name in {'panel.root','fp.boarder','fp.brow.board','mouth.board'} for b in rig.data.bones)
assert all(n in rig.pose.bones for n in CONTROLS | HELPERS | GAZE | HIGHLIGHTS)
assert all(rig.pose.bones[n].custom_shape for n in CONTROLS | GAZE | HIGHLIGHTS)
assert rig.pose.bones['MouthPanel'].custom_shape and not rig.data.bones['MouthPanel'].hide
assert rig.data.bones['MouthPanel'].hide_select
for name in ('FacePanelRoot', 'FacePanel'):
    assert [c.name for c in rig.data.bones[name].collections] == ['Others']
    assert rig.data.bones[name].hide and rig.data.bones[name].hide_select
    assert not rig.pose.bones[name].custom_shape.data.vertices
assert rig.pose.bones['fp.outline'].custom_shape.name.startswith('WGT-WuWaV3-Outline-OL')
assert any(c.type == 'COPY_LOCATION' and c.subtarget == 'EyeTracker'
           for c in rig.pose.bones['FacePanel'].constraints)
gaze_center=rig.matrix_world @ rig.data.bones['EyeTracker'].head_local
brow_center=rig.matrix_world @ rig.data.bones['Eyebrows'].head_local
mouth_center=rig.matrix_world @ rig.data.bones['Mouth'].head_local
assert abs(brow_center.z-gaze_center.z-.06*unit)<1e-5
for side,sign in [('L',1),('R',-1)]:
    point=rig.matrix_world @ rig.data.bones[f'Mouth.{side}'].head_local
    assert abs(point.x-mouth_center.x-sign*.045*unit)<1e-5
# Portable contracts from the unchanged script, even without the local
# reference fixture. In particular, circles/diamonds cannot stand in for
# the two capsule rings or the thin brow/eye-scale bars.
contracts={
    'EyeTracker':(.1128,.0408,68,68), 'Eye.L':(.024,.024,32,32),
    'Eye.R':(.024,.024,32,32), 'EyeScale':(.02,.002,4,4),
    'Eyebrows':(.09,.004,4,4), 'Mouth':(.0376,.0136,68,68),
    'Mouth.L':(.008,.008,4,4), 'Mouth.R':(.008,.008,4,4),
    'MouthPanel':(.08,.05,4,2)}
for name in CONTROLS-{'EyeScale','Eyebrows','Mouth','Mouth.L','Mouth.R','fp.outline'}:
    contracts[name]=(.008,.008,3,3)
for name,(width,height,vertices_count,edges_count) in contracts.items():
    pb=rig.pose.bones[name]
    shape=pb.custom_shape
    assert not pb.use_custom_shape_bone_size,name
    assert len(shape.data.vertices)==vertices_count and len(shape.data.edges)==edges_count,name
    points=[Vector(tuple(v.co[i]*pb.custom_shape_scale_xyz[i]/unit for i in range(3))) for v in shape.data.vertices]
    span=Vector(tuple(max(p[i] for p in points)-min(p[i] for p in points) for i in range(3)))
    assert abs(span.x-width)<1e-6 and abs(span.y-height)<1e-6 and abs(span.z)<1e-6,(name,tuple(span))
assert len(contracts)==35
reference_file=ROOT/'tests/.runtime/wuwa-original/widgets.json'
matched_widgets=0
if reference_file.exists():
    reference=json.loads(reference_file.read_text())
    for name,expected in reference.items():
        pb=rig.pose.bones[name]
        shape=pb.custom_shape
        assert shape and len(shape.data.vertices)==len(expected['vertices']), name
        length=pb.bone.length if pb.use_custom_shape_bone_size else 1.
        vertices=[Vector(tuple(v.co[i]*pb.custom_shape_scale_xyz[i]*length/unit for i in range(3))) for v in shape.data.vertices]
        points=[Vector(v) for v in expected['vertices']]
        mapping={}
        for i,point in enumerate(vertices):
            index=min(range(len(points)),key=lambda j:(point-points[j]).length)
            assert (point-points[index]).length<2e-6,(name,i,tuple(point),tuple(points[index]))
            mapping[i]=index
        assert len(set(mapping.values()))==len(points),name
        actual_edges={tuple(sorted(mapping[i] for i in e.vertices)) for e in shape.data.edges}
        expected_edges={tuple(sorted(e)) for e in expected['edges']}
        assert actual_edges==expected_edges,(name,'wrong widget connectivity')
        assert pb.color.palette==expected['color'],(name,pb.color.palette,expected['color'])
        matched_widgets+=1
    assert matched_widgets==35,matched_widgets
assert rig.data.collections['Face'].is_visible
for name in CONTROLS | GAZE:
    b = rig.data.bones[name]
    assert any(c.name == 'Face' for c in b.collections), name
    assert not b.hide, name
    normal = (rig.matrix_world.to_3x3() @ b.matrix_local.to_3x3().col[2]).normalized()
    assert abs(normal.dot(Vector((0,-1,0)))) > .99999, (name,tuple(normal))

def update():
    rig.update_tag()
    for m in meshes:
        m.update_tag()
    bpy.context.view_layer.update()

def weights():
    update()
    return {m.name: [k.value for k in m.data.shape_keys.key_blocks] for m in meshes}

def geometry():
    update()
    evaluated = face.evaluated_get(bpy.context.evaluated_depsgraph_get())
    data = evaluated.to_mesh()
    result = [v.co.copy() for v in data.vertices]
    evaluated.to_mesh_clear()
    return result

neutral = weights()
baseline = geometry()
cases = []
def check(bone, channel, value, key, expected=1., opposite=None):
    if key not in keys.key_blocks:
        return
    pb = rig.pose.bones[bone]
    prop, component = channel.split('.')
    vector = getattr(pb, prop)
    i = 'xyz'.index(component)
    old = vector[i]
    vector[i] = value
    update()
    actual = keys.key_blocks[key].value
    assert abs(actual-expected) < 1e-4, (bone,channel,key,actual,expected)
    if opposite and opposite in keys.key_blocks:
        assert abs(keys.key_blocks[opposite].value) < 1e-5, (bone,opposite,keys.key_blocks[opposite].value)
    after = geometry()
    delta = max((a-b).length for a,b in zip(after,baseline))
    assert delta > 1e-6, (bone,key,'No geometry response')
    vector[i] = old
    update()
    cases.append((bone,channel,key,delta))

check('EyeTracker','scale.y',.5,'E_Close')
check('EyeTracker','scale.y',1.5,'E_Stare')
check('Eye.L','scale.y',.5,'E_Close.L',opposite='E_Close.R')
check('Eye.R','scale.y',.5,'E_Close.R',opposite='E_Close.L')
check('EyeScale','location.y',.01*unit,'E_Blephar',expected=.5)
check('EyeScale','scale.x',.5,'Pupil_Scale.L')
check('EyeScale','scale.x',.5,'Pupil_Scale.R')
check('Eye.L','scale.x',.75,'Pupil_Scale.L',expected=.5,opposite='Pupil_Scale.R')
check('Eye.R','scale.x',.75,'Pupil_Scale.R',expected=.5,opposite='Pupil_Scale.L')
check('EyeTracker','location.x',.1*unit,'Pupil_L.L')
check('Eye.L','location.x',.1*unit,'Pupil_L.L',opposite='Pupil_L.R')
for side in ('L','R'):
    for fan in ('Smile','Anger','Sad','Focus','Insipid'):
        key = f'E_Smile_{side}' if fan == 'Smile' else f'E_{fan}.{side}'
        check(f'{fan}.{side}','location.y',.02*unit,key)
    check(f'Mouth.{side}','location.y',.01*unit,f'M_Smile_{side}',expected=.5)
    check(f'Mouth.{side}','location.y',-.01*unit,f'M_Ennui_{side}',expected=.5)
for name in ('B_Anger','B_Happy','B_Cheerful','B_Sad','B_Flat','B_Inside_Add',
             'Aa','M_OpenSmall','M_Laugh','M_Scared','M_ScaredTooth','M_Anger',
             'M_Trapezoid','M_Nutcracker','M_O','M_A'):
    check(name,'location.y',.02*unit,name)
check('Eyebrows','location.y',.01*unit,'B_Up_Add')
check('Eyebrows','location.y',-.01*unit,'B_Down_Add')
check('Eyebrows','rotation_euler.z',-math.radians(10),'B_AH_L')
check('Eyebrows','rotation_euler.z',math.radians(10),'B_AH_R')
for key,axis,sign in [('E','x',-1),('I','x',1),('A','y',1),('U','y',-1)]:
    check('Mouth','location.'+axis,sign*.02*unit,key)
check('Mouth','scale.x',1.5,'O',expected=1/3)
assert len(cases) >= 25, len(cases)
assert all(max(abs(a-b) for a,b in zip(weights()[name],values)) < 1e-6 for name,values in neutral.items())
# Closing eyelids must not also shrink pupils; EyeScale must not drive both
# split and original global morphs together.
rig.pose.bones['EyeTracker'].scale.y=.5
update()
for key in ('Pupil_Scale','Pupil_Scale.L','Pupil_Scale.R'):
    if key in keys.key_blocks:
        assert abs(keys.key_blocks[key].value) < 1e-5, key
rig.pose.bones['EyeTracker'].scale.y=1
update()
for key in ('Pupil_Scale','Pupil_L','Pupil_R','Pupil_Up','Pupil_Down'):
    if all(f'{key}.{s}' in keys.key_blocks for s in ('L','R')) and key in keys.key_blocks:
        assert abs(keys.key_blocks[key].value)<1e-6, key

highlight_objects = {}
for o in bpy.data.objects:
    if not o.animation_data:
        continue
    for d in o.animation_data.drivers:
        for v in d.driver.variables:
            for t in v.targets:
                if t.id == rig and t.bone_target in {'CTRL-Highlight_Top','CTRL-Highlight_Bottom'}:
                    highlight_objects[t.bone_target] = o
assert len(highlight_objects)==2, highlight_objects
top,bottom=[highlight_objects[n] for n in ('CTRL-Highlight_Top','CTRL-Highlight_Bottom')]
before_top,before_bottom=top.location.copy(),bottom.location.copy()
rig.pose.bones['CTRL-Eye_Highlight'].location.x=.01
update()
mouth_before=rig.pose.bones['Mouth'].matrix.translation.copy()
head=rig.pose.bones['head']
original_mode=head.rotation_mode
original_rotation=head.rotation_euler.copy()
head.rotation_mode='XYZ'
head.rotation_euler.z+=.2
update()
assert (rig.pose.bones['Mouth'].matrix.translation-mouth_before).length>1e-4
head.rotation_euler=original_rotation
head.rotation_mode=original_mode
update()
assert (rig.pose.bones['Mouth'].matrix.translation-mouth_before).length<1e-5
assert abs(top.location.x-before_top.x-.01)<1e-5
assert abs(bottom.location.x-before_bottom.x-.01)<1e-5
rig.pose.bones['CTRL-Eye_Highlight'].location.x=0
rig.pose.bones['CTRL-Highlight_Top'].location.y=.01
update()
assert abs(top.location.z-before_top.z-.01)<1e-5
assert (bottom.location-before_bottom).length<1e-5
rig.pose.bones['CTRL-Highlight_Top'].location.y=0
update()

outlines=[m for o in meshes for m in o.modifiers if 'outline' in m.name.lower()]
assert outlines
rig.pose.bones['fp.outline'].location.x=.02*unit
update()
assert all(not m.show_viewport and not m.show_render for m in outlines)
rig.pose.bones['fp.outline'].location.x=0
update()
assert all(m.show_viewport and m.show_render for m in outlines)

body={n:(rig.data.bones[n].matrix_local.copy(),rig.pose.bones[n].custom_shape,
         tuple(rig.pose.bones[n].lock_rotation)) for n in ('head','upper_arm_fk.L','hand_ik.L','thigh_fk.L','foot_ik.R')}
def head_widget_state():
    pb = rig.pose.bones['head']
    return (tuple(pb.custom_shape_translation), tuple(pb.custom_shape_rotation_euler),
            tuple(pb.custom_shape_scale_xyz), pb.use_custom_shape_bone_size,
            pb.custom_shape_transform, pb.bone.hide)
head_widget_before = head_widget_state()
highlight_state={n:rig.data.bones[n].matrix_local.copy() for n in HIGHLIGHTS}
counts=(len(rig.data.bones),len(bpy.data.objects),len(keys.key_blocks))
assert wuwa_face_rig_main(rig)
assert head_widget_state() == head_widget_before, 'Face rebuild changed the head widget'
assert counts == (len(rig.data.bones),len(bpy.data.objects),len(keys.key_blocks)), (counts,len(rig.data.bones),len(bpy.data.objects),len(keys.key_blocks))
for n,(matrix,shape,locks) in body.items():
    assert all((a-b).length<1e-6 for a,b in zip(matrix,rig.data.bones[n].matrix_local)), n
    assert rig.pose.bones[n].custom_shape==shape and tuple(rig.pose.bones[n].lock_rotation)==locks
for n,matrix in highlight_state.items():
    assert all((a-b).length<1e-6 for a,b in zip(matrix,rig.data.bones[n].matrix_local)), n
update()
for m in meshes:
    for curve in m.data.shape_keys.animation_data.drivers:
        assert curve.is_valid, (m.name,curve.data_path)
        for var in curve.driver.variables:
            for target in var.targets:
                if target.id==rig and var.type=='TRANSFORMS':
                    assert target.bone_target in rig.pose.bones, target.bone_target

report={'file':str(path),'expression_cases':cases,'highlights':True,'gaze':True,
        'independent_eyes':True,'outline_toggle':True,'neutral_restored':True,'rebuild_idempotent':True,
        'widgets_matching_unmodified_script':matched_widgets}
(RUNTIME/(path.stem+'-regression.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
if '--save-blend' in args:
    face.modifiers.remove(realize)
    bpy.data.node_groups.remove(realize_group)
    bpy.ops.wm.save_as_mainfile(filepath=str(path.resolve()))
print('WUWA_V3_FACE_PASS',len(cases),'highlights gaze outlines independent eyes rebuild','reference widgets',matched_widgets,flush=True)
