
import bpy
import os

from abc import ABC, abstractmethod
from bpy.types import Context, Operator

from setup_wizard.domain.shader_node_names import ShaderNodeNames
from setup_wizard.domain.shader_material import ShaderMaterial
from setup_wizard.domain.game_types import GameType
from setup_wizard.domain.shader_identifier_service import GenshinImpactShaders, HonkaiStarRailShaders, ShaderIdentifierService, \
    ShaderIdentifierServiceFactory
from setup_wizard.domain.shader_material_names import JaredNytsPunishingGrayRavenShaderMaterialNames, StellarToonShaderMaterialNames, V3_BonnyFestivityGenshinImpactMaterialNames, V2_FestivityGenshinImpactMaterialNames, \
    ShaderMaterialNames, Nya222HonkaiStarRailShaderMaterialNames, V4_PrimoToonGenshinImpactMaterialNames
from setup_wizard.domain.shader_material_name_keywords import ShaderMaterialNameKeywords

from setup_wizard.import_order import CHARACTER_MODEL_FOLDER_FILE_PATH, cache_using_cache_key, get_actual_material_name_for_dress, get_cache
import re
from setup_wizard.utils.genshin_body_part_deducer import get_npc_mesh_body_part_name


def matches_material_part_name(filename, part_name):
    """
    Checks if part_name appears as a distinct component in filename.
    Matches if part_name is followed by an underscore or dot, e.g.
    'Body' matches '_Body_Diffuse.png' or '_Body.png'
    but NOT '_Body2_Diffuse.png' or '_Body3_Diffuse.png'.
    """
    pattern = rf'{re.escape(part_name)}(?=[_.]|$)'
    return bool(re.search(pattern, filename))


from setup_wizard.texture_import_setup.texture_importer_types import TextureImporterFactory, TextureImporterType, TextureType, find_texture_nodes


class OutlineTextureImporter(ABC):
    def __init__(self, blender_operator: Operator, context: Context, material_names: ShaderMaterialNames, shader_node_names: ShaderNodeNames):
        self.blender_operator: Operator = blender_operator
        self.context: Context = context
        self.material_names = material_names
        self.shader_node_names = shader_node_names

    @abstractmethod
    def import_textures(self):
        raise NotImplementedError()

    def assign_lightmap_texture(self, character_model_folder_file_path, lightmap_files, body_part_material_name, actual_material_part_name, target_outline_material=None):
        shader_identifier_service = ShaderIdentifierServiceFactory.create(self.blender_operator.game_type)
        shader = shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)
        prefix = getattr(self.material_names, 'MATERIAL_PREFIX', '') if self.material_names else ''

        outline_material = target_outline_material or \
                           (bpy.data.materials.get(f'{prefix}{body_part_material_name} Outlines') if prefix else None) or \
                           next((m for m in bpy.data.materials if body_part_material_name.lower() in m.name.lower() and 'outlines' in m.name.lower()), None) or \
                           self.get_outline_material_fallback(body_part_material_name)

        if not outline_material:
            return

        possible_lightmap_names = ['Main_Lightmap', 'Lightmap (Non-Color) (Channel Packed)', 'Lightmap (Non-Color)', 'Outline_Lightmap', 'Lightmap_UV0', 'Lightmap', 'Image Texture.001', 'Image Texture.002', 'Image Texture']

        lightmap_node = None
        if outline_material.use_nodes:
            outline_nodes = find_texture_nodes(outline_material.node_tree, possible_lightmap_names)
            if outline_nodes:
                lightmap_node = outline_nodes[0]

        if not lightmap_node and outline_material.use_nodes:
            for node in outline_material.node_tree.nodes:
                if node.type == 'GROUP':
                    for inp in node.inputs:
                        if 'Lightmap' in inp.name and 'Alpha' in inp.name:
                            if inp.is_linked and inp.links[0].from_node.type == 'TEX_IMAGE':
                                lightmap_node = inp.links[0].from_node
                            break

        if not lightmap_node and outline_material.use_nodes:
            lightmap_node = outline_material.node_tree.nodes.new('ShaderNodeTexImage')
            for node in outline_material.node_tree.nodes:
                if node.type == 'GROUP':
                    for inp in node.inputs:
                        if 'Lightmap' in inp.name and 'Alpha' in inp.name:
                            outline_material.node_tree.links.new(lightmap_node.outputs['Alpha'], inp)

        # 1. Try to copy from base material
        base_material = None
        if outline_material:
            base_mat_name = outline_material.name.replace(' Outlines', '').replace(' outlines', '')
            base_material = bpy.data.materials.get(base_mat_name)
        if not base_material and prefix:
            base_material = bpy.data.materials.get(f'{prefix}{body_part_material_name}')
        if not base_material:
            base_material = next((m for m in bpy.data.materials if (body_part_material_name.lower() in m.name.lower() or actual_material_part_name.lower() in m.name.lower()) and 'outline' not in m.name.lower()), None)

        if base_material and base_material.use_nodes:
            base_nodes = find_texture_nodes(base_material.node_tree, possible_lightmap_names)
            base_lightmap_node = next((n for n in base_nodes if n.image), None)
            if not base_lightmap_node:
                possible_diffuse_names = ['Main_Diffuse', 'Diffuse (sRGB) (Channel Packed)', 'Diffuse (sRGB)', 'Outline_Diffuse', 'Diffuse_UV0', 'Diffuse', 'Image Texture', 'Image Texture.001']
                base_diff_nodes = find_texture_nodes(base_material.node_tree, possible_diffuse_names)
                base_lightmap_node = next((n for n in base_diff_nodes if n.image), None)
            if not base_lightmap_node:
                for n in base_material.node_tree.nodes:
                    if n.type == 'TEX_IMAGE' and n.image:
                        base_lightmap_node = n
                        break

            if base_lightmap_node and base_lightmap_node.image and lightmap_node:
                from setup_wizard.texture_import_setup.game_texture_importers import create_outline_image_copy
                lightmap_node.image = create_outline_image_copy(base_lightmap_node.image, 'Non-Color', '_outline_lightmap')
                self.blender_operator.report({'INFO'}, f'Assigned base material lightmap onto material "{outline_material.name}"')
                return

        # 2. Fallback: search loaded images in bpy.data.images
        loaded_img = next((img for img in bpy.data.images if (actual_material_part_name.lower() in img.name.lower() or body_part_material_name.lower() in img.name.lower()) and ('lightmap' in img.name.lower() or 'ligntmap' in img.name.lower())), None)
        if not loaded_img:
            loaded_img = next((img for img in bpy.data.images if (actual_material_part_name.lower() in img.name.lower() or body_part_material_name.lower() in img.name.lower()) and 'diffuse' in img.name.lower()), None)

        if loaded_img and lightmap_node:
            from setup_wizard.texture_import_setup.game_texture_importers import create_outline_image_copy
            lightmap_node.image = create_outline_image_copy(loaded_img, 'Non-Color', '_outline_lightmap')
            self.blender_operator.report({'INFO'}, f'Assigned loaded image lightmap onto material "{outline_material.name}"')
            return

        # 3. Fallback: search files in character directory
        lightmap_filenames = []
        if body_part_material_name == 'EffectHair':
            lightmap_filenames = [file for file in lightmap_files if 'EffectHair' in file]
        else:
            lightmap_filenames = [file for file in lightmap_files if matches_material_part_name(file, actual_material_part_name) and 'EffectHair' not in file]

        if lightmap_filenames and lightmap_node:
            self.assign_texture_to_node(lightmap_node, character_model_folder_file_path, lightmap_filenames[0])
            self.blender_operator.report({'INFO'}, f'Imported "{actual_material_part_name}" lightmap onto material "{outline_material.name}"')
        else:
            self.blender_operator.report({'WARNING'}, f'"{actual_material_part_name}" lightmap not found for material "{outline_material.name}".')

    def assign_diffuse_texture(self, character_model_folder_file_path, diffuse_files, body_part_material_name, actual_material_part_name, target_outline_material=None):
        shader_identifier_service = ShaderIdentifierServiceFactory.create(self.blender_operator.game_type)
        shader = shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)
        prefix = getattr(self.material_names, 'MATERIAL_PREFIX', '') if self.material_names else ''

        outline_material = target_outline_material or \
                           (bpy.data.materials.get(f'{prefix}{body_part_material_name} Outlines') if prefix else None) or \
                           next((m for m in bpy.data.materials if body_part_material_name.lower() in m.name.lower() and 'outlines' in m.name.lower()), None) or \
                           self.get_outline_material_fallback(body_part_material_name)

        if not outline_material:
            return

        possible_diffuse_names = ['Main_Diffuse', 'Diffuse (sRGB) (Channel Packed)', 'Diffuse (sRGB)', 'Outline_Diffuse', 'Diffuse_UV0', 'Diffuse', 'Image Texture', 'Image Texture.001']

        diffuse_node = None
        if outline_material.use_nodes:
            outline_nodes = find_texture_nodes(outline_material.node_tree, possible_diffuse_names)
            if outline_nodes:
                diffuse_node = outline_nodes[0]

        if not diffuse_node and outline_material.use_nodes:
            for node in outline_material.node_tree.nodes:
                if node.type == 'GROUP':
                    for inp in node.inputs:
                        if 'Diffuse' in inp.name and 'Alpha' in inp.name:
                            if inp.is_linked and inp.links[0].from_node.type == 'TEX_IMAGE':
                                diffuse_node = inp.links[0].from_node
                            break

        if not diffuse_node and outline_material.use_nodes:
            diffuse_node = outline_material.node_tree.nodes.new('ShaderNodeTexImage')
            for node in outline_material.node_tree.nodes:
                if node.type == 'GROUP':
                    for inp in node.inputs:
                        if 'Diffuse' in inp.name and 'Alpha' in inp.name:
                            outline_material.node_tree.links.new(diffuse_node.outputs['Alpha'], inp)

        # 1. Try to copy from base material
        base_material = None
        if outline_material:
            base_mat_name = outline_material.name.replace(' Outlines', '').replace(' outlines', '')
            base_material = bpy.data.materials.get(base_mat_name)
        if not base_material and prefix:
            base_material = bpy.data.materials.get(f'{prefix}{body_part_material_name}')
        if not base_material:
            base_material = next((m for m in bpy.data.materials if (body_part_material_name.lower() in m.name.lower() or actual_material_part_name.lower() in m.name.lower()) and 'outline' not in m.name.lower()), None)

        if base_material and base_material.use_nodes:
            base_nodes = find_texture_nodes(base_material.node_tree, possible_diffuse_names)
            base_diffuse_node = next((n for n in base_nodes if n.image), None)
            if not base_diffuse_node:
                for n in base_material.node_tree.nodes:
                    if n.type == 'TEX_IMAGE' and n.image:
                        base_diffuse_node = n
                        break

            if base_diffuse_node and base_diffuse_node.image and diffuse_node:
                diffuse_node.image = base_diffuse_node.image
                self.blender_operator.report({'INFO'}, f'Assigned base material diffuse onto material "{outline_material.name}"')
                return

        # 2. Fallback: search loaded images in bpy.data.images
        loaded_img = next((img for img in bpy.data.images if (actual_material_part_name.lower() in img.name.lower() or body_part_material_name.lower() in img.name.lower()) and 'diffuse' in img.name.lower()), None)
        if loaded_img and diffuse_node:
            diffuse_node.image = loaded_img
            self.blender_operator.report({'INFO'}, f'Assigned loaded image diffuse onto material "{outline_material.name}"')
            return

        # 3. Fallback: search files in character directory
        diffuse_filenames = []
        if body_part_material_name == 'EffectHair':
            diffuse_filenames = [file for file in diffuse_files if 'EffectHair' in file]
        else:
            diffuse_filenames = [file for file in diffuse_files if matches_material_part_name(file, actual_material_part_name) and 'EffectHair' not in file]

        if diffuse_filenames and diffuse_node:
            self.assign_texture_to_node(diffuse_node, character_model_folder_file_path, diffuse_filenames[0])
            self.blender_operator.report({'INFO'}, f'Imported "{actual_material_part_name}" diffuse onto material "{outline_material.name}"')
        else:
            self.blender_operator.report({'INFO'}, f'"{actual_material_part_name}" diffuse not found for material "{outline_material.name}"')

    def assign_texture_to_node(self, node, character_model_folder_file_path, texture_file_name):
        texture_img_path = os.path.normpath(os.path.join(character_model_folder_file_path, texture_file_name))
        texture_img = bpy.data.images.get(texture_file_name)
        if not texture_img:
            texture_img = bpy.data.images.load(filepath=texture_img_path, check_existing=True)
        texture_img.alpha_mode = 'CHANNEL_PACKED'
        node.image = texture_img

    def get_outline_material_fallback(self, body_part_material_name):
        prefix = getattr(self.material_names, 'MATERIAL_PREFIX', '') if self.material_names else ''
        shader_material = (bpy.data.materials.get(f'{prefix}{body_part_material_name}') if prefix else None) or \
                          next((m for m in bpy.data.materials if body_part_material_name.lower() in m.name.lower() and 'outline' not in m.name.lower()), None)
        if shader_material:
            return ShaderMaterial(shader_material, self.shader_node_names).get_outlines_material()
        return None

class OutlineTextureImporterFactory:
    def create(game_type: GameType, blender_operator: Operator, context: Context):
        shader_identifier_service: ShaderIdentifierService = ShaderIdentifierServiceFactory.create(game_type)
        shader = shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)
        if shader is None and game_type == GameType.ZENLESS_ZONE_ZERO.name:
            from setup_wizard.domain.game_shaders import ZenlessZoneZeroShaders
            shader = ZenlessZoneZeroShaders.V1_ZENLESS_ZONE_ZERO_SHADER
        shader_node_names = shader_identifier_service.get_shader_node_names(shader)

        # Because we inject the GameType via StringProperty, we need to compare using the Enum's name (a string)
        if game_type == GameType.GENSHIN_IMPACT.name:
            if shader is GenshinImpactShaders.V1_GENSHIN_IMPACT_SHADER or shader is GenshinImpactShaders.V2_GENSHIN_IMPACT_SHADER:
                material_names = V2_FestivityGenshinImpactMaterialNames
            elif shader is GenshinImpactShaders.V3_GENSHIN_IMPACT_SHADER:
                material_names = V3_BonnyFestivityGenshinImpactMaterialNames
            else:
                material_names = V4_PrimoToonGenshinImpactMaterialNames
            return GenshinImpactOutlineTextureImporter(blender_operator, context, material_names, shader_node_names)
        elif game_type == GameType.HONKAI_STAR_RAIL.name:
            if shader is HonkaiStarRailShaders.NYA222_HONKAI_STAR_RAIL_SHADER:
                return HonkaiStarRailOutlineTextureImporter(blender_operator, context, Nya222HonkaiStarRailShaderMaterialNames, shader_node_names)
            else:  # is HonkaiStarRailShaders.STELLARTOON_HONKAI_STAR_RAIL_SHADER
                return HonkaiStarRailOutlineTextureImporter(blender_operator, context, StellarToonShaderMaterialNames, shader_node_names)
        elif game_type == GameType.PUNISHING_GRAY_RAVEN.name:
            return PunishingGrayRavenOutlineTextureImporter(blender_operator, context, shader_node_names)
        elif game_type == GameType.ZENLESS_ZONE_ZERO.name:
            return ZenlessZoneZeroOutlineTextureImporter(blender_operator, context, shader_node_names)
        elif game_type == GameType.NEVERNESS_TO_EVERNESS.name:
            return NevernessToEvernessOutlineTextureImporter(blender_operator, context, shader_node_names)
        elif game_type == GameType.WUTHERING_WAVES.name:
            return WutheringWavesOutlineTextureImporter(blender_operator, context, shader_node_names)
        else:
            raise Exception(f'Unknown {GameType}: {game_type}')



class GenshinImpactOutlineTextureImporter(OutlineTextureImporter):
    SET_UP_MONSTER_AS_PLAYABLE_CHARACTER = [
        'LaSignora'
    ]

    def __init__(self, blender_operator, context, material_names, shader_node_names):
        super().__init__(blender_operator, context, material_names, shader_node_names)
        self.material_names = material_names

    def import_textures(self):
        cache_enabled = self.context.window_manager.cache_enabled
        character_model_folder_file_path = self.blender_operator.file_directory \
            or get_cache(cache_enabled).get(CHARACTER_MODEL_FOLDER_FILE_PATH) \
            or os.path.dirname(self.blender_operator.filepath)

        if not character_model_folder_file_path:
            bpy.ops.genshin.import_outline_lightmaps(
                'INVOKE_DEFAULT',
                next_step_idx=self.blender_operator.next_step_idx, 
                file_directory=self.blender_operator.file_directory,
                invoker_type=self.blender_operator.invoker_type,
                high_level_step_name=self.blender_operator.high_level_step_name,
                game_type=self.blender_operator.game_type,
            )
            return {'FINISHED'}
        
        for name, folder, files in os.walk(character_model_folder_file_path):
            diffuse_files = [file for file in files if 'Diffuse'.lower() in file.lower()]
            lightmap_files = [file for file in files if 'Lightmap'.lower() in file.lower() or 'Ligntmap'.lower() in file.lower()]  # Important typo check for: Wrioth
            prefix = getattr(self.material_names, 'MATERIAL_PREFIX', '')
            prefix_renamed = getattr(self.material_names, 'MATERIAL_PREFIX_AFTER_RENAME', '')
            outline_materials = [material for material in bpy.data.materials.values() if 
                                 material.name != self.material_names.OUTLINES and 
                                 material.name != self.material_names.NIGHT_SOUL_OUTLINES and
                                 self.material_names.VFX not in material.name and
                                 (('Outlines' in material.name and not self.material_names.NIGHT_SOUL_OUTLINES_SUFFIX in material.name) or 
                                 ShaderMaterial(material, self.shader_node_names).is_outlines_material())
            ]

            for outline_material in outline_materials:
                is_skill_obj = False
                if ShaderMaterialNameKeywords.SKILLOBJ in outline_material.name:
                    body_part_material_name = ' '.join(outline_material.name.split(' ')[-3:-1])  # ex. 'HoYoverse - Genshin SkillObj Fugu Outlines'
                    is_skill_obj = True
                else:
                    body_part_material_name = outline_material.name.split(' ')[-2]  # ex. 'miHoYo - Genshin Hair Outlines'
                character_type = None

                if [material for material in bpy.data.materials if material.name.startswith('NPC')]:
                    original_mesh_materials = [material for material in bpy.data.materials if material.name.startswith('NPC') and body_part_material_name in material.name]

                    if not original_mesh_materials:
                        continue

                    original_mesh_material = original_mesh_materials[0]
                    character_type = TextureImporterType.NPC
                elif [material for material in bpy.data.materials if material.name.startswith('Monster') and 
                    [playable_character_identifier for playable_character_identifier in self.SET_UP_MONSTER_AS_PLAYABLE_CHARACTER if playable_character_identifier not in material.name]
                    ]:
                    # Assuming all body parts are Body for now
                    # original_mesh_material = [material for material in bpy.data.materials if material.name.startswith('Monster') and 'Body' in material.name][0]
                    character_type = TextureImporterType.MONSTER
                else:
                    original_mesh_materials = [material for material in bpy.data.materials if 
                                               body_part_material_name in material.name and
                                               not material.name.startswith(prefix) and
                                               not (prefix_renamed and material.name.startswith(prefix_renamed))
                                               ]
                    character_type = TextureImporterType.AVATAR
                    original_mesh_material = original_mesh_materials[0] if original_mesh_materials else None

                if character_type == TextureImporterType.MONSTER:
                    actual_material_part_name = 'Tex'
                elif character_type == TextureImporterType.NPC and original_mesh_material:
                    actual_material_part_name = get_npc_mesh_body_part_name(original_mesh_material.name)
                else:
                    if original_mesh_material:
                        if is_skill_obj:
                            actual_material_part_name = get_actual_material_name_for_dress(original_mesh_material.name, character_type.name, is_skill_obj)
                        else:
                            actual_material_part_name = get_actual_material_name_for_dress(original_mesh_material.name, character_type.name)
                    else:
                        actual_material_part_name = body_part_material_name

                if 'Face' not in actual_material_part_name and 'Face' not in body_part_material_name:
                    self.assign_lightmap_texture(character_model_folder_file_path, lightmap_files, body_part_material_name, actual_material_part_name, target_outline_material=outline_material)
                    self.assign_diffuse_texture(character_model_folder_file_path, diffuse_files, body_part_material_name, actual_material_part_name, target_outline_material=outline_material)
            break  # IMPORTANT: We os.walk which also traverses through folders...we just want the files

        all_outlines = [m for m in bpy.data.materials if m.use_nodes and ('outlines' in m.name.lower() or m.name.endswith('Outlines')) and 'night_soul' not in m.name.lower() and m.name != 'HoYoverse - Genshin Outlines']
        for o_mat in all_outlines:
            part = o_mat.name.split()[-2] if len(o_mat.name.split()) >= 2 else ""
            self.assign_lightmap_texture(character_model_folder_file_path, lightmap_files, part, part, target_outline_material=o_mat)
            self.assign_diffuse_texture(character_model_folder_file_path, diffuse_files, part, part, target_outline_material=o_mat)

        if cache_enabled and character_model_folder_file_path:
            cache_using_cache_key(get_cache(cache_enabled), CHARACTER_MODEL_FOLDER_FILE_PATH, character_model_folder_file_path)


class HonkaiStarRailOutlineTextureImporter(OutlineTextureImporter):
    def __init__(self, blender_operator, context, shader_material_names, shader_node_names: ShaderNodeNames):
        super().__init__(blender_operator, context, shader_material_names, shader_node_names)
        self.shader_material_names = shader_material_names

    def import_textures(self):
        cache_enabled = self.context.window_manager.cache_enabled
        character_model_folder_file_path = self.blender_operator.file_directory \
            or get_cache(cache_enabled).get(CHARACTER_MODEL_FOLDER_FILE_PATH) \
            or os.path.dirname(self.blender_operator.filepath)

        if not character_model_folder_file_path:
            bpy.ops.genshin.import_outline_lightmaps(
                'INVOKE_DEFAULT',
                next_step_idx=self.blender_operator.next_step_idx, 
                file_directory=self.blender_operator.file_directory,
                invoker_type=self.blender_operator.invoker_type,
                high_level_step_name=self.blender_operator.high_level_step_name,
                game_type=self.blender_operator.game_type,
            )
            return {'FINISHED'}

        for name, folder, files in os.walk(character_model_folder_file_path):
            color_files = [file for file in files if 'Color'.lower() in file.lower()]
            lightmap_files = [file for file in files if 'LightMap'.lower() in file.lower() or 'FaceMap' in file.lower() or 'LigthMap'.lower() in file.lower()]  # that Lightmap typo is on purpose
            outline_materials = [material for material in bpy.data.materials.values() if 'outlines' in material.name.lower() and material.name != self.shader_material_names.OUTLINES]

            for outline_material in outline_materials:
                body_part_material_name = outline_material.name.split(' ')[-2]  # ex. 'miHoYo - Genshin Hair Outlines'
                original_mesh_material = [material for material in bpy.data.materials if f'Mat_{body_part_material_name}' in material.name]

                if original_mesh_material and 'EyeShadow' not in original_mesh_material and 'EyeShadow' not in body_part_material_name:
                    if 'Weapon' in body_part_material_name:
                        actual_material_part_name = 'Weapon'
                    elif 'Body' in body_part_material_name and 'Trans' in body_part_material_name:
                        actual_material_part_name = 'Body'
                    elif 'Body1' in body_part_material_name and [file for file in files if 'Body' in file and not 'Body1' in file and not 'Body2' in file]:
                        actual_material_part_name = 'Body'
                    else:
                        actual_material_part_name = body_part_material_name

                    self.assign_diffuse_texture(character_model_folder_file_path, color_files, body_part_material_name, actual_material_part_name)

                    # No Lightmap texture for Face (not sure if Face even needs Color diffuse either...)
                    if 'Face' not in original_mesh_material and 'Face' not in body_part_material_name:
                        self.assign_lightmap_texture(character_model_folder_file_path, lightmap_files, body_part_material_name, actual_material_part_name)
            break  # IMPORTANT: We os.walk which also traverses through folders...we just want the files

        if cache_enabled and character_model_folder_file_path:
            cache_using_cache_key(get_cache(cache_enabled), CHARACTER_MODEL_FOLDER_FILE_PATH, character_model_folder_file_path)

    def assign_lightmap_texture(self, character_model_folder_file_path, lightmap_files, body_part_material_name, actual_material_part_name):
        outline_material = bpy.data.materials.get(
            f'{self.shader_material_names.MATERIAL_PREFIX}{body_part_material_name} Outlines')
        texture_type = TextureType.HAIR if 'Hair' in body_part_material_name else TextureType.BODY

        # Genshin Note: Unable to determine between character/equipment textures for Monsters w/ equipment in same folder
        lightmap_filenames = [file for file in lightmap_files if actual_material_part_name in file]
        if not lightmap_filenames:
            print(f'Warn: Did not find lightmap for {actual_material_part_name} in {lightmap_files} when setting up outline textures. Falling back to base material.')
            base_material = bpy.data.materials.get(f'{self.shader_material_names.MATERIAL_PREFIX}{body_part_material_name}')
            shader_identifier_service = ShaderIdentifierServiceFactory.create(self.blender_operator.game_type)
            shader = shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)
            lightmap_node_name = shader_identifier_service.get_shader_texture_node_names(shader).LIGHTMAP
            if base_material and base_material.use_nodes:
                base_lightmap_node = base_material.node_tree.nodes.get(lightmap_node_name)
                if base_lightmap_node and base_lightmap_node.image:
                    hsr_texture_importer = TextureImporterFactory.create(TextureImporterType.HSR_AVATAR, GameType.HONKAI_STAR_RAIL)
                    hsr_texture_importer.set_lightmap_texture(texture_type, outline_material, base_lightmap_node.image)
            return
        lightmap_filename = lightmap_filenames[0]

        texture_img_path = os.path.normpath(os.path.join(character_model_folder_file_path, lightmap_filename))
        texture_img = bpy.data.images.get(lightmap_filename)
        if not texture_img:
            texture_img = bpy.data.images.load(filepath=texture_img_path, check_existing=True)
        texture_img.alpha_mode = 'CHANNEL_PACKED'

        hsr_texture_importer = TextureImporterFactory.create(TextureImporterType.HSR_AVATAR, GameType.HONKAI_STAR_RAIL)
        hsr_texture_importer.set_lightmap_texture(texture_type, outline_material, texture_img)

    def assign_diffuse_texture(self, character_model_folder_file_path, diffuse_files, body_part_material_name, actual_material_part_name):
        outline_material = bpy.data.materials.get(
            f'{self.shader_material_names.MATERIAL_PREFIX}{body_part_material_name} Outlines')
        texture_type = TextureType.HAIR if 'Hair' in body_part_material_name else TextureType.BODY

        diffuse_filenames = [file for file in diffuse_files if actual_material_part_name in file]
        if not diffuse_filenames:
            print(f'Warn: Did not find diffuse for {actual_material_part_name} in {diffuse_files} when setting up outline textures. Falling back to base material.')
            base_material = bpy.data.materials.get(f'{self.shader_material_names.MATERIAL_PREFIX}{body_part_material_name}')
            shader_identifier_service = ShaderIdentifierServiceFactory.create(self.blender_operator.game_type)
            shader = shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)
            diffuse_node_name = shader_identifier_service.get_shader_texture_node_names(shader).DIFFUSE
            if base_material and base_material.use_nodes:
                base_diffuse_node = base_material.node_tree.nodes.get(diffuse_node_name)
                if base_diffuse_node and base_diffuse_node.image:
                    hsr_texture_importer = TextureImporterFactory.create(TextureImporterType.HSR_AVATAR, GameType.HONKAI_STAR_RAIL)
                    hsr_texture_importer.set_diffuse_texture(texture_type, outline_material, base_diffuse_node.image)
            return
        diffuse_filename = diffuse_filenames[0]

        texture_img_path = os.path.normpath(os.path.join(character_model_folder_file_path, diffuse_filename))
        texture_img = bpy.data.images.get(diffuse_filename)
        if not texture_img:
            texture_img = bpy.data.images.load(filepath=texture_img_path, check_existing=True)
        texture_img.alpha_mode = 'CHANNEL_PACKED'

        hsr_texture_importer = TextureImporterFactory.create(TextureImporterType.HSR_AVATAR, GameType.HONKAI_STAR_RAIL)
        hsr_texture_importer.set_diffuse_texture(texture_type, outline_material, texture_img)


class PunishingGrayRavenOutlineTextureImporter(OutlineTextureImporter):
    def __init__(self, blender_operator, context, shader_node_names: ShaderNodeNames):
        super().__init__(blender_operator, context, JaredNytsPunishingGrayRavenShaderMaterialNames, shader_node_names)

    def import_textures(self):
        return


class ZenlessZoneZeroOutlineTextureImporter(OutlineTextureImporter):
    def __init__(self, blender_operator, context, shader_node_names: ShaderNodeNames):
        super().__init__(blender_operator, context, None, shader_node_names)

    def import_textures(self):
        from setup_wizard.import_order import get_cache, CHARACTER_MODEL_FOLDER_FILE_PATH
        cache_enabled = self.context.window_manager.cache_enabled if hasattr(self.context, 'window_manager') and hasattr(self.context.window_manager, 'cache_enabled') else True
        cached_folder = get_cache(cache_enabled).get(CHARACTER_MODEL_FOLDER_FILE_PATH) or getattr(self.blender_operator, 'file_directory', None)
        from setup_wizard.texture_import_setup.game_texture_importers import sync_zzz_outline_textures
        sync_zzz_outline_textures(folder=cached_folder)


class NevernessToEvernessOutlineTextureImporter(OutlineTextureImporter):
    def __init__(self, blender_operator, context, shader_node_names: ShaderNodeNames):
        super().__init__(blender_operator, context, None, shader_node_names)

    def import_textures(self):
        return


class WutheringWavesOutlineTextureImporter(OutlineTextureImporter):
    def __init__(self, blender_operator, context, shader_node_names: ShaderNodeNames):
        super().__init__(blender_operator, context, None, shader_node_names)

    def import_textures(self):
        return

