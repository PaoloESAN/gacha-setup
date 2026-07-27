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
        next_step_index = getattr(self, 'next_step_idx', 0)
        invoker_type = getattr(self, 'invoker_type', 'invoke_next_step_ui') or 'invoke_next_step_ui'
        high_level_name = getattr(self, 'high_level_step_name', '') or self.bl_idname

        NextStepInvoker().invoke(
            next_step_index,
            invoker_type, 
            high_level_step_name=high_level_name,
            game_type=self.game_type,
        )
        return {'FINISHED'}

