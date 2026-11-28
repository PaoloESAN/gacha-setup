import re
import bpy
import math
from mathutils import Vector, Matrix

from setup_wizard.character_rig_setup.shape_keys_panel import (
    build_shape_keys_panel,
    COL_BROW,
    COL_EYE,
    COL_EYELID as PANEL_COL_EYELID,
    COL_MOUTH as PANEL_COL_MOUTH,
    COL_VISEME as PANEL_COL_VISEME,
    COL_EXPRESSION as PANEL_COL_EXPRESSION,
    COL_EMOTION,
    COL_PHONEME,
    COL_EXTRA,
)

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

COL_MOUTH = (0.90, 0.20, 0.20)
COL_CORNER = (0.15, 0.85, 0.30)
COL_VISEME = (0.95, 0.85, 0.20)
COL_EYELID = (0.90, 0.15, 0.15)
COL_EYEAIM = (0.20, 0.85, 0.90)
COL_EXPRESSION = (0.65, 0.35, 0.90)
COL_LABEL = (0.95, 0.95, 0.95)

HEAD_CANDIDATES = [
    "DEF-spine.006", "spine.006", "head", "Head", "Head_M", "head_M",
    "Bip001 Head", "Bip001_Head", "Bip001Head"
]


def is_blender_3():
    return bpy.app.version[0] == 3


def find_armature_and_head(mesh_obj):
    armature = None
    for m in mesh_obj.modifiers:
        if m.type == 'ARMATURE' and m.object:
            armature = m.object
            break
    if armature is None:
        for o in bpy.data.objects:
            if o.type == 'ARMATURE' and o.name in bpy.context.view_layer.objects:
                armature = o
                break
    if armature is None:
        raise Exception("No armature found to attach the HSR face rig to.")

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
        head_name = armature.data.bones[0].name
    return armature, head_name


def face_frame(mesh_obj):
    mw = mesh_obj.matrix_world
    # Setup normalizes characters to face -Y, with Z upright. Averaging face
    # normals pitches the entire panel according to the character's topology
    # (Blade's controls tilted about 19 degrees). Keep sliders and labels in
    # the normalized frontal plane, like the other expression panels.
    fwd = Vector((0.0, -1.0, 0.0))
    world_up = Vector((0.0, 0.0, 1.0))
    right = world_up.cross(fwd).normalized()
    up = fwd.cross(right).normalized()

    corners = [mw @ Vector(c) for c in mesh_obj.bound_box]
    mn = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    mx = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    face_size = (mx - mn).length
    return fwd, right, up, face_size


def feature_centroid(mesh_obj, key_names):
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


def _strip_hsr_char_prefix(name):
    """Strip character-specific Emo_<Char>_ prefixes (e.g. Emo_Maid_, Emo_TheHerta_00_)."""
    s = re.sub(r'^Emo_[A-Za-z0-9]+_(?:0\d_)?', '', name)
    return s


def _hsr_clean_label(raw_name, strip_prefix_re, keep_variant=False):
    s = _strip_hsr_char_prefix(raw_name)
    m_var = re.search(r'_(0\d)_', s)
    var_tag = m_var.group(1) if (keep_variant and m_var) else ""
    s = re.sub(strip_prefix_re, '', s, flags=re.IGNORECASE)
    s = re.sub(r'^0\d_', '', s)
    s = s.replace('_', ' ').strip()
    if var_tag and var_tag not in s:
        s = f"{s} {var_tag}"
    return s or raw_name


def _hsr_find_key(keyblock, suffix_candidates, prefer_tag=None):
    """Find a matching HSR mouth/eye/brow key across naming conventions."""
    all_keys = list(keyblock.keys())
    # Prefer keys matching prefer_tag (e.g. 'Mouth_00_' or 'Mouth_01_') first
    ordered = all_keys
    if prefer_tag:
        ordered = [k for k in all_keys if prefer_tag in k] + [k for k in all_keys if prefer_tag not in k]
    for cand in suffix_candidates:
        cand_low = cand.lower()
        for k in ordered:
            kl = k.lower()
            if kl == cand_low or _strip_hsr_char_prefix(k).lower() == cand_low:
                return k
    return None


def split_bilateral_shapekey_lr(mesh_obj, key_name, fcx, right, feather=0.002):
    """Split a bilateral eye-close shape key into independent _L and _R shape keys.

    Uses world-space projection onto ``right`` (+right = viewer right = character .L,
    -right = viewer left = character .R) with a tiny centerline feather so that
    ``L + R == original`` identically at weight 1.0.
    Returns ``(name_L, name_R)`` or ``(None, None)`` if the key is already single-sided.
    """
    if not mesh_obj or not mesh_obj.data or not mesh_obj.data.shape_keys:
        return None, None
    kl = key_name.lower()
    if kl.endswith(("_l", "_r", ".l", ".r")):
        return None, None

    kb = mesh_obj.data.shape_keys.key_blocks
    basis = kb.get("Basis")
    src = kb.get(key_name)
    if basis is None or src is None:
        return None, None

    mw = mesh_obj.matrix_world
    n = len(basis.data)
    deltas = [None] * n
    dots = [0.0] * n
    max_pos = 0.0
    max_neg = 0.0

    for i in range(n):
        d = src.data[i].co - basis.data[i].co
        d_len = d.length
        if d_len > 1e-6:
            deltas[i] = d
            wco = mw @ basis.data[i].co
            dot = (wco - fcx).dot(right)
            dots[i] = dot
            if dot > feather and d_len > max_pos:
                max_pos = d_len
            elif dot < -feather and d_len > max_neg:
                max_neg = d_len

    # Only split if both left and right sides actually deform
    if max_pos <= 1e-5 or max_neg <= 1e-5:
        return None, None

    name_L = f"{key_name}_L"
    name_R = f"{key_name}_R"

    sk_L = kb.get(name_L) or mesh_obj.shape_key_add(name=name_L, from_mix=False)
    sk_R = kb.get(name_R) or mesh_obj.shape_key_add(name=name_R, from_mix=False)
    sk_L.slider_min = 0.0
    sk_L.slider_max = 1.0
    sk_L.value = 0.0
    sk_R.slider_min = 0.0
    sk_R.slider_max = 1.0
    sk_R.value = 0.0

    inv_2f = 1.0 / (2.0 * feather) if feather > 1e-9 else 0.0
    for i in range(n):
        bco = basis.data[i].co
        d = deltas[i]
        if d is None:
            sk_L.data[i].co = bco.copy()
            sk_R.data[i].co = bco.copy()
            continue
        dot = dots[i]
        if dot >= feather:
            w_l = 1.0
        elif dot <= -feather:
            w_l = 0.0
        else:
            w_l = (dot + feather) * inv_2f
        w_r = 1.0 - w_l
        sk_L.data[i].co = bco + d * w_l
        sk_R.data[i].co = bco + d * w_r

    return name_L, name_R


def plan_hsr_controls(mesh_obj, fwd, right, up, face_size, keyblock, wgt_coll=None, unique_tag="", armature=None):
    OFFSET = face_size * OFFSET_F
    LIM = face_size * TRAVEL_F

    def place(feature, h=0.0, v=0.0):
        return feature + fwd * OFFSET + right * h + up * v

    controls = []
    handled_keys = set()

    all_keys = list(keyblock.keys())

    # 0. Ignore default / rest utility keys
    for k in all_keys:
        kl = k.lower()
        stripped = _strip_hsr_char_prefix(k).lower()
        if (
            kl == "basis"
            or kl == "default"
            or "default" in kl
            or stripped.endswith(("_n", "_max", "_minimum"))
            or stripped in ("mouth_00_n", "mouth_01_n", "mouth_n")
        ):
            handled_keys.add(k)

    # Locate facial centroids for direct eye-close control and panel anchor
    mouth_keys = [k for k in all_keys if ("mouth" in k.lower() or "mth" in k.lower()) and k not in handled_keys]
    eye_keys = [k for k in all_keys if "eye" in k.lower() and "brow" not in k.lower() and k not in handled_keys]
    brow_keys = [k for k in all_keys if ("brow" in k.lower() or "ebr" in k.lower()) and k not in handled_keys]

    fcx = mesh_obj.matrix_world @ (0.125 * sum((Vector(c) for c in mesh_obj.bound_box), Vector()))

    # =========================================================================
    # 2. GENSHIN-STYLE FRAMED CONTROL PANEL (to the viewer's right of the head)
    # =========================================================================
    main_sections = []   # Column 1: Brows + Eyes
    mouth_sections = []  # Column 2: Mouth + Emotions
    side_sections = []   # Column 3: Phonemes + Mouth Alt + Extra

    # --- 2.A BROWS SECTION ---
    brow_list = [k for k in brow_keys if k not in handled_keys]
    if brow_list:
        brow_variants = {m.group(1) for k in brow_list for m in [re.search(r'Brow_(0\d)_', k)] if m}
        keep_brow_var = len(brow_variants) > 1
        brow_items = []
        for k in sorted(brow_list):
            handled_keys.add(k)
            lbl = _hsr_clean_label(k, r'^(?:Brow_|Ebr_)', keep_variant=keep_brow_var)
            brow_items.append({
                'name': f"CTRL-{k}",
                'label': lbl,
                'color': COL_BROW,
                'group': 'Face Eyebrow',
                'drivers': [{'key': k, 'axis': 'X', 'dir': +1}],
            })
        main_sections.append({
            'title': 'Brows',
            'rows': [{'type': 'grid', 'cols': 2, 'items': brow_items}],
        })

    # --- 2.B EYES SECTION ---
    eye_list = [k for k in eye_keys if k not in handled_keys]
    if eye_list:
        # Exclude previously generated _L/_R split keys from base list so rebuilds are idempotent
        base_close_keys = [
            k for k in eye_list
            if "close" in k.lower()
            and "ani_" not in k.lower()
            and not (k.endswith(("_L", "_R")) and k[:-2] in keyblock)
        ]
        split_close_children = {
            k for k in eye_list
            if k.endswith(("_L", "_R")) and k[:-2] in base_close_keys
        }
        expr_eye_keys = [
            k for k in eye_list
            if k not in base_close_keys
            and k not in split_close_children
            and "ani_" not in k.lower()
        ]

        eye_rows = []
        if base_close_keys:
            vsliders = []
            for k in sorted(base_close_keys):
                handled_keys.add(k)
                lbl = _hsr_clean_label(k, r'^(?:Eye_|0\d_)', keep_variant=False)
                lbl = lbl.replace(' Eye', '').strip() or 'Close'
                sk_L, sk_R = split_bilateral_shapekey_lr(mesh_obj, k, fcx, right)
                if sk_L and sk_R:
                    handled_keys.add(sk_L)
                    handled_keys.add(sk_R)
                    # Viewer's Left = Character's Right (.R), Viewer's Right = Character's Left (.L)
                    vsliders.append({
                        'name': f"CTRL-Panel_{sk_R}",
                        'label': f"{lbl} R",
                        'color': PANEL_COL_EYELID,
                        'group': 'Face Eyelid',
                        'range': 'neg',
                        'drivers': [{'key': sk_R, 'axis': 'Z', 'dir': -1}],
                    })
                    vsliders.append({
                        'name': f"CTRL-Panel_{sk_L}",
                        'label': f"{lbl} L",
                        'color': PANEL_COL_EYELID,
                        'group': 'Face Eyelid',
                        'range': 'neg',
                        'drivers': [{'key': sk_L, 'axis': 'Z', 'dir': -1}],
                    })
                else:
                    vsliders.append({
                        'name': f"CTRL-Panel_{k}",
                        'label': lbl,
                        'color': PANEL_COL_EYELID,
                        'group': 'Face Eyelid',
                        'range': 'neg',
                        'drivers': [{'key': k, 'axis': 'Z', 'dir': -1}],
                    })
            eye_rows.append({'type': 'vsliders_and_pad', 'pad': None, 'vsliders': vsliders, 'v_height': face_size * 0.28})

        if expr_eye_keys:
            eye_variants = {m.group(1) for k in expr_eye_keys for m in [re.search(r'Eye_(0\d)_', k)] if m}
            keep_eye_var = len(eye_variants) > 1
            e_items = []
            for k in sorted(expr_eye_keys):
                handled_keys.add(k)
                lbl = _hsr_clean_label(k, r'^Eye_', keep_variant=keep_eye_var)
                e_items.append({
                    'name': f"CTRL-{k}",
                    'label': lbl,
                    'color': COL_EYE,
                    'group': 'Face Eye Expressions',
                    'drivers': [{'key': k, 'axis': 'X', 'dir': +1}],
                })
            eye_rows.append({'type': 'grid', 'cols': 2, 'items': e_items})

        if eye_rows:
            main_sections.append({'title': 'Eyes', 'rows': eye_rows})

    # --- 2.C MOUTH SECTION (2D Pad + Visemes + Expressions) ---
    has_m00 = any("Mouth_00_" in k for k in mouth_keys)
    has_m01 = any("Mouth_01_" in k for k in mouth_keys)
    primary_m_tag = "Mouth_00_" if has_m00 else ("Mouth_01_" if has_m01 else None)
    secondary_m_tag = "Mouth_01_" if (has_m00 and has_m01) else None

    p_wide   = _hsr_find_key(keyblock, ["Mouth_00_Wide", "Mouth_01_Wide", "Mouth_Wide"], prefer_tag=primary_m_tag)
    p_narrow = _hsr_find_key(keyblock, ["Mouth_00_Narrow", "Mouth_01_Narrow", "Mouth_Narrow"], prefer_tag=primary_m_tag)
    p_up     = _hsr_find_key(keyblock, ["Mouth_00_Up", "Mouth_01_Up", "Mouth_Up"], prefer_tag=primary_m_tag)
    p_down   = _hsr_find_key(keyblock, ["Mouth_00_Down", "Mouth_01_Down", "Mouth_Down"], prefer_tag=primary_m_tag)

    mouth_pad_drv = []
    if p_wide and p_wide not in handled_keys:
        mouth_pad_drv.append({'key': p_wide, 'axis': 'X', 'dir': +1})
        handled_keys.add(p_wide)
    if p_narrow and p_narrow not in handled_keys:
        mouth_pad_drv.append({'key': p_narrow, 'axis': 'X', 'dir': -1})
        handled_keys.add(p_narrow)
    if p_up and p_up not in handled_keys:
        mouth_pad_drv.append({'key': p_up, 'axis': 'Z', 'dir': +1})
        handled_keys.add(p_up)
    if p_down and p_down not in handled_keys:
        mouth_pad_drv.append({'key': p_down, 'axis': 'Z', 'dir': -1})
        handled_keys.add(p_down)

    viseme_sliders = []
    for letter in ("A", "E", "I", "O", "U"):
        pk = _hsr_find_key(
            keyblock,
            [f"Mouth_00_{letter}", f"Mouth_01_{letter}", f"Mouth_{letter}"],
            prefer_tag=primary_m_tag,
        )
        if pk and pk not in handled_keys:
            handled_keys.add(pk)
            viseme_sliders.append({
                'name': f"CTRL-Viseme_{letter}",
                'label': letter,
                'color': PANEL_COL_VISEME,
                'group': 'Face Visemes',
                'drivers': [{'key': pk, 'axis': 'X', 'dir': +1}],
            })

    p_pout = _hsr_find_key(keyblock, ["Mouth_00_Pout", "Mouth_01_Pout", "Mouth_Pout"], prefer_tag=primary_m_tag)
    if p_pout and p_pout not in handled_keys:
        handled_keys.add(p_pout)
        viseme_sliders.append({
            'name': "CTRL-Expr_Pout",
            'label': "Pout",
            'color': PANEL_COL_VISEME,
            'group': 'Face Visemes',
            'drivers': [{'key': p_pout, 'axis': 'X', 'dir': +1}],
        })

    # Remaining primary mouth expressions (non-phoneme)
    primary_mouth_exprs = []
    secondary_mouth_exprs = []
    for k in mouth_keys:
        if k in handled_keys or "phoneme" in k.lower():
            continue
        if secondary_m_tag and secondary_m_tag in k:
            secondary_mouth_exprs.append(k)
        else:
            primary_mouth_exprs.append(k)

    mouth_rows = []
    if mouth_pad_drv or viseme_sliders:
        pad_spec = None
        if mouth_pad_drv:
            pad_spec = {
                'name': 'CTRL-Mouth_Pad',
                'label': 'Shape',
                'edge_labels': ('W', 'N', 'U', 'D'),
                'color': PANEL_COL_MOUTH,
                'group': 'Face Mouth',
                'drivers': mouth_pad_drv,
            }
        mouth_rows.append({
            'type': 'pad_and_sliders',
            'pad': pad_spec,
            'sliders': viseme_sliders,
            'slider_cols': 1,
        })

    if primary_mouth_exprs:
        m_items = []
        for k in sorted(primary_mouth_exprs):
            handled_keys.add(k)
            lbl = _hsr_clean_label(k, r'^Mouth_(?:0\d_)?', keep_variant=False)
            clean_c = _strip_hsr_char_prefix(k).replace("Mouth_00_", "").replace("Mouth_01_", "").replace("Mouth_", "")
            m_items.append({
                'name': f"CTRL-Expr_{clean_c}",
                'label': lbl,
                'color': PANEL_COL_EXPRESSION,
                'group': 'Face Expressions',
                'drivers': [{'key': k, 'axis': 'X', 'dir': +1}],
            })
        mouth_rows.append({'type': 'grid', 'cols': 2, 'items': m_items})

    if mouth_rows:
        mouth_sections.append({'title': 'Mouth', 'rows': mouth_rows})

    # --- 2.D EMOTIONS / ANI PRESETS SECTION (Column 2, below Mouth) ---
    emotion_keys = [
        k for k in all_keys
        if k not in handled_keys
        and ("emotion_" in k.lower() or "_ani_" in k.lower())
    ]
    if emotion_keys:
        emo_items = []
        for k in sorted(emotion_keys):
            handled_keys.add(k)
            lbl = _hsr_clean_label(k, r'^(?:Emotion_|Ani_PhotoGraph_|Ani_Battle_|Ani_)', keep_variant=False)
            emo_items.append({
                'name': f"CTRL-{k}",
                'label': lbl,
                'color': COL_EMOTION,
                'group': 'Face Emotions',
                'drivers': [{'key': k, 'axis': 'X', 'dir': +1}],
            })
        mouth_sections.append({
            'title': 'Emotions',
            'rows': [{'type': 'grid', 'cols': 2, 'items': emo_items}],
        })

    # --- 2.E SECONDARY COLUMN: PHONEMES ---
    phoneme_keys = [k for k in all_keys if "phoneme" in k.lower() and k not in handled_keys]
    primary_ph = [k for k in phoneme_keys if not (secondary_m_tag and secondary_m_tag in k)]
    secondary_ph = [k for k in phoneme_keys if (secondary_m_tag and secondary_m_tag in k)]

    if primary_ph:
        ph_items = []
        for k in sorted(primary_ph):
            handled_keys.add(k)
            idx_p = k.lower().find("phoneme_cn_")
            sub = k[idx_p + len("phoneme_cn_"):] if idx_p != -1 else k
            ph_items.append({
                'name': f"CTRL-ph_{sub}",
                'label': sub,
                'color': COL_PHONEME,
                'group': 'Face Phonemes',
                'drivers': [{'key': k, 'axis': 'X', 'dir': +1}],
            })
        side_sections.append({
            'title': 'Phonemes',
            'rows': [{'type': 'grid', 'cols': 2, 'items': ph_items}],
        })

    # --- 2.F SECONDARY COLUMN: MOUTH ALT (when model has both Mouth_00_ and Mouth_01_) ---
    if secondary_mouth_exprs or secondary_ph:
        alt_items = []
        for k in sorted(secondary_mouth_exprs + secondary_ph):
            handled_keys.add(k)
            lbl = _hsr_clean_label(k, r'^Mouth_(?:0\d_)?(?:Phoneme_cn_)?', keep_variant=False)
            alt_items.append({
                'name': f"CTRL-{k}",
                'label': lbl,
                'color': COL_EXTRA,
                'group': 'Face Mouth Alt',
                'drivers': [{'key': k, 'axis': 'X', 'dir': +1}],
            })
        side_sections.append({
            'title': 'Mouth Alt',
            'rows': [{'type': 'grid', 'cols': 2, 'items': alt_items}],
        })

    # --- 2.G EXTRA FALLBACK (any remaining shapekeys) ---
    remaining = [k for k in all_keys if k not in handled_keys]
    if remaining:
        rem_items = []
        for k in sorted(remaining):
            handled_keys.add(k)
            rem_items.append({
                'name': f"CTRL-{k}",
                'label': _strip_hsr_char_prefix(k).replace('_', ' '),
                'color': COL_EXTRA,
                'group': 'Face Extra Keys',
                'drivers': [{'key': k, 'axis': 'X', 'dir': +1}],
            })
        target_sec_list = side_sections if side_sections else main_sections
        target_sec_list.append({
            'title': 'Extra',
            'rows': [{'type': 'grid', 'cols': 2, 'items': rem_items}],
        })

    panel_columns = []
    if main_sections:
        panel_columns.append({'title': 'Brows & Eyes', 'sections': main_sections})
    if mouth_sections:
        panel_columns.append({'title': 'Mouth', 'sections': mouth_sections})
    if side_sections:
        panel_columns.append({'title': 'Phonemes & Extra', 'sections': side_sections})

    if panel_columns and wgt_coll is not None:
        # Place panel cleanly to the viewer's right (+right) of the head, aligned with Lighting Panel height
        panel_origin = fcx + right * (face_size * 2.35) + up * (face_size * 0.72) + fwd * (face_size * 0.05)
        _, panel_ctrls = build_shape_keys_panel(
            panel_columns=panel_columns,
            origin_world=panel_origin,
            right=right,
            up=up,
            fwd=fwd,
            face_size=face_size,
            wgt_coll=wgt_coll,
            game_tag="HSR",
            unique_tag=unique_tag,
            collection_name=FACERIG_COLLECTION,
            armature=armature,
            face_center=fcx,
        )
        controls.extend(panel_ctrls)

    return controls


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

        # Rotate mesh vertices so text stands upright facing the front camera
        # Text X (width) -> Bone -X (which is +X in world)
        # Text Y (height) -> Bone +Z (which is +Z in world)
        # Text Z (normal) -> Bone Y (0 depth)
        for v in mesh_from_eval.vertices:
            v.co = Vector((-v.co.x, 0.0, v.co.y))

        bpy.context.scene.collection.objects.unlink(temp_obj)
        bpy.data.objects.remove(temp_obj, do_unlink=True)
        bpy.data.curves.remove(curve_data, do_unlink=True)

        wgt_obj = bpy.data.objects.new(name, mesh_from_eval)
        wgt_coll.objects.link(wgt_obj)
        return wgt_obj
    except Exception as ex:
        # Fallback wireframe bounding box with center line
        s_w = max(1.0, len(text_string) * 0.4)
        s_h = 0.5
        verts = [(-s_w, 0, -s_h), (s_w, 0, -s_h), (s_w, 0, s_h), (-s_w, 0, s_h)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, edges, [])
        wgt_obj = bpy.data.objects.new(name, mesh)
        wgt_coll.objects.link(wgt_obj)
        return wgt_obj


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
        if b.name.startswith("CTRL-") or b.name.startswith("LABEL-") or b.name in ("Face-Root", "FacePanel-Root", "FacePanel-Board"):
            eb.remove(b)
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in list(bpy.data.objects):
        if o.name.startswith("WGT-Face_"):
            bpy.data.objects.remove(o, do_unlink=True)


def get_widget_collection(name="WGTS_FaceRig"):
    # Prefer per-character WGTS_<Char> (Append-safe): resolve from active/selected rig
    try:
        from setup_wizard.ui.character_settings_utils import resolve_settings_armature, resolve_character_name
        arm = resolve_settings_armature(bpy.context)
        if arm is not None:
            char_name = resolve_character_name(arm)
            if char_name:
                per_char = bpy.data.collections.get(f"WGTS_{char_name}")
                if per_char is not None:
                    return per_char
                # If the rig already lives in a character collection, create nested WGTS there
                try:
                    from setup_wizard.character_rig_setup.wgts_isolation import get_or_create_char_wgts, get_char_collection
                    char_coll = get_char_collection(arm, char_name)
                    if char_coll is not None:
                        return get_or_create_char_wgts(char_coll, char_name)
                except Exception:
                    pass
    except Exception:
        pass
    for name_candidate in ("WGTS", "wgt", "WGTS_FaceRig"):
        coll = bpy.data.collections.get(name_candidate)
        if coll:
            return coll

    for c in bpy.data.collections:
        c_low = c.name.lower()
        if "wgts" in c_low or "wgt" in c_low:
            return c

    coll = bpy.data.collections.new(name)
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


def setup_hsr_face_rig(mesh_obj, controls, armature, head_name, fwd, up, face_size, keyblock):
    print(f"Building {len(controls)} HSR face controls on '{armature.name}' under '{head_name}'")

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
        # Panel-space bones point into -fwd (+Y screen depth) so local +X = viewer right and +Z = up
        axis_dir = (-fwd_arm) if c.get('panel_space') else fwd_arm
        b.tail = h + axis_dir * bone_len
        b.use_deform = False
        try:
            b.align_roll(up_arm)
        except Exception:
            pass
        par_name = c.get('parent_bone')
        b.parent = (eb.get(par_name) if par_name else None) or root
        b.use_connect = False

    bpy.ops.object.mode_set(mode='OBJECT')

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
                coll.assign(bone)

    wgt_coll = get_widget_collection()
    bpy.ops.object.mode_set(mode='POSE')
    color_cache = {}

    for c in controls:
        pb = armature.pose.bones.get(c['name'])
        if not pb:
            continue

        is_lbl = c.get('is_label', False)
        is_panel_root = c.get('is_panel_root', False)
        is_panel_board = c.get('is_panel_board', False)

        if is_panel_root:
            # Movable and scalable panel root handle; keep upright by locking rotation
            pb.lock_location = (False, False, False)
            pb.lock_rotation = (True, True, True)
            pb.lock_rotation_w = True
            pb.lock_scale = (False, False, False)
        elif is_lbl or is_panel_board:
            # Lock all transforms for non-interactive labels and wireframe board
            for i in range(3):
                pb.lock_location[i] = True
                pb.lock_rotation[i] = True
                pb.lock_scale[i] = True
            pb.lock_rotation_w = True
            if is_panel_board:
                b_data = armature.data.bones.get(c['name'])
                if b_data:
                    b_data.hide_select = True
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

        if c.get('widget_obj') is not None:
            pb.custom_shape = c['widget_obj']
        elif c.get('widget', '').startswith('text:'):
            text_str = c['widget'].split(':', 1)[1]
            pb.custom_shape = make_text_widget(text_str, wgt_coll)
        else:
            pb.custom_shape = make_widget(c['widget'], wgt_coll)

        try:
            pb.use_custom_shape_bone_size = False
        except Exception:
            pass
        if c.get('custom_shape_translation') is not None:
            try:
                pb.custom_shape_translation = c['custom_shape_translation']
            except Exception:
                pass
        ss = c.get('shape_scale')
        pb.custom_shape_scale_xyz = ss if ss is not None else Vector((c.get('lim', 0.02) * WIDGET_F,) * 3)

        apply_color(armature, pb, c['group'], c['color'], color_cache)

    bpy.ops.object.mode_set(mode='OBJECT')

    # Build Drivers on Shape Keys
    agg = {}
    for c in controls:
        for d in c.get('drivers', []):
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
            vn = f"v{i}"
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
                terms.append(f"{sign}{vn} / {e['lim']!r}")
            else:
                terms.append(f"max(0.0, {sign}{vn} / {e['lim']!r})")
        drv.expression = terms[0] if len(terms) == 1 else "max(" + ", ".join(terms) + ")"

    # Hide stick facial bones, extra bones, tweak collections, FK collections, Fingers (Detail), and Face-Root
    hidden_colls = [
        "DEF", "ORG", "MCH", "Face", "Face (Secondary)", "Face (Primary)", "Face (Tweaks)", "Face Bones", "Face_Bones",
        "Extra Bones", "Extra_Bones", "Extra",
        "Torso (Tweak)", "Arm.L (Tweak)", "Arm.R (Tweak)", "Leg.L (Tweak)", "Leg.R (Tweak)",
        "Arm.L (FK)", "Arm.R (FK)", "Leg.L (FK)", "Leg.R (FK)",
        "Fingers (Detail)"
    ]
    for cn in hidden_colls:
        c = armature.data.collections.get(cn)
        if c:
            try:
                c.is_visible = False
            except Exception:
                pass

    palms_coll = armature.data.collections.get("Palms")
    if palms_coll:
        palms_coll.is_visible = True

    # Create visible "Face" collection for eye/face control bones
    facerig_coll = armature.data.collections.get("Face") or armature.data.collections.get("Facerig") or armature.data.collections.new("Face")
    facerig_coll.is_visible = True

    eye_ctrl_bone_names = ["Eye-Track-Master", "Eye-Track.L", "Eye-Track.R"]
    for bname in eye_ctrl_bone_names:
        if bname in armature.data.bones:
            b = armature.data.bones[bname]
            try:
                facerig_coll.assign(b)
                b.hide = False
            except Exception:
                pass

    # Hide helper tracking bones (+EyeBone L/R A01.001)
    for bname in ["+EyeBone L A01.001", "+EyeBone R A01.001"]:
        if bname in armature.data.bones:
            try:
                armature.data.bones[bname].hide = True
            except Exception:
                pass

    face_bones_coll = armature.data.collections.get("Face Bones") or armature.data.collections.new("Face Bones")
    face_bones_coll.is_visible = False

    extra_bones_coll = armature.data.collections.get("Extra Bones") or armature.data.collections.new("Extra Bones")
    extra_bones_coll.is_visible = False

    face_keywords = [
        "joint_", "brow", "eye", "eyelid", "cheek", "nose", 
        "mouth", "lip", "jaw", "teeth", "tongue", "skn", "face-root"
    ]
    main_ctrls = ["root", "torso", "hips", "chest", "neck", "head"]

    for bone in armature.data.bones:
        b_name = bone.name
        b_low = b_name.lower()
        if b_name.startswith("CTRL-") or b_name.startswith("LABEL-") or b_name in ("FacePanel-Root", "FacePanel-Board") or b_name in main_ctrls or b_name in eye_ctrl_bone_names:
            continue

        is_face_bone = any(kw in b_low for kw in face_keywords)
        target_coll = face_bones_coll if is_face_bone else extra_bones_coll

        if is_face_bone or b_low.startswith("def-") or b_low.startswith("org-") or b_low.startswith("mch-") or len(bone.collections) == 0:
            try:
                target_coll.assign(bone)
            except Exception:
                pass
            for c in list(bone.collections):
                if c != target_coll and c != facerig_coll and c.name not in hidden_colls:
                    try:
                        c.unassign(bone)
                    except Exception:
                        pass
            bone.hide = True

    # Set up dynamic Y location drivers for eye bones driven by eye shape key activation (up to -0.0040 max offset)
    setup_dynamic_eye_y_drivers(mesh_obj, armature, max_offset=-0.0040)

    print("HSR Face rig build complete.")


def setup_dynamic_eye_y_drivers(mesh_obj, armature, max_offset=-0.0040):
    """
    Drives eye.L and eye.R Y location backwards up to max_offset (-0.0040)
    proportionally when eye expression/close shape keys are activated by the facial rig.
    Replaces static fixed eye location offset hack.
    """
    candidate_eye_L = ["eye.L", "DEF-eye.L", "+EyeBone L A01", "+EyeBone L A02", "EYE_L", "Eye_L"]
    candidate_eye_R = ["eye.R", "DEF-eye.R", "+EyeBone R A01", "+EyeBone R A02", "EYE_R", "Eye_R"]

    eye_L_pbone = next((armature.pose.bones.get(b) for b in candidate_eye_L if armature.pose.bones.get(b)), None)
    eye_R_pbone = next((armature.pose.bones.get(b) for b in candidate_eye_R if armature.pose.bones.get(b)), None)

    # Reset any static pose location offsets
    if eye_L_pbone:
        eye_L_pbone.location = (0.0, 0.0, 0.0)
    if eye_R_pbone:
        eye_R_pbone.location = (0.0, 0.0, 0.0)

    if not mesh_obj or not mesh_obj.data or not mesh_obj.data.shape_keys:
        return

    keyblock = mesh_obj.data.shape_keys.key_blocks
    sk_id = mesh_obj.data.shape_keys

    eye_sk_L = []
    eye_sk_R = []

    for k_name in keyblock.keys():
        kl = k_name.lower()
        if "default" in kl or kl == "basis":
            continue
        # Only select eye shape keys (excluding brow/mouth)
        if any(kw in kl for kw in ["eye", "wink"]) and not any(ex in kl for ex in ["brow", "mouth"]):
            is_r_only = kl.endswith("_r") or kl.endswith(".r") or kl.endswith("right") or "_r_" in kl
            is_l_only = kl.endswith("_l") or kl.endswith(".l") or kl.endswith("left") or "_l_" in kl

            if not is_r_only:
                eye_sk_L.append(k_name)
            if not is_l_only:
                eye_sk_R.append(k_name)

    def attach_driver(pbone, sk_list):
        if not pbone or not sk_list:
            return
        try:
            pbone.driver_remove("location", 1)
        except Exception:
            pass

        driver_obj = pbone.driver_add("location", 1)
        drv = driver_obj.driver
        drv.type = 'SCRIPTED'

        var_names = []
        for i, sk_name in enumerate(sk_list):
            vn = f"v{i}"
            var = drv.variables.new()
            var.name = vn
            var.type = 'SINGLE_PROP'
            tgt = var.targets[0]
            try:
                tgt.id_type = 'KEY'
            except Exception:
                pass
            tgt.id = sk_id
            tgt.data_path = f'key_blocks["{sk_name}"].value'
            var_names.append(vn)

        if len(var_names) == 1:
            drv.expression = f"{max_offset!r} * max(0.0, min(1.0, {var_names[0]}))"
        else:
            terms_str = ", ".join(var_names)
            drv.expression = f"{max_offset!r} * max(0.0, min(1.0, max({terms_str})))"

    if eye_L_pbone:
        attach_driver(eye_L_pbone, eye_sk_L)
    if eye_R_pbone:
        attach_driver(eye_R_pbone, eye_sk_R)


def _find_hsr_face_mesh(armature=None):
    def _is_hsr_face(obj):
        if obj.type != 'MESH' or obj.name not in bpy.context.view_layer.objects:
            return False
        if not obj.data or not obj.data.shape_keys:
            return False
        n = obj.name.lower()
        return "face" in n or any(
            k.startswith(("Mouth_", "Brow_", "Eye_"))
            for k in obj.data.shape_keys.key_blocks.keys()
        )

    if armature is not None:
        # Prefer meshes directly deformed by or parented to the target armature
        arm_meshes = []
        for obj in bpy.data.objects:
            if not _is_hsr_face(obj):
                continue
            has_mod = any(m.type == 'ARMATURE' and m.object == armature for m in obj.modifiers)
            if has_mod or obj.parent == armature:
                arm_meshes.append(obj)
        if arm_meshes:
            return next((o for o in arm_meshes if "face" in o.name.lower()), arm_meshes[0])

        arm_colls = set(armature.users_collection)
        for obj in bpy.data.objects:
            if _is_hsr_face(obj) and (arm_colls & set(obj.users_collection)):
                return obj

    for obj in bpy.data.objects:
        if _is_hsr_face(obj):
            return obj
    return None


def hsr_face_rig_main(armature=None, faceobj=None):
    if faceobj is None:
        faceobj = _find_hsr_face_mesh(armature=armature)

    if faceobj is None:
        print("HSR Face Rig: No face mesh found.")
        return 0
    if faceobj.data.shape_keys is None:
        print("HSR Face Rig: Face mesh has no shape keys.")
        return 0

    from setup_wizard.utils.hsr_expression_reference import rebase_baked_expressions
    rebased = rebase_baked_expressions(faceobj)
    if rebased:
        print(f'HSR Face Rig: restored neutral references for {rebased} baked expressions.')

    keyblock = faceobj.data.shape_keys.key_blocks
    resolved_armature, head_name = find_armature_and_head(faceobj)
    if armature is None:
        armature = resolved_armature
    fwd, right, up, face_size = face_frame(faceobj)

    if CLEAN_REBUILD:
        purge_previous(armature)

    wgt_coll = get_widget_collection()
    controls = plan_hsr_controls(faceobj, fwd, right, up, face_size, keyblock, wgt_coll=wgt_coll, unique_tag=armature.name, armature=armature)

    if not controls:
        print("HSR Face Rig: No drivable shape keys found.")
        return 0

    setup_hsr_face_rig(faceobj, controls, armature, head_name, fwd, up, face_size, keyblock)

    finalize_widget_collection(wgt_coll)

    print(f"\nHSR Face Rig complete: {len(controls)} controls built on '{armature.name}'.\n")
    return len(controls)


class HSR_OT_CreateShapekeyPanel(bpy.types.Operator):
    """Creates or rebuilds the 3D facial shapekey control panel for an HSR character"""
    bl_idname = "honkai_star_rail.create_shapekey_panel"
    bl_label = "Create Shapekey Panel"
    bl_description = "Creates or rebuilds the 3D facial shapekey control panel for the selected HSR character"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from setup_wizard.character_rig_setup.rig_ui_utils import find_target_armature
        armature = find_target_armature(context)
        faceobj = None
        active = context.active_object
        if active and active.type == 'MESH' and active.data and active.data.shape_keys:
            if "face" in active.name.lower():
                faceobj = active
                if armature is None:
                    for m in active.modifiers:
                        if m.type == 'ARMATURE' and m.object:
                            armature = m.object
                            break

        try:
            count = hsr_face_rig_main(armature=armature, faceobj=faceobj)
        except Exception as ex:
            self.report({'ERROR'}, f"Failed to create HSR Shapekey Panel: {ex}")
            return {'CANCELLED'}

        if not count:
            self.report({'WARNING'}, "No HSR face mesh with drivable shape keys found.")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Created HSR Shapekey Panel ({count} controls).")
        return {'FINISHED'}
