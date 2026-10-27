"""Adapt embedded PMX data to the same game setup used by FBX models."""

import json
import os
import re
import uuid

import bpy
from mathutils import Vector


def _part(name):
    exact = {
        '颜': ('Face', 'Face'), '颜2': ('Face', 'Face'),
        '顔': ('Face', 'Face'), '顔2': ('Face', 'Face'),
        '白目': ('Face', 'Face'), '口舌': ('Face', 'Face'),
        '齿': ('Face', 'Face'), '歯': ('Face', 'Face'),
        '睫眉': ('Brow', 'Brow'), '眉': ('Brow', 'Brow'),
        'まつげ': ('Brow', 'Brow'), '目': ('Pupil', 'Pupil'),
        '瞳': ('Pupil', 'Pupil'), '星目': ('EyeStar', 'Pupil'),
        '髮': ('Hair', 'Hair'), '髪': ('Hair', 'Hair'), '发': ('Hair', 'Hair'),
        '髮+': ('Eff_HairSheen', 'Hair'), '髮饰': ('HairAccessory', 'Hair'),
        '体': ('Body', 'Body'), '肌': ('Skin', 'Body'), '肌2': ('Skin2', 'Body'),
        '裙': ('Skirt', 'Body'), '袖': ('Sleeves', 'Body'),
        '袖饰': ('SleeveAccessories', 'Body'), '披肩': ('Shawl', 'Body'),
        '披肩饰': ('ShawlAccessories', 'Body'), '披风': ('Cape', 'Body'),
        '披风饰': ('CapeAccessories', 'Body'), '带': ('Ribbons', 'Body'),
        '眼罩': ('Blindfold', 'Body'), '鞋': ('Shoes', 'Body'),
        '头饰': ('HeadAccessories', 'Body'), '头饰2': ('HeadAccessories2', 'Body'),
    }
    if name in exact:
        return exact[name]
    low = name.lower()
    for word, part in (('face', 'Face'), ('hair', 'Hair'), ('pupil', 'Pupil'),
                       ('iris', 'Pupil'), ('brow', 'Brow'), ('body', 'Body')):
        if word in low:
            return (part, part)
    return ('Part' + re.sub(r'\W', '', name), 'Body')


def prepare_pmx_for_setup(context, game_type):
    from setup_wizard.character_rig_setup.mmd_rig import is_mmd_armature
    armature = context.object
    if not is_mmd_armature(armature):
        raise RuntimeError('The PMX importer did not select its armature.')
    model_id = uuid.uuid4().hex
    context.scene['setup_wizard_pmx_model_id'] = model_id
    objects = [armature] + list(armature.children_recursive)
    meshes = [obj for obj in objects if obj.type == 'MESH']
    records = {}
    for obj in objects:
        obj['_setup_wizard_model_id'] = model_id
    canonical = {}
    for obj in meshes:
        for slot in obj.material_slots:
            mat = slot.material
            if not mat:
                continue
            original = mat.get('setup_wizard_pmx_original', mat.name)
            part, kind = _part(original)
            image_node = mat.node_tree.nodes.get('mmd_base_tex') if mat.node_tree else None
            image = image_node.image if image_node else None
            # PMX material names may differ while sharing the same face atlas.
            signature = (part, image.name if image else '')
            if signature in canonical:
                slot.material = canonical[signature]
                continue
            if part in records and records[part]['image'] != (image.name if image else ''):
                part += str(len(records))
            mat['setup_wizard_pmx_original'] = original
            mat['setup_wizard_pmx_part'] = part
            mat.name = f'Avatar_PMX_{part}'
            additive = (getattr(mat.mmd_material, 'sphere_texture_type', '0') == '2'
                        and mat.node_tree.nodes.get('mmd_sphere_tex') is not None
                        and (part.endswith('HairSheen') or original.endswith('+')))
            records[part] = dict(kind=kind, image=image.name if image else '',
                                 original=original, additive=additive)
            canonical[signature] = mat
        if obj.data.uv_layers and not obj.data.uv_layers.get('UV0'):
            obj.data.uv_layers[0].name = 'UV0'
        if not obj.data.uv_layers.get('UV1'):
            uv = obj.data.uv_layers.new(name='UV1')
            original_uv = obj.data.uv_layers[0]
            coords = [0.0] * (len(original_uv.data) * 2)
            original_uv.data.foreach_get('uv', coords)
            uv.data.foreach_set('uv', coords)
        _normalize_morphs(obj)
    context.scene['setup_wizard_pmx_materials'] = json.dumps(records, ensure_ascii=False)
    if not getattr(context.scene.character_rigger_props, 'disable_rigging', False):
        _normalize_armature(context, armature, meshes)
    # FBX inputs already have separate body, face, hair and pupil objects.
    # Split before pupil classification: a single PMX mesh with a pupil slot
    # must never be mistaken for an entire eye and have its slots replaced.
    for obj in meshes:
        materials = []
        indices = {}
        for i, material in enumerate(obj.data.materials):
            if material not in materials:
                materials.append(material)
            indices[i] = materials.index(material)
        polygon_slots = [indices[polygon.material_index] for polygon in obj.data.polygons]
        obj.data.materials.clear()
        for material in materials:
            obj.data.materials.append(material)
        for polygon, slot_index in zip(obj.data.polygons, polygon_slots):
            polygon.material_index = slot_index
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        if len(materials) > 1:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.separate(type='MATERIAL')
            bpy.ops.object.mode_set(mode='OBJECT')
        for part_mesh in context.selected_objects:
            # MMD morph metadata can retain an ID reference to the original
            # mesh. The game rig must be free to apply transforms to it.
            if part_mesh.data.users > 1:
                part_mesh.data = part_mesh.data.copy()
            used_slots = {polygon.material_index for polygon in part_mesh.data.polygons}
            for index in reversed(range(len(part_mesh.data.materials))):
                if index not in used_slots:
                    part_mesh.data.materials.pop(index=index)
            material = next((m for m in part_mesh.data.materials if m), None)
            if material:
                part_mesh.name = material['setup_wizard_pmx_part']
                if records[part_mesh.name].get('additive'):
                    # This duplicate shell only carries MMD's sphere-map
                    # highlight. The game hair shader supplies its own specular
                    # response; drawing the old shell as opaque covers it.
                    part_mesh['setup_wizard_pmx_sphere_overlay'] = True
                    part_mesh.hide_render = True
                    part_mesh.hide_set(True)
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    context.view_layer.objects.active = armature
    name = os.path.basename(context.scene['setup_wizard_imported_model_dir']).title()
    armature.name = f'Avatar_{name}'
    armature.data.name = armature.name
    armature['setup_wizard_pmx_normalized'] = True


def _normalize_morphs(obj):
    if not obj.data.shape_keys:
        return
    aliases = {
        'あ': 'Mouth_A01', 'あ２': 'Mouth_A02', 'い': 'Mouth_Smile01',
        'う': 'Mouth_Neko01', 'え': 'Mouth_Smile02', 'お': 'Mouth_Open01',
        'にやり': 'Mouth_Doya01', 'ω': 'Mouth_Neko02', 'ぺろっ': 'Mouth_Pero01',
        'てへぺろ': 'Mouth_Pero02', '口角上げ': 'Mouth_Up',
        '口角下げ': 'Mouth_Down', 'まばたき': 'Eye_Ha', '笑い': 'Eye_WinkB',
        'ウィンク': 'Eye_WinkA_L', 'ウィンク右': 'Eye_WinkA_R',
        'ウィンク２': 'Eye_WinkB_L', 'ウィンク２右': 'Eye_WinkB_R',
        'じと目': 'Eye_Jito', 'ジト目': 'Eye_Tired', '悲しむ': 'Eye_Wail',
        '怒り目': 'Eye_Hostility', '下眼上': 'Eye_Lowereyelid',
        '困る左': 'Brow_Trouble_L', '困る右': 'Brow_Trouble_R',
        'にこり左': 'Brow_Smily_L', 'にこり右': 'Brow_Smily_R',
        '怒り左': 'Brow_Angry_L', '怒り右': 'Brow_Angry_R',
        '恥ずかしい左': 'Brow_Shy_L', '恥ずかしい右': 'Brow_Shy_R',
        '上左': 'Brow_Up_L', '上右': 'Brow_Up_R',
        '下左': 'Brow_Down_L', '下右': 'Brow_Down_R',
    }
    for key in obj.data.shape_keys.key_blocks:
        if key.name in aliases:
            key.name = aliases[key.name]


def _normalize_armature(context, armature, meshes):
    from setup_wizard.character_rig_setup.mmd_rig import _mapping
    mapping = _mapping(armature)
    from mathutils import Matrix
    # PMX IK and append-transform constraints target the old control skeleton.
    # The standard game rig supplies the replacement controls and twist setup.
    for pb in armature.pose.bones:
        for constraint in list(pb.constraints):
            pb.constraints.remove(constraint)
        pb.matrix_basis = Matrix.Identity(4)
    armature.animation_data_clear()
    rename = {
        'spine': 'Bip001 Pelvis', 'spine.001': 'Bip001 Spine',
        'spine.002': 'Bip001 Spine1', 'spine.003': 'Bip001 Spine2',
        'spine.004': 'Bip001 Neck', 'spine.006': 'Bip001 Head',
    }
    for side in ('L', 'R'):
        for part, bip in (('shoulder', 'Clavicle'), ('upper_arm', 'UpperArm'),
                           ('forearm', 'Forearm'), ('hand', 'Hand'),
                           ('thigh', 'Thigh'), ('shin', 'Calf'), ('foot', 'Foot'), ('toe', 'Toe0')):
            rename[f'{part}.{side}'] = f'Bip001 {side} {bip}'
        rename[f'eye.{side}'] = f'+EyeBone {side} A02'
        for finger, index in (('thumb', 0), ('f_index', 1), ('f_middle', 2), ('f_ring', 3), ('f_pinky', 4)):
            for i in range(1, 4):
                rename[f'{finger}.{i:02d}.{side}'] = f'Bip001 {side} Finger{index}' + (str(i-1) if i > 1 else '')
    # Semi-standard D leg bones hold skin weights, but the humanoid chain
    # must use the primary leg bones. Merge those weights before removal.
    duplicates = {}
    for side in ('L', 'R'):
        for base in ('足', 'ひざ', '足首'):
            duplicate, original = f'{base}D.{side}', f'{base}.{side}'
            if duplicate in armature.data.bones and original in armature.data.bones:
                duplicates[duplicate] = original
    for obj in meshes:
        for old, new in duplicates.items():
            group = obj.vertex_groups.get(old)
            if group is None:
                continue
            target = obj.vertex_groups.get(new) or obj.vertex_groups.new(name=new)
            for vertex in obj.data.vertices:
                weight = sum(g.weight for g in vertex.groups if g.group in (group.index, target.index))
                if weight:
                    target.add([vertex.index], min(weight, 1.0), 'REPLACE')
            obj.vertex_groups.remove(group)
    used = set()
    for target, old in mapping.items():
        if old and old not in used:
            armature.data.bones[old].name = rename[target]
            used.add(old)
    context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    bones = armature.data.edit_bones
    for old in duplicates:
        if old in bones:
            bone = bones[old]
            for child in list(bone.children):
                child.parent = bones.get(rename[next(k for k,v in mapping.items() if v == duplicates[old])])
            bones.remove(bone)
    chain = ['Bip001 Pelvis', 'Bip001 Spine', 'Bip001 Spine1', 'Bip001 Spine2', 'Bip001 Neck', 'Bip001 Head']
    for i, name in enumerate(chain):
        if name not in bones:
            bone = bones.new(name)
            previous, following = bones[chain[i-1]], bones[chain[i+1]]
            bone.head = previous.head.lerp(following.head, 0.5)
            bone.tail = following.head
        if i:
            bones[name].use_connect = False
            bones[name].parent = bones[chain[i-1]]
    for side in ('L', 'R'):
        for names, parent in ((['Clavicle', 'UpperArm', 'Forearm', 'Hand'], 'Bip001 Spine2'),
                               (['Thigh', 'Calf', 'Foot', 'Toe0'], 'Bip001 Pelvis')):
            for part in names:
                name = f'Bip001 {side} {part}'
                if name in bones:
                    bones[name].use_connect = False
                    bones[name].parent = bones[parent]
                    parent = name
        eye = bones.get(f'+EyeBone {side} A02')
        if eye:
            eye.use_connect = False
            base = bones.new(f'+EyeBone {side} A01')
            base.head = eye.head
            base.tail = eye.head + Vector((0, -0.03, 0))
            base.parent = bones['Bip001 Head']
            eye.parent = base
    bpy.ops.object.mode_set(mode='OBJECT')


def replace_pmx_materials(context, material_names):
    records = json.loads(context.scene.get('setup_wizard_pmx_materials', '{}'))
    model_id = context.scene.get('setup_wizard_pmx_model_id')
    for obj in context.scene.objects:
        if obj.type != 'MESH' or obj.get('_setup_wizard_model_id') != model_id:
            continue
        for slot in obj.material_slots:
            old = slot.material
            part = old.get('setup_wizard_pmx_part') if old else None
            if part not in records:
                continue
            record = records[part]
            template = bpy.data.materials.get(material_names.MATERIAL_PREFIX + record['kind'])
            if template is None:
                template = bpy.data.materials.get(material_names.BODY)
            name = material_names.MATERIAL_PREFIX + part
            material = bpy.data.materials.get(name)
            if material is None:
                material = template.copy()
                material.name = name
            material['setup_wizard_pmx_part'] = part
            material['setup_wizard_pmx_model_id'] = model_id
            slot.material = material
    apply_pmx_textures(context)


def apply_pmx_textures(context):
    from setup_wizard.texture_import_setup.texture_importer_types import find_all_image_nodes_by_category
    records = json.loads(context.scene.get('setup_wizard_pmx_materials', '{}'))
    model_id = context.scene.get('setup_wizard_pmx_model_id')
    if not records:
        return
    lightmap = bpy.data.images.get('PMX Neutral Packed Lightmap')
    if lightmap is None:
        lightmap = bpy.data.images.new('PMX Neutral Packed Lightmap', width=4, height=4, alpha=True)
        lightmap.pixels[:] = [0.0, 1.0, 0.0, 0.0] * 16
        lightmap.colorspace_settings.name = 'Non-Color'
        lightmap.alpha_mode = 'CHANNEL_PACKED'
        lightmap.pack()
    for material in bpy.data.materials:
        part = material.get('setup_wizard_pmx_part')
        if (part not in records or not material.node_tree
                or material.get('setup_wizard_pmx_model_id') != model_id):
            continue
        image = bpy.data.images.get(records[part]['image'])
        if image is None:
            continue
        image.colorspace_settings.name = 'sRGB'
        for node in find_all_image_nodes_by_category(material.node_tree, 'diffuse'):
            node.image = image
        # MMD toon textures are not Genshin packed material-ID/AO maps.
        # A neutral packed map avoids interpreting diffuse colors as IDs.
        for node in find_all_image_nodes_by_category(material.node_tree, 'lightmap'):
            if part not in ('Face', 'Brow', 'Pupil', 'EyeStar'):
                node.image = lightmap
        for node in material.node_tree.nodes:
            if node.type != 'GROUP':
                continue
            # PMX does not ship the exported game's ramps or vertex AO.
            # Use the shader's normal lighting colors when these are absent.
            for name, value in (('Toggle Shadow Ramp', False), ('Toggle Vertex Color AO', False),
                                ('Toggle Alpha', True), ('Emit / Transparency', True)):
                socket = node.inputs.get(name)
                if socket:
                    socket.default_value = value
            for socket in node.inputs:
                if socket.name.startswith(('Cold Shadow Color', 'Warm Shadow Color')):
                    socket.default_value = (0.8, 0.8, 0.8, 1.0)
        if records[part].get('additive') and 'Outlines' not in material.name:
            _adapt_additive_layer(material)


def _adapt_additive_layer(material):
    """Keep black areas of an MMD additive sphere layer transparent."""
    nodes, links = material.node_tree.nodes, material.node_tree.links
    if nodes.get('PMX Additive Layer'):
        return
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output), None)
    texture = nodes.get('Main_Diffuse')
    if output is None or texture is None or not output.inputs['Surface'].links:
        return
    shader = output.inputs['Surface'].links[0].from_socket
    transparent = nodes.new('ShaderNodeBsdfTransparent')
    mask = nodes.new('ShaderNodeRGBToBW')
    mix = nodes.new('ShaderNodeMixShader')
    mix.name = 'PMX Additive Layer'
    links.new(texture.outputs['Color'], mask.inputs[0])
    links.new(mask.outputs[0], mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(shader, mix.inputs[2])
    links.new(mix.outputs[0], output.inputs['Surface'])


def bind_pmx_face_morphs(context, rig):
    """Bind available PMX expressions without requiring absent FBX morphs."""
    if not rig or not rig.get('setup_wizard_pmx_normalized'):
        return
    controls = {
        'Mouth_A01': ('Mouth-Control', 'LOC_Y', -1.33),
        'Mouth_Open01': ('Mouth-Control', 'LOC_Y', 1.33),
        'Mouth_Smile01': ('Mouth-Smile1-Control', 'LOC_X', 1.67),
        'Mouth_Smile02': ('Mouth-Smile2-Control', 'LOC_X', 1.67),
        'Mouth_Doya01': ('Mouth-Doya1-Control', 'LOC_X', 1.67),
        'Mouth_Neko01': ('Mouth-Neko1-Control', 'LOC_X', 1.67),
        'Mouth_Pero01': ('Mouth-Pero1-Control', 'LOC_X', 1.67),
        'Mouth_Pero02': ('Mouth-Pero2-Control', 'LOC_X', 1.67),
        'Eye_Ha': ('Eye-Ha-Control', 'LOC_Y', -2.22),
        'Eye_Jito': ('Eye-Jito-Control', 'LOC_Y', -2.22),
        'Eye_Tired': ('Eye-Tired-Control', 'LOC_Y', -2.22),
        'Eye_Wail': ('Eye-Wail-Control', 'LOC_Y', -2.22),
        'Eye_Hostility': ('Eye-Hostility-Control', 'LOC_Y', -2.22),
        'Eye_Lowereyelid': ('Eye-LowerEyelid-Control', 'LOC_Y', -2.22),
    }
    for side in ('L', 'R'):
        for letter in ('A', 'B'):
            controls[f'Eye_Wink{letter}_{side}'] = (f'Wink{letter}-{side}-Invis', 'LOC_Y', -.82)
        controls[f'Brow_Up_{side}'] = (f'Brow-{side}-Control', 'LOC_Y', 4)
        controls[f'Brow_Down_{side}'] = (f'Brow-{side}-Control', 'LOC_Y', -4)
        for morph, control in (('Trouble', 'Trouble'), ('Smily', 'Smily'), ('Angry', 'Angry'), ('Shy', 'Shy')):
            controls[f'Brow_{morph}_{side}'] = (f'Brow-{control}-{side}-Control', 'LOC_X', 2)
    for obj in context.scene.objects:
        if obj.type != 'MESH' or not obj.data.shape_keys or obj.find_armature() != rig:
            continue
        if obj.get('setup_wizard_pmx_sphere_overlay'):
            obj.hide_render = True
            obj.hide_set(True)
        for key in obj.data.shape_keys.key_blocks:
            config = controls.get(key.name)
            if not config or config[0] not in rig.pose.bones:
                continue
            bone, axis, amount = config
            driver = key.driver_add('value').driver
            for variable in list(driver.variables):
                driver.variables.remove(variable)
            var = driver.variables.new()
            var.name = 'bone'
            var.type = 'TRANSFORMS'
            var.targets[0].id = rig
            var.targets[0].bone_target = bone
            var.targets[0].transform_type = axis
            var.targets[0].transform_space = 'LOCAL_SPACE'
            driver.type = 'SCRIPTED'
            driver.expression = f'max(0, min(1, bone * {amount}))'
