from enum import Enum, auto
from typing import List
import bpy

import os
import re
import json
from setup_wizard.domain.material_identifier_service import PunishingGrayRavenMaterialIdentifierService
from setup_wizard.domain.game_types import GameType
from setup_wizard.domain.shader_identifier_service import GenshinImpactShaders, HonkaiStarRailShaders, ShaderIdentifierService, \
    ShaderIdentifierServiceFactory
from setup_wizard.domain.shader_material_names import JaredNytsPunishingGrayRavenShaderMaterialNames, StellarToonShaderMaterialNames, V3_BonnyFestivityGenshinImpactMaterialNames, V2_FestivityGenshinImpactMaterialNames, \
    ShaderMaterialNames, Nya222HonkaiStarRailShaderMaterialNames, V4_PrimoToonGenshinImpactMaterialNames
from setup_wizard.domain.shader_node_names import JaredNyts_PunishingGrayRavenNodeNames, ShaderNodeNames, StellarToonShaderNodeNames
from setup_wizard.domain.shader_material_name_keywords import ShaderMaterialNameKeywords

from setup_wizard.import_order import get_actual_material_name_for_dress
from setup_wizard.texture_import_setup.texture_node_names import JaredNytsPunishingGrayRavenTextureNodeNames, Nya222HonkaiStarRailTextureNodeNames, StellarToonTextureNodeNames, TextureNodeNames, V4_GenshinImpactTextureNodeNames
from setup_wizard.texture_import_setup.original_texture_locator_utils import OriginalTextureLocatorUtils


def get_or_create_white_texture(name="White_Shadow_Ramp"):
    img = bpy.data.images.get(name)
    if not img:
        img = bpy.data.images.new(name, width=16, height=16, alpha=True)
    try:
        img.generated_color = (1.0, 1.0, 1.0, 1.0)
    except Exception:
        pass
    try:
        pixels = [1.0] * (len(img.pixels) if len(img.pixels) > 0 else 16 * 16 * 4)
        img.pixels[:] = pixels
    except Exception:
        pass
    img.colorspace_settings.name = 'sRGB'
    img.update()
    return img


def set_use_alpha_on_material(material, value=1.0):
    if not material or not material.use_nodes:
        return
    for node in material.node_tree.nodes:
        if 'Use Alpha' in node.inputs:
            node.inputs['Use Alpha'].default_value = value
        if node.type == 'GROUP' and node.node_tree:
            for sub_node in node.node_tree.nodes:
                if 'Use Alpha' in sub_node.inputs:
                    sub_node.inputs['Use Alpha'].default_value = value


def is_mat_part_match(mat_name, part):
    """
    Checks if a material name matches a body/dress part token exactly.
    Ensures 'dress' matches 'HoYoverse - Genshin Dress' but NOT 'HoYoverse - Genshin Dress01'.
    """
    m_low = mat_name.lower()
    part_clean = part.lower().replace('_', '')
    if bool(re.search(rf'(?:^|[\s\-_]){re.escape(part)}$', m_low)):
        return True
    m_tokens = re.split(r'[\s\-_]+', m_low)
    if m_tokens and m_tokens[-1].replace('_', '') == part_clean:
        return True
    return False


def find_all_image_nodes_by_category(node_tree, category):
    """
    Recursively finds ALL Image Texture nodes in node_tree and nested GROUP node_trees (e.g. Textures)
    belonging to a category ('diffuse', 'lightmap', 'normal', 'ramp').
    """
    found = []
    if not node_tree:
        return found

    for node in node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            node_id = (node.name + " " + (node.label or "")).lower()
            if category == 'diffuse':
                if 'diffuse' in node_id or 'main_diffuse' in node_id:
                    if not any(k in node_id for k in ['lightmap', 'normal', 'ramp', 'mask']):
                        found.append(node)
            elif category == 'lightmap':
                if 'lightmap' in node_id or 'main_lightmap' in node_id:
                    if not any(k in node_id for k in ['diffuse', 'normal', 'ramp', 'mask']):
                        found.append(node)
            elif category == 'normal':
                if 'normal' in node_id or 'main_normal' in node_id:
                    if not any(k in node_id for k in ['diffuse', 'lightmap', 'ramp', 'mask']):
                        found.append(node)
            elif category in ['ramp', 'shadow_ramp']:
                if 'ramp' in node_id or 'shadow' in node_id:
                    if not any(k in node_id for k in ['diffuse', 'lightmap', 'normal']):
                        found.append(node)

    for node in node_tree.nodes:
        if node.type == 'GROUP' and node.node_tree:
            ng_name = node.node_tree.name.lower()
            # NEVER recurse into Face Factor, Face Shader, or internal calculation node groups
            if any(ign in ng_name for ign in ['face factor', 'face shader', 'eyeshadow', 'gi face', 'primotoon', 'hoyotoon', 'outline']):
                continue
            sub_found = find_all_image_nodes_by_category(node.node_tree, category)
            for sub_node in sub_found:
                if sub_node not in found:
                    found.append(sub_node)

    return found


def sync_material_category_textures(material):
    """
    Ensures that for a given material, all Image Texture nodes in each category
    (diffuse, lightmap, normal map) share the active loaded texture for that category.
    """
    if not material or not hasattr(material, 'node_tree') or not material.node_tree:
        return

    m_low = material.name.lower()
    # Face, Pupil, Eye, Brow, Outlines must NEVER have their internal category textures synced
    if any(k in m_low for k in ['pupil', 'pupila', 'face', 'brow', 'eye', 'outlines', 'outline']):
        return

    diffuse_nodes = find_all_image_nodes_by_category(material.node_tree, 'diffuse')
    lightmap_nodes = find_all_image_nodes_by_category(material.node_tree, 'lightmap')
    normal_nodes = find_all_image_nodes_by_category(material.node_tree, 'normal')

    diffuse_img = next((n.image for n in diffuse_nodes if n.image and 'lightmap' not in n.image.name.lower() and 'normal' not in n.image.name.lower()), None)
    lightmap_img = next((n.image for n in lightmap_nodes if n.image and 'diffuse' not in n.image.name.lower() and 'normal' not in n.image.name.lower()), None)
    normal_img = next((n.image for n in normal_nodes if n.image and 'diffuse' not in n.image.name.lower() and 'lightmap' not in n.image.name.lower()), None)

    if diffuse_img:
        for n in diffuse_nodes:
            n.image = diffuse_img

    if lightmap_img:
        lightmap_img.colorspace_settings.name = 'Non-Color'
        for n in lightmap_nodes:
            n.image = lightmap_img

    if normal_img:
        normal_img.colorspace_settings.name = 'Non-Color'
        for n in normal_nodes:
            n.image = normal_img


def find_texture_nodes(node_tree, possible_names):
    """
    Recursively searches node_tree and nested GROUP node_trees (e.g. Textures, Shader Textures, HoYoToon)
    for Image Texture nodes matching possible_names (by exact name, label, or partial string match).
    Returns ALL matching ShaderNodeTexImage nodes.
    """
    found_nodes = []
    if not node_tree:
        return found_nodes

    # 1. Exact name/label match in current node_tree
    for node in node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            for name in possible_names:
                if name == node.name or (node.label and name == node.label):
                    if node not in found_nodes:
                        found_nodes.append(node)

    # 2. Case-insensitive / partial substring match for remaining nodes in current node_tree
    for node in node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node not in found_nodes:
            combined_name = (node.name + " " + (node.label or "")).lower()
            for name in possible_names:
                if name.lower() in combined_name:
                    if node not in found_nodes:
                        found_nodes.append(node)

    # 3. Recurse into nested GROUP nodes
    for node in node_tree.nodes:
        if node.type == 'GROUP' and node.node_tree:
            sub_found = find_texture_nodes(node.node_tree, possible_names)
            for sub_node in sub_found:
                if sub_node not in found_nodes:
                    found_nodes.append(sub_node)

    return found_nodes


def setup_crystal_material_nodes(crystal_material):
    """
    Applies the Crystal transparency shader setup:
    (Lightmap Color if present, else Diffuse Color) -> Separate Color (Red) -> Greater Than (0.5) -> Mix Shader (Factor)
    with Transparent BSDF (Shader 1) and Body Shader BSDF (Shader 2) -> Material Output (Surface).
    """
    if not crystal_material or not crystal_material.use_nodes or not crystal_material.node_tree:
        return

    tree = crystal_material.node_tree

    output_node = next((n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not output_node:
        return

    body_shader = tree.nodes.get('Body Shader') or \
                  tree.nodes.get('PrimoToon') or \
                  tree.nodes.get('HoYoToon') or \
                  tree.nodes.get('Group.001') or \
                  next((n for n in tree.nodes if n.type == 'GROUP' and 'BSDF' in n.outputs), None)

    lightmap_img_nodes = [n for n in tree.nodes if n.type == 'TEX_IMAGE' and 'lightmap' in (n.name + " " + (n.label or "")).lower()]
    has_lightmap_image = any(n.image is not None for n in lightmap_img_nodes)

    color_source_socket = None
    # 1. Try Lightmap if an image is loaded
    if has_lightmap_image:
        if body_shader and 'Lightmap Color' in body_shader.inputs and body_shader.inputs['Lightmap Color'].links:
            color_source_socket = body_shader.inputs['Lightmap Color'].links[0].from_socket
        elif tree.nodes.get('Lightmap Lerp') and 'Color' in tree.nodes['Lightmap Lerp'].outputs:
            color_source_socket = tree.nodes['Lightmap Lerp'].outputs['Color']
        elif lightmap_img_nodes:
            for n in lightmap_img_nodes:
                if n.image and 'Color' in n.outputs:
                    color_source_socket = n.outputs['Color']
                    break

    # 2. Fallback to Diffuse Lerp / Diffuse Color
    if not color_source_socket:
        if body_shader and 'Diffuse Color' in body_shader.inputs and body_shader.inputs['Diffuse Color'].links:
            color_source_socket = body_shader.inputs['Diffuse Color'].links[0].from_socket
        elif tree.nodes.get('Diffuse Lerp') and 'Color' in tree.nodes['Diffuse Lerp'].outputs:
            color_source_socket = tree.nodes['Diffuse Lerp'].outputs['Color']
        else:
            diffuse_nodes = [n for n in tree.nodes if n.type == 'TEX_IMAGE' and 'diffuse' in (n.name + " " + (n.label or "")).lower()]
            if diffuse_nodes and 'Color' in diffuse_nodes[0].outputs:
                color_source_socket = diffuse_nodes[0].outputs['Color']

    mix_node = next((n for n in tree.nodes if n.type == 'MIX_SHADER'), None)
    trans_node = next((n for n in tree.nodes if n.type == 'BSDF_TRANSPARENT'), None)
    math_node = next((n for n in tree.nodes if n.type == 'MATH' and getattr(n, 'operation', '') == 'GREATER_THAN'), None)
    sep_node = next((n for n in tree.nodes if n.type in ('SEPARATE_COLOR', 'SEPARATE_RGB')), None)

    bsdf_loc_x = body_shader.location.x if body_shader else 0
    bsdf_loc_y = body_shader.location.y if body_shader else 0

    if not mix_node:
        mix_node = tree.nodes.new('ShaderNodeMixShader')
        mix_node.location = (bsdf_loc_x + 300, bsdf_loc_y)

    if not trans_node:
        trans_node = tree.nodes.new('ShaderNodeBsdfTransparent')
        trans_node.location = (bsdf_loc_x + 300, bsdf_loc_y - 150)
        if 'Color' in trans_node.inputs:
            trans_node.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)

    if not math_node:
        math_node = tree.nodes.new('ShaderNodeMath')
        math_node.location = (bsdf_loc_x + 100, bsdf_loc_y - 300)
        math_node.operation = 'GREATER_THAN'
        math_node.inputs[1].default_value = 0.5
        math_node.use_clamp = False

    if not sep_node:
        if hasattr(bpy.types, "ShaderNodeSeparateColor"):
            sep_node = tree.nodes.new('ShaderNodeSeparateColor')
            if hasattr(sep_node, "mode"):
                sep_node.mode = 'RGB'
        else:
            sep_node = tree.nodes.new('ShaderNodeSeparateRGB')
        sep_node.location = (bsdf_loc_x - 100, bsdf_loc_y - 300)

    if color_source_socket:
        if sep_node.inputs[0].links:
            for l in list(sep_node.inputs[0].links):
                tree.links.remove(l)
        tree.links.new(color_source_socket, sep_node.inputs[0])

    red_socket = sep_node.outputs.get('Red') or sep_node.outputs.get('R') or sep_node.outputs[0]
    if not math_node.inputs[0].links:
        tree.links.new(red_socket, math_node.inputs[0])

    if not mix_node.inputs[0].links:
        tree.links.new(math_node.outputs[0], mix_node.inputs[0])

    if not mix_node.inputs[1].links:
        tree.links.new(trans_node.outputs[0], mix_node.inputs[1])

    if body_shader and 'BSDF' in body_shader.outputs and not mix_node.inputs[2].links:
        tree.links.new(body_shader.outputs['BSDF'], mix_node.inputs[2])

    if not output_node.inputs['Surface'].links or output_node.inputs['Surface'].links[0].from_node != mix_node:
        tree.links.new(mix_node.outputs[0], output_node.inputs['Surface'])

    try:
        crystal_material.blend_method = 'BLEND'
    except Exception:
        pass

    try:
        crystal_material.shadow_method = 'NONE'
    except Exception:
        pass

    try:
        crystal_material.show_transparent_back = False
    except Exception:
        pass


class TextureImporterType(Enum):
    AVATAR = auto()
    MONSTER = auto()
    NPC = auto()
    HSR_AVATAR = auto()
    PGR_AVATAR = auto()
    PGR_CHIBI = auto()


class TextureType(Enum):
    HAIR = 'Hair'
    BODY = 'Body'
    BODY2 = 'Body2'
    FACE = 'Face'
    WEAPON = 'Weapon'


class TextureImporterFactory:
    def create(texture_importer_type, game_type: GameType):
        shader_identifier_service: ShaderIdentifierService = ShaderIdentifierServiceFactory.create(game_type.name)

        if game_type is GameType.GENSHIN_IMPACT:
            shader: GenshinImpactShaders = shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)

            if shader is GenshinImpactShaders.V1_GENSHIN_IMPACT_SHADER or shader is GenshinImpactShaders.V2_GENSHIN_IMPACT_SHADER:
                # Not sure why IDE says code is unreachable, it is used
                material_names = V2_FestivityGenshinImpactMaterialNames  # V1/V2 have the same material names
            elif shader is GenshinImpactShaders.V3_GENSHIN_IMPACT_SHADER:
                # Not sure why IDE says code is unreachable, it is used
                material_names = V3_BonnyFestivityGenshinImpactMaterialNames
            else:
                material_names = V4_PrimoToonGenshinImpactMaterialNames  

            if texture_importer_type == TextureImporterType.AVATAR:
                return GenshinAvatarTextureImporter(material_names)
            elif texture_importer_type == TextureImporterType.NPC:
                return GenshinNPCTextureImporter(material_names)
            elif texture_importer_type == TextureImporterType.MONSTER:
                return GenshinMonsterTextureImporter(material_names)
            else:
                print(f'Unknown TextureImporterType: {texture_importer_type}')
        elif game_type is GameType.HONKAI_STAR_RAIL:
            shader: HonkaiStarRailShaders = shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)

            if shader is HonkaiStarRailShaders.NYA222_HONKAI_STAR_RAIL_SHADER:
                material_names = Nya222HonkaiStarRailShaderMaterialNames
                texture_names = Nya222HonkaiStarRailTextureNodeNames
            else:  # shader is HonkaiStarRailShaders.STELLARTOON_HONKAI_STAR_RAIL_SHADER
                material_names = StellarToonShaderMaterialNames
                texture_names = StellarToonTextureNodeNames

            if texture_importer_type == TextureImporterType.HSR_AVATAR:
                return HonkaiStarRailAvatarTextureImporter(material_names, texture_names)
            else:
                print(f'Unknown TextureImporterType: {texture_importer_type}')
        elif game_type is GameType.PUNISHING_GRAY_RAVEN:
            if texture_importer_type == TextureImporterType.PGR_AVATAR:
                return PunishingGrayRavenAvatarTextureImporter(JaredNytsPunishingGrayRavenShaderMaterialNames, 
                                                               JaredNytsPunishingGrayRavenTextureNodeNames)
            else:
                print(f'Unknown TextureImporterType: {texture_importer_type}')
        else:
            print(f'Unknown game_type: {game_type}')


class GenshinTextureImporter:
    def __init__(self, game_type: GameType, character_type: TextureImporterType):
        self.game_type = game_type
        self.character_type = character_type
        self.shader_identifier_service: ShaderIdentifierService
        self.genshin_shader_version: GenshinImpactShaders

    def import_textures(self, directory):
        raise NotImplementedError()

    '''
    Checks if all texture identifiers are in the texture name
    Use Case: I want to check if a texture has [X, Y, Z] in it.
    '''
    def is_texture_identifiers_in_texture_name(self, texture_identifiers: List[str], texture_name: str):
        assert(type(texture_identifiers) is list)  # TODO: Write unit test, programming error, input is wrong type!
        texture_identifier: str

        for texture_identifier in texture_identifiers:
            if texture_identifier.lower() not in texture_name.lower():
                return False
        return True

    def is_one_texture_identifier_in_texture_name(self, texture_identifiers: List[str], texture_name: str, normalize=False):
        for texture_identifier in texture_identifiers:
            if normalize:
                if texture_identifier.lower() in texture_name.lower():
                    return True
            else:
                if texture_identifier in texture_name:
                    return True
        return False

    '''
    Checks a groups of files to see if there is a file that has all texture identifiers in the filename
    Use Case: I want to check if there is a file with [X, Y, Z] in a group of files
    '''
    def is_texture_identifiers_in_files(self, texture_identifiers, files):
        file: str

        for file in files:
            if self.is_texture_identifiers_in_texture_name(texture_identifiers, file.lower()):
                return True
        return False

    '''
    Checks if no texture identifiers exist in each file
    Use Case: I want to check if a group of files does not have [X, Y, Z] in each filename
    '''
    def is_no_texture_identifiers_in_files(self, texture_identifiers: List[str], files: List[str]):
        for file in files:
            for texture_identifier in texture_identifiers:
                if texture_identifier.lower() in file.lower():
                    return False
        return True

    def set_diffuse_texture(self, texture_type: TextureType, material, img, override=True):
        if not material or not material.use_nodes:
            return

        if img:
            img.colorspace_settings.name = 'sRGB'

        nodes = find_all_image_nodes_by_category(material.node_tree, 'diffuse')
        if not nodes:
            possible_texture_node_names = [
                f'{texture_type.value}_Diffuse_UV0',
                f'{texture_type.value}_Diffuse_UV1',
                'Main_Diffuse',
                'Diffuse (sRGB) (Channel Packed)',
                'Diffuse UV1 (sRGB) (Channel Packed)',
                'Diffuse (sRGB)',
                'Diffuse UV1 (sRGB)',
                'Diffuse_UV0',
                'Diffuse_UV1',
                'Diffuse',
                'Diffuse UV1',
                'VFX_Diffuse',
                'Outline_Diffuse',
                'Image Texture',
                'Image Texture.001',
            ]
            nodes = find_texture_nodes(material.node_tree, possible_texture_node_names)
        
        for node in nodes:
            if override or not node.image:
                node.image = img

        if material and 'crystal' in material.name.lower():
            setup_crystal_material_nodes(material)

    def set_lightmap_texture(self, texture_type: TextureType, material, img, override=True):
        if not material or not material.use_nodes:
            return

        if img and 'diffuse' not in img.name.lower():
            img.colorspace_settings.name = 'Non-Color'
        nodes = find_all_image_nodes_by_category(material.node_tree, 'lightmap')
        if not nodes:
            possible_texture_node_names = [
                f'{texture_type.value}_Lightmap_UV0',
                f'{texture_type.value}_Lightmap_UV1',
                'Main_Lightmap',
                'Lightmap (Non-Color) (Channel Packed)',
                'Lightmap UV1 (Non-Color) (Channel Packed)',
                'Lightmap (Non-Color)',
                'Lightmap UV1 (Non-Color)',
                'Lightmap_UV0',
                'Lightmap_UV1',
                'Lightmap',
                'Lightmap UV1',
                'Outline_Lightmap',
                'Image Texture.001',
                'Image Texture.002',
            ]
            nodes = find_texture_nodes(material.node_tree, possible_texture_node_names)

        for node in nodes:
            if override or not node.image:
                node.image = img

        if material and 'crystal' in material.name.lower():
            setup_crystal_material_nodes(material)

    def set_normalmap_texture(self, type: TextureType, material, img, override=True):
        if not material or not material.use_nodes:
            return

        img.colorspace_settings.name = 'Non-Color'
        nodes = find_all_image_nodes_by_category(material.node_tree, 'normal')
        if not nodes:
            possible_texture_node_names = [
                f'{type.value}_Normalmap_UV0',
                f'{type.value}_Normalmap_UV1',
                'Main_Normalmap',
                'Normal Map (Non-Color) (Channel Packed)',
                'Normal Map UV1 (Non-Color) (Channel Packed)',
                'Normal Map (Non-Color)',
                'Normal Map UV1 (Non-Color)',
                'Normalmap_UV0',
                'Normalmap_UV1',
                'Normalmap',
                'Normal Map',
                'Normal Map UV1',
            ]
            nodes = find_texture_nodes(material.node_tree, possible_texture_node_names)

        for node in nodes:
            if override or not node.image:
                node.image = img

        if self.game_type == GameType.GENSHIN_IMPACT:
            body_shader = material.node_tree.nodes.get('Body Shader') or material.node_tree.nodes.get('PrimoToon') or material.node_tree.nodes.get('HoYoToon') or material.node_tree.nodes.get('Group.006')
            if not body_shader:
                for n in material.node_tree.nodes:
                    if n.type == 'GROUP' and n.node_tree and 'Use Normal Map' in n.inputs:
                        body_shader = n
                        break
            if body_shader and 'Use Normal Map' in body_shader.inputs:
                has_normal = any(n.image is not None for n in nodes)
                body_shader.inputs['Use Normal Map'].default_value = 1.0 if has_normal else 0.0

        # Deprecated. Tries only if it exists. Only for V1 Shader
        self.plug_normal_map(f'miHoYo - Genshin {type.value}', 'MUTE IF ONLY 1 UV MAP EXISTS')
        self.plug_normal_map('miHoYo - Genshin Dress', 'MUTE IF ONLY 1 UV MAP EXISTS')
        self.plug_normal_map('miHoYo - Genshin Dress1', 'MUTE IF ONLY 1 UV MAP EXISTS')
        self.plug_normal_map('miHoYo - Genshin Dress2', 'MUTE IF ONLY 1 UV MAP EXISTS')

    def set_shadow_ramp_texture(self, type: TextureType, img):
        if not img:
            return
        img.colorspace_settings.name = 'Non-Color'
        possible_shadow_ramp_node_group_names = [
            f'{type.value} Shadow Ramp',
            f'{type.value}_Shadow_Ramp',
            'Body Shadow Ramp',
            'Hair Shadow Ramp',
            V4_GenshinImpactTextureNodeNames.SHADER_TEXTURES_NODE_GROUP,
        ]
        for shadow_ramp_node_name in possible_shadow_ramp_node_group_names:
            shadow_ramp_node_group = bpy.data.node_groups.get(shadow_ramp_node_name)
            if shadow_ramp_node_group and hasattr(shadow_ramp_node_group, 'nodes'):
                for n in shadow_ramp_node_group.nodes:
                    if n.type == 'TEX_IMAGE':
                        n.image = img

        for mat in bpy.data.materials:
            if mat.use_nodes and mat.node_tree:
                for n in mat.node_tree.nodes:
                    if n.type == 'TEX_IMAGE':
                        n_id = (n.name + " " + (n.label or "")).lower()
                        if 'shadow' in n_id or 'ramp' in n_id:
                            if not any(k in n_id for k in ['diffuse', 'lightmap', 'normal', 'mask']):
                                n.image = img

    def set_specular_ramp_texture(self, type: TextureType, img):
        specular_ramp_node_exists = bpy.data.node_groups.get(f'{type.value} Specular Ramp')

        if specular_ramp_node_exists:
            img.colorspace_settings.name='Non-Color'
            bpy.data.node_groups[f'{type.value} Specular Ramp'].nodes[f'{type.value}_Specular_Ramp'].image = img        

    def set_face_diffuse_texture(self, face_material, img):
        face_material.node_tree.nodes['Face_Diffuse'].image = img

        # Set Built-In Face Lightmap Value for the V3 Shader
        face_shader_node = face_material.node_tree.nodes.get('Face Shader')
        if face_shader_node:
            face_lightmap_input = face_shader_node.inputs.get('[Loli/Boy/Girl/Male/Lady]')
            global_properties = face_material.node_tree.nodes.get(ShaderNodeNames.EXTERNAL_GLOBAL_PROPERTIES)

            if not face_lightmap_input and global_properties:
                face_lightmap_input = global_properties.node_tree.nodes.get(
                    ShaderNodeNames.INTERNAL_GLOBAL_PROPERTIES).inputs.get('[Loli/Boy/Girl/Male/Lady]')

            if face_lightmap_input:
                if 'Loli' in img.name:
                    face_lightmap_input.default_value = 1.0
                elif 'Boy' in img.name:
                    face_lightmap_input.default_value = 2.0
                elif 'Girl' in img.name or 'Female' in img.name:
                    face_lightmap_input.default_value = 3.0
                elif 'Male' in img.name:
                    face_lightmap_input.default_value = 4.0
                elif 'Lady' in img.name:
                    face_lightmap_input.default_value = 5.0

    def set_face_shadow_texture(self, face_material, img):
        # V1/V2 - Node
        face_shadow_node = face_material.node_tree.nodes.get('Face_Shadow')
        if face_shadow_node:
            img.colorspace_settings.name='Non-Color'
            face_material.node_tree.nodes['Face_Shadow'].image = img

        # V4 - Node Group
        texture_node_names = self.shader_identifier_service.get_shader_texture_node_names(self.genshin_shader_version)
        face_shadow_map_node_group = bpy.data.node_groups.get(texture_node_names.FACE_SHADOW_MAP_NODE_GROUP)

        if face_shadow_map_node_group:
            img.colorspace_settings.name='Non-Color'
            face_shadow_map_node_group.nodes[texture_node_names.FACE_SHADOW_MAP].image = img


    def set_face_lightmap_texture(self, img):
        # Genshin Impact Shader V1/V2/V4
        texture_node_names = self.shader_identifier_service.get_shader_texture_node_names(self.genshin_shader_version)
        face_lightmap_node_group = bpy.data.node_groups.get(texture_node_names.FACE_LIGHTMAP_NODE_GROUP)

        if face_lightmap_node_group:
            img.colorspace_settings.name='Non-Color'
            face_lightmap_node_group.nodes[texture_node_names.FACE_LIGHTMAP].image = img

    def set_metalmap_texture(self, img):
        metallic_matcap_node_exists = bpy.data.node_groups.get('Metallic Matcap')

        if metallic_matcap_node_exists:
            bpy.data.node_groups['Metallic Matcap'].nodes['MetalMap'].image = img

    def set_glass_diffuse_texture(self, material, img):
        diffuse_node = material.node_tree.nodes.get('Main_Diffuse') 
        vfx_node = material.node_tree.nodes.get(V4_GenshinImpactTextureNodeNames.VFX_DIFFUSE)

        nodes = [diffuse_node, vfx_node]
        for node in nodes:
            if material and node:
                node.image = img

    def set_nyx_color_ramp_texture(self, img):
        possible_nyx_color_ramp_node_group_names = [
            V4_GenshinImpactTextureNodeNames.SHADER_TEXTURES_NODE_GROUP,
        ]
        for nyx_color_ramp_node_group_name in possible_nyx_color_ramp_node_group_names:
            nyx_color_ramp_node_group = bpy.data.node_groups.get(nyx_color_ramp_node_group_name)
            if nyx_color_ramp_node_group:
                nyx_color_ramp_node = nyx_color_ramp_node_group.nodes.get(V4_GenshinImpactTextureNodeNames.NYX_COLOR_RAMP)
                if nyx_color_ramp_node:
                    nyx_color_ramp_node.image = img

    def set_up_night_soul_mask_texture(self, material, img):
        if material and material.node_tree and material.node_tree.nodes:
            texture_node_names = self.shader_identifier_service.get_shader_texture_node_names(self.genshin_shader_version)
            night_soul_mask_texture_node = material.node_tree.nodes.get(texture_node_names.NIGHT_SOUL_MASK) or \
                material.node_tree.nodes.get(texture_node_names.FACE_NIGHT_SOUL_MASK)

            if night_soul_mask_texture_node:
                night_soul_mask_texture_node.image = img

    def has_dedicated_texture(self, part_name, tex_type):
        if not hasattr(self, 'files') or not self.files:
            return False
        return any(part_name.lower() in f.lower() and tex_type.lower() in f.lower() for f in self.files)

    def set_up_night_soul_outlines_material(self):
        night_soul_outline_material = self.create_night_soul_outlines()
        if not night_soul_outline_material:
            return None
        shader_node_names: ShaderNodeNames = self.shader_identifier_service.get_shader_node_names(self.genshin_shader_version)

        body_shader = night_soul_outline_material.node_tree.nodes[shader_node_names.BODY_SHADER]
        output = body_shader.outputs.get(shader_node_names.NIGHT_SOUL_OUTPUT)
        input = night_soul_outline_material.node_tree.nodes.get(shader_node_names.MATERIAL_OUTPUT_NODE).inputs.get(shader_node_names.MATERIAL_OUTPUT_SHADER_INPUT)
        night_soul_outline_material.node_tree.links.new(output, input)
        night_soul_outline_material.use_screen_refraction = True

    def create_night_soul_outlines(self):
        shader_material_names: ShaderMaterialNames = self.shader_identifier_service.get_shader_material_names_using_shader(self.genshin_shader_version)
        outline_material = bpy.data.materials.get(shader_material_names.OUTLINES)
        if not shader_material_names.NIGHT_SOUL_OUTLINES:
            return None
        night_soul_outlines_material = bpy.data.materials.get(shader_material_names.NIGHT_SOUL_OUTLINES)
        if not night_soul_outlines_material:
            night_soul_outlines_material = outline_material.copy()
            night_soul_outlines_material.name = shader_material_names.NIGHT_SOUL_OUTLINES
            night_soul_outlines_material.use_fake_user = True
        return night_soul_outlines_material

    def setup_dress_textures(self, texture_name, texture_img, character_type: TextureImporterType):
        shader_dress_materials = [material for material in bpy.data.materials if 
                                  ('Genshin Dress' in material.name or 'Dress' in material.name) and 'Outlines' not in material.name and not material.name.endswith('_Mat')]
        shader_cloak_materials = [material for material in bpy.data.materials
                                  if 'Genshin Arm' in material.name or 'Genshin Cloak' in material.name]

        tex_name_lower = texture_name.lower()
        if 'normal' in tex_name_lower:
            target_node_names = [texture_name, 'Main_Normalmap', 'Normal Map (Non-Color) (Channel Packed)']
        elif 'lightmap' in tex_name_lower:
            target_node_names = [texture_name, 'Main_Lightmap', 'Lightmap (Non-Color) (Channel Packed)', 'Lightmap UV1 (Non-Color) (Channel Packed)']
        else:
            target_node_names = [texture_name, 'Main_Diffuse', 'Diffuse (sRGB) (Channel Packed)', 'Diffuse UV1 (sRGB) (Channel Packed)']

        if shader_cloak_materials:
            matching_orig = [material for material in bpy.data.materials if material.name.endswith(shader_cloak_materials[0].name.split(' ')[-1])]
            if matching_orig:
                original_cloak_material = matching_orig[0]
                actual_cloak_material = get_actual_material_name_for_dress(original_cloak_material.name, character_type.name)
                if actual_cloak_material in texture_img.name:
                    cloak_mat = bpy.data.materials.get(shader_cloak_materials[0].name)
                    if cloak_mat and cloak_mat.use_nodes:
                        nodes = find_texture_nodes(cloak_mat.node_tree, target_node_names)
                        for n in nodes:
                            n.image = texture_img

        for shader_dress_material in shader_dress_materials:
            original_dress_material = self.get_original_dress_material(shader_dress_material)
            if not original_dress_material:
                continue

            if character_type == TextureImporterType.MONSTER:
                actual_material = OriginalTextureLocatorUtils.get_monster_original_texture_part(original_dress_material)
            else:
                actual_material = get_actual_material_name_for_dress(original_dress_material.name, character_type.name)

            is_match = (
                actual_material and (
                    actual_material in texture_img.name or
                    actual_material.replace('1', '01') in texture_img.name or
                    actual_material.replace('2', '02') in texture_img.name or
                    (actual_material == 'Body1' and ('Body01' in texture_img.name or 'Body1' in texture_img.name or 'Dress01' in texture_img.name or 'Dress1' in texture_img.name)) or
                    (actual_material == 'Body2' and ('Body02' in texture_img.name or 'Body2' in texture_img.name or 'Dress02' in texture_img.name or 'Dress2' in texture_img.name))
                )
            )

            if is_match:
                print(f'Importing texture "{texture_name}" onto material "{shader_dress_material.name}"')
                if shader_dress_material.use_nodes:
                    nodes = find_texture_nodes(shader_dress_material.node_tree, target_node_names)
                    for n in nodes:
                        n.image = texture_img

    def import_textures_from_json(self, directory):
        """
        Reads material JSON files from 'Materials/' subfolder or directory if present,
        and assigns textures with 100% precision based on the game's shader property mappings.
        """
        candidates = [
            os.path.join(directory, "Materials"),
            directory
        ]
        materials_dir = None
        for d in candidates:
            if os.path.isdir(d) and any(f.lower().endswith('.json') and not f.startswith('Avatar_Default_Mat') for f in os.listdir(d)):
                materials_dir = d
                break

        if not materials_dir:
            return False

        image_files = []
        for root, _, files in os.walk(directory):
            for f in files:
                if f.lower().endswith(('.png', '.tga', '.dds', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')):
                    image_files.append((f, os.path.join(root, f)))

        def is_generic_tex(fname):
            f_low = fname.lower()
            return f_low.startswith('avatar_tex_') or f_low.startswith('tex_')

        # Prioritize character-specific textures over generic ones
        image_files.sort(key=lambda item: 1 if is_generic_tex(item[0]) else 0)

        def resolve_img(tex_name):
            if not tex_name:
                return None
            t_low = tex_name.lower().strip()

            core_part = None
            if is_generic_tex(t_low):
                core_part = t_low.replace('avatar_tex_', '').replace('tex_', '')

            # 1. Exact match with non-generic (character-specific) files first
            for fname, fpath in image_files:
                if is_generic_tex(fname):
                    continue
                stem = os.path.splitext(fname)[0].lower()
                if stem == t_low:
                    img = bpy.data.images.get(fname) or bpy.data.images.load(filepath=os.path.normpath(fpath), check_existing=True)
                    img.alpha_mode = 'CHANNEL_PACKED'
                    return img

            # 2. Check if a character-specific texture matches the core part suffix (e.g. Crystal_Diffuse)
            if core_part:
                for fname, fpath in image_files:
                    if is_generic_tex(fname):
                        continue
                    stem = os.path.splitext(fname)[0].lower()
                    if stem.endswith(core_part) or f'_{core_part}' in stem or core_part in stem:
                        img = bpy.data.images.get(fname) or bpy.data.images.load(filepath=os.path.normpath(fpath), check_existing=True)
                        img.alpha_mode = 'CHANNEL_PACKED'
                        return img

            # 3. Exact stem match across all files
            for fname, fpath in image_files:
                stem = os.path.splitext(fname)[0].lower()
                if stem == t_low:
                    img = bpy.data.images.get(fname) or bpy.data.images.load(filepath=os.path.normpath(fpath), check_existing=True)
                    img.alpha_mode = 'CHANNEL_PACKED'
                    return img

            # 4. Prefix / suffix match across all files
            for fname, fpath in image_files:
                stem = os.path.splitext(fname)[0].lower()
                if stem.startswith(t_low) or t_low.startswith(stem):
                    img = bpy.data.images.get(fname) or bpy.data.images.load(filepath=os.path.normpath(fpath), check_existing=True)
                    img.alpha_mode = 'CHANNEL_PACKED'
                    return img

            # 5. Substring match across all files
            for fname, fpath in image_files:
                if t_low in fname.lower():
                    img = bpy.data.images.get(fname) or bpy.data.images.load(filepath=os.path.normpath(fpath), check_existing=True)
                    img.alpha_mode = 'CHANNEL_PACKED'
                    return img

            return None

        imported_any = False
        for jf in os.listdir(materials_dir):
            if not jf.lower().endswith('.json') or jf.startswith('Avatar_Default_Mat'):
                continue
            jpath = os.path.join(materials_dir, jf)
            try:
                with open(jpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                continue

            tex_envs = data.get('m_SavedProperties', {}).get('m_TexEnvs', {})
            raw_name = os.path.splitext(jf)[0]
            mat_part = raw_name.split('_')[-1]

            target_mat = None
            if hasattr(self, 'material_names') and hasattr(self.material_names, 'MATERIAL_PREFIX'):
                target_mat = bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}{mat_part}')

            if not target_mat:
                for mat in bpy.data.materials:
                    if mat.use_nodes and 'outlines' not in mat.name.lower() and 'outline' not in mat.name.lower():
                        if is_mat_part_match(mat.name, mat_part):
                            target_mat = mat
                            break

            if not target_mat and mat_part.lower() == 'pupil':
                target_mat = bpy.data.materials.get(getattr(self.material_names, 'NEW_PUPIL', f'{self.material_names.MATERIAL_PREFIX}New Pupil')) or \
                             bpy.data.materials.get('HoYoverse - Genshin New Pupil') or \
                             bpy.data.materials.get('miHoYo - Genshin New Pupil') or \
                             bpy.data.materials.get(getattr(self.material_names, 'PUPIL', f'{self.material_names.MATERIAL_PREFIX}Pupil')) or \
                             next((m for m in bpy.data.materials if 'pupil' in m.name.lower() and 'outlines' not in m.name.lower()), None)

            if not target_mat and mat_part.lower() == 'brow':
                target_mat = bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}Brow') or \
                             bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}Face')

            if not target_mat:
                for mat in bpy.data.materials:
                    if mat.use_nodes and 'outlines' not in mat.name.lower() and 'outline' not in mat.name.lower():
                        if raw_name.lower() in mat.name.lower():
                            target_mat = mat
                            break

            if not target_mat:
                target_mat = bpy.data.materials.get(raw_name)

            if not target_mat:
                continue

            diffuse_img = None
            diffuse_tex_name = tex_envs.get('_MainTex', {}).get('m_Texture', {}).get('Name') or \
                               tex_envs.get('_BaseTexV2', {}).get('m_Texture', {}).get('Name') or \
                               tex_envs.get('_BaseTex', {}).get('m_Texture', {}).get('Name')
            if diffuse_tex_name:
                diffuse_img = resolve_img(diffuse_tex_name)
                if diffuse_img:
                    tex_type = TextureType.HAIR if mat_part.lower() in ['hair', 'effecthair', 'helmet', 'helmetemo'] else TextureType.BODY
                    if mat_part.lower() == 'face':
                        self.set_face_diffuse_texture(target_mat, diffuse_img)
                    elif mat_part.lower() in ['pupil', 'pupila', 'sandrone pupil'] or ('pupil' in target_mat.name.lower() and 'outlines' not in target_mat.name.lower()):
                        pass  # Handled below by multi-pupil resolver
                    else:
                        self.set_diffuse_texture(tex_type, target_mat, diffuse_img)
                    imported_any = True
                else:
                    if mat_part.lower() not in ['face', 'pupil', 'pupila', 'sandrone pupil'] and not any(k in target_mat.name.lower() for k in ['face', 'pupil', 'pupila']):
                        for node in find_all_image_nodes_by_category(target_mat.node_tree, 'diffuse'):
                            node.image = None
            else:
                if mat_part.lower() not in ['face', 'pupil', 'pupila', 'sandrone pupil'] and not any(k in target_mat.name.lower() for k in ['face', 'pupil', 'pupila']):
                    for node in find_all_image_nodes_by_category(target_mat.node_tree, 'diffuse'):
                        node.image = None

            if mat_part.lower() not in ['face', 'pupil', 'pupila', 'sandrone pupil'] and not any(k in target_mat.name.lower() for k in ['face', 'pupil', 'pupila']):
                lightmap_tex_name = tex_envs.get('_LightMapTex', {}).get('m_Texture', {}).get('Name')
                if lightmap_tex_name:
                    lightmap_img = resolve_img(lightmap_tex_name)
                else:
                    lightmap_img = None

                # If no lightmap exists, fallback to diffuse image
                if not lightmap_img and diffuse_img:
                    lightmap_img = diffuse_img

                if lightmap_img:
                    tex_type = TextureType.HAIR if mat_part.lower() in ['hair', 'effecthair', 'helmet', 'helmetemo'] else TextureType.BODY
                    self.set_lightmap_texture(tex_type, target_mat, lightmap_img)
                    imported_any = True
                else:
                    for node in find_all_image_nodes_by_category(target_mat.node_tree, 'lightmap'):
                        node.image = None

                bump_tex_name = tex_envs.get('_BumpMap', {}).get('m_Texture', {}).get('Name')
                if bump_tex_name:
                    bump_img = resolve_img(bump_tex_name)
                    if bump_img:
                        tex_type = TextureType.HAIR if mat_part.lower() in ['hair', 'effecthair', 'helmet', 'helmetemo'] else TextureType.BODY
                        self.set_normalmap_texture(tex_type, target_mat, bump_img)
                        imported_any = True
                else:
                    for node in find_all_image_nodes_by_category(target_mat.node_tree, 'normal'):
                        node.image = None

                shadow_ramp_name = tex_envs.get('_PackedShadowRampTex', {}).get('m_Texture', {}).get('Name') or \
                                   tex_envs.get('_ShadowRampTex', {}).get('m_Texture', {}).get('Name')
                if shadow_ramp_name:
                    shadow_ramp_img = resolve_img(shadow_ramp_name)
                    if shadow_ramp_img:
                        tex_type = TextureType.HAIR if mat_part.lower() in ['hair', 'effecthair', 'helmet', 'helmetemo'] else TextureType.BODY
                        self.set_shadow_ramp_texture(tex_type, shadow_ramp_img)
                        imported_any = True

            # If equipment, assign white shadow ramp and set Use Alpha = 1
            is_mat_equip = target_mat.name.lower().startswith(('equip_', 'equipskin_')) or \
                           any(obj.name.startswith(('Equip_', 'EquipSkin_')) for obj in bpy.data.objects)
            if is_mat_equip:
                white_ramp = get_or_create_white_texture("White_Shadow_Ramp")
                self.set_shadow_ramp_texture(TextureType.BODY, white_ramp)
                set_use_alpha_on_material(target_mat, 1.0)

            # Pupil diffuse textures (for Pupil, New Pupil, and Sandrone pupil)
            if mat_part.lower() in ['pupil', 'pupila', 'sandrone pupil'] or ('pupil' in target_mat.name.lower() and 'outlines' not in target_mat.name.lower()):
                pupil_imgs = {}
                for fname, fpath in image_files:
                    f_low = fname.lower()
                    if ('pupil' in f_low or 'pupila' in f_low or 'eyepupil' in f_low) and 'diffuse' in f_low and f_low.endswith(('.png', '.tga', '.dds', '.jpg')):
                        p_img = resolve_img(os.path.splitext(fname)[0])
                        if p_img:
                            p_img.alpha_mode = 'CHANNEL_PACKED'
                            p_img.colorspace_settings.name = 'sRGB'
                            if any(k in f_low for k in ['01', 'pupil1', 'pupil_1', 'pupil 1', 'pupila1', 'diffuse1', 'diffuse_1', 'diffuse 1']):
                                pupil_imgs['01'] = p_img
                                pupil_imgs['1'] = p_img
                            elif any(k in f_low for k in ['02', 'pupil2', 'pupil_2', 'pupil 2', 'pupila2', 'diffuse2', 'diffuse_2', 'diffuse 2']):
                                pupil_imgs['02'] = p_img
                                pupil_imgs['2'] = p_img
                            elif any(k in f_low for k in ['03', 'pupil3', 'pupil_3', 'pupil 3', 'pupila3', 'diffuse3', 'diffuse_3', 'diffuse 3']):
                                pupil_imgs['03'] = p_img
                                pupil_imgs['3'] = p_img
                            elif any(k in f_low for k in ['04', 'pupil4', 'pupil_4', 'pupil 4', 'pupila4', 'diffuse4', 'diffuse_4', 'diffuse 4']):
                                pupil_imgs['04'] = p_img
                                pupil_imgs['4'] = p_img
                            else:
                                pupil_imgs['01'] = p_img
                                pupil_imgs['1'] = p_img
                if diffuse_tex_name and '01' not in pupil_imgs:
                    p1_img = resolve_img(diffuse_tex_name)
                    if p1_img:
                        p1_img.alpha_mode = 'CHANNEL_PACKED'
                        p1_img.colorspace_settings.name = 'sRGB'
                        pupil_imgs['01'] = p1_img
                        pupil_imgs['1'] = p1_img
                if pupil_imgs:
                    self.set_multi_pupil_textures(target_mat, pupil_imgs)
                    imported_any = True

            # Eye Highlight / Highlight Mask
            highlight_tex_name = tex_envs.get('_EyeHighlightTex', {}).get('m_Texture', {}).get('Name') or \
                                 tex_envs.get('_HighlightMask', {}).get('m_Texture', {}).get('Name') or \
                                 tex_envs.get('_EyeLightTex', {}).get('m_Texture', {}).get('Name') or \
                                 tex_envs.get('_HighlightTex', {}).get('m_Texture', {}).get('Name') or \
                                 tex_envs.get('_EyeHighlight', {}).get('m_Texture', {}).get('Name')
            if highlight_tex_name:
                h_img = resolve_img(highlight_tex_name)
                if h_img:
                    self.set_highlight_mask_texture(target_mat, h_img)
                    imported_any = True
            elif mat_part.lower() in ['pupil', 'pupila', 'sandrone pupil'] or ('pupil' in target_mat.name.lower() and 'outlines' not in target_mat.name.lower()):
                for fname, fpath in image_files:
                    f_low = fname.lower()
                    if ('eyehighlight' in f_low or 'eyelight' in f_low or 'eye_highlight' in f_low or 'eye_light' in f_low) or ('highlight' in f_low and ('diffuse' in f_low or 'mask' in f_low)):
                        h_img = resolve_img(os.path.splitext(fname)[0])
                        if h_img:
                            self.set_highlight_mask_texture(target_mat, h_img)
                            imported_any = True
                            break

            stockings_name = tex_envs.get('_ShiningCustomIDMask_V2', {}).get('m_Texture', {}).get('Name')
            if stockings_name:
                stock_img = resolve_img(stockings_name)
                if stock_img:
                    self.set_stocking_texture(stock_img)
                    imported_any = True

        return imported_any

    def import_part_texture_to_matching_materials(self, file, img):
        """
        Dynamically matches textures for Body01..04, Body1..4, Dress01..04, Dress1..4, Dress, Tail, Ribbon, VeilShadow, Stockings, Arm, Cloak, Helmet, etc.
        to their corresponding materials and assigns Diffuse, Lightmap, or Normal Map nodes via find_texture_nodes.
        """
        f_lower = file.lower()
        is_diffuse = 'diffuse' in f_lower
        is_lightmap = 'lightmap' in f_lower or 'light_map' in f_lower
        is_normal = 'normal' in f_lower or 'normalmap' in f_lower
        is_shadow_ramp = 'shadow_ramp' in f_lower

        if not (is_diffuse or is_lightmap or is_normal or is_shadow_ramp):
            return False

        matched_any = False

        # Match equipment / weapon textures directly
        if f_lower.startswith(('equip_', 'equipskin_')) or 'equip' in f_lower:
            equip_materials = [
                mat for mat in bpy.data.materials 
                if mat.use_nodes and 'outlines' not in mat.name.lower() and 'outline' not in mat.name.lower() and ('body' in mat.name.lower() or 'equip' in mat.name.lower())
            ]
            if not equip_materials:
                equip_materials = [
                    mat for mat in bpy.data.materials 
                    if mat.use_nodes and 'outlines' not in mat.name.lower() and 'pupil' not in mat.name.lower() and 'face' not in mat.name.lower()
                ]
            for target_mat in equip_materials:
                if is_diffuse:
                    self.set_diffuse_texture(TextureType.BODY, target_mat, img)
                    matched_any = True
                elif is_lightmap:
                    self.set_lightmap_texture(TextureType.BODY, target_mat, img)
                    matched_any = True
                elif is_normal:
                    self.set_normalmap_texture(TextureType.BODY, target_mat, img)
                    matched_any = True
                elif is_shadow_ramp:
                    self.set_shadow_ramp_texture(TextureType.BODY, img)
                    matched_any = True
            if matched_any:
                return True

        parts_to_check = [
            'body04', 'body03', 'body02', 'body01', 'body_04', 'body_03', 'body_02', 'body_01', 'body4', 'body3', 'body2', 'body1',
            'dress04', 'dress03', 'dress02', 'dress01', 'dress_04', 'dress_03', 'dress_02', 'dress_01', 'dress4', 'dress3', 'dress2', 'dress1',
            'tail', 'ribbon', 'veilshadow', 'veil', 'stockings', 'arm', 'cloak', 'helmetemo', 'helmet', 'gauntlet', 'leather', 'skirt',
            'glass_eff', 'glass', 'starcloak', 'wing', 'wings', 'crystal', 'dress', 'body'
        ]

        for part in parts_to_check:
            if part in f_lower:
                # If this file is generic (e.g. Avatar_Tex_Crystal_Diffuse.png) and a character-specific file exists in the directory, skip it
                if f_lower.startswith('avatar_tex_') or f_lower.startswith('tex_'):
                    if hasattr(self, 'files') and self.files:
                        category_key = 'diffuse' if is_diffuse else 'lightmap' if is_lightmap else 'normal' if is_normal else 'shadow_ramp'
                        has_character_specific = any(
                            part in f.lower() and category_key in f.lower() and not f.lower().startswith('avatar_tex_') and not f.lower().startswith('tex_')
                            for f in self.files
                        )
                        if has_character_specific:
                            return False

                matching_materials = [
                    mat for mat in bpy.data.materials 
                    if mat.use_nodes and 'outlines' not in mat.name.lower() and 'outline' not in mat.name.lower() and is_mat_part_match(mat.name, part)
                ]

                if matching_materials:
                    for target_mat in matching_materials:
                        if is_diffuse:
                            self.set_diffuse_texture(TextureType.BODY, target_mat, img)
                            matched_any = True
                        elif is_lightmap:
                            self.set_lightmap_texture(TextureType.BODY, target_mat, img)
                            matched_any = True
                        elif is_normal:
                            self.set_normalmap_texture(TextureType.BODY, target_mat, img)
                            matched_any = True
                        elif is_shadow_ramp:
                            self.set_shadow_ramp_texture(TextureType.BODY, img)
                            matched_any = True
                    break

        return matched_any

    def get_original_dress_material(self, shader_dress_material):
        for material in bpy.data.materials:
            is_not_original_material = (self.material_names.MATERIAL_PREFIX and material.name.startswith(self.material_names.MATERIAL_PREFIX)) or \
                                       (self.material_names.MATERIAL_PREFIX_AFTER_RENAME and material.name.startswith(self.material_names.MATERIAL_PREFIX_AFTER_RENAME))
            if is_not_original_material:
                continue

            is_playable_character_original_material = material.name.endswith(shader_dress_material.name.split(' ')[-1])
            # ex. 'Monster_Fatuus_Agent_01_Fire_Dress_Mat' and 'HoYoverse - Genshin Dress'
            # ex. 'Monster_Eremite_Male_Strong_Katar_01_Rock_Dress_Mat' and 'HoYoverse - Genshin Dress'
            is_npc_original_material = len(material.name.split('_')) > 2 and material.name.split('_')[-2].endswith(shader_dress_material.name.split(' ')[-1])

            if is_playable_character_original_material or is_npc_original_material:
                return material  # material that ends with 'Dress', 'Dress1', 'Dress2'

    def does_dress_texture_exist_in_directory_files(self):
        dress_texture_detected = False
        for file in self.files:
            if 'Dress' in file and '.png' in file:
                dress_texture_detected = True
        return dress_texture_detected

    def set_face_material_id(self, face_material, image):
        character_to_face_material_id_map = {
            'Collei': 5,
            'Cyno': 3,
            'DilucCostumeFlamme': 3,
            'Faruzan': 3,
            'AyakaCostumeFruhling': 5,
            'Ayato': 3,
            'KleeCostumeWitch': 3,
            'Linette': 3,  # Lynette
            'Liney': 3,  # Lyney
            'Nilou': 3,
            'Kokomi': 3,
            'Tighnari': 3,
            'Yelan': 3,
        }

        shader_has_face_material_id = self.genshin_shader_version is GenshinImpactShaders.V2_GENSHIN_IMPACT_SHADER

        # No longer a field in V3 shader
        if shader_has_face_material_id:
            for character_name in character_to_face_material_id_map.keys():
                if character_name in image.name:
                    shader_node_names = self.shader_identifier_service.get_shader_node_names(self.genshin_shader_version)
                    if face_material.node_tree.nodes.get(shader_node_names.FACE_SHADER):
                        face_shader_node = face_material.node_tree.nodes[shader_node_names.FACE_SHADER]
                        face_shader_node.inputs[shader_node_names.FACE_MATERIAL_ID].default_value = \
                            character_to_face_material_id_map[character_name]

    def set_body_hair_output_on_face_shader(self, face_material, image):
        characters_needing_hair_output = [
            'Funingna',  # Furina
        ]

        shader_has_body_hair_output = self.genshin_shader_version is GenshinImpactShaders.V2_GENSHIN_IMPACT_SHADER

        if shader_has_body_hair_output:
            for character_name in characters_needing_hair_output:
                shader_node_names = self.shader_identifier_service.get_shader_node_names(self.genshin_shader_version)
                if character_name in image.name and face_material.node_tree.nodes.get(shader_node_names.FACE_SHADER):
                    face_shader_node = face_material.node_tree.nodes[shader_node_names.FACE_SHADER]
                    face_shader_node_hair_output = face_shader_node.outputs.get('Hair')

                    depth_based_rim_node = face_material.node_tree.nodes.get(shader_node_names.DEPTH_BASED_RIM)
                    is_depth_based_rim_node = depth_based_rim_node and depth_based_rim_node.inputs.get('Lit Factor')

                    if is_depth_based_rim_node:
                        depth_based_rim_node_input = depth_based_rim_node.inputs.get('Input')
                        face_material.node_tree.links.new(
                            face_shader_node_hair_output,
                            depth_based_rim_node_input
                        )
                    else:
                        material_output_node = face_material.node_tree.nodes.get('Material Output')
                        material_output_node_surface_input = material_output_node.inputs.get('Surface')
                        face_material.node_tree.links.new(
                            face_shader_node_hair_output,
                            material_output_node_surface_input
                        )

    def star_cloak_uses_body_texture(self, file):
        texture_name_identifiers = [
            'Dainslaif',
        ]
        for identifier in texture_name_identifiers:
            if identifier in file:
                return True
        return False

    '''
    Deprecated: No longer needed after shader rewrite because normal map is plugged by default
    Still maintains backward compatibility by only trying this if `label_name` is found in the node tree.
    '''
    def plug_normal_map(self, shader_material_name, label_name):
        shader_group_material_name = 'Group.001'
        shader_material = bpy.data.materials.get(shader_material_name)

        if shader_material:
            normal_map_node_color_outputs = [node.outputs.get('Color') for node in shader_material.node_tree.nodes \
                if node.label == label_name and not node.outputs.get('Color').is_linked]
            
            if normal_map_node_color_outputs:
                normal_map_node_color_output = normal_map_node_color_outputs[0]
                normal_map_input = shader_material.node_tree.nodes.get(shader_group_material_name).inputs.get('Normal Map')

                bpy.data.materials.get(shader_material_name).node_tree.links.new(
                    normal_map_node_color_output,
                    normal_map_input
                )

    def set_stocking_texture(self, img):
        possible_shadow_ramp_node_group_names = [
            V4_GenshinImpactTextureNodeNames.SHADER_TEXTURES_NODE_GROUP,
        ]
        for shadow_ramp_node_name in possible_shadow_ramp_node_group_names:
            shadow_ramp_node_group = bpy.data.node_groups.get(shadow_ramp_node_name)
            if shadow_ramp_node_group:
                shader_node_names = self.shader_identifier_service.get_shader_node_names(self.genshin_shader_version)
                img.colorspace_settings.name='Non-Color'
                shadow_ramp_node_group.nodes[shader_node_names.STOCKINGS_DETAIL].image = img


    def set_highlight_mask_texture(self, material, img):
        if not material or not material.use_nodes or not material.node_tree:
            return

        m_low = material.name.lower()
        if any(k in m_low for k in ['face', 'body', 'hair', 'dress', 'arm', 'cloak', 'glass', 'tail', 'wing', 'skirt', 'gauntlet', 'leather', 'outlines']):
            return

        def get_all_tex_nodes(tree):
            nodes = []
            for n in tree.nodes:
                if n.type == 'TEX_IMAGE':
                    nodes.append(n)
                elif n.type == 'GROUP' and n.node_tree:
                    ng_name = n.node_tree.name.lower()
                    if any(ign in ng_name for ign in ['face factor', 'face shader', 'gi face', 'eyeshadow', 'body shader', 'gi body', 'gi hair', 'primotoon', 'hoyotoon', 'outline']):
                        continue
                    nodes.extend(get_all_tex_nodes(n.node_tree))
            return nodes

        img.colorspace_settings.name = 'sRGB'
        tex_nodes = get_all_tex_nodes(material.node_tree)
        for n in tex_nodes:
            n_id = (n.name + " " + (n.label or "")).lower()
            if any(k in n_id for k in ['highlight mask', 'highlight_mask', 'highlightmask', 'eyehighlight', 'eyelight', 'eye_highlight', 'eye_light', 'highlight']):
                if not ('blend' in n_id or 'ramp' in n_id):
                    n.image = img

    def set_multi_pupil_textures(self, material, pupil_images_dict):
        if not material or not material.use_nodes or not material.node_tree:
            return

        m_low = material.name.lower()
        if any(k in m_low for k in ['face', 'body', 'hair', 'dress', 'arm', 'cloak', 'glass', 'tail', 'wing', 'skirt', 'gauntlet', 'leather', 'outlines']):
            return

        def get_all_tex_nodes(tree):
            nodes = []
            for n in tree.nodes:
                if n.type == 'TEX_IMAGE':
                    nodes.append(n)
                elif n.type == 'GROUP' and n.node_tree:
                    ng_name = n.node_tree.name.lower()
                    if any(ign in ng_name for ign in ['face factor', 'face shader', 'gi face', 'eyeshadow', 'body shader', 'gi body', 'gi hair', 'primotoon', 'hoyotoon', 'outline']):
                        continue
                    nodes.extend(get_all_tex_nodes(n.node_tree))
            return nodes

        tex_nodes = get_all_tex_nodes(material.node_tree)

        diffuse_nodes = [
            n for n in tex_nodes
            if not any(k in (n.name + " " + (n.label or "")).lower() for k in ['blend', 'ramp', 'highlight', 'mask', 'lightmap', 'normal'])
        ]
        diffuse_nodes.sort(key=lambda n: n.location.y, reverse=True)

        matched_nodes = set()
        for n in diffuse_nodes:
            n_id = (n.name + " " + (n.label or "")).lower()
            for key in ['01', '02', '03', '04', '1', '2', '3', '4']:
                k_num = str(int(key))
                k_0num = f'{int(key):02d}'
                match_patterns = [
                    f'diffuse{k_0num}', f'diffuse{k_num}', f'diffuse_{k_0num}', f'diffuse_{k_num}',
                    f'diffuse {k_0num}', f'diffuse {k_num}',
                    f'pupil{k_0num}', f'pupil{k_num}', f'pupil_{k_0num}', f'pupil_{k_num}',
                    f'pupil {k_0num}', f'pupil {k_num}', f'pupil{k_0num}_', f'pupil{k_num}_',
                    f'pupila{k_0num}', f'pupila{k_num}', f'pupila_{k_0num}', f'pupila_{k_num}'
                ]
                if any(p in n_id for p in match_patterns):
                    img = pupil_images_dict.get(k_0num) or pupil_images_dict.get(k_num)
                    if img:
                        img.colorspace_settings.name = 'sRGB'
                        n.image = img
                        matched_nodes.add(n)
                    break

        if not matched_nodes and diffuse_nodes:
            slot_keys = ['01', '02', '03', '04']
            for idx, n in enumerate(diffuse_nodes):
                if idx < len(slot_keys):
                    key = slot_keys[idx]
                    img = pupil_images_dict.get(key) or pupil_images_dict.get(str(int(key)))
                    if img:
                        img.colorspace_settings.name = 'sRGB'
                        n.image = img


class GenshinAvatarTextureImporter(GenshinTextureImporter):
    def __init__(self, material_names: ShaderMaterialNames):
        super().__init__(GameType.GENSHIN_IMPACT, TextureImporterType.AVATAR)
        self.material_names = material_names

        self.shader_identifier_service = ShaderIdentifierServiceFactory.create(GameType.GENSHIN_IMPACT.name)
        self.genshin_shader_version = self.shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)

    def import_textures(self, directory):
        if self.import_textures_from_json(directory):
            for mat in bpy.data.materials:
                if mat.use_nodes and not any(k in mat.name.lower() for k in ['outlines', 'outline', 'face', 'pupil', 'brow', 'eye']):
                    sync_material_category_textures(mat)
            return

        for name, folder, files in os.walk(directory):
            self.files = files
            dir_lower = os.path.abspath(directory).lower()
            is_sandrone = any(
                'sandrone' in f.lower() or 'marionettenew' in f.lower() or 'marionette_new' in f.lower() or 'newmarionette' in f.lower()
                for f in files
            ) or any(
                k in dir_lower for k in ['sandrone', 'marionettenew', 'marionette_new', 'newmarionette']
            )
            is_equip = any(f.lower().startswith(('equip_', 'equipskin_')) for f in files) or \
                       any(k in dir_lower for k in ['equip_', 'equipskin_']) or \
                       any(obj.name.startswith(('Equip_', 'EquipSkin_')) for obj in bpy.data.objects)

            pupil_diffuse_images = {}
            highlight_img = None
            for f_name in files:
                f_lower = f_name.lower()
                if (('eyehighlight' in f_lower or 'eyelight' in f_lower or 'eye_highlight' in f_lower or 'eye_light' in f_lower) and f_lower.endswith(('.png', '.tga', '.dds'))) or \
                   ('highlight' in f_lower and ('diffuse' in f_lower or 'mask' in f_lower) and f_lower.endswith(('.png', '.tga', '.dds'))):
                    img_p = os.path.normpath(os.path.join(name, f_name))
                    highlight_img = bpy.data.images.get(f_name) or bpy.data.images.load(filepath=img_p, check_existing=True)
                    highlight_img.alpha_mode = 'CHANNEL_PACKED'
                    highlight_img.colorspace_settings.name = 'sRGB'

                if ('pupil' in f_lower or 'pupila' in f_lower) and 'diffuse' in f_lower and f_lower.endswith(('.png', '.tga', '.dds')):
                    for k in ['01', '02', '03', '04', '1', '2', '3', '4']:
                        k_num = str(int(k))
                        k_0num = f'{int(key):02d}' if 'key' in locals() else f'{int(k):02d}'
                        if (f'pupil{k_0num}' in f_lower or f'pupil{k_num}' in f_lower or f'pupil_{k_0num}' in f_lower or f'pupil_{k_num}' in f_lower or
                            f'pupil 0{k_num}' in f_lower or f'pupil 00{k_num}' in f_lower or f'pupil{k_0num}_' in f_lower or f'pupil{k_num}_' in f_lower or
                            f'pupila{k_0num}' in f_lower or f'pupila{k_num}' in f_lower or f'pupila_{k_0num}' in f_lower or f'pupila_{k_num}' in f_lower):
                            img_p = os.path.normpath(os.path.join(name, f_name))
                            img_obj = bpy.data.images.get(f_name) or bpy.data.images.load(filepath=img_p, check_existing=True)
                            img_obj.alpha_mode = 'CHANNEL_PACKED'
                            img_obj.colorspace_settings.name = 'sRGB'
                            pupil_diffuse_images[k_0num] = img_obj
                            pupil_diffuse_images[k_num] = img_obj
                            break

            has_multiple_pupil_diffuse = len(pupil_diffuse_images) > 1

            if is_sandrone:
                target_pupil_mats = [
                    m for m in bpy.data.materials
                    if m.use_nodes and 'sandrone pupil' in m.name.lower() and 'outlines' not in m.name.lower()
                ]
                if not target_pupil_mats:
                    sandrone_mat = bpy.data.materials.get(getattr(self.material_names, 'SANDRONE_PUPIL', f'{self.material_names.MATERIAL_PREFIX}Sandrone pupil')) or \
                                   bpy.data.materials.get('HoYoverse - Genshin Sandrone pupil')
                    if sandrone_mat:
                        target_pupil_mats = [sandrone_mat]
                for target_pupil_mat in target_pupil_mats:
                    if pupil_diffuse_images:
                        self.set_multi_pupil_textures(target_pupil_mat, pupil_diffuse_images)
                    if highlight_img:
                        self.set_highlight_mask_texture(target_pupil_mat, highlight_img)
                if target_pupil_mats:
                    primary_pupil_mat = target_pupil_mats[0]
                    for obj in bpy.data.objects:
                        if obj.type == 'MESH':
                            for slot in obj.material_slots:
                                if slot.material and slot.material not in target_pupil_mats:
                                    m_low = slot.material.name.lower()
                                    if ('pupil' in m_low or 'pupila' in m_low) and not any(x in m_low for x in ['face', 'eyestar', 'eyeshadow', 'brow', 'outlines']):
                                        slot.material = primary_pupil_mat
            elif has_multiple_pupil_diffuse:
                target_pupil_mats = [
                    m for m in bpy.data.materials
                    if m.use_nodes and 'new pupil' in m.name.lower() and 'outlines' not in m.name.lower()
                ]
                if not target_pupil_mats:
                    new_pupil_mat = bpy.data.materials.get(getattr(self.material_names, 'NEW_PUPIL', f'{self.material_names.MATERIAL_PREFIX}New Pupil')) or \
                                    bpy.data.materials.get('HoYoverse - Genshin New Pupil') or \
                                    bpy.data.materials.get('miHoYo - Genshin New Pupil') or \
                                    bpy.data.materials.get('HoYoverse - New Pupil')
                    if new_pupil_mat:
                        target_pupil_mats = [new_pupil_mat]
                for target_pupil_mat in target_pupil_mats:
                    if pupil_diffuse_images:
                        self.set_multi_pupil_textures(target_pupil_mat, pupil_diffuse_images)
                    if highlight_img:
                        self.set_highlight_mask_texture(target_pupil_mat, highlight_img)
                if target_pupil_mats:
                    primary_pupil_mat = target_pupil_mats[0]
                    for obj in bpy.data.objects:
                        if obj.type == 'MESH':
                            for slot in obj.material_slots:
                                if slot.material and slot.material not in target_pupil_mats:
                                    m_low = slot.material.name.lower()
                                    if ('pupil' in m_low or 'pupila' in m_low) and not any(x in m_low for x in ['face', 'eyestar', 'eyeshadow', 'brow', 'outlines']):
                                        slot.material = primary_pupil_mat
            elif highlight_img:
                for mat_candidate in [
                    bpy.data.materials.get(getattr(self.material_names, 'NEW_PUPIL', None)),
                    bpy.data.materials.get('HoYoverse - Genshin New Pupil'),
                    bpy.data.materials.get(getattr(self.material_names, 'PUPIL', None)),
                    bpy.data.materials.get('HoYoverse - Genshin Pupil')
                ]:
                    if mat_candidate:
                        self.set_highlight_mask_texture(mat_candidate, highlight_img)

            for file in files:
                # load the file with the correct alpha mode
                img_path = os.path.normpath(os.path.join(name, file))
                img = bpy.data.images.get(file)
                if not img:
                    img = bpy.data.images.load(filepath=img_path, check_existing=True)
                img.alpha_mode = 'CHANNEL_PACKED'

                effect_hair_material = bpy.data.materials.get(f'{self.material_names.EFFECT_HAIR}') or \
                    bpy.data.materials.get(f'{self.material_names.EFFECT}')
                hair_material = bpy.data.materials.get(f'{self.material_names.HAIR}')
                helmet_material = bpy.data.materials.get(f'{self.material_names.HELMET}')
                helmet_emotion_material = bpy.data.materials.get(f'{self.material_names.HELMET_EMO}')
                face_material = bpy.data.materials.get(f'{self.material_names.FACE}')
                body_material = bpy.data.materials.get(f'{self.material_names.BODY}')
                body1_material = bpy.data.materials.get(f'{self.material_names.BODY1}')
                body2_material = bpy.data.materials.get(f'{self.material_names.BODY2}')
                dress2_material = bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}Dress2')
                gauntlet_material = bpy.data.materials.get(f'{self.material_names.GAUNTLET}')
                glass_material = bpy.data.materials.get(f'{self.material_names.GLASS}')
                glass_eff_material = bpy.data.materials.get(f'{self.material_names.GLASS_EFF}')
                leather_material = bpy.data.materials.get(f'{self.material_names.LEATHER}')
                pupil_material = bpy.data.materials.get(f'{self.material_names.PUPIL}') or \
                                 bpy.data.materials.get('HoYoverse - Genshin Pupil') or \
                                 bpy.data.materials.get('HoYoverse - Pupil') or \
                                 next((m for m in bpy.data.materials if 'Pupil' in m.name and 'Outlines' not in m.name), None)
                skirt_material = bpy.data.materials.get(f'{self.material_names.SKIRT}')
                star_cloak_material = bpy.data.materials.get(f'{self.material_names.STAR_CLOAK}')
                ribbon_material = bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}Ribbon') or \
                                  bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX_AFTER_RENAME}Ribbon')
                veilshadow_material = bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}VeilShadow') or \
                                      bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX_AFTER_RENAME}VeilShadow')
                stockings_material = bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}Stockings') or \
                                     bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX_AFTER_RENAME}Stockings')

                # Implement the texture in the correct node
                print(f'Importing texture {file} using {self.__class__.__name__}')
                if self.import_part_texture_to_matching_materials(file, img):
                    pass
                elif "Hair_Diffuse" in file and "Eff" not in file:
                    self.set_diffuse_texture(TextureType.HAIR, hair_material, img)
                elif "EffectHair_Diffuse" in file:
                    self.set_diffuse_texture(TextureType.HAIR, effect_hair_material, img)
                elif 'Helmet_Tex_Diffuse' in file:
                    self.set_diffuse_texture(TextureType.HAIR, helmet_material, img)
                elif 'HelmetEmo_Tex_Diffuse' in file:
                    self.set_diffuse_texture(TextureType.HAIR, helmet_emotion_material, img)
                elif "Hair_Lightmap" in file and "Eff" not in file:
                    self.set_lightmap_texture(TextureType.HAIR, hair_material, img)
                elif "EffectHair_Lightmap" in file:
                    self.set_lightmap_texture(TextureType.HAIR, effect_hair_material, img)
                elif 'Helmet_Tex_Lightmap' in file:
                    self.set_lightmap_texture(TextureType.HAIR, helmet_material, img)
                elif self.is_texture_identifiers_in_texture_name([ShaderMaterialNameKeywords.HAIR, ShaderMaterialNameKeywords.NORMAL_MAP], file):
                    self.set_normalmap_texture(TextureType.HAIR, hair_material, img)
                elif "Hair_Shadow_Ramp" in file:
                    self.set_shadow_ramp_texture(TextureType.HAIR, img)
                elif self.is_one_texture_identifier_in_texture_name(
                    [
                        ShaderMaterialNameKeywords.BODY_DIFFUSE, 
                        ShaderMaterialNameKeywords.BODY1_DIFFUSE, 
                        ShaderMaterialNameKeywords.BODY2_DIFFUSE, 
                    ], file):
                    selected_body_material = \
                        body_material if ShaderMaterialNameKeywords.BODY_DIFFUSE in file else \
                        body1_material if ShaderMaterialNameKeywords.BODY1_DIFFUSE in file else \
                        body2_material if ShaderMaterialNameKeywords.BODY2_DIFFUSE in file else body_material
                    self.set_diffuse_texture(TextureType.BODY, selected_body_material, img)
                    # If no lightmap exists in files, fallback to diffuse image for lightmap
                    has_body_lightmap = any(
                        self.is_one_texture_identifier_in_texture_name(
                            [ShaderMaterialNameKeywords.BODY_LIGHTMAP, ShaderMaterialNameKeywords.BODY1_LIGHTMAP, ShaderMaterialNameKeywords.BODY2_LIGHTMAP], f
                        ) or 'lightmap' in f.lower()
                        for f in files
                    )
                    if not has_body_lightmap:
                        self.set_lightmap_texture(TextureType.BODY, selected_body_material, img)
                    # Set Face Id in Body_Diffuse because not all Face Diffuse filenames have the full costume name
                    # Ex. Diluc's costume does not have DilucCostumeFlamme, but just Diluc
                    self.set_face_material_id(face_material, img)
                    self.set_body_hair_output_on_face_shader(face_material, img)
                    extra_mapping = [('Leather', leather_material), ('Gauntlet', gauntlet_material), ('Ribbon', ribbon_material), ('Veil', veilshadow_material), ('Stockings', stockings_material)]
                    for extra_name, extra_mat in extra_mapping:
                        if extra_mat and not self.has_dedicated_texture(extra_name, 'Diffuse'):
                            self.set_diffuse_texture(TextureType.BODY, extra_mat, img, override=False)
                    if not has_multiple_pupil_diffuse and not is_sandrone:
                        self.set_diffuse_texture(TextureType.BODY, pupil_material, img) if pupil_material and selected_body_material is body1_material else None
                    if star_cloak_material and self.star_cloak_uses_body_texture(file):
                        self.set_diffuse_texture(TextureType.BODY, star_cloak_material, img)
                elif self.is_one_texture_identifier_in_texture_name(
                    [
                        ShaderMaterialNameKeywords.BODY_LIGHTMAP, 
                        ShaderMaterialNameKeywords.BODY1_LIGHTMAP, 
                        ShaderMaterialNameKeywords.BODY2_LIGHTMAP, 
                    ], file):
                    selected_body_material = \
                        body_material if ShaderMaterialNameKeywords.BODY_LIGHTMAP in file else \
                        body1_material if ShaderMaterialNameKeywords.BODY1_LIGHTMAP in file else \
                        body2_material if ShaderMaterialNameKeywords.BODY2_LIGHTMAP in file else body_material
                    self.set_lightmap_texture(TextureType.BODY, selected_body_material, img)
                elif any(k in file.lower() for k in ['eyehighlight', 'eyelight', 'eye_highlight', 'eye_light']) or ('highlight' in file.lower() and ('diffuse' in file.lower() or 'mask' in file.lower())):
                    for p_name in [getattr(self.material_names, 'NEW_PUPIL', None), getattr(self.material_names, 'SANDRONE_PUPIL', None), 'HoYoverse - Genshin New Pupil', 'HoYoverse - Genshin Sandrone pupil', 'HoYoverse - Genshin Pupil']:
                        if p_name:
                            p_mat = bpy.data.materials.get(p_name)
                            if p_mat:
                                self.set_highlight_mask_texture(p_mat, img)
                    for mat in bpy.data.materials:
                        if 'pupil' in mat.name.lower() and 'outlines' not in mat.name.lower():
                            self.set_highlight_mask_texture(mat, img)
                elif "Pupil" in file and "Diffuse" in file:
                    if not has_multiple_pupil_diffuse and not is_sandrone:
                        self.set_diffuse_texture(TextureType.BODY, pupil_material, img)
                elif self.is_texture_identifiers_in_texture_name([ShaderMaterialNameKeywords.BODY, ShaderMaterialNameKeywords.NORMAL_MAP], file):
                    self.set_normalmap_texture(TextureType.BODY, body_material, img)
                elif self.is_one_texture_identifier_in_texture_name(
                    [
                        ShaderMaterialNameKeywords.BODY_SHADOW_RAMP,
                        ShaderMaterialNameKeywords.BODY1_SHADOW_RAMP,
                        ShaderMaterialNameKeywords.BODY2_SHADOW_RAMP,
                    ], file):
                    if ShaderMaterialNameKeywords.BODY2_SHADOW_RAMP in file:
                        self.set_shadow_ramp_texture(TextureType.BODY2, img)
                    else:  # Body/Body1
                        self.set_shadow_ramp_texture(TextureType.BODY, img)
                elif "Body_Specular_Ramp" in file or "Tex_Specular_Ramp" in file:
                    self.set_specular_ramp_texture(TextureType.BODY, img)
                elif "Face_Diffuse" in file:
                    self.set_face_diffuse_texture(face_material, img)
                elif self.is_texture_identifiers_in_texture_name(['Face', 'Shadow'], file):
                    self.set_face_shadow_texture(face_material, img)
                elif "FaceLightmap" in file:
                    self.set_face_lightmap_texture(img)
                elif "MetalMap" in file:
                    self.set_metalmap_texture(img)
                elif self.is_texture_identifiers_in_texture_name(['Glass', 'Diffuse'], file):
                    if glass_material:
                        self.set_glass_diffuse_texture(glass_material, img)
                    if glass_eff_material:
                        self.set_glass_diffuse_texture(glass_eff_material, img)
                elif self.is_texture_identifiers_in_texture_name(['Glass', 'Lightmap'], file):
                    if glass_material:
                        self.set_lightmap_texture(TextureType.BODY, glass_material, img)
                    if glass_eff_material:
                        self.set_lightmap_texture(TextureType.BODY, glass_eff_material, img)
                elif "Gauntlet_Diffuse" in file:
                    self.set_diffuse_texture(TextureType.BODY, gauntlet_material, img)
                elif "Gauntlet_Ligntmap" in file:
                    self.set_lightmap_texture(TextureType.BODY, gauntlet_material, img)
                elif "Gauntlet_Normalmap" in file:
                    self.set_normalmap_texture(TextureType.BODY, gauntlet_material, img)
                elif self.is_texture_identifiers_in_texture_name([ShaderMaterialNameKeywords.TAIL, 'Diffuse'], file):
                    if skirt_material:
                        self.set_diffuse_texture(TextureType.BODY, skirt_material, img)
                elif self.is_texture_identifiers_in_texture_name([ShaderMaterialNameKeywords.SKILLOBJ, 'Diffuse'], file):
                    expected_skillobj_identifier = file.split('_')[2]
                    skillobj_material = bpy.data.materials.get(f'{self.material_names.SKILLOBJ} {expected_skillobj_identifier}')
                    if skillobj_material:
                        self.set_diffuse_texture(TextureType.BODY, skillobj_material, img)
                elif self.is_texture_identifiers_in_texture_name([ShaderMaterialNameKeywords.SKILLOBJ, 'Lightmap'], file):
                    expected_skillobj_identifier = file.split('_')[2]
                    skillobj_material = bpy.data.materials.get(f'{self.material_names.SKILLOBJ} {expected_skillobj_identifier}')
                    if skillobj_material:
                        self.set_lightmap_texture(TextureType.BODY, skillobj_material, img)
                elif "Effect_Diffuse" in file:  # keep at bottom as a last resort check (Skirk support)
                    if star_cloak_material:
                        self.set_diffuse_texture(TextureType.HAIR, star_cloak_material, img)
                    else:  # backwards compatible before VFX shader existed, pre-v4.0
                        self.set_diffuse_texture(TextureType.HAIR, dress2_material, img)
                elif "Effect_Lightmap" in file:  # keep at bottom as a last resort check (Skirk support)
                    if star_cloak_material:  # No lightmap texture node as of this commit
                        self.set_lightmap_texture(TextureType.HAIR, star_cloak_material, img)
                    else:  # backwards compatible before VFX shader existed, pre-v4.0
                        self.set_lightmap_texture(TextureType.HAIR, dress2_material, img)
                elif self.is_one_texture_identifier_in_texture_name([  # Nyx Color Ramp
                    "NyxState_Ramp",
                    "Nyx_Ramp",
                    "Tex_Ramp"
                ], file):
                    self.set_nyx_color_ramp_texture(img)
                    self.set_up_night_soul_outlines_material()
                elif self.is_texture_identifiers_in_texture_name(ShaderMaterialNameKeywords.NIGHT_SOUL_MASK_IDENTIFIERS, file):
                    for material in bpy.data.materials.values():
                        self.set_up_night_soul_mask_texture(material, img)
                elif self.is_texture_identifiers_in_texture_name([ShaderMaterialNameKeywords.STOCKINGS_DETAILMAP], file):
                    self.set_stocking_texture(img)
                elif f_lower.startswith(('equip_', 'equipskin_')) or (is_equip and ('diffuse' in f_lower or 'lightmap' in f_lower or 'normal' in f_lower or 'shadow_ramp' in f_lower)):
                    weapon_materials = [
                        mat for mat in bpy.data.materials
                        if mat.use_nodes and 'outlines' not in mat.name.lower() and ('body' in mat.name.lower() or 'equip' in mat.name.lower())
                    ] or [body_material or selected_body_material]
                    if 'lightmap' in f_lower:
                        for mat in weapon_materials:
                            if mat:
                                self.set_lightmap_texture(TextureType.BODY, mat, img)
                    elif 'diffuse' in f_lower:
                        for mat in weapon_materials:
                            if mat:
                                self.set_diffuse_texture(TextureType.BODY, mat, img)
                    elif 'normal' in f_lower:
                        for mat in weapon_materials:
                            if mat:
                                self.set_normalmap_texture(TextureType.BODY, mat, img)
                    elif 'shadow_ramp' in f_lower:
                        self.set_shadow_ramp_texture(TextureType.BODY, img)
                elif self.import_part_texture_to_matching_materials(file, img):
                    pass
                else:
                    print(f'WARN: Ignoring texture {file}')

        # Fallback: for any material with unassigned lightmaps, assign the diffuse texture
        for mat in bpy.data.materials:
            if mat.use_nodes and not any(k in mat.name.lower() for k in ['outlines', 'outline', 'face', 'pupil', 'brow', 'eye']):
                lm_nodes = find_all_image_nodes_by_category(mat.node_tree, 'lightmap')
                unassigned_lm = [n for n in lm_nodes if not n.image]
                if unassigned_lm:
                    diff_nodes = find_all_image_nodes_by_category(mat.node_tree, 'diffuse')
                    diff_img = next((n.image for n in diff_nodes if n.image), None)
                    if diff_img:
                        for n in unassigned_lm:
                            n.image = diff_img

        for mat in bpy.data.materials:
            if mat.use_nodes and not any(k in mat.name.lower() for k in ['outlines', 'outline', 'face', 'pupil', 'brow', 'eye']):
                sync_material_category_textures(mat)

        if is_equip:
            white_ramp = get_or_create_white_texture("White_Shadow_Ramp")
            self.set_shadow_ramp_texture(TextureType.BODY, white_ramp)
            for mat in bpy.data.materials:
                if mat.use_nodes and 'outlines' not in mat.name.lower():
                    set_use_alpha_on_material(mat, 1.0)

            def _delete_hierarchy_by_name(obj_name):
                target = bpy.data.objects.get(obj_name)
                if not target:
                    return
                child_names = [c.name for c in bpy.data.objects if getattr(c, "parent", None) and c.parent.name == obj_name]
                for child_name in child_names:
                    _delete_hierarchy_by_name(child_name)
                obj_to_remove = bpy.data.objects.get(obj_name)
                if obj_to_remove:
                    try:
                        bpy.data.objects.remove(obj_to_remove, do_unlink=True)
                    except Exception:
                        pass

            matching_names = [o.name for o in bpy.data.objects if "head origin" in o.name.lower()]
            for name in matching_names:
                _delete_hierarchy_by_name(name)


class GenshinNPCTextureImporter(GenshinTextureImporter):
    def __init__(self, material_names: ShaderMaterialNames):
        super().__init__(GameType.GENSHIN_IMPACT, TextureImporterType.NPC)
        self.material_names = material_names

        self.shader_identifier_service = ShaderIdentifierServiceFactory.create(GameType.GENSHIN_IMPACT.name)
        self.genshin_shader_version = self.shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)
        self.shader_material_names = self.shader_identifier_service.get_shader_material_names_using_shader(self.genshin_shader_version)

    def import_textures(self, directory):
        self.import_textures_from_json(directory)

        for name, folder, files in os.walk(directory):
            self.files = files
            for file in files:
                # load the file with the correct alpha mode
                img_path = os.path.normpath(os.path.join(name, file))
                img = bpy.data.images.load(filepath = img_path, check_existing=True)
                img.alpha_mode = 'CHANNEL_PACKED'

                hair_material = bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}Hair')
                face_material = bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}Face')
                body_material = bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}Body')
                star_cloak_material = bpy.data.materials.get(f'{self.material_names.STAR_CLOAK}')

                # Implement the texture in the correct node
                print(f'Importing texture {file} using {self.__class__.__name__}')
                if self.is_texture_identifiers_in_texture_name(['Hair', 'Diffuse'], file) and \
                    not self.is_texture_identifiers_in_texture_name(['Eff'], file):
                    self.set_diffuse_texture(TextureType.HAIR, hair_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Hair', 'Lightmap'], file):
                    self.set_lightmap_texture(TextureType.HAIR, hair_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Hair', 'Normalmap'], file):
                    self.set_normalmap_texture(TextureType.HAIR, hair_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Hair', 'Shadow_Ramp'], file):
                    self.set_shadow_ramp_texture(TextureType.HAIR, img)

                elif self.is_texture_identifiers_in_texture_name(['Body', 'Diffuse'], file):
                    self.set_diffuse_texture(TextureType.BODY, body_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Body', 'Lightmap'], file):
                    self.set_lightmap_texture(TextureType.BODY, body_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Body', 'Normalmap'], file):
                    self.set_normalmap_texture(TextureType.BODY, body_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Body', 'Shadow_Ramp'], file):
                    self.set_shadow_ramp_texture(TextureType.BODY, img)

                elif self.is_texture_identifiers_in_texture_name(['Body', 'Specular_Ramp'], file) or \
                    self.is_texture_identifiers_in_texture_name(['Tex', 'Specular_Ramp'], file):
                    self.set_specular_ramp_texture(TextureType.BODY, img)

                elif self.is_texture_identifiers_in_texture_name(['Face', 'Diffuse'], file):
                    self.set_face_diffuse_texture(face_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Face', 'Shadow'], file) or \
                    (self.is_texture_identifiers_in_texture_name(['NPC', 'Face', 'Lightmap'], file) and
                        not self.is_texture_identifiers_in_files(['Face', 'Shadow'], files)):
                    # If Face Shadow exists, use that texture
                    # If Face Shadow does not exist in this folder, use "Face Lightmap" (actually an NPC Face Shadow texture)
                    self.set_face_shadow_texture(face_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Face', 'Lightmap'], file):
                    self.set_face_lightmap_texture(img)

                elif self.is_texture_identifiers_in_texture_name(['MetalMap'], file):
                    self.set_metalmap_texture(img)

                elif self.is_texture_identifiers_in_texture_name(['Cloak', 'Diffuse'], file):  # Paimon - VFX support
                    if star_cloak_material:
                        self.set_diffuse_texture(TextureType.HAIR, star_cloak_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Item', 'Diffuse'], file):
                    # Remove the '_Mat' suffix on materials and the MATERIAL_PREFIX, then search if it matches the texture filename
                    item_materials = [material for material in bpy.data.materials if 
                                      material.name.split('_Mat')[0].replace(self.shader_material_names.MATERIAL_PREFIX, '') in file]
                    if item_materials:
                        item_material = item_materials[0]
                        self.set_diffuse_texture(TextureType.BODY, item_material, img)
                elif self.is_texture_identifiers_in_texture_name(['Item', 'Lightmap'], file):
                    # Remove the '_Mat' suffix on materials and the MATERIAL_PREFIX, then search if it matches the texture filename
                    item_materials = [material for material in bpy.data.materials if 
                                      material.name.split('_Mat')[0].replace(self.shader_material_names.MATERIAL_PREFIX, '') in file]
                    if item_materials:
                        item_material = item_materials[0]
                        self.set_lightmap_texture(TextureType.BODY, item_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Hat', 'Diffuse'], file):
                    hat_materials = [material for material in bpy.data.materials if 'Hat' in material.name and 
                                     self.shader_material_names.MATERIAL_PREFIX in material.name]
                    if hat_materials:
                        hat_material = hat_materials[0]
                        self.set_diffuse_texture(TextureType.BODY, hat_material, img)
                elif self.is_texture_identifiers_in_texture_name(['Hat', 'Lightmap'], file):
                    hat_materials = [material for material in bpy.data.materials if 'Hat' in material.name and 
                                     self.shader_material_names.MATERIAL_PREFIX in material.name]
                    if hat_materials:
                        hat_material = hat_materials[0]
                        self.set_lightmap_texture(TextureType.BODY, hat_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Screw', 'Diffuse'], file):
                    screw_materials = [material for material in bpy.data.materials if 'Screw' in material.name and 
                                     self.shader_material_names.MATERIAL_PREFIX in material.name]
                    if screw_materials:
                        screw_material = screw_materials[0]
                        self.set_diffuse_texture(TextureType.BODY, screw_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Screw', 'Lightmap'], file):
                    screw_materials = [material for material in bpy.data.materials if 'Screw' in material.name and 
                                     self.shader_material_names.MATERIAL_PREFIX in material.name]
                    if screw_materials:
                        screw_material = screw_materials[0]
                        self.set_lightmap_texture(TextureType.BODY, screw_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Others', 'Diffuse'], file):
                    others_materials = [material for material in bpy.data.materials if 'Others' in material.name and 
                                     self.shader_material_names.MATERIAL_PREFIX in material.name]
                    if others_materials:
                        others_material = others_materials[0]
                        self.set_diffuse_texture(TextureType.BODY, others_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Others', 'Lightmap'], file):
                    others_materials = [material for material in bpy.data.materials if 'Others' in material.name and 
                                     self.shader_material_names.MATERIAL_PREFIX in material.name]
                    if others_materials:
                        others_material = others_materials[0]
                        self.set_lightmap_texture(TextureType.BODY, others_material, img)

                elif any(k in file.lower() for k in ['eyehighlight', 'eyelight', 'eye_highlight', 'eye_light']) or ('highlight' in file.lower() and ('diffuse' in file.lower() or 'mask' in file.lower())):
                    for p_name in [getattr(self.material_names, 'NEW_PUPIL', None), getattr(self.material_names, 'SANDRONE_PUPIL', None), 'HoYoverse - Genshin New Pupil', 'HoYoverse - Genshin Sandrone pupil', 'HoYoverse - Genshin Pupil']:
                        if p_name:
                            p_mat = bpy.data.materials.get(p_name)
                            if p_mat:
                                self.set_highlight_mask_texture(p_mat, img)
                    for mat in bpy.data.materials:
                        if 'pupil' in mat.name.lower() and 'outlines' not in mat.name.lower():
                            self.set_highlight_mask_texture(mat, img)
                elif self.import_part_texture_to_matching_materials(file, img):
                    pass
                else:
                    print(f'WARN: Ignoring texture {file}')


class GenshinMonsterTextureImporter(GenshinTextureImporter):
    def __init__(self, material_names: ShaderMaterialNames):
        super().__init__(GameType.GENSHIN_IMPACT, TextureImporterType.MONSTER)
        self.material_names = material_names

        self.shader_identifier_service = ShaderIdentifierServiceFactory.create(GameType.GENSHIN_IMPACT.name)
        self.genshin_shader_version = self.shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)

    def import_textures(self, directory):
        self.import_textures_from_json(directory)

        for name, folder, files in os.walk(directory):
            self.files = files
            for file in files:
                # load the file with the correct alpha mode
                img_path = os.path.normpath(os.path.join(name, file))
                img = bpy.data.images.load(filepath = img_path, check_existing=True)
                img.alpha_mode = 'CHANNEL_PACKED'

                hair_material = bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}Hair')
                face_material = bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}Face')
                body_material = bpy.data.materials.get(f'{self.material_names.MATERIAL_PREFIX}Body')
                star_cloak_material = bpy.data.materials.get(f'{self.material_names.STAR_CLOAK}')

                # Implement the texture in the correct node
                print(f'Importing texture {file} using {self.__class__.__name__}')

                if self.is_texture_identifiers_in_texture_name(['Body', 'Tex', 'Diffuse'], file) or \
                    (self.is_texture_identifiers_in_texture_name(['Tex', 'Diffuse'], file) and \
                    not self.is_texture_identifiers_in_files(['Hair'], files)):
                    self.set_diffuse_texture(TextureType.BODY, body_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Body', 'Tex', 'Lightmap'], file) or \
                    (self.is_texture_identifiers_in_texture_name(['Tex', 'Lightmap'], file) and \
                    not self.is_texture_identifiers_in_files(['Hair'], files)):
                    self.set_lightmap_texture(TextureType.BODY, body_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Hair', 'Tex', 'Diffuse'], file) or \
                    (self.is_texture_identifiers_in_texture_name(['Tex', 'Diffuse'], file) and \
                    not self.is_texture_identifiers_in_files(['Body'], files)):
                    self.set_diffuse_texture(TextureType.HAIR, hair_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Hair', 'Tex', 'Lightmap'], file) or \
                    (self.is_texture_identifiers_in_texture_name(['Tex', 'Lightmap'], file) and \
                    not self.is_texture_identifiers_in_files(['Body'], files)):
                    self.set_lightmap_texture(TextureType.HAIR, hair_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Body_Shadow_Ramp'], file):
                    self.set_shadow_ramp_texture(TextureType.BODY, img)
                elif self.is_texture_identifiers_in_texture_name(['Hair_Shadow_Ramp'], file):
                    self.set_shadow_ramp_texture(TextureType.HAIR, img)
                elif self.is_texture_identifiers_in_texture_name(['Tex', 'Specular_Ramp'], file):
                    self.set_specular_ramp_texture(TextureType.BODY, img)

                elif self.is_texture_identifiers_in_texture_name(['Face', 'Diffuse'], file):
                    self.set_face_diffuse_texture(face_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Face', 'Shadow'], file) or \
                    (self.is_texture_identifiers_in_texture_name(['NPC', 'Face', 'Lightmap'], file) and
                        not self.is_texture_identifiers_in_files(['Face', 'Shadow'], files)):
                    # If Face Shadow exists, use that texture
                    # If Face Shadow does not exist in this folder, use "Face Lightmap" (actually an NPC Face Shadow texture)
                    self.set_face_shadow_texture(face_material, img)

                elif self.is_texture_identifiers_in_texture_name(['Face', 'Lightmap'], file):
                    self.set_face_lightmap_texture(img)

                elif self.is_texture_identifiers_in_texture_name(['MetalMap'], file):
                    self.set_metalmap_texture(img)

                elif self.is_texture_identifiers_in_texture_name(['Hand', 'Tex', 'Eff'], file):  # Asmoday - VFX Support
                    self.set_diffuse_texture(TextureType.BODY, star_cloak_material, img)

                else:
                    print(f'WARN: Ignoring texture {file}')


class HonkaiStarRailTextureImporter(GenshinTextureImporter):
    def __init__(self, game_type: GameType, character_type: TextureImporterType, material_names: ShaderMaterialNames, texture_node_names: TextureNodeNames):
        super().__init__(game_type, character_type)
        self.material_names = material_names
        self.texture_node_names: TextureNodeNames = texture_node_names

    '''
    Helper: find Image Texture nodes in a material by searching named candidates first,
    then falling back to matching node names/labels containing keywords.
    '''
    def _find_image_nodes(self, material, named_nodes, type_key):
        if not material or not material.node_tree:
            return []
        found = [n for n in named_nodes if n]
        if not found:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    name_lower = node.name.lower()
                    label_lower = node.label.lower()
                    
                    if type_key == 'diffuse':
                        # Look for diffuse / color / sRGB keywords
                        if ('diffuse' in name_lower or 'diffuse' in label_lower or \
                            'color' in name_lower or 'color' in label_lower or \
                            'srgb' in name_lower or 'srgb' in label_lower or \
                            'image texture.001' in name_lower) and not \
                           ('ramp' in name_lower or 'ramp' in label_lower or \
                            'lightmap' in name_lower or 'lightmap' in label_lower or \
                            'non-color' in name_lower or 'non-color' in label_lower or \
                            'non_color' in name_lower or 'non_color' in label_lower or \
                            'mask' in name_lower or 'mask' in label_lower or \
                            'expression' in name_lower or 'expression' in label_lower):
                            found.append(node)
                    elif type_key == 'lightmap':
                        # Look for lightmap / non-color keywords
                        if ('lightmap' in name_lower or 'lightmap' in label_lower or \
                            'non-color' in name_lower or 'non-color' in label_lower or \
                            'non_color' in name_lower or 'non_color' in label_lower or \
                            'image texture.002' in name_lower) and not \
                           ('ramp' in name_lower or 'ramp' in label_lower or \
                            'diffuse' in name_lower or 'diffuse' in label_lower or \
                            'srgb' in name_lower or 'srgb' in label_lower or \
                            'color' in name_lower or 'color' in label_lower or \
                            'mask' in name_lower or 'mask' in label_lower or \
                            'expression' in name_lower or 'expression' in label_lower):
                            found.append(node)
        return found

    '''
    Lazy attempt at setting all known diffuses across Nya222 HSR Shader and StellarToon
    If the material has the texture node, set it.
    When the texture type is FACE and a face-specific color node exists, skip the generic
    nya222/outline diffuse node to avoid overwriting the body diffuse slot in face materials.
    '''
    def set_diffuse_texture(self, type: TextureType, material, img):
        if not material or not material.node_tree:
            return
        nya222_or_outline_diffuse_node = material.node_tree.nodes.get(self.texture_node_names.DIFFUSE)
        # Support alternative node naming (e.g. 'Diffuse (sRGB) (Channel Packed)')
        diffuse_alt_node = material.node_tree.nodes.get(getattr(self.texture_node_names, 'DIFFUSE_ALT', ''))
        diffuse_uv0_node = material.node_tree.nodes.get(f'{type.value}{self.texture_node_names.DIFFUSE_UV0_SUFFIX}')
        diffuse_uv1_node = material.node_tree.nodes.get(f'{type.value}{self.texture_node_names.DIFFUSE_UV1_SUFFIX}')
        face_color_node = material.node_tree.nodes.get(f'{type.value}{self.texture_node_names.FACE_COLOR_SUFFIX}')

        # If a face-specific color node exists (StellarToon), do NOT also write to the
        # generic diffuse node – that node is shared with body-type materials and would
        # end up holding the wrong texture.
        skip_generic_diffuse = (type is TextureType.FACE and face_color_node is not None)

        named_candidates = [
            None if skip_generic_diffuse else nya222_or_outline_diffuse_node,
            None if skip_generic_diffuse else diffuse_alt_node,
            diffuse_uv0_node,
            diffuse_uv1_node,
            face_color_node,
        ]

        for diffuse_node in self._find_image_nodes(material, named_candidates, 'diffuse'):
            diffuse_node.image = img

    '''
    Lazy attempt at setting all known lightmaps across Nya222 HSR Shader and StellarToon.
    If the material has the texture node, set it.
    '''
    def set_lightmap_texture(self, type: TextureType, material, img):
        if not material or not material.node_tree:
            return
        img.colorspace_settings.name='Non-Color'
        lightmap_nya222_node = material.node_tree.nodes.get(self.texture_node_names.LIGHTMAP)
        # Support alternative node naming (e.g. 'Lightmap (Non-Color) (Channel Packed)')
        lightmap_alt_node = material.node_tree.nodes.get(getattr(self.texture_node_names, 'LIGHTMAP_ALT', ''))
        lightmap_uv0_node = material.node_tree.nodes.get(f'{type.value}{self.texture_node_names.LIGHTMAP_UV0_SUFFIX}')
        lightmap_uv1_node = material.node_tree.nodes.get(f'{type.value}{self.texture_node_names.LIGHTMAP_UV1_SUFFIX}')

        for lightmap_node in self._find_image_nodes(
            material,
            [lightmap_nya222_node, lightmap_alt_node, lightmap_uv0_node, lightmap_uv1_node],
            'lightmap'
        ):
            lightmap_node.image = img

    def set_warm_shadow_ramp_texture(self, type: TextureType, img):
        ramp_node_name = \
            self.texture_node_names.BODY_WARM_RAMP if type is TextureType.BODY else \
            self.texture_node_names.HAIR_WARM_RAMP

        ramp_texture_node = bpy.data.node_groups.get(self.texture_node_names.BODY_WARM_RAMP_NODE_GROUP).nodes[ramp_node_name] if \
            type is TextureType.BODY else bpy.data.node_groups.get(self.texture_node_names.HAIR_WARM_RAMP_NODE_GROUP).nodes[ramp_node_name]
        ramp_texture_node.image = img

    def set_cool_shadow_ramp_texture(self, type: TextureType, img):
        if not bpy.data.node_groups.get(self.texture_node_names.BODY_COOL_RAMP_NODE_GROUP) or \
            not bpy.data.node_groups.get(self.texture_node_names.HAIR_COOL_RAMP_NODE_GROUP):
            return

        ramp_node_name = \
            self.texture_node_names.BODY_COOL_RAMP if type is TextureType.BODY else \
            self.texture_node_names.HAIR_COOL_RAMP

        ramp_texture_node = bpy.data.node_groups.get(self.texture_node_names.BODY_COOL_RAMP_NODE_GROUP).nodes[ramp_node_name] if \
            type is TextureType.BODY else bpy.data.node_groups.get(self.texture_node_names.HAIR_COOL_RAMP_NODE_GROUP).nodes[ramp_node_name]
        ramp_texture_node.image = img

    def set_weapon_ramp_texture(self, img, override=False):
        weapon_ramp_node = bpy.data.node_groups[f'{self.texture_node_names.WEAPON_RAMP_NODE_GROUP}'].nodes[
            self.texture_node_names.WEAPON_RAMP
        ]
        
        if override or not weapon_ramp_node.image:
            weapon_ramp_node.image = img

    def set_facemap_texture(self, img):
        img.colorspace_settings.name='Non-Color'
        bpy.data.node_groups[self.texture_node_names.FACE_LIGHTMAP_NODE_GROUP].nodes[
            self.texture_node_names.FACE_LIGHTMAP].image = img

    def set_face_expression_texture(self, face_material, img):
        img.colorspace_settings.name='Non-Color'

        # Nya222 Shader has it inside a node group
        face_expression_node_group = bpy.data.node_groups.get(self.texture_node_names.FACE_EXPRESSION_NODE_GROUP)
        if face_expression_node_group:
            face_expression_node_group.nodes[self.texture_node_names.FACE_EXPRESSION_MAP].image = img
        
        # Stellartoon
        face_expression_node = face_material.node_tree.nodes.get(self.texture_node_names.FACE_EXPRESSION_MAP)
        if face_expression_node:
            face_expression_node.image = img

    def set_stocking_texture(self, type: TextureType, material, img):
        body_material = bpy.data.materials.get(self.material_names.BODY)
        body1_material = bpy.data.materials.get(self.material_names.BODY1)
        body2_material = bpy.data.materials.get(self.material_names.BODY2)
        img.colorspace_settings.name='Non-Color'

        # If Body material or Body1 material apply to Body1 Stockings
        # Else Body2 material or Body Stockings texture with Body1/Body2 materials apply to Body2 Stockings
        if (body_material and material is body_material) or (body1_material and material is body1_material):
            stockings_body1_node_group = bpy.data.node_groups.get(self.texture_node_names.STOCKINGS_BODY1_NODE_GROUP)

            if stockings_body1_node_group:  # Nya222
                stockings_body1_node_group.nodes[self.texture_node_names.STOCKINGS].image = img

            # StellarToon Shader
            self.set_up_stellartoon_stocking_texture(material, img)  # Body or Body1 material
        else:
            stockings_body2_node_group = bpy.data.node_groups.get(self.texture_node_names.STOCKINGS_BODY2_NODE_GROUP)
            if stockings_body2_node_group:  # Nya222
                stockings_body2_node_group.nodes[self.texture_node_names.STOCKINGS].image = img

            # StellarToon Shader
            self.set_up_stellartoon_stocking_texture(body2_material, img)

    def set_up_stellartoon_stocking_texture(self, material, img):
        if not material or not material.node_tree:
            body_stockings_node_group = bpy.data.node_groups.get(self.texture_node_names.STOCKINGS_NODE_GROUP)
            if body_stockings_node_group and self.texture_node_names.STOCKINGS in body_stockings_node_group.nodes:
                body_stockings_node_group.nodes[self.texture_node_names.STOCKINGS].image = img
            return

        body_stockings_node = material.node_tree.nodes.get(self.texture_node_names.STOCKINGS)
        body_stockings_node_group = bpy.data.node_groups.get(self.texture_node_names.STOCKINGS_NODE_GROUP)

        if body_stockings_node:
            body_stockings_node.image = img
            body_shader = material.node_tree.nodes.get(StellarToonShaderNodeNames.BODY_SHADER)
            if body_shader and body_shader.inputs.get(StellarToonShaderNodeNames.ENABLE_STOCKINGS):
                body_shader.inputs.get(StellarToonShaderNodeNames.ENABLE_STOCKINGS).default_value = 1.0
        if body_stockings_node_group and self.texture_node_names.STOCKINGS in body_stockings_node_group.nodes:
            body_stockings_node_group.nodes[self.texture_node_names.STOCKINGS].image = img

class HonkaiStarRailAvatarTextureImporter(HonkaiStarRailTextureImporter):
    def __init__(self, material_names: ShaderMaterialNames, texture_node_names: TextureNodeNames):
        super().__init__(
            GameType.HONKAI_STAR_RAIL, 
            TextureImporterType.HSR_AVATAR, 
            material_names, 
            texture_node_names
        )
        self.material_names = material_names

    def _collect_image_files(self, directory):
        image_exts = ('.png', '.tga', '.dds', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.webp')
        candidates = [
            directory,
            os.path.join(directory, "Textures"),
        ]
        seen_paths = set()
        image_files = []

        for d in candidates:
            if not d or not os.path.isdir(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(image_exts):
                        full_p = os.path.normpath(os.path.join(root, f))
                        if full_p not in seen_paths:
                            seen_paths.add(full_p)
                            image_files.append((f, full_p))
        return image_files

    def _resolve_image(self, tex_name, image_files):
        if not tex_name:
            return None

        # Check if an existing image with the same name actually belongs to the character folder
        existing_img = bpy.data.images.get(tex_name)
        if existing_img and (existing_img.has_data or (hasattr(existing_img, 'filepath') and existing_img.filepath)):
            img_fp = getattr(existing_img, 'filepath', '')
            if img_fp and any(os.path.samefile(img_fp, fp) for _, fp in image_files if os.path.exists(img_fp) and os.path.exists(fp)):
                existing_img.alpha_mode = 'CHANNEL_PACKED'
                return existing_img

        t_clean = os.path.splitext(tex_name)[0].strip()
        t_low = t_clean.lower()

        # 1. Exact stem match
        for fname, fpath in image_files:
            stem = os.path.splitext(fname)[0]
            if stem.lower() == t_low:
                img = bpy.data.images.get(fname) or bpy.data.images.load(filepath=fpath, check_existing=True)
                img.alpha_mode = 'CHANNEL_PACKED'
                return img

        # 2. Match ignoring common prefixes
        t_no_prefix = re.sub(r'^(avatar_tex_|tex_avatar_|tex_|avatar_)', '', t_low)
        for fname, fpath in image_files:
            stem = os.path.splitext(fname)[0].lower()
            stem_no_prefix = re.sub(r'^(avatar_tex_|tex_avatar_|tex_|avatar_)', '', stem)
            if stem_no_prefix == t_no_prefix or stem == t_no_prefix or stem_no_prefix == t_low:
                img = bpy.data.images.get(fname) or bpy.data.images.load(filepath=fpath, check_existing=True)
                img.alpha_mode = 'CHANNEL_PACKED'
                return img

        # 3. Prefix / Suffix match
        for fname, fpath in image_files:
            stem = os.path.splitext(fname)[0].lower()
            if stem.startswith(t_low) or t_low.startswith(stem) or stem.endswith(t_low) or t_low.endswith(stem):
                img = bpy.data.images.get(fname) or bpy.data.images.load(filepath=fpath, check_existing=True)
                img.alpha_mode = 'CHANNEL_PACKED'
                return img

        # 4. Substring match
        for fname, fpath in image_files:
            if t_low in fname.lower() or fname.lower() in t_low:
                img = bpy.data.images.get(fname) or bpy.data.images.load(filepath=fpath, check_existing=True)
                img.alpha_mode = 'CHANNEL_PACKED'
                return img

        return None

    def _build_hsr_json_texture_map(self, directory):
        candidates = [
            os.path.join(directory, "Materials"),
            directory,
        ]
        materials_dirs = []
        for d in candidates:
            if d and os.path.isdir(d) and d not in materials_dirs:
                if any(f.lower().endswith('.json') and not f.startswith('config') and not f.startswith('character_setup_wizard') for f in os.listdir(d)):
                    materials_dirs.append(d)

        json_map = {}
        for m_dir in materials_dirs:
            for jf in os.listdir(m_dir):
                if not jf.lower().endswith('.json') or jf.startswith('config') or jf.startswith('character_setup_wizard'):
                    continue
                jpath = os.path.join(m_dir, jf)
                try:
                    with open(jpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    continue

                tex_envs = {}
                if isinstance(data, dict):
                    saved_props = data.get('m_SavedProperties') or data.get('0 UnityPropertySheet m_SavedProperties') or {}
                    raw_envs = saved_props.get('m_TexEnvs') or saved_props.get('0 map m_TexEnvs') or data.get('m_TexEnvs') or {}

                    if isinstance(raw_envs, dict):
                        tex_envs = raw_envs
                    elif isinstance(raw_envs, list):
                        for item in raw_envs:
                            if isinstance(item, dict):
                                k = item.get('Key') or item.get('0 pair data', {}).get('1 string first')
                                v = item.get('Value') or item.get('0 pair data', {}).get('0 TextureEnv second')
                                if k:
                                    tex_envs[k] = v

                def extract_tex_name(slot_keys):
                    for k in slot_keys:
                        slot = tex_envs.get(k)
                        if not slot:
                            continue
                        if isinstance(slot, dict):
                            tex_obj = slot.get('m_Texture') or slot.get('m_Texture2D') or slot.get('0 PPtr<Texture> m_Texture') or {}
                            if isinstance(tex_obj, dict):
                                name = tex_obj.get('Name') or tex_obj.get('m_Name') or tex_obj.get('1 string m_Name')
                                if name:
                                    return name
                            elif isinstance(slot.get('Name'), str):
                                return slot.get('Name')
                        elif isinstance(slot, str):
                            return slot
                    return None

                extracted = {
                    'diffuse': extract_tex_name(['_MainTex', '_BaseTex', '_BaseTexV2', '_ColorTex', '_Diffuse', '_Tex', '_EyeColorMap']),
                    'lightmap': extract_tex_name(['_LightMapTex', '_LightMap', '_Lightmap', '_LightmapTex', '_MainLightmap', '_LightTex']),
                    'warm_ramp': extract_tex_name(['_WarmRampTex', '_WarmRamp', '_ShadowRampTex', '_PackedShadowRampTex', '_Body_Warm_Ramp', '_Hair_Warm_Ramp', '_RampTex']),
                    'cool_ramp': extract_tex_name(['_CoolRampTex', '_CoolRamp', '_Body_Cool_Ramp', '_Hair_Cool_Ramp']),
                    'stockings': extract_tex_name(['_StockingsTex', '_StockingTex', '_Stockings', '_Body_Stockings']),
                    'facemap': extract_tex_name(['_FaceMapTex', '_FaceMap', '_FaceLightMap', '_Face_LightMap', '_FaceShadow']),
                    'expression': extract_tex_name(['_ExpressionMap', '_Face_ExpressionMap', '_FaceExpressionMap', '_Expression']),
                    'normal': extract_tex_name(['_BumpMap', '_NormalMap', '_NormalTex']),
                }

                mat_key = os.path.splitext(jf)[0].lower()
                json_map[mat_key] = extracted

        return json_map

    def _find_json_textures_for_material(self, mat, json_map):
        if not json_map:
            return None

        orig_mat_name = mat.get("_original_material_name") or ""
        mat_name = mat.name

        def clean_key(name):
            k = re.sub(r'\.\d+$', '', name.lower())
            k = re.sub(r'^(mihoyo - honkai star rail |hoyoverse - star rail |mihoyo - genshin |hoyoverse - genshin |stellartoon )', '', k)
            k = k.replace('mat_', '').replace('_mat', '').replace('material', '')
            return k.strip(' _-')

        m_clean = clean_key(mat_name)
        orig_clean = clean_key(orig_mat_name) if orig_mat_name else ""

        # 1. Exact match on candidates
        for candidate in [mat_name.lower(), orig_mat_name.lower(), m_clean, orig_clean]:
            if candidate and candidate in json_map:
                return json_map[candidate]
            for j_key, tex_dict in json_map.items():
                if candidate and (j_key == candidate or clean_key(j_key) == candidate):
                    return tex_dict

        # 2. Body part matching
        parts = ['hair', 'face', 'body_trans', 'body2_trans', 'body3', 'body2', 'body1', 'body_leather', 'body_tuoma', 'body_stockings', 'body_s', 'body_d', 'body', 'coat', 'weapon', 'handbag', 'kendama', 'eyeshadow', 'eyespecular', 'eyestar']
        target_part = None
        for p in parts:
            if p in m_clean or (orig_clean and p in orig_clean):
                target_part = p
                break

        if target_part:
            for j_key, tex_dict in json_map.items():
                j_clean = clean_key(j_key)
                if target_part in j_clean:
                    return tex_dict

        # 3. Token similarity
        m_tokens = set(re.split(r'[^a-zA-Z0-9]+', m_clean + " " + orig_clean)) - {'', 'mat', 'mihoyo', 'hoyoverse', 'star', 'rail'}
        best_match = None
        best_score = 0
        for j_key, tex_dict in json_map.items():
            j_tokens = set(re.split(r'[^a-zA-Z0-9]+', clean_key(j_key))) - {'', 'mat', 'mihoyo', 'hoyoverse', 'star', 'rail'}
            score = len(m_tokens.intersection(j_tokens))
            if score > best_score:
                best_score = score
                best_match = tex_dict

        if best_match and best_score > 0:
            return best_match

        return None

    def _get_current_material_texture(self, material):
        if not material:
            return None

        # 1. Diffuse node image
        if material.use_nodes and material.node_tree:
            diffuse_nodes = find_all_image_nodes_by_category(material.node_tree, 'diffuse')
            for n in diffuse_nodes:
                if n.image and n.image.name and not n.image.name.startswith('White_'):
                    return n.image

        # 2. _original_fbx_texture property
        orig_tex_name = material.get('_original_fbx_texture')
        if orig_tex_name:
            img = bpy.data.images.get(orig_tex_name)
            if img:
                return img

        # 3. Any non-ramp image node
        if material.use_nodes and material.node_tree:
            for n in material.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image and n.image.name:
                    i_low = n.image.name.lower()
                    if not any(k in i_low for k in ['ramp', 'white_', 'mask', 'curve']):
                        return n.image

        # 4. Check original material if recorded
        orig_mat_name = material.get('_original_material_name')
        if orig_mat_name:
            orig_mat = bpy.data.materials.get(orig_mat_name)
            if orig_mat and orig_mat.use_nodes and orig_mat.node_tree:
                for n in orig_mat.node_tree.nodes:
                    if n.type == 'TEX_IMAGE' and n.image and n.image.name:
                        return n.image

        return None

    def _find_matching_lightmap_for_texture(self, tex_name, image_files):
        if not tex_name:
            return None

        stem = os.path.splitext(tex_name)[0].strip()
        tex_clean = re.sub(r'\.\d+$', '', stem)

        candidates = []
        sub_patterns = [
            (r'_Color_A_L$', '_LightMap_L'),
            (r'_Color_A$', '_LightMap_A'),
            (r'_Color_L$', '_LightMap_L'),
            (r'_Color_0(\d)$', r'_LightMap_0\1'),
            (r'_Color$', '_LightMap'),
            (r'_Diffuse$', '_LightMap'),
            (r'_Col$', '_LightMap'),
            (r'_BaseColor$', '_LightMap'),
        ]
        for pat, repl in sub_patterns:
            cand = re.sub(pat, repl, tex_clean, flags=re.IGNORECASE)
            if cand != tex_clean and cand not in candidates:
                candidates.append(cand)
                candidates.append(cand.replace('_LightMap', '_Lightmap'))
                candidates.append(cand.replace('_LightMap', '_LM'))

        base_prefix = re.sub(r'(_color|_diffuse|_col|_basecolor|_tex_diffuse|_tex|_basetex|_albedo)(_a_l|_a|_l|_0\d)?$', '', tex_clean, flags=re.IGNORECASE)
        base_prefix_clean = re.sub(r'(_d|_s)$', '', base_prefix, flags=re.IGNORECASE)

        for bp in [base_prefix, base_prefix_clean]:
            for suffix in ['_LightMap_L', '_LightMap', '_Lightmap_L', '_Lightmap', '_LigthMap', '_LM', '_M']:
                c = f"{bp}{suffix}"
                if c not in candidates:
                    candidates.append(c)

        filtered_candidates = [c for c in candidates if c.lower() != tex_clean.lower() and not any(k in c.lower() for k in ['color', 'diffuse'])]

        for cand in filtered_candidates:
            img = self._resolve_image(cand, image_files)
            if img and img.name.lower() != tex_name.lower() and not any(k in img.name.lower() for k in ['color', 'diffuse']):
                return img

        bp_low = base_prefix_clean.lower()
        for fname, fpath in image_files:
            f_low = fname.lower()
            if ('lightmap' in f_low or 'ligthmap' in f_low) and bp_low in f_low and not any(k in f_low for k in ['color', 'diffuse', 'eff', 'lut', 'curve', 'materialid']):
                img = bpy.data.images.get(fname) or bpy.data.images.load(filepath=fpath, check_existing=True)
                img.alpha_mode = 'CHANNEL_PACKED'
                return img

        return None

    def _assign_global_character_textures(self, image_files, json_map):
        for fname, fpath in image_files:
            f_low = fname.lower()
            if any(k in f_low for k in ['eff', 'lut', 'curve', 'materialid']):
                continue

            # Hair Warm Ramp
            if 'hair' in f_low and ('warm_ramp' in f_low or 'warmramp' in f_low or 'hair_ramp' in f_low):
                img = self._resolve_image(fname, image_files)
                if img: self.set_warm_shadow_ramp_texture(TextureType.HAIR, img)
            # Hair Cool Ramp
            elif 'hair' in f_low and ('cool_ramp' in f_low or 'coolramp' in f_low):
                img = self._resolve_image(fname, image_files)
                if img: self.set_cool_shadow_ramp_texture(TextureType.HAIR, img)
            # Body Warm Ramp
            elif ('body_warm_ramp' in f_low or 'body_ramp' in f_low or ('warm_ramp' in f_low and 'body' in f_low) or ('warm_ramp' in f_low and not any(k in f_low for k in ['hair', 'weapon']))) and not any(k in f_low for k in ['weapon', 'hair']):
                img = self._resolve_image(fname, image_files)
                if img:
                    self.set_warm_shadow_ramp_texture(TextureType.BODY, img)
                    self.set_weapon_ramp_texture(img)
            # Body Cool Ramp
            elif ('body_cool_ramp' in f_low or ('cool_ramp' in f_low and 'body' in f_low) or ('cool_ramp' in f_low and not any(k in f_low for k in ['hair', 'weapon']))) and not any(k in f_low for k in ['weapon', 'hair']):
                img = self._resolve_image(fname, image_files)
                if img: self.set_cool_shadow_ramp_texture(TextureType.BODY, img)
            # Weapon Ramp
            elif 'weapon' in f_low and 'ramp' in f_low and not any(k in f_low for k in ['body', 'hair']):
                img = self._resolve_image(fname, image_files)
                if img: self.set_weapon_ramp_texture(img, override=True)
            # Face Map
            elif 'facemap' in f_low or ('face' in f_low and 'lightmap' in f_low):
                img = self._resolve_image(fname, image_files)
                if img: self.set_facemap_texture(img)
            # Face Expression
            elif 'expressionmap' in f_low or 'expression' in f_low:
                img = self._resolve_image(fname, image_files)
                if img:
                    face_material = bpy.data.materials.get(self.material_names.FACE)
                    if face_material:
                        self.set_face_expression_texture(face_material, img)
            # Stockings
            elif ('stockings' in f_low or 'stocking' in f_low) and not any(k in f_low for k in ['lut', 'materialid']):
                img = self._resolve_image(fname, image_files)
                if img:
                    body_mat = bpy.data.materials.get(self.material_names.BODY) or \
                               bpy.data.materials.get(self.material_names.BODY1) or \
                               bpy.data.materials.get(self.material_names.BODY2) or \
                               bpy.data.materials.get(f"{getattr(self.material_names, 'MATERIAL_PREFIX', '')}Body_Stockings")
                    if body_mat:
                        self.set_stocking_texture(TextureType.BODY, body_mat, img)

    def import_textures(self, directory):
        image_files = self._collect_image_files(directory)
        json_map = self._build_hsr_json_texture_map(directory)

        prefix = getattr(self.material_names, 'MATERIAL_PREFIX', '')
        character_materials = []
        for mat in bpy.data.materials:
            if not mat.use_nodes:
                continue
            if 'outlines' in mat.name.lower() or 'outline' in mat.name.lower():
                continue
            if prefix and mat.name.startswith(prefix):
                character_materials.append(mat)

        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    if slot.material and slot.material not in character_materials and 'outline' not in slot.material.name.lower():
                        if prefix and slot.material.name.startswith(prefix):
                            character_materials.append(slot.material)

        for material in character_materials:
            mat_low = material.name.lower()
            orig_low = (material.get("_original_material_name") or "").lower()

            if 'hair' in mat_low or 'hair' in orig_low:
                tex_type = TextureType.HAIR
            elif 'face' in mat_low or 'face' in orig_low:
                tex_type = TextureType.FACE
            elif any(k in mat_low or k in orig_low for k in ['weapon', 'handbag', 'kendama']):
                tex_type = TextureType.WEAPON
            else:
                tex_type = TextureType.BODY

            diffuse_img = None
            lightmap_img = None

            # PRIORITY 1: Check existing texture on the material ("revisar en la textura del personaje del material que tiene actualmente")
            current_tex = self._get_current_material_texture(material)
            if current_tex:
                diffuse_img = current_tex
                self.set_diffuse_texture(tex_type, material, diffuse_img)
                # Derive LightMap from this current texture ("y con eso sacar el lightmap y tal")
                lightmap_img = self._find_matching_lightmap_for_texture(current_tex.name, image_files)
                if lightmap_img:
                    self.set_lightmap_texture(tex_type, material, lightmap_img)

            # PRIORITY 2: If NO texture on material, use JSON ("si esque no hubiera textura, usa el json para saber la textura y tal")
            if not diffuse_img or not lightmap_img:
                json_data = self._find_json_textures_for_material(material, json_map)
                if json_data:
                    if not diffuse_img and json_data.get('diffuse'):
                        diffuse_img = self._resolve_image(json_data['diffuse'], image_files)
                        if diffuse_img:
                            self.set_diffuse_texture(tex_type, material, diffuse_img)

                    if not lightmap_img and json_data.get('lightmap'):
                        lightmap_img = self._resolve_image(json_data['lightmap'], image_files)
                        if lightmap_img:
                            self.set_lightmap_texture(tex_type, material, lightmap_img)
                        elif diffuse_img:
                            lightmap_img = self._find_matching_lightmap_for_texture(diffuse_img.name, image_files)
                            if lightmap_img:
                                self.set_lightmap_texture(tex_type, material, lightmap_img)

                    # Ramps / Stockings / Maps from JSON
                    if json_data.get('warm_ramp'):
                        w_ramp = self._resolve_image(json_data['warm_ramp'], image_files)
                        if w_ramp:
                            self.set_warm_shadow_ramp_texture(tex_type, w_ramp)
                            if tex_type == TextureType.BODY:
                                self.set_weapon_ramp_texture(w_ramp)

                    if json_data.get('cool_ramp'):
                        c_ramp = self._resolve_image(json_data['cool_ramp'], image_files)
                        if c_ramp:
                            self.set_cool_shadow_ramp_texture(tex_type, c_ramp)

                    if json_data.get('stockings'):
                        stocking_img = self._resolve_image(json_data['stockings'], image_files)
                        if stocking_img:
                            self.set_stocking_texture(tex_type, material, stocking_img)

                    if json_data.get('facemap'):
                        fmap = self._resolve_image(json_data['facemap'], image_files)
                        if fmap:
                            self.set_facemap_texture(fmap)

                    if json_data.get('expression'):
                        exp_map = self._resolve_image(json_data['expression'], image_files)
                        if exp_map:
                            self.set_face_expression_texture(material, exp_map)

            # PRIORITY 3: Fallback heuristic scan if still missing diffuse or lightmap
            if not diffuse_img or not lightmap_img:
                part_kw = 'Hair' if tex_type == TextureType.HAIR else \
                          'Face' if tex_type == TextureType.FACE else \
                          'Weapon' if tex_type == TextureType.WEAPON else \
                          'Body'
                if 'body1' in mat_low: part_kw = 'Body1'
                elif 'body2' in mat_low: part_kw = 'Body2'
                elif 'body3' in mat_low: part_kw = 'Body3'
                elif 'coat' in mat_low: part_kw = 'Coat'
                elif 'handbag' in mat_low: part_kw = 'Handbag'
                elif 'kendama' in mat_low: part_kw = 'Kendama'

                if not diffuse_img:
                    for fname, fpath in image_files:
                        f_low = fname.lower()
                        if part_kw.lower() in f_low and any(k in f_low for k in ['color', 'diffuse']) and not any(k in f_low for k in ['ramp', 'eff', 'lightmap', 'mask']):
                            diffuse_img = self._resolve_image(fname, image_files)
                            if diffuse_img:
                                self.set_diffuse_texture(tex_type, material, diffuse_img)
                                break

                if not lightmap_img:
                    if diffuse_img:
                        lightmap_img = self._find_matching_lightmap_for_texture(diffuse_img.name, image_files)
                    if not lightmap_img:
                        for fname, fpath in image_files:
                            f_low = fname.lower()
                            if part_kw.lower() in f_low and any(k in f_low for k in ['lightmap', 'ligthmap', 'facemap']) and 'eff' not in f_low:
                                lightmap_img = self._resolve_image(fname, image_files)
                                if lightmap_img:
                                    break
                    if lightmap_img:
                        self.set_lightmap_texture(tex_type, material, lightmap_img)

        # Global Pass: Character Ramps, Stockings, Face Maps
        self._assign_global_character_textures(image_files, json_map)

        # Synchronize categories & set color spaces on all materials
        for material in character_materials:
            sync_material_category_textures(material)



class PunishingGrayRavenTextureImporter(GenshinTextureImporter):
    def __init__(self, game_type: GameType, character_type: TextureImporterType, texture_node_names: TextureNodeNames):
        super().__init__(game_type, character_type)
        self.texture_node_names: TextureNodeNames = texture_node_names

    def set_diffuse_texture(self, type: TextureType, material, img, override=False):
        img.colorspace_settings.name = 'sRGB'

        if type is TextureType.FACE:
            texture_image = material.node_tree.nodes[self.texture_node_names.FACE_DIFFUSE].image
            if texture_image and not override:
                return
            material.node_tree.nodes[self.texture_node_names.FACE_DIFFUSE].image = img
        else:
            texture_image = material.node_tree.nodes[self.texture_node_names.DIFFUSE].image
            if texture_image and not override:
                return
            material.node_tree.nodes[self.texture_node_names.DIFFUSE].image = img

    def set_lightmap_texture(self, type: TextureType, material, img):
        img.colorspace_settings.name = 'Non-Color'
        lightmap_node = material.node_tree.nodes.get(self.texture_node_names.LIGHTMAP)

        if lightmap_node:
            lightmap_node.image = img

    def set_pbr_texture(self, type: TextureType, material, img):
        img.colorspace_settings.name = 'Non-Color'
        material.node_tree.nodes.get(self.texture_node_names.PBR).image = img

    def set_normalmap_texture(self, type: TextureType, material, img):
        img.colorspace_settings.name = 'Non-Color'
        normal_map_node = material.node_tree.nodes.get(self.texture_node_names.NORMALMAP)

        if normal_map_node:
            normal_map_node.image = img

    def set_lut_texture(self, type: TextureType, material, img):
        if type is TextureType.FACE:
            lut_node = material.node_tree.nodes.get(self.texture_node_names.FACE_LUT)
        else:
            lut_node = material.node_tree.nodes.get(self.texture_node_names.LUT)

        if lut_node:
            lut_node.image = img
            shader_node_name = JaredNyts_PunishingGrayRavenNodeNames.FACE_SHADER if type is TextureType.FACE else \
                JaredNyts_PunishingGrayRavenNodeNames.MAIN_SHADER
            if type is not TextureType.FACE:  # TODO: Something is wrong when LUT enabled on face
                self.set_lut_value(material, shader_node_name, True)

    def set_lut_value(self, material, shader_node_name, enabled):
        lut_value = 1.0 if enabled else 0.0

        material.node_tree.nodes.get(shader_node_name) \
            .inputs.get(JaredNyts_PunishingGrayRavenNodeNames.USE_LUT).default_value = lut_value

    def set_eye_diffuse_texture(self, material, img):
        eye_node = material.node_tree.nodes.get(self.texture_node_names.EYE)

        if eye_node:
            eye_node.image = img

    def set_face_heao_texture(self, img):
        face_heao_node = bpy.data.node_groups.get(self.texture_node_names.FACE_HEAO_NODE_GROUP)

        if face_heao_node:
            img.colorspace_settings.name = 'Non-Color'
            face_heao_node.nodes.get(self.texture_node_names.FACE_HEAO).image = img

    def set_metalmap_texture(self, img):
        metallic_matcap_node = bpy.data.node_groups.get(self.texture_node_names.METALLIC_MATCAP_NODE_GROUP)

        if metallic_matcap_node:
            metallic_matcap_node.nodes[self.texture_node_names.METALLIC_MATCAP].image = img


class PunishingGrayRavenAvatarTextureImporter(PunishingGrayRavenTextureImporter):
    def __init__(self, material_names: ShaderMaterialNames, texture_node_names: TextureNodeNames):
        super().__init__(GameType.PUNISHING_GRAY_RAVEN, TextureImporterType.PGR_AVATAR, texture_node_names)
        self.material_names = material_names

        shader_identifier_service = ShaderIdentifierServiceFactory.create(GameType.PUNISHING_GRAY_RAVEN.name)
        self.genshin_shader_version = shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)

    def import_textures(self, directory):
        for name, folder, files in os.walk(directory):
            self.files = files
            for file in files:
                # load the file with the correct alpha mode
                img_path = directory + "/" + file
                img = bpy.data.images.load(filepath = img_path, check_existing=True)
                img.alpha_mode = 'CHANNEL_PACKED'

                alpha_material = bpy.data.materials.get(f'{self.material_names.ALPHA}') 
                eye_material = bpy.data.materials.get(f'{self.material_names.EYE}')

                # Implement the texture in the correct node
                print(f'Importing texture {file} using {self.__class__.__name__}')

                # Eyes
                if self.is_texture_identifiers_in_texture_name(['Eye'], file) and \
                    not self.is_one_texture_identifier_in_texture_name(['HET'], file):
                    self.set_eye_diffuse_texture(eye_material, img)

                else:
                    material_identifer_service = PunishingGrayRavenMaterialIdentifierService()
                    texture_body_part_name = material_identifer_service.get_body_part_name(file)

                    if not texture_body_part_name or '.fbx' in file or 'Mt4Ejector' in file or 'Mb1Motor' in file or \
                        'Mt2Machinehand' in file:
                        continue

                    materials = [material for material in bpy.data.materials if material.name.replace(JaredNytsPunishingGrayRavenShaderMaterialNames.MATERIAL_PREFIX, '') in texture_body_part_name]

                    # Check cases where textures are not prefixed with body part names
                    if not materials:
                        texture_body_part_name = material_identifer_service.search_original_material_user_for_body_part_name(file)
                        if not texture_body_part_name:
                            continue
                        materials = [material for material in bpy.data.materials if material.name.replace(JaredNytsPunishingGrayRavenShaderMaterialNames.MATERIAL_PREFIX, '') in texture_body_part_name]

                    if materials:
                        material = bpy.data.materials.get(max([material.name for material in materials], key=len))
                        body_part_name = material.name.replace(JaredNytsPunishingGrayRavenShaderMaterialNames.MATERIAL_PREFIX, '')
                        img = self.reload_texture(img, img_path)  # reloads only if the texture already exists

                        if 'AO' in file and \
                            not self.is_one_texture_identifier_in_texture_name(['HEAO'], file):
                            if 'Face' in file:
                                self.set_face_heao_texture(img)
                            elif 'Cloth' in body_part_name and 'UV' not in file:
                                cloth_materials = [material for material in bpy.data.materials if 'Cloth' in material.name]
                                for material in cloth_materials:
                                    self.set_lightmap_texture(TextureType.BODY, material, img)
                            else:
                                self.set_lightmap_texture(TextureType.BODY, material, img)
                        elif 'HEAO' in file:
                            if 'Face' in file:
                                self.set_face_heao_texture(img)
                            else:
                                self.set_lightmap_texture(TextureType.BODY, material, img)
                        elif 'NM' in file:
                            self.set_normalmap_texture(TextureType.BODY, material, img)
                        elif 'PBR' in file:
                            self.set_pbr_texture(TextureType.BODY, material, img)
                        elif 'Skin' in file:
                            if 'Face' in file:
                                self.set_lut_texture(TextureType.FACE, material, img)
                            else:
                                self.set_lut_texture(TextureType.BODY, material, img)
                        elif file.endswith(f'{body_part_name}.png'):
                            if 'Face' in file:
                                self.set_diffuse_texture(TextureType.FACE, material, img)
                            else:
                                self.set_diffuse_texture(TextureType.BODY, material, img)
                        else:
                            print(f'WARN: Unexpected texture {file}')
                            if file.endswith(f'{body_part_name}.png') or \
                                material.name == JaredNytsPunishingGrayRavenShaderMaterialNames.XDEFAULTMATERIAL:
                                print(f'WARN: Default setting Diffuse to {material.name}')
                                try:
                                    self.set_diffuse_texture(TextureType.BODY, material, img)
                                except:
                                    pass  # Unexpected or unused textures hit here!
                            elif ('Body' in body_part_name or 'Cloth' in body_part_name) and \
                                not self.is_one_texture_identifier_in_texture_name(['UV', 'MC'], file):
                                print(f'WARN: Default setting Diffuse to {material.name}')
                                try:
                                    fallback_materials = [material for material in bpy.data.materials if
                                                       JaredNytsPunishingGrayRavenShaderMaterialNames.MATERIAL_PREFIX and
                                                       ('Body' in material.name or 'Cloth' in material.name)]
                                    for material in fallback_materials:
                                        self.set_diffuse_texture(TextureType.BODY, material, img)
                                except:
                                    pass  # Unexpected or unused textures hit here!

    # Fix characters with blank textures in their original material texture
    # We do this by deleting the original texture and loading the new texture
    # This happens on characters with textures named the same as their model
    # MUST BE DONE AFTER search_original_material_user_for_body_part_name() is called
    # Ex. Sophia_Silverfang
    def reload_texture(self, img, img_path):
        image_exists = [image for image in bpy.data.images.values() if image.name == img.name]
        if image_exists:
            print(f'Reloading texture! {img}')
            bpy.data.images.remove(image_exists[0])
            img = bpy.data.images.load(filepath = img_path, check_existing=True)
            img.alpha_mode = 'CHANNEL_PACKED'
        return img

class PunishingGrayRavenChibiTextureImporter(PunishingGrayRavenTextureImporter):
    def __init__(self, material_names: ShaderMaterialNames, texture_node_names: TextureNodeNames):
        super().__init__(GameType.PUNISHING_GRAY_RAVEN, TextureImporterType.PGR_CHIBI, texture_node_names)
        self.material_names = material_names

        shader_identifier_service = ShaderIdentifierServiceFactory.create(GameType.PUNISHING_GRAY_RAVEN.name)
        self.genshin_shader_version = shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)

    def import_textures(self, directory):
        pass