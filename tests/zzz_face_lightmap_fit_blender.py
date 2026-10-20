"""Run with Blender --background --factory-startup --python-exit-code 1 --python this_file."""
import sys
from pathlib import Path
from types import SimpleNamespace
import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
original_resource = bpy.utils.user_resource
def isolated_resource(kind, path='', create=False):
    if kind in {'SCRIPTS', 'CONFIG'}:
        target = ROOT / '.tmp/zzz-lightmap-fit-test' / kind.lower() / path
        target.mkdir(parents=True, exist_ok=True)
        return str(target)
    return original_resource(kind, path=path, create=create)
bpy.utils.user_resource = isolated_resource

from setup_wizard.utils.zzz_face_lightmap_fit import nose_uv, select_face_lightmap
from setup_wizard.texture_import_setup.game_texture_importers import ZenlessZoneZeroTextureImporterFacade
folder = ROOT/'chars/zzz/Avatar_Female_Size03_Sunbringer_UI'
bpy.ops.import_scene.fbx(filepath=str(next(folder.glob('*.fbx'))))
face = next(o for o in bpy.data.objects if o.type == 'MESH' and 'face' in o.name.lower())
with bpy.data.libraries.load(str(ROOT/'setup_wizard/shaders/zzz/ZZZ Setup v7.blend')) as (src, dst):
    dst.node_groups = ['Face Lightmap']
group = dst.node_groups[0]
reserves = {n.name: n.image for n in group.nodes if n.type == 'TEX_IMAGE' and n.image}
images = list(reserves.values())
print('Sunbringer nose UV:', nose_uv(face))
chosen = select_face_lightmap(images, [face])
assert chosen and chosen.name == 'Female_Face_Lightmap_02.png', getattr(chosen, 'name', None)

# Actual import path must supply the material's mesh, not use a scene-wide face.
mat = bpy.data.materials.new('ZZZ Shader Face')
mat.use_nodes = True
node = mat.node_tree.nodes.new('ShaderNodeGroup')
node.node_tree = group
face.data.materials.clear()
face.data.materials.append(mat)
importer = ZenlessZoneZeroTextureImporterFacade(SimpleNamespace(game_type='ZENLESS_ZONE_ZERO'), bpy.context)
importer.import_textures_from_folder(str(folder))
assert group.nodes['Face_Lightmap'].image == chosen
assert all(group.nodes[n].image == img for n, img in reserves.items())

# A shared armature/object transform cannot change the chosen layout.
transform = Matrix.Rotation(.8, 4, 'X') @ Matrix.Scale(2.5, 4)
armature = face.find_armature()
armature.matrix_world = transform @ armature.matrix_world
face.matrix_world = transform @ face.matrix_world
bpy.context.view_layer.update()
assert select_face_lightmap(images, [face]) == chosen

# Move the UV layout to the other female template: selection must follow UVs,
# even with the exact same character name and geometry.
for loop in face.data.uv_layers.active.data:
    loop.uv.y += .067
shifted = select_face_lightmap(images, [face])
assert shifted and shifted.name == 'Female_Face_Lightmap.png', getattr(shifted, 'name', None)
importer._set_face_lightmap_group(group, chosen, face_objects=[face])
assert group.nodes['Face_Lightmap'].image == chosen
assert select_face_lightmap(images, []) is None
print('PASS UV-based choice, actual import, transform invariance, changed UV layout, explicit override and preserved reserves')
