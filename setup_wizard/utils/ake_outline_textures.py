"""Resolve Endfield stroke maps without borrowing another material's texture."""
import json
import os
import re

import bpy


class StrokeTextures:
    def __init__(self, folder):
        self.files = {}
        self.materials = {}
        if not folder or not os.path.isdir(folder):
            return
        for root, _, files in os.walk(folder):
            for filename in sorted(files):
                path = os.path.join(root, filename)
                stem, extension = os.path.splitext(filename)
                if extension.lower() in {'.png', '.tga', '.dds', '.exr', '.jpg', '.jpeg', '.tif', '.tiff'}:
                    self.files[stem.lower()] = path
                elif extension.lower() == '.json':
                    try:
                        with open(path, encoding='utf-8') as source:
                            props = json.load(source).get('m_SavedProperties', {})
                        self.materials[stem.lower()] = props.get('m_TexEnvs', {})
                    except (OSError, ValueError):
                        continue

    def for_mesh(self, mesh):
        counts = {}
        for polygon in mesh.data.polygons:
            counts[polygon.material_index] = counts.get(polygon.material_index, 0) + 1
        for index in sorted(range(len(mesh.material_slots)), key=lambda i: -counts.get(i, 0)):
            material = mesh.material_slots[index].material
            if material is None:
                continue
            name = re.sub(r'\.\d+$', '', material.name).lower().replace('__raw_fbx_', '')
            candidates = []
            for prop, value in self.materials.get(name, {}).items():
                if 'stroke' in prop.lower() or 'outlinemask' in prop.lower():
                    texture = value.get('m_Texture', {}).get('Name', '')
                    if texture:
                        candidates.append(texture.lower())
            if material.use_nodes:
                for node in material.node_tree.nodes:
                    if node.type != 'TEX_IMAGE' or node.image is None:
                        continue
                    stem = os.path.splitext(os.path.basename(bpy.path.abspath(node.image.filepath)))[0].lower()
                    if stem.endswith('_st'):
                        candidates.append(stem)
                    elif stem.endswith('_d'):
                        candidates.append(stem[:-2] + '_st')
            # Exact exported material/texture names share the actor identifier.
            if name.startswith('m_'):
                candidates.append('t_' + name[2:] + '_st')
            for candidate in candidates:
                path = self.files.get(candidate)
                if path:
                    image = bpy.data.images.load(path, check_existing=True)
                    image.colorspace_settings.name = 'Non-Color'
                    image.alpha_mode = 'CHANNEL_PACKED'
                    return image
        return None
