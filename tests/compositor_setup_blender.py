"""Blender --background --factory-startup --python tests/compositor_setup_blender.py."""
import sys
from pathlib import Path
from types import SimpleNamespace

import addon_utils
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
addon_utils.enable('setup_wizard', default_set=True)
from setup_wizard.ui.compositor_setup import (
    COMPOSITOR_OPERATORS, GACHA_PT_CompositorSetup, GACHA_PT_CompositorBasicSetup,
    REFLECTION_GAMES,
)
from setup_wizard.genshin_compositing_node_setup import get_node_tree, get_output_node_type

assert GACHA_PT_CompositorSetup.bl_category == 'Gacha Setup Compositor'
assert GACHA_PT_CompositorBasicSetup.bl_options == {'DEFAULT_CLOSED'}
assert hasattr(bpy.types, 'GACHA_PT_CompositorSetup')
assert hasattr(bpy.types, 'GACHA_PT_CompositorBasicSetup')
assert not hasattr(bpy.types, 'GI_PT_Custom_Compositing_Node_UI_Layout')
assert GACHA_PT_CompositorSetup.poll(SimpleNamespace(space_data=SimpleNamespace(tree_type='CompositorNodeTree')))
assert not GACHA_PT_CompositorSetup.poll(SimpleNamespace(space_data=SimpleNamespace(tree_type='ShaderNodeTree')))
keep_scenes = {bpy.data.scenes.new('Preview'), bpy.data.scenes.new('Scene.001')}
for game in (*COMPOSITOR_OPERATORS, 'ZENLESS_ZONE_ZERO', 'GENSHIN_IMPACT', 'WUTHERING_WAVES'):
    scene = bpy.context.scene
    scene.game_type_dropdown = game
    # Leave a real object in place to ensure this never launches character setup.
    objects_before = set(scene.objects)
    assert bpy.ops.gacha.run_compositing('EXEC_DEFAULT') == {'FINISHED'}, game
    assert scene.view_settings.view_transform == ('AgX' if game == 'ARKNIGHTS_ENDFIELD' else 'Standard'), game
    if game in REFLECTION_GAMES:
        eevee = getattr(scene, 'eevee', None)
        if hasattr(eevee, 'use_raytracing'):
            assert eevee.use_raytracing, game
        if hasattr(eevee, 'use_ssr'):
            assert eevee.use_ssr, game
    assert set(scene.objects) == objects_before, game
    assert keep_scenes.issubset(set(bpy.data.scenes)), (game, 'Removed an existing scene')
    tree = get_node_tree(scene)
    output = next((n for n in tree.nodes if n.bl_idname == get_output_node_type()), None)
    assert output and any(s.is_linked for s in output.inputs), (game, 'No connected image output')
    assert any(n.bl_idname == 'CompositorNodeRLayers' for n in tree.nodes), game
    if game == 'ZENLESS_ZONE_ZERO':
        assert any(n.bl_idname == 'CompositorNodeGlare' for n in tree.nodes)
    elif game == 'ARKNIGHTS_ENDFIELD':
        assert any(n.bl_idname == 'CompositorNodeColorBalance' for n in tree.nodes), game
    elif game != 'PUNISHING_GRAY_RAVEN':
        assert any(n.bl_idname == 'CompositorNodeGroup' for n in tree.nodes), game
    if game == 'WUTHERING_WAVES':
        group = next(n.node_tree for n in tree.nodes if n.bl_idname == 'CompositorNodeGroup')
        assert 'shaders' in group['_gacha_compositor_source'] and 'wuwa' in group['_gacha_compositor_source']
    if game in {'GENSHIN_IMPACT', 'HONKAI_STAR_RAIL', 'HONKAI_IMPACT_3RD', 'HONKAI_NEXUS_ANIMA'}:
        group = tree.nodes['HoYoverse Post Processing'].node_tree
        assert 'gi' in group['_gacha_compositor_source']
    # Drawing both panels must work for every game, including the individual steps.
    class Layout:
        def __init__(self): self.ops = []
        def prop(self, *args, **kwargs): pass
        def menu(self, *args, **kwargs): pass
        def label(self, *args, **kwargs): pass
        def row(self, *args, **kwargs): return self
        def column(self, *args, **kwargs): return self
        def operator(self, identifier, **kwargs):
            op = SimpleNamespace(identifier=identifier)
            self.ops.append(op)
            return op
    layout = Layout()
    for panel in (GACHA_PT_CompositorSetup, GACHA_PT_CompositorBasicSetup):
        panel.draw(SimpleNamespace(layout=layout), bpy.context)
    assert [op.step for op in layout.ops][:2] == ['ALL', 'COLOR']
    assert any(op.step == 'NODES' for op in layout.ops)
    for op in layout.ops:
        if op.step in {'COLOR', 'STANDARD', 'RENDER', 'DEFAULTS'}:
            before = set(tree.nodes)
            assert bpy.ops.gacha.run_compositing('EXEC_DEFAULT', step=op.step) == {'FINISHED'}
            assert set(tree.nodes) == before, game
            if op.step == 'STANDARD':
                assert scene.view_settings.view_transform == 'Standard'
    print('COMPOSITOR_PASS', game, [(n.name, getattr(getattr(n, 'node_tree', None), 'name', '')) for n in tree.nodes], flush=True)
print('PASS: nine games, connected outputs, individual defaults, panels and no character setup', flush=True)
