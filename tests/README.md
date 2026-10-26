# Automated Test Suite

Automated testing framework for the Gacha Setup Wizard addon, designed to validate each pipeline phase across supported games and character models in a modular, headless fashion.

## Credits

Original author and core development by **michael-gh1**.

---

## Directory Structure

```
tests/
  ├── README.md                    # Test suite documentation
  ├── run_tests.py                 # Master test runner CLI
  ├── common/
  │   ├── character_resolver.py    # Resolves character names and model paths (.fbx / .uemodel)
  │   ├── runner.py                # Host CLI runner, subprocess manager, and output formatter
  │   └── blender_executor.py      # In-Blender test dispatcher and step executor
  ├── rig/                         # Rig validation (arms, fingers, FK/IK, scaling, symmetry)
  │   ├── rig_assertions.py        # Rig validation logic
  │   ├── genshin.py
  │   ├── zzz.py
  │   ├── hsr.py
  │   ├── wuwa.py
  │   ├── nte.py
  │   └── ake.py
  ├── textures/                    # Material, texture, and shader validation
  │   ├── texture_assertions.py    # Texture and material assertions
  │   ├── genshin.py
  │   ├── zzz.py
  │   ├── hsr.py
  │   ├── wuwa.py
  │   ├── nte.py
  │   └── ake.py
  ├── facerig/                     # Face rig, eye/pupil tracking, and driver validation
  │   ├── facerig_assertions.py    # Face rig and driver assertions
  │   ├── genshin.py
  │   ├── zzz.py
  │   ├── hsr.py
  │   ├── wuwa.py
  │   ├── nte.py
  │   └── ake.py
  └── charactersettings/           # Scene settings, physics properties, and outlines validation
      ├── settings_assertions.py   # Settings, physics, and outlines assertions
      ├── genshin.py
      ├── zzz.py
      ├── hsr.py
      ├── wuwa.py
      ├── nte.py
      └── ake.py
```

---

## Test Suites Overview

### 1. rig/
- **Rig Generation**: Verifies generated Rigify armature with valid `rig_id` and complete bone hierarchy.
- **Arms**:
  - Validates FK controls (`upper_arm_fk.*`, `forearm_fk.*`, `hand_fk.*`) and IK controls (`hand_ik.*`) for both Left and Right arms.
  - Tests FK rotation propagation to deformation bones (`DEF-upper_arm.*`).
  - Tests IK translation response and ensures deformation bones follow without numerical errors (NaN / Inf).
- **Fingers**:
  - Validates all 5 finger chains on both hands (Thumb, Index, Middle, Ring, Pinky on Left and Right).
  - **Scaling**: Applies scale transforms (e.g. 1.5x) to finger controls and confirms clean propagation to `DEF-*` bones without zero-determinants or NaN values.
  - **Rotation**: Validates joint flexion along local axes without inversions or unnatural axial rolling.
  - **Symmetry & Orientation**: Verifies local axes and roll consistency between Left and Right hands.
- **Widgets and Constraints**: Confirms generation of widget control objects (`WGT-*`) and verifies no broken/unresolved constraints.

### 2. textures/
- Verifies character mesh presence and material slot assignments.
- Verifies that default Blender materials (`Material`, `Default`) were replaced with game-specific shaders.
- Validates that image texture nodes (`TEX_IMAGE`) have loaded image datablocks with valid dimensions (>0x0 px).
- Confirms presence and assignment of required core texture maps (Diffuse/Base Color and Lightmap/Shading).

### 3. facerig/
- Validates facial control bones (`head`, `eye`, `pupil`, `brow`, `mouth`, etc.).
- Verifies eye tracking and pupil driver configuration (Left and Right).
- Verifies mouth control bones and facial phoneme/expression shape keys.
- Confirms `Head Origin` / `Head Driver` setup with an active `Child Of` constraint targeting the armature head bone.

### 4. charactersettings/
- Validates color management configuration (`sRGB` / `Standard`).
- Confirms outline modifiers (Geometry Nodes / Solidify) attached to character meshes.
- Validates outline materials and assigned outline lightmaps.
- Verifies character physics properties (`character_rigger_props`, hair/clothes influence settings).
- Confirms scene cleanup (removal of extraneous FBX empties).

---

## How to Run Tests

FBX dispatch regression uses the real Columbina FBX. Blender below 4.5 must
always use installed BetterFBX; Blender 4.5+ prefers the registered native
importer. To test an older Blender without enabling the add-on permanently,
set `GACHA_TEST_BETTER_FBX_DIR` to the installed BetterFBX package directory:

```bash
blender --background --factory-startup --python-exit-code 1 --python tests/fbx_import_blender.py
blender --background --factory-startup --python-exit-code 1 --python tests/fbx_import_blender.py -- --full
```

The full variant executes the production isolated worker through rig generation
and saving, then verifies the result. Reports/blends go to `tests/.runtime/fbx-import`.

The Genshin shader selector regression checks the version-based default, both
UI choices, isolated-worker settings, and actual material/outline/compositor
imports. Run each choice in a fresh process; it supports Blender 4.1+ and 5+:

```bash
blender --background --factory-startup --python-exit-code 1 --python tests/genshin_shader_selection_blender.py -- NEW
blender --background --factory-startup --python-exit-code 1 --python tests/genshin_shader_selection_blender.py -- OLD
```

PGR regression runs the complete setup for all three Bianca outfits, Nirvatia,
the three Laiya Animator outfits, and Kurumi in fresh Blender processes, plus
material setup for the nine accessories/chibi models in `chars/pgr`. It
checks material JSON texture references (including eye color atlases), restored
Nirvatia skin bindings, neutral geometry, and arm/finger controls. Bianca's
unskinned face/eye layers must be attached and follow head rotation. Its two
bracelets must follow their own hands in FK and IK without stretching or moving
the opposite bracelet. All 31 mapped facial controls must deform the face,
keep FaceEX synchronized, and return to neutral:

```bash
blender --background --factory-startup --python-exit-code 1 --python tests/pgr_setup_blender.py
```

Pass `-- path/to/model.fbx --save-blend` to check and save one model. Reports
and logs are written to `tests/.runtime/pgr`.

PMX regression (requires MMD Tools) runs the actual Run Entire Setup chain for
each PMX in the folder. It verifies that every normal FBX stage runs, that all
character parts receive game shaders with their original PMX textures, and that
Light Vectors, outlines, the standard controls, face plate and lighting panel
are present. It exercises facial morph drivers and the rig's FK, IK and finger
checks, then saves the resulting blends and `results.json`:

```bash
blender --background --factory-startup --python-exit-code 1 --python tests/mmd_setup_blender.py -- chars/COLUMBINA
```

The version-specific dependency/conversion smoke test can run on Blender 4 or 5:

```bash
blender --background --factory-startup --python-exit-code 1 --python tests/rig_conversion_blender.py
```

This also verifies temporary dependency activation, nested scopes, cleanup after
failure, and preservation of dependencies already enabled by the user. The PMX
regression starts with optional dependencies disabled. The VMD regression on
Blender 5 checks the real root VMD on an FBX and Rigify controls, cleanup after
failure, and rejection of Blender versions below 5.0:

```bash
blender --background --factory-startup --python-exit-code 1 --python tests/vmd_motion_blender.py
blender --background --factory-startup --python-exit-code 1 --python tests/facial_transfer_blender.py
blender --background --factory-startup --python-exit-code 1 --python tests/optional_ueformat_blender.py
```

The VMD test uses `chars/vmdmotion/Motion & Facials.vmd` (or the root copy),
and generates a reproducible motion if neither file is present.
It also checks driven expressions on an FBX and facial-only VMD import. The
standalone facial regression needs no optional add-ons; it covers shared
channels, independent bone axes, linear weights, rollback, source snapshots,
custom properties and preservation of drivers and previous actions.

To measure import time on an existing character without saving the `.blend`:

```bash
blender --background --factory-startup --python-exit-code 1 --python tests/vmd_motion_performance_blender.py -- "Starriia - Kinich.blend"
```

This reports total import time and facial calibration time separately. Optional
`--engine PATH --snapshot output.json` and `--compare output.json` compare an
older facial engine against the current implementation, including evaluated
shape-key weights across the entire motion and unchanged body channels.

With `Starriia - Kinich.blend` and the two Hiasobi VMDs in `chars/vmdmotion`,
`tests/vmd_face_overlay_blender.py` checks the real body-then-face workflow,
including the operator's facial-only option, unchanged body curve coordinates,
scene duration, FPS, drivers and FK/IK switches. It does not save the blend.

The isolated texture-path regression runs in fresh Blender processes and checks
Windows exporter paths, Unicode filenames, saved/unsaved destinations, packed
images, temporary-folder cleanup and isolation from other characters:

```bash
blender --background --python-exit-code 1 --python tests/isolated_texture_paths_blender.py
```

### Command-Line Options
- `--blender` / `-b`: Path to the Blender executable (e.g. `"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"` or `"D:\GOOENGINE\goo-engine-4.4.3-windows+8ab20b9\blender.exe"`). Defaults to auto-detecting an installed Blender instance if omitted.
- `--character` / `--characters` / `-c`: One or more character folder names or paths to test (e.g. `collei-a-new-leaf`, `roxy-default`).
- `--save-blend`: Saves the resulting `.blend` file for visual inspection.
- `--verbose` / `-v`: Prints verbose in-process Blender console logs.

---

### Usage Examples

#### 1. Run a specific suite for a game
```bash
# Test Genshin rig on Collei using Blender 5.2
python tests/rig/genshin.py --blender "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --characters collei-a-new-leaf

# Test ZZZ rig on Roxy using Goo Engine
python tests/rig/zzz.py --blender "D:\GOOENGINE\goo-engine-4.4.3-windows+8ab20b9\blender.exe" --characters roxy-default

# Test textures for Honkai: Star Rail
python tests/textures/hsr.py --characters firefly-spring-missive

# Test face rig for Genshin Impact
python tests/facerig/genshin.py --characters collei-a-new-leaf

# Test character settings for Zenless Zone Zero
python tests/charactersettings/zzz.py --characters roxy-default
```

#### 2. Run multiple characters simultaneously
Pass multiple character names separated by spaces to `--characters`:
```bash
python tests/rig/genshin.py --characters collei-a-new-leaf columbina-moonweave-gossamer
```

#### 3. Use the Master Test Runner (run_tests.py)
```bash
# Run all test suites for Genshin Impact:
python tests/run_tests.py --game genshin --characters collei-a-new-leaf

# Run the rig suite across all supported games:
python tests/run_tests.py --suite rig --blender "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"

# Run a specific suite on a character and save the blend file:
python tests/run_tests.py --suite rig --game zzz --characters roxy-default --save-blend
```

## Legacy Genshin lighting and Goo nodes

Run `blender --background --factory-startup --python-exit-code 1 --python tests/genshin_legacy_lighting_blender.py`.
The test imports Old through the production material/outline/compositor path, creates the native Set Depth node when available, checks exact optional connections and idempotence, and verifies portable/native reversibility on Goo. It installs the real lighting panel and evaluates mesh attributes while moving Ambient, Fresnel, ShadowOffset, FresnelSize, and FresnelToggle controls. Reports are written under `tests/.runtime/genshin-legacy-lighting/`.

## Finger IK

Run `blender --background --factory-startup --python-exit-code 1 --python tests/finger_ik_blender.py -- hsr`, replacing `hsr` with `hi3`, `hna`, `pgr`, `nte`, or `wuwa` as needed. For Blender below 4.5, set `GACHA_TEST_BETTER_FBX_DIR` to a workspace copy of BetterFBX.

The test runs the complete isolated setup on a real character, checks all ten fingertip IK controls, widgets and collection assignments, enables each control's `FK_IK`, and verifies fingertip movement, reset, and independence from the opposite hand. Results and generated rigs are saved under `tests/.runtime/finger-ik/<version>/<game>/`.
