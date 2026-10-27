# Author: michael-gh1

import bpy
import os

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator
from setup_wizard.import_order import cache_using_cache_key, get_cache, HOYOVERSE_COMPOSITING_NODE_FILE_PATH, get_shader_file_path
from setup_wizard.domain.game_types import GameType

from setup_wizard.setup_wizard_operator_base_classes import CustomOperatorProperties
from setup_wizard.setup_wizard_operator_base_classes import NextStepInvoker
from setup_wizard.setup_wizard_operator_base_classes import BasicSetupUIOperator

NAME_OF_DEFAULT_SCENE = 'Scene'

NAME_OF_COMPOSITE_NODE = 'HoYoverse Post Processing'
NAME_OF_GRAN_TURISMO_NODE_TREE = 'GranTurismoWrapper [APPEND]'
NAME_OF_HOYOVERSE_POST_PROCESSING_NODE_TREE = 'HoYoverse - Post Processing'

NAME_OF_COMPOSITOR_INPUT_NODE = 'Render Layers'
NAME_OF_COMPOSITOR_OUTPUT_NODE = 'Composite'

NAME_OF_VIEWER_NODE = 'Viewer'
NAME_OF_VIEWER_NODE_TYPE = 'CompositorNodeViewer'

NAME_OF_IMAGE_IO = 'Image'
NAME_OF_GT_COMPOSITE_NODE_OUTPUT = 'Result'
NAME_OF_HYV_PP_COMPOSITE_NODE_OUTPUT = 'Image'
NAME_OF_HYV_PP_COMPOSITE_NODE_OUTPUT_V2 = 'Combined'


def get_output_node_name():
    if bpy.app.version >= (5, 0, 0):
        return 'Group Output'
    return 'Composite'


def get_output_node_type():
    if bpy.app.version >= (5, 0, 0):
        return 'NodeGroupOutput'
    return 'CompositorNodeComposite'


def find_builtin_node(tree, node_type):
    """Built-in node names are translated when Blender creates them."""
    return next((n for n in tree.nodes if n.bl_idname == node_type
                 and getattr(n, 'is_active_output', True)), None)


def get_node_tree(scene):
    if hasattr(scene, "compositing_node_group"):
        if not scene.compositing_node_group:
            tree = bpy.data.node_groups.new("Compositing Nodetree", "CompositorNodeTree")
            scene.compositing_node_group = tree
            # Create default Render Layers and Composite nodes if they don't exist
            if not tree.nodes.get("Render Layers"):
                node = tree.nodes.new(type="CompositorNodeRLayers")
                node.name = "Render Layers"
            
            output_name = get_output_node_name()
            output_type = get_output_node_type()
            if not tree.nodes.get(output_name):
                if hasattr(tree, "interface"):
                    try:
                        tree.interface.new_socket(name="Image", in_out='OUTPUT', socket_type='NodeSocketColor')
                    except Exception:
                        pass
                node = tree.nodes.new(type=output_type)
                node.name = output_name
        return scene.compositing_node_group

    scene.use_nodes = True
    return scene.node_tree


class GI_OT_PostProcessingCompositingSetup(Operator, BasicSetupUIOperator):
    '''Sets Up Post Processing Compositing'''
    bl_idname = 'hoyoverse.post_processing_compositing_setup'
    bl_label = 'HoYoverse: Set Up Post Processing Compositing (UI)'


class PGR_OT_SetUpCompositor(Operator, CustomOperatorProperties):
    """Ensure a render output without adding foreign post-processing to PGR."""
    bl_idname = 'punishing_gray_raven.setup_compositor'
    bl_label = 'PGR: Set Up Compositor'

    def execute(self, context):
        context.scene.render.use_compositing = True
        tree = get_node_tree(context.scene)
        output_type = get_output_node_type()
        output = next((n for n in tree.nodes if n.bl_idname == output_type
                       and (output_type != 'NodeGroupOutput' or n.is_active_output)), None)
        if output is None:
            if output_type == 'NodeGroupOutput':
                if not any(s.item_type == 'SOCKET' and s.in_out == 'OUTPUT' and s.socket_type == 'NodeSocketColor'
                           for s in tree.interface.items_tree):
                    tree.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
            output = tree.nodes.new(output_type)
        image_input = output.inputs.get('Image') or next((s for s in output.inputs if s.type == 'RGBA'), None)
        if image_input is None:
            self.report({'ERROR'}, 'PGR compositor output has no image socket')
            return {'CANCELLED'}
        # Preserve an existing custom processing chain.
        if not image_input.is_linked:
            render = next((n for n in tree.nodes if n.bl_idname == 'CompositorNodeRLayers'), None)
            if render is None:
                render = tree.nodes.new('CompositorNodeRLayers')
            tree.links.new(render.outputs['Image'], image_input)
        if self.next_step_idx:
            NextStepInvoker().invoke(self.next_step_idx, self.invoker_type,
                                     high_level_step_name=self.high_level_step_name,
                                     game_type=self.game_type)
        return {'FINISHED'}


class PostProcessingFeatureFlag:
    # self is CustomOperatorProperties only for IDE syntax highlighting purposes
    def feature_disabled(self: CustomOperatorProperties, context):
        post_processing_setup_enabled = context.window_manager.post_processing_setup_enabled

        is_advanced_setup = self.high_level_step_name != 'GENSHIN_OT_setup_wizard_ui' and \
            self.high_level_step_name != 'GENSHIN_OT_setup_wizard_ui_no_outlines' and \
            self.high_level_step_name != 'HONKAI_STAR_RAIL_OT_setup_wizard_ui' and \
            self.high_level_step_name != 'HONKAI_STAR_RAIL_OT_setup_wizard_ui_no_outlines'
        
        return not post_processing_setup_enabled and not is_advanced_setup


class HYV_OT_CustomCompositeNodeSetup(Operator, ImportHelper, CustomOperatorProperties, PostProcessingFeatureFlag):
    """Imports Composite node tree"""
    bl_idname = 'hoyoverse.custom_composite_node_setup'
    bl_label = 'Hoyoverse: Custom Composite Node Setup'

    # ImportHelper mixin class uses this
    filename_ext = "*.*"

    import_path: StringProperty(
        name="Path",
        description="Path to the file to import",
        default="",
        subtype='DIR_PATH'
    )

    filter_glob: StringProperty(
        default="*.*",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    logs = 'Custom Composite Node Setup:\n'
    names_of_node_groups = [
        NAME_OF_GRAN_TURISMO_NODE_TREE,
        NAME_OF_HOYOVERSE_POST_PROCESSING_NODE_TREE,
    ]
    names_of_composite_node_outputs = [
        NAME_OF_GT_COMPOSITE_NODE_OUTPUT,
        NAME_OF_HYV_PP_COMPOSITE_NODE_OUTPUT,
        NAME_OF_HYV_PP_COMPOSITE_NODE_OUTPUT_V2,
    ]

    def execute(self, context):
        if self.feature_disabled(context):
            if self.next_step_idx:
                NextStepInvoker().invoke(
                    self.next_step_idx, 
                    self.invoker_type, 
                    high_level_step_name=self.high_level_step_name,
                    game_type=self.game_type,
                )
            self.clear_custom_properties()
            return {'FINISHED'}

        composite_blend_file_path = get_shader_file_path(GameType.GENSHIN_IMPACT.name, 'compositing')

        if hasattr(context.scene, 'use_nodes'):
            context.scene.use_nodes = True
        
        get_node_tree(context.scene)

        # Technically works if only running this Operator, but this cannot be chained because we need to be 
        # out of the script (or in another Operator) to update ctx before the import modal appears
        # Solution would be to create a separate Operator that handles context switches
        # TODO: This does not work unless INVOKE_DEFAULT with a modal or some window appears to update the Blender UI
        # self.switch_to_compositor()

        composite_node_group = next((g for g in bpy.data.node_groups
                                    if g.get('_gacha_compositor_source') == composite_blend_file_path), None)
        if not composite_node_group and composite_blend_file_path:
            name_of_composite_node_group = self.append_composite_node_group(composite_blend_file_path)
            composite_node_group = bpy.data.node_groups.get(name_of_composite_node_group)
        elif not composite_node_group:
            self.logs += 'No composite node group blend file found.\n'

        scene = context.scene
        composite_node = get_node_tree(scene).nodes.get(NAME_OF_COMPOSITE_NODE)
        if not composite_node or composite_node.bl_idname != 'CompositorNodeGroup':
            self.create_compositor_node_group(composite_node_group.name)
        else:
            composite_node.node_tree = composite_node_group
            self.logs += f'{composite_node_group.name} node already created, skipping and not creating new node.\n'

        viewer_node = find_builtin_node(get_node_tree(scene), NAME_OF_VIEWER_NODE_TYPE)
        if not viewer_node:
            self.create_compositor_node(NAME_OF_VIEWER_NODE_TYPE)
        else:
            self.logs += f'Viewer node already exists, skipping.\n'

        self.connect_starting_nodes(scene)
        self.set_node_locations(scene)

        self.report({'INFO'}, f'{self.logs}')
        if self.next_step_idx:
            NextStepInvoker().invoke(
                self.next_step_idx, 
                self.invoker_type, 
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
            )
        self.clear_custom_properties()
        return {'FINISHED'}

    '''
    def switch_to_compositor(self):
        bpy.ops.genshin.change_bpy_context(
            'EXEC_DEFAULT',
            bpy_context_attr='area.type',
            bpy_context_value_str='NODE_EDITOR'
        )
        bpy.ops.genshin.change_bpy_context(
            'EXEC_DEFAULT',
            bpy_context_attr='scene.use_nodes',
            bpy_context_value_bool=True
        )
    '''

    def append_composite_node_group(self, composite_node_group_blend_file_path):
        from setup_wizard.services.compositor_sources import load_group
        with bpy.data.libraries.load(composite_node_group_blend_file_path, link=False) as (source, target):
            name = next((n for n in self.names_of_node_groups if n in source.node_groups), None)
        if name is None:
            raise RuntimeError('No HoYoverse post-processing group found in shader')
        group = load_group(composite_node_group_blend_file_path, name)
        self.logs += f'Appended {group.name}\n'
        return group.name

    # Important to create using node_tree.nodes.new() instead of bpy.ops.node.add_node()
    def create_compositor_node_group(self, node_name):
        node_tree = get_node_tree(bpy.context.scene)
        node = node_tree.nodes.new(
            type='CompositorNodeGroup'
        )
        node.node_tree = bpy.data.node_groups.get(node_name)
        node.name = NAME_OF_COMPOSITE_NODE
        self.logs += f'Created {node_name} node tree\n'

    # Important to create using node_tree.nodes.new() instead of bpy.ops.node.add_node()
    def create_compositor_node(self, node_type):
        node_tree = get_node_tree(bpy.context.scene)
        node_tree.nodes.new(
            type=node_type
        )
        self.logs += f'Created {node_type} node tree\n'

    def connect_starting_nodes(self, scene):
        render_layers_node = find_builtin_node(get_node_tree(scene), 'CompositorNodeRLayers')
        render_layers_output = render_layers_node.outputs.get(NAME_OF_IMAGE_IO)

        composite_wrapper_node = get_node_tree(scene).nodes.get(NAME_OF_COMPOSITE_NODE)
        composite_wrapper_node_input = composite_wrapper_node.inputs.get(NAME_OF_IMAGE_IO)
        composite_wrapper_node_output = None

        for composite_node_output_name in self.names_of_composite_node_outputs:
            composite_wrapper_node_output = composite_wrapper_node.outputs.get(composite_node_output_name)
            if composite_wrapper_node_output:
                break

        composite_node = find_builtin_node(get_node_tree(scene), get_output_node_type())
        composite_node_input = composite_node.inputs.get(NAME_OF_IMAGE_IO) or next(
            (s for s in composite_node.inputs if s.type == 'RGBA'), None)

        viewer_node = find_builtin_node(get_node_tree(scene), NAME_OF_VIEWER_NODE_TYPE)
        viewer_node_input = viewer_node.inputs.get(NAME_OF_IMAGE_IO)

        self.connect_nodes_in_scene(scene, render_layers_output, composite_wrapper_node_input)
        self.connect_nodes_in_scene(scene, composite_wrapper_node_output, composite_node_input)
        self.connect_nodes_in_scene(scene, composite_wrapper_node_output, viewer_node_input)

    def connect_nodes_in_scene(self, scene, input, output):
        # This is very important! The links are at the scene.node_tree level
        # It makes sense after you spend some time thinking about it because you're linking the nodes in the scene.
        # I spent way too much time troubleshooting at the scene.node_tree.nodes level
        # At that point you're trying to link things inside nodes, which is wrong!
        scene_node_tree_links = get_node_tree(scene).links
        scene_node_tree_links.new(
            input, 
            output
        )

        input_node_name = input.node.node_tree.name_full if hasattr(input.node, 'node_tree') else input.node.name
        output_node_name = output.node.node_tree.name_full if hasattr(output.node, 'node_tree') else output.node.name

        self.logs += f"Connected '{input_node_name}' ({input.name}) to '{output_node_name}' ({output.name}) in scene: {scene.name}\n"

    def set_node_locations(self, scene):
        render_layers_node = find_builtin_node(get_node_tree(scene), 'CompositorNodeRLayers')
        composite_wrapper_node = get_node_tree(scene).nodes.get(NAME_OF_COMPOSITE_NODE)
        composite_node = find_builtin_node(get_node_tree(scene), get_output_node_type())
        viewer_node = find_builtin_node(get_node_tree(scene), NAME_OF_VIEWER_NODE_TYPE)

        render_layers_node.location = (-200, 400)
        composite_wrapper_node.location = (250, 400)
        composite_node.location = (500, 400)
        viewer_node.location = (500, 200)
        self.logs += f'Set default locations for nodes in Compositing\n'


class HYV_OT_HoyoversePostProcessingDefaultSettings(Operator, ImportHelper, CustomOperatorProperties, PostProcessingFeatureFlag):
    """Sets default settings when using Hoyoverse - Post Processing"""
    bl_idname = 'hoyoverse.post_processing_default_settings'
    bl_label = 'Hoyoverse: Post Processing - Default Settings'

    # ImportHelper mixin class uses this
    filename_ext = "*.*"

    def execute(self, context):
        if self.feature_disabled(context):
            if self.next_step_idx:
                NextStepInvoker().invoke(
                    self.next_step_idx, 
                    self.invoker_type, 
                    high_level_step_name=self.high_level_step_name,
                    game_type=self.game_type,
                )
            self.clear_custom_properties()
            return {'FINISHED'}

        tree = get_node_tree(bpy.context.scene)
        if hasattr(tree, "use_opencl"):
            tree.use_opencl = False
        if hasattr(tree, "use_two_pass"):
            tree.use_two_pass = True
        if hasattr(getattr(bpy.context.scene, "eevee", None), "use_bloom"):
            bpy.context.scene.eevee.use_bloom = False
        bpy.context.scene.render.film_transparent = False

        if self.next_step_idx:
            NextStepInvoker().invoke(
                self.next_step_idx, 
                self.invoker_type, 
                high_level_step_name=self.high_level_step_name,
                game_type=self.game_type,
            )
        self.report({'INFO'}, 'Applied HoYoverse post-processing default settings')
        self.clear_custom_properties()

        return {'FINISHED'}


GI_OT_CompositingNodeSetup = HYV_OT_CustomCompositeNodeSetup

