# Author: Gacha Setup (HNA Integration via HSR Isaac Face Rig System)
# Isaac / HSR Style Face Rig for Honkai: Nexus Anima Characters
# Creates facial control rig with central face controls and side expression panels

import bpy
import math
from mathutils import Vector, Matrix

HEAD_BONE_NAME = None
CLEAN_REBUILD = True
FLIP_HORIZONTAL = True
FLIP_VERTICAL = False
FLIP_EYE_LR = False

BONE_LEN_F = 0.020
OFFSET_F = 0.120
TRAVEL_F = 0.050
SPACING_F = 0.045
WIDGET_F = 1.0
FACERIG_COLLECTION = "Face"
RIGIFY_UI_ROW = 1

EYE_HL_F = 0.013
TRI_F = 0.022
EMOTE_W_F = 0.011
EMOTE_H_F = 0.006
EMOTE_LIM_F = 0.022
EMOTE_SPACING_F = 0.040
EMOTE_FWD_F = 0.050
MOUTH_SHIFT_F = 0.55
MOUTH_RAISE_F = 0.040

# HSR Isaac Color Palette
COL_MOUTH = (0.90, 0.20, 0.20)
COL_CORNER = (0.15, 0.85, 0.30)
COL_VISEME = (0.95, 0.85, 0.20)
COL_EYELID = (0.90, 0.15, 0.15)
COL_EYEAIM = (0.20, 0.85, 0.90)
COL_EXPRESSION = (0.65, 0.35, 0.90)
COL_LABEL = (0.95, 0.95, 0.95)

HEAD_CANDIDATES = [
    "DEF-spine.006", "spine.006", "head", "Head", "Head_M", "head_M",
    "Bip001 Head", "Bip001_Head", "Bip001Head", "ORG-head"
]


def is_blender_3():
    return bpy.app.version[0] == 3


def find_face_meshes():
    meshes = []
    for obj in bpy.context.view_layer.objects:
        if obj.type == 'MESH' and obj.data and obj.data.shape_keys:
            n = obj.name.lower()
            if any(k in n for k in ["face", "head", "skin", "eye", "mouth", "brow"]) and not any(ign in n for ign in ["weapon", "gun", "sword"]):
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
        raise RuntimeError("No armature found for HNA Face Rig.")

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


def face_frame(mesh_objs, armature=None, head_name=None):
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
        face_size = max(0.18, min(0.35, head_len * 1.5 if head_len > 0.05 else 0.28))
        fcx = head_pos + up * 0.03 + fwd * 0.035
    else:
        face_size = 0.28
        fcx = Vector((0.0, -0.05, 1.45))

    return fwd, right, up, face_size, fcx


def get_widget_collection():
    name = "WGTS_FaceRig_HNA"
    coll = bpy.data.collections.get(name)
    if not coll:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def make_widget(kind, coll):
    name = f"WGT-HNA_{kind}"
    existing = bpy.data.objects.get(name)
    if existing:
        return existing

    if kind == 'pad':
        s = 1.0
        verts = [(-s, 0, -s), (s, 0, -s), (s, 0, s), (-s, 0, s)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
    elif kind == 'slider':
        verts = [(0, 0, -1), (0, 0, 1), (-0.35, 0, 1), (0.35, 0, 1)]
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


def make_text_widget(text_str, coll):
    clean = text_str.replace(' ', '_').replace(':', '_').replace('&', 'AND')
    name = f"WGT-HNA_Text_{clean}"
    existing = bpy.data.objects.get(name)
    if existing:
        return existing

    try:
        curve_data = bpy.data.curves.new(name=name + "_Curve", type='FONT')
        curve_data.body = text_str
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
        coll.objects.link(wgt_obj)
        return wgt_obj
    except Exception:
        s_w = max(1.0, len(text_str) * 0.4)
        s_h = 0.5
        verts = [(-s_w, 0, -s_h), (s_w, 0, -s_h), (s_w, 0, s_h), (-s_w, 0, s_h)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, edges, [])
        wgt_obj = bpy.data.objects.new(name, mesh)
        coll.objects.link(wgt_obj)
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


def plan_hna_isaac_controls(face_meshes, armature, head_name):
    fwd, right, up, face_size, fcx = face_frame(face_meshes, armature, head_name)

    OFFSET = face_size * OFFSET_F
    LIM = face_size * TRAVEL_F

    def place(feature, h=0.0, v=0.0):
        return feature + fwd * OFFSET + right * h + up * v

    controls = []
    handled_keys = set()

    all_keys = []
    for m in face_meshes:
        if m.data.shape_keys:
            for k in m.data.shape_keys.key_blocks.keys():
                if k.lower() != 'basis':
                    all_keys.append((m, k))

    eye_center = fcx + up * (face_size * 0.05)
    mouth = fcx - up * (face_size * 0.12)
    tri_scale = Vector((0.012, 0.012, 0.012))
    mouth_scale = Vector((0.022, 0.022, 0.014))

    # Helper to find shape key
    def find_key(patterns):
        for pat in patterns:
            for m, k in all_keys:
                if pat.lower() in k.lower() and k not in handled_keys:
                    return m, k
        return None, None

    # 1. HSR Isaac Style Direct Face Controls
    # Eye Close
    ec_l_m, ec_l_k = find_key(["EyeClose_L", "Eye_Close_L", "00_Close01_Eye"])
    ec_r_m, ec_r_k = find_key(["EyeClose_R", "Eye_Close_R", "00_Close02_Eye"])
    drv_close = []
    if ec_l_k:
        drv_close.append({'mesh': ec_l_m, 'key': ec_l_k, 'axis': 'Z', 'dir': -1})
        handled_keys.add(ec_l_k)
    if ec_r_k:
        drv_close.append({'mesh': ec_r_m, 'key': ec_r_k, 'axis': 'Z', 'dir': -1})
        handled_keys.add(ec_r_k)

    if drv_close:
        controls.append({
            'name': 'CTRL-Eye_Close',
            'collection': FACERIG_COLLECTION,
            'color': COL_EYELID,
            'group': 'Face Eyelid',
            'head': place(eye_center, v=face_size * 0.04),
            'widget': 'triangle_down',
            'lim': LIM,
            'free': ('Z',),
            'range': 'neg',
            'shape_scale': tri_scale,
            'drivers': drv_close
        })

    # Eye Smile
    es_l_m, es_l_k = find_key(["EyeSmile_L", "Eye_Smile_L", "Smile_Eye"])
    es_r_m, es_r_k = find_key(["EyeSmile_R", "Eye_Smile_R"])
    drv_smile = []
    if es_l_k:
        drv_smile.append({'mesh': es_l_m, 'key': es_l_k, 'axis': 'Z', 'dir': +1})
        handled_keys.add(es_l_k)
    if es_r_k:
        drv_smile.append({'mesh': es_r_m, 'key': es_r_k, 'axis': 'Z', 'dir': +1})
        handled_keys.add(es_r_k)

    if drv_smile:
        controls.append({
            'name': 'CTRL-Eye_Smile',
            'collection': FACERIG_COLLECTION,
            'color': COL_EYELID,
            'group': 'Face Eyelid',
            'head': place(eye_center, v=face_size * 0.08),
            'widget': 'triangle',
            'lim': LIM,
            'free': ('Z',),
            'range': 'pos',
            'shape_scale': tri_scale,
            'drivers': drv_smile
        })

    # Central Mouth Shift / Open
    m_open_m, m_open_k = find_key(["Mouth_Open", "Mouth_A", "Mouth_00_A"])
    drv_m = []
    if m_open_k:
        drv_m.append({'mesh': m_open_m, 'key': m_open_k, 'axis': 'Z', 'dir': -1})
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
        'drivers': drv_m
    })

    # 2. HSR Isaac Side Panels
    MAX_PER_ROW = 12
    ROW_Z_GAP = 0.120
    ITEM_SP = 0.035

    # Left Panel: Eyebrows and Eyes
    left_panel_origin = fcx - right * (face_size * 0.45) + up * (face_size * 0.45)
    current_left_v = 0.0

    brow_keys = [(m, k) for m, k in all_keys if ("brow" in k.lower() or "ebr" in k.lower()) and k not in handled_keys]
    eye_keys = [(m, k) for m, k in all_keys if ("eye" in k.lower() and "brow" not in k.lower()) and k not in handled_keys]

    def add_left_grid(items, grp_name, color, label_text):
        nonlocal current_left_v
        if not items:
            return
        controls.append({
            'name': f"LABEL-HNA_{label_text.replace(' ', '_')}",
            'collection': FACERIG_COLLECTION,
            'color': COL_LABEL,
            'group': 'Face Labels',
            'head': place(left_panel_origin, h=0.0, v=current_left_v + face_size * 0.075),
            'widget': f"text:{label_text}",
            'is_label': True,
            'lim': 0.0,
            'free': (),
            'shape_scale': Vector((0.035, 0.035, 0.035)),
            'drivers': []
        })
        for i, (m, k) in enumerate(items):
            handled_keys.add(k)
            row = i // MAX_PER_ROW
            col = i % MAX_PER_ROW
            h = -col * (face_size * ITEM_SP)
            v = current_left_v - row * (face_size * ROW_Z_GAP)
            controls.append({
                'name': f"CTRL-HNA_{k[:18]}",
                'collection': FACERIG_COLLECTION,
                'color': color,
                'group': grp_name,
                'head': place(left_panel_origin, h=h, v=v),
                'widget': 'slider',
                'lim': LIM,
                'free': ('Z',),
                'range': 'pos',
                'shape_scale': Vector((0.040, 0.040, 0.040)),
                'drivers': [{'mesh': m, 'key': k, 'axis': 'Z', 'dir': +1}]
            })
        num_rows = (len(items) + MAX_PER_ROW - 1) // MAX_PER_ROW
        current_left_v -= num_rows * (face_size * ROW_Z_GAP) + (face_size * 0.01)

    add_left_grid(brow_keys, 'Face Eyebrows', (0.30, 0.80, 0.35), "EYEBROWS")
    add_left_grid(eye_keys, 'Face Eye Expressions', COL_EYEAIM, "EYES")

    # Right Panel: Mouth, Visemes, Expressions & Other
    right_panel_origin = fcx + right * (face_size * 0.45) + up * (face_size * 0.45)
    current_right_v = 0.0

    mouth_keys = [(m, k) for m, k in all_keys if ("mouth" in k.lower() or "viseme" in k.lower()) and k not in handled_keys]
    other_keys = [(m, k) for m, k in all_keys if k not in handled_keys]

    def add_right_grid(items, grp_name, color, label_text):
        nonlocal current_right_v
        if not items:
            return
        controls.append({
            'name': f"LABEL-HNA_{label_text.replace(' ', '_')}",
            'collection': FACERIG_COLLECTION,
            'color': COL_LABEL,
            'group': 'Face Labels',
            'head': place(right_panel_origin, h=0.0, v=current_right_v + face_size * 0.075),
            'widget': f"text:{label_text}",
            'is_label': True,
            'lim': 0.0,
            'free': (),
            'shape_scale': Vector((0.035, 0.035, 0.035)),
            'drivers': []
        })
        for i, (m, k) in enumerate(items):
            handled_keys.add(k)
            row = i // MAX_PER_ROW
            col = i % MAX_PER_ROW
            h = col * (face_size * ITEM_SP)
            v = current_right_v - row * (face_size * ROW_Z_GAP)
            controls.append({
                'name': f"CTRL-HNA_{k[:18]}",
                'collection': FACERIG_COLLECTION,
                'color': color,
                'group': grp_name,
                'head': place(right_panel_origin, h=h, v=v),
                'widget': 'slider',
                'lim': LIM,
                'free': ('Z',),
                'range': 'pos',
                'shape_scale': Vector((0.040, 0.040, 0.040)),
                'drivers': [{'mesh': m, 'key': k, 'axis': 'Z', 'dir': +1}]
            })
        num_rows = (len(items) + MAX_PER_ROW - 1) // MAX_PER_ROW
        current_right_v -= num_rows * (face_size * ROW_Z_GAP) + (face_size * 0.01)

    add_right_grid(mouth_keys, 'Face Mouth', COL_MOUTH, "MOUTH")
    add_right_grid(other_keys, 'Face Expressions', COL_EXPRESSION, "EXPRESSIONS")

    return controls, fwd, up, face_size


def setup_hna_isaac_face_rig(face_meshes, controls, armature, head_name, fwd, up, face_size):
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

    # Collections
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

    # Drivers on Shape Keys
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

    print(f"[HNA ISAAC FACE RIG] Successfully created {len(controls)} face controls and drivers!")


def hna_face_rig_main():
    face_meshes = find_face_meshes()
    if not face_meshes:
        print("[HNA Face Rig] Notice: No mesh with shape keys found.")
        return

    armature, head_name = find_armature_and_head(face_meshes)
    if not armature:
        print("[HNA Face Rig] Notice: No armature found.")
        return

    if CLEAN_REBUILD:
        purge_previous(armature)

    controls, fwd, up, face_size = plan_hna_isaac_controls(face_meshes, armature, head_name)
    setup_hna_isaac_face_rig(face_meshes, controls, armature, head_name, fwd, up, face_size)


class HNA_OT_SetupFaceRig(bpy.types.Operator):
    bl_idname = "honkai_nexus_anima.setup_face_rig"
    bl_label = "Honkai: Nexus Anima: Setup Face Rig"
    bl_description = "Creates an HSR/Isaac style facial rig for Honkai: Nexus Anima character"

    def execute(self, context):
        try:
            hna_face_rig_main()
            self.report({'INFO'}, "Successfully generated HNA Face Rig!")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to setup HNA Face Rig: {e}")
            return {'CANCELLED'}


def register():
    bpy.utils.register_class(HNA_OT_SetupFaceRig)


def unregister():
    bpy.utils.unregister_class(HNA_OT_SetupFaceRig)
