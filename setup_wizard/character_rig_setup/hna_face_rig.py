"""HNA facial bones and expressions bound to the shared Isaac FaceRig asset."""
import bpy
from setup_wizard.character_rig_setup.ake_face_rig import setup_endfield_isaac_face_rig
from setup_wizard.character_rig_setup.rig_ui_utils import find_target_armature


def hna_face_mapping():
    mapping = {'Jaw': {'deform': 'JawdnEnd_M'},
               'Lip_U_M': {'mouth_chain': True, 'deform': 'lipUpper_M'},
               'Lip_D_M': {'mouth_chain': True, 'deform': 'lipLower_M'}}
    for side in ('L', 'R'):
        for prefix, parts in [('Brow', ('brow_Inn', 'brow_Mid', 'brow_Out')),
                              ('EyeBrow', ('eyebrow_Inn', 'eyebrow_Mid', 'eyebrow_Out', 'eyebrow_Out'))]:
            for index, part in enumerate(parts):
                mapping[f'{prefix}_{index}_{side}'] = {'master': f'Eyebrow-Master.{side}', 'deform': f'{part}_{side}'}
        for level, part in [('U', 'eyeup'), ('D', 'eyedn')]:
            for index, segment in enumerate(('inn', 'M', 'out')):
                mapping[f'Eyelid_{level}_{index}_{side}'] = {'master': f'Eye-Master.{side}', 'deform': f'{part}_{segment}_{side}'}
        mapping[f'Lip_Conner_{side}'] = {'mouth_chain': True, 'deform': f'lipConner_{side}'}
        for level, part in [('U', 'lipUpper'), ('D', 'lipLower')]:
            for index in range(2):
                mapping[f'Lip_{level}_{index}_{side}'] = {'mouth_chain': True, 'deform': f'{part}_{index:02}_{side}'}
    return mapping


def bind_hna_iris_scale(arm, context):
    """Scale the iris and catchlights around the iris, keeping the eyeball pivot for gaze."""
    context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='OBJECT')
    sides = []
    for side in ('L', 'R'):
        iris = arm.data.bones.get(f'Eyeball_Iris_{side}')
        eyeball = arm.pose.bones.get(f'Eyeball_{side}')
        if not iris or not eyeball:
            continue
        for constraint in list(eyeball.constraints):
            if constraint.name == f'Isaac_EyeScale_{side}':
                eyeball.constraints.remove(constraint)
        sides.append(side)
    bpy.ops.object.mode_set(mode='EDIT')
    bones = arm.data.edit_bones
    for side in sides:
        iris = bones[f'Eyeball_Iris_{side}']
        mechanism = bones.get(f'MCH-Isaac-IrisScale.{side}')
        if mechanism is None:
            mechanism = bones.new(f'MCH-Isaac-IrisScale.{side}')
            mechanism.matrix = iris.matrix.copy()
            mechanism.length = max(iris.length, .01)
            mechanism.parent = iris.parent
            mechanism.use_deform = False
        children = [bone for bone in bones if bone.name == iris.name or
                    (bone.name.startswith('Eyeball_Catchlight_') and bone.name.endswith('_' + side))]
        for bone in children:
            bone.use_connect = False
            bone.parent = mechanism
    bpy.ops.object.mode_set(mode='OBJECT')
    for side in sides:
        mechanism = arm.pose.bones[f'MCH-Isaac-IrisScale.{side}']
        for constraint in list(mechanism.constraints):
            if constraint.name == f'Isaac_IrisScale_{side}':
                mechanism.constraints.remove(constraint)
        scale = mechanism.constraints.new('COPY_SCALE')
        scale.name = f'Isaac_IrisScale_{side}'
        scale.target = arm
        scale.subtarget = f'Eye-Scale-Control.{side}'
        scale.owner_space = scale.target_space = 'LOCAL'
        mechanism.bone.hide = True
    context.view_layer.update()


def hna_face_rig_main(context=None):
    context = context or bpy.context
    arm = find_target_armature(context)
    if not arm:
        raise RuntimeError('Select the HNA character armature or a bound mesh.')
    eyes = {}
    for side in ('L', 'R'):
        eyes[side] = next((name for name in (f'Eyeball_{side}', f'eye.{side}', f'DEF-eye.{side}')
                           if name in arm.data.bones), '')
    rig = setup_endfield_isaac_face_rig(arm, context, face_mapping=hna_face_mapping(),
                                      eye_names=eyes, eye_pivots=eyes)
    if not rig:
        raise RuntimeError('Could not append the Isaac FaceRig.')
    bind_hna_iris_scale(arm, context)
    # Native HNA eyelid expressions supplement the bone-driven facial controls.
    for obj in context.scene.objects:
        if obj.type != 'MESH' or not obj.data.shape_keys:
            continue
        if not any(m.type == 'ARMATURE' and m.object == arm for m in obj.modifiers):
            continue
        for side in ('L', 'R'):
            key = obj.data.shape_keys.key_blocks.get(f'EyeClose_{side}')
            control = arm.pose.bones.get(f'Eye-Blink-Top.{side}')
            if not key or not control:
                continue
            limits = [c for c in control.constraints if c.type == 'LIMIT_LOCATION' and c.use_min_z]
            travel = abs(limits[0].min_z) if limits else .03
            if travel < 1e-6:
                travel = .03
            try: key.driver_remove('value')
            except (TypeError, RuntimeError): pass
            driver = key.driver_add('value').driver
            driver.type = 'SCRIPTED'
            variable = driver.variables.new()
            variable.name = 'blink'
            variable.type = 'TRANSFORMS'
            target = variable.targets[0]
            target.id = arm
            target.bone_target = control.name
            target.transform_type = 'LOC_Z'
            target.transform_space = 'LOCAL_SPACE'
            driver.expression = f'min(1.0,max(0.0,-blink/{travel!r}))'
    face = arm.data.collections.get('Face') if hasattr(arm.data, 'collections') else None
    if face:
        face.is_visible = True
    return rig


class HNA_OT_SetupFaceRig(bpy.types.Operator):
    bl_idname = 'honkai_nexus_anima.setup_face_rig'
    bl_label = 'Honkai: Nexus Anima: Setup Isaac Face Rig'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            hna_face_rig_main(context)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}
