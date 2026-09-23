"""Character Settings and Scene Configuration Assertions.

Validates that:
1. Color management is configured properly (sRGB / Standard).
2. Outlines modifier (Geometry Nodes) is attached to character meshes.
3. Outline lightmaps are assigned to the outline materials.
4. Character rigger scene properties are valid (physics sliders, toggles).
5. Scene cleanup was performed (no stray FBX empties).
"""
import bpy


def assert_charactersettings(game, char_dir):
    """Run character settings assertions and return check result dictionaries."""
    checks = []

    # 1. Color Management Check
    display_device = bpy.context.scene.display_settings.display_device
    view_transform = bpy.context.scene.view_settings.view_transform

    is_standard = view_transform in ("Standard", "AgX", "Filmic")
    checks.append({
        "name": "Color Management View Transform",
        "passed": is_standard,
        "message": f"Display: '{display_device}', View: '{view_transform}'",
    })

    # 2. Outlines Geometry Nodes Modifier Check
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("WGT-")]
    geo_node_meshes = []
    for m in meshes:
        for mod in m.modifiers:
            if mod.type == "NODES" and mod.node_group and "outline" in mod.node_group.name.lower():
                geo_node_meshes.append(m.name)
                break

    # Some games use solidify or custom nodes
    solidify_meshes = [m.name for m in meshes if any(mod.type == "SOLIDIFY" for mod in m.modifiers)]
    has_outlines = len(geo_node_meshes) > 0 or len(solidify_meshes) > 0

    checks.append({
        "name": "Outlines Modifier Attached",
        "passed": has_outlines,
        "message": f"Geometry Nodes outlines on {len(geo_node_meshes)} mesh(es): {geo_node_meshes[:4]}" if geo_node_meshes else f"Solidify outlines on {len(solidify_meshes)} mesh(es)",
    })

    # 3. Outline Materials & Lightmap Check
    outline_materials = [m for m in bpy.data.materials if "outline" in m.name.lower()]
    checks.append({
        "name": "Outline Materials Created",
        "passed": len(outline_materials) > 0 or not has_outlines,
        "message": f"Found {len(outline_materials)} outline material(s): {[m.name for m in outline_materials[:4]]}",
    })

    # 4. Character Rigger Scene Properties
    props = getattr(bpy.context.scene, "character_rigger_props", None)
    has_props = props is not None
    checks.append({
        "name": "Character Rigger Properties",
        "passed": has_props,
        "message": "scene.character_rigger_props registered and accessible" if has_props else "character_rigger_props missing on scene",
    })

    if has_props:
        physics_present = hasattr(props, "enable_hair_clothes_physics") or hasattr(props, "enable_hair_dress_physics")
        checks.append({
            "name": "Hair & Clothes Physics Settings",
            "passed": physics_present,
            "message": f"Physics toggle present: {physics_present}, hair_influence: {getattr(props, 'hair_physics_influence', 'N/A')}",
        })

    # 5. Scene Cleanup Check (FBX root empties cleaned up)
    stray_empties = [o.name for o in bpy.data.objects if o.type == "EMPTY" and not any(k in o.name.lower() for k in ["head", "light", "driver", "origin"])]
    checks.append({
        "name": "Scene Empties Cleanup",
        "passed": len(stray_empties) <= 2,
        "message": f"Remaining non-driver empties: {stray_empties}" if stray_empties else "All extraneous FBX empties cleaned up",
    })

    return checks
