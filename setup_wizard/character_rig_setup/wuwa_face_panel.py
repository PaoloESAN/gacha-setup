# Based on Blender-WuWa-Character-Setup by @fnoji (https://github.com/fnoji/Blender-WuWa-Character-Setup)
# Adapted for Gacha Setup by PaoloESAN
# Licensed under GPL-3.0-or-later

import bpy
import math
import mathutils
from bpy.types import Operator

class WW_OT_CreateFacePanel(Operator):
    bl_idname = "wuthering_waves.create_face_panel"
    bl_label = "Create Face Panel"
    bl_description = "Generate Face Rig Panel for Wuthering Waves character"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj:
            return False
        if obj.type == 'MESH':
            return any(m.type == 'ARMATURE' and m.object for m in obj.modifiers)
        elif obj.type == 'ARMATURE':
            return True
        return False

    def setup_create_panel_drivers(self, context, armature_obj, CharacterMesh):
        shape_key_mappings = {
            "Smile.L": {"shape_key": "E_Smile_L", "var_type": "LOC_Y"},
            "Smile.R": {"shape_key": "E_Smile_R", "var_type": "LOC_Y"},
            "Anger.L": {"shape_key": "E_Anger.L", "var_type": "LOC_Y"},
            "Sad.L": {"shape_key": "E_Sad.L", "var_type": "LOC_Y"},
            "Focus.L": {"shape_key": "E_Focus.L", "var_type": "LOC_Y"},
            "Insipid.L": {"shape_key": "E_Insipid.L", "var_type": "LOC_Y"},
            "Anger.R": {"shape_key": "E_Anger.R", "var_type": "LOC_Y"},
            "Sad.R": {"shape_key": "E_Sad.R", "var_type": "LOC_Y"},
            "Focus.R": {"shape_key": "E_Focus.R", "var_type": "LOC_Y"},
            "Insipid.R": {"shape_key": "E_Insipid.R", "var_type": "LOC_Y"},
            "B_Anger": {"shape_key": "B_Anger", "var_type": "LOC_Y"},
            "B_Happy": {"shape_key": "B_Happy", "var_type": "LOC_Y"},
            "B_Cheerful": {"shape_key": "B_Cheerful", "var_type": "LOC_Y"},
            "B_Sad": {"shape_key": "B_Sad", "var_type": "LOC_Y"},
            "B_Flat": {"shape_key": "B_Flat", "var_type": "LOC_Y"},
            "B_Inside_Add": {"shape_key": "B_Inside_Add", "var_type": "LOC_Y"},
            "EyeScale": {"shape_key": "E_Blephar", "var_type": "LOC_Y"}
        }

        mouth_mappings = {
            "Mouth.L": {
                "positive_shape": "M_Smile_L",
                "negative_shape": "M_Ennui_L",
                "multiplier": 50,
                "var_type": "LOC_Y"
            },
            "Mouth.R": {
                "positive_shape": "M_Smile_R",
                "negative_shape": "M_Ennui_R",
                "multiplier": 50,
                "var_type": "LOC_Y"
            }
        }

        mouth_x_mappings = {
            "Mouth.L": {
                "negative_shape": "P_M_Scale_Add.L",
                "positive_shape": "P_M_L_Add"
            },
            "Mouth.R": {
                "negative_shape": "P_M_R_Add",
                "positive_shape": "P_M_Scale_Add.R"
            }
        }

        if not CharacterMesh.data.shape_keys:
            return

        for bone_name, mapping in shape_key_mappings.items():
            if bone_name not in armature_obj.pose.bones:
                continue
            bone = armature_obj.pose.bones[bone_name]
            shape_key = CharacterMesh.data.shape_keys.key_blocks.get(mapping["shape_key"])
            if not shape_key:
                continue
            driver = shape_key.driver_add('value').driver
            driver.type = 'SCRIPTED'
            var = driver.variables.new()
            var.name = 'bone_var'
            var.targets[0].id = armature_obj
            var.targets[0].data_path = (
                f'pose.bones["{bone.name}"].location.y' if mapping["var_type"] == "LOC_Y"
                else f'pose.bones["{bone.name}"].location.x'
            )
            driver.expression = "bone_var * 50"

        for bone_name, mapping in mouth_mappings.items():
            if bone_name not in armature_obj.pose.bones:
                continue
            bone = armature_obj.pose.bones[bone_name]
            multiplier = mapping["multiplier"]
            if mapping["positive_shape"]:
                shape_key = CharacterMesh.data.shape_keys.key_blocks.get(mapping["positive_shape"])
                if shape_key:
                    driver = shape_key.driver_add('value').driver
                    driver.type = 'SCRIPTED'
                    var = driver.variables.new()
                    var.name = 'mouth_y'
                    var.targets[0].id = armature_obj
                    var.targets[0].data_path = f'pose.bones["{bone.name}"].location.y'
                    driver.expression = f"max(min(mouth_y * {multiplier}, 1), 0)"
            if mapping["negative_shape"]:
                shape_key = CharacterMesh.data.shape_keys.key_blocks.get(mapping["negative_shape"])
                if shape_key:
                    driver = shape_key.driver_add('value').driver
                    driver.type = 'SCRIPTED'
                    var = driver.variables.new()
                    var.name = 'mouth_y'
                    var.targets[0].id = armature_obj
                    var.targets[0].data_path = f'pose.bones["{bone.name}"].location.y'
                    driver.expression = f"max(min(-mouth_y * {multiplier}, 1), 0)"

        for bone_name, mapping in mouth_x_mappings.items():
            if bone_name not in armature_obj.pose.bones:
                continue
            bone = armature_obj.pose.bones[bone_name]
            if mapping["positive_shape"]:
                shape_key = CharacterMesh.data.shape_keys.key_blocks.get(mapping["positive_shape"])
                if shape_key:
                    driver = shape_key.driver_add('value').driver
                    driver.type = 'SCRIPTED'
                    var = driver.variables.new()
                    var.name = 'mouth_x'
                    var.targets[0].id = armature_obj
                    var.targets[0].data_path = f'pose.bones["{bone.name}"].location.x'
                    driver.expression = "max(min(mouth_x * 50, 1), 0)"
            if mapping["negative_shape"]:
                shape_key = CharacterMesh.data.shape_keys.key_blocks.get(mapping["negative_shape"])
                if shape_key:
                    driver = shape_key.driver_add('value').driver
                    driver.type = 'SCRIPTED'
                    var = driver.variables.new()
                    var.name = 'mouth_x'
                    var.targets[0].id = armature_obj
                    var.targets[0].data_path = f'pose.bones["{bone.name}"].location.x'
                    driver.expression = "max(min(-mouth_x * 50, 1), 0)"

        vowel_shapes = {
            "E": {"axis": "x", "direction": -1, "max_value": 0.02},
            "I": {"axis": "x", "direction": 1, "max_value": 0.02},
            "A": {"axis": "y", "direction": 1, "max_value": 0.02},
            "U": {"axis": "y", "direction": -1, "max_value": 0.02},
        }
        mouth_bone = armature_obj.pose.bones.get("Mouth")
        if mouth_bone:
            for shape_key_name, info in vowel_shapes.items():
                shape_key = CharacterMesh.data.shape_keys.key_blocks.get(shape_key_name)
                if not shape_key:
                    continue
                driver = shape_key.driver_add('value').driver
                driver.type = 'SCRIPTED'
                var_main = driver.variables.new()
                var_main.name = 'coord'
                var_main.targets[0].id = armature_obj
                var_main.targets[0].data_path = f'pose.bones["Mouth"].location.{info["axis"]}'
                var_o = driver.variables.new()
                var_o.name = 'oval'
                var_o.targets[0].id_type = 'KEY'
                var_o.targets[0].id = CharacterMesh.data.shape_keys
                var_o.targets[0].data_path = 'key_blocks["O"].value' if "O" in CharacterMesh.data.shape_keys.key_blocks else ''
                if shape_key_name in ["E", "I"]:
                    var_y = driver.variables.new()
                    var_y.name = 'yval'
                    var_y.targets[0].id = armature_obj
                    var_y.targets[0].data_path = 'pose.bones["Mouth"].location.y'
                    driver.expression = (
                        f"(1 - min(abs(yval) / 0.02, 1)) * "
                        f"max(min(({info['direction']} * coord) / {info['max_value']}, 1), 0)"
                    )
                else:
                    driver.expression = f"max(min(({info['direction']} * coord) / {info['max_value']}, 1), 0)"

            o_shape = CharacterMesh.data.shape_keys.key_blocks.get("O")
            if o_shape:
                driver = o_shape.driver_add('value').driver
                driver.type = 'SCRIPTED'
                for axis in ["x", "y", "z"]:
                    var = driver.variables.new()
                    var.name = f"s_{axis}"
                    var.targets[0].id = armature_obj
                    var.targets[0].data_path = f'pose.bones["Mouth"].scale.{axis}'
                driver.expression = "max(min(((abs(s_x) + abs(s_y) + abs(s_z)) / 3 - 1) / 0.5, 1), 0)"

        shape_map = {
            "M_OpenSmall": "M_OpenSmall",
            "M_Laugh": "M_Laugh",
            "M_Scared": "M_Scared",
            "M_ScaredTooth": "M_ScaredTooth",
            "M_Anger": "M_Anger",
            "M_Trapezoid": "M_Trapezoid",
            "M_Nutcracker": "M_Nutcracker",
            "Aa": "Aa",
            "M_A": "M_A",
            "M_O": "M_O",
        }
        for b_name, s_name in shape_map.items():
            shape_key = CharacterMesh.data.shape_keys.key_blocks.get(s_name)
            if not shape_key or b_name not in armature_obj.pose.bones:
                continue
            driver = shape_key.driver_add('value').driver
            driver.type = 'SCRIPTED'
            var = driver.variables.new()
            var.name = 'yval'
            var.targets[0].id = armature_obj
            var.targets[0].data_path = f'pose.bones["{b_name}"].location.y'
            driver.expression = "max(min(yval / 0.02, 1), 0)"

        if "Eyebrows" in armature_obj.pose.bones:
            y_mappings = {
                "B_Up_Add": {"direction": 1, "shape_key": "B_Up_Add"},
                "B_Down_Add": {"direction": -1, "shape_key": "B_Down_Add"},
            }
            for key, data in y_mappings.items():
                shape_key = CharacterMesh.data.shape_keys.key_blocks.get(data["shape_key"])
                if not shape_key:
                    continue
                driver = shape_key.driver_add('value').driver
                driver.type = 'SCRIPTED'
                var = driver.variables.new()
                var.name = 'yval'
                var.targets[0].id = armature_obj
                var.targets[0].data_path = 'pose.bones["Eyebrows"].location.y'
                dir = data["direction"]
                driver.expression = f"max(min(({dir} * yval) / 0.01, 1), 0)"

            z_mappings = {
                "B_AH_L": {"direction": -1, "angle_deg": 10},
                "B_AH_R": {"direction": 1, "angle_deg": 10}
            }
            for key, info in z_mappings.items():
                shape_key = CharacterMesh.data.shape_keys.key_blocks.get(key)
                if not shape_key:
                    continue
                driver = shape_key.driver_add('value').driver
                driver.type = 'SCRIPTED'
                var = driver.variables.new()
                var.name = 'zrot'
                var.targets[0].id = armature_obj
                var.targets[0].data_path = 'pose.bones["Eyebrows"].rotation_euler.z'
                max_radians = math.radians(info["angle_deg"])
                direction = info["direction"]
                driver.expression = f"max(min(({direction} * zrot) / {max_radians:.5f}, 1), 0)"

    def execute(self, context):
        active_obj = context.active_object
        CharacterMesh = None
        armature_obj = None

        if active_obj.type == 'MESH':
            CharacterMesh = active_obj
            for m in active_obj.modifiers:
                if m.type == 'ARMATURE' and m.object:
                    armature_obj = m.object
                    break
        elif active_obj.type == 'ARMATURE':
            armature_obj = active_obj
            for o in context.scene.objects:
                if o.type == 'MESH':
                    for m in o.modifiers:
                        if m.type == 'ARMATURE' and m.object == armature_obj:
                            CharacterMesh = o
                            break
                    if CharacterMesh:
                        break

        if not armature_obj:
            self.report({'ERROR'}, "No armature found")
            return {'CANCELLED'}

        context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = armature_obj.data.edit_bones

        eye_tracker_bone = edit_bones.get("EyeTracker")
        if not eye_tracker_bone:
            self.report({'ERROR'}, "EyeTracker bone not found. Rig the character first.")
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'CANCELLED'}

        # Create FacePanelRoot and FacePanel bones
        face_panel_root = edit_bones.new("FacePanelRoot")
        face_panel_root.head = eye_tracker_bone.head.copy()
        face_panel_root.head.y -= 0.05
        face_panel_root.tail = face_panel_root.head + mathutils.Vector((0, 0, 0.03))
        head_bone = edit_bones.get("ORG-head") or edit_bones.get("head") or edit_bones.get("Bip001Head")
        if head_bone:
            face_panel_root.parent = head_bone

        face_panel = edit_bones.new("FacePanel")
        face_panel.head = face_panel_root.head.copy()
        face_panel.tail = face_panel.head + mathutils.Vector((0, 0, 0.03))
        face_panel.parent = face_panel_root

        eye_scale = edit_bones.new("EyeScale")
        eye_scale.head = face_panel.head.copy()
        eye_scale.tail = eye_scale.head + mathutils.Vector((0.0, 0.0, 0.01))
        eye_scale.parent = face_panel

        for bone_name in ["Eye.L", "Eye.R"]:
            bone = edit_bones.get(bone_name)
            if bone:
                bone.parent = face_panel

        eye_tracker_bone.parent = face_panel_root

        # Fan bones for expressions
        def create_fan_bones(base_bone_name, custom_bone_names, side_suffix):
            base_bone = edit_bones.get(base_bone_name)
            if not base_bone:
                return
            fan_center = base_bone.head
            radius = 0.035
            bone_length = 0.02
            num_bones = len(custom_bone_names)
            arc_angle = math.radians(120)
            angle_start = -arc_angle / 2
            for i in range(num_bones):
                angle = angle_start + i * (arc_angle / (num_bones - 1))
                direction_multiplier = -1 if side_suffix == ".R" else 1
                head_x = math.cos(angle) * radius * direction_multiplier
                head_z = math.sin(angle) * radius
                head = fan_center + mathutils.Vector((head_x, 0, head_z))
                tail = head + (head - fan_center).normalized() * bone_length
                bone_name = custom_bone_names[i].replace(".L", side_suffix)
                fan_bone = edit_bones.new(bone_name)
                fan_bone.head = head
                fan_bone.tail = tail
                fan_bone.parent = edit_bones["FacePanel"]
                fan_bone.use_connect = False

        custom_bone_names_L = ["Insipid.L", "Focus.L", "Sad.L", "Anger.L", "Smile.L"]
        custom_bone_names_R = [name.replace(".L", ".R") for name in custom_bone_names_L]
        create_fan_bones("Eye.L", custom_bone_names_L, ".L")
        create_fan_bones("Eye.R", custom_bone_names_R, ".R")

        # Eyebrows panel
        eyebrows_bone = edit_bones.new("Eyebrows")
        eyebrows_head = face_panel.head + mathutils.Vector((0, 0, 0.06))
        eyebrows_bone.head = eyebrows_head
        eyebrows_bone.tail = eyebrows_head + mathutils.Vector((0, 0, 0.01))
        eyebrows_bone.parent = face_panel
        eyebrows_bone.use_connect = False

        b_names = ["B_Anger", "B_Happy", "B_Cheerful", "B_Sad", "B_Flat", "B_Inside_Add"]
        spacing = 0.015
        start_x = -spacing * (len(b_names) - 1) / 2
        y = eyebrows_head.y
        z = eyebrows_bone.tail.z
        for i, name in enumerate(b_names):
            b = edit_bones.new(name)
            head = mathutils.Vector((start_x + i * spacing, y, z))
            tail = head + mathutils.Vector((0, 0, 0.02))
            b.head = head
            b.tail = tail
            b.parent = eyebrows_bone
            b.use_connect = False

        # Mouth panel
        mouth_panel_bone = edit_bones.new("MouthPanel")
        mouth_panel_head = face_panel.head - mathutils.Vector((0, 0, 0.055))
        mouth_panel_bone.head = mouth_panel_head
        mouth_panel_bone.tail = mouth_panel_head + mathutils.Vector((0, 0, 0.01))
        mouth_panel_bone.parent = face_panel
        mouth_panel_bone.use_connect = False

        mouth_bone = edit_bones.new("Mouth")
        mouth_bone.head = mouth_panel_head
        mouth_bone.tail = mouth_bone.head + mathutils.Vector((0, 0, 0.02))
        mouth_bone.parent = mouth_panel_bone
        mouth_bone.use_connect = False

        offset_x = 0.045
        for side in [("Mouth.L", offset_x), ("Mouth.R", -offset_x)]:
            name, x_offset = side
            b = edit_bones.new(name)
            head = mathutils.Vector((mouth_bone.head.x + x_offset, mouth_bone.head.y, mouth_bone.head.z))
            tail = head + mathutils.Vector((0, 0, 0.02))
            b.head = head
            b.tail = tail
            b.parent = mouth_panel_bone
            b.use_connect = False

        expressions = ["Aa", "M_OpenSmall", "M_Laugh", "M_Scared", "M_ScaredTooth",
                       "M_Anger", "M_Trapezoid", "M_Nutcracker", "M_O", "M_A"]
        num = len(expressions)
        spacing = 0.01
        total_width = (num - 1) * spacing
        start_x = mouth_panel_head.x - total_width / 2
        y = mouth_panel_head.y
        z = mouth_panel_head.z - 0.035
        for i, name in enumerate(expressions):
            b = edit_bones.new(name)
            head = mathutils.Vector((start_x + i * spacing, y, z))
            tail = head - mathutils.Vector((0, 0, 0.02))
            b.head = head
            b.tail = tail
            b.parent = mouth_panel_bone
            b.use_connect = False

        bpy.ops.object.mode_set(mode='OBJECT')

        # Constraint for FollowEyeTracker
        if "FacePanel" in armature_obj.pose.bones and "EyeTracker" in armature_obj.pose.bones:
            face_panel_pose = armature_obj.pose.bones["FacePanel"]
            if "FollowEyeTracker" not in face_panel_pose.constraints:
                con = face_panel_pose.constraints.new(type='COPY_LOCATION')
                con.name = "FollowEyeTracker"
                con.target = armature_obj
                con.subtarget = "EyeTracker"

        # Apply Drivers
        if CharacterMesh:
            self.setup_create_panel_drivers(context, armature_obj, CharacterMesh)

        self.report({'INFO'}, "Created Face Panel and configured expression drivers successfully!")
        return {'FINISHED'}


register, unregister = bpy.utils.register_classes_factory([WW_OT_CreateFacePanel])

