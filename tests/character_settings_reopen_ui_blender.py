"""Native panel regression: run Blender WITHOUT --background.

blender --factory-startup --python tests/character_settings_reopen_ui_blender.py
Optionally append: -- path/to/a/rigged-character.blend
The test draws the sidebar, saves/reopens twice, and toggles the addon.
"""

import json
import sys
import traceback
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import setup_wizard
from setup_wizard.ui import character_settings_tabs as tabs
from setup_wizard.ui.character_settings_utils import invalidate_caches, stamp_rig_game

assert not bpy.app.background, 'Native panel callbacks must be exercised in UI mode'
OUT = ROOT / 'tests/.runtime/character-settings-reopen-ui'
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / 'progress.txt'
LOG.write_text('', encoding='utf-8')
fixture = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else None


def log(message):
    with LOG.open('a', encoding='utf-8') as stream:
        stream.write(message + '\n')
    print(message, flush=True)


def redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.show_region_ui = True
                area.spaces.active.shading.type = 'SOLID'
                area.tag_redraw()
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)


# Mimic Rigify's auto-run UI script replacing its panel class on every load.
SCRIPT = '''import bpy
class VIEW3D_PT_rig_layers_reopen_regression(bpy.types.Panel):
    bl_label = 'Rig Layers Reopen Regression'
    bl_idname = 'VIEW3D_PT_rig_layers_reopen_regression'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'
    @classmethod
    def poll(cls, context):
        return bool(context.active_object)
    def draw(self, context):
        self.layout.label(text='Legacy layers')
previous = bpy.types.Panel.bl_rna_get_subclass_py(VIEW3D_PT_rig_layers_reopen_regression.bl_idname)
if previous:
    bpy.utils.unregister_class(previous)
bpy.utils.register_class(VIEW3D_PT_rig_layers_reopen_regression)
'''

setup_wizard.register()
bpy.context.preferences.filepaths.use_scripts_auto_execute = True
phase = 0


def reopen():
    bpy.ops.wm.open_mainfile(filepath=str(OUT / 'reopen.blend'), load_ui=True, use_scripts=True)
    invalidate_caches()


def step():
    global phase
    try:
        log(f'PHASE {phase}')
        if phase == 0:
            if fixture:
                bpy.ops.wm.open_mainfile(filepath=str(fixture), load_ui=True, use_scripts=True)
        elif phase == 1:
            arm = next((obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE'
                        and obj.data.get('rig_id')), None)
            if arm is None:
                arm = bpy.data.objects.new('Panel Test Rig', bpy.data.armatures.new('Panel Test Rig'))
                bpy.context.collection.objects.link(arm)
            active = bpy.context.view_layer.objects.active
            if active and active.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            arm.hide_set(False)
            arm.select_set(True)
            bpy.context.view_layer.objects.active = arm
            stamp_rig_game(arm, 'GENSHIN_IMPACT')
            text = bpy.data.texts.new('reopen_regression_ui.py')
            text.from_string(SCRIPT)
            text.use_module = True
            exec(compile(SCRIPT, text.name, 'exec'), {})
            redraw()
        elif phase in (2, 5, 8, 11):
            tabs.hide_registered_rig_layers()
            assert tabs.has_character_settings(bpy.context)
            panel = bpy.types.Panel.bl_rna_get_subclass_py('VIEW3D_PT_rig_layers_reopen_regression')
            assert panel.is_registered and not panel.poll(bpy.context)
            redraw()
        elif phase in (3, 6):
            bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'reopen.blend'))
        elif phase in (4, 7):
            reopen()
        elif phase == 9:
            setup_wizard.unregister()
            redraw()
        elif phase == 10:
            setup_wizard.register()
            redraw()
        else:
            setup_wizard.unregister()
            redraw()
            log('NATIVE_UI_SAVE_REOPEN_PASS')
            (OUT / 'result.json').write_text(json.dumps({'status': 'PASS', 'fixture': str(fixture),
                                                       'blender': bpy.app.version_string}), encoding='utf-8')
            bpy.ops.wm.quit_blender()
            return None
        phase += 1
        return 1.0
    except Exception:
        log(traceback.format_exc())
        (OUT / 'result.json').write_text(json.dumps({'status': 'FAIL', 'phase': phase,
                                                   'error': traceback.format_exc()}), encoding='utf-8')
        bpy.ops.wm.quit_blender()
        return None


log('STARTED ' + bpy.app.version_string)
bpy.app.timers.register(step, first_interval=2.0, persistent=True)
