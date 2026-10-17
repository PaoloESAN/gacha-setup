"""Blender --background --python-exit-code 1 --python tests/isolated_texture_paths_blender.py.

Uses fresh Blender processes to test the worker/UI file boundary, including an
unsaved destination, Unicode filenames and stale Windows exporter paths.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unicodedata

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if not args:
    with tempfile.TemporaryDirectory(prefix='gacha_texture_paths_') as directory:
        for stage in ('build', 'receive_unsaved', 'receive_saved', 'receive_legacy'):
            subprocess.run([
                bpy.app.binary_path, '--background', '--factory-startup', '--python-exit-code', '1',
                '--python', str(Path(__file__).resolve()), '--', stage, directory,
            ], check=True)
    print('PASS: isolated textures survive save/append/temp cleanup in saved and unsaved scenes')
    sys.exit(0)

from tests.common.blender_executor import enable_addons, clear_scene
enable_addons()
clear_scene()
from setup_wizard.utils.texture_utils import prepare_image_paths
from setup_wizard.services.isolation.isolation_service import append_result

stage, directory = args
root = Path(directory)
character = root / 'Modèle 測試'
textures = character / 'Textures'
worker = root / 'worker'
destination = root / stage
destination.mkdir(exist_ok=True)
os.chdir(destination)
filename = unicodedata.normalize('NFD', 'Peau Été.PNG')

if stage == 'build':
    textures.mkdir(parents=True)
    worker.mkdir()
    bpy.ops.wm.save_as_mainfile(filepath=str(character / 'source.blend'))
    images = []
    for name in (filename, 'Mask.png', 'Packed.png'):
        image = bpy.data.images.new(name, width=2, height=2)
        image.generated_color = (0.2, 0.4, 0.6, 1.0)
        image.filepath_raw = str(textures / name)
        image.file_format = 'PNG'
        image.save()
        images.append(image)
    color, mask, packed = images
    color.name = unicodedata.normalize('NFC', filename).lower() + '.001'
    color.filepath = 'C:\\Exported\\Textures\\' + unicodedata.normalize('NFC', filename).upper()
    color.alpha_mode = 'STRAIGHT'
    mask.filepath = '//Textures/Mask.png'
    mask.colorspace_settings.name = 'Non-Color'
    packed.pack()
    material = bpy.data.materials.new('Path Regression')
    material.use_nodes = True
    for image in images:
        node = material.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = image
    bpy.ops.mesh.primitive_cube_add()
    bpy.context.object.data.materials.append(material)
    bpy.context.object.name = 'Texture Character'
    collection = bpy.data.collections.new('Character')
    bpy.context.scene.collection.children.link(collection)
    collection.objects.link(bpy.context.object)
    bpy.ops.wm.save_as_mainfile(filepath=str(worker / 'legacy.blend'), copy=True)
    assert not prepare_image_paths(str(character), images=images)
    assert Path(color.filepath) == textures / filename
    assert color.alpha_mode == 'STRAIGHT'
    assert mask.colorspace_settings.name == 'Non-Color'
    assert not color.packed_file and not mask.packed_file
    bpy.ops.wm.save_as_mainfile(filepath=str(worker / 'result.blend'), copy=True, relative_remap=False)
    (textures / 'Packed.png').unlink()
else:
    if stage == 'receive_saved':
        bpy.ops.wm.save_as_mainfile(filepath=str(destination / 'user.blend'))
    guard = bpy.data.images.new('Existing other character', width=2, height=2)
    guard.filepath_raw = 'Z:/other_character/Mask.png'
    guard.source = 'FILE'
    original_guard_path = guard.filepath
    # Appending and then deleting the temporary worker must preserve images.
    temporary = Path(tempfile.mkdtemp(dir=root, prefix='append_'))
    try:
        source = worker / ('legacy.blend' if stage == 'receive_legacy' else 'result.blend')
        result = temporary / 'character.blend'
        shutil.copy2(source, result)
        append_result(result, character_directory=str(character))
    finally:
        shutil.rmtree(temporary)
    assert guard.filepath == original_guard_path, 'Existing character texture was modified'
    images = [node.image for mat in bpy.data.materials if mat.name.startswith('Path Regression')
              for node in mat.node_tree.nodes if node.type == 'TEX_IMAGE']
    assert len(images) == 3, [image.name for image in images]
    for image in images:
        if not image.packed_file:
            image.reload()
        assert tuple(image.size) == (2, 2), (image.name, image.filepath)
        if not image.packed_file:
            assert not image.filepath.startswith('//'), image.filepath
            assert Path(image.filepath).is_file(), image.filepath
    assert next(im for im in images if im.name.startswith('peau')).alpha_mode == 'STRAIGHT'
    assert next(im for im in images if im.name.startswith('Mask')).colorspace_settings.name == 'Non-Color'
    print('PASS:', stage, 'external paths, packed images, colorspace and other-character isolation')
