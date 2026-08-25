# Author: michael-gh1

# Kudos to Modder4869 for introducing another way to get the real material name for Dress materials

import bpy
import json
import os

from setup_wizard.domain.game_types import GameType

# Config Constants
COMPONENT_NAME = 'component_name'
ENABLED = 'enabled'
CACHE_KEY = 'cache_key'
UI_ORDER_CONFIG_KEY = 'ui_order'
BLENDER_ADDON_CONFIG_FILENAME = f'character_setup_wizard.json'
BLENDER_ADDON_CONFIG_FILEPATH = os.path.join(bpy.utils.user_resource('CONFIG'), BLENDER_ADDON_CONFIG_FILENAME)

# Cache Constants
CHARACTER_MODEL_FOLDER_FILE_PATH = 'character_model_folder_file_path'

GENSHIN_IMPACT_ROOT_FOLDER_FILE_PATH = 'genshin_impact_root_folder_file_path'
GENSHIN_IMPACT_SHADER_FILE_PATH = "genshin_impact_shader_file_path"
GENSHIN_IMPACT_OUTLINES_FILE_PATH = 'genshin_impact_outlines_file_path'
HOYOVERSE_COMPOSITING_NODE_FILE_PATH = 'hoyoverse_compositing_node_file_path'
GENSHIN_RIGIFY_BONE_SHAPES_FILE_PATH = 'genshin_rigify_bone_shapes_file_path'

HONKAI_STAR_RAIL_ROOT_FOLDER_FILE_PATH = 'honkai_star_rail_folder_file_path'
HONKAI_STAR_RAIL_SHADER_FILE_PATH = 'honkai_star_rail_shader_file_path'
HONKAI_STAR_RAIL_OUTLINES_FILE_PATH = 'honkai_star_rail_outlines_file_path'

PUNISHING_GRAY_RAVEN_ROOT_FOLDER_FILE_PATH = 'punishing_gray_raven_folder_file_path'
PUNISHING_GRAY_RAVEN_SHADER_FILE_PATH = 'punishing_gray_raven_shader_file_path'
PUNISHING_GRAY_RAVEN_OUTLINES_FILE_PATH = 'punishing_gray_raven_outlines_file_path'
PUNISHING_GRAY_RAVEN_CHIBI_MESH_FILE_PATH = 'punishing_gray_raven_chibi_mesh_file_path'

ZENLESS_ZONE_ZERO_ROOT_FOLDER_FILE_PATH = 'zenless_zone_zero_folder_file_path'
ZENLESS_ZONE_ZERO_SHADER_FILE_PATH = 'zenless_zone_zero_shader_file_path'
ZENLESS_ZONE_ZERO_OUTLINES_FILE_PATH = 'zenless_zone_zero_outlines_file_path'

NEVERNESS_TO_EVERNESS_ROOT_FOLDER_FILE_PATH = 'neverness_to_everness_folder_file_path'
NEVERNESS_TO_EVERNESS_SHADER_FILE_PATH = 'neverness_to_everness_shader_file_path'
NEVERNESS_TO_EVERNESS_OUTLINES_FILE_PATH = 'neverness_to_everness_outlines_file_path'

WUTHERING_WAVES_ROOT_FOLDER_FILE_PATH = 'wuthering_waves_folder_file_path'
WUTHERING_WAVES_SHADER_FILE_PATH = 'wuthering_waves_shader_file_path'
WUTHERING_WAVES_OUTLINES_FILE_PATH = 'wuthering_waves_outlines_file_path'



class NextStepInvoker:
    def invoke(self, 
               current_step_index, 
               type, 
               file_path_to_cache=None, 
               high_level_step_name=None, 
               game_type: str=GameType.GENSHIN_IMPACT.name):
        if file_path_to_cache:
            set_active_character_directory(file_path_to_cache)
        if type == 'invoke_next_step':
            invoke_next_step(current_step_index, file_path_to_cache, game_type)
        elif type == 'invoke_next_step_ui':
            invoke_next_step_ui(high_level_step_name, current_step_index, game_type, file_directory=file_path_to_cache)
        else:
            print(f'Warning: Unknown type found when invoking: {type}')


def invoke_next_step(
        current_step_idx: int, 
        file_path_to_cache=None, 
        game_type: str=GameType.GENSHIN_IMPACT.name):
    path_to_setup_wizard_folder = os.path.dirname(os.path.abspath(__file__))
    file = open(f'{path_to_setup_wizard_folder}/config.json')
    config = json.load(file)

    if current_step_idx == 1:
        clear_cache()
    cache = get_cache()

    if current_step_idx <= 0 or current_step_idx + 1 > len(config):  # +1 because we have a step 0
        return

    # Cache only if running SetupWizard using F3 search menu. It should return before reaching here.
    previous_step = config.get(str(current_step_idx - 1))
    if file_path_to_cache and previous_step and previous_step[CACHE_KEY]:
        cache_previous_step_file_path(cache, previous_step, file_path_to_cache)
    
    if config[str(current_step_idx)][ENABLED]:
        cached_file_directory = cache.get(config[str(current_step_idx)][CACHE_KEY], '')
        execute_or_invoke = 'EXEC' if cached_file_directory else 'INVOKE'
        component_name = config[str(current_step_idx)][COMPONENT_NAME]
        function_to_use = ComponentFunctionFactory.create_component_function(component_name)

        if type(function_to_use) is bpy.ops._BPyOpsSubModOp:
            print(f'Calling {function_to_use} with {execute_or_invoke}_DEFAULT w/ cache: {cached_file_directory}')
            function_to_use(
                    f'{execute_or_invoke}_DEFAULT',
                    next_step_idx=current_step_idx + 1, 
                    file_directory=cached_file_directory,
                    invoker_type='invoke_next_step',
                    game_type=game_type,
            )
        else:
            function_to_use(current_step_idx + 1)
    else:
        invoke_next_step(current_step_idx + 1)


def invoke_next_step_ui(
        high_level_step_name, 
        current_step_index, 
        game_type: str=GameType.GENSHIN_IMPACT.name,
        file_directory=None):
    if not game_type:
        hl_low = (high_level_step_name or "").lower()
        if 'wuthering_waves' in hl_low or 'wuwa' in hl_low:
            game_type = GameType.WUTHERING_WAVES.name
        elif 'neverness' in hl_low or 'nte' in hl_low:
            game_type = GameType.NEVERNESS_TO_EVERNESS.name
        elif 'zenless' in hl_low or 'zzz' in hl_low:
            game_type = GameType.ZENLESS_ZONE_ZERO.name
        elif 'honkai' in hl_low or 'hsr' in hl_low:
            game_type = GameType.HONKAI_STAR_RAIL.name
        elif 'punishing' in hl_low or 'pgr' in hl_low:
            game_type = GameType.PUNISHING_GRAY_RAVEN.name
        elif hasattr(bpy.context, 'scene') and hasattr(bpy.context.scene, 'game_type_dropdown') and bpy.context.scene.game_type_dropdown:
            game_type = bpy.context.scene.game_type_dropdown
        else:
            game_type = GameType.GENSHIN_IMPACT.name

    print(f"[DEBUG] invoke_next_step_ui called: high_level_step_name='{high_level_step_name}', current_step_index={current_step_index}, game_type='{game_type}', file_directory='{file_directory}'")
    path_to_setup_wizard_folder = os.path.dirname(os.path.abspath(__file__))

    file = open(f'{path_to_setup_wizard_folder}/config_ui.json')
    config = json.load(file)
    ui_order = config.get(UI_ORDER_CONFIG_KEY, {})
    high_level_step_list = ui_order.get(high_level_step_name)

    if not high_level_step_list and high_level_step_name:
        if '.' in high_level_step_name:
            prefix, rest = high_level_step_name.split('.', 1)
            candidate = f"{prefix.upper()}_OT_{rest}"
            high_level_step_list = ui_order.get(candidate)
        elif '_OT_' in high_level_step_name:
            prefix, rest = high_level_step_name.split('_OT_', 1)
            candidate = f"{prefix.lower()}.{rest}"
            high_level_step_list = ui_order.get(candidate)

    print(f"[DEBUG] high_level_step_list for '{high_level_step_name}': {high_level_step_list}")

    if not high_level_step_list or current_step_index >= len(high_level_step_list) - 1:
        print(f"[DEBUG] Reached end of step list or high_level_step_list is empty. Returning.")
        return

    component_name = high_level_step_list[current_step_index + 1]
    print(f"[DEBUG] Next component to execute: '{component_name}' at index {current_step_index + 1}")
    operator_to_execute = ComponentFunctionFactory.create_component_function(component_name)
    print(f"[DEBUG] Executing operator: {operator_to_execute}")

    operator_to_execute(
        'EXEC_DEFAULT',
        next_step_idx=current_step_index + 1,
        invoker_type='invoke_next_step_ui',
        high_level_step_name=high_level_step_name,
        game_type=game_type,
        file_directory=file_directory or '',
    )


_ACTIVE_CHARACTER_DIRECTORY = ""


def set_active_character_directory(file_path_or_dir):
    global _ACTIVE_CHARACTER_DIRECTORY
    if not file_path_or_dir:
        return
    if os.path.isfile(file_path_or_dir):
        file_path_or_dir = os.path.dirname(file_path_or_dir)
    if os.path.isdir(file_path_or_dir):
        _ACTIVE_CHARACTER_DIRECTORY = file_path_or_dir
        print(f"[SETUP WIZARD] Set active character directory: {_ACTIVE_CHARACTER_DIRECTORY}")


def get_active_character_directory():
    global _ACTIVE_CHARACTER_DIRECTORY
    return _ACTIVE_CHARACTER_DIRECTORY


def get_shader_file_path(game_type: str, file_type: str = "main") -> str:
    """
    Directly resolves the bundled .blend shader file path for the given game type.
    """
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    shaders_dir = os.path.join(addon_dir, 'shaders')

    if game_type == GameType.GENSHIN_IMPACT.name:
        if file_type == 'outlines':
            p = os.path.join(shaders_dir, 'gi', 'HoYoverse - Genshin Impact Outlines v3.blend')
            if os.path.isfile(p):
                return p
        elif file_type == 'compositing':
            p = os.path.join(shaders_dir, 'gi', 'HoYoverse - Genshin Impact Post-Processing.blend')
            if os.path.isfile(p):
                return p
        p_main = os.path.join(shaders_dir, 'gi', 'HoYoverse - Genshin Impact v3.4.blend')
        if os.path.isfile(p_main):
            return p_main

    elif game_type == GameType.HONKAI_STAR_RAIL.name:
        p = os.path.join(shaders_dir, 'hsr', 'StellarToonV1.1.blend')
        if os.path.isfile(p):
            return p

    elif game_type == GameType.ZENLESS_ZONE_ZERO.name:
        if file_type == 'outlines':
            p_outlines = os.path.join(shaders_dir, 'zzz', 'ZZZ Setup File V2.0.blend')
            if os.path.isfile(p_outlines):
                return p_outlines
        
        selected_shader = getattr(bpy.context.scene, 'zzz_shader_type', 'KYTHERA') if hasattr(bpy, 'context') and hasattr(bpy.context, 'scene') else 'KYTHERA'

        if selected_shader == 'LEGACY':
            p_legacy = os.path.join(shaders_dir, 'zzz', 'ZZZ Setup File V2.0.blend')
            if os.path.isfile(p_legacy):
                return p_legacy
        else:
            p_v1 = os.path.join(shaders_dir, 'zzz', "Kythera's ZZZ Shader V1.0.blend")
            if os.path.isfile(p_v1):
                return p_v1
            p_ge = os.path.join(shaders_dir, 'zzz', "Kythera's ZZZ Shader GE432.blend")
            if os.path.isfile(p_ge):
                return p_ge
            p_legacy = os.path.join(shaders_dir, 'zzz', 'ZZZ Setup File V2.0.blend')
            if os.path.isfile(p_legacy):
                return p_legacy

    elif game_type == GameType.NEVERNESS_TO_EVERNESS.name:
        p = os.path.join(shaders_dir, 'nte', 'YH Shader.blend')
        if os.path.isfile(p):
            return p

    elif game_type == GameType.WUTHERING_WAVES.name:
        p = os.path.join(shaders_dir, 'wuwa', 'Gustling Waters.blend')
        if os.path.isfile(p):
            return p

    return ""


def read_from_blender_cache():
    return get_cache()


def get_cache(cache_enabled=True):
    active_dir = get_active_character_directory()
    if active_dir:
        return {
            CHARACTER_MODEL_FOLDER_FILE_PATH: active_dir,
            GENSHIN_IMPACT_ROOT_FOLDER_FILE_PATH: active_dir,
            GENSHIN_IMPACT_SHADER_FILE_PATH: active_dir,
            HONKAI_STAR_RAIL_ROOT_FOLDER_FILE_PATH: active_dir,
            HONKAI_STAR_RAIL_SHADER_FILE_PATH: active_dir,
            PUNISHING_GRAY_RAVEN_ROOT_FOLDER_FILE_PATH: active_dir,
            PUNISHING_GRAY_RAVEN_SHADER_FILE_PATH: active_dir,
            ZENLESS_ZONE_ZERO_ROOT_FOLDER_FILE_PATH: active_dir,
            ZENLESS_ZONE_ZERO_SHADER_FILE_PATH: active_dir,
            NEVERNESS_TO_EVERNESS_ROOT_FOLDER_FILE_PATH: active_dir,
            NEVERNESS_TO_EVERNESS_SHADER_FILE_PATH: active_dir,
            WUTHERING_WAVES_ROOT_FOLDER_FILE_PATH: active_dir,
            WUTHERING_WAVES_SHADER_FILE_PATH: active_dir,
        }
    return {}


def write_to_blender_cache(config):
    pass


def cache_previous_step_file_path(cache, last_step, file_path_to_cache):
    set_active_character_directory(file_path_to_cache)


def cache_using_cache_key(cache, cache_key, file_path_for_cache):
    set_active_character_directory(file_path_for_cache)


def clear_cache(game_type: str = None):
    pass




def material_replacer_get_actual_material_name_for_dress(material_name, character_type='AVATAR'):
    '''
    A wrapper function around get_actual_material_name_for_dress()
    The GameDefaultMaterialReplacer needs a template name to clone a material from the shader.
    A real Dress material uses the body-type shader, so return 'Body' if the actual material is a Dress.
    '''
    deduced_material_name_for_dress = get_actual_material_name_for_dress(material_name, character_type)

    if deduced_material_name_for_dress == 'Dress':
        return 'Body'
    return deduced_material_name_for_dress


'''
This method is a real mess, be prepared to spend some time if you're working with a Dress material!
There are a few issues that cause this:
1. AVATARs and NPCs/MONSTERs have different logic
2. Dress materials can be Body or Hair for AVATARs
3. Dress materials are only Body (to be confirmed) for NPCs/MONSTERs
'''
def get_actual_material_name_for_dress(material_name, character_type='AVATAR', is_skill_obj=False):
    # must check string instead of enum until this is moved out of import_order.py due to circular dependency
    if character_type == 'AVATAR' or character_type == 'HSR_AVATAR':
        for material in bpy.data.materials:
            if material_name in material.name:
                try:
                    # ex. 'Avatar_Lady_Pole_Rosaria_Tex_Body_Diffuse.png'
                    base_color_texture_image_name = material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].links[0].from_node.image.name_full
                    if is_skill_obj:
                        actual_material_name = base_color_texture_image_name.split('_')[-3]
                    else:
                        actual_material_name = base_color_texture_image_name.split('_')[-2]
                    
                    if 'Hair' in base_color_texture_image_name:
                        actual_material_name = 'Hair'
                    elif any(k in base_color_texture_image_name for k in ['Body2', 'Body02', 'Dress2', 'Dress02']):
                        actual_material_name = 'Body2'
                    elif any(k in base_color_texture_image_name for k in ['Body1', 'Body01', 'Dress1', 'Dress01']):
                        actual_material_name = 'Body1'
                    elif 'Body' in base_color_texture_image_name:
                        actual_material_name = 'Body'

                    # If actual_material_name is still a non-shader name (e.g. 'Dress', 'Dress01', 'Arm', 'Cloak', 'Veil'),
                    # default to 'Body1' for Dress01/1, 'Body2' for Dress02/2, or 'Body'
                    if actual_material_name not in ('Hair', 'Body', 'Body1', 'Body2', 'Face', 'Effect', 'Eff', 'Cloak'):
                        if any(k in material_name for k in ['Dress02', 'Dress2', 'Body02', 'Body2']):
                            actual_material_name = 'Body2'
                        elif any(k in material_name for k in ['Dress01', 'Dress1', 'Body01', 'Body1']):
                            actual_material_name = 'Body1'
                        else:
                            actual_material_name = 'Body'
                except (IndexError, AttributeError, KeyError, Exception):
                    # ex. 'Diffuse Texture.001'
                    actual_material_name = material_name.split('_')[-1]
                    if any(k in material_name or k in actual_material_name for k in ['Dress02', 'Dress2', 'Body02', 'Body2']):
                        actual_material_name = 'Body2'
                    elif any(k in material_name or k in actual_material_name for k in ['Dress01', 'Dress1', 'Body01', 'Body1']):
                        actual_material_name = 'Body1'
                    elif actual_material_name == 'Dress' or 'Dress' in material_name:
                        actual_material_name = 'Body'
                    print(f'WARNING: Fallback to applying "{actual_material_name}" onto "{material_name}". Image name is not parseable for: {material_name}')
                return actual_material_name
    else:
        # NPC/Monster?
        # ex. 'XXXX_Dress_Mat' or 'XXXX - Genshin Dress'
        is_shader_dress_material = 'Genshin Dress' in material_name  # 'XXXX - Genshin Dress'

        # is it the shader's Dress material? or are we checking the original material's name?
        actual_material_name = material_name.split(' ')[-1] if is_shader_dress_material else material_name.split('_')[-2] if material_name.split('_')[-2] != 'Mat' else material_name.split('_')[-1]
        if any(k in material_name or k in actual_material_name for k in ['Dress02', 'Dress2', 'Body02', 'Body2']):
            actual_material_name = 'Body2'
        elif any(k in material_name or k in actual_material_name for k in ['Dress01', 'Dress1', 'Body01', 'Body1']):
            actual_material_name = 'Body1'
        elif actual_material_name == 'Dress':
            actual_material_name = 'Body'
        print(f'WARNING: Fallback to applying "{actual_material_name}" onto "{material_name}". Image name is not parseable for: {material_name}')
        return actual_material_name


class ComponentFunctionFactory:
    @staticmethod
    def create_component_function(component_name):
        if component_name == 'import_materials':
            return bpy.ops.genshin.import_materials
        elif component_name == 'import_character_model':
            return bpy.ops.genshin.import_model
        elif component_name == 'replace_default_materials':
            return bpy.ops.genshin.replace_default_materials
        elif component_name == 'import_character_textures':
            return bpy.ops.genshin.import_textures
        elif component_name == 'import_outlines':
            return bpy.ops.genshin.import_outlines
        elif component_name == 'setup_geometry_nodes':
            return bpy.ops.genshin.setup_geometry_nodes
        elif component_name == 'import_outline_lightmaps':
            return bpy.ops.genshin.import_outline_lightmaps
        elif component_name == 'import_material_data':
            return bpy.ops.genshin.import_material_data
        elif component_name == 'fix_mouth_outlines':
            return bpy.ops.genshin.fix_mouth_outlines
        elif component_name == 'delete_empties':
            return bpy.ops.genshin.delete_empties
        elif component_name ==  'delete_specific_objects':
            return bpy.ops.genshin.delete_specific_objects
        elif component_name == 'fix_transformations':
            return bpy.ops.genshin.fix_transformations
        elif component_name == 'set_color_management_to_standard':
            return bpy.ops.genshin.set_color_management_to_standard
        elif component_name == 'set_up_screen_space_reflections':
            return bpy.ops.hoyoverse.set_up_screen_space_reflections
        elif component_name == 'vertex_paint_face_see_through_effect':
            return bpy.ops.hoyoverse.vertex_paint_face_see_through_effect
        elif component_name == 'zzz_setup_head_driver':
            return bpy.ops.zenless_zone_zero.setup_head_driver
        elif component_name == 'setup_head_driver':
            return bpy.ops.genshin.setup_head_driver
        elif component_name == 'rename_shader_materials':
            return bpy.ops.hoyoverse.rename_shader_materials
        elif component_name == 'rename_collection_and_rig':
            return bpy.ops.zenless_zone_zero.rename_collection_and_rig
        elif component_name == 'move_lighting_panel_to_char_collection':
            return bpy.ops.zenless_zone_zero.move_lighting_panel_to_char_collection
        elif component_name == 'set_up_armtwist_bone_constraints':
            return bpy.ops.genshin.set_up_armtwist_bone_constraints
        elif component_name == 'clear_cache_operator':
            return bpy.ops.genshin.clear_cache_operator
        elif component_name == 'change_bpy_context':
            return bpy.ops.genshin.change_bpy_context
        elif component_name == 'join_meshes_on_armature':
            return bpy.ops.hoyoverse.join_meshes_on_armature
        elif component_name == 'rig_character':
            return bpy.ops.hoyoverse.rig_character
        elif component_name == 'rootshape_filepath_setter':
            return bpy.ops.hoyoverse.rootshape_filepath_setter
        elif component_name == 'set_up_chibi_face_mesh':
            return bpy.ops.punishing_gray_raven.set_up_chibi_face_mesh
        elif component_name == 'import_chibi_face_texture':
            return bpy.ops.punishing_gray_raven.import_chibi_face_texture
        elif component_name == 'paint_vertex_colors':
            return bpy.ops.punishing_gray_raven.paint_vertex_colors
        elif component_name == 'compositing_node_setup':
            return bpy.ops.hoyoverse.custom_composite_node_setup
        elif component_name == 'post_processing_default_settings':
            return bpy.ops.hoyoverse.post_processing_default_settings
        elif component_name == 'nte_setup_outlines':
            return bpy.ops.neverness_to_everness.set_up_outlines
        elif component_name == 'nte_setup_compositor_nodes':
            return bpy.ops.neverness_to_everness.setup_compositor_nodes
        elif component_name == 'nte_finish_setup':
            return bpy.ops.neverness_to_everness.finish_setup
        elif component_name == 'wuwa_setup_head_driver':
            return bpy.ops.wuthering_waves.setup_head_driver
        elif component_name == 'wuwa_finish_setup':
            return bpy.ops.wuthering_waves.finish_setup
        else:
            raise Exception(f'Unknown component name passed into {__name__}: {component_name}')

