"""HNA setup using exact Unity material names and the authored shader library.

Material JSONs supply supported shader inputs and nested textures. Outline
bindings live in the GeometryNodeTree asset; masks must not inherit Body maps.
The eye stencil mesh is split without changing the armature or its shape keys.
"""
import json
from pathlib import Path
import bpy
from setup_wizard.import_order import get_active_character_directory
from setup_wizard.utils.modifier_utils import get_modifier_property, set_modifier_property

def directory(op):
    return Path(getattr(op, 'file_directory', '') or get_active_character_directory())

def material_kind(name):
    low = name.lower()
    if 'face_mask' in low:
        return None
    if 'eye_mask' in low:
        return 'Oqaque'
    if 'eyehighlight' in low:
        return 'Iris'
    for part in ('Hair', 'Face', 'Body'):
        if part.lower() in low:
            return part
    return None

def replace_materials():
    templates = {'Body': 'Body1', 'Hair': 'Hair', 'Face': 'Face', 'Iris': 'Iris', 'Oqaque': 'Oqaque'}
    for obj in list(bpy.context.scene.objects):
        if obj.type != 'MESH':
            continue
        for slot in obj.material_slots:
            old = slot.material
            if not old or old.name.startswith('HSR - '):
                continue
            kind = material_kind(old.name)
            if not kind:
                continue
            name = 'HSR - Avatar ' + kind
            mat = bpy.data.materials.get(name)
            if not mat:
                template = bpy.data.materials.get('HSR - ' + templates[kind])
                if not template:
                    raise RuntimeError('Missing HNA template: ' + kind)
                mat = template.copy()
                mat.name = name
                mat.use_fake_user = True
                mat['_original_material_name'] = old.name
            slot.material = mat
    for obj in list(bpy.context.scene.objects):
        if obj.type != 'MESH' or not obj.name.lower().startswith('face'):
            continue
        mask_indices = {i for i, m in enumerate(obj.data.materials) if m and m.name == 'HSR - Avatar Oqaque'}
        if not mask_indices or len(obj.data.materials) == 1:
            continue
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        before = set(bpy.data.objects)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.context.tool_settings.mesh_select_mode = (False, False, True)
        bpy.ops.mesh.select_all(action='DESELECT')
        import bmesh
        bm = bmesh.from_edit_mesh(obj.data)
        for face in bm.faces:
            if face.material_index in mask_indices:
                face.select_set(True)
        bmesh.update_edit_mesh(obj.data)
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        for part in [obj] + list(set(bpy.data.objects) - before):
            used = sorted({poly.material_index for poly in part.data.polygons})
            mats = [part.data.materials[i] for i in used]
            indices = [used.index(poly.material_index) for poly in part.data.polygons]
            part.data.materials.clear()
            for mat in mats:
                part.data.materials.append(mat)
            for poly, index in zip(part.data.polygons, indices):
                poly.material_index = index
            keys = part.data.shape_keys
            if keys:
                basis = keys.key_blocks[0]
                for key in list(keys.key_blocks)[1:]:
                    if key.name.startswith('Basis.') and all(((a.co - b.co).length < 1e-07 for a, b in zip(key.data, basis.data))):
                        part.shape_key_remove(key)
    if not bpy.data.materials.get('HSR - Avatar Trans'):
        mat = bpy.data.materials['HSR - Trans'].copy()
        mat.name = 'HSR - Avatar Trans'
        mat.use_fake_user = True
    configure_eye_materials()


def configure_iris_nodes(mat):
    """Match HNA EyeHighlight's color/alpha wiring and additive body shader."""
    if not mat.use_nodes or not mat.node_tree:
        return
    tree = mat.node_tree
    shader = next((n for n in tree.nodes if n.type == 'GROUP'
                   and n.inputs.get('Diffuse Color') is not None
                   and n.outputs.get('Body Shader') is not None), None)
    if shader is None:
        return
    color = next((n for n in tree.nodes if n.type == 'TEX_IMAGE'
                  and (n.label == '_Color' or n.name == '_Color')), None)
    if color is None:
        color = tree.nodes.new('ShaderNodeTexImage')
        color.label = '_Color'
    color.interpolation = 'Cubic'
    color.projection = 'FLAT'
    color.extension = 'REPEAT'
    if color.image:
        color.image.alpha_mode = 'CHANNEL_PACKED'
        color.image.colorspace_settings.name = 'sRGB'
    tree.links.new(color.outputs['Color'], shader.inputs['Diffuse Color'])
    tree.links.new(color.outputs['Alpha'], shader.inputs['Diffuse Alpha'])
    for name, value in [('LightMap Color', (0, 0, 0, 1)), ('LightMap Alpha', .1),
                        ('Alpha / 0 = Normal, 1 = Add', 1), ('Use Alpha', 1), ('Use Emission', 0)]:
        socket = shader.inputs.get(name)
        if socket is not None:
            for link in list(socket.links):
                tree.links.remove(link)
            socket.default_value = value
    for output in (n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL'):
        tree.links.new(shader.outputs['Body Shader'], output.inputs['Surface'])


def configure_eye_materials(materials=None):
    """Apply HNA's transparent eye surface method after material defaults."""
    for mat in materials if materials is not None else bpy.data.materials:
        if not mat or not mat.name.startswith('HSR - '):
            continue
        name = mat.name.lower().replace('_', '').replace(' ', '')
        if 'outlines' in name or not any(kind in name for kind in ('eyeshadow', 'iris', 'opaque', 'oqaque')):
            continue
        if (material_kind(mat.get('_original_material_name', '')) == 'Iris'
                or mat.name.startswith('HSR - Avatar Iris')):
            configure_iris_nodes(mat)
        if hasattr(mat, 'surface_render_method'):
            mat.surface_render_method = 'BLENDED'
        elif hasattr(mat, 'blend_method'):
            mat.blend_method = 'BLEND'


def configure_outline_vertex_colors(objects=None):
    """Set the actual outline color socket to attribute Col on Blender 4/5."""
    for obj in objects if objects is not None else bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        for mod in obj.modifiers:
            if mod.type != 'NODES' or not mod.node_group:
                continue
            group = mod.node_group
            if not group.name.startswith('HoYoverse - Outlines'):
                continue
            socket = next((item for item in group.interface.items_tree
                           if item.item_type == 'SOCKET' and item.in_out == 'INPUT'
                           and (item.identifier == 'Input_3'
                                or item.name in {'Vertex Colors', 'Vertex Color'})), None)
            if not socket:
                raise RuntimeError('HNA outline vertex color socket is missing')
            set_modifier_property(mod, socket.identifier + '_attribute_name', 'Col')
            set_modifier_property(mod, socket.identifier + '_use_attribute', True)


def configure_runtime_settings(objects=None):
    """Reapply HNA settings after rig/setup operations and isolated append."""
    materials = None
    if objects is not None:
        materials = {slot.material for obj in objects if obj.type == 'MESH'
                     for slot in obj.material_slots if slot.material}
    configure_eye_materials(materials)
    configure_outline_vertex_colors(objects)

def nodes_with_images(tree, seen=None):
    seen = seen or set()
    if tree in seen:
        return
    seen.add(tree)
    for node in tree.nodes:
        if node.type == 'TEX_IMAGE':
            yield node
        elif node.type == 'GROUP' and node.node_tree:
            yield from nodes_with_images(node.node_tree, seen)

def load_image(folder, name, colorspace):
    path = next((p for p in folder.iterdir() if p.stem.lower() == name.lower() and p.suffix.lower() in {'.png', '.tga', '.dds', '.jpg'}), None)
    if not path:
        raise RuntimeError('Missing HNA texture: ' + name)
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = colorspace
    return img

def import_textures(op):
    folder = directory(op)
    for mat in bpy.data.materials:
        source = mat.get('_original_material_name')
        if not source:
            continue
        kind = material_kind(source)
        if kind not in {'Body', 'Hair', 'Face', 'Iris'}:
            continue
        data = json.loads((folder / 'Materials' / (source + '.json')).read_text(encoding='utf8'))['m_SavedProperties']
        env = data.get('m_TexEnvs', {})
        top = [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE']
        for prop, cs in [('_MainTex', 'sRGB'), ('_LightMap', 'Non-Color')]:
            texture = env.get(prop, {}).get('m_Texture', {}).get('Name')
            if not texture:
                continue
            if kind == 'Iris':
                configure_iris_nodes(mat)
                color = next(n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.label == '_Color')
                if prop == '_MainTex':
                    color.image = load_image(folder, texture, cs)
            else:
                index = 0 if prop == '_MainTex' else 1
                if index < len(top):
                    top[index].image = load_image(folder, texture, cs)
        groups = {'_DSRampTex': ('Hair_Ramp' if kind == 'Hair' else 'Body_Ramp', 'sRGB'), '_FaceMap': ('_FaceMap', 'Non-Color'), '_FaceExpression': ('_Expression', 'sRGB')}
        for prop, (groupname, cs) in groups.items():
            texture = env.get(prop, {}).get('m_Texture', {}).get('Name')
            if not texture:
                continue
            group = next((n.node_tree for n in mat.node_tree.nodes if n.type == 'GROUP' and n.node_tree and (n.node_tree.name == groupname)), None)
            if group:
                for n in nodes_with_images(group):
                    n.image = load_image(folder, texture, cs)
    configure_eye_materials()
    return {'FINISHED'}

def linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def apply_json(op):
    folder = directory(op)
    for mat in bpy.data.materials:
        source = mat.get('_original_material_name')
        if not source or material_kind(source) not in {'Body', 'Hair', 'Face'}:
            continue
        data = json.loads((folder / 'Materials' / (source + '.json')).read_text(encoding='utf8'))['m_SavedProperties']
        values = dict(data.get('m_Floats', {}))
        values.update({k: tuple((linear(v[c]) for c in 'rgb')) + (v.get('a', 1.0),) for k, v in data.get('m_Colors', {}).items()})
        for target in [mat, bpy.data.materials.get(mat.name + ' Outlines')]:
            if not target:
                continue
            for n in target.node_tree.nodes:
                for socket in n.inputs:
                    if socket.name in values and hasattr(socket, 'default_value') and (socket.type in {'VALUE', 'RGBA'}):
                        socket.default_value = values[socket.name]
    return {'FINISHED'}

class MaterialDataImporter:

    def __init__(self, op):
        self.op = op

    def import_material_data(self):
        return apply_json(self.op)

class GeometrySetup:

    def __init__(self, op):
        self.op = op

    def setup_geometry_nodes(self):
        group = bpy.data.node_groups.get('HoYoverse - Outlines')
        if not group or group.bl_idname != 'GeometryNodeTree':
            raise RuntimeError('HNA geometry outline group is missing')
        bindings = json.loads(group.get('_hna_modifier_bindings', '{}'))
        for obj in bpy.context.scene.objects:
            if obj.type != 'MESH':
                continue
            name = 'Outlines Face' if obj.name.startswith('Face.') else 'Outlines ' + obj.name
            mod = obj.modifiers.get(name) or obj.modifiers.new(name, 'NODES')
            mod.node_group = group
            set_modifier_property(mod, 'Input_3_use_attribute', True)
            set_modifier_property(mod, 'Input_3_attribute_name', 'Col')
            set_modifier_property(mod, 'Input_7', 0.25)
            for i, (mask, out) in enumerate([('Input_10', 'Input_5'), ('Input_11', 'Input_9'), ('Input_14', 'Input_15'), ('Input_18', 'Input_19'), ('Input_24', 'Input_25')]):
                if i >= len(obj.data.materials):
                    continue
                mat = obj.data.materials[i]
                if not mat or not mat.name.startswith('HSR - Avatar '):
                    continue
                kind = mat.name.removeprefix('HSR - Avatar ')
                outline = bpy.data.materials.get(mat.name + ' Outlines')
                if not outline:
                    template = bpy.data.materials.get('HSR - ' + kind + ' Outlines') or bpy.data.materials.get('HSR - Outlines')
                    outline = template.copy()
                    outline.name = mat.name + ' Outlines'
                    outline.use_fake_user = True
                set_modifier_property(mod, mask, mat)
                set_modifier_property(mod, out, outline)
            role = 'Face' if obj.name.startswith('Face.') else obj.name
            role_bindings = bindings.get(role, {})
            # Attribute names may enable attribute mode in Blender 5.x. Set
            # the explicit mode flags last so VALUE inputs stay as values.
            for key, val in sorted(role_bindings.items(), key=lambda item: item[0].endswith('_use_attribute')):
                if key in {'Input_10', 'Input_5', 'Input_11', 'Input_9', 'Input_14', 'Input_15', 'Input_18', 'Input_19', 'Input_24', 'Input_25'}:
                    if val and (not bpy.data.materials.get(val)):
                        template = bpy.data.materials.get(val.replace('HSR - Avatar ', 'HSR - '))
                        if template:
                            mat = template.copy()
                            mat.name = val
                            mat.use_fake_user = True
                    set_modifier_property(mod, key, bpy.data.materials.get(val) if val else None)
                else:
                    current = get_modifier_property(mod, key)
                    set_modifier_property(mod, key, bool(val) if isinstance(current, bool) else val)
        configure_runtime_settings()
        return {'FINISHED'}

class OutlineTextures:

    def import_textures(self):
        return {'FINISHED'}
