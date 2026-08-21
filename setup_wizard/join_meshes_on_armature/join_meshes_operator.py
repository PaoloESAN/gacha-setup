# Author: michael-gh1

import bpy
from bpy.types import Operator

from setup_wizard.domain.game_types import GameType
from setup_wizard.domain.mesh_names import MeshNames
from setup_wizard.domain.shader_material_names import ShaderMaterialNames
from setup_wizard.domain.shader_identifier_service import ShaderIdentifierService, ShaderIdentifierServiceFactory
from setup_wizard.import_order import NextStepInvoker
from setup_wizard.setup_wizard_operator_base_classes import CustomOperatorProperties
from setup_wizard.utils.mesh_utils import remove_material_slots


class GI_OT_JoinMeshesOnArmature(Operator, CustomOperatorProperties):
    '''Joins Meshes on Armature'''
    bl_idname = 'hoyoverse.join_meshes_on_armature'
    bl_label = 'HoYoverse: Join Meshes on Armature'

    def execute(self, context):
        join_meshes = self.game_type == GameType.GENSHIN_IMPACT.name

        if join_meshes:
            self.__join_face_meshes()
            self.__delete_brow_material_from_material_slot()

        # Join face rig armature (e.g. isaac FaceRig) into main body rig
        self.__join_armature_rigs(context)

        if self.next_step_idx:
            NextStepInvoker().invoke(
                self.next_step_idx, 
                self.invoker_type, 
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
            )
        return {'FINISHED'}

    def __join_armature_rigs(self, context=None):
        ctx = context or bpy.context

        facerig_obj = bpy.data.objects.get("isaac FaceRig")
        if not facerig_obj:
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and any(k in obj.name.lower() for k in ['facerig', 'isaac']):
                    facerig_obj = obj
                    break

        if not facerig_obj:
            return

        main_rig = None
        selected_armatures = [obj for obj in ctx.selected_objects if obj.type == 'ARMATURE' and obj != facerig_obj]
        if selected_armatures:
            main_rig = selected_armatures[0]

        if not main_rig:
            view_layer_objs = getattr(ctx.view_layer, "objects", ctx.scene.objects)
            for obj in view_layer_objs:
                if obj.type == 'ARMATURE' and obj != facerig_obj and not any(ign in obj.name.lower() for ign in ['eyerig', 'metarig', 'backup', 'lighting']):
                    main_rig = obj
                    break

        if not main_rig:
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj != facerig_obj and not any(ign in obj.name.lower() for ign in ['eyerig', 'metarig', 'backup', 'lighting']):
                    main_rig = obj
                    break

        if not main_rig or main_rig == facerig_obj:
            return

        self.safe_merge_armatures(main_rig, facerig_obj, ctx)

    @staticmethod
    def safe_merge_armatures(main_rig, facerig_obj, ctx=None):
        """
        Safely merges facerig_obj bones into main_rig via the Blender Python API without calling
        bpy.ops.object.join(), avoiding crashes (e.g. EXCEPTION_ACCESS_VIOLATION in ED_armature_join_objects_exec in Blender 4/5.x).
        """
        if not main_rig or not facerig_obj or main_rig == facerig_obj:
            return

        context = ctx or bpy.context

        # 1. Retarget all mesh Armature modifiers to main_rig
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                for mod in obj.modifiers:
                    if mod.type == 'ARMATURE' and mod.object == facerig_obj:
                        mod.object = main_rig

        # 2. Collect information from facerig_obj bones before modifying
        facerig_data = facerig_obj.data
        main_data = main_rig.data

        # Map head bone on main_rig for parenting root facerig bones
        head_bone_name = None
        for candidate in ["DEF-spine.006", "head", "Head", "Head_M"]:
            if candidate in main_data.bones:
                head_bone_name = candidate
                break
        if not head_bone_name:
            for b in main_data.bones.keys():
                if "head" in b.lower() or "spine.006" in b.lower():
                    head_bone_name = b
                    break

        bone_info = {}
        for b in facerig_data.bones:
            world_mat = facerig_obj.matrix_world @ b.matrix_local
            local_mat = main_rig.matrix_world.inverted() @ world_mat
            bone_info[b.name] = {
                'head': main_rig.matrix_world.inverted() @ (facerig_obj.matrix_world @ b.head_local),
                'tail': main_rig.matrix_world.inverted() @ (facerig_obj.matrix_world @ b.tail_local),
                'matrix': local_mat,
                'parent': b.parent.name if b.parent else None,
                'use_deform': b.use_deform,
                'use_connect': b.use_connect,
                'use_inherit_rotation': b.use_inherit_rotation,
                'use_inherit_scale': getattr(b, 'use_inherit_scale', True),
                'use_local_location': b.use_local_location,
                'hide': b.hide,
            }

        pose_info = {}
        for pb in facerig_obj.pose.bones:
            constraints_data = []
            for c in pb.constraints:
                c_dict = {'type': c.type, 'name': c.name, 'influence': c.influence, 'mute': c.mute}
                for attr in dir(c):
                    if attr.startswith('_') or attr in ['type', 'name', 'influence', 'mute', 'rna_type', 'is_valid', 'is_proxy']:
                        continue
                    try:
                        val = getattr(c, attr)
                        if isinstance(val, (int, float, str, bool, tuple)):
                            c_dict[attr] = val
                        elif hasattr(val, 'name'):
                            c_dict[attr] = val
                    except Exception:
                        pass
                constraints_data.append(c_dict)

            pose_info[pb.name] = {
                'custom_shape': pb.custom_shape,
                'use_custom_shape_bone_size': getattr(pb, 'use_custom_shape_bone_size', True),
                'custom_shape_scale_xyz': getattr(pb, 'custom_shape_scale_xyz', (1.0, 1.0, 1.0)),
                'custom_shape_translation': getattr(pb, 'custom_shape_translation', (0.0, 0.0, 0.0)),
                'custom_shape_rotation_euler': getattr(pb, 'custom_shape_rotation_euler', (0.0, 0.0, 0.0)),
                'lock_location': tuple(pb.lock_location),
                'lock_rotation': tuple(pb.lock_rotation),
                'lock_scale': tuple(pb.lock_scale),
                'lock_rotation_w': getattr(pb, 'lock_rotation_w', False),
                'rotation_mode': pb.rotation_mode,
                'constraints': constraints_data,
            }

        # 3. Create Edit Bones in main_rig
        try:
            if context.object and context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass

        context.view_layer.objects.active = main_rig
        bpy.ops.object.mode_set(mode='EDIT')

        ebs = main_data.edit_bones
        created_bones = []
        for b_name, data in bone_info.items():
            if b_name in ebs:
                eb = ebs[b_name]
            else:
                eb = ebs.new(b_name)
                created_bones.append(b_name)

            eb.head = data['head']
            eb.tail = data['tail']
            try:
                eb.matrix = data['matrix']
            except Exception:
                pass
            eb.use_deform = data['use_deform']
            eb.use_inherit_rotation = data['use_inherit_rotation']
            if hasattr(eb, 'use_inherit_scale'):
                eb.use_inherit_scale = data['use_inherit_scale']
            eb.use_local_location = data['use_local_location']

        # Set parenting in Edit mode
        for b_name, data in bone_info.items():
            if b_name in ebs:
                eb = ebs[b_name]
                p_name = data['parent']
                if p_name and p_name in ebs:
                    eb.parent = ebs[p_name]
                    eb.use_connect = data['use_connect']
                elif not eb.parent and head_bone_name and b_name != head_bone_name:
                    eb.parent = ebs.get(head_bone_name)

        bpy.ops.object.mode_set(mode='OBJECT')

        # 4. Assign bone collections (Blender 4.0+ / 5.x)
        if hasattr(main_data, "collections"):
            face_coll = main_data.collections.get("Face") or main_data.collections.get("Face Rig") or main_data.collections.new("Face")
            face_coll.is_visible = True
            for b_name in created_bones:
                b = main_data.bones.get(b_name)
                if b:
                    try:
                        face_coll.assign(b)
                    except Exception:
                        pass

        # 5. Configure Pose Bones (constraints, custom shapes, locks)
        for b_name, p_data in pose_info.items():
            pb = main_rig.pose.bones.get(b_name)
            if not pb:
                continue

            if p_data.get('custom_shape'):
                pb.custom_shape = p_data['custom_shape']
            if hasattr(pb, 'use_custom_shape_bone_size'):
                pb.use_custom_shape_bone_size = p_data.get('use_custom_shape_bone_size', True)
            if hasattr(pb, 'custom_shape_scale_xyz'):
                pb.custom_shape_scale_xyz = p_data.get('custom_shape_scale_xyz', (1.0, 1.0, 1.0))
            if hasattr(pb, 'custom_shape_translation'):
                pb.custom_shape_translation = p_data.get('custom_shape_translation', (0.0, 0.0, 0.0))
            if hasattr(pb, 'custom_shape_rotation_euler'):
                pb.custom_shape_rotation_euler = p_data.get('custom_shape_rotation_euler', (0.0, 0.0, 0.0))

            pb.lock_location = p_data['lock_location']
            pb.lock_rotation = p_data['lock_rotation']
            pb.lock_scale = p_data['lock_scale']
            if hasattr(pb, 'lock_rotation_w'):
                pb.lock_rotation_w = p_data['lock_rotation_w']
            pb.rotation_mode = p_data['rotation_mode']

            for c_data in p_data['constraints']:
                c_type = c_data['type']
                c_name = c_data['name']
                if c_name == "Copy Head Transforms":
                    continue

                existing_c = pb.constraints.get(c_name)
                if not existing_c:
                    existing_c = pb.constraints.new(c_type)
                    existing_c.name = c_name

                for k, v in c_data.items():
                    if k in ['type', 'name']:
                        continue
                    try:
                        if k == 'target' and v == facerig_obj:
                            setattr(existing_c, k, main_rig)
                        else:
                            setattr(existing_c, k, v)
                    except Exception:
                        pass

        # 6. Delete facerig_obj cleanly
        facerig_arm_data = facerig_obj.data
        bpy.data.objects.remove(facerig_obj, do_unlink=True)
        if facerig_arm_data and facerig_arm_data.users == 0:
            try:
                bpy.data.armatures.remove(facerig_arm_data, do_unlink=True)
            except Exception:
                pass

        # 7. Keep main_rig selected and active
        main_rig.select_set(True)
        context.view_layer.objects.active = main_rig
        print(f"[JOIN RIGS] Successfully merged facerig bones into '{main_rig.name}'")

    def __join_face_meshes(self):
        face_mesh = bpy.data.objects.get(MeshNames.FACE)
        face_eye_mesh = bpy.data.objects.get(MeshNames.FACE_EYE)
        brow_mesh = bpy.data.objects.get(MeshNames.Brow)

        if face_mesh:
            bpy.context.view_layer.objects.active = face_mesh
            try:
                if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')
            except RuntimeError:
                pass

        # Collect explicit shape key drivers that will be lost when meshes are joined
        drivers_to_copy = []
        for mesh in [face_eye_mesh, brow_mesh]:
            if mesh and mesh.data.shape_keys and mesh.data.shape_keys.animation_data:
                for d in mesh.data.shape_keys.animation_data.drivers:
                    if hasattr(d, 'data_path'):
                        parts = d.data_path.split('"')
                        if len(parts) >= 3:
                            sk_name = parts[1]
                            var = d.driver.variables[0] if d.driver.variables else None
                            if var and var.type == 'TRANSFORMS':
                                drivers_to_copy.append({
                                    'shape_key': sk_name,
                                    'bone_name': var.targets[0].bone_target,
                                    'expression': d.driver.expression,
                                    'transform': var.targets[0].transform_type,
                                    'armature': var.targets[0].id
                                })

        for obj in bpy.context.selected_objects:
            obj.select_set(False)

        if face_eye_mesh:
            face_eye_mesh.select_set(True)
        if brow_mesh:
            brow_mesh.select_set(True)
        if face_mesh:
            face_mesh.select_set(True)
            bpy.context.view_layer.objects.active = face_mesh
            print(f'Joining {face_eye_mesh}, {brow_mesh} to {face_mesh}')
            try:
                bpy.ops.object.join()
                
                # Restore destroyed drivers from Face_Eye and Brow onto the main Face shape keys
                if face_mesh and face_mesh.data.shape_keys:
                    for d_info in drivers_to_copy:
                        sk = face_mesh.data.shape_keys.key_blocks.get(d_info['shape_key'])
                        if sk:
                            driver = sk.driver_add("value").driver
                            var = driver.variables.new()
                            var.name = "bone"
                            var.type = 'TRANSFORMS'
                            var.targets[0].id = d_info['armature']
                            var.targets[0].bone_target = d_info['bone_name']
                            var.targets[0].transform_space = 'LOCAL_SPACE'
                            var.targets[0].transform_type = d_info['transform']
                            driver.type = 'SCRIPTED'
                            driver.expression = d_info['expression']
                            
            except Exception as e:
                print(f"Failed to join meshes or transfer drivers: {e}")

    def __delete_brow_material_from_material_slot(self):
        face_mesh = bpy.data.objects.get(MeshNames.FACE)
        if face_mesh:
            try:
                shader_identifier_service: ShaderIdentifierService = ShaderIdentifierServiceFactory.create(self.game_type)
                shader_material_names: ShaderMaterialNames = shader_identifier_service.get_shader_material_names(self.game_type, bpy.data.materials, bpy.data.node_groups)
                brow_mat_name = getattr(shader_material_names, 'BROW', None)
                brow_material = bpy.data.materials.get(brow_mat_name) if brow_mat_name else None
                if not brow_material:
                    brow_material = bpy.data.materials.get('HoYoverse - Genshin Brow') or bpy.data.materials.get('Brow')
                if brow_material:
                    remove_material_slots(face_mesh, [brow_material])
            except Exception as ex:
                print(f"Notice: __delete_brow_material_from_material_slot: {ex}")
