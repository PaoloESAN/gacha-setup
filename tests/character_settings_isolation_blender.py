"""Blender --background --factory-startup --python-exit-code 1 --python this_file.

Exercise real bundled shaders: per-character writes/pulls, shared materials,
unrigged targets, library Append/Link, render callbacks and shader animation.
"""
import os
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'tests/.runtime/character-settings-isolation'
RUNTIME.mkdir(parents=True, exist_ok=True)
os.environ['PYTEST_VERSION'] = 'blender-regression'
sys.path.insert(0, str(ROOT))
original_resource = bpy.utils.user_resource
def resource(kind, path='', create=False):
    if kind in {'CONFIG', 'SCRIPTS'}:
        destination = RUNTIME / kind / path
        destination.mkdir(parents=True, exist_ok=True)
        return str(destination)
    return original_resource(kind, path=path, create=create)
bpy.utils.user_resource = resource

from setup_wizard.ui import character_settings_utils as cu
from setup_wizard.ui import gi_ui_setup_wizard_menu as gi
from setup_wizard.ui import hsr_ui_setup_wizard_menu as hsr
from setup_wizard.ui import zzz_ui_setup_wizard_menu as zzz
from setup_wizard.ui import ake_ui_setup_wizard_menu as ake
from setup_wizard.ui import hi3_character_settings as hi3
from setup_wizard.ui import pgr_character_settings as pgr
from setup_wizard.ui import hna_character_settings as hna
from setup_wizard import wuwa_operations as ww
from setup_wizard.utils.modifier_utils import get_modifier_property, set_modifier_property

CASES = [
    ('gi', 'GENSHIN_IMPACT', 'gi/HoYoverse - PrimoToon v4.0.blend', 'HoYoverse - Genshin Face', 'Blush Strength', 'gi_blush_strength', gi.register_gi_properties, gi.pull_gi_panel_values),
    ('ww', 'WUTHERING_WAVES', 'wuwa/Gustling Waters.blend', 'WW - Face', 'Blush Intensity', 'ww_blush_value', ww.register_wuwa_properties, ww.pull_wuwa_panel_values),
    ('hsr', 'HONKAI_STAR_RAIL', 'hsr/StellarToonV1.1.blend', 'StellarToon - Face', 'Expression Cheek Intensity', 'hsr_exp_cheek', hsr.register_hsr_properties, hsr.pull_hsr_panel_values),
    ('zzz', 'ZENLESS_ZONE_ZERO', "zzz/Kythera's ZZZ Shader V2.blend", "Kythera's ZZZ Face Shader V2", 'Lit Brightness', 'zzz_lit_brightness', zzz.register_zzz_properties, zzz.pull_zzz_panel_values),
    ('ake', 'ARKNIGHTS_ENDFIELD', 'ake/AKE.blend', 'face_01', 'SmoothnessMax', 'ake_smoothness_max', ake.register_ake_properties, ake.pull_ake_panel_values),
    ('hi3', 'HONKAI_IMPACT_3RD', 'hi3/betterhi3rdshader.blend', 'ImpactToon - Face', None, None, None, None),
    ('pgr', 'PUNISHING_GRAY_RAVEN', 'pgr/Jared_PGR_Shader_4.4_compat.blend', 'PGR - Face', None, None, None, None),
    ('hna', 'HONKAI_NEXUS_ANIMA', 'hna/HSR_Shader_1.07.blend', 'HSR - Face', None, None, None, None),
]

def select(obj):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    if obj:
        obj.select_set(True)
    cu.invalidate_caches()

def primary_socket(mesh, name):
    return next(n.inputs[name] for mat in mesh.material_slots if mat.material
                for n in mat.material.node_tree.nodes if n.type == 'GROUP' and name in n.inputs)

def materials(mesh):
    return [s.material for s in mesh.material_slots if s.material]

def property_tree(mesh):
    return next(n.node_tree for m in materials(mesh) for n in m.node_tree.nodes
                if n.type == 'GROUP' and n.node_tree and any(
                    k in n.node_tree.name.lower() for k in ['global material properties', 'globalproperties']))

def prepare(case, arm, mesh):
    if case[0] == 'hi3':
        return hi3.prepare_character_settings(arm, materials(mesh))
    if case[0] == 'pgr':
        return pgr.prepare_character_settings(arm, materials(mesh))

def get(case, arm, mesh):
    if case[0] == 'hi3':
        return property_tree(mesh).nodes['Global Properties'].inputs['Exp Blush Intensity'].default_value
    if case[0] == 'pgr':
        return pgr._get_power(property_tree(mesh))
    if case[0] == 'hna':
        return hna.get_rim_intensity(arm)
    if case[0] == 'hsr':
        return property_tree(mesh).nodes['Group Output'].inputs['Expression Cheek Intensity'].default_value
    return primary_socket(mesh, case[4]).default_value

def set_value(case, arm, mesh, value):
    select(arm)
    prepare(case, arm, mesh)
    if case[0] == 'hi3':
        property_tree(mesh).nodes['Global Properties'].inputs['Exp Blush Intensity'].default_value = value
    elif case[0] == 'pgr':
        pgr._set_power(property_tree(mesh), value)
    elif case[0] == 'hna':
        hna.set_rim_intensity(arm, value)
    else:
        setattr(bpy.context.scene, case[5], value)

def character(name, game, mat, collection=None, data=None):
    coll = collection or bpy.context.scene.collection
    arm = bpy.data.objects.new(name + '_Rig', bpy.data.armatures.new(name + '_RigData'))
    arm['gacha_game'] = game
    coll.objects.link(arm)
    if data is None:
        data = bpy.data.meshes.new(name + '_MeshData')
        data.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
        for uv_name, coordinates in [
            ('UV0', [(0, 0), (1, 0), (1, 1), (0, 1)]),
            ('UV1', [(1, 0), (0, 0), (0, 1), (1, 1)]),
        ]:
            uv = data.uv_layers.new(name=uv_name)
            for corner, coordinate in zip(uv.data, coordinates):
                corner.uv = coordinate
        data.uv_layers.active_index = 1
        data.uv_layers['UV0'].active_render = True
        data.normals_split_custom_set([(0.1, 0.0, 0.9949874)] * len(data.loops))
        data.materials.append(mat)
    mesh = bpy.data.objects.new(name + '_Face', data)
    mesh.parent = arm
    coll.objects.link(mesh)
    return arm, mesh

def close(a, b):
    assert abs(a - b) < 1e-4, (a, b)

def surface_snapshot(mesh):
    data = mesh.data
    return (
        tuple(tuple(v.co) for v in data.vertices),
        tuple((uv.name, uv.active_render, tuple(tuple(c.uv) for c in uv.data))
              for uv in data.uv_layers),
        data.uv_layers.active_index,
        tuple(tuple(n.vector) for n in data.corner_normals),
    )

def shared_outline_fixture(pairs, mat):
    tree = bpy.data.node_groups.new('Outlines Settings Fixture', 'GeometryNodeTree')
    tree.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    tree.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    mask = tree.interface.new_socket(name='Face Mask', in_out='INPUT', socket_type='NodeSocketMaterial')
    width = tree.interface.new_socket(name='Outline Thickness', in_out='INPUT', socket_type='NodeSocketFloat')
    inp = tree.nodes.new('NodeGroupInput'); out = tree.nodes.new('NodeGroupOutput')
    nested = bpy.data.node_groups.new('Nested Outline Materials', 'GeometryNodeTree')
    nested.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    nested.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    ni = nested.nodes.new('NodeGroupInput'); no = nested.nodes.new('NodeGroupOutput')
    material = nested.nodes.new('GeometryNodeSetMaterial')
    material.inputs['Material'].default_value = mat
    nested.links.new(ni.outputs['Geometry'], material.inputs['Geometry'])
    nested.links.new(material.outputs['Geometry'], no.inputs['Geometry'])
    node = tree.nodes.new('GeometryNodeGroup'); node.node_tree = nested
    selection = tree.nodes.new('GeometryNodeMaterialSelection')
    tree.links.new(inp.outputs['Face Mask'], selection.inputs['Material'])
    capture = tree.nodes.new('GeometryNodeStoreNamedAttribute')
    capture.data_type = 'BOOLEAN'; capture.domain = 'FACE'
    capture.inputs['Name'].default_value = 'settings_material_mask_matches'
    tree.links.new(selection.outputs['Selection'], capture.inputs['Value'])
    tree.links.new(inp.outputs['Geometry'], capture.inputs['Geometry'])
    tree.links.new(capture.outputs['Geometry'], node.inputs['Geometry'])
    tree.links.new(node.outputs['Geometry'], out.inputs['Geometry'])
    for arm, mesh in pairs:
        mod = mesh.modifiers.new('Outlines Fixture', 'NODES'); mod.node_group = tree
        set_modifier_property(mod, mask.identifier, mat)
        set_modifier_property(mod, width.identifier, .25)
    return mask.identifier, width.identifier

def nested_material(mesh):
    tree = mesh.modifiers['Outlines Fixture'].node_group
    nested = next(n.node_tree for n in tree.nodes if n.type == 'GROUP')
    return next(n.inputs['Material'].default_value for n in nested.nodes if n.type == 'SET_MATERIAL')

def assert_evaluated_material_mask(mesh):
    mesh.update_tag(); bpy.context.view_layer.update()
    evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    data = evaluated.to_mesh()
    try:
        values = data.attributes.get('settings_material_mask_matches')
        assert values is not None and len(values.data), mesh.name
        assert all(v.value for v in values.data), (
            mesh.name, 'Geometry Nodes did not match the isolated material')
    finally:
        evaluated.to_mesh_clear()

def palette(mesh):
    tree = property_tree(mesh)
    return next(n for n in tree.nodes if n.type == 'GROUP' and 'color palette' in n.node_tree.name.lower())

def extra_controls(case, a, b):
    scene = bpy.context.scene
    key = case[0]
    if key == 'ww':
        before = tuple(palette(b[1]).inputs['Custom Ambient'].default_value)
        select(a[0]); scene.ww_light_mode = '6'; scene.ww_amb_color = (.2, .3, .4)
        close(palette(a[1]).inputs['Custom Ambient'].default_value[0], .2)
        assert tuple(palette(b[1]).inputs['Custom Ambient'].default_value) == before
        assert palette(a[1]).node_tree != palette(b[1]).node_tree
        out_a = property_tree(a[1]).nodes['Global Properties']
        out_b = property_tree(b[1]).nodes['Global Properties']
        original = out_b.inputs['Fresnel Scale'].default_value
        scene.ww_fresnel_scale = 3.5
        close(out_a.inputs['Fresnel Scale'].default_value, 3.5)
        close(out_b.inputs['Fresnel Scale'].default_value, original)
        old = primary_socket(b[1], 'Face Shadows Softness').default_value
        scene.ww_face_shadow_softness_value = .15
        close(primary_socket(a[1], 'Face Shadows Softness').default_value, .15)
        close(primary_socket(b[1], 'Face Shadows Softness').default_value, old)
        scene.ww_catch_shadows = True
        assert out_a.inputs['Catch Shadows'].default_value
        width = next(s.identifier for s in a[1].modifiers['Outlines Fixture'].node_group.interface.items_tree
                     if s.item_type == 'SOCKET' and s.name == 'Outline Thickness')
        scene.ww_outline_thickness = .7
        close(get_modifier_property(a[1].modifiers['Outlines Fixture'], width), .7)
        close(get_modifier_property(b[1].modifiers['Outlines Fixture'], width), .25)
        select(b[0]); ww.pull_wuwa_panel_values(scene, bpy.context, force=True)
        close(scene.ww_outline_thickness, .25)
        close(scene.ww_face_shadow_softness_value, old)
        close(out_a.inputs['Fresnel Scale'].default_value, 3.5)
        close(primary_socket(a[1], 'Blush Intensity').default_value, .4)
        with bpy.data.libraries.load(str(ROOT / 'setup_wizard/shaders/wuwa/Gustling Waters.blend'), link=False) as (src, dst):
            dst.materials = ['WW - ResonatorStar', 'WW - Main', 'WW - Outlines']
        stars, alpha, outline = dst.materials
        alpha.name = 'WW Alpha Body Fixture'
        extras = []
        for arm, mesh in [a, b]:
            obj = bpy.data.objects.new(arm.name + '_Extras', bpy.data.meshes.new(arm.name + '_ExtrasData'))
            obj.parent = arm; scene.collection.objects.link(obj)
            for mat in [stars, alpha, outline]:
                obj.data.materials.append(mat)
            extras.append(obj)
        def extra_socket(index, name):
            return primary_socket(extras[index], name)
        old_star = bool(extra_socket(1, 'Switch to Ult').default_value)
        select(a[0])
        for cls in [ww.WW_OT_ToggleStarMotion, ww.WW_OT_ToggleHairTrans]:
            bpy.utils.register_class(cls)
        assert bpy.ops.wuthering_waves.toggle_star_motion() == {'FINISHED'}
        assert bool(extra_socket(0, 'Switch to Ult').default_value) != old_star
        assert bool(extra_socket(1, 'Switch to Ult').default_value) == old_star
        see_a = next(n for n in a[1].material_slots[0].material.node_tree.nodes
                     if n.type == 'GROUP' and 'see through' in n.node_tree.name.lower())
        see_b = next(n for n in b[1].material_slots[0].material.node_tree.nodes
                     if n.type == 'GROUP' and 'see through' in n.node_tree.name.lower())
        mute_a, mute_b = see_a.mute, see_b.mute
        assert bpy.ops.wuthering_waves.toggle_hair_transparency() == {'FINISHED'}
        assert see_a.mute != mute_a and see_b.mute == mute_b
        alpha_b = extras[1].material_slots[1].material.node_tree.nodes['Group.001']
        old_alpha = alpha_b.mute
        scene.ww_alpha_transparency = False
        assert extras[0].material_slots[1].material.node_tree.nodes['Group.001'].mute
        assert alpha_b.mute == old_alpha
        old_color = tuple(extra_socket(1, 'Outline Color ').default_value)
        scene.ww_outline_mode = 'CUSTOM'; scene.ww_outline_color_1 = (.2, .3, .4)
        close(extra_socket(0, 'Outline Color ').default_value[0], .2)
        assert tuple(extra_socket(1, 'Outline Color ').default_value) == old_color
        # Editing settings during Animate Mode must update/restore the same
        # selected character's full material, including its source references.
        ww.set_animate_mode(True, context=bpy.context, arm=a[0])
        scene.ww_blush_value = .3
        ww.set_animate_mode(False, context=bpy.context, arm=a[0])
        close(primary_socket(a[1], 'Blush Intensity').default_value, .3)
        close(primary_socket(b[1], 'Blush Intensity').default_value, .8)
        scene.ww_blush_value = .4
        for cls in [ww.WW_OT_ToggleStarMotion, ww.WW_OT_ToggleHairTrans]:
            bpy.utils.unregister_class(cls)
    if key == 'gi':
        eyes = []
        eye_materials = []
        for name in ['Durin Pupil One', 'Durin Pupil Two']:
            mat = bpy.data.materials.new(name); mat.use_nodes = True
            mix = mat.node_tree.nodes.new('ShaderNodeMixShader')
            mix.inputs[0].default_value = .2
            eye_materials.append(mat)
        for arm, mesh in [a, b]:
            eye = bpy.data.objects.new(arm.name + '_Pupil', bpy.data.meshes.new(arm.name + '_PupilData'))
            eye.parent = arm; scene.collection.objects.link(eye)
            for mat in eye_materials:
                eye.data.materials.append(mat)
            eyes.append(eye)
        select(a[0]); gi.apply_durin_dark_eyes(bpy.context, True)
        close(eyes[0].material_slots[0].material.node_tree.nodes['Mix Shader'].inputs[0].default_value, 0)
        close(eyes[0].material_slots[1].material.node_tree.nodes['Mix Shader'].inputs[0].default_value, 1)
        close(eyes[1].material_slots[1].material.node_tree.nodes['Mix Shader'].inputs[0].default_value, .2)
        select(None); gi.apply_durin_dark_eyes(bpy.context, False)
        close(eyes[0].material_slots[1].material.node_tree.nodes['Mix Shader'].inputs[0].default_value, 1)
    if key == 'ake':
        # Same custom color on two characters must not be skipped by a global
        # "last applied" cache, and shared shader interface defaults stay put.
        before = primary_socket(b[1], 'BaseColor').default_value[:]
        for arm, mesh in [a, b]:
            select(arm); ake.pull_ake_panel_values(scene, bpy.context, force=True)
            scene.ake_light_mode = '6'; scene.ake_base_color = (.2, .3, .4)
            close(primary_socket(mesh, 'BaseColor').default_value[0], .2)
        close(primary_socket(a[1], 'BaseColor').default_value[0], .2)
    if key == 'zzz':
        from setup_wizard.character_rig_setup.lighting_panel_setup import (
            connect_zzz_lighting_panel, disconnect_zzz_lighting_panel, is_zzz_lighting_panel_connected)
        lp = bpy.data.node_groups.get('ZZZLightPanelAttr')
        if not lp:
            lp = bpy.data.node_groups.new('ZZZLightPanelAttr', 'ShaderNodeTree')
            for name in ['Ambient', 'Lit', 'Shad']:
                lp.interface.new_socket(name=name, in_out='OUTPUT', socket_type='NodeSocketColor')
            lp.nodes.new('NodeGroupOutput')
        for arm, mesh in [a, b]:
            connect_zzz_lighting_panel(materials(mesh))
            assert is_zzz_lighting_panel_connected(materials(mesh))
        disconnect_zzz_lighting_panel([])
        assert is_zzz_lighting_panel_connected(materials(a[1]))
        assert is_zzz_lighting_panel_connected(materials(b[1]))
        disconnect_zzz_lighting_panel(materials(a[1]))
        assert not is_zzz_lighting_panel_connected(materials(a[1]))
        assert is_zzz_lighting_panel_connected(materials(b[1]))
    print('EXTRA_CONTROLS_PASS', key, flush=True)

def shader_animation(case, a, b):
    key = case[0]
    if key == 'hi3':
        socket = property_tree(a[1]).nodes['Global Properties'].inputs['Exp Blush Intensity']
    elif key == 'pgr':
        socket = property_tree(a[1]).nodes['Global Properties'].inputs['Fresnel Power']
    elif key == 'hsr':
        socket = property_tree(a[1]).nodes['Group Output'].inputs['Expression Cheek Intensity']
    elif key == 'hna':
        socket = hna.rim_sockets(a[1].material_slots[0].material)[0]
    else:
        socket = primary_socket(a[1], case[4])
    for frame, value in [(1, .4), (2, .7)]:
        socket.default_value = 30 - value if key == 'pgr' else value
        socket.keyframe_insert('default_value', frame=frame)
    bpy.context.scene.frame_set(2)
    render_without_changes([.7, .8], case, [a, b])
    socket.id_data.animation_data.action = None
    socket.default_value = 29.6 if key == 'pgr' else .4
    print('SHADER_ANIMATION_PASS', key, flush=True)

def render_without_changes(expected, case, pairs):
    scene = bpy.context.scene
    cam = scene.objects.get('TestCamera')
    if not cam:
        cam = bpy.data.objects.new('TestCamera', bpy.data.cameras.new('TestCamera'))
        scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 8
    scene.render.resolution_y = 8
    scene.render.resolution_percentage = 100
    for obj in scene.objects:
        if obj.type == 'MESH':
            obj.hide_render = True
    hooks = [gi.gi_frame_change_handler, ww.wuwa_frame_change_handler, ake.ake_frame_change_handler]
    for hook in hooks:
        bpy.app.handlers.render_init.append(hook)
    # Include both a character and the camera as active render context.
    for active in [pairs[0][0], cam]:
        select(active)
        bpy.ops.render.render()
        for val, (arm, mesh) in zip(expected, pairs):
            close(get(case, arm, mesh), val)
    for hook in hooks:
        bpy.app.handlers.render_init.remove(hook)

for case in CASES:
    key, game, shader, mat_name, socket_name, prop, register, pull = case
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cu.invalidate_caches()
    if register:
        register()
    if key == 'zzz':
        if not hasattr(bpy.types.Scene, 'zzz_shader_type'):
            bpy.types.Scene.zzz_shader_type = bpy.props.StringProperty(default='KYTHERA')
        bpy.context.scene.zzz_shader_type = 'KYTHERA'
    with bpy.data.libraries.load(str(ROOT / 'setup_wizard/shaders' / shader), link=False) as (src, dst):
        dst.materials = [mat_name]
    template = dst.materials[0]
    # Deliberately share material AND mesh datablock between two characters.
    a = character(key + 'A', game, template)
    b = character(key + 'B', game, template, data=a[1].data)
    original_surface = surface_snapshot(a[1])
    mask, width = shared_outline_fixture([a, b], template)
    set_value(case, *a, .2)
    set_value(case, *b, .8)
    close(get(case, *a), .2)
    close(get(case, *b), .8)
    assert a[1].material_slots[0].material != b[1].material_slots[0].material
    for arm, mesh in [a, b]:
        assert surface_snapshot(mesh) == original_surface, (key, 'UVs or custom normals changed')
        assert get_modifier_property(mesh.modifiers['Outlines Fixture'], mask) == mesh.material_slots[0].material
        assert nested_material(mesh) == mesh.material_slots[0].material
        assert_evaluated_material_mask(mesh)
        assert mesh.data.materials[0] == mesh.material_slots[0].material
    # Re-opened files may already contain the invalid OBJECT overrides from
    # the previous implementation, even though their materials are unique.
    isolated_material = a[1].material_slots[0].material
    a[1].data = b[1].data
    a[1].material_slots[0].link = 'OBJECT'
    a[1].material_slots[0].material = isolated_material
    assert a[1].data.materials[0] != isolated_material
    cu.ensure_character_node_trees_isolated(a[0], materials(a[1]))
    assert a[1].data.materials[0] == isolated_material
    assert b[1].data.materials[0] != isolated_material
    assert_evaluated_material_mask(a[1])
    set_value(case, *a, .4)
    close(get(case, *a), .4)
    close(get(case, *b), .8)
    if pull:
        select(b[0]); pull(bpy.context.scene, bpy.context, force=True)
        close(getattr(bpy.context.scene, prop), .8)
        close(get(case, *a), .4)
        select(a[0]); pull(bpy.context.scene, bpy.context, force=True)
        close(getattr(bpy.context.scene, prop), .4)
    extra_controls(case, a, b)
    if key in {'ake', 'ww'}:
        # Older appended files may predate the per-rig game stamp.
        del a[0]['gacha_game']; cu.invalidate_caches()
        assert cu.detect_armature_game(a[0]) == game
        set_value(case, *a, .4)
        close(get(case, *a), .4)
        a[0]['gacha_game'] = game; cu.invalidate_caches()
    # No character and wrong-game selection must not broadcast panel values.
    wrong = bpy.data.objects.new('UnrelatedRig', bpy.data.armatures.new('UnrelatedRigData'))
    wrong['gacha_game'] = 'UNRELATED'
    bpy.context.scene.collection.objects.link(wrong)
    cam = bpy.data.objects.new('TestCamera', bpy.data.cameras.new('TestCamera'))
    bpy.context.scene.collection.objects.link(cam)
    if prop:
        for active in [None, cam, wrong]:
            select(active)
            setattr(bpy.context.scene, prop, .6)
            close(get(case, *a), .4)
            close(get(case, *b), .8)
    # A mesh-only target must not borrow a rig elsewhere in the scene.
    unrigged = bpy.data.objects.new('Unrigged', bpy.data.meshes.new('UnriggedMesh'))
    unrigged['gacha_game'] = game
    unrigged.data.materials.append(template.copy())
    bpy.context.scene.collection.objects.link(unrigged)
    select(unrigged)
    assert cu.resolve_settings_armature(bpy.context) == unrigged
    b[0].select_set(True)
    assert cu.resolve_settings_armature(bpy.context) == unrigged
    set_value(case, unrigged, unrigged, .3)
    close(get(case, unrigged, unrigged), .3)
    close(get(case, *a), .4)
    close(get(case, *b), .8)
    render_without_changes([.4, .8], case, [a, b])
    shader_animation(case, a, b)
    print('LOCAL_SHARED_PULL_RENDER_PASS', key, flush=True)
    # Export independent characters, load both through actual Append and Link.
    paths = []
    for index, (arm, mesh) in enumerate([a, b]):
        coll = bpy.data.collections.new(key + str(index))
        coll.objects.link(arm); coll.objects.link(mesh)
        path = RUNTIME / (key + str(index) + '.blend')
        bpy.data.libraries.write(str(path), {coll})
        paths.append(path)
    for linked in [False, True]:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        cu.invalidate_caches()
        pairs = []
        for index, path in enumerate(paths):
            with bpy.data.libraries.load(str(path), link=linked) as (src, dst):
                dst.collections = [key + str(index)]
            coll = dst.collections[0]
            bpy.context.scene.collection.children.link(coll)
            arm = next(o for o in coll.objects if o.type == 'ARMATURE')
            mesh = next(o for o in coll.objects if o.type == 'MESH')
            pairs.append((arm, mesh))
        render_without_changes([.4, .8], case, pairs)
        print('LIBRARY_RENDER_PASS', key, 'LINK' if linked else 'APPEND', flush=True)

print('ALL_CHARACTER_SETTINGS_ISOLATION_PASS', flush=True)
