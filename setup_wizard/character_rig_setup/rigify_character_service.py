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
            try:
                from setup_wizard.ui.character_settings_utils import stamp_rig_game, hide_eyestar_if_unrigged
                for obj in self.context.scene.objects:
                    if obj.type == 'ARMATURE':
                        stamp_rig_game(obj, getattr(self.blender_operator, "game_type", ""))
                hide_eyestar_if_unrigged(self.context)
            except Exception:
                pass
            try:
                from setup_wizard.character_rig_setup.lighting_panel_setup import (
                    disconnect_lighting_panel_nodes_from_global_material_properties,
                )
                disconnect_lighting_panel_nodes_from_global_material_properties()
            except Exception as e:
                print(f"[SETUP WIZARD] Notice disconnecting Global Properties: {e}")
            print("[SETUP WIZARD] Rigging skipped: Disable Rigging is enabled in Setup Settings.")
            if self.blender_operator and hasattr(self.blender_operator, "report"):
                self.blender_operator.report({'INFO'}, 'Rigging skipped. Disable Rigging is enabled.')
            return
        self.character_rigger.rig_character()
