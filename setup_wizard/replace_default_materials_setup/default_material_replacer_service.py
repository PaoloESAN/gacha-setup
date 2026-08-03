
from setup_wizard.replace_default_materials_setup.game_default_material_replacers import (
    GameDefaultMaterialReplacer,
    ZenlessZoneZeroDefaultMaterialReplacer,
    clean_mesh_slots,
)


class DefaultMaterialReplacerService:
    def __init__(self, game_default_material_replacer: GameDefaultMaterialReplacer):
        self.game_default_material_replacer = game_default_material_replacer

    def replace_default_materials(self):
        res = self.game_default_material_replacer.replace_default_materials()
        if isinstance(self.game_default_material_replacer, ZenlessZoneZeroDefaultMaterialReplacer):
            clean_mesh_slots()
        return res
