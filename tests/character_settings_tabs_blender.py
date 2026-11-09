"""Run with Blender --background --factory-startup --python-exit-code 1 --python FILE."""

import ast
import sys
from pathlib import Path
from types import SimpleNamespace

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import setup_wizard
from setup_wizard.ui import character_settings_tabs as tabs
from setup_wizard.ui.character_settings_utils import invalidate_caches, stamp_rig_game


class Layout:
    """Record the actual RNA targets passed to the UI drawing code."""

    def __init__(self):
        self.labels = []
        self.props = []

    def row(self, **kwargs):
        return self

    column = row
    box = row
    grid_flow = row
    split = row

    def label(self, *, text, **kwargs):
        self.labels.append(text)

    def prop(self, target, prop, **kwargs):
        self.props.append((target, prop, kwargs))

    def separator(self):
        pass


def make_rig(name):
    arm = bpy.data.objects.new(name, bpy.data.armatures.new(name))
    bpy.context.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bone = arm.data.edit_bones.new('Control')
    bone.tail = (0, 0, 1)
    bpy.ops.object.mode_set(mode='OBJECT')
    for name in ('Root', 'Face', 'Torso (IK)', 'Fingers', 'Arm.L (IK)',
                 'Arm.L (FK)', 'Arm.R (IK)', 'Leg.L (IK)', 'Leg.R (IK)',
                 'Weapon', 'Hat_Tweak', 'Hair', 'Lighting', 'Custom Control'):
        arm.data.collections.new(name).assign(arm.data.bones['Control'])
    arm.data.collections.new('Empty')
    return arm


setup_wizard.register()
try:
    arm = make_rig('Tabs Test')
    panels = [cls for cls in setup_wizard.classes
              if getattr(cls, 'bl_label', '') == 'Character Settings']
    assert len(panels) == 9, panels
    matched = set()
    for game in tabs.SUPPORTED_GAMES:
        stamp_rig_game(arm, game, 'Test Character')
        matching = [cls for cls in panels if cls.poll(bpy.context)]
        assert len(matching) == 1, (game, matching)
        panel = matching[0]
        matched.add(panel)
        arm.gacha_settings_tab = 'BONE_LAYERS'
        layout = Layout()
        panel.draw(SimpleNamespace(layout=layout), bpy.context)
        assert layout.labels[0] == 'Test Character', (game, layout.labels)
        assert layout.labels[-1].startswith('Rig: '), layout.labels
        visibility = [(target, args) for target, prop, args in layout.props
                      if prop == 'is_visible']
        expected = {coll.name for coll in arm.data.collections if len(coll.bones)}
        expected -= {'Custom Control', 'Hat_Tweak'}
        assert {target.name for target, _ in visibility} == expected
        assert any(prop == 'is_solo' for _, prop, _ in layout.props)
        # UI controls must write directly to the selected rig's collections.
        target = visibility[0][0]
        target.is_visible = False
        assert not arm.data.collections[target.name].is_visible
        target.is_visible = True
        arm.gacha_settings_tab = 'CHARACTER'
        assert not tabs.draw_character_settings_tabs(Layout(), bpy.context)
    assert len(matched) == 9

    # Tab state belongs to each character, including mesh selection.
    other = make_rig('Other Character')
    stamp_rig_game(other, 'NEVERNESS_TO_EVERNESS')
    assert other.gacha_settings_tab == 'CHARACTER'
    arm.gacha_settings_tab = 'BONE_LAYERS'
    assert other.gacha_settings_tab == 'CHARACTER'
    mesh = bpy.data.objects.new('Character Mesh', bpy.data.meshes.new('Mesh'))
    bpy.context.collection.objects.link(mesh)
    mesh.parent = arm
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    invalidate_caches()
    assert tabs.draw_character_settings_tabs(Layout(), bpy.context)

    # Embedded scripts remain syntactically valid and patching is idempotent.
    source = '''class RigLayers(bpy.types.Panel):
    @classmethod
    def poll(cls, context):
        return True
'''
    patched = tabs.patch_standalone_layers(source)
    ast.parse(patched)
    assert tabs.patch_standalone_layers(patched) == patched
    namespace = {'bpy': bpy}
    exec(patched, namespace)
    assert not namespace['RigLayers'].poll(bpy.context)

    class VIEW3D_PT_rig_layers_tabs_test(bpy.types.Panel):
        bl_label = 'Old Rig Layers'
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_category = 'Item'

        @classmethod
        def poll(cls, context):
            return True

        def draw(self, context):
            pass

    bpy.utils.register_class(VIEW3D_PT_rig_layers_tabs_test)
    tabs.hide_registered_rig_layers()
    assert not VIEW3D_PT_rig_layers_tabs_test.poll(bpy.context)
    # Unrelated rigs retain their original standalone layers panel.
    stamp_rig_game(arm, 'UNRELATED_GAME')
    assert VIEW3D_PT_rig_layers_tabs_test.poll(bpy.context)

    print('PASS: all nine game panels, character header, original visibility and solo '
          'controls, per-character tabs, mesh selection, and embedded rig panels')
finally:
    setup_wizard.unregister()
    if 'VIEW3D_PT_rig_layers_tabs_test' in locals():
        assert VIEW3D_PT_rig_layers_tabs_test.poll(bpy.context)
        bpy.utils.unregister_class(VIEW3D_PT_rig_layers_tabs_test)
    assert not hasattr(bpy.types.Object, 'gacha_settings_tab')
