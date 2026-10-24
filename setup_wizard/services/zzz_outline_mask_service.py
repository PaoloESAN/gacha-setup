# Purpose: Creates a painted color mask and separate Solidify weights on ZZZ faces
#          so that outline modifiers (Geometry Nodes 'Outlines' or 'Solidify') only extrude the face skin
#          and exclude the eyes, eyebrows, teeth, and interior mouth details, preventing weird duplicates or clipping.

import bpy
import bmesh


def find_face_objects(context=None):
    """Finds all mesh objects that represent character faces."""
    if context is None:
        context = bpy.context

    face_objs = []
    excluded_keywords = [
        "wgt", "plane", "picker", "slider", "panel", "origin", "driver",
        "camera", "light", "shadow", "hairshadow", "armature", "facerig", "controls", "huge"
    ]

    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        o_low = obj.name.lower()
        if any(kw in o_low for kw in excluded_keywords):
            continue

        # Check by object name
        is_face = "face" in o_low

        # Or check by material slots
        if not is_face:
            for slot in obj.material_slots:
                if slot.material and "face" in slot.material.name.lower() and not any(kw in slot.material.name.lower() for kw in ["panel", "wgt"]):
                    is_face = True
                    break

        if is_face:
            face_objs.append(obj)

    return face_objs


def patch_face_outlines_node_group(nt):
    """Upgrade the shipped face hull to use the painted red mask consistently."""
    if not nt:
        return False
    sep = nt.nodes.get('Separate RGB')
    weight = nt.nodes.get('Reroute.024')
    use_colors = next((n.outputs.get('Use Vertex Colors?') for n in nt.nodes
                       if n.type == 'GROUP_INPUT' and n.outputs.get('Use Vertex Colors?') is not None), None)
    if sep is None or weight is None or use_colors is None:
        return False
    if not all(nt.nodes.get(name) for name in ('Merge by Distance', 'Set Position')):
        return False
    # The library may already contain the old per-vertex alpha/red heuristic.
    for name in ('ZZZ_Smart_Weight_Switch', 'ZZZ_Comp_Alpha_GT',
                 'ZZZ_Comp_Alpha_LT', 'ZZZ_Alpha_Range_AND'):
        old = nt.nodes.get(name)
        if old:
            nt.nodes.remove(old)
    nt.links.new(sep.outputs['Red'], weight.inputs[0])
    zero = nt.nodes.get('ZZZ_Comp_Weight_Zero') or nt.nodes.new('FunctionNodeCompare')
    zero.name = 'ZZZ_Comp_Weight_Zero'
    zero.data_type = 'FLOAT'
    zero.operation = 'LESS_EQUAL'
    zero.inputs[1].default_value = 0.001
    nt.links.new(sep.outputs['Red'], zero.inputs[0])
    gate = nt.nodes.get('ZZZ_Delete_AND') or nt.nodes.new('FunctionNodeBooleanMath')
    gate.name = 'ZZZ_Delete_AND'
    gate.operation = 'AND'
    nt.links.new(zero.outputs[0], gate.inputs[0])
    nt.links.new(use_colors, gate.inputs[1])
    delete = nt.nodes.get('ZZZ_Delete_Masked_Outlines') or nt.nodes.new('GeometryNodeDeleteGeometry')
    delete.name = 'ZZZ_Delete_Masked_Outlines'
    delete.domain = 'POINT'
    nt.links.new(gate.outputs[0], delete.inputs['Selection'])
    _filter_before_merge(nt)
    return True


def _filter_before_merge(nt):
    """Filter the hull before coincident eye/skin vertices blend mask values."""
    merge = nt.nodes.get('Merge by Distance')
    position = nt.nodes.get('Set Position')
    delete = nt.nodes.get('ZZZ_Delete_Masked_Outlines')
    if not all((merge, position, delete)):
        return
    source = next((link.from_socket for link in merge.inputs['Geometry'].links
                   if link.from_node != delete), None)
    if source is not None:
        nt.links.new(source, delete.inputs['Geometry'])
    nt.links.new(delete.outputs['Geometry'], merge.inputs['Geometry'])
    nt.links.new(merge.outputs['Geometry'], position.inputs['Geometry'])


def ensure_face_outlines_node_group():
    """
    Returns the 'face_outlines' GeometryNode tree, loading or duplicating it if needed,
    leaving 'ZZZ Outlines' completely untouched for other meshes.
    """
    face_ng = bpy.data.node_groups.get("face_outlines")
    if face_ng:
        patch_face_outlines_node_group(face_ng)
        return face_ng

    # 1. Try loading from ZZZ Setup v7.blend
    try:
        from setup_wizard.import_order import get_shader_file_path
        from setup_wizard.domain.game_types import GameType
        import os
        blend_path = get_shader_file_path(GameType.ZENLESS_ZONE_ZERO.name, 'outlines')
        if blend_path and os.path.isfile(blend_path):
            with bpy.data.libraries.load(blend_path, link=False) as (df, dt):
                if "face_outlines" in df.node_groups:
                    dt.node_groups = ["face_outlines"]
            face_ng = bpy.data.node_groups.get("face_outlines")
            if face_ng:
                face_ng.use_fake_user = True
                patch_face_outlines_node_group(face_ng)
                return face_ng
    except Exception as e:
        print(f"[ZZZ] Notice loading face_outlines from blend: {e}")

    # 2. Fallback: Duplicate ZZZ Outlines into face_outlines and patch face_outlines only
    orig = bpy.data.node_groups.get("ZZZ Outlines")
    if orig:
        face_ng = orig.copy()
        face_ng.name = "face_outlines"
        face_ng.use_fake_user = True
        patch_face_outlines_node_group(face_ng)
        return face_ng

    return None


def create_face_outline_mask(face_obj, configure_modifier=True, attribute_name="outline_mask"):
    """
    Create a color attribute and a separate `<attribute_name>_weights` group.

    Geometry Nodes can resolve a vertex group before a color attribute with
    the same name. Distinct names ensure painting the color mask affects the
    hull instead of silently reading stale vertex-group weights.

    - Face skin: Weight = 1.0 / Color = (1.0, 1.0, 1.0, 1.0) [White] -> receives outline
    - Eyes, eyebrows, teeth, mouth interior, eyeshadow: Weight = 0.0 / Color = (0.0, 0.0, 0.0, 1.0) [Black] -> masked out, no outline

    Also automatically configures Geometry Nodes 'Outlines' (using 'face_outlines') and/or 'Solidify' modifier if present.
    """
    if not face_obj or face_obj.type != 'MESH' or not face_obj.data:
        return False

    o_low = face_obj.name.lower()
    is_wgt = face_obj.name.startswith("WGT-") or any(kw in o_low for kw in ["wgt", "facerig", "panel", "picker", "slider", "control", "shape", "plane", "rim"]) or any(c.name.startswith("WGTS") or "wgt" in c.name.lower() or "facerig" in c.name.lower() for c in face_obj.users_collection)
    if is_wgt:
        return False

    mesh = face_obj.data
    if len(mesh.vertices) == 0:
        return False

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    # 1. Virtual seam welding, for classification only. Roxy's skin is split
    # into equal left/right islands; selecting just one erases half the hull.
    from mathutils.kdtree import KDTree
    tree = KDTree(len(bm.verts))
    for vertex in bm.verts:
        tree.insert(vertex.co, vertex.index)
    tree.balance()
    extent = max(max(v.co[i] for v in bm.verts) - min(v.co[i] for v in bm.verts)
                 for i in range(3))
    tolerance = max(extent * 1e-6, 1e-10)
    visited = set()
    islands = []
    for vertex in bm.verts:
        if vertex.index in visited:
            continue
        island = set()
        q = [vertex]
        visited.add(vertex.index)
        while q:
            curr = q.pop()
            island.add(curr.index)
            neighbors = [edge.other_vert(curr) for edge in curr.link_edges]
            neighbors.extend(bm.verts[index] for _, index, _ in tree.find_range(curr.co, tolerance))
            for neighbor in neighbors:
                if neighbor.index not in visited:
                    visited.add(neighbor.index)
                    q.append(neighbor)
        islands.append(island)

    # Sort virtual islands by vertex count descending.
    # In Hoyoverse / ZZZ characters, the main face skin is the largest connected manifold mesh.
    islands.sort(key=lambda x: len(x), reverse=True)
    if not islands:
        bm.free()
        return False

    main_island = islands[0]
    face_skin_vert_indices = main_island

    # 2. Material inspection: exclude any faces assigned to eye, shadow, brow, teeth, mouth, or transparent slots
    non_skin_mats = [
        "eye", "pupil", "iris", "shadow", "eyeshadow", "brow", "eyebrow",
        "teeth", "tooth", "mouth", "tongue", "transparent", "transp", "blush"
    ]
    for idx, slot in enumerate(face_obj.material_slots):
        if slot.material and any(kw in slot.material.name.lower() for kw in non_skin_mats):
            for f in bm.faces:
                if f.material_index == idx:
                    for v in f.verts:
                        face_skin_vert_indices.discard(v.index)

    # 3. Exclude eyeballs and teeth, preserving deforming skin on brows/lids.
    dvert_layer = bm.verts.layers.deform.active
    if dvert_layer and face_obj.vertex_groups:
        vg_names = [vg.name.lower() for vg in face_obj.vertex_groups]
        bone_bad_keywords = ["eye", "pupil", "iris", "eyebrow", "brow", "teeth", "tooth", "tongue", "highlight"]
        for v in bm.verts:
            if v.index in face_skin_vert_indices:
                dvert = v[dvert_layer]
                for g_idx in dvert.keys():
                    if g_idx < len(vg_names):
                        gname = vg_names[g_idx]
                        if any(kw in gname for kw in bone_bad_keywords) and not any(ok in gname for ok in ["spine", "head", "neck", "brow", "lid", "lash"]):
                            # Exclude if strongly influenced by eye/teeth bone
                            if dvert[g_idx] > 0.5:
                                face_skin_vert_indices.discard(v.index)
                                break

    bm.free()

    # Migrate legacy weights before creating the color attribute. Blender 5
    # otherwise renames the new color attribute to outline_mask.001.
    weight_name = attribute_name + '_weights'
    vg = face_obj.vertex_groups.get(weight_name)
    legacy = face_obj.vertex_groups.get(attribute_name)
    if legacy:
        if vg is None:
            legacy.name = weight_name
            vg = legacy
        else:
            face_obj.vertex_groups.remove(legacy)

    # 4. Create or update Color Attribute
    ca = mesh.color_attributes.get(attribute_name)
    if not ca:
        try:
            ca = mesh.color_attributes.new(name=attribute_name, type='FLOAT_COLOR', domain='POINT')
        except Exception:
            try:
                ca = mesh.color_attributes.new(name=attribute_name, type='BYTE_COLOR', domain='POINT')
            except Exception:
                ca = None

    if ca:
        white = (1.0, 1.0, 1.0, 1.0)
        black = (0.0, 0.0, 0.0, 1.0)
        if ca.domain == 'POINT':
            for i, d in enumerate(ca.data):
                d.color = white if i in face_skin_vert_indices else black
        elif ca.domain == 'CORNER':
            for poly in mesh.polygons:
                for loop_idx in poly.loop_indices:
                    v_idx = mesh.loops[loop_idx].vertex_index
                    ca.data[loop_idx].color = white if v_idx in face_skin_vert_indices else black

    # 5. Solidify needs weights, but GN must read the painted color attribute.
    if not vg:
        vg = face_obj.vertex_groups.new(name=weight_name)

    skin_list = list(face_skin_vert_indices)
    non_skin_list = [i for i in range(len(mesh.vertices)) if i not in face_skin_vert_indices]

    if skin_list:
        vg.add(skin_list, 1.0, 'REPLACE')
    if non_skin_list:
        vg.add(non_skin_list, 0.0, 'REPLACE')

    # 6. Configure Outline Modifiers if requested
    if configure_modifier:
        face_ng = ensure_face_outlines_node_group()
        from setup_wizard.utils.modifier_utils import set_modifier_property
        # A. Geometry Nodes 'Outlines' modifier
        mod_gn = face_obj.modifiers.get("Outlines")
        if not mod_gn:
            mod_gn = face_obj.modifiers.new("Outlines", 'NODES')
        if mod_gn and mod_gn.type == 'NODES':
            if face_ng:
                mod_gn.node_group = face_ng
            for socket in mod_gn.node_group.interface.items_tree if mod_gn.node_group else ():
                if socket.item_type != 'SOCKET' or socket.in_out != 'INPUT':
                    continue
                key = socket.identifier
                if socket.name in ('Use Vertex Colors?', 'Use Vertex Colors'):
                    set_modifier_property(mod_gn, key, True)
                elif socket.name in ('Vertex Colors', 'Vertex Color'):
                    set_modifier_property(mod_gn, key + '_use_attribute', True)
                    set_modifier_property(mod_gn, key + '_attribute_name', attribute_name)
                elif socket.name == 'Outline Thickness':
                    set_modifier_property(mod_gn, key, 0.075)

        # B. Solidify modifier
        for m in face_obj.modifiers:
            if m.type == 'SOLIDIFY':
                try:
                    m.vertex_group = weight_name
                    m.thickness_vertex_group = 0.0
                    m.invert_vertex_group = False
                except Exception:
                    pass

    print(f"[ZZZ] Configured '{attribute_name}' on {face_obj.name}: {len(skin_list)} skin verts, {len(non_skin_list)} non-skin verts.")
    return True


def setup_all_face_outline_masks(context=None, configure_modifier=True):
    """Finds all face objects and generates outline masks on each."""
    face_objs = find_face_objects(context)
    success = False
    for f_obj in face_objs:
        if create_face_outline_mask(f_obj, configure_modifier=configure_modifier):
            success = True
    return success


class ZZZ_OT_CreateFaceOutlineMask(bpy.types.Operator):
    """Generates a face outline mask (Color Attribute & Vertex Group) excluding eyes and details for ZZZ outlines"""
    bl_idname = "zenless_zone_zero.create_face_outline_mask"
    bl_label = "Create Face Outline Mask"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active_obj = context.active_object
        if active_obj and active_obj.type == 'MESH' and ("face" in active_obj.name.lower() or any("face" in s.name.lower() for s in active_obj.material_slots)):
            if not create_face_outline_mask(active_obj, configure_modifier=True):
                self.report({'WARNING'}, "Could not create face outline mask")
                return {'CANCELLED'}
            self.report({'INFO'}, f"Face outline mask created on {active_obj.name}")
            return {'FINISHED'}

        # Otherwise process all detected face objects
        count = 0
        for f_obj in find_face_objects(context):
            if create_face_outline_mask(f_obj, configure_modifier=True):
                count += 1

        if count > 0:
            self.report({'INFO'}, f"Created face outline mask on {count} face object(s)")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No face mesh objects found")
            return {'CANCELLED'}
