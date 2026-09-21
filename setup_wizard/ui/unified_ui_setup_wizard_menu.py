import bpy

from bpy.props import EnumProperty
from bpy.types import Panel

from setup_wizard import bl_info
from setup_wizard.addon_updater import addon_updater_ops
from setup_wizard.domain.game_types import GameType
from setup_wizard.ui.addon_icon_manager import get_addon_icon_id


class CSW_PT_Updater_UI_Layout(Panel):
    bl_label = "Add-on info"
    bl_idname = 'CSW_PT_Updater_UI_Layout'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gacha Setup"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        updater = addon_updater_ops.updater

        # Trigger background update check if interval reached
        addon_updater_ops.check_for_update_background()

        # Everything inside a single dark gray container box
        box = layout.box()

        # Top Header: Thumbnail + Title + Version
        header_row = box.row()

        # Thumbnail Image
        icon_id = get_addon_icon_id("addon_icon.png")
        icon_col = header_row.column()
        if icon_id:
            icon_col.template_icon(icon_value=icon_id, scale=3.2)
        else:
            icon_col.label(text="", icon="COMMUNITY")

        # Text Info
        text_col = header_row.column()

        raw_version = bl_info.get("version", (0, 0, 0))
        if len(raw_version) >= 4:
            ver_text = f"v{raw_version[0]}.{raw_version[1]}.{raw_version[2]} Beta {raw_version[3]}"
        else:
            ver_text = "v" + ".".join(str(v) for v in raw_version)

        text_col.separator(factor=0.75)

        # Line 1: Title + Website Link Icon
        row_title = text_col.row(align=True)
        row_title.label(text="Gacha Setup")
        web_btn = row_title.operator("wm.url_open", text="", icon="URL")
        web_btn.url = "https://gacha-setup.pages.dev/"

        text_col.separator(factor=0.3)

        # Line 2: Version + Changelog Link Icon (solo icono)
        row_ver = text_col.row(align=True)
        row_ver.label(text=ver_text)
        cl_btn = row_ver.operator("wm.url_open", text="", icon="TEXT")
        cl_btn.url = "https://github.com/PaoloESAN/gacha-setup/releases"

        # Need restart after update alert
        if not updater.auto_reload_post_update:
            saved_state = updater.json
            if saved_state and saved_state.get("just_updated", False):
                rst_col = box.column(align=True)
                rst_col.alert = True
                rst_col.operator(
                    "wm.quit_blender",
                    text="Restart Blender to Complete Update",
                    icon="ERROR"
                )
                return

        # New update ready alert
        if updater.update_ready:
            alert_col = box.column(align=True)
            alert_col.alert = True
            target_version = updater.update_version or "new version"
            alert_col.label(text=f"Update ready: {target_version}")
            alert_col.operator(
                addon_updater_ops.AddonUpdaterUpdateNow.bl_idname,
                text="Update Now",
                icon="IMPORT"
            )
            box.separator(factor=0.4)

        # Check for Updates Button
        if updater.async_checking:
            chk_row = box.row(align=True)
            chk_row.label(text="Checking for updates...")
            chk_row.operator(addon_updater_ops.AddonUpdaterEndBackground.bl_idname, text="", icon="X")
        elif updater.error is not None:
            err_col = box.column(align=True)
            err_col.label(text=str(updater.error))
            err_col.operator(addon_updater_ops.AddonUpdaterCheckNow.bl_idname, text="Retry Check", icon="FILE_REFRESH")
        else:
            box.operator(
                addon_updater_ops.AddonUpdaterCheckNow.bl_idname,
                text="Check for Updates",
                icon="FILE_REFRESH"
            )

        # Last check label (compact text)
        last_check = updater.json.get("last_check") if updater.json else None
        if last_check:
            date_only = last_check.split(" ")[0].split("T")[0]
            box.label(text=f"Last check: {date_only}")
        else:
            box.label(text="Last check: Never")

        # Checkboxes (Standard Blender Checkboxes)
        settings = addon_updater_ops.get_user_preferences(context)
        if settings:
            box.prop(settings, "auto_check_update", text="Auto-check for Updates")
            box.prop(settings, "include_beta_updates", text="Include Beta Versions")


class CSW_PT_Unified_Character_Setup_Wizard_UI_Layout(Panel):
    bl_label = "Character Setup Wizard"
    bl_idname = 'CSW_PT_Unified_Character_Setup_Wizard_UI_Layout'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gacha Setup"

    bl_order = 1

    bpy.types.Scene.game_type_dropdown = EnumProperty(
        items=[
            (GameType.GENSHIN_IMPACT.name, 'Genshin Impact', 'Genshin Impact Setup'),
            (GameType.HONKAI_STAR_RAIL.name, 'Honkai Star Rail', 'Honkai Star Rail Setup'),
            (GameType.ZENLESS_ZONE_ZERO.name, 'Zenless Zone Zero', 'Zenless Zone Zero Setup'),
            (GameType.NEVERNESS_TO_EVERNESS.name, 'Neverness to Everness', 'Neverness to Everness Setup'),
            (GameType.WUTHERING_WAVES.name, 'Wuthering Waves', 'Wuthering Waves Setup'),
            (GameType.ARKNIGHTS_ENDFIELD.name, 'Arknights: Endfield', 'Arknights: Endfield Setup'),
        ],
        name='Game',
        description='Setup for the selected game',
        default=GameType.GENSHIN_IMPACT.name,
    )

    bpy.types.Scene.character_setup_wizard_logging_enabled = bpy.props.BoolProperty(
        name="(Debug) Enable Logging",
        description="Enables Logging to Addon Config Directory for Character Setup Wizard",
        default=False
    )

    def draw(self, context):
        layout = self.layout
        main_box = layout.box()
        main_box.prop(context.scene, 'game_type_dropdown')

        selected_game = getattr(context.scene, 'game_type_dropdown', GameType.GENSHIN_IMPACT.name)

        game_op_map = {
            GameType.GENSHIN_IMPACT.name: ('genshin.setup_wizard_ui', GameType.GENSHIN_IMPACT.name, 'EXEC_DEFAULT'),
            GameType.HONKAI_STAR_RAIL.name: ('honkai_star_rail.setup_wizard_ui', GameType.HONKAI_STAR_RAIL.name, 'EXEC_DEFAULT'),
            GameType.ZENLESS_ZONE_ZERO.name: ('zenless_zone_zero.setup_wizard_ui', GameType.ZENLESS_ZONE_ZERO.name, 'EXEC_DEFAULT'),
            GameType.NEVERNESS_TO_EVERNESS.name: ('neverness_to_everness.setup_wizard_ui', GameType.NEVERNESS_TO_EVERNESS.name, 'INVOKE_DEFAULT'),
            GameType.WUTHERING_WAVES.name: ('wuthering_waves.setup_wizard_ui', GameType.WUTHERING_WAVES.name, 'INVOKE_DEFAULT'),
            GameType.ARKNIGHTS_ENDFIELD.name: ('arknights_endfield.setup_wizard_ui', GameType.ARKNIGHTS_ENDFIELD.name, 'INVOKE_DEFAULT'),
        }

        info = game_op_map.get(selected_game)
        if not info:
            return

        op_name, gt_name, op_context = info

        run_entire_setup_column = main_box.column()

        from setup_wizard.ui.gi_ui_setup_wizard_menu import OperatorFactory
        OperatorFactory.create(
            run_entire_setup_column,
            op_name,
            'Run Entire Setup',
            'PLAY',
            operator_context=op_context,
            game_type=gt_name,
        )

        from setup_wizard.services.isolation import isolation_service
        isolation_service.draw_setup_status_box(main_box, context, run_entire_setup_column)

        settings_box = layout.box()
        settings_header = settings_box.row()
        settings_header.label(text="Setup Settings", icon="PREFERENCES")

        settings_col = settings_box.column()
        if selected_game == GameType.ZENLESS_ZONE_ZERO.name and hasattr(context.scene, "zzz_shader_type"):
            settings_col.prop(context.scene, "zzz_shader_type", text="Shader")

        props = getattr(context.scene, "character_rigger_props", None)
        if props:
            enable_physics = getattr(props, "enable_hair_clothes_physics", getattr(props, "enable_hair_dress_physics", False))
            settings_col.prop(props, "enable_hair_clothes_physics", text="Hair & Clothes Physics")
            if enable_physics:
                sliders_col = settings_col.column()
                sliders_col.prop(props, "hair_physics_influence", text="Hair", slider=True)
                sliders_col.prop(props, "clothes_physics_influence", text="Clothes", slider=True)
            settings_col.prop(props, "disable_rigging", text="Disable Rigging")
