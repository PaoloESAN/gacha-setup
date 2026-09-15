import bpy
from setup_wizard.addon_updater import addon_updater_ops


@addon_updater_ops.make_annotations
class CharacterSetupWizardAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__.split('.')[0] if __package__ else "setup_wizard"

    # Addon updater preferences
    auto_check_update: bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False,
    )
    updater_interval_months: bpy.props.IntProperty(
        name="Months",
        description="Number of months between checking for updates",
        default=0,
        min=0,
    )
    updater_interval_days: bpy.props.IntProperty(
        name="Days",
        description="Number of days between checking for updates",
        default=1,
        min=0,
    )
    updater_interval_hours: bpy.props.IntProperty(
        name="Hours",
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23,
    )
    updater_interval_minutes: bpy.props.IntProperty(
        name="Minutes",
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59,
    )

    # Setup isolation preferences
    setup_execution_mode: bpy.props.EnumProperty(
        name="Setup Mode",
        description="Execution mode for Run Entire Setup",
        items=[
            (
                "ISOLATED",
                "Isolated Safe Setup (Recommended)",
                "Runs setup in a clean temporary process to eliminate object/shader collisions and viewport lag",
            ),
            (
                "DIRECT",
                "Direct In-Scene (Legacy)",
                "Runs setup directly inside the current project scene",
            ),
        ],
        default="ISOLATED",
    )
    auto_cleanup_temp_blend: bpy.props.BoolProperty(
        name="Clean Up Temp Files",
        description="Automatically delete the temporary .blend file and folder after successful setup",
        default=True,
    )
    keep_log_on_error: bpy.props.BoolProperty(
        name="Keep Log on Error",
        description="Preserve the isolated process log if setup encounters an error",
        default=True,
    )

    def draw(self, context):
        layout: bpy.types.UILayout = self.layout

        iso_box = layout.box()
        iso_box.label(text="Character Setup Pipeline", icon="MODIFIER")
        iso_box.prop(self, "setup_execution_mode")
        row = iso_box.row()
        row.prop(self, "auto_cleanup_temp_blend")
        row.prop(self, "keep_log_on_error")

        layout.separator()
        addon_updater_ops.update_settings_ui(self, context)

