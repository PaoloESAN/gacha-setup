
from abc import ABC, abstractmethod
import json
import os
from pathlib import PurePosixPath
from typing import List, Union
import bpy
from bpy.types import Operator, Context, Material
from mathutils import Vector

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

        outlines_material: Material = (
            self.outlines_material
            or bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}{body_part} Outlines')
            or bpy.data.materials.get(getattr(self.material_names, 'OUTLINES', ''))
            or bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}Outlines')
            or bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX_AFTER_RENAME}Outlines')
            or searched_outlines_material
        )
        if not outlines_material:
            for mat in bpy.data.materials.values():
                m_name = mat.name
                if 'outline' in m_name.lower() and not (getattr(self.material_names, 'NIGHT_SOUL_OUTLINES_SUFFIX', 'Night Soul Outlines') in m_name):
                    outlines_material = mat
                    break
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
            if any(f.endswith('.json') and not f.startswith('._') and not f.startswith('.') for f in os.listdir(character_directory)):
                material_data_directory_exists = True
                material_data_directory = character_directory
            else:
                for root, dirs, files in os.walk(character_directory):
                    if "__MACOSX" in root:
                        continue
                    if any(f.endswith('.json') and not f.startswith('._') and not f.startswith('.') for f in files):
                        material_data_directory_exists = True
                        material_data_directory = root
                        break

        directory_file_path = os.path.dirname(self.blender_operator.filepath) or material_data_directory

        material_data_files = []
        if material_data_directory:
            for filename in os.listdir(material_data_directory):
                if filename.endswith('.json') and not filename.startswith('._') and not filename.startswith('.'):
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
        elif game_type == GameType.HONKAI_IMPACT_3RD.name:
            return HonkaiImpact3rdMaterialDataImporter(blender_operator, context, outline_material_group, material_names, shader_node_names)
        elif game_type == GameType.HONKAI_NEXUS_ANIMA.name:
            from setup_wizard.utils.hna_material_utils import MaterialDataImporter
            return MaterialDataImporter(blender_operator)
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
                stem = PurePosixPath(file.name).stem
                equipment = next((m for m in bpy.data.materials if m.get('_genshin_equipment')
                                  and m.get('_original_material_name') == stem), None)
                if equipment is None and any(m.get('_genshin_equipment') for m in bpy.data.materials):
                    # Alternate weapon skins in the folder must not overwrite
                    # the shared Body template or another equipment material.
                    continue
                body_part = equipment.name.removeprefix(self.material_names.MATERIAL_PREFIX) if equipment else 'Body'
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
            if material and material.get('_genshin_weapon_elements'):
                from setup_wizard.utils.genshin_weapon_elements import find_weapon_outline
                outlines_material = find_weapon_outline(material)
                night_soul_outlines_material = None
                if outlines_material:
                    material['_gi_element_outline'] = outlines_material
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
                if material.get('_genshin_weapon_elements'):
                    pass  # A transparent weapon part intentionally has no outline.
                elif file.name.startswith('Eff_'):
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

        # Apply diffuse fallback to any outline materials in the scene that still have sentinel colors
        for mat in bpy.data.materials:
            if 'outline' in mat.name.lower() and mat.node_tree:
                pt = mat.node_tree.nodes.get(self.shader_node_names.OUTLINES_SHADER) or \
                     mat.node_tree.nodes.get('PrimoToon')
                if not pt:
                    for n in mat.node_tree.nodes:
                        if n.type == 'GROUP' and any(inp.name.startswith('Outline Color') for inp in n.inputs):
                            pt = n
                            break
                if pt:
                    indexed = {}
                    for inp in pt.inputs:
                        if inp.name.startswith('Outline Color'):
                            try:
                                idx = int(inp.name.split('Outline Color')[1].strip())
                                indexed[idx] = inp
                            except Exception:
                                pass
                    if MaterialDataApplier._defaults_match_sentinels(indexed):
                        targets = [indexed[i] for i in (1, 2, 3, 4, 5) if i in indexed]
                        if targets and all(len(list(inp.links)) == 0 for inp in targets):
                            diffuse_node = None
                            for n in mat.node_tree.nodes:
                                if n.type == 'TEX_IMAGE' and 'diffuse' in (n.name + ' ' + (n.label or '')).lower():
                                    diffuse_node = n
                                    break
                            if diffuse_node and not diffuse_node.image:
                                for other_mat in bpy.data.materials:
                                    if other_mat.node_tree and 'outline' not in other_mat.name.lower():
                                        for n in other_mat.node_tree.nodes:
                                            if n.type == 'TEX_IMAGE' and 'diffuse' in (n.name + ' ' + (n.label or '')).lower() and n.image:
                                                diffuse_node.image = n.image
                                                break
                                        if diffuse_node.image:
                                            break
                            if diffuse_node and diffuse_node.image:
                                color_out = diffuse_node.outputs.get('Color') or diffuse_node.outputs[0]
                                color_out.hide = False
                                for inp in targets:
                                    inp.hide = False
                                    for link in list(inp.links):
                                        mat.node_tree.links.remove(link)
                                    mat.node_tree.links.new(color_out, inp)
                                mat[MaterialDataApplier.OUTLINE_DIFFUSE_FALLBACK_TAG] = True

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


class HonkaiImpact3rdMaterialDataImporter(GameMaterialDataImporter):
    def __init__(self, blender_operator, context, outline_material_group: OutlineMaterialGroup, material_names, shader_node_names):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context
        self.parsers = []
        self.material = None
        self.outline_material_group = outline_material_group
        self.material_names = material_names
        self.shader_node_names = shader_node_names

    @staticmethod
    def _extract_props(jdata):
        colors = {}
        floats = {}
        keywords = []
        if not isinstance(jdata, dict):
            return colors, floats, keywords
        kw = jdata.get("m_ShaderKeywords")
        if isinstance(kw, list):
            keywords = [str(x) for x in kw]
        elif isinstance(kw, str):
            keywords = kw.split()

        saved = jdata.get("m_SavedProperties") or {}
        raw_colors = saved.get("m_Colors")
        if isinstance(raw_colors, dict):
            for k, v in raw_colors.items():
                if isinstance(v, dict) and "r" in v:
                    colors[k] = (
                        float(v.get("r", 1.0)),
                        float(v.get("g", 1.0)),
                        float(v.get("b", 1.0)),
                        float(v.get("a", 1.0)),
                    )
        elif isinstance(raw_colors, list):
            for entry in raw_colors:
                if isinstance(entry, dict):
                    k = entry.get("Key") or entry.get("first")
                    v = entry.get("Value") or entry.get("second")
                    if k and isinstance(v, dict) and "r" in v:
                        colors[k] = (
                            float(v.get("r", 1.0)),
                            float(v.get("g", 1.0)),
                            float(v.get("b", 1.0)),
                            float(v.get("a", 1.0)),
                        )

        raw_floats = saved.get("m_Floats")
        if isinstance(raw_floats, dict):
            for k, v in raw_floats.items():
                if isinstance(v, (int, float)):
                    floats[k] = float(v)
        elif isinstance(raw_floats, list):
            for entry in raw_floats:
                if isinstance(entry, dict):
                    k = entry.get("Key") or entry.get("first")
                    v = entry.get("Value") or entry.get("second")
                    if k and isinstance(v, (int, float)):
                        floats[k] = float(v)

        return colors, floats, keywords

    @staticmethod
    def _extract_tex_envs(jdata):
        tex_envs = {}
        if not isinstance(jdata, dict):
            return tex_envs
        saved = jdata.get("m_SavedProperties") or {}
        raw_tex = saved.get("m_TexEnvs")
        tex_items = []
        if isinstance(raw_tex, dict):
            tex_items = list(raw_tex.items())
        elif isinstance(raw_tex, list):
            for entry in raw_tex:
                if isinstance(entry, dict):
                    k = entry.get("Key") or entry.get("first")
                    v = entry.get("Value") or entry.get("second")
                    if k and isinstance(v, dict):
                        tex_items.append((k, v))
        for k, v in tex_items:
            if not isinstance(v, dict):
                continue
            sc = v.get("m_Scale") or {}
            of = v.get("m_Offset") or {}
            tex_ref = v.get("m_Texture") or {}
            sx = float(sc.get("X", sc.get("x", 1.0)))
            sy = float(sc.get("Y", sc.get("y", 1.0)))
            ox = float(of.get("X", of.get("x", 0.0)))
            oy = float(of.get("Y", of.get("y", 0.0)))
            is_null = bool(tex_ref.get("IsNull", False)) or (
                tex_ref.get("m_PathID", 0) == 0 and not tex_ref.get("Name")
            )
            tex_envs[k] = {
                "scale": (sx, sy),
                "offset": (ox, oy),
                "name": str(tex_ref.get("Name") or ""),
                "path_id": tex_ref.get("m_PathID", 0),
                "is_null": is_null,
            }
        return tex_envs

    @staticmethod
    def _ensure_eye_atlas_node_group():
        """Creates or returns the 'HI3 Eye Atlas Controller' ShaderNodeTree.

        Maps an 'Eye Type' index (1..8) and 'Is Left Eye' (0 or 1) to the 8 expression pairs
        of a 4x4 HI3 eye texture sheet:
          - Pair idx = floor(clamp(Eye Type, 1, 8) - 1) in 0..7
          - Column pair (0 or 1) = floor(idx / 4) -> base X = col_pair * 0.5 + (0.25 if Is Left Eye else 0.0)
          - Row (0..3 from bottom to top) = idx % 4 -> Y = row * 0.25
        """
        ng_name = "HI3 Eye Atlas Controller"
        ng = bpy.data.node_groups.get(ng_name)
        if ng and ng.get("_hi3_eye_atlas_v1"):
            return ng
        if not ng:
            ng = bpy.data.node_groups.new(ng_name, "ShaderNodeTree")
        ng.nodes.clear()
        if hasattr(ng, "interface"):
            ng.interface.clear()
            s_uv = ng.interface.new_socket(name="UV", in_out="INPUT", socket_type="NodeSocketVector")
            s_type = ng.interface.new_socket(name="Eye Type", in_out="INPUT", socket_type="NodeSocketInt")
            s_type.min_value = 1
            s_type.max_value = 8
            s_type.default_value = 1
            s_left = ng.interface.new_socket(name="Is Left Eye", in_out="INPUT", socket_type="NodeSocketFloat")
            s_left.min_value = 0.0
            s_left.max_value = 1.0
            s_left.default_value = 0.0
            s_scale = ng.interface.new_socket(name="Scale", in_out="INPUT", socket_type="NodeSocketVector")
            s_scale.default_value = (0.25, 0.25, 1.0)
            ng.interface.new_socket(name="Vector", in_out="OUTPUT", socket_type="NodeSocketVector")
        else:
            ng.inputs.clear()
            ng.outputs.clear()
            ng.inputs.new("NodeSocketVector", "UV")
            s_type = ng.inputs.new("NodeSocketInt", "Eye Type")
            s_type.min_value = 1
            s_type.max_value = 8
            s_type.default_value = 1
            s_left = ng.inputs.new("NodeSocketFloat", "Is Left Eye")
            s_left.min_value = 0.0
            s_left.max_value = 1.0
            s_left.default_value = 0.0
            s_scale = ng.inputs.new("NodeSocketVector", "Scale")
            s_scale.default_value = (0.25, 0.25, 1.0)
            ng.outputs.new("NodeSocketVector", "Vector")

        n_in = ng.nodes.new("NodeGroupInput")
        n_in.location = (-800, 0)
        n_out = ng.nodes.new("NodeGroupOutput")
        n_out.location = (600, 0)

        def _math(op, loc, val1=None, val2=None, clamp=False):
            m = ng.nodes.new("ShaderNodeMath")
            m.operation = op
            m.location = loc
            m.use_clamp = clamp
            if val1 is not None:
                m.inputs[0].default_value = val1
            if val2 is not None and len(m.inputs) > 1:
                m.inputs[1].default_value = val2
            return m

        # Clamp Eye Type to [1, 8]: max(1, min(8, Eye Type))
        m_min8 = _math('MINIMUM', (-600, 100), val2=8.0)
        ng.links.new(n_in.outputs["Eye Type"], m_min8.inputs[0])
        m_max1 = _math('MAXIMUM', (-450, 100), val2=1.0)
        ng.links.new(m_min8.outputs[0], m_max1.inputs[0])
        m_sub1 = _math('SUBTRACT', (-300, 100), val2=1.0)
        ng.links.new(m_max1.outputs[0], m_sub1.inputs[0])
        m_idx = _math('FLOOR', (-150, 100))
        ng.links.new(m_sub1.outputs[0], m_idx.inputs[0])

        # col_pair = floor(idx / 4.0)
        m_div4 = _math('DIVIDE', (0, 220), val2=4.0)
        ng.links.new(m_idx.outputs[0], m_div4.inputs[0])
        m_col_pair = _math('FLOOR', (150, 220))
        ng.links.new(m_div4.outputs[0], m_col_pair.inputs[0])

        # base_x = col_pair * 0.5 + Is_Left_Eye * 0.25
        m_col_x = _math('MULTIPLY', (300, 220), val2=0.5)
        ng.links.new(m_col_pair.outputs[0], m_col_x.inputs[0])
        m_side_x = _math('MULTIPLY', (150, 80), val2=0.25)
        ng.links.new(n_in.outputs["Is Left Eye"], m_side_x.inputs[0])
        m_off_x = _math('ADD', (450, 160))
        ng.links.new(m_col_x.outputs[0], m_off_x.inputs[0])
        ng.links.new(m_side_x.outputs[0], m_off_x.inputs[1])

        # row = idx % 4.0 -> off_y = row * 0.25
        m_mod4 = _math('MODULO', (0, -60), val2=4.0)
        ng.links.new(m_idx.outputs[0], m_mod4.inputs[0])
        m_off_y = _math('MULTIPLY', (200, -60), val2=0.25)
        ng.links.new(m_mod4.outputs[0], m_off_y.inputs[0])

        # Combine XYZ for Location
        n_comb = ng.nodes.new("ShaderNodeCombineXYZ")
        n_comb.location = (380, -20)
        ng.links.new(m_off_x.outputs[0], n_comb.inputs["X"])
        ng.links.new(m_off_y.outputs[0], n_comb.inputs["Y"])

        # Mapping node (POINT): Vector = UV * Scale + Location
        n_map = ng.nodes.new("ShaderNodeMapping")
        n_map.vector_type = 'POINT'
        n_map.location = (480, 100)
        ng.links.new(n_in.outputs["UV"], n_map.inputs["Vector"])
        ng.links.new(n_in.outputs["Scale"], n_map.inputs["Scale"])
        ng.links.new(n_comb.outputs["Vector"], n_map.inputs["Location"])
        ng.links.new(n_map.outputs["Vector"], n_out.inputs["Vector"])

        ng["_hi3_eye_atlas_v1"] = True
        return ng

    @classmethod
    def _apply_uv_scale_offset(cls, mat, scale, offset, orig_low=""):
        if not mat or not mat.use_nodes or not mat.node_tree:
            return
        sx, sy = scale
        ox, oy = offset
        if abs(sx - 1.0) <= 1e-4 and abs(sy - 1.0) <= 1e-4 and abs(ox) <= 1e-4 and abs(oy) <= 1e-4:
            return
        nt = mat.node_tree
        uv_group = nt.nodes.get("Group")
        if not uv_group:
            for n in nt.nodes:
                if n.type == 'GROUP' and n.node_tree and 'combine uv' in n.node_tree.name.lower():
                    uv_group = n
                    break
        if not uv_group:
            return
        uv_out = uv_group.outputs.get("Result") or (uv_group.outputs[0] if len(uv_group.outputs) > 0 else None)
        if not uv_out:
            return

        is_eye_4x4 = ("eye" in orig_low and abs(sx - 0.25) <= 1e-3 and abs(sy - 0.25) <= 1e-3)
        if is_eye_4x4:
            old_map = nt.nodes.get("HI3_Atlas_Mapping")
            if old_map and old_map.type != 'GROUP':
                nt.nodes.remove(old_map)
            ctrl_ng = cls._ensure_eye_atlas_node_group()
            grp_node = nt.nodes.get("HI3_Eye_Atlas_Controller")
            if not grp_node or grp_node.type != 'GROUP':
                grp_node = nt.nodes.new("ShaderNodeGroup")
                grp_node.name = "HI3_Eye_Atlas_Controller"
            grp_node.node_tree = ctrl_ng
            is_left = ("lefteye" in orig_low or abs(ox - 0.25) <= 1e-3 or abs(ox - 0.75) <= 1e-3)
            grp_node.label = "HI3 Left Eye Controller" if is_left else "HI3 Right Eye Controller"
            grp_node.location = (uv_group.location.x + 180, uv_group.location.y)
            if "Is Left Eye" in grp_node.inputs:
                grp_node.inputs["Is Left Eye"].default_value = 1.0 if is_left else 0.0
            if "Scale" in grp_node.inputs:
                grp_node.inputs["Scale"].default_value = (sx, sy, 1.0)
            # Compute initial Eye Type (1..8) from initial offset (ox, oy)
            col_pair = 1 if ox >= 0.49 else 0
            row_idx = max(0, min(3, int(round(oy / 0.25))))
            initial_type = col_pair * 4 + row_idx + 1
            if "Eye Type" in grp_node.inputs and not mat.get("_hi3_eye_controller_init"):
                grp_node.inputs["Eye Type"].default_value = initial_type
                mat["_hi3_eye_controller_init"] = True
            mat["_hi3_eye_side"] = "L" if is_left else "R"
            nt.links.new(uv_out, grp_node.inputs["UV"])
            for tex_name in ("Image Texture.001", "Outline_Diffuse"):
                tex_node = nt.nodes.get(tex_name)
                if tex_node and "Vector" in tex_node.inputs:
                    nt.links.new(grp_node.outputs["Vector"], tex_node.inputs["Vector"])
            return

        map_node = nt.nodes.get("HI3_Atlas_Mapping")
        if not map_node:
            map_node = nt.nodes.new("ShaderNodeMapping")
            map_node.name = "HI3_Atlas_Mapping"
            map_node.label = "HI3 Atlas Mapping"
        map_node.vector_type = 'POINT'
        map_node.inputs['Scale'].default_value = (sx, sy, 1.0)
        map_node.inputs['Location'].default_value = (ox, oy, 0.0)
        nt.links.new(uv_out, map_node.inputs['Vector'])
        for tex_name in ("Image Texture.001", "Outline_Diffuse"):
            tex_node = nt.nodes.get(tex_name)
            if tex_node and "Vector" in tex_node.inputs:
                nt.links.new(map_node.outputs['Vector'], tex_node.inputs['Vector'])

    @classmethod
    def apply_all_hi3_material_data(cls, context=None, directory=None):
        ctx = context or bpy.context
        cache_enabled = ctx.window_manager.cache_enabled if hasattr(ctx, 'window_manager') and hasattr(ctx.window_manager, 'cache_enabled') else True
        base_dir = (
            directory
            or (ctx.scene.get("setup_wizard_imported_model_dir") if hasattr(ctx, "scene") and ctx.scene else None)
            or get_cache(cache_enabled).get(CHARACTER_MODEL_FOLDER_FILE_PATH)
            or get_active_character_directory()
        )
        search_roots = []
        for cand in [
            base_dir,
            os.path.dirname(os.path.normpath(base_dir)) if base_dir else None,
            ctx.scene.get("setup_wizard_imported_model_dir") if hasattr(ctx, "scene") and ctx.scene else None,
            get_cache(cache_enabled).get(CHARACTER_MODEL_FOLDER_FILE_PATH),
            get_active_character_directory(),
        ]:
            if cand and os.path.isdir(cand):
                norm_c = os.path.normpath(cand)
                if norm_c not in search_roots:
                    search_roots.append(norm_c)
                parent_c = os.path.dirname(norm_c)
                if parent_c and os.path.isdir(parent_c) and os.path.basename(norm_c).lower() in (
                    'textures', 'texture', 'texture2d', 'materials', 'material', 'images'
                ):
                    if parent_c not in search_roots:
                        search_roots.insert(0, parent_c)

        material_json_map = {}
        for r_dir in search_roots:
            for root, _, files in os.walk(r_dir):
                if "__MACOSX" in root:
                    continue
                for f in files:
                    if f.startswith("._") or f.startswith(".") or not f.lower().endswith(".json"):
                        continue
                    full_p = os.path.join(root, f)
                    stem = os.path.splitext(f)[0].lower()
                    if stem not in material_json_map:
                        try:
                            with open(full_p, "r", encoding="utf-8") as jf:
                                jdata = json.load(jf)
                            if isinstance(jdata, dict) and "m_SavedProperties" in jdata:
                                material_json_map[stem] = jdata
                                m_name = (jdata.get("m_Name") or "").lower()
                                if m_name:
                                    material_json_map[m_name] = jdata
                        except Exception:
                            pass

        def _set_sock(node, name, val):
            if node and name in node.inputs:
                try:
                    node.inputs[name].default_value = val
                except Exception:
                    pass

        eye_atlas_tex_ids = set()
        mouth_materials_using_eye_atlas = set()

        for mat in bpy.data.materials:
            if not mat.use_nodes or not mat.node_tree:
                continue
            m_low = mat.name.lower()
            if not m_low.startswith("impacttoon - "):
                continue
            if m_low in ("impacttoon - base", "impacttoon - face", "impacttoon - hair", "impacttoon - eye", "impacttoon - outlines"):
                continue

            orig_m = (mat.get("_original_material_name") or mat.name.replace("ImpactToon - ", "").replace(" Outlines", "")).strip()
            orig_low = orig_m.lower()
            part_key = 'face' if ('face' in orig_low and 'dualface' not in orig_low) else \
                       'hair' if 'hair' in orig_low else \
                       'eye' if 'eye' in orig_low else \
                       'body' if 'body' in orig_low else orig_low.split('_')[-1]

            jdata = material_json_map.get(orig_low)
            if not jdata:
                for jk, jv in material_json_map.items():
                    if jk == orig_low or jk.endswith(f"_{orig_low}"):
                        jdata = jv
                        break
            if not jdata:
                for jk, jv in material_json_map.items():
                    if jk.endswith(f"_{part_key}"):
                        jdata = jv
                        break
            colors, floats, keywords = cls._extract_props(jdata) if jdata else ({}, {}, [])
            tex_envs = cls._extract_tex_envs(jdata) if jdata else {}
            main_tex_info = tex_envs.get("_MainTex") or {}
            uv_scale = main_tex_info.get("scale", (1.0, 1.0))
            uv_offset = main_tex_info.get("offset", (0.0, 0.0))
            main_tex_is_null = bool(main_tex_info.get("is_null", False))
            is_atlas = (abs(uv_scale[0] - 1.0) > 1e-4 or abs(uv_scale[1] - 1.0) > 1e-4 or abs(uv_offset[0]) > 1e-4 or abs(uv_offset[1]) > 1e-4)

            if is_atlas:
                cls._apply_uv_scale_offset(mat, uv_scale, uv_offset, orig_low=orig_low)
                if "eye" in orig_low:
                    tex_id = main_tex_info.get("name") or main_tex_info.get("path_id")
                    if tex_id:
                        eye_atlas_tex_ids.add(tex_id)

            is_eye_decal = ("lefteye" in orig_low or "righteye" in orig_low or ("eye" in orig_low and is_atlas))
            is_eyeshadow_overlay = ("eyeshadow" in orig_low or "shadow_eye" in orig_low) and main_tex_is_null

            use_alpha = 1.0 if (
                floats.get("_UseAlphaClip", 0.0) == 1.0
                or floats.get("_EnableAlphaTest", 0.0) == 1.0
                or floats.get("_AlphaClip", 0.0) == 1.0
                or is_eye_decal
                or is_eyeshadow_overlay
            ) else 0.0
            cutoff = floats.get("_AlphaClipThreshold", floats.get("_CutOff", 0.05 if is_eye_decal else 0.5))

            if is_eye_decal or is_eyeshadow_overlay:
                if hasattr(mat, "surface_render_method"):
                    try:
                        mat.surface_render_method = 'BLENDED'
                    except Exception:
                        pass

            if "mouth" in orig_low and is_atlas:
                tex_id = main_tex_info.get("name") or main_tex_info.get("path_id")
                if tex_id:
                    mouth_materials_using_eye_atlas.add((mat.name, tex_id))

            # 1. Outline material
            ol_node = mat.node_tree.nodes.get("Outlines")
            if ol_node:
                is_face_ol = ('face' in orig_low and 'dualface' not in orig_low)
                _set_sock(ol_node, "Use Face Shader", 1.0 if is_face_ol else 0.0)
                _set_sock(ol_node, "Use Alpha", use_alpha)
                _set_sock(ol_node, "Transparency Cutoff", cutoff)
                c1 = colors.get("_OutlineColor", (0.2, 0.2, 0.2, 1.0))
                c1_rgb = (c1[0], c1[1], c1[2], 1.0)
                _set_sock(ol_node, "Outline Color 1", c1_rgb)
                for idx in range(2, 6):
                    ci = colors.get(f"_OutlineColor{idx}", c1)
                    _set_sock(ol_node, f"Outline Color {idx}", (ci[0], ci[1], ci[2], 1.0))
                for cname in ("Ambient Colour", "Sharp Lit Colour", "Outline Tint"):
                    _set_sock(ol_node, cname, (1.0, 1.0, 1.0, 1.0))
                _set_sock(ol_node, "Outline Saturation", 1.0)
                _set_sock(ol_node, "Outline Intensity", 1.0)
                more_ol = (
                    floats.get("_More_Outline_Color", 0.0) == 1.0
                    or "MORE_OUTLINE_COLOR" in keywords
                    or ("_OutlineColor2" in colors and part_key == "body")
                )
                _set_sock(ol_node, "Hair/ Base", 1.0 if (more_ol and not is_face_ol and part_key != "hair") else 0.0)
                continue

            # 2. Main shader node (Group.005)
            sh_node = mat.node_tree.nodes.get("Group.005")
            if not sh_node or not sh_node.node_tree:
                continue

            nt_name = sh_node.node_tree.name
            for cname in ("Ambient Colour", "Sharp Light Colour", "Soft Light Colour", "Sharp Shadow Color", "Soft Shadow Colour"):
                _set_sock(sh_node, cname, (1.0, 1.0, 1.0, 1.0))

            if "ImpactToon - Face" in nt_name:
                _set_sock(sh_node, "_LightArea", floats.get("_LightArea", 0.51))
                feather = floats.get("_ShadowFeather", 0.001)
                _set_sock(sh_node, "_ShadowFeather", max(float(feather if feather else 0.001), 0.001))
                sc = (
                    colors.get("_ShadowColor")
                    or colors.get("_ShadowMultColor")
                    or colors.get("_FirstShadowMultColor")
                    or (0.96862745, 0.7529412, 0.7529412, 1.0)
                )
                _set_sock(sh_node, "_ShadowColor", (sc[0], sc[1], sc[2], 1.0))
                _set_sock(sh_node, "_ExpBlushIntensity", floats.get("_ExpBlushIntensity", floats.get("_ExpBlushIntensityR", 0.0)))
                _set_sock(sh_node, "_ExpShadowIntensity", floats.get("_ExpShadowIntensity", floats.get("_ExpShadowIntensityG", 0.0)))
                _set_sock(sh_node, "_ExpShadowIntensity2", floats.get("_ExpShadowIntensity2", floats.get("_ExpShadowIntensityB", 0.0)))
                _set_sock(sh_node, "_ExpShadowIntensity3", floats.get("_ExpShadowIntensity3", floats.get("_ExpShadowIntensityA", 0.0)))
                for s_name, c_keys, fallback in [
                    ("_ExpBlushColor", ("_ExpBlushColor", "_ExpBlushColorR"), (1.0, 0.0, 0.0, 1.0)),
                    ("_ExpShadowColor", ("_ExpShadowColor", "_ExpShadowColorG"), (0.6397, 0.3725, 0.3057, 1.0)),
                    ("_ExpShadowColor2", ("_ExpShadowColor2", "_ExpShadowColorB"), (0.5, 0.5, 0.5, 1.0)),
                    ("_ExpShadowColor3", ("_ExpShadowColor3", "_ExpShadowColorA"), (0.7569, 0.1686, 0.1686, 1.0)),
                ]:
                    c_val = next((colors[k] for k in c_keys if k in colors), fallback)
                    _set_sock(sh_node, s_name, (c_val[0], c_val[1], c_val[2], 1.0))
            else:
                has_multi_id = ("_FirstShadowMultColor2" in colors or "_ShadowMultColor2" in colors)
                is_single = (part_key in ("hair", "eye") or not has_multi_id)
                _set_sock(sh_node, "Body / Hair", 1.0 if is_single else 0.0)

                s1 = (
                    colors.get("_FirstShadowMultColor")
                    or colors.get("_ShadowMultColor")
                    or (0.9, 0.7, 0.75, 1.0)
                )
                if part_key == 'eye' and not any(k in orig_low for k in ('eyebrow', 'eyeshadow', 'shadow_eye')):
                    s1 = (1.0, 1.0, 1.0, 1.0)
                _set_sock(sh_node, "_FirstShadowMultColor", (s1[0], s1[1], s1[2], 1.0))
                for idx in range(2, 6):
                    si = (
                        colors.get(f"_FirstShadowMultColor{idx}")
                        or colors.get(f"_ShadowMultColor{idx}")
                        or s1
                    )
                    _set_sock(sh_node, f"_FirstShadowMultColor{idx}", (si[0], si[1], si[2], 1.0))

                _set_sock(sh_node, "_LightArea", floats.get("_LightArea", 0.51))
                _set_sock(sh_node, "_Shininess", max(float(floats.get("_Shininess", 10.0) or 10.0), 0.1))
                _set_sock(sh_node, "_SpecMulti", floats.get("_SpecMulti", 0.0))
                lsc = colors.get("_LightSpecColor", (1.0, 1.0, 1.0, 1.0))
                _set_sock(sh_node, "_LightSpecColor", (lsc[0], lsc[1], lsc[2], 1.0))

                if is_eyeshadow_overlay:
                    _set_sock(sh_node, "_MainTex Alpha", 0.0)
                _set_sock(sh_node, "Use Alpha", use_alpha)
                _set_sock(sh_node, "0 = Emission, 1 = Transparency", 1.0)
                _set_sock(sh_node, "Transparency Cutoff", cutoff)
                _set_sock(sh_node, "Emission Tint", (0.0, 0.0, 0.0, 1.0))
                _set_sock(sh_node, "Emission Strength", 0.0)

        cls._fix_hi3_eye_and_mouth_meshes(eye_atlas_tex_ids, mouth_materials_using_eye_atlas)
        try:
            from setup_wizard.ui.character_settings_utils import get_character_materials
            from setup_wizard.ui.hi3_character_settings import prepare_character_settings
            arm, mats = get_character_materials(ctx)
            if arm and mats:
                prepare_character_settings(arm, mats)
        except Exception:
            pass

    @classmethod
    def _fix_hi3_eye_and_mouth_meshes(cls, eye_atlas_tex_ids, mouth_materials_using_eye_atlas):
        """Fixes coplanar eye decal z-fighting (Eye_L / Eye_R on Face), hides Mouth decals mapped to eye atlas, and hides duplicate Eyes2 mesh."""
        face_obj = next((o for o in bpy.data.objects if o.type == 'MESH' and o.name.lower() == 'face'), None)
        face_coords = set()
        if face_obj and face_obj.data and face_obj.data.vertices:
            face_coords = {
                (round(v.co.x, 4), round(v.co.y, 4), round(v.co.z, 4))
                for v in face_obj.data.vertices
            }

        eyes_obj = next((o for o in bpy.data.objects if o.type == 'MESH' and o.name.lower() == 'eyes'), None)
        eyes2_obj = next((o for o in bpy.data.objects if o.type == 'MESH' and o.name.lower() == 'eyes2'), None)
        if eyes_obj and eyes2_obj:
            eyes2_obj.hide_viewport = True
            eyes2_obj.hide_render = True
            try:
                eyes2_obj.hide_set(True)
            except Exception:
                pass

        bad_mouth_mat_names = {
            mat_name for mat_name, tex_id in mouth_materials_using_eye_atlas
            if tex_id in eye_atlas_tex_ids
        }

        for obj in bpy.data.objects:
            if obj.type != 'MESH' or not obj.data:
                continue
            o_low = obj.name.lower()
            if o_low == 'mouth' and bad_mouth_mat_names:
                if any(ms.material and ms.material.name in bad_mouth_mat_names for ms in obj.material_slots):
                    obj.hide_viewport = True
                    obj.hide_render = True
                    try:
                        obj.hide_set(True)
                    except Exception:
                        pass
            elif o_low in ('eye_l', 'eye_r') and face_coords and not obj.get("_hi3_eye_decal_offset"):
                verts = obj.data.vertices
                if len(verts) > 0:
                    matches = sum(
                        1 for v in verts
                        if (round(v.co.x, 4), round(v.co.y, 4), round(v.co.z, 4)) in face_coords
                    )
                    if matches > len(verts) * 0.5:
                        # Determine local forward axis corresponding to world -Y (character forward)
                        try:
                            world_fwd = Vector((0.0, -1.0, 0.0))
                            local_fwd = (obj.matrix_world.to_3x3().inverted() @ world_fwd)
                            if local_fwd.length > 1e-6:
                                local_fwd.normalize()
                            else:
                                local_fwd = Vector((0.0, 0.0, 1.0))
                        except Exception:
                            local_fwd = Vector((0.0, 0.0, 1.0))
                        offset_vec = local_fwd * 0.0005
                        for v in verts:
                            v.co += offset_vec
                        obj.data.update()
                        obj["_hi3_eye_decal_offset"] = True

    def import_material_data(self):
        directory = getattr(self.blender_operator, "file_directory", None) or (
            os.path.dirname(self.blender_operator.filepath)
            if hasattr(self.blender_operator, "filepath") and self.blender_operator.filepath
            else None
        )
        self.apply_all_hi3_material_data(self.context, directory=directory)
        return {'FINISHED'}


