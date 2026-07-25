# Author: michael-gh1

import re
import bpy
import os

from setup_wizard.domain.shader_material_names import ShaderMaterialNames, V2_FestivityGenshinImpactMaterialNames, V3_BonnyFestivityGenshinImpactMaterialNames, V4_PrimoToonGenshinImpactMaterialNames
from setup_wizard.domain.shader_identifier_service import GenshinImpactShaders, ShaderIdentifierService, ShaderIdentifierServiceFactory
from setup_wizard.character_rig_setup.lighting_panel_setup import LightingPanel, LightingPanelFileNames, LightingPanelFileNamesFactory
from setup_wizard.character_rig_setup.rig_script import rig_character
from setup_wizard.character_rig_setup.npc_rig_script import rig_character as rig_npc
from setup_wizard.character_rig_setup.hsr_rig_script import rig_character as hsr_rig_character
from setup_wizard.character_rig_setup.zzz_rig_script import rig_character as zzz_rig_character
from setup_wizard.character_rig_setup.zzz_face_rig import zzz_face_rig_main

from abc import ABC, abstractmethod
from bpy.types import Armature, Operator, Context

from setup_wizard.domain.game_types import GameType
from setup_wizard.import_order import GENSHIN_RIGIFY_BONE_SHAPES_FILE_PATH, NextStepInvoker, cache_using_cache_key, \
    get_cache

from setup_wizard.character_rig_setup.character_rigger_props import CharacterRiggerPropertyGroup
from setup_wizard.texture_import_setup.texture_node_names import TextureNodeNames, V1_GenshinImpactTextureNodeNames, V2_GenshinImpactTextureNodeNames, V3_GenshinImpactTextureNodeNames, V4_GenshinImpactTextureNodeNames
from setup_wizard.utils.modifier_utils import get_modifier_property, set_modifier_property

class CharacterRiggerFactory:
    def create(game_type: GameType, blender_operator: Operator, context: Context):
        shader_identifier_service: ShaderIdentifierService = ShaderIdentifierServiceFactory.create(game_type)
        shader = shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)
        if game_type == GameType.GENSHIN_IMPACT.name:
            if shader is GenshinImpactShaders.V1_GENSHIN_IMPACT_SHADER:
                material_names = V2_FestivityGenshinImpactMaterialNames
                texture_node_names = V1_GenshinImpactTextureNodeNames
            elif shader is GenshinImpactShaders.V2_GENSHIN_IMPACT_SHADER:
                material_names = V2_FestivityGenshinImpactMaterialNames
                texture_node_names = V2_GenshinImpactTextureNodeNames
            elif shader is GenshinImpactShaders.V3_GENSHIN_IMPACT_SHADER:
                material_names = V3_BonnyFestivityGenshinImpactMaterialNames
                texture_node_names = V3_GenshinImpactTextureNodeNames
            else:
                material_names = V4_PrimoToonGenshinImpactMaterialNames
                texture_node_names = V4_GenshinImpactTextureNodeNames
            return GenshinImpactCharacterRigger(blender_operator, context, material_names, texture_node_names, shader)
        elif game_type == GameType.HONKAI_STAR_RAIL.name:
            return HonkaiStarRailCharacterRigger(blender_operator, context)
        elif game_type == GameType.PUNISHING_GRAY_RAVEN.name:
            return PunishingGrayRavenCharacterRigger(blender_operator, context)
        elif game_type == GameType.ZENLESS_ZONE_ZERO.name:
            return ZenlessZoneZeroCharacterRigger(blender_operator, context)
        elif game_type == GameType.NEVERNESS_TO_EVERNESS.name:
            return NevernessToEvernessCharacterRigger(blender_operator, context)
        else:
            raise Exception(f'Unexpected input GameType "{game_type}" for CharacterRiggerFactory')



class CharacterRigger(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def rig_character(self):
        raise NotImplementedError


def _get_character_armature(context):
    selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
    if selected_armatures:
        return selected_armatures[0]

    view_layer_objs = getattr(context.view_layer, 'objects', context.scene.objects)
    view_armatures = [obj for obj in view_layer_objs if obj.type == 'ARMATURE']

    for obj in view_armatures:
        if 'Rig' in obj.name and not any(ign in obj.name.lower() for ign in ['eyerig', 'facerig', 'lighting', 'metarig']):
            return obj

    for obj in view_armatures:
        if not any(ign in obj.name.lower() for ign in ['eyerig', 'facerig', 'lighting', 'metarig']):
            return obj

    return view_armatures[0] if view_armatures else None


class GenshinImpactCharacterRigger(CharacterRigger):
    def __init__(self, blender_operator, context, material_names, texture_node_names, shader):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context
        self.rigify_bone_shapes_file_path = GENSHIN_RIGIFY_BONE_SHAPES_FILE_PATH
        self.material_names: ShaderMaterialNames = material_names
        self.texture_node_names: TextureNodeNames = texture_node_names
        self.lighting_panel_file_names: LightingPanelFileNames = LightingPanelFileNamesFactory.create(shader)

    def rig_character(self):
        cache_enabled = self.context.window_manager.cache_enabled
        filepath = get_cache(cache_enabled).get(self.rigify_bone_shapes_file_path) or self.blender_operator.filepath

        if not filepath:
            filepath = self.lighting_panel_file_names.ROOT_SHAPE_FILEPATH

        light_vectors_modifiers = [modifier for obj in bpy.data.objects.values() if 
                                   obj.type == 'MESH' for modifier in obj.modifiers if 
                                   'Light Vectors' in modifier.name]

        armature: Armature = _get_character_armature(self.context)
        if not armature:
            self.blender_operator.report({'ERROR'}, 'No armature found. Please import or select a character.')
            return

        hand_bones = [bone for bone in armature.pose.bones.values() if 'Hand' in bone.name]
        number_of_hand_bone_children = max([len(hand_bone.children) for hand_bone in hand_bones]) if hand_bones else 0
        is_player_hand = number_of_hand_bone_children >= 5
        avatar_in_texture_name = self.__get_body_diffuse_texture_name().startswith('Avatar')
        is_playable_character = avatar_in_texture_name or is_player_hand

        character_rigger_props: CharacterRiggerPropertyGroup = self.context.scene.character_rigger_props

        # Lighting Panel is an Armature, so it's important this goes after the armature variable initialization above
        # Genshin Shader >= v3.4
        if character_rigger_props.set_up_lighting_panel:
            for modifier in light_vectors_modifiers:
                LightingPanel(self.lighting_panel_file_names.LIGHTING_PANEL_FILEPATH).set_up_lighting_panel(modifier)

        # Important that the Armature is selected before performing rigging operations
        # Ensure we are in OBJECT mode before manipulating selection (Blender 5.0 compatibility)
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError:
            pass
        bpy.ops.object.select_all(action='DESELECT')
        try:
            armature.hide_set(False)
        except:
            pass
        self.context.view_layer.objects.active = armature
        armature.select_set(True)

        meshes_joined = not (bpy.data.objects.get('Body') and bpy.data.objects.get('Face'))
        if [material for material in bpy.data.materials.values() if 'Paimon' in material.name]:
            rig_npc(
                filepath,
                not character_rigger_props.allow_arm_ik_stretch,
                not character_rigger_props.allow_leg_ik_stretch,
                character_rigger_props.use_arm_ik_poles,
                character_rigger_props.use_leg_ik_poles,
                character_rigger_props.add_children_of_constraints,
                character_rigger_props.use_head_tracker,
            )
        elif not is_playable_character:
            rig_npc(
                filepath,
                not character_rigger_props.allow_arm_ik_stretch,
                not character_rigger_props.allow_leg_ik_stretch,
                character_rigger_props.use_arm_ik_poles,
                character_rigger_props.use_leg_ik_poles,
                character_rigger_props.add_children_of_constraints,
                character_rigger_props.use_head_tracker,
            )                                 
        else:
            rig_character(
                filepath,
                self.lighting_panel_file_names.VERSION,
                not character_rigger_props.allow_arm_ik_stretch,
                not character_rigger_props.allow_leg_ik_stretch,
                character_rigger_props.use_arm_ik_poles,
                character_rigger_props.use_leg_ik_poles,
                character_rigger_props.add_children_of_constraints,
                character_rigger_props.use_head_tracker,
                meshes_joined=meshes_joined
            )

        # Refresh Light Vectors modifiers since empties are renamed/appended during rigging
        def refresh_light_vectors_modifiers():
            char_name = armature.name.replace("Rig", "")
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.parent == armature:
                    for modifier in obj.modifiers:
                        if modifier.type == 'NODES' and modifier.node_group and 'Light Vectors' in modifier.node_group.name:
                            def assign_empty(socket, empty_name):
                                empty_obj = bpy.data.objects.get(f"{empty_name}_{char_name}")
                                if empty_obj:
                                    set_modifier_property(modifier, socket, empty_obj)

                            assign_empty('Input_3', 'Light Direction')
                            if not get_modifier_property(modifier, 'Input_3'):
                                assign_empty('Input_3', 'Main Light Direction')
                            assign_empty('Input_4', 'Head Origin')
                            assign_empty('Input_5', 'Head Forward')
                            assign_empty('Input_6', 'Head Up')

        refresh_light_vectors_modifiers()

        self.blender_operator.report({'INFO'}, 'Successfully rigged character')

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx,
            self.blender_operator.invoker_type,
            file_path_to_cache=filepath,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=GameType.GENSHIN_IMPACT.name
        )

    def __get_body_diffuse_texture_name(self):
        body_material = self.__get_body_material()
        if not body_material:
            return ''

        body_diffuse_node = self.__get_body_diffuse_node(body_material, self.texture_node_names)
        body_diffuse_texture = self.__get_body_diffuse_texture(body_material, body_diffuse_node)
        return body_diffuse_texture.name if body_diffuse_texture else ''

    def __get_body_material(self):
        pattern = fr"^{self.material_names.MATERIAL_PREFIX_AFTER_RENAME}.*Body$"
        for material in bpy.data.materials.values():
            if re.match(pattern, material.name):
                return material

    def __get_body_diffuse_node(self, material, texture_node_names):
        body_diffuse_node_names = [
            texture_node_names.BODY_DIFFUSE_UV0,  # Genshin
            texture_node_names.MAIN_DIFFUSE,  # Genshin >= v4.0
        ]

        for node_name in body_diffuse_node_names:
            if material and material.node_tree.nodes.get(node_name):
                return material.node_tree.nodes.get(node_name)

    def __get_body_diffuse_texture(self, body_material, body_diffuse_node):
        return body_material.node_tree.nodes.get(body_diffuse_node.name).image


class HonkaiStarRailCharacterRigger(CharacterRigger):
    def __init__(self, blender_operator, context):
        self.blender_operator = blender_operator
        self.context = context
        self.rigify_bone_shapes_file_path = GENSHIN_RIGIFY_BONE_SHAPES_FILE_PATH

    def rig_character(self):
        cache_enabled = self.context.window_manager.cache_enabled
        filepath = get_cache(cache_enabled).get(self.rigify_bone_shapes_file_path) or self.blender_operator.filepath

        if not filepath:
            filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RootShape.blend')

        armature = _get_character_armature(self.context)
        if not armature:
            self.blender_operator.report({'ERROR'}, 'No armature found. Please import or select a character.')
            return

        character_rigger_props: CharacterRiggerPropertyGroup = self.context.scene.character_rigger_props
        meshes_joined = not (bpy.data.objects.get('Body') and bpy.data.objects.get('Face'))

        bpy.ops.object.select_all(action='DESELECT')
        try:
            armature.hide_set(False)
        except:
            pass
        self.context.view_layer.objects.active = armature
        armature.select_set(True)

        hsr_rig_character(
            filepath,
            not character_rigger_props.allow_arm_ik_stretch,
            not character_rigger_props.allow_leg_ik_stretch,
            character_rigger_props.use_arm_ik_poles,
            character_rigger_props.use_leg_ik_poles,
            character_rigger_props.add_children_of_constraints,
            character_rigger_props.use_head_tracker,
            meshes_joined=meshes_joined
        )

        try:
            from setup_wizard.character_rig_setup.hsr_face_rig import hsr_face_rig_main
            hsr_face_rig_main()
        except Exception as e:
            print(f"HSR face rig skipped: {e}")

        def refresh_light_vectors_modifiers():
            char_name = armature.name.replace("Rig", "")
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.parent == armature:
                    for modifier in obj.modifiers:
                        if modifier.type == 'NODES' and modifier.node_group and 'Light Vectors' in modifier.node_group.name:
                            def assign_empty(socket, empty_name):
                                empty_obj = bpy.data.objects.get(f"{empty_name}_{char_name}")
                                if empty_obj:
                                    set_modifier_property(modifier, socket, empty_obj)

                            assign_empty('Input_3', 'Light Direction')
                            if not get_modifier_property(modifier, 'Input_3'):
                                assign_empty('Input_3', 'Main Light Direction')
                            assign_empty('Input_4', 'Head Origin')
                            assign_empty('Input_5', 'Head Forward')
                            assign_empty('Input_6', 'Head Up')

        refresh_light_vectors_modifiers()

        self.blender_operator.report({'INFO'}, 'Successfully rigged HSR character')

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx,
            self.blender_operator.invoker_type,
            file_path_to_cache=filepath,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=GameType.HONKAI_STAR_RAIL.name
        )


class PunishingGrayRavenCharacterRigger(CharacterRigger):
    def __init__(self, blender_operator, context):
        self.blender_operator = blender_operator
        self.context = context
        self.rigify_bone_shapes_file_path = 'PLACEHOLDER'

    def rig_character(self):
        return


class ZenlessZoneZeroCharacterRigger(CharacterRigger):
    def __init__(self, blender_operator, context):
        self.blender_operator = blender_operator
        self.context = context
        self.rigify_bone_shapes_file_path = GENSHIN_RIGIFY_BONE_SHAPES_FILE_PATH

    def rig_character(self):
        cache_enabled = self.context.window_manager.cache_enabled
        filepath = get_cache(cache_enabled).get(self.rigify_bone_shapes_file_path) or self.blender_operator.filepath

        if not filepath:
            filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RootShape.blend')

        armature = _get_character_armature(self.context)
        if not armature:
            self.blender_operator.report({'ERROR'}, 'No armature found. Please import or select a character.')
            return

        character_rigger_props: CharacterRiggerPropertyGroup = self.context.scene.character_rigger_props
        meshes_joined = not (bpy.data.objects.get('Body') and bpy.data.objects.get('Face'))

        bpy.ops.object.select_all(action='DESELECT')
        try:
            armature.hide_set(False)
        except:
            pass
        self.context.view_layer.objects.active = armature
        armature.select_set(True)

        zzz_rig_character(
            filepath,
            0, # lighting_panel_version
            not character_rigger_props.allow_arm_ik_stretch,
            not character_rigger_props.allow_leg_ik_stretch,
            character_rigger_props.use_arm_ik_poles,
            character_rigger_props.use_leg_ik_poles,
            character_rigger_props.add_children_of_constraints,
            character_rigger_props.use_head_tracker,
            meshes_joined=meshes_joined
        )

        try:
            zzz_face_rig_main()
        except Exception as e:
            print(f"Face rig skipped: {e}")

        def refresh_light_vectors_modifiers():
            char_name = armature.name.replace("Rig", "")
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.parent == armature:
                    for modifier in obj.modifiers:
                        if modifier.type == 'NODES' and modifier.node_group and 'Light Vectors' in modifier.node_group.name:
                            def assign_empty(socket, empty_name):
                                empty_obj = bpy.data.objects.get(f"{empty_name}_{char_name}")
                                if empty_obj:
                                    set_modifier_property(modifier, socket, empty_obj)

                            assign_empty('Input_3', 'Light Direction')
                            if not get_modifier_property(modifier, 'Input_3'):
                                assign_empty('Input_3', 'Main Light Direction')
                            assign_empty('Input_4', 'Head Origin')
                            assign_empty('Input_5', 'Head Forward')
                            assign_empty('Input_6', 'Head Up')

        refresh_light_vectors_modifiers()

        self.blender_operator.report({'INFO'}, 'Successfully rigged ZZZ character')

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx,
            self.blender_operator.invoker_type,
            file_path_to_cache=filepath,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=GameType.ZENLESS_ZONE_ZERO.name
        )


class NevernessToEvernessCharacterRigger(CharacterRigger):
    def __init__(self, blender_operator, context):
        self.blender_operator = blender_operator
        self.context = context

    def rig_character(self):
        armature = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
        armature = armature[0] if armature else None

        cache_enabled = self.context.window_manager.cache_enabled
        filepath = self.blender_operator.filepath or get_cache(cache_enabled).get(GENSHIN_RIGIFY_BONE_SHAPES_FILE_PATH)

        if armature:
            try:
                rig_character(armature, filepath)
            except Exception as ex:
                self.blender_operator.report({'ERROR'}, f"Failed to rig NTE character: {ex}")

        self.blender_operator.report({'INFO'}, 'Successfully rigged NTE character')

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx,
            self.blender_operator.invoker_type,
            file_path_to_cache=filepath,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=GameType.NEVERNESS_TO_EVERNESS.name
        )

