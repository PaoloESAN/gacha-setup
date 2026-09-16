import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
import bpy

from setup_wizard.services.isolation import face_widget_manager
from setup_wizard.services.isolation import rig_ui_manager

_ACTIVE_JOB = None
_POLL_TIMER_REGISTERED = False


def is_isolated_mode_enabled():
    """Check if safe isolated setup mode is enabled in add-on preferences."""
    try:
        pref = bpy.context.preferences.addons.get("setup_wizard")
        if pref and hasattr(pref.preferences, "setup_execution_mode"):
            return pref.preferences.setup_execution_mode == "ISOLATED"
    except Exception:
        pass
    return True


def should_auto_cleanup():
    try:
        pref = bpy.context.preferences.addons.get("setup_wizard")
        if pref and hasattr(pref.preferences, "auto_cleanup_temp_blend"):
            return bool(pref.preferences.auto_cleanup_temp_blend)
    except Exception:
        pass
    return True


def draw_setup_status_box(sub_layout, context, column):
    """Draws execution status and cancel/open log buttons in wizard UI panels."""
    is_running = getattr(context.scene, "gacha_setup_is_running", False)
    column.enabled = not is_running
    if is_running:
        status_row = sub_layout.row(align=True)
        status_row.label(
            text=getattr(context.scene, "gacha_setup_status", "Processing in background..."),
            icon="TIME",
        )
        status_row.operator("hoyoverse.cancel_isolated_setup", text="", icon="CANCEL")
    else:
        status_txt = getattr(context.scene, "gacha_setup_status", "")
        if status_txt and status_txt != "Idle":
            status_row = sub_layout.row(align=True)
            icon = (
                "ERROR"
                if "error" in status_txt.lower() or "failed" in status_txt.lower()
                else "CHECKMARK"
            )
            status_row.label(text=status_txt[:50], icon=icon)
            if "error" in status_txt.lower() or "failed" in status_txt.lower():
                status_row.operator(
                    "hoyoverse.open_isolated_setup_log", text="", icon="TEXT"
                )


def _runner_path():
    return Path(__file__).resolve().with_name("isolated_runner.py")


def snapshot_settings(scene, game_type=""):
    props = getattr(scene, "character_rigger_props", None)
    physics = False
    hair = 0.70
    clothes = 0.40
    disable_rigging = False

    if props is not None:
        physics = bool(
            getattr(
                props,
                "enable_hair_clothes_physics",
                getattr(props, "enable_hair_dress_physics", False),
            )
        )
        hair = float(getattr(props, "hair_physics_influence", 0.70))
        clothes = float(getattr(props, "clothes_physics_influence", 0.40))
        disable_rigging = bool(getattr(props, "disable_rigging", False))

    current_game = game_type or getattr(scene, "game_type_dropdown", "ZENLESS_ZONE_ZERO")
    values = {
        "game_type": current_game,
        "zzz_shader_type": getattr(scene, "zzz_shader_type", "KYTHERA"),
        "enable_hair_clothes_physics": physics,
        "hair_physics_influence": hair,
        "clothes_physics_influence": clothes,
        "disable_rigging": disable_rigging,
    }
    if props is not None:
        values["rigger_settings"] = {
            prop.identifier: getattr(props, prop.identifier)
            for prop in props.bl_rna.properties
            if prop.identifier != "rna_type"
            and not prop.is_readonly
            and prop.type in {"BOOLEAN", "INT", "FLOAT", "STRING", "ENUM"}
            and not getattr(prop, "is_array", False)
            and isinstance(getattr(props, prop.identifier), (bool, int, float, str))
        }
    return values


def _read_status(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def job_is_running():
    return bool(_ACTIVE_JOB and _ACTIVE_JOB["process"].poll() is None)


def cancel_job():
    global _ACTIVE_JOB
    if not _ACTIVE_JOB:
        return False
    try:
        proc = _ACTIVE_JOB.get("process")
        if proc and proc.poll() is None:
            proc.terminate()
        job_dir = _ACTIVE_JOB.get("job_dir")
        if job_dir and os.path.isdir(job_dir) and should_auto_cleanup():
            shutil.rmtree(job_dir, ignore_errors=True)
    except Exception:
        pass
    finally:
        _ACTIVE_JOB = None
        if hasattr(bpy.types.Scene, "gacha_setup_is_running"):
            bpy.context.scene.gacha_setup_is_running = False
        if hasattr(bpy.types.Scene, "gacha_setup_status"):
            bpy.context.scene.gacha_setup_status = "Cancelled by user"
    return True


def launch_job(
    context,
    operator,
    character_dir,
    selected_model_file="",
    game_type="",
    high_level_step_name="",
):
    global _ACTIVE_JOB

    if _ACTIVE_JOB and _ACTIVE_JOB["process"].poll() is None:
        if operator:
            operator.report({"WARNING"}, "A setup process is already running.")
        return {"CANCELLED"}

    character_dir = os.path.abspath(bpy.path.abspath(character_dir)) if character_dir else ""
    if selected_model_file:
        selected_model_file = os.path.abspath(bpy.path.abspath(selected_model_file))
        if not character_dir and os.path.isfile(selected_model_file):
            character_dir = os.path.dirname(selected_model_file)

    if not character_dir or not os.path.isdir(character_dir):
        if operator:
            operator.report({"ERROR"}, "Please select a valid character folder or model file.")
        return {"CANCELLED"}

    runner = _runner_path()
    if not runner.is_file():
        if operator:
            operator.report({"ERROR"}, "isolated_runner.py not found.")
        return {"CANCELLED"}

    # Determine module root and addon parent
    module_root = Path(__file__).resolve().parent.parent.parent
    module_name = module_root.name
    addon_parent = str(module_root.parent)

    job_dir = Path(tempfile.mkdtemp(prefix="GachaSetup_"))
    job_json = job_dir / "job.json"
    status_path = job_dir / "status.json"
    result_path = job_dir / "character_result.blend"
    log_path = job_dir / "isolated_blender.log"

    job = snapshot_settings(context.scene, game_type=game_type)
    job.update(
        {
            "character_directory": character_dir,
            "selected_model_file": selected_model_file or "",
            "gacha_module": module_name,
            "gacha_addon_parent": addon_parent,
            "status_path": str(status_path),
            "result_path": str(result_path),
        }
    )
    job_json.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")

    log_handle = open(log_path, "w", encoding="utf-8", errors="replace")

    # Run in background (--background) to keep the setup completely headless
    command = [
        bpy.app.binary_path,
        "--background",
        "--factory-startup",
        "--python",
        str(runner),
        "--",
        str(job_json),
    ]

    popen_kwargs = {
        "cwd": str(job_dir),
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
    }
    # On Windows, suppress any CMD console window popup
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    try:
        process = subprocess.Popen(command, **popen_kwargs)
    except Exception as exc:
        log_handle.close()
        shutil.rmtree(job_dir, ignore_errors=True)
        if operator:
            operator.report({"ERROR"}, f"Could not launch background Blender process: {exc!r}")
        return {"CANCELLED"}

    _ACTIVE_JOB = {
        "process": process,
        "job_dir": str(job_dir),
        "status_path": str(status_path),
        "result_path": str(result_path),
        "log_path": str(log_path),
        "log_handle": log_handle,
        "originating_scene_name": context.scene.name,
        "game_type": game_type or job.get("game_type", ""),
    }

    scene = context.scene
    scene.gacha_setup_is_running = True
    scene.gacha_setup_status = "Starting background setup..."
    scene.gacha_setup_last_log = str(log_path)

    _ensure_poll_timer()
    if operator:
        operator.report(
            {"INFO"},
            "Setup started in background. Character will be added automatically.",
        )
    return {"FINISHED"}


def _ensure_poll_timer():
    global _POLL_TIMER_REGISTERED
    if _POLL_TIMER_REGISTERED:
        return
    _POLL_TIMER_REGISTERED = True
    bpy.app.timers.register(_poll_job, first_interval=0.5, persistent=False)


def _tag_all_areas_redraw():
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type in ("VIEW_3D", "NODE_EDITOR", "PROPERTIES"):
                    area.tag_redraw()
    except Exception:
        pass


def _poll_job():
    global _ACTIVE_JOB, _POLL_TIMER_REGISTERED

    if not _ACTIVE_JOB:
        _POLL_TIMER_REGISTERED = False
        return None

    scene = bpy.data.scenes.get(_ACTIVE_JOB.get("originating_scene_name", "")) or bpy.context.scene
    status = _read_status(_ACTIVE_JOB["status_path"])
    state = status.get("state", "RUNNING")
    message = status.get("message", "")
    if message:
        scene.gacha_setup_status = f"{message}"
    _tag_all_areas_redraw()

    process = _ACTIVE_JOB["process"]
    return_code = process.poll()
    if return_code is None:
        return 0.5  # Next poll in 0.5s

    # Process finished
    try:
        _ACTIVE_JOB["log_handle"].flush()
        _ACTIVE_JOB["log_handle"].close()
    except Exception:
        pass

    result_path = _ACTIVE_JOB["result_path"]
    job_dir = _ACTIVE_JOB["job_dir"]
    status = _read_status(_ACTIVE_JOB["status_path"])

    if status.get("state") == "SUCCESS" and os.path.isfile(result_path):
        try:
            manifest_collections = status.get("collections", [])
            manifest_loose = status.get("loose_objects", [])
            effective_game_type = _ACTIVE_JOB.get("game_type") or status.get("game_type", "")
            append_result(
                result_path,
                manifest_collections=manifest_collections,
                manifest_loose_objects=manifest_loose,
                target_scene=scene,
                game_type=effective_game_type,
            )
            scene.gacha_setup_status = "Setup completed successfully."

            # Automatically clean up temporary blend file and directory if enabled
            if should_auto_cleanup():
                try:
                    shutil.rmtree(job_dir, ignore_errors=True)
                    print(f"[GACHA SETUP] Cleaned up temporary files: {job_dir}")
                except Exception as del_err:
                    print(f"[GACHA SETUP] Cleanup notice: {del_err}")
        except Exception as exc:
            scene.gacha_setup_status = f"Error appending character: {exc}"
            print(f"[GACHA SETUP] Error in append_result:\n{traceback.format_exc()}")
    else:
        err_msg = status.get("message") or f"Process exited with code {return_code}. Check log."
        scene.gacha_setup_status = f"Setup failed: {err_msg}"
        if status.get("traceback"):
            print(f"[GACHA SETUP CHILD ERROR]\n{status['traceback']}")

    scene.gacha_setup_is_running = False
    _tag_all_areas_redraw()

    _ACTIVE_JOB = None
    _POLL_TIMER_REGISTERED = False
    return None


def append_result(
    result_path,
    manifest_collections=None,
    manifest_loose_objects=None,
    target_scene=None,
    game_type="",
):
    """
    Appends finished character from the temporary .blend into target scene,
    deduplicates FaceRig widgets, registers Rig UI to eliminate lag, and
    synchronizes scene-level settings (Color Management, SSR, Compositor).
    """
    result_path = str(Path(result_path).resolve())
    if not os.path.isfile(result_path):
        raise FileNotFoundError(f"Result file not found: {result_path}")

    canonical_widgets = face_widget_manager.capture_existing_face_widgets()

    with bpy.data.libraries.load(result_path, link=False) as (data_from, data_to):
        available_colls = list(data_from.collections)
        if manifest_collections:
            chosen_colls = [c for c in manifest_collections if c in available_colls]
            data_to.collections = chosen_colls if chosen_colls else available_colls
        else:
            data_to.collections = available_colls

        available_objs = list(data_from.objects)
        if manifest_loose_objects:
            data_to.objects = [o for o in manifest_loose_objects if o in available_objs]

    target = target_scene or bpy.context.scene
    scene_root = target.collection
    all_imported_objects = []

    # Link imported collections directly with original hierarchy
    for loaded_coll in (data_to.collections or []):
        if loaded_coll is None:
            continue
        if loaded_coll.name not in scene_root.children:
            scene_root.children.link(loaded_coll)
        all_imported_objects.extend(list(loaded_coll.all_objects))

    # Link loose objects if any
    for loaded_obj in (data_to.objects or []):
        if loaded_obj is None:
            continue
        if loaded_obj.name not in scene_root.objects:
            scene_root.objects.link(loaded_obj)
        all_imported_objects.append(loaded_obj)

    # 1. Deduplicate FaceRig widgets
    face_stats = face_widget_manager.dedupe_shared_face_widgets(
        all_imported_objects, canonical_widgets
    )

    # 2. Register Rig UI in writable operator context (zero lag)
    rig_stats = rig_ui_manager.initialize_rig_uis(all_imported_objects)

    # 3. Synchronize scene-level settings (Color Management, EEVEE SSR, Compositor nodes)
    sync_scene_environment(target_scene=target, game_type=game_type)

    # 4. Exclude and hide widget collections (unchecks the viewport checkbox in outliner)
    exclude_widget_collections(target)

    # Select primary armature for immediate user interaction
    try:
        armatures = [o for o in all_imported_objects if o.type == "ARMATURE"]
        if armatures:
            bpy.context.view_layer.objects.active = armatures[0]
            armatures[0].select_set(True)
    except Exception:
        pass

    try:
        bpy.context.view_layer.update()
    except Exception:
        pass

    print(
        f"[GACHA SETUP] Character appended successfully. "
        f"Face widgets remapped: {face_stats.get('face_widget_bones_remapped', 0)}, "
        f"Rigs ready: {rig_stats.get('rig_ui_ready', 0)}"
    )


def exclude_widget_collections(scene=None):
    """
    Excludes (unchecks the checkbox in Outliner) and hides all widget collections
    (WGTS_*, wgt*, *widget*) in the view layers of the scene so they do not
    clutter the viewport after append.
    """
    scene = scene or bpy.context.scene
    if not scene:
        return

    # 1. Hide on data collections
    for coll in bpy.data.collections:
        cname = coll.name.lower()
        if cname.startswith("wgts") or cname.startswith("wgt") or "widget" in cname:
            try:
                coll.hide_viewport = True
                coll.hide_select = True
                coll.hide_render = True
            except Exception:
                pass

    # 2. Exclude from all view layers (unchecks the checkbox in Outliner)
    for vl in getattr(scene, "view_layers", []):
        def _traverse(lc):
            c = getattr(lc, "collection", None)
            if c:
                cname = c.name.lower()
                if cname.startswith("wgts") or cname.startswith("wgt") or "widget" in cname:
                    try:
                        lc.exclude = True
                    except Exception:
                        pass
            for child in getattr(lc, "children", []):
                _traverse(child)

        try:
            _traverse(vl.layer_collection)
        except Exception:
            pass


def sync_scene_environment(target_scene=None, game_type=""):
    """
    Synchronizes scene-level configurations to the main active Blender scene:
    1. Color Management: Standard view transform and sRGB display device.
    2. EEVEE Screen Space Reflections / Next Raytracing and Shadows.
    3. Render frame rate & Film transparency.
    4. Post-processing Compositor node tree.
    """
    scene = target_scene or bpy.context.scene
    if not scene:
        return

    # 1. Color Management
    try:
        if hasattr(scene, "display_settings") and hasattr(scene.display_settings, "display_device"):
            scene.display_settings.display_device = "sRGB"
    except Exception as ex:
        print(f"[GACHA SETUP] Display device notice: {ex}")

    try:
        gt = (game_type or "").upper()
        if gt == "ARKNIGHTS_ENDFIELD":
            try:
                scene.view_settings.view_transform = "AgX"
                scene.view_settings.look = "AgX - Medium High Contrast"
            except Exception:
                scene.view_settings.view_transform = "Standard"
        else:
            scene.view_settings.view_transform = "Standard"
    except Exception as ex:
        print(f"[GACHA SETUP] Color management notice: {ex}")

    # 2. EEVEE Screen Space Reflections / Raytracing
    try:
        if hasattr(scene, "eevee"):
            eevee = scene.eevee
            # Blender 4.2+ / 5.x EEVEE Next Raytracing
            if hasattr(eevee, "use_raytracing"):
                try:
                    eevee.use_raytracing = True
                except Exception:
                    pass
            if hasattr(eevee, "raytracing_method"):
                try:
                    eevee.raytracing_method = "SCREEN_SPACE"
                except Exception:
                    pass
            # Blender 4.1 and earlier EEVEE SSR
            if hasattr(eevee, "use_ssr"):
                try:
                    eevee.use_ssr = True
                    eevee.use_ssr_refraction = True
                except Exception:
                    pass
            if hasattr(eevee, "use_shadows"):
                try:
                    eevee.use_shadows = True
                except Exception:
                    pass
    except Exception as ex:
        print(f"[GACHA SETUP] EEVEE SSR notice: {ex}")

    # 3. Render FPS & Film Transparency
    try:
        gt = (game_type or "").upper()
        if gt in ("WUTHERING_WAVES", "ARKNIGHTS_ENDFIELD"):
            scene.render.fps = 60
        if gt in ("GENSHIN_IMPACT", "NEVERNESS_TO_EVERNESS"):
            scene.render.film_transparent = False
    except Exception as ex:
        print(f"[GACHA SETUP] Render settings notice: {ex}")

    # 4. Compositor Post-Processing Nodes
    try:
        _setup_scene_compositor(scene, game_type)
    except Exception as ex:
        print(f"[GACHA SETUP] Compositor sync notice: {ex}")


def _setup_scene_compositor(scene, game_type):
    """
    Ensures compositor post-processing nodes are configured directly in the target scene.
    """
    if not scene:
        return

    # Enable compositing nodes on scene
    if hasattr(scene, "use_nodes"):
        scene.use_nodes = True

    gt = (game_type or "").upper()
    if gt == "WUTHERING_WAVES":
        try:
            from setup_wizard.misc_final_steps import setup_wuwa_compositor_nodes
            setup_wuwa_compositor_nodes(scene=scene)
            print("[GACHA SETUP] Configured Wuthering Waves Compositor nodes in main scene.")
        except Exception as exc:
            print(f"[GACHA SETUP] WuWa Compositor setup notice: {exc}")

    elif gt == "ARKNIGHTS_ENDFIELD":
        try:
            from setup_wizard.misc_final_steps import setup_ake_compositor_nodes
            setup_ake_compositor_nodes(scene=scene)
            # Setup AKE World environment nodes if available
            world = scene.world
            world_ng = bpy.data.node_groups.get("Arknights_Endfield_Env")
            if world and world_ng:
                world.use_nodes = True
                tree = world.node_tree
                if tree:
                    out_node = next((n for n in tree.nodes if n.type == "OUTPUT_WORLD"), None)
                    if not out_node:
                        out_node = tree.nodes.new("ShaderNodeOutputWorld")
                    for bg in [n for n in tree.nodes if n.type == "BACKGROUND"]:
                        try:
                            tree.nodes.remove(bg)
                        except Exception:
                            pass
                    grp_node = next((n for n in tree.nodes if n.type == "GROUP" and n.node_tree == world_ng), None)
                    if not grp_node:
                        grp_node = tree.nodes.new("ShaderNodeGroup")
                        grp_node.node_tree = world_ng
                    if grp_node.outputs and out_node.inputs:
                        tree.links.new(grp_node.outputs[0], out_node.inputs[0])
            print("[GACHA SETUP] Configured Arknights: Endfield Compositor & World nodes in main scene.")
        except Exception as exc:
            print(f"[GACHA SETUP] AKE Compositor setup notice: {exc}")

    elif gt == "NEVERNESS_TO_EVERNESS":
        try:
            if hasattr(bpy.ops.neverness_to_everness, "setup_compositor_nodes"):
                bpy.ops.neverness_to_everness.setup_compositor_nodes("EXEC_DEFAULT")
                print("[GACHA SETUP] Configured Neverness to Everness Compositor nodes in main scene.")
        except Exception as exc:
            print(f"[GACHA SETUP] NTE Compositor setup notice: {exc}")

    elif gt == "GENSHIN_IMPACT":
        try:
            wm = getattr(bpy.context, "window_manager", None)
            pp_enabled = getattr(wm, "post_processing_setup_enabled", False)
            if pp_enabled and hasattr(bpy.ops.hoyoverse, "custom_composite_node_setup"):
                bpy.ops.hoyoverse.custom_composite_node_setup("EXEC_DEFAULT")
                if hasattr(bpy.ops.hoyoverse, "post_processing_default_settings"):
                    bpy.ops.hoyoverse.post_processing_default_settings("EXEC_DEFAULT")
                print("[GACHA SETUP] Configured Genshin Compositor nodes in main scene.")
        except Exception as exc:
            print(f"[GACHA SETUP] Genshin Compositor setup notice: {exc}")
