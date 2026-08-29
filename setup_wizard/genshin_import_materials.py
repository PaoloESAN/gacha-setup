# Author: michael-gh1

import bpy

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator

from setup_wizard.import_order import NextStepInvoker
from setup_wizard.material_import_setup.game_material_importers import GameMaterialImporterFactory
from setup_wizard.material_import_setup.material_importer_service import MaterialImporterService
from setup_wizard.setup_wizard_operator_base_classes import BasicSetupUIOperator, CustomOperatorProperties
from setup_wizard.utils.modifier_utils import set_modifier_property


class GI_OT_SetUpMaterials(Operator, BasicSetupUIOperator):
    '''Sets Up Materials'''
    bl_idname = 'genshin.set_up_materials'
    bl_label = 'Genshin: Set Up Materials (UI)'


class HSR_OT_SetUpMaterials(Operator, BasicSetupUIOperator):
    '''Sets Up Materials'''
    bl_idname = 'honkai_star_rail.set_up_materials'
    bl_label = 'Honkai Star Rail: Set Up Materials (UI)'


class ZZZ_OT_SetUpMaterials(Operator, BasicSetupUIOperator):
    '''Sets Up Materials'''
    bl_idname = 'zenless_zone_zero.set_up_materials'
    bl_label = 'Zenless Zone Zero: Set Up Materials (UI)'


class NTE_OT_SetUpMaterials(Operator, BasicSetupUIOperator):
    '''Sets Up Materials'''
    bl_idname = 'neverness_to_everness.set_up_materials'
    bl_label = 'Neverness to Everness: Set Up Materials (UI)'


class WW_OT_SetUpMaterials(Operator, BasicSetupUIOperator):
    '''Sets Up Materials'''
    bl_idname = 'wuthering_waves.set_up_materials'
    bl_label = 'Wuthering Waves: Set Up Materials (UI)'


def build_anisotropic_hair_spec_group():
    GROUP_NAME = "KK_Anisotropic_HairSpec"
    group = bpy.data.node_groups.get(GROUP_NAME)
    if group:
        return group

    tree = bpy.data.node_groups.new(GROUP_NAME, "ShaderNodeTree")

    def add_socket(t, name, socket_type, in_out="INPUT", default=None):
        if hasattr(t, "interface"):
            socket = t.interface.new_socket(name=name, in_out=in_out, socket_type=socket_type)
        else:
            collection = t.inputs if in_out == "INPUT" else t.outputs
            socket = collection.new(socket_type, name)
        if default is not None:
            try:
                socket.default_value = default
            except Exception:
                pass
        return socket

    def socket_by_name(sockets, name):
        if name in sockets:
            return sockets[name]
        for socket in sockets:
            if socket.name == name:
                return socket
        raise KeyError(name)

    def new_math(nodes, operation, label, x=0, y=0, clamp=False):
        node = nodes.new("ShaderNodeMath")
        node.operation = operation
        node.label = label
        node.location = (x, y)
        node.use_clamp = clamp
        return node

    def new_vec(nodes, operation, label, x=0, y=0):
        node = nodes.new("ShaderNodeVectorMath")
        node.operation = operation
        node.label = label
        node.location = (x, y)
        return node

    add_socket(tree, "BNormal", "NodeSocketVector", "INPUT", (0.0, 1.0, 0.0))
    add_socket(tree, "ViewDir V", "NodeSocketVector", "INPUT", (0.0, 0.0, 1.0))
    add_socket(tree, "LightDir L", "NodeSocketVector", "INPUT", (0.0, 0.0, 1.0))

    # Masks.
    add_socket(tree, "Hair M R Mask", "NodeSocketFloat", "INPUT", 1.0)
    add_socket(tree, "Hair M G Offset", "NodeSocketFloat", "INPUT", 0.5)
    add_socket(tree, "Aniso Map", "NodeSocketFloat", "INPUT", 1.0)

    # Mint hair defaults from the material JSON.
    add_socket(tree, "Spec Color", "NodeSocketColor", "INPUT", (0.097309, 0.225041, 0.234375, 1.0))
    add_socket(tree, "Spec Intensity", "NodeSocketFloat", "INPUT", 0.416)
    add_socket(tree, "Center Offset", "NodeSocketFloat", "INPUT", 0.466)
    add_socket(tree, "Offset 1", "NodeSocketFloat", "INPUT", 0.0)
    add_socket(tree, "Time", "NodeSocketFloat", "INPUT", 0.0)
    add_socket(tree, "Slide Speed", "NodeSocketFloat", "INPUT", 0.07)
    add_socket(tree, "D Max", "NodeSocketFloat", "INPUT", 14.360021)
    add_socket(tree, "D Min / Power", "NodeSocketFloat", "INPUT", 1.009032)
    add_socket(tree, "Stretch Contrast", "NodeSocketFloat", "INPUT", 0.728)
    add_socket(tree, "G Offset Scale", "NodeSocketFloat", "INPUT", 1.0)
    add_socket(tree, "G Offset Contrast", "NodeSocketFloat", "INPUT", 1.0)
    add_socket(tree, "Flip B", "NodeSocketFloat", "INPUT", 1.0)

    add_socket(tree, "Spec Factor", "NodeSocketFloat", "OUTPUT")
    add_socket(tree, "Spec Color Out", "NodeSocketColor", "OUTPUT")

    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    group_in = nodes.new("NodeGroupInput")
    group_in.location = (-1200, 0)
    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (1200, 0)

    b_flip = new_vec(nodes, "SCALE", "B * FlipB", -980, 260)
    b_norm = new_vec(nodes, "NORMALIZE", "normalize(B)", -780, 260)
    v_norm = new_vec(nodes, "NORMALIZE", "normalize(V)", -980, 40)
    l_norm = new_vec(nodes, "NORMALIZE", "normalize(L)", -980, -140)
    h_add = new_vec(nodes, "ADD", "L + V", -760, -60)
    h_norm = new_vec(nodes, "NORMALIZE", "MixV/H = normalize(L+V)", -540, -60)
    b_dot_h = new_vec(nodes, "DOT_PRODUCT", "dot(B, MixV)", -320, 120)

    links.new(socket_by_name(group_in.outputs, "BNormal"), b_flip.inputs[0])
    links.new(socket_by_name(group_in.outputs, "Flip B"), b_flip.inputs[3])
    links.new(b_flip.outputs[0], b_norm.inputs[0])
    links.new(socket_by_name(group_in.outputs, "ViewDir V"), v_norm.inputs[0])
    links.new(socket_by_name(group_in.outputs, "LightDir L"), l_norm.inputs[0])
    links.new(l_norm.outputs[0], h_add.inputs[0])
    links.new(v_norm.outputs[0], h_add.inputs[1])
    links.new(h_add.outputs[0], h_norm.inputs[0])
    links.new(b_norm.outputs[0], b_dot_h.inputs[0])
    links.new(h_norm.outputs[0], b_dot_h.inputs[1])

    dot_mul = new_math(nodes, "MULTIPLY", "dot * 0.5", -100, 140)
    dot_mul.inputs[1].default_value = 0.5
    dot_add = new_math(nodes, "ADD", "BdotMixV 0..1", 80, 140)
    dot_add.inputs[1].default_value = 0.5
    links.new(b_dot_h.outputs[1], dot_mul.inputs[0])
    links.new(dot_mul.outputs[0], dot_add.inputs[0])

    g_mul_scale = new_math(nodes, "MULTIPLY", "M.G * Scale", -100, 360)
    g_minus_half = new_math(nodes, "SUBTRACT", "G - 0.5", 80, 360)
    g_minus_half.inputs[1].default_value = 0.5
    g_mul_contrast = new_math(nodes, "MULTIPLY", "* G Contrast", 260, 360)
    g_times_two = new_math(nodes, "MULTIPLY", "* 2", 440, 360)
    g_times_two.inputs[1].default_value = 2.0
    bdot_with_g = new_math(nodes, "ADD", "Bdot + M.G Offset", 260, 160, clamp=True)
    links.new(socket_by_name(group_in.outputs, "Hair M G Offset"), g_mul_scale.inputs[0])
    links.new(socket_by_name(group_in.outputs, "G Offset Scale"), g_mul_scale.inputs[1])
    links.new(g_mul_scale.outputs[0], g_minus_half.inputs[0])
    links.new(g_minus_half.outputs[0], g_mul_contrast.inputs[0])
    links.new(socket_by_name(group_in.outputs, "G Offset Contrast"), g_mul_contrast.inputs[1])
    links.new(g_mul_contrast.outputs[0], g_times_two.inputs[0])
    links.new(dot_add.outputs[0], bdot_with_g.inputs[0])
    links.new(g_times_two.outputs[0], bdot_with_g.inputs[1])

    time_mul = new_math(nodes, "MULTIPLY", "Time * SlideSpeed", -320, -300)
    center_add_1 = new_math(nodes, "ADD", "Center + Offset1", -100, -260)
    center_add_2 = new_math(nodes, "ADD", "Center + Motion", 80, -220)
    links.new(socket_by_name(group_in.outputs, "Time"), time_mul.inputs[0])
    links.new(socket_by_name(group_in.outputs, "Slide Speed"), time_mul.inputs[1])
    links.new(socket_by_name(group_in.outputs, "Center Offset"), center_add_1.inputs[0])
    links.new(socket_by_name(group_in.outputs, "Offset 1"), center_add_1.inputs[1])
    links.new(center_add_1.outputs[0], center_add_2.inputs[0])
    links.new(time_mul.outputs[0], center_add_2.inputs[1])

    sub_center = new_math(nodes, "SUBTRACT", "Bdot - Center", 460, 80)
    abs_center = new_math(nodes, "ABSOLUTE", "abs()", 640, 80)
    mul_dmax = new_math(nodes, "MULTIPLY", "* DMax", 820, 80)
    one_minus = new_math(nodes, "SUBTRACT", "1 - x", 1000, 80, clamp=True)
    one_minus.inputs[0].default_value = 1.0
    links.new(bdot_with_g.outputs[0], sub_center.inputs[0])
    links.new(center_add_2.outputs[0], sub_center.inputs[1])
    links.new(sub_center.outputs[0], abs_center.inputs[0])
    links.new(abs_center.outputs[0], mul_dmax.inputs[0])
    links.new(socket_by_name(group_in.outputs, "D Max"), mul_dmax.inputs[1])
    links.new(mul_dmax.outputs[0], one_minus.inputs[1])

    power = new_math(nodes, "POWER", "pow(DMin)", 1000, 80, clamp=True)
    links.new(one_minus.outputs[0], power.inputs[0])
    links.new(socket_by_name(group_in.outputs, "D Min / Power"), power.inputs[1])

    one_minus_c = new_math(nodes, "SUBTRACT", "1 - Contrast", 640, -180)
    one_minus_c.inputs[0].default_value = 1.0
    smooth_sub = new_math(nodes, "SUBTRACT", "x - edge0", 820, -120)
    smooth_div = new_math(nodes, "DIVIDE", "/ Contrast", 1000, -120, clamp=True)
    t_sq = new_math(nodes, "MULTIPLY", "t * t", 1180, -120)
    two_t = new_math(nodes, "MULTIPLY", "2 * t", 1180, -280)
    two_t.inputs[0].default_value = 2.0
    three_minus = new_math(nodes, "SUBTRACT", "3 - 2t", 1360, -220)
    three_minus.inputs[0].default_value = 3.0
    smooth = new_math(nodes, "MULTIPLY", "smoothstep", 1540, -120)
    links.new(socket_by_name(group_in.outputs, "Stretch Contrast"), one_minus_c.inputs[1])
    links.new(power.outputs[0], smooth_sub.inputs[0])
    links.new(one_minus_c.outputs[0], smooth_sub.inputs[1])
    links.new(smooth_sub.outputs[0], smooth_div.inputs[0])
    links.new(socket_by_name(group_in.outputs, "Stretch Contrast"), smooth_div.inputs[1])
    links.new(smooth_div.outputs[0], t_sq.inputs[0])
    links.new(smooth_div.outputs[0], t_sq.inputs[1])
    links.new(smooth_div.outputs[0], two_t.inputs[1])
    links.new(two_t.outputs[0], three_minus.inputs[1])
    links.new(t_sq.outputs[0], smooth.inputs[0])
    links.new(three_minus.outputs[0], smooth.inputs[1])

    mask_mul = new_math(nodes, "MULTIPLY", "* Hair M R", 1720, -40)
    aniso_mul = new_math(nodes, "MULTIPLY", "* Aniso Map", 1880, -40)
    intensity_mul = new_math(nodes, "MULTIPLY", "* Intensity", 2040, -40)
    links.new(smooth.outputs[0], mask_mul.inputs[0])
    links.new(socket_by_name(group_in.outputs, "Hair M R Mask"), mask_mul.inputs[1])
    links.new(mask_mul.outputs[0], aniso_mul.inputs[0])
    links.new(socket_by_name(group_in.outputs, "Aniso Map"), aniso_mul.inputs[1])
    links.new(aniso_mul.outputs[0], intensity_mul.inputs[0])
    links.new(socket_by_name(group_in.outputs, "Spec Intensity"), intensity_mul.inputs[1])

    color_mul = new_vec(nodes, "SCALE", "SpecColor * Factor", 2220, 40)
    links.new(socket_by_name(group_in.outputs, "Spec Color"), color_mul.inputs[0])
    links.new(intensity_mul.outputs[0], color_mul.inputs[3])

    links.new(intensity_mul.outputs[0], socket_by_name(group_out.inputs, "Spec Factor"))
    links.new(color_mul.outputs[0], socket_by_name(group_out.inputs, "Spec Color Out"))

    return tree



def set_nte_gn_input(modifier, name_or_id_keywords, value):
    props = getattr(modifier, "properties", None)
    if not props:
        return False
    inputs = getattr(props, "inputs", None)
    if not inputs:
        return False

    kw_list = name_or_id_keywords if isinstance(name_or_id_keywords, list) else [name_or_id_keywords]

    # 1. Direct key match in dir(inputs)
    for kw in kw_list:
        if kw in dir(inputs):
            try:
                inputs[kw]['type'] = 'VALUE'
            except Exception:
                pass
            try:
                inputs[kw]['value'] = value
                return True
            except Exception:
                pass

    # 2. Interface item name matching to identifier in Blender 4.x
    if hasattr(modifier, "node_group") and modifier.node_group and hasattr(modifier.node_group, "interface"):
        for item in modifier.node_group.interface.items_tree:
            if getattr(item, "item_type", None) == 'SOCKET' and getattr(item, "in_out", None) == 'INPUT':
                item_name = getattr(item, "name", "")
                item_id = getattr(item, "identifier", "")
                if any(kw.lower() in item_name.lower() for kw in kw_list):
                    if item_id and item_id in dir(inputs):
                        try:
                            inputs[item_id]['type'] = 'VALUE'
                        except Exception:
                            pass
                        try:
                            inputs[item_id]['value'] = value
                            return True
                        except Exception:
                            pass

    return False


def copy_nte_modifiers_to_character_models():
    # 1. Get or create the 4 Light Vector empties
    rig_obj = None
    for o in bpy.data.objects:
        if o.type == 'ARMATURE' and "metarig" not in o.name.lower():
            rig_obj = o
            break

    head_matrix = None
    if rig_obj and hasattr(rig_obj, "pose"):
        head_bone = (
            rig_obj.pose.bones.get("head") or
            rig_obj.pose.bones.get("DEF-spine.006") or
            rig_obj.pose.bones.get("Bip001-Head")
        )
        if head_bone:
            head_matrix = rig_obj.matrix_world @ head_bone.matrix

    light_dir = bpy.data.objects.get("Light Direction")
    if not light_dir:
        light_dir = bpy.data.objects.new("Light Direction", None)
        light_dir.empty_display_type = 'SINGLE_ARROW'
        light_dir.location = (0, -2, 1.5)
        bpy.context.scene.collection.objects.link(light_dir)

    head_orig = bpy.data.objects.get("Head Origin")
    if not head_orig:
        head_orig = bpy.data.objects.new("Head Origin", None)
        head_orig.empty_display_type = 'PLAIN_AXES'
        if head_matrix:
            head_orig.location = head_matrix.translation
        else:
            head_orig.location = (0, 0, 1.5)
        bpy.context.scene.collection.objects.link(head_orig)

    head_fwd = bpy.data.objects.get("Head Forward")
    if not head_fwd:
        head_fwd = bpy.data.objects.new("Head Forward", None)
        head_fwd.empty_display_type = 'SINGLE_ARROW'
        if head_matrix:
            head_fwd.location = head_matrix.translation + head_matrix.to_3x3() @ bpy.mathutils.Vector((0, -0.2, 0))
        else:
            head_fwd.location = (0, -0.2, 1.5)
        bpy.context.scene.collection.objects.link(head_fwd)

    head_up = bpy.data.objects.get("Head Up")
    if not head_up:
        head_up = bpy.data.objects.new("Head Up", None)
        head_up.empty_display_type = 'SINGLE_ARROW'
        if head_matrix:
            head_up.location = head_matrix.translation + head_matrix.to_3x3() @ bpy.mathutils.Vector((0, 0, 0.2))
        else:
            head_up.location = (0, 0, 1.7)
        bpy.context.scene.collection.objects.link(head_up)

    # 2. Get mrim outline material
    mrim_mat = (
        bpy.data.materials.get("mrim") or
        bpy.data.materials.get("mrim.001") or
        next((m for m in bpy.data.materials if "mrim" in m.name.lower()), None)
    )

    # 3. Find node groups for Light Vectors and Outlines
    ng_light = next((ng for ng in bpy.data.node_groups if any(k in ng.name for k in ["Light Vectors", "灯光矢量"])), None)
    ng_outline = next((ng for ng in bpy.data.node_groups if any(k in ng.name for k in ["几何节点描边", "描边", "Outline", "Outlines"])), None)

    # Character mesh objects: all character meshes, excluding temp template/sphere meshes
    temp_mesh_names = ["球体", "sphere", "template", "shader"]
    char_meshes = [
        o for o in bpy.context.scene.objects
        if o.type == 'MESH' and not o.name.startswith("append_") and not any(t in o.name.lower() for t in temp_mesh_names)
    ]

    for mesh_obj in char_meshes:
        # Collect all existing Light Vectors and Outlines modifiers on this mesh
        light_mods = []
        outline_mods = []
        for m in list(mesh_obj.modifiers):
            if m.type == 'NODES':
                gname = m.node_group.name if m.node_group else ""
                if "Light Vectors" in m.name or "灯光矢量" in m.name or "Light Vectors" in gname or "灯光矢量" in gname:
                    light_mods.append(m)
                elif "描边" in m.name or "Outline" in m.name or "描边" in gname or "Outline" in gname:
                    outline_mods.append(m)

        # Ensure only 1 Light Vectors modifier remains
        if light_mods:
            mod_l = light_mods[0]
            # Remove duplicate copies (.001, etc.)
            for extra_m in light_mods[1:]:
                try:
                    mesh_obj.modifiers.remove(extra_m)
                except Exception:
                    pass
        elif ng_light:
            mod_l = mesh_obj.modifiers.new(name="Light Vectors - 灯光矢量", type='NODES')
            mod_l.node_group = ng_light
        else:
            mod_l = None

        # Configure Light Vectors modifier
        if mod_l:
            if not mod_l.node_group and ng_light:
                mod_l.node_group = ng_light
            mod_l.name = "Light Vectors - 灯光矢量"
            set_nte_gn_input(mod_l, ["Input_3", "光照方向", "Light Direction"], light_dir)
            set_nte_gn_input(mod_l, ["Input_4", "头部原点", "Head Origin"], head_orig)
            set_nte_gn_input(mod_l, ["Input_5", "头部前向", "Head Forward"], head_fwd)
            set_nte_gn_input(mod_l, ["Input_6", "头部上向", "Head Up"], head_up)
            for output_attr in ["FM", "FR", "LR"]:
                set_modifier_property(mod_l, output_attr, output_attr)
                set_modifier_property(mod_l, f"{output_attr}_attribute_name", output_attr)

        # Ensure only 1 Outline modifier remains
        if outline_mods:
            mod_o = outline_mods[0]
            # Remove duplicate copies (.001, etc.)
            for extra_m in outline_mods[1:]:
                try:
                    mesh_obj.modifiers.remove(extra_m)
                except Exception:
                    pass
        elif ng_outline:
            mod_o = mesh_obj.modifiers.new(name="几何节点描边", type='NODES')
            mod_o.node_group = ng_outline
        else:
            mod_o = None

        # Configure Outline modifier
        if mod_o:
            if not mod_o.node_group and ng_outline:
                mod_o.node_group = ng_outline
            mod_o.name = "几何节点描边"
            set_nte_gn_input(mod_o, ["Socket_2", "描边宽度", "Outline Width", "Width"], 0.0003)
            set_nte_gn_input(mod_o, ["Socket_3", "描边权重", "Weight"], 1.0)
            if mrim_mat:
                set_nte_gn_input(mod_o, ["Socket_6", "描边颜色", "Outline Material", "mrim"], mrim_mat)

    # Clean up any leftover template sphere objects
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and any(t in o.name.lower() for t in ["球体", "template"]):
            try:
                bpy.data.objects.remove(o, do_unlink=True)
            except Exception:
                pass





class NTE_OT_SetUpOutlines(Operator, BasicSetupUIOperator, CustomOperatorProperties):
    '''Setup Outlines, Hair Specular and Geometry Nodes modifiers for Neverness to Everness'''
    bl_idname = 'neverness_to_everness.set_up_outlines'
    bl_label = 'Neverness to Everness: Setup Outlines'

    def execute(self, context):
        group = build_anisotropic_hair_spec_group()
        ng_hair = bpy.data.node_groups.get('异环-头发')

        for mat in bpy.data.materials:
            if not mat.use_nodes or not mat.node_tree:
                continue
            matname = mat.name.lower()
            if any(k in matname for k in ["前发", "后发", "hair", "pelo"]):
                nodes = mat.node_tree.nodes
                links = mat.node_tree.links

                nte_hair_node = next((n for n in nodes if n.type == 'GROUP' and n.node_tree == ng_hair), None) if ng_hair else None

                aniso_node = next((n for n in nodes if n.type == 'GROUP' and n.node_tree == group), None)
                if not aniso_node:
                    aniso_node = nodes.new('ShaderNodeGroup')
                    aniso_node.node_tree = group
                if nte_hair_node:
                    aniso_node.location = (nte_hair_node.location.x + 300, nte_hair_node.location.y - 300)
                else:
                    aniso_node.location = (400, -200)

                # Geometry (Normal, ViewDir V)
                geom_node = next((n for n in nodes if n.type == 'NEW_GEOMETRY' or n.type == 'GEOMETRY'), None)
                if not geom_node:
                    try:
                        geom_node = nodes.new('ShaderNodeNewGeometry')
                        geom_node.location = (aniso_node.location.x - 400, aniso_node.location.y - 200)
                    except Exception:
                        geom_node = None

                if geom_node:
                    if 'BNormal' in aniso_node.inputs and not aniso_node.inputs['BNormal'].is_linked:
                        links.new(geom_node.outputs['Normal'], aniso_node.inputs['BNormal'])
                    if 'ViewDir V' in aniso_node.inputs and not aniso_node.inputs['ViewDir V'].is_linked:
                        links.new(geom_node.outputs['Incoming'], aniso_node.inputs['ViewDir V'])

                # Hair Mask Texture (Hair M R Mask & Hair M G Offset)
                mask_tex_node = next((n for n in nodes if n.type == 'TEX_IMAGE' and n.image and ('hair' in n.image.name.lower() or 'mask' in n.image.name.lower()) and ('_m' in n.image.name.lower() or 'm_' in n.image.name.lower())), None)
                if not mask_tex_node:
                    mask_tex_node = next((n for n in nodes if n.type == 'TEX_IMAGE' and n.image and '_m' in n.image.name.lower()), None)

                if mask_tex_node:
                    sep_color = next((n for n in nodes if n.type == 'SEPARATE_COLOR' or n.type == 'SEPRGB'), None)
                    if not sep_color:
                        try:
                            sep_color = nodes.new('ShaderNodeSeparateColor')
                        except Exception:
                            sep_color = nodes.new('ShaderNodeSeparateRGB')
                        sep_color.location = (mask_tex_node.location.x + 250, mask_tex_node.location.y - 100)
                        links.new(mask_tex_node.outputs['Color'], sep_color.inputs[0])

                    r_out = sep_color.outputs[0]
                    g_out = sep_color.outputs[1]

                    if 'Hair M R Mask' in aniso_node.inputs and not aniso_node.inputs['Hair M R Mask'].is_linked:
                        links.new(r_out, aniso_node.inputs['Hair M R Mask'])
                    if 'Hair M G Offset' in aniso_node.inputs and not aniso_node.inputs['Hair M G Offset'].is_linked:
                        links.new(g_out, aniso_node.inputs['Hair M G Offset'])

                # Connect Spec Color Out -> 特效... or Mix (ADD) Color + Spec Color Out
                out_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
                connected_to_effect = False

                if nte_hair_node:
                    eff_in = nte_hair_node.inputs.get('特效...') or nte_hair_node.inputs.get('特效') or nte_hair_node.inputs.get('高光')
                    if eff_in and not eff_in.is_linked:
                        links.new(aniso_node.outputs['Spec Color Out'], eff_in)
                        connected_to_effect = True

                if not connected_to_effect and nte_hair_node and out_node:
                    mix_node = next((n for n in nodes if n.name == 'Hair_Spec_Mix_Add'), None)
                    if not mix_node:
                        try:
                            mix_node = nodes.new('ShaderNodeMixRGB')
                            mix_node.blend_type = 'ADD'
                            mix_node.name = 'Hair_Spec_Mix_Add'
                            mix_node.inputs['Fac'].default_value = 1.0
                            mix_node.location = (nte_hair_node.location.x + 250, nte_hair_node.location.y)

                            links.new(nte_hair_node.outputs['Color'], mix_node.inputs[1])
                            links.new(aniso_node.outputs['Spec Color Out'], mix_node.inputs[2])
                            links.new(mix_node.outputs['Color'], out_node.inputs['Surface'])
                        except Exception:
                            pass

        # Copy Geometry Nodes modifiers from shader/template object onto character meshes
        copy_nte_modifiers_to_character_models()

        try:
            from setup_wizard.replace_default_materials_setup.game_default_material_replacers import ensure_hair_white_texture
            from setup_wizard.utils.active_character_directory_store import get_active_character_directory
            folder = get_active_character_directory() or context.scene.get("setup_wizard_imported_model_dir")
            ensure_hair_white_texture(folder)
        except Exception as ex:
            print(f"[NTE Setup Outlines] Notice ensuring hair white texture: {ex}")

        self.report({'INFO'}, 'Setup Outlines completed: Hair Specular & Geometry Nodes modifiers assigned.')

        next_step = getattr(self, 'next_step_idx', 0)
        if next_step:
            NextStepInvoker().invoke(
                next_step, 
                getattr(self, 'invoker_type', 'invoke_next_step_ui'),
                high_level_step_name=getattr(self, 'high_level_step_name', ''),
                game_type=getattr(self, 'game_type', 'NEVERNESS_TO_EVERNESS'),
            )

        return {'FINISHED'}


class NTE_OT_SetUpHairSpecular(Operator, BasicSetupUIOperator, CustomOperatorProperties):
    '''Legacy alias for Setup Outlines'''
    bl_idname = 'neverness_to_everness.set_up_hair_specular'
    bl_label = 'Neverness to Everness: Setup Outlines (Hair Specular)'

    def execute(self, context):
        return bpy.ops.neverness_to_everness.set_up_outlines(
            'EXEC_DEFAULT',
            next_step_idx=getattr(self, 'next_step_idx', 0),
            invoker_type=getattr(self, 'invoker_type', 'invoke_next_step_ui'),
            high_level_step_name=getattr(self, 'high_level_step_name', ''),
            game_type=getattr(self, 'game_type', 'NEVERNESS_TO_EVERNESS'),
        )






class GI_OT_GenshinImportMaterials(Operator, ImportHelper, CustomOperatorProperties):
    """Select the .blend file with Shader materials to import"""
    bl_idname = "genshin.import_materials"  # important since its how we chain file dialogs
    bl_label = "Select Shader .blend File"

    # ImportHelper mixin class uses this
    filename_ext = "*.*"

    import_path: StringProperty(
        name="Path",
        description="Festivity's Shader .blend File",
        default="",
        subtype='DIR_PATH'
    )

    filter_glob: StringProperty(
        default="*.*",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def invoke(self, context, event):
        print(f"[DEBUG] GI_OT_GenshinImportMaterials.invoke called: game_type='{self.game_type}', filepath='{self.filepath}'")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        print(f"[DEBUG] GI_OT_GenshinImportMaterials.execute called: game_type='{self.game_type}', filepath='{self.filepath}'")
        try:
            game_material_importer = GameMaterialImporterFactory.create(self.game_type, self, context)
            print(f"[DEBUG] GameMaterialImporter created: {game_material_importer}")

            material_importer_service = MaterialImporterService(game_material_importer)
            material_importer_service.import_materials()
        except Exception as ex:
            print(f"[DEBUG ERROR] Exception in GI_OT_GenshinImportMaterials.execute: {ex}")
            raise ex
        finally:
            super().clear_custom_properties()
        return {'FINISHED'}



register, unregister = bpy.utils.register_classes_factory([
    GI_OT_GenshinImportMaterials,
    GI_OT_SetUpMaterials,
    HSR_OT_SetUpMaterials,
    ZZZ_OT_SetUpMaterials,
    NTE_OT_SetUpMaterials,
    NTE_OT_SetUpHairSpecular,
    WW_OT_SetUpMaterials,
])


