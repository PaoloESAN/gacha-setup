import os

_preview_collections = {}


def get_addon_icon_id(icon_name="addon_icon.png"):
    pcoll = _preview_collections.get("main")
    if pcoll and icon_name in pcoll:
        return pcoll[icon_name].icon_id
    return 0


def register_icons():
    global _preview_collections
    try:
        import bpy
        import bpy.utils.previews

        if "main" not in _preview_collections:
            pcoll = bpy.utils.previews.new()
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
            icon_path = os.path.join(assets_dir, icon_name := "addon_icon.png")
            if os.path.exists(icon_path):
                try:
                    pcoll.load(icon_name, icon_path, 'IMAGE')
                except Exception as e:
                    print(f"[GACHA SETUP] Notice loading addon icon: {e}")
            _preview_collections["main"] = pcoll
    except Exception as e:
        print(f"[GACHA SETUP] Notice initializing previews: {e}")


def unregister_icons():
    global _preview_collections
    try:
        import bpy
        import bpy.utils.previews

        for pcoll in _preview_collections.values():
            try:
                bpy.utils.previews.remove(pcoll)
            except Exception:
                pass
        _preview_collections.clear()
    except Exception:
        pass
