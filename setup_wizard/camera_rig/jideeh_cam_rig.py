# Jideeh's CamRig for Blender / Gacha Setup
# Compatible with Blender 3.0+ / 4.x / Goo Engine 4.4 / 5.2+

import bpy
import math
from mathutils import Vector, Matrix

COLL_NAME = "Camera Pro"
WGT_COLL_NAME = "Camera Pro Widgets"
RIG_NAME = "Camera Pro"
CON_AIM = "CamRig Aim"
CON_FACE = "CamRig Face"
CON_SLIDE = "CamRig Slide"
P_TRACK = "Track To"
AIM_DIST = 5.0
HUD_DIST = 2.0
FRAME_FIT = 0.34
SHAKE_MAX = math.radians(2.2)
FREQ_MIN = 0.12
FREQ_MAX = 1.05

WHITE = (1.00, 1.00, 1.00)
YELLOW = (1.00, 0.80, 0.10)
ORANGE = (1.00, 0.48, 0.12)
PURPLE = (0.62, 0.36, 0.95)

MCH_BONES = ("MCH_PIV_AIM", "MCH_PIVOT", "MCH_TRACK", "MCH_ROLL", "MCH_SHAKE", "MCH_HUD")


def _poly(v, e, pts, closed=True):
    base = len(v)
    for p in pts:
        v.append((p[0], 0.0, p[1]))
    n = len(pts)
    for k in range(n - 1):
        e.append((base + k, base + k + 1))
    if closed and n > 2:
        e.append((base + n - 1, base))


def _seg(v, e, p0, p1):
    base = len(v)
    v.append((p0[0], 0.0, p0[1]))
    v.append((p1[0], 0.0, p1[1]))
    e.append((base, base + 1))


def _fill(v, f, pts):
    area = 0.0
    n = len(pts)
    for k in range(n):
        x0, z0 = pts[k]
        x1, z1 = pts[(k + 1) % n]
        area += x0 * z1 - x1 * z0
    seq = tuple(pts) if area > 0.0 else tuple(reversed(pts))
    base = len(v)
    for p in seq:
        v.append((p[0], 0.0, p[1]))
    f.append([base + k for k in range(len(seq))])


def _corner_art(v, e, f, hx, hz, arm_x, arm_z, th, filled):
    for sx, sz in ((1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0), (1.0, -1.0)):
        ox = hx * sx
        oz = hz * sz
        pts = (
            (ox, oz),
            (ox - arm_x * sx, oz),
            (ox - arm_x * sx, oz - th * sz),
            (ox - th * sx, oz - th * sz),
            (ox - th * sx, oz - arm_z * sz),
            (ox, oz - arm_z * sz),
        )
        if filled:
            _fill(v, f, pts)
        else:
            _poly(v, e, pts)


def _meter_art(v, e, ox, oz, length, horizontal, side, ticks, major, t_minor, t_major):
    half = length * 0.5

    def pt(along, across):
        if horizontal:
            return (ox + along, oz + across * side)
        return (ox + across * side, oz + along)

    _seg(v, e, pt(-half, 0.0), pt(half, 0.0))
    for k in range(ticks + 1):
        a = -half + length * k / ticks
        _seg(v, e, pt(a, 0.0), pt(a, t_major if k % major == 0 else t_minor))


def _arc_art(v, e, ox, oz, length, depth, steps):
    half = length * 0.5
    pts = []
    for k in range(steps + 1):
        t = -half + length * k / steps
        pts.append((ox + t, oz - depth * (t / half) * (t / half)))
    _poly(v, e, pts, False)


def _reticle_widget(half, arm, th):
    v = []
    e = []
    f = []
    _corner_art(v, e, f, half, half, arm, arm, th, False)
    return v, e, f


def _focus_widget(radius, th, seg):
    v = []
    e = []
    for r in (radius, radius + th):
        pts = []
        for k in range(seg):
            a = 2.0 * math.pi * k / seg
            pts.append((r * math.cos(a), r * math.sin(a)))
        _poly(v, e, pts)
    return v, e, []


def _body_widget(w, h, back):
    v = []
    e = []
    _poly(v, e, ((-w, -h), (w, -h), (w, h), (-w, h)))
    _seg(v, e, (-w * 0.45, h), (0.0, h * 1.7))
    _seg(v, e, (0.0, h * 1.7), (w * 0.45, h))
    return [(p[0], -back, p[2]) for p in v], e, []


def _sphere_widget(radius, seg):
    v = []
    e = []
    for plane in range(3):
        base = len(v)
        for k in range(seg):
            a = 2.0 * math.pi * k / seg
            c = radius * math.cos(a)
            s = radius * math.sin(a)
            if plane == 0:
                v.append((c, s, 0.0))
            elif plane == 1:
                v.append((c, 0.0, s))
            else:
                v.append((0.0, c, s))
        for k in range(seg):
            e.append((base + k, base + (k + 1) % seg))
    return v, e, []


def _root_widget(radius, band, ang_w, arrow_len, seg):
    v = []
    e = []
    base = len(v)
    inner = radius - band
    for k in range(seg):
        a = 2.0 * math.pi * k / seg
        v.append((inner * math.cos(a), inner * math.sin(a), 0.0))
    for k in range(seg):
        e.append((base + k, base + (k + 1) % seg))
    pts = []
    steps = max(seg // 4, 5)
    for q in range(4):
        a0 = q * math.pi * 0.5 + ang_w
        a1 = (q + 1) * math.pi * 0.5 - ang_w
        for k in range(steps + 1):
            a = a0 + (a1 - a0) * k / steps
            pts.append((radius * math.cos(a), radius * math.sin(a)))
        tip = (q + 1) * math.pi * 0.5
        pts.append(((radius + arrow_len) * math.cos(tip),
                    (radius + arrow_len) * math.sin(tip)))
    base = len(v)
    for p in pts:
        v.append((p[0], p[1], 0.0))
    n = len(pts)
    for k in range(n):
        e.append((base + k, base + (k + 1) % n))
    return v, e, []


def _tri_widget(w, h, horizontal):
    v = []
    f = []
    if horizontal:
        _fill(v, f, ((0.0, 0.0), (-w, h), (w, h)))
    else:
        _fill(v, f, ((0.0, 0.0), (h, -w), (h, w)))
    return v, [], f


def _box_widget(w, h):
    v = []
    e = []
    _poly(v, e, ((-w, -h), (w, -h), (w, h), (-w, h)))
    return v, e, []


def _plate_widget(w, h):
    v = []
    f = []
    _fill(v, f, ((-w, -h), (w, -h), (w, h), (-w, h)))
    return v, [], f


def _gauge_widget(w, h, vertical):
    v = []
    f = []
    if vertical:
        _fill(v, f, ((-w, 0.0), (w, 0.0), (w, h), (-w, h)))
    else:
        _fill(v, f, ((0.0, -h), (w, -h), (w, h), (0.0, h)))
    return v, [], f


def _dof_widget(w, h, th, ft):
    v = []
    f = []
    ring = (
        (-w, -h), (w, -h), (w, h), (-w, h),
        (-w + th, -h + th), (w - th, -h + th), (w - th, h - th), (-w + th, h - th),
    )
    base = len(v)
    for p in ring:
        v.append((p[0], 0.0, p[1]))
    for k in range(4):
        n = (k + 1) % 4
        f.append([base + k, base + n, base + 4 + n, base + 4 + k])
    fx = -w * 0.34
    top = h * 0.46
    bot = -h * 0.46
    bar_a = w * 0.44
    bar_b = w * 0.30
    _fill(v, f, (
        (fx, bot),
        (fx + ft, bot),
        (fx + ft, -ft * 0.5),
        (fx + ft + bar_b, -ft * 0.5),
        (fx + ft + bar_b, ft * 0.5),
        (fx + ft, ft * 0.5),
        (fx + ft, top - ft),
        (fx + ft + bar_a, top - ft),
        (fx + ft + bar_a, top),
        (fx, top),
    ))
    return v, [], f


def _bone_flag(rig, name, attr, state):
    if bpy.app.version >= (5, 0, 0):
        holders = (rig.pose.bones.get(name), rig.data.bones.get(name))
    else:
        holders = (rig.data.bones.get(name), rig.pose.bones.get(name))
    for holder in holders:
        if holder is None:
            continue
        try:
            setattr(holder, attr, state)
            return True
        except (AttributeError, TypeError):
            continue
    return False


def _set_active_bone(rig, name):
    for owner, coll in ((rig.data.bones, rig.data.bones),
                        (rig.pose.bones, rig.pose.bones)):
        try:
            owner.active = coll[name]
            return True
        except (AttributeError, TypeError, KeyError, RuntimeError):
            continue
    return False


def _purge_object(name):
    ob = bpy.data.objects.get(name)
    if ob is None:
        return
    data = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if data is None or data.users:
        return
    if isinstance(data, bpy.types.Mesh):
        bpy.data.meshes.remove(data)
    elif isinstance(data, bpy.types.Armature):
        bpy.data.armatures.remove(data)


def _rig_collection(scene):
    coll = bpy.data.collections.get(COLL_NAME)
    if coll is None:
        coll = bpy.data.collections.new(COLL_NAME)
    if coll.name not in scene.collection.children:
        try:
            scene.collection.children.link(coll)
        except RuntimeError:
            pass
    return coll


def _widget_collection(parent):
    coll = bpy.data.collections.get(WGT_COLL_NAME)
    if coll is None:
        coll = bpy.data.collections.new(WGT_COLL_NAME)
    if coll.name not in parent.children:
        try:
            parent.children.link(coll)
        except RuntimeError:
            pass
    return coll


def _layer_collection(root, target):
    if root.collection == target:
        return root
    for child in root.children:
        found = _layer_collection(child, target)
        if found is not None:
            return found
    return None


def _set_excluded(view_layer, coll, state):
    lc = _layer_collection(view_layer.layer_collection, coll)
    if lc is not None:
        lc.exclude = state


def _move_to(ob, coll):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)


def _mesh_object(name, verts, edges, faces, coll):
    _purge_object(name)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, edges, faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.hide_render = True
    ob.hide_select = True
    return ob


def _set_bone_color(pb, rgb):
    if not hasattr(pb, "color"):
        return
    pb.color.palette = 'CUSTOM'
    pb.color.custom.normal = rgb
    pb.color.custom.select = tuple(min(c + 0.22, 1.0) for c in rgb)
    pb.color.custom.active = tuple(min(c + 0.38, 1.0) for c in rgb)


def _get_next_rig_index():
    import re
    used = set()
    pattern = re.compile(r"^Camera Pro(?:[\s\.]*(\d+))?$", re.IGNORECASE)
    legacy_pattern = re.compile(r"^CAM_RIG(?:[\s\.]*(\d+))?$", re.IGNORECASE)
    for ob in bpy.data.objects:
        if ob.type in ('ARMATURE', 'CAMERA'):
            m = pattern.match(ob.name)
            if m:
                used.add(int(m.group(1)) if m.group(1) else 1)
            m_leg = legacy_pattern.match(ob.name)
            if m_leg:
                used.add(int(m_leg.group(1)) if m_leg.group(1) else 1)
    idx = 1
    while idx in used:
        idx += 1
    return idx


def _find_or_create_camera(context, rig_name):
    scene = context.scene
    # 1. If user has selected an unparented camera in the scene, adopt it
    sel_cams = [ob for ob in context.selected_objects if ob.type == 'CAMERA' and ob.parent is None]
    if sel_cams:
        cam = sel_cams[0]
        if abs(cam.rotation_euler.x - math.radians(78.0)) < 0.05 or abs(cam.rotation_euler.x - 0.0) < 0.01:
            cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
            if abs(cam.location.y - (-8.5)) < 0.1:
                cam.location = (0.0, -5.0, 1.3)
        cam.name = f"{rig_name} Camera"
        scene.camera = cam
        context.view_layer.update()
        return cam

    # 2. If no camera is selected, check if there's an unparented default "Camera" in the scene
    unparented_default = [
        ob for ob in scene.objects
        if ob.type == 'CAMERA' and ob.parent is None and ob.name.lower() in ("camera", "camera.001")
    ]
    if unparented_default:
        cam = unparented_default[0]
        cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
        cam.location = (0.0, -5.0, 1.3)
        cam.name = f"{rig_name} Camera"
        scene.camera = cam
        context.view_layer.update()
        return cam

    # 3. Otherwise create a dedicated camera for this rig
    cam_name = f"{rig_name} Camera"
    cd = bpy.data.cameras.new(cam_name)
    ob = bpy.data.objects.new(cam_name, cd)
    scene.collection.objects.link(ob)
    # Position camera looking straight ahead (90 degrees on X) at character height
    ob.location = (0.0, -5.0, 1.3)
    ob.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    scene.camera = ob
    context.view_layer.update()
    return ob


def _view_extents(cam, scene, dist, lens):
    cd = cam.data
    lens = max(lens, 1.0)
    rx = max(scene.render.resolution_x * scene.render.pixel_aspect_x, 1.0)
    ry = max(scene.render.resolution_y * scene.render.pixel_aspect_y, 1.0)
    if cd.sensor_fit == 'VERTICAL':
        hh = dist * (cd.sensor_height * 0.5) / lens
        hw = hh * (rx / ry)
    elif cd.sensor_fit == 'AUTO' and ry > rx:
        hh = dist * (cd.sensor_width * 0.5) / lens
        hw = hh * (rx / ry)
    else:
        hw = dist * (cd.sensor_width * 0.5) / lens
        hh = hw * (ry / rx)
    return max(hw, 0.05), max(hh, 0.05)


def _split_index(path):
    if path.endswith("]"):
        head, _, tail = path.rpartition("[")
        inner = tail[:-1]
        if inner.isdigit():
            return head, int(inner)
    return path, -1


def _clear_drivers(id_data, path, index=-1):
    ad = getattr(id_data, "animation_data", None)
    if ad is None:
        return
    for fc in list(ad.drivers):
        if fc.data_path == path and (index < 0 or fc.array_index == index):
            ad.drivers.remove(fc)


def _purge_constraint_drivers(ob):
    ad = getattr(ob, "animation_data", None)
    if ad is None:
        return
    for fc in list(ad.drivers):
        if fc.data_path.startswith("constraints["):
            ad.drivers.remove(fc)


def _make_driver(id_data, path, props=(), dists=(), expr=None, coeffs=(0.0, 1.0)):
    path, index = _split_index(path)
    _clear_drivers(id_data, path, index)
    fc = id_data.driver_add(path, index) if index >= 0 else id_data.driver_add(path)
    drv = fc.driver
    for v in list(drv.variables):
        drv.variables.remove(v)
    for name, id_type, target, dpath in props:
        var = drv.variables.new()
        var.name = name
        var.type = 'SINGLE_PROP'
        tgt = var.targets[0]
        tgt.id_type = id_type
        tgt.id = target
        tgt.data_path = dpath
    for name, target, bone_a, bone_b in dists:
        var = drv.variables.new()
        var.name = name
        var.type = 'LOC_DIFF'
        t0 = var.targets[0]
        t0.id = target
        t0.bone_target = bone_a
        t0.transform_space = 'WORLD_SPACE'
        t1 = var.targets[1]
        t1.id = target
        t1.bone_target = bone_b
        t1.transform_space = 'WORLD_SPACE'
    for m in list(fc.modifiers):
        fc.modifiers.remove(m)
    if expr is None:
        drv.type = 'AVERAGE'
        gen = fc.modifiers.new('GENERATOR')
        gen.mode = 'POLYNOMIAL'
        gen.poly_order = 1
        gen.use_restricted_range = False
        gen.coefficients[0] = coeffs[0]
        gen.coefficients[1] = coeffs[1]
    else:
        drv.type = 'SCRIPTED'
        drv.use_self = False
        drv.expression = expr
    while len(fc.keyframe_points):
        fc.keyframe_points.remove(fc.keyframe_points[0], fast=True)
    return fc


def _rest_bone_matrix(rig, bone_name):
    bone = rig.data.bones[bone_name]
    return rig.matrix_world @ bone.matrix_local @ Matrix.Translation((0.0, bone.length, 0.0))


def _face_constraint(pb, rig):
    con = pb.constraints.new('DAMPED_TRACK')
    con.name = CON_FACE
    con.target = rig
    con.subtarget = "CAM"
    con.head_tail = 0.0
    con.track_axis = 'TRACK_NEGATIVE_Y'
    return con


def _slide_limit(pb, axis, low, high):
    con = pb.constraints.new('LIMIT_LOCATION')
    con.name = CON_SLIDE
    con.owner_space = 'LOCAL'
    con.use_transform_limit = True
    if axis == 0:
        con.use_min_x = True
        con.use_max_x = True
        con.min_x = low
        con.max_x = high
    else:
        con.use_min_z = True
        con.use_max_z = True
        con.min_z = low
        con.max_z = high
    return con


def _lock_slider(pb, axis):
    pb.rotation_mode = 'XYZ'
    pb.lock_rotation = (True, True, True)
    pb.lock_scale = (True, True, True)
    pb.lock_location = (False, True, True) if axis == 0 else (True, True, False)


def _new_bone(ebs, name, head, fwd, up, length, parent):
    b = ebs.new(name)
    b.head = head
    b.tail = head + fwd * length
    b.align_roll(up)
    b.use_connect = False
    if parent is not None:
        b.parent = parent
    return b


def build(context=None):
    if bpy.app.version < (3, 0, 0):
        raise RuntimeError("This rig requires Blender 3.0 or newer")

    if context is None:
        context = bpy.context
    scene = context.scene
    view_layer = context.view_layer

    if context.object is not None and context.object.mode != 'OBJECT':
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError:
            pass

    index = _get_next_rig_index()
    rig_name = f"Camera Pro {index}"

    cam = _find_or_create_camera(context, rig_name)
    cd = cam.data

    coll = _rig_collection(scene)
    wgts = _widget_collection(coll)
    _set_excluded(view_layer, wgts, False)

    mw = cam.matrix_world.copy()
    loc = mw.translation.copy()
    basis = mw.to_3x3()
    fwd = (basis @ Vector((0.0, 0.0, -1.0))).normalized()
    up = (basis @ Vector((0.0, 1.0, 0.0))).normalized()
    right = fwd.cross(up).normalized()
    aim_point = loc + fwd * AIM_DIST
    base_lens = max(cd.lens, 1.0)

    fw, fh = _view_extents(cam, scene, AIM_DIST, base_lens)
    span = min(fw, fh) * FRAME_FIT
    seg = AIM_DIST * 0.14

    focus_r = span * 0.42
    focus_th = span * 0.085
    ret_half = (focus_r + focus_th) * 1.55

    hw, hh = _view_extents(cam, scene, HUD_DIST, base_lens)

    cor_x = hw * 0.930
    cor_z = hh * 0.900
    cor_arm_x = hw * 0.340
    cor_arm_z = hh * 0.430
    cor_th = hh * 0.026

    gap_x = cor_x - cor_arm_x
    gap_z = cor_z - cor_arm_z

    mtr_v_x = -cor_x + cor_th * 0.5
    mtr_v_len = gap_z * 1.30
    mtr_h_z = -cor_z + cor_th * 0.5
    mtr_h_len = gap_x * 0.97

    tick_s = hh * 0.020
    tick_l = hh * 0.046

    arc_z = hh * 0.560
    arc_len = hw * 0.520
    arc_depth = hh * 0.110

    tri_w = tick_l * 0.46
    tri_h = tick_l * 0.82

    box_w = tri_w
    box_h = tri_w
    box_pad = box_w * 0.24
    gauge_hw = box_w - box_pad
    gauge_hh = box_h - box_pad

    dof_w = hh * 0.058
    dof_h = hh * 0.038
    dof_th = dof_h * 0.16
    dof_ft = dof_h * 0.18
    dof_left = cor_x - cor_th - dof_w * 0.80 - dof_w * 4.0
    dof_cz = -cor_z + cor_th + dof_h * 2.05

    corner_v = []
    corner_e = []
    corner_f = []
    _corner_art(corner_v, corner_e, corner_f, cor_x, cor_z,
                cor_arm_x, cor_arm_z, cor_th, True)

    meter_v = []
    meter_e = []
    _meter_art(meter_v, meter_e, mtr_v_x, 0.0, mtr_v_len, False, -1.0, 48, 6, tick_s, tick_l)
    _meter_art(meter_v, meter_e, 0.0, mtr_h_z, mtr_h_len, True, -1.0, 48, 6, tick_s, tick_l)
    _arc_art(meter_v, meter_e, 0.0, arc_z, arc_len, arc_depth, 28)

    wgt_reticle = _mesh_object(f"WGT_Cam_{index}_Reticle",
                               *_reticle_widget(ret_half, ret_half * 0.42, ret_half * 0.075), wgts)
    wgt_focus = _mesh_object(f"WGT_Cam_{index}_Focus", *_focus_widget(focus_r, focus_th, 32), wgts)
    wgt_body = _mesh_object(f"WGT_Cam_{index}_Body",
                            *_body_widget(span * 0.20, span * 0.14, AIM_DIST * 0.055), wgts)
    root_r = max(AIM_DIST * 0.10, 0.22)
    wgt_root = _mesh_object(f"WGT_Cam_{index}_Root",
                            *_root_widget(root_r, root_r * 0.26, math.radians(17.0),
                                          root_r * 0.42, 48), wgts)
    wgt_pivot = _mesh_object(f"WGT_Cam_{index}_Pivot", *_sphere_widget(span * 0.30, 24), wgts)
    wgt_corner = _mesh_object(f"WGT_Cam_{index}_Corner", corner_v, corner_e, corner_f, wgts)
    wgt_meter = _mesh_object(f"WGT_Cam_{index}_Meter", meter_v, meter_e, [], wgts)
    wgt_tri_v = _mesh_object(f"WGT_Cam_{index}_TriV", *_tri_widget(tri_w, tri_h, False), wgts)
    wgt_tri_h = _mesh_object(f"WGT_Cam_{index}_TriH", *_tri_widget(tri_w, tri_h, True), wgts)
    wgt_box = _mesh_object(f"WGT_Cam_{index}_Box", *_box_widget(box_w, box_h), wgts)
    wgt_gauge_h = _mesh_object(f"WGT_Cam_{index}_GaugeH",
                               *_gauge_widget(gauge_hw * 2.0, gauge_hh, False), wgts)
    wgt_gauge_v = _mesh_object(f"WGT_Cam_{index}_GaugeV",
                               *_gauge_widget(gauge_hw, gauge_hh * 2.0, True), wgts)
    wgt_dof = _mesh_object(f"WGT_Cam_{index}_Dof", *_dof_widget(dof_w, dof_h, dof_th, dof_ft), wgts)
    wgt_plate = _mesh_object(f"WGT_Cam_{index}_Plate", *_plate_widget(dof_w, dof_h), wgts)

    arm_data = bpy.data.armatures.new(rig_name)
    rig = bpy.data.objects.new(rig_name, arm_data)
    coll.objects.link(rig)
    rig.matrix_world = Matrix.Identity(4)
    rig.show_in_front = True

    view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')

    ebs = arm_data.edit_bones
    ground = Vector((loc.x, loc.y, 0.0))
    hud_origin = loc + fwd * HUD_DIST

    def hud_at(x, z):
        return hud_origin + right * x + up * z

    root = ebs.new("ROOT")
    root.head = ground
    root.tail = ground + Vector((0.0, max(AIM_DIST * 0.12, 0.3), 0.0))
    root.align_roll(Vector((0.0, 0.0, 1.0)))
    root.use_connect = False

    aim = _new_bone(ebs, "AIM", aim_point, fwd, up, seg, root)
    focus = _new_bone(ebs, "FOCUS", aim_point, fwd, up, seg * 0.8, aim)
    focus.inherit_scale = 'FULL'

    piv_aim = _new_bone(ebs, "MCH_PIV_AIM", aim_point, fwd, up, seg * 0.5, root)
    pivot = _new_bone(ebs, "PIVOT", aim_point, fwd, up, seg * 0.7, piv_aim)
    mch_pivot = _new_bone(ebs, "MCH_PIVOT", aim_point, fwd, up, seg * 0.5, pivot)
    body = _new_bone(ebs, "CAM", loc, fwd, up, seg, mch_pivot)

    mch_track = _new_bone(ebs, "MCH_TRACK", loc, fwd, up, seg, body)
    mch_track.inherit_scale = 'NONE'
    mch_roll = _new_bone(ebs, "MCH_ROLL", loc, fwd, up, seg, mch_track)
    mch_roll.inherit_scale = 'NONE'
    mch_shake = _new_bone(ebs, "MCH_SHAKE", loc, fwd, up, seg, mch_roll)
    mch_shake.inherit_scale = 'NONE'
    mch_hud = _new_bone(ebs, "MCH_HUD", hud_origin, fwd, up, seg * 0.3, mch_shake)
    mch_hud.inherit_scale = 'NONE'

    art_bones = []
    _new_bone(ebs, "HUD_CORNER", hud_origin, fwd, up, seg * 0.2, mch_hud)
    art_bones.append(("HUD_CORNER", wgt_corner, WHITE))
    _new_bone(ebs, "HUD_METER", hud_origin, fwd, up, seg * 0.2, mch_hud)
    art_bones.append(("HUD_METER", wgt_meter, YELLOW))

    shake_y = _new_bone(ebs, "SHAKE_Y", hud_at(mtr_v_x, -mtr_v_len * 0.5),
                        fwd, up, seg * 0.2, mch_hud)
    shake_x = _new_bone(ebs, "SHAKE_X", hud_at(-mtr_h_len * 0.5, mtr_h_z),
                        fwd, up, seg * 0.2, mch_hud)
    freq = _new_bone(ebs, "FREQ", hud_at(0.0, arc_z), fwd, up, seg * 0.2, mch_hud)

    dof_rest_x = dof_left + dof_w * 3.0
    dof = _new_bone(ebs, "DOF", hud_at(dof_rest_x, dof_cz), fwd, up, seg * 0.2, mch_hud)
    _new_bone(ebs, "DOF_PLATE", hud_at(dof_rest_x, dof_cz), fwd, up, seg * 0.15, mch_hud)
    art_bones.append(("DOF_PLATE", wgt_plate, YELLOW))

    box_cy = mtr_v_x + tri_h + box_w * 1.4
    box_cx = mtr_h_z + tri_h + box_h * 1.4
    _new_bone(ebs, "SY_BOX", hud_at(box_cy, -mtr_v_len * 0.5), fwd, up, seg * 0.15, shake_y)
    _new_bone(ebs, "SY_GAUGE", hud_at(box_cy - gauge_hw, -mtr_v_len * 0.5),
              fwd, up, seg * 0.15, shake_y)
    _new_bone(ebs, "SX_BOX", hud_at(-mtr_h_len * 0.5, box_cx), fwd, up, seg * 0.15, shake_x)
    _new_bone(ebs, "SX_GAUGE", hud_at(-mtr_h_len * 0.5, box_cx - gauge_hh),
              fwd, up, seg * 0.15, shake_x)
    art_bones.append(("SY_BOX", wgt_box, YELLOW))
    art_bones.append(("SY_GAUGE", wgt_gauge_h, YELLOW))
    art_bones.append(("SX_BOX", wgt_box, YELLOW))
    art_bones.append(("SX_GAUGE", wgt_gauge_v, YELLOW))

    for name, _, _ in art_bones:
        ebs[name].inherit_scale = 'FULL'

    bpy.ops.object.mode_set(mode='OBJECT')

    shapes = [
        ("ROOT", wgt_root, YELLOW),
        ("PIVOT", wgt_pivot, PURPLE),
        ("CAM", wgt_body, WHITE),
        ("AIM", wgt_reticle, YELLOW),
        ("FOCUS", wgt_focus, ORANGE),
        ("SHAKE_Y", wgt_tri_v, YELLOW),
        ("SHAKE_X", wgt_tri_h, YELLOW),
        ("FREQ", wgt_tri_h, YELLOW),
        ("DOF", wgt_dof, WHITE),
    ]
    shapes.extend(art_bones)
    for bone_name, shape, rgb in shapes:
        pb = rig.pose.bones[bone_name]
        pb.custom_shape = shape
        pb.use_custom_shape_bone_size = False
        _set_bone_color(pb, rgb)

    rig.pose.bones["CAM"].custom_shape_transform = rig.pose.bones["MCH_ROLL"]

    for bone_name, _, _ in art_bones:
        _bone_flag(rig, bone_name, "hide_select", True)
        pb = rig.pose.bones[bone_name]
        pb.lock_location = (True, True, True)
        pb.lock_rotation = (True, True, True)
        pb.lock_scale = (True, True, True)

    for bone_name in MCH_BONES:
        _bone_flag(rig, bone_name, "hide", True)
        pb = rig.pose.bones[bone_name]
        pb.rotation_mode = 'XYZ'
        pb.lock_location = (True, True, True)
        pb.lock_rotation = (True, True, True)
        pb.lock_scale = (True, True, True)

    for bone_name in ("ROOT", "PIVOT", "CAM", "AIM", "FOCUS"):
        rig.pose.bones[bone_name].rotation_mode = 'XYZ'

    pb_focus = rig.pose.bones["FOCUS"]
    pb_focus.lock_rotation = (True, True, True)
    pb_focus.lock_scale = (True, True, True)

    pb_aim = rig.pose.bones["AIM"]
    pb_aim.lock_rotation = (True, False, True)

    pb_pivot = rig.pose.bones["PIVOT"]
    pb_pivot.lock_location = (True, False, True)
    pb_pivot.lock_scale = (True, True, True)

    _face_constraint(pb_aim, rig)
    _face_constraint(pb_focus, rig)

    pb_sy = rig.pose.bones["SHAKE_Y"]
    _lock_slider(pb_sy, 2)
    _slide_limit(pb_sy, 2, 0.0, mtr_v_len)

    pb_sx = rig.pose.bones["SHAKE_X"]
    _lock_slider(pb_sx, 0)
    _slide_limit(pb_sx, 0, 0.0, mtr_h_len)

    pb_fq = rig.pose.bones["FREQ"]
    _lock_slider(pb_fq, 0)
    _slide_limit(pb_fq, 0, -arc_len * 0.5, arc_len * 0.5)

    pb_dof = rig.pose.bones["DOF"]
    _lock_slider(pb_dof, 0)
    _slide_limit(pb_dof, 0, -dof_w * 2.0, 0.0)

    pb_track = rig.pose.bones["MCH_TRACK"]
    con_aim = pb_track.constraints.new('DAMPED_TRACK')
    con_aim.name = CON_AIM
    con_aim.target = rig
    con_aim.subtarget = "AIM"
    con_aim.track_axis = 'TRACK_Y'

    _purge_constraint_drivers(cam)
    for c in list(cam.constraints):
        if c.type in ('TRACK_TO', 'DAMPED_TRACK', 'LOCKED_TRACK', 'COPY_LOCATION',
                      'COPY_ROTATION', 'TRANSFORM', 'LIMIT_DISTANCE'):
            cam.constraints.remove(c)

    parent_rest = _rest_bone_matrix(rig, "MCH_SHAKE")
    cam.parent = rig
    cam.parent_type = 'BONE'
    cam.parent_bone = "MCH_SHAKE"
    cam.matrix_parent_inverse = parent_rest.inverted()
    cam.rotation_mode = 'XYZ'
    cam.location = loc
    cam.rotation_euler = mw.to_euler('XYZ')
    cam.scale = (1.0, 1.0, 1.0)
    cam.lock_location = (True, True, True)
    cam.lock_rotation = (True, True, True)
    cam.lock_scale = (True, True, True)
    _move_to(cam, coll)

    cam[P_TRACK] = True
    try:
        cam.id_properties_ui(P_TRACK).update(description="Aim the camera at the reticle")
    except (TypeError, AttributeError):
        pass

    cd.dof.use_dof = True
    cd.dof.focus_object = rig
    cd.dof.focus_subtarget = "FOCUS"

    _make_driver(
        cd,
        "lens",
        props=(
            ("sx", 'OBJECT', rig, 'pose.bones["AIM"].scale[0]'),
            ("sz", 'OBJECT', rig, 'pose.bones["AIM"].scale[2]'),
        ),
        coeffs=(0.0, base_lens),
    )
    _make_driver(
        rig,
        'pose.bones["MCH_TRACK"].constraints["%s"].influence' % CON_AIM,
        props=(("trk", 'OBJECT', cam, '["%s"]' % P_TRACK),),
    )
    _make_driver(
        rig,
        'pose.bones["MCH_ROLL"].rotation_euler[1]',
        props=(("rl", 'OBJECT', rig, 'pose.bones["AIM"].rotation_euler[1]'),),
    )

    for axis in range(3):
        _make_driver(
            rig,
            'pose.bones["AIM"].custom_shape_scale_xyz[%d]' % axis,
            dists=(("d", rig, "AIM", "CAM"),),
            coeffs=(0.0, 1.0 / AIM_DIST),
        )
        _make_driver(
            rig,
            'pose.bones["FOCUS"].custom_shape_scale_xyz[%d]' % axis,
            dists=(("d", rig, "FOCUS", "CAM"),),
            coeffs=(0.0, 1.0 / AIM_DIST),
        )
        _make_driver(
            rig,
            'pose.bones["MCH_PIV_AIM"].location[%d]' % axis,
            props=(("a", 'OBJECT', rig, 'pose.bones["AIM"].location[%d]' % axis),),
        )
        _make_driver(
            rig,
            'pose.bones["MCH_PIVOT"].location[%d]' % axis,
            props=(("a", 'OBJECT', rig, 'pose.bones["MCH_PIV_AIM"].location[%d]' % axis),
                   ("p", 'OBJECT', rig, 'pose.bones["PIVOT"].location[%d]' % axis)),
            expr="-(a + p)",
        )
        _make_driver(
            rig,
            'pose.bones["MCH_HUD"].scale[%d]' % axis,
            props=(("s", 'OBJECT', rig, 'pose.bones["AIM"].scale[0]'),),
            expr="1.0 / max(0.0001, s)",
        )

    arc_k = -arc_depth / ((arc_len * 0.5) ** 2)
    _make_driver(
        rig,
        'pose.bones["FREQ"].location[2]',
        props=(("x", 'OBJECT', rig, 'pose.bones["FREQ"].location[0]'),),
        expr="%.9f * x * x" % arc_k,
    )
    _make_driver(
        rig,
        'pose.bones["FREQ"].rotation_euler[1]',
        props=(("x", 'OBJECT', rig, 'pose.bones["FREQ"].location[0]'),),
        expr="-atan(%.9f * x)" % (2.0 * arc_k),
    )

    ky = SHAKE_MAX / mtr_v_len
    kx = SHAKE_MAX / mtr_h_len
    fmid = (FREQ_MIN + FREQ_MAX) * 0.5
    fk = (FREQ_MAX - FREQ_MIN) / arc_len
    rate = "(%.9f + fq * %.9f)" % (fmid, fk)

    shake_vars = (
        ("fr", 'SCENE', scene, "frame_current"),
        ("fq", 'OBJECT', rig, 'pose.bones["FREQ"].location[0]'),
    )

    _make_driver(
        rig,
        'pose.bones["MCH_SHAKE"].rotation_euler[0]',
        props=shake_vars + (("iy", 'OBJECT', rig, 'pose.bones["SHAKE_Y"].location[2]'),),
        expr="%.9f * iy * (sin(fr * %s) * 0.62 + sin(fr * %s * 2.37 + 1.7) * 0.38)"
             % (ky, rate, rate),
    )
    _make_driver(
        rig,
        'pose.bones["MCH_SHAKE"].rotation_euler[2]',
        props=shake_vars + (("ix", 'OBJECT', rig, 'pose.bones["SHAKE_X"].location[0]'),),
        expr="%.9f * ix * (cos(fr * %s * 1.13 + 0.9) * 0.65 + cos(fr * %s * 2.71) * 0.35)"
             % (kx, rate, rate),
    )
    _make_driver(
        rig,
        'pose.bones["MCH_SHAKE"].rotation_euler[1]',
        props=shake_vars + (
            ("ix", 'OBJECT', rig, 'pose.bones["SHAKE_X"].location[0]'),
            ("iy", 'OBJECT', rig, 'pose.bones["SHAKE_Y"].location[2]'),
        ),
        expr="%.9f * (ix * 0.5 + iy * 0.5) * sin(fr * %s * 0.77 + 2.4)"
             % (min(kx, ky) * 0.35, rate),
    )

    _make_driver(
        rig,
        'pose.bones["SY_GAUGE"].scale[1]',
        props=(("y", 'OBJECT', rig, 'pose.bones["SHAKE_Y"].location[2]'),),
        expr="max(0.001, y * %.9f)" % (1.0 / mtr_v_len),
    )
    _make_driver(
        rig,
        'pose.bones["SX_GAUGE"].scale[0]',
        props=(("x", 'OBJECT', rig, 'pose.bones["SHAKE_X"].location[0]'),),
        expr="max(0.001, x * %.9f)" % (1.0 / mtr_h_len),
    )

    _make_driver(
        cd,
        "dof.use_dof",
        props=(("x", 'OBJECT', rig, 'pose.bones["DOF"].location[0]'),),
        expr="min(1.0, max(0.0, floor(x * %.9f + 1.5)))" % (0.5 / dof_w),
    )

    view_layer.update()

    for ob in context.selected_objects:
        ob.select_set(False)
    rig.select_set(True)
    view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')
    for b in arm_data.bones:
        _bone_flag(rig, b.name, "select", b.name == "AIM")
    _set_active_bone(rig, "AIM")

    _set_excluded(view_layer, wgts, True)

    return rig, cam


class CSW_OT_CreateCameraPro(bpy.types.Operator):
    bl_idname = "setup_wizard.create_camera_pro"
    bl_label = "Camera Pro"
    bl_description = "Create Camera Pro in the active scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            rig, cam = build(context)
            self.report({'INFO'}, f"Successfully created Camera Pro: '{rig.name}'")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to create Camera Pro: {e}")
            return {'CANCELLED'}


class CSW_OT_CreateJideehCamrig(bpy.types.Operator):
    bl_idname = "setup_wizard.create_jideeh_camrig"
    bl_label = "Camera Pro"
    bl_description = "Create Camera Pro in the active scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            rig, cam = build(context)
            self.report({'INFO'}, f"Successfully created Camera Pro: '{rig.name}'")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to create Camera Pro: {e}")
            return {'CANCELLED'}

