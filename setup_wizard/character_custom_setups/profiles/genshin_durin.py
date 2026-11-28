"""Genshin Impact: Durin custom character profile.

Replaces the legacy ad-hoc ``is_durin(context)`` / ``gacha_is_durin`` UI check
with a registered :class:`CharacterSetupProfile` while preserving backward
compatibility with existing ``gi_dark_eyes`` scenes.
"""

from __future__ import annotations

import bpy

from setup_wizard.character_custom_setups.registry import (
    CharacterSetupProfile,
    register_profile,
)
from setup_wizard.domain.game_types import GameType


def _sync_durin_ui(scene, context, arm) -> None:
    try:
        from setup_wizard.domain.shader_material_names import DURIN_NORMAL_EYE_MATERIAL_NAME
        from setup_wizard.ui.gi_ui_setup_wizard_menu import get_durin_pupil_materials

        _mesh, _mat1, mat2 = get_durin_pupil_materials(context, arm)
        if not mat2 or not getattr(mat2, "node_tree", None):
            mat2 = bpy.data.materials.get(DURIN_NORMAL_EYE_MATERIAL_NAME)
        if mat2 and getattr(mat2, "node_tree", None):
            mix_n = next((n for n in mat2.node_tree.nodes if n.type == 'MIX_SHADER'), None)
            if mix_n:
                scene.gi_dark_eyes = bool(mix_n.inputs[0].default_value > 0.5)
                return
        scene.gi_dark_eyes = False
    except Exception:
        pass


def _draw_durin_ui(layout, context, arm) -> None:
    scene = context.scene
    box = layout.box()
    box.label(text="Durin Settings", icon="HIDE_OFF")
    col = box.column(align=True)
    col.prop(scene, "gi_dark_eyes", text="Dark Eyes")


DURIN_PROFILE = register_profile(
    CharacterSetupProfile(
        id="genshin_durin",
        display_name="Durin",
        aliases=("durin",),
        game_types=(GameType.GENSHIN_IMPACT.name,),
        sync_ui=_sync_durin_ui,
        draw_ui=_draw_durin_ui,
    )
)
