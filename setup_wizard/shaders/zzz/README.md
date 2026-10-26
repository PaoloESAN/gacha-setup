# Zenless Zone Zero (ZZZ) Shader & Rig Setup

This folder contains the shader and rig setup files for **Zenless Zone Zero (ZZZ)** character models in Blender.

> **Source & Origin**:
> This shader was obtained / sourced from the **Omatsuri Discord Server**.

---

## Included Files

* `ZZZ Setup v7.blend` — Shader setup file for ZZZ character materials, rig drivers, and node configurations.
* `Kythera's ZZZ Shader V2.blend` — Toon Shader for Blender 5.2+, replacing V1.5.1. Includes the original V2 body, face and highlight materials, plus the complete `ZZZ Shader Eye` and `ZZZ Shader EyeHighlights` materials from the previous bundle.

The V2 face uses the bundled Sun light and `SUN`, `RIGHT`, and `FRONT` attributes. Setup copies the face-vector group per character, binds its Sun and head basis, and updates the head target after rig generation. Each Sun has independent light data and receiver links, so a second character's light does not alter the first. Legacy setups retain their existing Light Direction system.

---

## Credits & Acknowledgments

* **Shader Creators**:
  * **Kytherity**
  * **Just_ScaasI** ([Twitter](https://x.com/Just_ScaasI/))
  * **BonnyAnimations** ([YouTube](https://www.youtube.com/@BonnyAnimations) | [Twitter](https://x.com/BonnyTweetsOFF))
  * **Aiko** ([YouTube](https://www.youtube.com/@AikoDesu) | [Twitter](https://x.com/Aiko__ya))
* **Character Rigging & Scripting**:
  * **Rigging & Scripting**: **Enthralpy** ([YouTube](https://www.youtube.com/@Enthralpy))
  * **Facial Rig**: [**jideeh**](https://github.com/Jideeh1)
    * **Poke / Enthralpy**: Driver Logic
    * **Isaac / Just_ScaasI**: Facerig Logic + Widgets
    * **The_Crabnuts / Kan_Natto**: Facerig Logic + Widgets
* **Supervised & Made Possible By**: **Stormz67**
* **Community Source**: [Omatsuri Discord Server](https://discord.gg/omatsuri)

---

## License

Distributed under the **GNU General Public License v3.0 (GPL-3.0)**.
