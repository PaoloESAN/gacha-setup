"""Genshin Impact: Danica custom character profile."""

from setup_wizard.character_custom_setups.registry import (
    CharacterSetupProfile,
    register_profile,
)
from setup_wizard.domain.game_types import GameType


DANICA_PROFILE = register_profile(
    CharacterSetupProfile(
        id="genshin_danica",
        display_name="Danica",
        aliases=("danica",),
        game_types=(GameType.GENSHIN_IMPACT.name,),
        shader_overrides={
            "face": {
                "Cold Shadow Color 2": (1.0, 1.0, 1.0, 1.0),
                "Cold Shadow Color 3": (1.0, 1.0, 1.0, 1.0),
                "Warm Shadow Color 2": (1.0, 1.0, 1.0, 1.0),
                "Warm Shadow Color 3": (1.0, 1.0, 1.0, 1.0),
            }
        },
    )
)
