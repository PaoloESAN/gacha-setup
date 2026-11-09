"""Blender --background --factory-startup --python-exit-code 1 --python this_file."""
import sys
from pathlib import Path
import bpy, addon_utils
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
original=bpy.utils.user_resource
def resource(kind,path='',create=False):
    if kind in {'CONFIG','SCRIPTS'}:
        p=ROOT/'tests/.runtime/cecilia-materials'/kind/path;p.mkdir(parents=True,exist_ok=True);return str(p)
    return original(kind,path=path,create=create)
bpy.utils.user_resource=resource
addon_utils.enable('setup_wizard',default_set=False)
from setup_wizard.import_order import set_active_character_directory
from setup_wizard.utils.zzz_material_json import is_untextured
assert is_untextured({'m_SavedProperties': {'m_TexEnvs': {'_MainTex': {'m_Texture': {'IsNull': True}}}}})
assert not is_untextured({'m_SavedProperties': {'m_TexEnvs': {'_MainTex': {'m_Texture': {'IsNull': False, 'Name': 'Body'}}}}})
assert is_untextured({'textures': [{'slot': '_MainTex', 'empty': True}]})
assert not is_untextured({'textures': [{'slot': '_MainTex', 'name': 'Body', 'empty': False}]})
assert not is_untextured({}), 'Unknown JSON must not suppress material replacement'
directory=ROOT/'chars/zzz/Cecilia'
for shader in ('LEGACY','KYTHERA'):
    for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
    for m in list(bpy.data.materials):bpy.data.materials.remove(m,do_unlink=True)
    for g in list(bpy.data.node_groups):bpy.data.node_groups.remove(g,do_unlink=True)
    bpy.context.scene.game_type_dropdown='ZENLESS_ZONE_ZERO'
    bpy.context.scene.zzz_shader_type=shader
    bpy.context.scene.character_rigger_props.disable_rigging=True
    set_active_character_directory(str(directory))
    args=dict(game_type='ZENLESS_ZONE_ZERO',file_directory=str(directory),next_step_idx=-1,invoker_type='',high_level_step_name='')
    assert bpy.ops.genshin.import_model(filepath=str(directory/'Cecilia.fbx'),**args)=={'FINISHED'}
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    before=[(o.name,[s.material.name for s in o.material_slots if s.material]) for o in meshes]
    print('BEFORE',shader,before,flush=True)
    assert bpy.ops.genshin.import_materials(**args)=={'FINISHED'}
    assert bpy.ops.genshin.replace_default_materials(**args)=={'FINISHED'}
    after=[(o.name,[s.material.name for s in o.material_slots if s.material]) for o in meshes]
    print('AFTER',shader,after,flush=True)
    assert all(s.material and s.material.name.startswith(('ZZZ ','Kythera')) for o in meshes for s in o.material_slots),after
    assert bpy.ops.genshin.import_textures(**args)=={'FINISHED'}
    from setup_wizard.texture_import_setup.game_texture_importers import ZenlessZoneZeroTextureImporterFacade
    from types import SimpleNamespace
    importer=ZenlessZoneZeroTextureImporterFacade(SimpleNamespace(),bpy.context)
    mappings,_=importer._build_zzz_json_texture_map(str(directory))
    for part in ('body_1','body_2','hair'):
        body=mappings[f'mat_cecilia_{part}']
        for role in ('d','m','n','a'):
            assert body[role].lower()==f'cecilia_{part}_{role}.png',body
    print('CECILIA_MATERIALS_AND_TEXTURES_PASS',shader,flush=True)

