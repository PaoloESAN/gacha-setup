"""Blender In-Process Test Runner.

Invoked inside Blender in background mode:
  blender --background --python blender_executor.py -- <suite> <game> <character_dir> <output_json_path> <extra_json>
"""
import sys
import os
import json
import traceback
from pathlib import Path

# Setup sys.path so tests module and setup_wizard are importable
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = SCRIPT_DIR.parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

import bpy
import addon_utils

from tests.common.character_resolver import find_model_file, GAME_TYPE_NAMES


def enable_addons():
    """Ensure setup_wizard, rigify, and expykit are enabled."""
    addon_utils.enable("setup_wizard", default_set=True)
    addon_utils.enable("rigify", default_set=True)
    for mod in addon_utils.modules():
        name = getattr(mod, "__name__", "")
        if "expy" in name.lower() or "ueformat" in name.lower():
            try:
                addon_utils.enable(name, default_set=True)
            except Exception:
                pass


def clear_scene():
    """Reset scene to a completely clean state."""
    try:
        if bpy.context.object and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
    except Exception:
        pass
    for obj in list(bpy.data.objects):
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
        except Exception:
            pass
    for coll in list(bpy.data.collections):
        try:
            bpy.data.collections.remove(coll)
        except Exception:
            pass


def execute_pipeline(game_key, char_dir, model_file, target_suite):
    """Execute setup steps appropriate for the game and target test suite."""
    from setup_wizard.import_order import set_active_character_directory
    set_active_character_directory(char_dir)
    game_type = GAME_TYPE_NAMES.get(game_key, "GENSHIN_IMPACT")

    step_log = []

    def run_op(name, fn, **kwargs):
        try:
            res = fn("EXEC_DEFAULT", **kwargs)
            step_log.append({"step": name, "status": "OK", "result": str(res)})
            return True
        except Exception as e:
            step_log.append({"step": name, "status": "ERROR", "error": str(e), "trace": traceback.format_exc()})
            print(f"[PIPELINE ERROR] {name}: {e}")
            return False

    # Common Step 1: Import model
    if not run_op(
        "import_character_model",
        bpy.ops.genshin.import_model,
        filepath=model_file,
        file_directory=char_dir,
        game_type=game_type,
        next_step_idx=-1,
        invoker_type="",
        high_level_step_name="",
    ):
        return step_log

    # Common Step 2: Delete empties
    run_op("delete_empties", bpy.ops.genshin.delete_empties, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")

    # Texture & Material Steps
    if target_suite in ("textures", "charactersettings", "facerig", "rig"):
        run_op("import_materials", bpy.ops.genshin.import_materials, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")
        run_op("replace_default_materials", bpy.ops.genshin.replace_default_materials, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")
        run_op("import_character_textures", bpy.ops.genshin.import_textures, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")

    # Outlines / Lightmaps / Material Data / Transform fix
    if target_suite in ("charactersettings", "facerig", "rig"):
        if game_key in ("genshin", "zzz", "hsr"):
            run_op("import_outlines", bpy.ops.genshin.import_outlines, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")
            run_op("setup_geometry_nodes", bpy.ops.genshin.setup_geometry_nodes, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")
            run_op("import_outline_lightmaps", bpy.ops.genshin.import_outline_lightmaps, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")
            run_op("import_material_data", bpy.ops.genshin.import_material_data, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")
        elif game_key == "wuwa":
            run_op("import_outlines", bpy.ops.genshin.import_outlines, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")
            run_op("setup_geometry_nodes", bpy.ops.genshin.setup_geometry_nodes, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")
        elif game_key == "nte":
            run_op("nte_setup_outlines", bpy.ops.neverness_to_everness.set_up_outlines, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")
        elif game_key == "ake":
            run_op("ake_setup_outlines", bpy.ops.arknights_endfield.set_up_outlines, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")

        if hasattr(bpy.ops.genshin, "fix_transformations"):
            run_op("fix_transformations", bpy.ops.genshin.fix_transformations)

    # Rigging & Face Rig / Head driver steps
    if target_suite in ("facerig", "rig", "charactersettings"):
        run_op("rig_character", bpy.ops.hoyoverse.rig_character, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")

        if game_key == "zzz":
            run_op("zzz_setup_head_driver", bpy.ops.zenless_zone_zero.setup_head_driver)
        elif game_key == "wuwa":
            run_op("wuwa_setup_head_driver", bpy.ops.wuthering_waves.setup_head_driver)
        elif hasattr(bpy.ops.genshin, "setup_head_driver"):
            run_op("setup_head_driver", bpy.ops.genshin.setup_head_driver)

        if hasattr(bpy.ops.genshin, "set_color_management_to_standard"):
            run_op("set_color_management_to_standard", bpy.ops.genshin.set_color_management_to_standard)

        if hasattr(bpy.ops.genshin, "delete_specific_objects"):
            run_op("delete_specific_objects", bpy.ops.genshin.delete_specific_objects)

        if hasattr(bpy.ops.hoyoverse, "rename_shader_materials"):
            run_op("rename_shader_materials", bpy.ops.hoyoverse.rename_shader_materials, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")

        if game_key == "zzz" and hasattr(bpy.ops.zenless_zone_zero, "rename_collection_and_rig"):
            run_op("rename_collection_and_rig", bpy.ops.zenless_zone_zero.rename_collection_and_rig, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")
            run_op("move_lighting_panel_to_char_collection", bpy.ops.zenless_zone_zero.move_lighting_panel_to_char_collection, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")
        elif game_key == "wuwa" and hasattr(bpy.ops.wuthering_waves, "finish_setup"):
            run_op("wuwa_finish_setup", bpy.ops.wuthering_waves.finish_setup, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")
        elif game_key == "ake" and hasattr(bpy.ops.arknights_endfield, "finish_setup"):
            run_op("ake_finish_setup", bpy.ops.arknights_endfield.finish_setup, game_type=game_type, file_directory=char_dir, next_step_idx=-1, invoker_type="", high_level_step_name="")
        elif hasattr(bpy.ops.hoyoverse, "join_meshes_on_armature"):
            run_op("join_meshes_on_armature", bpy.ops.hoyoverse.join_meshes_on_armature)

    return step_log


def main():
    if "--" not in sys.argv:
        print("[ERROR] Missing arguments after '--'")
        sys.exit(1)

    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) < 4:
        print(f"[ERROR] Expected at least 4 arguments: suite game char_dir output_json [extra_json], got {args}")
        sys.exit(1)

    suite = args[0]
    game = args[1]
    char_dir = args[2]
    output_json_path = args[3]
    extra_json = json.loads(args[4]) if len(args) > 4 else {}

    print(f"\n[IN-BLENDER] Test Suite: {suite} | Game: {game}")
    print(f"[IN-BLENDER] Character dir: {char_dir}")

    enable_addons()
    clear_scene()

    model_file = find_model_file(char_dir)
    if not model_file:
        result = {
            "status": "FAIL",
            "suite": suite,
            "game": game,
            "character_dir": char_dir,
            "error": "No model file (.fbx / .uemodel) found in character directory",
            "checks": [],
            "pipeline_steps": [],
        }
        Path(output_json_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
        sys.exit(1)

    # 1. Run pipeline steps
    pipeline_log = execute_pipeline(game, char_dir, model_file, suite)

    # 2. Run suite assertions
    checks = []
    status = "PASS"
    error_msg = None

    try:
        if suite == "rig":
            from tests.rig.rig_assertions import assert_rig
            checks = assert_rig(game=game, char_dir=char_dir)
        elif suite == "textures":
            from tests.textures.texture_assertions import assert_textures
            checks = assert_textures(game=game, char_dir=char_dir)
        elif suite == "facerig":
            from tests.facerig.facerig_assertions import assert_facerig
            checks = assert_facerig(game=game, char_dir=char_dir)
        elif suite == "charactersettings":
            from tests.charactersettings.settings_assertions import assert_charactersettings
            checks = assert_charactersettings(game=game, char_dir=char_dir)
        else:
            raise ValueError(f"Unknown test suite: {suite}")

        failed_checks = [c for c in checks if not c.get("passed", False)]
        if failed_checks:
            status = "FAIL"
            error_msg = f"{len(failed_checks)} assertion(s) failed."
    except Exception as e:
        status = "FAIL"
        error_msg = str(e)
        checks.append({
            "name": f"Suite execution ({suite})",
            "passed": False,
            "message": f"Exception raised: {e}",
            "traceback": traceback.format_exc(),
        })

    # Optional blend save
    save_blend_path = extra_json.get("save_blend_path")
    if save_blend_path:
        try:
            bpy.ops.wm.save_as_mainfile(filepath=save_blend_path)
            print(f"[IN-BLENDER] Saved test blend to: {save_blend_path}")
        except Exception as e:
            print(f"[IN-BLENDER] Failed to save blend: {e}")

    result = {
        "status": status,
        "suite": suite,
        "game": game,
        "character_dir": char_dir,
        "character_name": Path(char_dir).name,
        "error": error_msg,
        "checks": checks,
        "pipeline_steps": pipeline_log,
    }

    Path(output_json_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n[IN-BLENDER] Test finished with status: {status}")
    sys.exit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()
