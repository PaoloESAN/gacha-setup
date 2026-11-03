"""Import MMD motion onto a selected humanoid FBX/Rigify character."""
import importlib
import re
from pathlib import Path

import bpy
from bpy_extras.io_utils import ImportHelper
from setup_wizard.utils.optional_addons import find_addon, temporary_addon


def selected_armature(context):
    obj = context.object
    if obj and obj.type == 'ARMATURE':
        return obj
    return obj.find_armature() if obj and obj.type == 'MESH' else None


def bone_map(rig, motion):
    bones = rig.pose.bones
    result = {}
    # Exporters vary separators/case, e.g. Bip001_L_UpperArm,
    # Bip001-L-UpperArm and Bip001LUpperArm. Keep exact control names first.
    normalized = {}
    for bone in bones:
        normalized.setdefault(re.sub(r'[\s_.-]', '', bone.name).casefold(), bone)

    def add(japanese, *aliases):
        if japanese not in motion:
            return
        # Original PMX metadata also works after Blender renamed the bones.
        bone = next((bones[n] for n in aliases if n in bones), None)
        bone = bone or next((b for b in bones if getattr(b, 'mmd_bone', None)
                            and b.mmd_bone.name_j == japanese), None)
        bone = bone or bones.get(japanese)
        bone = bone or next((normalized[key] for n in aliases
                             if (key := re.sub(r'[\s_.-]', '', n).casefold()) in normalized), None)
        if bone and bone not in result.values():
            result[japanese] = bone

    add('全ての親', 'root', 'Bip001')
    add('センター', 'torso', 'Bip001 Pelvis', 'Hips', 'Root_M', 'Pelvis_M', 'Hip_M')
    add('下半身', 'hips', 'Bip001 Pelvis', 'Hips', 'Root_M', 'Pelvis_M', 'Hip_M')
    add('グルーブ', 'groove', *(('torso', 'Bip001 Pelvis', 'Hips') if 'センター' not in motion else ()))
    upper_body = ('spine_fk.001', 'Spine_fk', 'chest', 'Bip001 Spine', 'Spine', 'Spine1_M')
    # Some dances (including Hiasobi) animate an extra 上半身1 track while
    # keeping 上半身 static. Reserve the working spine control for that track.
    if '上半身1' in motion:
        add('上半身1', *upper_body)
        add('上半身', 'spine_fk')
    else:
        add('上半身', *upper_body)
    add('上半身2', 'spine_fk.002', 'Spine1_fk', 'Bip001 Spine1', 'Spine1', 'Spine2_M')
    add('上半身3', 'spine_fk.003', 'Spine2_fk', 'Bip001 Spine2', 'Spine2', 'Chest_M')
    add('首', 'neck', 'Bip001 Neck', 'Neck', 'Neck_M')
    add('頭', 'head', 'Bip001 Head', 'Head', 'Head_M')
    for jp, side, english in (('左', 'L', 'Left'), ('右', 'R', 'Right')):
        for name, aliases in (
            ('肩', (f'shoulder.{side}', f'Bip001 {side} Clavicle', english+'Shoulder', f'Scapula_{side}')),
            ('腕', (f'upper_arm_fk.{side}', f'Bip001 {side} UpperArm', english+'Arm', f'Shoulder_{side}')),
            ('ひじ', (f'forearm_fk.{side}', f'Bip001 {side} Forearm', english+'ForeArm', f'Elbow_{side}')),
            ('手首', (f'hand_fk.{side}', f'Bip001 {side} Hand', english+'Hand', f'Wrist_{side}')),
            ('足', (f'thigh_fk.{side}', f'Bip001 {side} Thigh', english+'UpLeg', f'Hip_{side}')),
            ('ひざ', (f'shin_fk.{side}', f'Bip001 {side} Calf', english+'Leg', f'Knee_{side}')),
            ('足首', (f'foot_fk.{side}', f'Bip001 {side} Foot', english+'Foot', f'Ankle_{side}')),
            ('つま先', (f'toe.{side}', f'Bip001 {side} Toe0', english+'ToeBase', f'Toes_{side}')),
            ('目', (f'eye.{side}', f'+EyeBone {side} A02')),
            ('足ＩＫ', (f'foot_ik.{side}',)),
            ('つま先ＩＫ', (f'toe_ik.{side}',)),
        ):
            add(jp+name, *aliases)
            if 'ＩＫ' in name:
                add(jp+name.replace('ＩＫ', 'IK'), *aliases)
        for index, (jp_finger, finger, digits) in enumerate((
            ('親指', 'thumb', '０１２'), ('人指', 'f_index', '１２３'),
            ('中指', 'f_middle', '１２３'), ('薬指', 'f_ring', '１２３'),
            ('小指', 'f_pinky', '１２３'),
        )):
            for segment, digit in enumerate(digits, 1):
                suffix = '' if segment == 1 else str(segment-1)
                finger_name = ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky')[index]
                # Some WuWa skeletons count non-thumb segments from 11 to 13.
                numbered = index and any(re.sub(r'[\s_.-]', '', b.name).casefold() ==
                                         f'bip001{side}finger{index}3'.casefold() for b in bones)
                suffix = str(segment) if numbered else suffix
                aliases = (f'{finger}.{segment:02d}.{side}', f'Bip001 {side} Finger{index}{suffix}',
                           f'{finger_name}Finger{segment}_{side}', english+f'Hand{finger_name}{segment}')
                add(jp+jp_finger+digit, *aliases)
                add(jp+jp_finger+str('０１２３'.index(digit)), *aliases)
    # Exact names support custom motions without guessing additional skeletons.
    used = {b.name for b in result.values()}
    for name in motion:
        if name not in result and name in bones and name not in used:
            result[name] = bones[name]
            used.add(name)
    return result


def mmd_modules():
    module = find_addon('mmd_tools')
    if not module:
        raise RuntimeError('MMD Tools is required. Install it first; it can remain disabled.')
    return (importlib.import_module(module+'.core.vmd'),
            importlib.import_module(module+'.core.vmd.importer'))


def import_morphs(context, rig, motion, start, action_name):
    """Import mapped morphs through their existing facial controls when possible."""
    from .facial_transfer import SHAPEKEY_MAP, transfer_tracks

    objects = [obj for obj in context.scene.objects
               if obj.type == 'MESH' and obj.find_armature() == rig and obj.data.shape_keys]
    mapping = dict(SHAPEKEY_MAP)
    names = {key.name for obj in objects for key in obj.data.shape_keys.key_blocks}
    # Use each game's authored phonemes and expression controls. Exact Japanese
    # keys still take precedence inside transfer_tracks (PMX/custom characters).
    for marker, aliases in (
        ('Fac_Mth_Aa1', {'あ': 'Fac_Mth_Aa1', 'い': 'Fac_Mth_Ii', 'う': 'Fac_Mth_Uu',
                        'え': 'Fac_Mth_Ee', 'お': 'Fac_Mth_Oo', 'まばたき': 'Fac_Eye_Close',
                        'ウィンク': 'Fac_Eye_L_Wink', 'ウィンク右': 'Fac_Eye_R_Wink',
                        'にやり': 'Fac_Mth_Laugh', 'じと目': 'Fac_Eye_HalfClose'}),
        ('Mouth_01_A', {'あ': 'Mouth_01_A', 'い': 'Mouth_01_I', 'う': 'Mouth_01_U',
                        'え': 'Mouth_01_E', 'お': 'Mouth_01_O', 'ん': 'Mouth_01_N',
                        'にやり': 'Mouth_01_Smile01', 'まばたき': '00_Close01_Eye'}),
        ('E_Close', {'あ': 'A', 'あ２': 'Aa', 'い': 'I', 'う': 'U', 'え': 'E', 'お': 'O',
                     'まばたき': 'E_Close', '笑い': ['E_Smile_L', 'E_Smile_R'],
                     'にやり': ['M_Smile_L', 'M_Smile_R'], '困る': 'B_Sad',
                     '怒り': 'B_Anger', 'にこり': 'B_Happy', '上': 'B_Up_Add', '下': 'B_Down_Add'}),
        ('jawOpen_a', {'あ': 'jawOpen_a', 'い': 'jawOpen_yi', 'う': 'jawOpen_wu',
                       'え': 'jawOpen_ei', 'お': 'jawOpen_o', 'まばたき': 'biyan',
                       'ウィンク': 'biyan_L', 'ウィンク右': 'biyan_R',
                       '笑い': 'EL_Smile_01_CLO', 'にやり': 'jawOpen_Smile_01_OP'}),
        ('mouth01', {'あ': 'mouth01', 'い': 'mouth07', 'う': 'mouth04', 'え': 'mouth03',
                     'お': 'mouth02', 'まばたき': 'eye01'}),
        ('Mouth_I01', {'い': 'Mouth_I01', 'う': 'Mouth_U01', 'え': 'Mouth_E01', 'お': 'Mouth_O01',
                       'まばたき': ['Eye_Wink02_L', 'Eye_Wink02_R'],
                       'ウィンク': 'Eye_Wink01_L', 'ウィンク右': 'Eye_Wink01_R'}),
        ('EyeClose_L', {'まばたき': ['EyeClose_L', 'EyeClose_R'],
                        'ウィンク': 'EyeClose_L', 'ウィンク右': 'EyeClose_R',
                        '笑い': ['EyeSmile_L', 'EyeSmile_R']}),
    ):
        if marker in names:
            mapping.update(aliases)
    imported, diagnostics = transfer_tracks(
        context, objects, motion, start, action_name, mapping=mapping, owners=[rig, *objects])
    rig['setup_wizard_vmd_unmapped_morphs'] = ', '.join(sorted(set(motion)-imported))
    rig['setup_wizard_vmd_face_warnings'] = '\n'.join(diagnostics)
    for message in diagnostics:
        print('[VMD Face] ' + message)
    return imported


def apply_vmd(context, rig, filepath, scale=.08, start=1, facial=True, face_only=False):
    if bpy.app.version < (5, 0, 0):
        raise RuntimeError('VMD Motion requires Blender 5.0 or newer.')
    with temporary_addon('mmd_tools'):
        return _apply_vmd(context, rig, filepath, scale, start, facial, face_only)


def merge_groove(rig, importer, torso, start, frames):
    """Rigify has one torso translation control for MMD's center + groove.

    Sample the two imported actions at VMD's 30 fps before composing them.
    This preserves the pelvis control for lower-body rotation.
    """
    from mathutils import Euler, Quaternion, Vector
    from .facial_transfer import action_curves

    data = rig.animation_data
    body, slot = data.action, data.action_slot
    body_curves = {(c.data_path, c.array_index): c for c in action_curves(data)}
    temporary = None
    try:
        data.action = None
        importer.assign(rig, action_name='VMD groove transfer')
        temporary = data.action
        groove_curves = {(c.data_path, c.array_index): c for c in action_curves(data)}
        rotation = 'rotation_quaternion' if torso.rotation_mode == 'QUATERNION' else 'rotation_euler'
        if torso.rotation_mode == 'AXIS_ANGLE':
            rotation = 'rotation_axis_angle'
        paths = {p: torso.path_from_id(p) for p in ('location', rotation)}
        coordinates = {(p, i): [] for p in paths for i in range(len(getattr(torso, p)))}

        def values(curves, prop, frame):
            defaults = (0, 0, 0) if prop == 'location' else ((1, 0, 0, 0) if prop != 'rotation_euler' else (0, 0, 0))
            return [curves[(paths[prop], i)].evaluate(frame) if (paths[prop], i) in curves else v
                    for i, v in enumerate(defaults)]

        def quaternion(v):
            if rotation == 'rotation_quaternion':
                return Quaternion(v)
            if rotation == 'rotation_axis_angle':
                return Quaternion(v[1:], v[0])
            return Euler(v, torso.rotation_mode).to_quaternion()

        previous = None
        end = start + max(f.frame_number for f in frames)
        for frame in range(start, int(end) + 1):
            center_rotation = quaternion(values(body_curves, rotation, frame))
            loc = Vector(values(body_curves, 'location', frame)) + center_rotation @ Vector(values(groove_curves, 'location', frame))
            rot = center_rotation @ quaternion(values(groove_curves, rotation, frame))
            if rotation == 'rotation_euler':
                rot = rot.to_euler(torso.rotation_mode, previous) if previous else rot.to_euler(torso.rotation_mode)
            elif rotation == 'rotation_axis_angle':
                axis, angle = rot.to_axis_angle()
                rot = (angle, *axis)
            elif previous and rot.dot(previous) < 0:
                rot.negate()
            previous = rot.copy() if hasattr(rot, 'copy') else rot
            for prop, vector in (('location', loc), (rotation, rot)):
                for i, value in enumerate(vector):
                    coordinates[prop, i].extend((frame, value))
        for (prop, i), points in coordinates.items():
            curve = body_curves[paths[prop], i]
            curve.keyframe_points.clear()
            curve.keyframe_points.add(len(points)//2)
            curve.keyframe_points.foreach_set('co', points)
            for point in curve.keyframe_points:
                point.interpolation = 'LINEAR'
            curve.update()
    finally:
        data.action = body
        data.action_slot = slot
        if temporary and not temporary.users:
            bpy.data.actions.remove(temporary)


def _apply_vmd(context, rig, filepath, scale, start, facial, face_only=False):
    vmd, importer_module = mmd_modules()
    motion = vmd.File()
    motion.load(filepath=filepath)
    mapping = {} if face_only else bone_map(rig, motion.boneAnimation)
    facial = facial or face_only
    has_face = facial and bool(motion.shapeKeyAnimation)
    if not mapping and not has_face:
        raise RuntimeError('No compatible VMD bones found. Select a humanoid FBX armature or its Rigify rig.')
    action_name = Path(filepath).stem+' - '+rig.name
    data = rig.animation_data_create()
    previous = data.action
    previous_slot = data.action_slot
    if mapping:
        data.action = None
    old_frame, old_subframe = context.scene.frame_current, context.scene.frame_subframe
    context.scene.frame_set(start)
    try:
        if mapping:
            importer = importer_module.VMDImporter(
                filepath, scale=scale, bone_mapper=lambda _: mapping, frame_margin=0,
                convert_mmd_camera=False, convert_mmd_light=False,
            )
            importer.assign(rig, action_name=action_name)
            if 'グルーブ' in motion.boneAnimation and 'グルーブ' not in mapping and 'センター' in mapping:
                body_mapping = mapping
                torso = mapping['センター']
                mapping = {'グルーブ': torso}
                try:
                    merge_groove(rig, importer, torso, start,
                                 [f for name in ('センター', 'グルーブ') for f in motion.boneAnimation.get(name, [])])
                finally:
                    mapping = body_mapping
                mapping['グルーブ'] = torso
        else:
            data.action = previous
            if previous_slot:
                data.action_slot = previous_slot
        # Rigify: arms use FK; legs use IK only if the VMD supplies foot targets.
        for side, jp in (('L', '左'), ('R', '右')):
            for limb in ('upper_arm', 'thigh'):
                parent = rig.pose.bones.get(f'{limb}_parent.{side}')
                if mapping and parent and 'IK_FK' in parent:
                    ik = limb == 'thigh' and any(n in mapping for n in (jp+'足ＩＫ', jp+'足IK'))
                    parent['IK_FK'] = 0.0 if ik else 1.0
                    parent.keyframe_insert(data_path='["IK_FK"]', frame=start)
            for finger in ('thumb', 'f_index', 'f_middle', 'f_ring', 'f_pinky'):
                control = rig.pose.bones.get(f'{finger}.01_ik.{side}')
                if mapping and control and 'FK_IK' in control and any(
                        b.name.startswith(f'{finger}.') and b.name.endswith(f'.{side}')
                        for b in mapping.values()):
                    control['FK_IK'] = 0.0
                    control.keyframe_insert(data_path='["FK_IK"]', frame=start)
        imported_morphs = import_morphs(context, rig, motion.shapeKeyAnimation, start, action_name) if facial else set()
        if not mapping and not imported_morphs:
            raise RuntimeError('No compatible VMD bones or facial morphs found for this character.')
    except Exception:
        data.action = previous
        if previous_slot:
            data.action_slot = previous_slot
        raise
    finally:
        context.scene.frame_set(old_frame, subframe=old_subframe)
    if previous:
        previous.use_fake_user = True
    frames = [f.frame_number for animation in (motion.boneAnimation if mapping else {}, motion.shapeKeyAnimation if facial else {})
              for values in animation.values() for f in values]
    end = start+max(frames, default=0)
    if mapping:
        context.scene.frame_start = start
        context.scene.frame_end = end
        context.scene.render.fps = 30
        context.scene.render.fps_base = 1
    else:
        context.scene.frame_start = min(context.scene.frame_start, start)
        context.scene.frame_end = max(context.scene.frame_end, end)
    context.scene.frame_set(start)
    skipped = set() if face_only else set(motion.boneAnimation)-set(mapping)
    if mapping:
        rig['setup_wizard_vmd_unmapped_bones'] = ', '.join(sorted(skipped))
    return len(mapping), len(imported_morphs), len(skipped)


class CSW_OT_ApplyVMD(bpy.types.Operator, ImportHelper):
    bl_idname = 'setup_wizard.apply_vmd'
    bl_label = 'Apply VMD Motion'
    bl_description = 'Apply a VMD animation to the selected FBX armature or Rigify character (requires MMD Tools installed)'
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = '.vmd'
    filter_glob: bpy.props.StringProperty(default='*.vmd', options={'HIDDEN'})
    target_name: bpy.props.StringProperty(options={'HIDDEN'})
    scale: bpy.props.FloatProperty(name='Motion Scale', default=.08, min=.00001,
                                  description='Translation scale from MMD units to character units')
    start_frame: bpy.props.IntProperty(name='Start Frame', default=1, min=0)
    facial: bpy.props.BoolProperty(name='Matching Facial Morphs', default=True,
                                  description='Transfer matching expressions to shape keys and supported facial rig controls')
    face_only: bpy.props.BoolProperty(name='Facial Only (Preserve Body)', default=False,
                                     description='Import only facial morphs; preserve body animation, FK/IK settings, frame rate and scene range')

    @classmethod
    def poll(cls, context):
        if bpy.app.version < (5, 0, 0):
            cls.poll_message_set('VMD Motion requires Blender 5.0 or newer')
            return False
        return selected_armature(context) is not None and context.mode in {'OBJECT', 'POSE'}

    def draw(self, context):
        self.layout.prop(self, 'face_only')
        options = self.layout.column()
        options.enabled = not self.face_only
        options.prop(self, 'scale')
        options.prop(self, 'facial')
        self.layout.prop(self, 'start_frame')

    def invoke(self, context, event):
        self.target_name = selected_armature(context).name
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if bpy.app.version < (5, 0, 0):
            self.report({'ERROR'}, 'VMD Motion requires Blender 5.0 or newer.')
            return {'CANCELLED'}
        rig = bpy.data.objects.get(self.target_name) if self.target_name else selected_armature(context)
        if not rig or rig.type != 'ARMATURE':
            self.report({'ERROR'}, 'Select the character armature before opening the VMD file.')
            return {'CANCELLED'}
        if not Path(self.filepath).is_file() or Path(self.filepath).suffix.lower() != '.vmd':
            self.report({'ERROR'}, 'Choose an existing .vmd file.')
            return {'CANCELLED'}
        try:
            bones, morphs, skipped = apply_vmd(context, rig, self.filepath, self.scale, self.start_frame,
                                             self.facial, self.face_only)
        except Exception as exc:
            self.report({'ERROR'}, f'VMD import failed: {exc}')
            return {'CANCELLED'}
        skipped_morphs = rig.get('setup_wizard_vmd_unmapped_morphs', '') if self.facial or self.face_only else ''
        self.report({'WARNING'} if skipped or skipped_morphs else {'INFO'},
                    f'VMD applied: {bones} bones, {morphs} facial morphs; {skipped} unmapped bones.'
                    + (' Some facial morphs were skipped; see armature custom properties.' if skipped_morphs else ''))
        return {'FINISHED'}
