import os
import bpy
from bpy.app.handlers import persistent
from bpy.types import Operator

from setup_wizard.services.isolation import isolation_service


@persistent
def _clear_stale_setup_state(_dummy=None):
    """Reset persisted setup-running flags when opening a .blend with no live worker."""
    if isolation_service.job_is_running():
        return
    for scene in getattr(bpy.data, "scenes", ()):
        if getattr(scene, "gacha_setup_is_running", False):
            scene.gacha_setup_is_running = False
            status = getattr(scene, "gacha_setup_status", "")
            if status and "error" not in status.lower() and "failed" not in status.lower():
                scene.gacha_setup_status = "Idle"


class GACHA_OT_CancelIsolatedSetup(Operator):
    """Cancels the character setup running in the background"""

    bl_idname = "hoyoverse.cancel_isolated_setup"
    bl_label = "Cancel Setup"

    def execute(self, context):
        if isolation_service.cancel_job():
            self.report({"INFO"}, "Setup process cancelled.")
            return {"FINISHED"}
        self.report({"WARNING"}, "No active setup process.")
        return {"CANCELLED"}


class GACHA_OT_OpenIsolatedSetupLog(Operator):
    """Opens the log file of the last background setup process"""

    bl_idname = "hoyoverse.open_isolated_setup_log"
    bl_label = "Open Setup Log"

    def execute(self, context):
        log_path = getattr(context.scene, "gacha_setup_last_log", "")
        if not log_path or not os.path.isfile(log_path):
            self.report({"WARNING"}, "No log file available.")
            return {"CANCELLED"}
        bpy.ops.wm.path_open(filepath=log_path)
        return {"FINISHED"}


CLASSES = (
    GACHA_OT_CancelIsolatedSetup,
    GACHA_OT_OpenIsolatedSetupLog,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.Scene.gacha_setup_is_running = bpy.props.BoolProperty(
        name="Gacha Setup Running",
        default=False,
    )
    bpy.types.Scene.gacha_setup_status = bpy.props.StringProperty(
        name="Gacha Setup Status",
        default="Idle",
    )
    bpy.types.Scene.gacha_setup_last_log = bpy.props.StringProperty(
        name="Gacha Setup Last Log",
        default="",
        subtype="FILE_PATH",
    )

    if _clear_stale_setup_state not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_clear_stale_setup_state)


def unregister():
    if _clear_stale_setup_state in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_clear_stale_setup_state)

    isolation_service.cancel_job()

    for name in (
        "gacha_setup_is_running",
        "gacha_setup_status",
        "gacha_setup_last_log",
    ):
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)

    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
