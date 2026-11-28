"""Wuthering Waves: Denia (Daniya / R2T1DaniyaMd10011) custom character setup profile.

Reproduces all manual adjustments from ``Denia No Geonode.blend`` automatically
when setting up Denia in Wuthering Waves, and adds multi-``.uemodel`` variant
importing with a Geometry Nodes variant switcher modifier:

1. Imports all ``.uemodel`` files in Denia's folder (``R2T1DaniyaMd10011``,
   ``_Body``, ``_Up1``, ``_Up2``) and binds secondary meshes to the primary skeleton.
2. Material adjustments:
   - ``Bangs1`` / ``Bangs2``: ``Hair Shader`` -> ``Highlights Intensity = 0.33``.
   - ``Cloth``: unmute ``Alpha Transparency`` (``Group.001``), ``Texture Converter``
     ``RGID Threshold = 0.5``.
   - ``Eye1`` / ``Eye2``: force ``Eye HET`` image to ``T_R2T1DaniyaMd10011Eye_HET.png``.
   - ``Fur``: ``surface_render_method = 'DITHERED'``, ``Texture Converter``
     ``RGID Threshold = 0.5``, link ``UV Map (UV2) -> Image Texture (T_Fur02_M.png,
     Non-Color) -> Alpha Transparency (Group.001).FTM``.
   - ``Outlines Fur``: ``surface_render_method = 'BLENDED'``,
     ``use_transparency_overlap = False``.
   - ``Hair01`` / ``Hair02``: glitter/sparkle Voronoi + FX overlay node chain
     using ``T_R2T1DaniyaMd10011Hair01_FX.png`` / ``Hair02_FX.png``.
3. Headband separation:
   - Separates the two head-weighted headband mesh islands (104 polygons) from
     ``Up01`` (and ``Up02``) into a dedicated ``Headband`` (``Headband 2``)
     material slot with ``Alpha Transparency`` unmuted.
4. Geometry Nodes Variant Switcher (``Denia Variant Switch``):
   - Placed on the primary mesh right after ``Armature`` and before
     ``Light Vectors`` / ``WW - Outlines``, switching between:
       0 = Default (``R2T1DaniyaMd10011``)
       1 = Alt Form (``_Body`` + ``_Up2``)
       2 = Body + Up1 (``_Body`` + ``_Up1``)
   - Exposed in the WuWa Character Settings N-panel via ``draw_ui``.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import bpy

from setup_wizard.character_custom_setups.registry import (
    CharacterSetupContext,
    CharacterSetupProfile,
    register_profile,
)
from setup_wizard.domain.game_types import GameType


DENIA_PROFILE_ID = "wuwa_denia"
DENIA_VARIANT_MOD_NAME = "Denia Variant Switch"
DENIA_VARIANT_GROUP_NAME = "Denia Variant Switch"


def _find_image_in_dir(char_dir: str, target_filename: str, colorspace: str = "Non-Color"):
    """Loads or reuses ``target_filename`` from ``char_dir`` (recursive)."""
    if not target_filename:
        return None
    target_low = target_filename.lower()

    # Reuse already-loaded image if exact match exists
    for img in bpy.data.images:
        name_clean = img.name.lower()
        base_clean = os.path.basename(getattr(img, "filepath", "") or "").lower()
        if name_clean == target_low or base_clean == target_low:
            try:
                img.colorspace_settings.name = colorspace
            except Exception:
                pass
            return img

    if not char_dir or not os.path.isdir(char_dir):
        return None

    found_path = None
    direct = os.path.join(char_dir, target_filename)
    if os.path.isfile(direct):
        found_path = direct
    else:
        for root, _, files in os.walk(char_dir):
            if "__MACOSX" in root:
                continue
            for fname in files:
                if fname.lower() == target_low:
                    found_path = os.path.join(root, fname)
                    break
            if found_path:
                break

    if not found_path:
        return None

    try:
        img = bpy.data.images.load(found_path, check_existing=True)
        try:
            img.colorspace_settings.name = colorspace
        except Exception:
            pass
        return img
    except Exception as exc:
        print(f"[DENIA] Could not load image {found_path}: {exc}")
        return None


def _find_group_node(node_tree, name_substrings: Tuple[str, ...]):
    if not node_tree:
        return None
    for node in node_tree.nodes:
        if node.type == 'GROUP':
            ng_name = node.node_tree.name.lower() if node.node_tree else ""
            n_name = node.name.lower()
            if any(sub in ng_name or sub in n_name for sub in name_substrings):
                return node
    return None


def _is_denia_material(mat) -> bool:
    if not mat or not getattr(mat, "node_tree", None):
        return False
    combined = " ".join([
        mat.name.lower(),
        str(mat.get("ww_original_name", "")).lower(),
    ])
    return any(k in combined for k in ("daniya", "denia", "r2t1daniyamd10011"))


def _apply_bangs_tweaks(mat) -> None:
    hair_shader = _find_group_node(mat.node_tree, ("ww - hair", "hair shader"))
    if hair_shader:
        sock = hair_shader.inputs.get("Highlights Intensity")
        if sock is not None:
            sock.default_value = 0.33


def _apply_cloth_tweaks(mat) -> None:
    alpha_node = _find_group_node(mat.node_tree, ("alpha transparency",))
    if alpha_node:
        alpha_node.mute = False
    tex_conv = _find_group_node(mat.node_tree, ("texture converter",))
    if tex_conv:
        sock = tex_conv.inputs.get("RGID Threshold")
        if sock is not None:
            sock.default_value = 0.5
    if mat.node_tree:
        mat.node_tree.update_tag()


def _apply_eye_tweaks(mat, char_dir: str) -> None:
    eye_het_img = _find_image_in_dir(char_dir, "T_R2T1DaniyaMd10011Eye_HET.png", colorspace="Non-Color")
    if not eye_het_img:
        return
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and (
            node.name.lower() == "eye het"
            or (node.label and node.label.lower() == "eye het")
            or (node.image and "eye_het" in node.image.name.lower())
        ):
            node.image = eye_het_img


def _apply_fur_tweaks(mat, char_dir: str) -> None:
    # Alpha-masked fur cards must not receive solid extruded outline shells,
    # and must keep DITHERED (Alpha Hashed) so overlapping fur cards sort cleanly.
    mat["ww_no_outline"] = True
    mat["ww_keep_dithered"] = True

    if hasattr(mat, "surface_render_method"):
        try:
            mat.surface_render_method = 'DITHERED'
        except Exception:
            pass

    tex_conv = _find_group_node(mat.node_tree, ("texture converter",))
    if tex_conv:
        sock = tex_conv.inputs.get("RGID Threshold")
        if sock is not None:
            sock.default_value = 0.5

    alpha_node = _find_group_node(mat.node_tree, ("alpha transparency",))
    if not alpha_node:
        return

    nt = mat.node_tree
    fur_img = _find_image_in_dir(char_dir, "T_Fur02_M.png", colorspace="Non-Color")
    if fur_img is not None:
        try:
            fur_img.alpha_mode = 'STRAIGHT'
        except Exception:
            pass

    uv_node = nt.nodes.get("Denia Fur UV2")
    if uv_node is None:
        uv_node = nt.nodes.new("ShaderNodeUVMap")
        uv_node.name = "Denia Fur UV2"
        uv_node.location = (1213.0, 330.0)
    uv_node.uv_map = "UV2"

    tex_node = nt.nodes.get("Denia Fur Mask")
    if tex_node is None:
        tex_node = nt.nodes.new("ShaderNodeTexImage")
        tex_node.name = "Denia Fur Mask"
        tex_node.location = (1468.0, 440.0)
    if fur_img:
        tex_node.image = fur_img

    # Wire UV2 -> T_Fur02_M -> Alpha Transparency.FTM
    nt.links.new(uv_node.outputs["UV"], tex_node.inputs["Vector"])
    ftm_in = alpha_node.inputs.get("FTM")
    if ftm_in is not None:
        for link in list(ftm_in.links):
            nt.links.remove(link)
        nt.links.new(tex_node.outputs["Color"], ftm_in)


def _apply_hair_sparkle_tweaks(mat, char_dir: str) -> None:
    """Adds Denia's Voronoi + Hair FX sparkle overlay chain between Hair Shader and Output."""
    nt = mat.node_tree
    if not nt:
        return
    if nt.nodes.get("Denia Hair FX Overlay"):
        return  # Already applied

    hair_shader = _find_group_node(nt, ("ww - hair", "hair shader"))
    mat_output = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not hair_shader or not mat_output:
        return

    # Pick Hair01_FX or Hair02_FX depending on material version
    low = (mat.name + " " + str(mat.get("ww_original_name", ""))).lower()
    fx_filename = (
        "T_R2T1DaniyaMd10011Hair02_FX.png"
        if ("hair02" in low or "hair2" in low)
        else "T_R2T1DaniyaMd10011Hair01_FX.png"
    )
    fx_img = _find_image_in_dir(char_dir, fx_filename, colorspace="sRGB")
    if not fx_img:
        fx_img = _find_image_in_dir(char_dir, "T_R2T1DaniyaMd10011Hair01_FX.png", colorspace="sRGB")

    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    tex_coord.name = "Denia Hair FX TexCoord"
    tex_coord.location = (1491.0, 671.0)

    vec_scale = nt.nodes.new("ShaderNodeVectorMath")
    vec_scale.name = "Denia Hair FX Scale"
    vec_scale.operation = 'SCALE'
    vec_scale.inputs["Scale"].default_value = 14.0
    vec_scale.location = (1851.0, 552.0)

    math_w = nt.nodes.new("ShaderNodeMath")
    math_w.name = "Denia Hair FX W"
    math_w.operation = 'DIVIDE'
    math_w.inputs[0].default_value = 6.3
    math_w.inputs[1].default_value = 3.6
    math_w.location = (1868.0, 415.0)

    voronoi = nt.nodes.new("ShaderNodeTexVoronoi")
    voronoi.name = "Denia Hair FX Voronoi"
    voronoi.voronoi_dimensions = '4D'
    voronoi.feature = 'F1'
    voronoi.distance = 'EUCLIDEAN'
    voronoi.normalize = False
    voronoi.inputs["Scale"].default_value = 28.5
    voronoi.inputs["Detail"].default_value = 0.06
    voronoi.inputs["Roughness"].default_value = 0.60857
    voronoi.inputs["Lacunarity"].default_value = 2.0
    voronoi.inputs["Randomness"].default_value = 1.0
    voronoi.location = (2031.0, 711.0)

    ramp_dist = nt.nodes.new("ShaderNodeValToRGB")
    ramp_dist.name = "Denia Hair FX Dist Ramp"
    ramp_dist.color_ramp.color_mode = 'RGB'
    ramp_dist.color_ramp.interpolation = 'LINEAR'
    ramp_dist.color_ramp.elements[0].position = 0.00909
    ramp_dist.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    ramp_dist.color_ramp.elements[1].position = 0.18636
    ramp_dist.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
    ramp_dist.location = (2208.0, 682.0)

    fx_tex = nt.nodes.new("ShaderNodeTexImage")
    fx_tex.name = "Denia Hair FX Texture"
    if fx_img:
        fx_tex.image = fx_img
    fx_tex.location = (2222.0, 445.0)

    ramp_color = nt.nodes.new("ShaderNodeValToRGB")
    ramp_color.name = "Denia Hair FX Color Ramp"
    ramp_color.color_ramp.color_mode = 'RGB'
    ramp_color.color_ramp.interpolation = 'LINEAR'
    ramp_color.color_ramp.elements[0].position = 0.48636
    ramp_color.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    ramp_color.color_ramp.elements[1].position = 0.81364
    ramp_color.color_ramp.elements[1].color = (0.08293, 0.14801, 1.0, 1.0)
    mid_elem = ramp_color.color_ramp.elements.new(0.61591)
    mid_elem.color = (0.99788, 0.25758, 1.0, 1.0)
    ramp_color.location = (2422.0, 396.0)

    math_mul = nt.nodes.new("ShaderNodeMath")
    math_mul.name = "Denia Hair FX Mask"
    math_mul.operation = 'MULTIPLY'
    math_mul.location = (2557.0, 638.0)

    mix_add = nt.nodes.new("ShaderNodeMix")
    mix_add.name = "Denia Hair FX Add"
    mix_add.data_type = 'RGBA'
    mix_add.blend_type = 'ADD'
    mix_add.clamp_factor = True
    mix_add.clamp_result = False
    mix_add.inputs[6].default_value = (0.5, 0.5, 0.5, 1.0)
    mix_add.location = (2779.0, 602.0)

    shader_to_rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    shader_to_rgb.name = "Denia Hair FX ShaderToRGB"
    shader_to_rgb.location = (1997.0, -53.0)

    mix_overlay = nt.nodes.new("ShaderNodeMix")
    mix_overlay.name = "Denia Hair FX Overlay"
    mix_overlay.data_type = 'RGBA'
    mix_overlay.blend_type = 'OVERLAY'
    mix_overlay.clamp_factor = True
    mix_overlay.clamp_result = False
    mix_overlay.inputs[0].default_value = 1.0
    mix_overlay.location = (2940.0, 188.0)

    # Wire everything up
    nt.links.new(tex_coord.outputs["UV"], vec_scale.inputs[0])
    nt.links.new(vec_scale.outputs["Vector"], voronoi.inputs["Vector"])
    nt.links.new(math_w.outputs["Value"], voronoi.inputs["W"])
    nt.links.new(voronoi.outputs["Distance"], ramp_dist.inputs["Fac"])
    nt.links.new(voronoi.outputs["Color"], ramp_color.inputs["Fac"])
    nt.links.new(ramp_dist.outputs["Color"], math_mul.inputs[0])
    nt.links.new(fx_tex.outputs["Alpha"], math_mul.inputs[1])
    nt.links.new(math_mul.outputs["Value"], mix_add.inputs[0])
    nt.links.new(ramp_color.outputs["Color"], mix_add.inputs[7])
    nt.links.new(hair_shader.outputs["BSDF"], shader_to_rgb.inputs["Shader"])
    nt.links.new(mix_add.outputs[2], mix_overlay.inputs[6])
    nt.links.new(shader_to_rgb.outputs["Color"], mix_overlay.inputs[7])

    # Replace Hair Shader -> Material Output.Surface with Mix Overlay -> Surface
    surface_in = mat_output.inputs.get("Surface")
    if surface_in is not None:
        for link in list(surface_in.links):
            nt.links.remove(link)
        nt.links.new(mix_overlay.outputs[2], surface_in)


def _separate_headband_on_mesh(mesh) -> bool:
    """Separates Denia's headband polygons from Up01/Up02 into a dedicated Headband material slot."""
    if not mesh or mesh.type != 'MESH' or not mesh.data or not mesh.data.polygons:
        return False

    # Already separated?
    if any(s.material and "headband" in s.material.name.lower() for s in mesh.material_slots):
        return False

    # Locate head vertex group (works both pre-rig and post-rig)
    head_vg_idx = None
    for vg in mesh.vertex_groups:
        if vg.name.lower() in ("bip001head", "org-head", "def-head", "head"):
            head_vg_idx = vg.index
            break
    if head_vg_idx is None:
        return False

    uv_layer = mesh.data.uv_layers.active.data if mesh.data.uv_layers else None
    if uv_layer is None:
        return False

    separated_any = False
    for slot_idx, slot in enumerate(list(mesh.material_slots)):
        src_mat = slot.material
        if not src_mat:
            continue
        mat_low = (src_mat.name + " " + str(src_mat.get("ww_original_name", ""))).lower()
        if "up01" not in mat_low and "up02" not in mat_low:
            continue

        # Collect head-weighted polygons in this Up01/Up02 slot
        head_polys = []
        for poly in mesh.data.polygons:
            if poly.material_index != slot_idx:
                continue
            if all(
                any(g.group == head_vg_idx and g.weight > 0.5 for g in mesh.data.vertices[vi].groups)
                for vi in poly.vertices
            ):
                head_polys.append(poly)

        if not head_polys:
            continue

        # Split head_polys into connected mesh islands
        v2p: Dict[int, List[int]] = {}
        pmap = {p.index: p for p in head_polys}
        for p in head_polys:
            for vi in p.vertices:
                v2p.setdefault(vi, []).append(p.index)

        seen = set()
        headband_poly_indices: List[int] = []
        for p in head_polys:
            if p.index in seen:
                continue
            stack = [p.index]
            comp_p = []
            comp_v = set()
            while stack:
                cur = stack.pop()
                if cur in seen:
                    continue
                seen.add(cur)
                cp = pmap[cur]
                comp_p.append(cp)
                for vi in cp.vertices:
                    comp_v.add(vi)
                    for nb in v2p[vi]:
                        if nb not in seen:
                            stack.append(nb)

            zs = [mesh.data.vertices[vi].co.z for vi in comp_v]
            vs = [uv_layer[li].uv.y for cp in comp_p for li in cp.loop_indices]
            # Headband islands sit at z >= 1.28 and UV v in [0.45, 0.65]
            # (cleanly excluding earrings at z <= 1.25 and v <= 0.25)
            if min(zs) >= 1.28 and min(vs) >= 0.45 and max(vs) <= 0.65:
                headband_poly_indices.extend(cp.index for cp in comp_p)

        if not headband_poly_indices:
            continue

        hb_mat_name = "Headband 2" if "up02" in mat_low else "Headband"
        hb_mat = bpy.data.materials.get(hb_mat_name)
        if hb_mat is None:
            hb_mat = src_mat.copy()
            hb_mat.name = hb_mat_name
            hb_mat.use_fake_user = True
            hb_mat["ww_base_part"] = "Headband"
            hb_mat["ww_no_outline"] = True

        # Unmute Alpha Transparency on Headband material
        alpha_node = _find_group_node(hb_mat.node_tree, ("alpha transparency",))
        if alpha_node:
            alpha_node.mute = False

        mesh.data.materials.append(hb_mat)
        new_slot_idx = len(mesh.material_slots) - 1
        for p_idx in headband_poly_indices:
            mesh.data.polygons[p_idx].material_index = new_slot_idx

        print(f"[DENIA] Separated {len(headband_poly_indices)} headband polys on {mesh.name} -> {hb_mat.name}")
        separated_any = True

    return separated_any


def _on_after_materials(ctx: CharacterSetupContext) -> None:
    """Applies all Denia material adjustments from Denia No Geonode.blend."""
    char_dir = ctx.char_dir

    for mat in list(bpy.data.materials):
        if not _is_denia_material(mat):
            continue
        low = (mat.name + " " + str(mat.get("ww_original_name", ""))).lower()
        if "outline" in low:
            continue

        if "bang" in low:
            _apply_bangs_tweaks(mat)
        elif "cloth" in low:
            _apply_cloth_tweaks(mat)
        elif "eye" in low and not any(k in low for k in ("eyebrow", "eyelash")):
            _apply_eye_tweaks(mat, char_dir)
        elif "fur" in low:
            _apply_fur_tweaks(mat, char_dir)
        elif "hair" in low:
            _apply_hair_sparkle_tweaks(mat, char_dir)

    # Give Variant 0 (primary) a dedicated Cloth material copy (matching Denia No Geonode.blend's
    # single-user WW - Cloth Daniya) so it is not shared with Variant 1's _Up2 mesh.
    classified = _classify_denia_meshes(ctx.meshes)
    primary = classified.get("primary")
    up2 = classified.get("up2")
    if primary and up2:
        for slot in up2.material_slots:
            if slot.material and "cloth" in slot.material.name.lower() and _is_denia_material(slot.material):
                cloth_v2_name = f"{slot.material.name} Alt"
                cloth_v2 = bpy.data.materials.get(cloth_v2_name)
                if cloth_v2 is None:
                    cloth_v2 = slot.material.copy()
                    cloth_v2.name = cloth_v2_name
                    cloth_v2.use_fake_user = True
                slot.material = cloth_v2

    # Separate headband on primary (Up01) and variant body (Up02) meshes
    for mesh in ctx.meshes:
        if any(k in mesh.name.lower() for k in ("daniya", "denia", "r2t1daniyamd10011")):
            _separate_headband_on_mesh(mesh)


def _exclude_materials_from_outline_modifier(mesh, excluded_materials: List[object]) -> None:
    """Clones the mesh's WW - Outlines node group and deletes ``excluded_materials``
    faces from the extruded outline branch (before Flip Faces) so alpha-masked
    materials like Fur and Headband get zero outline shells or inflated duplicates."""
    if not mesh or not excluded_materials:
        return
    ol_mod = next(
        (m for m in mesh.modifiers if m.type == 'NODES' and m.node_group and "outlines" in m.name.lower()),
        None,
    )
    if ol_mod is None:
        return

    src_ng = ol_mod.node_group
    target_ng_name = f"WW - Outlines Denia ({mesh.name})"
    if src_ng.name != target_ng_name:
        existing = bpy.data.node_groups.get(target_ng_name)
        if existing is not None:
            bpy.data.node_groups.remove(existing)
        ng = src_ng.copy()
        ng.name = target_ng_name
        ol_mod.node_group = ng
    else:
        ng = src_ng

    if ng.nodes.get("Denia Exclude Outline Faces"):
        return  # Already patched

    flip_node = next((n for n in ng.nodes if n.type == 'FLIP_FACES'), None)
    if flip_node is None or not flip_node.inputs["Mesh"].is_linked:
        return

    in_link = flip_node.inputs["Mesh"].links[0]
    from_socket = in_link.from_socket
    ng.links.remove(in_link)

    del_node = ng.nodes.new("GeometryNodeDeleteGeometry")
    del_node.name = "Denia Exclude Outline Faces"
    del_node.domain = 'FACE'
    del_node.mode = 'ALL'
    del_node.location = (flip_node.location.x - 220.0, flip_node.location.y)

    # Build OR-combined Material Selection for all excluded materials
    sel_sockets = []
    for idx, mat in enumerate(excluded_materials):
        ms = ng.nodes.new("GeometryNodeMaterialSelection")
        ms.name = f"Denia Exclude Mat {idx}"
        ms.inputs["Material"].default_value = mat
        ms.location = (flip_node.location.x - 460.0, flip_node.location.y - 140.0 * (idx + 1))
        sel_sockets.append(ms.outputs["Selection"])

    combined_sel = sel_sockets[0]
    for idx, sock in enumerate(sel_sockets[1:], start=1):
        bm = ng.nodes.new("FunctionNodeBooleanMath")
        bm.name = f"Denia Exclude OR {idx}"
        bm.operation = 'OR'
        bm.location = (flip_node.location.x - 260.0, flip_node.location.y - 140.0 * (idx + 1))
        ng.links.new(combined_sel, bm.inputs[0])
        ng.links.new(sock, bm.inputs[1])
        combined_sel = bm.outputs["Boolean"]

    ng.links.new(from_socket, del_node.inputs["Geometry"])
    ng.links.new(combined_sel, del_node.inputs["Selection"])
    ng.links.new(del_node.outputs["Geometry"], flip_node.inputs["Mesh"])
    print(f"[DENIA] Excluded {[m.name for m in excluded_materials]} from outline shell on {mesh.name}")


def _on_after_outlines(ctx: CharacterSetupContext) -> None:
    """Applies Fur outline render method tweaks and removes Fur/Headband from the outline shell."""
    for mat in bpy.data.materials:
        low = mat.name.lower()
        if "outline" in low and "fur" in low and any(k in low for k in ("daniya", "denia")):
            if hasattr(mat, "surface_render_method"):
                try:
                    mat.surface_render_method = 'BLENDED'
                except Exception:
                    pass
            if hasattr(mat, "use_transparency_overlap"):
                try:
                    mat.use_transparency_overlap = False
                except Exception:
                    pass

    # Exclude Fur and Headband faces from the extruded outline geometry on Denia's meshes
    for mesh in ctx.meshes:
        if not any(k in mesh.name.lower() for k in ("daniya", "denia", "r2t1daniyamd10011")):
            continue
        excluded = [
            s.material for s in mesh.material_slots
            if s.material and (
                s.material.get("ww_no_outline")
                or "fur" in s.material.name.lower()
                or "headband" in s.material.name.lower()
            )
        ]
        # Deduplicate while preserving order
        seen_ids = set()
        unique_excluded = []
        for m in excluded:
            if m.as_pointer() not in seen_ids:
                seen_ids.add(m.as_pointer())
                unique_excluded.append(m)
        if unique_excluded:
            _exclude_materials_from_outline_modifier(mesh, unique_excluded)


def _classify_denia_meshes(meshes: List[object]) -> Dict[str, Optional[object]]:
    """Classifies Denia's imported meshes into primary, body, up1, up2."""
    classified: Dict[str, Optional[object]] = {
        "primary": None,
        "body": None,
        "up1": None,
        "up2": None,
    }
    for m in meshes:
        if not m or m.type != 'MESH':
            continue
        low = m.name.lower()
        if not any(k in low for k in ("daniya", "denia", "r2t1daniyamd10011")):
            continue
        if "_seethru" in low or "wgt" in low:
            continue
        if "_body" in low:
            classified["body"] = m
        elif "_up2" in low:
            classified["up2"] = m
        elif "_up1" in low:
            classified["up1"] = m
        else:
            # Prefer the largest non-variant mesh as primary
            cur = classified["primary"]
            if cur is None or len(m.data.polygons) > len(cur.data.polygons):
                classified["primary"] = m
    return classified


def _build_variant_switcher_node_group(
    target_variant: int,
    group_name: str,
):
    """Creates a lightweight per-mesh Geometry Nodes visibility switch with only
    a single ``Variant`` input (0 = Default, 1 = Alt Form).

    When ``Variant == target_variant``, passes ``Geometry`` through untouched
    (preserving native custom split normals, tangents, UV maps, Light Vectors,
    and per-variant Outlines). Otherwise outputs empty geometry.
    """
    ng = bpy.data.node_groups.get(group_name)
    if ng is not None:
        bpy.data.node_groups.remove(ng)

    ng = bpy.data.node_groups.new(name=group_name, type='GeometryNodeTree')

    ng.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    var_sock = ng.interface.new_socket(name="Variant", in_out='INPUT', socket_type='NodeSocketInt')
    var_sock.default_value = 0
    var_sock.min_value = 0
    var_sock.max_value = 1
    var_sock.description = "0: Default, 1: Alt Form (Body + Up2)"

    ng.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    nodes = ng.nodes
    links = ng.links

    n_in = nodes.new("NodeGroupInput")
    n_in.location = (-400.0, 0.0)

    n_cmp = nodes.new("FunctionNodeCompare")
    n_cmp.data_type = 'INT'
    n_cmp.operation = 'EQUAL'
    n_cmp.location = (-120.0, 120.0)

    n_sw = nodes.new("GeometryNodeSwitch")
    n_sw.input_type = 'GEOMETRY'
    n_sw.location = (140.0, 0.0)

    n_out = nodes.new("NodeGroupOutput")
    n_out.location = (380.0, 0.0)

    int_inputs = [s for s in n_cmp.inputs if s.type == 'INT']
    links.new(n_in.outputs["Variant"], int_inputs[0])
    int_inputs[1].default_value = int(target_variant)
    links.new(n_cmp.outputs["Result"], n_sw.inputs["Switch"])
    links.new(n_in.outputs["Geometry"], n_sw.inputs["True"])
    links.new(n_sw.outputs["Output"], n_out.inputs["Geometry"])
    return ng


def _get_gn_socket_identifier(mod, socket_name: str) -> Optional[str]:
    if not mod or mod.type != 'NODES' or not mod.node_group:
        return None
    for item in mod.node_group.interface.items_tree:
        if getattr(item, "item_type", "") == 'SOCKET' and getattr(item, "in_out", "") == 'INPUT':
            if item.name == socket_name:
                return item.identifier
    return None


def _get_variant_socket_identifier(mod) -> Optional[str]:
    return _get_gn_socket_identifier(mod, "Variant")


def _set_gn_int_input(mod, ident: str, value: int) -> None:
    props_inputs = getattr(getattr(mod, "properties", None), "inputs", None)
    sock = getattr(props_inputs, ident, None) if props_inputs is not None else None
    if sock is not None and hasattr(sock, "value"):
        sock.value = int(value)
    else:
        mod[ident] = int(value)


def _add_variant_driver(dst_obj, dst_mod, src_obj, src_mod, var_ident: str) -> None:
    """Drives ``dst_mod``'s Variant input from ``src_mod``'s Variant input."""
    props_inputs = getattr(getattr(dst_mod, "properties", None), "inputs", None)
    use_new_api = props_inputs is not None and hasattr(getattr(props_inputs, var_ident, None), "value")

    if use_new_api:
        dst_path = f'modifiers["{dst_mod.name}"].properties.inputs.{var_ident}.value'
        src_path = f'modifiers["{src_mod.name}"].properties.inputs.{var_ident}.value'
    else:
        dst_path = f'modifiers["{dst_mod.name}"]["{var_ident}"]'
        src_path = f'modifiers["{src_mod.name}"]["{var_ident}"]'

    try:
        dst_obj.driver_remove(dst_path)
    except Exception:
        pass

    fcurve = dst_obj.driver_add(dst_path)
    drv = fcurve.driver
    drv.type = 'AVERAGE'
    var = drv.variables.new()
    var.name = "variant"
    var.type = 'SINGLE_PROP'
    tgt = var.targets[0]
    tgt.id_type = 'OBJECT'
    tgt.id = src_obj
    tgt.data_path = src_path


def _on_finish_setup(ctx: CharacterSetupContext) -> None:
    """Sets up per-mesh Geometry Nodes Variant Switchers (0=Default, 1=Alt Form)
    so each variant keeps its own native normals, tangents, Light Vectors, and Outlines."""
    _on_after_outlines(ctx)

    classified = _classify_denia_meshes(ctx.meshes)
    primary = classified["primary"]
    body = classified["body"]
    up2 = classified["up2"]

    if not primary or (not body and not up2):
        return

    rig = ctx.armature or primary.parent or primary.find_armature()
    alt_meshes = [m for m in (body, up2) if m is not None]

    ng_default = _build_variant_switcher_node_group(0, f"{DENIA_VARIANT_GROUP_NAME} (Default)")
    ng_alt = _build_variant_switcher_node_group(1, f"{DENIA_VARIANT_GROUP_NAME} (Alt)")

    # Primary mesh (Variant 0 = Default)
    p_mod = primary.modifiers.get(DENIA_VARIANT_MOD_NAME)
    if p_mod is None:
        p_mod = primary.modifiers.new(name=DENIA_VARIANT_MOD_NAME, type='NODES')
    p_mod.node_group = ng_default

    var_ident = _get_gn_socket_identifier(p_mod, "Variant")
    if var_ident:
        _set_gn_int_input(p_mod, var_ident, 0)

    # Keep modifier at the end of the stack so switching off outputs empty geometry
    # (including outlines) without disturbing Light Vectors or Outlines when active.
    try:
        cur_idx = list(primary.modifiers).index(p_mod)
        last_idx = len(primary.modifiers) - 1
        if cur_idx != last_idx:
            primary.modifiers.move(cur_idx, last_idx)
    except Exception:
        pass

    # Alt Form meshes (Body + Up2 -> Variant 1)
    for sec in alt_meshes:
        if rig is not None:
            sec.parent = rig
            arm_mod = next((m for m in sec.modifiers if m.type == 'ARMATURE'), None)
            if arm_mod is None:
                arm_mod = sec.modifiers.new(name="Armature", type='ARMATURE')
            arm_mod.object = rig

        # Keep visible in viewport & render — the GN switcher handles visibility cleanly
        sec.hide_viewport = False
        sec.hide_render = False
        try:
            sec.hide_set(False)
        except Exception:
            pass

        s_mod = sec.modifiers.get(DENIA_VARIANT_MOD_NAME)
        if s_mod is None:
            s_mod = sec.modifiers.new(name=DENIA_VARIANT_MOD_NAME, type='NODES')
        s_mod.node_group = ng_alt
        s_var_ident = _get_gn_socket_identifier(s_mod, "Variant")
        if s_var_ident:
            _set_gn_int_input(s_mod, s_var_ident, 0)

        try:
            cur_idx = list(sec.modifiers).index(s_mod)
            last_idx = len(sec.modifiers) - 1
            if cur_idx != last_idx:
                sec.modifiers.move(cur_idx, last_idx)
        except Exception:
            pass

        if var_ident and s_var_ident:
            _add_variant_driver(sec, s_mod, primary, p_mod, var_ident)

    print(
        f"[DENIA] Configured per-mesh '{DENIA_VARIANT_MOD_NAME}' (0=Default, 1=Alt Form) on "
        f"{[primary.name] + [m.name for m in alt_meshes]}"
    )


def _find_denia_variant_modifier(arm):
    if arm is None:
        return None, None
    try:
        from setup_wizard.ui.character_settings_utils import _iter_rig_meshes
        meshes = _iter_rig_meshes(arm)
    except Exception:
        meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm]

    # Prefer the primary mesh (the one without _body/_up2 in its name)
    candidates = []
    for m in meshes:
        mod = m.modifiers.get(DENIA_VARIANT_MOD_NAME)
        if mod and mod.type == 'NODES' and mod.node_group:
            is_sec = any(s in m.name.lower() for s in ("_body", "_up1", "_up2"))
            candidates.append((1 if is_sec else 0, m, mod))
    if candidates:
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1], candidates[0][2]
    return None, None


def _draw_denia_ui(layout, context, arm) -> None:
    """Draws Denia's Variant Switcher inside WuWa's Character Settings panel."""
    mesh, mod = _find_denia_variant_modifier(arm)
    if not mod:
        return
    ident = _get_variant_socket_identifier(mod)
    if not ident:
        return

    box = layout.box()
    box.label(text="Denia Settings", icon="MOD_BUILD")
    col = box.column(align=True)
    # Blender 5.2+ exposes GN modifier inputs via mod.properties.inputs.<ident>.value
    props_inputs = getattr(getattr(mod, "properties", None), "inputs", None)
    sock = getattr(props_inputs, ident, None) if props_inputs is not None else None
    if sock is not None and hasattr(sock, "value"):
        col.prop(sock, "value", text="Variant (0=Default, 1=Alt Form)")
    else:
        col.prop(mod, f'["{ident}"]', text="Variant (0=Default, 1=Alt Form)")


DENIA_PROFILE = register_profile(
    CharacterSetupProfile(
        id=DENIA_PROFILE_ID,
        display_name="Denia",
        aliases=("denia", "daniya", "r2t1daniyamd10011"),
        game_types=(GameType.WUTHERING_WAVES.name,),
        import_all_uemodels=True,
        uemodel_exclude_substrings=("_up1",),
        on_after_materials=_on_after_materials,
        on_after_outlines=_on_after_outlines,
        on_finish_setup=_on_finish_setup,
        draw_ui=_draw_denia_ui,
    )
)
