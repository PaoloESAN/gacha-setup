"""Import MMD motion onto a selected humanoid FBX/Rigify character."""
import importlib
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

    def add(japanese, *aliases):
        # Original PMX metadata also works after Blender renamed the bones.
        bone = next((b for b in bones if getattr(b, 'mmd_bone', None)
                     and b.mmd_bone.name_j == japanese), None)
        bone = bone or next((bones[n] for n in (japanese, *aliases) if n in bones), None)
        if bone and japanese in motion and bone not in result.values():
            result[japanese] = bone

    add('全ての親', 'root', 'Bip001')
    add('センター', 'torso', 'Bip001 Pelvis', 'Hips')
    add('グルーブ', 'hips')
    add('下半身', 'hips', 'Bip001 Pelvis', 'Hips')
    add('上半身', 'spine_fk.001', 'Bip001 Spine', 'Spine')
    add('上半身2', 'spine_fk.002', 'Bip001 Spine1', 'Spine1')
    add('上半身3', 'spine_fk.003', 'Bip001 Spine2', 'Spine2')
    add('首', 'neck', 'Bip001 Neck', 'Neck')
    add('頭', 'head', 'Bip001 Head', 'Head')
    for jp, side, english in (('左', 'L', 'Left'), ('右', 'R', 'Right')):
        for name, aliases in (
            ('肩', (f'shoulder.{side}', f'Bip001 {side} Clavicle', english+'Shoulder')),
            ('腕', (f'upper_arm_fk.{side}', f'Bip001 {side} UpperArm', english+'Arm')),
            ('ひじ', (f'forearm_fk.{side}', f'Bip001 {side} Forearm', english+'ForeArm')),
            ('手首', (f'hand_fk.{side}', f'Bip001 {side} Hand', english+'Hand')),
            ('足', (f'thigh_fk.{side}', f'Bip001 {side} Thigh', english+'UpLeg')),
            ('ひざ', (f'shin_fk.{side}', f'Bip001 {side} Calf', english+'Leg')),
            ('足首', (f'foot_fk.{side}', f'Bip001 {side} Foot', english+'Foot')),
            ('つま先', (f'toe.{side}', f'Bip001 {side} Toe0', english+'ToeBase')),
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
                aliases = (f'{finger}.{segment:02d}.{side}', f'Bip001 {side} Finger{index}{suffix}')
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
    from .facial_transfer import transfer_tracks

    objects = [obj for obj in context.scene.objects
               if obj.type == 'MESH' and obj.find_armature() == rig and obj.data.shape_keys]
    imported, diagnostics = transfer_tracks(
        context, objects, motion, start, action_name, owners=[rig, *objects])
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
