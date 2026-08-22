
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
    NEVERNESS_TO_EVERNESS_ROOT_FOLDER_FILE_PATH, NEVERNESS_TO_EVERNESS_SHADER_FILE_PATH, NEVERNESS_TO_EVERNESS_OUTLINES_FILE_PATH, get_shader_file_path
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
        target_blend_file = get_shader_file_path(self.blender_operator.game_type, 'main')
        if not target_blend_file or not os.path.isfile(target_blend_file):
            print(f"[ERROR] Could not locate bundled shader blend file for game: {self.blender_operator.game_type}")
            return {'FINISHED'}

        shader_blend_file_path = os.path.join(target_blend_file, self.MATERIAL_PATH_INSIDE_BLEND_FILE)
        shader_blend_node_tree_file_path = os.path.join(target_blend_file, self.NODE_TREE_PATH_INSIDE_BLEND_FILE)
        light_direction_empties_file_path = os.path.join(target_blend_file, self.OBJECT_PATH_INSIDE_BLEND_FILE)

        try:
            bpy.ops.wm.append(
                directory=shader_blend_file_path,
                files=self.names_of_game_materials,
                set_fake=True
            )
            self.import_light_vectors_geometry_node(shader_blend_node_tree_file_path, light_direction_empties_file_path)
        except RuntimeError as ex:
            self.blender_operator.report({'ERROR'}, f"ERROR: Error appending materials from `{target_blend_file}`: {ex}")
            raise ex

        self.blender_operator.report({'INFO'}, f'Imported Shader Materials from {target_blend_file}...')


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
        {'name': V2_FestivityGenshinImpactMaterialNames.PUPIL},
        {'name': V2_FestivityGenshinImpactMaterialNames.NEW_PUPIL},
        {'name': V3_BonnyFestivityGenshinImpactMaterialNames.BODY},
        {'name': V3_BonnyFestivityGenshinImpactMaterialNames.FACE},
        {'name': V3_BonnyFestivityGenshinImpactMaterialNames.HAIR},
        {'name': V3_BonnyFestivityGenshinImpactMaterialNames.OUTLINES},
        {'name': V3_BonnyFestivityGenshinImpactMaterialNames.PUPIL},
        {'name': V3_BonnyFestivityGenshinImpactMaterialNames.NEW_PUPIL},
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

        self.move_required_scene_objects()
        self.update_vfx_shader_scene_dependency()
        self.clean_up_unused_objects()

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

    def move_required_scene_objects(self):
        OBJECTS_TO_MOVE = ['Head Origin', 'Light Direction']
        try:
            from setup_wizard.utils.scene_utils import move_objects_between_scenes
            move_objects_between_scenes('Preview', object_names=OBJECTS_TO_MOVE)
        except Exception:
            pass

    def update_vfx_shader_scene_dependency(self, material: bpy.types.Material = None):
        try:
            from setup_wizard.domain.node_group_names import ShaderNodeGroupNames
            vfx_shader_node_group = bpy.data.node_groups.get(ShaderNodeGroupNames.VFX_SHADER_STAR_CLOAK)
            if vfx_shader_node_group:
                render_size_nodes = [node for node in vfx_shader_node_group.nodes if node.type == 'VALUE' and node.label in ['Screen Res Width', 'Screen Res Height']]
                for render_size_node in render_size_nodes:
                    try:
                        driver = render_size_node.outputs[0].animation_data.drivers[0]
                        driver.driver.variables[0].targets[0].id = bpy.context.scene
                    except (AttributeError, IndexError):
                        pass
        except Exception:
            pass

    def clean_up_unused_objects(self, object_names: list = ['Preview']):
        for object_name in object_names:
            scene_object = bpy.data.scenes.get(object_name)
            if scene_object:
                bpy.data.scenes.remove(scene_object)

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
            mat_name = material_dictionary.get('name')
            material: bpy.types.Material = bpy.data.materials.get(mat_name)
            if material:
                material.use_nodes = True
                if material.node_tree:
                    m_low = mat_name.lower()
                    is_trans = ('_trans' in m_low or 
                                'transparent' in m_low or 
                                'eyespecular' in m_low or 
                                'eye_specular' in m_low or 
                                'eyeshadow' in m_low or 
                                'eyestar' in m_low)
                    val = 1.0 if is_trans else 0.0
                    for node in material.node_tree.nodes:
                        inp = node.inputs.get('Enable Transparency')
                        if inp:
                            inp.default_value = val


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
            game_default_blend_file_with_materials="Kythera's ZZZ Shader V1.0.blend",
            names_of_game_materials=[
                {'name': "Kythera's ZZZ Face Shader"},
                {'name': "Kythera's ZZZ Shader"},
                {'name': "Kythera's ZZZ Face Shader V1.0"},
                {'name': "Kythera's ZZZ Shader V1.0"},
                {'name': "F Kythera's ZZZ Face Shader"},
                {'name': "F Kythera's ZZZ Shader"},
            ]
        )

    def import_materials(self):
        target_blend_file = get_shader_file_path(self.blender_operator.game_type, 'main')
        if target_blend_file and os.path.isfile(target_blend_file):
            try:
                with bpy.data.libraries.load(target_blend_file, link=False) as (data_from, data_to):
                    data_to.materials = data_from.materials
                    data_to.node_groups = data_from.node_groups

                for mat in data_to.materials:
                    if mat:
                        mat.use_fake_user = True
                for ng in data_to.node_groups:
                    if ng:
                        ng.use_fake_user = True
                self.blender_operator.report({'INFO'}, f"Imported Kythera ZZZ Shader Materials from `{target_blend_file}`")
            except Exception as ex:
                print(f"[ZZZ Material Importer Notice] libraries.load fallback: {ex}")
                super().import_materials()
        else:
            super().import_materials()

        # Load outline materials from the previous ZZZ Setup File V2.0.blend
        outlines_blend_file = get_shader_file_path(self.blender_operator.game_type, 'outlines')
        if outlines_blend_file and os.path.isfile(outlines_blend_file):
            try:
                outline_mat_names = {
                    ZenlessZoneZeroShaderMaterialNames.BODY_OUTLINE,
                    ZenlessZoneZeroShaderMaterialNames.BODY2_OUTLINE,
                    ZenlessZoneZeroShaderMaterialNames.BODY3_OUTLINE,
                    ZenlessZoneZeroShaderMaterialNames.FACE_OUTLINE,
                    ZenlessZoneZeroShaderMaterialNames.FACE_OUTLINES,
                    ZenlessZoneZeroShaderMaterialNames.HAIR_OUTLINE,
                    ZenlessZoneZeroShaderMaterialNames.WEAPON_OUTLINE,
                    'Transp OL',
                    'Eye Transparent',
                }
                with bpy.data.libraries.load(outlines_blend_file, link=False) as (data_from, data_to):
                    data_to.materials = [
                        m for m in data_from.materials
                        if m in outline_mat_names or 'outline' in m.lower() or 'transp' in m.lower()
                    ]
                for mat in data_to.materials:
                    if mat:
                        mat.use_fake_user = True
            except Exception as ex:
                print(f"[ZZZ Outline Material Import Notice]: {ex}")

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
        super().import_materials()

        user_selected_shader_blend_file_path = get_shader_file_path(GameType.NEVERNESS_TO_EVERNESS.name, 'main')
        if not user_selected_shader_blend_file_path or not os.path.isfile(user_selected_shader_blend_file_path):
            addon_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            for rel in ["shaders/nte/YH Shader.blend", "YH Shader.blend", "shader/YH Shader.blend"]:
                cand = os.path.join(addon_dir, rel)
                if os.path.isfile(cand):
                    user_selected_shader_blend_file_path = cand
                    break
        print(f"[DEBUG] NTE shader blend path: '{user_selected_shader_blend_file_path}'")

        if user_selected_shader_blend_file_path and os.path.isfile(user_selected_shader_blend_file_path):
            node_tree_path = os.path.join(user_selected_shader_blend_file_path, 'NodeTree')
            try:
                bpy.ops.wm.append(
                    directory=node_tree_path,
                    files=self.NTE_NODE_GROUPS,
                    set_fake=True
                )
                print(f"[DEBUG] Successfully appended NTE NodeGroups from '{user_selected_shader_blend_file_path}'")
            except Exception as ex:
                print(f"Notice: Handled appending NTE node groups: {ex}")

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





