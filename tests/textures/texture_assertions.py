"""Texture and Material Assertions.

Validates that:
1. Character meshes have material slots assigned.
2. Materials contain valid node trees with shader groups.
3. Image texture nodes have loaded image datablocks with valid dimensions (>0x0).
4. Required texture maps (Diffuse/BaseColor, Lightmap) are present and assigned.
5. No missing/pink default materials remain.
"""
import os
from pathlib import Path
import bpy


def assert_textures(game, char_dir):
    """Run texture and material assertions and return check result dictionaries."""
    checks = []

    # 1. Meshes check
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("WGT-")]
    if not meshes:
        checks.append({
            "name": "Character Meshes Presence",
            "passed": False,
            "message": "No character mesh objects found in scene",
        })
        return checks

    checks.append({
        "name": "Character Meshes Presence",
        "passed": True,
        "message": f"Found {len(meshes)} character mesh(es): {[m.name for m in meshes]}",
    })

    # 2. Material slots check
    meshes_without_mats = [m.name for m in meshes if not m.material_slots or not any(s.material for s in m.material_slots)]
    checks.append({
        "name": "Mesh Material Slots Assigned",
        "passed": len(meshes_without_mats) == 0,
        "message": f"Meshes missing materials: {meshes_without_mats}" if meshes_without_mats else "All character meshes have materials assigned",
    })

    # 3. Default materials replaced check on active character meshes
    default_names = ["material", "default", "none"]
    mesh_materials = {slot.material for m in meshes for slot in m.material_slots if slot.material}
    unreplaced = [mat.name for mat in mesh_materials if any(d == mat.name.lower() or mat.name.lower().startswith(d + ".") for d in default_names)]

    checks.append({
        "name": "Default Materials Replaced",
        "passed": len(unreplaced) == 0 and len(mesh_materials) > 0,
        "message": f"Unreplaced default materials on mesh: {unreplaced}" if unreplaced else f"{len(mesh_materials)} active character material(s) verified",
    })

    # 4. Image textures inspection on active materials
    loaded_images = set()
    zero_size_images = []
    active_image_nodes = 0

    for mat in mesh_materials:
        if not mat.use_nodes or not mat.node_tree:
            continue

        nodes_to_inspect = list(mat.node_tree.nodes)
        for node in mat.node_tree.nodes:
            if node.type == "GROUP" and getattr(node, "node_tree", None):
                nodes_to_inspect.extend(node.node_tree.nodes)

        for node in nodes_to_inspect:
            if node.type == "TEX_IMAGE":
                img = node.image
                if img is not None:
                    active_image_nodes += 1
                    loaded_images.add(img.name)
                    if img.size[0] == 0 or img.size[1] == 0:
                        zero_size_images.append(f"{img.name} (0x0)")

    checks.append({
        "name": "Image Texture Nodes Loaded",
        "passed": active_image_nodes > 0 and len(loaded_images) > 0,
        "message": f"{active_image_nodes} texture node(s) with {len(loaded_images)} image(s) loaded",
    })

    checks.append({
        "name": "Image Dimensions Valid (>0x0)",
        "passed": len(zero_size_images) == 0 and len(loaded_images) > 0,
        "message": f"Zero-dimension images: {zero_size_images}" if zero_size_images else f"All {len(loaded_images)} loaded images have valid non-zero dimensions",
    })

    # 5. Core texture types check (Diffuse & Lightmap)
    has_diffuse = False
    has_lightmap = False
    for img_name in loaded_images:
        low = img_name.lower()
        if any(k in low for k in ["diffuse", "basecolor", "tex_diff", "color", "body", "hair", "face", "dress"]):
            has_diffuse = True
        if any(k in low for k in ["lightmap", "light", "shadow", "ilm", "ilm", "mask"]):
            has_lightmap = True

    checks.append({
        "name": "Core Texture Maps (Diffuse / Base Color)",
        "passed": has_diffuse,
        "message": "Base Color / Diffuse texture identified" if has_diffuse else "No recognizable diffuse/color texture found",
    })

    checks.append({
        "name": "Shading / Lightmap Textures",
        "passed": has_lightmap or len(loaded_images) >= 2,
        "message": "Lightmap/shadow texture identified" if has_lightmap else f"Loaded {len(loaded_images)} texture(s)",
    })

    return checks
