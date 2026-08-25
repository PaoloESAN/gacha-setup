import bpy
import os
import re
import json

from abc import ABC, abstractmethod
from bpy.types import Operator, Context
from setup_wizard.domain.game_types import GameType

from setup_wizard.domain.shader_configurator import ShaderConfigurator
from setup_wizard.import_order import (
    CHARACTER_MODEL_FOLDER_FILE_PATH,
    NEVERNESS_TO_EVERNESS_ROOT_FOLDER_FILE_PATH,
    NextStepInvoker,
    cache_using_cache_key,
    get_cache,
    get_active_character_directory,
    set_active_character_directory,
)
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
        elif game_type == GameType.NEVERNESS_TO_EVERNESS.name:
            return NevernessToEvernessTextureImporterFacade(blender_operator, context)
        elif game_type == GameType.WUTHERING_WAVES.name:
            return WutheringWavesTextureImporterFacade(blender_operator, context)
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

    def _build_zzz_json_texture_map(self, folder):
        candidates_dirs = [
            folder,
            os.path.join(folder, "Materials"),
            os.path.join(os.path.dirname(folder), "Materials"),
        ]
        
        materials_dir = None
        for d in candidates_dirs:
            if os.path.isdir(d) and any(f.lower().endswith(".json") for f in os.listdir(d)):
                materials_dir = d
                break
                
        # Find texture directory
        tex_dir = folder
        if not any(f.lower().endswith(('.png', '.tga', '.dds', '.jpg', '.jpeg')) for f in os.listdir(folder)):
            sub = os.path.join(folder, "Textures")
            if os.path.isdir(sub):
                tex_dir = sub
            else:
                sub = os.path.join(os.path.dirname(folder), "Textures")
                if os.path.isdir(sub):
                    tex_dir = sub

        if not materials_dir:
            return {}, tex_dir

        image_files = [f for f in os.listdir(tex_dir) if f.lower().endswith(('.png', '.tga', '.dds', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'))]
        
        def resolve_file(tex_name):
            if not tex_name:
                return None
            t_low = tex_name.lower().strip()
            for f in image_files:
                stem = os.path.splitext(f)[0].lower()
                if stem == t_low:
                    return f
            for f in image_files:
                stem = os.path.splitext(f)[0].lower()
                if stem.startswith(t_low) or t_low.startswith(stem):
                    return f
            for f in image_files:
                if t_low in f.lower():
                    return f
            return None

        mat_map = {}
        for jf in os.listdir(materials_dir):
            if not jf.lower().endswith(".json"):
                continue
            jpath = os.path.join(materials_dir, jf)
            try:
                with open(jpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
                
            tex_envs = data.get("m_SavedProperties", {}).get("m_TexEnvs", {})
            mat_key = os.path.splitext(jf)[0].lower()
            
            extracted = {}
            slot_mappings = {
                '_MainTex': 'd',
                '_EyeColorMap': 'd',
                '_OtherDataTex': 'm',
                '_OtherDataTex2': 'a',
                '_LightTex': 'n',
                '_BumpMap': 'n',
                '_FaceLightMap': 'n',
                '_MatCapTex': 'matcap',
                '_MatCapTex2': 'matcap2',
                '_MatCapTex3': 'matcap3',
                '_MatCapTex4': 'matcap4',
                '_MatCapTex5': 'matcap5',
            }
            
            for slot_name, map_key in slot_mappings.items():
                slot_data = tex_envs.get(slot_name, {})
                if isinstance(slot_data, dict):
                    tex_obj = slot_data.get("m_Texture", {})
                    if isinstance(tex_obj, dict) and not tex_obj.get("IsNull", True):
                        t_name = tex_obj.get("Name")
                        if t_name:
                            resolved = resolve_file(t_name)
                            if resolved:
                                extracted[map_key] = resolved
                                
            mat_map[mat_key] = extracted
        return mat_map, tex_dir

    def _find_json_textures_for_material(self, mat_name, json_map):
        if not json_map:
            return None
        m_clean = mat_name.lower().replace("zzz", "").replace("kythera's", "").replace("kythera", "").replace("shader", "").strip(" _-")
        
        # 1. Exact / Substring match
        for j_key, tex_dict in json_map.items():
            if j_key == m_clean or j_key in m_clean or m_clean in j_key:
                return tex_dict
                
        # 2. Token overlap match
        m_tokens = set(re.split(r'[^a-zA-Z0-9]+', m_clean)) - {'', 'mat', 'ui'}
        best_key = None
        best_overlap = 0
        for j_key, tex_dict in json_map.items():
            j_tokens = set(re.split(r'[^a-zA-Z0-9]+', j_key)) - {'', 'mat', 'ui'}
            overlap = len(m_tokens.intersection(j_tokens))
            if overlap > best_overlap:
                best_overlap = overlap
                best_key = j_key
                
        if best_key and best_overlap > 0:
            return json_map[best_key]
        return None

    def import_textures_from_folder(self, folder):
        json_map, tex_folder = self._build_zzz_json_texture_map(folder)
        if not tex_folder:
            tex_folder = folder

        files = os.listdir(tex_folder)
        
        # Try to find a character name prefix to filter the files (prevents importing other characters' textures if in same folder)
        main_prefix = ""
        armatures = [ob for ob in bpy.data.objects if ob.type == 'ARMATURE']
        if armatures:
            active_arm = bpy.context.view_layer.objects.active
            arm_obj = active_arm if (active_arm and active_arm.type == 'ARMATURE') else armatures[0]
            char_prefix = arm_obj.name.split(".")[0]
            
            # Clean up common suffixes/prefixes
            for affix in ["_Armature", "_armature", "_Rig", "_rig", "avatar_zzz_", "avatar_"]:
                if char_prefix.endswith(affix):
                    char_prefix = char_prefix[:-len(affix)]
                if char_prefix.startswith(affix):
                    char_prefix = char_prefix[len(affix):]
            
            # Use the main name prefix (e.g. "Zhenzhen" from "Zhenzhen_Dawnlight")
            main_prefix = char_prefix.split("_")[0]

        filtered_files = []
        if main_prefix:
            for filename in files:
                if main_prefix.lower() in filename.lower():
                    filtered_files.append(filename)
        
        if not filtered_files:
            filtered_files = files
        
        import re

        def clean_tokens(text):
            text = re.sub(r'zzz|kythera\'s|kythera|shader|mat|mat_|mesh|object|\+ t', '', text, flags=re.IGNORECASE)
            tokens = [t.lower() for t in re.split(r'[^a-zA-Z0-9]+', text) if len(t) > 1 and not t.isdigit()]
            return set(tokens)

        def find_best_texture(mat_name, mesh_names, tex_type, image_files, char_prefix=''):
            suf = f'_{tex_type.lower()}'
            candidates = [
                f for f in image_files 
                if f.lower().rsplit('.', 1)[0].endswith(suf) or f'_{tex_type.lower()}.' in f.lower()
            ]
            if not candidates:
                candidates = [f for f in image_files if f.lower().rsplit('.', 1)[0].endswith(tex_type.lower())]
            if not candidates:
                return None
            if len(candidates) == 1:
                return candidates[0]

            combined = mat_name + ' ' + ' '.join(mesh_names)
            mat_tokens = clean_tokens(combined)
            combined_lower = combined.lower()

            # Determine target body level / category
            is_body3 = any(k in combined_lower for k in ['body 3', 'body3', 'body_3', 'map3', 'map_3', 'leg', 'shoe', 'boot', 'foot', 'sock', 'stocking', 'thigh', 'tail', 'cola'])
            is_body2 = any(k in combined_lower for k in ['body 2', 'body2', 'body_2', 'map2', 'map_2', 'wing', 'ala', 'feather', 'dress', 'cape', 'cloak', 'coat', 'jacket', 'acc', 'deco', 'extra', 'outer'])
            is_face = any(k in combined_lower for k in ['face', 'eyebrow', 'brow', 'eye', 'cara', 'head', 'rostro', 'pupil', 'iris'])
            is_hair = any(k in combined_lower for k in ['hair', 'pelo', 'cabello', 'bang', 'ponytail', 'twintail', 'ahoge'])
            is_sticker = any(k in combined_lower for k in ['sticker', 'decal', 'ui', 'logo', 'badge'])
            is_weapon = any(k in combined_lower for k in ['weapon', 'wpn', 'equip', 'sword', 'blade', 'spear', 'gun', 'prop', 'arma', 'katana'])

            has_b3_files = any(any(k in f.lower() for k in ['body_3', 'body3', 'body 3', 'map3', 'map_3', 'leg', 'tail', '_3.']) for f in candidates)
            has_b2_files = any(any(k in f.lower() for k in ['body_2', 'body2', 'body 2', 'map2', 'map_2', '_2.']) for f in candidates)

            categories = {
                'face': ['face', 'eyebrow', 'brow', 'eye', 'cara', 'head', 'rostro', 'pupil', 'iris'],
                'hair': ['hair', 'pelo', 'cabello', 'bang', 'ponytail', 'twintail', 'ahoge'],
                'weapon': ['weapon', 'wpn', 'equip', 'sword', 'blade', 'spear', 'gun', 'prop', 'arma', 'katana'],
                'sticker': ['sticker', 'decal', 'ui', 'logo', 'badge'],
                'wing': ['wing', 'ala', 'feather', 'pluma'],
                'body3': ['body3', 'body 3', 'body_3', 'map3', 'map_3', 'leg', 'shoe', 'boot', 'foot', 'sock', 'stocking', 'thigh', 'tail', 'cola'],
                'body2': ['body2', 'body 2', 'body_2', 'map2', 'map_2', 'wing', 'ala', 'feather', 'dress', 'cape', 'cloak', 'coat', 'jacket', 'acc', 'deco', 'extra', 'outer'],
                'body1': ['body1', 'body 1', 'body_1', 'map1', 'body', 'torso', 'chest', 'main', 'skin', 'cloth', 'shirt']
            }

            best_file = candidates[0]
            best_score = -999999

            for f in candidates:
                f_lower = f.lower()
                f_clean = f_lower.rsplit('.', 1)[0]
                for p in ['_d', '_m', '_a', '_n', '_diffuse', '_normal', '_lightmap']:
                    if f_clean.endswith(p):
                        f_clean = f_clean[:-len(p)]
                if char_prefix and f_clean.startswith(char_prefix.lower()):
                    f_clean = f_clean[len(char_prefix.lower()):].lstrip('_')
                
                f_tokens = clean_tokens(f_clean)
                score = 0
                
                # 1. Exact Word/Token matches
                matched = len(mat_tokens.intersection(f_tokens))
                extra_in_file = len(f_tokens - mat_tokens)
                score += matched * 60 - extra_in_file * 10
                
                # 2. Sub-keyword matching & Tiered Fallback:
                if is_body3:
                    f_is_3 = any(k in f_lower for k in ['body_3', 'body3', 'body 3', 'map3', 'map_3', 'leg', 'tail', '_3.'])
                    f_is_2 = any(k in f_lower for k in ['body_2', 'body2', 'body 2', 'map2', 'map_2', '_2.'])
                    f_is_1 = 'body' in f_lower and not (f_is_3 or f_is_2)
                    if f_is_3:
                        score += 100
                    elif f_is_2:
                        score += 70 if not has_b3_files else -20
                    elif f_is_1:
                        score += 40 if (not has_b3_files and not has_b2_files) else -40

                elif is_body2:
                    f_is_2 = any(k in f_lower for k in ['body_2', 'body2', 'body 2', 'map2', 'map_2', 'wing', 'dress', 'cape', '_2.'])
                    f_is_1 = 'body' in f_lower and not f_is_2
                    if f_is_2:
                        score += 100
                    elif f_is_1:
                        score += 50 if not has_b2_files else -30

                elif not (is_face or is_hair or is_sticker or is_weapon):
                    f_is_1 = 'body' in f_lower and not any(k in f_lower for k in ['body_2', 'body2', 'body 2', 'body_3', 'body3', 'body 3', '_2.', '_3.'])
                    f_is_2 = any(k in f_lower for k in ['body_2', 'body2', 'body 2', '_2.'])
                    if f_is_1:
                        score += 100
                    elif f_is_2:
                        score += 30

                else:
                    for sub in ['2', '3', '02', '03']:
                        f_has = sub in f_lower
                        m_has = sub in combined_lower
                        if f_has and m_has:
                            score += 35
                        elif f_has and not m_has:
                            score -= 35

                # 3. Exact token substring bonus
                for tok in mat_tokens:
                    if tok in f_clean or f_clean in tok:
                        score += 30

                # 4. Category affinity (face, hair, weapon, sticker)
                for cat in ['face', 'hair', 'weapon', 'sticker']:
                    keywords = categories[cat]
                    mat_in_cat = any(k in combined_lower for k in keywords)
                    file_in_cat = any(k in f_lower for k in keywords)
                    if mat_in_cat and file_in_cat:
                        score += 50
                    elif mat_in_cat and not file_in_cat and any(any(k in other.lower() for k in keywords) for other in candidates):
                        score -= 35

                if score > best_score:
                    best_score = score
                    best_file = f

            return best_file

        def find_best_face_lightmap(mat_name, mesh_names, image_files, char_prefix=''):
            lm_candidates = [
                f for f in image_files
                if 'lightmap' in f.lower() and (f.lower().endswith('.png') or f.lower().endswith('.tga') or f.lower().endswith('.dds'))
            ]
            if not lm_candidates:
                return find_best_texture(mat_name, mesh_names, 'm', image_files, char_prefix)
            if len(lm_candidates) == 1:
                return lm_candidates[0]
            
            best = lm_candidates[0]
            best_sc = -9999
            for f in lm_candidates:
                sc = 0
                if any(k in f.lower() for k in ['face', 'head', 'cara']): sc += 50
                if char_prefix and char_prefix.lower() in f.lower(): sc += 30
                if sc > best_sc:
                    best_sc = sc
                    best = f
            return best

        def connect_tex_to_socket(mat, group_node, socket_id, socket_names, file_name, is_color=False, y_offset=0):
            if not file_name:
                return None
            img_path = os.path.join(tex_folder, file_name)
            if not os.path.isfile(img_path):
                img_path = os.path.join(folder, file_name)
            if not os.path.isfile(img_path):
                return None

            img = bpy.data.images.load(img_path, check_existing=True)
            img.colorspace_settings.name = 'sRGB' if is_color else 'Non-Color'
            img.alpha_mode = 'CHANNEL_PACKED'

            nodes = mat.node_tree.nodes
            links = mat.node_tree.links

            if isinstance(socket_names, str):
                socket_names = [socket_names]

            target_socket = None
            for sname in socket_names:
                for inp in group_node.inputs:
                    if inp.name.lower().strip() == sname.lower().strip():
                        target_socket = inp
                        break
                if target_socket:
                    break

            if not target_socket:
                for sname in socket_names:
                    s_words = set(sname.lower().replace("_", " ").split())
                    for inp in group_node.inputs:
                        inp_words = set(inp.name.lower().replace("_", " ").split())
                        if s_words == inp_words:
                            target_socket = inp
                            break
                    if target_socket:
                        break

            if not target_socket:
                return None

            node_tag = f"Texture_{socket_id}"
            tex_node = None
            for link in list(links):
                if link.to_socket == target_socket:
                    if link.from_node.type == 'TEX_IMAGE' and (link.from_node.name == node_tag or (link.from_node.name.startswith(f"Texture_{socket_id}") and not any(other in link.from_node.name for other in ["_D", "_M", "_A", "_N"] if other != f"_{socket_id}"))):
                        tex_node = link.from_node
                    else:
                        links.remove(link)

            if not tex_node:
                tex_node = nodes.get(node_tag)

            if not tex_node:
                tex_node = nodes.new('ShaderNodeTexImage')
                tex_node.name = node_tag
                tex_node.label = f"Texture {socket_id}"
                tex_node.location = (group_node.location.x - 360, group_node.location.y + y_offset)

            tex_node.image = img

            if not any(link.to_socket == target_socket and link.from_node == tex_node for link in links):
                links.new(tex_node.outputs['Color'], target_socket)

            return tex_node

        for mat in bpy.data.materials:
            if not mat.node_tree:
                continue

            matname = mat.name.lower()
            is_zzz_mat = mat.name.startswith("ZZZ") or mat.name.startswith("Kythera") or \
                any(n.type == 'GROUP' and n.node_tree and ('kythera' in n.node_tree.name.lower() or 'zzz' in n.node_tree.name.lower()) for n in mat.node_tree.nodes)
            if not is_zzz_mat:
                continue

            # Find the primary shader group node
            shader_group_node = None
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    nt_low = node.node_tree.name.lower()
                    if "kythera" in nt_low or "face shader" in nt_low or "shader t" in nt_low or "shader + t" in nt_low or "shader" in nt_low or "zzz" in nt_low:
                        shader_group_node = node
                        break

            if not shader_group_node:
                for node in mat.node_tree.nodes:
                    if node.type == 'GROUP' and node.node_tree:
                        shader_group_node = node
                        break

            if not shader_group_node:
                continue

            # Combine material name and any mesh names using this material for complete context
            mesh_names = [obj.name.lower() for obj in bpy.data.objects if obj.type == 'MESH' and any(s.material == mat for s in obj.material_slots)]
            combined_names = matname + " " + " ".join(mesh_names)
            is_alice_pingmu = "alice" in combined_names and "pingmu" in combined_names

            # Check if JSON material data contains exact textures
            json_textures = self._find_json_textures_for_material(mat.name, json_map)

            # Check if this is a Kythera shader material
            kythera_group_node = None
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    nt_low = node.node_tree.name.lower()
                    if "kythera" in nt_low:
                        kythera_group_node = node
                        break

            if kythera_group_node:
                # --- KYTHERA SHADER TEXTURE CONNECTION ---
                if is_alice_pingmu:
                    belt_path = get_belt_texture_path()
                    if belt_path and os.path.isfile(belt_path):
                        belt_img = bpy.data.images.load(belt_path, check_existing=True)
                        belt_img.colorspace_settings.name = 'sRGB'
                        belt_img.alpha_mode = 'CHANNEL_PACKED'
                        
                        target_socket = None
                        for inp in kythera_group_node.inputs:
                            if inp.name.lower().strip() in ["_d map", "_d", "diffuse", "diffuse texture"]:
                                target_socket = inp
                                break
                        if target_socket:
                            tex_node = mat.node_tree.nodes.get("Texture_D")
                            if not tex_node:
                                tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                                tex_node.name = "Texture_D"
                                tex_node.label = "Texture D"
                                tex_node.location = (kythera_group_node.location.x - 360, kythera_group_node.location.y)
                            tex_node.image = belt_img
                            if not any(l.to_socket == target_socket and l.from_node == tex_node for l in mat.node_tree.links):
                                mat.node_tree.links.new(tex_node.outputs['Color'], target_socket)

                        # Leave M, A, N empty / disconnected
                        for other_tag in ["Texture_M", "Texture_A", "Texture_N", "Texture_Lightmap"]:
                            old_n = mat.node_tree.nodes.get(other_tag)
                            if old_n:
                                for l in list(mat.node_tree.links):
                                    if l.from_node == old_n:
                                        mat.node_tree.links.remove(l)
                    continue

                is_face = any(k in combined_names for k in ["face", "eyebrow", "brow", "眉", "eye", "eyelash", "pupil", "iris", "highlight", "cara", "head", "rostro"]) or \
                    (kythera_group_node.node_tree and "face" in kythera_group_node.node_tree.name.lower())

                if is_face:
                    # 1. Face D -> _D Map / Diffuse Texture (sRGB)
                    face_d = (json_textures.get('d') if json_textures else None) or find_best_texture(matname, mesh_names, "d", filtered_files, main_prefix)
                    if face_d:
                        connect_tex_to_socket(mat, kythera_group_node, "Face_D", ["_D Map", "_D", "Diffuse Texture", "Diffuse"], face_d, is_color=True, y_offset=0)

                    # 2. Face Lightmap -> Light Map (Non-Color)
                    face_lm = (json_textures.get('n') if json_textures else None) or find_best_face_lightmap(matname, mesh_names, filtered_files, main_prefix)
                    if face_lm:
                        lm_node = None
                        for node in mat.node_tree.nodes:
                            if node.type == 'TEX_IMAGE':
                                if (node.image and "lightmap" in node.image.name.lower()) or "lightmap" in node.name.lower() or "lightmap" in node.label.lower():
                                    lm_node = node
                                    break
                        if lm_node:
                            img_path = os.path.join(tex_folder, face_lm) if os.path.isfile(os.path.join(tex_folder, face_lm)) else os.path.join(folder, face_lm)
                            if os.path.isfile(img_path):
                                img = bpy.data.images.load(img_path, check_existing=True)
                                img.colorspace_settings.name = 'Non-Color'
                                img.alpha_mode = 'CHANNEL_PACKED'
                                lm_node.image = img
                        else:
                            connect_tex_to_socket(mat, kythera_group_node, "Face_Lightmap", ["Light Map", "LightMap", "_Lightmap"], face_lm, is_color=False, y_offset=-280)

                else:
                    # Body, Hair, Weapon, Dress, Wings, Stickers, Acc, etc. (Kythera's ZZZ Shader)
                    # 1. Texture D -> _D Map / Diffuse (sRGB)
                    tex_d = (json_textures.get('d') if json_textures else None) or find_best_texture(matname, mesh_names, "d", filtered_files, main_prefix)
                    if tex_d:
                        connect_tex_to_socket(mat, kythera_group_node, "D", ["_D Map", "_D", "Diffuse", "Diffuse Texture"], tex_d, is_color=True, y_offset=0)

                    # 2. Texture M -> _M Map / Metallic (Non-Color)
                    tex_m = (json_textures.get('m') if json_textures else None) or find_best_texture(matname, mesh_names, "m", filtered_files, main_prefix)
                    if tex_m:
                        connect_tex_to_socket(mat, kythera_group_node, "M", ["_M Map", "_M", "Metallic"], tex_m, is_color=False, y_offset=-260)

                    # 3. Texture A -> _A Map / Ambient (Non-Color)
                    tex_a = (json_textures.get('a') if json_textures else None) or find_best_texture(matname, mesh_names, "a", filtered_files, main_prefix)
                    if tex_a:
                        connect_tex_to_socket(mat, kythera_group_node, "A", ["_A Map", "_A", "Ambient"], tex_a, is_color=False, y_offset=-520)

                    # 4. Texture N -> _N Map / Normal (Non-Color)
                    tex_n = (json_textures.get('n') if json_textures else None) or find_best_texture(matname, mesh_names, "n", filtered_files, main_prefix)
                    if tex_n:
                        connect_tex_to_socket(mat, kythera_group_node, "N", ["_N Map", "_N", "Normal"], tex_n, is_color=False, y_offset=-780)

            else:
                # --- LEGACY SHADER TEXTURE CONNECTION ---
                if is_alice_pingmu:
                    belt_path = get_belt_texture_path()
                    if belt_path and os.path.isfile(belt_path):
                        belt_img = bpy.data.images.load(belt_path, check_existing=True)
                        belt_img.colorspace_settings.name = 'sRGB'
                        belt_img.alpha_mode = 'CHANNEL_PACKED'

                        gmp_node = None
                        for node in mat.node_tree.nodes:
                            if "global material properties" in node.name.lower() or (node.type == 'GROUP' and node.node_tree and "global material properties" in node.node_tree.name.lower()):
                                gmp_node = node
                                break

                        if gmp_node:
                            target_socket = None
                            for inp in gmp_node.inputs:
                                if "plug shader output" in inp.name.lower():
                                    target_socket = inp
                                    break

                            if target_socket:
                                # Remove any previous links into Plug Shader Output
                                for l in list(mat.node_tree.links):
                                    if l.to_socket == target_socket:
                                        mat.node_tree.links.remove(l)

                                # Create or reuse image texture node for Belt.png
                                tex_node = mat.node_tree.nodes.get("Texture_Belt") or mat.node_tree.nodes.get("Face_D") or mat.node_tree.nodes.get("Texture_D")
                                if not tex_node:
                                    tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                                    tex_node.name = "Texture_Belt"
                                    tex_node.label = "Belt Texture"
                                tex_node.image = belt_img
                                tex_node.location = (gmp_node.location.x - 320, gmp_node.location.y - 100)
                                mat.node_tree.links.new(tex_node.outputs['Color'], target_socket)
                    continue

                is_face = any(k in combined_names for k in ["face", "eyebrow", "brow", "眉", "eye", "eyelash", "pupil", "iris", "highlight", "cara", "head", "rostro"])

                if is_face:
                    face_d = (json_textures.get('d') if json_textures else None) or find_best_texture(matname, mesh_names, "d", filtered_files, main_prefix)
                    if face_d:
                        img_path = os.path.join(tex_folder, face_d) if os.path.isfile(os.path.join(tex_folder, face_d)) else os.path.join(folder, face_d)
                        if os.path.isfile(img_path):
                            img = bpy.data.images.load(img_path, check_existing=True)
                            img.colorspace_settings.name = 'sRGB'
                            img.alpha_mode = 'CHANNEL_PACKED'
                            for node in mat.node_tree.nodes:
                                if node.type == 'TEX_IMAGE':
                                    n_low = node.name.lower()
                                    if any(k in n_low for k in ["face_d", "texture_d", "_d", "diffuse"]):
                                        node.image = img
                                    elif not node.image and "lightmap" not in n_low and "shadow" not in n_low:
                                        node.image = img

                    face_lm = (json_textures.get('n') if json_textures else None) or find_best_face_lightmap(matname, mesh_names, filtered_files, main_prefix)
                    if face_lm:
                        img_path = os.path.join(tex_folder, face_lm) if os.path.isfile(os.path.join(tex_folder, face_lm)) else os.path.join(folder, face_lm)
                        if os.path.isfile(img_path):
                            img_lm = bpy.data.images.load(img_path, check_existing=True)
                            img_lm.colorspace_settings.name = 'Non-Color'
                            img_lm.alpha_mode = 'CHANNEL_PACKED'
                            for node in mat.node_tree.nodes:
                                if node.type == 'TEX_IMAGE' and "lightmap" in node.name.lower():
                                    node.image = img_lm
                                elif node.type == 'GROUP' and node.node_tree and 'face lightmap' in node.node_tree.name.lower():
                                    for sub_node in node.node_tree.nodes:
                                        if sub_node.type == 'TEX_IMAGE':
                                            sub_node.image = img_lm

                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        node_name_lower = node.name.lower()
                        if node.image and (is_face and any(k in node_name_lower for k in ["face_d", "texture_d", "lightmap"])):
                            continue
                        
                        suffix = None
                        for s in ["d", "m", "a", "n"]:
                            if node_name_lower.endswith(f"_{s}") or node_name_lower.endswith(s) or f"_{s}_" in node_name_lower or f"_{s}." in node_name_lower or f"texture_{s}" in node_name_lower:
                                suffix = s
                                break
                        if not suffix:
                            if any(k in node_name_lower for k in ["face_d", "diffuse", "base_color", "color"]):
                                suffix = "d"
                            elif any(k in node_name_lower for k in ["metallic", "metal"]):
                                suffix = "m"
                            elif any(k in node_name_lower for k in ["ambient", "ao"]):
                                suffix = "a"
                            elif any(k in node_name_lower for k in ["normal", "nor"]):
                                suffix = "n"
                            elif "lightmap" in node_name_lower:
                                suffix = "lightmap"

                        if suffix == "lightmap":
                            best_tex = (json_textures.get('n') if json_textures else None) or find_best_face_lightmap(matname, mesh_names, filtered_files, main_prefix)
                        elif suffix:
                            best_tex = (json_textures.get(suffix) if json_textures else None) or find_best_texture(matname, mesh_names, suffix, filtered_files, main_prefix)
                        else:
                            best_tex = None

                        if best_tex:
                            img_path = os.path.join(tex_folder, best_tex) if os.path.isfile(os.path.join(tex_folder, best_tex)) else os.path.join(folder, best_tex)
                            if os.path.isfile(img_path):
                                img = bpy.data.images.load(img_path, check_existing=True)
                                img.colorspace_settings.name = 'sRGB' if suffix == 'd' else 'Non-Color'
                                img.alpha_mode = 'CHANNEL_PACKED'
                                node.image = img

                    elif node.type == 'GROUP' and node.node_tree and 'face lightmap' in node.node_tree.name.lower():
                        face_lm = (json_textures.get('n') if json_textures else None) or find_best_face_lightmap(matname, mesh_names, filtered_files, main_prefix)
                        if face_lm:
                            img_path = os.path.join(tex_folder, face_lm) if os.path.isfile(os.path.join(tex_folder, face_lm)) else os.path.join(folder, face_lm)
                            if os.path.isfile(img_path):
                                img = bpy.data.images.load(img_path, check_existing=True)
                                img.colorspace_settings.name = 'Non-Color'
                                img.alpha_mode = 'CHANNEL_PACKED'
                                for sub_node in node.node_tree.nodes:
                                    if sub_node.type == 'TEX_IMAGE':
                                        sub_node.image = img

            # If this is a Hair material and no hair texture was found,
            # remove its material slot (Slot 2+) from mesh objects so the hair inherits Slot 1 (only for ZZZ)
            if self.blender_operator.game_type == GameType.ZENLESS_ZONE_ZERO.name and "hair" in matname:
                has_hair_texture = any(node.type == 'TEX_IMAGE' and node.image for node in mat.node_tree.nodes)
                if not has_hair_texture:
                    for obj in bpy.data.objects:
                        if obj.type == 'MESH' and obj.data and hasattr(obj.data, "materials") and hasattr(obj.data, "polygons"):
                            for i in range(len(obj.data.materials) - 1, 0, -1):
                                if obj.data.materials[i] == mat:
                                    for p in obj.data.polygons:
                                        if p.material_index == i:
                                            p.material_index = 0
                                    obj.data.materials.pop(index=i)

        # Ensure all weapon mesh objects/slots are assigned a valid weapon material (Weapon 1)
        weapon_mats = [m for m in bpy.data.materials if (m.name.startswith("ZZZ") or m.name.startswith("Kythera")) and "weapon" in m.name.lower()]
        main_weapon_mat = weapon_mats[0] if weapon_mats else None

        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                o_lower = obj.name.lower()
                is_weapon_obj = any(k in o_lower for k in ["weapon", "wpn", "equip", "sword", "blade", "spear", "lance", "gun", "prop"])
                
                for slot in obj.material_slots:
                    if is_weapon_obj and (not slot.material or not slot.material.node_tree):
                        if main_weapon_mat:
                            slot.material = main_weapon_mat
                    elif slot.material and "weapon" in slot.material.name.lower():
                        nodes = slot.material.node_tree.nodes if slot.material.node_tree else []
                        has_tex = any(n.type == 'TEX_IMAGE' and n.image for n in nodes)
                        if not has_tex and main_weapon_mat and slot.material != main_weapon_mat:
                            slot.material = main_weapon_mat

        # Sync textures from main ZZZ materials to ZZZ Outline materials if any
        sync_zzz_outline_textures(folder=folder, filtered_files=filtered_files, main_prefix=main_prefix)


def get_belt_texture_path():
    current_dir = os.path.dirname(os.path.realpath(__file__))
    candidates = [
        os.path.normpath(os.path.join(current_dir, "..", "shaders", "zzz", "Belt.png")),
        os.path.normpath(os.path.join(current_dir, "shaders", "zzz", "Belt.png")),
        os.path.normpath(os.path.join(os.path.dirname(current_dir), "shaders", "zzz", "Belt.png")),
        os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(current_dir)), "shaders", "zzz", "Belt.png")),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return ""


def sync_zzz_outline_textures(folder=None, filtered_files=None, main_prefix=None):
    if not folder:
        from setup_wizard.import_order import get_cache, CHARACTER_MODEL_FOLDER_FILE_PATH
        cache_enabled = bpy.context.window_manager.cache_enabled if hasattr(bpy.context, 'window_manager') and hasattr(bpy.context.window_manager, 'cache_enabled') else True
        folder = get_cache(cache_enabled).get(CHARACTER_MODEL_FOLDER_FILE_PATH)

    if folder and not filtered_files:
        try:
            filtered_files = os.listdir(folder)
        except Exception:
            filtered_files = []

    outline_materials = [m for m in bpy.data.materials if "outlines" in m.name.lower() or m.name.endswith("Outlines") or "outline" in m.name.lower()]
    main_materials = [m for m in bpy.data.materials if (m.name.startswith("ZZZ") or m.name.startswith("Kythera")) and m.node_tree and "outline" not in m.name.lower()]

    for outline_mat in outline_materials:
        if not outline_mat.node_tree:
            continue
        
        outline_lower = outline_mat.name.lower()
        matched_main_mat = None

        if "hair" in outline_lower:
            cand = [m for m in main_materials if "hair" in m.name.lower()]
            if cand: matched_main_mat = cand[0]
        elif "face" in outline_lower:
            cand = [m for m in main_materials if "face" in m.name.lower()]
            if cand: matched_main_mat = cand[0]
        elif any(k in outline_lower for k in ["body 2", "body2", "body_2", "dress"]):
            cand = [m for m in main_materials if any(k in m.name.lower() for k in ["body 2", "body2", "body_2", "map2"])]
            if cand: matched_main_mat = cand[0]
        elif any(k in outline_lower for k in ["body 3", "body3", "body_3", "leg"]):
            cand = [m for m in main_materials if any(k in m.name.lower() for k in ["body 3", "body3", "body_3", "map3", "leg"])]
            if cand: matched_main_mat = cand[0]
        elif "body" in outline_lower:
            cand = [m for m in main_materials if any(k in m.name.lower() for k in ["body_1", "body1", "body 1"]) or ("body" in m.name.lower() and "2" not in m.name.lower() and "3" not in m.name.lower())]
            if cand: matched_main_mat = cand[0]
        elif "weapon" in outline_lower:
            cand = [m for m in main_materials if "weapon" in m.name.lower()]
            if cand: matched_main_mat = cand[0]

        if not matched_main_mat:
            out_words = [w for w in outline_lower.replace("zzz", "").replace("outlines", "").replace("outline", "").split("_") if w]
            best_match = None
            best_score = 0
            for m in main_materials:
                m_words = [w for w in m.name.lower().replace("zzz shader", "").replace("zzz", "").replace("kythera's", "").split("_") if w]
                score = sum(1 for w in out_words if w in m_words)
                if score > best_score:
                    best_score = score
                    best_match = m
            matched_main_mat = best_match

        # 1. Sync from matched main material
        if matched_main_mat and matched_main_mat.node_tree:
            main_images = {}
            for node in matched_main_mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    suffix = node.name.rsplit("_", 1)[-1].upper() if "_" in node.name else node.name.upper()
                    main_images[suffix] = node.image
                    main_images[node.name] = node.image
                    if "face_d" in node.name.lower() or suffix == "D":
                        main_images["FACE_D"] = node.image
                        main_images["D"] = node.image
                    if "lightmap" in node.name.lower():
                        main_images["LIGHTMAP"] = node.image

            for node in outline_mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    suf = node.name.rsplit("_", 1)[-1].upper() if "_" in node.name else node.name.upper()
                    if suf in main_images:
                        node.image = main_images[suf]
                    elif node.name in main_images:
                        node.image = main_images[node.name]
                    elif "lightmap" in node.name.lower() and "LIGHTMAP" in main_images:
                        node.image = main_images["LIGHTMAP"]
                    elif (suf == "D" or "d" in node.name.lower()) and "D" in main_images:
                        node.image = main_images["D"]

        # 2. Direct folder assignment if still unassigned and folder files are available
        if folder and filtered_files:
            import re
            def clean_tok(text):
                text = re.sub(r'zzz|kythera\'s|kythera|shader|mat|mat_|mesh|object|\+ t', '', text, flags=re.IGNORECASE)
                return set([t.lower() for t in re.split(r'[^a-zA-Z0-9]+', text) if len(t) > 1 and not t.isdigit()])

            for node in outline_mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and not node.image:
                    n_low = node.name.lower()
                    if any(k in n_low for k in ["lightmap", "lm"]):
                        target_lm = None
                        if "face" in outline_lower:
                            cand_lm = [f for f in filtered_files if "lightmap" in f.lower() and any(k in f.lower() for k in ["face", "head"])]
                            if cand_lm: target_lm = cand_lm[0]
                        if not target_lm:
                            cand_lm = [f for f in filtered_files if "lightmap" in f.lower()]
                            if cand_lm: target_lm = cand_lm[0]
                        if target_lm:
                            img = bpy.data.images.load(os.path.join(folder, target_lm), check_existing=True)
                            img.colorspace_settings.name = 'Non-Color'
                            img.alpha_mode = 'CHANNEL_PACKED'
                            node.image = img
                    else:
                        # Diffuse / D image
                        cat_tag = "face" if "face" in outline_lower else ("hair" if "hair" in outline_lower else ("body_2" if "2" in outline_lower else "body"))
                        cand_d = [f for f in filtered_files if f.lower().rsplit(".", 1)[0].endswith("_d") and cat_tag in f.lower()]
                        if not cand_d and cat_tag == "body":
                            cand_d = [f for f in filtered_files if f.lower().rsplit(".", 1)[0].endswith("_d") and "body" in f.lower() and "2" not in f.lower() and "3" not in f.lower()]
                        if cand_d:
                            img = bpy.data.images.load(os.path.join(folder, cand_d[0]), check_existing=True)
                            img.colorspace_settings.name = 'sRGB'
                            img.alpha_mode = 'CHANNEL_PACKED'
                            node.image = img


def create_outline_image_copy(src_image, colorspace_name='Non-Color', suffix='_outline_lightmap'):
    if not src_image:
        return None
    if colorspace_name == 'Non-Color':
        copy_name = f"{src_image.name}{suffix}"
        existing = bpy.data.images.get(copy_name)
        if existing:
            return existing
        img_copy = src_image.copy()
        img_copy.name = copy_name
        img_copy.colorspace_settings.name = 'Non-Color'
        img_copy.alpha_mode = 'CHANNEL_PACKED'
        return img_copy
    else:
        if src_image.colorspace_settings.name != 'sRGB':
            src_image.colorspace_settings.name = 'sRGB'
        return src_image


def sync_genshin_outline_textures():
    """
    Scans all Genshin outline materials in bpy.data.materials and syncs their Diffuse & Lightmap texture nodes
    with loaded textures from corresponding main character materials.
    Creates a duplicate image datablock for lightmaps set to Non-Color so main character diffuse textures remain in sRGB.
    """
    outline_materials = [
        m for m in bpy.data.materials if m.use_nodes and 
        (('outlines' in m.name.lower() or m.name.endswith('Outlines')) and
         'night_soul' not in m.name.lower() and
         m.name != 'HoYoverse - Genshin Outlines')
    ]
    main_materials = [
        m for m in bpy.data.materials if m.use_nodes and
        ('HoYoverse' in m.name or 'miHoYo' in m.name) and
        not ('outlines' in m.name.lower() or m.name.endswith('Outlines'))
    ]

    def get_all_tex_image_nodes(node_tree):
        nodes = []
        if not node_tree:
            return nodes
        for n in node_tree.nodes:
            if n.type == 'TEX_IMAGE':
                nodes.append(n)
            elif n.type == 'GROUP' and n.node_tree:
                nodes.extend(get_all_tex_image_nodes(n.node_tree))
        return nodes

    for outline_mat in outline_materials:
        outline_lower = outline_mat.name.lower()

        # 1. Direct name matching by stripping ' Outlines' or ' outlines'
        direct_base_name = outline_mat.name.replace(' Outlines', '').replace(' outlines', '')
        matched_main_mat = bpy.data.materials.get(direct_base_name)

        # 2. Body part keyword matching if direct match fails
        if not matched_main_mat:
            body_parts = ['hair', 'body3', 'body2', 'body1', 'body', 'dress', 'skirt', 'helmet', 'gauntlet', 'leather', 'glass', 'skillobj']
            for part in body_parts:
                if part in outline_lower:
                    cand = [m for m in main_materials if part in m.name.lower()]
                    if cand:
                        matched_main_mat = cand[0]
                        break

        # 3. Fuzzy word matching score fallback
        if not matched_main_mat:
            out_words = [w for w in outline_lower.replace("hoyoverse", "").replace("mihoyo", "").replace("genshin", "").replace("outlines", "").split() if w]
            best_match = None
            best_score = 0
            for m in main_materials:
                m_words = [w for w in m.name.lower().replace("hoyoverse", "").replace("mihoyo", "").replace("genshin", "").split() if w]
                score = sum(1 for w in out_words if w in m_words)
                if score > best_score:
                    best_score = score
                    best_match = m
            matched_main_mat = best_match

        if not matched_main_mat or not matched_main_mat.use_nodes:
            continue

        # Extract active Diffuse and Lightmap images from matched_main_mat
        main_tex_nodes = get_all_tex_image_nodes(matched_main_mat.node_tree)
        main_images = [n.image for n in main_tex_nodes if n.image]

        diffuse_image = None
        lightmap_image = None

        for n in main_tex_nodes:
            if not n.image:
                continue
            nid = (n.name + " " + (n.label or "")).lower()
            if 'diffuse' in nid or 'color' in nid or 'main_diffuse' in nid or 'tex' in nid:
                if not diffuse_image and 'lightmap' not in nid:
                    diffuse_image = n.image
            elif 'lightmap' in nid or 'ligntmap' in nid:
                if not lightmap_image:
                    lightmap_image = n.image

        if not diffuse_image and main_images:
            diffuse_image = main_images[0]
        if not lightmap_image:
            lightmap_image = diffuse_image

        if not diffuse_image:
            part_name = outline_mat.name.split()[-2] if len(outline_mat.name.split()) >= 2 else ""
            if part_name:
                diffuse_image = next((img for img in bpy.data.images if part_name.lower() in img.name.lower() and 'diffuse' in img.name.lower()), None)
                lightmap_image = next((img for img in bpy.data.images if part_name.lower() in img.name.lower() and ('lightmap' in img.name.lower() or 'ligntmap' in img.name.lower())), None) or diffuse_image

        if not diffuse_image:
            continue

        # Assign images to outline_mat's TEX_IMAGE nodes
        outline_tex_nodes = get_all_tex_image_nodes(outline_mat.node_tree)
        for node in outline_tex_nodes:
            nid = (node.name + " " + (node.label or "")).lower()
            if 'diffuse' in nid or 'srgb' in nid or 'color' in nid or 'main_diffuse' in nid or 'image texture' in nid:
                if 'lightmap' not in nid:
                    node.image = create_outline_image_copy(diffuse_image, 'sRGB', '_outline_diffuse')
            if 'lightmap' in nid or 'non-color' in nid or 'ligntmap' in nid:
                if lightmap_image:
                    node.image = create_outline_image_copy(lightmap_image, 'Non-Color', '_outline_lightmap')


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
        hair_num = None
        for p in re.split(r'[-_.\s]+', name_lower):
            if p.isdigit():
                hair_num = p
                break
        if not hair_num and ('02' in name_lower or '2' in name_lower or '后发' in name_lower):
            hair_num = '02'
        elif not hair_num:
            hair_num = '01'

        padded_num = hair_num.zfill(2)
        candidates = [f for f in image_files if 'hair' in f.lower() and matches_type(f) and (f'_{padded_num}_' in f.lower() or f'_{padded_num}.' in f.lower() or f'_{int(padded_num)}_' in f.lower() or f'_{int(padded_num)}.' in f.lower() or padded_num in f.lower())]
        if not candidates:
            candidates = [f for f in image_files if 'hair' in f.lower() and matches_type(f)]
        if candidates:
            return candidates[0]

    material_noise_tokens = {'player', 'oneiroi', 'oneir', 'mint', 'skin', 'lod0', 'skeleton', 'nte', 'shader', 'mi', 'mat', 'chastener'}

    clean_mat = name_lower.split('.')[0] if '.' in name_lower and name_lower.split('.')[-1].isdigit() else name_lower
    raw_tokens = [p for p in re.split(r'[-_.\s]+', clean_mat) if p]
    tokens = [p for p in raw_tokens if p not in material_noise_tokens]

    def score_file(f):
        if not matches_type(f) or (not is_eye_mat and is_eye_texture(f)):
            return -1000
        
        f_lower = f.lower()
        f_clean = f_lower.rsplit('.', 1)[0]
        f_tokens = set(re.split(r'[-_.\s]+', f_clean))

        score = 0
        for t in tokens:
            if t.isdigit():
                t_num = str(int(t))
                t_pad = t.zfill(2)
                if t in f_tokens or t_num in f_tokens or t_pad in f_tokens or f'_{t}_' in f_lower or f'_{t_pad}_' in f_lower or f'_{t_num}_' in f_lower or f'_{t_pad}.' in f_lower or f'_{t}.' in f_lower:
                    score += 50
                elif any(f'_{num.zfill(2)}_' in f_lower or f'_{int(num)}_' in f_lower for num in ['01', '02', '03', '04', '05', '1', '2', '3', '4', '5'] if int(num) != int(t)):
                    score -= 30
            else:
                if len(t) >= 2:
                    if t in f_tokens:
                        score += 20
                    elif t in f_lower:
                        score += 10
        return score

    best_file = None
    best_score = 0
    for f in image_files:
        sc = score_file(f)
        if sc > best_score:
            best_score = sc
            best_file = f

    if best_file and best_score > 0:
        return best_file

    candidates = [f for f in image_files if matches_type(f) and (is_eye_mat or not is_eye_texture(f))]
    return candidates[0] if candidates else (image_files[0] if image_files else None)


class NevernessToEvernessTextureImporterFacade(GameTextureImporter):
    def __init__(self, blender_operator, context):
        self.blender_operator = blender_operator
        self.context = context

    def import_textures(self):
        op = self.blender_operator
        cache_enabled = self.context.window_manager.cache_enabled

        fp = getattr(op, 'filepath', '') or getattr(op, 'import_path', '') or getattr(op, 'directory', '')
        folder = op.file_directory \
            or get_cache(cache_enabled).get(CHARACTER_MODEL_FOLDER_FILE_PATH) \
            or get_cache(cache_enabled).get(NEVERNESS_TO_EVERNESS_ROOT_FOLDER_FILE_PATH) \
            or get_active_character_directory() \
            or self.context.scene.get("setup_wizard_imported_model_dir")

        if not folder and fp:
            folder = fp if os.path.isdir(fp) else os.path.dirname(fp)

        if not folder:
            for img in bpy.data.images:
                if img.filepath and os.path.exists(bpy.path.abspath(img.filepath)):
                    cand = os.path.dirname(bpy.path.abspath(img.filepath))
                    if os.path.isdir(cand):
                        folder = cand
                        set_active_character_directory(folder)
                        break

        has_textures = False
        if folder and os.path.isdir(folder):
            try:
                has_textures = any(f.lower().endswith(('.png', '.tga', '.dds', '.jpg', '.jpeg', '.webp')) for f in os.listdir(folder))
            except Exception:
                has_textures = False

        if not folder or not os.path.isdir(folder) or not has_textures:
            print(f"[DEBUG] Character texture folder not set or valid. Prompting user via INVOKE_DEFAULT.")
            bpy.ops.genshin.import_textures(
                'INVOKE_DEFAULT',
                next_step_idx=self.blender_operator.next_step_idx,
                file_directory=self.blender_operator.file_directory,
                invoker_type=self.blender_operator.invoker_type,
                high_level_step_name=self.blender_operator.high_level_step_name,
                game_type=self.blender_operator.game_type,
            )
            return {'FINISHED'}

        from setup_wizard.utils.nte_json_parser import load_nte_character_data, get_nte_material_data

        database = load_nte_character_data(folder)
        image_files = database.get("image_files_list", [])
        if not image_files and os.path.isdir(folder):
            image_files = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.tga', '.dds', '.jpg', '.jpeg', '.webp'))]

        for mat in bpy.data.materials:
            if not mat.use_nodes or not mat.node_tree or mat.name == '材质球' or 'touming' in mat.name.lower():
                continue

            mat_name_lower = mat.name.lower()

            if any(k in mat_name_lower for k in ["common_face", "common_face_mask", "face_mask", "facemask"]):
                from setup_wizard.replace_default_materials_setup.game_default_material_replacers import setup_common_face_material
                setup_common_face_material(mat, folder=folder, image_files=image_files)
                continue

            if 'gaoguang' in mat_name_lower:
                candidates = [f for f in image_files if 'face' in f.lower() and any(dk in f.lower() for dk in ['_d.', '_d_', '_diff', 'face_d', 'd_01', 'd_02'])]
                specific_candidates = [f for f in candidates if not any(k in f.lower() for k in ['common', 'touming', 'default', 'dummy', 'transparent', 'bantou'])]
                best_diff = specific_candidates[0] if specific_candidates else (candidates[0] if candidates else None)
                if not best_diff:
                    candidates = [f for f in image_files if 'face' in f.lower()]
                    specific_candidates = [f for f in candidates if not any(k in f.lower() for k in ['common', 'touming', 'default', 'dummy', 'transparent', 'bantou'])]
                    best_diff = specific_candidates[0] if specific_candidates else (candidates[0] if candidates else None)
                if best_diff:
                    img_path = os.path.join(folder, best_diff)
                    if os.path.isfile(img_path):
                        img = bpy.data.images.load(img_path, check_existing=True)
                        for node in mat.node_tree.nodes:
                            if node.type == 'TEX_IMAGE':
                                node.image = img
                continue

            mat_info = get_nte_material_data(mat.name, database)
            tex_data = mat_info.get("textures", {}) if mat_info else {}

            if mat_info:
                best_diff = tex_data.get("diffuse")
                best_mask = tex_data.get("lightmap")
                best_id = tex_data.get("id")
                best_norm = tex_data.get("normal")
            else:
                best_diff = find_nte_texture_for_material(mat.name, 'd', image_files)
                best_mask = find_nte_texture_for_material(mat.name, 'm', image_files)
                best_id = find_nte_texture_for_material(mat.name, 'id', image_files)
                best_norm = find_nte_texture_for_material(mat.name, 'n', image_files)

            for node in mat.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree:
                    ng_name = node.node_tree.name
                    if ng_name in ['异环-头发', '异环-身体', '异环-面部']:
                        if ng_name == '异环-头发' or any(k in mat_name_lower for k in ['hair', 'pelo', '前发', '后发']):
                            target_socket = node.inputs.get('基础色') or node.inputs.get('Color') or node.inputs.get('Input')
                        elif ng_name == '异环-面部' or any(k in mat_name_lower for k in ['face', 'cara', '面']):
                            target_socket = node.inputs.get('Color') or node.inputs.get('Input') or node.inputs.get('基础色')
                        else:
                            target_socket = node.inputs.get('Input') or node.inputs.get('Color') or node.inputs.get('基础色')

                        if best_diff and target_socket and not target_socket.is_linked:
                            img_path = os.path.join(folder, best_diff)
                            if os.path.isfile(img_path):
                                img = bpy.data.images.load(img_path, check_existing=True)
                                tex_node = next((n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image == img), None)
                                if not tex_node:
                                    tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                                    tex_node.image = img
                                    tex_node.location = (node.location.x - 320, node.location.y)
                                mat.node_tree.links.new(tex_node.outputs['Color'], target_socket)

                        mask_socket = node.inputs.get('M') or node.inputs.get('MASK') or node.inputs.get('Mask')
                        if mask_socket and not mask_socket.is_linked:
                            if best_mask:
                                img_path = os.path.join(folder, best_mask)
                                if os.path.isfile(img_path):
                                    img = bpy.data.images.load(img_path, check_existing=True)
                                    img.colorspace_settings.name = 'Non-Color'
                                    tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                                    tex_node.image = img
                                    tex_node.location = (node.location.x - 320, node.location.y - 220)
                                    mat.node_tree.links.new(tex_node.outputs['Color'], mask_socket)

                        id_socket = node.inputs.get('ID') or node.inputs.get('Id') or node.inputs.get('id')
                        if id_socket and not id_socket.is_linked:
                            if best_id:
                                img_path = os.path.join(folder, best_id)
                                if os.path.isfile(img_path):
                                    img = bpy.data.images.load(img_path, check_existing=True)
                                    img.colorspace_settings.name = 'Non-Color'
                                    tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                                    tex_node.image = img
                                    tex_node.location = (node.location.x - 320, node.location.y - 440)
                                    mat.node_tree.links.new(tex_node.outputs['Color'], id_socket)

                        # Apply JSON parameters to group inputs if available
                        if mat_info:
                            scalars = mat_info.get("scalars", {})
                            for s_name, s_val in scalars.items():
                                if s_name in node.inputs and isinstance(s_val, (int, float)):
                                    try:
                                        node.inputs[s_name].default_value = float(s_val)
                                    except Exception:
                                        pass

        from setup_wizard.replace_default_materials_setup.game_default_material_replacers import ensure_hair_white_texture
        ensure_hair_white_texture(folder, image_files)

        self.blender_operator.report({'INFO'}, 'Imported Neverness to Everness textures and JSON material data...')
        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx, 
            self.blender_operator.invoker_type, 
            file_path_to_cache=folder,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=self.blender_operator.game_type,
        )


class WutheringWavesTextureImporterFacade(GameTextureImporter):
    def __init__(self, blender_operator, context):
        self.blender_operator = blender_operator
        self.context = context

    def import_textures(self):
        from setup_wizard.utils.wuwa_texture_utils import (
            split_material_name,
            extract_character_name,
            make_texture_patterns,
            find_texture_for_slot,
            TEXTURE_TYPE_MAPPINGS_JAREDNYTS,
        )

        cache_enabled = self.context.window_manager.cache_enabled if hasattr(self.context, 'window_manager') and hasattr(self.context.window_manager, 'cache_enabled') else True
        folder = getattr(self.blender_operator, 'filepath', None) \
            or getattr(self.blender_operator, 'file_directory', None) \
            or get_cache(cache_enabled).get(CHARACTER_MODEL_FOLDER_FILE_PATH) \
            or get_active_character_directory()

        if folder and os.path.isfile(folder):
            folder = os.path.dirname(folder)

        if not folder or not os.path.isdir(folder):
            self.blender_operator.report({'WARNING'}, f"Texture folder not found: {folder}")
            NextStepInvoker().invoke(
                self.blender_operator.next_step_idx, 
                self.blender_operator.invoker_type, 
                high_level_step_name=self.blender_operator.high_level_step_name,
                game_type=self.blender_operator.game_type,
            )
            return

        set_active_character_directory(folder)

        from setup_wizard.utils.wuwa_texture_utils import (
            split_material_name,
            extract_character_name,
            make_texture_patterns,
            find_texture_for_slot,
            load_image_safely,
            load_wuwa_json_mappings,
            TEXTURE_TYPE_MAPPINGS_JAREDNYTS,
        )

        all_texture_files = []
        for root, _, files in os.walk(folder):
            for file_name in files:
                if any(file_name.lower().endswith(ext) for ext in ['.png', '.tga', '.dds', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp']):
                    all_texture_files.append(file_name)

        if not all_texture_files:
            self.blender_operator.report({'WARNING'}, f"No texture image files found in: {folder}")

        json_mappings = load_wuwa_json_mappings(folder)

        has_het_any = False
        has_id_any = False
        has_rgid_any = False

        # Process each WW - * material in the scene
        for mat in bpy.data.materials:
            if not mat.name.startswith("WW - ") or not mat.use_nodes or not mat.node_tree:
                continue

            orig_name = mat.get("ww_original_name", "")
            base_part, version = split_material_name(mat.name)
            if mat.get("ww_base_part"):
                base_part = mat.get("ww_base_part")

            # Merge JSON mappings: base_part has aggregated entries (like _HET from sub-materials),
            # while orig_name has specific entries.
            mat_json_texs = {}
            if base_part and base_part.lower() in json_mappings:
                mat_json_texs.update(json_mappings[base_part.lower()])
            ver_key = f"{base_part}{version}".lower()
            if ver_key in json_mappings:
                mat_json_texs.update(json_mappings[ver_key])
            if orig_name and orig_name.lower() in json_mappings:
                mat_json_texs.update(json_mappings[orig_name.lower()])
            if base_part and base_part.lower() in json_mappings and "_HET" in json_mappings[base_part.lower()]:
                mat_json_texs.setdefault("_HET", json_mappings[base_part.lower()]["_HET"])

            tex_mode_prop = getattr(self.context.scene, "ww_tex_mode", "Default")
            is_default_mode = (tex_mode_prop == "Default")

            # Map texture slots
            for suffix, node_names in TEXTURE_TYPE_MAPPINGS_JAREDNYTS.items():
                img = None

                # In Version mode, check if a switch/damage/version variant exists first
                if not is_default_mode:
                    ver_patterns = make_texture_patterns(base_part, version, suffix, orig_name, mode=False)
                    img = find_texture_for_slot(all_texture_files, ver_patterns, folder, suffix)

                # Check JSON mapping
                if not img and suffix in mat_json_texs:
                    json_fname = mat_json_texs[suffix]
                    full_json_path = os.path.join(folder, json_fname)
                    img = load_image_safely(full_json_path, suffix)

                # Fallback to pattern matching if not in JSON or image not found
                if not img:
                    patterns = make_texture_patterns(base_part, version, suffix, orig_name, mode=is_default_mode)
                    img = find_texture_for_slot(all_texture_files, patterns, folder, suffix)

                if img:
                    # Assign to matching Image Texture nodes
                    for target_node_name in node_names:
                        target_node = mat.node_tree.nodes.get(target_node_name)
                        if target_node and target_node.type == 'TEX_IMAGE':
                            target_node.image = img
                            if suffix == '_HET':
                                has_het_any = True
                            elif suffix == '_ID':
                                has_id_any = True
                            elif suffix == '_RGID':
                                has_rgid_any = True

                    # Fallback match by node label or lowercase node name
                    for node in mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE':
                            n_label = (node.label or "").lower()
                            n_name = node.name.lower()
                            for expected_name in node_names:
                                if expected_name.lower() in [n_label, n_name]:
                                    node.image = img
                                    if suffix == '_HET':
                                        has_het_any = True
                                    elif suffix == '_ID':
                                        has_id_any = True
                                    elif suffix == '_RGID':
                                        has_rgid_any = True

            # Fallback for Face ID texture: If no Face ID image was found, use Face Diffuse image
            if "face" in mat.name.lower() or base_part.lower() in ["face", "head"]:
                mask_id_node = (
                    mat.node_tree.nodes.get("Mask ID")
                    or mat.node_tree.nodes.get("Face ID")
                    or mat.node_tree.nodes.get("Texture_ID")
                    or mat.node_tree.nodes.get("Face ID Texture")
                )
                if not mask_id_node:
                    for n in mat.node_tree.nodes:
                        if n.type == 'TEX_IMAGE':
                            n_low = (n.name + " " + (n.label or "")).lower()
                            if any(k in n_low for k in ["mask id", "face id", "texture_id", "face_id"]):
                                mask_id_node = n
                                break

                if mask_id_node and not mask_id_node.image:
                    face_diff_node = (
                        mat.node_tree.nodes.get("Face Diffuse")
                        or mat.node_tree.nodes.get("Face_D")
                        or mat.node_tree.nodes.get("Face Texture")
                        or mat.node_tree.nodes.get("Base Color")
                    )
                    if not face_diff_node:
                        for n in mat.node_tree.nodes:
                            if n.type == 'TEX_IMAGE' and n.image:
                                n_low = (n.name + " " + (n.label or "")).lower()
                                if any(k in n_low for k in ["face diffuse", "face_d", "face texture", "diffuse"]):
                                    face_diff_node = n
                                    break
                    if face_diff_node and face_diff_node.image:
                        mask_id_node.image = face_diff_node.image
                        has_id_any = True
                        print(f"[WUWA TEXTURES] Fallback: Assigned Face Diffuse ({face_diff_node.image.name}) to {mask_id_node.name} on {mat.name}")

            # Fix Eye UV map
            if "eye" in mat.name.lower() or base_part.lower() in ["eye", "eyes"]:
                for node in mat.node_tree.nodes:
                    if node.type == 'UVMAP':
                        node.uv_map = "UV2"

        # If HET texture was found, enable See Through node groups
        if has_het_any:
            for mat in bpy.data.materials:
                if mat.use_nodes and mat.node_tree:
                    for node in mat.node_tree.nodes:
                        if node.type == 'GROUP' and node.node_tree and "see through" in node.node_tree.name.lower():
                            node.mute = False

        # Set global switches if ID or RGID textures found
        g_props = bpy.data.node_groups.get("Global Material Properties Main")
        if g_props and hasattr(g_props, "nodes"):
            inp = g_props.nodes.get("Group Input")
            if inp:
                if has_id_any and "Use ID Color" in inp.outputs:
                    inp.outputs["Use ID Color"].default_value = 1.0
                if has_rgid_any and "Use New Shading" in inp.outputs:
                    inp.outputs["Use New Shading"].default_value = 1.0

        self.blender_operator.report({'INFO'}, 'Successfully imported and assigned Wuthering Waves textures!')
        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx, 
            self.blender_operator.invoker_type, 
            file_path_to_cache=folder,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=self.blender_operator.game_type,
        )



