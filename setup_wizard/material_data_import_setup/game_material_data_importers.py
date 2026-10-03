
from abc import ABC, abstractmethod
import json
import os
from pathlib import PurePosixPath
from typing import List, Union
import bpy
from bpy.types import Operator, Context, Material

from setup_wizard.domain.body_hair_ramp_switch_values import BodyHairRampSwitchValues
from setup_wizard.logger import log_function
from setup_wizard.domain.material_data_body_part_to_version_map import body_part_based_on_version_map
from setup_wizard.domain.shader_node_names import ShaderNodeNames, V2_GenshinShaderNodeNames, V3_GenshinShaderNodeNames
from setup_wizard.domain.shader_material import ShaderMaterial
from setup_wizard.domain.shader_identifier_service import GenshinImpactShaders, HonkaiStarRailShaders, ShaderIdentifierService, \
    ShaderIdentifierServiceFactory
from setup_wizard.domain.shader_material_names import JaredNytsPunishingGrayRavenShaderMaterialNames, ShaderMaterialNames, StellarToonShaderMaterialNames, V3_BonnyFestivityGenshinImpactMaterialNames, V2_FestivityGenshinImpactMaterialNames, \
    Nya222HonkaiStarRailShaderMaterialNames
from setup_wizard.domain.character_types import CharacterType
from setup_wizard.domain.shader_material_name_keywords import ShaderMaterialNameKeywords

from setup_wizard.domain.game_types import GameType
from setup_wizard.domain.outline_material_data import OutlineMaterialGroup
from setup_wizard.exceptions import UnsupportedMaterialDataJsonFormatException, UserInputException
from setup_wizard.import_order import CHARACTER_MODEL_FOLDER_FILE_PATH, get_cache, get_active_character_directory
from setup_wizard.material_data_import_setup.material_data_applier import MaterialDataApplier, MaterialDataAppliersFactory
from setup_wizard.parsers.material_data_json_parsers import MaterialDataJsonParser, HoyoStudioMaterialDataJsonParser, \
    UABEMaterialDataJsonParser, UnknownHoyoStudioMaterialDataJsonParser
from setup_wizard.utils.genshin_body_part_deducer import get_monster_body_part_name, get_npc_mesh_body_part_name, \
    get_body_part


class MaterialDataFile:
    def __init__(self, filename):
        self.name = filename


class MaterialDataDirectory:
    def __init__(self, exists, file_path, files):
        self.exists = exists
        self.file_path = file_path
        self.files = files


class GameMaterialDataImporter(ABC):
    shader_node_names: ShaderNodeNames
    material_names: ShaderMaterialNames

    @abstractmethod
    def import_material_data(self):
        raise NotImplementedError

    def apply_material_data(self, body_part: str, material_data_appliers: List[MaterialDataApplier], file):
        for material_data_applier in material_data_appliers:
            try:
                material_data_applier.set_up_mesh_material_data()
                material_data_applier.set_up_outline_material_data(body_part, file)
                material_data_applier.set_up_outline_colors()
                print(f'INFO: Successfully applied material data on {material_data_applier.__class__}')
                break  # Important! If a MaterialDataApplier runs successfully, we don't need to try the next version
            except AttributeError as err:
                print(f'WARNING: {err} on {material_data_applier.__class__}')
                print('WARNING: Falling back and trying next version')
                continue # fallback and try next version
            except KeyError as err:
                print(f'WARNING: {err} on {material_data_applier.__class__}')
                print('WARNING: Falling back and trying next version')
                continue # fallback and try next version

    # Originally a "private" method, but moved to public due to inheriting classes
    def get_material_data_json_parser(self, json_material_data):
        for index, parser_class in enumerate(self.parsers):
            try:
                parser: MaterialDataJsonParser  = parser_class(json_material_data)
                parser.parse()
                return parser
            except AttributeError:
                if index == len(self.parsers) - 1:
                    raise UnsupportedMaterialDataJsonFormatException(self.parsers)

    # TOOD: Refactor into own class?
    @staticmethod
    def open_and_load_json_data(directory_file_path, file):
        with open(f'{directory_file_path}/{file.name}') as fp:
            try:
                json_material_data = json.load(fp)
                return json_material_data
            except UnicodeDecodeError:
                raise Exception(f'Failed to load JSON. Did you select a different type of file? \nFile Selected: "{file.name}"')

    @log_function()
    def find_material_and_outline_material_for_body_part(self, body_part) -> Union[Material, Material, Material]:
        # Order of Selection
        # 1. Target Material selected.
        # 2. Shader Materials not renamed (regular setup).
        # 3. Shader Materials renamed. Search for material.
        searched_materials = [material for material in bpy.data.materials.values() if 
                              body_part in material.name and 
                              (self.material_names.MATERIAL_PREFIX in material.name or
                               self.material_names.MATERIAL_PREFIX_AFTER_RENAME in material.name) and
                              'Outlines' not in material.name
        ] if body_part else []
        is_not_outlines_material = lambda material: not ShaderMaterial(material, self.shader_node_names).is_outlines_material()
        searched_material = next((material for material in searched_materials if is_not_outlines_material(material)), None)
        material: Material = self.material or bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}{body_part}') or searched_material

        # Order of Selection
        # 1. Outline Material selected.
        # 2. Shader Materials not renamed (regular setup).
        # 3. Shader Materials renamed. Search for material.
        searched_outlines_materials = [material for material in bpy.data.materials.values() if 
                                       body_part in material.name and 
                                       (self.material_names.MATERIAL_PREFIX in material.name or
                                        self.material_names.MATERIAL_PREFIX_AFTER_RENAME in material.name) and
                                       ' Outlines' in material.name and
                                       not self.material_names.NIGHT_SOUL_OUTLINES_SUFFIX in material.name
        ] if body_part else []
        searched_night_soul_outlines_materials = [material for material in bpy.data.materials.values() if 
                                       body_part in material.name and 
                                       self.material_names.MATERIAL_PREFIX_AFTER_RENAME in material.name and
                                       self.material_names.NIGHT_SOUL_OUTLINES_SUFFIX in material.name
        ] if body_part else []

        # If outlines could not be found, the material name may be too long.
        # Try searching for the outlines material by specific settings in it.
        is_outlines_material = lambda material: ShaderMaterial(material, self.shader_node_names).is_outlines_material()
        if not searched_outlines_materials:
            searched_outlines_materials = [material for material in searched_materials if is_outlines_material(material)] or []
        searched_outlines_material = next(
            (material for material in searched_outlines_materials if is_outlines_material(material)), None
        )
        is_night_soul_outlines_material = lambda material: ShaderMaterial(material, self.shader_node_names).is_night_soul_outlines_material()
        if not searched_night_soul_outlines_materials:
            searched_night_soul_outlines_materials = [material for material in searched_materials if is_night_soul_outlines_material(material)] or []
            searched_night_soul_outlines_material = next(
                (material for material in searched_outlines_materials if is_night_soul_outlines_material(material)), None
            )

        outlines_material: Material = self.outlines_material or \
            bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}{body_part} Outlines') or \
            searched_outlines_material
        night_soul_outlines_material: Material = self.outlines_material or \
            bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}{body_part} {self.material_names.NIGHT_SOUL_OUTLINES_SUFFIX}') or \
            searched_night_soul_outlines_material

        return (material, outlines_material, night_soul_outlines_material)

    def get_material_data_files(self):
        # Attempt to use the Material or Materials folder in the cached character folder to import material data json
        # It's possible these folders are in the parent folder for characters with skins, however, it's not possible to
        # easily determine which material data json to apply to the character, so in that scenario,
        # pop-up the File Explorer window and ask the user to select material data json files (old flow)
        cache_enabled = self.context.window_manager.cache_enabled
        character_directory = self.blender_operator.file_directory \
            or get_cache(cache_enabled).get(CHARACTER_MODEL_FOLDER_FILE_PATH) \
            or os.path.dirname(self.blender_operator.filepath)
        if character_directory and os.path.basename(character_directory).lower() == 'textures':
            character_directory = os.path.dirname(character_directory)
        character_material_data_directory = os.path.join(character_directory, 'Material') if character_directory else ''
        character_materials_data_directory = os.path.join(character_directory, 'Materials') if character_directory else ''
        
        material_data_directory_exists = False
        material_data_directory = None

        if character_material_data_directory and os.path.isdir(character_material_data_directory):
            material_data_directory_exists = True
            material_data_directory = character_material_data_directory
        elif character_materials_data_directory and os.path.isdir(character_materials_data_directory):
            material_data_directory_exists = True
            material_data_directory = character_materials_data_directory
        elif character_directory and os.path.isdir(character_directory):
            if any(f.endswith('.json') for f in os.listdir(character_directory)):
                material_data_directory_exists = True
                material_data_directory = character_directory
            else:
                for root, dirs, files in os.walk(character_directory):
                    if any(f.endswith('.json') for f in files):
                        material_data_directory_exists = True
                        material_data_directory = root
                        break

        directory_file_path = os.path.dirname(self.blender_operator.filepath) or material_data_directory

        material_data_files = []
        if material_data_directory:
            for filename in os.listdir(material_data_directory):
                if filename.endswith('.json'):
                    material_data_file = MaterialDataFile(filename)
                    material_data_files.append(material_data_file)

        is_targeted_material_data_import = self.material and self.outlines_material
        material_data_files = self.blender_operator.files or (material_data_files if not is_targeted_material_data_import else None)

        material_data_directory = MaterialDataDirectory(
            exists=material_data_directory_exists,
            file_path=directory_file_path,
            files=material_data_files,
        )
        return material_data_directory

    def validate_UI_inputs_for_targeted_material_data_import(self):
        if self.material and not self.outlines_material:
            raise UserInputException(f'\n\n>>> Targeted Material Data Import: Missing "Outlines Material" input')
        elif not self.material and self.outlines_material:
            raise UserInputException(f'\n\n>>> Targeted Material Data Import: Missing "Target Material" input')

    def validate_num_of_file_inputs_for_targeted_material_data_import(self, material_data_files):
        num_of_files = len(material_data_files)
        if self.material and self.outlines_material and num_of_files != 1:
            raise UserInputException(f'\n\n>>> Select only 1 material data file to apply to the material. You selected {num_of_files} material data files to apply on 1 material.')


class GameMaterialDataImporterFactory:
    def create(game_type: GameType, blender_operator: Operator, context: Context, outline_material_group: OutlineMaterialGroup):
        shader_identifier_service: ShaderIdentifierService = ShaderIdentifierServiceFactory.create(game_type)
        shader = shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)
        material_names = shader_identifier_service.get_shader_material_names(game_type, bpy.data.materials, bpy.data.node_groups)
        shader_node_names = shader_identifier_service.get_shader_node_names(shader)

        # Because we inject the GameType via StringProperty, we need to compare using the Enum's name (a string)
        if game_type == GameType.GENSHIN_IMPACT.name:
            return GenshinImpactMaterialDataImporter(blender_operator, context, outline_material_group, material_names, shader_node_names)
        elif game_type == GameType.HONKAI_STAR_RAIL.name:
            return HonkaiStarRailMaterialDataImporter(blender_operator, context, outline_material_group, material_names, shader_node_names)
        elif game_type == GameType.PUNISHING_GRAY_RAVEN.name:
            return PunishingGrayRavenMaterialDataImporter(blender_operator, context, outline_material_group, material_names, shader_node_names)
        elif game_type == GameType.ZENLESS_ZONE_ZERO.name:
            return ZenlessZoneZeroMaterialDataImporter(blender_operator, context, outline_material_group, material_names, shader_node_names)
        elif game_type == GameType.NEVERNESS_TO_EVERNESS.name:
            return NevernessToEvernessMaterialDataImporter(blender_operator, context, outline_material_group, material_names, shader_node_names)
        elif game_type == GameType.WUTHERING_WAVES.name:
            return WutheringWavesMaterialDataImporter(blender_operator, context, outline_material_group, material_names, shader_node_names)
        else:
            raise Exception(f'Unknown {GameType}: {game_type}')



class GenshinImpactMaterialDataImporter(GameMaterialDataImporter):
    WEAPON_NAME_IDENTIFIER = 'Mat'

    def __init__(self, blender_operator, context, outline_material_group: OutlineMaterialGroup, material_names, shader_node_names):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context
        self.parsers = [
            HoyoStudioMaterialDataJsonParser,
            UnknownHoyoStudioMaterialDataJsonParser,
            UABEMaterialDataJsonParser,
        ]
        self.material = outline_material_group.material
        self.outlines_material = outline_material_group.outlines_material
        self.material_names = material_names
        self.shader_node_names: ShaderNodeNames = shader_node_names

    def import_material_data(self):
        self.validate_UI_inputs_for_targeted_material_data_import()
        material_data_directory: MaterialDataDirectory = self.get_material_data_files()

        caller_is_advanced_setup = getattr(self.blender_operator, "setup_mode", "") == 'ADVANCED'
        no_material_data_files = not material_data_directory.exists and \
            (not self.blender_operator.filepath or not self.blender_operator.files)
        if no_material_data_files:
            if caller_is_advanced_setup and not bpy.app.background:
                bpy.ops.genshin.import_material_data(
                    'INVOKE_DEFAULT',
                    next_step_idx=self.blender_operator.next_step_idx, 
                    file_directory=self.blender_operator.file_directory,
                    invoker_type=self.blender_operator.invoker_type,
                    high_level_step_name=self.blender_operator.high_level_step_name,
                    game_type=self.blender_operator.game_type,
                )
                return {'SKIP'}
            print("[SETUP WIZARD] No Material Data JSON files found. Skipping.")
            return {'FINISHED'}

        self.validate_num_of_file_inputs_for_targeted_material_data_import(material_data_directory.files)

        for file in material_data_directory.files:
            body_part = None

            if 'Monster' in file.name:
                expected_body_part_name = PurePosixPath(file.name).stem.split('_')[-2]
                body_part = get_monster_body_part_name(PurePosixPath(file.name).stem.split('_')[-2]) if expected_body_part_name != 'Mat' else get_monster_body_part_name(PurePosixPath(file.name).stem.split('_')[-1])
                character_type = CharacterType.MONSTER
            elif 'NPC' in file.name:
                body_part = get_npc_mesh_body_part_name(PurePosixPath(file.name).stem)
                character_type = CharacterType.NPC
            elif 'Equip' in file.name:
                body_part = 'Body'
                character_type = CharacterType.GI_EQUIPMENT
            elif file.name.endswith('Glass_Mat.json'):
                body_part = 'Glass'
                character_type = CharacterType.UNKNOWN
            elif file.name.endswith('Glass_Eff_Mat.json'):
                body_part = 'Glass_Eff'
                character_type = CharacterType.UNKNOWN
            elif file.name.startswith(ShaderMaterialNameKeywords.SKILLOBJ):
                skillobj_identifier = file.name.split('_')[2]  # WARNING: This is a brittle way to get the identifier
                body_part = f'{ShaderMaterialNameKeywords.SKILLOBJ} {skillobj_identifier}'
                character_type = CharacterType.UNKNOWN
            elif file.name.startswith('AvatarObj') and PurePosixPath(file.name).stem.endswith('_Mat'):
                # Quest object materials (ex. AvatarObj_Ani_Quest_IkhorShackles_01_Mat.json):
                # keep the full object name so each maps to its own dedicated
                # material. Using only the last token ('Mat') would fail to
                # resolve any material and skip the file entirely.
                body_part = PurePosixPath(file.name).stem[:-len('_Mat')]
                character_type = CharacterType.UNKNOWN
            elif file.name.startswith('Eff_'):
                # Effect object materials (ex. Eff_Fresnel_048_NO_00.json):
                # keep the full name so each effect maps to its own dedicated
                # material instead of collapsing to '00'. These transparent
                # effects intentionally get no outline materials (see the 'Eff'
                # outline ignore keyword), so only the main material data is
                # applied for them.
                body_part = PurePosixPath(file.name).stem
                character_type = CharacterType.UNKNOWN
            else:
                stem = PurePosixPath(file.name).stem
                if stem.endswith('_D') or stem.endswith('_S'):
                    body_part = stem.split('_')[-2]
                else:
                    body_part = stem.split('_')[-1]
                character_type = CharacterType.UNKNOWN  # catch-all, tries default material applying behavior

            json_material_data = self.open_and_load_json_data(material_data_directory.file_path, file)
            material_data_parser = self.get_material_data_json_parser(json_material_data)

            material, outlines_material, night_soul_outlines_material = self.find_material_and_outline_material_for_body_part(body_part)
            outline_material_group: OutlineMaterialGroup = OutlineMaterialGroup(material, outlines_material, night_soul_outlines_material)

            # Skirk's Dress2 material data JSON is for her StarCloak
            if body_part == 'Dress2' and 'Skirk' in file.name:
                body_part_based_on_version = body_part_based_on_version_map.get(
                    type(self.material_names),
                    body_part_based_on_version_map.get(self.material_names, 'StarCloak')
                )
                if body_part_based_on_version != body_part:
                    self.__customized_skirk_starcloak_material_data_setup(material_data_parser, character_type, file, body_part_based_on_version)

            if not material:
                self.blender_operator.report({'WARNING'}, \
                    f'Continuing to apply other material data, but: \n'
                    f'* Type: {character_type}\n'
                    f'* Material Data JSON "{file.name}" was selected, but unable to determine material to apply this to.\n'
                    f'* Expected Materials "{self.material_names.MATERIAL_PREFIX}{body_part}" and "{self.material_names.MATERIAL_PREFIX}{body_part} Outlines"')
                continue

            if not outlines_material:
                if file.name.startswith('Eff_'):
                    # Transparent effects intentionally get no outline
                    # materials (see the 'Eff' outline ignore keyword), so
                    # only the main material data is applied for them.
                    print(f'[MATERIAL DATA] No outlines for effect "{file.name}"; applying main material data only.')
                else:
                    self.blender_operator.report({'WARNING'}, \
                        f'Continuing to apply other material data, but: \n'
                        f'* Type: {character_type}\n'
                        f'* Material Data JSON "{file.name}" was selected, but unable to determine outlines material to apply this to.\n'
                        f'* Expected Material "{self.material_names.MATERIAL_PREFIX}{body_part} Outlines"')
                    continue

            shadow_ramp_type_setter = ShadowRampTypeSetter(file, material_data_directory, self.shader_node_names)
            shadow_ramp_type_setter.set_shadow_ramp_type(material)

            material_data_appliers = MaterialDataAppliersFactory.create(
                self.blender_operator.game_type,
                material_data_parser,
                outline_material_group,
                character_type
            )
            self.apply_material_data(body_part, material_data_appliers, file)
        return {'FINISHED'}

    def __customized_skirk_starcloak_material_data_setup(self, material_data_parser, character_type, file, body_part):
        material, outlines_material, night_soul_outlines_material = self.find_material_and_outline_material_for_body_part(body_part)
        if not material or not outlines_material:
            return
        outline_material_group: OutlineMaterialGroup = OutlineMaterialGroup(material, outlines_material, night_soul_outlines_material)

        material_data_appliers = MaterialDataAppliersFactory.create(
            self.blender_operator.game_type,
            material_data_parser,
            outline_material_group,
            character_type
        )
        self.apply_material_data(body_part, material_data_appliers, file)

class ShadowRampTypeSetter:
    def __init__(self, target_file, material_data_directory: MaterialDataDirectory, shader_node_names: ShaderNodeNames):
        self.target_file = target_file
        self.material_data_directory = material_data_directory
        self.shader_node_names = shader_node_names

    def set_shadow_ramp_type(self, shader_material):
        shadow_ramp_type = self.__get_shadow_ramp_type_by_PackedShadowRampTex()
        self.__set_shadow_ramp_type_on_shader_material(shader_material, shadow_ramp_type)

    def __get_shadow_ramp_type_by_PackedShadowRampTex(self):
        material_data_files = [mat_file for mat_file in self.material_data_directory.files if mat_file.name.lower() != self.target_file.name.lower()]

        target_file_json = GenshinImpactMaterialDataImporter.open_and_load_json_data(
            self.material_data_directory.file_path, 
            self.target_file
        )
        target_file_shadow_ramp_pathID = self.__get_shadow_ramp_pathID(target_file_json)

        for material_data_file in material_data_files:
            material_data_json = GenshinImpactMaterialDataImporter.open_and_load_json_data(
                self.material_data_directory.file_path, 
                material_data_file
            )
            shadow_ramp_pathID = self.__get_shadow_ramp_pathID(material_data_json)

            if shadow_ramp_pathID and target_file_shadow_ramp_pathID and shadow_ramp_pathID == target_file_shadow_ramp_pathID:
                return get_body_part(material_data_file)

    def __get_shadow_ramp_pathID(self, material_data_json):
        try:
            return material_data_json.get('m_SavedProperties').get('m_TexEnvs').get('_PackedShadowRampTex').get('m_Texture').get('m_PathID')
        except AttributeError:
            return None

    def __set_shadow_ramp_type_on_shader_material(self, shader_material, shadow_ramp_type):
        body_shader_node = shader_material.node_tree.nodes.get(self.shader_node_names.BODY_SHADER)
        body_hair_ramp_switch_input = body_shader_node.inputs.get(self.shader_node_names.BODY_HAIR_RAMP_SWITCH) if body_shader_node else None

        if body_hair_ramp_switch_input:
            body_hair_ramp_switch_values: BodyHairRampSwitchValues = BodyHairRampSwitchValues(self.shader_node_names)
            self.__set_up_body_hair_ramp_switch_value(body_hair_ramp_switch_input, shadow_ramp_type, body_hair_ramp_switch_values)

    def __set_up_body_hair_ramp_switch_value(self, switch_input, shadow_ramp_type, switch_values: BodyHairRampSwitchValues):
        if type(switch_input) is bpy.types.NodeSocketBool:
            if shadow_ramp_type == 'Hair':
                switch_input.default_value = True
            elif shadow_ramp_type == 'Body':
                switch_input.default_value = False
        else:
            if shadow_ramp_type == 'Hair':  # TODO: Refactor into Enum along side genshin_body_part_deducer.py
                switch_input.default_value = switch_values.HAIR
            elif shadow_ramp_type == 'Body':  # TODO: Refactor into Enum along side genshin_body_part_deducer.py
                switch_input.default_value = switch_values.BODY


class HonkaiStarRailMaterialDataImporter(GameMaterialDataImporter):
    def __init__(self, blender_operator, context, outline_material_group: OutlineMaterialGroup, material_names, shader_node_names: ShaderNodeNames):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context
        self.parsers = [
            HoyoStudioMaterialDataJsonParser,
            UnknownHoyoStudioMaterialDataJsonParser,
            UABEMaterialDataJsonParser,
        ]
        self.material = outline_material_group.material
        self.outlines_material = outline_material_group.outlines_material
        self.material_names = material_names
        self.shader_node_names = shader_node_names

    @staticmethod
    def deduce_hsr_body_part(filename: str) -> str:
        stem = PurePosixPath(filename).stem
        stem_lower = stem.lower()

        if 'eyeshadow' in stem_lower or 'eyespecular' in stem_lower or 'eye_specular' in stem_lower or 'eyestar' in stem_lower:
            return 'EyeShadow'
        if 'facemask' in stem_lower:
            return 'FaceMask'
        if 'hair' in stem_lower:
            return 'Hair'
        if 'face' in stem_lower:
            return 'Face'
        if 'handbag' in stem_lower:
            return 'Handbag'
        if 'kendama' in stem_lower:
            return 'Kendama'
        if 'coat' in stem_lower:
            return 'Coat'

        if 'weapon' in stem_lower or 'wpn' in stem_lower:
            if 'crystal' in stem_lower:
                return 'Weapon_Crystal'
            if 'trans' in stem_lower:
                return 'Weapon_Trans'
            return 'Weapon'

        if 'crystal' in stem_lower:
            return 'Crystal'

        if stem_lower.startswith('eff_') or '_eff_' in stem_lower:
            if '_Mat_' in stem:
                return stem.split('_Mat_')[-1]
            return stem

        if 'body' in stem_lower:
            is_trans = 'trans' in stem_lower
            is_d = stem_lower.endswith(('_d', '_mat_d')) or '_d_' in stem_lower or '_body_d' in stem_lower
            is_s = stem_lower.endswith(('_s', '_mat_s')) or '_s_' in stem_lower or '_body_s' in stem_lower

            if 'body3' in stem_lower:
                return 'Body3'
            if 'body2' in stem_lower:
                if is_trans:
                    return 'Body2_Trans'
                if is_d:
                    return 'Body2_D'
                if is_s:
                    return 'Body2_S'
                return 'Body2'
            if 'body1' in stem_lower:
                if is_d:
                    return 'Body1_D'
                if is_s:
                    return 'Body1_S'
                return 'Body1'

            if is_trans:
                return 'Body_Trans'
            if is_d:
                return 'Body_D'
            if is_s:
                return 'Body_S'
            return 'Body'

        if '_Mat_' in stem:
            part = stem.split('_Mat_')[-1]
            tokens = part.split('_')
            if len(tokens) > 1 and tokens[-1].isdigit():
                part = '_'.join(tokens[:-1])
            if part:
                return part

        parts = stem.split('_')
        return parts[-1] if parts else stem

    def find_hsr_material_and_outlines(self, body_part: str, filename: str):
        mat = self.material
        ol_mat = self.outlines_material

        prefix = getattr(self.material_names, 'MATERIAL_PREFIX', '') or ''
        prefix_after = getattr(self.material_names, 'MATERIAL_PREFIX_AFTER_RENAME', '') or ''

        candidate_mat_names = []
        if body_part in ('Body_D', 'Body_S'):
            candidate_mat_names.extend([
                f'{prefix}{body_part}',
                f'{prefix}Body',
                f'{prefix}Base',
                f'{prefix}Body1',
                f'{prefix_after}{body_part}',
                f'{prefix_after}Body',
                f'{prefix_after}Base',
            ])
        elif body_part == 'Body_Trans':
            candidate_mat_names.extend([
                f'{prefix}Body_Trans',
                f'{prefix}Body2_Trans',
                f'{prefix}Body',
                f'{prefix}Base',
                f'{prefix_after}Body_Trans',
                f'{prefix_after}Body2_Trans',
            ])
        elif body_part in ('Body', 'Base'):
            candidate_mat_names.extend([
                f'{prefix}Body',
                f'{prefix}Base',
                f'{prefix}Body_D',
                f'{prefix}Body1',
                f'{prefix_after}Body',
                f'{prefix_after}Base',
            ])
        elif 'Weapon' in body_part:
            candidate_mat_names.extend([
                f'{prefix}{body_part}',
                f'{prefix}Weapon',
                f'{prefix}Weapon01',
                f'{prefix}Weapon1',
                f'{prefix_after}{body_part}',
                f'{prefix_after}Weapon',
            ])
        elif body_part == 'EyeShadow':
            candidate_mat_names.extend([
                f'{prefix}EyeShadow',
                f'{prefix}Eye_Shadow',
                f'{prefix}Eye',
                f'{prefix_after}EyeShadow',
            ])
        else:
            candidate_mat_names.extend([
                f'{prefix}{body_part}',
                f'{prefix_after}{body_part}',
            ])

        stem = PurePosixPath(filename).stem
        candidate_mat_names.append(f'{prefix}{stem}')
        if '_Mat_' in stem:
            candidate_mat_names.append(f"{prefix}{stem.split('_Mat_')[-1]}")

        # Find mesh material
        if not mat:
            for cand in candidate_mat_names:
                if cand:
                    found = bpy.data.materials.get(cand)
                    if found and not found.name.endswith('Outlines'):
                        mat = found
                        break

        if not mat:
            for m in bpy.data.materials.values():
                if m.name.endswith('Outlines'):
                    continue
                if (prefix and prefix in m.name) or (prefix_after and prefix_after in m.name):
                    if body_part.lower() in m.name.lower():
                        mat = m
                        break

        # Find outline material
        if not ol_mat and mat:
            ol_mat = bpy.data.materials.get(f'{mat.name} Outlines')

        if not ol_mat:
            for cand in candidate_mat_names:
                if cand:
                    found_ol = bpy.data.materials.get(f'{cand} Outlines')
                    if found_ol:
                        ol_mat = found_ol
                        break

        if not ol_mat:
            if 'body' in body_part.lower():
                ol_mat = (bpy.data.materials.get(f'{prefix}Base Outlines') or
                          bpy.data.materials.get(f'{prefix}Outlines') or
                          bpy.data.materials.get(f'{prefix_after}Outlines'))
            elif 'weapon' in body_part.lower():
                ol_mat = (bpy.data.materials.get(f'{prefix}Weapon Outlines') or
                          bpy.data.materials.get(f'{prefix_after}Weapon Outlines'))
            elif body_part == 'Hair':
                ol_mat = (bpy.data.materials.get(f'{prefix}Hair Outlines') or
                          bpy.data.materials.get(f'{prefix_after}Hair Outlines'))
            elif body_part == 'Face':
                ol_mat = (bpy.data.materials.get(f'{prefix}Face Outlines') or
                          bpy.data.materials.get(f'{prefix_after}Face Outlines'))

        if not ol_mat:
            for m in bpy.data.materials.values():
                if 'outlines' in m.name.lower() and ((prefix and prefix in m.name) or (prefix_after and prefix_after in m.name)):
                    if body_part.lower() in m.name.lower():
                        ol_mat = m
                        break

        return (mat, ol_mat, None)

    def import_material_data(self):
        self.validate_UI_inputs_for_targeted_material_data_import()
        material_data_directory: MaterialDataDirectory = self.get_material_data_files()

        caller_is_advanced_setup = self.blender_operator.setup_mode == 'ADVANCED'
        no_material_data_files = not material_data_directory.exists and \
            (not self.blender_operator.filepath or not self.blender_operator.files)
        if caller_is_advanced_setup or no_material_data_files:
            bpy.ops.genshin.import_material_data(
                'INVOKE_DEFAULT',
                next_step_idx=self.blender_operator.next_step_idx, 
                file_directory=self.blender_operator.file_directory,
                invoker_type=self.blender_operator.invoker_type,
                high_level_step_name=self.blender_operator.high_level_step_name,
                game_type=self.blender_operator.game_type,
            )
            return {'SKIP'}

        self.validate_num_of_file_inputs_for_targeted_material_data_import(material_data_directory.files)

        for file in material_data_directory.files:
            body_part = self.deduce_hsr_body_part(file.name)
            character_type = CharacterType.HSR_AVATAR

            material, outlines_material, __ = self.find_hsr_material_and_outlines(body_part, file.name)
            outline_material_group: OutlineMaterialGroup = OutlineMaterialGroup(material, outlines_material)

            if not material and not outlines_material:
                if body_part not in ('FaceMask', 'DefaultMat'):
                    self.blender_operator.report({'WARNING'}, \
                        f'Continuing to apply other material data, but: \n'
                        f'* Type: {character_type}\n'
                        f'* Material Data JSON "{file.name}" was selected, but unable to determine material to apply this to.\n'
                        f'* Expected Materials "{self.material_names.MATERIAL_PREFIX}{body_part}" and "{self.material_names.MATERIAL_PREFIX}{body_part} Outlines"')
                continue

            json_material_data = self.open_and_load_json_data(material_data_directory.file_path, file)
            material_data_parser = self.get_material_data_json_parser(json_material_data)
            material_data_appliers = MaterialDataAppliersFactory.create(
                self.blender_operator.game_type,
                material_data_parser,
                outline_material_group,
                character_type
            )
            self.apply_material_data(body_part, material_data_appliers, file)
        return {'FINISHED'}


# Unused.
class PunishingGrayRavenMaterialDataImporter(GameMaterialDataImporter):
    def __init__(self, blender_operator, context, outline_material_group: OutlineMaterialGroup, material_names, shader_node_names: ShaderNodeNames):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context
        self.parsers = [
            HoyoStudioMaterialDataJsonParser,
            UnknownHoyoStudioMaterialDataJsonParser,
            UABEMaterialDataJsonParser,
        ]
        self.material = outline_material_group.material
        self.outlines_material = outline_material_group.outlines_material
        self.material_names = material_names
        self.shader_node_names = shader_node_names

    def import_material_data(self):
        return {'FINISHED'}


class ZenlessZoneZeroMaterialDataImporter(GameMaterialDataImporter):
    def __init__(self, blender_operator, context, outline_material_group: OutlineMaterialGroup, material_names, shader_node_names: ShaderNodeNames):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context
        self.parsers = [
            HoyoStudioMaterialDataJsonParser,
            UnknownHoyoStudioMaterialDataJsonParser,
            UABEMaterialDataJsonParser,
        ]
        self.material = outline_material_group.material
        self.outlines_material = outline_material_group.outlines_material
        self.material_names = material_names
        self.shader_node_names = shader_node_names

    def import_material_data(self):
        return {'FINISHED'}


class NevernessToEvernessMaterialDataImporter(GameMaterialDataImporter):
    def __init__(self, blender_operator, context, outline_material_group: OutlineMaterialGroup, material_names, shader_node_names: ShaderNodeNames):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context
        self.material = outline_material_group.material
        self.outlines_material = outline_material_group.outlines_material
        self.material_names = material_names
        self.shader_node_names = shader_node_names

    def import_material_data(self):
        if self.material and self.material.use_nodes and self.material.node_tree:
            cache_enabled = self.context.window_manager.cache_enabled
            folder = (
                getattr(self.blender_operator, 'file_directory', None)
                or get_cache(cache_enabled).get(CHARACTER_MODEL_FOLDER_FILE_PATH)
                or get_active_character_directory()
            )
            if folder and os.path.isdir(folder):
                from setup_wizard.utils.nte_json_parser import load_nte_character_data, get_nte_material_data
                try:
                    database = load_nte_character_data(folder)
                    mat_info = get_nte_material_data(self.material.name, database)
                    if mat_info:
                        scalars = mat_info.get("scalars", {})
                        for n in self.material.node_tree.nodes:
                            if n.type == 'GROUP' and n.node_tree:
                                for s_name, s_val in scalars.items():
                                    if s_name in n.inputs and isinstance(s_val, (int, float)):
                                        try:
                                            n.inputs[s_name].default_value = float(s_val)
                                        except Exception:
                                            pass
                except Exception as ex:
                    print(f"[NTE Material Data Importer] Notice: {ex}")
        return {'FINISHED'}


class WutheringWavesMaterialDataImporter(GameMaterialDataImporter):
    def __init__(self, blender_operator, context, outline_material_group: OutlineMaterialGroup, material_names, shader_node_names):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context
        self.parsers = []
        self.material = None
        self.outline_material_group = outline_material_group
        self.material_names = material_names
        self.shader_node_names = shader_node_names

    def import_material_data(self):
        return {'FINISHED'}

