
import bpy
import os

from bpy.types import Operator, Context

from setup_wizard.domain.game_types import GameType
from setup_wizard.domain.shader_material_names import StellarToonShaderMaterialNames, V3_BonnyFestivityGenshinImpactMaterialNames, \
    V2_FestivityGenshinImpactMaterialNames, Nya222HonkaiStarRailShaderMaterialNames, \
    JaredNytsPunishingGrayRavenShaderMaterialNames, V4_PrimoToonGenshinImpactMaterialNames, ZenlessZoneZeroShaderMaterialNames, \
    NevernessToEvernessShaderMaterialNames
from setup_wizard.import_order import GENSHIN_IMPACT_OUTLINES_FILE_PATH, NextStepInvoker, cache_using_cache_key, get_cache, \
    GENSHIN_IMPACT_ROOT_FOLDER_FILE_PATH, GENSHIN_IMPACT_SHADER_FILE_PATH, HONKAI_STAR_RAIL_ROOT_FOLDER_FILE_PATH, \
    HONKAI_STAR_RAIL_SHADER_FILE_PATH, PUNISHING_GRAY_RAVEN_ROOT_FOLDER_FILE_PATH, PUNISHING_GRAY_RAVEN_SHADER_FILE_PATH, \
    ZENLESS_ZONE_ZERO_ROOT_FOLDER_FILE_PATH, ZENLESS_ZONE_ZERO_SHADER_FILE_PATH, ZENLESS_ZONE_ZERO_OUTLINES_FILE_PATH, \
    NEVERNESS_TO_EVERNESS_ROOT_FOLDER_FILE_PATH, NEVERNESS_TO_EVERNESS_SHADER_FILE_PATH, NEVERNESS_TO_EVERNESS_OUTLINES_FILE_PATH
from setup_wizard.material_import_setup.empty_names import LightDirectionEmptyNames
from setup_wizard.outline_import_setup.outline_node_groups import OutlineNodeGroupNames
from setup_wizard.texture_import_setup.material_default_value_setters import MaterialDefaultValueSetter, MaterialDefaultValueSetterFactory


class GameMaterialImporterFactory:
    def create(game_type: GameType, blender_operator: Operator, context: Context):
        if game_type == GameType.GENSHIN_IMPACT.name:
            return GenshinImpactMaterialImporterFacade(blender_operator, context)
        elif game_type == GameType.HONKAI_STAR_RAIL.name:
            return HonkaiStarRailMaterialImporterFacade(blender_operator, context)
        elif game_type == GameType.PUNISHING_GRAY_RAVEN.name:
            return PunishingGrayRavenMaterialImporterFacade(blender_operator, context)
        elif game_type == GameType.ZENLESS_ZONE_ZERO.name:
            return ZenlessZoneZeroMaterialImporterFacade(blender_operator, context)
        elif game_type == GameType.NEVERNESS_TO_EVERNESS.name:
            return NevernessToEvernessMaterialImporterFacade(blender_operator, context)
        else:
            raise Exception(f'Unknown {GameType}: {game_type}')



class GameMaterialImporter:
    MATERIAL_PATH_INSIDE_BLEND_FILE = 'Material'
    NODE_TREE_PATH_INSIDE_BLEND_FILE = 'NodeTree'
    OBJECT_PATH_INSIDE_BLEND_FILE = 'Object'
    OUTLINES_FILE_PATH = None

    def __init__(self, 
                 blender_operator: Operator, 
                 context: Context,
                 game_shader_cache_file_path: str,
                 game_shader_cache_folder_path: str,
                 game_default_blend_file_with_materials: str,
                 names_of_game_materials: list):
        self.blender_operator = blender_operator
        self.context = context
        self.game_shader_file_path = game_shader_cache_file_path
        self.game_shader_folder_path = game_shader_cache_folder_path
        self.game_default_blend_file_with_materials = game_default_blend_file_with_materials
        self.names_of_game_materials = names_of_game_materials

    def import_materials(self):
        cache_enabled = self.context.window_manager.cache_enabled
        user_selected_shader_blend_file_path = self.blender_operator.filepath if \
            self.blender_operator.filepath and not os.path.isdir(self.blender_operator.filepath) else \
            get_cache(cache_enabled).get(self.game_shader_file_path)
        project_root_directory_file_path = self.blender_operator.file_directory \
            or get_cache(cache_enabled).get(self.game_shader_folder_path) \
            or (os.path.dirname(self.blender_operator.filepath) if self.blender_operator.filepath else None)

        print(f"[DEBUG] GameMaterialImporter.import_materials: user_selected_shader_blend_file_path='{user_selected_shader_blend_file_path}', project_root_directory_file_path='{project_root_directory_file_path}'")

        # Resolve exact target blend file
        target_blend_file = None
        if user_selected_shader_blend_file_path and os.path.isfile(user_selected_shader_blend_file_path):
            target_blend_file = user_selected_shader_blend_file_path
        elif project_root_directory_file_path:
            c1 = os.path.join(project_root_directory_file_path, self.game_default_blend_file_with_materials)
            c2 = os.path.join(os.path.dirname(project_root_directory_file_path), self.game_default_blend_file_with_materials) if project_root_directory_file_path else None
            if os.path.isfile(c1):
                target_blend_file = c1
            elif c2 and os.path.isfile(c2):
                target_blend_file = c2

        if not target_blend_file:
            addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            for rel in [self.game_default_blend_file_with_materials, f"shader/{self.game_default_blend_file_with_materials}"]:
                cand = os.path.join(addon_dir, rel)
                if os.path.isfile(cand):
                    target_blend_file = cand
                    break

        if not target_blend_file:
            cached_path = get_cache(cache_enabled).get(self.game_shader_file_path)
            if cached_path and os.path.isfile(cached_path):
                target_blend_file = cached_path

        if not target_blend_file and not project_root_directory_file_path:
            print(f"[DEBUG] No blend path or root folder cached. Calling bpy.ops.genshin.import_materials('INVOKE_DEFAULT')")
            bpy.ops.genshin.import_materials(
                'INVOKE_DEFAULT',
                next_step_idx=self.blender_operator.next_step_idx, 
                file_directory=self.blender_operator.file_directory,
                invoker_type=self.blender_operator.invoker_type,
                high_level_step_name=self.blender_operator.high_level_step_name,
                game_type=self.blender_operator.game_type,
            )
            return {'FINISHED'}

        shader_blend_file_path = os.path.join(target_blend_file, self.MATERIAL_PATH_INSIDE_BLEND_FILE) if target_blend_file else os.path.join(project_root_directory_file_path, self.game_default_blend_file_with_materials, self.MATERIAL_PATH_INSIDE_BLEND_FILE)
        shader_blend_node_tree_file_path = os.path.join(target_blend_file, self.NODE_TREE_PATH_INSIDE_BLEND_FILE) if target_blend_file else os.path.join(project_root_directory_file_path, self.game_default_blend_file_with_materials, self.NODE_TREE_PATH_INSIDE_BLEND_FILE)
        light_direction_empties_file_path = os.path.join(target_blend_file, self.OBJECT_PATH_INSIDE_BLEND_FILE) if target_blend_file else os.path.join(project_root_directory_file_path, self.game_default_blend_file_with_materials, self.OBJECT_PATH_INSIDE_BLEND_FILE)

        try:
            bpy.ops.wm.append(
                directory=shader_blend_file_path,
                files=self.names_of_game_materials,
                set_fake=True
            )
            self.import_light_vectors_geometry_node(shader_blend_node_tree_file_path, light_direction_empties_file_path)
        except RuntimeError as ex:
            self.blender_operator.report({'ERROR'}, \
                f"ERROR: Error when trying to append materials and Light Vector geometry node. \n\
                Did not find `{self.game_default_blend_file_with_materials}` in the directory you selected. \n\
                Try selecting the exact blend file you want to use.")
            raise ex

        self.blender_operator.report({'INFO'}, 'Imported Shader/Genshin Materials...')
        if cache_enabled and (user_selected_shader_blend_file_path or project_root_directory_file_path):
            if user_selected_shader_blend_file_path:
                cache_using_cache_key(get_cache(cache_enabled), self.game_shader_file_path, user_selected_shader_blend_file_path)

                outlines_in_shader_blend_file = self.__get_outlines_node_group_from_shader_blend_file(
                    user_selected_shader_blend_file_path)
                if outlines_in_shader_blend_file:
                    self.__set_outlines_cache(cache_enabled, user_selected_shader_blend_file_path)
            else:
                cache_using_cache_key(get_cache(cache_enabled), self.game_shader_folder_path, project_root_directory_file_path)


    def import_light_vectors_geometry_node(self, node_tree_filepath, object_file_path):
        for outline_node_group_name in OutlineNodeGroupNames.V3_LIGHT_VECTORS_GEOMETRY_NODES:
            if not bpy.data.node_groups.get(outline_node_group_name):
                try:
                    bpy.ops.wm.append(
                        filepath=os.path.join(node_tree_filepath, outline_node_group_name),
                        directory=os.path.join(node_tree_filepath),
                        filename=outline_node_group_name
                    )
                except Exception as ex:
                    print(f"Notice: Handled appending light vectors node group: {ex}")

        # Clean up any existing duplicate empties (.001, .002) first
        for obj in list(bpy.data.objects):
            if any(base in obj.name for base in ['Head Origin', 'Light Direction']) and ('.00' in obj.name or '.01' in obj.name):
                base_name = obj.name.split('.')[0]
                if bpy.data.objects.get(base_name) and bpy.data.objects.get(base_name) != obj:
                    bpy.data.objects.remove(obj, do_unlink=True)

        has_light_empties = any(bpy.data.objects.get(name) for name in ['Head Origin', 'Light Direction'])
        if not has_light_empties:
            light_direction_empties_to_append = [
                empty_object for empty_object in LightDirectionEmptyNames.LIGHT_DIRECTION_EMPTIES_FILE_IMPORT 
                if not bpy.data.objects.get(empty_object.get('name'))
            ]
            if light_direction_empties_to_append:
                try:
                    bpy.ops.wm.append(
                        directory=object_file_path,
                        files=light_direction_empties_to_append,
                    )
                except Exception as ex:
                    print(f"Notice: Handled appending light empties: {ex}")

    def __get_outlines_node_group_from_shader_blend_file(self, shader_blend_file_path):
        with bpy.data.libraries.load(shader_blend_file_path) as (data_from, data_to):
            outlines_in_shader_blend_file = [node_group for node_group in data_from.node_groups if
                                                node_group in [
                                                    node_group_name for node_group_name in OutlineNodeGroupNames.V3_BONNY_FESTIVITY_GENSHIN_OUTLINES
                                                ]
                                            ]
        return outlines_in_shader_blend_file

    def __set_outlines_cache(self, cache_enabled, shader_file_path):
        if self.OUTLINES_FILE_PATH and cache_enabled and shader_file_path:
            cache_using_cache_key(get_cache(cache_enabled), self.OUTLINES_FILE_PATH, shader_file_path)

class GenshinImpactMaterialImporterFacade(GameMaterialImporter):
    DEFAULT_BLEND_FILE_WITH_GENSHIN_MATERIALS = 'HoYoverse - Genshin Impact - Goo Engine v3.blend'
    NAMES_OF_GENSHIN_MATERIALS = [
        {'name': V2_FestivityGenshinImpactMaterialNames.BODY},
        {'name': V2_FestivityGenshinImpactMaterialNames.FACE},
        {'name': V2_FestivityGenshinImpactMaterialNames.HAIR},
        {'name': V2_FestivityGenshinImpactMaterialNames.OUTLINES},
        {'name': V3_BonnyFestivityGenshinImpactMaterialNames.BODY},
        {'name': V3_BonnyFestivityGenshinImpactMaterialNames.FACE},
        {'name': V3_BonnyFestivityGenshinImpactMaterialNames.HAIR},
        {'name': V3_BonnyFestivityGenshinImpactMaterialNames.OUTLINES},
        {'name': V4_PrimoToonGenshinImpactMaterialNames.VFX},
    ]
    OUTLINES_FILE_PATH = GENSHIN_IMPACT_OUTLINES_FILE_PATH

    def __init__(self, blender_operator, context):
        super().__init__(
            blender_operator,
            context,
            GENSHIN_IMPACT_SHADER_FILE_PATH,
            GENSHIN_IMPACT_ROOT_FOLDER_FILE_PATH,
            self.DEFAULT_BLEND_FILE_WITH_GENSHIN_MATERIALS,
            self.NAMES_OF_GENSHIN_MATERIALS
        )

    def import_materials(self):
        status = super().import_materials()  # Genshin Impact Material Importer

        if status == {'FINISHED'}:
            return status

        if self.is_create_hair_material_from_body():  # Genshin Shader >= v4.0
            self.create_hair_material()

        cache_enabled = self.context.window_manager.cache_enabled
        project_root_directory_file_path = self.blender_operator.file_directory \
            or get_cache(cache_enabled).get(self.game_shader_folder_path) \
            or os.path.dirname(self.blender_operator.filepath)

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx, 
            self.blender_operator.invoker_type, 
            file_path_to_cache=project_root_directory_file_path,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=self.blender_operator.game_type,
        )

    def is_create_hair_material_from_body(self):
        body_material_exists = bpy.data.materials.get(V4_PrimoToonGenshinImpactMaterialNames.BODY)
        hair_material_missing = not bpy.data.materials.get(V4_PrimoToonGenshinImpactMaterialNames.HAIR)
        return body_material_exists and hair_material_missing

    def create_hair_material(self):
        body_material = bpy.data.materials.get(V4_PrimoToonGenshinImpactMaterialNames.BODY)
        hair_material = body_material.copy()
        material_default_value_setter: MaterialDefaultValueSetter = MaterialDefaultValueSetterFactory.create(self.blender_operator.game_type)
        material_default_value_setter.set_up_hair_material(hair_material)


class HonkaiStarRailMaterialImporterFacade(GameMaterialImporter):
    DEFAULT_BLEND_FILE_WITH_HSR_MATERIALS = 'StellarToon.blend'
    NAMES_OF_HONKAI_STAR_RAIL_MATERIALS = [
        {'name': Nya222HonkaiStarRailShaderMaterialNames.BODY1},
        {'name': Nya222HonkaiStarRailShaderMaterialNames.BODY2},
        {'name': Nya222HonkaiStarRailShaderMaterialNames.BODY_TRANS},
        {'name': Nya222HonkaiStarRailShaderMaterialNames.HAIR},
        {'name': Nya222HonkaiStarRailShaderMaterialNames.FACE},
        {'name': Nya222HonkaiStarRailShaderMaterialNames.EYESHADOW},
        {'name': Nya222HonkaiStarRailShaderMaterialNames.OUTLINES},
        {'name': Nya222HonkaiStarRailShaderMaterialNames.WEAPON},
        {'name': StellarToonShaderMaterialNames.BASE},
        {'name': StellarToonShaderMaterialNames.HAIR},
        {'name': StellarToonShaderMaterialNames.FACE},
        {'name': StellarToonShaderMaterialNames.EYESHADOW},
        {'name': StellarToonShaderMaterialNames.WEAPON},
        {'name': StellarToonShaderMaterialNames.BASE_OUTLINES},
        {'name': StellarToonShaderMaterialNames.HAIR_OUTLINES},
        {'name': StellarToonShaderMaterialNames.FACE_OUTLINES},
        {'name': StellarToonShaderMaterialNames.WEAPON_OUTLINES},
    ]

    def __init__(self, blender_operator, context):
        super().__init__(
            blender_operator,
            context,
            HONKAI_STAR_RAIL_SHADER_FILE_PATH,
            HONKAI_STAR_RAIL_ROOT_FOLDER_FILE_PATH,
            self.DEFAULT_BLEND_FILE_WITH_HSR_MATERIALS,
            self.NAMES_OF_HONKAI_STAR_RAIL_MATERIALS
        )

    def import_materials(self):
        status = super().import_materials()  # Honkai Star Rail Material Importer

        # EXEC_DEFAULT hits this if INVOKE_DEFAULT is executed above.
        # Ensure it ends here otherwise it will error below due to the materia
        if status == {'FINISHED'}:
            return status

        # Set 'Use Nodes' because shader does not have that by default
        # It's important this runs BEFORE the next step is invoked because Replace Default Materials clones materials
        for material_dictionary in self.NAMES_OF_HONKAI_STAR_RAIL_MATERIALS:
            material: bpy.types.Material = bpy.data.materials.get(material_dictionary.get('name'))
            if material:
                material.use_nodes = True


        cache_enabled = self.context.window_manager.cache_enabled
        project_root_directory_file_path = self.blender_operator.file_directory \
            or get_cache(cache_enabled).get(self.game_shader_folder_path) \
            or os.path.dirname(self.blender_operator.filepath)

        # Important that this is called here so that 'Use Nodes' is set on all original materials before Replace Default Materials
        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx, 
            self.blender_operator.invoker_type, 
            file_path_to_cache=project_root_directory_file_path,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=self.blender_operator.game_type,
        )


class PunishingGrayRavenMaterialImporterFacade(GameMaterialImporter):
    DEFAULT_BLEND_FILE_WITH_PGR_MATERIALS = 'PGR_Shader.blend'
    NAMES_OF_PUNISHING_GRAY_RAVEN_MATERIALS = [
        {'name': JaredNytsPunishingGrayRavenShaderMaterialNames.ALPHA},
        {'name': JaredNytsPunishingGrayRavenShaderMaterialNames.EYE},
        {'name': JaredNytsPunishingGrayRavenShaderMaterialNames.FACE},
        {'name': JaredNytsPunishingGrayRavenShaderMaterialNames.HAIR},
        {'name': JaredNytsPunishingGrayRavenShaderMaterialNames.MAIN},
        {'name': JaredNytsPunishingGrayRavenShaderMaterialNames.OUTLINES},
    ]

    def __init__(self, blender_operator, context):
        super().__init__(
            blender_operator,
            context,
            PUNISHING_GRAY_RAVEN_SHADER_FILE_PATH,
            PUNISHING_GRAY_RAVEN_ROOT_FOLDER_FILE_PATH,
            self.DEFAULT_BLEND_FILE_WITH_PGR_MATERIALS,
            self.NAMES_OF_PUNISHING_GRAY_RAVEN_MATERIALS
        )

    def import_materials(self):
        status = super().import_materials()  # Punishing Gray Raven Material Importer

        # EXEC_DEFAULT hits this if INVOKE_DEFAULT is executed above.
        # Ensure it ends here otherwise it will error below due to the materia
        if status == {'FINISHED'}:
            return status

        cache_enabled = self.context.window_manager.cache_enabled
        project_root_directory_file_path = self.blender_operator.file_directory \
            or get_cache(cache_enabled).get(self.game_shader_folder_path) \
            or os.path.dirname(self.blender_operator.filepath)

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx, 
            self.blender_operator.invoker_type, 
            file_path_to_cache=project_root_directory_file_path,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=self.blender_operator.game_type,
        )


class ZenlessZoneZeroMaterialImporterFacade(GameMaterialImporter):
    def __init__(self, blender_operator, context):
        super().__init__(
            blender_operator=blender_operator,
            context=context,
            game_shader_cache_file_path=ZENLESS_ZONE_ZERO_SHADER_FILE_PATH,
            game_shader_cache_folder_path=ZENLESS_ZONE_ZERO_ROOT_FOLDER_FILE_PATH,
            game_default_blend_file_with_materials='ZZZ_Shader.blend',
            names_of_game_materials=[
                {'name': ZenlessZoneZeroShaderMaterialNames.BODY},
                {'name': ZenlessZoneZeroShaderMaterialNames.BODY2},
                {'name': ZenlessZoneZeroShaderMaterialNames.BODY3},
                {'name': ZenlessZoneZeroShaderMaterialNames.FACE},
                {'name': ZenlessZoneZeroShaderMaterialNames.HAIR},
                {'name': ZenlessZoneZeroShaderMaterialNames.WEAPON},
                {'name': ZenlessZoneZeroShaderMaterialNames.WEAPON2},
                {'name': ZenlessZoneZeroShaderMaterialNames.EYE},
                {'name': ZenlessZoneZeroShaderMaterialNames.EYE_HIGHLIGHTS},
                {'name': ZenlessZoneZeroShaderMaterialNames.BODY_OUTLINE},
                {'name': ZenlessZoneZeroShaderMaterialNames.BODY2_OUTLINE},
                {'name': ZenlessZoneZeroShaderMaterialNames.BODY3_OUTLINE},
                {'name': ZenlessZoneZeroShaderMaterialNames.FACE_OUTLINE},
                {'name': ZenlessZoneZeroShaderMaterialNames.FACE_OUTLINES},
                {'name': ZenlessZoneZeroShaderMaterialNames.HAIR_OUTLINE},
                {'name': ZenlessZoneZeroShaderMaterialNames.WEAPON_OUTLINE},
                {'name': 'Transp OL'},
                {'name': 'Eye Transparent'},
            ]
        )

    def import_materials(self):
        status = super().import_materials()

        if status == {'FINISHED'}:
            return status

        cache_enabled = self.context.window_manager.cache_enabled
        user_selected_shader_blend_file_path = self.blender_operator.filepath if \
            self.blender_operator.filepath and not os.path.isdir(self.blender_operator.filepath) else \
            get_cache(cache_enabled).get(self.game_shader_file_path)

        if user_selected_shader_blend_file_path and cache_enabled:
            cache_using_cache_key(get_cache(cache_enabled), ZENLESS_ZONE_ZERO_OUTLINES_FILE_PATH, user_selected_shader_blend_file_path)

        project_root_directory_file_path = self.blender_operator.file_directory \
            or get_cache(cache_enabled).get(self.game_shader_folder_path) \
            or os.path.dirname(self.blender_operator.filepath)

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx, 
            self.blender_operator.invoker_type, 
            file_path_to_cache=project_root_directory_file_path,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=self.blender_operator.game_type,
        )


class NevernessToEvernessMaterialImporterFacade(GameMaterialImporter):
    NTE_MATERIAL_NAMES = [
        {'name': '异环-头发'},
        {'name': '异环-身体'},
        {'name': '异环-面部'},
        {'name': 'YH-Main-UP'},
        {'name': 'YH-Main-DOWN'},
        {'name': '前发'},
        {'name': '后发'},
        {'name': '面'},
        {'name': '肌'},
        {'name': '目'},
        {'name': '目Hi'},
        {'name': '目影'},
        {'name': '目白'},
        {'name': '眉毛'},
        {'name': '睫毛'},
        {'name': '二重'},
        {'name': '口'},
        {'name': '齿舌'},
        {'name': '表情'},
        {'name': 'edge_clothes2'},
        {'name': 'facerim'},
        {'name': 'hairrim'},
        {'name': 'mrim'},
        {'name': 'Dots Stroke'},
    ]

    NTE_NODE_GROUPS = [
        {'name': '异环-头发'},
        {'name': '异环-身体'},
        {'name': '异环-面部'},
        {'name': 'Light Vectors'},
        {'name': 'Face Factor Main'},
        {'name': 'Dot Creation Main'},
        {'name': 'WuwaNormals'},
        {'name': 'Super Color Ramp'},
        {'name': 'Super-Color-Ramp'},
        {'name': '几何节点描边'},
        {'name': '实体化描边.001'},
        {'name': 'DX To GL'},
        {'name': 'Matcap矢量'},
        {'name': 'Matcap采样'},
        {'name': '全局调色'},
        {'name': '深度边缘光'},
        {'name': '菲涅尔'},
        {'name': '衣服描边'},
    ]

    def __init__(self, blender_operator, context):
        super().__init__(
            blender_operator=blender_operator,
            context=context,
            game_shader_cache_file_path=NEVERNESS_TO_EVERNESS_SHADER_FILE_PATH,
            game_shader_cache_folder_path=NEVERNESS_TO_EVERNESS_ROOT_FOLDER_FILE_PATH,
            game_default_blend_file_with_materials='YH Shader.blend',
            names_of_game_materials=self.NTE_MATERIAL_NAMES
        )

    def import_materials(self):
        print(f"[DEBUG] NevernessToEvernessMaterialImporterFacade.import_materials called: filepath='{self.blender_operator.filepath}'")
        status = super().import_materials()
        print(f"[DEBUG] super().import_materials() returned: {status}")

        if status == {'FINISHED'}:
            return status

        cache_enabled = self.context.window_manager.cache_enabled
        user_selected_shader_blend_file_path = self.blender_operator.filepath if \
            self.blender_operator.filepath and not os.path.isdir(self.blender_operator.filepath) else \
            get_cache(cache_enabled).get(self.game_shader_file_path)

        if not user_selected_shader_blend_file_path:
            addon_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            for rel in ["YH Shader.blend", "shader/YH Shader.blend"]:
                cand = os.path.join(addon_dir, rel)
                if os.path.isfile(cand):
                    user_selected_shader_blend_file_path = cand
                    break
        print(f"[DEBUG] user_selected_shader_blend_file_path: '{user_selected_shader_blend_file_path}'")


        if user_selected_shader_blend_file_path:
            node_tree_path = os.path.join(user_selected_shader_blend_file_path, 'NodeTree')
            try:
                bpy.ops.wm.append(
                    directory=node_tree_path,
                    files=self.NTE_NODE_GROUPS,
                    set_fake=True
                )
            except Exception as ex:
                print(f"Notice: Handled appending NTE node groups: {ex}")

        if user_selected_shader_blend_file_path and cache_enabled:
            cache_using_cache_key(get_cache(cache_enabled), NEVERNESS_TO_EVERNESS_OUTLINES_FILE_PATH, user_selected_shader_blend_file_path)

        # Clean up any duplicate empties (.001, .002) safely without ReferenceError
        orig_head = bpy.data.objects.get('Head Origin')
        orig_light = bpy.data.objects.get('Light Direction')

        head_dupes = []
        light_dupes = []

        for obj in list(bpy.data.objects):
            try:
                name_low = obj.name.lower()
                has_suffix = '.00' in obj.name or '.01' in obj.name
                if has_suffix:
                    if any(k in name_low for k in ['head origin', 'head forward', 'head up']):
                        if orig_head and obj != orig_head:
                            head_dupes.append(obj)
                    elif any(k in name_low for k in ['light direction', 'sun']):
                        if orig_light and obj != orig_light:
                            light_dupes.append(obj)
            except Exception:
                pass

        for obj in head_dupes:
            try:
                if orig_head:
                    for other in list(bpy.data.objects):
                        try:
                            if getattr(other, 'parent', None) == obj:
                                other.parent = orig_head
                            for con in getattr(other, 'constraints', []):
                                if getattr(con, 'target', None) == obj:
                                    con.target = orig_head
                        except Exception:
                            pass
                bpy.data.objects.remove(obj, do_unlink=True)
            except Exception:
                pass

        for obj in light_dupes:
            try:
                if orig_light:
                    for other in list(bpy.data.objects):
                        try:
                            if getattr(other, 'parent', None) == obj:
                                other.parent = orig_light
                            for con in getattr(other, 'constraints', []):
                                if getattr(con, 'target', None) == obj:
                                    con.target = orig_light
                        except Exception:
                            pass
                bpy.data.objects.remove(obj, do_unlink=True)
            except Exception:
                pass

        project_root_directory_file_path = self.blender_operator.file_directory \
            or get_cache(cache_enabled).get(self.game_shader_folder_path) \
            or (os.path.dirname(self.blender_operator.filepath) if self.blender_operator.filepath else None)

        NextStepInvoker().invoke(
            self.blender_operator.next_step_idx, 
            self.blender_operator.invoker_type, 
            file_path_to_cache=project_root_directory_file_path,
            high_level_step_name=self.blender_operator.high_level_step_name,
            game_type=self.blender_operator.game_type,
        )





