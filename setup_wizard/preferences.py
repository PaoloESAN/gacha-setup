import bpy


class CharacterSetupWizardAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout: bpy.types.UILayout = self.layout
        layout.label(text="HoYoverse Setup Wizard has no preferences config.")
