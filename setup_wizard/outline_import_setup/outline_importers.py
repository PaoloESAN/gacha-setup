# Author: michael-gh1

import os
import bpy

from abc import ABC, abstractmethod
from bpy.types import Operator, Context

from setup_wizard.domain.shader_identifier_service import GenshinImpactShaders, HonkaiStarRailShaders, ShaderIdentifierService, ShaderIdentifierServiceFactory
from setup_wizard.outline_import_setup.outline_node_groups import OutlineNodeGroupNames
from setup_wizard.import_order import GENSHIN_IMPACT_OUTLINES_FILE_PATH, PUNISHING_GRAY_RAVEN_OUTLINES_FILE_PATH, HONKAI_STAR_RAIL_OUTLINES_FILE_PATH, \
    HONKAI_STAR_RAIL_SHADER_FILE_PATH, ZENLESS_ZONE_ZERO_SHADER_FILE_PATH, \
    ZENLESS_ZONE_ZERO_OUTLINES_FILE_PATH, NextStepInvoker, cache_using_cache_key, get_cache, get_shader_file_path
from setup_wizard.domain.game_types import GameType


class GameOutlineImporterFactory:
    def create(game_type: str, blender_operator: Operator, context: Context):
        shader_identifier_service: ShaderIdentifierService = ShaderIdentifierServiceFactory.create(game_type)
        shader = shader_identifier_service.identify_shader(bpy.data.materials, bpy.data.node_groups)

        if game_type == GameType.GENSHIN_IMPACT.name:
            if shader is GenshinImpactShaders.V1_GENSHIN_IMPACT_SHADER or shader is GenshinImpactShaders.V2_GENSHIN_IMPACT_SHADER:
                outlines_node_group_name = OutlineNodeGroupNames.FESTIVITY_GENSHIN_OUTLINES
            elif shader is GenshinImpactShaders.V3_GENSHIN_IMPACT_SHADER:
                outlines_node_group_name = OutlineNodeGroupNames.V3_BONNY_FESTIVITY_GENSHIN_OUTLINES
            else:
                outlines_node_group_name = OutlineNodeGroupNames.V3_BONNY_FESTIVITY_GENSHIN_OUTLINES
            return GenshinImpactOutlineNodeGroupImporter(blender_operator, context, outlines_node_group_name)
        elif game_type == GameType.HONKAI_STAR_RAIL.name:
            if shader is HonkaiStarRailShaders.NYA222_HONKAI_STAR_RAIL_SHADER:
                return HonkaiStarRailOutlineNodeGroupImporter(blender_operator, context, OutlineNodeGroupNames.NYA222_HSR_OUTLINES)
            else:  # is HonkaiStarRailShaders.STELLARTOON_HONKAI_STAR_RAIL_SHADER
                return HonkaiStarRailOutlineNodeGroupImporter(blender_operator, context, OutlineNodeGroupNames.STELLARTOON_HSR_OUTLINES)
                
        elif game_type == GameType.PUNISHING_GRAY_RAVEN.name:
            return PunishingGrayRavenOutlineNodeGroupImporter(blender_operator, context)
        elif game_type == GameType.ZENLESS_ZONE_ZERO.name:
            return ZenlessZoneZeroOutlineNodeGroupImporter(blender_operator, context)
        elif game_type == GameType.NEVERNESS_TO_EVERNESS.name:
            return NevernessToEvernessOutlineNodeGroupImporter(blender_operator, context)
        else:
            raise Exception(f'Unknown {GameType}: {game_type}')



class GameOutlineNodeGroupImporter(ABC):
    @abstractmethod
    def import_outline_node_group(self):
        raise NotImplementedError


class GenshinImpactOutlineNodeGroupImporter(GameOutlineNodeGroupImporter):
    def __init__(self, blender_operator, context, outlines_node_group_name):
        self.blender_operator = blender_operator
        self.context = context
        self.outlines_file_path = GENSHIN_IMPACT_OUTLINES_FILE_PATH  # Keep same filepath for all Genshin Impact
        self.outlines_node_group_names = outlines_node_group_name

    def import_outline_node_group(self):
        filepath = get_shader_file_path(GameType.GENSHIN_IMPACT.name, 'outlines') or get_shader_file_path(GameType.GENSHIN_IMPACT.name, 'main')

        if filepath and os.path.isfile(filepath):
            for outline_node_group_name in self.outlines_node_group_names:
                if not bpy.data.node_groups.get(outline_node_group_name):
                    inner_path = 'NodeTree'
                    try:
                        bpy.ops.wm.append(
                            filepath=os.path.join(filepath, inner_path, outline_node_group_name),
                            directory=os.path.join(filepath, inner_path),
                            filename=outline_node_group_name
                        )
                    except Exception as e:
                        print(f"Notice: Failed appending outline node group {outline_node_group_name}: {e}")

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx, 
            self.blender_operator.invoker_type,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=self.blender_operator.game_type,
        )

class HonkaiStarRailOutlineNodeGroupImporter(GameOutlineNodeGroupImporter):
    def __init__(self, blender_operator, context, outlines_node_group_names):
        self.blender_operator = blender_operator
        self.context = context
        self.outlines_file_path = HONKAI_STAR_RAIL_OUTLINES_FILE_PATH  # Keep same filepath for all HSR
        self.outlines_node_group_names = outlines_node_group_names

    def import_outline_node_group(self):
        filepath = get_shader_file_path(GameType.HONKAI_STAR_RAIL.name, 'main')

        if filepath and os.path.isfile(filepath):
            for outline_node_group_name in self.outlines_node_group_names:
                if not bpy.data.node_groups.get(outline_node_group_name):
                    inner_path = 'NodeTree'
                    try:
                        bpy.ops.wm.append(
                            filepath=os.path.join(filepath, inner_path, outline_node_group_name),
                            directory=os.path.join(filepath, inner_path),
                            filename=outline_node_group_name
                        )
                    except Exception as e:
                        print(f"Notice: Failed appending outline node group {outline_node_group_name}: {e}")

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx, 
            self.blender_operator.invoker_type,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=self.blender_operator.game_type,
        )


class PunishingGrayRavenOutlineNodeGroupImporter(GameOutlineNodeGroupImporter):
    def __init__(self, blender_operator, context):
        self.blender_operator = blender_operator
        self.context = context
        self.outlines_file_path = PUNISHING_GRAY_RAVEN_OUTLINES_FILE_PATH
        self.outlines_node_group_names = \
            OutlineNodeGroupNames.V2_JAREDNYTS_PGR_OUTLINES + OutlineNodeGroupNames.V3_JAREDNYTS_PGR_OUTLINES

    def import_outline_node_group(self):
        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx, 
            self.blender_operator.invoker_type,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=self.blender_operator.game_type,
        )


class ZenlessZoneZeroOutlineNodeGroupImporter(GameOutlineNodeGroupImporter):
    def __init__(self, blender_operator, context):
        self.blender_operator = blender_operator
        self.context = context
        self.outlines_file_path = ZENLESS_ZONE_ZERO_OUTLINES_FILE_PATH
        self.outlines_node_group_names = OutlineNodeGroupNames.ZENLESS_ZONE_ZERO_OUTLINES

    def import_outline_node_group(self):
        filepath = get_shader_file_path(GameType.ZENLESS_ZONE_ZERO.name, 'main')

        if filepath and os.path.isfile(filepath):
            for outline_node_group_name in self.outlines_node_group_names:
                if not bpy.data.node_groups.get(outline_node_group_name):
                    inner_path = 'NodeTree'

                    try:
                        bpy.ops.wm.append(
                            filepath=os.path.join(filepath, inner_path, outline_node_group_name),
                            directory=os.path.join(filepath, inner_path),
                            filename=outline_node_group_name
                        )
                    except Exception as e:
                        print(f"Failed to append {outline_node_group_name} from {filepath}: {e}")

            # Import strictly the Lighting Panel UI & Direction Objects / Collections
            try:
                with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
                    excluded_kw = ["face", "phoneme", "mouth", "eyebrow", "expression", "facrig"]
                    lighting_keywords = [
                        "colorwheel", "colorpicker", "slider-rim", "origin-rim",
                        "light direction", "head direction", "head forward", "head up",
                        "lighting panel", "light panel", "lighting_panel", "light_panel"
                    ]
                    
                    target_colls = [
                        c for c in data_from.collections 
                        if not any(kw in c.lower() for kw in excluded_kw) and
                        ("lighting" in c.lower() or "panel" in c.lower() or "light" in c.lower()) and
                        c not in bpy.data.collections
                    ]
                    data_to.collections = target_colls

                    target_objs = [
                        o for o in data_from.objects 
                        if not any(kw in o.lower() for kw in excluded_kw) and
                        (any(kw in o.lower() for kw in lighting_keywords) or "panel" in o.lower() or "lighting" in o.lower()) and
                        o not in bpy.data.objects
                    ]
                    data_to.objects = target_objs

                for coll in data_to.collections:
                    if coll and coll.name not in [c.name for c in bpy.context.scene.collection.children]:
                        bpy.context.scene.collection.children.link(coll)

                for obj in data_to.objects:
                    if obj and not any(obj.name in c.objects for c in bpy.data.collections.values()):
                        bpy.context.scene.collection.objects.link(obj)
            except Exception as e:
                print(f"Failed to append lighting objects/collections from {filepath}: {e}")

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx, 
            self.blender_operator.invoker_type,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=self.blender_operator.game_type,
        )


class NevernessToEvernessOutlineNodeGroupImporter(GameOutlineNodeGroupImporter):
    def __init__(self, blender_operator, context):
        self.blender_operator = blender_operator
        self.context = context

    def import_outline_node_group(self):
        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx, 
            self.blender_operator.invoker_type,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=self.blender_operator.game_type,
        )

