"""Regression: Art The Herta outline scale and baked face expressions (5.2+)."""
import importlib
import json
from pathlib import Path
import runpy
import sys
import zipfile

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
legacy = '--legacy' in sys.argv
runtime = ROOT / 'tests/.runtime/hsr-herta-art'
runtime.mkdir(parents=True, exist_ok=True)
original_resource = bpy.utils.user_resource
def resource(kind, path='', create=False):
    if kind in {'CONFIG', 'SCRIPTS'}:
        destination = runtime / kind / path
        destination.mkdir(parents=True, exist_ok=True)
        return str(destination)
    return original_resource(kind, path=path, create=create)
bpy.utils.user_resource = resource
sys.path.insert(0, str(ROOT))
dependencies = runtime / 'dependencies'
with zipfile.ZipFile(ROOT / 'setup_wizard/dependencies/retarget.zip') as archive:
    archive.extractall(dependencies)
package = min(dependencies.rglob('__init__.py'), key=lambda p: len(p.parts)).parent
sys.path.insert(0, str(package.parent))
importlib.import_module(package.name)
model = ROOT / 'chars/hsr/Art_TheHerta_00/Art_TheHerta_00.fbx'
job = {'game_type': 'HONKAI_STAR_RAIL', 'disable_rigging': False,
       'character_directory': str(model.parent), 'selected_model_file': str(model),
       'gacha_module': 'setup_wizard', 'gacha_addon_parent': str(ROOT),
       'status_path': str(runtime / 'status.json'), 'result_path': str(runtime / 'The Herta.blend')}
(runtime / 'job.json').write_text(json.dumps(job), encoding='utf-8')
sys.argv = [sys.argv[0], '--', str(runtime / 'job.json')]
try:
    runpy.run_path(str(ROOT / 'setup_wizard/services/isolation/isolated_runner.py'), run_name='__main__')
except SystemExit as error:
    if error.code not in (None, 0):
        raise
assert json.loads((runtime / 'status.json').read_text(encoding='utf-8'))['state'] == 'SUCCESS'



from setup_wizard.geometry_nodes_setup.geometry_nodes_setups import refresh_hsr_outline_scale, get_mesh_world_scale
from setup_wizard.utils.modifier_utils import get_modifier_property
checked = 0
for obj in bpy.context.scene.objects:
 if obj.type != 'MESH': continue
 for mod in obj.modifiers:
  if mod.type != 'NODES' or not mod.node_group or mod.node_group.name != 'StellarToon - Outlines GN': continue
  scale = get_mesh_world_scale(obj)
  width = get_modifier_property(mod, 'Input_7')
  depth = get_modifier_property(mod, 'Input_8')
  assert abs(width * scale - .25) < 1e-5, (obj.name, width, scale)
  assert abs(depth * scale - .0075) < 1e-5, (obj.name, depth, scale)
  refresh_hsr_outline_scale(bpy.context)
  assert get_modifier_property(mod, 'Input_7') == width
  checked += 1
assert checked >= 3, checked
print('HSR_HERTA_OUTLINE_SCALE_PASS', checked, flush=True)

rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and o.data.get('rig_id'))
face=bpy.data.objects['Face']
for m in face.modifiers:
 if m.type!='ARMATURE':m.show_viewport=False
keys=face.data.shape_keys
controls={}
for d in keys.animation_data.drivers:
 for v in d.driver.variables:
  if v.type=='TRANSFORMS' and v.targets[0].id==rig and v.targets[0].transform_type.startswith('LOC_'):
   controls.setdefault(v.targets[0].bone_target,set()).add('XYZ'.index(v.targets[0].transform_type[-1]))
def state():
 rig.update_tag();face.update_tag();bpy.context.view_layer.update()
 return [v.co.copy() for v in face.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
before=state();worst=(0,None);tested=0;active=set();bad=[]
for name,axes in controls.items():
 p=rig.pose.bones.get(name)
 if not p:continue
 for axis in axes:
  old=p.location.copy()
  for value in (-.05,.05):
   p.location[axis]=old[axis]+value
   after=state();ds=[a-b for a,b in zip(after,before)]
   mean=sum(ds,Vector())/len(ds)
   maximum=max(v.length for v in ds)
   fraction=sum(v.length>.003 for v in ds)/len(ds)
   values=[k.name for k in keys.key_blocks if k.value>.001]
   active.update(values);tested+=1
   if abs(mean.x)>worst[0]:worst=(abs(mean.x),(name,axis,value,tuple(mean),maximum,fraction,values))
   if fraction>.8 and abs(mean.x)>.003:bad.append((name,axis,value,tuple(mean),fraction))
  p.location=old;state()
print('EXPRESSION_SWEEP',tested,'CONTROLS',len(controls),'ACTIVATED_KEYS',len(active),'WORST_LATERAL',worst,'GLOBAL_SHIFTS',bad,flush=True)
assert not bad
print('HERTA_NO_GLOBAL_FACE_SHIFT',flush=True)

from setup_wizard.utils.hsr_expression_reference import rebase_baked_expressions
assert rebase_baked_expressions(face) == 0, 'Neutral-reference repair must be idempotent'
assert len(active) >= 190, 'Expression controls did not activate their shape keys'
