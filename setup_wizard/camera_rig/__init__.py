"""Camera rig modules for Gacha Setup Addon."""
from setup_wizard.camera_rig.jideeh_cam_rig import (
    build as build_jideeh_camrig,
    CSW_OT_CreateCameraPro,
    CSW_OT_CreateJideehCamrig,
)

__all__ = ["build_jideeh_camrig", "CSW_OT_CreateCameraPro", "CSW_OT_CreateJideehCamrig"]
