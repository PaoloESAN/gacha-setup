---
title: Installation Guide
description: How to install Gacha Setup. Blender 5.2 is recommended; Blender/Goo Engine 4.1+ are supported.
---

# Installation Guide

:::note[Blender Compatibility]
**Blender 5.2 is recommended.** Gacha Setup is also compatible with **Blender/Goo Engine 4.1+**. If you use Blender **below 4.5**, install **BetterFBX** to import models.
:::

## Step-by-Step Installation

1. Download the latest `Gacha_Setup-<version>.zip` release package from GitHub Releases.
2. Launch Blender 5.2 (recommended) or Blender/Goo Engine 4.1+. On Blender versions below 4.5, install BetterFBX first.
3. Open **Edit > Preferences > Add-ons**.
4. Click the drop-down menu in the top-right corner and choose **Install from Disk...**
5. Select the downloaded `.zip` file and enable the add-on checkbox.
6. Press <kbd>N</kbd> in the 3D Viewport to open the **Character Setup Wizard** sidebar panel.

---

## Bundled Dependencies

The add-on automatically checks and installs required sub-dependencies when enabled:

- **ExpyKit**: Automates Rigify character conversions.
- **UEFormat**: Enables direct import of Neverness to Everness (`.ueformat`) models.

---

:::tip[Quick Tip]
Here will go additional details about configuration options, automatic dependency installation checks, and troubleshooting missing dependencies.
:::
