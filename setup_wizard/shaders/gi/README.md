# Genshin Impact Shader

This folder contains the shader files for setting up **Genshin Impact** character models in Blender.

* **Original Repository**: [https://github.com/festivize/Blender-miHoYo-Shaders](https://github.com/festivize/Blender-miHoYo-Shaders)
* **Original Author**: [Festivity](https://github.com/festivities) ([YouTube](https://www.youtube.com/channel/UCXCTHNBA8TVs0s5aQuNtWwg) | [Twitter](https://x.com/festivizing))

---

## Included Shader File

* **Quality**: `HoYoverse - PrimoToon v4.0.blend` — Unified Genshin Impact shader file containing character shaders (Body, Face, Outlines, VFX), geometry nodes outlines, and compositing post-processing node groups. Selected by default in Blender 5.0 and newer.
* **Performance**: `HoYoverse - Genshin Impact v3.4 starriia.blend` — Legacy Starriia shader with Body, Hair, Face, Pupil, New Pupil, Highlight, Weapons, and Outlines materials. Selected by default in Blender versions below 5.0.
* `HoYoverse - Genshin Impact Outlines v3.blend` — Geometry-node outlines used by Performance.
* `HoYoverse - Genshin Impact Post-Processing.blend` — Compositing groups used by Performance.

Choose the shader in **Gacha Setup → Setup Settings → Shader** before running character setup. Both choices are available regardless of the version-based default, and the selection is passed to isolated imports.

Old uses the same packed lighting-panel attributes and Global Properties controls as Quality, including Fresnel toggle/size, shadow offset, and rim controls. Its geometry nodes also retain the original full direction vectors for legacy face/body shading. The panel's relative shadow offset is added to the original 0.55 threshold.

The optional Starriia Set Depth and Screenspace Shadows nodes stay disconnected in the bundled file. Setup and file-load handlers restore their original connections when `bpy.types.ShaderNodeSetDepth` exists; standard Blender keeps the portable connections. The identifier was verified by creating the native node in Goo Engine 4.1.1, 4.2.13, 4.3.2, and 4.4.3.


---

## Credits & Special Thanks

Original shader development created by **Festivity** and contributors:

* **Arc System Works** & **HoYoverse**
* **Aerthas Veras** ([GitHub](https://github.com/Aerthas/))
* **Manashiku** ([GitHub](https://github.com/Manashiku/))
* **No_Tables** ([Twitter](https://twitter.com/No_Tables))
* **BonnyAnimations** ([YouTube](https://www.youtube.com/@BonnyAnimations) | [Twitter](https://x.com/BonnyTweetsOFF))
* **Mken** ([Twitter](https://twitter.com/Mken_TechArt))
* **Enthralpy** ([YouTube](https://www.youtube.com/@Enthralpy))
* **Llama** ([Twitter](https://x.com/Llama3D))
* **JTAOO**
* **VANS** — Sandrone Pupil Shader
* **nedarb183** — Genshin Pupil Highlight

---

## License

Distributed under the **GNU General Public License v3.0 (GPL-3.0)** in compliance with original source repository terms.
