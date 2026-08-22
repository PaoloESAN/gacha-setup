# Author: michael-gh1


from abc import abstractmethod
from enum import Enum, auto

from setup_wizard.domain.shader_node_names import JaredNyts_PunishingGrayRavenNodeNames, ShaderNodeNames, StellarToonShaderNodeNames, V2_GenshinShaderNodeNames, V3_GenshinShaderNodeNames, V4_PrimoToonShaderNodeNames, V1_HoYoToonShaderNodeNames
from setup_wizard.domain.game_types import GameType
from setup_wizard.domain.shader_material_names import JaredNytsPunishingGrayRavenShaderMaterialNames, Nya222HonkaiStarRailShaderMaterialNames, StellarToonShaderMaterialNames, V3_BonnyFestivityGenshinImpactMaterialNames, V2_FestivityGenshinImpactMaterialNames, V4_PrimoToonGenshinImpactMaterialNames, V1_HoYoToonGenshinImpactMaterialNames, ZenlessZoneZeroShaderMaterialNames
from setup_wizard.texture_import_setup.texture_node_names import GenshinImpactTextureNodeNames, JaredNytsPunishingGrayRavenTextureNodeNames, Nya222HonkaiStarRailTextureNodeNames, StellarToonTextureNodeNames, V1_GenshinImpactTextureNodeNames, V2_GenshinImpactTextureNodeNames, V3_GenshinImpactTextureNodeNames, V4_GenshinImpactTextureNodeNames, V1_HoYoToonGenshinImpactTextureNodeNames, ZenlessZoneZeroTextureNodeNames


class GenshinImpactShaders(Enum):
    V1_GENSHIN_IMPACT_SHADER = auto()
    V2_GENSHIN_IMPACT_SHADER = auto()
    V3_GENSHIN_IMPACT_SHADER = auto()
    V4_GENSHIN_IMPACT_SHADER = auto()
    V1_HOYOTOON_GENSHIN_IMPACT_SHADER = auto()


class HonkaiStarRailShaders(Enum):
    NYA222_HONKAI_STAR_RAIL_SHADER = auto()
    STELLARTOON_HONKAI_STAR_RAIL_SHADER = auto()


class PunishingGrayRavenShaders(Enum):
    V1_JAREDNYTS_PUNISHING_GRAY_RAVEN_SHADER = auto()


class ZenlessZoneZeroShaders(Enum):
    V1_ZENLESS_ZONE_ZERO_SHADER = auto()


class NevernessToEvernessShaders(Enum):
    V1_NEVERNESS_TO_EVERNESS_SHADER = auto()


class ShaderIdentifier:
    def __init__(self, material_name, shader_node_name, shader_label_name, material_prefix_after_rename, material_endswith_after_rename):
        self.material_name = material_name
        self.shader_node_name = shader_node_name
        self.shader_label_name = shader_label_name
        self.material_prefix_after_rename = material_prefix_after_rename
        self.material_endswith_after_rename = material_endswith_after_rename


class ShaderIdentifierServiceFactory:
    def create(game_type):
        if game_type == GameType.GENSHIN_IMPACT.name:
            return GenshinImpactShaderIdentifierService()
        elif game_type == GameType.HONKAI_STAR_RAIL.name:
            return HonkaiStarRailShaderIdentifierService()
        elif game_type == GameType.PUNISHING_GRAY_RAVEN.name:
            return PunishingGrayRavenShaderIdentifierService()
        elif game_type == GameType.ZENLESS_ZONE_ZERO.name:
            return ZenlessZoneZeroShaderIdentifierService()
        elif game_type == GameType.NEVERNESS_TO_EVERNESS.name:
            return NevernessToEvernessShaderIdentifierService()
        else:
            raise Exception(f'Unexpected input GameType "{game_type}" for ShaderIdentifierServiceFactory')



class ShaderIdentifierService:
    material_lists_to_search_through = {}
    node_groups_to_search_through = {}
    shader_labels_to_search_through = {}

    def __init__(self):
        pass

    def identify_shader(self, materials, node_groups):
        # Check for V4 shader first
        shader_identifier: ShaderIdentifier
        for shader, shader_identifier in self.shader_labels_to_search_through.items():
            shader_material = materials.get(shader_identifier.material_name)
            renamed_shader_material = [material for material in materials if 
                                       material.name.startswith(shader_identifier.material_prefix_after_rename) and material.name.endswith(shader_identifier.material_endswith_after_rename)]

            shader_material = shader_material or renamed_shader_material[0] if renamed_shader_material else None
            if shader_material and shader_material.node_tree:
                shader_node = shader_material.node_tree.nodes.get(shader_identifier.shader_node_name)
                if shader_node:
                    return shader

        # Check for V1 shader
        for shader, node_group_list in self.node_groups_to_search_through.items():
            found_all = True
            for node_group in node_group_list:
                if node_group not in node_groups:
                    found_all = False
                    break
            if found_all:
                return shader

        # Check for V2 shader next b/c V1 and V2 have same material names
        # Then check for later versions (V3, etc.)
        for shader, material_list in self.material_lists_to_search_through.items():
            found_all = True
            for material in material_list:
                if not [scene_material for scene_material in materials.values() if material in scene_material.name]:
                    found_all = False
                    break
            if found_all:
                return shader

    def get_shader_material_names(self, game_type, materials, node_groups):
        game_shader = self.identify_shader(materials, node_groups)
        if game_type == GameType.GENSHIN_IMPACT.name:
            if game_shader is GenshinImpactShaders.V1_GENSHIN_IMPACT_SHADER or game_shader is GenshinImpactShaders.V2_GENSHIN_IMPACT_SHADER:
                return V2_FestivityGenshinImpactMaterialNames
            elif game_shader is GenshinImpactShaders.V3_GENSHIN_IMPACT_SHADER:
                return V3_BonnyFestivityGenshinImpactMaterialNames
            elif game_shader is GenshinImpactShaders.V1_HOYOTOON_GENSHIN_IMPACT_SHADER:
                return V1_HoYoToonGenshinImpactMaterialNames
            else:
                return V4_PrimoToonGenshinImpactMaterialNames
        elif game_type == GameType.HONKAI_STAR_RAIL.name:
            if game_shader is HonkaiStarRailShaders.NYA222_HONKAI_STAR_RAIL_SHADER:
                return Nya222HonkaiStarRailShaderMaterialNames
            else:
                return StellarToonShaderMaterialNames
        elif game_type == GameType.PUNISHING_GRAY_RAVEN.name:
            return JaredNytsPunishingGrayRavenShaderMaterialNames
        elif game_type == GameType.ZENLESS_ZONE_ZERO.name:
            return ZenlessZoneZeroShaderMaterialNames
        else:
            raise Exception(f'Unknown {GameType}: {game_type}')

    def get_shader_material_names_using_shader(self, shader: GenshinImpactShaders):
        if shader is GenshinImpactShaders.V1_HOYOTOON_GENSHIN_IMPACT_SHADER:
            return V1_HoYoToonGenshinImpactMaterialNames
        elif shader is GenshinImpactShaders.V4_GENSHIN_IMPACT_SHADER:
            return V4_PrimoToonGenshinImpactMaterialNames
        elif shader is GenshinImpactShaders.V3_GENSHIN_IMPACT_SHADER:
            return V3_BonnyFestivityGenshinImpactMaterialNames
        elif shader is GenshinImpactShaders.V2_GENSHIN_IMPACT_SHADER or \
            shader is GenshinImpactShaders.V1_GENSHIN_IMPACT_SHADER:
            return V2_FestivityGenshinImpactMaterialNames
        elif shader is HonkaiStarRailShaders.NYA222_HONKAI_STAR_RAIL_SHADER:
            return Nya222HonkaiStarRailShaderMaterialNames
        elif shader is HonkaiStarRailShaders.STELLARTOON_HONKAI_STAR_RAIL_SHADER:
            return StellarToonShaderMaterialNames
        elif shader is PunishingGrayRavenShaders.V1_JAREDNYTS_PUNISHING_GRAY_RAVEN_SHADER:
            return JaredNytsPunishingGrayRavenShaderMaterialNames
        elif shader is ZenlessZoneZeroShaders.V1_ZENLESS_ZONE_ZERO_SHADER:
            return ZenlessZoneZeroShaderMaterialNames
        else:
            raise Exception(f'Unknown Shader: {shader}')

    def get_shader_texture_node_names(self, shader):
        if shader is GenshinImpactShaders.V1_HOYOTOON_GENSHIN_IMPACT_SHADER:
            return V1_HoYoToonGenshinImpactTextureNodeNames
        elif shader is GenshinImpactShaders.V4_GENSHIN_IMPACT_SHADER:
            return V4_GenshinImpactTextureNodeNames
        elif shader is GenshinImpactShaders.V3_GENSHIN_IMPACT_SHADER:
            return V3_GenshinImpactTextureNodeNames
        elif shader is GenshinImpactShaders.V2_GENSHIN_IMPACT_SHADER:
            return V2_GenshinImpactTextureNodeNames
        elif shader is GenshinImpactShaders.V1_GENSHIN_IMPACT_SHADER:
            return V1_GenshinImpactTextureNodeNames
        elif shader is HonkaiStarRailShaders.NYA222_HONKAI_STAR_RAIL_SHADER:
            return Nya222HonkaiStarRailTextureNodeNames
        elif shader is HonkaiStarRailShaders.STELLARTOON_HONKAI_STAR_RAIL_SHADER:
            return StellarToonTextureNodeNames
        elif shader is PunishingGrayRavenShaders.V1_JAREDNYTS_PUNISHING_GRAY_RAVEN_SHADER:
            return JaredNytsPunishingGrayRavenTextureNodeNames
        elif shader is ZenlessZoneZeroShaders.V1_ZENLESS_ZONE_ZERO_SHADER or shader is None:
            return ZenlessZoneZeroTextureNodeNames
        else:
            raise Exception(f'Unknown Shader: {shader}')

    def get_shader_node_names(self, shader):
        if shader is GenshinImpactShaders.V1_HOYOTOON_GENSHIN_IMPACT_SHADER:
            return V1_HoYoToonShaderNodeNames
        elif shader is GenshinImpactShaders.V4_GENSHIN_IMPACT_SHADER:
            return V4_PrimoToonShaderNodeNames
        elif shader is GenshinImpactShaders.V3_GENSHIN_IMPACT_SHADER:
            return V3_GenshinShaderNodeNames
        elif shader is GenshinImpactShaders.V2_GENSHIN_IMPACT_SHADER or \
            shader is GenshinImpactShaders.V1_GENSHIN_IMPACT_SHADER:
            return V2_GenshinShaderNodeNames
        elif shader is HonkaiStarRailShaders.STELLARTOON_HONKAI_STAR_RAIL_SHADER:
            return StellarToonShaderNodeNames  # Unsued
        elif shader is HonkaiStarRailShaders.NYA222_HONKAI_STAR_RAIL_SHADER:
            return ShaderNodeNames  # Unused, no ShaderNodeName available
        elif shader is PunishingGrayRavenShaders.V1_JAREDNYTS_PUNISHING_GRAY_RAVEN_SHADER:
            return JaredNyts_PunishingGrayRavenNodeNames  # Unused
        elif shader is ZenlessZoneZeroShaders.V1_ZENLESS_ZONE_ZERO_SHADER or shader is None:
            return ShaderNodeNames  # Unused
        else:
            raise Exception(f'Unknown Shader: {shader}')


class GenshinImpactShaderIdentifierService(ShaderIdentifierService):
    V2_NAMES_OF_GENSHIN_MATERIALS = [
        V2_FestivityGenshinImpactMaterialNames.MATERIAL_PREFIX_AFTER_RENAME,
    ]
    V3_NAMES_OF_GENSHIN_MATERIALS = [
        V3_BonnyFestivityGenshinImpactMaterialNames.MATERIAL_PREFIX_AFTER_RENAME,
    ]
    V4_SHADER_LABEL_NAME = 'PrimoToon v4.0'
    material_lists_to_search_through = {
        GenshinImpactShaders.V3_GENSHIN_IMPACT_SHADER: V3_NAMES_OF_GENSHIN_MATERIALS,
        GenshinImpactShaders.V2_GENSHIN_IMPACT_SHADER: V2_NAMES_OF_GENSHIN_MATERIALS,
    }

    node_groups_to_search_through = {
        GenshinImpactShaders.V1_GENSHIN_IMPACT_SHADER: ['miHoYo - Genshin Face'],
    }

    shader_labels_to_search_through = {
        GenshinImpactShaders.V1_HOYOTOON_GENSHIN_IMPACT_SHADER: ShaderIdentifier(
            material_name=V1_HoYoToonGenshinImpactMaterialNames.BODY,
            shader_node_name=V1_HoYoToonShaderNodeNames.BODY_SHADER,
            shader_label_name=V1_HoYoToonShaderNodeNames.BODY_SHADER_LABEL,
            material_prefix_after_rename=V1_HoYoToonGenshinImpactMaterialNames.MATERIAL_PREFIX_AFTER_RENAME,
            material_endswith_after_rename='Body'
        ),
        GenshinImpactShaders.V4_GENSHIN_IMPACT_SHADER: ShaderIdentifier(
            material_name=V4_PrimoToonGenshinImpactMaterialNames.BODY,
            shader_node_name=V4_PrimoToonShaderNodeNames.BODY_SHADER,
            shader_label_name=V4_PrimoToonShaderNodeNames.BODY_SHADER_LABEL,
            material_prefix_after_rename=V4_PrimoToonGenshinImpactMaterialNames.MATERIAL_PREFIX_AFTER_RENAME,
            material_endswith_after_rename='Body'
        ),
    }

    def __init__(self):
        super().__init__()


class HonkaiStarRailShaderIdentifierService(ShaderIdentifierService):
    NYA222_NAMES_OF_SHADER_MATERIALS = [
        Nya222HonkaiStarRailShaderMaterialNames.MATERIAL_PREFIX_AFTER_RENAME,
    ]
    STELLARTOON_NAMES_OF_SHADER_MATERIALS = [
        StellarToonShaderMaterialNames.MATERIAL_PREFIX_AFTER_RENAME,
    ]
    material_lists_to_search_through = {
        HonkaiStarRailShaders.NYA222_HONKAI_STAR_RAIL_SHADER: NYA222_NAMES_OF_SHADER_MATERIALS,
        HonkaiStarRailShaders.STELLARTOON_HONKAI_STAR_RAIL_SHADER: STELLARTOON_NAMES_OF_SHADER_MATERIALS
    }

    def __init__(self):
        super().__init__()


# Unused.
class PunishingGrayRavenShaderIdentifierService(ShaderIdentifierService):
    V1_NAMES_OF_PGR_MATERIALS = [
        JaredNytsPunishingGrayRavenShaderMaterialNames.MATERIAL_PREFIX_AFTER_RENAME,
    ]
    material_lists_to_search_through = {
        PunishingGrayRavenShaders.V1_JAREDNYTS_PUNISHING_GRAY_RAVEN_SHADER: V1_NAMES_OF_PGR_MATERIALS
    }

    def __init__(self):
        super().__init__()


class ZenlessZoneZeroShaderIdentifierService(ShaderIdentifierService):
    V1_NAMES_OF_ZZZ_MATERIALS = [
        "ZZZ",
    ]
    material_lists_to_search_through = {
        ZenlessZoneZeroShaders.V1_ZENLESS_ZONE_ZERO_SHADER: V1_NAMES_OF_ZZZ_MATERIALS
    }

    def __init__(self):
        super().__init__()

    def identify_shader(self, materials, node_groups):
        res = super().identify_shader(materials, node_groups)
        if res is not None:
            return res
        for m in materials.values():
            if m and any(k in m.name.lower() for k in ["zzz", "kythera"]):
                return ZenlessZoneZeroShaders.V1_ZENLESS_ZONE_ZERO_SHADER
        for ng in node_groups.values():
            if ng and any(k in ng.name.lower() for k in ["zzz", "kythera", "outline", "face lightmap"]):
                return ZenlessZoneZeroShaders.V1_ZENLESS_ZONE_ZERO_SHADER
        return ZenlessZoneZeroShaders.V1_ZENLESS_ZONE_ZERO_SHADER

    def get_shader_node_names(self, shader):
        return ShaderNodeNames

    def get_shader_texture_node_names(self, shader):
        return ZenlessZoneZeroTextureNodeNames


class NevernessToEvernessShaderIdentifierService(ShaderIdentifierService):
    V1_NAMES_OF_NTE_MATERIALS = [
        '异环-',
    ]
    material_lists_to_search_through = {
        NevernessToEvernessShaders.V1_NEVERNESS_TO_EVERNESS_SHADER: V1_NAMES_OF_NTE_MATERIALS
    }

    def __init__(self):
        super().__init__()

