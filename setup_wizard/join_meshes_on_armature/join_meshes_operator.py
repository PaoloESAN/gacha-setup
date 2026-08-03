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

        if self.next_step_idx:
            NextStepInvoker().invoke(
                self.next_step_idx, 
                self.invoker_type, 
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
            )
        return {'FINISHED'}

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
