# Purpose: Creates a Color Attribute & Vertex Group mask on character face meshes in Zenless Zone Zero (ZZZ)
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
    """
    Patches 'face_outlines' Geometry Node tree in-memory:
    1. Smart Weight Selector: If Alpha is between 0.001 and 0.999 (original game rip channel),
       use Alpha. Otherwise (Alpha=0 or 1, typical for painted vertex colors, vertex groups, and color attributes),
       use Red.
    2. Geometry Deletion: Automatically deletes un-extruded outline faces (eyes, brows, mouth)
       from the inverted-hull outline stream so duplicate/glitched faces never overlap the face details.
    """
    if not nt or nt.nodes.get('ZZZ_Smart_Weight_Switch'):
        return False

    sep_rgb = nt.nodes.get('Separate RGB')
    if not sep_rgb:
        for n in nt.nodes:
            if n.type in ('SEPARATE_COLOR', 'SEPARATE_RGBA'):
                sep_rgb = n
                break
    if not sep_rgb:
        return False

    comp_gt = nt.nodes.new('FunctionNodeCompare')
    comp_gt.name = 'ZZZ_Comp_Alpha_GT'
    comp_gt.data_type = 'FLOAT'
    comp_gt.operation = 'GREATER_THAN'
    comp_gt.inputs[1].default_value = 0.001

    comp_lt = nt.nodes.new('FunctionNodeCompare')
    comp_lt.name = 'ZZZ_Comp_Alpha_LT'
    comp_lt.data_type = 'FLOAT'
    comp_lt.operation = 'LESS_THAN'
    comp_lt.inputs[1].default_value = 0.999

    and_alpha = nt.nodes.new('FunctionNodeBooleanMath')
    and_alpha.name = 'ZZZ_Alpha_Range_AND'
    and_alpha.operation = 'AND'

    sw_weight = nt.nodes.new('GeometryNodeSwitch')
    sw_weight.name = 'ZZZ_Smart_Weight_Switch'
    sw_weight.input_type = 'FLOAT'

    nt.links.new(sep_rgb.outputs['Alpha'], comp_gt.inputs[0])
    nt.links.new(sep_rgb.outputs['Alpha'], comp_lt.inputs[0])
    nt.links.new(comp_gt.outputs[0], and_alpha.inputs[0])
    nt.links.new(comp_lt.outputs[0], and_alpha.inputs[1])
    nt.links.new(and_alpha.outputs[0], sw_weight.inputs['Switch'])
    nt.links.new(sep_rgb.outputs['Red'], sw_weight.inputs['False'])
    nt.links.new(sep_rgb.outputs['Alpha'], sw_weight.inputs['True'])

    rr24 = nt.nodes.get('Reroute.024')
    if rr24:
        for l in list(rr24.inputs[0].links):
            nt.links.remove(l)
        nt.links.new(sw_weight.outputs['Output'], rr24.inputs[0])

    comp_zero = nt.nodes.new('FunctionNodeCompare')
    comp_zero.name = 'ZZZ_Comp_Weight_Zero'
    comp_zero.data_type = 'FLOAT'
    comp_zero.operation = 'LESS_EQUAL'
    comp_zero.inputs[1].default_value = 0.001
    nt.links.new(sw_weight.outputs['Output'], comp_zero.inputs[0])

    use_vc_sock = None
    for n in nt.nodes:
        if n.type == 'GROUP_INPUT':
            for out in n.outputs:
                if 'use vertex color' in out.name.lower():
                    use_vc_sock = out
                    break
        if use_vc_sock:
            break

    and_del = nt.nodes.new('FunctionNodeBooleanMath')
    and_del.name = 'ZZZ_Delete_AND'
    and_del.operation = 'AND'
    nt.links.new(comp_zero.outputs[0], and_del.inputs[0])
    if use_vc_sock:
        nt.links.new(use_vc_sock, and_del.inputs[1])

    del_geo = nt.nodes.new('GeometryNodeDeleteGeometry')
    del_geo.name = 'ZZZ_Delete_Masked_Outlines'
    del_geo.domain = 'POINT'
    nt.links.new(and_del.outputs[0], del_geo.inputs['Selection'])

    merge_node = nt.nodes.get('Merge by Distance')
    set_pos = nt.nodes.get('Set Position')
    if merge_node and set_pos:
        for l in list(set_pos.inputs['Geometry'].links):
            if l.from_node == merge_node:
                nt.links.remove(l)
        nt.links.new(merge_node.outputs['Geometry'], del_geo.inputs['Geometry'])
        nt.links.new(del_geo.outputs['Geometry'], set_pos.inputs['Geometry'])

    print(f"[ZZZ] Successfully patched '{nt.name}' for smart vertex color & geometry deletion.")
    return True


def ensure_face_outlines_node_group():
    """
    Returns the 'face_outlines' GeometryNode tree, loading or duplicating it if needed,
    leaving 'ZZZ Outlines' completely untouched for other meshes.
    """
    face_ng = bpy.data.node_groups.get("face_outlines")
    if face_ng:
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
    Creates both a Color Attribute and a Vertex Group named `attribute_name` on `face_obj`.

    - Face skin: Weight = 1.0 / Color = (1.0, 1.0, 1.0, 1.0) [White] -> receives outline
    - Eyes, eyebrows, teeth, mouth interior, eyeshadow: Weight = 0.0 / Color = (0.0, 0.0, 0.0, 1.0) [Black] -> masked out, no outline

    Also automatically configures Geometry Nodes 'Outlines' (using 'face_outlines') and/or 'Solidify' modifier if present.
    """
    face_ng = ensure_face_outlines_node_group()

    if not face_obj or face_obj.type != 'MESH' or not face_obj.data:
        return False

    o_low = face_obj.name.lower()
    is_wgt = face_obj.name.startswith("WGT-") or any(kw in o_low for kw in ["wgt", "facerig", "panel", "picker", "slider", "control", "shape", "plane", "rim"]) or any(c.name.startswith("WGTS") or "wgt" in c.name.lower() or "facerig" in c.name.lower() for c in face_obj.users_collection)
    if is_wgt:
        face_obj.modifiers.clear()
        return False

    mesh = face_obj.data
    if len(mesh.vertices) == 0:
        return False

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    # 1. Connected components (mesh island) detection
    visited = set()
    islands = []
    for f in bm.faces:
        if f in visited:
            continue
        island = []
        q = [f]
        visited.add(f)
        while q:
            curr = q.pop()
            island.append(curr)
            for e in curr.edges:
                for lf in e.link_faces:
                    if lf not in visited:
                        visited.add(lf)
                        q.append(lf)
        islands.append(island)

    # Sort islands by face count descending.
    # In Hoyoverse / ZZZ characters, the main face skin is the largest connected manifold mesh.
    islands.sort(key=lambda x: len(x), reverse=True)
    if not islands:
        bm.free()
        return False

    main_island = islands[0]
    face_skin_vert_indices = set(v.index for f in main_island for v in f.verts)

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

    # 3. Vertex deform group check: exclude vertices weighted primarily to eye, brow, or teeth bones
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
                        if any(kw in gname for kw in bone_bad_keywords) and not any(ok in gname for ok in ["spine", "head", "neck"]):
                            # Exclude if strongly influenced by eye/teeth bone
                            if dvert[g_idx] > 0.5:
                                face_skin_vert_indices.discard(v.index)
                                break

    bm.free()

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

    # 5. Create or update Vertex Group (essential for Solidify modifier and flexible GN access)
    vg = face_obj.vertex_groups.get(attribute_name)
    if not vg:
        vg = face_obj.vertex_groups.new(name=attribute_name)

    skin_list = list(face_skin_vert_indices)
    non_skin_list = [i for i in range(len(mesh.vertices)) if i not in face_skin_vert_indices]

    if skin_list:
        vg.add(skin_list, 1.0, 'REPLACE')
    if non_skin_list:
        vg.add(non_skin_list, 0.0, 'REPLACE')

    # 6. Configure Outline Modifiers if requested
    if configure_modifier:
        # A. Geometry Nodes 'Outlines' modifier
        mod_gn = face_obj.modifiers.get("Outlines")
        if not mod_gn:
            mod_gn = face_obj.modifiers.new("Outlines", 'NODES')
        if mod_gn and mod_gn.type == 'NODES':
            if face_ng:
                mod_gn.node_group = face_ng
            # Set 'Use Vertex Colors?' (Input_13) to True
            try:
                mod_gn["Input_13"] = True
            except Exception:
                pass

            # Set 'Vertex Colors' (Input_3) to use attribute mode with attribute_name
            # Blender 4.0+ / 5.x interface inputs
            if hasattr(mod_gn, "properties") and hasattr(mod_gn.properties, "inputs"):
                inp_item = getattr(mod_gn.properties.inputs, "Input_3", None) or getattr(mod_gn.properties.inputs, "Vertex Colors", None)
                if inp_item:
                    try:
                        inp_item.type = 'ATTRIBUTE'
                        inp_item.attribute_name = attribute_name
                    except Exception:
                        pass

            try:
                mod_gn['Input_3_use_attribute'] = 1
                mod_gn['Input_3_attribute_name'] = attribute_name
            except Exception:
                pass

            # Outline Thickness = 0.075 without exception
            try:
                mod_gn["Input_7"] = 0.075
            except Exception:
                pass
            if hasattr(mod_gn, "properties") and hasattr(mod_gn.properties, "inputs"):
                inp_th = getattr(mod_gn.properties.inputs, "Input_7", None) or getattr(mod_gn.properties.inputs, "Outline Thickness", None)
                if inp_th and hasattr(inp_th, "value"):
                    try:
                        inp_th.value = 0.075
                    except Exception:
                        pass

        # B. Solidify modifier
        for m in face_obj.modifiers:
            if m.type == 'SOLIDIFY':
                try:
                    m.vertex_group = attribute_name
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
            create_face_outline_mask(active_obj, configure_modifier=True)
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
