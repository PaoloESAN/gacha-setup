# Based on Blender-WuWa-Character-Setup by @fnoji (https://github.com/fnoji/Blender-WuWa-Character-Setup)
# Gustling Waters integration by @nytsjared (https://github.com/nytsjared)
# Adapted for Gacha Setup by PaoloESAN
# Licensed under GPL-3.0-or-later

import bpy
import os
import re
from bpy.types import Operator, Panel
from bpy.props import (
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)


def get_global_material_properties_group():
    return bpy.data.node_groups.get("Global Material Properties Main")


def update_material_property(node_group_name, input_name, value):
    group = bpy.data.node_groups.get(node_group_name)
    if group:
        if hasattr(group, "inputs") and input_name in group.inputs:
            group.inputs[input_name].default_value = value
        elif hasattr(group, "interface"):
            # Blender 4.0+ / 5.2 interface check
            for item in group.interface.items_tree:
                if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.name == input_name:
                    if hasattr(group, "nodes"):
                        for node in group.nodes:
                            if node.type == 'GROUP_INPUT' and input_name in node.outputs:
                                node.outputs[input_name].default_value = value
                                return
        # Fallback search in all nodes
        for node in getattr(group, "nodes", []):
            if node.type == 'GROUP_INPUT' and input_name in node.outputs:
                try:
                    node.outputs[input_name].default_value = value
                except Exception:
                    pass


# Appearance Property Update Callbacks
def update_blush(self, context):
    group = get_global_material_properties_group()
    if group and "Blush Multiplier" in group.nodes.get("Group Input", group).outputs:
        try:
            group.nodes["Group Input"].outputs["Blush Multiplier"].default_value = self.ww_blush_value
        except Exception:
            pass


def update_disgust(self, context):
    group = get_global_material_properties_group()
    if group and "Disgust Multiplier" in group.nodes.get("Group Input", group).outputs:
        try:
            group.nodes["Group Input"].outputs["Disgust Multiplier"].default_value = self.ww_disgust_value
        except Exception:
            pass


def update_metallic(self, context):
    group = get_global_material_properties_group()
    if group and "Metallic Multiplier" in group.nodes.get("Group Input", group).outputs:
        try:
            group.nodes["Group Input"].outputs["Metallic Multiplier"].default_value = self.ww_metallic_value
        except Exception:
            pass


def update_specular(self, context):
    group = get_global_material_properties_group()
    if group and "Specular Multiplier" in group.nodes.get("Group Input", group).outputs:
        try:
            group.nodes["Group Input"].outputs["Specular Multiplier"].default_value = self.ww_specular_value
        except Exception:
            pass


def update_custom_colors(self, context):
    palette = bpy.data.node_groups.get("Color Palette")
    if palette:
        try:
            inp = palette.nodes.get("Group Input")
            if inp:
                if "Amb Color" in inp.outputs:
                    inp.outputs["Amb Color"].default_value = (*self.ww_amb_color, 1.0)
                if "Light Color" in inp.outputs:
                    inp.outputs["Light Color"].default_value = (*self.ww_light_color, 1.0)
                if "Shadow Color" in inp.outputs:
                    inp.outputs["Shadow Color"].default_value = (*self.ww_shadow_color, 1.0)
                if "Rim Color" in inp.outputs:
                    inp.outputs["Rim Color"].default_value = (*self.ww_rim_color, 1.0)
        except Exception as e:
            print(f"Notice updating color palette: {e}")


def update_shadow_range(self, context):
    group = get_global_material_properties_group()
    if group:
        try:
            inp = group.nodes.get("Group Input")
            if inp and "Shadow Transition Range" in inp.outputs:
                inp.outputs["Shadow Transition Range"].default_value = self.ww_shadow_transition_range_value
        except Exception:
            pass


def update_face_shadow_softness(self, context):
    group = get_global_material_properties_group()
    if group:
        try:
            inp = group.nodes.get("Group Input")
            if inp and "Face Shadow Softness" in inp.outputs:
                inp.outputs["Face Shadow Softness"].default_value = self.ww_face_shadow_softness_value
        except Exception:
            pass


def update_catch_shadows(self, context):
    group = get_global_material_properties_group()
    if group:
        try:
            inp = group.nodes.get("Group Input")
            if inp and "Catch Shadows" in inp.outputs:
                inp.outputs["Catch Shadows"].default_value = 1.0 if self.ww_catch_shadows else 0.0
        except Exception:
            pass


def update_light_mode(self, context):
    group = get_global_material_properties_group()
    if group:
        try:
            inp = group.nodes.get("Group Input")
            if inp and "Light Mode" in inp.outputs:
                inp.outputs["Light Mode"].default_value = float(self.ww_light_mode)
        except Exception:
            pass


# Animate Mode: Swapping materials for low-poly/simplified fast viewport playback
ANIMATE_MODE_SUFFIX = "_Low"

def set_animate_mode(enable: bool):
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        for slot in obj.material_slots:
            mat = slot.material
            if not mat:
                continue

            if enable:
                if mat.name.endswith(ANIMATE_MODE_SUFFIX):
                    continue
                low_name = mat.name + ANIMATE_MODE_SUFFIX
                low_mat = bpy.data.materials.get(low_name)
                if not low_mat:
                    low_mat = bpy.data.materials.new(name=low_name)
                    low_mat.use_nodes = True
                    bsdf = low_mat.node_tree.nodes.get("Principled BSDF")

                    # Find diffuse image from original material
                    diff_img = None
                    if mat.use_nodes and mat.node_tree:
                        for node in mat.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image:
                                if any(k in node.image.name.lower() for k in ['_d.', '_d_', 'diff', 'basecolor']):
                                    diff_img = node.image
                                    break
                        if not diff_img:
                            for node in mat.node_tree.nodes:
                                if node.type == 'TEX_IMAGE' and node.image:
                                    diff_img = node.image
                                    break

                    if bsdf and diff_img:
                        tex_node = low_mat.node_tree.nodes.new("ShaderNodeTexImage")
                        tex_node.image = diff_img
                        low_mat.node_tree.links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
                        if "Roughness" in bsdf.inputs:
                            bsdf.inputs["Roughness"].default_value = 1.0

                slot.material = low_mat
            else:
                if mat.name.endswith(ANIMATE_MODE_SUFFIX):
                    orig_name = mat.name[:-len(ANIMATE_MODE_SUFFIX)]
                    orig_mat = bpy.data.materials.get(orig_name)
                    if orig_mat:
                        slot.material = orig_mat


# Operators
class WW_OT_ToggleAnimateMode(Operator):
    bl_idname = "wuthering_waves.toggle_animate_mode"
    bl_label = "Toggle Animate Mode"
    bl_description = "Switch between full shaders and lightweight materials for smooth animation playback"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        current = context.scene.get("ww_animate_mode", False)
        new_val = not current
        context.scene["ww_animate_mode"] = new_val
        set_animate_mode(new_val)
        status = "Enabled (Fast Playback)" if new_val else "Disabled (Full Shaders)"
        self.report({'INFO'}, f"Animate Mode {status}")
        return {'FINISHED'}


class WW_OT_ToggleOutlines(Operator):
    bl_idname = "wuthering_waves.toggle_outlines"
    bl_label = "Toggle Outlines"
    bl_description = "Toggle viewport visibility for Wuthering Waves outline modifiers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        hidden_any = False
        found_any = False
        helper_names = ['wgt', 'rootshape', 'isaacfacerig', 'lightingpanel', 'head origin', 'head forward', 'head up', 'light direction', 'eye highlight', 'sun', 'cube']

        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                name_low = obj.name.lower()
                # Skip Rigify bone custom shapes and helper widgets
                if name_low.startswith('wgt-') or any(h in name_low for h in helper_names):
                    continue
                if any(c.name.startswith("WGTS") or c.name.lower() == "wgt" for c in obj.users_collection):
                    continue

                for mod in obj.modifiers:
                    if "outline" in mod.name.lower() or "ww - outlines" in mod.name.lower():
                        found_any = True
                        mod.show_viewport = not mod.show_viewport
                        hidden_any = not mod.show_viewport

        # Ensure all rigs maintain in-front display so controls are never occluded
        for obj in context.scene.objects:
            if obj.type == 'ARMATURE' and (obj.name.startswith("RIG-") or "rig" in obj.name.lower()):
                obj.show_in_front = True
                if hasattr(obj, "data") and obj.data:
                    obj.data.show_bone_custom_shapes = True

        if not found_any:
            self.report({'WARNING'}, "No Outline modifiers found on scene meshes.")
            return {'FINISHED'}

        state = "Hidden" if hidden_any else "Visible"
        self.report({'INFO'}, f"Outlines are now {state}.")
        return {'FINISHED'}


class WW_OT_ToggleHairTrans(Operator):
    bl_idname = "wuthering_waves.toggle_hair_transparency"
    bl_label = "Toggle Hair Transparency"
    bl_description = "Toggle see-through / transparency effect on hair materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        toggled = False
        for mat in bpy.data.materials:
            if mat.use_nodes and mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type == 'GROUP' and node.node_tree and "see through" in node.node_tree.name.lower():
                        node.mute = not node.mute
                        toggled = True

        for obj in bpy.data.objects:
            if "_seethru" in obj.name.lower():
                obj.hide_viewport = not obj.hide_viewport
                toggled = True

        if toggled:
            self.report({'INFO'}, "Toggled Hair Transparency.")
        else:
            self.report({'WARNING'}, "No Hair Transparency / See Through nodes found.")
        return {'FINISHED'}


class WW_OT_ToggleStarMotion(Operator):
    bl_idname = "wuthering_waves.toggle_star_motion"
    bl_label = "Toggle Resonator Star Motion"
    bl_description = "Toggle Resonator Star animation modifier / node"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        toggled = False
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                for mod in obj.modifiers:
                    if "resonatorstar" in mod.name.lower() or "star move" in mod.name.lower():
                        mod.show_viewport = not mod.show_viewport
                        toggled = True

        for mat in bpy.data.materials:
            if mat.use_nodes and mat.node_tree and "resonatorstar" in mat.name.lower():
                for node in mat.node_tree.nodes:
                    if "Moving" in node.inputs:
                        cur = node.inputs["Moving"].default_value
                        node.inputs["Moving"].default_value = 0.0 if cur > 0.5 else 1.0
                        toggled = True

        if toggled:
            self.report({'INFO'}, "Toggled Resonator Star Motion.")
        else:
            self.report({'WARNING'}, "No Resonator Star modifiers or materials found.")
        return {'FINISHED'}


class WW_OT_FixEyeUV(Operator):
    bl_idname = "wuthering_waves.fix_eye_uv"
    bl_label = "Fix Eye UV"
    bl_description = "Ensure Eye materials use UV2 / correct UV Map channel"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        count = 0
        for mat in bpy.data.materials:
            if not mat.use_nodes or not mat.node_tree:
                continue
            if "eye" in mat.name.lower() or "ww - eye" in mat.name.lower():
                for node in mat.node_tree.nodes:
                    if node.type == 'UVMAP':
                        node.uv_map = "UV2"
                        count += 1
                    elif node.type == 'GROUP' and node.node_tree and "eye depth" in node.node_tree.name.lower():
                        for subnode in node.node_tree.nodes:
                            if subnode.type == 'UVMAP':
                                subnode.uv_map = "UV2"
                                count += 1

        self.report({'INFO'}, f"Fixed Eye UV to UV2 on {count} nodes.")
        return {'FINISHED'}


class WW_OT_SeparateMesh(Operator):
    bl_idname = "wuthering_waves.separate_mesh"
    bl_label = "Separate Mesh by Vertex Groups"
    bl_description = "Separates character mesh into Hair, Cloth (Piao), Skirt, and Body meshes"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        mesh_obj = context.active_object
        if not mesh_obj or mesh_obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a Mesh.")
            return {'CANCELLED'}

        # Groups to separate
        group_categories = [
            ("Hair", ["Hair", "hair", "TouFa", "前发", "后发"]),
            ("Cloth", ["Piao", "piao", "Cloth", "cloth", "Sleeve", "Ribbon"]),
            ("Skirt", ["Skirt", "skirt", "Trousers", "trousers", "QunZi"]),
        ]

        bpy.ops.object.mode_set(mode='OBJECT')
        initial_name = mesh_obj.name

        separated_objs = []
        for cat_name, keywords in group_categories:
            matching_groups = [
                g.name for g in mesh_obj.vertex_groups
                if any(kw.lower() in g.name.lower() for kw in keywords)
            ]
            if not matching_groups:
                continue

            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')

            for g_name in matching_groups:
                g = mesh_obj.vertex_groups[g_name]
                for v in mesh_obj.data.vertices:
                    for vg in v.groups:
                        if vg.group == g.index and vg.weight > 0.01:
                            v.select = True

            bpy.ops.object.mode_set(mode='EDIT')
            try:
                bpy.ops.mesh.separate(type='SELECTED')
                bpy.ops.object.mode_set(mode='OBJECT')
                for o in context.selected_objects:
                    if o != mesh_obj and o not in separated_objs:
                        o.name = f"{initial_name}_{cat_name}"
                        separated_objs.append(o)
            except Exception as e:
                bpy.ops.object.mode_set(mode='OBJECT')
                print(f"Notice separating {cat_name}: {e}")

        self.report({'INFO'}, f"Separated mesh into {len(separated_objs) + 1} parts.")
        return {'FINISHED'}


class WW_OT_SetPerformanceMode(Operator):
    bl_idname = "wuthering_waves.set_performance_mode"
    bl_label = "Performance Mode"
    bl_description = "Optimize viewport settings for smooth viewport animation performance"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        if hasattr(scene, "eevee"):
            if hasattr(scene.eevee, "taa_samples"):
                scene.eevee.taa_samples = 1
            if hasattr(scene.eevee, "taa_render_samples"):
                scene.eevee.taa_render_samples = 16
            if hasattr(scene.eevee, "use_ssr"):
                scene.eevee.use_ssr = False
            if hasattr(scene.eevee, "use_gtao"):
                scene.eevee.use_gtao = False
            if hasattr(scene.eevee, "use_shadows"):
                scene.eevee.use_shadows = False

        self.report({'INFO'}, "Performance Viewport Mode Enabled.")
        return {'FINISHED'}


class WW_OT_SetQualityMode(Operator):
    bl_idname = "wuthering_waves.set_quality_mode"
    bl_label = "Quality Mode"
    bl_description = "Configure high quality viewport shading and render settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        if hasattr(scene, "eevee"):
            if hasattr(scene.eevee, "taa_samples"):
                scene.eevee.taa_samples = 64
            if hasattr(scene.eevee, "taa_render_samples"):
                scene.eevee.taa_render_samples = 128
            if hasattr(scene.eevee, "use_ssr"):
                scene.eevee.use_ssr = True
            if hasattr(scene.eevee, "use_gtao"):
                scene.eevee.use_gtao = True
            if hasattr(scene.eevee, "use_shadows"):
                scene.eevee.use_shadows = True

        scene.display_settings.display_device = 'sRGB'
        scene.view_settings.view_transform = 'Standard'

        self.report({'INFO'}, "Quality Viewport Mode Enabled.")
        return {'FINISHED'}


def register_wuwa_properties():
    bpy.types.Scene.ww_tex_mode = EnumProperty(
        name="Texture Mode",
        description="Texture assignment mode for Wuthering Waves",
        items=[
            ("Default", "Default", "Default texture matching"),
            ("Version", "Version", "Version-based texture matching"),
        ],
        default="Default",
    )

    bpy.types.Scene.ww_light_mode = EnumProperty(
        name="Light Mode",
        description="Lighting preset mode for Gustling Waters shader",
        items=[
            ("0", "Default", "Default Game Lighting"),
            ("1", "Sunrise", "Sunrise Tone"),
            ("2", "Day", "Bright Daylight"),
            ("3", "Sunset", "Warm Sunset"),
            ("4", "Night", "Cool Night"),
            ("5", "Rainy", "Overcast / Rainy"),
            ("6", "Custom", "Custom User Colors"),
        ],
        default="0",
        update=update_light_mode,
    )

    bpy.types.Scene.ww_blush_value = FloatProperty(
        name="Blush",
        description="Face blush intensity",
        min=0.0,
        max=2.0,
        default=0.0,
        update=update_blush,
    )

    bpy.types.Scene.ww_disgust_value = FloatProperty(
        name="Disgust",
        description="Face disgust shadow intensity",
        min=0.0,
        max=2.0,
        default=0.0,
        update=update_disgust,
    )

    bpy.types.Scene.ww_metallic_value = FloatProperty(
        name="Metallic Multiplier",
        description="Metallic reflections intensity",
        min=0.0,
        max=2.0,
        default=1.0,
        update=update_metallic,
    )

    bpy.types.Scene.ww_specular_value = FloatProperty(
        name="Specular Multiplier",
        description="Specular highlight multiplier",
        min=0.0,
        max=2.0,
        default=1.0,
        update=update_specular,
    )

    bpy.types.Scene.ww_amb_color = FloatVectorProperty(
        name="Ambient Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(0.5, 0.5, 0.5),
        update=update_custom_colors,
    )

    bpy.types.Scene.ww_light_color = FloatVectorProperty(
        name="Light Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_custom_colors,
    )

    bpy.types.Scene.ww_shadow_color = FloatVectorProperty(
        name="Shadow Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(0.3, 0.3, 0.4),
        update=update_custom_colors,
    )

    bpy.types.Scene.ww_rim_color = FloatVectorProperty(
        name="Rim Color",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_custom_colors,
    )

    bpy.types.Scene.ww_shadow_transition_range_value = FloatProperty(
        name="Shadow Transition Range",
        description="Softness range of shadow transitions",
        min=0.0,
        max=1.0,
        default=0.05,
        update=update_shadow_range,
    )

    bpy.types.Scene.ww_face_shadow_softness_value = FloatProperty(
        name="Face Shadow Softness",
        description="Face shadow boundary softness",
        min=0.0,
        max=1.0,
        default=0.05,
        update=update_face_shadow_softness,
    )

    bpy.types.Scene.ww_catch_shadows = BoolProperty(
        name="Catch Shadows",
        description="Enable shadow receiving on character",
        default=True,
        update=update_catch_shadows,
    )


classes = (
    WW_OT_ToggleAnimateMode,
    WW_OT_ToggleOutlines,
    WW_OT_ToggleHairTrans,
    WW_OT_ToggleStarMotion,
    WW_OT_FixEyeUV,
    WW_OT_SeparateMesh,
    WW_OT_SetPerformanceMode,
    WW_OT_SetQualityMode,
)


def register():
    register_wuwa_properties()
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
