# Third-Party Dependencies

This directory contains third-party Blender add-on packages provided in `.zip` format for convenience and automated setup within this tool.

> **Ownership & Disclaimer Notice:**
> 
> The add-ons contained within this folder **do NOT belong to me**. They were created by their respective original authors and are included in this directory solely to automate dependency installation for users.

---

## Bundled Third-Party Add-ons

### 1. Expy-Kit
* **Repository**: [https://github.com/pKrime/Expy-Kit](https://github.com/pKrime/Expy-Kit)
* **Author**: [pKrime](https://github.com/pKrime)
* **File**: `Expy-Kit-v052.zip`
* **Description**: Toolset for extracting and converting armatures for Rigify in Blender.
* **Blender versions**: Installed automatically for character setup on Blender 4.x and 5.x.

### 2. UEFormat
* **Repository**: [https://github.com/h4lfheart/UEFormat](https://github.com/h4lfheart/UEFormat)
* **Author**: [h4lfheart](https://github.com/h4lfheart)
* **File**: `ueformat-blender.zip`
* **Description**: Blender add-on for importing Unreal Engine format models (used for NTE model pipelines).

MMD Tools is required to import PMX files and VMD motion (VMD Motion requires Blender 4.2+). It must be installed separately and is not bundled here.

Expy-Kit, UEFormat, and MMD Tools can remain disabled. Gacha Setup temporarily activates the dependency for the operation that needs it and restores its prior state afterward, including when an operation fails. Dependencies already enabled by the user remain enabled.

---

## Licensing Notice

Blender add-ons that interface with the Blender Python API are generally distributed under the terms of the **GNU General Public License v3.0 (GPL-3.0)**.

* No copyright ownership over these external add-ons is claimed by this project. All rights belong to their respective original creators ([pKrime](https://github.com/pKrime), [h4lfheart](https://github.com/h4lfheart)).
* **Note / Clarification**: If for any reason these dependencies have been incorrectly understood to be under the GPL-3.0 license, or if there are any licensing concerns regarding their inclusion, please let me know or open an issue so it can be promptly resolved.
