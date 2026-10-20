"""Character-scoped screen-space hair shadows, based on Sandrone/Danica."""
import math
import re
import uuid

import bpy

from .compositor_effects import render_layer, insert_effect, order_aov_passes
from .eye_through_hair import get_or_create_compositor_tree, supports_eye_through_hair, set_viewport_compositor_always


def character_meshes(context):
    """Follow the active character's rig, never all meshes in the scene."""
    obj = context.active_object
    if obj is None:
        return None, []
    rig = obj if obj.type == 'ARMATURE' else obj.find_armature() if obj.type == 'MESH' else None
    parent = obj
    while parent.parent:
        parent = parent.parent
        if parent.type == 'ARMATURE':
            rig = rig or parent
    if rig:
        descendants = set(rig.children_recursive)
        meshes = [o for o in context.scene.objects if o.type == 'MESH'
                  and (o.find_armature() == rig or o in descendants)]
        return rig, meshes
    if obj.type == 'EMPTY' or obj.parent:
        return parent, [o for o in parent.children_recursive if o.type == 'MESH']
    return obj, [o for o in context.selected_objects if o.type == 'MESH']


def material_role(obj, mat):
    if not mat:
        return None
    name = mat.name.lower().replace('_eyethroughhair', '').replace('_seethrough', '')
    excluded = ('outline', 'hairshadow', 'hair_shadow', 'hair shadow', 'pupil', 'iris', 'brow', 'lash', 'highlight', 'eyestar', 'eyeshadow', 'mouth', 'teeth', 'tongue')
    if any(word in name for word in excluded):
        return None
    if 'eye' in name:
        return None
    if any(word in name for word in ('hair', 'bang', 'pelo')):
        return 'hair'
    if 'face' in name:
        return 'face'
    # Shader group names cover exported models with opaque material names.
    groups = [n.node_tree.name.lower() for n in mat.node_tree.nodes
              if n.type == 'GROUP' and n.node_tree] if mat.node_tree else []
    if any('hair' in g or 'bang' in g for g in groups):
        return 'hair'
    if any(g.endswith('face') or 'face shader' in g for g in groups):
        return 'face'
    obj_name = obj.name.lower()
    if any(word in obj_name for word in excluded) or 'eye' in obj_name:
        return None
    if any(word in obj_name for word in ('hair', 'bang', 'pelo')):
        return 'hair'
    if 'face' in obj_name:
        return 'face'
    return None


def character_masks(obj):
    """Classify polygons, including hair sharing a Body material with clothes.

    Hair weights seed connected islands so rigid scalp vertices weighted only
    to the head are included, while separate clothing/tail islands stay out.
    Facial eye/mouth weights protect those islands even in a Face material.
    """
    mesh = obj.data
    face = [0.0] * len(mesh.polygons)
    hair = face.copy()
    if obj.hide_render or any(k in obj.name.lower() for k in ('outline', 'hairshadow', 'hair_shadow', 'hair shadow', 'wgt-', 'colorwheel')):
        return face, hair
    roles = {i: material_role(obj, slot.material) for i, slot in enumerate(obj.material_slots)}
    hair_groups, protected_groups = set(), set()
    for group in obj.vertex_groups:
        name = group.name.lower()
        if any(k in name for k in ('hair', 'bang', 'pelo')) and 'shadow' not in name:
            hair_groups.add(group.index)
        if (any(k in name for k in ('pupil', 'iris', 'highlight', 'teeth', 'tongue', 'mouth', 'brow'))
                or re.search(r'(?:^|[_. -])eye(?:[_. -]?[lr]|lf|rt)?(?:joint)?$', name)):
            protected_groups.add(group.index)
    seeds, protected = set(), set()
    for vertex in mesh.vertices:
        if sum(w.weight for w in vertex.groups if w.group in hair_groups) > .1:
            seeds.add(vertex.index)
        if sum(w.weight for w in vertex.groups if w.group in protected_groups) > .5:
            protected.add(vertex.index)
    hair_vertices = set(seeds)
    if seeds:
        adjacent = [[] for _ in mesh.vertices]
        for edge in mesh.edges:
            a, b = edge.vertices
            adjacent[a].append(b)
            adjacent[b].append(a)
        pending = list(seeds)
        while pending:
            for index in adjacent[pending.pop()]:
                if index not in hair_vertices and index not in protected:
                    hair_vertices.add(index)
                    pending.append(index)
    existing = mesh.attributes.get('hair_shadow_face')
    skin = [v.value for v in existing.data] if existing and existing.domain == 'FACE' and existing.data_type == 'FLOAT' else None
    allow_face = not any(k in obj.name.lower() for k in ('eye', 'pupil', 'brow', 'lash'))
    for p in mesh.polygons:
        role = roles.get(p.material_index)
        if role == 'face' and allow_face and (skin is not None or not any(i in protected for i in p.vertices)):
            face[p.index] = skin[p.index] if skin else 1.0
        elif role == 'hair' or (role is None and all(i in hair_vertices for i in p.vertices)):
            # Eye, outline and auxiliary materials must never become casters.
            mat = obj.material_slots[p.material_index].material if p.material_index < len(obj.material_slots) else None
            name = mat.name.lower() if mat else ''
            if not any(k in name for k in ('eye', 'outline', 'shadow')):
                hair[p.index] = 1.0
    return face, hair


def _group(scope, scene):
    """Append the original Sandrone group; keep its nodes, links and defaults."""
    from pathlib import Path
    template = next((g for g in bpy.data.node_groups if g.get('csw_hair_shadow_template') and g.get('csw_library_version') == 1), None)
    if template is None:
        asset = Path(__file__).with_name('hair_shadows.blend')
        with bpy.data.libraries.load(str(asset), link=False) as (source, target):
            target.node_groups = ['Sandrone Hair Shadow - Danica']
        template = target.node_groups[0]
    group = template.copy()
    group.name = 'Hair Shadows'
    del group['csw_hair_shadow_template']
    group['csw_effect'], group['csw_scope'], group['csw_version'] = 'hair', scope, 4
    if group.animation_data:
        for curve in group.animation_data.drivers:
            for variable in curve.driver.variables:
                for target in variable.targets:
                    if target.id_type == 'SCENE':
                        target.id = scene
    return group


def _replace_group(node, group):
    """Migrate earlier approximations without changing the reference calculation."""
    tree = node.id_data
    aliases = {'Face Mask': 'face_mask', 'Hair Mask': 'hair_mask',
               'Color': 'Shadow Tint', 'Opacity': 'Strength'}
    inputs = [(aliases.get(s.name, s.name), l.from_socket) for s in node.inputs for l in list(s.links)]
    consumers = [(s.name, l.to_socket) for s in node.outputs for l in list(s.links)]
    controls = {}
    for name in ('Offset X', 'Offset Y', 'Shadow Tint', 'Strength'):
        old_name = next((old for old, new in aliases.items() if new == name and old in node.inputs), name)
        if old_name in node.inputs:
            value = node.inputs[old_name].default_value
            controls[name] = tuple(value) if name == 'Shadow Tint' else value
    if 'Direction' in node.inputs:
        angle = node.inputs['Direction'].default_value
        controls['Offset X'] = math.cos(angle) * math.hypot(1.5, 16.6)
        controls['Offset Y'] = math.sin(angle) * math.hypot(1.5, 16.6)
    old = node.node_tree
    node.node_tree = group
    for s in [*node.inputs, *node.outputs]:
        for link in list(s.links):
            tree.links.remove(link)
    for name, value in controls.items():
        node.inputs[name].default_value = value
    for name, source in inputs:
        if name in node.inputs:
            tree.links.new(source, node.inputs[name])
    for name, dest in consumers:
        if name in node.outputs:
            tree.links.new(node.outputs[name], dest)
    if old.users == 0 and old.get('csw_effect') == 'hair':
        bpy.data.node_groups.remove(old)


def _readable_aovs(owner, meshes, view_layer, node, scope):
    """Name the passes after the character, keeping UUIDs out of the UI."""
    display = re.sub(r'(?i)[_. -]*(?:rig|armature)(?=(?:\.\d+)?$)', '', owner.name).strip('_. -')
    if not display or display.lower() == 'character':
        face = next((o for o in meshes if 'face' in o.name.lower()), owner)
        display = re.sub(r'(?i)[_. -]*face(?:\.\d+)?$', '', face.name).strip('_. -') or owner.name
    display = display[:40]
    old = [f'HS {scope} {part}' for part in ('face_mask', 'hair_mask', 'view_depth')]
    if node:
        for index, names in enumerate((('face_mask', 'Face Mask'), ('hair_mask', 'Hair Mask'), ('Depth',))):
            s = next((node.inputs.get(n) for n in names if node.inputs.get(n) is not None), None)
            if s is not None and s.is_linked:
                old[index] = s.links[0].from_socket.name
    taken = {a.name for a in view_layer.aovs} - set(old)
    label, number = display, 2
    parts = ('Face Mask', 'Hair Mask', 'View Depth')
    while any(f'{label} - {part}' in taken for part in parts):
        label, number = f'{display} ({number})', number + 1
    names = [f'{label} - {part}' for part in parts]
    for before, after in zip(old, names):
        aov = next((a for a in view_layer.aovs if a.name == before), None)
        if aov:
            aov.name = after
    return names, dict(zip(old, names))

def _attribute(mesh, name, values):
    old = mesh.attributes.get(name)
    if old and (old.domain != 'FACE' or old.data_type != 'FLOAT'):
        mesh.attributes.remove(old)
        old = None
    attr = old or mesh.attributes.new(name, 'FLOAT', 'FACE')
    attr.data.foreach_set('value', values)
    mesh.update()


def _aov_material(mat, aovs, attributes, constants, renamed):
    mat.use_nodes = True
    tree = mat.node_tree
    for node in tree.nodes:
        if node.type == 'OUTPUT_AOV' and node.aov_name in renamed:
            node.aov_name = renamed[node.aov_name]
    # Copied characters/materials may still write the original character's
    # passes. Keep the new character's output isolated as well as its masks.
    for node in list(tree.nodes):
        if node.type == 'OUTPUT_AOV' and node.get('csw_hair_shadow_output') and node.aov_name not in aovs:
            tree.nodes.remove(node)
    for name, attribute, constant, label in zip(aovs[:2], attributes, constants, ('Face Mask', 'Hair Mask')):
        output = next((n for n in tree.nodes if n.type == 'OUTPUT_AOV' and n.aov_name == name), None)
        output = output or tree.nodes.new('ShaderNodeOutputAOV')
        output.aov_name, output.label = name, 'Hair Shadows: ' + label
        output['csw_hair_shadow_output'] = True
        source = next((n for n in tree.nodes if n.type == 'ATTRIBUTE' and n.attribute_name == attribute), None)
        for link in list(output.inputs['Value'].links):
            tree.links.remove(link)
        if constant is None:
            source = source or tree.nodes.new('ShaderNodeAttribute')
            source.attribute_name = attribute
            source.label = 'Hair Shadows: ' + label
            tree.links.new(source.outputs['Fac'], output.inputs['Value'])
            source.location = (-500, -700 if name == aovs[0] else -950)
        else:
            output.inputs['Value'].default_value = constant
            if source and not any(s.is_linked for s in source.outputs):
                tree.nodes.remove(source)
        output.location = (-240, -700 if name == aovs[0] else -950)
    depth = next((n for n in tree.nodes if n.type == 'OUTPUT_AOV' and n.aov_name == aovs[2]), None)
    depth = depth or tree.nodes.new('ShaderNodeOutputAOV')
    depth.aov_name, depth.label = aovs[2], 'Hair Shadows: camera-axis depth'
    depth['csw_hair_shadow_output'] = True
    camera = next((n for n in tree.nodes if n.type == 'CAMERA'), None) or tree.nodes.new('ShaderNodeCameraData')
    camera.location, depth.location = (-500, -1200), (-240, -1200)
    tree.links.new(camera.outputs['View Z Depth'], depth.inputs['Value'])


def execute_hair_shadows(context):
    if not supports_eye_through_hair():
        return False, 'Hair Shadows requires Blender 5.2 or newer.'
    owner, meshes = character_meshes(context)
    if not meshes:
        return False, 'Select a character mesh or its armature.'
    if any(o.mode != 'OBJECT' for o in meshes):
        return False, 'Switch to Object Mode before applying Hair Shadows.'
    masks = {o: character_masks(o) for o in meshes}
    face_count = sum(sum(face) for face, hair in masks.values())
    hair_count = sum(sum(hair) for face, hair in masks.values())
    if not face_count or not hair_count:
        return False, 'Could not identify both facial skin and hair. Use Face / Hair / Bangs material names on the selected character.'
    scope = owner.get('csw_hair_shadow_id')
    if scope and any(o != owner and o.get('csw_hair_shadow_id') == scope for o in bpy.data.objects):
        # Blender duplicates custom properties with a rig. Retain the group
        # belonging to its original owner and give a duplicate fresh passes.
        tree = get_or_create_compositor_tree(context.scene)
        existing = next((n for n in tree.nodes if n.get('csw_scope') == scope and n.get('csw_effect') == 'hair'), None)
        if existing is None or existing.get('csw_owner') != owner:
            scope = None
    scope = scope or uuid.uuid4().hex[:10]
    owner['csw_hair_shadow_id'] = scope
    tree = get_or_create_compositor_tree(context.scene)
    node = next((n for n in tree.nodes if n.get('csw_effect') == 'hair' and n.get('csw_scope') == scope), None)
    aovs, renamed = _readable_aovs(owner, meshes, context.view_layer, node, scope)
    attrs = [f'csw_hs_{scope}_{part}' for part in ('face', 'hair')]
    material_copies = {}
    mesh_set = set(meshes)
    # Don't request attributes for constant masks: complex ZZZ shaders already
    # use most GPU vertex inputs. A hair material needs no facial attribute.
    material_values = {}
    for obj in meshes:
        for p in obj.data.polygons:
            mat = obj.material_slots[p.material_index].material if p.material_index < len(obj.material_slots) else None
            if mat:
                values = material_values.setdefault(mat, [set(), set()])
                for index in (0, 1):
                    values[index].add(masks[obj][index][p.index])
    for obj in meshes:
        # Linked duplicates must not receive another character's face masks.
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        face, hair = masks[obj]
        _attribute(obj.data, attrs[0], face)
        _attribute(obj.data, attrs[1], hair)
        used_slots = {p.material_index for p in obj.data.polygons if face[p.index] or hair[p.index]}
        for index, slot in enumerate(obj.material_slots):
            mat = slot.material
            if mat is None:
                continue
            # Repair stale writers on materials misclassified by older runs,
            # including Eye Through Hair duplicates of the facial material.
            stale = mat.node_tree and any(n.type == 'OUTPUT_AOV' and n.aov_name in {*aovs, *renamed} for n in mat.node_tree.nodes)
            if index not in used_slots and not stale:
                continue
            if mat not in material_copies:
                external = any(o not in mesh_set and any(s.material == mat for s in o.material_slots) for o in bpy.data.objects if o.type == 'MESH')
                isolated = mat.copy() if external else mat
                material_copies[mat] = isolated
                values = material_values.get(mat, [set(), set()])
                constants = [next(iter(v)) if len(v) == 1 else 0.0 if not v else None for v in values]
                _aov_material(isolated, aovs, attrs, constants, renamed)
            obj.material_slots[index].material = material_copies[mat]
    for name in aovs:
        aov = next((a for a in context.view_layer.aovs if a.name == name), None) or context.view_layer.aovs.add()
        aov.name, aov.type = name, 'VALUE'
    order_aov_passes(context.scene, context.view_layer)
    context.view_layer.use_pass_z = True
    tree = get_or_create_compositor_tree(context.scene)
    rl = render_layer(tree, context.scene, context.view_layer)
    node = next((n for n in tree.nodes if n.get('csw_effect') == 'hair' and n.get('csw_scope') == scope), None)
    # Upgrade the reference setup rather than applying the effect twice.
    reference = next((n for n in tree.nodes if n.type == 'GROUP' and n.node_tree
                      and n.node_tree.name == 'Sandrone Hair Shadow - Danica'), None) if any(o.data.attributes.get('hair_shadow_face') for o in meshes) else None
    if node is None:
        if reference:
            node = reference
            _replace_group(node, _group(scope, context.scene))
        else:
            node = tree.nodes.new('CompositorNodeGroup')
            node.node_tree = _group(scope, context.scene)
        node.name = 'Hair Shadows - ' + owner.name
        node.label, node['csw_effect'], node['csw_scope'] = 'Hair Shadows', 'hair', scope
        node['csw_owner'] = owner
    elif node.node_tree.get('csw_version', 0) < 4:
        _replace_group(node, _group(scope, context.scene))
    for pass_name, input_name in zip(aovs, ('face_mask', 'hair_mask', 'Depth')):
        output = rl.outputs.get(pass_name)
        if output is None:
            return False, 'Could not expose the hair-shadow render passes.'
        tree.links.new(output, node.inputs[input_name])
    tree.links.new(rl.outputs['Depth'], node.inputs['Camera Distance'])
    insert_effect(tree, context.scene, rl, node)
    for s in node.inputs:
        s.hide = s.name not in ('Offset X', 'Offset Y', 'Shadow Tint', 'Strength')
    node.outputs['Shadow Mask'].hide = True
    set_viewport_compositor_always(context)
    return True, f'Hair Shadows applied to {owner.name}. Adjust Offset X, Offset Y, Shadow Tint and Strength in the compositor group.'


class CSW_OT_HairShadows(bpy.types.Operator):
    bl_idname = 'setup_wizard.hair_shadows'
    bl_label = 'Hair Shadows'
    bl_description = 'Apply the original Sandrone hair shadow group with Offset X, Offset Y, Shadow Tint and Strength'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return supports_eye_through_hair() and context.active_object is not None and context.mode == 'OBJECT'

    def execute(self, context):
        success, message = execute_hair_shadows(context)
        self.report({'INFO'} if success else {'ERROR'}, message)
        return {'FINISHED'} if success else {'CANCELLED'}
