import addon_utils
import bpy
import importlib
import json
import os
import re
import sys
import time
import traceback
from contextlib import nullcontext
from pathlib import Path

GAME_TO_WIZARD = {
    "GENSHIN_IMPACT": "genshin.setup_wizard_ui",
    "HONKAI_STAR_RAIL": "honkai_star_rail.setup_wizard_ui",
    "ZENLESS_ZONE_ZERO": "zenless_zone_zero.setup_wizard_ui",
    "NEVERNESS_TO_EVERNESS": "neverness_to_everness.setup_wizard_ui",
    "WUTHERING_WAVES": "wuthering_waves.setup_wizard_ui",
    "ARKNIGHTS_ENDFIELD": "arknights_endfield.setup_wizard_ui",
    "PUNISHING_GRAY_RAVEN": "punishing_gray_raven.setup_wizard_ui",
}


def load_job():
    if "--" not in sys.argv:
        raise RuntimeError("Missing job.json in arguments.")
    index = sys.argv.index("--")
    if index + 1 >= len(sys.argv):
        raise RuntimeError("Path to job.json was not provided.")
    job_path = Path(sys.argv[index + 1]).resolve()
    return json.loads(job_path.read_text(encoding="utf-8"))


JOB = load_job()
STATUS_PATH = Path(JOB["status_path"])
RESULT_PATH = Path(JOB["result_path"])


def write_status(state, message="", **extra):
    payload = {"state": state, "message": message, "time": time.time(), **extra}
    temp = STATUS_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, STATUS_PATH)
    print(f"[GACHA SETUP WORKER] {state}: {message}", flush=True)


def clear_all_objects():
    """Completely clear temporary Blender scene before registering Gacha Setup."""
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

    scene = bpy.context.scene
    for collection in list(scene.collection.children):
        try:
            scene.collection.children.unlink(collection)
        except Exception:
            pass

    for collection in list(bpy.data.collections):
        try:
            if collection.users == 0:
                bpy.data.collections.remove(collection)
        except Exception:
            pass

    for datablocks in (
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.meshes,
        bpy.data.curves,
    ):
        for datablock in list(datablocks):
            try:
                if datablock.users == 0:
                    datablocks.remove(datablock)
            except Exception:
                pass

    try:
        bpy.data.orphans_purge(
            do_local_ids=True,
            do_linked_ids=True,
            do_recursive=True,
        )
    except Exception:
        pass

    write_status("SCENE_CLEARED", "Temporary scene cleared.")


def ensure_gacha_registered():
    os.environ["GACHA_SETUP_ISOLATED_WORKER"] = "1"
    addon_parent = JOB.get("gacha_addon_parent", "")
    module_name = JOB.get("gacha_module", "setup_wizard")

    if addon_parent and addon_parent not in sys.path:
        sys.path.insert(0, addon_parent)

    write_status("ENABLE_GACHA", "Registering Gacha Setup...")

    enabled = False
    try:
        is_enabled, _ = addon_utils.check(module_name)
        if not is_enabled:
            try:
                bpy.ops.preferences.addon_enable(module=module_name)
            except Exception:
                pass
        enabled, _ = addon_utils.check(module_name)
    except Exception:
        pass

    setup_wizard = importlib.import_module(module_name)
    if not enabled:
        try:
            setup_wizard.register()
        except Exception as exc:
            print(f"[GACHA SETUP WORKER] Direct register notice: {exc!r}", flush=True)

    try:
        wizard = importlib.import_module(module_name + ".genshin_setup_wizard")
        if hasattr(wizard, "on_register"):
            wizard.on_register()
    except Exception as exc:
        print(f"[GACHA SETUP WORKER] Dependency bootstrap notice: {exc!r}", flush=True)

    detected = tuple(setup_wizard.bl_info.get("version", (0, 0, 0)))
    write_status(
        "GACHA_READY",
        "Gacha Setup ready.",
        gacha_version=".".join(str(x) for x in detected),
    )


def apply_settings():
    scene = bpy.context.scene

    if hasattr(scene, "game_type_dropdown"):
        try:
            scene.game_type_dropdown = JOB["game_type"]
        except Exception:
            pass

    if JOB["game_type"] == "ZENLESS_ZONE_ZERO" and hasattr(scene, "zzz_shader_type"):
        try:
            scene.zzz_shader_type = JOB.get("zzz_shader_type", "KYTHERA")
        except Exception:
            pass

    props = getattr(scene, "character_rigger_props", None)
    if props is None:
        return

    values = {
        "enable_hair_clothes_physics": JOB.get("enable_hair_clothes_physics", False),
        "enable_hair_dress_physics": JOB.get("enable_hair_clothes_physics", False),
        "hair_physics_influence": JOB.get("hair_physics_influence", 0.70),
        "clothes_physics_influence": JOB.get("clothes_physics_influence", 0.40),
        "disable_rigging": JOB.get("disable_rigging", False),
    }
    for name, value in values.items():
        if hasattr(props, name):
            try:
                setattr(props, name, value)
            except Exception:
                pass

    # Restore all scalar rigging properties (IK toggles, pole targets, head tracking, etc.)
    for name, value in JOB.get("rigger_settings", {}).items():
        if hasattr(props, name):
            try:
                setattr(props, name, value)
            except Exception:
                pass


def save_and_quit():
    try:
        write_status("PACKAGING", "Packaging finished character...")
        scene = bpy.context.scene

        # Validate result integrity
        mesh_count = sum(1 for obj in scene.objects if obj.type == "MESH")
        if not mesh_count:
            raise RuntimeError("Setup produced no mesh objects.")
        if not JOB.get("disable_rigging", False) and not any(
            obj.type == "ARMATURE" and obj.data.get("rig_id") for obj in scene.objects
        ):
            raise RuntimeError("Setup produced no generated rig with rig_id.")

        # Capture collections and loose objects in clean original hierarchy
        top_level_collections = [c.name for c in scene.collection.children]
        loose_objects = [o.name for o in scene.collection.objects]

        write_status(
            "SAVING",
            "Writing temporary .blend...",
            collections=top_level_collections,
            loose_objects=loose_objects,
        )
        bpy.ops.wm.save_as_mainfile(filepath=str(RESULT_PATH))

        write_status(
            "SUCCESS",
            "Setup completed successfully.",
            collections=top_level_collections,
            loose_objects=loose_objects,
            game_type=JOB.get("game_type", ""),
        )
    except Exception:
        write_status(
            "ERROR",
            "Failed while saving isolated result.",
            traceback=traceback.format_exc(),
        )
    finally:
        if bpy.app.background:
            sys.exit(0)
        else:
            bpy.app.timers.register(
                lambda: (bpy.ops.wm.quit_blender(), None)[1],
                first_interval=0.25,
            )
    return None


def run_setup():
    try:
        apply_settings()

        game = JOB["game_type"]
        if game not in GAME_TO_WIZARD:
            raise RuntimeError(f"Unsupported game: {game}")

        character_dir = JOB["character_directory"]
        if not os.path.isdir(character_dir):
            raise RuntimeError(f"Character directory does not exist: {character_dir}")

        import_order = importlib.import_module(JOB["gacha_module"] + ".import_order")
        selected_file = JOB.get("selected_model_file", "")
        if selected_file and not os.path.isfile(selected_file):
            raise RuntimeError(f"Selected model file does not exist: {selected_file}")

        config = json.loads(
            Path(import_order.__file__).with_name("config_ui.json").read_text(encoding="utf-8")
        )
        wizard_name = GAME_TO_WIZARD[game]
        prefix, suffix = wizard_name.split(".", 1)
        order = config.get("ui_order", {})
        steps = order.get(wizard_name) or order.get(prefix.upper() + "_OT_" + suffix)

        from setup_wizard.services.isolation.workflow import checked_workflow

        write_status("SETUP_RUNNING", "Running setup pipeline...")

        # Provide a VIEW_3D context override so all steps, operators and third-party addons
        # (like ExpyKit) have access to valid space_data and areas in headless mode.
        screens = [bpy.context.screen] if getattr(bpy.context, "screen", None) else []
        screens.extend([s for s in bpy.data.screens if s not in screens])
        ov = {}
        for s in screens:
            for a in getattr(s, "areas", []):
                if a.type == "VIEW_3D":
                    sp = a.spaces.active if a.spaces else None
                    reg = next((r for r in a.regions if r.type == "WINDOW"), None)
                    ov = {"screen": s, "area": a}
                    if sp:
                        ov["space_data"] = sp
                    if reg and not bpy.app.background:
                        ov["region"] = reg
                    break
            if ov:
                break

        override_ctx = (
            bpy.context.temp_override(**ov)
            if (ov and hasattr(bpy.context, "temp_override"))
            else nullcontext()
        )

        with override_ctx:
            with checked_workflow(import_order, steps):
                if selected_file and os.path.isfile(selected_file):
                    import_order.set_active_character_directory(character_dir)
                    import_op = import_order.ComponentFunctionFactory.create_component_function(
                        "import_character_model"
                    )
                    import_op(
                        "EXEC_DEFAULT",
                        filepath=selected_file,
                        file_directory=character_dir,
                        next_step_idx=1,
                        invoker_type="invoke_next_step_ui",
                        high_level_step_name=GAME_TO_WIZARD[game],
                        game_type=game,
                    )
                else:
                    import_order.NextStepInvoker().invoke(
                        0,
                        "invoke_next_step_ui",
                        file_path_to_cache=character_dir,
                        high_level_step_name=GAME_TO_WIZARD[game],
                        game_type=game,
                    )

        if bpy.app.background:
            save_and_quit()
        else:
            bpy.app.timers.register(save_and_quit, first_interval=0.75)
    except Exception:
        write_status(
            "ERROR",
            "Error during setup process.",
            traceback=traceback.format_exc(),
        )
        if bpy.app.background:
            sys.exit(1)
        else:
            bpy.app.timers.register(
                lambda: (bpy.ops.wm.quit_blender(), None)[1],
                first_interval=0.5,
            )
    return None


def bootstrap():
    try:
        clear_all_objects()
        ensure_gacha_registered()
        if bpy.app.background:
            run_setup()
        else:
            bpy.app.timers.register(run_setup, first_interval=1.0)
    except Exception:
        write_status(
            "ERROR",
            "Error initializing isolated setup.",
            traceback=traceback.format_exc(),
        )
        if bpy.app.background:
            sys.exit(1)
        else:
            bpy.app.timers.register(
                lambda: (bpy.ops.wm.quit_blender(), None)[1],
                first_interval=0.5,
            )
    return None


if bpy.app.background:
    bootstrap()
else:
    bpy.app.timers.register(bootstrap, first_interval=0.25)
