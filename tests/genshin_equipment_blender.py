import sys, json, traceback
from pathlib import Path
import bpy, addon_utils
WORKSPACE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(WORKSPACE))
original_resource=bpy.utils.user_resource
def isolated_resource(kind,path='',create=False):
 if kind in {'SCRIPTS','CONFIG'}:
  target=WORKSPACE/'.tmp/weapon-blender'/kind.lower()/path;target.mkdir(parents=True,exist_ok=True);return str(target)
 return original_resource(kind,path=path,create=create)
bpy.utils.user_resource=isolated_resource
addon_utils.enable('setup_wizard',default_set=True)
for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
bpy.context.scene.character_rigger_props.disable_rigging=True
folder=WORKSPACE/'EquipSkin_Sword_WeaponQuestSnezhnaya01'
from setup_wizard.import_order import set_active_character_directory
set_active_character_directory(str(folder))
kwargs=dict(game_type='GENSHIN_IMPACT',file_directory=str(folder),next_step_idx=-1,invoker_type='',high_level_step_name='')
report={'steps':[],'snapshots':{}}
def snapshot(label):
 meshes=[]
 for obj in bpy.data.objects:
  if obj.type!='MESH':continue
  mats=[]
  for slot in obj.material_slots:
   mat=slot.material
   if not mat:mats.append(None);continue
   settings=[]
   if mat.node_tree:
    for n in mat.node_tree.nodes:
     values={s.name:s.default_value for s in n.inputs if hasattr(s,'default_value') and s.type in {'VALUE','BOOLEAN'} and any(k in s.name.lower() for k in ['alpha','transparen','dissolv','opacity'])}
     if values:settings.append({'node':n.name,'values':values})
   mats.append({'name':mat.name,'source':mat.get('_original_material_name'),'nodes':mat.use_nodes,'textures':[(n.name,n.image.name if n.image else None) for n in mat.node_tree.nodes if n.type=='TEX_IMAGE'] if mat.node_tree else [],'alpha':settings})
  meshes.append({'name':obj.name,'vertices':len(obj.data.vertices),'polygons':len(obj.data.polygons),'materials':mats,'hidden':obj.hide_viewport,'mods':[(m.name,m.type) for m in obj.modifiers]})
 report['snapshots'][label]=meshes
 print('SNAPSHOT',label,[(o['name'],[m['name'] if m else None for m in o['materials']]) for o in meshes])
def bones():
 return {o.name:{b.name:[*b.head_local,*b.tail_local,b.matrix_local.to_quaternion()[:]] for b in o.data.bones} for o in bpy.data.objects if o.type=='ARMATURE'}
def op(name,fn,**extra):
 try:
  result=fn('EXEC_DEFAULT',**kwargs,**extra);report['steps'].append({'name':name,'result':str(result)});print('STEP',name,result)
 except Exception as e:
  report['steps'].append({'name':name,'error':str(e)});traceback.print_exc()
op('import_model',bpy.ops.genshin.import_model,filepath=str(folder/'EquipSkin_Sword_WeaponQuestSnezhnaya01.fbx'))
snapshot('imported');original_bones=bones()
op('delete_empties',bpy.ops.genshin.delete_empties)
op('import_materials',bpy.ops.genshin.import_materials)
op('replace_materials',bpy.ops.genshin.replace_default_materials)
snapshot('replaced')
op('textures',bpy.ops.genshin.import_textures)
snapshot('textured')
op('outlines',bpy.ops.genshin.import_outlines)
op('geometry_nodes',bpy.ops.genshin.setup_geometry_nodes)
op('outline_lightmaps',bpy.ops.genshin.import_outline_lightmaps)
op('material_json',bpy.ops.genshin.import_material_data)
snapshot('configured')
try:print('STEP','fix_transformations',bpy.ops.genshin.fix_transformations('EXEC_DEFAULT'))
except Exception:traceback.print_exc()
op('rig_character',bpy.ops.hoyoverse.rig_character)
try:print('STEP','setup_head_driver',bpy.ops.genshin.setup_head_driver('EXEC_DEFAULT'))
except Exception:traceback.print_exc()
try:bpy.ops.genshin.set_color_management_to_standard('EXEC_DEFAULT')
except Exception:traceback.print_exc()
try:bpy.ops.genshin.delete_specific_objects('EXEC_DEFAULT')
except Exception:traceback.print_exc()
op('rename_materials',bpy.ops.hoyoverse.rename_shader_materials)
try:print('STEP','join_meshes',bpy.ops.hoyoverse.join_meshes_on_armature('EXEC_DEFAULT'))
except Exception:traceback.print_exc()
snapshot('final')
report['disable_rigging']=bpy.context.scene.character_rigger_props.disable_rigging
report['bones_preserved']=original_bones==bones()
report['armatures']=[o.name for o in bpy.data.objects if o.type=='ARMATURE']
out=WORKSPACE/'output/weapon_setup'
(out/'setup_report.json').write_text(json.dumps(report,indent=2))

# Integration checks for the actual export, including the original material slots.
assert report['disable_rigging'] and report['bones_preserved']
assert all('error' not in step and step.get('result')=="{'FINISHED'}" for step in report['steps'])
source_meshes = {o['name']: o for o in report['snapshots']['imported'] if not o['hidden']}
final_meshes = {o['name']: o for o in report['snapshots']['final']}
assert source_meshes.keys() == final_meshes.keys()
for name, original in source_meshes.items():
    final = final_meshes[name]
    assert (original['vertices'],original['polygons']) == (final['vertices'],final['polygons'])
    assert len(original['materials']) == len(final['materials'])
    assert all(material and material['nodes'] for material in final['materials'])
    assert [m['name'] for m in original['materials']] == [m['source'] for m in final['materials']]
main = bpy.data.objects['Equip_Sword_WeaponQuestSnezhnaya_Model']
assert len({slot.material for slot in main.material_slots}) == 2
for slot in main.material_slots:
    mat = slot.material
    shader = next(n for n in mat.node_tree.nodes if n.inputs.get('Toggle Alpha') is not None or n.inputs.get('Use Alpha') is not None)
    alpha = shader.inputs.get('Toggle Alpha') or shader.inputs.get('Use Alpha')
    assert not alpha.default_value
    assert mat.node_tree.nodes['Main_Lightmap'].image.name == 'Equip_Sword_WeaponQuestSnezhnaya_Tex_Lightmap.png'
    assert mat.node_tree.nodes['Main_Diffuse'].image.name == 'Equip_Sword_WeaponQuestSnezhnaya02_Tex_Diffuse.png'
    outline = bpy.data.materials.get(mat.name + ' Outlines')
    assert outline is not None
    outline_shader = next(n for n in outline.node_tree.nodes if n.inputs.get('Outline Color 1') is not None)
    assert all(not socket.is_linked for socket in outline_shader.inputs if socket.name.startswith('Outline Color '))
    assert tuple(outline_shader.inputs['Outline Color 1'].default_value) == (0, 0, 0, 1)
template = bpy.data.materials['HoYoverse - Genshin Body']
template_output = next(n for n in template.node_tree.nodes if n.type=='OUTPUT_MATERIAL')
original_link = template_output.inputs['Surface'].links[0]
for obj_name in final_meshes:
    for mat in bpy.data.objects[obj_name].data.materials:
        assert len(mat.node_tree.nodes) == len(template.node_tree.nodes)
        assert not any(n.name.startswith('Equipment ') for n in mat.node_tree.nodes)
        output = next(n for n in mat.node_tree.nodes if n.type=='OUTPUT_MATERIAL')
        link = output.inputs['Surface'].links[0]
        assert (link.from_node.name, link.from_socket.name) == (original_link.from_node.name, original_link.from_socket.name)
for name in ('StarLine','SwordGuard'):
    assert not any(m.name.startswith('Outlines') for m in bpy.data.objects[name].modifiers)
print('PASS: original shader nodes and output preserved; distinct materials, textures, opaque alpha, geometry and bones preserved with rigging disabled.')

bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(out/'WeaponQuestSnezhnaya01.blend'))
print('RESULT',report['disable_rigging'],report['bones_preserved'])
