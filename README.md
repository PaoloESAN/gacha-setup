# Gacha Blender Setup (Blender 5.0+ Modified Version)

Gacha Blender Setup is a modified and optimized version of the original Setup Wizard add-on from Addons-And-Tools-For-Blender-miHoYo-Shaders, updated to ensure full compatibility, modern rigging support, and stability with Blender 5.0 and newer versions.

## License and Attribution

This project is a derivative work modified in 2026 and distributed under the GNU General Public License v3 (GPL v3).

- Original Repository & Author: [michael-gh1/Addons-And-Tools-For-Blender-miHoYo-Shaders](https://github.com/michael-gh1/Addons-And-Tools-For-Blender-miHoYo-Shaders)
- Additional Credits: jideeh (ZZZ Face Rig)

## Summary of Key Modifications

In compliance with Section 5a of the GNU General Public License v3, the following primary modifications and major features have been implemented:

- Blender 5.x Full Support:
  - Added support and compatibility fixes for Blender 5.1.1, 5.2, and newer versions.
  - Resolved null pointer crashes, updated legacy Python API calls, and fixed mesh join operations during final setup.
- Honkai: Star Rail (HSR) Rigging & Texture Pipeline:
  - Integrated complete HSR character rigging and automatic texture loading pipelines.
  - Corrected finger, arm, torso, and hip bone rotations/hierarchies.
  - Implemented advanced eye tracking controls and a dynamic eye Y-location driver system to prevent eye popping and mesh clipping during shape key expressions.
- Zenless Zone Zero (ZZZ) Model & Facial Rigging:
  - Added full support for importing and setup of ZZZ models using Genshin rigging as a baseline.
  - Integrated the specialized ZZZ facial rig by jideeh.
- Shader, Outline & Material Fixes:
  - Fixed broken outline rendering, eyeshadow, and outline line thickness across Genshin, ZZZ, and HSR models.
  - Enhanced post-processing execution and automated texture binding for both manual and standard imports.
- Codebase Refactoring & Streamlining:
  - Removed outdated third-party dependencies (e.g., BetterFBX) and legacy auto-updater code for a clean, lightweight addon architecture.

## Installation

1. In Blender, go to Edit > Preferences > Add-ons.
2. Click the drop-down menu in the top right corner and select Install from Disk...
3. Select the .zip file of the Gacha Blender Setup add-on.
4. Enable the add-on by checking the checkbox next to it.
