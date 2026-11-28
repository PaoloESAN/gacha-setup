import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from typing import List, Tuple, Set, Optional

try:
    from ..utils.modifier_utils import get_modifier_property, set_modifier_property
except ImportError:
    try:
        from setup_wizard.utils.modifier_utils import get_modifier_property, set_modifier_property
    except ImportError:
        get_modifier_property = None
        set_modifier_property = None


def _assign_to_genshin_other_material_option(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    if not obj or not getattr(obj, "modifiers", None) or not mat:
        return
    for mod in obj.modifiers:
        if getattr(mod, "type", None) != 'NODES':
            continue
        ng = getattr(mod, "node_group", None)
        if not ng:
            continue
        ng_name = (getattr(ng, "name", "") or "").lower()
        mod_name = (getattr(mod, "name", "") or "").lower()
        if "genshin impact" in ng_name or "genshin impact" in mod_name:
            if set_modifier_property:
                set_modifier_property(mod, 'Input_26', mat)
            try:
                if hasattr(mod, "properties") and hasattr(mod.properties, "inputs"):
                    if 'Input_26' in mod.properties.inputs:
                        mod.properties.inputs['Input_26']['value'] = mat
            except Exception:
                pass
            try:
                mod['Input_26'] = mat
            except Exception:
                pass


EYE_THROUGH_HAIR_S2RGB_LABEL = "Eye Through Hair Shader to RGB"
EYE_THROUGH_HAIR_AOV_COLOR_LABEL = "Eye Through Hair Color"
EYE_THROUGH_HAIR_AOV_MASK_LABEL = "Eye Through Hair Mask"
EYE_THROUGH_HAIR_SUFFIX = "_EyeThroughHair"
EYE_THROUGH_HAIR_MIN_VERSION = (5, 2, 0)


def supports_eye_through_hair():
    """Supported utility baseline; this is not the introduction version of AOVs."""
    return (bpy.app.version >= EYE_THROUGH_HAIR_MIN_VERSION
            and 'aovs' in bpy.types.ViewLayer.bl_rna.properties
            and hasattr(bpy.types, 'ShaderNodeOutputAOV')
            and hasattr(bpy.types, 'ShaderNodeShaderToRGB'))


def ensure_aov_passes(view_layer: bpy.types.ViewLayer) -> Tuple[bool, bool]:
    """Ensure that 'Eye color' and 'Eye mask' AOV passes exist in the view layer."""
    existing_aovs = {aov.name: aov for aov in view_layer.aovs}
    
    if "Eye color" not in existing_aovs:
        aov = view_layer.aovs.add()
        aov.name = "Eye color"
        if hasattr(aov, "type"):
            aov.type = 'COLOR'

    if "Eye mask" not in existing_aovs:
        aov = view_layer.aovs.add()
        aov.name = "Eye mask"
        if hasattr(aov, "type"):
            aov.type = 'COLOR'

    # Repair passes created manually or by older setups with the wrong type.
    for aov in view_layer.aovs:
        if aov.name in ('Eye color', 'Eye mask'):
            aov.type = 'COLOR'

    from .compositor_effects import order_aov_passes
    order_aov_passes(bpy.context.scene, view_layer)
    return True, True


def get_selected_faces_and_materials(obj: bpy.types.Object) -> Tuple[List[int], dict]:
    """
    Returns a list of selected face indices and a map of {material_index: [face_indices]}.
    Works both in EDIT mode and OBJECT mode.
    """
    selected_face_indices = []
    mat_index_to_faces = {}

    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        # Check faces directly selected
        faces = [f for f in bm.faces if f.select]
        if not faces:
            # Fallback: if user selected vertices or edges, find faces touching selected verts
            faces = [f for f in bm.faces if any(v.select for v in f.verts)]
        
        for f in faces:
            selected_face_indices.append(f.index)
            mat_index_to_faces.setdefault(f.material_index, []).append(f.index)
    else:
        for poly in obj.data.polygons:
            if poly.select:
                selected_face_indices.append(poly.index)
                mat_index_to_faces.setdefault(poly.material_index, []).append(poly.index)

    return selected_face_indices, mat_index_to_faces


def configure_material_eye_through_hair_nodes(mat: bpy.types.Material) -> bool:
    """
    Configures shader nodes in the duplicated material:
    - Finds Material Output Surface link.
    - Connects that surface shader into a DEDICATED Shader to RGB node.
      (Never reuses any internal Shader to RGB node already present in the material)
    - Connects that Shader to RGB Color into an AOV Output named 'Eye color'.
    - Adds an AOV Output named 'Eye mask' with pure white color (1.0, 1.0, 1.0, 1.0).
    """
    if hasattr(mat, "use_nodes"):
        try:
            mat.use_nodes = True
        except Exception:
            pass

    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = 'DITHERED'
    if hasattr(mat, "blend_method"):
        try:
            mat.blend_method = 'HASHED'
        except Exception:
            pass

    tree = getattr(mat, "node_tree", None)
    if not tree:
        return False

    nodes = tree.nodes
    links = tree.links

    # Find the active material output node
    output_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL' and getattr(n, "is_active_output", False)), None)
    if not output_node:
        output_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)

    if not output_node:
        return False

    surface_input = output_node.inputs.get("Surface")
    if not surface_input or not surface_input.is_linked:
        return False

    source_shader_socket = surface_input.links[0].from_socket

    # ONLY reuse a Shader to RGB node if it was specifically created by this eye-through-hair tool.
    # NEVER hijack internal Shader to RGB nodes that belong to the material.
    s2rgb_node = next(
        (n for n in nodes if (n.type == 'SHADER_TO_RGB' or n.bl_idname == 'ShaderNodeShaderToRGB')
         and getattr(n, "label", "") in (EYE_THROUGH_HAIR_S2RGB_LABEL, "See-Through Shader to RGB")),
        None
    )
    if not s2rgb_node:
        s2rgb_node = nodes.new(type='ShaderNodeShaderToRGB')
        s2rgb_node.name = "Shader to RGB (Eye Through Hair)"
        s2rgb_node.label = EYE_THROUGH_HAIR_S2RGB_LABEL
        s2rgb_node.location = (output_node.location.x - 220, output_node.location.y - 140)
    else:
        s2rgb_node.label = EYE_THROUGH_HAIR_S2RGB_LABEL

    # Connect surface shader output to our dedicated Shader to RGB
    links.new(source_shader_socket, s2rgb_node.inputs.get("Shader") or s2rgb_node.inputs[0])

    # AOV Output: Eye color
    aov_color = next(
        (n for n in nodes if getattr(n, "aov_name", "") == "Eye color"
         and getattr(n, "label", "") in (EYE_THROUGH_HAIR_AOV_COLOR_LABEL, "See-Through Eye Color")),
        None
    )
    if not aov_color:
        aov_color = next((n for n in nodes if getattr(n, "aov_name", "") == "Eye color"), None)

    if not aov_color:
        aov_color = nodes.new(type='ShaderNodeOutputAOV')
        aov_color.name = "AOV Output (Eye Color)"
        aov_color.label = EYE_THROUGH_HAIR_AOV_COLOR_LABEL
        aov_color.aov_name = "Eye color"
        aov_color.location = (s2rgb_node.location.x + 220, s2rgb_node.location.y)
    else:
        aov_color.label = EYE_THROUGH_HAIR_AOV_COLOR_LABEL

    # Ensure Eye color AOV is linked from OUR dedicated s2rgb node
    color_in = aov_color.inputs.get("Color") or aov_color.inputs[0]
    links.new(s2rgb_node.outputs.get("Color") or s2rgb_node.outputs[0], color_in)
    if "Value" in aov_color.inputs:
        aov_color.inputs["Value"].default_value = 0.0

    # AOV Output: Eye mask
    aov_mask = next(
        (n for n in nodes if getattr(n, "aov_name", "") == "Eye mask"
         and getattr(n, "label", "") in (EYE_THROUGH_HAIR_AOV_MASK_LABEL, "See-Through Eye Mask")),
        None
    )
    if not aov_mask:
        aov_mask = next((n for n in nodes if getattr(n, "aov_name", "") == "Eye mask"), None)

    if not aov_mask:
        aov_mask = nodes.new(type='ShaderNodeOutputAOV')
        aov_mask.name = "AOV Output (Eye Mask)"
        aov_mask.label = EYE_THROUGH_HAIR_AOV_MASK_LABEL
        aov_mask.aov_name = "Eye mask"
        aov_mask.location = (aov_color.location.x, aov_color.location.y - 120)
    else:
        aov_mask.label = EYE_THROUGH_HAIR_AOV_MASK_LABEL

    mask_color_input = aov_mask.inputs.get("Color") or aov_mask.inputs[0]
    for l in list(mask_color_input.links):
        links.remove(l)
    mask_color_input.default_value = (1.0, 1.0, 1.0, 1.0)
    if "Value" in aov_mask.inputs:
        aov_mask.inputs["Value"].default_value = 0.0

    # Prevent duplicated EyeThroughHair materials from writing Hair Shadows face/hair masks
    for n in list(nodes):
        if n.type == 'OUTPUT_AOV' and n.get('csw_hair_shadow_output'):
            aov_lower = (getattr(n, "aov_name", "") or "").lower()
            if "face mask" in aov_lower or "hair mask" in aov_lower:
                nodes.remove(n)

    return True


def _is_eye_through_hair_material(mat: bpy.types.Material) -> bool:
    name_lower = mat.name.lower()
    return "_eyethroughhair" in name_lower or "_seethrough" in name_lower


def _set_dithered_blend(mat: bpy.types.Material) -> None:
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = 'DITHERED'
    if hasattr(mat, "blend_method"):
        try:
            mat.blend_method = 'HASHED'
        except Exception:
            pass


def _get_or_create_eye_through_hair_slot(
    obj: bpy.types.Object, orig_mat: bpy.types.Material
) -> Tuple[bpy.types.Material, int]:
    """Reuse or duplicate {orig_mat.name}_EyeThroughHair and assign its slot on obj."""
    target_name = f"{orig_mat.name}{EYE_THROUGH_HAIR_SUFFIX}"
    existing_slot = next(
        (i for i, s in enumerate(obj.material_slots) if s.material and s.material.name == target_name),
        None,
    )
    if existing_slot is not None:
        return obj.material_slots[existing_slot].material, existing_slot

    existing_mat = bpy.data.materials.get(target_name)
    if existing_mat:
        new_mat = existing_mat
    else:
        new_mat = orig_mat.copy()
        new_mat.name = target_name

    obj.data.materials.append(new_mat)
    return new_mat, len(obj.material_slots) - 1


def isolate_and_assign_eye_through_hair_materials(obj: bpy.types.Object) -> List[bpy.types.Material]:
    """
    Duplicates the selected faces on an object (like Shift+D in Edit Mode), then
    duplicates their materials into {mat}_EyeThroughHair and assigns those exclusively
    to the duplicated faces, leaving the original faces untouched.
    Reuses existing EyeThroughHair faces/slots without double-duplicating geometry.
    """
    was_edit_mode = (obj.mode == 'EDIT')
    if not was_edit_mode:
        has_sel = any(p.select for p in obj.data.polygons) or any(v.select for v in obj.data.vertices)
        if not has_sel:
            return []

    view_layer = bpy.context.view_layer
    prev_active = None
    prev_selected = []
    if not was_edit_mode:
        prev_active = view_layer.objects.active
        prev_selected = list(getattr(bpy.context, "selected_objects", []))
        for o in prev_selected:
            o.select_set(False)
        obj.select_set(True)
        view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')

    created_materials: List[bpy.types.Material] = []
    seen_created: Set[str] = set()

    try:
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            selected_faces = [f for f in bm.faces if any(v.select for v in f.verts)]
        if not selected_faces:
            return []

        faces_to_dup: List[bmesh.types.BMFace] = []
        existing_eth_faces: List[bmesh.types.BMFace] = []
        for f in selected_faces:
            if f.material_index < 0 or f.material_index >= len(obj.material_slots):
                continue
            mat = obj.material_slots[f.material_index].material
            if not mat:
                continue
            if _is_eye_through_hair_material(mat):
                existing_eth_faces.append(f)
            else:
                faces_to_dup.append(f)

        # Reconfigure already-isolated eye-through-hair faces without duplicating again
        for f in existing_eth_faces:
            mat = obj.material_slots[f.material_index].material
            if mat.name not in seen_created:
                configure_material_eye_through_hair_nodes(mat)
                _set_dithered_blend(mat)
                _assign_to_genshin_other_material_option(obj, mat)
                created_materials.append(mat)
                seen_created.add(mat.name)

        if faces_to_dup:
            # Capture original materials before appending new slots shifts slot count
            face_orig_mats = [obj.material_slots[f.material_index].material for f in faces_to_dup]
            verts_to_dup = list({v for f in faces_to_dup for v in f.verts})
            edges_to_dup = list({e for f in faces_to_dup for e in f.edges})
            geom_to_dup = verts_to_dup + edges_to_dup + faces_to_dup

            ret = bmesh.ops.duplicate(bm, geom=geom_to_dup)
            dup_faces = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMFace)]

            for elem in geom_to_dup:
                elem.select = False
            for f in existing_eth_faces:
                f.select = True
                for e in f.edges:
                    e.select = True
                for v in f.verts:
                    v.select = True
            for elem in ret["geom"]:
                elem.select = True

            # Map duplicated faces to their respective source material index
            mat_index_to_dup_faces: dict = {}
            for df in dup_faces:
                mat_index_to_dup_faces.setdefault(df.material_index, []).append(df)

            orig_by_index = {}
            for f, mat in zip(faces_to_dup, face_orig_mats):
                orig_by_index.setdefault(f.material_index, mat)

            for mat_idx, grp_faces in mat_index_to_dup_faces.items():
                orig_mat = orig_by_index.get(mat_idx)
                if not orig_mat:
                    continue
                new_mat, new_slot_idx = _get_or_create_eye_through_hair_slot(obj, orig_mat)
                if new_mat.name not in seen_created:
                    configure_material_eye_through_hair_nodes(new_mat)
                    _set_dithered_blend(new_mat)
                    _assign_to_genshin_other_material_option(obj, new_mat)
                    created_materials.append(new_mat)
                    seen_created.add(new_mat.name)

                for df in grp_faces:
                    df.material_index = new_slot_idx

        bm.select_flush_mode()
        bmesh.update_edit_mesh(obj.data)
    finally:
        if not was_edit_mode:
            bpy.ops.object.mode_set(mode='OBJECT')
            for o in list(getattr(bpy.context, "selected_objects", [])):
                o.select_set(False)
            for o in prev_selected:
                if o and o.name in bpy.data.objects:
                    o.select_set(True)
            if prev_active and prev_active.name in bpy.data.objects:
                view_layer.objects.active = prev_active

    return created_materials


def _collect_selected_face_rays(objs: List[bpy.types.Object]) -> List[Tuple[Vector, Vector]]:
    """Collect world-space (center, normal) rays from selected faces on target meshes."""
    rays: List[Tuple[Vector, Vector]] = []
    for obj in objs:
        if not obj or obj.type != 'MESH' or not obj.data:
            continue
        mw = obj.matrix_world
        try:
            nm = mw.to_3x3().inverted().transposed()
        except ValueError:
            nm = mw.to_3x3()
        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            faces = [f for f in bm.faces if f.select]
            if not faces:
                faces = [f for f in bm.faces if any(v.select for v in f.verts)]
            for f in faces:
                n = (nm @ f.normal)
                if n.length > 1e-6:
                    rays.append((mw @ f.calc_center_median(), n.normalized()))
        else:
            for p in obj.data.polygons:
                if p.select:
                    n = (nm @ p.normal)
                    if n.length > 1e-6:
                        rays.append((mw @ p.center, n.normalized()))
    return rays


def _collect_paired_outline_materials(obj: bpy.types.Object, hair_mats: Set[bpy.types.Material]) -> List[bpy.types.Material]:
    """Find outline materials paired with hair_mats in Geometry Nodes Outlines modifiers."""
    if not obj or not getattr(obj, "modifiers", None) or not hair_mats or not get_modifier_property:
        return []
    paired: List[bpy.types.Material] = []
    for mod in obj.modifiers:
        if getattr(mod, "type", None) != 'NODES' or not getattr(mod, "node_group", None):
            continue
        ng = mod.node_group
        if "outline" not in (mod.name or "").lower() and "outline" not in (ng.name or "").lower():
            continue
        sockets_by_name = {}
        for item in ng.interface.items_tree:
            if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.socket_type == 'NodeSocketMaterial':
                sockets_by_name[item.name] = item.identifier
        for s_name, s_id in sockets_by_name.items():
            if s_name.lower().endswith("outline"):
                continue
            val = get_modifier_property(mod, s_id)
            if val in hair_mats:
                ol_id = sockets_by_name.get(f"{s_name} Outline")
                if ol_id:
                    ol_mat = get_modifier_property(mod, ol_id)
                    if isinstance(ol_mat, bpy.types.Material) and ol_mat not in paired:
                        paired.append(ol_mat)
    return paired


def _detect_occluding_hair_materials(
    context: bpy.types.Context,
    target_objs: List[bpy.types.Object],
    selected_eye_rays: List[Tuple[Vector, Vector]],
) -> List[Tuple[bpy.types.Object, bpy.types.Material]]:
    """
    Detect hair materials that don't have 'hair' in their mesh/material name
    (e.g. ZZZ characters like Rina/Belle/Wise/Robin/Vivian whose hair lives in Body_2).
    Uses:
    1. Forward raycasts from selected eye/eyebrow faces onto visible non-target meshes.
    2. Hair-bone vertex-group fallback on meshes sharing the same armature.
    """
    detected: List[Tuple[bpy.types.Object, bpy.types.Material]] = []
    seen: Set[Tuple[str, str]] = set()
    target_set = set(target_objs or [])
    target_armatures = {o.find_armature() for o in target_set if o.type == 'MESH' and o.find_armature()}
    ignored_obj_keywords = ("hairshadow", "wgt", "colorwheel", "panel", "widget", "eyeglass", "glasses")
    hair_vg_keywords = ("hair", "hari", "pelo", "bang", "ahoge", "ponytail", "twintail")

    # Subsample rays if there are many selected faces to keep it fast
    rays = selected_eye_rays or []
    if len(rays) > 256:
        step = max(1, len(rays) // 256)
        rays = rays[::step]
    eye_center = (sum((pt for pt, _ in rays), Vector()) / len(rays)) if rays else None

    def add_mat(obj: bpy.types.Object, mat: Optional[bpy.types.Material]):
        if not mat or _is_eye_through_hair_material(mat):
            return
        m_low = mat.name.lower()
        if any(k in m_low for k in ("eye transparent", "eyeglass", "glasses", "transp ol")):
            return
        key = (obj.name, mat.name)
        if key not in seen:
            seen.add(key)
            detected.append((obj, mat))

    for obj in context.scene.objects:
        if obj.type != 'MESH' or obj in target_set or not obj.data or not obj.data.polygons:
            continue
        if obj.hide_viewport or obj.hide_render or obj.get("csw_hair_shadow_proxy"):
            continue
        o_low = obj.name.lower()
        if any(k in o_low for k in ignored_obj_keywords) or "face" in o_low or "weapon" in o_low:
            continue

        # 1. Geometric raycast in front of selected eye/eyebrow faces
        if rays:
            mw = obj.matrix_world
            verts = [mw @ v.co for v in obj.data.vertices]
            polys = [list(p.vertices) for p in obj.data.polygons]
            try:
                bvh = BVHTree.FromPolygons(verts, polys)
            except Exception:
                bvh = None
            if bvh:
                hit_slots: Set[int] = set()
                for pt, n in rays:
                    loc, _norm, idx, _dist = bvh.ray_cast(pt + n * 0.001, n, 0.25)
                    if loc is not None and 0 <= idx < len(obj.data.polygons):
                        hit_slots.add(obj.data.polygons[idx].material_index)
                for slot_idx in hit_slots:
                    if 0 <= slot_idx < len(obj.material_slots):
                        add_mat(obj, obj.material_slots[slot_idx].material)

        # 2. Hair-bone vertex group fallback for same-character meshes near the eyes/head
        if target_armatures and obj.find_armature() in target_armatures and obj.vertex_groups:
            hair_vg_indices = {
                vg.index for vg in obj.vertex_groups
                if any(k in vg.name.lower() for k in hair_vg_keywords)
            }
            if hair_vg_indices:
                mw = obj.matrix_world
                hair_verts = {
                    v.index for v in obj.data.vertices
                    if any(g.group in hair_vg_indices and g.weight > 0.2 for g in v.groups)
                    and (eye_center is None or ((mw @ v.co) - eye_center).length < 0.35)
                }
                if hair_verts:
                    slot_hits: Set[int] = set()
                    for p in obj.data.polygons:
                        if any(vi in hair_verts for vi in p.vertices):
                            slot_hits.add(p.material_index)
                    for slot_idx in slot_hits:
                        if 0 <= slot_idx < len(obj.material_slots):
                            add_mat(obj, obj.material_slots[slot_idx].material)

    return detected


def _is_hair_shadow_dithered_material(mat: bpy.types.Material) -> bool:
    if not mat:
        return False
    return bool(mat.get("csw_hair_shadow_dithered")) or "_hairshadowdithered" in mat.name.lower()


def configure_hair_materials_blended(
    context: bpy.types.Context,
    target_objs: Optional[List[bpy.types.Object]] = None,
    selected_eye_rays: Optional[List[Tuple[Vector, Vector]]] = None,
) -> int:
    """
    Finds hair objects and materials in the scene (including NTE 'mrim' material
    and ZZZ characters whose hair is inside a Body_* mesh)
    and ensures they use 'BLENDED' (Eevee Next) / 'BLEND' (legacy Eevee) render method.
    Disables use_transparency_overlap on hair mesh materials and HSR/ZZZ hair outlines.
    Other games' outline settings are preserved.
    Explicitly ignores eye-through-hair materials (_EyeThroughHair, _SeeThrough)
    and Hair Shadows render-layer dithered copies (_HairShadowDithered) so they
    remain DITHERED.
    """
    count = 0
    hair_keywords = ("hair", "pelo", "bangs", "mrim")
    outline_keywords = ("outline", "_ol", "mrim")
    processed_materials = set()
    blended_hair_mats_by_obj: dict = {}

    def process_material(mat: bpy.types.Material, is_hair_mesh_obj: bool, is_outline_obj: bool, force_no_overlap: bool = False):
        nonlocal count
        if not mat or mat.name in processed_materials:
            return
        if _is_eye_through_hair_material(mat) or _is_hair_shadow_dithered_material(mat):
            return
        processed_materials.add(mat.name)

        is_outline = is_outline_obj or any(k in mat.name.lower() for k in outline_keywords)
        modified = False

        if hasattr(mat, "surface_render_method") and mat.surface_render_method != 'BLENDED':
            mat.surface_render_method = 'BLENDED'
            modified = True
        if hasattr(mat, "blend_method") and mat.blend_method != 'BLEND':
            mat.blend_method = 'BLEND'
            modified = True

        is_hsr_outline = is_outline and mat.name.lower().startswith(('stellartoon', 'hsr -'))
        is_zzz_outline = is_outline and mat.name.lower().startswith('zzz ')
        if not is_outline or is_hsr_outline or is_zzz_outline or force_no_overlap:
            if hasattr(mat, "use_transparency_overlap") and mat.use_transparency_overlap:
                mat.use_transparency_overlap = False
                modified = True

        if modified:
            count += 1

    # 1. Check all mesh objects with hair in their name
    for o in context.scene.objects:
        if o.type == 'MESH':
            if o.get("csw_hair_shadow_proxy"):
                continue
            is_hair_obj = any(k in o.name.lower() for k in hair_keywords)
            is_outline_obj = any(k in o.name.lower() for k in outline_keywords)
            for slot in o.material_slots:
                mat = slot.material
                if not mat:
                    continue
                if _is_eye_through_hair_material(mat) or _is_hair_shadow_dithered_material(mat):
                    continue
                is_hair_mat = any(k in mat.name.lower() for k in hair_keywords)
                if is_hair_obj or is_hair_mat:
                    process_material(mat, is_hair_mesh_obj=is_hair_obj and not is_outline_obj, is_outline_obj=is_outline_obj)
                    if not is_outline_obj:
                        blended_hair_mats_by_obj.setdefault(o, set()).add(mat)

    # 2. Check all materials in bpy.data.materials as fallback
    for mat in bpy.data.materials:
        if _is_eye_through_hair_material(mat) or _is_hair_shadow_dithered_material(mat):
            continue
        if any(k in mat.name.lower() for k in hair_keywords):
            process_material(mat, is_hair_mesh_obj=True, is_outline_obj=False)

    # 3. Geometric & hair-bone detection for characters whose hair is inside Body_* meshes (e.g. ZZZ Rina/Belle/Wise/Vivian)
    if target_objs or selected_eye_rays:
        for obj, mat in _detect_occluding_hair_materials(context, target_objs or [], selected_eye_rays or []):
            process_material(mat, is_hair_mesh_obj=True, is_outline_obj=False)
            blended_hair_mats_by_obj.setdefault(obj, set()).add(mat)

    # 4. Also set paired Geometry Nodes outline materials (e.g. ZZZ Body 2 Outlines) to BLENDED
    for obj, mats in blended_hair_mats_by_obj.items():
        for ol_mat in _collect_paired_outline_materials(obj, mats):
            process_material(ol_mat, is_hair_mesh_obj=False, is_outline_obj=True)

    return count


def get_or_create_compositor_tree(scene: bpy.types.Scene) -> bpy.types.NodeTree:
    """
    Retrieves or creates the compositor node tree across Blender 4.x / Goo Engine
    and Blender 5.x.
    """
    scene.render.use_compositing = True
    if hasattr(scene, "compositing_node_group"):
        if not scene.compositing_node_group:
            scene.compositing_node_group = bpy.data.node_groups.new("Compositing Nodetree", "CompositorNodeTree")
        return scene.compositing_node_group
    else:
        if hasattr(scene, "use_nodes"):
            scene.use_nodes = True
        return getattr(scene, "node_tree", None)


def setup_compositor_nodes(scene: bpy.types.Scene) -> bool:
    """Expose the effect as one Eye See Through group with an Opacity control."""
    from .compositor_effects import setup_eye_group
    tree = get_or_create_compositor_tree(scene)
    return bool(tree and setup_eye_group(scene, tree))


def set_viewport_compositor_always(context: bpy.types.Context) -> None:
    """Sets Viewport Compositor to 'ALWAYS' across all 3D View spaces."""
    screens: Set[bpy.types.Screen] = set()
    if hasattr(context, "screen") and context.screen:
        screens.add(context.screen)
    for scr in bpy.data.screens:
        screens.add(scr)
    for wm in bpy.data.window_managers:
        for win in wm.windows:
            if win.screen:
                screens.add(win.screen)

    for scr in screens:
        for area in scr.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D' and hasattr(space, "shading"):
                        if hasattr(space.shading, "use_compositor"):
                            try:
                                space.shading.use_compositor = 'ALWAYS'
                            except Exception:
                                pass


def get_target_mesh_objects(context: bpy.types.Context) -> List[bpy.types.Object]:
    """
    Returns all candidate mesh objects:
    - Objects currently in Edit mode (multi-object editing)
    - Selected mesh objects
    - Active mesh object
    """
    target_objs = []
    
    # 1. Objects in Edit mode (multi-object editing in Blender 2.8+)
    if hasattr(context, "objects_in_mode") and context.objects_in_mode:
        for o in context.objects_in_mode:
            if o.type == 'MESH' and o not in target_objs:
                target_objs.append(o)

    # 2. Selected objects
    for o in getattr(context, "selected_objects", []):
        if o.type == 'MESH' and o not in target_objs:
            target_objs.append(o)

    # 3. Active object fallback
    act = context.active_object or context.object
    if act and act.type == 'MESH' and act not in target_objs:
        target_objs.append(act)

    return target_objs


def execute_eye_through_hair(context: bpy.types.Context) -> Tuple[bool, str]:
    """
    Full pipeline execution:
    1. Ensures AOV passes in ViewLayer.
    2. Isolates materials for selected faces on ALL target mesh objects (multi-object support).
    3. Configures hair materials to blended render method.
    4. Sets up Compositor nodes.
    5. Sets viewport compositor to ALWAYS.
    """
    if not supports_eye_through_hair():
        return False, 'Eye Through Hair requires Blender 5.2 or newer with shader AOV support.'
    target_objs = get_target_mesh_objects(context)
    if not target_objs:
        return False, "No mesh objects found in selection or active context."

    # Step 1: Ensure AOVs
    view_layer = context.view_layer
    ensure_aov_passes(view_layer)

    # Collect world-space rays from selected faces before duplication alters selection
    selected_eye_rays = _collect_selected_face_rays(target_objs)

    # Step 2: Isolate materials & configure shader nodes across all target objects
    all_created_materials = []
    processed_objects = []

    for obj in target_objs:
        created = isolate_and_assign_eye_through_hair_materials(obj)
        if created:
            all_created_materials.extend(created)
            processed_objects.append(obj.name)

    if not all_created_materials:
        return False, "No faces were selected on any target mesh. Please select eye/eyebrow faces in Edit Mode."

    # Step 3: Hair materials to BLENDED
    hair_count = configure_hair_materials_blended(
        context, target_objs=target_objs, selected_eye_rays=selected_eye_rays
    )

    # Step 3b: Ensure all eye through hair materials are set to DITHERED
    for mat in all_created_materials:
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = 'DITHERED'
        if hasattr(mat, "blend_method"):
            try:
                mat.blend_method = 'HASHED'
            except Exception:
                pass
    for mat in bpy.data.materials:
        if "_eyethroughhair" in mat.name.lower() or "_seethrough" in mat.name.lower():
            if hasattr(mat, "surface_render_method"):
                mat.surface_render_method = 'DITHERED'
            if hasattr(mat, "blend_method"):
                try:
                    mat.blend_method = 'HASHED'
                except Exception:
                    pass

    # Step 4: Compositor setup
    comp_ok = setup_compositor_nodes(context.scene)
    if not comp_ok:
        return False, "Failed to configure Compositor node tree."

    # Step 5: Set viewport compositor to ALWAYS
    set_viewport_compositor_always(context)

    obj_names_str = ", ".join(processed_objects)
    return True, (
        f"Successfully applied Eye Through Hair on {len(processed_objects)} object(s) [{obj_names_str}] "
        f"({len(all_created_materials)} materials isolated as Dithered, {hair_count} hair materials set to Blended). "
        f"Viewport Compositor set to ALWAYS."
    )


class CSW_OT_EyeThroughHair(bpy.types.Operator):
    """Configure eye through hair effect for selected mesh faces with AOVs and Compositor"""
    bl_idname = "setup_wizard.eye_through_hair"
    bl_label = "Eye Through Hair"
    bl_description = "Duplicate selected eye/eyebrow faces and assign EyeThroughHair materials to the duplicates, add AOVs, set hair to Blended, and set Compositor to Always"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not supports_eye_through_hair():
            cls.poll_message_set('Eye Through Hair requires Blender 5.2 or newer with shader AOV support.')
            return False
        if context.active_object and context.active_object.type == 'MESH':
            return True
        if any(o.type == 'MESH' for o in getattr(context, 'selected_objects', [])):
            return True
        if any(o.type == 'MESH' for o in getattr(context, 'objects_in_mode', [])):
            return True
        return False

    def execute(self, context):
        success, message = execute_eye_through_hair(context)
        if success:
            self.report({'INFO'}, message)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}
