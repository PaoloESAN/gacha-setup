import os
import bpy
from bpy.types import Operator

from setup_wizard.services.isolation import isolation_service


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


def unregister():
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
