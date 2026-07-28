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
        elif game_type == GameType.NEVERNESS_TO_EVERNESS.name:
            return NevernessToEvernessTextureImporterFacade(blender_operator, context)
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

    def import_textures_from_folder(self, folder):
        files = os.listdir(folder)
        
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

        for filename in filtered_files:
            lower_name = filename.lower()
            if "weapon" in lower_name:
                if "weapon_2" in lower_name or "weapon2" in lower_name or "weapon 2" in lower_name or "weapon_map2" in lower_name or "weaponmap2" in lower_name or "map2" in lower_name or "map_2" in lower_name:
                    groups["Weapon_2"].append(filename)
                else:
                    groups["Weapon"].append(filename)
            elif "face" in lower_name:
                groups["Face"].append(filename)
            elif "hair" in lower_name:
                groups["Hair"].append(filename)
            elif "leg" in lower_name:
                groups["Leg"].append(filename)
            elif "tail" in lower_name:
                groups["Tail"].append(filename)
            elif "body_3" in lower_name or "body3" in lower_name or "body 3" in lower_name or "body_map3" in lower_name or "bodymap3" in lower_name or "map3" in lower_name or "map_3" in lower_name:
                groups["Body_3"].append(filename)
            elif "body_2" in lower_name or "body2" in lower_name or "body 2" in lower_name or "body_map2" in lower_name or "bodymap2" in lower_name or "map2" in lower_name or "map_2" in lower_name:
                groups["Body_2"].append(filename)
            elif "body" in lower_name:
                groups["Body_1"].append(filename)
            elif "map3" in lower_name or "map_3" in lower_name:
                groups["Body_3"].append(filename)
            elif "map2" in lower_name or "map_2" in lower_name:
                groups["Body_2"].append(filename)
            elif "map1" in lower_name or "map_1" in lower_name:
                groups["Body_1"].append(filename)

        for mat in bpy.data.materials:
            if not mat.name.startswith("ZZZ Shader") or not mat.node_tree:
                continue
            
            matname = mat.name.lower()
            group_keys = []
            if "hair" in matname:
                group_keys = ["Hair"]
            elif "eyebrow" in matname or "brow" in matname or "眉" in matname:
                group_keys = ["Face"]
            elif "face" in matname:
                group_keys = ["Face"]
            elif "eye" in matname:
                group_keys = ["Face"]
            elif "body" in matname or "leg" in matname or "tail" in matname:
                if "leg" in matname:
                    group_keys = ["Leg", "Body_3", "Body_2", "Body_1", "Tail"]
                elif "tail" in matname:
                    group_keys = ["Tail", "Body_3", "Body_2", "Body_1", "Leg"]
                elif "body 3" in matname or "body3" in matname or "body_3" in matname or "map3" in matname or "map_3" in matname or "_3_" in matname or matname.endswith("_3"):
                    group_keys = ["Body_3", "Leg", "Body_2", "Body_1", "Tail"]
                elif "body 2" in matname or "body2" in matname or "body_2" in matname or "map2" in matname or "map_2" in matname or "_2_" in matname or matname.endswith("_2"):
                    group_keys = ["Body_2", "Body_1", "Body_3", "Leg"]
                else:
                    group_keys = ["Body_1", "Body_2", "Body_3", "Leg"]
            elif "weapon" in matname:
                if "weapon 2" in matname or "weapon2" in matname or "weapon_2" in matname or "map2" in matname or "map_2" in matname or "_2_" in matname or matname.endswith("_2"):
                    group_keys = ["Weapon_2", "Weapon"]
                else:
                    group_keys = ["Weapon", "Weapon_2"]

            nodes = mat.node_tree.nodes
            for node in nodes:
                if node.type == 'TEX_IMAGE':
                    suffix = node.name.split("_")[-1] if "_" in node.name else node.name[-1]
                    target_suffix = f"_{suffix}.png"
                    
                    def get_best_match(target_suf):
                        candidates = []
                        for key in group_keys:
                            key_candidates = [f for f in groups[key] if f.lower().endswith(target_suf.lower())]
                            if key_candidates:
                                candidates = key_candidates
                                break
                        
                        if len(candidates) > 1:
                            sub_keywords = ["2", "3", "pro"]
                            mat_has_sub = [sub for sub in sub_keywords if sub in matname]
                            filtered_candidates = []
                            for f in candidates:
                                f_lower = f.lower()
                                f_clean = f_lower
                                if main_prefix and f_lower.startswith(main_prefix.lower()):
                                    f_clean = f_lower[len(main_prefix):]
                                
                                match = True
                                for sub in sub_keywords:
                                    if sub in mat_has_sub:
                                        if sub not in f_clean:
                                            match = False
                                            break
                                    else:
                                        if sub in f_clean:
                                            match = False
                                            break
                                if match:
                                    filtered_candidates.append(f)
                            if filtered_candidates:
                                list_to_score = filtered_candidates
                            else:
                                list_to_score = candidates

                            clean_mat_name = matname.replace("zzz shader", "").strip()
                            mat_words = [w for w in clean_mat_name.split("_") if w]

                            best_candidate = list_to_score[0]
                            best_score = -99999
                            for f in list_to_score:
                                f_clean = f.lower().rsplit(".", 1)[0]
                                for suffix_part in ["_d", "_m", "_a", "_n", "_map1", "_map2", "_map3", "_diffuse", "_normal", "_lightmap"]:
                                    if f_clean.endswith(suffix_part):
                                        f_clean = f_clean[:-len(suffix_part)]
                                f_words = [w for w in f_clean.split("_") if w]

                                matched_words = sum(1 for w in f_words if w in mat_words)
                                extra_words = sum(1 for w in f_words if w not in mat_words)
                                score = matched_words * 2 - extra_words
                                if score > best_score:
                                    best_score = score
                                    best_candidate = f
                            return best_candidate
                        return candidates[0] if candidates else None

                    found_img = get_best_match(target_suffix)
                    if not found_img:
                        found_img = get_best_match(f"{suffix}.png")

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

            # If this is a Hair material and no hair texture was found,
            # remove its material slot (Slot 2+) from mesh objects so the hair inherits Slot 1 (only for ZZZ)
            if self.blender_operator.game_type == GameType.ZENLESS_ZONE_ZERO.name and "hair" in matname:
                has_hair_texture = any(node.type == 'TEX_IMAGE' and node.image for node in nodes)
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
        weapon_mats = [m for m in bpy.data.materials if m.name.startswith("ZZZ Shader") and "weapon" in m.name.lower()]
        main_weapon_mat = weapon_mats[0] if weapon_mats else bpy.data.materials.get("ZZZ Shader Weapon")

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

        # Sync textures from main ZZZ materials to ZZZ Outline materials
        sync_zzz_outline_textures()


def sync_zzz_outline_textures():
    outline_materials = [m for m in bpy.data.materials if "outlines" in m.name.lower() or m.name.endswith("Outlines")]
    main_materials = [m for m in bpy.data.materials if m.name.startswith("ZZZ Shader") and m.node_tree]

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
        elif "body 2" in outline_lower or "body2" in outline_lower or "body_2" in outline_lower or "dress" in outline_lower:
            cand = [m for m in main_materials if "body 2" in m.name.lower() or "body2" in m.name.lower() or "body_2" in m.name.lower() or "map2" in m.name.lower()]
            if cand: matched_main_mat = cand[0]
        elif "body 3" in outline_lower or "body3" in outline_lower or "body_3" in outline_lower or "leg" in outline_lower:
            cand = [m for m in main_materials if "body 3" in m.name.lower() or "body3" in m.name.lower() or "body_3" in m.name.lower() or "map3" in m.name.lower() or "leg" in m.name.lower()]
            if cand: matched_main_mat = cand[0]
        elif "body" in outline_lower:
            cand = [m for m in main_materials if "body_1" in m.name.lower() or "body1" in m.name.lower() or "body 1" in m.name.lower() or ("body" in m.name.lower() and "2" not in m.name.lower() and "3" not in m.name.lower())]
            if cand: matched_main_mat = cand[0]
        elif "weapon" in outline_lower:
            cand = [m for m in main_materials if "weapon" in m.name.lower()]
            if cand: matched_main_mat = cand[0]

        if not matched_main_mat:
            out_words = [w for w in outline_lower.replace("zzz", "").replace("outlines", "").split("_") if w]
            best_match = None
            best_score = 0
            for m in main_materials:
                m_words = [w for w in m.name.lower().replace("zzz shader", "").split("_") if w]
                score = sum(1 for w in out_words if w in m_words)
                if score > best_score:
                    best_score = score
                    best_match = m
            matched_main_mat = best_match

        if matched_main_mat and matched_main_mat.node_tree:
            main_images = {}
            for node in matched_main_mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    suffix = node.name.rsplit("_", 1)[-1].upper() if "_" in node.name else node.name.upper()
                    main_images[suffix] = node.image
                    main_images[node.name] = node.image
                    if "D" in suffix or "DIFFUSE" in suffix or "MAIN" not in main_images:
                        main_images["MAIN"] = node.image

            for node in outline_mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    suffix = node.name.rsplit("_", 1)[-1].upper() if "_" in node.name else node.name.upper()
                    assigned_img = main_images.get(node.name) or main_images.get(suffix) or main_images.get("D") or main_images.get("MAIN")
                    if assigned_img:
                        node.image = assigned_img


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
        return True

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

    if any(k in name_lower for k in ['eye', '目', 'iris', 'pupil', 'eyelash', 'eyebrow', '眉毛', '睫毛']):
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

    if any(k in name_lower for k in ['down', '02', '_2', 'bottom', 'skirt', 'leg']):
        candidates = [f for f in image_files if ('_02_' in f.lower() or '_2_' in f.lower() or 'down' in f.lower() or 'body2' in f.lower()) and matches_type(f)]
        if not candidates:
            candidates = [f for f in image_files if '_02_' in f.lower() or '_2_' in f.lower()]
        if candidates:
            return candidates[0]

    if any(k in name_lower for k in ['up', '01', '_1', 'top', 'upper', 'body', 'skin', 'chastener_1']):
        candidates = [f for f in image_files if ('_01_' in f.lower() or '_1_' in f.lower() or 'up' in f.lower()) and matches_type(f)]
        if not candidates:
            candidates = [f for f in image_files if '_01_' in f.lower() or '_1_' in f.lower()]
        if candidates:
            return candidates[0]

    clean_parts = [p for p in name_lower.split('_') if p not in ['player', '075', '019', 'oneiroi', 'oneir', 'mint', 'skin', 'lod0', 'skeleton', 'nte', 'shader', 'mi', 'mat', 'chastener']]
    if clean_parts:
        candidates = [
            f for f in image_files
            if any(part in f.lower() for part in clean_parts) and matches_type(f)
        ]
        if candidates:
            return candidates[0]

    candidates = [f for f in image_files if matches_type(f)]
    return candidates[0] if candidates else (image_files[0] if image_files else None)



class NevernessToEvernessTextureImporterFacade(GameTextureImporter):
    def __init__(self, blender_operator, context):
        self.blender_operator = blender_operator
        self.context = context

    def import_textures(self):
        op = self.blender_operator

        fp = getattr(op, 'filepath', '') or getattr(op, 'import_path', '') or getattr(op, 'directory', '')
        folder = op.file_directory
        if not folder and fp:
            folder = fp if os.path.isdir(fp) else os.path.dirname(fp)

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

        import json
        files = os.listdir(folder)
        image_files = [f for f in files if f.lower().endswith(('.png', '.tga', '.dds', '.jpg', '.jpeg', '.webp'))]
        json_files = [f for f in files if f.lower().endswith('.json')]

        json_data_map = {}
        for jf in json_files:
            try:
                jpath = os.path.join(folder, jf)
                with open(jpath, 'r', encoding='utf-8') as f:
                    jcontent = json.load(f)
                    json_data_map[jf.lower()] = jcontent
            except Exception as ex:
                print(f"Notice: Reading JSON {jf}: {ex}")

        for mat in bpy.data.materials:
            if not mat.use_nodes or not mat.node_tree or mat.name == '材质球' or 'touming' in mat.name.lower():
                continue

            mat_name_lower = mat.name.lower()

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

                        best_diff = find_nte_texture_for_material(mat.name, 'd', image_files)

                        if best_diff and target_socket and not target_socket.is_linked:
                            img_path = os.path.join(folder, best_diff)
                            img = bpy.data.images.load(img_path, check_existing=True)

                            tex_node = next((n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image == img), None)
                            if not tex_node:
                                tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                                tex_node.image = img
                                tex_node.location = (node.location.x - 320, node.location.y)

                            mat.node_tree.links.new(tex_node.outputs['Color'], target_socket)

                        mask_socket = node.inputs.get('M') or node.inputs.get('MASK') or node.inputs.get('Mask')
                        if mask_socket and not mask_socket.is_linked:
                            best_mask = find_nte_texture_for_material(mat.name, 'm', image_files)
                            if best_mask:
                                img_path = os.path.join(folder, best_mask)
                                img = bpy.data.images.load(img_path, check_existing=True)
                                img.colorspace_settings.name = 'Non-Color'
                                tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                                tex_node.image = img
                                tex_node.location = (node.location.x - 320, node.location.y - 220)
                                mat.node_tree.links.new(tex_node.outputs['Color'], mask_socket)



        self.blender_operator.report({'INFO'}, 'Imported Neverness to Everness textures and JSON material data...')
        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx, 
            self.blender_operator.invoker_type, 
            file_path_to_cache=folder,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=self.blender_operator.game_type,
        )



