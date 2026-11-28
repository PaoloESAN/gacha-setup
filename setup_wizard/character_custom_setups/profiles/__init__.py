"""Built-in character custom setup profiles.

Adding a new character-specific setup:
  1. Create a new module in this folder (e.g. ``wuwa_mychar.py`` or ``hsr_mychar.py``).
  2. Call ``register_profile(CharacterSetupProfile(...))`` in that module.
  3. Import the module below so it auto-registers on startup.
"""

from setup_wizard.character_custom_setups.profiles import (  # noqa: F401
    genshin_danica,
    genshin_durin,
    wuwa_denia,
)
