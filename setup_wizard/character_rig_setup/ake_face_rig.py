# Author: michael-gh1, PaoloESAN
# Arknights: Endfield - Isaac Face Rig Integration

import os
import math
import bpy
from bpy.types import Operator
from mathutils import Vector, Matrix

from setup_wizard.domain.game_types import GameType
from setup_wizard.setup_wizard_operator_base_classes import BasicSetupUIOperator


ENDFIELD_FACE_MAPPING = {
    # Eyebrows Left
    "browLf01Joint": {"master": "Eyebrow-Master.L", "deform": "brow_Inn_L"},
    "browLf02Joint": {"master": "Eyebrow-Master.L", "deform": "brow_Inn_L"},
    "browLf03Joint": {"master": "Eyebrow-Master.L", "deform": "brow_Mid_L"},
    "browLf04Joint": {"master": "Eyebrow-Master.L", "deform": "brow_Mid_L"},
    "browLf05Joint": {"master": "Eyebrow-Master.L", "deform": "brow_Out_L"},
    "browLineLf01Joint": {"master": "Eyebrow-Master.L", "deform": "eyebrow_Inn_L"},
    "browLineLf02Joint": {"master": "Eyebrow-Master.L", "deform": "eyebrow_Mid_L"},
    "browLineLf03Joint": {"master": "Eyebrow-Master.L", "deform": "eyebrow_Out_L"},

    # Eyebrows Right
    "browRt01Joint": {"master": "Eyebrow-Master.R", "deform": "brow_Inn_R"},
    "browRt02Joint": {"master": "Eyebrow-Master.R", "deform": "brow_Inn_R"},
    "browRt03Joint": {"master": "Eyebrow-Master.R", "deform": "brow_Mid_R"},
    "browRt04Joint": {"master": "Eyebrow-Master.R", "deform": "brow_Mid_R"},
    "browRt05Joint": {"master": "Eyebrow-Master.R", "deform": "brow_Out_R"},
    "browLineRt01Joint": {"master": "Eyebrow-Master.R", "deform": "eyebrow_Inn_R"},
    "browLineRt02Joint": {"master": "Eyebrow-Master.R", "deform": "eyebrow_Mid_R"},
    "browLineRt03Joint": {"master": "Eyebrow-Master.R", "deform": "eyebrow_Out_R"},

    # Eyes & Eyelids Left
    "eyeLf01Joint": {"master": "Eye-Master.L", "deform": "eyeconner_inn_L"},
    "eyeLf02Joint": {"master": "Eye-Master.L", "deform": "eyeup_inn_L"},
    "eyeLf03Joint": {"master": "Eye-Master.L", "deform": "eyeup_M_L"},
    "eyeLf04Joint": {"master": "Eye-Master.L", "deform": "eyeup_out_L"},
    "eyeLf05Joint": {"master": "Eye-Master.L", "deform": "eyeconner_out_L"},
    "eyeLf06Joint": {"master": "Eye-Master.L", "deform": "eyedn_out_L"},
    "eyeLf07Joint": {"master": "Eye-Master.L", "deform": "eyedn_M_L"},
    "eyeLf08Joint": {"master": "Eye-Master.L", "deform": "eyedn_inn_L"},

    # Eyes & Eyelids Right
    "eyeRt01Joint": {"master": "Eye-Master.R", "deform": "eyeconner_inn_R"},
    "eyeRt02Joint": {"master": "Eye-Master.R", "deform": "eyeup_inn_R"},
    "eyeRt03Joint": {"master": "Eye-Master.R", "deform": "eyeup_M_R"},
    "eyeRt04Joint": {"master": "Eye-Master.R", "deform": "eyeup_out_R"},
    "eyeRt05Joint": {"master": "Eye-Master.R", "deform": "eyeconner_out_R"},
    "eyeRt06Joint": {"master": "Eye-Master.R", "deform": "eyedn_out_R"},
    "eyeRt07Joint": {"master": "Eye-Master.R", "deform": "eyedn_M_R"},
    "eyeRt08Joint": {"master": "Eye-Master.R", "deform": "eyedn_inn_R"},

    # Mouth & Lips
    "lipMupJoint": {"mouth_chain": True, "deform": "lipUpper_M"},
    "lipMdnJoint": {"mouth_chain": True, "deform": "lipLower_M"},
    "lipLup1Joint": {"mouth_chain": True, "deform": "lipConner_L"},
    "lipLup2Joint": {"mouth_chain": True, "deform": "lipUpper_01_L"},
    "lipLup3Joint": {"mouth_chain": True, "deform": "lipUpper_00_L"},
    "lipLup4Joint": {"mouth_chain": True, "deform": "lipUpper_00_L"},
    "lipLdn1Joint": {"mouth_chain": True, "deform": "lipConner_L"},
    "lipLdn2Joint": {"mouth_chain": True, "deform": "lipLower_01_L"},
    "lipLdn3Joint": {"mouth_chain": True, "deform": "lipLower_00_L"},
    "lipLdn4Joint": {"mouth_chain": True, "deform": "lipLower_00_L"},
    "lipRup1Joint": {"mouth_chain": True, "deform": "lipConner_R"},
    "lipRup2Joint": {"mouth_chain": True, "deform": "lipUpper_01_R"},
    "lipRup3Joint": {"mouth_chain": True, "deform": "lipUpper_00_R"},
    "lipRup4Joint": {"mouth_chain": True, "deform": "lipUpper_00_R"},
    "lipRdn1Joint": {"mouth_chain": True, "deform": "lipConner_R"},
    "lipRdn2Joint": {"mouth_chain": True, "deform": "lipLower_01_R"},
    "lipRdn3Joint": {"mouth_chain": True, "deform": "lipLower_00_R"},
    "lipRdn4Joint": {"mouth_chain": True, "deform": "lipLower_00_R"},

    # Cheeks Left & Right
    "faceLfCheekOtJoint": {"mouth_master": True, "deform": "chhek_L"},
    "faceLfCheekOtUpJoint": {"mouth_master": True, "deform": "chhek_L"},
    "faceLfCheekOtDnJoint": {"mouth_master": True, "deform": "mouthUpper_03_L.001"},
    "faceLfCheekOtInJoint": {"mouth_master": True, "deform": "mouthUpper_01_L.001"},
    "faceRtCheekOtJoint": {"mouth_master": True, "deform": "chhek_R"},
    "faceRtCheekOtUpJoint": {"mouth_master": True, "deform": "chhek_R"},
    "faceRtCheekOtDnJoint": {"mouth_master": True, "deform": "mouthUpper_03_R.001"},
    "faceRtCheekOtInJoint": {"mouth_master": True, "deform": "mouthUpper_01_R.001"},

    # Jaw & Teeth
    "jawJoint": {"deform": "mouthLower_M.001"},
    "faceMdJawDnJoint": {"deform": "mouthLower_M.001"},
    "faceMdToothUpJoint": {"mouth_chain": True, "deform": "UpTeeth"},
    "faceMdToothDnJoint": {"mouth_chain": True, "deform": "DownTeeth"},
    "line_toothJoint": {"mouth_chain": True, "deform": "DownTeeth"},

    # Tongue
    "TongueMd01Joint": {"mouth_chain": True, "deform": "tongue_01"},
    "TongueMd02Joint": {"mouth_chain": True, "deform": "tongue_02"},
    "TongueMd03Joint": {"mouth_chain": True, "deform": "tongue_03"},
    "TongueMd04Joint": {"mouth_chain": True, "deform": "tongue_04"},

    # Nose
    "NoseMd01Joint": {"deform": "nosetip_M"},
}


def _resolve_isaac_eyes(rig, eye_names=None):
    eyes = {}
    for side in ("L", "R"):
        names = [eye_names[side]] if eye_names and side in eye_names else [
            f"eye.{side}", f"DEF-eye.{side}", f"face{'Lf' if side == 'L' else 'Rt'}IrisJoint"]
        eyes[side] = next((name for name in names if name in rig.pose.bones), None)
    return eyes


def _isaac_iris_center(rig, side, name, context):
    """Find the iris surface in rig rest space, including rigid NPC irises."""
    candidates = list(dict.fromkeys([f'face{"Lf" if side == "L" else "Rt"}IrisJoint',
                                    f'DEF-eye.{side}', name]))
    inverse = rig.matrix_world.inverted()
    for candidate in candidates:
        points = []
        for mesh in context.scene.objects:
            if mesh.type != 'MESH' or not any(m.type == 'ARMATURE' and m.object == rig for m in mesh.modifiers):
                continue
            group = mesh.vertex_groups.get(candidate)
            if group is None:
                continue
            transform = inverse @ mesh.matrix_world
            points.extend(transform @ v.co for v in mesh.data.vertices
                          if any(g.group == group.index and g.weight > .9 for g in v.groups))
        if points:
            return sum(points, Vector()) / len(points)
    return rig.data.bones[name].head_local.copy()


def bind_isaac_eye_tracking(rig, eyes, pivots=None, context=None):
    """Rotate the iris around its socket without translating it with the gaze target."""
    context = context or bpy.context
    pivots = pivots or {"L": "eyeLfJoint", "R": "eyeRtJoint"}
    context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='OBJECT')
    positions = {}
    follow_positions = {}
    context.view_layer.update()
    for side, name in eyes.items():
        if not name:
            continue
        pivot = rig.data.bones.get(pivots.get(side, ""))
        saved_socket = rig.get(f'ake_eye_socket_{side}')
        positions[side] = (pivot.head_local.copy() if pivot else
                           Vector(saved_socket) if saved_socket is not None else
                           rig.data.bones[name].head_local.copy())
        follow = rig.pose.bones.get(f"Eye-Track-Follow.{side}")
        if follow:
            target = follow.bone.head_local.copy()
            ray = _isaac_iris_center(rig, side, name, context) - positions[side]
            if ray.length > 1e-6 and (target - positions[side]).dot(ray) <= 0:
                # The template panel can end up behind a scaled FBX socket.
                # Keep the gaze target in front of the iris in the neutral pose.
                world_scale = max(rig.matrix_world.to_scale().length / math.sqrt(3), 1e-6)
                target = positions[side] + ray.normalized() * max(ray.length * 2, .1 / world_scale)
            follow_positions[side] = target
        for c in list(rig.pose.bones[name].constraints):
            if c.name.startswith("Isaac_Eye"):
                rig.pose.bones[name].constraints.remove(c)
    bpy.ops.object.mode_set(mode='EDIT')
    for side, position in positions.items():
        eye = rig.data.edit_bones[eyes[side]]
        track = rig.data.edit_bones.get(f"Eye-Track.{side}")
        if not track:
            continue
        follow = rig.data.edit_bones.get(f"Eye-Track-Follow.{side}")
        if follow and side in follow_positions:
            offset = follow_positions[side] - follow.head
            follow.head += offset
            follow.tail += offset
        length = track.length or 0.05
        track.head = position
        direction = follow_positions.get(side, position + Vector((0, -1, 0))) - position
        track.tail = position + direction.normalized() * length
        track.roll = 0
        mechanism = rig.data.edit_bones.get(f"MCH-Isaac-EyeOrbit.{side}")
        if mechanism is None:
            mechanism = rig.data.edit_bones.new(f"MCH-Isaac-EyeOrbit.{side}")
            mechanism.parent = eye.parent
            mechanism.use_deform = False
            eye.use_connect = False
            eye.parent = mechanism
        # Use the tracker frame, not the imported iris joint's arbitrary axes.
        # Reparenting in edit mode keeps the iris's global rest transform intact.
        track.parent = mechanism.parent
        track.use_connect = False
        mechanism.head = track.head.copy()
        mechanism.tail = track.tail.copy()
        mechanism.roll = track.roll
    bpy.ops.object.mode_set(mode='OBJECT')
    context.view_layer.update()
    for side, name in eyes.items():
        mechanism = rig.pose.bones.get(f"MCH-Isaac-EyeOrbit.{side}")
        track = rig.pose.bones.get(f"Eye-Track.{side}")
        if not name or not mechanism or not track:
            continue
        for c in list(mechanism.constraints):
            if c.name.startswith('Isaac_'):
                mechanism.constraints.remove(c)
        orbit = mechanism.constraints.new('COPY_ROTATION')
        orbit.name = f"Isaac_EyeOrbit_{side}"
        orbit.target = rig
        orbit.subtarget = track.name
        orbit.owner_space = orbit.target_space = 'POSE'
        bone = rig.data.bones[mechanism.name]
        if hasattr(rig.data, 'collections'):
            other = rig.data.collections.get('Other') or rig.data.collections.new('Other')
            for collection in list(bone.collections):
                collection.unassign(bone)
            other.assign(bone)
        else:
            bone.layers = tuple(index == 25 for index in range(32))
        bone.hide = True
        scale = rig.pose.bones[name].constraints.new('COPY_SCALE')
        scale.name = f"Isaac_EyeScale_{side}"
        scale.target = rig
        scale.subtarget = f"Eye-Scale-Control.{side}"
        scale.owner_space = scale.target_space = 'LOCAL'
    context.view_layer.update()


def bind_endfield_iris_scale(rig, eyes, context):
    """Bind scale to the weighted iris, about its mesh center rather than the socket."""
    meshes = [obj for obj in context.scene.objects if obj.type == 'MESH' and
              any(mod.type == 'ARMATURE' and mod.object == rig for mod in obj.modifiers)]
    inverse = rig.matrix_world.inverted()
    plans = []
    for side in ('L', 'R'):
        candidates = [f'face{ "Lf" if side == "L" else "Rt" }IrisJoint',
                      f'DEF-eye.{side}', eyes.get(side), f'eye{ "Lf" if side == "L" else "Rt" }Joint']
        for name in dict.fromkeys(n for n in candidates if n):
            if name not in rig.data.bones:
                continue
            points = []
            for mesh in meshes:
                group = mesh.vertex_groups.get(name)
                if group is None:
                    continue
                transform = inverse @ mesh.matrix_world
                for vertex in mesh.data.vertices:
                    if any(g.group == group.index and g.weight > .9 for g in vertex.groups):
                        points.append(transform @ vertex.co)
            if not points:
                continue
            center = sum(points, Vector()) / len(points)
            plans.append((side, name, center))
            break
    # The iris follows the head through its parent hierarchy. Duplicate
    # deform weights would leave an unscaled contribution when shrinking it.
    for side, name, center in plans:
        for mesh in meshes:
            group = mesh.vertex_groups.get(name)
            if group is None:
                continue
            indices = [v.index for v in mesh.data.vertices
                       if any(g.group == group.index and g.weight > .9 for g in v.groups)]
            if not indices:
                continue
            for other in mesh.vertex_groups:
                bone = rig.data.bones.get(other.name)
                if other != group and bone and bone.use_deform:
                    other.remove(indices)
            group.add(indices, 1.0, 'REPLACE')

    # Remove the old binding on the tracking control and refresh existing rigs.
    for side, name, center in plans:
        for bone_name in dict.fromkeys([eyes.get(side), name]):
            bone = rig.pose.bones.get(bone_name or '')
            if bone:
                for constraint in list(bone.constraints):
                    if constraint.name == f'Isaac_EyeScale_{side}':
                        bone.constraints.remove(constraint)
    context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    bones = rig.data.edit_bones
    for side, name, center in plans:
        # Rigid NPC irises can be offset from their socket joint. Place the
        # scale widget over the actual iris while retaining the panel depth.
        control = bones.get(f'Eye-Scale-Control.{side}')
        if control:
            offset = Vector((center.x - control.head.x, 0.0, center.z - control.head.z))
            control.head += offset
            control.tail += offset
        iris = bones[name]
        mechanism = bones.get(f'MCH-Isaac-IrisScale.{side}')
        if mechanism is None:
            mechanism = bones.new(f'MCH-Isaac-IrisScale.{side}')
            mechanism.matrix = iris.matrix.copy()
            mechanism.head = center
            mechanism.tail = center + iris.y_axis * max(iris.length, .01)
            mechanism.parent = iris.parent
            mechanism.use_deform = False
            iris.use_connect = False
            iris.parent = mechanism
    bpy.ops.object.mode_set(mode='OBJECT')
    for side, name, center in plans:
        mechanism = rig.pose.bones[f'MCH-Isaac-IrisScale.{side}']
        for constraint in list(mechanism.constraints):
            if constraint.name == f'Isaac_IrisScale_{side}':
                mechanism.constraints.remove(constraint)
        scale = mechanism.constraints.new('COPY_SCALE')
        scale.name = f'Isaac_IrisScale_{side}'
        scale.target = rig
        scale.subtarget = f'Eye-Scale-Control.{side}'
        scale.owner_space = scale.target_space = 'LOCAL'
        mechanism.bone.hide = True
        if hasattr(rig.data, 'collections'):
            other = rig.data.collections.get('Other') or rig.data.collections.new('Other')
            for collection in list(mechanism.bone.collections):
                collection.unassign(mechanism.bone)
            other.assign(mechanism.bone)
    context.view_layer.update()


def align_endfield_mouth_panel(rig, context):
    """Center the mouth widgets vertically on the imported lips in rest space."""
    upper = rig.data.bones.get('lipMupJoint')
    lower = rig.data.bones.get('lipMdnJoint')
    master = rig.data.bones.get('Mouth-Master')
    if not upper or not lower or not master:
        return
    height = (upper.head_local.z + lower.head_local.z) * .5
    offset = Vector((0.0, 0.0, height - master.head_local.z))
    if abs(offset.z) < 1e-6:
        return
    context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    master = rig.data.edit_bones['Mouth-Master']
    # Move the complete panel together so local control/deform transforms stay
    # unchanged. Imported facial joints and the eye panel retain their rest pose.
    for bone in [master, *master.children_recursive]:
        bone.head += offset
        bone.tail += offset
    bpy.ops.object.mode_set(mode='OBJECT')
    context.view_layer.update()


def bind_isaac_face_deformations(body_rig, face_mapping):
    """Refresh imported facial bindings without appending another control rig."""
    assigned_count = 0
    for bone_name, mapping in face_mapping.items():
        pb = body_rig.pose.bones.get(bone_name)
        if not pb:
            continue

        # Remove existing Isaac constraints to allow clean idempotent re-runs
        for c in list(pb.constraints):
            if c.name.startswith("Isaac_"):
                pb.constraints.remove(c)

        btype = mapping.get("type", "TRANSFORMS")

        if btype == "ROTATION":
            c = pb.constraints.new('COPY_ROTATION')
            c.name = "Isaac_CopyRotation"
            c.target = body_rig
            c.subtarget = mapping["deform"]
            c.owner_space = 'LOCAL'
            c.target_space = 'LOCAL_OWNER_ORIENT'
            assigned_count += 1

        elif btype == "SCALE":
            c = pb.constraints.new('COPY_SCALE')
            c.name = "Isaac_CopyScale"
            c.target = body_rig
            c.subtarget = mapping["deform"]
            c.owner_space = 'LOCAL'
            c.target_space = 'LOCAL'
            assigned_count += 1

        elif mapping.get("mouth_chain"):
            # Mouth chain: Mouth-Master -> Lip-Master -> Specific Deform Bone
            c1 = pb.constraints.new('COPY_TRANSFORMS')
            c1.name = "Isaac_MouthMaster"
            c1.target = body_rig
            c1.subtarget = "Mouth-Master"
            c1.owner_space = 'LOCAL'
            c1.target_space = 'LOCAL_OWNER_ORIENT'

            c2 = pb.constraints.new('COPY_TRANSFORMS')
            c2.name = "Isaac_LipMaster"
            c2.target = body_rig
            c2.subtarget = "Lip-Master"
            c2.owner_space = 'LOCAL'
            c2.target_space = 'LOCAL_OWNER_ORIENT'
            c2.mix_mode = 'AFTER'

            c3 = pb.constraints.new('COPY_TRANSFORMS')
            c3.name = f"Isaac_Deform_{mapping['deform']}"
            c3.target = body_rig
            c3.subtarget = mapping["deform"]
            c3.owner_space = 'LOCAL'
            c3.target_space = 'LOCAL_OWNER_ORIENT'
            c3.mix_mode = 'AFTER'
            assigned_count += 1

        elif mapping.get("mouth_master"):
            # Cheeks: Mouth-Master -> Specific Deform Bone
            c1 = pb.constraints.new('COPY_TRANSFORMS')
            c1.name = "Isaac_MouthMaster"
            c1.target = body_rig
            c1.subtarget = "Mouth-Master"
            c1.owner_space = 'LOCAL'
            c1.target_space = 'LOCAL_OWNER_ORIENT'

            c2 = pb.constraints.new('COPY_TRANSFORMS')
            c2.name = f"Isaac_Deform_{mapping['deform']}"
            c2.target = body_rig
            c2.subtarget = mapping["deform"]
            c2.owner_space = 'LOCAL'
            c2.target_space = 'LOCAL_OWNER_ORIENT'
            c2.mix_mode = 'AFTER'
            assigned_count += 1

        elif "master" in mapping:
            # Eyebrows / Eyelids: Master Bone -> Specific Deform Bone
            c1 = pb.constraints.new('COPY_TRANSFORMS')
            c1.name = f"Isaac_Master_{mapping['master']}"
            c1.target = body_rig
            c1.subtarget = mapping["master"]
            c1.owner_space = 'LOCAL'
            c1.target_space = 'LOCAL_OWNER_ORIENT'

            c2 = pb.constraints.new('COPY_TRANSFORMS')
            c2.name = f"Isaac_Deform_{mapping['deform']}"
            c2.target = body_rig
            c2.subtarget = mapping["deform"]
            c2.owner_space = 'LOCAL'
            c2.target_space = 'LOCAL_OWNER_ORIENT'
            c2.mix_mode = 'AFTER'
            assigned_count += 1

        else:
            # Jaw, Nose, etc.
            c = pb.constraints.new('COPY_TRANSFORMS')
            c.name = f"Isaac_Deform_{mapping['deform']}"
            c.target = body_rig
            c.subtarget = mapping["deform"]
            c.owner_space = 'LOCAL'
            c.target_space = 'LOCAL_OWNER_ORIENT'
            assigned_count += 1

    return assigned_count


def setup_endfield_isaac_face_rig(body_rig, context=None, face_mapping=None, eye_names=None, eye_pivots=None):
    """Sets up the Isaac Face Rig controls for Arknights: Endfield characters.
    
    Preserves original Endfield bone positions and geometry while binding
    face deformations to Isaac FaceRig control widgets.
    """
    if not body_rig or body_rig.type != 'ARMATURE':
        print("[AKE FACE RIG] Error: Invalid body armature provided.")
        return None

    if not context:
        context = bpy.context

    is_endfield = face_mapping is None
    face_mapping = ENDFIELD_FACE_MAPPING if face_mapping is None else face_mapping
    eyes = _resolve_isaac_eyes(body_rig, eye_names)

    # Idempotency (HSR parity): an already-fused body rig carries the FaceRig
    # bones itself; fusing again would only spawn .001 dupes.
    try:
        if "Eye-Track-Master" in body_rig.data.bones:
            if is_endfield:
                align_endfield_mouth_panel(body_rig, context)
            bind_isaac_face_deformations(body_rig, face_mapping)
            bind_isaac_eye_tracking(body_rig, eyes, eye_pivots, context)
            if is_endfield:
                bind_endfield_iris_scale(body_rig, eyes, context)
            print("[AKE FACE RIG] FaceRig already fused; facial bindings and eye tracking refreshed.")
            return body_rig
    except Exception:
        pass

    blend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'isaacfacerig.blend')
    if not os.path.exists(blend_path):
        print(f"[AKE FACE RIG] Error: File not found: {blend_path}")
        return None

    objects_before = set(bpy.data.objects)
    facerig_obj = None
    appended_coll = None

    # Check if isaac FaceRig already exists in the scene
    facerig_obj = bpy.data.objects.get("isaac FaceRig")
    if not facerig_obj:
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and any(k in obj.name.lower() for k in ['facerig', 'isaac']):
                facerig_obj = obj
                break

    # If not already in scene, append from isaacfacerig.blend
    if not facerig_obj:
        try:
            with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
                if data_from.collections:
                    first_coll_name = data_from.collections[0]
                    data_to.collections = [first_coll_name]
                    print(f"[AKE FACE RIG] Loading collection from blend: '{first_coll_name}'")

            for collection in data_to.collections:
                if collection:
                    appended_coll = collection
                    if collection.name not in context.scene.collection.children:
                        context.scene.collection.children.link(collection)
        except Exception as err:
            print(f"[AKE FACE RIG] Library load error: {err}")

        new_objects = set(bpy.data.objects) - objects_before
        for obj in new_objects:
            if obj.type == 'ARMATURE':
                facerig_obj = obj
                break

        if not facerig_obj:
            facerig_obj = bpy.data.objects.get("isaac FaceRig")

    if not facerig_obj:
        print("[AKE FACE RIG] Error: Could not find or append 'isaac FaceRig' armature.")
        return None

    print(f"[AKE FACE RIG] Using FaceRig armature: '{facerig_obj.name}'")

    # Organize collections: FaceRig armature to character collection,
    # widget planes to per-character WGTS_<Char> nested inside it (Append-safe)
    target_armature_coll = body_rig.users_collection[0] if body_rig.users_collection else context.scene.collection
    char_name = target_armature_coll.name if target_armature_coll != context.scene.collection else (body_rig.name.replace("Rig", "") or "Character")
    wgts_name = f"WGTS_{char_name}"
    wgt_coll = bpy.data.collections.get(wgts_name)
    if not wgt_coll:
        wgt_coll = bpy.data.collections.new(wgts_name)
    if wgt_coll.name not in target_armature_coll.children:
        try:
            target_armature_coll.children.link(wgt_coll)
        except Exception:
            pass
    if wgt_coll.name in context.scene.collection.children:
        try:
            context.scene.collection.children.unlink(wgt_coll)
        except Exception:
            pass
    try:
        wgt_coll.hide_viewport = True
        wgt_coll.hide_select = True
        wgt_coll.hide_render = True
    except Exception:
        pass

    if facerig_obj and target_armature_coll:
        if facerig_obj.name not in target_armature_coll.objects:
            target_armature_coll.objects.link(facerig_obj)
        for coll in list(facerig_obj.users_collection):
            if coll != target_armature_coll:
                coll.objects.unlink(facerig_obj)

    plane_objs = [
        obj for obj in (set(bpy.data.objects) - objects_before)
        if obj.type == 'MESH' and ('Plane.' in obj.name or 'wgt' in obj.name.lower()) and obj != facerig_obj
    ]
    if appended_coll:
        plane_objs.extend([obj for obj in appended_coll.objects if obj != facerig_obj and obj not in plane_objs])

    for p_obj in plane_objs:
        if p_obj.name not in wgt_coll.objects:
            wgt_coll.objects.link(p_obj)
        for coll in list(p_obj.users_collection):
            if coll != wgt_coll:
                coll.objects.unlink(p_obj)

    # Clean up appended collection if necessary
    if appended_coll:
        try:
            for parent_coll in bpy.data.collections:
                if appended_coll.name in parent_coll.children:
                    parent_coll.children.unlink(appended_coll)
            if appended_coll.name in context.scene.collection.children:
                context.scene.collection.children.unlink(appended_coll)
            bpy.data.collections.remove(appended_coll, do_unlink=True)
            print(f"[AKE FACE RIG] Cleaned up temporary collection '{appended_coll.name}'")
        except Exception as c_err:
            print(f"[AKE FACE RIG] Collection cleanup notice: {c_err}")

    # Set display properties
    facerig_obj.show_in_front = True

    # Identify head bone on body rig
    body_head_bone_name = None
    for candidate in ["DEF-spine.006", "head", "Head", "Head_M", "Bip001_Head"]:
        if candidate in body_rig.data.bones:
            body_head_bone_name = candidate
            break
    if not body_head_bone_name:
        for b in body_rig.data.bones.keys():
            if "head" in b.lower() or "spine.006" in b.lower():
                body_head_bone_name = b
                break

    if not body_head_bone_name:
        print("[AKE FACE RIG] Error: Could not find head bone on body rig.")
        return None

    facerig_head_bone_name = "DEF-spine.006" if "DEF-spine.006" in facerig_obj.data.bones else facerig_obj.data.bones[0].name

    # Align FaceRig world matrix to body head bone
    try:
        body_head_matrix_world = body_rig.matrix_world @ body_rig.pose.bones[body_head_bone_name].matrix
        facerig_head_matrix_local = facerig_obj.pose.bones[facerig_head_bone_name].matrix
        facerig_obj.matrix_world = body_head_matrix_world @ facerig_head_matrix_local.inverted()
    except Exception as e:
        print(f"[AKE FACE RIG] Matrix alignment warning: {e}")

    context.view_layer.update()

    # HSR parity: no head-follow constraint on the FaceRig (it would
    # self-target after the fuse below). DEF-spine.006 is removed from the
    # FaceRig instead, right before joining.
    context.view_layer.update()

    # Precisely align Eye-Track-Master, Eye-Track, Eye-Track-Follow, and Eye-Scale-Control to character's eye coordinates
    try:
        pb_eye_l = body_rig.pose.bones.get(eyes.get("L") or "")
        pb_eye_r = body_rig.pose.bones.get(eyes.get("R") or "")
        if pb_eye_l and pb_eye_r:
            eye_l_world = body_rig.matrix_world @ pb_eye_l.head
            eye_r_world = body_rig.matrix_world @ pb_eye_r.head
            eye_center_world = (eye_l_world + eye_r_world) / 2.0

            facerig_inv = facerig_obj.matrix_world.inverted()
            eye_l_local = facerig_inv @ eye_l_world
            eye_r_local = facerig_inv @ eye_r_world
            eye_center_local = (eye_l_local + eye_r_local) / 2.0

            orig_active = context.view_layer.objects.active
            orig_mode = facerig_obj.mode if facerig_obj.mode in ('OBJECT', 'EDIT', 'POSE') else 'OBJECT'
            context.view_layer.objects.active = facerig_obj
            bpy.ops.object.mode_set(mode='EDIT')
            ebs = facerig_obj.data.edit_bones

            # 1. Align Eye-Track-Master (the big eye rectangle) directly centered to eye height and midpoint
            eb_master = ebs.get("Eye-Track-Master")
            if eb_master:
                dx = eye_center_local.x - eb_master.head.x
                dz = eye_center_local.z - eb_master.head.z
                eb_master.head.x += dx
                eb_master.head.z += dz
                eb_master.tail.x += dx
                eb_master.tail.z += dz

            # 2. Align Eye-Scale-Control, Eye-Track, and Eye-Track-Follow for each eye
            for side, pos_local in [("L", eye_l_local), ("R", eye_r_local)]:
                # Eye scale control box: MUST stay at Eye-Track-Master depth Y (inside the blue rectangle)
                eb_scale = ebs.get(f"Eye-Scale-Control.{side}")
                if eb_scale and eb_master:
                    dx = pos_local.x - eb_scale.head.x
                    dz = pos_local.z - eb_scale.head.z
                    dy = eb_master.head.y - eb_scale.head.y
                    eb_scale.head.x += dx
                    eb_scale.head.z += dz
                    eb_scale.head.y += dy
                    eb_scale.tail.x += dx
                    eb_scale.tail.z += dz
                    eb_scale.tail.y += dy

                # Eye-Track gaze pivot centered on the eye, pointing straight forward with zero tilt
                eb_track = ebs.get(f"Eye-Track.{side}")
                if eb_track:
                    track_len = eb_track.length or 0.05
                    eb_track.head = pos_local.copy()
                    eb_track.tail = Vector((pos_local.x, pos_local.y - track_len, pos_local.z))
                    eb_track.roll = 0.0

                # Eye-Track-Follow target aligned in X and Z with the eye, at Eye-Track-Master depth Y
                eb_follow = ebs.get(f"Eye-Track-Follow.{side}")
                if eb_follow and eb_master:
                    dx = pos_local.x - eb_follow.head.x
                    dz = pos_local.z - eb_follow.head.z
                    dy = eb_master.head.y - eb_follow.head.y
                    eb_follow.head.x += dx
                    eb_follow.head.z += dz
                    eb_follow.head.y += dy
                    eb_follow.tail.x += dx
                    eb_follow.tail.z += dz
                    eb_follow.tail.y += dy

            bpy.ops.object.mode_set(mode=orig_mode)
            if orig_active:
                context.view_layer.objects.active = orig_active

            # NOTE: Child Of inverse on Eye-Track-Follow is fixed AFTER the fuse
            # (in body-rig space), and the lowered flag moves to the body rig.
            print("[AKE FACE RIG] Perfectly aligned Eye-Track-Master, Eye-Track, Eye-Track-Follow, and Eye-Scale-Control to character eye coordinates.")
    except Exception as align_err:
        print(f"[AKE FACE RIG] Warning while aligning eye widgets: {align_err}")

    context.view_layer.update()

    # Fuse the FaceRig into the body rig (HSR parity): a single armature
    # travels as one collection unit on Append instead of two rigs.
    # The FaceRig carries junk drivers from the template character in the
    # .blend (same file HSR fuses), which would clobber rig properties.
    try:
        facerig_obj.animation_data_clear()
    except Exception:
        pass
    try:
        prev_active = context.view_layer.objects.active
        try:
            facerig_obj.hide_viewport = False
            facerig_obj.hide_set(False)
        except Exception:
            pass
        context.view_layer.objects.active = facerig_obj
        bpy.ops.object.mode_set(mode='EDIT')
        eb_dupe = facerig_obj.data.edit_bones.get(facerig_head_bone_name)
        if eb_dupe:
            facerig_obj.data.edit_bones.remove(eb_dupe)
            print(f"[AKE FACE RIG] Removed '{facerig_head_bone_name}' from FaceRig to avoid collision on join.")
        bpy.ops.object.mode_set(mode='OBJECT')
        if prev_active:
            try:
                context.view_layer.objects.active = prev_active
            except Exception:
                pass
    except Exception as ex_undupe:
        print(f"[AKE FACE RIG] FaceRig dedupe notice: {ex_undupe}")
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass
    try:
        for o in (facerig_obj, body_rig):
            try:
                o.hide_viewport = False
                o.hide_set(False)
            except Exception:
                pass
        bpy.ops.object.select_all(action='DESELECT')
        facerig_obj.select_set(True)
        body_rig.select_set(True)
        context.view_layer.objects.active = body_rig
        bpy.ops.object.join()
        print(f"[AKE FACE RIG] Successfully fused FaceRig into '{body_rig.name}'")
    except Exception as ex_join:
        print(f"[AKE FACE RIG] Error joining FaceRig into body rig: {ex_join}")
        return None
    facerig_obj = body_rig
    context.view_layer.update()

    # Parent the facial root to the body head bone (HSR parity).
    try:
        context.view_layer.objects.active = body_rig
        bpy.ops.object.mode_set(mode='EDIT')
        head_eb = body_rig.data.edit_bones.get(body_head_bone_name)
        if head_eb:
            for bname in ["joint_face"]:
                eb = body_rig.data.edit_bones.get(bname)
                if eb:
                    eb.parent = head_eb
                    print(f"[AKE FACE RIG] Parented '{bname}' to '{head_eb.name}'")
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception as ex_parent:
        print(f"[AKE FACE RIG] Face root parenting notice: {ex_parent}")
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass

    # Sanity: warn about mapping bones missing after the fuse.
    try:
        wanted = {"Mouth-Master", "Lip-Master", "Eye-Track-Master"}
        for mapping in face_mapping.values():
            if mapping.get("deform"):
                wanted.add(mapping["deform"])
            if mapping.get("master"):
                wanted.add(mapping["master"])
        missing = sorted(b for b in wanted if b and b not in body_rig.data.bones)
        if missing:
            print(f"[AKE FACE RIG] Warning: fused rig is missing face bones: {missing}")
    except Exception:
        pass

    if is_endfield:
        align_endfield_mouth_panel(body_rig, context)
    assigned_count = bind_isaac_face_deformations(body_rig, face_mapping)

    # Post-fuse Child Of inverse fix (HSR parity): recompute in body-rig space
    # so Eye-Track-Follow rests perfectly horizontal.
    try:
        context.view_layer.update()
        for bname in ["Eye-Track-Follow.L", "Eye-Track-Follow.R"]:
            pb = body_rig.pose.bones.get(bname)
            if pb:
                c = pb.constraints.get("Child Of")
                if c and c.subtarget in body_rig.pose.bones:
                    tgt_pbone = body_rig.pose.bones[c.subtarget]
                    c.inverse_matrix = tgt_pbone.matrix.inverted()
        body_rig["ake_facerig_lowered"] = True
    except Exception as ex_inv:
        print(f"[AKE FACE RIG] Post-fuse inverse fix notice: {ex_inv}")

    bind_isaac_eye_tracking(body_rig, eyes, eye_pivots, context)
    if is_endfield:
        bind_endfield_iris_scale(body_rig, eyes, context)

    # Hide the "Face" bone collection on the body rig as requested
    if hasattr(body_rig.data, "collections"):
        face_coll = body_rig.data.collections.get("Face")
        if face_coll:
            face_coll.is_visible = False
            print("[AKE FACE RIG] Hidden 'Face' bone collection on body rig.")

    print(f"[AKE FACE RIG] Successfully constrained {assigned_count} Endfield face bones to the fused rig!")
    context.view_layer.update()
    return body_rig


class AKE_OT_SetUpIsaacFaceRig(Operator, BasicSetupUIOperator):
    """Sets Up Isaac Face Rig for Arknights: Endfield Character"""
    bl_idname = "arknights_endfield.setup_face_rig"
    bl_label = "Arknights: Endfield: Set Up Isaac Face Rig"

    def execute(self, context):
        from setup_wizard.character_rig_setup.rig_ui_utils import find_target_armature
        armature = find_target_armature(context)
        if not armature:
            self.report({'ERROR'}, 'No character armature found. Please select or rig a character first.')
            return {'CANCELLED'}

        facerig = setup_endfield_isaac_face_rig(armature, context)
        if not facerig:
            self.report({'ERROR'}, 'Failed to set up Isaac Face Rig.')
            return {'CANCELLED'}

        self.report({'INFO'}, 'Successfully set up Isaac Face Rig for Arknights: Endfield character!')
        return {'FINISHED'}
