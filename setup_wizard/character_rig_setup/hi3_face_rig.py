# Author: Gacha Setup (HI3 Integration via WuWa Face Panel System)
# Wuthering Waves Style Face Rig for Honkai Impact 3rd Characters
# Integrates central facial widgets (Brows, Eyelids, Mouth Corners) and side expression slider grids

import bpy
import math
from mathutils import Vector, Matrix

HEAD_BONE_NAME = None
CLEAN_REBUILD = True
FLIP_HORIZONTAL = True
FLIP_VERTICAL = False

BONE_LEN_F = 0.060
OFFSET_F = 0.040
TRAVEL_F = 0.033
SPACING_F = 0.050
WIDGET_F = 1.0
FACERIG_COLLECTION = "Face"
RIGIFY_UI_ROW = 1

# WuWa standard color groups
COL_MOUTH = (0.95, 0.25, 0.25)
COL_CORNER = (0.95, 0.70, 0.15)
COL_BROW = (0.25, 0.85, 0.35)
COL_EYELID = (0.20, 0.80, 0.95)
COL_EXPRESSION = (0.95, 0.30, 0.30)
COL_CHEEK = (0.95, 0.45, 0.75)
COL_PRESET = (0.75, 0.35, 0.95)
COL_VARIATION = (0.25, 0.60, 0.95)
COL_LABEL = (1.00, 1.00, 1.00)

HEAD_CANDIDATES = [
    "DEF-spine.006", "spine.006", "head", "Head", "Bip001 Head", "Bip001_Head",
    "Bip001Head", "ORG-head", "Head_M", "head_M"
]

ISAAC_BLINK_TOP_VERTS = [[1.0, 0.0, 0.5638], [-1.0, 0.0, 0.5638], [-0.0, 0.0, 0.8878], [-0.0, 0.0, -0.484], [-0.5916, 0.0, -0.0569], [0.5916, 0.0, -0.0569], [0.6306, 0.0, 0.8199], [-0.6306, 0.0, 0.8199], [-1.0, 0.0, 0.5638], [-0.0, 0.0, -0.484], [1.0, 0.0, 0.5638]]
ISAAC_BLINK_TOP_EDGES = [[7, 1], [4, 1], [3, 4], [6, 2], [5, 3], [0, 5], [0, 6], [2, 7], [1, 8], [3, 9], [0, 10]]
ISAAC_BLINK_BOT_VERTS = [[-1.0, 0.0, -0.5638], [1.0, 0.0, -0.5638], [0.0, 0.0, -0.8878], [0.0, 0.0, 0.484], [0.5916, 0.0, 0.0569], [-0.5916, 0.0, 0.0569], [-0.6306, 0.0, -0.8199], [0.6306, 0.0, -0.8199], [1.0, 0.0, -0.5638], [0.0, 0.0, 0.484], [-1.0, 0.0, -0.5638]]
ISAAC_BLINK_BOT_EDGES = [[7, 1], [4, 1], [3, 4], [6, 2], [5, 3], [0, 5], [0, 6], [2, 7], [1, 8], [3, 9], [0, 10]]


def is_blender_3():
    return bpy.app.version[0] == 3


def find_face_meshes():
    meshes = []
    for obj in bpy.context.view_layer.objects:
        if obj.type == 'MESH' and obj.data and obj.data.shape_keys:
            n = obj.name.lower()
            if any(k in n for k in ["face", "eyebrow", "eyeshape", "eye", "head", "mouth"]) and not any(ign in n for ign in ["weapon", "toy", "gun"]):
                meshes.append(obj)
    if not meshes:
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.data and obj.data.shape_keys:
                meshes.append(obj)
    return meshes


def find_armature_and_head(mesh_objs):
    armature = None
    for o in bpy.data.objects:
        if o.type == 'ARMATURE' and (o.name.endswith("Rig") or "rig" in o.name.lower()) and "metarig" not in o.name.lower():
            armature = o
            break
    if armature is None:
        for m in mesh_objs:
            for mod in m.modifiers:
                if mod.type == 'ARMATURE' and mod.object and "metarig" not in mod.object.name.lower():
                    armature = mod.object
                    break
            if armature:
                break
    if armature is None:
        for o in bpy.data.objects:
            if o.type == 'ARMATURE' and "metarig" not in o.name.lower():
                armature = o
                break
    if armature is None:
        raise RuntimeError("No armature found for HI3 Face Rig.")

    head_name = None
    for cand in HEAD_CANDIDATES:
        if cand in armature.data.bones:
            head_name = cand
            break
    if not head_name:
        for b in armature.data.bones:
            if 'head' in b.name.lower():
                head_name = b.name
                break
    if not head_name:
        head_name = armature.data.bones[0].name

    return armature, head_name


def get_face_metrics(face_meshes, armature, head_name):
    head_pos = None
    head_tail = None
    if armature and head_name and hasattr(armature, 'data') and hasattr(armature.data, 'bones'):
        head_bone = armature.data.bones.get(head_name)
        if head_bone:
            head_pos = armature.matrix_world @ head_bone.head_local
            head_tail = armature.matrix_world @ head_bone.tail_local

    fwd = Vector((0.0, -1.0, 0.0))
    world_up = Vector((0.0, 0.0, 1.0))
    right = world_up.cross(fwd).normalized()
    up = fwd.cross(right).normalized()

    if head_pos and head_tail:
        head_len = (head_tail - head_pos).length
        face_size = max(0.18, min(0.28, head_len * 1.15 if head_len > 0.05 else 0.22))
        fcx = head_pos + up * 0.03 + fwd * 0.035
    else:
        face_size = 0.22
        fcx = Vector((0.0, -0.05, 1.45))

    return fwd, right, up, face_size, fcx


def get_widget_collection():
    name = "WGTS_FaceRig_HI3"
    coll = bpy.data.collections.get(name)
    if not coll:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def make_widget(kind, coll):
    name = f"WGT-HI3_{kind}"
    existing = bpy.data.objects.get(name)
    if existing:
        return existing

    if kind == 'isaac_blink_top':
        verts = ISAAC_BLINK_TOP_VERTS
        edges = ISAAC_BLINK_TOP_EDGES
    elif kind == 'isaac_blink_bot':
        verts = ISAAC_BLINK_BOT_VERTS
        edges = ISAAC_BLINK_BOT_EDGES
    elif kind == 'pad':
        s = 1.0
        verts = [(-s, 0, -s), (s, 0, -s), (s, 0, s), (-s, 0, s)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
    elif kind == 'slider':
        verts = [(0, 0, -1), (0, 0, 1), (-0.45, 0, 1), (0.45, 0, 1)]
        edges = [(0, 1), (2, 3)]
    elif kind == 'ring':
        verts, edges, N = [], [], 20
        for i in range(N):
            a = 2 * math.pi * i / N
            verts.append((math.cos(a), 0.0, math.sin(a)))
            edges.append((i, (i + 1) % N))
    elif kind == 'triangle':
        verts = [(0, 0, 1), (-0.9, 0, -0.7), (0.9, 0, -0.7)]
        edges = [(0, 1), (1, 2), (2, 0)]
    elif kind == 'triangle_down':
        verts = [(0, 0, -1), (-0.9, 0, 0.7), (0.9, 0, 0.7)]
        edges = [(0, 1), (1, 2), (2, 0)]
    else:
        s = 1.0
        verts = [(-s, 0, -s), (s, 0, -s), (s, 0, s), (-s, 0, s)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def make_text_widget(text_string, wgt_coll):
    clean_name = text_string.replace(' ', '_').replace(':', '_').replace('&', 'AND')
    name = f"WGT-HI3_Text_{clean_name}"
    existing = bpy.data.objects.get(name)
    if existing:
        return existing

    try:
        curve_data = bpy.data.curves.new(name=name + "_Curve", type='FONT')
        curve_data.body = text_string
        curve_data.size = 1.0
        curve_data.align_x = 'CENTER'
        curve_data.align_y = 'CENTER'
        curve_data.fill_mode = 'NONE'

        temp_obj = bpy.data.objects.new(name + "_Temp", curve_data)
        bpy.context.scene.collection.objects.link(temp_obj)

        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = temp_obj.evaluated_get(depsgraph)
        mesh_from_eval = bpy.data.meshes.new_from_object(eval_obj)
        mesh_from_eval.name = name

        for v in mesh_from_eval.vertices:
            v.co = Vector((-v.co.x, 0.0, v.co.y))

        bpy.context.scene.collection.objects.unlink(temp_obj)
        bpy.data.objects.remove(temp_obj, do_unlink=True)
        bpy.data.curves.remove(curve_data, do_unlink=True)

        wgt_obj = bpy.data.objects.new(name, mesh_from_eval)
        wgt_coll.objects.link(wgt_obj)
        return wgt_obj
    except Exception:
        s_w = max(1.0, len(text_string) * 0.4)
        s_h = 0.5
        verts = [(-s_w, 0, -s_h), (s_w, 0, -s_h), (s_w, 0, s_h), (-s_w, 0, s_h)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, edges, [])
        wgt_obj = bpy.data.objects.new(name, mesh)
        wgt_coll.objects.link(wgt_obj)
        return wgt_obj


def apply_color(armature, pb, group_name, rgb, cache):
    if not hasattr(pb, "color"):
        return
    pb.color.palette = 'CUSTOM'
    pb.color.custom.normal = rgb
    pb.color.custom.select = (min(1.0, rgb[0] + 0.3), min(1.0, rgb[1] + 0.3), min(1.0, rgb[2] + 0.3))
    pb.color.custom.active = (1.0, 1.0, 1.0)


def purge_previous(armature):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    eb = armature.data.edit_bones

    to_remove = [b.name for b in eb if b.name.startswith("CTRL-") or b.name.startswith("LABEL-") or b.name == "Face-Root"]
    for b_name in to_remove:
        bone = eb.get(b_name)
        if bone:
            eb.remove(bone)
    bpy.ops.object.mode_set(mode='OBJECT')


def plan_hi3_wuwa_controls(face_meshes, armature, head_name):
    fwd, right, up, face_size, fcx = get_face_metrics(face_meshes, armature, head_name)
    OFFSET = face_size * OFFSET_F
    LIM = face_size * TRAVEL_F

    def place(feature, h=0.0, v=0.0):
        return feature + fwd * OFFSET + right * h + up * v

    controls = []
    handled_keys = set()

    # Collect all shape keys across all face meshes
    all_keys = []
    for m in face_meshes:
        if m.data.shape_keys:
            for k in m.data.shape_keys.key_blocks.keys():
                if k.lower() != 'basis':
                    all_keys.append((m, k))

    eye_center = fcx + fwd * 0.02
    mouth = eye_center - up * (face_size * 0.20)
    pos_brow_posX = eye_center + right * 0.040 + up * 0.035
    pos_brow_negX = eye_center - right * 0.040 + up * 0.035
    pos_wink_posX = eye_center + right * 0.040
    pos_wink_negX = eye_center - right * 0.040
    pos_corner_posX = mouth + right * 0.025
    pos_corner_negX = mouth - right * 0.025

    tri_scale = Vector((0.012, 0.012, 0.012))
    brow_scale = Vector((0.020, 0.020, 0.012))
    mouth_scale = Vector((0.022, 0.022, 0.014))
    corner_scale = Vector((0.012, 0.012, 0.012))

    # Helper to find shape keys matching patterns
    def find_key(patterns):
        for pat in patterns:
            for m, k in all_keys:
                if pat.lower() in k.lower() and k not in handled_keys:
                    return m, k
        return None, None

    # Central Eyebrow Controls (WuWa style)
    b_up_m, b_up_k = find_key(["Eyebrow_Smily", "Eyebrow_Happy", "Eyebrow_Angry"])
    b_dn_m, b_dn_k = find_key(["Eyebrow_Serious", "Eyebrow_Sad", "Eyebrow_Trouble"])
    b_drv = []
    if b_up_k:
        b_drv.append({'mesh': b_up_m, 'key': b_up_k, 'axis': 'Z', 'dir': +1})
        handled_keys.add(b_up_k)
    if b_dn_k:
        b_drv.append({'mesh': b_dn_m, 'key': b_dn_k, 'axis': 'Z', 'dir': -1})
        handled_keys.add(b_dn_k)

    controls.append({
        'name': 'CTRL-Eyebrow.L',
        'collection': FACERIG_COLLECTION,
        'color': COL_BROW,
        'group': 'Face Eyebrows',
        'head': place(pos_brow_posX),
        'widget': 'pad',
        'lim': LIM,
        'free': ('Z',),
        'range': 'both',
        'shape_scale': brow_scale,
        'drivers': b_drv
    })
    controls.append({
        'name': 'CTRL-Eyebrow.R',
        'collection': FACERIG_COLLECTION,
        'color': COL_BROW,
        'group': 'Face Eyebrows',
        'head': place(pos_brow_negX),
        'widget': 'pad',
        'lim': LIM,
        'free': ('Z',),
        'range': 'both',
        'shape_scale': brow_scale,
        'drivers': b_drv
    })

    # Central Blink and Winks (WuWa style)
    e_close_m, e_close_k = find_key(["Eye_Half01", "Eye_Half", "Eye_Close", "Eye_Wink"])
    w_drv = []
    if e_close_k:
        w_drv.append({'mesh': e_close_m, 'key': e_close_k, 'axis': 'Z', 'dir': -1})
        handled_keys.add(e_close_k)

    controls.append({
        'name': 'CTRL-Blink',
        'collection': FACERIG_COLLECTION,
        'color': COL_EYELID,
        'group': 'Face Eyelids',
        'head': place(eye_center + up * 0.015),
        'widget': 'isaac_blink_bot',
        'lim': LIM,
        'free': ('Z',),
        'range': 'neg',
        'shape_scale': tri_scale,
        'drivers': w_drv
    })
    controls.append({
        'name': 'CTRL-Eye_Wink.L',
        'collection': FACERIG_COLLECTION,
        'color': COL_EYELID,
        'group': 'Face Eyelids',
        'head': place(pos_wink_posX),
        'widget': 'triangle_down',
        'lim': LIM,
        'free': ('Z',),
        'range': 'neg',
        'shape_scale': tri_scale,
        'drivers': w_drv
    })
    controls.append({
        'name': 'CTRL-Eye_Wink.R',
        'collection': FACERIG_COLLECTION,
        'color': COL_EYELID,
        'group': 'Face Eyelids',
        'head': place(pos_wink_negX),
        'widget': 'triangle_down',
        'lim': LIM,
        'free': ('Z',),
        'range': 'neg',
        'shape_scale': tri_scale,
        'drivers': w_drv
    })

    # Central Mouth Open & Mouth Corners (WuWa style)
    m_open_m, m_open_k = find_key(["Mouth_A01", "Mouth_Open", "Mouth_OpenSmall"])
    m_drv = []
    if m_open_k:
        m_drv.append({'mesh': m_open_m, 'key': m_open_k, 'axis': 'Z', 'dir': -1})
        handled_keys.add(m_open_k)

    controls.append({
        'name': 'CTRL-Mouth_Open',
        'collection': FACERIG_COLLECTION,
        'color': COL_MOUTH,
        'group': 'Face Mouth',
        'head': place(mouth),
        'widget': 'pad',
        'lim': LIM,
        'free': ('Z',),
        'range': 'neg',
        'shape_scale': mouth_scale,
        'drivers': m_drv
    })
    controls.append({
        'name': 'CTRL-Mouth_Corner.L',
        'collection': FACERIG_COLLECTION,
        'color': COL_CORNER,
        'group': 'Face Mouth Corners',
        'head': place(pos_corner_posX),
        'widget': 'triangle',
        'lim': LIM,
        'free': ('Z',),
        'range': 'both',
        'shape_scale': corner_scale,
        'drivers': m_drv
    })
    controls.append({
        'name': 'CTRL-Mouth_Corner.R',
        'collection': FACERIG_COLLECTION,
        'color': COL_CORNER,
        'group': 'Face Mouth Corners',
        'head': place(pos_corner_negX),
        'widget': 'triangle',
        'lim': LIM,
        'free': ('Z',),
        'range': 'both',
        'shape_scale': corner_scale,
        'drivers': m_drv
    })

    # Side Panels (WuWa Side Panels Grid)
    MAX_PER_ROW = 5
    ITEM_SP = 0.045
    ROW_Z_GAP = 0.045

    # Left Panel: Eyebrows & Eyes
    left_origin = eye_center - right * (face_size * 0.65) + up * 0.02
    current_left_v = 0.0

    brow_items = [(m, k) for m, k in all_keys if ("eyebrow" in k.lower() or "brow" in k.lower()) and k not in handled_keys]
    eye_items = [(m, k) for m, k in all_keys if ("eye" in k.lower() and "eyebrow" not in k.lower()) and k not in handled_keys]

    def add_left_grid(items, grp_name, color, label_text):
        nonlocal current_left_v
        if not items:
            return
        controls.append({
            'name': f"LABEL-HI3_{label_text.replace(' ', '_')}",
            'collection': FACERIG_COLLECTION,
            'color': COL_LABEL,
            'group': 'Face Labels',
            'head': place(left_origin, h=0.0, v=current_left_v + face_size * 0.035),
            'widget': f"text:{label_text}",
            'is_label': True,
            'lim': 0.0,
            'free': (),
            'shape_scale': Vector((0.010, 0.010, 0.010)),
            'drivers': []
        })
        for i, (m, k) in enumerate(items):
            handled_keys.add(k)
            row = i // MAX_PER_ROW
            col = i % MAX_PER_ROW
            h = -col * (face_size * ITEM_SP)
            v = current_left_v - row * (face_size * ROW_Z_GAP)
            controls.append({
                'name': f"CTRL-HI3_{k[:18]}",
                'collection': FACERIG_COLLECTION,
                'color': color,
                'group': grp_name,
                'head': place(left_origin, h=h, v=v),
                'widget': 'slider',
                'lim': LIM,
                'free': ('Z',),
                'range': 'pos',
                'shape_scale': Vector((0.012, 0.012, 0.012)),
                'drivers': [{'mesh': m, 'key': k, 'axis': 'Z', 'dir': +1}]
            })
        num_rows = (len(items) + MAX_PER_ROW - 1) // MAX_PER_ROW
        current_left_v -= num_rows * (face_size * ROW_Z_GAP) + (face_size * 0.025)

    add_left_grid(brow_items, 'Face Eyebrows', COL_BROW, "EYEBROWS")
    add_left_grid(eye_items, 'Face Eye Expressions', COL_EYELID, "EYES")

    # Right Panel: Mouth, Visemes & Other
    right_origin = eye_center + right * (face_size * 0.65) + up * 0.02
    current_right_v = 0.0

    mouth_items = [(m, k) for m, k in all_keys if ("mouth" in k.lower() or "viseme" in k.lower()) and k not in handled_keys]
    other_items = [(m, k) for m, k in all_keys if k not in handled_keys]

    def add_right_grid(items, grp_name, color, label_text):
        nonlocal current_right_v
        if not items:
            return
        controls.append({
            'name': f"LABEL-HI3_{label_text.replace(' ', '_')}",
            'collection': FACERIG_COLLECTION,
            'color': COL_LABEL,
            'group': 'Face Labels',
            'head': place(right_origin, h=0.0, v=current_right_v + face_size * 0.035),
            'widget': f"text:{label_text}",
            'is_label': True,
            'lim': 0.0,
            'free': (),
            'shape_scale': Vector((0.010, 0.010, 0.010)),
            'drivers': []
        })
        for i, (m, k) in enumerate(items):
            handled_keys.add(k)
            row = i // MAX_PER_ROW
            col = i % MAX_PER_ROW
            h = col * (face_size * ITEM_SP)
            v = current_right_v - row * (face_size * ROW_Z_GAP)
            controls.append({
                'name': f"CTRL-HI3_{k[:18]}",
                'collection': FACERIG_COLLECTION,
                'color': color,
                'group': grp_name,
                'head': place(right_origin, h=h, v=v),
                'widget': 'slider',
                'lim': LIM,
                'free': ('Z',),
                'range': 'pos',
                'shape_scale': Vector((0.012, 0.012, 0.012)),
                'drivers': [{'mesh': m, 'key': k, 'axis': 'Z', 'dir': +1}]
            })
        num_rows = (len(items) + MAX_PER_ROW - 1) // MAX_PER_ROW
        current_right_v -= num_rows * (face_size * ROW_Z_GAP) + (face_size * 0.025)

    add_right_grid(mouth_items, 'Face Mouth Expressions', COL_EXPRESSION, "MOUTH")
    add_right_grid(other_items, 'Face Other Expressions', COL_PRESET, "OTHER")

    return controls, fwd, up, face_size


def setup_hi3_wuwa_face_rig(face_meshes, controls, armature, head_name, fwd, up, face_size):
    amw_inv = armature.matrix_world.inverted()
    bone_len = face_size * BONE_LEN_F

    def to_arm_point(p):
        return amw_inv @ p

    def to_arm_vec(v):
        return amw_inv.to_3x3() @ v

    fwd_arm = to_arm_vec(fwd).normalized()
    up_arm = to_arm_vec(up).normalized()

    bpy.context.view_layer.objects.active = armature
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')
    eb = armature.data.edit_bones

    root = eb.get("Face-Root") or eb.new("Face-Root")
    head_edit = eb.get(head_name)
    root.head = head_edit.head.copy() if head_edit else Vector((0, 0, 0))
    root.tail = root.head + up_arm * bone_len * 2.0
    root.use_deform = False
    if head_edit:
        root.parent = head_edit

    for c in controls:
        b = eb.get(c['name']) or eb.new(c['name'])
        h = to_arm_point(c['head'])
        b.head = h
        b.tail = h + fwd_arm * bone_len
        b.use_deform = False
        try:
            b.align_roll(up_arm)
        except Exception:
            pass
        b.parent = root
        b.use_connect = False

    bpy.ops.object.mode_set(mode='OBJECT')

    # Bone Collections
    coll_names = [c['collection'] for c in controls if c.get('collection')]
    if not is_blender_3() and hasattr(armature.data, "collections"):
        for cn in set(coll_names):
            coll = armature.data.collections.get(cn) or armature.data.collections.new(cn)
            coll.is_visible = True
            coll.rigify_ui_row = RIGIFY_UI_ROW
        for c in controls:
            bone = armature.data.bones.get(c['name'])
            coll = armature.data.collections.get(c.get('collection', FACERIG_COLLECTION))
            if bone and coll:
                for existing_coll in list(bone.collections):
                    if existing_coll != coll:
                        existing_coll.unassign(bone)
                coll.assign(bone)

        other_coll = armature.data.collections.get("Other") or armature.data.collections.new("Other")
        root_bone = armature.data.bones.get("Face-Root")
        if root_bone and other_coll:
            other_coll.assign(root_bone)

    # Pose mode widgets and constraints
    bpy.ops.object.mode_set(mode='POSE')
    wgt_coll = get_widget_collection()
    color_cache = {}

    for c in controls:
        pb = armature.pose.bones.get(c['name'])
        if not pb:
            continue

        free = c.get('free', ())
        lim = c.get('lim', 0.02)
        rng = c.get('range', 'pos')

        if not c.get('is_label', False):
            for con in list(pb.constraints):
                pb.constraints.remove(con)
            con = pb.constraints.new('LIMIT_LOCATION')
            con.owner_space = 'LOCAL'
            con.use_transform_limit = True
            con.use_min_x = con.use_max_x = True
            con.use_min_y = con.use_max_y = True
            con.use_min_z = con.use_max_z = True
            con.min_y = con.max_y = 0.0

            lo = -lim if rng == 'both' else 0.0
            hi = lim
            if rng == 'neg':
                lo = -lim
                hi = 0.0

            con.min_x = lo if 'X' in free else 0.0
            con.max_x = hi if 'X' in free else 0.0
            con.min_z = lo if 'Z' in free else 0.0
            con.max_z = hi if 'Z' in free else 0.0

        if c['widget'].startswith('text:'):
            text_str = c['widget'].split(':', 1)[1]
            pb.custom_shape = make_text_widget(text_str, wgt_coll)
        else:
            pb.custom_shape = make_widget(c['widget'], wgt_coll)

        try:
            pb.use_custom_shape_bone_size = False
        except Exception:
            pass
        ss = c.get('shape_scale')
        pb.custom_shape_scale_xyz = ss if ss is not None else Vector((c.get('lim', 0.02) * WIDGET_F,) * 3)

        apply_color(armature, pb, c['group'], c['color'], color_cache)

    bpy.ops.object.mode_set(mode='OBJECT')

    # Build Shape Key Drivers on Meshes
    for c in controls:
        for d in c.get('drivers', []):
            mesh = d.get('mesh')
            if not mesh or not mesh.data or not mesh.data.shape_keys:
                continue
            key = d.get('key')
            sk = mesh.data.shape_keys.key_blocks.get(key)
            if not sk:
                continue

            try:
                sk.driver_remove("value")
            except Exception:
                pass
            drv = sk.driver_add("value").driver
            drv.type = 'SCRIPTED'

            var = drv.variables.new()
            var.name = "v0"
            var.type = 'TRANSFORMS'
            tgt = var.targets[0]
            tgt.id = armature
            tgt.bone_target = c['name']
            tgt.transform_type = 'LOC_' + d['axis']
            tgt.transform_space = 'LOCAL_SPACE'

            sign = '' if d['dir'] > 0 else '-'
            lim = c['lim']
            drv.expression = f"max(0.0, {sign}v0 / {lim!r})"
    try:
        wgt_coll.hide_viewport = True
    except Exception:
        pass
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    print(f"[HI3 WUWA FACE RIG] Successfully created {len(controls)} face controls and drivers!")


def hi3_face_rig_main():
    face_meshes = find_face_meshes()
    try:
        armature, head_name = find_armature_and_head(face_meshes)
    except Exception as e:
        print(f"[HI3 Face Rig] Notice: {e}")
        return

    # 1. Import WuWa 3D Face Panel
    import os
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    blend_path = os.path.join(cur_dir, "face_panel_wuwa.blend")
    if os.path.exists(blend_path):
        try:
            from setup_wizard.character_rig_setup.wuwa_face_panel import import_wuwa_face_panel_blend
            faceobj = face_meshes[0] if face_meshes else None
            import_wuwa_face_panel_blend(bpy.context, faceobj, armature, head_name)
            if hasattr(armature.data, 'collections'):
                fc = armature.data.collections.get("Face")
                if fc:
                    fc.is_visible = True
            print("[HI3 FACE RIG] Successfully created face rig using face_panel_wuwa.blend!")
            return
        except Exception as ex:
            print(f"[HI3 FACE RIG] Notice importing blend face panel: {ex}. Falling back to procedural sliders.")

    if not face_meshes:
        print("[HI3 Face Rig] Notice: No mesh with shape keys found for procedural sliders.")
        return

    if CLEAN_REBUILD:
        purge_previous(armature)

    controls, fwd, up, face_size = plan_hi3_wuwa_controls(face_meshes, armature, head_name)
    setup_hi3_wuwa_face_rig(face_meshes, controls, armature, head_name, fwd, up, face_size)
    if hasattr(armature.data, 'collections'):
        fc = armature.data.collections.get("Face")
        if fc:
            fc.is_visible = True


class HI3_OT_SetupFaceRig(bpy.types.Operator):
    bl_idname = "honkai_impact_3rd.setup_face_rig"
    bl_label = "Honkai Impact 3rd: Setup Face Rig"
    bl_description = "Creates a WuWa-style facial rig for Honkai Impact 3rd character"

    def execute(self, context):
        try:
            hi3_face_rig_main()
            self.report({'INFO'}, "Successfully generated HI3 Face Rig!")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to setup HI3 Face Rig: {e}")
            return {'CANCELLED'}


def register():
    bpy.utils.register_class(HI3_OT_SetupFaceRig)


def unregister():
    bpy.utils.unregister_class(HI3_OT_SetupFaceRig)
