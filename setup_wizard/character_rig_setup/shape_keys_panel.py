"""Procedural 3D Shape Keys Control Panel builder for Blender character rigs.

Generates a clean, framed 3D facial shape-keys control panel beside the character's head:
  - Single movable/scalable ``FacePanel-Root`` bone (parented to ``Face-Root``)
  - Single non-selectable wireframe board mesh (``FacePanel-Board``) combining:
      * Outer panel border(s)
      * Crisp vector font section titles ("Brows", "Eyes", "Mouth", "2D VFX", ...)
      * Horizontal rectangular slider tracks with short readable labels
      * Vertical rectangular slider tracks (with optional up/down chevrons)
      * Square 2D joystick boxes with center crosshairs and axis ticks
  - Color-coded draggable handle bones (``CTRL-...``) with clean rounded-box /
    ring custom shapes and LOCAL ``LIMIT_LOCATION`` constraints driving shape keys.

Used by ``hsr_face_rig.py``, ``nte_face_rig.py``, and ``ake_face_rig.py``.
"""

import math
import bpy
from mathutils import Vector

# Shared palette (matching Genshin / Gacha Face Rig conventions)
COL_BOARD      = (0.92, 0.72, 0.35)  # Warm gold/amber panel wireframe (classic Genshin orange-gold look)
COL_ROOT       = (0.95, 0.65, 0.20)  # Panel root handle
COL_BROW       = (0.30, 0.85, 0.40)  # Green
COL_EYE        = (0.20, 0.85, 0.95)  # Cyan
COL_EYELID     = (0.95, 0.25, 0.25)  # Red
COL_MOUTH      = (0.95, 0.30, 0.30)  # Coral / Red
COL_VISEME     = (0.98, 0.82, 0.20)  # Gold / Yellow
COL_EXPRESSION = (0.72, 0.40, 0.95)  # Purple
COL_EMOTION    = (0.95, 0.55, 0.20)  # Orange
COL_PHONEME    = (0.35, 0.82, 0.62)  # Mint / Teal
COL_VFX        = (0.96, 0.40, 0.68)  # Magenta / Pink
COL_EXTRA      = (0.55, 0.72, 0.95)  # Soft Blue


# =============================================================================
# VECTOR WIREFRAME PRIMITIVES (in panel-local X-right, Z-up coordinates)
# =============================================================================

class _WireBuilder:
    """Accumulates 2D wireframe edges (X, 0, Z) into a single Blender mesh."""

    def __init__(self):
        self.verts = []
        self.edges = []

    def add_line(self, x0, z0, x1, z1):
        i = len(self.verts)
        self.verts.append((x0, 0.0, z0))
        self.verts.append((x1, 0.0, z1))
        self.edges.append((i, i + 1))

    def add_rect(self, x0, z0, x1, z1):
        i = len(self.verts)
        self.verts.extend([
            (x0, 0.0, z0),
            (x1, 0.0, z0),
            (x1, 0.0, z1),
            (x0, 0.0, z1),
        ])
        self.edges.extend([(i, i + 1), (i + 1, i + 2), (i + 2, i + 3), (i + 3, i)])

    def add_polyline(self, pts, closed=False):
        if len(pts) < 2:
            return
        base = len(self.verts)
        for x, z in pts:
            self.verts.append((x, 0.0, z))
        for k in range(len(pts) - 1):
            self.edges.append((base + k, base + k + 1))
        if closed and len(pts) > 2:
            self.edges.append((base + len(pts) - 1, base))

    def add_chevron(self, cx, cz, size, direction='UP'):
        s = size
        if direction == 'UP':
            self.add_polyline([(cx - s, cz - s * 0.4), (cx, cz + s * 0.6), (cx + s, cz - s * 0.4)])
        elif direction == 'DOWN':
            self.add_polyline([(cx - s, cz + s * 0.4), (cx, cz - s * 0.6), (cx + s, cz + s * 0.4)])
        elif direction == 'RIGHT':
            self.add_polyline([(cx - s * 0.4, cz - s), (cx + s * 0.6, cz), (cx - s * 0.4, cz + s)])
        elif direction == 'LEFT':
            self.add_polyline([(cx + s * 0.4, cz - s), (cx - s * 0.6, cz), (cx + s * 0.4, cz + s)])

    def add_text(self, text_string, x, z, height, align_x='LEFT', align_y='CENTER', max_width=None):
        """Convert Blender vector FONT curve into clean outline wireframe edges."""
        if not text_string:
            return
        try:
            curve = bpy.data.curves.new(name="_tmp_panel_txt_curve", type='FONT')
            curve.body = str(text_string)
            curve.size = 1.0
            curve.align_x = align_x
            curve.align_y = align_y
            curve.fill_mode = 'NONE'
            curve.resolution_u = 2  # Crisp & lightweight wireframe

            temp_obj = bpy.data.objects.new("_tmp_panel_txt_obj", curve)
            bpy.context.scene.collection.objects.link(temp_obj)

            depsgraph = bpy.context.evaluated_depsgraph_get()
            eval_obj = temp_obj.evaluated_get(depsgraph)
            mesh = bpy.data.meshes.new_from_object(eval_obj)

            # Compute horizontal scale factor if max_width is specified
            scale_x = height
            scale_z = height
            if max_width and len(mesh.vertices) > 0:
                xs = [v.co.x for v in mesh.vertices]
                raw_w = max(xs) - min(xs)
                if raw_w > 1e-5 and raw_w * scale_x > max_width:
                    scale_x = max_width / raw_w

            base = len(self.verts)
            for v in mesh.vertices:
                self.verts.append((x + v.co.x * scale_x, 0.0, z + v.co.y * scale_z))
            for e in mesh.edges:
                self.edges.append((base + e.vertices[0], base + e.vertices[1]))

            bpy.data.meshes.remove(mesh, do_unlink=True)
            bpy.context.scene.collection.objects.unlink(temp_obj)
            bpy.data.objects.remove(temp_obj, do_unlink=True)
            bpy.data.curves.remove(curve, do_unlink=True)
        except Exception:
            # Fallback: tiny horizontal tick if font conversion fails in headless edge cases
            w = min(max_width or (len(text_string) * height * 0.5), len(text_string) * height * 0.5)
            self.add_line(x, z, x + w, z)

    def build_object(self, name, wgt_coll):
        old = bpy.data.objects.get(name)
        if old:
            old_mesh = old.data
            bpy.data.objects.remove(old, do_unlink=True)
            if old_mesh and old_mesh.users == 0:
                bpy.data.meshes.remove(old_mesh, do_unlink=True)

        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.verts, self.edges, [])
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        wgt_coll.objects.link(obj)
        return obj


# =============================================================================
# HANDLE WIDGET SHAPES (clean Genshin-style knobs & root tab)
# =============================================================================

def make_panel_handle_widget(kind, wgt_coll):
    """Create or reuse a crisp Genshin-style knob widget mesh."""
    name = f"WGT-FacePanel_{kind}"
    obj = bpy.data.objects.get(name)
    if obj:
        return obj

    wb = _WireBuilder()
    if kind == 'knob_box':
        # Rounded square knob with inner dot (classic Genshin slider handle)
        s = 0.85
        c = 0.25
        wb.add_polyline([
            (-s + c, -s), (s - c, -s), (s, -s + c), (s, s - c),
            (s - c, s), (-s + c, s), (-s, s - c), (-s, -s + c),
        ], closed=True)
        r = 0.32
        N = 12
        pts = [(r * math.cos(2 * math.pi * i / N), r * math.sin(2 * math.pi * i / N)) for i in range(N)]
        wb.add_polyline(pts, closed=True)
    elif kind == 'knob_pad':
        # Classic Genshin 2D joystick knob (rounded square + inner circle)
        s = 0.90
        c = 0.30
        wb.add_polyline([
            (-s + c, -s), (s - c, -s), (s, -s + c), (s, s - c),
            (s - c, s), (-s + c, s), (-s, s - c), (-s, -s + c),
        ], closed=True)
        r = 0.45
        N = 16
        pts = [(r * math.cos(2 * math.pi * i / N), r * math.sin(2 * math.pi * i / N)) for i in range(N)]
        wb.add_polyline(pts, closed=True)
    elif kind == 'knob_v':
        # Vertical slider knob (compact horizontal capsule with center bar)
        wb.add_rect(-0.85, -0.55, 0.85, 0.55)
        wb.add_line(-0.50, 0.0, 0.50, 0.0)
    elif kind == 'root_tab':
        # Clean top drag-bar handle for moving/scaling the whole panel
        wb.add_rect(-1.0, -0.25, 1.0, 0.25)
        wb.add_line(-0.6, 0.0, 0.6, 0.0)
        wb.add_chevron(-0.82, 0.0, 0.14, 'LEFT')
        wb.add_chevron(0.82, 0.0, 0.14, 'RIGHT')
    else:
        wb.add_rect(-0.7, -0.7, 0.7, 0.7)

    return wb.build_object(name, wgt_coll)


# =============================================================================
# PANEL LAYOUT ENGINE
# =============================================================================
# Declarative spec passed by hsr_face_rig.py / nte_face_rig.py:
#
#   panel_columns = [
#       {
#           'title': 'Main',   # optional column title
#           'sections': [
#               {
#                   'title': 'Brows',
#                   'rows': [
#                       # Row type 1: 'grid' -> N columns of horizontal sliders
#                       {'type': 'grid', 'cols': 2, 'items': [
#                           {'name': 'CTRL-...', 'label': 'Angry', 'color': COL_BROW,
#                            'group': 'Face Eyebrow', 'drivers': [{'key': '...', 'axis': 'X', 'dir': +1}]},
#                       ]},
#                       # Row type 2: 'pad_and_sliders' -> 2D square joystick on left + stacked h-sliders on right
#                       {'type': 'pad_and_sliders',
#                        'pad': {'name': 'CTRL-...', 'label': 'Mouth', 'color': COL_MOUTH,
#                                'group': 'Face Mouth', 'edge_labels': ('W', 'N', 'U', 'D'),
#                                'drivers': [...]},
#                        'sliders': [...]},
#                       # Row type 3: 'vsliders_and_pad' -> optional 2D pad + vertical sliders side by side
#                       {'type': 'vsliders_and_pad',
#                        'pad': {...} or None,
#                        'vsliders': [
#                            {'name': 'CTRL-...', 'label': 'Wink L', 'color': COL_EYELID,
#                             'group': 'Face Eyelid', 'range': 'both'|'pos'|'neg',
#                             'drivers': [...]},
#                        ]},
#                       # Row type 4: 'pads_row' -> 1 or 2 square 2D pads side by side
#                       {'type': 'pads_row', 'pads': [...]},
#                   ]
#               }
#           ]
#       },
#       ...
#   ]


def _align_origin_to_lighting_panel(origin_world, armature=None):
    """Align panel Y (depth) and top Z border with the character's Lighting Panel if present.

    Falls back to placing the panel on the character's Y=0 frontal plane when no
    Lighting Panel exists in the scene.
    """
    aligned = origin_world.copy()
    lp = None

    # Prefer a Lighting Panel sharing a collection with the character armature
    if armature is not None:
        arm_colls = set(armature.users_collection)
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and "lighting panel" in obj.name.lower():
                if arm_colls & set(obj.users_collection):
                    lp = obj
                    break

    if lp is None:
        lp = bpy.data.objects.get("Lighting Panel")
    if lp is None:
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and "lighting panel" in obj.name.lower():
                lp = obj
                break

    # Also check if Lighting Panel bone was fused directly into the character armature
    if lp is None and armature is not None and armature.pose.bones.get("Lighting Panel") is not None:
        lp = armature

    if lp is not None and lp.type == 'ARMATURE':
        pb = lp.pose.bones.get("Lighting Panel")
        if pb is None:
            pb = next((b for b in lp.pose.bones if b.custom_shape and 'panel' in (b.name + b.custom_shape.name).lower()), None)
        if pb is not None:
            wgt = pb.custom_shape
            if wgt is None:
                for cand in ("LightPanelWGT", "Plane"):
                    o_w = bpy.data.objects.get(cand)
                    if o_w and o_w.type == 'MESH' and o_w.data.vertices:
                        wgt = o_w
                        break
            if wgt and wgt.type == 'MESH' and wgt.data.vertices:
                try:
                    m = lp.matrix_world @ pb.matrix
                    sx, sy, sz = pb.custom_shape_scale_xyz
                    b_len = pb.bone.length if pb.use_custom_shape_bone_size else 1.0
                    pts = [
                        m @ Vector((v.co.x * sx * b_len, v.co.y * sy * b_len, v.co.z * sz * b_len))
                        for v in wgt.data.vertices
                    ]
                    lp_y = sum(p.y for p in pts) / len(pts)
                    lp_z_max = max(p.z for p in pts)
                    aligned.y = lp_y
                    if abs(lp_z_max - aligned.z) < 1.50:
                        aligned.z = lp_z_max
                    return aligned
                except Exception:
                    pass
            # Fallback if custom shape mesh isn't linked yet: Lighting Panel top border is +6.41 * bone_len above head
            try:
                w_head = lp.matrix_world @ pb.bone.head_local
                w_tail = lp.matrix_world @ pb.bone.tail_local
                w_len = (w_tail - w_head).length
                lp_z_max = w_head.z + 6.41 * w_len
                aligned.y = w_head.y
                if abs(lp_z_max - aligned.z) < 1.50:
                    aligned.z = lp_z_max
                return aligned
            except Exception:
                pass

    # Fallback: keep cleanly on the character's Y=0 frontal plane
    if armature is not None:
        aligned.y = armature.matrix_world.translation.y
    else:
        aligned.y = 0.0
    return aligned


def build_shape_keys_panel(
    panel_columns,
    origin_world,
    right,
    up,
    fwd,
    face_size,
    wgt_coll,
    game_tag="HSR",
    unique_tag="",
    collection_name="Face",
    root_name="FacePanel-Root",
    board_name="FacePanel-Board",
    armature=None,
    face_center=None,
):
    """Lay out a Genshin-style framed panel and return (board_widget, panel_controls).

    All panel coordinates are measured in units of ``u = face_size``:
      - Origin of ``FacePanel-Root`` sits at ``origin_world`` (top-left of the panel).
      - Board wireframe coordinates ``(x, 0, z)`` live in ``FacePanel-Root``'s local space
        where ``+X == +right`` (viewer right) and ``+Z == +up`` (world up).
      - Each returned control dict carries ``'panel_space': True`` so the rig builder
        orients its bone along ``-fwd`` (local ``+X = +right``, ``+Z = +up``) and
        parents it to ``FacePanel-Root``.
    """
    # Filter out empty sections and empty columns
    cleaned_cols = []
    for col in panel_columns:
        secs = [s for s in col.get('sections', []) if s.get('rows')]
        if secs:
            cleaned_cols.append({'title': col.get('title'), 'sections': secs})

    if not cleaned_cols:
        return None, []

    origin_world = _align_origin_to_lighting_panel(origin_world, armature=armature)

    u = face_size  # ~0.22 - 0.30 meters for typical anime characters

    # Proportional Genshin panel dimensions (tuned to match Image 1 proportions)
    PAD_OUTER    = u * 0.085   # Padding inside outer panel border
    SEC_GAP      = u * 0.090   # Vertical gap between sections
    HEADER_H     = u * 0.135   # Section title height ("Brows", "Eyes", "Mouth")
    HEADER_GAP   = u * 0.040   # Gap below section title
    ROW_GAP      = u * 0.032   # Vertical gap between slider rows
    COL_GAP      = u * 0.045   # Horizontal gap between columns inside a grid
    PANEL_COL_GAP = u * 0.140  # Gap between adjacent framed panels (e.g. Main vs Phonemes/VFX)

    HSLIDER_W    = u * 0.380   # Width of one horizontal slider track box
    HSLIDER_H    = u * 0.072   # Height of one horizontal slider track box
    HSLIDER_PAD  = u * 0.036   # Left/right inset inside track so knob stays inside box
    HSLIDER_LIM  = HSLIDER_W - 2.0 * HSLIDER_PAD

    VSLIDER_W    = u * 0.088   # Width of one vertical slider track box
    VSLIDER_H    = u * 0.360   # Height of one vertical slider track box
    VSLIDER_PAD  = u * 0.040
    VSLIDER_LIM  = VSLIDER_H - 2.0 * VSLIDER_PAD

    PAD2D_SIZE   = u * 0.420   # Square 2D joystick frame size
    PAD2D_INSET  = u * 0.055
    PAD2D_LIM    = (PAD2D_SIZE * 0.5) - PAD2D_INSET

    KNOB_H_SCALE = Vector((HSLIDER_H * 0.36, HSLIDER_H * 0.36, HSLIDER_H * 0.36))
    KNOB_V_SCALE = Vector((VSLIDER_W * 0.36, VSLIDER_W * 0.36, VSLIDER_W * 0.36))
    KNOB_P_SCALE = Vector((u * 0.042, u * 0.042, u * 0.042))

    wb = _WireBuilder()
    controls = []

    # Pre-create handle widgets
    wgt_knob_box = make_panel_handle_widget('knob_box', wgt_coll)
    wgt_knob_pad = make_panel_handle_widget('knob_pad', wgt_coll)
    wgt_knob_v   = make_panel_handle_widget('knob_v', wgt_coll)
    wgt_root_tab = make_panel_handle_widget('root_tab', wgt_coll)

    def _to_world(lx, lz):
        return origin_world + right * lx + up * lz

    def _draw_hslider(x0, z_top, width, item):
        """Draw one horizontal slider box [x0 .. x0+width] from z_top down by HSLIDER_H."""
        z_bot = z_top - HSLIDER_H
        z_mid = 0.5 * (z_top + z_bot)
        wb.add_rect(x0, z_bot, x0 + width, z_top)

        # Label neatly inside the right portion of the track box (clear of rest knob on left)
        lbl = item.get('label', '')
        if lbl:
            text_x = x0 + HSLIDER_PAD * 2.15
            max_tw = max(u * 0.05, width - HSLIDER_PAD * 2.65)
            wb.add_text(lbl, text_x, z_mid, HSLIDER_H * 0.56, align_x='LEFT', align_y='CENTER', max_width=max_tw)

        lim = max(u * 0.02, width - 2.0 * HSLIDER_PAD)
        knob_x = x0 + HSLIDER_PAD
        controls.append({
            'name': item['name'],
            'collection': item.get('collection', collection_name),
            'color': item.get('color', COL_EXPRESSION),
            'group': item.get('group', 'Face Panel'),
            'head': _to_world(knob_x, z_mid),
            'widget_obj': wgt_knob_box,
            'lim': lim,
            'free': ('X',),
            'range': 'pos',
            'shape_scale': KNOB_H_SCALE,
            'drivers': item.get('drivers', []),
            'panel_space': True,
            'parent_bone': root_name,
        })

    def _draw_vslider(x0, z_top, height, item):
        """Draw one vertical slider box [x0 .. x0+VSLIDER_W] from z_top down by height."""
        x1 = x0 + VSLIDER_W
        x_mid = 0.5 * (x0 + x1)
        z_bot = z_top - height
        wb.add_rect(x0, z_bot, x1, z_top)

        rng = item.get('range', 'pos')  # 'pos', 'neg', or 'both'
        if rng == 'both':
            lim = (height - 2.0 * VSLIDER_PAD) * 0.5
            knob_z = 0.5 * (z_top + z_bot)
            wb.add_line(x0 + VSLIDER_W * 0.25, knob_z, x1 - VSLIDER_W * 0.25, knob_z)
            wb.add_chevron(x_mid, z_top - VSLIDER_PAD * 0.45, VSLIDER_W * 0.22, 'UP')
            wb.add_chevron(x_mid, z_bot + VSLIDER_PAD * 0.45, VSLIDER_W * 0.22, 'DOWN')
        elif rng == 'neg':
            lim = height - 2.0 * VSLIDER_PAD
            knob_z = z_top - VSLIDER_PAD
            wb.add_chevron(x_mid, z_bot + VSLIDER_PAD * 0.45, VSLIDER_W * 0.22, 'DOWN')
        else:
            lim = height - 2.0 * VSLIDER_PAD
            knob_z = z_bot + VSLIDER_PAD
            wb.add_chevron(x_mid, z_top - VSLIDER_PAD * 0.45, VSLIDER_W * 0.22, 'UP')

        lbl = item.get('label', '')
        if lbl:
            wb.add_text(lbl, x_mid, z_bot - u * 0.032, HSLIDER_H * 0.44,
                        align_x='CENTER', align_y='CENTER', max_width=VSLIDER_W * 1.15)

        controls.append({
            'name': item['name'],
            'collection': item.get('collection', collection_name),
            'color': item.get('color', COL_EYE),
            'group': item.get('group', 'Face Panel'),
            'head': _to_world(x_mid, knob_z),
            'widget_obj': wgt_knob_v,
            'lim': lim,
            'free': ('Z',),
            'range': rng,
            'shape_scale': KNOB_V_SCALE,
            'drivers': item.get('drivers', []),
            'panel_space': True,
            'parent_bone': root_name,
        })

    def _draw_pad2d(x0, z_top, size, item):
        """Draw one square 2D joystick frame [x0 .. x0+size] from z_top down by size."""
        x1 = x0 + size
        z_bot = z_top - size
        cx = 0.5 * (x0 + x1)
        cz = 0.5 * (z_top + z_bot)
        wb.add_rect(x0, z_bot, x1, z_top)

        # Subtle center crosshair ticks
        tk = size * 0.055
        wb.add_line(cx - tk, cz, cx + tk, cz)
        wb.add_line(cx, cz - tk, cx, cz + tk)

        # Optional tiny edge labels: (right_lbl, left_lbl, up_lbl, down_lbl)
        el = item.get('edge_labels')
        if el and len(el) == 4:
            r_l, l_l, u_l, d_l = el
            eh = HSLIDER_H * 0.42
            if r_l:
                wb.add_text(r_l, x1 - size * 0.06, cz, eh, align_x='RIGHT', align_y='CENTER', max_width=size * 0.24)
            if l_l:
                wb.add_text(l_l, x0 + size * 0.06, cz, eh, align_x='LEFT', align_y='CENTER', max_width=size * 0.24)
            if u_l:
                wb.add_text(u_l, cx, z_top - size * 0.09, eh, align_x='CENTER', align_y='CENTER', max_width=size * 0.35)
            if d_l:
                wb.add_text(d_l, cx, z_bot + size * 0.09, eh, align_x='CENTER', align_y='CENTER', max_width=size * 0.35)

        lbl = item.get('label', '')
        if lbl:
            wb.add_text(lbl, cx, z_bot - u * 0.032, HSLIDER_H * 0.46,
                        align_x='CENTER', align_y='CENTER', max_width=size)

        lim = max(u * 0.04, size * 0.5 - PAD2D_INSET)
        controls.append({
            'name': item['name'],
            'collection': item.get('collection', collection_name),
            'color': item.get('color', COL_MOUTH),
            'group': item.get('group', 'Face Panel'),
            'head': _to_world(cx, cz),
            'widget_obj': wgt_knob_pad,
            'lim': lim,
            'free': ('X', 'Z'),
            'range': 'both',
            'shape_scale': KNOB_P_SCALE,
            'drivers': item.get('drivers', []),
            'panel_space': True,
            'parent_bone': root_name,
        })

    # Compute each panel column's inner width and outer height first so frames
    # fit tightly and panel placement adapts to how many shapekeys the character has.
    def _measure_col_inner_width(col):
        max_w = u * 0.28
        for sec in col['sections']:
            sec_title = sec.get('title', '')
            if sec_title:
                title_w = min(HSLIDER_W * 2.0 + COL_GAP, len(sec_title) * HEADER_H * 0.42)
                max_w = max(max_w, title_w)
            for row in sec['rows']:
                rtype = row.get('type', 'grid')
                if rtype == 'grid':
                    items = row.get('items', [])
                    ncols = max(1, int(row.get('cols', 2)))
                    eff_cols = min(ncols, len(items)) if items else ncols
                    w = eff_cols * HSLIDER_W + (eff_cols - 1) * COL_GAP
                    max_w = max(max_w, w)
                elif rtype == 'pad_and_sliders':
                    s_cols = max(1, int(row.get('slider_cols', 1)))
                    pad_sz = row.get('pad_size', PAD2D_SIZE)
                    pad_w = (pad_sz + COL_GAP * 1.4) if row.get('pad') else 0.0
                    w = pad_w + s_cols * HSLIDER_W + (s_cols - 1) * COL_GAP
                    max_w = max(max_w, w)
                elif rtype == 'vsliders_and_pad':
                    nv = len(row.get('vsliders', []))
                    vw = nv * VSLIDER_W + max(0, nv - 1) * (COL_GAP * 0.65)
                    pad_sz = row.get('pad_size', row.get('v_height', VSLIDER_H))
                    pw = (pad_sz + COL_GAP * 1.4) if row.get('pad') else 0.0
                    max_w = max(max_w, pw + vw)
                elif rtype == 'pads_row':
                    npads = len(row.get('pads', []))
                    psize = row.get('pad_size', u * 0.28)
                    w = npads * psize + max(0, npads - 1) * COL_GAP * 1.5
                    max_w = max(max_w, w)
        return max_w

    def _measure_col_height(col):
        h = PAD_OUTER
        for sec_idx, sec in enumerate(col['sections']):
            if sec_idx > 0:
                h += SEC_GAP
            if sec.get('title', ''):
                h += HEADER_H + HEADER_GAP
            for row_idx, row in enumerate(sec['rows']):
                if row_idx > 0:
                    h += ROW_GAP * 1.4
                rtype = row.get('type', 'grid')
                if rtype == 'grid':
                    items = row.get('items', [])
                    if not items:
                        continue
                    ncols = max(1, int(row.get('cols', 2)))
                    nrows = (len(items) + ncols - 1) // ncols
                    h += nrows * HSLIDER_H + max(0, nrows - 1) * ROW_GAP
                elif rtype == 'pad_and_sliders':
                    pad = row.get('pad')
                    sliders = row.get('sliders', [])
                    s_cols = max(1, int(row.get('slider_cols', 1)))
                    pad_sz = row.get('pad_size', PAD2D_SIZE)
                    pad_bottom_extra = u * 0.055 if (pad and pad.get('label')) else 0.0
                    s_rows = (len(sliders) + s_cols - 1) // s_cols if sliders else 0
                    s_h = (s_rows * HSLIDER_H + max(0, s_rows - 1) * ROW_GAP) if s_rows else 0.0
                    p_h = (pad_sz + pad_bottom_extra) if pad else 0.0
                    h += max(p_h, s_h)
                elif rtype == 'vsliders_and_pad':
                    pad = row.get('pad')
                    v_h = row.get('v_height', VSLIDER_H)
                    pad_sz = row.get('pad_size', v_h)
                    h += max(pad_sz if pad else 0.0, v_h) + u * 0.060
                elif rtype == 'pads_row':
                    pads = row.get('pads', [])
                    if not pads:
                        continue
                    psize = row.get('pad_size', u * 0.28)
                    has_lbl = any(p.get('label') for p in pads)
                    h += psize + (u * 0.055 if has_lbl else 0.0)
        return h + PAD_OUTER

    col_inner_widths = [_measure_col_inner_width(col) for col in cleaned_cols]
    col_heights = [_measure_col_height(col) for col in cleaned_cols]

    # Adaptive positioning: bring compact panels (few shapekeys / short left column,
    # e.g. HSR Evernight) closer to the face, while keeping tall multi-section panels
    # (e.g. HSR Robin) far enough right and high enough to clear the character's arms.
    if face_center is not None:
        max_h = max(col_heights)
        tall_z = origin_world.z
        compact_z = face_center.z + u * 0.38
        t_z = max(0.0, min(1.0, (max_h - u * 0.90) / (u * 2.70 - u * 0.90)))
        if compact_z < tall_z:
            origin_world.z = compact_z + (tall_z - compact_z) * t_z

        current_x_off = (origin_world - face_center).dot(right)
        min_x_off = u * 1.15
        max_x_off = max(min_x_off, current_x_off)
        z_top_rel = origin_world.z - face_center.z

        col_x0 = 0.0
        req_x_off = min_x_off
        for inner_w, ch in zip(col_inner_widths, col_heights):
            drop = max(0.0, ch - z_top_rel)
            if drop <= u * 0.65:
                clearance = min_x_off
            elif drop >= u * 2.60:
                clearance = max_x_off
            else:
                t_x = (drop - u * 0.65) / (u * 2.60 - u * 0.65)
                clearance = min_x_off + (max_x_off - min_x_off) * t_x
            req_x_off = max(req_x_off, clearance - col_x0)
            col_x0 += inner_w + 2.0 * PAD_OUTER + PANEL_COL_GAP

        target_x_off = max(min_x_off, min(max_x_off, req_x_off))
        origin_world = origin_world + right * (target_x_off - current_x_off)

    cursor_x = 0.0
    total_width = 0.0

    for col_idx, col in enumerate(cleaned_cols):
        inner_w = col_inner_widths[col_idx]
        frame_x0 = cursor_x
        frame_x1 = frame_x0 + inner_w + 2.0 * PAD_OUTER
        content_x0 = frame_x0 + PAD_OUTER

        z = -PAD_OUTER  # Start at top inside border (panel extends downward in -Z)

        for sec_idx, sec in enumerate(col['sections']):
            if sec_idx > 0:
                # Subtle section divider line
                z -= SEC_GAP * 0.45
                wb.add_line(content_x0, z, content_x0 + inner_w, z)
                z -= SEC_GAP * 0.55

            sec_title = sec.get('title', '')
            if sec_title:
                wb.add_text(
                    sec_title,
                    content_x0,
                    z - HEADER_H * 0.48,
                    HEADER_H * 0.85,
                    align_x='LEFT',
                    align_y='CENTER',
                    max_width=inner_w,
                )
                z -= HEADER_H + HEADER_GAP

            for row_idx, row in enumerate(sec['rows']):
                if row_idx > 0:
                    z -= ROW_GAP * 1.4

                rtype = row.get('type', 'grid')

                if rtype == 'grid':
                    items = row.get('items', [])
                    if not items:
                        continue
                    ncols = max(1, int(row.get('cols', 2)))
                    cell_w = (inner_w - (ncols - 1) * COL_GAP) / ncols
                    for i, item in enumerate(items):
                        r_i = i // ncols
                        c_i = i % ncols
                        ix = content_x0 + c_i * (cell_w + COL_GAP)
                        iz = z - r_i * (HSLIDER_H + ROW_GAP)
                        _draw_hslider(ix, iz, cell_w, item)
                    nrows = (len(items) + ncols - 1) // ncols
                    z -= nrows * HSLIDER_H + max(0, nrows - 1) * ROW_GAP

                elif rtype == 'pad_and_sliders':
                    pad = row.get('pad')
                    sliders = row.get('sliders', [])
                    s_cols = max(1, int(row.get('slider_cols', 1)))
                    pad_sz = row.get('pad_size', PAD2D_SIZE)

                    pad_bottom_extra = u * 0.055 if (pad and pad.get('label')) else 0.0
                    if pad:
                        _draw_pad2d(content_x0, z, pad_sz, pad)

                    s_x0 = content_x0 + (pad_sz + COL_GAP * 1.4 if pad else 0.0)
                    rem_w = max(HSLIDER_W, inner_w - (s_x0 - content_x0))
                    cell_w = (rem_w - (s_cols - 1) * COL_GAP) / s_cols

                    for i, item in enumerate(sliders):
                        r_i = i // s_cols
                        c_i = i % s_cols
                        ix = s_x0 + c_i * (cell_w + COL_GAP)
                        iz = z - r_i * (HSLIDER_H + ROW_GAP)
                        _draw_hslider(ix, iz, cell_w, item)

                    s_rows = (len(sliders) + s_cols - 1) // s_cols if sliders else 0
                    s_h = (s_rows * HSLIDER_H + max(0, s_rows - 1) * ROW_GAP) if s_rows else 0.0
                    p_h = (pad_sz + pad_bottom_extra) if pad else 0.0
                    z -= max(p_h, s_h)

                elif rtype == 'vsliders_and_pad':
                    pad = row.get('pad')
                    vsliders = row.get('vsliders', [])
                    v_h = row.get('v_height', VSLIDER_H)
                    pad_sz = row.get('pad_size', v_h)

                    vx = content_x0
                    if pad:
                        _draw_pad2d(vx, z, pad_sz, pad)
                        vx += pad_sz + COL_GAP * 1.4

                    for v_item in vsliders:
                        _draw_vslider(vx, z, v_h, v_item)
                        vx += VSLIDER_W + COL_GAP * 0.65

                    lbl_extra = u * 0.060
                    z -= max(pad_sz if pad else 0.0, v_h) + lbl_extra

                elif rtype == 'pads_row':
                    pads = row.get('pads', [])
                    if not pads:
                        continue
                    psize = row.get('pad_size', u * 0.28)
                    px = content_x0
                    has_lbl = any(p.get('label') for p in pads)
                    for p_item in pads:
                        _draw_pad2d(px, z, psize, p_item)
                        px += psize + COL_GAP * 1.5
                    z -= psize + (u * 0.055 if has_lbl else 0.0)

        frame_z_bot = z - PAD_OUTER
        # Outer Genshin-style rectangular border
        wb.add_rect(frame_x0, frame_z_bot, frame_x1, 0.0)

        cursor_x = frame_x1 + PANEL_COL_GAP
        total_width = frame_x1

    safe_tag = "".join(c if c.isalnum() or c in "_-" else "_" for c in (unique_tag or ""))[:32]
    board_widget_name = f"WGT-FacePanel_{game_tag}_{safe_tag}_Board" if safe_tag else f"WGT-FacePanel_{game_tag}_Board"
    board_wgt = wb.build_object(board_widget_name, wgt_coll)

    # Prepend FacePanel-Root (movable/scalable tab at top-center of first panel) and FacePanel-Board
    root_ctrl = {
        'name': root_name,
        'collection': collection_name,
        'color': COL_ROOT,
        'group': 'Face Panel Root',
        'head': _to_world(0.0, 0.0),
        'widget_obj': wgt_root_tab,
        'lim': 0.0,
        'free': ('X', 'Y', 'Z'),
        'range': 'free',
        'shape_scale': Vector((u * 0.14, u * 0.14, u * 0.14)),
        'custom_shape_translation': Vector((total_width * 0.5, 0.0, u * 0.055)),
        'is_panel_root': True,
        'panel_space': True,
        'parent_bone': 'Face-Root',
        'drivers': [],
    }
    board_ctrl = {
        'name': board_name,
        'collection': collection_name,
        'color': COL_BOARD,
        'group': 'Face Panel Board',
        'head': _to_world(0.0, 0.0),
        'widget_obj': board_wgt,
        'lim': 0.0,
        'free': (),
        'range': 'locked',
        'shape_scale': Vector((1.0, 1.0, 1.0)),
        'is_panel_board': True,
        'panel_space': True,
        'parent_bone': root_name,
        'drivers': [],
    }

    return board_wgt, [root_ctrl, board_ctrl] + controls
