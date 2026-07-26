import os

bl_info = {
    "name": "Gacha Blender Setup",
    "author": "Mken, OctavoPE, Enthralpy",
    "version": (3, 0, 0),
    "blender": (3, 3, 0),
    "location": "3D View > Sidebar > Genshin Impact / Honkai Star Rail / Zenless Zone Zero",
    "description": "An addon to streamline the character model setup process when using Festivity, Nya222's or JaredNyts' Shaders",
    "warning": "",
    "doc_url": "",
    "support": "COMMUNITY",
    "category": "HoYoverse",
    "license": "GPL-3.0-or-later",
    "tracker_url": "",
}

is_test_env = (
    os.environ.get("PYTEST_VERSION") is not None
)  # This environ variable gets set when pytest is run

if is_test_env:
    pytest_version = os.environ.get("PYTEST_VERSION")
    print(f"Pytest version: {pytest_version}")
else:
    import importlib
    import os

    import bpy

    import setup_wizard.cache_operator
    import setup_wizard.genshin_setup_wizard
    import setup_wizard.ui.gi_ui_setup_wizard_menu
    from setup_wizard.cache_operator import ClearCacheOperator
    from setup_wizard.character_rig_setup.character_rigger_operator import (
        GI_OT_RigCharacter,
        ZZZ_OT_FixBoneChains,
    )
    from setup_wizard.character_rig_setup.character_rigger_props import (
        CharacterRiggerPropertyGroup,
        CharacterRiggerPropertyManager,
    )
    from setup_wizard.genshin_compositing_node_setup import (
        GI_OT_PostProcessingCompositingSetup,
    )
    from setup_wizard.genshin_import_character_model import (
        GI_OT_SetUpCharacter,
        HSR_OT_SetUpCharacter,
        ZZZ_OT_SetUpCharacter,
    )
    from setup_wizard.genshin_import_materials import (
        GI_OT_SetUpMaterials,
        HSR_OT_SetUpMaterials,
        ZZZ_OT_SetUpMaterials,
        NTE_OT_SetUpMaterials,
        NTE_OT_SetUpOutlines,
        NTE_OT_SetUpHairSpecular,
    )

    from setup_wizard.genshin_import_outlines import (
        GI_OT_SetUpOutlines,
        HSR_OT_SetUpOutlines,
        ZZZ_OT_SetUpOutlines,
    )
    from setup_wizard.genshin_setup_wizard import (
        GI_OT_GenshinSetupWizardUI,
        HSR_OT_HonkaiStarRailSetupWizardUI,
        ZZZ_OT_SetupWizardUI,
        NTE_OT_SetupWizardUI,
        setup_dependencies,
    )
    from setup_wizard.genshin_setup_wizard import (
        register as register_genshin_setup_wizard,
    )
    from setup_wizard.misc_final_steps import (
        GI_OT_FinishSetup,
        HSR_OT_FinishSetup,
        ZZZ_OT_FinishSetup,
        NTE_OT_FinishSetup,
        NTE_OT_SetupCompositorNodes,
    )
    from setup_wizard.preferences import CharacterSetupWizardAddonPreferences
    from setup_wizard.ui.gi_ui_setup_wizard_menu import (
        GI_PT_Advanced_Setup_Wizard_UI_Layout,
        GI_PT_Basic_Setup_Wizard_UI_Layout,
        GI_PT_Setup_Wizard_UI_Layout,
        GI_PT_UI_Character_Model_Menu,
        GI_PT_UI_Character_Rig_Setup_Menu,
        GI_PT_UI_Finish_Setup_Menu,
        GI_PT_UI_Materials_Menu,
        GI_PT_UI_Outlines_Menu,
        GI_PT_UI_Post_Processing_Node_Editor_Setup_Menu,
        GI_PT_UI_Post_Processing_Setup_Menu,
        UI_Properties,
    )
    from setup_wizard.ui.hsr_ui_setup_wizard_menu import (
        HSR_PT_Advanced_Setup_Wizard_UI_Layout,
        HSR_PT_Basic_Setup_Wizard_UI_Layout,
        HSR_PT_Setup_Wizard_UI_Layout,
        HSR_PT_UI_Character_Model_Menu,
        HSR_PT_UI_Character_Rig_Setup_Menu,
        HSR_PT_UI_Finish_Setup_Menu,
        HSR_PT_UI_Materials_Menu,
        HSR_PT_UI_Outlines_Menu,
    )
    from setup_wizard.ui.nte_ui_setup_wizard_menu import (
        NTE_PT_Setup_Wizard_UI_Layout,
        NTE_PT_Basic_Setup_Wizard_UI_Layout,
        NTE_PT_Advanced_Setup_Wizard_UI_Layout,
        NTE_PT_UI_Character_Model_Menu,
        NTE_PT_UI_Materials_Menu,
        NTE_PT_UI_Outlines_Menu,
        NTE_PT_UI_Rig_Character_Menu,
        NTE_PT_UI_Finish_Setup_Menu,
    )

    from setup_wizard.ui.unified_ui_setup_wizard_menu import (
        CSW_PT_Unified_Character_Setup_Wizard_UI_Layout,
    )

    # HSR_PT_UI_Compositing_Panel_Post_Processing_UI_Layout
    from setup_wizard.ui.zzz_ui_setup_wizard_menu import (
        ZZZ_PT_Advanced_Setup_Wizard_UI_Layout,
        ZZZ_PT_Basic_Setup_Wizard_UI_Layout,
        ZZZ_PT_Setup_Wizard_UI_Layout,
        ZZZ_PT_UI_Character_Model_Menu,
        ZZZ_PT_UI_Character_Rig_Setup_Menu,
        ZZZ_PT_UI_Finish_Setup_Menu,
        ZZZ_PT_UI_Materials_Menu,
        ZZZ_PT_UI_Outlines_Menu,
    )

    register_genshin_setup_wizard()
    setup_dependencies()

    modules = [
        setup_wizard.ui.gi_ui_setup_wizard_menu,
        setup_wizard.ui.zzz_ui_setup_wizard_menu,
        setup_wizard.ui.nte_ui_setup_wizard_menu,
        setup_wizard.genshin_setup_wizard,
        setup_wizard.cache_operator,
    ]

    classes = [
        CharacterRiggerPropertyGroup,
        CharacterRiggerPropertyManager,
        CharacterSetupWizardAddonPreferences,
        CSW_PT_Unified_Character_Setup_Wizard_UI_Layout,
        GI_PT_Setup_Wizard_UI_Layout,
        GI_PT_Basic_Setup_Wizard_UI_Layout,
        GI_PT_Advanced_Setup_Wizard_UI_Layout,
        GI_PT_UI_Character_Model_Menu,
        GI_PT_UI_Materials_Menu,
        GI_PT_UI_Outlines_Menu,
        GI_PT_UI_Finish_Setup_Menu,
        GI_PT_UI_Character_Rig_Setup_Menu,
        GI_PT_UI_Post_Processing_Setup_Menu,
        GI_PT_UI_Post_Processing_Node_Editor_Setup_Menu,
        GI_OT_GenshinSetupWizardUI,
        GI_OT_SetUpCharacter,
        GI_OT_SetUpMaterials,
        GI_OT_SetUpOutlines,
        GI_OT_FinishSetup,
        GI_OT_RigCharacter,
        GI_OT_PostProcessingCompositingSetup,
        HSR_PT_Setup_Wizard_UI_Layout,
        HSR_PT_Basic_Setup_Wizard_UI_Layout,
        HSR_PT_Advanced_Setup_Wizard_UI_Layout,
        HSR_PT_UI_Character_Model_Menu,
        HSR_PT_UI_Materials_Menu,
        HSR_PT_UI_Outlines_Menu,
        HSR_PT_UI_Finish_Setup_Menu,
        HSR_PT_UI_Character_Rig_Setup_Menu,
        # HSR_PT_UI_Compositing_Panel_Post_Processing_UI_Layout,
        HSR_OT_HonkaiStarRailSetupWizardUI,
        HSR_OT_SetUpCharacter,
        HSR_OT_SetUpMaterials,
        HSR_OT_SetUpOutlines,
        HSR_OT_FinishSetup,
        ZZZ_PT_Setup_Wizard_UI_Layout,
        ZZZ_PT_Basic_Setup_Wizard_UI_Layout,
        ZZZ_PT_Advanced_Setup_Wizard_UI_Layout,
        ZZZ_PT_UI_Character_Model_Menu,
        ZZZ_PT_UI_Materials_Menu,
        ZZZ_PT_UI_Outlines_Menu,
        ZZZ_PT_UI_Character_Rig_Setup_Menu,
        ZZZ_PT_UI_Finish_Setup_Menu,
        ZZZ_OT_SetupWizardUI,
        ZZZ_OT_SetUpCharacter,
        ZZZ_OT_SetUpMaterials,
        ZZZ_OT_SetUpOutlines,
        ZZZ_OT_FinishSetup,
        ZZZ_OT_FixBoneChains,
        NTE_PT_Setup_Wizard_UI_Layout,
        NTE_PT_Basic_Setup_Wizard_UI_Layout,
        NTE_PT_Advanced_Setup_Wizard_UI_Layout,
        NTE_PT_UI_Character_Model_Menu,
        NTE_PT_UI_Materials_Menu,
        NTE_PT_UI_Outlines_Menu,
        NTE_PT_UI_Rig_Character_Menu,
        NTE_PT_UI_Finish_Setup_Menu,
        NTE_OT_SetupWizardUI,
        NTE_OT_SetUpMaterials,
        NTE_OT_SetUpOutlines,
        NTE_OT_SetUpHairSpecular,
        NTE_OT_SetupCompositorNodes,
        NTE_OT_FinishSetup,
        ClearCacheOperator,
    ]




    for module in modules:
        try:
            importlib.reload(module)
        except ModuleNotFoundError:
            pass  # likely new class

    register, unregister = bpy.utils.register_classes_factory(classes)
    UI_Properties.create_custom_ui_properties()

    """
    For auto_loading, but right now we're doing simple loading to have
    direct control for the order of class registration.
    """
    """
    # from setup_wizard import auto_load
    # auto_load.init()


    # def register():
    #     # auto_load.register()


    # def unregister():
    #     # auto_load.unregister()
    """
