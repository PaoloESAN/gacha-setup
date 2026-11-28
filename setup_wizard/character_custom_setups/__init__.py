"""Character-specific custom setup registry and built-in profiles."""

from setup_wizard.character_custom_setups.registry import (
    GACHA_CHAR_PROFILE_KEY,
    CharacterSetupContext,
    CharacterSetupProfile,
    apply_profile_shader_overrides,
    detect_character_profiles,
    draw_character_profile_ui,
    get_all_profiles,
    get_profile_by_id,
    get_uemodel_import_config,
    register_profile,
    run_character_setup_stage,
    should_import_all_uemodels,
    stamp_character_profile,
    sync_character_profile_ui,
)

__all__ = [
    "GACHA_CHAR_PROFILE_KEY",
    "CharacterSetupContext",
    "CharacterSetupProfile",
    "apply_profile_shader_overrides",
    "detect_character_profiles",
    "draw_character_profile_ui",
    "get_all_profiles",
    "get_profile_by_id",
    "get_uemodel_import_config",
    "register_profile",
    "run_character_setup_stage",
    "should_import_all_uemodels",
    "stamp_character_profile",
    "sync_character_profile_ui",
]
