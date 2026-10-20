"""Run with Blender --background --factory-startup --python-exit-code 1 --python this_file."""
import sys
from pathlib import Path
from types import SimpleNamespace
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
original_resource = bpy.utils.user_resource
def isolated_resource(kind, path='', create=False):
    if kind in {'SCRIPTS', 'CONFIG'}:
        target = ROOT / '.tmp/zzz-highlights-test' / kind.lower() / path
        target.mkdir(parents=True, exist_ok=True)
        return str(target)
    return original_resource(kind, path=path, create=create)
bpy.utils.user_resource = isolated_resource

from setup_wizard.replace_default_materials_setup.game_default_material_replacers import ZenlessZoneZeroDefaultMaterialReplacer
from setup_wizard.genshin_import_character_model import _execute_fbx_import
from setup_wizard.utils.zzz_eye_highlights import assign_zzz_eye_highlights
from setup_wizard.texture_import_setup.game_texture_importers import ZenlessZoneZeroTextureImporterFacade

from itertools import product
for shader, character in product(('LEGACY', 'KYTHERA'), ('Avatar_Female_Size03_Sunbringer_UI', 'Avatar_Female_Size02_Belle_UI', 'belle-summer-skies')):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.types.Scene.zzz_shader_type = bpy.props.EnumProperty(items=[('LEGACY', 'Legacy', ''), ('KYTHERA', 'Kythera', '')])
    bpy.context.scene.zzz_shader_type = shader
    folder = ROOT/'chars/zzz'/character
    _execute_fbx_import(str(next(folder.glob('*.fbx'))))
    filename = 'ZZZ Setup v7.blend' if shader == 'LEGACY' else "Kythera's ZZZ Shader V1.5.1.blend"
    with bpy.data.libraries.load(str(ROOT/'setup_wizard/shaders/zzz'/filename)) as (src, dst):
        dst.materials = src.materials
    material = bpy.data.materials['ZZZ Shader EyeHighlights']
    face = next(o for o in bpy.data.objects if o.type == 'MESH' and 'face' in o.name.lower())
    by_side = {}
    for side in ('L', 'R'):
        group = next((g for g in face.vertex_groups if 'highlights' in g.name.lower()
                      and f'_{side}_' in g.name), None)
        if group:
            vertices = {v.index for v in face.data.vertices if any(g.group == group.index and g.weight > .0001 for g in v.groups)}
            by_side[side] = {p.index for p in face.data.polygons if all(v in vertices for v in p.vertices)}
            assert by_side[side]
    # The original Belle fixture uses identical highlight geometry/UVs to her
    # summer costume but binds it to Bdy_L/R_Eye rather than highlight groups.
    expected = by_side['L'] | by_side['R'] if by_side else set(range(3090, 3142))
    operator = SimpleNamespace(file_directory=str(folder), game_type='ZENLESS_ZONE_ZERO', report=lambda *args: None)
    replacer = ZenlessZoneZeroDefaultMaterialReplacer(operator, bpy.context)
    replacer.replace_default_materials()
    assigned = {p.index for p in face.data.polygons if face.data.materials[p.material_index] == material}
    assert assigned == expected, (shader, len(assigned), len(expected))
    baseline = [p.material_index for p in face.data.polygons]
    slots = len(face.material_slots)
    replacer.replace_default_materials()
    assert len(face.material_slots) == slots
    assert [p.material_index for p in face.data.polygons] == baseline
    # Texture import must bind the face atlas to the highlight material too.
    importer = ZenlessZoneZeroTextureImporterFacade(operator, bpy.context)
    importer.import_textures_from_folder(str(folder))
    assert material.node_tree.nodes['Face_D'].image
    assert 'face_d' in material.node_tree.nodes['Face_D'].image.name.casefold(), material.node_tree.nodes['Face_D'].image.name
    groups = [g for g in face.vertex_groups if 'highlights' in g.name.lower()]
    if groups:
        # New/Better variants and a Blender numerical suffix are equivalent.
        for group in groups:
            side = 'L' if '_L_' in group.name else 'R'
            group.name = f'Skn_{side}_Highlights_Better.001'
        assert assign_zzz_eye_highlights(face, material) == len(expected)
        for group in groups:
            side = 'L' if '_L_' in group.name else 'R'
            group.name = 'Eye Highlight L' if side == 'L' else 'Eye Highliht R'
        assert assign_zzz_eye_highlights(face, material) == len(expected)
    assert [p.material_index for p in face.data.polygons] == baseline
    print('PASS', shader, character, 'highlights:', len(expected), 'faces; correct atlas; unrelated faces preserved; repeated replacement stable')
