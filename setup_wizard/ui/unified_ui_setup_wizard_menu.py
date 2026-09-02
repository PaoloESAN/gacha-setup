import bpy

from bpy.props import EnumProperty
from bpy.types import Panel

from setup_wizard import bl_info
from setup_wizard.addon_updater import addon_updater_ops
from setup_wizard.domain.game_types import GameType


class CSW_PT_Updater_UI_Layout(Panel):
    bl_label = "Add-on Updater"
    bl_idname = 'CSW_PT_Updater_UI_Layout'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"

    def draw(self, context):
        layout = self.layout
        addon_updater_ops.check_for_update_background()
        addon_updater_ops.update_settings_ui_condensed(self, context, element=layout)


class CSW_PT_Unified_Character_Setup_Wizard_UI_Layout(Panel):
    bl_label = "Character Setup Wizard"
    bl_idname = 'CSW_PT_Unified_Character_Setup_Wizard_UI_Layout'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character Setup Wizard"

    bpy.types.Scene.game_type_dropdown = EnumProperty(
        items=[
            (GameType.GENSHIN_IMPACT.name, 'Genshin Impact', 'Genshin Impact Setup'),
            (GameType.HONKAI_STAR_RAIL.name, 'Honkai Star Rail', 'Honkai Star Rail Setup'),
            (GameType.ZENLESS_ZONE_ZERO.name, 'Zenless Zone Zero', 'Zenless Zone Zero Setup'),
            (GameType.NEVERNESS_TO_EVERNESS.name, 'Neverness to Everness', 'Neverness to Everness Setup'),
            (GameType.WUTHERING_WAVES.name, 'Wuthering Waves', 'Wuthering Waves Setup'),
            (GameType.ARKNIGHTS_ENDFIELD.name, 'Arknights: Endfield', 'Arknights: Endfield Setup'),
        ],
        name='Game',
        description='Setup for the selected game',
        default=GameType.GENSHIN_IMPACT.name,
    )

    bpy.types.Scene.character_setup_wizard_logging_enabled = bpy.props.BoolProperty(
        name = "(Debug) Enable Logging",
        description = "Enables Logging to Addon Config Directory for Character Setup Wizard",
        default = False
    )

    def draw(self, context):
        layout = self.layout

        version_text = layout.row()
        version_text.label(text='v' + '.'.join([str(version_num) for version_num in bl_info.get('version')]))

        sub_layout = layout.box()
        sub_layout.prop(context.scene, 'game_type_dropdown')
        # sub_layout.prop(context.scene, 'character_setup_wizard_logging_enabled')
