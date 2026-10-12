# Author: michael-gh1

from bpy.types import Operator, Context

from setup_wizard.character_rig_setup.character_riggers import CharacterRiggerFactory
from setup_wizard.domain.game_types import GameType


class RigifyCharacterService:
    def __init__(self, game_type: GameType, blender_operator: Operator, context: Context):
        self.context = context
        self.blender_operator = blender_operator
        self.character_rigger = CharacterRiggerFactory.create(game_type, blender_operator, context)

    def rig_character(self):
        props = getattr(self.context.scene, "character_rigger_props", None)
        disable_rigging = getattr(props, "disable_rigging", getattr(self.context.scene, "disable_rigging", False))
        if disable_rigging:
            print("[SETUP WIZARD] Rigging skipped: Disable Rigging is enabled in Setup Settings.")
            if self.blender_operator and hasattr(self.blender_operator, "report"):
                self.blender_operator.report({'INFO'}, 'Rigging skipped. Disable Rigging is enabled.')
            return
        self.character_rigger.rig_character()
