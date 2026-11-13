import json
import bpy
from mathutils import Matrix, Vector

from setup_wizard.domain.game_types import GameType


BONE_NAME = "Light Direction"
MCH_PARENT_BONE_NAME = "MCH-Light Direction-parent"
PARENT_SWITCH_CANDIDATES = ("root", "root.001", "root.002")


def _is_helper_rig(obj):
    if not obj or obj.type != "ARMATURE":
        return True
    low = obj.name.lower()
    return any(ign in low for ign in ("eyerig", "facerig", "lighting", "metarig", "wgt"))


def _find_target_rig(context):
    active = getattr(context, "active_object", None)
    if active and not _is_helper_rig(active):
        if active.data.get("rig_id") or active.name.endswith("Rig"):
            return active

    view_objs = getattr(getattr(context, "view_layer", None), "objects", context.scene.objects)
    candidates = [o for o in view_objs if not _is_helper_rig(o)]
    generated = [o for o in candidates if o.data.get("rig_id") or o.name.endswith("Rig")]
    if generated:
        return generated[-1]
    if candidates:
        return candidates[-1]
    return None


def _is_zzz_kythera_v2(context, rig_obj):
    if getattr(context.scene, "zzz_shader_type", "LEGACY") == "KYTHERA":
        return True
    if any(group.get("zzz_kythera_vectors") for group in bpy.data.node_groups):
        return True
    try:
        from setup_wizard.utils.zzz_kythera_lighting import is_kythera_v2_material
        for obj in bpy.data.objects:
            if obj.type != "MESH":
                continue
            if rig_obj is not None and obj.find_armature() not in (rig_obj, None):
                continue
            for slot in getattr(obj, "material_slots", []) or []:
                if slot.material and is_kythera_v2_material(slot.material):
                    return True
    except Exception:
        pass
    return False


def _find_light_empty(base_name, char_name, rig_obj):
    for candidate_name in (f"{base_name}_{char_name}", base_name):
        obj = bpy.data.objects.get(candidate_name)
        if not obj or obj.type != "EMPTY":
            continue
        bound_to_other = any(
            c.type == "COPY_TRANSFORMS" and c.target is not None and c.target != rig_obj
            for c in getattr(obj, "constraints", []) or []
        )
        if not bound_to_other:
            return obj
    return None


def _ensure_wgt_collection(context, rig_obj, char_name):
    for coll_name in (f"WGTS_{char_name}", f"WGTS_{rig_obj.name}", "wgt", "WGTS"):
        coll = bpy.data.collections.get(coll_name)
        if coll is not None:
            return coll

    wgt_coll = bpy.data.collections.new(f"WGTS_{char_name}")
    parent_coll = None
    for coll in getattr(rig_obj, "users_collection", []) or []:
        if coll != context.scene.collection and "wgt" not in coll.name.lower():
            parent_coll = coll
            break
    if parent_coll is not None:
        parent_coll.children.link(wgt_coll)
    else:
        context.scene.collection.children.link(wgt_coll)

    wgt_coll.hide_viewport = True
    wgt_coll.hide_select = True
    wgt_coll.hide_render = True
    return wgt_coll


def _move_to_collection_only(obj, target_coll):
    for coll in list(getattr(obj, "users_collection", []) or []):
        coll.objects.unlink(obj)
    if obj.name not in target_coll.objects:
        target_coll.objects.link(obj)


def _build_arrow_geometry(display_type, size):
    s = max(float(size or 1.0), 0.05)
    verts = []
    edges = []

    def add_arrow(axis_idx):
        base = len(verts)
        tip = [0.0, 0.0, 0.0]
        tip[axis_idx] = s
        verts.append((0.0, 0.0, 0.0))
        verts.append(tuple(tip))
        edges.append((base, base + 1))

        head_len = s * 0.75
        head_r = s * 0.035
        other = [i for i in range(3) if i != axis_idx]
        ring = []
        for sign_a, sign_b in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            p = [0.0, 0.0, 0.0]
            p[axis_idx] = head_len
            p[other[0]] = sign_a * head_r
            p[other[1]] = sign_b * head_r
            ring.append(len(verts))
            verts.append(tuple(p))
        for idx in ring:
            edges.append((base + 1, idx))
        for i in range(4):
            edges.append((ring[i], ring[(i + 1) % 4]))

    if display_type == "PLAIN_AXES":
        verts = [
            (-s, 0.0, 0.0), (s, 0.0, 0.0),
            (0.0, -s, 0.0), (0.0, s, 0.0),
            (0.0, 0.0, -s), (0.0, 0.0, s),
        ]
        edges = [(0, 1), (2, 3), (4, 5)]
    elif display_type == "ARROWS":
        for axis in (0, 1, 2):
            add_arrow(axis)
    else:
        add_arrow(2)

    return verts, edges


def _create_or_update_widget_mesh(wgt_name, display_type, size, wgt_coll):
    verts, edges = _build_arrow_geometry(display_type, size)
    existing = bpy.data.objects.get(wgt_name)
    if existing and existing.type == "MESH":
        mesh = existing.data
        mesh.clear_geometry()
        mesh.from_pydata(verts, edges, [])
        mesh.update()
        _move_to_collection_only(existing, wgt_coll)
        return existing

    mesh = bpy.data.meshes.new(wgt_name)
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    wgt_obj = bpy.data.objects.new(wgt_name, mesh)
    wgt_coll.objects.link(wgt_obj)
    return wgt_obj


def _assign_bone_to_visible_collection(rig_obj, bone):
    if not hasattr(rig_obj.data, "collections"):
        return
    for c in list(bone.collections):
        c.unassign(bone)
    colls = rig_obj.data.collections
    target = colls.get("Root") or colls.get("Other")
    if target is None:
        target = next((c for c in colls if not c.is_hidden), None)
    if target is None:
        target = colls.new("Root")
    target.is_visible = True
    target.assign(bone)


def _assign_bone_to_mch_collection(rig_obj, bone):
    if hasattr(rig_obj.data, "collections"):
        for c in list(bone.collections):
            c.unassign(bone)
        mch_coll = rig_obj.data.collections.get("MCH") or rig_obj.data.collections.get("Other")
        if mch_coll is not None:
            mch_coll.assign(bone)
    bone.hide = True


def _get_parent_switch_targets(rig_obj):
    targets = [name for name in PARENT_SWITCH_CANDIDATES if name in rig_obj.pose.bones]
    if not targets and "Root" in rig_obj.pose.bones:
        targets.append("Root")
    return targets


def _get_default_parent_switch_index(sw_targets):
    for preferred in ("root.002", "root.001", "root", "Root"):
        if preferred in sw_targets:
            return sw_targets.index(preferred) + 1
    return 0


def _setup_light_direction_parent_switch(rig_obj, pbone, sw_targets, default_idx):
    items = [("P0", "None", "")] + [(f"P{i + 1}", name, "") for i, name in enumerate(sw_targets)]
    pbone["parent_switch"] = default_idx
    try:
        pbone.id_properties_ui("parent_switch").update(
            items=items,
            default=default_idx,
            description="Light Direction Parent",
        )
    except Exception:
        pass

    mch_pb = rig_obj.pose.bones.get(MCH_PARENT_BONE_NAME)
    if mch_pb is None or not sw_targets:
        return

    const = mch_pb.constraints.get("SWITCH PARENT") or mch_pb.constraints.new("ARMATURE")
    const.name = "SWITCH PARENT"
    while len(const.targets) > len(sw_targets):
        const.targets.remove(const.targets[-1])
    while len(const.targets) < len(sw_targets):
        const.targets.new()

    for idx, subtarget in enumerate(sw_targets):
        tgt = const.targets[idx]
        tgt.target = rig_obj
        tgt.subtarget = subtarget
        try:
            tgt.driver_remove("weight")
        except Exception:
            pass
        fcurve = tgt.driver_add("weight")
        drv = fcurve.driver
        drv.type = "SCRIPTED"
        var = drv.variables.new()
        var.name = "toggle"
        var.type = "SINGLE_PROP"
        var.targets[0].id = rig_obj
        var.targets[0].data_path = f'pose.bones["{BONE_NAME}"]["parent_switch"]'
        drv.expression = f"toggle == {idx + 1}"

    const.enabled = False
    const.enabled = True


def _find_rig_ui_text(rig_obj):
    rig_id = rig_obj.data.get("rig_id") if getattr(rig_obj, "data", None) else None
    if rig_id:
        needle = f'rig_id = "{rig_id}"'
        for txt in bpy.data.texts:
            try:
                if needle in txt.as_string():
                    return txt, rig_id
            except Exception:
                continue
    for txt in bpy.data.texts:
        try:
            content = txt.as_string()
        except Exception:
            continue
        if 'rig_id = "' in content and "num_rig_separators[0] += 1" in content:
            parsed_id = content.split('rig_id = "')[1].split('"')[0]
            return txt, parsed_id
    return None, None


def _inject_light_direction_rig_ui(rig_obj, sw_targets):
    rig_file, rig_id = _find_rig_ui_text(rig_obj)
    if rig_file is None or not rig_id:
        return

    rig_text = rig_file.as_string()
    if f"is_selected({{'{BONE_NAME}'}})" in rig_text or f'is_selected({{"{BONE_NAME}"}})' in rig_text:
        return

    divider = "num_rig_separators[0] += 1"
    if divider not in rig_text:
        return

    pnames_json = json.dumps(["None"] + sw_targets)
    ui_block = (
        f"\n        if is_selected({{'{BONE_NAME}'}}):"
        f"\n            group1 = layout.row(align=True)"
        f"\n            group2 = group1.split(factor=0.55, align=True)"
        f"\n            props = group2.operator('pose.rigify_switch_parent_{rig_id}', text='Parent Switch', icon='DOWNARROW_HLT')"
        f"\n            props.bone = '{BONE_NAME}'"
        f"\n            props.prop_bone = '{BONE_NAME}'"
        f"\n            props.prop_id = 'parent_switch'"
        f"\n            props.parent_names = '{pnames_json}'"
        f"\n            props.locks = (False, False, False)"
        f"\n            group2.prop(pose_bones['{BONE_NAME}'], '[\"parent_switch\"]', text='')"
        f"\n            props = group1.operator('pose.rigify_switch_parent_bake_{rig_id}', text='', icon='ACTION_TWEAK')"
        f"\n            props.bone = '{BONE_NAME}'"
        f"\n            props.prop_bone = '{BONE_NAME}'"
        f"\n            props.prop_id = 'parent_switch'"
        f"\n            props.parent_names = '{pnames_json}'"
        f"\n            props.locks = (False, False, False)"
    )

    parts = rig_text.split(divider, 1)
    updated_text = parts[0] + divider + ui_block + parts[1]
    rig_file.clear()
    rig_file.write(updated_text)

    try:
        with bpy.context.temp_override(edit_text=rig_file):
            bpy.ops.text.run_script()
    except Exception:
        try:
            exec(compile(updated_text, rig_file.name, "exec"), {"__name__": "__main__"})
        except Exception as ex:
            print(f"[Light Direction] Warning: failed to reload rig UI script: {ex}")


def setup_light_direction_bone(context, game_type, rig_obj=None):
    """Convert the character's Light Direction empty into a bone on the rig.

    Keeps the hidden empty constrained to the bone via COPY_TRANSFORMS so
    Geometry Nodes (Light Vectors) and shader drivers keep working identically,
    while hiding the empty in WGTS so only the rig bone is user-facing.
    Skipped for ZZZ Kythera V2 (which uses a Sun light instead).
    """
    if rig_obj is None:
        rig_obj = _find_target_rig(context)
    if not rig_obj or rig_obj.type != "ARMATURE":
        return None

    if game_type == GameType.NEVERNESS_TO_EVERNESS.name:
        return None
    if game_type == GameType.ZENLESS_ZONE_ZERO.name and _is_zzz_kythera_v2(context, rig_obj):
        return None

    char_name = rig_obj.name[:-3] if rig_obj.name.endswith("Rig") else rig_obj.name
    light_dir = _find_light_empty("Light Direction", char_name, rig_obj)
    main_light_dir = _find_light_empty("Main Light Direction", char_name, rig_obj)
    source_empty = light_dir or main_light_dir
    if source_empty is None:
        return None

    wgt_coll = _ensure_wgt_collection(context, rig_obj, char_name)
    display_type = getattr(source_empty, "empty_display_type", "SINGLE_ARROW")
    display_size = float(getattr(source_empty, "empty_display_size", 1.0) or 1.0)
    wgt_obj = _create_or_update_widget_mesh(
        f"WGT-{BONE_NAME}_{char_name}", display_type, display_size, wgt_coll
    )

    arm_local_mat = rig_obj.matrix_world.inverted() @ source_empty.matrix_world
    loc = arm_local_mat.translation.copy()
    init_euler = arm_local_mat.to_euler("XYZ")
    bone_scale = tuple(arm_local_mat.to_scale())
    bone_mat = Matrix.Translation(loc)

    prev_active = getattr(context.view_layer.objects, "active", None)
    prev_mode = prev_active.mode if prev_active else "OBJECT"
    was_hidden = rig_obj.hide_viewport

    try:
        if prev_active and prev_active.mode != "OBJECT" and bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode="OBJECT")

        rig_obj.hide_viewport = False
        rig_obj.hide_set(False)
        for o in context.selected_objects:
            o.select_set(False)
        rig_obj.select_set(True)
        context.view_layer.objects.active = rig_obj

        bpy.ops.object.mode_set(mode="EDIT")
        ebs = rig_obj.data.edit_bones
        mch_eb = ebs.get(MCH_PARENT_BONE_NAME) or ebs.new(MCH_PARENT_BONE_NAME)
        mch_eb.use_deform = False
        mch_eb.use_connect = False
        mch_eb.parent = None
        mch_eb.head = loc
        mch_eb.tail = loc + Vector((0.0, max(display_size * 0.5, 0.25), 0.0))
        mch_eb.matrix = bone_mat

        eb = ebs.get(BONE_NAME) or ebs.new(BONE_NAME)
        eb.use_deform = False
        eb.use_connect = False
        eb.parent = mch_eb
        eb.head = loc
        eb.tail = loc + Vector((0.0, max(display_size * 0.5, 0.25), 0.0))
        eb.matrix = bone_mat
        bpy.ops.object.mode_set(mode="OBJECT")

        bone = rig_obj.data.bones.get(BONE_NAME)
        if bone is not None:
            _assign_bone_to_visible_collection(rig_obj, bone)

        mch_bone = rig_obj.data.bones.get(MCH_PARENT_BONE_NAME)
        if mch_bone is not None:
            _assign_bone_to_mch_collection(rig_obj, mch_bone)

        pbone = rig_obj.pose.bones.get(BONE_NAME)
        if pbone is not None:
            pbone.rotation_mode = "XYZ"
            pbone.rotation_euler = init_euler
            pbone.custom_shape = wgt_obj
            pbone.use_custom_shape_bone_size = False
            pbone.custom_shape_scale_xyz = bone_scale

            sw_targets = _get_parent_switch_targets(rig_obj)
            default_idx = _get_default_parent_switch_index(sw_targets)
            _setup_light_direction_parent_switch(rig_obj, pbone, sw_targets, default_idx)
            _inject_light_direction_rig_ui(rig_obj, sw_targets)

        for emp in (light_dir, main_light_dir):
            if emp is None:
                continue
            for con in list(emp.constraints):
                if con.type in ("CHILD_OF", "COPY_TRANSFORMS"):
                    emp.constraints.remove(con)
            con = emp.constraints.new("COPY_TRANSFORMS")
            con.target = rig_obj
            con.subtarget = BONE_NAME
            _move_to_collection_only(emp, wgt_coll)
            emp.hide_viewport = True
            emp.hide_select = True
            emp.hide_render = True
    finally:
        rig_obj.hide_viewport = was_hidden
        try:
            if prev_active and prev_active.name in bpy.data.objects:
                context.view_layer.objects.active = prev_active
                if prev_mode != "OBJECT" and bpy.ops.object.mode_set.poll():
                    bpy.ops.object.mode_set(mode=prev_mode)
        except Exception:
            pass

    return rig_obj.pose.bones.get(BONE_NAME)
