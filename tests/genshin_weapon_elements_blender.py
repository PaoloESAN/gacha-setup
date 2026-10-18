"""Run with Blender --background --factory-startup --python tests/genshin_weapon_elements_blender.py."""
import sys
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import bpy, addon_utils
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
addon_utils.enable('setup_wizard',default_set=True)
for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
bpy.context.scene.character_rigger_props.disable_rigging=True
folder=ROOT/'chars/golden-bough-of-nemorensis-sublimation-default'
from setup_wizard.import_order import set_active_character_directory
set_active_character_directory(str(folder))
kwargs=dict(game_type='GENSHIN_IMPACT',file_directory=str(folder),next_step_idx=-1,invoker_type='',high_level_step_name='')
def op(fn,**extra):
    result=fn('EXEC_DEFAULT',**kwargs,**extra)
    assert result=={'FINISHED'},result
op(bpy.ops.genshin.import_model,filepath=str(next(folder.glob('*.fbx'))))
op(bpy.ops.genshin.delete_empties)
op(bpy.ops.genshin.import_materials)
op(bpy.ops.genshin.replace_default_materials)
op(bpy.ops.genshin.import_textures)
op(bpy.ops.genshin.import_outlines)
op(bpy.ops.genshin.setup_geometry_nodes)
op(bpy.ops.genshin.import_outline_lightmaps)
op(bpy.ops.genshin.import_material_data)
from setup_wizard.utils.genshin_weapon_elements import settings_target, weapon_materials, ELEMENTS, _decode, PRESETS_KEY, SELECTION_KEY, capture_element_presets
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(s.material and s.material.get(PRESETS_KEY) for s in o.material_slots)]
print('ELEMENT_MESHES',[o.name for o in meshes],flush=True)
assert meshes,'Element metadata was not detected during setup'
bpy.context.view_layer.objects.active=meshes[0]
owner=settings_target(bpy.context)
assert owner
materials=weapon_materials(owner)
print('ELEMENT_MATERIALS',[(m.name,m.get('_original_material_name')) for m in materials],flush=True)
assert len(materials)==2, len(materials)  # The FBX uses normal + transparent slots.

# The same detection also supports Great when that family is used by a mesh.
great=next(m for m in materials if '_Trans_' not in m['_original_material_name']).copy()
great['_original_material_name']='EquipSkin_Sword_MorphNemorensis_Mat_Great_Electric'
capture_element_presets(great,folder)
assert set(_decode(great[PRESETS_KEY]))==set(dict(ELEMENTS))
bpy.data.materials.remove(great)

# Reproduce the previous additive shader on a saved-material copy and upgrade it.
legacy=next(m for m in materials if '_Trans_' not in m['_original_material_name']).copy()
legacy_shader=legacy.node_tree.nodes['Body Shader']
legacy_shader.node_tree=legacy_shader.node_tree.copy()
legacy_tree=legacy_shader.node_tree
for node in list(legacy_tree.nodes):
    if not node.name.startswith('Weapon Emission BSDF') or node.type!='MIX_SHADER':continue
    name=node.name
    sources=[node.inputs[i].links[0].from_socket for i in (1,2)]
    targets=[link.to_socket for link in node.outputs[0].links]
    legacy_tree.nodes.remove(node)
    add=legacy_tree.nodes.new('ShaderNodeAddShader');add.name=name
    for i,source in enumerate(sources):legacy_tree.links.new(source,add.inputs[i])
    for target in targets:legacy_tree.links.new(add.outputs[0],target)
legacy_tree['_gi_weapon_output_version']=3
from setup_wizard.parsers.material_data_json_parsers import HoyoStudioMaterialDataJsonParser
from setup_wizard.utils.genshin_weapon_material_utils import apply_weapon_properties
saved=_decode(legacy[PRESETS_KEY])['Electric']['saved']
parser=HoyoStudioMaterialDataJsonParser({'m_SavedProperties':saved});parser.parse()
apply_weapon_properties(legacy,legacy_shader,vars(parser.m_colors),vars(parser.m_floats))
assert legacy_shader.node_tree.get('_gi_weapon_output_version')==4
assert all(n.type=='MIX_SHADER' for n in legacy_shader.node_tree.nodes if n.name.startswith('Weapon Emission BSDF'))
bpy.data.materials.remove(legacy)

from setup_wizard.ui.gi_ui_setup_wizard_menu import GI_PT_Rig_Character_Settings
assert GI_PT_Rig_Character_Settings.poll(bpy.context)
class Layout:
    def __init__(self):self.props=[]
    def prop(self,obj,name,**kwargs):self.props.append((obj,name))
    def operator(self,*args,**kwargs):return SimpleNamespace()
    def __getattr__(self,name):return lambda *args,**kwargs:self
layout=Layout()
GI_PT_Rig_Character_Settings.draw(SimpleNamespace(layout=layout),bpy.context)
assert (owner,'gi_weapon_element') in layout.props
assert layout.props==[(owner,'gi_weapon_element')], 'Weapon settings must only show the element selector'

for key,_ in ELEMENTS:
    # Selection must work from embedded presets without reading source JSONs.
    with patch.object(Path,'read_text',side_effect=AssertionError('Source file read during switching')):
        owner.gi_weapon_element=key
    assert owner.get(SELECTION_KEY)==key
    for m in materials:
        assert m.get(SELECTION_KEY)==key
        saved=_decode(m[PRESETS_KEY])[key]['saved']
        c=saved['m_Colors'].get('_EmissionColor_MHY')
        shader=m.node_tree.nodes.get('Body Shader')
        ids=m.node_tree.nodes.get('Weapon Element Colors')
        assert ids is not None
        for i in range(1,6):
            tint_color=saved['m_Colors'].get('_Color'+(str(i) if i>1 else ''))
            if tint_color:
                expected=[tint_color.get(k,tint_color.get(k.upper())) for k in 'rgba']
                assert all(abs(a-b)<1e-5 for a,b in zip(ids.inputs['Color '+str(i)].default_value,expected))
        assert shader.inputs['Diffuse Color'].links[0].from_node.name=='Weapon Element Tint'
        assert shader.node_tree.get('_gi_weapon_output_version')==4
        if saved['m_Floats'].get('_UseMaterialMasksTex'):
            assert shader.inputs['Element Emission Mask'].is_linked
            assert shader.inputs['Element Emission Color'].links[0].from_node.name=='Weapon Element Tint'
            assert abs(shader.inputs['Element Emission Strength'].default_value-saved['m_Floats']['_EmissionScaler'])<1e-5
        if c and shader and shader.inputs.get('Emission Tint'):
            expected=[c.get(k,c.get(k.upper())) for k in 'rgba']
            assert all(abs(a-b)<1e-5 for a,b in zip(shader.inputs['Emission Tint'].default_value,expected)),(key,m.name,expected)
        outline=m.get('_gi_element_outline')
        if outline:
            node=next(n for n in outline.node_tree.nodes if 'Outline Color 5' in n.inputs)
            c=saved['m_Colors'].get('_OutlineColor5')
            if c:
                expected=[c.get(k,c.get(k.upper())) for k in 'rgba']
                assert all(abs(a-b)<1e-5 for a,b in zip(node.inputs['Outline Color 5'].default_value,expected)),(key,m.name,'outline')
    print('ELEMENT_PASS',key,flush=True)
# Changing a linked duplicate must leave the original weapon unchanged.
original=next(o for o in meshes if any(
    s.material and s.material.get('_gi_element_outline') for s in o.material_slots))
duplicate=original.copy()
duplicate.data=original.data
bpy.context.collection.objects.link(duplicate)
duplicate.parent=None
bpy.context.view_layer.objects.active=duplicate
assert settings_target(bpy.context)==duplicate, 'A detached copy must keep its own settings target'
original_mats=[s.material for s in original.material_slots]
duplicate.gi_weapon_element='Fire'
assert all(m.get(SELECTION_KEY)=='Ice' for m in original_mats if m and m.get(PRESETS_KEY))
assert all(s.material not in original_mats for s in duplicate.material_slots if s.material and s.material.get(PRESETS_KEY))
original_outlines={m.get('_gi_element_outline') for m in original_mats if m and m.get('_gi_element_outline')}
assert all(s.material.get('_gi_element_outline') not in original_outlines
           for s in duplicate.material_slots if s.material and s.material.get('_gi_element_outline'))
for mod in duplicate.modifiers:
    if mod.type=='NODES':
        from setup_wizard.utils.modifier_utils import get_modifier_property
        for item in mod.node_group.interface.items_tree:
            if item.item_type=='SOCKET' and item.in_out=='INPUT' and item.socket_type=='NodeSocketMaterial':
                assert get_modifier_property(mod,item.identifier) not in original_outlines
# Save/reopen also exercises ID references for presets and their textures.
output=ROOT/f'.weapon-elements-check/result-{bpy.app.version[0]}-{bpy.app.version[1]}.blend'
output.parent.mkdir(parents=True,exist_ok=True)
duplicate_name=duplicate.name
bpy.ops.wm.save_as_mainfile(filepath=str(output))
bpy.ops.wm.open_mainfile(filepath=str(output))
duplicate=bpy.data.objects[duplicate_name]
duplicate.gi_weapon_element='Water'
assert duplicate.get(SELECTION_KEY)=='Water'
append_source=output.with_name(output.stem+'-append.blend')
shutil.copyfile(output,append_source)
with bpy.data.libraries.load(str(append_source),link=False) as (source,destination):
    destination.objects=[duplicate_name]
appended=destination.objects[0]
bpy.context.scene.collection.objects.link(appended)
appended.gi_weapon_element='Grass'
assert appended.get(SELECTION_KEY)=='Grass'
assert duplicate.get(SELECTION_KEY)=='Water'
assert all(s.material.get(SELECTION_KEY)=='Grass' for s in appended.material_slots if s.material and s.material.get(PRESETS_KEY))
print('PASS: seven elements, UI, normal/Great/transparent families, outlines, duplicate isolation, save/reopen and Append',flush=True)
