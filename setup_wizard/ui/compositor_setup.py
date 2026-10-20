"""Compositor-only setup, using each game's existing post-processing workflow."""
import bpy
from bpy.props import EnumProperty
from bpy.types import Operator, Panel

from setup_wizard.domain.game_types import GameType


HYV_GAMES = {
    'GENSHIN_IMPACT', 'HONKAI_STAR_RAIL', 'HONKAI_IMPACT_3RD', 'HONKAI_NEXUS_ANIMA',
}
COMPOSITOR_OPERATORS = {
    **{game: 'hoyoverse.custom_composite_node_setup' for game in HYV_GAMES},
    'NEVERNESS_TO_EVERNESS': 'neverness_to_everness.setup_compositor_nodes',
    'WUTHERING_WAVES': 'wuthering_waves.setup_compositor_nodes',
    'ARKNIGHTS_ENDFIELD': 'arknights_endfield.setup_compositor_nodes',
    'PUNISHING_GRAY_RAVEN': 'punishing_gray_raven.setup_compositor',
}
REFLECTION_GAMES = {
    'HONKAI_STAR_RAIL', 'HONKAI_NEXUS_ANIMA', 'NEVERNESS_TO_EVERNESS',
    'WUTHERING_WAVES', 'ARKNIGHTS_ENDFIELD',
}


def call_compositor_operator(identifier, game):
    namespace, name = identifier.split('.')
    return getattr(getattr(bpy.ops, namespace), name)(
        'EXEC_DEFAULT', game_type=game, next_step_idx=0,
        invoker_type='', high_level_step_name='',
    )


def setup_nodes(context, game):
    context.scene.render.use_compositing = True
    if game == 'ZENLESS_ZONE_ZERO':
        from setup_wizard.services.zzz_bloom_service import setup_zzz_bloom
        setup_zzz_bloom(context.scene)
        return {'FINISHED'}
    return call_compositor_operator(COMPOSITOR_OPERATORS[game], game)


def setup_color(context, game):
    scene = context.scene
    if game in {'WUTHERING_WAVES', 'ARKNIGHTS_ENDFIELD'}:
        scene.display_settings.display_device = 'sRGB'
    if game == 'ARKNIGHTS_ENDFIELD':
        # Match Endfield's normal Finish Setup preset.
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.look = 'AgX - Medium High Contrast'
        return {'FINISHED'}
    return call_compositor_operator('genshin.set_color_management_to_standard', game)


def setup_render_settings(context, game):
    if game in REFLECTION_GAMES:
        result = call_compositor_operator('hoyoverse.set_up_screen_space_reflections', game)
        if 'FINISHED' not in result:
            return result
        eevee = getattr(context.scene, 'eevee', None)
        if hasattr(eevee, 'use_shadows'):
            eevee.use_shadows = True
    return {'FINISHED'}


def setup_defaults(context, game):
    scene = context.scene
    scene.render.use_compositing = True
    if game == 'ZENLESS_ZONE_ZERO':
        from setup_wizard.services.zzz_bloom_service import setup_zzz_bloom
        setup_zzz_bloom(scene)
    elif game in HYV_GAMES:
        return call_compositor_operator('hoyoverse.post_processing_default_settings', game)
    elif game == 'NEVERNESS_TO_EVERNESS':
        from setup_wizard.genshin_compositing_node_setup import get_node_tree
        scene.render.film_transparent = False
        tree = get_node_tree(scene)
        if hasattr(tree, 'use_two_pass'):
            tree.use_two_pass = True
    # WuWa / AKE apply their post-processing preset when creating the nodes.
    # PGR only requires the render output; it has no HYV post-processing preset.
    return {'FINISHED'}


class GACHA_OT_RunCompositing(Operator):
    """Configure only the selected game's compositor and post-processing settings"""
    bl_idname = 'gacha.run_compositing'
    bl_label = 'Run Compositing'
    bl_options = {'REGISTER', 'UNDO'}

    step: EnumProperty(items=[
        ('ALL', 'All', 'Set up color management, render settings, compositor and post-processing defaults'),
        ('COLOR', 'Color Management', 'Apply the selected game\'s color management preset'),
        ('STANDARD', 'Standard', 'Set color management to Standard'),
        ('RENDER', 'Render Settings', 'Enable screen-space reflections / ray tracing and shadows where supported'),
        ('NODES', 'Nodes', 'Set up compositor nodes only'),
        ('DEFAULTS', 'Defaults', 'Apply post-processing defaults only'),
    ], default='ALL', options={'HIDDEN'})

    def execute(self, context):
        game = getattr(context.scene, 'game_type_dropdown', GameType.GENSHIN_IMPACT.name)
        if game not in COMPOSITOR_OPERATORS and game != 'ZENLESS_ZONE_ZERO':
            self.report({'ERROR'}, 'Unsupported compositor game')
            return {'CANCELLED'}
        try:
            if self.step in {'ALL', 'COLOR'}:
                if 'FINISHED' not in setup_color(context, game):
                    return {'CANCELLED'}
            if self.step == 'STANDARD':
                return call_compositor_operator('genshin.set_color_management_to_standard', game)
            if self.step in {'ALL', 'RENDER'}:
                if 'FINISHED' not in setup_render_settings(context, game):
                    return {'CANCELLED'}
            if self.step in {'ALL', 'NODES'}:
                if 'FINISHED' not in setup_nodes(context, game):
                    return {'CANCELLED'}
            if self.step in {'ALL', 'DEFAULTS'}:
                if 'FINISHED' not in setup_defaults(context, game):
                    return {'CANCELLED'}
        except Exception as exc:
            self.report({'ERROR'}, f'Compositor setup failed: {exc}')
            return {'CANCELLED'}
        self.report({'INFO'}, 'Compositor setup completed')
        return {'FINISHED'}


class CompositorPanel:
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Gacha Setup Compositor'

    @classmethod
    def poll(cls, context):
        return getattr(context.space_data, 'tree_type', '') == 'CompositorNodeTree'


class GACHA_PT_CompositorSetup(CompositorPanel, Panel):
    bl_label = 'Compositing Setup Wizard'
    bl_idname = 'GACHA_PT_CompositorSetup'
    bl_order = 0

    def draw(self, context):
        game = context.scene.game_type_dropdown
        label = context.scene.bl_rna.properties['game_type_dropdown'].enum_items[game].name
        self.layout.row(align=True).menu('CSW_MT_game_selector_menu', text=f'Game:  {label}')
        row = self.layout.row()
        row.scale_y = 1.4
        row.operator('gacha.run_compositing', text='Run Compositing', icon='PLAY').step = 'ALL'


class GACHA_PT_CompositorBasicSetup(CompositorPanel, Panel):
    bl_label = 'Basic Setup'
    bl_idname = 'GACHA_PT_CompositorBasicSetup'
    bl_order = 1
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        game = context.scene.game_type_dropdown
        col = self.layout.column(align=True)
        color_text = ('Set Color Management to AgX' if game == 'ARKNIGHTS_ENDFIELD'
                      else 'Set Color Management to Standard')
        col.operator('gacha.run_compositing', text=color_text, icon='COLOR').step = 'COLOR'
        if game == 'ARKNIGHTS_ENDFIELD':
            col.operator('gacha.run_compositing', text='Set Color Management to Standard',
                         icon='COLOR').step = 'STANDARD'
        if game in REFLECTION_GAMES:
            col.operator('gacha.run_compositing', text='Enable SSR / Ray Tracing & Shadows',
                         icon='SCENE').step = 'RENDER'
        col.operator('gacha.run_compositing', text='Set Up Compositing Nodes',
                     icon='NODE_COMPOSITING').step = 'NODES'
        if game in HYV_GAMES:
            text = 'Set HYV-PP Defaults'
        elif game == 'ZENLESS_ZONE_ZERO':
            text = 'Set Bloom Defaults'
        elif game == 'NEVERNESS_TO_EVERNESS':
            text = 'Set Post-Processing Defaults'
        else:
            self.layout.label(text='Defaults included in compositor setup', icon='INFO')
            return
        col.operator('gacha.run_compositing', text=text, icon='FILE_REFRESH').step = 'DEFAULTS'
