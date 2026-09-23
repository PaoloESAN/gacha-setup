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
