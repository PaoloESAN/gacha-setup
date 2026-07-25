# Author: michael-gh1

import bpy

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator

from setup_wizard.material_import_setup.game_material_importers import GameMaterialImporterFactory
from setup_wizard.material_import_setup.material_importer_service import MaterialImporterService
from setup_wizard.setup_wizard_operator_base_classes import BasicSetupUIOperator, CustomOperatorProperties


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
    add_socket(tree, "Hair M R Mask", "NodeSocketFloat", "INPUT", 1.0)
    add_socket(tree, "Aniso Map", "NodeSocketFloat", "INPUT", 1.0)
    add_socket(tree, "Spec Color", "NodeSocketColor", "INPUT", (0.097309, 0.225041, 0.234375, 1.0))
    add_socket(tree, "Spec Intensity", "NodeSocketFloat", "INPUT", 0.416)
    add_socket(tree, "Center Offset", "NodeSocketFloat", "INPUT", 0.466)
    add_socket(tree, "Offset 1", "NodeSocketFloat", "INPUT", 0.0)
    add_socket(tree, "Time", "NodeSocketFloat", "INPUT", 0.0)
    add_socket(tree, "Slide Speed", "NodeSocketFloat", "INPUT", 0.07)
    add_socket(tree, "D Max", "NodeSocketFloat", "INPUT", 14.360021)
    add_socket(tree, "D Min / Power", "NodeSocketFloat", "INPUT", 1.009032)
    add_socket(tree, "Stretch Contrast", "NodeSocketFloat", "INPUT", 0.728)
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

    time_mul = new_math(nodes, "MULTIPLY", "Time * SlideSpeed", -320, -300)
    center_add_1 = new_math(nodes, "ADD", "Center + Offset1", -100, -260)
    center_add_2 = new_math(nodes, "ADD", "Center + Motion", 80, -220)
    links.new(socket_by_name(group_in.outputs, "Time"), time_mul.inputs[0])
    links.new(socket_by_name(group_in.outputs, "Slide Speed"), time_mul.inputs[1])
    links.new(socket_by_name(group_in.outputs, "Center Offset"), center_add_1.inputs[0])
    links.new(socket_by_name(group_in.outputs, "Offset 1"), center_add_1.inputs[1])
    links.new(center_add_1.outputs[0], center_add_2.inputs[0])
    links.new(time_mul.outputs[0], center_add_2.inputs[1])

    sub_center = new_math(nodes, "SUBTRACT", "Bdot - Center", 280, 80)
    abs_center = new_math(nodes, "ABSOLUTE", "abs()", 460, 80)
    mul_dmax = new_math(nodes, "MULTIPLY", "* DMax", 640, 80)
    one_minus = new_math(nodes, "SUBTRACT", "1 - x", 820, 80, clamp=True)
    one_minus.inputs[0].default_value = 1.0
    links.new(dot_add.outputs[0], sub_center.inputs[0])
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


class NTE_OT_SetUpHairSpecular(Operator, BasicSetupUIOperator):
    '''Genera y asigna el nodo especular anisotrópico de cabello (KK_Anisotropic_HairSpec)'''
    bl_idname = 'neverness_to_everness.set_up_hair_specular'
    bl_label = 'Neverness to Everness: Set Up Hair Specular'

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
                aniso_node = next((n for n in nodes if n.type == 'GROUP' and n.node_tree == group), None)
                if not aniso_node:
                    aniso_node = nodes.new('ShaderNodeGroup')
                    aniso_node.node_tree = group
                    aniso_node.location = (-300, 200)

                nte_hair_node = next((n for n in nodes if n.type == 'GROUP' and n.node_tree == ng_hair), None) if ng_hair else None
                if nte_hair_node:
                    spec_in = nte_hair_node.inputs.get('高光') or nte_hair_node.inputs.get('Specular') or nte_hair_node.inputs.get('Hair Specular')
                    if spec_in and not spec_in.is_linked:
                        links.new(aniso_node.outputs['Spec Color Out'], spec_in)

        self.report({'INFO'}, 'Created and assigned Hair Specular Node Group: KK_Anisotropic_HairSpec')
        return {'FINISHED'}



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
])


