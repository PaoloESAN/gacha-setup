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
        elif game_type == GameType.WUTHERING_WAVES.name:
            return WutheringWavesOutlineNodeGroupImporter(blender_operator, context)
        elif game_type == GameType.ARKNIGHTS_ENDFIELD.name:
            return ArknightsEndfieldOutlineNodeGroupImporter(blender_operator, context)
        elif game_type == GameType.HONKAI_IMPACT_3RD.name:
            return HonkaiImpact3rdOutlineNodeGroupImporter(blender_operator, context)
        elif game_type == GameType.HONKAI_NEXUS_ANIMA.name:
            return HonkaiStarRailOutlineNodeGroupImporter(blender_operator, context, OutlineNodeGroupNames.HONKAI_NEXUS_ANIMA_OUTLINES)
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
        filepath = get_shader_file_path(GameType.PUNISHING_GRAY_RAVEN.name, 'main')
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

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx, 
            self.blender_operator.invoker_type,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=self.blender_operator.game_type,
        )


class HonkaiImpact3rdOutlineNodeGroupImporter(GameOutlineNodeGroupImporter):
    def __init__(self, blender_operator, context):
        self.blender_operator = blender_operator
        self.context = context
        self.outlines_node_group_names = OutlineNodeGroupNames.HONKAI_IMPACT_3RD_OUTLINES

    def import_outline_node_group(self):
        filepath = get_shader_file_path(GameType.HONKAI_IMPACT_3RD.name, 'main')
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

            # Import direction control objects from shader file
            try:
                with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
                    direction_keywords = ["light direction", "head origin", "head forward", "head up"]
                    target_objs = [
                        o for o in data_from.objects
                        if any(kw == o.lower() for kw in direction_keywords)
                        and o not in bpy.data.objects
                    ]
                    data_to.objects = target_objs

                for obj in data_to.objects:
                    if obj and obj.name not in bpy.context.scene.collection.objects:
                        bpy.context.scene.collection.objects.link(obj)
            except Exception as e:
                print(f"Failed to import HI3 direction objects from {filepath}: {e}")

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
        # Outlines and Lighting Panel come specifically from the setup file (ZZZ Setup v7.blend)
        filepath = get_shader_file_path(GameType.ZENLESS_ZONE_ZERO.name, 'outlines')
        if not filepath or not os.path.isfile(filepath):
            addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            filepath = os.path.join(addon_dir, 'shaders', 'zzz', 'ZZZ Setup v7.blend')
            if not os.path.isfile(filepath):
                filepath = os.path.join(addon_dir, 'shaders', 'zzz', 'ZZZ Setup File V2.0.blend')

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

            # Also append ZZZLightPanelAttr node group from ZZZ Setup File V2.0.blend if not present
            if not bpy.data.node_groups.get("ZZZLightPanelAttr"):
                try:
                    bpy.ops.wm.append(
                        filepath=os.path.join(filepath, inner_path, "ZZZLightPanelAttr"),
                        directory=os.path.join(filepath, inner_path),
                        filename="ZZZLightPanelAttr"
                    )
                except Exception as e:
                    print(f"Failed to append ZZZLightPanelAttr from {filepath}: {e}")

            # Import direction objects and Lighting Panel UI from ZZZ Setup File V2.0.blend
            try:
                with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
                    direction_keywords = ["light direction", "head direction", "head forward", "head up"]
                    lighting_panel_keywords = [
                        "colorwheel", "colorpicker", "slider-rim", "origin-rim",
                        "lightpanelwgtplane", "lightpanelselectorwgt", "lighting panel", "light panel"
                    ]
                    excluded_kw = ["face", "phoneme", "mouth", "eyebrow", "expression", "facrig"]
                    
                    target_colls = [
                        c for c in data_from.collections 
                        if not any(kw in c.lower() for kw in excluded_kw) and
                        ("lighting" in c.lower() or "panel" in c.lower() or "light" in c.lower() or "widget" in c.lower()) and
                        c not in bpy.data.collections
                    ]
                    data_to.collections = target_colls

                    target_objs = [
                        o for o in data_from.objects 
                        if not any(kw in o.lower() for kw in excluded_kw) and
                        (any(kw in o.lower() for kw in direction_keywords + lighting_panel_keywords) or "panel" in o.lower() or "lighting" in o.lower()) and
                        o not in bpy.data.objects
                    ]
                    data_to.objects = target_objs

                target_wgt_coll = next((c for c in bpy.data.collections if c.name.startswith("WGTS_")), None)
                if not target_wgt_coll:
                    target_wgt_coll = bpy.data.collections.get("wgt") or bpy.data.collections.get("WGTS")

                for coll in data_to.collections:
                    if coll:
                        if coll.name.lower() in ("widgets", "widget"):
                            if not target_wgt_coll:
                                target_wgt_coll = bpy.data.collections.get("wgt") or bpy.data.collections.new("wgt")
                                if target_wgt_coll.name not in [c.name for c in bpy.context.scene.collection.children]:
                                    bpy.context.scene.collection.children.link(target_wgt_coll)
                            for obj in list(coll.objects):
                                if obj.name not in target_wgt_coll.objects:
                                    target_wgt_coll.objects.link(obj)
                                obj.hide_viewport = True
                                obj.hide_render = True
                                try:
                                    coll.objects.unlink(obj)
                                except Exception:
                                    pass
                            try:
                                bpy.data.collections.remove(coll, do_unlink=True)
                            except Exception:
                                pass
                        elif coll.name not in [c.name for c in bpy.context.scene.collection.children]:
                            bpy.context.scene.collection.children.link(coll)

                for obj in data_to.objects:
                    if obj and not any(obj.name in c.objects for c in bpy.data.collections.values()):
                        dest = target_wgt_coll if target_wgt_coll else bpy.context.scene.collection
                        dest.objects.link(obj)

                # Ensure WGT objects have proper viewport and render visibility
                wgt_plane = bpy.data.objects.get("LightPanelWGTPlane")
                wgt_selector = bpy.data.objects.get("LightPanelSelectorWGT")
                if wgt_plane:
                    wgt_plane.hide_viewport = False
                    wgt_plane.hide_render = True
                if wgt_selector:
                    wgt_selector.hide_viewport = False
                    wgt_selector.hide_render = True

                # Reconnect custom shapes to Lighting Panel armature pose bones if missing
                lp_arm = bpy.data.objects.get("Lighting Panel")
                if lp_arm and lp_arm.type == 'ARMATURE':
                    wgt_p = bpy.data.objects.get("LightPanelWGTPlane")
                    wgt_s = bpy.data.objects.get("LightPanelSelectorWGT")
                    for pb in lp_arm.pose.bones:
                        if pb.name == "Lighting Panel" and wgt_p:
                            pb.custom_shape = wgt_p
                            pb.custom_shape_scale_xyz = (1.0, 1.0, 1.0)
                            pb.use_custom_shape_bone_size = True
                            pb.bone.hide = False
                        elif pb.name in ["Rim Lit", "Shadow", "Lit", "Ambient", "RimShadow", "Rim.R", "Rim.L", "RimX", "RimY"] and wgt_s:
                            pb.custom_shape = wgt_s
                            pb.custom_shape_scale_xyz = (0.15, 0.15, 0.15)
                            pb.use_custom_shape_bone_size = True
                            pb.bone.hide = False

                    scene = bpy.context.scene
                    shader_type = getattr(scene, "zzz_shader_type", "LEGACY")
                    if shader_type == "KYTHERA":
                        for pb_name in ["Rim.L", "Rim.R"]:
                            pb_rim = lp_arm.pose.bones.get(pb_name)
                            if pb_rim:
                                con = next((c for c in pb_rim.constraints if c.type == 'LIMIT_LOCATION'), None)
                                if con and con.use_min_x and con.use_max_x:
                                    pb_rim.location.x = (con.min_x + con.max_x) / 2.0
                                elif pb_name == "Rim.L":
                                    pb_rim.location.x = 0.0425
                                elif pb_name == "Rim.R":
                                    pb_rim.location.x = 0.050
            except Exception as e:
                print(f"Failed to append objects/collections from {filepath}: {e}")

            # Ensure Light Direction empty exists as fallback if not in blend
            if not bpy.data.objects.get("Light Direction"):
                light_dir_empty = bpy.data.objects.new("Light Direction", None)
                light_dir_empty.empty_display_type = 'SINGLE_ARROW'
                bpy.context.scene.collection.objects.link(light_dir_empty)

            scene = bpy.context.scene
            shader_type = getattr(scene, "zzz_shader_type", "LEGACY")
            if shader_type == "KYTHERA":
                import math
                for obj in bpy.data.objects:
                    if obj.name.startswith("Light Direction") or obj.name.startswith("Main Light Direction"):
                        obj.rotation_mode = 'XYZ'
                        obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)

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


class WutheringWavesOutlineNodeGroupImporter(GameOutlineNodeGroupImporter):
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


class ArknightsEndfieldOutlineNodeGroupImporter(GameOutlineNodeGroupImporter):
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

