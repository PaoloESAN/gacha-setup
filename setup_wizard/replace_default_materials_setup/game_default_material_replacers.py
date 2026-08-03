# Author: michael-gh1

import bpy
import os


from abc import ABC, abstractmethod
from bpy.types import Context, Operator
from setup_wizard.domain.shader_node_names import ShaderNodeNames, StellarToonShaderNodeNames, V2_GenshinShaderNodeNames, V3_GenshinShaderNodeNames, V4_PrimoToonShaderNodeNames
from setup_wizard.domain.star_cloak_types import StarCloakTypes
from setup_wizard.domain.material_identifier_service import PunishingGrayRavenMaterialIdentifierService

from setup_wizard.import_order import CHARACTER_MODEL_FOLDER_FILE_PATH, NextStepInvoker, get_actual_material_name_for_dress, get_cache, get_active_character_directory


from setup_wizard.domain.game_types import GameType
from setup_wizard.domain.shader_identifier_service import GenshinImpactShaders, HonkaiStarRailShaders, ShaderIdentifierService, \
    ShaderIdentifierServiceFactory
from setup_wizard.domain.shader_material_names import StellarToonShaderMaterialNames, V3_BonnyFestivityGenshinImpactMaterialNames, V2_FestivityGenshinImpactMaterialNames, \
    ShaderMaterialNames, Nya222HonkaiStarRailShaderMaterialNames, JaredNytsPunishingGrayRavenShaderMaterialNames, V4_PrimoToonGenshinImpactMaterialNames, \
    ZenlessZoneZeroShaderMaterialNames
from setup_wizard.texture_import_setup.texture_importer_types import TextureImporterType
from setup_wizard.domain.shader_material_name_keywords import ShaderMaterialNameKeywords
from setup_wizard.utils.genshin_body_part_deducer import get_monster_body_part_name, \
    get_npc_mesh_body_part_name

class GameDefaultMaterialReplacer(ABC):
    @abstractmethod
    def replace_default_materials(self):
        raise NotImplementedError()


class GameDefaultMaterialReplacerFactory:
    def create(game_type: GameType, blender_operator: Operator, context: Context):
        shader_identifier_service: ShaderIdentifierService = ShaderIdentifierServiceFactory.create(game_type)
        shader = shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)

        # Because we inject the GameType via StringProperty, we need to compare using the Enum's name (a string)
        if game_type == GameType.GENSHIN_IMPACT.name:
            if shader is GenshinImpactShaders.V1_GENSHIN_IMPACT_SHADER or shader is GenshinImpactShaders.V2_GENSHIN_IMPACT_SHADER:
                material_names = V2_FestivityGenshinImpactMaterialNames
                shader_node_names = V2_GenshinShaderNodeNames
            elif shader is GenshinImpactShaders.V3_GENSHIN_IMPACT_SHADER:
                material_names = V3_BonnyFestivityGenshinImpactMaterialNames
                shader_node_names = V3_GenshinShaderNodeNames
            elif shader is GenshinImpactShaders.V1_HOYOTOON_GENSHIN_IMPACT_SHADER:
                from setup_wizard.domain.shader_material_names import V1_HoYoToonGenshinImpactMaterialNames
                from setup_wizard.domain.shader_node_names import V1_HoYoToonShaderNodeNames
                material_names = V1_HoYoToonGenshinImpactMaterialNames
                shader_node_names = V1_HoYoToonShaderNodeNames
            else:
                material_names = V4_PrimoToonGenshinImpactMaterialNames 
                shader_node_names = V4_PrimoToonShaderNodeNames
            return GenshinImpactDefaultMaterialReplacer(blender_operator, context, material_names, shader_node_names)
        elif game_type == GameType.HONKAI_STAR_RAIL.name:
            if shader is HonkaiStarRailShaders.NYA222_HONKAI_STAR_RAIL_SHADER:
                return HonkaiStarRailDefaultMaterialReplacer(blender_operator, context, Nya222HonkaiStarRailShaderMaterialNames)
            else:  # shader is HonkaiStarRailShaders.STELLARTOON_HONKAI_STAR_RAIL_SHADER
                return StellarToonDefaultMaterialReplacer(blender_operator, context, StellarToonShaderMaterialNames)
        elif game_type == GameType.PUNISHING_GRAY_RAVEN.name:
            return PunishingGrayRavenDefaultMaterialReplacer(blender_operator, context)
        elif game_type == GameType.ZENLESS_ZONE_ZERO.name:
            return ZenlessZoneZeroDefaultMaterialReplacer(blender_operator, context)
        elif game_type == GameType.NEVERNESS_TO_EVERNESS.name:
            return NevernessToEvernessDefaultMaterialReplacer(blender_operator, context)
        else:
            raise Exception(f'Unknown {GameType}: {game_type}')



class GenshinImpactDefaultMaterialReplacer(GameDefaultMaterialReplacer):
    def __init__(self, blender_operator, context, material_names: ShaderMaterialNames, shader_node_names: ShaderNodeNames):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context
        self.material_names = material_names
        self.shader_node_names = shader_node_names

    def replace_default_materials(self):
        mesh_ignore_list = [
            'Dress',  # Scaramouche
        ]
        meshes = [mesh for mesh in bpy.context.scene.objects if mesh.type == 'MESH' and mesh.name not in mesh_ignore_list]

        for mesh in meshes:
            for material_slot in mesh.material_slots:
                material_name = material_slot.name
                
                # If it already has our shader prefix, it was processed previously (e.g. earlier character).
                if material_name.startswith(self.material_names.MATERIAL_PREFIX):
                    continue

                mesh_body_part_name = None
                character_type = None

                if material_name.startswith('NPC'):
                    mesh_body_part_name = get_npc_mesh_body_part_name(material_name)
                    character_type = TextureImporterType.NPC
                elif material_name.startswith('Monster'):
                    mesh_body_part_name = get_monster_body_part_name(material_name)
                    character_type = TextureImporterType.MONSTER
                else:
                    mesh_body_part_name = material_name.split('_')[-1]
                    character_type = TextureImporterType.AVATAR

                if material_name.startswith(ShaderMaterialNameKeywords.SKILLOBJ) and material_name.endswith('Glass_Mat'):
                    mesh_body_part_name = 'Glass'
                elif material_name.startswith(ShaderMaterialNameKeywords.SKILLOBJ) and material_name.endswith('Glass_Eff_Mat'):
                    mesh_body_part_name = 'Glass_Eff'
                elif material_name.startswith(ShaderMaterialNameKeywords.SKILLOBJ):
                    skillobj_identifier = material_name.split('_')[2]
                    mesh_body_part_name = f'{ShaderMaterialNameKeywords.SKILLOBJ} {skillobj_identifier}'
                elif material_name.endswith('Hand_Eff_Mat'):  # Asmoday
                    mesh_body_part_name = 'StarCloak'

                if mesh_body_part_name in ['Eye', 'EyeStar', 'Eyes', 'EyeShadow']:
                    mesh_body_part_name = 'Face'

                # If material_name is ever 'Dress', 'Arm' or 'Cloak', there could be issues with get_actual_material_name_for_dress()
                material_name = self.create_shader_material_if_unique_mesh(mesh, mesh_body_part_name, material_name)
                genshin_material = bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}{mesh_body_part_name}')
                if not genshin_material and mesh_body_part_name in ['Eye', 'EyeStar', 'Eyes', 'EyeShadow', 'Brow']:
                    genshin_material = bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}Face') or \
                                       bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}Brow')

                if genshin_material:
                    self.__transfer_diffuse_texture(material_slot.material, genshin_material)
                    material_slot.material = genshin_material
                elif mesh_body_part_name and ('Dress' in mesh_body_part_name or 'Arm' in mesh_body_part_name or 'Cloak' in mesh_body_part_name):
                    # Xiao is the only character with an Arm material
                    # Dainsleif and Paimon are the only characters with Cloak materials
                    self.blender_operator.report({'INFO'}, 'Dress detected on character model!')

                    actual_material_for_dress = get_actual_material_name_for_dress(material_name, character_type.name)
                    if actual_material_for_dress == 'Cloak' or mesh_body_part_name == 'Cloak':
                        if bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}VFX'):
                            actual_material_for_dress = 'VFX'
                            mesh_body_part_name = 'StarCloak'
                        elif mesh_body_part_name == 'Cloak' and character_type == TextureImporterType.AVATAR:
                            pass  # Give Dainslief basic body shader (backwards compatibility)
                        else:
                            # short-circuit, no shader available for 'Cloak' so do nothing (Paimon)
                            continue
                    elif actual_material_for_dress == 'Effect':  # Dress2 material w/ Effect texture filename (Skirk support)
                        # (dangerous) assumption that all Dress w/ Effect texture filename are Hair-type
                        actual_material_for_dress = 'Hair'  # backwards compatible before VFX shader existed, pre-v4.0

                        if bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}VFX'):
                            actual_material_for_dress = 'VFX'
                            mesh_body_part_name = 'StarCloak'
                    elif actual_material_for_dress == 'Eff':  # Asmoday support
                        # (dangerous) assumption that all Eff texture filename are Body-type
                        actual_material_for_dress = 'Body'  # backwards compatible before VFX shader existed, pre-v4.0

                        if bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}VFX'):
                            actual_material_for_dress = 'VFX'
                            mesh_body_part_name = 'StarCloak'

                    genshin_material = self.__clone_material_and_rename(
                        material_slot, 
                        f'{self.material_names.MATERIAL_PREFIX}{actual_material_for_dress}', 
                        mesh_body_part_name
                    )
                    if not genshin_material:
                        self.blender_operator.report({'WARNING'}, f'Could not find template material for "{actual_material_for_dress}", skipping material: {material_name}')
                        continue
                    if genshin_material.name == f'{self.material_names.STAR_CLOAK}':
                        self.__set_glass_star_cloak_toggle(genshin_material, True)
                        self.__set_star_cloak_type(genshin_material, material_name)  # original material name, which contains character name
                    self.blender_operator.report({'INFO'}, f'Replaced material: "{material_name}" with "{actual_material_for_dress}"')
                elif material_name == 'miHoYoDiffuse':
                    material_slot.material = bpy.data.materials.get(self.material_names.BODY)
                    continue
                else:
                    self.blender_operator.report({'WARNING'}, f'Ignoring unknown mesh body part in character model: {mesh_body_part_name} / Material: {material_name}')
                    continue

                # Deprecated: I don't think cloning and renaming groups is necessary? (original commit: 6a4772e)
                # Don't need to duplicate multiple Face shader nodes
                # if genshin_material.name != f'miHoYo - Genshin Face':
                #     genshin_main_shader_node = genshin_material.node_tree.nodes.get('Group.001')
                #     genshin_main_shader_node.node_tree = self.__clone_shader_node_and_rename(genshin_material, mesh_body_part_name)
        self.blender_operator.report({'INFO'}, 'Replaced default materials with Genshin shader materials...')

    def create_shader_material_if_unique_mesh(self, mesh, mesh_body_part_name, material_name):
        if mesh_body_part_name == 'Body1':  # >= GI v5.7
            body_material = self.create_body_material(self.material_names, self.material_names.BODY1)
            material_name = body_material.name
        elif mesh_body_part_name == 'Body2':  # >= GI v5.7
            body_material = self.create_body_material(self.material_names, self.material_names.BODY2)
            material_name = body_material.name
        elif mesh_body_part_name == 'EffectHair':  # Furina
            hair_material = self.create_hair_material(self.material_names, self.material_names.EFFECT_HAIR)
            material_name = hair_material.name
        elif mesh_body_part_name == 'Effect':  # Furina (Default)
            hair_material = self.create_hair_material(self.material_names, self.material_names.EFFECT)
            material_name = hair_material.name
        elif mesh_body_part_name == 'Helmet':  # Frem
            helmet_material = self.create_hair_material(self.material_names, self.material_names.HELMET)
            material_name = helmet_material.name
        elif mesh_body_part_name == 'HelmetEmo':  # Frem
            helmet_material = self.create_hair_material(self.material_names, self.material_names.HELMET_EMO)
            material_name = helmet_material.name
        elif mesh_body_part_name == 'Gauntlet':  # Wrioth
            gauntlet_material = self.create_body_material(self.material_names, self.material_names.GAUNTLET)
            material_name = gauntlet_material.name
        elif mesh_body_part_name == 'Leather':
            leather_material = self.create_body_material(self.material_names, self.material_names.LEATHER)
            material_name = leather_material.name
        elif mesh_body_part_name == 'Glass':
            glass_material = self.create_body_material(self.material_names, self.material_names.GLASS)
            material_name = glass_material.name
        elif mesh_body_part_name == 'Glass_Eff':
            glass_material = self.create_glass_material(self.material_names, self.material_names.GLASS_EFF)
            if glass_material:
                self.__set_glass_star_cloak_toggle(glass_material, False)
                glass_method_set = True
                glass_material.blend_method = 'BLEND'
                glass_material.shadow_method = 'NONE'
                glass_material.show_transparent_back = False
                material_name = glass_material.name
        elif mesh_body_part_name and mesh_body_part_name.startswith(ShaderMaterialNameKeywords.SKILLOBJ):
            skillobj_material = self.create_body_material(self.material_names, self.material_names.SKILLOBJ)
            skillobj_material.name = skillobj_material.name.replace(ShaderMaterialNameKeywords.SKILLOBJ, mesh_body_part_name)
            material_name = skillobj_material.name
        elif mesh_body_part_name == 'Skirt':
            skirt_material = self.create_body_material(self.material_names, self.material_names.SKIRT)
            material_name = skirt_material.name
        elif mesh_body_part_name == 'Pupil':
            pupil_material = self.create_body_material(self.material_names, self.material_names.PUPIL)
            material_name = pupil_material.name
        elif mesh_body_part_name and 'Item' in mesh_body_part_name:  # NPCs
            item_material = self.create_body_material(self.material_names, f'{self.material_names.MATERIAL_PREFIX}{mesh_body_part_name}')
            material_name = item_material.name
        elif mesh_body_part_name and ('Screw' in mesh_body_part_name or 'Hat' in mesh_body_part_name):  # Aranaras
            new_material = self.create_body_material(self.material_names, f'{self.material_names.MATERIAL_PREFIX}{mesh_body_part_name}')
            material_name = new_material.name
        elif mesh_body_part_name and 'Others' in mesh_body_part_name:  # NPCs, Frem Penguins
            new_material = self.create_body_material(self.material_names, f'{self.material_names.MATERIAL_PREFIX}{mesh_body_part_name}')
            material_name = new_material.name
        elif mesh_body_part_name and mesh_body_part_name not in ['Face', 'Body', 'Hair', 'Eye', 'Dress', 'Arm', 'Cloak', 'VFX', 'StarCloak']:
            # Fallback for completely unknown materials (like 'Stockings', 'Wings', etc)
            new_material = self.create_body_material(self.material_names, f'{self.material_names.MATERIAL_PREFIX}{mesh_body_part_name}')
            material_name = new_material.name
        return material_name

    def __clone_material_and_rename(self, material_slot, mesh_body_part_name_template, mesh_body_part_name):
        template_material = bpy.data.materials.get(mesh_body_part_name_template)
        if not template_material:
            print(f'WARNING: Template material "{mesh_body_part_name_template}" not found, cannot clone for "{mesh_body_part_name}"')
            return None
        new_material = template_material.copy()
        new_material.name = f'{self.material_names.MATERIAL_PREFIX}{mesh_body_part_name}'
        new_material.use_fake_user = True

        self.__transfer_diffuse_texture(material_slot.material, new_material)
        material_slot.material = new_material
        return new_material

    def __transfer_diffuse_texture(self, old_material, new_material):
        if not old_material or not old_material.use_nodes or not new_material or not new_material.use_nodes:
            return
            
        old_image = None
        for node in old_material.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                old_image = node.image
                break
                
        if not old_image:
            return
            
        target_tree = new_material.node_tree
        group = target_tree.nodes.get('Shader Textures')
        if group and group.node_tree:
            target_tree = group.node_tree
            
        for name in ['Main_Diffuse', 'Outline_Diffuse', 'Body_Diffuse_UV0']:
            img_node = target_tree.nodes.get(name)
            if img_node and img_node.type == 'TEX_IMAGE':
                img_node.image = old_image
                return

    def __set_glass_star_cloak_toggle(self, material, value):
        vfx_shader_node = material.node_tree.nodes.get(self.shader_node_names.VFX_SHADER)
        vfx_shader_node.inputs.get(self.shader_node_names.TOGGLE_GLASS_STAR_CLOAK).default_value = value

    def __set_star_cloak_type(self, material, original_material_name):
        for star_cloak_type in StarCloakTypes._member_names_:
            if star_cloak_type.lower() in original_material_name.lower():
                vfx_shader_node = material.node_tree.nodes.get(self.shader_node_names.VFX_SHADER)
                vfx_shader_node.inputs.get(self.shader_node_names.STAR_CLOAK_TYPE).default_value = getattr(StarCloakTypes, star_cloak_type).value

    def create_face_material(self, shader_material_names: ShaderMaterialNames, material_name):
        face_material = bpy.data.materials.get(material_name)
        if not face_material:
            face_template = bpy.data.materials.get(shader_material_names.FACE)
            if face_template:
                face_material = face_template.copy()
                face_material.name = material_name
                face_material.use_fake_user = True
        return face_material

    def create_body_material(self, shader_material_names: ShaderMaterialNames, material_name):
        body_material = bpy.data.materials.get(material_name)
        if not body_material:
            body_material = bpy.data.materials.get(shader_material_names.BODY).copy()
            body_material.name = material_name
            body_material.use_fake_user = True
        return body_material

    def create_hair_material(self, shader_material_names: ShaderMaterialNames, material_name):
        hair_material = bpy.data.materials.get(material_name)
        if not hair_material:
            hair_material = bpy.data.materials.get(shader_material_names.HAIR).copy()
            hair_material.name = material_name
            hair_material.use_fake_user = True
        return hair_material

    def create_glass_material(self, shader_material_names: ShaderMaterialNames, material_name):
        glass_material = bpy.data.materials.get(material_name)
        vfx_template_material = bpy.data.materials.get(shader_material_names.VFX)
        if vfx_template_material and not glass_material:
            glass_material = vfx_template_material.copy()
            glass_material.name = material_name
            glass_material.use_fake_user = True
        return glass_material

    '''
    This method was used for V1 shader and should NOT be used for V2 shader because the group name is different.
    The intent was purely to have separate shader nodes and matching the name to the material.
    This does not seem necessary. Haven't checked if there's a performance impact
    '''
    def __clone_shader_node_and_rename(self, material, mesh_body_part_name):
        new_shader_node_tree = material.node_tree.nodes.get('Group.001').node_tree.copy()
        new_shader_node_tree.name = f'miHoYo - Genshin {mesh_body_part_name}'
        return new_shader_node_tree


class HonkaiStarRailDefaultMaterialReplacer(GameDefaultMaterialReplacer):
    MESH_IGNORE_LIST = [
        'Face_Mask'
    ]

    def __init__(self, blender_operator, context, material_names: ShaderMaterialNames):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context
        self.shader_material_names = material_names

    def replace_default_materials(self):
        meshes = [mesh for mesh in bpy.context.scene.objects if mesh.type == 'MESH' and mesh.name not in self.MESH_IGNORE_LIST]

        for mesh in meshes:
            for material_slot in mesh.material_slots:
                material_name = material_slot.name
                
                if material_name.startswith(self.shader_material_names.MATERIAL_PREFIX):
                    continue

                mesh_body_part_name = self.find_body_part_name(material_name)

                # Another hacky-solution, some characters only have a "Body" material, but the shader materials
                # only have Body1, Body2 and Body_A. Should request Shader to have a "Body" material
                # Some characters have a mismatch between Texture and Material Data too... (Body_Color_A and Body)
                # Checklist:
                # 1. Materials
                # 2. Textures
                # 3. Material Data
                # The best fix would be to create a "Body" material via code in case the shader is updated to have the same
                if mesh_body_part_name == 'Body':
                    body_material = self.create_body_material(mesh, self.shader_material_names.BODY)
                    material_name = body_material.name
                elif mesh_body_part_name == 'Body1':  # for StellarToon
                    body_material = self.create_body_material(mesh, self.shader_material_names.BODY1)
                    material_name = body_material.name
                elif mesh_body_part_name == 'Body2':  # for StellarToon
                    body_material = self.create_body_material(mesh, self.shader_material_names.BODY2)
                    material_name = body_material.name
                elif mesh_body_part_name == 'Body3':
                    body_material = self.create_body_material(mesh, self.shader_material_names.BODY3)
                    material_name = body_material.name
                elif mesh_body_part_name ==  'Body_Trans' or mesh_body_part_name == 'Mat_Trans':
                    body_material = self.create_body_trans_material(mesh, self.shader_material_names.BODY_TRANS) 
                    mesh_body_part_name = 'Body_Trans'
                    material_name = body_material.name
                elif mesh_body_part_name ==  'Body2_Trans':
                    body_material = self.create_body_trans_material(mesh, self.shader_material_names.BODY2_TRANS) 
                    material_name = body_material.name
                elif mesh_body_part_name == 'EyeShadow':
                    eyeshadow_material = self.create_body_material(mesh, self.shader_material_names.EYESHADOW)
                    material_name = eyeshadow_material.name
                elif mesh_body_part_name == 'Face':
                    face_material = self.create_body_material(mesh, self.shader_material_names.FACE)
                    material_name = face_material.name
                elif 'Coat' in mesh_body_part_name:
                    body_material = self.create_body_material(mesh, self.shader_material_names.COAT)
                    material_name = body_material.name
                elif 'Weapon' in mesh_body_part_name:
                    weapon_material = self.create_weapon_materials(mesh_body_part_name)
                    material_name = weapon_material.name
                elif 'Handbag' in mesh_body_part_name:
                    handbag_material = self.create_weapon_materials(mesh_body_part_name)
                    material_name = handbag_material.name
                elif 'Kendama' in mesh_body_part_name:
                    handbag_material = self.create_weapon_materials(mesh_body_part_name)
                    material_name = handbag_material.name
                else:  # Fallback, best guess attempt by creating a Body-type material for the unknown material body part
                    material_name = f'{self.shader_material_names.MATERIAL_PREFIX}{mesh_body_part_name}'
                    self.create_body_material(mesh, material_name)

                honkai_star_rail_material = bpy.data.materials.get(
                    f'{self.shader_material_names.MATERIAL_PREFIX}{mesh_body_part_name}'
                )

                if honkai_star_rail_material:
                    material_slot.material = honkai_star_rail_material
                else:
                    self.blender_operator.report({'WARNING'}, f'Ignoring unknown mesh body part in character model: {mesh_body_part_name} / Material: {material_name}')
                    continue
        self.blender_operator.report({'INFO'}, 'Replaced default materials with Genshin shader materials...')

    def find_body_part_name(self, material_name):
        expected_format_body_part_name = self.__expected_format_body_part_name_search(material_name)
        naive_search_body_part_name = self.__naive_body_part_name_search(material_name)
        body_part_name = ''

        # If the two are equal, then we're confident that the body part name is correct (pick either)
        # Elif the naive search found none of the expected body part names, return expected format search body part name
        # Else expected format and naive searches do not equal, use the naive search (pulls from list of expected body part names)
        if expected_format_body_part_name == naive_search_body_part_name:
            body_part_name = expected_format_body_part_name
        elif expected_format_body_part_name and not naive_search_body_part_name:
            body_part_name = expected_format_body_part_name
        else:
            return naive_search_body_part_name
        return body_part_name

    '''
    Expected Format Search: Search for body part name at expected location, at the end of the material name (ex. 'Body')
    '''
    def __expected_format_body_part_name_search(self, material_name):
        if material_name.endswith('_S') or material_name.endswith('_D'):
            return material_name.split('_')[-2]
        return material_name.split('_')[-1]

    '''
    Naive Search: Search for body part name in material name
    '''
    def __naive_body_part_name_search(self, material_name):
        EXPECTED_BODY_PART_NAMES = [
            'Hair',
            'Body1',
            'Body2_Trans',
            'Body2',
            'Body3',
            'Body_Trans',
            'Mat_Trans',
            'EyeShadow',
            'Face',
            'Weapon_Trans',
            'Body',  # Important this is last in the list because it could interfere with Body1 and Body2
        ]

        for expected_body_part_name in EXPECTED_BODY_PART_NAMES:
            if expected_body_part_name in material_name:
                return expected_body_part_name

    def create_body_material(self, mesh, material_name):
        body_material = bpy.data.materials.get(material_name)
        if not body_material:
            body_material = bpy.data.materials.get(self.shader_material_names.BODY1).copy()
            body_material.name = material_name
            body_material.use_fake_user = True
        return body_material

    def create_body_trans_material(self, mesh, material_name):
        body_material = bpy.data.materials.get(material_name)
        if not body_material:
            body_material = bpy.data.materials.get(self.shader_material_names.BODY_TRANS).copy()
            body_material.name = material_name
            body_material.use_fake_user = True
        return body_material

    def create_weapon_materials(self, mesh_body_part_name):
        weapon_material_name = \
            f'{self.shader_material_names.MATERIAL_PREFIX}{mesh_body_part_name}' if \
            mesh_body_part_name == 'Weapon01' or \
            mesh_body_part_name == 'Weapon02' or \
            mesh_body_part_name == 'Weapon1' or \
            mesh_body_part_name == 'Weapon_Trans' or \
            mesh_body_part_name == 'Handbag' or \
            mesh_body_part_name == 'Kendama' else \
            f'{self.shader_material_names.WEAPON}'
        weapon_material = bpy.data.materials.get(weapon_material_name)

        if not weapon_material:
            weapon_material = bpy.data.materials.get(f'{self.shader_material_names.WEAPON}').copy()
            weapon_material.name = weapon_material_name
            weapon_material.use_fake_user = True
        return weapon_material


class StellarToonDefaultMaterialReplacer(HonkaiStarRailDefaultMaterialReplacer):
    MESH_IGNORE_LIST = [
        'Face_Mask'
    ]

    ENABLE_TRANSPARENCY = 'Enable Transparency'

    def __init__(self, blender_operator, context, material_names: ShaderMaterialNames):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context
        self.shader_material_names = material_names

    def replace_default_materials(self):
        super().replace_default_materials()

    def create_body_material(self, mesh, material_name):
        body_material = bpy.data.materials.get(material_name)
        if not body_material:
            body_material = bpy.data.materials.get(self.shader_material_names.BASE).copy()
            body_material.name = material_name
            body_material.use_fake_user = True
        return body_material

    def create_body_trans_material(self, mesh, material_name):
        body_material = bpy.data.materials.get(material_name)
        if not body_material:
            body_material = bpy.data.materials.get(self.shader_material_names.BASE).copy()
            body_material.name = material_name
            body_material.use_fake_user = True
        body_material.node_tree.nodes.get(StellarToonShaderNodeNames.BODY_SHADER).inputs.get(self.ENABLE_TRANSPARENCY).default_value = 1.0
        return body_material

    def create_weapon_materials(self, mesh_body_part_name):
        weapon_material = super().create_weapon_materials(mesh_body_part_name)
        if self.shader_material_names.WEAPON_TRANS in weapon_material.name:
            weapon_material.node_tree.nodes.get(StellarToonShaderNodeNames.MAIN_SHADER).inputs.get(self.ENABLE_TRANSPARENCY).default_value = 1.0
        return weapon_material


class PunishingGrayRavenDefaultMaterialReplacer(GameDefaultMaterialReplacer):
    MESH_IGNORE_LIST = []

    def __init__(self, blender_operator, context):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context

    def replace_default_materials(self):
        meshes = [mesh for mesh in bpy.context.scene.objects if mesh.type == 'MESH' and mesh.name not in self.MESH_IGNORE_LIST]

        for mesh in meshes:
            for material_slot in mesh.material_slots:
                material_name = material_slot.name
                
                if material_name.startswith(JaredNytsPunishingGrayRavenShaderMaterialNames.MATERIAL_PREFIX):
                    continue

                material_identifier_service = PunishingGrayRavenMaterialIdentifierService()
                mesh_body_part_name = material_identifier_service.get_body_part_name(material_name) or \
                    self.find_body_part_name(material_name)  # If in different naming schema, fallback to best guess mode
                mesh_body_part_name = \
                    material_identifier_service.get_body_part_name_of_shared_material(material_name) or \
                    mesh_body_part_name
                if 'Face' in mesh_body_part_name:  # 6.Karenina_Ember (material w/ Face in it, but no called just Face)
                    mesh_body_part_name = 'Face'
                if 'OL' in mesh_body_part_name:  # 9S (Generic), Bianca_Veritas (Ink-lit Hermit)
                    mesh_body_part_name = mesh_body_part_name.replace('OL', '')

                if mesh_body_part_name and 'Alpha' not in mesh_body_part_name:
                    material_type = JaredNytsPunishingGrayRavenShaderMaterialNames.HAIR if 'Hair' in mesh_body_part_name else \
                        JaredNytsPunishingGrayRavenShaderMaterialNames.MAIN
                    material_name = f'{JaredNytsPunishingGrayRavenShaderMaterialNames.MATERIAL_PREFIX}{mesh_body_part_name}'
                    self.create_main_material(mesh, material_type, material_name)
                elif mesh_body_part_name and 'Alpha' in mesh_body_part_name:
                    material_name = JaredNytsPunishingGrayRavenShaderMaterialNames.ALPHA
                    mesh_body_part_name = 'Alpha'
                else:
                    self.blender_operator.report({'WARNING'}, f'Ignoring unknown mesh body part in character model: {mesh_body_part_name} / Material: {material_name}')
                    continue

                punishing_gray_raven_material = bpy.data.materials.get(
                    f'{JaredNytsPunishingGrayRavenShaderMaterialNames.MATERIAL_PREFIX}{mesh_body_part_name}'
                )

                if punishing_gray_raven_material:
                    material_slot.material = punishing_gray_raven_material
                else:
                    self.blender_operator.report({'WARNING'}, f'Ignoring unknown mesh body part in character model: {mesh_body_part_name} / Material: {material_name}')
                    continue
        self.blender_operator.report({'INFO'}, 'Replaced default materials with Genshin shader materials...')

    def find_body_part_name(self, material_name):
        expected_format_body_part_name = self.__expected_format_body_part_name_search(material_name)
        naive_search_body_part_name = self.__naive_body_part_name_search(material_name)
        body_part_name = ''

        # If the two are equal, then we're confident that the body part name is correct (pick either)
        # Elif the naive search found none of the expected body part names, return expected format search body part name
        # Else expected format and naive searches do not equal, use the naive search (pulls from list of expected body part names)
        if expected_format_body_part_name == naive_search_body_part_name:
            body_part_name = expected_format_body_part_name
        elif expected_format_body_part_name and not naive_search_body_part_name:
            body_part_name = expected_format_body_part_name
        else:
            return naive_search_body_part_name
        return body_part_name

    '''
    Expected Format Search: Search for body part name at expected location, at the end of the material name (ex. 'Body')
    '''
    def __expected_format_body_part_name_search(self, material_name):
        armature =  [object for object in bpy.data.objects if object.type == 'ARMATURE'][0]
        return material_name.split(armature.name)[-1]

    '''
    Naive Search: Search for body part name in material name
    '''
    def __naive_body_part_name_search(self, material_name):
        EXPECTED_BODY_PART_NAMES = [
            'Alpha',
            'Alpha01',
            'Alpha02',
            'Upper',
            'Down',
            'Eye',
            'Face',
            'Cloth01',
            'Cloth02',
            'Hair01',
            'Hair02',
            'Mantilla',
            'Pipe',
            'Weapon',
            'Cloth',
            'Hair',
            'Body',  # Default to Body last
        ]

        for expected_body_part_name in EXPECTED_BODY_PART_NAMES:
            if expected_body_part_name in material_name:
                return expected_body_part_name

    def create_main_material(self, mesh, material_type: ShaderMaterialNames, material_name):
        body_material = bpy.data.materials.get(material_name)
        if not body_material:
            body_material = bpy.data.materials.get(material_type).copy()
            body_material.name = material_name
            body_material.use_fake_user = True
        return body_material


class ZenlessZoneZeroDefaultMaterialReplacer(GameDefaultMaterialReplacer):
    def __init__(self, blender_operator, context):
        self.blender_operator = blender_operator
        self.context = context

    def replace_default_materials(self):
        meshes = [mesh for mesh in bpy.context.scene.objects if mesh.type == 'MESH']

        for mesh in meshes:
            if len(mesh.material_slots) == 0:
                mesh.data.materials.append(None)

            for slot in mesh.material_slots:
                mat = slot.material
                matname = mat.name.lower() if mat else mesh.name.lower()

                if mat and mat.name.startswith("ZZZ Shader"):
                    continue

                target_mat_name = None
                if "hair" in matname:
                    target_mat_name = "ZZZ Shader Hair"
                elif "eyebrow" in matname or "brow" in matname or "眉" in matname:
                    target_mat_name = "ZZZ Shader Face"
                elif "eyehighlight" in matname or "highlight" in matname:
                    target_mat_name = "ZZZ Shader EyeHighlights" if bpy.data.materials.get("ZZZ Shader EyeHighlights") else "ZZZ Shader Face"
                elif "eye" in matname and matname != "eye transparent":
                    target_mat_name = "ZZZ Shader Eye" if bpy.data.materials.get("ZZZ Shader Eye") else "ZZZ Shader Face"
                elif "face" in matname:
                    target_mat_name = "ZZZ Shader Face"
                elif "body" in matname or "leg" in matname or "tail" in matname:
                    if "leg" in matname or "tail" in matname:
                        target_mat_name = "ZZZ Shader Body3/Leg"
                    elif "body 2" in matname or "body2" in matname or "body_2" in matname:
                        target_mat_name = "ZZZ Shader Body 2"
                    elif "body3" in matname or "body3/leg" in matname or "body_3" in matname or "body 3" in matname:
                        target_mat_name = "ZZZ Shader Body3/Leg"
                    else:
                        target_mat_name = "ZZZ Shader Body"
                elif "weapon" in matname or "wpn" in matname or "equip" in matname or "sword" in matname or "blade" in matname or "spear" in matname or "lance" in matname or "gun" in matname or "prop" in matname:
                    if "weapon 2" in matname or "weapon2" in matname or "weapon_2" in matname or "map2" in matname:
                        target_mat_name = "ZZZ Shader Weapon 2" if bpy.data.materials.get("ZZZ Shader Weapon 2") else "ZZZ Shader Weapon"
                    else:
                        target_mat_name = "ZZZ Shader Weapon"

                if target_mat_name:
                    template_mat = bpy.data.materials.get(target_mat_name)
                    if template_mat:
                        new_mat = template_mat.copy()
                        name_base = mat.name if mat else mesh.name
                        new_mat.name = f"ZZZ Shader {name_base}"
                        new_mat.use_fake_user = True
                        slot.material = new_mat

        # Fallback: Ensure any weapon mesh object with empty material slots gets assigned a valid ZZZ Weapon material
        weapon_mats = [m for m in bpy.data.materials if m.name.startswith("ZZZ Shader") and "weapon" in m.name.lower()]
        main_weapon_mat = weapon_mats[0] if weapon_mats else bpy.data.materials.get("ZZZ Shader Weapon")

        for mesh in meshes:
            m_lower = mesh.name.lower()
            if any(k in m_lower for k in ["weapon", "wpn", "equip", "sword", "blade", "spear", "lance", "gun", "prop"]):
                for slot in mesh.material_slots:
                    if not slot.material and main_weapon_mat:
                        slot.material = main_weapon_mat

        self.blender_operator.report({'INFO'}, 'Replaced default materials with ZZZ shader materials...')


def find_nte_texture_for_material(mat_name, tex_type, image_files):
    name_lower = mat_name.lower()

    def matches_type(f):
        flow = f.lower()
        if tex_type == 'd':
            return any(k in flow for k in ['_d.', '_d_', '_d1', '_d2', '_diff', '_color', '_base', '_albedo'])
        elif tex_type == 'n':
            return any(k in flow for k in ['_n.', '_n_', '_n1', '_n2', '_norm', '_normal'])
        elif tex_type == 'm':
            return any(k in flow for k in ['_m.', '_m_', '_m1', '_m2', '_mask', '_lightmap'])
        elif tex_type == 'id':
            return any(k in flow for k in ['_id.', '_id_', '_id1', '_id2', '_idmap'])
        elif tex_type == 'r':
            return any(k in flow for k in ['_r.', '_r_', '_r1', '_r2', '_rim'])
        return True

    is_eye_mat = any(k in name_lower for k in ['eye', '目', 'iris', 'pupil', 'eyelash', 'eyebrow', '眉毛', '睫毛'])

    def is_eye_texture(f):
        flow = f.lower()
        return any(k in flow for k in ['eye', 'eyes', 'bantou', '目', '睫毛', '眉毛', 'eyelash', 'eyebrow'])

    if 'hair' in name_lower or 'pelo' in name_lower or '发' in name_lower:
        sub_idx = '02' if ('02' in name_lower or '2' in name_lower or '后发' in name_lower) else '01'
        candidates = [f for f in image_files if 'hair' in f.lower() and matches_type(f) and (sub_idx in f.lower() or f'_{int(sub_idx)}_' in f.lower() or f'_{int(sub_idx)}.' in f.lower())]
        if not candidates:
            candidates = [f for f in image_files if 'hair' in f.lower() and matches_type(f)]
        if candidates:
            return candidates[0]

    if 'face' in name_lower or 'cara' in name_lower or '面' in name_lower or 'head' in name_lower:
        candidates = [f for f in image_files if 'face' in f.lower() and matches_type(f)]
        specific_candidates = [f for f in candidates if not any(k in f.lower() for k in ['common', 'touming', 'default', 'dummy', 'transparent'])]
        if specific_candidates:
            return specific_candidates[0]
        if candidates:
            return candidates[0]

    if any(k in name_lower for k in ['gaoguang', 'hi', 'high', 'bantou']):
        candidates = [f for f in image_files if 'face' in f.lower() and matches_type(f)]
        specific_candidates = [f for f in candidates if not any(k in f.lower() for k in ['common', 'touming', 'default', 'dummy', 'transparent', 'bantou'])]
        if specific_candidates:
            return specific_candidates[0]
        if candidates:
            return candidates[0]

    if is_eye_mat:
        candidates = [f for f in image_files if ('eyes' in f.lower() or 'eye_' in f.lower() or 'eye.' in f.lower() or 'eye' in f.lower()) and matches_type(f)]
        specific_candidates = [f for f in candidates if not any(k in f.lower() for k in ['touming', 'common', 'default', 'dummy', 'transparent'])]
        if specific_candidates:
            return specific_candidates[0]
        if not candidates:
            candidates = [f for f in image_files if 'eye' in f.lower()]
            specific_candidates = [f for f in candidates if not any(k in f.lower() for k in ['touming', 'common', 'default', 'dummy', 'transparent'])]
            if specific_candidates:
                return specific_candidates[0]
        if candidates:
            return candidates[0]

    material_noise_tokens = ['player', '075', '019', 'oneiroi', 'oneir', 'mint', 'skin', 'lod0', 'skeleton', 'nte', 'shader', 'mi', 'mat', 'chastener']

    def find_by_material_name():
        name_tokens = [p for p in name_lower.replace('-', '_').replace('.', '_').split('_') if len(p) >= 3 and p.isalnum() and p not in material_noise_tokens]
        if not name_tokens:
            return None
        best_file = None
        best_score = 0
        for f in image_files:
            if not matches_type(f) or (not is_eye_mat and is_eye_texture(f)):
                continue
            fnorm = ''.join(ch for ch in f.lower() if ch.isalnum())
            score = sum(1 for t in name_tokens if t in fnorm)
            if score > best_score:
                best_score = score
                best_file = f
        return best_file if best_score > 0 else None

    material_name_match = find_by_material_name()
    if material_name_match:
        return material_name_match

    if any(k in name_lower for k in ['down', '02', '_2', 'bottom', 'skirt', 'leg']):
        candidates = [f for f in image_files if ('_02_' in f.lower() or '_2_' in f.lower() or 'down' in f.lower() or 'body2' in f.lower() or 'cloth' in f.lower() or 'clothing' in f.lower() or '衣服' in f.lower()) and matches_type(f)]
        if not candidates:
            candidates = [f for f in image_files if '_02_' in f.lower() or '_2_' in f.lower()]
        if candidates:
            return candidates[0]

    if any(k in name_lower for k in ['up', '01', '_1', 'top', 'upper', 'body', 'skin', 'chastener_1']):
        candidates = [f for f in image_files if ('_01_' in f.lower() or '_1_' in f.lower() or 'up' in f.lower() or 'cloth' in f.lower() or 'clothing' in f.lower() or '衣服' in f.lower()) and matches_type(f)]
        if not candidates:
            candidates = [f for f in image_files if '_01_' in f.lower() or '_1_' in f.lower()]
        if candidates:
            return candidates[0]

    candidates = [f for f in image_files if matches_type(f) and (is_eye_mat or not is_eye_texture(f))]
    return candidates[0] if candidates else (image_files[0] if image_files else None)


def find_nte_body_texture_by_material_name(mat_name_lower, type_keys, image_files):
    material_noise_tokens = ['player', '075', '019', '001', 'oneiroi', 'oneir', 'mint', 'skin', 'lod0', 'skeleton', 'nte', 'shader', 'mi', 'mat', 'chastener']
    name_tokens = [p for p in mat_name_lower.replace('-', '_').replace('.', '_').split('_') if len(p) >= 3 and p.isalnum() and p not in material_noise_tokens]
    if not name_tokens:
        return None
    best_file = None
    best_score = 0
    for f in image_files:
        if not any(tk in f.lower() for tk in type_keys):
            continue
        if any(k in f.lower() for k in ['hair', 'face', 'eye', 'eyes', 'bantou', 'gaoguang', '睫毛', '眉毛']):
            continue
        fnorm = ''.join(ch for ch in f.lower() if ch.isalnum())
        score = sum(1 for t in name_tokens if t in fnorm)
        if score > best_score:
            best_score = score
            best_file = f
    return best_file if best_score > 0 else None


def replace_template_image_node(tex_node, image_files, folder, slot_mat_name=""):
    if not tex_node.image:
        return

    old_img_name = tex_node.image.name.lower()
    mat_name_lower = slot_mat_name.lower()
    replacement_file = None

    hair_sub_idx = '01'
    if any(k in mat_name_lower for k in ['hair_2', 'hair_02', 'hair2', '后发', 'back']):
        hair_sub_idx = '02'
    elif any(k in mat_name_lower for k in ['hair_3', 'hair_03', 'hair3']):
        hair_sub_idx = '03'
    elif '02' in old_img_name or '2' in old_img_name:
        hair_sub_idx = '02'

    if any(fk in mat_name_lower for fk in ['面部因子', 'face factor', 'face_factor']):
        is_r_node = any(rk in old_img_name for rk in ['_r.', '_r_', 'r_1', 'r_2', 'face_r', 'ramp', 'blush'])
        is_m_node = any(mk in old_img_name for mk in ['_m.', '_m_', 'm_1', 'm_2', 'face_m', '_mask'])

        if not is_r_node and not is_m_node:
            if getattr(tex_node, 'location', None) and tex_node.location.y < -50:
                is_r_node = True
            else:
                is_m_node = True

        if is_r_node and not is_m_node:
            candidates = [f for f in image_files if 'face' in f.lower() and any(rk in f.lower() for rk in ['_r.', '_r_', '_r1', '_r_1', '_ramp', 'face_r', 'blush'])]
            specific_candidates = [f for f in candidates if not any(k in f.lower() for k in ['common', 'touming', 'default', 'dummy', 'transparent', 'bantou'])]
            if specific_candidates:
                replacement_file = specific_candidates[0]
            elif candidates:
                replacement_file = candidates[0]
        else:
            candidates = [f for f in image_files if 'face' in f.lower() and ('_m' in f.lower() or 'm_' in f.lower() or '_mask' in f.lower() or 'm.' in f.lower())]
            specific_candidates = [f for f in candidates if not any(k in f.lower() for k in ['common', 'touming', 'default', 'dummy', 'transparent', 'bantou'])]
            if specific_candidates:
                replacement_file = specific_candidates[0]
            elif candidates:
                replacement_file = candidates[0]

    elif any(k in old_img_name for k in ['ramp', 'night_dusk', 'srgb']):
        clean_old_base = old_img_name.split('.')[0].replace('.001', '').replace('.002', '').strip()
        exact_match = next((f for f in image_files if clean_old_base in f.lower() or f.lower().split('.')[0] == clean_old_base), None)
        if exact_match:
            replacement_file = exact_match
        else:
            white_candidate = next((f for f in image_files if 't_srgb_white' in f.lower() or 'srgb_white' in f.lower() or ('srgb' in f.lower() and 'white' in f.lower())), None)
            if white_candidate:
                replacement_file = white_candidate
            else:
                ramp_candidates = [f for f in image_files if 't_srgb' in f.lower() or 'srgb' in f.lower() or 'ramp' in f.lower()]
                if ramp_candidates:
                    replacement_file = ramp_candidates[0]

    elif any(k in old_img_name for k in ['matcap', 'silk']):
        clean_old_base = old_img_name.split('.')[0].replace('.001', '').replace('.002', '').strip()
        exact_match = next((f for f in image_files if clean_old_base in f.lower() or f.lower().split('.')[0] == clean_old_base), None)
        if exact_match:
            replacement_file = exact_match
        else:
            matcap_candidates = [f for f in image_files if 'matcap' in f.lower() or 'silk' in f.lower()]
            if matcap_candidates:
                replacement_file = matcap_candidates[0]

    elif 'hair' in old_img_name and any(dk in old_img_name for dk in ['_d.', '_d_', '_d1', '_d2', '_diff', 'd_0', 'd_1', 'd_2']):
        candidates = [f for f in image_files if 'hair' in f.lower() and ('_d' in f.lower() or 'd_' in f.lower()) and hair_sub_idx in f.lower()]
        if not candidates:
            candidates = [f for f in image_files if 'hair' in f.lower() and ('_d' in f.lower() or 'd_' in f.lower())]
        if candidates:
            replacement_file = candidates[0]

    elif 'hair' in old_img_name and any(mk in old_img_name for mk in ['_m.', '_m_', '_m1', '_m2', '_mask', 'm_0', 'm_1', 'm_2']):
        candidates = [f for f in image_files if 'hair' in f.lower() and ('_m' in f.lower() or 'm_' in f.lower()) and hair_sub_idx in f.lower()]
        if not candidates:
            candidates = [f for f in image_files if 'hair' in f.lower() and ('_m' in f.lower() or 'm_' in f.lower())]
        if candidates:
            replacement_file = candidates[0]

    elif 'hair' in old_img_name and any(nk in old_img_name for nk in ['_n.', '_n_', '_n1', '_n2', '_norm', 'n_0', 'n_1', 'n_2']):
        candidates = [f for f in image_files if 'hair' in f.lower() and ('_n' in f.lower() or 'n_' in f.lower()) and hair_sub_idx in f.lower()]
        if not candidates:
            candidates = [f for f in image_files if 'hair' in f.lower() and ('_n' in f.lower() or 'n_' in f.lower())]
        if candidates:
            replacement_file = candidates[0]

    elif 'face' in old_img_name and any(rk in old_img_name for rk in ['_r.', '_r_', '_r1', '_r_1', '_ramp', 'face_r', 'blush']):
        candidates = [f for f in image_files if 'face' in f.lower() and ('_r' in f.lower() or 'r_' in f.lower() or 'ramp' in f.lower())]
        specific_candidates = [f for f in candidates if 'common' not in f.lower()]
        if specific_candidates:
            replacement_file = specific_candidates[0]
        elif candidates:
            replacement_file = candidates[0]

    elif 'face' in old_img_name and any(mk in old_img_name for mk in ['_m.', '_m_', '_mask']):
        candidates = [f for f in image_files if 'face' in f.lower() and ('_m' in f.lower() or 'm_' in f.lower())]
        specific_candidates = [f for f in candidates if 'common' not in f.lower()]
        if specific_candidates:
            replacement_file = specific_candidates[0]
        elif candidates:
            replacement_file = candidates[0]

    elif 'face' in old_img_name and any(dk in old_img_name for dk in ['_d.', '_d_', '_d1', '_diff', 'd_0']):
        candidates = [f for f in image_files if 'face' in f.lower() and ('_d' in f.lower() or 'd_' in f.lower() or 'd1' in f.lower())]
        specific_candidates = [f for f in candidates if 'common' not in f.lower()]
        if specific_candidates:
            replacement_file = specific_candidates[0]
        elif candidates:
            replacement_file = candidates[0]

    elif any(gk in mat_name_lower for gk in ['gaoguang', '目hi']):
        candidates = [f for f in image_files if 'face' in f.lower() and any(dk in f.lower() for dk in ['_d.', '_d_', '_d1', '_diff', 'd_0'])]
        specific_candidates = [f for f in candidates if not any(k in f.lower() for k in ['common', 'touming', 'default', 'dummy', 'transparent', 'bantou'])]
        if specific_candidates:
            replacement_file = specific_candidates[0]
        elif candidates:
            replacement_file = candidates[0]
        else:
            candidates = [f for f in image_files if 'face' in f.lower()]
            specific_candidates = [f for f in candidates if not any(k in f.lower() for k in ['common', 'touming', 'default', 'dummy', 'transparent', 'bantou'])]
            if specific_candidates:
                replacement_file = specific_candidates[0]
            elif candidates:
                replacement_file = candidates[0]


    elif ('eyes' in old_img_name or 'eye' in old_img_name or 'eye' in mat_name_lower) and not any(ek in mat_name_lower for ek in ['eyelash', 'eyebrow', 'shadow', 'white', '二重', '眉', '睫', 'gaoguang', 'bantou', '目hi']):
        candidates = [
            f for f in image_files
            if ('eyes' in f.lower() or 'eye' in f.lower())
            and not any(bg in f.lower() for bg in ['bantou', 'gaoguang', 'eyelash', 'eyebrow', 'shadow', 'white'])
            and any(dk in f.lower() for dk in ['_d.', '_d_', '_d1', '_diff', 'd_0'])
        ]
        specific_candidates = [f for f in candidates if not any(k in f.lower() for k in ['touming', 'common', 'default', 'dummy', 'transparent'])]
        if specific_candidates:
            replacement_file = specific_candidates[0]
        elif candidates:
            replacement_file = candidates[0]
        if not replacement_file:
            candidates = [
                f for f in image_files
                if ('eyes' in f.lower() or 'eye' in f.lower())
                and not any(bg in f.lower() for bg in ['bantou', 'gaoguang', 'eyelash', 'eyebrow'])
            ]
            specific_candidates = [f for f in candidates if not any(k in f.lower() for k in ['touming', 'common', 'default', 'dummy', 'transparent'])]
            if specific_candidates:
                replacement_file = specific_candidates[0]
            elif candidates:
                replacement_file = candidates[0]



    elif ('mint_01_d' in old_img_name or 'mint_02_d' in old_img_name or any(dk in old_img_name for dk in ['_d.', '_d_', '_d1', '_diff'])) and 'hair' not in old_img_name and 'face' not in old_img_name:
        name_match = find_nte_body_texture_by_material_name(mat_name_lower, ['_d.', '_d_', '_d1', '_diff', 'd_0', 'd_1', 'd_2'], image_files)
        if name_match:
            replacement_file = name_match
        else:
            body_sub_idx = '01'
            if any(k in mat_name_lower for k in ['_2', '_02', 'chastener_2', 'down', 'bottom', 'leg', 'skirt', 'body_2', 'body2']):
                body_sub_idx = '02'
            candidates = [
                f for f in image_files
                if (f'_{body_sub_idx}_' in f.lower() or f'_{int(body_sub_idx)}_' in f.lower() or (body_sub_idx == '02' and 'down' in f.lower()) or (body_sub_idx == '01' and 'up' in f.lower()) or 'cloth' in f.lower() or 'clothing' in f.lower() or '衣服' in f.lower())
                and any(dk in f.lower() for dk in ['_d.', '_d_', '_d1', '_diff', 'd_0', 'd_1', 'd_2'])
                and 'hair' not in f.lower() and 'face' not in f.lower()
            ]
            if not candidates:
                candidates = [
                    f for f in image_files
                    if any(dk in f.lower() for dk in ['_d.', '_d_', '_d1', '_diff'])
                    and 'hair' not in f.lower() and 'face' not in f.lower()
                    and not any(k in f.lower() for k in ['eye', 'eyes', 'bantou', '目', '睫毛', '眉毛', 'eyelash', 'eyebrow'])
                ]
            if candidates:
                replacement_file = candidates[0]

    elif ('mint_01_m' in old_img_name or 'mint_02_m' in old_img_name or any(mk in old_img_name for mk in ['_m.', '_m_', '_mask'])) and 'hair' not in old_img_name and 'face' not in old_img_name:
        name_match = find_nte_body_texture_by_material_name(mat_name_lower, ['_m.', '_m_', '_mask'], image_files)
        if name_match:
            replacement_file = name_match
        else:
            body_sub_idx = '01'
            if any(k in mat_name_lower for k in ['_2', '_02', 'chastener_2', 'down', 'bottom', 'leg', 'skirt', 'body_2', 'body2']):
                body_sub_idx = '02'
            candidates = [
                f for f in image_files
                if (f'_{body_sub_idx}_' in f.lower() or f'_{int(body_sub_idx)}_' in f.lower() or (body_sub_idx == '02' and 'down' in f.lower()) or (body_sub_idx == '01' and 'up' in f.lower()) or 'cloth' in f.lower() or 'clothing' in f.lower() or '衣服' in f.lower())
                and any(mk in f.lower() for mk in ['_m.', '_m_', '_mask'])
                and 'hair' not in f.lower() and 'face' not in f.lower()
                and not any(k in f.lower() for k in ['eye', 'eyes', 'bantou', '目', '睫毛', '眉毛', 'eyelash', 'eyebrow'])
            ]
            if candidates:
                replacement_file = candidates[0]

    elif ('mint_01_n' in old_img_name or 'mint_02_n' in old_img_name or any(nk in old_img_name for nk in ['_n.', '_n_', '_norm'])) and 'hair' not in old_img_name and 'face' not in old_img_name:
        name_match = find_nte_body_texture_by_material_name(mat_name_lower, ['_n.', '_n_', '_norm'], image_files)
        if name_match:
            replacement_file = name_match
        else:
            body_sub_idx = '01'
            if any(k in mat_name_lower for k in ['_2', '_02', 'chastener_2', 'down', 'bottom', 'leg', 'skirt', 'body_2', 'body2']):
                body_sub_idx = '02'
            candidates = [
                f for f in image_files
                if (f'_{body_sub_idx}_' in f.lower() or f'_{int(body_sub_idx)}_' in f.lower() or (body_sub_idx == '02' and 'down' in f.lower()) or (body_sub_idx == '01' and 'up' in f.lower()) or 'cloth' in f.lower() or 'clothing' in f.lower() or '衣服' in f.lower())
                and any(nk in f.lower() for nk in ['_n.', '_n_', '_norm'])
                and 'hair' not in f.lower() and 'face' not in f.lower()
                and not any(k in f.lower() for k in ['eye', 'eyes', 'bantou', '目', '睫毛', '眉毛', 'eyelash', 'eyebrow'])
            ]
            if candidates:
                replacement_file = candidates[0]

    elif ('mint_01_id' in old_img_name or 'mint_02_id' in old_img_name or any(ik in old_img_name for ik in ['_id.', '_id_'])) and 'hair' not in old_img_name and 'face' not in old_img_name:
        name_match = find_nte_body_texture_by_material_name(mat_name_lower, ['_id.', '_id_'], image_files)
        if name_match:
            replacement_file = name_match
        else:
            body_sub_idx = '01'
            if any(k in mat_name_lower for k in ['_2', '_02', 'chastener_2', 'down', 'bottom', 'leg', 'skirt', 'body_2', 'body2']):
                body_sub_idx = '02'
            candidates = [
                f for f in image_files
                if (f'_{body_sub_idx}_' in f.lower() or f'_{int(body_sub_idx)}_' in f.lower() or (body_sub_idx == '02' and 'down' in f.lower()) or (body_sub_idx == '01' and 'up' in f.lower()) or 'cloth' in f.lower() or 'clothing' in f.lower() or '衣服' in f.lower())
                and any(ik in f.lower() for ik in ['_id.', '_id_'])
                and 'hair' not in f.lower() and 'face' not in f.lower()
                and not any(k in f.lower() for k in ['eye', 'eyes', 'bantou', '目', '睫毛', '眉毛', 'eyelash', 'eyebrow'])
            ]
            if candidates:
                replacement_file = candidates[0]

    if replacement_file:
        img_path = os.path.join(folder, replacement_file)
        img = bpy.data.images.load(img_path, check_existing=True)
        try:
            img.alpha_mode = 'CHANNEL_PACKED'
        except Exception:
            pass
        tex_node.image = img


def process_node_tree(node_tree, image_files, folder, slot_mat_name="", visited=None):
    if visited is None:
        visited = set()
    if not node_tree or node_tree in visited:
        return
    visited.add(node_tree)

    for node in node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            replace_template_image_node(node, image_files, folder, slot_mat_name)
        elif node.type == 'GROUP' and node.node_tree:
            sub_mat_name = f"{slot_mat_name} / {node.node_tree.name}" if slot_mat_name else node.node_tree.name
            process_node_tree(node.node_tree, image_files, folder, sub_mat_name, visited)



class NevernessToEvernessDefaultMaterialReplacer(GameDefaultMaterialReplacer):
    def __init__(self, blender_operator, context):
        self.blender_operator = blender_operator
        self.context = context

    def replace_default_materials(self):
        cache_enabled = self.context.window_manager.cache_enabled
        folder = self.blender_operator.file_directory or get_cache(cache_enabled).get(CHARACTER_MODEL_FOLDER_FILE_PATH) or get_active_character_directory()
        image_files = []
        if folder and os.path.isdir(folder):
            try:
                for root, dirs, files in os.walk(folder):
                    for f in files:
                        if f.lower().endswith(('.png', '.tga', '.dds', '.jpg', '.jpeg', '.webp', '.hdr', '.png.001', '.tga.001', '.dds.001')):
                            image_files.append(f)
            except Exception:
                image_files = []

        meshes = [mesh for mesh in bpy.context.scene.objects if mesh.type == 'MESH']

        template_names = [
            'YH-Main-UP', 'YH-Main-DOWN', '前发', '后发', '面', '肌', '目', '目Hi',
            '目影', '目白', '眉毛', '睫毛', '二重', '口', '齿舌', '表情', 'edge_clothes2', 'Dots Stroke'
        ]

        for mesh in meshes:
            if len(mesh.material_slots) == 0:
                new_mat = bpy.data.materials.new(name=mesh.name)
                mesh.data.materials.append(new_mat)

            for slot in mesh.material_slots:
                mat = slot.material
                if not mat:
                    continue

                matname = mat.name.lower()

                if "touming" in matname:
                    mat.use_nodes = True
                    nodes = mat.node_tree.nodes
                    links = mat.node_tree.links
                    nodes.clear()
                    out_node = nodes.new('ShaderNodeOutputMaterial')
                    out_node.location = (300, 0)
                    trans_node = nodes.new('ShaderNodeBsdfTransparent')
                    trans_node.location = (0, 0)
                    links.new(trans_node.outputs['BSDF'], out_node.inputs['Surface'])
                    try:
                        mat.blend_method = 'BLEND'
                    except Exception:
                        pass
                    continue

                if mat.name in template_names or mat.name == '材质球':
                    continue

                template_to_use = None
                is_skin = 0.0

                if any(k in matname for k in ["后发", "back_hair", "hair_2", "hair_02", "hair2", "hair_3", "hair_03", "hair3"]):
                    template_to_use = "后发"
                    is_skin = 1.0
                elif any(k in matname for k in ["前发", "hair", "pelo", "toufa"]):
                    template_to_use = "前发"
                    is_skin = 1.0
                elif any(k in matname for k in ["面", "face", "cara", "head", "mian", "facio", "kao"]):
                    template_to_use = "面"
                    is_skin = 1.0
                elif any(k in matname for k in ["肌", "skin", "piel", "body_skin"]):
                    template_to_use = "肌"
                    is_skin = 1.0
                elif any(k in matname for k in ["目hi", "eye_hi", "gaoguang"]):
                    template_to_use = "目Hi"
                elif any(k in matname for k in ["睫毛", "eyelash"]):
                    template_to_use = "睫毛"
                elif any(k in matname for k in ["眉毛", "eyebrow"]):
                    template_to_use = "眉毛"
                elif any(k in matname for k in ["目影", "eye_shadow", "bantou"]):
                    template_to_use = "目影"

                elif any(k in matname for k in ["目白", "eye_white"]):
                    template_to_use = "目白"
                elif any(k in matname for k in ["二重", "double_eyelid"]):
                    template_to_use = "二重"
                elif any(k in matname for k in ["目", "eye", "iris", "pupil"]):
                    template_to_use = "目"

                elif any(k in matname for k in ["口", "mouth"]):
                    template_to_use = "口"
                elif any(k in matname for k in ["齿舌", "teeth", "tongue"]):
                    template_to_use = "齿舌"
                elif any(k in matname for k in ["down", "bottom", "skirt", "leg", "02"]):
                    template_to_use = "YH-Main-DOWN"
                elif any(k in matname for k in ["edge"]):
                    template_to_use = "edge_clothes2"
                else:
                    template_to_use = "YH-Main-UP"

                template_mat = bpy.data.materials.get(template_to_use)
                if template_mat:
                    new_mat = template_mat.copy()
                    new_mat.name = slot.material.name
                    slot.material = new_mat
                    mat = new_mat

                if mat and mat.use_nodes and mat.node_tree:
                    nodes = mat.node_tree.nodes
                    for node in nodes:
                        if node.type == 'GROUP' and node.node_tree:
                            for inp in node.inputs:
                                if '是否为' in inp.name or '皮肤' in inp.name or inp.name == '是否为皮肤':
                                    inp.default_value = is_skin

                    if folder and image_files:
                        process_node_tree(mat.node_tree, image_files, folder, slot.material.name)

        if folder and image_files:
            for ng_name in ['异环-头发', '异环-身体', '异环-面部', 'Matcap采样']:
                ng = bpy.data.node_groups.get(ng_name)
                if ng:
                    process_node_tree(ng, image_files, folder, "NodeGroup_" + ng_name)

        try:
            bpy.ops.neverness_to_everness.set_up_hair_specular()
        except Exception as ex:
            print(f"Notice: Handled setting up hair specular: {ex}")


        # Clean up any duplicate empties (.001, .002) safely without ReferenceError
        orig_head = bpy.data.objects.get('Head Origin')
        orig_light = bpy.data.objects.get('Light Direction')

        head_dupes = []
        light_dupes = []

        for obj in list(bpy.data.objects):
            try:
                name_low = obj.name.lower()
                has_suffix = '.00' in obj.name or '.01' in obj.name
                if has_suffix:
                    if any(k in name_low for k in ['head origin', 'head forward', 'head up']):
                        if orig_head and obj != orig_head:
                            head_dupes.append(obj)
                    elif any(k in name_low for k in ['light direction', 'sun']):
                        if orig_light and obj != orig_light:
                            light_dupes.append(obj)
            except Exception:
                pass

        for obj in head_dupes:
            try:
                if orig_head:
                    for other in list(bpy.data.objects):
                        try:
                            if getattr(other, 'parent', None) == obj:
                                other.parent = orig_head
                            for con in getattr(other, 'constraints', []):
                                if getattr(con, 'target', None) == obj:
                                    con.target = orig_head
                        except Exception:
                            pass
                bpy.data.objects.remove(obj, do_unlink=True)
            except Exception:
                pass

        for obj in light_dupes:
            try:
                if orig_light:
                    for other in list(bpy.data.objects):
                        try:
                            if getattr(other, 'parent', None) == obj:
                                other.parent = orig_light
                            for con in getattr(other, 'constraints', []):
                                if getattr(con, 'target', None) == obj:
                                    con.target = orig_light
                        except Exception:
                            pass
                bpy.data.objects.remove(obj, do_unlink=True)
            except Exception:
                pass

        self.blender_operator.report({'INFO'}, 'Replaced default materials with NTE template materials from nteTodo.md...')
        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx, 
            self.blender_operator.invoker_type, 
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=self.blender_operator.game_type,
        )


def clean_hair_mesh_slots():
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and obj.data and hasattr(obj.data, "polygons"):
            obj_name_lower = obj.name.lower()
            slot_names = [slot.material.name.lower() for slot in obj.material_slots if slot.material]
            is_hair_mesh = 'hair' in obj_name_lower or any('hair' in s or '头' in s or 'pelo' in s for s in slot_names)
            if is_hair_mesh and len(obj.material_slots) >= 2:
                for p in obj.data.polygons:
                    if p.material_index >= 1:
                        p.material_index = 0
                while len(obj.data.materials) > 1:
                    obj.data.materials.pop(index=1)


def clean_face_mesh_slots():
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and obj.data and hasattr(obj.data, "polygons"):
            obj_name_lower = obj.name.lower()
            slot_names = [slot.material.name.lower() for slot in obj.material_slots if slot.material]
            is_face_mesh = 'face' in obj_name_lower or any('face' in s or '面' in s or 'cara' in s or 'head' in s for s in slot_names)
            if is_face_mesh and len(obj.material_slots) >= 2:
                for p in obj.data.polygons:
                    if p.material_index >= 1:
                        p.material_index = 0
                while len(obj.data.materials) > 1:
                    obj.data.materials.pop(index=1)
                try:
                    obj.data.update()
                except Exception:
                    pass


def clean_mesh_slots():
    clean_hair_mesh_slots()
    clean_face_mesh_slots()









