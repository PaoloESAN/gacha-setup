# Author: PaoloESAN
# Face Rig Logic for Wuthering Waves (WuWa)
# Integrates direct facial widgets (Eyes, Brows, Mouth) and structured expression/preset slider panels

import bpy
import math
from mathutils import Vector, Matrix
from bpy.types import Operator

HEAD_BONE_NAME   = None
CLEAN_REBUILD    = True
FLIP_HORIZONTAL  = True
FLIP_VERTICAL    = False
FLIP_EYE_LR      = False

BONE_LEN_F   = 0.060
OFFSET_F     = 0.040
TRAVEL_F     = 0.033
SPACING_F    = 0.050
WIDGET_F     = 1.0
FACERIG_COLLECTION = "Face"
RIGIFY_UI_ROW = 1

# Distinct Color Groups matching standard Gacha Face Rigs
COL_MOUTH      = (0.95, 0.25, 0.25)  # Bright Red / Mouth
COL_CORNER     = (0.95, 0.70, 0.15)  # Amber / Corners
COL_BROW       = (0.25, 0.85, 0.35)  # Green / Eyebrows
COL_EYELID     = (0.20, 0.80, 0.95)  # Sky Blue / Cyan / Eyelids
COL_EXPRESSION = (0.95, 0.30, 0.30)  # Coral / Mouth Expressions
COL_CHEEK      = (0.95, 0.45, 0.75)  # Pink / Rose / Cheek & Nose
COL_PRESET     = (0.75, 0.35, 0.95)  # Purple / Cutscene Presets
COL_VARIATION  = (0.25, 0.60, 0.95)  # Steel Blue / Asymmetry & Variations
COL_LABEL      = (1.00, 1.00, 1.00)  # Pure White / Labels

HEAD_CANDIDATES = [
    "ORG-head", "head", "Head", "Bip001Head", "Bip001-Head", "Bip001 Head", "Bip001_Head",
    "DEF-spine.006", "ORG-spine.006", "spine.006", "Head_M", "head_M", "Bip001 头", "頭", "头",
]


def is_blender_3():
    return bpy.app.version[0] == 3


def find_face_mesh():
    wuwa_signatures = [
        "Pupil_Up", "B_Anger", "B_Happy", "E_Smile_R", "E_Close",
        "M_Smile_R", "Aa", "M_OpenSmall", "S_01", "L_P"
    ]
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data and obj.data.shape_keys:
            kb = obj.data.shape_keys.key_blocks
            if any(sig in kb for sig in wuwa_signatures):
                return obj

    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data and obj.data.shape_keys:
            n = obj.name.lower()
            if any(k in n for k in ["face", "head", "skin", "lod0", "kamola", "phoebe", "shorekeeper", "rover"]):
                if not any(ign in n for ign in ["weapon", "gun", "sword"]):
                    return obj

    for obj in bpy.context.view_layer.objects:
        if obj.type == 'MESH' and obj.data and obj.data.shape_keys:
            return obj

    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data and obj.data.shape_keys:
            return obj

    return None


def find_armature_and_head(mesh_obj):
    armature = None
    for m in mesh_obj.modifiers:
        if m.type == 'ARMATURE' and m.object:
            armature = m.object
            break
    if armature is None:
        for o in bpy.data.objects:
            if o.type == 'ARMATURE' and o.name in bpy.context.view_layer.objects:
                if not any(ign in o.name.lower() for ign in ['metarig', 'backup']):
                    armature = o
                    break
    if armature is None:
        for o in bpy.data.objects:
            if o.type == 'ARMATURE':
                armature = o
                break
    if armature is None:
        raise Exception("No armature found to attach the WuWa face rig to.")

    names = [HEAD_BONE_NAME] if HEAD_BONE_NAME else []
    names += ["ORG-head", "head", "Head", "Bip001Head", "Bip001-Head", "Bip001 Head", "Bip001_Head"] + HEAD_CANDIDATES
    head_name = None
    for cand in names:
        if cand and cand in armature.data.bones:
            head_name = cand
            break
    if head_name is None:
        for b in armature.data.bones:
            if 'head' in b.name.lower() or 'spine.006' in b.name.lower():
                head_name = b.name
                break
    if head_name is None:
        head_name = armature.data.bones[0].name
    return armature, head_name


def get_face_metrics(mesh_obj, armature, head_name):
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


def feature_centroid(mesh_obj, key_names, side=None):
    if not mesh_obj or not mesh_obj.data or not mesh_obj.data.shape_keys:
        return None
    kb = mesh_obj.data.shape_keys.key_blocks
    basis = kb.get("Basis")
    if basis is None or not hasattr(basis, 'data'):
        return None
    key = None
    for kn in key_names:
        if kn in kb:
            key = kb[kn]
            break
    if key is None or not hasattr(key, 'data'):
        return None

    n = len(basis.data)
    deltas = [0.0] * n
    maxd = 0.0
    for i in range(n):
        d = (key.data[i].co - basis.data[i].co).length
        deltas[i] = d
        if d > maxd:
            maxd = d
    if maxd <= 1e-9:
        return None

    thr = maxd * 0.30
    idx = [i for i in range(n) if deltas[i] >= thr]
    if not idx:
        return None

    is_already_single_sided = False
    if key.name:
        kn_low = key.name.lower()
        if "_l" in kn_low or ".l" in kn_low or "left" in kn_low or "_r" in kn_low or ".r" in kn_low or "right" in kn_low:
            is_already_single_sided = True

    if side in ('L', 'R') and not is_already_single_sided:
        xs = sorted(basis.data[i].co.x for i in idx)
        median_x = xs[len(xs) // 2]
        hi = [i for i in idx if basis.data[i].co.x >= median_x]
        lo = [i for i in idx if basis.data[i].co.x < median_x]
        pick = hi if (side == 'L') != FLIP_EYE_LR else lo
        idx = pick or idx

    c = Vector((0.0, 0.0, 0.0))
    for i in idx:
        c += basis.data[i].co
    c /= len(idx)
    return mesh_obj.matrix_world @ c


def pick_primary_key(keyblock, candidates):
    for c in candidates:
        if c in keyblock:
            return c
    return None


def plan_wuwa_controls(mesh_obj, armature, head_name, keyblock):
    fwd, right, up, face_size, fcx = get_face_metrics(mesh_obj, armature, head_name)

    OFFSET  = face_size * OFFSET_F
    LIM     = face_size * TRAVEL_F

    def place(feature, h=0.0, v=0.0):
        return feature + fwd * OFFSET + right * h + up * v

    controls = []
    handled_keys = set()

    for k in keyblock.keys():
        kl = k.lower()
        if kl in ["basis", "default", "rest"] or k.startswith("S_") or k.startswith("s_"):
            handled_keys.add(k)

    # Mark all eye tracking & pupil scaling keys as handled (driven by EyeTracker / Eye.L / Eye.R)
    eye_tracker_keys = [
        "Pupil_Up", "Pupil_Down", "Pupil_L", "Pupil_R", "Pupil_Scale", "E_Blephar",
        "Pupil_Up.L", "Pupil_Up.R", "Pupil_Down.L", "Pupil_Down.R",
        "Pupil_L.L", "Pupil_L.R", "Pupil_R.L", "Pupil_R.R"
    ]
    for k in eye_tracker_keys:
        handled_keys.add(k)

    # -------------------------------------------------------------------------
    # Physical Feature Positions
    # -------------------------------------------------------------------------
    # eye_center is exact midpoint between both eyes
    eye_center = fcx + fwd * 0.02

    # Eyebrows (Positioned directly on the eyebrow arches above eyes)
    pos_brow_posX = eye_center + right * 0.035 + up * 0.035
    pos_brow_negX = eye_center - right * 0.035 + up * 0.035

    # Eyelids / Wink (Positioned on the eyelid contour)
    pos_wink_posX = eye_center + right * 0.035 - up * 0.002
    pos_wink_negX = eye_center - right * 0.035 - up * 0.002

    # Central Blink Position (Between eyes, moves DOWN)
    pos_blink = eye_center + up * 0.012

    # Mouth (Positioned directly on the lip line)
    mouth = eye_center - up * 0.026
    pos_corner_posX = mouth + right * 0.018
    pos_corner_negX = mouth - right * 0.018

    tri_scale = Vector((0.007, 0.007, 0.007))
    brow_scale = Vector((0.016, 0.016, 0.010))
    mouth_scale = Vector((0.018, 0.018, 0.012))
    corner_scale = Vector((0.007, 0.007, 0.007))
    slider_shape_scale = Vector((0.008, 0.008, 0.008))
    label_scale = Vector((0.008, 0.008, 0.008))

    ITEM_SP = 0.016
    ROW_Z_GAP = 0.018
    MAX_PER_ROW = 5

    # =========================================================================
    # 1. DIRECT FACIAL CONTROLS
    # =========================================================================

    # 1.A Central Eye Blink (E_Close / Eye_Close) with triangle_down widget (Moves DOWN)
    close_all = pick_primary_key(keyblock, ["E_Close", "Blink", "Eye_Close", "E_Blephar"])
    if close_all:
        handled_keys.add(close_all)
        controls.append({
            'name': 'CTRL-Eye_Close',
            'collection': FACERIG_COLLECTION,
            'color': COL_EYELID,
            'group': 'Face Eyelid',
            'head': place(pos_blink),
            'widget': 'triangle_down',
            'lim': LIM,
            'free': ('Z',),
            'range': 'neg',
            'shape_scale': Vector((0.008, 0.008, 0.008)),
            'drivers': [{'key': close_all, 'axis': 'Z', 'dir': -1}]
        })

    # 1.B Eye Wink (.L at +X / Viewer Right, .R at -X / Viewer Left)
    smile_l = pick_primary_key(keyblock, ["E_Smile_L", "Smile.L", "E_Wink_L"])
    smile_r = pick_primary_key(keyblock, ["E_Smile_R", "Smile.R", "E_Wink_R"])

    if smile_l:
        handled_keys.add(smile_l)
        controls.append({
            'name': 'CTRL-Eye_Wink.L',
            'collection': FACERIG_COLLECTION,
            'color': COL_EYELID,
            'group': 'Face Eyelid',
            'head': place(pos_wink_posX),
            'widget': 'isaac_blink_bot',
            'lim': LIM,
            'free': ('Z',),
            'range': 'pos',
            'shape_scale': tri_scale,
            'drivers': [{'key': smile_l, 'axis': 'Z', 'dir': +1}]
        })

    if smile_r:
        handled_keys.add(smile_r)
        controls.append({
            'name': 'CTRL-Eye_Wink.R',
            'collection': FACERIG_COLLECTION,
            'color': COL_EYELID,
            'group': 'Face Eyelid',
            'head': place(pos_wink_negX),
            'widget': 'isaac_blink_bot',
            'lim': LIM,
            'free': ('Z',),
            'range': 'pos',
            'shape_scale': tri_scale,
            'drivers': [{'key': smile_r, 'axis': 'Z', 'dir': +1}]
        })

    # 1.C Eyebrows Direct (.L at +X / Viewer Right, .R at -X / Viewer Left)
    brow_up = pick_primary_key(keyblock, ["B_Up_Add", "EB_Up"])
    brow_down = pick_primary_key(keyblock, ["B_Down_Add", "EB_Down"])
    brow_ah_l = pick_primary_key(keyblock, ["B_AH_L"])
    brow_ah_r = pick_primary_key(keyblock, ["B_AH_R"])

    bdrv_L = []
    if brow_up:
        bdrv_L.append({'key': brow_up, 'axis': 'Z', 'dir': +1})
        handled_keys.add(brow_up)
    if brow_down:
        bdrv_L.append({'key': brow_down, 'axis': 'Z', 'dir': -1})
        handled_keys.add(brow_down)
    if brow_ah_l:
        bdrv_L.append({'key': brow_ah_l, 'axis': 'X', 'dir': +1})
        handled_keys.add(brow_ah_l)

    if bdrv_L:
        controls.append({
            'name': 'CTRL-Brow.L',
            'collection': FACERIG_COLLECTION,
            'color': COL_BROW,
            'group': 'Face Eyebrow',
            'head': place(pos_brow_posX),
            'widget': 'eyeblink',
            'lim': LIM,
            'free': ('X', 'Z'),
            'range': 'both',
            'shape_scale': brow_scale,
            'drivers': bdrv_L
        })

    bdrv_R = []
    if brow_up:
        bdrv_R.append({'key': brow_up, 'axis': 'Z', 'dir': +1})
    if brow_down:
        bdrv_R.append({'key': brow_down, 'axis': 'Z', 'dir': -1})
    if brow_ah_r:
        bdrv_R.append({'key': brow_ah_r, 'axis': 'X', 'dir': -1})
        handled_keys.add(brow_ah_r)

    if bdrv_R:
        controls.append({
            'name': 'CTRL-Brow.R',
            'collection': FACERIG_COLLECTION,
            'color': COL_BROW,
            'group': 'Face Eyebrow',
            'head': place(pos_brow_negX),
            'widget': 'eyeblink',
            'lim': LIM,
            'free': ('X', 'Z'),
            'range': 'both',
            'shape_scale': brow_scale,
            'drivers': bdrv_R
        })

    # 1.D Mouth Smile / Ennui Keys
    m_smile_l = pick_primary_key(keyblock, ["M_Smile_L"])
    m_smile_r = pick_primary_key(keyblock, ["M_Smile_R"])
    m_ennui_l = pick_primary_key(keyblock, ["M_Ennui_L"])
    m_ennui_r = pick_primary_key(keyblock, ["M_Ennui_R"])

    if m_smile_l: handled_keys.add(m_smile_l)
    if m_smile_r: handled_keys.add(m_smile_r)
    if m_ennui_l: handled_keys.add(m_ennui_l)
    if m_ennui_r: handled_keys.add(m_ennui_r)

    # 1.E Mouth Shift Pad (Rectangular pad for P_M_* Mouth Shifts / Transforms)
    pm_up = pick_primary_key(keyblock, ["P_M_Up_Add", "P_M_U_Add", "P_M_Up", "P_M_U"])
    pm_down = pick_primary_key(keyblock, ["P_M_Down_Add", "P_M_D_Add", "P_M_Down", "P_M_D"])
    pm_right = pick_primary_key(keyblock, ["P_M_RMove_Add", "P_M_R_Add", "P_M_Right_Add", "P_M_R"])
    pm_left = pick_primary_key(keyblock, ["P_M_LMove_Add", "P_M_L_Add", "P_M_Left_Add", "P_M_L"])

    pm_drv = []
    # Up (+Z)
    if pm_up:
        pm_drv.append({'key': pm_up, 'axis': 'Z', 'dir': +1})
        handled_keys.add(pm_up)
    elif m_smile_l and m_smile_r:
        pm_drv.append({'key': m_smile_l, 'axis': 'Z', 'dir': +1})
        pm_drv.append({'key': m_smile_r, 'axis': 'Z', 'dir': +1})

    # Down (-Z)
    if pm_down:
        pm_drv.append({'key': pm_down, 'axis': 'Z', 'dir': -1})
        handled_keys.add(pm_down)
    elif m_ennui_l and m_ennui_r:
        pm_drv.append({'key': m_ennui_l, 'axis': 'Z', 'dir': -1})
        pm_drv.append({'key': m_ennui_r, 'axis': 'Z', 'dir': -1})

    # Right (+X)
    if pm_right:
        pm_drv.append({'key': pm_right, 'axis': 'X', 'dir': +1})
        handled_keys.add(pm_right)
    elif m_smile_r:
        pm_drv.append({'key': m_smile_r, 'axis': 'X', 'dir': +1})

    # Left (-X)
    if pm_left:
        pm_drv.append({'key': pm_left, 'axis': 'X', 'dir': -1})
        handled_keys.add(pm_left)
    elif m_smile_l:
        pm_drv.append({'key': m_smile_l, 'axis': 'X', 'dir': -1})

    if pm_drv:
        controls.append({
            'name': 'CTRL-Mouth_Shift',
            'collection': FACERIG_COLLECTION,
            'color': COL_CORNER,
            'group': 'Face Mouth Shifts',
            'head': place(mouth),
            'widget': 'pad',
            'lim': LIM,
            'free': ('X', 'Z'),
            'range': 'both',
            'shape_scale': Vector((0.016, 0.016, 0.010)),
            'drivers': pm_drv
        })

    # 1.F Mouth Vowels 2D Pad (Aa / A / M_A, E, I, O / M_O, U)
    vow_a = pick_primary_key(keyblock, ["Aa", "A", "M_A"])
    vow_e = pick_primary_key(keyblock, ["E"])
    vow_i = pick_primary_key(keyblock, ["I"])
    vow_o = pick_primary_key(keyblock, ["O", "M_O"])
    vow_u = pick_primary_key(keyblock, ["U"])

    m_pad_drv = []
    if vow_a:
        m_pad_drv.append({'key': vow_a, 'axis': 'Z', 'dir': +1})
        handled_keys.add(vow_a)
    if vow_u:
        m_pad_drv.append({'key': vow_u, 'axis': 'Z', 'dir': -1})
        handled_keys.add(vow_u)
    if vow_e:
        m_pad_drv.append({'key': vow_e, 'axis': 'X', 'dir': -1})
        handled_keys.add(vow_e)
    if vow_i:
        m_pad_drv.append({'key': vow_i, 'axis': 'X', 'dir': +1})
        handled_keys.add(vow_i)
    if vow_o and vow_o not in handled_keys:
        m_pad_drv.append({'key': vow_o, 'axis': 'Z', 'dir': -1})
        handled_keys.add(vow_o)

    if m_pad_drv:
        controls.append({
            'name': 'CTRL-Mouth',
            'collection': FACERIG_COLLECTION,
            'color': COL_MOUTH,
            'group': 'Face Mouth',
            'head': place(mouth),
            'widget': 'lipsmaster',
            'lim': LIM,
            'free': ('X', 'Z'),
            'range': 'both',
            'shape_scale': mouth_scale,
            'drivers': m_pad_drv
        })

    # 1.G Mouth Corner Triangles (.L at +X / Viewer Right, .R at -X / Viewer Left)
    c_drv_L = []
    if m_smile_l: c_drv_L.append({'key': m_smile_l, 'axis': 'Z', 'dir': +1})
    if m_ennui_l: c_drv_L.append({'key': m_ennui_l, 'axis': 'Z', 'dir': -1})

    if c_drv_L:
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
            'drivers': c_drv_L
        })

    c_drv_R = []
    if m_smile_r: c_drv_R.append({'key': m_smile_r, 'axis': 'Z', 'dir': +1})
    if m_ennui_r: c_drv_R.append({'key': m_ennui_r, 'axis': 'Z', 'dir': -1})

    if c_drv_R:
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
            'drivers': c_drv_R
        })

    # =========================================================================
    # 2. SIDE PANELS: EXPRESSIONS & CUSTOM SHAPEKEYS
    # =========================================================================

    # -------------------------------------------------------------------------
    # LEFT PANEL (-right side: Eyebrows, Eye Expressions)
    # -------------------------------------------------------------------------
    left_panel_origin = eye_center - right * (face_size * 0.65) + up * 0.010
    current_left_v = 0.0

    def add_left_panel_grid(items_list, group_name, color, widget_type='slider'):
        nonlocal current_left_v
        if not items_list:
            return
        total = len(items_list)
        for i, item in enumerate(items_list):
            if isinstance(item, tuple):
                c_name, drv_list = item[0], item[1]
            else:
                c_name = item.get('name') if isinstance(item, dict) else f"CTRL-{item}"
                drv_list = item.get('drivers') if isinstance(item, dict) else [{'key': item, 'axis': 'Z', 'dir': +1}]
                if isinstance(item, str):
                    handled_keys.add(item)

            row_idx = i // MAX_PER_ROW
            col_idx = i % MAX_PER_ROW

            h = -col_idx * ITEM_SP
            v = current_left_v - row_idx * ROW_Z_GAP

            controls.append({
                'name': c_name,
                'collection': FACERIG_COLLECTION,
                'color': color,
                'group': group_name,
                'head': place(left_panel_origin, h=h, v=v),
                'widget': widget_type,
                'lim': LIM,
                'free': ('Z',),
                'range': 'pos',
                'shape_scale': slider_shape_scale,
                'drivers': drv_list
            })

        num_rows = (total + MAX_PER_ROW - 1) // MAX_PER_ROW
        current_left_v -= num_rows * ROW_Z_GAP + 0.008

    # 2.A Eyebrows Grid (B_*)
    eb_keys = [k for k in ["B_Anger", "B_Happy", "B_Cheerful", "B_Sad", "B_Flat", "B_Inside_Add"] if k in keyblock and k not in handled_keys]
    if eb_keys:
        eb_items = []
        for k in eb_keys:
            c_name = f"CTRL-{k}"
            handled_keys.add(k)
            eb_items.append((c_name, [{'key': k, 'axis': 'Z', 'dir': +1}]))
        add_left_panel_grid(eb_items, 'Face Eyebrows', COL_BROW)

    # 2.B Eye Expressions Grid (E_*)
    el_keys = [k for k in ["E_Anger", "E_Sad", "E_Focus", "E_Insipid", "E_Stare"] if k in keyblock and k not in handled_keys]
    if el_keys:
        el_items = []
        for k in el_keys:
            c_name = f"CTRL-{k}"
            handled_keys.add(k)
            el_items.append((c_name, [{'key': k, 'axis': 'Z', 'dir': +1}]))
        add_left_panel_grid(el_items, 'Face Eye Expressions', COL_EYELID)

    # Add Left Panel Header Label
    controls.append({
        'name': 'LABEL-Brows_Eyes',
        'collection': FACERIG_COLLECTION,
        'color': COL_LABEL,
        'group': 'Face Labels',
        'head': place(left_panel_origin, h=-2.0 * ITEM_SP, v=0.016),
        'widget': 'text:BROWS & EYES',
        'lim': 0.0,
        'free': (),
        'range': 'pos',
        'shape_scale': label_scale,
        'is_label': True,
        'drivers': []
    })

    # -------------------------------------------------------------------------
    # RIGHT PANEL (+right side: Mouth Expressions, Cheek & Nose, Variations)
    # -------------------------------------------------------------------------
    right_panel_origin = eye_center + right * (face_size * 0.65) + up * 0.010
    current_right_v_col1 = 0.0
    current_right_v_col2 = 0.0
    col2_offset = 0.105

    def add_right_panel_grid(items_list, group_name, color, widget_type='slider', is_col2=False):
        nonlocal current_right_v_col1, current_right_v_col2
        if not items_list:
            return
        col_offset = col2_offset if is_col2 else 0.0
        v_base = current_right_v_col2 if is_col2 else current_right_v_col1

        total = len(items_list)
        for i, item in enumerate(items_list):
            if isinstance(item, tuple):
                c_name, drv_list = item[0], item[1]
            else:
                c_name = item.get('name') if isinstance(item, dict) else f"CTRL-{item}"
                drv_list = item.get('drivers') if isinstance(item, dict) else [{'key': item, 'axis': 'Z', 'dir': +1}]
                if isinstance(item, str):
                    handled_keys.add(item)

            row_idx = i // MAX_PER_ROW
            col_idx = i % MAX_PER_ROW

            h = col_idx * ITEM_SP + col_offset
            v = v_base - row_idx * ROW_Z_GAP

            controls.append({
                'name': c_name,
                'collection': FACERIG_COLLECTION,
                'color': color,
                'group': group_name,
                'head': place(right_panel_origin, h=h, v=v),
                'widget': widget_type,
                'lim': LIM,
                'free': ('Z',),
                'range': 'pos',
                'shape_scale': slider_shape_scale,
                'drivers': drv_list
            })

        num_rows = (total + MAX_PER_ROW - 1) // MAX_PER_ROW
        v_drop = num_rows * ROW_Z_GAP + 0.008
        if is_col2:
            current_right_v_col2 -= v_drop
        else:
            current_right_v_col1 -= v_drop

    # 2.D Mouth Expressions Grid (M_OpenSmall, M_Laugh, M_Scared, M_ScaredTooth, M_Anger, M_Trapezoid, M_Nutcracker)
    m_exp_keys = [k for k in ["M_OpenSmall", "M_Laugh", "M_Scared", "M_ScaredTooth", "M_Anger", "M_Trapezoid", "M_Nutcracker"] if k in keyblock and k not in handled_keys]
    if m_exp_keys:
        m_items = []
        for k in m_exp_keys:
            c_name = f"CTRL-{k}"
            handled_keys.add(k)
            m_items.append((c_name, [{'key': k, 'axis': 'Z', 'dir': +1}]))
        add_right_panel_grid(m_items, 'Face Mouth Expressions', COL_EXPRESSION, is_col2=False)

    # 2.E Cheek & Nose Grid (C_*, P_Nose_*)
    cheek_keys = [k for k in keyblock.keys() if (k.startswith("C_") or k.startswith("P_Nose_")) and k not in handled_keys]
    cheek_keys.sort()
    if cheek_keys:
        ch_items = []
        for k in cheek_keys:
            c_name = f"CTRL-{k}"
            handled_keys.add(k)
            ch_items.append((c_name, [{'key': k, 'axis': 'Z', 'dir': +1}]))
        add_right_panel_grid(ch_items, 'Face Cheek & Nose', COL_CHEEK, is_col2=False)

    # 2.F Asymmetric Variations & Eye-Look Details (L_*, R_*)
    var_keys = [k for k in keyblock.keys() if (k.startswith("L_") or k.startswith("R_")) and k not in handled_keys]
    var_keys.sort()
    if var_keys:
        var_items = []
        for k in var_keys:
            c_name = f"CTRL-{k}"
            handled_keys.add(k)
            var_items.append((c_name, [{'key': k, 'axis': 'Z', 'dir': +1}]))
        add_right_panel_grid(var_items, 'Face Asymmetry & Variations', COL_VARIATION, is_col2=True)

    # 2.G Any other unhandled shapekeys
    remaining_keys = [k for k in keyblock.keys() if k not in handled_keys]
    remaining_keys.sort()
    if remaining_keys:
        rem_items = []
        for k in remaining_keys:
            c_name = f"CTRL-{k}"
            handled_keys.add(k)
            rem_items.append((c_name, [{'key': k, 'axis': 'Z', 'dir': +1}]))
        add_right_panel_grid(rem_items, 'Face Other Expressions', COL_CHEEK, is_col2=True)

    # Add Right Panel Header Labels
    controls.append({
        'name': 'LABEL-Mouth_Face',
        'collection': FACERIG_COLLECTION,
        'color': COL_LABEL,
        'group': 'Face Labels',
        'head': place(right_panel_origin, h=2.0 * ITEM_SP, v=0.016),
        'widget': 'text:MOUTH & FACE',
        'lim': 0.0,
        'free': (),
        'range': 'pos',
        'shape_scale': label_scale,
        'is_label': True,
        'drivers': []
    })

    if var_keys or remaining_keys:
        controls.append({
            'name': 'LABEL-Variations',
            'collection': FACERIG_COLLECTION,
            'color': COL_LABEL,
            'group': 'Face Labels',
            'head': place(right_panel_origin, h=col2_offset + 2.0 * ITEM_SP, v=0.016),
            'widget': 'text:VARIATIONS & ASYMMETRY',
            'lim': 0.0,
            'free': (),
            'range': 'pos',
            'shape_scale': label_scale,
            'is_label': True,
            'drivers': []
        })

    return controls


# =============================================================================
# WIDGET GEOMETRY DEFINITIONS
# =============================================================================

EYE_MASTER_VERTS = [[-0.40348, 0.0, 0.32632], [-0.28803, 0.0, 0.29715], [-0.21194, 0.0, 0.24992], [0.0, 0.0, -0.19968], [0.0, 0.0, 0.19968], [-0.21194, 0.0, -0.24992], [-0.28803, 0.0, -0.29715], [-0.40348, 0.0, -0.32632], [-0.53133, 0.0, -0.31136], [-0.64684, 0.0, -0.24534], [-0.72806, 0.0, -0.13551], [-0.7574, 0.0, 0.0], [-0.72806, 0.0, 0.13551], [-0.64684, 0.0, 0.24534], [-0.53133, 0.0, 0.31136], [-0.11372, 0.0, 0.1995], [-0.11372, 0.0, -0.1995], [-0.03778, 0.0, -0.19971], [-0.03778, 0.0, 0.19971], [-0.16207, 0.0, 0.20723], [-0.16207, 0.0, -0.20723], [-0.34203, 0.0, 0.3157], [-0.24529, 0.0, 0.2746], [-0.0037, 0.0, -0.19969], [-0.07706, 0.0, 0.1997], [-0.24529, 0.0, -0.2746], [-0.34203, 0.0, -0.3157], [-0.4676, 0.0, -0.32523], [-0.59202, 0.0, -0.28451], [-0.693, 0.0, -0.19498], [-0.74991, 0.0, -0.06945], [-0.74991, 0.0, 0.06945], [-0.693, 0.0, 0.19498], [-0.59202, 0.0, 0.28451], [-0.4676, 0.0, 0.32523], [-0.18492, 0.0, 0.22542], [-0.07706, 0.0, -0.1997], [-0.0037, 0.0, 0.19969], [-0.14053, 0.0, -0.20011], [-0.14053, 0.0, 0.20011], [-0.18492, 0.0, -0.22542], [0.40348, 0.0, 0.32632], [0.28803, 0.0, 0.29715], [0.21194, 0.0, 0.24992], [-0.0, 0.0, -0.19968], [-0.0, 0.0, 0.19968], [0.21194, 0.0, -0.24992], [0.28803, 0.0, -0.29715], [0.40348, 0.0, -0.32632], [0.53133, 0.0, -0.31136], [0.64684, 0.0, -0.24534], [0.72806, 0.0, -0.13551], [0.7574, 0.0, 0.0], [0.72806, 0.0, 0.13551], [0.64684, 0.0, 0.24534], [0.53133, 0.0, 0.31136], [0.11372, 0.0, 0.1995], [0.11372, 0.0, -0.1995], [0.03778, 0.0, -0.19971], [0.03778, 0.0, 0.19971], [0.16207, 0.0, 0.20723], [0.16207, 0.0, -0.20723], [0.34203, 0.0, 0.3157], [0.24529, 0.0, 0.2746], [0.0037, 0.0, -0.19969], [0.07706, 0.0, 0.1997], [0.24529, 0.0, -0.2746], [0.34203, 0.0, -0.3157], [0.4676, 0.0, -0.32523], [0.59202, 0.0, -0.28451], [0.693, 0.0, -0.19498], [0.74991, 0.0, -0.06945], [0.74991, 0.0, 0.06945], [0.693, 0.0, 0.19498], [0.59202, 0.0, 0.28451], [0.4676, 0.0, 0.32523], [0.18492, 0.0, 0.22542], [0.07706, 0.0, -0.1997], [0.0037, 0.0, 0.19969], [0.14053, 0.0, -0.20011], [0.14053, 0.0, 0.20011], [0.18492, 0.0, -0.22542]]
EYE_MASTER_EDGES = [[1, 21], [0, 21], [2, 22], [1, 22], [17, 23], [3, 23], [18, 24], [15, 24], [6, 25], [5, 25], [7, 26], [6, 26], [8, 27], [7, 27], [9, 28], [8, 28], [10, 29], [9, 29], [11, 30], [10, 30], [12, 31], [11, 31], [13, 32], [12, 32], [14, 33], [13, 33], [0, 34], [14, 34], [19, 35], [2, 35], [16, 36], [17, 36], [4, 37], [18, 37], [20, 38], [16, 38], [15, 39], [19, 39], [5, 40], [20, 40], [42, 62], [41, 62], [43, 63], [42, 63], [58, 64], [44, 64], [59, 65], [56, 65], [47, 66], [46, 66], [48, 67], [47, 67], [49, 68], [48, 68], [50, 69], [49, 69], [51, 70], [50, 70], [52, 71], [51, 71], [53, 72], [52, 72], [54, 73], [53, 73], [55, 74], [54, 74], [41, 75], [55, 75], [60, 76], [43, 76], [57, 77], [58, 77], [45, 78], [59, 78], [61, 79], [57, 79], [56, 80], [60, 80], [46, 81], [61, 81]]
EYE_CIRCLE_VERTS = [[0.0, 0.0, 0.5], [-0.09755, 0.0, 0.49039], [-0.19134, 0.0, 0.46194], [-0.27779, 0.0, 0.41574], [-0.35355, 0.0, 0.35355], [-0.41574, 0.0, 0.27779], [-0.46194, 0.0, 0.19134], [-0.49039, 0.0, 0.09755], [-0.5, 0.0, -0.0], [-0.49039, 0.0, -0.09755], [-0.46194, 0.0, -0.19134], [-0.41574, 0.0, -0.27779], [-0.35355, 0.0, -0.35355], [-0.27779, 0.0, -0.41574], [-0.19134, 0.0, -0.46194], [-0.09755, 0.0, -0.49039], [0.0, 0.0, -0.5], [0.09755, 0.0, -0.49039], [0.19134, 0.0, -0.46194], [0.27779, 0.0, -0.41574], [0.35355, 0.0, -0.35355], [0.41574, 0.0, -0.27779], [0.46194, 0.0, -0.19134], [0.49039, 0.0, -0.09755], [0.5, 0.0, 0.0], [0.49039, 0.0, 0.09755], [0.46194, 0.0, 0.19134], [0.41573, 0.0, 0.27779], [0.35355, 0.0, 0.35355], [0.27779, 0.0, 0.41574], [0.19134, 0.0, 0.46194], [0.09754, 0.0, 0.49039]]
EYE_CIRCLE_EDGES = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10], [10, 11], [11, 12], [12, 13], [13, 14], [14, 15], [15, 16], [16, 17], [17, 18], [18, 19], [19, 20], [20, 21], [21, 22], [22, 23], [23, 24], [24, 25], [25, 26], [26, 27], [27, 28], [28, 29], [29, 30], [30, 31], [0, 31]]
LIPS_MASTER_VERTS = [[0.0, 0.19233, 0.11033], [0.13499, 0.18609, 0.10769], [0.2648, 0.15671, 0.10386], [0.38443, 0.10515, 0.09906], [0.48929, 0.03669, 0.09225], [0.57534, -0.04048, 0.08167], [0.63928, -0.11576, 0.0649], [0.67866, -0.17692, 0.03916], [0.69195, -0.21104, 0.00157], [0.67866, -0.20938, -0.04918], [0.63928, -0.17943, -0.10838], [0.57534, -0.13291, -0.1699], [0.48929, -0.08096, -0.22793], [0.38443, -0.03318, -0.27744], [0.2648, 0.00301, -0.31449], [0.13499, 0.02292, -0.33643], [-0.0, 0.02596, -0.34248], [-0.135, 0.02292, -0.33643], [-0.2648, 0.00301, -0.31449], [-0.38443, -0.03318, -0.27744], [-0.48929, -0.08096, -0.22793], [-0.57534, -0.13291, -0.1699], [-0.63928, -0.17943, -0.10838], [-0.67866, -0.20938, -0.04917], [-0.69195, -0.21104, 0.00157], [-0.67866, -0.17692, 0.03916], [-0.63928, -0.11576, 0.0649], [-0.57534, -0.04048, 0.08167], [-0.48928, 0.03669, 0.09225], [-0.38442, 0.10515, 0.09906], [-0.26479, 0.15671, 0.10386], [-0.13499, 0.1861, 0.10769]]
LIPS_MASTER_EDGES = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10], [10, 11], [11, 12], [12, 13], [13, 14], [14, 15], [15, 16], [16, 17], [17, 18], [18, 19], [19, 20], [20, 21], [21, 22], [22, 23], [23, 24], [24, 25], [25, 26], [26, 27], [27, 28], [28, 29], [29, 30], [30, 31], [0, 31]]
EYEBLINK_VERTS = [[-0.42167, 0.0, -0.22917], [0.42167, 0.0, -0.22917], [-0.42167, -0.0, 0.22917], [0.42167, -0.0, 0.22917], [0.46, 0.0, -0.125], [0.46, 0.0, -0.0], [0.46, -0.0, 0.125], [-0.23, 0.0, -0.25], [-0.0, 0.0, -0.25], [0.23, 0.0, -0.25], [-0.46, 0.0, -0.125], [-0.46, -0.0, 0.0], [-0.46, -0.0, 0.125], [-0.23, -0.0, 0.25], [0.0, -0.0, 0.25], [0.23, -0.0, 0.25], [0.4594, -0.0, 0.15592], [0.45521, -0.0, 0.1849], [0.44383, -0.0, 0.20996], [0.2869, 0.0, -0.24968], [0.34021, 0.0, -0.2474], [0.38633, 0.0, -0.24121], [-0.4594, -0.0, 0.15592], [-0.45521, -0.0, 0.1849], [-0.44383, -0.0, 0.20996], [0.2869, -0.0, 0.24968], [0.34021, -0.0, 0.2474], [0.38633, -0.0, 0.24121], [0.44383, 0.0, -0.20996], [0.45521, 0.0, -0.1849], [0.4594, 0.0, -0.15592], [0.46, 0.0, -0.0625], [0.46, -0.0, 0.0625], [-0.38633, 0.0, -0.24121], [-0.34021, 0.0, -0.2474], [-0.2869, 0.0, -0.24967], [-0.115, 0.0, -0.25], [0.115, 0.0, -0.25], [-0.44383, 0.0, -0.20996], [-0.45521, 0.0, -0.1849], [-0.4594, 0.0, -0.15592], [-0.46, 0.0, -0.0625], [-0.46, -0.0, 0.0625], [-0.38633, -0.0, 0.24121], [-0.34021, -0.0, 0.2474], [-0.2869, -0.0, 0.24967], [-0.115, -0.0, 0.25], [0.115, -0.0, 0.25], [-0.39485, -0.00338, -0.20822], [0.39485, 0.00338, -0.20822], [-0.39485, -0.00338, 0.20822], [0.39485, 0.00338, 0.20822], [0.43075, 0.00369, -0.11357], [0.43075, 0.00369, 0.11358], [-0.43075, -0.00369, -0.11357], [-0.43075, -0.00369, 0.11358], [0.43018, 0.00368, 0.14167], [0.42626, 0.00365, 0.168], [0.4156, 0.00356, 0.19077], [0.31857, 0.00273, -0.22478], [0.36176, 0.0031, -0.21916], [-0.43018, -0.00368, 0.14167], [-0.42626, -0.00365, 0.168], [-0.4156, -0.00356, 0.19077], [0.31857, 0.00273, 0.22479], [0.36176, 0.0031, 0.21917], [0.4156, 0.00356, -0.19077], [0.42626, 0.00365, -0.16799], [0.43018, 0.00368, -0.14167], [-0.36176, -0.0031, -0.21916], [-0.31857, -0.00273, -0.22478], [-0.4156, -0.00356, -0.19077], [-0.42626, -0.00365, -0.16799], [-0.43018, -0.00368, -0.14167], [-0.36176, -0.0031, 0.21917], [-0.31857, -0.00273, 0.22479]]
EYEBLINK_EDGES = [[6, 16], [16, 17], [17, 18], [3, 18], [9, 19], [19, 20], [20, 21], [1, 21], [12, 22], [22, 23], [23, 24], [2, 24], [15, 25], [25, 26], [26, 27], [3, 27], [1, 28], [28, 29], [29, 30], [4, 30], [4, 31], [5, 31], [5, 32], [6, 32], [0, 33], [33, 34], [34, 35], [7, 35], [7, 36], [8, 36], [8, 37], [9, 37], [0, 38], [38, 39], [39, 40], [10, 40], [10, 41], [11, 41], [11, 42], [12, 42], [2, 43], [43, 44], [44, 45], [13, 45], [13, 46], [14, 46], [14, 47], [15, 47], [53, 56], [56, 57], [57, 58], [51, 58], [59, 60], [49, 60], [55, 61], [61, 62], [62, 63], [50, 63], [64, 65], [51, 65], [49, 66], [66, 67], [67, 68], [52, 68], [48, 69], [69, 70], [48, 71], [71, 72], [72, 73], [54, 73], [50, 74], [74, 75]]
ISAAC_BLINK_TOP_VERTS = [[1.0, 0.0, 0.5638], [-1.0, 0.0, 0.5638], [-0.0, 0.0, 0.8878], [-0.0, 0.0, -0.484], [-0.5916, 0.0, -0.0569], [0.5916, 0.0, -0.0569], [0.6306, 0.0, 0.8199], [-0.6306, 0.0, 0.8199], [-1.0, 0.0, 0.5638], [-0.0, 0.0, -0.484], [1.0, 0.0, 0.5638]]
ISAAC_BLINK_TOP_EDGES = [[7, 1], [4, 1], [3, 4], [6, 2], [5, 3], [0, 5], [0, 6], [2, 7], [1, 8], [3, 9], [0, 10]]
ISAAC_BLINK_BOT_VERTS = [[-1.0, 0.0, -0.5638], [1.0, 0.0, -0.5638], [0.0, 0.0, -0.8878], [0.0, 0.0, 0.484], [0.5916, 0.0, 0.0569], [-0.5916, 0.0, 0.0569], [-0.6306, 0.0, -0.8199], [0.6306, 0.0, -0.8199], [1.0, 0.0, -0.5638], [0.0, 0.0, 0.484], [-1.0, 0.0, -0.5638]]
ISAAC_BLINK_BOT_EDGES = [[7, 1], [4, 1], [3, 4], [6, 2], [5, 3], [0, 5], [0, 6], [2, 7], [1, 8], [3, 9], [0, 10]]


def make_widget(kind, coll):
    name = "WGT-Face_" + kind
    obj = bpy.data.objects.get(name)
    if obj:
        return obj
    if kind == 'isaac_blink_top':
        verts = ISAAC_BLINK_TOP_VERTS
        edges = ISAAC_BLINK_TOP_EDGES
    elif kind == 'isaac_blink_bot':
        verts = ISAAC_BLINK_BOT_VERTS
        edges = ISAAC_BLINK_BOT_EDGES
    elif kind == 'lipsmaster':
        verts = LIPS_MASTER_VERTS
        edges = LIPS_MASTER_EDGES
    elif kind == 'eyeblink':
        verts = EYEBLINK_VERTS
        edges = EYEBLINK_EDGES
    elif kind == 'eyemaster':
        verts = EYE_MASTER_VERTS
        edges = EYE_MASTER_EDGES
    elif kind == 'eyecircle':
        verts = EYE_CIRCLE_VERTS
        edges = EYE_CIRCLE_EDGES
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
        verts, edges = [(0, 0, 0)], []

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, [])
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def make_text_widget(text_string, wgt_coll):
    safe_name = text_string.replace(' ', '_').replace('&', 'AND').replace('/', '_')
    name = "WGT-Face_Label_" + safe_name
    obj = bpy.data.objects.get(name)
    if obj:
        return obj

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


def get_widget_collection():
    for name_candidate in ("WGTS", "wgt", "WGTS_FaceRig"):
        coll = bpy.data.collections.get(name_candidate)
        if coll:
            return coll

    for c in bpy.data.collections:
        c_low = c.name.lower()
        if "wgts" in c_low or "wgt" in c_low:
            return c

    coll = bpy.data.collections.new("WGTS")
    return coll


def finalize_widget_collection(wgt_coll):
    if not wgt_coll:
        return
    try:
        wgt_coll.hide_viewport = True
    except Exception:
        pass
    if wgt_coll.name in bpy.context.scene.collection.children:
        try:
            bpy.context.scene.collection.children.unlink(wgt_coll)
        except Exception:
            pass


def lighten(rgb, amt):
    return tuple(min(1.0, c + amt) for c in rgb)


def apply_color(armature, pb, group_name, rgb, cache):
    if is_blender_3():
        grp = cache.get(group_name)
        if grp is None:
            grp = armature.pose.bone_groups.get(group_name)
            if grp is None:
                grp = armature.pose.bone_groups.new(name=group_name)
            grp.color_set = 'CUSTOM'
            grp.colors.normal = rgb
            grp.colors.select = lighten(rgb, 0.25)
            grp.colors.active = lighten(rgb, 0.5)
            cache[group_name] = grp
        pb.bone_group = grp
    else:
        try:
            pb.color.palette = 'CUSTOM'
            cc = pb.color.custom
            cc.normal = rgb
            cc.select = lighten(rgb, 0.25)
            cc.active = lighten(rgb, 0.5)
        except Exception:
            pass


def purge_previous(armature):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    eb = armature.data.edit_bones
    for b in list(eb):
        if b.name.startswith("CTRL-") or b.name.startswith("LABEL-") or b.name in ["Face-Root", "FacePanelRoot", "FacePanel", "Eyebrows", "MouthPanel"]:
            eb.remove(b)
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in list(bpy.data.objects):
        if o.name.startswith("WGT-Face_"):
            bpy.data.objects.remove(o, do_unlink=True)


# =============================================================================
# FACE RIG SETUP AND DRIVER GENERATION
# =============================================================================

def setup_wuwa_face_rig(mesh_obj, controls, armature, head_name, fwd, up, face_size, keyblock):
    print(f"[WUWA FACE RIG] Building {len(controls)} face controls on '{armature.name}' under '{head_name}'")

    amw_inv = armature.matrix_world.inverted()
    bone_len = face_size * BONE_LEN_F

    def to_arm_point(p):
        return amw_inv @ p

    def to_arm_vec(v):
        return amw_inv.to_3x3() @ v

    fwd_arm = to_arm_vec(fwd).normalized()
    up_arm = to_arm_vec(up).normalized()

    bpy.context.view_layer.objects.active = armature
    try:
        armature.data.use_mirror_x = False
    except Exception:
        pass

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

    # Bone Collections Setup
    coll_names = [c['collection'] for c in controls if c.get('collection')]
    if not is_blender_3() and hasattr(armature.data, "collections"):
        for cn in set(coll_names):
            coll = armature.data.collections.get(cn) or armature.data.collections.new(cn)
            try:
                coll.is_visible = True
            except Exception:
                pass
            try:
                coll.rigify_ui_row = RIGIFY_UI_ROW
            except Exception:
                pass
        for c in controls:
            bone = armature.data.bones.get(c['name'])
            coll = armature.data.collections.get(c.get('collection', FACERIG_COLLECTION))
            if bone and coll:
                for existing_coll in list(bone.collections):
                    if existing_coll != coll:
                        existing_coll.unassign(bone)
                coll.assign(bone)

        # Place Face-Root into Other
        other_coll = None
        for ocn in ["Other", "Others"]:
            if ocn in armature.data.collections:
                other_coll = armature.data.collections[ocn]
                break
        if not other_coll:
            other_coll = armature.data.collections.new("Other")
            try:
                other_coll.is_visible = False
            except Exception:
                pass

        root_bone = armature.data.bones.get("Face-Root")
        if root_bone and other_coll:
            for c in list(root_bone.collections):
                c.unassign(root_bone)
            other_coll.assign(root_bone)
    elif is_blender_3():
        for c in controls:
            bone = armature.data.bones.get(c['name'])
            if bone:
                bone.layers = [i == 0 for i in range(32)]
        root_bone = armature.data.bones.get("Face-Root")
        if root_bone:
            root_bone.layers = [i == 25 for i in range(32)]

    wgt_coll = get_widget_collection()
    bpy.ops.object.mode_set(mode='POSE')
    color_cache = {}

    for c in controls:
        pb = armature.pose.bones.get(c['name'])
        if not pb:
            continue

        is_lbl = c.get('is_label', False)

        if is_lbl:
            for i in range(3):
                pb.lock_location[i] = True
                pb.lock_rotation[i] = True
                pb.lock_scale[i] = True
            pb.lock_rotation_w = True
        else:
            lim = c['lim']
            free = c['free']
            rng = c['range']
            if rng == 'both':
                lo, hi = -lim, lim
            elif rng == 'neg':
                lo, hi = -lim, 0.0
            else:
                lo, hi = 0.0, lim

            pb.lock_location[0] = 'X' not in free
            pb.lock_location[1] = True
            pb.lock_location[2] = 'Z' not in free
            for i in range(3):
                pb.lock_rotation[i] = True
                pb.lock_scale[i] = True
            pb.lock_rotation_w = True

            con = pb.constraints.new(type='LIMIT_LOCATION')
            con.owner_space = 'LOCAL'
            con.use_transform_limit = True
            con.use_min_x = con.use_max_x = True
            con.use_min_y = con.use_max_y = True
            con.use_min_z = con.use_max_z = True
            con.min_y = con.max_y = 0.0
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

    # Build Shape Key Drivers
    agg = {}
    for c in controls:
        for d in c['drivers']:
            agg.setdefault(d['key'], []).append({
                'bone': c['name'],
                'axis': d['axis'],
                'dir': d['dir'],
                'lim': c['lim'],
                'bidir': d.get('bidir', False),
                'gain': d.get('gain', 1.0),
                'is_diagonal': d.get('is_diagonal', False),
                'extra_axis': d.get('extra_axis'),
                'extra_dir': d.get('extra_dir', 1)
            })

    for key, entries in agg.items():
        sk = keyblock.get(key)
        if sk is None:
            continue
        sk.slider_min = -1.0 if any(e['bidir'] for e in entries) else 0.0
        try:
            sk.driver_remove("value")
        except Exception:
            pass
        drv = sk.driver_add("value").driver
        drv.type = 'SCRIPTED'
        terms = []
        var_count = 0

        for e in entries:
            vn1 = f"v{var_count}"
            var1 = drv.variables.new()
            var1.name = vn1
            var1.type = 'TRANSFORMS'
            tgt1 = var1.targets[0]
            tgt1.id = armature
            tgt1.bone_target = e['bone']
            tgt1.transform_type = 'LOC_' + e['axis']
            tgt1.transform_space = 'LOCAL_SPACE'
            var_count += 1

            sign1 = '' if e['dir'] > 0 else '-'
            lim = e['lim']
            gain = e.get('gain', 1.0)

            if e.get('is_diagonal') and e.get('extra_axis'):
                vn2 = f"v{var_count}"
                var2 = drv.variables.new()
                var2.name = vn2
                var2.type = 'TRANSFORMS'
                tgt2 = var2.targets[0]
                tgt2.id = armature
                tgt2.bone_target = e['bone']
                tgt2.transform_type = 'LOC_' + e['extra_axis']
                tgt2.transform_space = 'LOCAL_SPACE'
                var_count += 1
                sign2 = '' if e['extra_dir'] > 0 else '-'

                term = f"max(0.0, min({sign1}{vn1} / {lim!r}, {sign2}{vn2} / {lim!r}))"
            elif e.get('bidir'):
                term = f"{sign1}{vn1} / {lim!r}"
            else:
                term = f"max(0.0, {sign1}{vn1} / {lim!r})"

            if gain != 1.0:
                term = f"({gain!r} * {term})"
            terms.append(term)

        drv.expression = terms[0] if len(terms) == 1 else "max(" + ", ".join(terms) + ")"

    finalize_widget_collection(wgt_coll)
    print("[WUWA FACE RIG] Successfully created face rig controls and drivers!")
    return True


def wuwa_face_rig_main(armature_obj=None):
    faceobj = find_face_mesh()
    if faceobj is None:
        print("[WUWA FACE RIG] Notice: No mesh with shapekeys found.")
        return False

    if armature_obj:
        armature = armature_obj
        head_name = None
        for cand in ["ORG-head", "head", "Head", "Bip001Head", "Bip001-Head"]:
            if cand in armature.data.bones:
                head_name = cand
                break
        if not head_name:
            _, head_name = find_armature_and_head(faceobj)
    else:
        armature, head_name = find_armature_and_head(faceobj)

    if armature is None:
        print("[WUWA FACE RIG] Notice: No armature found.")
        return False

    fwd, right, up, face_size, fcx = get_face_metrics(faceobj, armature, head_name)
    keyblock = faceobj.data.shape_keys.key_blocks

    if CLEAN_REBUILD:
        purge_previous(armature)

    controls = plan_wuwa_controls(faceobj, armature, head_name, keyblock)
    return setup_wuwa_face_rig(faceobj, controls, armature, head_name, fwd, up, face_size, keyblock)


class WW_OT_CreateFacePanel(Operator):
    bl_idname = "wuthering_waves.create_face_panel"
    bl_label = "Create Face Rig"
    bl_description = "Generate complete Face Rig & Expression Controls for Wuthering Waves"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object or context.object
        if not obj:
            return False
        if obj.type == 'MESH':
            return any(m.type == 'ARMATURE' and m.object for m in obj.modifiers)
        elif obj.type == 'ARMATURE':
            return True
        return False

    def execute(self, context):
        try:
            success = wuwa_face_rig_main()
            if success:
                self.report({'INFO'}, "Successfully generated Wuthering Waves Face Rig!")
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "No face mesh or armature found for Face Rig.")
                return {'CANCELLED'}
        except Exception as ex:
            self.report({'ERROR'}, f"Failed to generate Face Rig: {ex}")
            return {'CANCELLED'}


register, unregister = bpy.utils.register_classes_factory([WW_OT_CreateFacePanel])

