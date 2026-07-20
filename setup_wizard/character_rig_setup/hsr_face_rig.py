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
FACERIG_COLLECTION = "Facerig"
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


def plan_hsr_controls(mesh_obj, fwd, right, up, face_size, keyblock):
    OFFSET = face_size * OFFSET_F
    LIM = face_size * TRAVEL_F
    SPACING = face_size * SPACING_F

    def place(feature, h=0.0, v=0.0):
        return feature + fwd * OFFSET + right * h + up * v

    controls = []

    mouth_keys = [k for k in keyblock.keys() if k.startswith("Mouth_01_")]
    mouth = feature_centroid(mesh_obj, mouth_keys)
    eye = feature_centroid(mesh_obj, ["00_Close01_Eye", "00_Default_Eye"])

    fcx = mesh_obj.matrix_world @ (0.125 * sum((Vector(c) for c in mesh_obj.bound_box), Vector()))
    if mouth is None:
        mouth = fcx - up * face_size * 0.12
    if eye is None:
        eye = fcx + up * face_size * 0.10

    mouth = mouth + up * (face_size * MOUTH_RAISE_F)
    tri_scale = Vector((face_size * TRI_F,) * 3)

    # 1. Eye Close Control
    if "00_Close01_Eye" in keyblock:
        controls.append({
            'name': 'CTRL-Eye_Close',
            'collection': FACERIG_COLLECTION,
            'color': COL_EYELID,
            'group': 'Face Eyelid',
            'head': place(eye, v=face_size * 0.05),
            'widget': 'triangle_down',
            'lim': LIM,
            'free': ('Z',),
            'range': 'neg',
            'shape_scale': tri_scale,
            'drivers': [{'key': "00_Close01_Eye", 'axis': 'Z', 'dir': -1}]
        })

    # 2. Mouth Shift Pad (Driving Mouth_01_Up, Down, Wide, Narrow)
    drv_shift = []
    if "Mouth_01_Wide" in keyblock:
        drv_shift.append({'key': "Mouth_01_Wide", 'axis': 'X', 'dir': +1})
    if "Mouth_01_Narrow" in keyblock:
        drv_shift.append({'key': "Mouth_01_Narrow", 'axis': 'X', 'dir': -1})
    if "Mouth_01_Up" in keyblock:
        drv_shift.append({'key': "Mouth_01_Up", 'axis': 'Z', 'dir': +1})
    if "Mouth_01_Down" in keyblock:
        drv_shift.append({'key': "Mouth_01_Down", 'axis': 'Z', 'dir': -1})

    if drv_shift:
        mouth_scale = Vector((LIM * 0.9, LIM, LIM * 0.4))
        controls.append({
            'name': 'CTRL-Mouth-Shift',
            'collection': FACERIG_COLLECTION,
            'color': COL_MOUTH,
            'group': 'Face Mouth',
            'head': place(mouth),
            'widget': 'pad',
            'lim': LIM,
            'free': ('X', 'Z'),
            'range': 'both',
            'shape_scale': mouth_scale,
            'drivers': drv_shift
        })

    # 3. Visemes Row (A, E, I, O, U)
    viseme_keys = ["Mouth_01_A", "Mouth_01_E", "Mouth_01_I", "Mouth_01_O", "Mouth_01_U"]
    active_visemes = [k for k in viseme_keys if k in keyblock]
    if active_visemes:
        n = len(active_visemes)
        for i, k in enumerate(active_visemes):
            h = (i - (n - 1) / 2.0) * SPACING
            short_name = k.replace("Mouth_01_", "")
            controls.append({
                'name': f'CTRL-Viseme_{short_name}',
                'collection': FACERIG_COLLECTION,
                'color': COL_VISEME,
                'group': 'Face Visemes',
                'head': place(mouth, h=h, v=-face_size * 0.08),
                'widget': 'slider',
                'lim': LIM,
                'free': ('Z',),
                'range': 'pos',
                'drivers': [{'key': k, 'axis': 'Z', 'dir': +1}]
            })

    # 4. Expressions Row (Smile, Angry, Pain, Worry, Proud, Twisted, Pout)
    expr_candidates = [
        "Mouth_01_Smile01", "Mouth_01_Smile02", "Mouth_01_Smile03", "Mouth_01_Smile04",
        "Mouth_01_Angry01", "Mouth_01_Angry02", "Mouth_01_Angry03", "Mouth_01_Angry04",
        "Mouth_01_Pain01", "Mouth_01_Pain02", "Mouth_01_Pain03", "Mouth_01_Pain04",
        "Mouth_01_Worry01", "Mouth_01_Worry02", "Mouth_01_Worry03", "Mouth_01_Worry04",
        "Mouth_01_Proud01", "Mouth_01_Proud02",
        "Mouth_01_Twisted01", "Mouth_01_Twisted02",
        "Mouth_01_Pout"
    ]
    active_expr = [k for k in expr_candidates if k in keyblock]
    if active_expr:
        n = len(active_expr)
        expr_spacing = min(SPACING, face_size * 0.035)
        for i, k in enumerate(active_expr):
            h = (i - (n - 1) / 2.0) * expr_spacing
            short_name = k.replace("Mouth_01_", "")
            controls.append({
                'name': f'CTRL-Expr_{short_name}',
                'collection': FACERIG_COLLECTION,
                'color': COL_EXPRESSION,
                'group': 'Face Expressions',
                'head': place(mouth, h=h, v=-face_size * 0.14),
                'widget': 'slider',
                'lim': LIM,
                'free': ('Z',),
                'range': 'pos',
                'drivers': [{'key': k, 'axis': 'Z', 'dir': +1}]
            })

    # 5. Phonemes Row (cn_*)
    phoneme_keys = [k for k in keyblock.keys() if k.startswith("Mouth_01_Phoneme_cn_")]
    if phoneme_keys:
        n = len(phoneme_keys)
        ph_spacing = min(SPACING, face_size * 0.025)
        for i, k in enumerate(phoneme_keys):
            h = (i - (n - 1) / 2.0) * ph_spacing
            short_name = k.replace("Mouth_01_Phoneme_cn_", "ph_")
            controls.append({
                'name': f'CTRL-{short_name}',
                'collection': FACERIG_COLLECTION,
                'color': COL_CORNER,
                'group': 'Face Phonemes',
                'head': place(mouth, h=h, v=-face_size * 0.20),
                'widget': 'slider',
                'lim': LIM,
                'free': ('Z',),
                'range': 'pos',
                'drivers': [{'key': k, 'axis': 'Z', 'dir': +1}]
            })

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
        if b.name.startswith("CTRL-") or b.name == "Face-Root":
            eb.remove(b)
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in list(bpy.data.objects):
        if o.name.startswith("WGT-Face_"):
            bpy.data.objects.remove(o, do_unlink=True)


def get_widget_collection(name="WGTS_FaceRig"):
    wgt = bpy.data.collections.get("wgt")
    if wgt:
        return wgt
    for c in bpy.data.collections:
        if "WGTS" in c.name:
            return c
    coll = bpy.data.collections.get(name)
    if not coll:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


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
        b.tail = h + fwd_arm * bone_len
        b.use_deform = False
        try:
            b.align_roll(up_arm)
        except Exception:
            pass
        b.parent = root
        b.use_connect = False

    bpy.ops.object.mode_set(mode='OBJECT')

    coll_names = [c['collection'] for c in controls if c['collection']]
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
            coll = armature.data.collections.get(c['collection'])
            if bone and coll:
                coll.assign(bone)

    wgt_coll = get_widget_collection()
    bpy.ops.object.mode_set(mode='POSE')
    color_cache = {}

    for c in controls:
        pb = armature.pose.bones.get(c['name'])
        if not pb:
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

    # Build Drivers on Shape Keys
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
        if b_name.startswith("CTRL-") or b_name in main_ctrls:
            continue

        is_face_bone = any(kw in b_low for kw in face_keywords)
        target_coll = face_bones_coll if is_face_bone else extra_bones_coll

        if is_face_bone or b_low.startswith("def-") or b_low.startswith("org-") or b_low.startswith("mch-") or len(bone.collections) == 0:
            try:
                target_coll.assign(bone)
            except Exception:
                pass
            for c in list(bone.collections):
                if c != target_coll and c.name not in hidden_colls:
                    try:
                        c.unassign(bone)
                    except Exception:
                        pass
            bone.hide = True

    print("HSR Face rig build complete.")


def hsr_face_rig_main():
    faceobj = None
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.name in bpy.context.view_layer.objects:
            n = obj.name.lower()
            if "face" in n or (obj.data.shape_keys and any(k.startswith("Mouth_01_") for k in obj.data.shape_keys.key_blocks.keys())):
                faceobj = obj
                break

    if faceobj is None:
        print("HSR Face Rig: No face mesh found.")
        return
    if faceobj.data.shape_keys is None:
        print("HSR Face Rig: Face mesh has no shape keys.")
        return

    keyblock = faceobj.data.shape_keys.key_blocks
    armature, head_name = find_armature_and_head(faceobj)
    fwd, right, up, face_size = face_frame(faceobj)
    controls = plan_hsr_controls(faceobj, fwd, right, up, face_size, keyblock)

    if not controls:
        print("HSR Face Rig: No drivable shape keys found.")
        return

    if CLEAN_REBUILD:
        purge_previous(armature)

    setup_hsr_face_rig(faceobj, controls, armature, head_name, fwd, up, face_size, keyblock)
    print(f"\nHSR Face Rig complete: {len(controls)} controls built on '{armature.name}'.\n")
