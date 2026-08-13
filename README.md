# Gacha Setup for Blender

**Gacha Setup** is a fork of the original [Setup Wizard](https://github.com/michael-gh1/Addons-And-Tools-For-Blender-miHoYo-Shaders) add-on, created to provide a simple, automated character setup process for Gacha models specifically in modern **official Blender versions (Blender 5.2+)**. Using older versions of Blender or Goo Blender is not recommended, as the primary focus and target of this project is standard official Blender 5.2+.

---

## Supported Games

* **Genshin Impact**
* **Honkai: Star Rail (HSR)**
* **Zenless Zone Zero (ZZZ)**
* **Neverness to Everness (NTE)** *(Face rig missing)*
* **Wuthering Waves** *(Soon)*
* **Silver Palace** *(Soon)*
* **Honkai Impact 3rd** *(Soon)*

---

## Installation

1. Download the `Gacha_Setup-<version>.zip` file from the **Releases** page.
2. In Blender 5.2+, go to **Edit > Preferences > Add-ons**.
3. Click the drop-down menu in the top right corner and select **Install from Disk...**
4. Select the downloaded `Gacha_Setup-<version>.zip` file.
5. Press **N** in the 3D Viewport to access the `Character Setup Wizard` sidebar panel.

---

## Additional Add-ons

The following add-on dependencies are bundled in the `dependencies` directory and will be **automatically installed and enabled** if they are not already present in your Blender:

* **ExpyKit**: [pKrime/Expy-Kit](https://github.com/pKrime/Expy-Kit) — Installed for automating Rigify character rigging setups.
* **UEFormat**: [h4lfheart/UEFormat](https://github.com/h4lfheart/UEFormat) — Installed for importing Neverness to Everness (NTE) character models.

---

## License and Attribution

This project is a derivative work modified in 2026 and distributed under the GNU General Public License v3 (GPL v3).

- Original Repository & Author: [michael-gh1/Addons-And-Tools-For-Blender-miHoYo-Shaders](https://github.com/michael-gh1/Addons-And-Tools-For-Blender-miHoYo-Shaders)

### Original Project Credits & Acknowledgments

Thanks to all those who collaborated on the original project:

* [@Festivity](https://github.com/festivities) — [YouTube](https://www.youtube.com/channel/UCXCTHNBA8TVs0s5aQuNtWwg) | [Twitter](https://x.com/festivizing)
* TheyCallMeSpy
* Sultana
* M4urlcl0
* Modder4869
* [@BonnyAnimations](https://github.com/BonnyAnimations) — [YouTube](https://www.youtube.com/@BonnyAnimations) | [Twitter](https://x.com/BonnyTweetsOFF)
* Enthralpy — [YouTube](https://www.youtube.com/@Enthralpy) | [Twitter](https://x.com/Enthralpy)
* [@OctavoPE](https://github.com/OctavoPE) — [Twitter](https://x.com/Llama3D)
* JaredNyts — [Twitter](https://twitter.com/jared_nyts)
* SubutaiProduction — [YouTube](https://www.youtube.com/@SubutaiProduction) | [Twitter](https://twitter.com/SubutaiEdits)
* Aiko — [YouTube](https://www.youtube.com/@AikoDesu) | [Twitter](https://x.com/Aiko__ya)

### Additional Credits & Acknowledgments (This Project)

* **Genshin Impact**:
  * **Shader**: [Blender-miHoYo-Shaders](https://github.com/festivize/Blender-miHoYo-Shaders) by Festivity
* **HSR**:
  * **Shader**: [Blender-StellarToon](https://github.com/festivities/Blender-StellarToon) by Festivity
  * **Face Rig**: Isaac / Just_ScaasI
* **ZZZ**:
  * **Shader**: Just_ScaasI, BonnyAnimations, Aiko
  * **Rigging + Scripting**: Enthralpy
  * **Supervised and made possible by**: Stormz67
  * **Face Rig**: [@jideeh](https://github.com/Jideeh1)
    * **Poke / Enthralpy**: Driver Logic
    * **Isaac / Just_ScaasI**: Facerig Logic + Widgets
    * **The_Crabnuts / Kan_Natto**: Facerig Logic + Widgets
* **NTE**:
  * **Shader**: Omatsuri Discord
  * **Rig**: 矩阵映画
* **Logo Icon**: <a href="https://www.flaticon.com/free-icons/star" title="star icons">Star icons created by Magnific - Flaticon</a>

---

## Summary of Key Modifications & Features

In compliance with Section 5a of the GNU General Public License v3, the following primary modifications and major features have been implemented:

- **Blender 5.x Full Support**:
  - Added support and compatibility fixes for Blender 5.2+.
  - Dynamically queries active armature bone collections for interactive N-panel **Rig Layers UI** (with visibility toggles and solo star $\star$ buttons).
  - Resolved null pointer crashes, updated legacy Python API calls, and cleaned up final setup operations.
- **Honkai: Star Rail (HSR) Rigging & Texture Pipeline**:
  - Integrated complete HSR character rigging and automatic texture loading pipelines.
  - Corrected finger, arm, torso, and hip bone rotations/hierarchies.
  - Implemented advanced eye tracking controls and a dynamic eye Y-location driver system to prevent eye popping and mesh clipping during shape key expressions.
- **Zenless Zone Zero (ZZZ) Model & Rigging Suite**:
  - Added full support for importing and setting up ZZZ models with custom breast/breath physics controls (`Torso (IK)`).
  - Integrated the specialized ZZZ facial rig (v6) with advanced shapekey drivers and eye tracking by jideeh.
  - Corrected shoulder widget roll rotations and repositioned thigh parent controls.
  - Automated character collection/armature renaming and `lights` collection handling with native completion status popups.
- **Neverness to Everness (NTE) Support**:
  - Integrated complete character importing, UEFormat support, material assignment, outline setup, and compositor post-processing node configuration.
- **Shader, Outline & Material Fixes**:
  - Fixed broken outline rendering, eyeshadow, and outline line thickness across Genshin, ZZZ, and HSR models.
  - Enhanced post-processing execution and automated texture binding for both manual and standard imports.
- **Codebase Refactoring & Streamlining**:
  - Removed Punishing: Gray Raven (PGR) support and outdated third-party dependencies (e.g., BetterFBX, legacy auto-updater) for a clean, lightweight addon architecture.
