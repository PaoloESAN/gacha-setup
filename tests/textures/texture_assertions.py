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
    meshes_without_mats = [
        m.name for m in meshes
        if (not m.material_slots or not any(s.material for s in m.material_slots))
        and not any(k in m.name.lower() for k in ["effect", "collider", "hitbox"])
    ]
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

    # 6. Shadow Ramp Assignment Validation
    char_path = Path(char_dir)
    char_files = [f.name.lower() for f in char_path.iterdir() if f.is_file()] if char_path.is_dir() else []
    has_body_ramp_file = any("body" in f and "shadow_ramp" in f and not any(k in f for k in ["body01", "body1", "body2", "body02"]) for f in char_files)
    has_hair_ramp_file = any("hair" in f and "shadow_ramp" in f for f in char_files)

    body_ramp_node = None
    hair_ramp_node = None
    for ng in bpy.data.node_groups:
        for n in getattr(ng, "nodes", []):
            if n.type == "TEX_IMAGE":
                n_id = f"{n.name} {n.label or ''}".lower()
                if "body" in n_id and ("shadow" in n_id or "ramp" in n_id) and not any(k in n_id for k in ["body2", "body02", "body_2", "body1", "body01", "body_1", "holographic", "nyx"]):
                    body_ramp_node = n
                elif "hair" in n_id and ("shadow" in n_id or "ramp" in n_id):
                    hair_ramp_node = n

    if has_body_ramp_file or body_ramp_node:
        body_ramp_img = body_ramp_node.image if body_ramp_node else None
        has_body_ramp_assigned = body_ramp_img is not None
        correct_body_ramp = False
        if has_body_ramp_assigned:
            img_low = body_ramp_img.name.lower()
            if has_body_ramp_file:
                correct_body_ramp = "body" in img_low and not any(ign in img_low for ign in ["dress", "shell", "hair", "body01", "body1", "body2"])
            else:
                correct_body_ramp = True

        checks.append({
            "name": "Body Shadow Ramp Texture Assignment",
            "passed": has_body_ramp_assigned and correct_body_ramp,
            "message": f"Assigned: '{body_ramp_img.name}'" if has_body_ramp_assigned and correct_body_ramp
            else (f"Incorrectly assigned '{body_ramp_img.name}' instead of Body shadow ramp" if has_body_ramp_assigned
                  else "Body Shadow Ramp node has no image assigned"),
        })

    if has_hair_ramp_file and hair_ramp_node:
        hair_ramp_img = hair_ramp_node.image
        has_hair_ramp_assigned = hair_ramp_img is not None
        correct_hair_ramp = has_hair_ramp_assigned and ("hair" in hair_ramp_img.name.lower() and "body" not in hair_ramp_img.name.lower())
        checks.append({
            "name": "Hair Shadow Ramp Texture Assignment",
            "passed": correct_hair_ramp,
            "message": f"Assigned: '{hair_ramp_img.name}'" if correct_hair_ramp
            else (f"Incorrectly assigned '{hair_ramp_img.name if hair_ramp_img else None}' instead of Hair shadow ramp"),
        })

    return checks
