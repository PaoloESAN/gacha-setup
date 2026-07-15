# Author: michael-gh1

import bpy
import os

from abc import ABC, abstractmethod
from bpy.types import Operator, Context
from setup_wizard.domain.game_types import GameType

from setup_wizard.domain.shader_configurator import ShaderConfigurator
from setup_wizard.import_order import CHARACTER_MODEL_FOLDER_FILE_PATH, NextStepInvoker, cache_using_cache_key, get_cache
from setup_wizard.texture_import_setup.texture_importer_types import GenshinTextureImporter, TextureImporterFactory, TextureImporterType


class GameTextureImporter(ABC):
    @abstractmethod
    def import_textures(self):
        raise NotImplementedError()


class GameTextureImporterFactory:
    def create(game_type: GameType, blender_operator: Operator, context: Context):
        # Because we inject the GameType via StringProperty, we need to compare using the Enum's name (a string)
        if game_type == GameType.GENSHIN_IMPACT.name:
            return GenshinImpactTextureImporterFacade(blender_operator, context)
        elif game_type == GameType.HONKAI_STAR_RAIL.name:
            return HonkaiStarRailTextureImporterFacade(blender_operator, context)
        elif game_type == GameType.PUNISHING_GRAY_RAVEN.name:
            return PunishingGrayRavenTextureImporterFacade(blender_operator, context)
        elif game_type == GameType.ZENLESS_ZONE_ZERO.name:
            return ZenlessZoneZeroTextureImporterFacade(blender_operator, context)
        else:
            raise Exception(f'Unknown {GameType}: {game_type}')


'''
GI Texture Importer Abstraction Layer
Facade class intended to help abstract the Blender Operator layer from the Texture Importing layer.
Also named as a Facade in order to differentiate from the actual Texture Importers.
'''
class GenshinImpactTextureImporterFacade(GameTextureImporter):
    def __init__(self, blender_operator, context):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context

    '''
    This does look odd, but is intended to help with troubleshooting errors that users may encounter.
    The stacktrace will contain the method name (game name).
    '''
    def import_textures(self):
        return self.__import_genshin_impact_textures()

    def __import_genshin_impact_textures(self):
        cache_enabled = self.context.window_manager.cache_enabled
        directory = self.blender_operator.file_directory \
            or get_cache(cache_enabled).get(CHARACTER_MODEL_FOLDER_FILE_PATH) \
            or os.path.dirname(self.blender_operator.filepath)

        if not directory:
            bpy.ops.genshin.import_textures(
                'INVOKE_DEFAULT',
                next_step_idx=self.blender_operator.next_step_idx, 
                file_directory=self.blender_operator.file_directory,
                invoker_type=self.blender_operator.invoker_type,
                high_level_step_name=self.blender_operator.high_level_step_name,
                game_type=GameType.GENSHIN_IMPACT.name,
            )
            return {'SKIP'}

        texture_importer_type = ''
        
        if [material_name for material_name, material in bpy.data.materials.items() if 'Avatar'.lower() in material_name.lower() and 'Avatar_Default_Mat'.lower() not in material_name.lower()]:
            texture_importer_type = TextureImporterType.AVATAR
        elif [material_name for material_name, material in bpy.data.materials.items() if 'Monster'.lower() in material_name.lower()]:
            texture_importer_type = TextureImporterType.MONSTER
        else:
            texture_importer_type = TextureImporterType.NPC

        texture_importer: GenshinTextureImporter = TextureImporterFactory.create(texture_importer_type, GameType.GENSHIN_IMPACT)
        texture_importer.import_textures(directory)

        '''
            NPCs and Monsters don't typically have shadow ramps. Turn off using shadow ramp if there are no assets for it.
            If an asset does exist, leave it as the default value (1.0).
        '''
        if (texture_importer_type is TextureImporterType.NPC or texture_importer_type is TextureImporterType.MONSTER) and \
            not [file for file in [file for name, folder, file in os.walk(directory)][0] if 'Shadow_Ramp' in file]:
            ShaderConfigurator().update_shader_value(
                materials = [
                    bpy.data.materials.get('miHoYo - Genshin Hair'),
                    bpy.data.materials.get('miHoYo - Genshin Face'),
                    bpy.data.materials.get('miHoYo - Genshin Body'),
                    bpy.data.materials.get('miHoYo - Genshin Dress'),
                ],
                node_name = 'miHoYo - Genshin Impact',
                input_name = 'Use Shadow Ramp',
                value = 0
        )

        self.blender_operator.report({'INFO'}, 'Imported textures')
        if cache_enabled and directory:
            cache_using_cache_key(get_cache(cache_enabled), CHARACTER_MODEL_FOLDER_FILE_PATH, directory)

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx,
            self.blender_operator.invoker_type,
            file_path_to_cache=directory,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=GameType.GENSHIN_IMPACT.name,
        )
        return {'FINISHED'}


'''
HSR Texture Importer Abstraction Layer
Facade class intended to help abstract the Blender Operator layer from the Texture Importing layer.
Also named as a Facade in order to differentiate from the actual Texture Importers.
'''
class HonkaiStarRailTextureImporterFacade(GameTextureImporter):
    def __init__(self, blender_operator, context):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context

    '''
    This does look odd, but is intended to help with troubleshooting errors that users may encounter.
    The stacktrace will contain the method name (game name).
    '''
    def import_textures(self):
        return self.__import_honkai_star_rail_textures()

    def __import_honkai_star_rail_textures(self):
        cache_enabled = self.context.window_manager.cache_enabled
        directory = self.blender_operator.file_directory \
            or get_cache(cache_enabled).get(CHARACTER_MODEL_FOLDER_FILE_PATH) \
            or os.path.dirname(self.blender_operator.filepath)

        if not directory:
            bpy.ops.genshin.import_textures(
                'INVOKE_DEFAULT',
                next_step_idx=self.blender_operator.next_step_idx, 
                file_directory=self.blender_operator.file_directory,
                invoker_type=self.blender_operator.invoker_type,
                high_level_step_name=self.blender_operator.high_level_step_name,
                game_type=GameType.HONKAI_STAR_RAIL.name,
            )
            return {'FINISHED'}

        texture_importer_type = TextureImporterType.HSR_AVATAR
        texture_importer: GenshinTextureImporter = TextureImporterFactory.create(texture_importer_type, GameType.HONKAI_STAR_RAIL)
        texture_importer.import_textures(directory)

        self.blender_operator.report({'INFO'}, 'Imported textures')
        if cache_enabled and directory:
            cache_using_cache_key(get_cache(cache_enabled), CHARACTER_MODEL_FOLDER_FILE_PATH, directory)

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx,
            self.blender_operator.invoker_type,
            file_path_to_cache=directory,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=GameType.HONKAI_STAR_RAIL.name
        )


'''
PGR Texture Importer Abstraction Layer
Facade class intended to help abstract the Blender Operator layer from the Texture Importing layer.
Also named as a Facade in order to differentiate from the actual Texture Importers.
'''
class PunishingGrayRavenTextureImporterFacade(GameTextureImporter):
    def __init__(self, blender_operator, context):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context

    '''
    This does look odd, but is intended to help with troubleshooting errors that users may encounter.
    The stacktrace will contain the method name (game name).
    '''
    def import_textures(self):
        return self.__import_punishing_gray_raven_textures()

    def __import_punishing_gray_raven_textures(self):
        cache_enabled = self.context.window_manager.cache_enabled
        directory = self.blender_operator.file_directory \
            or get_cache(cache_enabled).get(CHARACTER_MODEL_FOLDER_FILE_PATH) \
            or os.path.dirname(self.blender_operator.filepath)

        if not directory:
            bpy.ops.genshin.import_textures(
                'INVOKE_DEFAULT',
                next_step_idx=self.blender_operator.next_step_idx, 
                file_directory=self.blender_operator.file_directory,
                invoker_type=self.blender_operator.invoker_type,
                high_level_step_name=self.blender_operator.high_level_step_name,
                game_type=GameType.PUNISHING_GRAY_RAVEN.name,
            )
            return {'FINISHED'}

        texture_importer_type = TextureImporterType.PGR_AVATAR
        texture_importer: GenshinTextureImporter = TextureImporterFactory.create(texture_importer_type, GameType.PUNISHING_GRAY_RAVEN)
        texture_importer.import_textures(directory)

        self.blender_operator.report({'INFO'}, 'Imported textures')
        if cache_enabled and directory:
            cache_using_cache_key(get_cache(cache_enabled), CHARACTER_MODEL_FOLDER_FILE_PATH, directory)

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx,
            self.blender_operator.invoker_type,
            file_path_to_cache=directory,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=GameType.PUNISHING_GRAY_RAVEN.name
        )


class ZenlessZoneZeroTextureImporterFacade(GameTextureImporter):
    def __init__(self, blender_operator, context):
        self.blender_operator = blender_operator
        self.context = context

    def import_textures(self):
        cache_enabled = self.context.window_manager.cache_enabled
        directory = self.blender_operator.file_directory \
            or get_cache(cache_enabled).get(CHARACTER_MODEL_FOLDER_FILE_PATH) \
            or os.path.dirname(self.blender_operator.filepath)

        if directory:
            textures_subdir = os.path.join(directory, "Textures")
            if os.path.isdir(textures_subdir):
                directory = textures_subdir
            elif not os.path.isdir(directory):
                directory = None

        if not directory:
            bpy.ops.genshin.import_textures(
                'INVOKE_DEFAULT',
                next_step_idx=self.blender_operator.next_step_idx, 
                file_directory=self.blender_operator.file_directory,
                invoker_type=self.blender_operator.invoker_type,
                high_level_step_name=self.blender_operator.high_level_step_name,
                game_type=GameType.ZENLESS_ZONE_ZERO.name,
            )
            return {'FINISHED'}

        self.import_textures_from_folder(directory)

        self.blender_operator.report({'INFO'}, 'Imported textures')
        if cache_enabled and directory:
            cache_using_cache_key(get_cache(cache_enabled), CHARACTER_MODEL_FOLDER_FILE_PATH, directory)

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx,
            self.blender_operator.invoker_type,
            file_path_to_cache=directory,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=GameType.ZENLESS_ZONE_ZERO.name
        )
        return {'FINISHED'}

    def import_textures_from_folder(self, folder):
        files = os.listdir(folder)
        
        groups = {
            "Body_1": [],
            "Body_2": [],
            "Body_3": [],
            "Face": [],
            "Hair": [],
            "Weapon": [],
            "Weapon_2": [],
            "Leg": [],
            "Tail": []
        }

        for filename in files:
            lower_name = filename.lower()
            if "weapon_2" in lower_name or "weapon2" in lower_name or "weapon_map2" in lower_name or "weaponmap2" in lower_name:
                groups["Weapon_2"].append(filename)
            elif "weapon" in lower_name:
                groups["Weapon"].append(filename)
            elif "face" in lower_name:
                groups["Face"].append(filename)
            elif "hair" in lower_name:
                groups["Hair"].append(filename)
            elif "leg" in lower_name:
                groups["Leg"].append(filename)
            elif "tail" in lower_name:
                groups["Tail"].append(filename)
            elif "body_3" in lower_name or "body3" in lower_name or "body_map3" in lower_name or "bodymap3" in lower_name:
                groups["Body_3"].append(filename)
            elif "body_2" in lower_name or "body2" in lower_name or "body_map2" in lower_name or "bodymap2" in lower_name:
                groups["Body_2"].append(filename)
            elif "body" in lower_name:
                groups["Body_1"].append(filename)

        for mat in bpy.data.materials:
            if not mat.name.startswith("ZZZ Shader") or not mat.node_tree:
                continue
            
            matname = mat.name.lower()
            group_keys = []
            if "hair" in matname:
                group_keys = ["Hair"]
            elif "face" in matname:
                group_keys = ["Face"]
            elif "eye" in matname:
                group_keys = ["Face"]
            elif "body" in matname or "leg" in matname or "tail" in matname:
                if "body 2" in matname or "body2" in matname:
                    group_keys = ["Body_2"]
                elif "body3" in matname or "body3/leg" in matname or "leg" in matname or "tail" in matname:
                    group_keys = ["Body_3", "Leg", "Tail"]
                else:
                    group_keys = ["Body_1"]
            elif "weapon" in matname:
                if "weapon 2" in matname or "weapon2" in matname:
                    group_keys = ["Weapon_2"]
                else:
                    group_keys = ["Weapon"]

            nodes = mat.node_tree.nodes
            for node in nodes:
                if node.type == 'TEX_IMAGE':
                    suffix = node.name.split("_")[-1] if "_" in node.name else node.name[-1]
                    target_suffix = f"_{suffix}.png"
                    
                    found_img = None
                    for key in group_keys:
                        for f in groups[key]:
                            if f.lower().endswith(target_suffix.lower()):
                                found_img = f
                                break
                        if found_img:
                            break
                    
                    if not found_img:
                        target_suffix_simple = f"{suffix}.png"
                        for key in group_keys:
                            for f in groups[key]:
                                if f.lower().endswith(target_suffix_simple.lower()):
                                    found_img = f
                                    break
                            if found_img:
                                break

                    if found_img:
                        img_path = os.path.join(folder, found_img)
                        img = bpy.data.images.load(img_path, check_existing=True)
                        node.image = img
                        
                        if suffix.upper() in ["D", "DIFFUSE"]:
                            img.colorspace_settings.name = 'sRGB'
                        else:
                            img.colorspace_settings.name = 'Non-Color'
                        img.alpha_mode = 'CHANNEL_PACKED'

                elif node.type == 'GROUP' and node.node_tree and node.node_tree.name == "Face Lightmap":
                    face_lightmap_node = node.node_tree.nodes.get("Face_Lightmap")
                    if face_lightmap_node:
                        found_lightmap = None
                        for f in groups["Face"]:
                            if "lightmap" in f.lower():
                                found_lightmap = f
                                break
                        if found_lightmap:
                            img_path = os.path.join(folder, found_lightmap)
                            img = bpy.data.images.load(img_path, check_existing=True)
                            face_lightmap_node.image = img
                            img.colorspace_settings.name = 'Non-Color'
                            img.alpha_mode = 'CHANNEL_PACKED'
