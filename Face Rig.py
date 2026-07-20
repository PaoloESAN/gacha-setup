import bpy
import mathutils
from mathutils import Vector, Matrix

HEAD_BONE_NAME   = None
CLEAN_REBUILD    = True
FLIP_HORIZONTAL  = True
FLIP_VERTICAL    = False
FLIP_EYE_LR      = False

BONE_LEN_F   = 0.020
OFFSET_F     = 0.120
TRAVEL_F     = 0.050
SPACING_F    = 0.055
WIDGET_F     = 1.0
FACERIG_COLLECTION = "Facerig"
RIGIFY_UI_ROW = 1

EYE_HL_F     = 0.013
TRI_F        = 0.022
EMOTE_W_F    = 0.011
EMOTE_H_F    = 0.006
EMOTE_LIM_F  = 0.022
EMOTE_SPACING_F = 0.045
EMOTE_FWD_F  = 0.050
MOUTH_SHIFT_F = 0.55
MOUTH_RAISE_F = 0.040
EBR_WGT_F    = 0.016
EBR_MASTER_F = 0.030

COL_MOUTH   = (0.90, 0.20, 0.20)
COL_CORNER  = (0.15, 0.85, 0.30)
COL_VISEME  = (0.95, 0.85, 0.20)
COL_EYELID  = (0.90, 0.15, 0.15)
COL_EYEAIM  = (0.20, 0.85, 0.90)
COL_EYEMOTE = (0.65, 0.35, 0.90)
COL_BROW    = (0.30, 0.80, 0.35)
COL_BROWSAD = (0.95, 0.45, 0.75)
COL_EBRBONE = (0.20, 0.55, 0.95)
COL_EBRMASTER = (0.95, 0.55, 0.10)

HEAD_CANDIDATES = [
    "DEF-spine.006", "spine.006", "head", "Head", "Head_M", "head_M",
    "Bip001 Head", "Bip001_Head", "Bip001Head", "Bip001 头", "頭", "头",
]

ver = bpy.app.version_string
if ver[:3] == '4.0':
    ver = 4
elif ver[0] == '4':
    ver = float(ver[:3])
elif ver[0] == '3':
    ver = 3
else:
    raise Exception("This script targets Blender 3.x or 4.x.")

faceobj = None
for obj in bpy.data.objects:
    n = obj.name.lower()
    if "_face" in n and "weapon_" not in n and "gun_" not in n:
        faceobj = obj

if faceobj is None:
    raise Exception("Couldn't find a '*_face' mesh in the scene.")
if faceobj.data.shape_keys is None:
    raise Exception("The face mesh has no shape keys to drive.")

keyblock = faceobj.data.shape_keys.key_blocks


def shapekeyrename(keyblock):
    for sk in keyblock:
        if sk.name.endswith("_Unagi") or sk.name.endswith("_Anton") or sk.name.endswith("_Corin"):
            sk.name = sk.name[:-6]
        if sk.name.endswith("_NuoCha"):
            sk.name = sk.name[:-7]
    rename_map = {
        "Mouth_↖_Ben": "Fac_Mth_R_Up",   "Mouth_↗_Ben": "Fac_Mth_L_Up",
        "Mouth_↙_Ben": "Fac_Mth_R_Down", "Mouth_↘_Ben": "Fac_Mth_L_Down",
        "Mouth_上颌↑_Ben": "Fac_Mth_Up",  "Mouth_下颌↓_Ben": "Fac_Mth_Down",
        "Mouth_呲_L_Ben": "Fac_Mth_L_In", "Mouth_呲_R_Ben": "Fac_Mth_R_In",
        "Eye_Open_↑_Ben": "Fac_Eye_R_Open", "Mouth_Oo_Ben": "Fac_Mth_UuOo",
        "Eye_Close2_Ben": "Fac_Eye_Sad",
        "Eye_Ball_↑_Ben": "Eye_Up", "Eye_Ball_↓_Ben": "Eye_Down",
        "Eye_Ball_→_Ben": "Eye_Left", "Eye_Ball_←_Ben": "Eye_Right",
        "Eye_Ball_No_Ben": "O_O",
        "Mouth_啧_R_Ben": "Fac_Mth_R_Out", "Mouth_啧_L_Ben": "Fac_Mth_L_Out",
        "Mouth_Ii1": "Fac_Mth_Ii",
        "Fac_Mth_Aa": "Fac_Mth_Aa1",
        "Fac_Mth_ooR": "Fac_Mth_R_Out", "Fac_Mth_Roo": "Fac_Mth_R_In",
        "Fac_Mth_Loo": "Fac_Mth_L_Out", "Fac_Mth_ooL": "Fac_Mth_L_In",
        "Fac_Mth_oo_RDown": "Fac_Mth_R_Down", "Fac_Mth_LDown_oo": "Fac_Mth_L_Down",
        "Fac_Mth_LUp_oo": "Fac_Mth_L_Up",
        "Fac_Eye_Open_L": "Fac_Eye_L_Open",
        "Fac_Eye_LowEyeUP": "Fac_Eye_LowlidUp",
        "Fac_Mth_Laugh1": "Fac_Mth_Laugh",
        "EB_↑": "Fac_Ebr_Up", "EB_↓": "Fac_Ebr_Down",
        "EB_Angry": "Fac_Ebr_Angry", "EB_Relax": "Fac_Ebr_Relax",
        "EB_困扰": "Fac_Ebr_Sad",
        "Eye_↙↘": "Fac_Eye_BLBR", "Eye_Angry": "Fac_Eye_Angry",
        "Eye_Close": "Fac_Eye_Close",
        "Eye_Open_L": "Fac_Eye_L_Open", "Eye_Open_R": "Fac_Eye_R_Open",
        "Eye_Wink_L": "Fac_Eye_L_Wink", "Eye_Wink_R": "Fac_Eye_R_Wink",
        "EYE_Wink_L": "Fac_Eye_L_Wink", "EYE_Wink_R": "Fac_Eye_R_Wink",
        "Eye_半闭": "Fac_Eye_HalfClose", "Eye_困扰": "Fac_Eye_Sad",
        "Eye_认真": "Fac_Eye_MidDown", "Eye_下眼睑↑": "Fac_Eye_LowlidUp",
        "Mouth_△": "Fac_Mth_Triangle", "Mouth_↑": "Fac_Mth_Up",
        "Mouth_→": "Fac_Mth_Left", "Mouth_↓": "Fac_Mth_Down", "Mouth_←": "Fac_Mth_Right",
        "Mouth_Aa1": "Fac_Mth_Aa1", "Mouth_Aa2": "Fac_Mth_Aa2",
        "Mouth_Aa3Shout": "Fac_Mth_Aa3Shout", "Mouth_AaTalk": "Fac_Mth_AaTalk",
        "Mouth_Ee": "Fac_Mth_Ee", "Mouth_Ii": "Fac_Mth_Ii",
        "Mouth_Uu_Ben": "Fac_Mth_Uu", "Mouth_Laugh": "Fac_Mth_Laugh",
        "Mouth_Laugh2": "Fac_Mth_Laugh2",
        "Mouth_oo←": "Fac_Mth_L_In", "Mouth_↖oo": "Fac_Mth_L_Up",
        "Mouth_←oo": "Fac_Mth_R_Out", "Mouth_↙oo": "Fac_Mth_R_Down",
        "Mouth_→oo": "Fac_Mth_R_In", "Mouth_oo↗": "Fac_Mth_R_Up",
        "Mouth_oo→": "Fac_Mth_L_Out", "Mouth_oo↘": "Fac_Mth_L_Down",
        "Mouth_Oo": "Fac_Mth_Oo", "Mouth_Uu": "Fac_Mth_Uu", "Mouth_UuOo": "Fac_Mth_UuOo",
    }
    for key in rename_map.keys():
        try:
            keyblock[key].name = rename_map[key]
        except Exception:
            for sk in keyblock:
                if key in sk.name:
                    sk.name = rename_map[key]
    for sk in keyblock:
        if sk.name.endswith("_Ben"):
            sk.name = sk.name[:-4]


def find_armature_and_head(mesh_obj):
    armature = None
    for m in mesh_obj.modifiers:
        if m.type == 'ARMATURE' and m.object:
            armature = m.object
            break
    if armature is None:
        for o in bpy.data.objects:
            if o.type == 'ARMATURE':
                armature = o
                break
    if armature is None:
        raise Exception("No armature found to attach the face rig to.")

    names = [HEAD_BONE_NAME] if HEAD_BONE_NAME else []
    names += HEAD_CANDIDATES
    head_name = None
    for cand in names:
        if cand and cand in armature.data.bones:
            head_name = cand
            break
    if head_name is None:
        for b in armature.data.bones:
            if 'head' in b.name.lower():
                head_name = b.name
                break
    if head_name is None:
        raise Exception(
            "Couldn't find a head bone. Set HEAD_BONE_NAME at the top of the "
            "script. Looked for: " + ", ".join(c for c in names if c))
    return armature, head_name


def find_eyebrow_bones(armature):
    out = []
    for b in armature.data.bones:
        low = b.name.strip().lower()
        if low.startswith("ctrl-") or low.startswith("face-root"):
            continue
        if low.startswith("skneyebrow_") or "eyebrow" in low:
            out.append(b.name)
        elif (low.startswith("ebr_") or low.startswith("ebr ")) and low.endswith("bone"):
            out.append(b.name)
    return out


def eyebrow_side(name):
    low = name.strip().lower()
    if low.endswith(".r") or low.endswith("_r") or "_r_" in low or "_r " in low or ".r " in low:
        return 'R'
    if low.endswith(".l") or low.endswith("_l") or "_l_" in low or "_l " in low or ".l " in low:
        return 'L'
    return 'C'


def is_eyebrow_key(name):
    low = name.strip().lower()
    return (low.startswith("fac_ebr_") or low.startswith("ebr_")
            or low.startswith("ebr ") or "_ebr_" in low or "eyebrow" in low)


def skneyebrow_pos(armature, seg, side):
    for b in armature.data.bones:
        low = b.name.strip().lower()
        if ("skneyebrow_" + seg) in low or ("eyebrow_" + seg) in low:
            if eyebrow_side(b.name) == side:
                return armature.matrix_world @ b.head_local
    return None


def build_brow_shapekey_controls(mesh_obj, armature, fwd, up, face_size):
    kb = mesh_obj.data.shape_keys.key_blocks
    right = up.cross(fwd).normalized()
    OFFSET = face_size * OFFSET_F

    def place_s(feature, h=0.0, v=0.0):
        return feature + fwd * OFFSET + right * h + up * v

    ebkeys = [sk.name for sk in kb if is_eyebrow_key(sk.name)]

    def match(sub):
        return [n for n in ebkeys if sub in n.strip().lower()]

    up_keys = match("up")
    down_keys = match("down")
    angry = (match("angry") or [None])[0]
    relax = (match("relax") or [None])[0]
    sad = (match("sad") or [None])[0]

    out = []

    brow_c = feature_centroid(mesh_obj, ebkeys)
    seg_positions = [skneyebrow_pos(armature, s, sd)
                     for s in ("01", "02", "03") for sd in ("L", "R")]
    seg_positions = [p for p in seg_positions if p is not None]
    if brow_c is None and seg_positions:
        brow_c = sum(seg_positions, Vector()) / len(seg_positions)
    if brow_c is None:
        bb = [mesh_obj.matrix_world @ Vector(c) for c in mesh_obj.bound_box]
        brow_c = sum(bb, Vector()) / len(bb) + up * face_size * 0.12

    up_l = [n for n in up_keys if eyebrow_side(n) == 'L'] or up_keys
    up_r = [n for n in up_keys if eyebrow_side(n) == 'R'] or up_keys
    side_up = {'L': up_l, 'R': up_r}

    def side_brow_center(side):
        su = side_up[side]
        if su:
            c = feature_centroid(mesh_obj, [su[0]])
            if c is not None:
                return c
        pts = [skneyebrow_pos(armature, s, side) for s in ("01", "02", "03")]
        pts = [p for p in pts if p is not None]
        if pts:
            return sum(pts, Vector()) / len(pts)
        sgn = 1.0 if (side == 'L') != FLIP_EYE_LR else -1.0
        return brow_c + right * (sgn * face_size * 0.09)

    for side in ('L', 'R'):
        su = side_up[side]
        if not su:
            continue
        sbc = side_brow_center(side)
        out.append({'name': 'CTRL-Brow-UpDown.%s' % side,
                    'collection': FACERIG_COLLECTION, 'color': COL_EBRMASTER,
                    'group': 'Face Eyebrow', 'head': sbc + fwd * OFFSET + up * (face_size * 0.02),
                    'widget': 'eyebrow', 'lim': face_size * EBR_MASTER_F,
                    'free': ('Z',), 'range': 'both',
                    'shape_scale': Vector((face_size * EBR_MASTER_F,) * 3),
                    'drivers': [{'key': su[0], 'axis': 'Z', 'dir': +1, 'bidir': True}]})

    eyeL = feature_centroid(mesh_obj, ["Fac_Eye_L_Wink", "Fac_Eye_L_Open"]) \
           or feature_centroid(mesh_obj, ["Fac_Eye_Close"], side='L')
    eyeR = feature_centroid(mesh_obj, ["Fac_Eye_R_Wink", "Fac_Eye_R_Open"]) \
           or feature_centroid(mesh_obj, ["Fac_Eye_Close"], side='R')
    if eyeL is not None and eyeR is not None:
        eyeC = (eyeL + eyeR) * 0.5
    else:
        eyeC = brow_c

    box = Vector((face_size * EBR_WGT_F,) * 3)
    stack = [(k, nm) for k, nm in ((angry, 'Angry'), (relax, 'Relax'), (sad, 'Sad')) if k]
    n = len(stack)
    for i, (key, nm) in enumerate(stack):
        h = (i - (n - 1) / 2.0) * (face_size * EMOTE_SPACING_F)
        out.append({'name': 'CTRL-Brow-%s' % nm,
                    'collection': FACERIG_COLLECTION, 'color': COL_BROW,
                    'group': 'Face Eyebrow',
                    'head': eyeC + fwd * (face_size * (OFFSET_F + 0.05)) + right * h,
                    'widget': 'pad', 'lim': face_size * EBR_WGT_F,
                    'free': ('Z',), 'range': 'pos', 'shape_scale': box,
                    'drivers': [{'key': key, 'axis': 'Z', 'dir': +1}]})
    return out


def feature_centroid(mesh_obj, key_names, side=None):
    kb = mesh_obj.data.shape_keys.key_blocks
    basis = kb.get("Basis")
    if basis is None:
        return None
    key = None
    for kn in key_names:
        if kn in kb:
            key = kb[kn]
            break
    if key is None:
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

    if side in ('L', 'R'):
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


def feature_extent(mesh_obj, key_names, right, up):
    kb = mesh_obj.data.shape_keys.key_blocks
    basis = kb.get("Basis")
    if basis is None:
        return None
    key = None
    for kn in key_names:
        if kn in kb:
            key = kb[kn]
            break
    if key is None:
        return None
    n = len(basis.data)
    deltas = [(key.data[i].co - basis.data[i].co).length for i in range(n)]
    maxd = max(deltas) if deltas else 0.0
    if maxd <= 1e-9:
        return None
    thr = maxd * 0.30
    mw = mesh_obj.matrix_world
    pts = [mw @ basis.data[i].co for i in range(n) if deltas[i] >= thr]
    if not pts:
        return None
    rs = [p.dot(right) for p in pts]
    us = [p.dot(up) for p in pts]
    return (max(rs) - min(rs), max(us) - min(us))


def feature_extreme(mesh_obj, key_names, axis):
    kb = mesh_obj.data.shape_keys.key_blocks
    basis = kb.get("Basis")
    if basis is None:
        return None
    key = None
    for kn in key_names:
        if kn in kb:
            key = kb[kn]
            break
    if key is None:
        return None
    n = len(basis.data)
    deltas = [(key.data[i].co - basis.data[i].co).length for i in range(n)]
    maxd = max(deltas) if deltas else 0.0
    if maxd <= 1e-9:
        return None
    thr = maxd * 0.30
    mw = mesh_obj.matrix_world
    pts = [mw @ basis.data[i].co for i in range(n) if deltas[i] >= thr]
    if not pts:
        return None
    pmax = max(pts, key=lambda p: p.dot(axis))
    pmin = min(pts, key=lambda p: p.dot(axis))
    return (pmax, pmin)


def face_frame(mesh_obj):
    me = mesh_obj.data
    mw = mesh_obj.matrix_world
    fwd = Vector((0.0, 0.0, 0.0))
    for v in me.vertices:
        fwd += v.normal
    fwd = mw.to_3x3() @ fwd
    if fwd.length < 1e-6:
        fwd = Vector((0.0, -1.0, 0.0))
    fwd.normalize()

    world_up = Vector((0.0, 0.0, 1.0))
    if abs(fwd.dot(world_up)) > 0.95:
        world_up = Vector((0.0, 1.0, 0.0))
    right = world_up.cross(fwd).normalized()
    up = fwd.cross(right).normalized()

    corners = [mw @ Vector(c) for c in mesh_obj.bound_box]
    mn = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    mx = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    face_size = (mx - mn).length
    return fwd, right, up, face_size


def plan_controls(mesh_obj, fwd, right, up, face_size):
    OFFSET  = face_size * OFFSET_F
    LIM     = face_size * TRAVEL_F
    SPACING = face_size * SPACING_F

    def place(feature, h=0.0, v=0.0):
        return feature + fwd * OFFSET + right * h + up * v

    def hkey(pos, neg):
        return (pos, neg) if not FLIP_HORIZONTAL else (neg, pos)

    def vkey(pos, neg):
        return (pos, neg) if not FLIP_VERTICAL else (neg, pos)

    controls = []

    MOUTH_KEYS = ["Fac_Mth_Ii", "Fac_Mth_Ee", "Fac_Mth_Triangle",
                  "Fac_Mth_Left", "Fac_Mth_Right", "Fac_Mth_Up", "Fac_Mth_Down",
                  "Fac_Mth_L_Up", "Fac_Mth_R_Up", "Fac_Mth_L_Out", "Fac_Mth_R_Out",
                  "Fac_Mth_L_In", "Fac_Mth_R_In", "Fac_Mth_Aa1", "Fac_Mth_AaTalk"]

    mouth = feature_centroid(mesh_obj, MOUTH_KEYS)
    eyeL = feature_centroid(mesh_obj, ["Fac_Eye_L_Wink", "Fac_Eye_L_Open"]) \
           or feature_centroid(mesh_obj, ["Fac_Eye_Close"], side='L')
    eyeR = feature_centroid(mesh_obj, ["Fac_Eye_R_Wink", "Fac_Eye_R_Open"]) \
           or feature_centroid(mesh_obj, ["Fac_Eye_Close"], side='R')
    brow = feature_centroid(mesh_obj, ["Fac_Ebr_Up", "Fac_Ebr_Down", "Fac_Ebr_Angry"]
                            + [sk.name for sk in keyblock if is_eyebrow_key(sk.name)])

    fcx = mesh_obj.matrix_world @ (0.125 * sum((Vector(c) for c in mesh_obj.bound_box), Vector()))
    if mouth is None:
        mouth = fcx - up * face_size * 0.12
    if eyeL is None:
        eyeL = fcx + up * face_size * 0.10 + right * face_size * 0.10
    if eyeR is None:
        eyeR = fcx + up * face_size * 0.10 - right * face_size * 0.10
    if brow is None:
        brow = ((eyeL + eyeR) * 0.5) + up * face_size * 0.10
    eyeC = (eyeL + eyeR) * 0.5

    mouth_raise = up * (face_size * MOUTH_RAISE_F)
    mouth = mouth + mouth_raise

    mouth_edges = feature_extreme(mesh_obj, MOUTH_KEYS, right)

    def corner(side):
        cc = feature_centroid(mesh_obj,
            ["Fac_Mth_%s_Up" % side, "Fac_Mth_%s_Down" % side,
             "Fac_Mth_%s_Out" % side, "Fac_Mth_%s_In" % side])
        if mouth_edges is not None:
            pmax, pmin = mouth_edges
            if cc is not None:
                return pmax if (pmax - cc).length <= (pmin - cc).length else pmin
            return pmax if (side == 'L') != FLIP_EYE_LR else pmin
        if cc is not None:
            return cc
        s = 1.0 if (side == 'L') != FLIP_EYE_LR else -1.0
        return mouth + right * (s * face_size * 0.06)

    mouth_ext = feature_extent(mesh_obj, MOUTH_KEYS, right, up)
    if mouth_ext:
        mw2, mh2 = mouth_ext[0] * 0.5 * MOUTH_SHIFT_F, mouth_ext[1] * 0.5 * MOUTH_SHIFT_F
    else:
        mw2, mh2 = LIM * 0.9, LIM * 0.4
    mouth_scale = Vector((max(mw2, LIM * 0.3), LIM, max(mh2, LIM * 0.18)))
    hl = face_size * EYE_HL_F
    corner_scale = Vector((hl, hl, hl))
    tri = face_size * TRI_F
    tri_scale = Vector((tri, tri, tri))
    emote_scale = Vector((face_size * EMOTE_W_F, LIM, face_size * EMOTE_H_F))

    lr = hkey("Fac_Mth_Left", "Fac_Mth_Right")
    ud = vkey("Fac_Mth_Up", "Fac_Mth_Down")
    drv = []
    if lr[0] in keyblock: drv.append({'key': lr[0], 'axis': 'X', 'dir': +1})
    if lr[1] in keyblock: drv.append({'key': lr[1], 'axis': 'X', 'dir': -1})
    if ud[0] in keyblock: drv.append({'key': ud[0], 'axis': 'Z', 'dir': +1})
    if ud[1] in keyblock: drv.append({'key': ud[1], 'axis': 'Z', 'dir': -1})
    if drv:
        controls.append({'name': 'CTRL-Mouth-Shift', 'collection': 'Face Main',
                         'color': COL_MOUTH, 'group': 'Face Mouth',
                         'head': place(mouth), 'widget': 'pad', 'lim': LIM,
                         'free': ('X', 'Z'), 'range': 'both', 'shape_scale': mouth_scale,
                         'drivers': drv})

    for side in ('L', 'R'):
        out_name = "Fac_Mth_%s_Out" % side
        in_name = "Fac_Mth_%s_In" % side
        if side == 'R':
            outk = hkey(in_name, out_name)
        else:
            outk = hkey(out_name, in_name)
        udk = vkey("Fac_Mth_%s_Up" % side, "Fac_Mth_%s_Down" % side)
        drv = []
        if outk[0] in keyblock: drv.append({'key': outk[0], 'axis': 'X', 'dir': +1})
        if outk[1] in keyblock: drv.append({'key': outk[1], 'axis': 'X', 'dir': -1})
        if udk[0] in keyblock:  drv.append({'key': udk[0], 'axis': 'Z', 'dir': +1})
        if udk[1] in keyblock:  drv.append({'key': udk[1], 'axis': 'Z', 'dir': -1})
        if drv:
            controls.append({'name': 'CTRL-Mouth-Corner.%s' % side,
                             'collection': 'Face Main', 'color': COL_CORNER,
                             'group': 'Face Corner', 'head': place(corner(side) + mouth_raise),
                             'widget': 'pad', 'lim': LIM, 'free': ('X', 'Z'),
                             'range': 'both', 'shape_scale': corner_scale,
                             'drivers': drv})

    visemes = [k for k in ["Fac_Mth_Aa1", "Fac_Mth_Aa2", "Fac_Mth_Aa3Shout",
               "Fac_Mth_AaTalk", "Fac_Mth_Ee", "Fac_Mth_Ii", "Fac_Mth_Oo",
               "Fac_Mth_Uu", "Fac_Mth_UuOo", "Fac_Mth_Laugh", "Fac_Mth_Laugh2",
               "Fac_Mth_Triangle"] if k in keyblock]
    if visemes:
        n = len(visemes)
        for i, k in enumerate(visemes):
            h = (i - (n - 1) / 2.0) * SPACING
            controls.append({'name': 'CTRL-%s' % k[4:], 'collection': 'Face Visemes',
                             'color': COL_VISEME, 'group': 'Face Visemes',
                             'head': place(mouth, h=h, v=-face_size * 0.09),
                             'widget': 'slider', 'lim': LIM, 'free': ('Z',),
                             'range': 'pos',
                             'drivers': [{'key': k, 'axis': 'Z', 'dir': +1}]})

    for side, pos in (('L', eyeL), ('R', eyeR)):
        openk = "Fac_Eye_%s_Open" % side
        winkk = "Fac_Eye_%s_Wink" % side
        if openk in keyblock:
            controls.append({'name': 'CTRL-Eye_Open.%s' % side,
                             'collection': 'Face Main', 'color': COL_EYELID,
                             'group': 'Face Eyelid',
                             'head': place(pos, v=face_size * 0.055),
                             'widget': 'triangle', 'lim': LIM, 'free': ('Z',),
                             'range': 'pos', 'shape_scale': tri_scale,
                             'drivers': [{'key': openk, 'axis': 'Z', 'dir': +1}]})
        if winkk in keyblock:
            controls.append({'name': 'CTRL-Eye_Wink.%s' % side,
                             'collection': 'Face Main', 'color': COL_EYELID,
                             'group': 'Face Eyelid',
                             'head': place(pos, v=-face_size * 0.06),
                             'widget': 'triangle_down', 'lim': LIM, 'free': ('Z',),
                             'range': 'neg', 'shape_scale': tri_scale,
                             'drivers': [{'key': winkk, 'axis': 'Z', 'dir': -1}]})

    lr = hkey("Eye_Left", "Eye_Right")
    ud = vkey("Eye_Up", "Eye_Down")
    drv = []
    if lr[0] in keyblock: drv.append({'key': lr[0], 'axis': 'X', 'dir': +1})
    if lr[1] in keyblock: drv.append({'key': lr[1], 'axis': 'X', 'dir': -1})
    if ud[0] in keyblock: drv.append({'key': ud[0], 'axis': 'Z', 'dir': +1})
    if ud[1] in keyblock: drv.append({'key': ud[1], 'axis': 'Z', 'dir': -1})
    if drv:
        controls.append({'name': 'CTRL-Eye-Aim', 'collection': 'Face Main',
                         'color': COL_EYEAIM, 'group': 'Face Eye-Aim',
                         'head': place(eyeC, v=face_size * 0.02), 'widget': 'ring',
                         'lim': LIM, 'free': ('X', 'Z'), 'range': 'both', 'drivers': drv})

    emote_order = ["Fac_Eye_Sad", "Fac_Eye_BLBR", "Fac_Eye_MidDown",
                   "Fac_Eye_Angry", "Fac_Eye_HalfClose", "Fac_Eye_Close",
                   "Fac_Eye_LowlidUp"]
    emote_lim = face_size * EMOTE_LIM_F
    emote_spacing = face_size * EMOTE_SPACING_F
    emote_fwd = fwd * (face_size * EMOTE_FWD_F)
    eye_emotes = [k for k in emote_order if k in keyblock]
    if eye_emotes:
        n = len(eye_emotes)
        for i, k in enumerate(eye_emotes):
            v = ((n - 1) / 2.0 - i) * emote_spacing
            controls.append({'name': 'CTRL-%s' % k[4:], 'collection': 'Face Eyes',
                             'color': COL_EYEMOTE, 'group': 'Face Eye-Emote',
                             'head': place(eyeC, v=v) + emote_fwd, 'widget': 'pad',
                             'lim': emote_lim, 'free': ('Z',), 'range': 'pos',
                             'shape_scale': emote_scale,
                             'drivers': [{'key': k, 'axis': 'Z', 'dir': +1}]})
    if "O_O" in keyblock:
        controls.append({'name': 'CTRL-O_O', 'collection': 'Face Eyes',
                         'color': COL_EYEMOTE, 'group': 'Face Eye-Emote',
                         'head': place(eyeC, h=face_size * 0.14) + emote_fwd, 'widget': 'pad',
                         'lim': emote_lim, 'free': ('Z',), 'range': 'pos',
                         'shape_scale': emote_scale,
                         'drivers': [{'key': "O_O", 'axis': 'Z', 'dir': +1}]})

    for c in controls:
        c['collection'] = FACERIG_COLLECTION
    return controls


def get_widget_collection(name="WGTS_FaceRig"):
    for c in bpy.data.collections:
        if "WGTS" in c.name:
            return c
    coll = bpy.data.collections.get(name)
    if not coll:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def make_widget(kind, coll):
    name = "WGT-Face_" + kind
    obj = bpy.data.objects.get(name)
    if obj:
        return obj
    if kind == 'pad':
        s = 1.0
        verts = [(-s, 0, -s), (s, 0, -s), (s, 0, s), (-s, 0, s)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
    elif kind == 'slider':
        verts = [(0, 0, -1), (0, 0, 1), (-0.35, 0, 1), (0.35, 0, 1)]
        edges = [(0, 1), (2, 3)]
    elif kind == 'ring':
        import math
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
    elif kind == 'diamond':
        verts = [(0, 0, 1), (0.75, 0, 0), (0, 0, -1), (-0.75, 0, 0)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
    elif kind == 'eyebrow':
        N = 14
        top = []
        bot = []
        for i in range(N + 1):
            x = -1.0 + 2.0 * i / N
            arch = 0.40 * (1.0 - x * x)
            ht = 0.20 * (1.0 - x * x)
            top.append((x, 0.0, arch + ht))
            bot.append((x, 0.0, arch - ht))
        verts = top + [bot[i] for i in range(N - 1, 0, -1)]
        edges = [(i, (i + 1) % len(verts)) for i in range(len(verts))]
    else:
        verts, edges = [(0, 0, 0)], []
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, [])
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def lighten(rgb, amt):
    return tuple(min(1.0, c + amt) for c in rgb)


def apply_color(armature, pb, group_name, rgb, cache):
    if ver != 3:
        try:
            pb.color.palette = 'CUSTOM'
            cc = pb.color.custom
            cc.normal = rgb
            cc.select = lighten(rgb, 0.25)
            cc.active = lighten(rgb, 0.5)
        except Exception:
            pass
    else:
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


def purge_previous(armature):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    eb = armature.data.edit_bones
    for b in list(eb):
        if b.name.startswith("CTRL-") or b.name == "Face-Root":
            eb.remove(b)
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in list(bpy.data.objects):
        if o.name.startswith("WGT-Face_"):
            bpy.data.objects.remove(o, do_unlink=True)


def setup_face_rig(mesh_obj, controls, armature, head_name, fwd, up, face_size):
    print("Building %d controls on armature '%s' under bone '%s'"
          % (len(controls), armature.name, head_name))

    amw_inv = armature.matrix_world.inverted()
    bone_len = face_size * BONE_LEN_F

    def to_arm_point(p):
        return amw_inv @ p

    def to_arm_vec(v):
        return amw_inv.to_3x3() @ v

    fwd_arm = to_arm_vec(fwd).normalized()
    up_arm = to_arm_vec(up).normalized()

    has_ebrow_sk = any(is_eyebrow_key(sk.name) for sk in keyblock)
    ebrow_bones = [] if has_ebrow_sk else find_eyebrow_bones(armature)
    if has_ebrow_sk:
        print("Eyebrow shape keys found; using shape-key controls (skipping bone rig).")
        controls.extend(build_brow_shapekey_controls(mesh_obj, armature, fwd, up, face_size))
    elif ebrow_bones:
        print("Eyebrow bones detected: %s" % ", ".join(ebrow_bones))
    else:
        cand = [b.name for b in armature.data.bones
                if 'ebr' in b.name.lower() or 'brow' in b.name.lower()]
        print("No eyebrow shape keys or bones matched on '%s'. Candidates: %s"
              % (armature.name, cand))

    sides = {}
    for name in ebrow_bones:
        b = armature.data.bones.get(name)
        if b is None:
            continue
        s = eyebrow_side(name)
        sides.setdefault(s, []).append((name, armature.matrix_world @ b.head_local))

    for s, items in sides.items():
        center = Vector((0.0, 0.0, 0.0))
        for _, p in items:
            center += p
        center /= len(items)
        master_name = 'CTRL-Master-Eyebrow.%s' % s
        controls.append({'name': master_name, 'collection': FACERIG_COLLECTION,
                         'color': COL_EBRMASTER, 'group': 'Face Eyebrow',
                         'head': center + fwd * (face_size * OFFSET_F * 1.5),
                         'widget': 'eyebrow', 'lim': face_size * EBR_MASTER_F,
                         'free': ('X', 'Y', 'Z'), 'range': 'both',
                         'shape_scale': Vector((face_size * EBR_MASTER_F,) * 3),
                         'kind': 'master', 'drivers': []})
        for name, head_world in items:
            front = head_world + fwd * (face_size * OFFSET_F)
            ctrl_name = 'CTRL-' + name.strip().replace(' ', '_')
            controls.append({'name': ctrl_name, 'collection': FACERIG_COLLECTION,
                             'color': COL_EBRBONE, 'group': 'Face Eyebrow',
                             'head': front, 'widget': 'pad',
                             'lim': face_size * EBR_WGT_F, 'free': ('X', 'Y', 'Z'),
                             'range': 'both',
                             'shape_scale': Vector((face_size * EBR_WGT_F,) * 3),
                             'kind': 'fk', 'target_bone': name, 'parent': master_name,
                             'hook_name': ctrl_name + '_Hook', 'hook_head': head_world,
                             'drivers': []})

    bpy.context.view_layer.objects.active = armature
    try:
        armature.data.use_mirror_x = False
    except Exception:
        pass
    try:
        armature.pose.use_mirror_x = False
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
        par = eb.get(c['parent']) if c.get('parent') else None
        b.parent = par if par else root
        b.use_connect = False
        if c.get('hook_name'):
            hk = eb.get(c['hook_name']) or eb.new(c['hook_name'])
            hh = to_arm_point(c['hook_head'])
            hk.head = hh
            hk.tail = hh + fwd_arm * bone_len
            hk.use_deform = False
            hk.parent = b
            hk.use_connect = False

    bpy.ops.object.mode_set(mode='OBJECT')

    coll_names = []
    for c in controls:
        if c['collection'] not in coll_names:
            coll_names.append(c['collection'])
    if ver != 3 and hasattr(armature.data, "collections"):
        for cn in coll_names:
            coll = armature.data.collections.get(cn)
            if not coll:
                coll = armature.data.collections.new(cn)
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
            coll = armature.data.collections.get(c['collection'])
            if bone and coll:
                coll.assign(bone)
        hook_names = [c['hook_name'] for c in controls if c.get('hook_name')]
        if hook_names:
            hc = armature.data.collections.get("Facerig Hooks") \
                or armature.data.collections.new("Facerig Hooks")
            try:
                hc.is_visible = False
            except Exception:
                pass
            for hn in hook_names:
                bone = armature.data.bones.get(hn)
                if bone:
                    hc.assign(bone)

    wgt_coll = get_widget_collection()
    bpy.ops.object.mode_set(mode='POSE')
    color_cache = {}

    for c in controls:
        pb = armature.pose.bones.get(c['name'])
        if not pb:
            continue

        if c.get('kind') in ('fk', 'master'):
            is_master = c['kind'] == 'master'
            for i in range(3):
                pb.lock_location[i] = False
                pb.lock_rotation[i] = not is_master
                pb.lock_scale[i] = not is_master
            pb.lock_rotation_w = not is_master
            pb.custom_shape = make_widget(c['widget'], wgt_coll)
            try:
                pb.use_custom_shape_bone_size = False
            except Exception:
                pass
            ss = c.get('shape_scale')
            pb.custom_shape_scale_xyz = ss if ss is not None else Vector((c['lim'] * WIDGET_F,) * 3)
            apply_color(armature, pb, c['group'], c['color'], color_cache)
            tb = armature.pose.bones.get(c['target_bone']) if c.get('target_bone') else None
            if tb:
                for cn in [x for x in tb.constraints if x.name == 'FaceRig CopyLoc']:
                    tb.constraints.remove(cn)
                con = tb.constraints.new(type='COPY_LOCATION')
                con.name = 'FaceRig CopyLoc'
                con.target = armature
                con.subtarget = c.get('hook_name') or c['name']
            continue

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

        pb.custom_shape = make_widget(c['widget'], wgt_coll)
        try:
            pb.use_custom_shape_bone_size = False
        except Exception:
            pass
        ss = c.get('shape_scale')
        pb.custom_shape_scale_xyz = ss if ss is not None else Vector((lim * WIDGET_F,) * 3)

        apply_color(armature, pb, c['group'], c['color'], color_cache)

    bpy.ops.object.mode_set(mode='OBJECT')

    agg = {}
    for c in controls:
        for d in c['drivers']:
            agg.setdefault(d['key'], []).append(
                {'bone': c['name'], 'axis': d['axis'], 'dir': d['dir'],
                 'lim': c['lim'], 'bidir': d.get('bidir', False)})

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
        for i, e in enumerate(entries):
            vn = "v%d" % i
            var = drv.variables.new()
            var.name = vn
            var.type = 'TRANSFORMS'
            tgt = var.targets[0]
            tgt.id = armature
            tgt.bone_target = e['bone']
            tgt.transform_type = 'LOC_' + e['axis']
            tgt.transform_space = 'LOCAL_SPACE'
            sign = '' if e['dir'] > 0 else '-'
            if e['bidir']:
                terms.append("%s%s / %r" % (sign, vn, e['lim']))
            else:
                terms.append("max(0.0, %s%s / %r)" % (sign, vn, e['lim']))
        drv.expression = terms[0] if len(terms) == 1 else "max(" + ", ".join(terms) + ")"

    print("Face rig build complete.")


shapekeyrename(keyblock)
armature, head_name = find_armature_and_head(faceobj)
fwd, right, up, face_size = face_frame(faceobj)
controls = plan_controls(faceobj, fwd, right, up, face_size)

if not controls:
    raise Exception("No drivable face shape keys were found after renaming.")

if CLEAN_REBUILD:
    purge_previous(armature)

setup_face_rig(faceobj, controls, armature, head_name, fwd, up, face_size)

print("\nZZZ Isaac-style face rig done. %d controls built on '%s'.\n"
      % (len(controls), armature.name))