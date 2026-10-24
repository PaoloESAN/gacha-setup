"""Exercise both UEFormat import entry points with the dependency disabled."""
from pathlib import Path
import os
import sys

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['GACHA_SETUP_ISOLATED_WORKER'] = '1'
addon_utils.enable('setup_wizard', default_set=True)
from setup_wizard.genshin_setup_wizard import on_register
from setup_wizard.genshin_import_character_model import _import_nte_uemodel, _import_wuwa_uemodel
from setup_wizard.utils.optional_addons import find_addon

on_register()
module = find_addon('ueformat')
assert module
addon_utils.disable(module, default_set=True)
fixtures = (
    (_import_nte_uemodel, ROOT/'chars/nte/Zankou swimsuit/player_036_zankou_swimsuit_skin.uemodel'),
    (_import_wuwa_uemodel, ROOT/'chars/wuwa/Phrolova/R2T1FuluoluoMd10011.uemodel'),
)
for operation, model in fixtures:
    assert not addon_utils.check(module)[1]
    before = set(bpy.context.scene.objects)
    operation(bpy.context, str(model))
    assert any(o.type == 'MESH' for o in set(bpy.context.scene.objects)-before)
    assert not addon_utils.check(module)[1]
    assert module not in bpy.context.preferences.addons
    print('OPTIONAL_UEFORMAT_PASS', model.name)
try:
    _import_nte_uemodel(bpy.context, str(ROOT/'missing.uemodel'))
    raise AssertionError('Missing file must fail')
except RuntimeError:
    pass
assert not addon_utils.check(module)[1]
assert module not in bpy.context.preferences.addons
