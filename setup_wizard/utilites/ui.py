import bpy
from bpy.types import Panel

from setup_wizard.utilites.jideeh_cam_rig import (
    build as build_jideeh_camrig,
)


class CSW_OT_JideehCamera(bpy.types.Operator):
    bl_idname = "setup_wizard.jideeh_camera"
    bl_label = "Camera Pro"
    bl_description = "Create Camera Pro in the active scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            rig, cam = build_jideeh_camrig(context)
            self.report({'INFO'}, f"Successfully created Camera Pro: '{rig.name}'")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to create Camera Pro: {e}")
            return {'CANCELLED'}


class CSW_PT_Utilities_UI_Layout(Panel):
    bl_label = "Utilities"
    bl_idname = 'CSW_PT_Utilities_UI_Layout'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gacha Setup"
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        row_cam = col.row(align=True)
        row_cam.operator("setup_wizard.create_camera_pro", text="Jideeh's Camera", icon="CAMERA_DATA")
        doc_cam = row_cam.operator("wm.url_open", text="", icon="TEXT")
        doc_cam.url = "https://gacha-setup.pages.dev/utilities/#jideehs-camera"

        from setup_wizard.utilites.eye_through_hair import supports_eye_through_hair
        if supports_eye_through_hair():
            row_eye = col.row(align=True)
            row_eye.operator("setup_wizard.eye_through_hair", text="Eye Through Hair", icon="HIDE_OFF")
            doc_eye = row_eye.operator("wm.url_open", text="", icon="TEXT")
            doc_eye.url = "https://gacha-setup.pages.dev/utilities/#eye-through-hair"
            col.operator("setup_wizard.hair_shadows", text="Hair Shadows", icon="SHADING_RENDERED")


