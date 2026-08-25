# Author: michael-gh1

from bpy.props import IntProperty, StringProperty

from setup_wizard.import_order import NextStepInvoker

class CustomOperatorProperties:
    next_step_idx: IntProperty()
    file_directory: StringProperty()
    invoker_type: StringProperty()
    high_level_step_name: StringProperty()
    game_type: StringProperty()
    setup_mode: StringProperty()

    '''
    Modules will be registered and store previous choices within the same Blender file instance/session.
    This method will reset all values in the module in order for previous state to persist.
    
    Scenario: After running Setup Wizard, Import Material Data would run the next steps in the Setup Wizard.
    This would occur despite running the individual component in Advanced Setup.
    '''
    def clear_custom_properties(self):
        self.filepath = ''  # Important! UI saves previous choices to the Operator instance
        self.next_step_idx = -1
        self.file_directory = ''
        self.invoker_type = ''
        self.high_level_step_name = ''
        self.game_type = ''
        self.setup_mode = ''


class BasicSetupUIOperator:
    game_type: StringProperty()

    def execute(self, context):
        from setup_wizard.domain.game_types import GameType

        next_step_index = getattr(self, 'next_step_idx', 0)
        invoker_type = getattr(self, 'invoker_type', 'invoke_next_step_ui') or 'invoke_next_step_ui'
        high_level_name = getattr(self, 'high_level_step_name', '') or self.bl_idname

        game_type = self.game_type
        if not game_type:
            bl_id = getattr(self, 'bl_idname', '').lower()
            if 'wuthering_waves' in bl_id or 'wuwa' in bl_id:
                game_type = GameType.WUTHERING_WAVES.name
            elif 'neverness' in bl_id or 'nte' in bl_id:
                game_type = GameType.NEVERNESS_TO_EVERNESS.name
            elif 'zenless' in bl_id or 'zzz' in bl_id:
                game_type = GameType.ZENLESS_ZONE_ZERO.name
            elif 'honkai' in bl_id or 'hsr' in bl_id:
                game_type = GameType.HONKAI_STAR_RAIL.name
            elif 'punishing' in bl_id or 'pgr' in bl_id:
                game_type = GameType.PUNISHING_GRAY_RAVEN.name
            elif 'genshin' in bl_id:
                game_type = GameType.GENSHIN_IMPACT.name
            elif hasattr(context.scene, 'game_type_dropdown') and context.scene.game_type_dropdown:
                game_type = context.scene.game_type_dropdown
            else:
                game_type = GameType.GENSHIN_IMPACT.name

        NextStepInvoker().invoke(
            next_step_index,
            invoker_type, 
            high_level_step_name=high_level_name,
            game_type=game_type,
        )
        return {'FINISHED'}

