import bpy
import bmesh
import math
import mathutils
import sys
import os
import platform
import subprocess
import uuid
from bpy.props import *


def is_ill_matrix(matrix):
    for m in range(4):
        for n in range(4):
            if math.isnan(matrix[m][n]):
                return True
    return False


def compose_matrix(pose):
    return mathutils.Matrix([pose[0:4], pose[4:8], pose[8:12], pose[12:]]).transposed()


def load_unique_image(filename, max_uv):
    result = None
    for image in bpy.data.images:
        if image.filepath == filename:
            result = image
    if result == None:
        # Create a new small image
        result = bpy.data.images.new(name=os.path.basename(filename), width=64, height=64)
        # Blender supports UDIM texture since v2.82, UDIM texture filename usually contains "1001."
        partition = filename.partition("1001.")
        create_udim_image = bpy.app.version >= (2, 82) and partition[1] == "1001." and (max_uv[0] > 1.0 or max_uv[1] > 1.0)
        # Set the file path anyway
        result.source = 'FILE' if not create_udim_image else 'TILED'
        if create_udim_image:
            # Find all UDIM planes.
            udim_planes = []
            for udim_plane in range(1001, 1101, 1):
                udim_filename = "{}{}{}{}".format(partition[0], udim_plane, ".", partition[2])
                if os.access(udim_filename, os.F_OK):
                    udim_planes.append(udim_plane)
            # Create extra UDIM planes.
            for udim_plane in udim_planes:
                if udim_plane != 1001:
                    result.tiles.new(udim_plane)
        result.filepath = filename
        result.filepath_raw = filename
    return result


def make_texture_dic(context, texture_dic, max_uv):
    for (key, texture) in texture_dic.items():
        image = load_unique_image(texture[0], max_uv)
        texture.append(image)


def make_material_dic(context, texture_dic, material_dic, custom_property_dic):
    for (key, material) in material_dic.items():
        ob = bpy.data.materials.new(material[0])
        material.append(ob)
        if bpy.context.scene.render.engine == 'BLENDER_RENDER':
            ob.diffuse_color = (material[1], material[2], material[3])
            ob.specular_color = (material[9], material[10], material[11])
            ob.emit = material[17]
            if material[4] != -1:
                image = texture_dic[material[4]][-1]
                if image != None:
                    texImage = bpy.data.textures.new("Diffuse Texture", 'IMAGE')
                    texImage.image = image
                    texture_slot = ob.texture_slots.add()
                    texture_slot.texture = texImage
        elif bpy.context.scene.render.engine == 'CYCLES' or bpy.context.scene.render.engine == 'BLENDER_EEVEE':
            ob.diffuse_color = (material[1], material[2], material[3]) if bpy.app.version < (2, 80) else (material[1], material[2], material[3], 1.0)
            ob.specular_color = (material[9], material[10], material[11])
            ob.use_nodes = True
            bsdf = None
            material_output = None
            for node in ob.node_tree.nodes:
                if node.bl_idname == 'ShaderNodeOutputMaterial':
                    material_output = node
                if bpy.app.version < (2, 80):
                    if node.bl_idname == 'ShaderNodeBsdfDiffuse':
                        # replace the diffuse bsdf node with a principled bsdf node
                        location = node.location.copy()
                        ob.node_tree.nodes.remove(node)
                        bsdf = ob.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
                        bsdf.location = location
                        ob.node_tree.links.new(bsdf.outputs['BSDF'], ob.node_tree.nodes['Material Output'].inputs['Surface'])
                else:
                    if node.bl_idname == 'ShaderNodeBsdfPrincipled':
                        bsdf = node
            if bsdf != None and material_output != None:
                input_name_list = ['Base Color', 'Metallic', 'Specular', 'Roughness', 'Emission', 'Alpha', 'Normal', 'Bump', 'Displacement', 'Ambient']
                use_mix_rgb = (material[4] != -1 and material[40] != -1)
                mix_rgb_node = None
                for (i, input_name) in enumerate(input_name_list):
                    # no emission input and alpha input in principled bsdf node when blender version is lower than 2.8
                    if bpy.app.version < (2, 80) and (i == 4 or i == 5):
                        continue
                    # we only setup base color and emission color, leave other values as default, because the meanings of other values between BSDF and phone shading are different.
                    if i == 0 or i == 4:
                        bsdf.inputs[input_name].default_value = (material[i*4+1], material[i*4+2], material[i*4+3], 1.0)
                    # setup texture image
                    if material[i*4+4] != -1:
                        image = texture_dic[material[i*4+4]][-1]
                        if image != None:
                            texImage = ob.node_tree.nodes.new('ShaderNodeTexImage')
                            if i == 0:
                                texImage.location = bsdf.location + mathutils.Vector((-600, 700-i*300))
                            elif i == 9:
                                texImage.location = bsdf.location + mathutils.Vector((-600, 3100-i*300))
                            else:
                                texImage.location = bsdf.location + mathutils.Vector((-600, 400-i*300))
                            texImage.image = image
                            if not (i == 0 or i == 4 or i == 9):
                                if bpy.app.version < (2, 80):
                                    texImage.color_space = 'NONE'
                                else:
                                    texImage.image.colorspace_settings.name = 'Non-Color'
                            if i == 0:
                                if not use_mix_rgb:
                                    ob.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])
                                else:
                                    if mix_rgb_node == None:
                                        mix_rgb_node = ob.node_tree.nodes.new('ShaderNodeMixRGB')
                                        mix_rgb_node.blend_type = 'MULTIPLY'
                                        mix_rgb_node.location = bsdf.location + mathutils.Vector((-300, 400-i*300))
                                    ob.node_tree.links.new(bsdf.inputs['Base Color'], mix_rgb_node.outputs['Color'])
                                    ob.node_tree.links.new(mix_rgb_node.inputs['Color1'], texImage.outputs['Color'])
                            if i == 6:
                                normalMap = ob.node_tree.nodes.new('ShaderNodeNormalMap')
                                normalMap.location = bsdf.location + mathutils.Vector((-300, 400-i*300))
                                ob.node_tree.links.new(bsdf.inputs['Normal'], normalMap.outputs['Normal'])
                                ob.node_tree.links.new(normalMap.inputs['Color'], texImage.outputs['Color'])
                            elif i == 7:
                                bumpMap = ob.node_tree.nodes.new('ShaderNodeBump')
                                bumpMap.location = bsdf.location + mathutils.Vector((-300, 400-i*300))
                                ob.node_tree.links.new(bsdf.inputs['Normal'], bumpMap.outputs['Normal'])
                                ob.node_tree.links.new(bumpMap.inputs['Height'], texImage.outputs['Color'])
                            elif i == 8:
                                if bpy.app.version < (2, 80):
                                    ob.node_tree.links.new(material_output.inputs['Displacement'], texImage.outputs['Color'])
                                else:
                                    displacementMap = ob.node_tree.nodes.new('ShaderNodeDisplacement')
                                    displacementMap.location = bsdf.location + mathutils.Vector((-300, 400-i*300))
                                    ob.node_tree.links.new(material_output.inputs['Displacement'], displacementMap.outputs['Displacement'])
                                    ob.node_tree.links.new(displacementMap.inputs['Height'], texImage.outputs['Color'])
                            elif i == 9:
                                if not use_mix_rgb:
                                    ob.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])
                                else:
                                    if mix_rgb_node == None:
                                        mix_rgb_node = ob.node_tree.nodes.new('ShaderNodeMixRGB')
                                        mix_rgb_node.blend_type = 'MULTIPLY'
                                        mix_rgb_node.location = bsdf.location + mathutils.Vector((-300, 400-i*300))
                                    ob.node_tree.links.new(bsdf.inputs['Base Color'], mix_rgb_node.outputs['Color'])
                                    ob.node_tree.links.new(mix_rgb_node.inputs['Color2'], texImage.outputs['Color'])
                            else:
                                ob.node_tree.links.new(bsdf.inputs[input_name], texImage.outputs['Color'])
        # make custom properties for material
        custom_property_index = material[41]
        if custom_property_index != -1:
            if len(ob.keys()) == 0:
                make_custom_property(context, ob, custom_property_dic, custom_property_index)


def make_dummy_dic(context, hierarchy_dic, node_dic, bind_pose_dic, my_rotation_mode):
    for (key, hierarchy) in hierarchy_dic.items():
        if hierarchy[0] == 'EMPTY':
            dummy_key = key
            dummy_name = hierarchy[1]
            print(dummy_name)
            node = node_dic[dummy_key]
            # create a new object
            ob = bpy.data.objects.new(dummy_name, None)
            # change default rotation mode from euler('XYZ') to quaternion
            ob.rotation_mode = my_rotation_mode
            # add to dictionary for later use
            node['Object'] = ob
            # transform the object by transform matrix
            pose = bind_pose_dic[node['BindPose'][0][1]]
            ob.matrix_world = compose_matrix(pose)
            # link the object to the scene & make it active and selected
            if bpy.app.version < (2, 80):
                context.scene.objects.link(ob)
                context.scene.update()
                context.scene.objects.active = ob
                ob.select = True
            else:
                context.view_layer.active_layer_collection.collection.objects.link(ob)
                context.view_layer.active_layer_collection.collection.update_tag()
                context.view_layer.objects.active = ob
                ob.select_set(True)


def make_camera_dic(context, hierarchy_dic, node_dic, bind_pose_dic, camera_dic, my_rotation_mode):
    for (key, hierarchy) in hierarchy_dic.items():
        if hierarchy[0] == 'CAMERA':
            camera_key = key
            camera_name = hierarchy[1]
            print(camera_name)
            node = node_dic[camera_key]
            # create a new camera
            ca = bpy.data.cameras.new(camera_name)
            ca.type = camera_dic[node['Camera'][0][1]][0]
            ca.lens = camera_dic[node['Camera'][0][1]][1]
            ca.angle = math.radians(camera_dic[node['Camera'][0][1]][2])
            ca.angle_x = math.radians(camera_dic[node['Camera'][0][1]][3])
            ca.angle_y = math.radians(camera_dic[node['Camera'][0][1]][4])
            ca.lens_unit = camera_dic[node['Camera'][0][1]][5]
            ca.clip_start = camera_dic[node['Camera'][0][1]][6]
            ca.clip_end = camera_dic[node['Camera'][0][1]][7]
            ca.sensor_width = camera_dic[node['Camera'][0][1]][8]
            ca.sensor_height = camera_dic[node['Camera'][0][1]][9]
            ca.shift_x = camera_dic[node['Camera'][0][1]][10]
            ca.shift_y = camera_dic[node['Camera'][0][1]][11]
            # create a new object
            ob = bpy.data.objects.new(camera_name, ca)
            # change default rotation mode from euler('XYZ') to quaternion
            ob.rotation_mode = my_rotation_mode
            # add to dictionary for later use
            node['Object'] = ob
            # transform the object by transform matrix
            pose = bind_pose_dic[node['BindPose'][0][1]]
            ob.matrix_world = compose_matrix(pose)
            if bpy.app.version < (2, 80):
                ob.matrix_world = ob.matrix_world * mathutils.Matrix.Rotation(math.radians(-90.0), 4, 'Y')
            else:
                ob.matrix_world = ob.matrix_world @ mathutils.Matrix.Rotation(math.radians(-90.0), 4, 'Y')
            # link the object to the scene & make it active and selected
            if bpy.app.version < (2, 80):
                context.scene.objects.link(ob)
                context.scene.update()
                context.scene.objects.active = ob
                ob.select = True
            else:
                context.view_layer.active_layer_collection.collection.objects.link(ob)
                context.view_layer.active_layer_collection.collection.update_tag()
                context.view_layer.objects.active = ob
                ob.select_set(True)


def make_light_dic(context, hierarchy_dic, node_dic, bind_pose_dic, light_dic, my_rotation_mode):
    for (key, hierarchy) in hierarchy_dic.items():
        if hierarchy[0] == 'LIGHT':
            light_key = key
            light_name = hierarchy[1]
            print(light_name)
            node = node_dic[light_key]
            # create a new object
            if bpy.app.version < (2, 80):
                lt = bpy.data.lamps.new(light_name, type='POINT')
            else:
                lt = bpy.data.lights.new(light_name, type='POINT')
            lt.type = light_dic[node['Light'][0][1]][0]
            lt.energy = light_dic[node['Light'][0][1]][1]
            lt.color = (light_dic[node['Light'][0][1]][2], light_dic[node['Light'][0][1]][3], light_dic[node['Light'][0][1]][4])
            # create a new object
            ob = bpy.data.objects.new(light_name, lt)
            # change default rotation mode from euler('XYZ') to quaternion
            ob.rotation_mode = my_rotation_mode
            # add to dictionary for later use
            node['Object'] = ob
            # transform the object by transform matrix
            pose = bind_pose_dic[node['BindPose'][0][1]]
            ob.matrix_world = compose_matrix(pose)
            if bpy.app.version < (2, 80):
                ob.matrix_world = ob.matrix_world * mathutils.Matrix.Rotation(math.radians(-90.0), 4, 'X')
            else:
                ob.matrix_world = ob.matrix_world @ mathutils.Matrix.Rotation(math.radians(-90.0), 4, 'X')
            # link the object to the scene & make it active and selected
            if bpy.app.version < (2, 80):
                context.scene.objects.link(ob)
                context.scene.update()
                context.scene.objects.active = ob
                ob.select = True
            else:
                context.view_layer.active_layer_collection.collection.objects.link(ob)
                context.view_layer.active_layer_collection.collection.update_tag()
                context.view_layer.objects.active = ob
                ob.select_set(True)


def make_mesh_dic(context, hierarchy_dic, node_dic, bind_pose_dic, vertex_dic, polygon_dic, uv_dic, color_dic, normal_dic, polygon_material_dic, mesh_material_dic, material_dic, exist_object_dic, my_import_normal, my_shade_mode, use_auto_smooth, my_angle, edge_crease_dic, use_edge_crease, my_edge_crease_scale, my_edge_smoothing, edge_smoothing_dic, use_import_materials, obj_name, my_rotation_mode):
    for (key, hierarchy) in hierarchy_dic.items():
        if hierarchy[0] == 'MESH':
            mesh_key = key
            mesh_name = hierarchy[1] if obj_name == None else obj_name
            print(mesh_name)
            node = node_dic[mesh_key]
            vertex_index = node['Vertex'][0][1]
            polygon_index = node['Polygon'][0][1]
            keyword = ('Mesh', vertex_index, polygon_index)
            if keyword in exist_object_dic:
                me = exist_object_dic[keyword]
                # create a new object
                ob = bpy.data.objects.new(mesh_name, me)
                # change default rotation mode from euler('XYZ') to quaternion
                ob.rotation_mode = my_rotation_mode
                # add to dictionary for later use
                node['Object'] = ob
                # transform the object by transform matrix
                pose = bind_pose_dic[node['BindPose'][0][1]]
                ob.matrix_world = compose_matrix(pose)
                # link the object to the scene & make it active and selected
                if bpy.app.version < (2, 80):
                    context.scene.objects.link(ob)
                    context.scene.update()
                    context.scene.objects.active = ob
                    ob.select = True
                else:
                    context.view_layer.active_layer_collection.collection.objects.link(ob)
                    context.view_layer.active_layer_collection.collection.update_tag()
                    context.view_layer.objects.active = ob
                    ob.select_set(True)
            else:
                # create a new empty mesh
                me = bpy.data.meshes.new(name=mesh_name)
                exist_object_dic[keyword] = me
                # create a new bmesh
                bm = bmesh.new()
                # add some geometry
                for v_co in vertex_dic[vertex_index]:
                    bm.verts.new(v_co)
                bm.verts.ensure_lookup_table()
                for indices in polygon_dic[polygon_index]:
                    bm.faces.new([bm.verts[index] for index in indices])
                # write the bmesh to the mesh
                bm.to_mesh(me)
                me.update()
                bm.free()  # free and prevent further access
                # add uv layers
                bm = bmesh.new()
                bm.from_mesh(me)
                # create a new layer
                if 'UV' in node:
                    # multiple uv sets
                    for uv in node['UV']:
                        uv_name = uv[0]
                        uv_index = uv[1]
                        uvs = uv_dic[uv_index]
                        uv_layer = bm.loops.layers.uv.new(uv_name)
                        if bpy.app.version < (2, 80):
                            bm.faces.layers.tex.verify()
                        else:
                            bm.faces.layers.face_map.verify()
                        for (i, f) in enumerate(bm.faces):
                            for (j, l) in enumerate(f.loops):
                                luv = l[uv_layer]
                                luv.uv = (uvs[i][j][0], uvs[i][j][1])
                bm.to_mesh(me)
                me.update()
                bm.free  # free and prevent further access
                # add color layers
                bm = bmesh.new()
                bm.from_mesh(me)
                # create a new layer
                if 'Color' in node:
                    # multiple color sets
                    for color in node['Color']:
                        color_name = color[0]
                        color_index = color[1]
                        colors = color_dic[color_index]
                        color_layer = bm.loops.layers.color.new(color_name)
                        for (i, f) in enumerate(bm.faces):
                            for (j, l) in enumerate(f.loops):
                                lcolor = l[color_layer]
                                if bpy.app.version < (2, 80):
                                    (lcolor[0], lcolor[1], lcolor[2]) = (colors[i][j][0], colors[i][j][1], colors[i][j][2])
                                else:
                                    (lcolor[0], lcolor[1], lcolor[2], lcolor[3]) = (colors[i][j][0], colors[i][j][1], colors[i][j][2], colors[i][j][3])
                bm.to_mesh(me)
                me.update()
                bm.free  # free and prevent further access
                if use_import_materials:
                    # add mesh material
                    if 'MeshMaterial' in node:
                        mesh_material_index = node['MeshMaterial'][0][1]
                        mesh_material = mesh_material_dic[mesh_material_index]
                        for material_index in mesh_material:
                            material = material_dic[material_index][-1]
                            me.materials.append(material)
                    # assign material index for each polygon
                    if 'PolygonMaterial' in node:
                        polygon_material_index = node['PolygonMaterial'][0][1]
                        polygon_materials = polygon_material_dic[polygon_material_index]
                        for (i, material_index) in enumerate(polygon_materials):
                            me.polygons[i].material_index = material_index
                # create a new object
                ob = bpy.data.objects.new(mesh_name, me)
                # change default rotation mode from euler('XYZ') to quaternion
                ob.rotation_mode = my_rotation_mode
                # add to dictionary for later use
                node['Object'] = ob
                # transform the object by transform matrix
                pose = bind_pose_dic[node['BindPose'][0][1]]
                ob.matrix_world = compose_matrix(pose)
                # link the object to the scene & make it active and selected
                if bpy.app.version < (2, 80):
                    context.scene.objects.link(ob)
                    context.scene.update()
                    context.scene.objects.active = ob
                    ob.select = True
                else:
                    context.view_layer.active_layer_collection.collection.objects.link(ob)
                    context.view_layer.active_layer_collection.collection.update_tag()
                    context.view_layer.objects.active = ob
                    ob.select_set(True)
                # use imported normals
                if my_import_normal == 'Import' and 'Normal' in node:
                    # create empty split vertex normals
                    ob.data.create_normals_split()
                    # fill split vertex normals, we just use the first normal set.
                    normal_index = node['Normal'][0][1]
                    normals = normal_dic[normal_index]
                    for (i, polygon) in enumerate(ob.data.polygons):
                        for (j, loop_index) in enumerate(polygon.loop_indices):
                            ob.data.loops[loop_index].normal = (normals[i][j][0], normals[i][j][1], normals[i][j][2])
                    # apply split vertex normals
                    loop_normals = [loop.normal for loop in ob.data.loops]
                    # set smooth for each polygons
                    ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))
                    # define polygon loop normals
                    ob.data.normals_split_custom_set(loop_normals)
                    # free split vertex normals
                    ob.data.free_normals_split()
                    # auto display split vertex normals
                    ob.data.use_auto_smooth = True
                # generate normals
                else:
                    #recalculate_normals(ob)
                    if use_auto_smooth:
                        # let the mesh look better based on the sharpness between faces
                        ob.data.use_auto_smooth = True
                        # angle gate set to 60 degrees
                        ob.data.auto_smooth_angle = (my_angle / 180.0) * math.pi
                    else:
                        # let the mesh look very smoothly based on vertex normals
                        ob.data.use_auto_smooth = False
                    if my_shade_mode == 'Smooth':
                        # mark object as smooth (example of using ops on active object)
                        bpy.ops.object.shade_smooth()
                    else:
                        # mark object as flat (example of using ops on active object)
                        bpy.ops.object.shade_flat()
                # set edge crease
                if use_edge_crease:
                    if 'EdgeCrease' in node:
                        edge_crease_index = node['EdgeCrease'][0][1]
                        edge_creases = edge_crease_dic[edge_crease_index]
                        # make a edge crease map to increase the search speed.
                        edge_crease_map = {}
                        for edge_crease in edge_creases:
                            edge_crease_map[(edge_crease[0], edge_crease[1])] = edge_crease[2]
                        for edge in ob.data.edges:
                            edge_vertex_pair1 = (edge.vertices[0], edge.vertices[1])
                            if edge_vertex_pair1 in edge_crease_map:
                                edge.crease = edge_crease_map[edge_vertex_pair1] * my_edge_crease_scale
                            edge_vertex_pair2 = (edge.vertices[1], edge.vertices[0])
                            if edge_vertex_pair2 in edge_crease_map:
                                edge.crease = edge_crease_map[edge_vertex_pair2] * my_edge_crease_scale
                        ob.data.use_customdata_edge_crease = True
                # set edge smoothing
                if my_edge_smoothing == 'Import' or my_edge_smoothing == 'FBXSDK':
                    if 'EdgeSmoothing' in node:
                        edge_smoothing_index = node['EdgeSmoothing'][0][1]
                        edge_smoothings = edge_smoothing_dic[edge_smoothing_index]
                        # make a edge smoothing set to increase the search speed.
                        edge_smoothing_set = set()
                        for edge_smoothing in edge_smoothings:
                            edge_smoothing_set.add((edge_smoothing[0], edge_smoothing[1]))
                        for edge in ob.data.edges:
                            edge_vertex_pair1 = (edge.vertices[0], edge.vertices[1])
                            if edge_vertex_pair1 in edge_smoothing_set:
                                edge.use_edge_sharp = True
                            edge_vertex_pair2 = (edge.vertices[1], edge.vertices[0])
                            if edge_vertex_pair2 in edge_smoothing_set:
                                edge.use_edge_sharp = True
                elif my_edge_smoothing == 'Blender':
                    # not flat shading
                    if not (not (my_import_normal == 'Import' and 'Normal' in node) and not (my_shade_mode == 'Smooth')):
                        # generate polygon loop normals
                        if not (my_import_normal == 'Import' and 'Normal' in node):
                            ob.data.calc_normals_split()
                        # prepare to mark sharp edges
                        vertex_normals_dict = {}
                        edge_polygon_dict = {}
                        edge_normals_dic = {}
                        if not (my_import_normal == 'Import' and 'Normal' in node):
                            for (i, polygon) in enumerate(ob.data.polygons):
                                # how many normals per vertex
                                for (j, loop_index) in enumerate(polygon.loop_indices):
                                    if vertex_normals_dict.get(ob.data.loops[loop_index].vertex_index) is None:
                                        vertex_normals_dict[ob.data.loops[loop_index].vertex_index] = set()
                                    vertex_normals_dict[ob.data.loops[loop_index].vertex_index].add(tuple(ob.data.loops[loop_index].normal))
                                # how many polygons per edge
                                for key in polygon.edge_keys:
                                    if edge_polygon_dict.get(key) is None:
                                        edge_polygon_dict[key] = 0
                                    edge_polygon_dict[key] += 1
                                    if edge_normals_dic.get(key) is None:
                                        edge_normals_dic[key] = set()
                                    edge_normals_dic[key].add(tuple(polygon.normal))
                        else:
                            normal_index = node['Normal'][0][1]
                            normals = normal_dic[normal_index]
                            for (i, polygon) in enumerate(ob.data.polygons):
                                # how many normals per vertex
                                for (j, loop_index) in enumerate(polygon.loop_indices):
                                    if vertex_normals_dict.get(ob.data.loops[loop_index].vertex_index) is None:
                                        vertex_normals_dict[ob.data.loops[loop_index].vertex_index] = set()
                                    vertex_normals_dict[ob.data.loops[loop_index].vertex_index].add((normals[i][j][0], normals[i][j][1], normals[i][j][2]))
                                # how many polygons per edge
                                for key in polygon.edge_keys:
                                    if edge_polygon_dict.get(key) is None:
                                        edge_polygon_dict[key] = 0
                                    edge_polygon_dict[key] += 1
                                    if edge_normals_dic.get(key) is None:
                                        edge_normals_dic[key] = set()
                                    edge_normals_dic[key].add(tuple(polygon.normal))
                        # free polygon loop normals
                        if not (my_import_normal == 'Import' and 'Normal' in node):
                            ob.data.free_normals_split()
                        # mark sharp edges
                        for edge in ob.data.edges:
                            # mark loose edge as sharp
                            if edge.is_loose:
                                edge.use_edge_sharp = True
                            # mark boundary edge as sharp
                            if edge_polygon_dict[edge.key] == 1:
                                edge.use_edge_sharp = True
                            # mark edge which both two vertices have multiple normals and the edge shares multiple face normals as sharp
                            if len(vertex_normals_dict[edge.vertices[0]]) > 1 and len(vertex_normals_dict[edge.vertices[1]]) > 1 and len(edge_normals_dic[edge.key]) > 1:
                                edge.use_edge_sharp = True
                        # show sharp edges
                        if bpy.app.version < (2, 80):
                            ob.data.show_edge_sharp = True


def make_shape_dic(context, hierarchy_dic, node_dic, shape_dic):
    for (key, hierarchy) in hierarchy_dic.items():
        if hierarchy[0] == 'MESH':
            mesh_key = key
            mesh_name = hierarchy[1]
            node = node_dic[mesh_key]
            if 'Shape' in node:
                ob = node['Object']
                # no shape yet
                if ob.data.shape_keys == None:
                    bm = bmesh.new()
                    bm.from_mesh(ob.data)
                    bm.verts.ensure_lookup_table()
                    # we need to add a basic shape if not exists
                    if len(bm.verts.layers.shape.items()) == 0:
                        if bpy.app.version < (2, 80):
                            ob.shape_key_add("Basis")
                        else:
                            ob.shape_key_add(name="Basis")
                        bm.to_mesh(ob.data)
                        ob.data.shape_keys.use_relative = True
                    for shape_item in node['Shape']:
                        shape_name = shape_item[0]
                        shape_index = shape_item[1]
                        if bpy.app.version < (2, 80):
                            shape = ob.shape_key_add(shape_name)
                        else:
                            shape = ob.shape_key_add(name=shape_name)
                        bm.free()  # free and prevent further access
                        bm = bmesh.new()
                        bm.from_mesh(ob.data)
                        bm.verts.ensure_lookup_table()
                        shape_layer = bm.verts.layers.shape.get(shape.name)
                        for item in shape_dic[shape_index]:
                            bm.verts[item[0]][shape_layer].x = item[1]
                            bm.verts[item[0]][shape_layer].y = item[2]
                            bm.verts[item[0]][shape_layer].z = item[3]
                        bm.to_mesh(ob.data)
                        bm.free()  # free and prevent further access


def make_custom_property(context, ob, custom_property_dic, custom_property_index):
    for custom_property in custom_property_dic[custom_property_index]:
        if custom_property[1] == 'INT':
            ob[custom_property[0]] = int(custom_property[2])
        elif custom_property[1] == 'FLOAT':
            ob[custom_property[0]] = float(custom_property[2])
        elif custom_property[1] == 'STRING':
            ob[custom_property[0]] = custom_property[2]
        elif custom_property[1] == 'VECTOR_FLOAT':
            ob[custom_property[0]] = [float(item) for item in custom_property[2:]]


def make_custom_property_dic(context, hierarchy_dic, node_dic, custom_property_dic):
    for (key, hierarchy) in hierarchy_dic.items():
        node = node_dic[key]
        if 'CustomProperty' in node:
            if hierarchy[0] != 'BONE':
                ob = node['Object']
            else:
                tokens = key.split(".")
                armature_key = tokens[0]
                armature_node = node_dic[armature_key]
                armature = armature_node['Object']
                bone_name = hierarchy[1]
                ob = armature.data.bones[bone_name]
            custom_property_index = node['CustomProperty'][0][1]
            if len(ob.keys()) == 0:
                make_custom_property(context, ob, custom_property_dic, custom_property_index)


def make_ik_dic(context, hierarchy_dic, node_dic, ik_dic):
    for (key, hierarchy) in hierarchy_dic.items():
        node = node_dic[key]
        if 'IK' in node:
            tokens = key.split(".")
            armature_key = tokens[0]
            armature_node = node_dic[armature_key]
            armature = armature_node['Object']
            bone_name = hierarchy[1]
            pose_bone = armature.pose.bones[bone_name]
            ik_index = node['IK'][0][1]
            # Create an IK constraint
            ik_constraint = pose_bone.constraints.new(type='IK')
            ik_constraint.name = ik_dic[ik_index][0]
            if ik_dic[ik_index][1] != "-1":
                ik_constraint.target = node_dic[ik_dic[ik_index][1]]['Object']
            ik_constraint.chain_count = ik_dic[ik_index][2]
            ik_constraint.use_tail = False


def make_armature_dic(context, hierarchy_dic, node_dic, bind_pose_dic, my_leaf_bone, use_auto_bone_orientation, my_bone_length, my_calculate_roll, obj_name, my_rotation_mode):
    for (key, hierarchy) in hierarchy_dic.items():
        if hierarchy[0] == 'ARMATURE':
            leaf_bone_scale = 1.0 if my_leaf_bone == 'Long' else 0.1
            armature_key = key
            armature_name = hierarchy[1] if obj_name == None else obj_name
            print(armature_name)
            armature_node = node_dic[armature_key]
            # create a new empty armature
            me = bpy.data.armatures.new(name=armature_name)
            # create a new object
            ob = bpy.data.objects.new(armature_name, me)
            # change default rotation mode from euler('XYZ') to quaternion
            ob.rotation_mode = my_rotation_mode
            # add to dictionary for later use
            armature_node['Object'] = ob
            pose = bind_pose_dic[armature_node['BindPose'][0][1]]
            ob.matrix_world = compose_matrix(pose)
            inverse_armature_matrix = ob.matrix_world.inverted()
            # link the object to the scene & make it active and selected
            if bpy.app.version < (2, 80):
                context.scene.objects.link(ob)
                context.scene.update()
                context.scene.objects.active = ob
                ob.select = True
            else:
                context.view_layer.active_layer_collection.collection.objects.link(ob)
                context.view_layer.active_layer_collection.collection.update_tag()
                context.view_layer.objects.active = ob
                ob.select_set(True)
            # must be in edit mode to add bones
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)
            edit_bones = ob.data.edit_bones
            for (key2, hierarchy2) in hierarchy_dic.items():
                if hierarchy2[0] == 'BONE':
                    bone_key = key2
                    bone_name = hierarchy2[1]
                    tokens = bone_key.split(".")
                    if len(tokens) == 2 and tokens[0] == armature_key:
                        bone_node = node_dic[bone_key]
                        b = edit_bones.new(bone_name)
                        # set bone length
                        b.head = (0.0, 0.0, 0.0)
                        b.tail = (0.0, 0.0, my_bone_length)
                        # add to dictionary for later use
                        bone_node['Object'] = b
                        # we also need bone name for later use
                        bone_node['ObjectName'] = b.name
                        pose = bind_pose_dic[bone_node['BindPose'][0][1]]
                        matrix = compose_matrix(pose)
                        # make armature space matrix
                        if bpy.app.version < (2, 80):
                            matrix = inverse_armature_matrix * matrix
                        else:
                            matrix = inverse_armature_matrix @ matrix
                        # sometimes matrix has negative scale, in this case, we have to reconstruct the matrix.
                        if matrix.is_negative:
                            # decompose matrix to channels
                            loc, rot, sca = matrix.decompose()
                            mat_t = mathutils.Matrix.Translation(loc)
                            mat_r = rot.to_matrix().to_4x4()
                            if bpy.app.version < (2, 80):
                                mat_s = mathutils.Matrix.Scale(abs(sca[0]), 4, (1.0, 0.0, 0.0)) * mathutils.Matrix.Scale(abs(sca[1]), 4, (0.0, 1.0, 0.0)) * mathutils.Matrix.Scale(abs(sca[2]), 4, (0.0, 0.0, 1.0))
                                matrix = mat_t * mat_r * mat_s
                            else:
                                mat_s = mathutils.Matrix.Scale(abs(sca[0]), 4, (1.0, 0.0, 0.0)) @ mathutils.Matrix.Scale(abs(sca[1]), 4, (0.0, 1.0, 0.0)) @ mathutils.Matrix.Scale(abs(sca[2]), 4, (0.0, 0.0, 1.0))
                                matrix = mat_t @ mat_r @ mat_s
                        b.matrix = mathutils.Matrix() if is_ill_matrix(matrix) else matrix
            # set parent for bones
            for (key2, hierarchy2) in hierarchy_dic.items():
                if hierarchy2[0] == 'BONE':
                    bone_key = key2
                    tokens = bone_key.split(".")
                    if len(tokens) == 2 and tokens[0] == armature_key:
                        parent_key = hierarchy2[2]
                        tokens2 = parent_key.split(".")
                        # in same bone hierarchy
                        if len(tokens2) == 2 and tokens2[0] == armature_key:
                            bone_node = node_dic[bone_key]
                            parent_node = node_dic[parent_key]
                            bone_node['Object'].parent = parent_node['Object']
            if use_auto_bone_orientation:
                # calculate old local matrix
                for (key2, hierarchy2) in hierarchy_dic.items():
                    if hierarchy2[0] == 'BONE':
                        bone_key = key2
                        tokens = bone_key.split(".")
                        if len(tokens) == 2 and tokens[0] == armature_key:
                            bone_node = node_dic[bone_key]
                            parent_key = hierarchy2[2]
                            parent_node = node_dic[parent_key]
                            if bpy.app.version < (2, 80):
                                mat_parent = mathutils.Matrix() if parent_key == armature_key else mathutils.Matrix.Translation(parent_node['Object'].tail - parent_node['Object'].head) * parent_node['Object'].matrix
                                old_mat_local = mat_parent.inverted() * bone_node['Object'].matrix
                            else:
                                mat_parent = mathutils.Matrix() if parent_key == armature_key else mathutils.Matrix.Translation(parent_node['Object'].tail - parent_node['Object'].head) @ parent_node['Object'].matrix
                                old_mat_local = mat_parent.inverted() @ bone_node['Object'].matrix
                            # save for later use
                            bone_node['MatParent'] = mat_parent
                            bone_node['OldMatLocal'] = old_mat_local
                # force connect children
                for (key2, hierarchy2) in hierarchy_dic.items():
                    if hierarchy2[0] == 'BONE':
                        bone_key = key2
                        tokens = bone_key.split(".")
                        if len(tokens) == 2 and tokens[0] == armature_key:
                            bone_node = node_dic[bone_key]
                            b = bone_node['Object']
                            # average head position of all children
                            if len(b.children) > 0:
                                loc = mathutils.Vector((0.0, 0.0, 0.0))
                                for child in b.children:
                                    loc += child.head
                                loc /= len(b.children)
                            # leaf bone, extrude out a bit.
                            elif b.parent:
                                loc = b.head + (b.head - b.parent.head) * leaf_bone_scale
                            # single bone, use original bone tail
                            else:
                                loc = b.tail
                            # bone length must not be zero
                            if (loc - b.head).length > 1e-3:
                                b.tail = loc
                            # make the bone very short
                            else:
                                if bpy.app.version < (2, 80):
                                    b.tail = b.head + b.matrix * mathutils.Vector((0.0, 1.0, 0.0)) * 0.01
                                else:
                                    b.tail = b.head + b.matrix @ mathutils.Vector((0.0, 1.0, 0.0)) * 0.01
                # calculate roll for bones
                if my_calculate_roll != "None":
                    # set bone selection status
                    for b in ob.data.edit_bones:
                        b.select = True
                    bpy.ops.armature.calculate_roll(type=my_calculate_roll)
                    # clear bone selection status
                    for b in ob.data.edit_bones:
                        b.select = False
                # calculate new local matrix
                for (key2, hierarchy2) in hierarchy_dic.items():
                    if hierarchy2[0] == 'BONE':
                        bone_key = key2
                        tokens = bone_key.split(".")
                        if len(tokens) == 2 and tokens[0] == armature_key:
                            bone_node = node_dic[bone_key]
                            if bpy.app.version < (2, 80):
                                new_mat_local = bone_node['MatParent'].inverted() * bone_node['Object'].matrix
                            else:
                                new_mat_local = bone_node['MatParent'].inverted() @ bone_node['Object'].matrix
                            # save for later use
                            bone_node['NewMatLocal'] = new_mat_local
                # calculate inverse correct matrix
                for (key2, hierarchy2) in hierarchy_dic.items():
                    if hierarchy2[0] == 'BONE':
                        bone_key = key2
                        tokens = bone_key.split(".")
                        if len(tokens) == 2 and tokens[0] == armature_key:
                            bone_node = node_dic[bone_key]
                            if bpy.app.version < (2, 80):
                                inverse_correct_matrix = bone_node['NewMatLocal'].inverted() * bone_node['OldMatLocal']
                            else:
                                inverse_correct_matrix = bone_node['NewMatLocal'].inverted() @ bone_node['OldMatLocal']
                            # save for later use
                            bone_node['CorrectPose'] = inverse_correct_matrix.to_quaternion()
                            # no longer use
                            del bone_node['MatParent']
                            del bone_node['OldMatLocal']
                            del bone_node['NewMatLocal']
            # exit edit mode to save bones
            bpy.ops.object.mode_set(mode='OBJECT')

            # set rotation mode for all bones
            for bone in ob.pose.bones:
                bone.rotation_mode = my_rotation_mode

def reset_matrix_parent_inverse(ob):
    if bpy.app.version < (2, 80):
        ob.matrix_basis = ob.matrix_parent_inverse * ob.matrix_basis
    else:
        ob.matrix_basis = ob.matrix_parent_inverse @ ob.matrix_basis
    ob.matrix_parent_inverse.identity()


def reset_all_matrix_parent_inverses(context, hierarchy_dic, node_dic):
    for (key, hierarchy) in hierarchy_dic.items():
        if hierarchy[0] != 'BONE':
            node = node_dic[key]
            ob = node['Object']
            reset_matrix_parent_inverse(ob)


def make_hierarchy_dic(context, hierarchy_dic, node_dic, default_pose_dic, bind_pose_dic):
    # set parent for all nodes
    for (key, hierarchy) in hierarchy_dic.items():
        parent_key = hierarchy[2]
        # ignore root node
        if parent_key != str(-1):
            # we have already set parent for all bones
            if hierarchy[0] != 'BONE':
                node = node_dic[key]
                parent_node = node_dic[parent_key]
                # parent is bone
                if hierarchy_dic[parent_key][0] == 'BONE':
                    tokens = parent_key.split(".")
                    if len(tokens) == 2:
                        armature_key = tokens[0]
                        armature_node = node_dic[armature_key]
                        # set parent to armature
                        node['Object'].parent = armature_node['Object']
                        bone_name = parent_node['ObjectName']
                        bone = armature_node['Object'].pose.bones[bone_name]
                        node['Object'].parent_bone = bone.name
                        node['Object'].parent_type = 'BONE'
                        # keep transform
                        if bpy.app.version < (2, 80):
                            node['Object'].matrix_parent_inverse = (armature_node['Object'].matrix_world * mathutils.Matrix.Translation(bone.tail - bone.head) * bone.matrix).inverted()
                        else:
                            node['Object'].matrix_parent_inverse = (armature_node['Object'].matrix_world @ mathutils.Matrix.Translation(bone.tail - bone.head) @ bone.matrix).inverted()
                else:
                    # set parent
                    node['Object'].parent = parent_node['Object']
                    # keep transform
                    node['Object'].matrix_parent_inverse = parent_node['Object'].matrix_world.inverted()


def fix_bind_pose(context, hierarchy_dic, node_dic, default_pose_dic, bind_pose_dic):
    for (key, hierarchy) in hierarchy_dic.items():
        parent_key = hierarchy[2]
        # ignore root node
        if parent_key != str(-1):
            # we have already set parent for all bones
            if hierarchy[0] != 'BONE':
                node = node_dic[key]
                parent_node = node_dic[parent_key]
                # parent is bone
                if hierarchy_dic[parent_key][0] == 'BONE':
                    tokens = parent_key.split(".")
                    if len(tokens) == 2:
                        parent_bind_matrix = compose_matrix(bind_pose_dic[parent_node['BindPose'][0][1]])
                        parent_default_matrix = compose_matrix(default_pose_dic[parent_node['DefaultPose'][0][1]])
                        node_default_matrix = compose_matrix(default_pose_dic[node['DefaultPose'][0][1]])
                        if bpy.app.version < (2, 80):
                            node_local_matrix = parent_default_matrix.inverted() * node_default_matrix
                            node_bind_matrix = parent_bind_matrix * node_local_matrix
                        else:
                            node_local_matrix = parent_default_matrix.inverted() @ node_default_matrix
                            node_bind_matrix = parent_bind_matrix @ node_local_matrix
                        node['Object'].matrix_world = node_bind_matrix


def set_default_pose(context, hierarchy_dic, node_dic, default_pose_dic):
    for (key, hierarchy) in hierarchy_dic.items():
        if hierarchy[0] == 'BONE':
            bone_node = node_dic[key]
            bone_name = bone_node['ObjectName']
            parent_key = hierarchy[2]
            parent_node = node_dic[parent_key]
            tokens = key.split(".")
            if len(tokens) == 2:
                armature_key = tokens[0]
                armature_node = node_dic[armature_key]
                armature = armature_node['Object']
                pose_bone = armature.pose.bones[bone_name]
                parent_default_matrix = compose_matrix(default_pose_dic[parent_node['DefaultPose'][0][1]])
                node_default_matrix = compose_matrix(default_pose_dic[bone_node['DefaultPose'][0][1]])
                if bpy.app.version < (2, 80):
                    node_local_matrix = parent_default_matrix.inverted() * node_default_matrix
                else:
                    node_local_matrix = parent_default_matrix.inverted() @ node_default_matrix
                # correct pose
                correct_pose = bone_node['CorrectPose'] if 'CorrectPose' in bone_node else None
                if correct_pose != None:
                    loc, rot, sca = node_local_matrix.decompose()
                    axis, angle = rot.to_axis_angle()
                    if bpy.app.version < (2, 80):
                        original_axis = correct_pose * axis
                        loc = correct_pose * loc
                    else:
                        original_axis = correct_pose @ axis
                        loc = correct_pose @ loc
                    rot = mathutils.Quaternion(original_axis, angle)
                    mat_loc = mathutils.Matrix.Translation(loc)
                    mat_rot = rot.to_matrix().to_4x4()
                    mat_sca = mathutils.Matrix.Identity(4)
                    mat_sca_x = mathutils.Matrix.Scale(sca.x, 4, (1,0,0))
                    mat_sca_y = mathutils.Matrix.Scale(sca.y, 4, (0,1,0))
                    mat_sca_z = mathutils.Matrix.Scale(sca.z, 4, (0,0,1))
                    if bpy.app.version < (2, 80):
                        mat_sca = mat_sca_x * mat_sca_y * mat_sca_z
                    else:
                        mat_sca = mat_sca_x @ mat_sca_y @ mat_sca_z
                    if bpy.app.version < (2, 80):
                        node_local_matrix = mat_loc * mat_rot * mat_sca
                    else:
                        node_local_matrix = mat_loc @ mat_rot @ mat_sca
                pose_bone.matrix_basis = node_local_matrix


def bind_mesh_to_armature(context, hierarchy_dic, node_dic, weight_dic):
    for (key, hierarchy) in hierarchy_dic.items():
        if hierarchy[0] == 'MESH':
            mesh_key = key
            node = node_dic[mesh_key]
            if 'Weight' in node:
                ob = node['Object']
                # not bound yet
                if len(ob.vertex_groups) == 0:
                    weight_index = node['Weight'][0][1]
                    armature_key_set = set()
                    for (vertex_index, weight_list) in enumerate(weight_dic[weight_index]):
                        if weight_list != None:
                            for weight in weight_list:
                                bone_key = weight[0]
                                bone_node = node_dic[bone_key]
                                bone_name = bone_node['ObjectName']
                                tokens = bone_key.split(".")
                                if len(tokens) == 2:
                                    armature_key = tokens[0]
                                    armature_key_set.add(armature_key)
                                bone_weight = weight[1]
                                # create vertex groups if not exists
                                if ob.vertex_groups.find(bone_name) == -1:
                                    ob.vertex_groups.new(name=bone_name)
                                ob.vertex_groups[bone_name].add([vertex_index], bone_weight, 'REPLACE')
                    for armature_key in armature_key_set:
                        armature_node = node_dic[armature_key]
                        armature_ob = armature_node['Object']
                        # clear existed parent
                        ob.parent = None
                        ob.matrix_parent_inverse.identity()
                        # set parent to armature
                        ob.parent = armature_ob
                        # keep transform
                        ob.matrix_parent_inverse = armature_ob.matrix_world.inverted()
                        mod = ob.modifiers.new(armature_ob.name, 'ARMATURE')
                        mod.object = armature_ob
                        mod.use_bone_envelopes = False
                        mod.use_vertex_groups = True


def make_fcurves_list(action_ob, ob, parent_bind_pose, bind_pose, parent_pose_list, pose_list, correct_pose, ob_type, my_rotation_mode):
    key_frames = len(pose_list)
    channel_location = [None] * 3
    channel_rotation = [None] * 4
    channel_scale = [None] * 3
    for i in range(3):
        channel_location[i] = action_ob.fcurves.new(data_path=ob.path_from_id("location"), index=i)
        channel_location[i].keyframe_points.add(key_frames)
    if my_rotation_mode == 'QUATERNION':
        for i in range(4):
            channel_rotation[i] = action_ob.fcurves.new(data_path=ob.path_from_id("rotation_quaternion"), index=i)
            channel_rotation[i].keyframe_points.add(key_frames)
    elif my_rotation_mode == 'AXIS_ANGLE':
        for i in range(4):
            channel_rotation[i] = action_ob.fcurves.new(data_path=ob.path_from_id("rotation_axis_angle"), index=i)
            channel_rotation[i].keyframe_points.add(key_frames)
    else:
        for i in range(3):
            channel_rotation[i] = action_ob.fcurves.new(data_path=ob.path_from_id("rotation_euler"), index=i)
            channel_rotation[i].keyframe_points.add(key_frames)
    for i in range(3):
        channel_scale[i] = action_ob.fcurves.new(data_path=ob.path_from_id("scale"), index=i)
        channel_scale[i].keyframe_points.add(key_frames)
    # write to channels
    parent_bind_pose_matrix = compose_matrix(parent_bind_pose) if parent_bind_pose != None else mathutils.Matrix()
    bind_pose_matrix = compose_matrix(bind_pose)
    if bpy.app.version < (2, 80):
        local_bind_pose_matrix = parent_bind_pose_matrix.inverted() * bind_pose_matrix
    else:
        local_bind_pose_matrix = parent_bind_pose_matrix.inverted() @ bind_pose_matrix
    for (frame_counter, pose) in enumerate(pose_list):
        key_frame = pose[0]
        parent_pose_matrix = compose_matrix(parent_pose_list[frame_counter][1:]) if parent_pose_list != None else parent_bind_pose_matrix
        pose_matrix = compose_matrix(pose_list[frame_counter][1:])
        if bpy.app.version < (2, 80):
            local_pose_matrix = parent_pose_matrix.inverted() * pose_matrix
            if ob_type and ob_type in ['CAMERA', 'LIGHT']:
                local_pose_matrix = local_pose_matrix * mathutils.Matrix.Rotation(math.radians(-90.0), 4, 'Y' if ob_type == 'CAMERA' else 'X')
            local_basic_pose_matrix = local_bind_pose_matrix.inverted() * local_pose_matrix if parent_bind_pose != None else pose_matrix
        else:
            local_pose_matrix = parent_pose_matrix.inverted() @ pose_matrix
            if ob_type and ob_type in ['CAMERA', 'LIGHT']:
                local_pose_matrix = local_pose_matrix @ mathutils.Matrix.Rotation(math.radians(-90.0), 4, 'Y' if ob_type == 'CAMERA' else 'X')
            local_basic_pose_matrix = local_bind_pose_matrix.inverted() @ local_pose_matrix if parent_bind_pose != None else pose_matrix
        if ob_type:
            loc, rot, sca = local_pose_matrix.decompose()
            ob.matrix_parent_inverse.identity()
        else:
            loc, rot, sca = local_basic_pose_matrix.decompose()
        # correct pose
        if correct_pose != None:
            axis, angle = rot.to_axis_angle()
            if bpy.app.version < (2, 80):
                original_axis = correct_pose * axis
                loc = correct_pose * loc
            else:
                original_axis = correct_pose @ axis
                loc = correct_pose @ loc
            rot = mathutils.Quaternion(original_axis, angle)
        if my_rotation_mode != 'QUATERNION':
            if my_rotation_mode == 'AXIS_ANGLE':
                rot_axis_angle = rot.to_axis_angle()
                rot_axis_angle = [rot_axis_angle[1], rot_axis_angle[0][0], rot_axis_angle[0][1], rot_axis_angle[0][2]]
            else:
                rot_euler = rot.to_euler(my_rotation_mode)
        for i in range(3):
            channel_location[i].keyframe_points[frame_counter].co = (key_frame, loc[i])
            channel_location[i].keyframe_points[frame_counter].interpolation = 'LINEAR'
        if my_rotation_mode == 'QUATERNION':
            for i in range(4):
                channel_rotation[i].keyframe_points[frame_counter].co = (key_frame, rot[i])
                channel_rotation[i].keyframe_points[frame_counter].interpolation = 'LINEAR'
        elif my_rotation_mode == 'AXIS_ANGLE':
            for i in range(4):
                channel_rotation[i].keyframe_points[frame_counter].co = (key_frame, rot_axis_angle[i])
                channel_rotation[i].keyframe_points[frame_counter].interpolation = 'LINEAR'
        else:
            for i in range(3):
                channel_rotation[i].keyframe_points[frame_counter].co = (key_frame, rot_euler[i])
                channel_rotation[i].keyframe_points[frame_counter].interpolation = 'LINEAR'
        for i in range(3):
            channel_scale[i].keyframe_points[frame_counter].co = (key_frame, sca[i])
            channel_scale[i].keyframe_points[frame_counter].interpolation = 'LINEAR'


def get_pose_list(pose_key_dic, node, action_name):
    if node != None and 'PoseKey' in node:
        action_list = node['PoseKey']
        for action in action_list:
            if action_name == action[0]:
                action_index = action[1]
                return pose_key_dic[action_index]
    return None


def make_pose_key_dic(context, hierarchy_dic, node_dic, bind_pose_dic, pose_key_dic, my_rotation_mode):
    for (key, hierarchy) in hierarchy_dic.items():
        if hierarchy[0] != 'BONE':
            node = node_dic[key]
            parent_key = hierarchy[2]
            # ignore object attached to bone
            if parent_key != str(-1) and hierarchy_dic[parent_key][0] == 'BONE':
                continue
            # ignore skinned mesh
            if hierarchy[0] == 'MESH' and 'Weight' in node:
                continue
            parent_node = node_dic[parent_key] if parent_key != str(-1) else None
            ob = node['Object']
            if 'PoseKey' in node:
                action_list = node['PoseKey']
                for action in action_list:
                    action_name = action[0]
                    action_index = action[1]
                    pose_list = pose_key_dic[action_index]
                    # create action
                    action_ob = bpy.data.actions.new(name=action_name)
                    action_ob.id_root = 'OBJECT'
                    # fill action
                    parent_pose_list = get_pose_list(pose_key_dic, parent_node, action_name)
                    ob_bind_pose = bind_pose_dic[node['BindPose'][0][1]]
                    ob_parent_bind_pose = bind_pose_dic[parent_node['BindPose'][0][1]] if parent_node != None else None
                    make_fcurves_list(action_ob, ob, ob_parent_bind_pose, ob_bind_pose, parent_pose_list, pose_list, None, ob.type, my_rotation_mode)
                    # create animation data and set default action if not exists
                    if ob.animation_data == None:
                        ob.animation_data_create()
                        ob.animation_data.action = action_ob
                    if hierarchy[0] == 'ARMATURE':
                        armature_key = key
                        armature_node = node_dic[armature_key]
                        for (key2, hierarchy2) in hierarchy_dic.items():
                            if hierarchy2[0] == 'BONE':
                                bone_key = key2
                                tokens = bone_key.split(".")
                                # same armature
                                if len(tokens) == 2 and tokens[0] == armature_key:
                                    bone_node = node_dic[bone_key]
                                    bone_parent_key = hierarchy2[2]
                                    bone_parent_node = node_dic[bone_parent_key]
                                    bone_ob = ob.pose.bones[bone_node['ObjectName']]
                                    if 'PoseKey' in bone_node:
                                        bone_action_list = bone_node['PoseKey']
                                        for bone_action in bone_action_list:
                                            bone_action_name = bone_action[0]
                                            # same action
                                            if bone_action_name == action_name:
                                                bone_action_index = bone_action[1]
                                                bone_pose_list = pose_key_dic[bone_action_index]
                                                # fill action
                                                bone_parent_pose_list = get_pose_list(pose_key_dic, bone_parent_node, bone_action_name)
                                                bone_ob_bind_pose = bind_pose_dic[bone_node['BindPose'][0][1]]
                                                bone_ob_parent_bind_pose = bind_pose_dic[bone_parent_node['BindPose'][0][1]]
                                                make_fcurves_list(action_ob, bone_ob, bone_ob_parent_bind_pose, bone_ob_bind_pose, bone_parent_pose_list, bone_pose_list, bone_node['CorrectPose'] if 'CorrectPose' in bone_node else None, None, my_rotation_mode)


def make_shape_key_dic(context, hierarchy_dic, node_dic, bind_pose_dic, shape_key_dic):
    for (key, hierarchy) in hierarchy_dic.items():
        if hierarchy[0] == 'MESH':
            node = node_dic[key]
            ob = node['Object']
            if 'ShapeKey' in node:
                # no shape key yet
                if ob.data.shape_keys.animation_data == None:
                    action_list = node['ShapeKey']
                    for action in action_list:
                        action_name = action[0]
                        action_index = action[1]
                        # create action
                        action_ob = bpy.data.actions.new(name=action_name)
                        action_ob.id_root = 'KEY'
                        # create animation data and set default action if not exists
                        if ob.data.shape_keys.animation_data == None:
                            ob.data.shape_keys.animation_data_create()
                            ob.data.shape_keys.animation_data.action = action_ob
                        channel_value = []
                        for block in ob.data.shape_keys.key_blocks:
                            channel_value.append(action_ob.fcurves.new(data_path=block.path_from_id("value")))
                            channel_value[-1].keyframe_points.add(len(shape_key_dic[action_index]))
                        for (i, shape_key) in enumerate(shape_key_dic[action_index]):
                            for j in range(1, len(shape_key), 1):
                                channel_value[shape_key[j][0]].keyframe_points[i].co = (shape_key[0], shape_key[j][1])
                                channel_value[shape_key[j][0]].keyframe_points[i].interpolation = 'LINEAR'


def make_vertex_animation(context, hierarchy_dic, node_dic, exist_object_dic):
    for (key, hierarchy) in hierarchy_dic.items():
        if hierarchy[0] == 'MESH':
            node = node_dic[key]
            ob = node['Object']
            if 'VertexPoseKey' in node:
                mesh_cache_exist = False
                for mod in ob.modifiers:
                    if type(mod) == bpy.types.MeshCacheModifier:
                        mesh_cache_exist = True
                        break
                if not mesh_cache_exist:
                    mod = ob.modifiers.new("", 'MESH_CACHE')
                    mod.cache_format = 'PC2'
                    mod.forward_axis = 'POS_Y'
                    mod.up_axis = 'POS_Z'
                    mod.filepath = node['VertexPoseKey'][0][0]


def parse_frame_rate(tokens):
    return int(tokens[1].strip(" \t"))


def parse_hierarchy_dic(hierarchy_dic, tokens):
    hierarchy_dic[tokens[1].strip(" \t")] = [tokens[2].strip(" \t"), tokens[3].strip(" \t"), tokens[4].strip(" \t")]


def parse_node_dic(node_dic, tokens):
    key = tokens[1].strip(" \t")
    if key not in node_dic:
        node_dic[key] = {}
    key2 = tokens[2].strip(" \t")
    if key2 not in node_dic[key]:
        node_dic[key][key2] = []
    node_dic[key][key2].append([tokens[3].strip(" \t"), int(tokens[4].strip(" \t"))])


def parse_default_pose_dic(default_pose_dic, tokens):
    default_pose_dic[int(tokens[1].strip(" \t"))] = [float(token.strip(" \t")) for token in tokens[2:]]


def parse_bind_pose_dic(bind_pose_dic, tokens):
    bind_pose_dic[int(tokens[1].strip(" \t"))] = [float(token.strip(" \t")) for token in tokens[2:]]


def parse_pose_key_dic(pose_key_dic, tokens):
    key = int(tokens[1].strip(" \t"))
    if key not in pose_key_dic:
        length = int(tokens[3].strip(" \t"))
        pose_key_dic[key] = [None] * length
    pose_key_dic[key][int(tokens[2].strip(" \t"))] = [int(tokens[4].strip(" \t"))] + [float(token.strip(" \t")) for token in tokens[5:]]


def parse_shape_key_dic(shape_key_dic, tokens):
    key = int(tokens[1].strip(" \t"))
    if key not in shape_key_dic:
        length = int(tokens[3].strip(" \t"))
        shape_key_dic[key] = [None] * length
    shape_key_dic[key][int(tokens[2].strip(" \t"))] = [int(tokens[4].strip(" \t"))] + [(int(tokens[i].strip(" \t")), float(tokens[i+1].strip(" \t"))) for i in range(5, len(tokens), 2)]


def parse_vertex_dic(vertex_dic, tokens):
    key = int(tokens[1].strip(" \t"))
    if key not in vertex_dic:
        length = int(tokens[3].strip(" \t"))
        vertex_dic[key] = [None] * length
    vertex_dic[key][int(tokens[2].strip(" \t"))] = [float(token.strip(" \t")) for token in tokens[4:]]


def parse_weight_dic(weight_dic, tokens):
    key = int(tokens[1].strip(" \t"))
    if key not in weight_dic:
        length = int(tokens[3].strip(" \t"))
        weight_dic[key] = [None] * length
    weight_dic[key][int(tokens[2].strip(" \t"))] = [(tokens[i].strip(" \t"), float(tokens[i+1].strip(" \t"))) for i in range(4, len(tokens), 2)]


def parse_shape_dic(shape_dic, tokens):
    shape_dic[int(tokens[1].strip(" \t"))] = [(int(tokens[i].strip(" \t")), float(tokens[i+1].strip(" \t")), float(tokens[i+2].strip(" \t")), float(tokens[i+3].strip(" \t"))) for i in range(2, len(tokens), 4)]


def parse_polygon_dic(polygon_dic, tokens):
    key = int(tokens[1].strip(" \t"))
    if key not in polygon_dic:
        length = int(tokens[3].strip(" \t"))
        polygon_dic[key] = [None] * length
    polygon_dic[key][int(tokens[2].strip(" \t"))] = [int(token.strip(" \t")) for token in tokens[4:]]


def parse_texture_dic(texture_dic, tokens):
    texture_dic[int(tokens[1].strip(" \t"))] = [tokens[2].strip(" \t")]


def parse_material_dic(material_dic, tokens):
    material_dic[int(tokens[1].strip(" \t"))] = []
    material_dic[int(tokens[1].strip(" \t"))].append(tokens[2].strip(" \t"))
    for i in range(0, 40, 4):
        material_dic[int(tokens[1].strip(" \t"))].append(float(tokens[i+3].strip(" \t")))
        material_dic[int(tokens[1].strip(" \t"))].append(float(tokens[i+4].strip(" \t")))
        material_dic[int(tokens[1].strip(" \t"))].append(float(tokens[i+5].strip(" \t")))
        material_dic[int(tokens[1].strip(" \t"))].append(int(tokens[i+6].strip(" \t")))
    material_dic[int(tokens[1].strip(" \t"))].append(int(tokens[43].strip(" \t")))


def parse_mesh_material_dic(mesh_material_dic, tokens):
    mesh_material_dic[int(tokens[1].strip(" \t"))] = [int(token.strip(" \t")) for token in tokens[2:]]


def parse_uv_dic(uv_dic, tokens, max_uv):
    key = int(tokens[1].strip(" \t"))
    if key not in uv_dic:
        length = int(tokens[3].strip(" \t"))
        uv_dic[key] = [None] * length
    index = int(tokens[2].strip(" \t"))
    uv_dic[key][index] = []
    for i in range(4, len(tokens), 2):
        uv = (float(tokens[i].strip(" \t")), float(tokens[i+1].strip(" \t")))
        # Add UV to uvlist
        uv_dic[key][index].append(uv)
        # get maximum UV
        if uv[0] > max_uv[0]:
            max_uv[0] = uv[0]
        if uv[1] > max_uv[1]:
            max_uv[1] = uv[1]


def parse_normal_dic(normal_dic, tokens):
    key = int(tokens[1].strip(" \t"))
    if key not in normal_dic:
        length = int(tokens[3].strip(" \t"))
        normal_dic[key] = [None] * length
    normal_dic[key][int(tokens[2].strip(" \t"))] = [(float(tokens[i].strip(" \t")), float(tokens[i+1].strip(" \t")), float(tokens[i+2].strip(" \t"))) for i in range(4, len(tokens), 3)]


def parse_color_dic(color_dic, tokens):
    key = int(tokens[1].strip(" \t"))
    if key not in color_dic:
        length = int(tokens[3].strip(" \t"))
        color_dic[key] = [None] * length
    color_dic[key][int(tokens[2].strip(" \t"))] = [(float(tokens[i].strip(" \t")), float(tokens[i+1].strip(" \t")), float(tokens[i+2].strip(" \t")), float(tokens[i+3].strip(" \t"))) for i in range(4, len(tokens), 4)]


def parse_polygon_material_dic(polygon_material_dic, tokens):
    key = int(tokens[1].strip(" \t"))
    if key not in polygon_material_dic:
        length = int(tokens[3].strip(" \t"))
        polygon_material_dic[key] = [None] * length
    polygon_material_dic[key][int(tokens[2].strip(" \t"))] = int(tokens[4].strip(" \t"))


def parse_camera_dic(camera_dic, tokens):
    camera_dic[int(tokens[1].strip(" \t"))] = [tokens[2].strip(" \t"), float(tokens[3].strip(" \t")), float(tokens[4].strip(" \t")), float(tokens[5].strip(" \t")), float(tokens[6].strip(" \t")), tokens[7].strip(" \t"), float(tokens[8].strip(" \t")), float(tokens[9].strip(" \t")), float(tokens[10].strip(" \t")), float(tokens[11].strip(" \t")), float(tokens[12].strip(" \t")), float(tokens[13].strip(" \t"))]


def parse_light_dic(light_dic, tokens):
    light_dic[int(tokens[1].strip(" \t"))] = [tokens[2].strip(" \t"), float(tokens[3].strip(" \t")), float(tokens[4].strip(" \t")), float(tokens[5].strip(" \t")), float(tokens[6].strip(" \t"))]


def parse_custom_property_dic(custom_property_dic, tokens):
    key = int(tokens[1].strip(" \t"))
    if key not in custom_property_dic:
        length = int(tokens[3].strip(" \t"))
        custom_property_dic[key] = [None] * length
    custom_property_dic[key][int(tokens[2].strip(" \t"))] = [token.strip(" \t") for token in tokens[4:]]


def parse_edge_crease_dic(edge_crease_dic, tokens):
    key = int(tokens[1].strip(" \t"))
    if key not in edge_crease_dic:
        length = int(tokens[3].strip(" \t"))
        edge_crease_dic[key] = [None] * length
    edge_crease_dic[key][int(tokens[2].strip(" \t"))] = [int(tokens[4].strip(" \t")), int(tokens[5].strip(" \t")), float(tokens[6].strip(" \t"))]


def parse_edge_smoothing_dic(edge_smoothing_dic, tokens):
    key = int(tokens[1].strip(" \t"))
    if key not in edge_smoothing_dic:
        length = int(tokens[3].strip(" \t"))
        edge_smoothing_dic[key] = [None] * length
    edge_smoothing_dic[key][int(tokens[2].strip(" \t"))] = [int(tokens[4].strip(" \t")), int(tokens[5].strip(" \t"))]


def parse_ik_dic(ik_dic, tokens):
    key = int(tokens[1].strip(" \t"))
    ik_dic[key] = [tokens[2].strip(" \t"), tokens[3].strip(" \t"), int(tokens[4].strip(" \t"))]


def read_some_data(context, filepath, my_leaf_bone, my_import_normal, my_shade_mode, use_auto_smooth, my_angle, use_auto_bone_orientation, my_bone_length, my_calculate_roll, use_vertex_animation, use_edge_crease, my_edge_crease_scale, my_edge_smoothing, use_import_materials, obj_name, my_rotation_mode, use_fix_bone_poses):
    print("running read_some_data...")
    print("="*30)
    frame_rate = 30
    hierarchy_dic = {}
    node_dic = {}
    default_pose_dic = {}
    bind_pose_dic = {}
    pose_key_dic = {}
    shape_key_dic = {}
    vertex_dic = {}
    weight_dic = {}
    shape_dic = {}
    polygon_dic = {}
    texture_dic = {}
    material_dic = {}
    mesh_material_dic = {}
    uv_dic = {}
    normal_dic = {}
    color_dic = {}
    polygon_material_dic = {}
    exist_object_dic = {}
    camera_dic = {}
    light_dic = {}
    custom_property_dic = {}
    edge_crease_dic = {}
    edge_smoothing_dic = {}
    ik_dic = {}
    max_uv = [0.0, 0.0]
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip(" \t\r\n")
            # ignore empty line
            if len(line) == 0:
                continue
            # ignore comment line
            if line.startswith("#"):
                continue
            # section line
            if line.startswith("[") and line.endswith("]"):
                line = line[1:-1]
                tokens = line.split(",")
                for i in range(len(tokens)):
                    tokens[i] = tokens[i].replace("\\;", ",")
                if len(tokens) > 0:
                    section = tokens[0]
                    # parse frame rate
                    if section == "FrameRate":
                        # validate data length
                        if len(tokens) == 2:
                            frame_rate = parse_frame_rate(tokens)
                    # parse hierarchy dictionary
                    elif section == "Hierarchy":
                        # validate data length
                        if len(tokens) == 5:
                            parse_hierarchy_dic(hierarchy_dic, tokens)
                    # parse node dictionary
                    elif section == "Node":
                        # validate data length
                        if len(tokens) == 5:
                            parse_node_dic(node_dic, tokens)
                    # parse default pose dictionary
                    elif section == "DefaultPose":
                        # validate data length
                        if len(tokens) == 18:
                            parse_default_pose_dic(default_pose_dic, tokens)
                    # parse bind pose dictionary
                    elif section == "BindPose":
                        # validate data length
                        if len(tokens) == 18:
                            parse_bind_pose_dic(bind_pose_dic, tokens)
                    # parse pose key dictionary
                    elif section == "PoseKey":
                        # validate data length
                        if len(tokens) == 21:
                            parse_pose_key_dic(pose_key_dic, tokens)
                    # parse shape key dictionary
                    elif section == "ShapeKey":
                        # validate data length
                        if len(tokens) >= 5:
                            parse_shape_key_dic(shape_key_dic, tokens)
                    # parse vertex dictionary
                    elif section == "Vertex":
                        # validate data length
                        if len(tokens) == 7:
                            parse_vertex_dic(vertex_dic, tokens)
                    # parse weight dictionary
                    elif section == "Weight":
                        # validate data length
                        if len(tokens) >= 4:
                            parse_weight_dic(weight_dic, tokens)
                    # parse shape dictionary
                    elif section == "Shape":
                        # validate data length
                        if len(tokens) >= 2:
                            parse_shape_dic(shape_dic, tokens)
                    # parse polygon dictionary
                    elif section == "Polygon":
                        # validate data length
                        if len(tokens) >= 4:
                            parse_polygon_dic(polygon_dic, tokens)
                    # parse texture dictionary
                    elif section == "Texture":
                        # validate data length
                        if len(tokens) == 3:
                            parse_texture_dic(texture_dic, tokens)
                    # parse material dictionary
                    elif section == "Material":
                        # validate data length
                        if len(tokens) == 44:
                            parse_material_dic(material_dic, tokens)
                    # parse mesh material dictionary
                    elif section == "MeshMaterial":
                        # validate data length
                        if len(tokens) >= 2:
                            parse_mesh_material_dic(mesh_material_dic, tokens)
                    # parse uv dictionary
                    elif section == "UV":
                        # validate data length
                        if len(tokens) >= 4:
                            parse_uv_dic(uv_dic, tokens, max_uv)
                    # parse normal dictionary
                    elif section == "Normal":
                        # validate data length
                        if len(tokens) >= 4:
                            parse_normal_dic(normal_dic, tokens)
                    # parse color dictionary
                    elif section == "Color":
                        # validate data length
                        if len(tokens) >= 4:
                            parse_color_dic(color_dic, tokens)
                    # parse polygon material dictionary
                    elif section == "PolygonMaterial":
                        # validate data length
                        if len(tokens) == 5:
                            parse_polygon_material_dic(polygon_material_dic, tokens)
                    # parse camera dictionary
                    elif section == "Camera":
                        # validate data length
                        if len(tokens) == 14:
                            parse_camera_dic(camera_dic, tokens)
                    # parse light dictionary
                    elif section == "Light":
                        # validate data length
                        if len(tokens) == 7:
                            parse_light_dic(light_dic, tokens)
                    # parse custom property dictionary
                    elif section == "CustomProperty":
                        # validate data length
                        if len(tokens) >= 7 and len(tokens) <= 10:
                            parse_custom_property_dic(custom_property_dic, tokens)
                    # parse edge crease dictionary
                    elif section == "EdgeCrease":
                        # validate data length
                        if len(tokens) == 7:
                            parse_edge_crease_dic(edge_crease_dic, tokens)
                    # parse edge smoothing dictionary
                    elif section == "EdgeSmoothing":
                        # validate data length
                        if len(tokens) == 6:
                            parse_edge_smoothing_dic(edge_smoothing_dic, tokens)
                    # parse IK dictionary
                    elif section == "IK":
                        # validate data length
                        if len(tokens) == 5:
                            parse_ik_dic(ik_dic, tokens)
    # set frame rate
    context.scene.render.fps = frame_rate
    # make texture dic
    make_texture_dic(context, texture_dic, max_uv)
    # make material dic
    if use_import_materials:
        make_material_dic(context, texture_dic, material_dic, custom_property_dic)
    # make dummy dic
    make_dummy_dic(context, hierarchy_dic, node_dic, bind_pose_dic, my_rotation_mode)
    # make camera dic
    make_camera_dic(context, hierarchy_dic, node_dic, bind_pose_dic, camera_dic, my_rotation_mode)
    # make light dic
    make_light_dic(context, hierarchy_dic, node_dic, bind_pose_dic, light_dic, my_rotation_mode)
    # make mesh dic
    make_mesh_dic(context, hierarchy_dic, node_dic, bind_pose_dic, vertex_dic, polygon_dic, uv_dic, color_dic, normal_dic, polygon_material_dic, mesh_material_dic, material_dic, exist_object_dic, my_import_normal, my_shade_mode, use_auto_smooth, my_angle, edge_crease_dic, use_edge_crease, my_edge_crease_scale, my_edge_smoothing, edge_smoothing_dic, use_import_materials, obj_name, my_rotation_mode)
    # make shape dic
    make_shape_dic(context, hierarchy_dic, node_dic, shape_dic)
    # make armature dic
    make_armature_dic(context, hierarchy_dic, node_dic, bind_pose_dic, my_leaf_bone, use_auto_bone_orientation, my_bone_length, my_calculate_roll, obj_name, my_rotation_mode)
    # make hierarchy dic
    make_hierarchy_dic(context, hierarchy_dic, node_dic, default_pose_dic, bind_pose_dic)
    # fix bind pose for nodes which attach to bones from default pose
    fix_bind_pose(context, hierarchy_dic, node_dic, default_pose_dic, bind_pose_dic)
    # bind mesh to armature
    bind_mesh_to_armature(context, hierarchy_dic, node_dic, weight_dic)
    # reset all matrix parent inverses
    reset_all_matrix_parent_inverses(context, hierarchy_dic, node_dic)
    # set default pose, may have bug, use at your own risk!!!
    if use_fix_bone_poses:
        set_default_pose(context, hierarchy_dic, node_dic, default_pose_dic)
    # make pose key dic
    make_pose_key_dic(context, hierarchy_dic, node_dic, bind_pose_dic, pose_key_dic, my_rotation_mode)
    # make shape key dic
    make_shape_key_dic(context, hierarchy_dic, node_dic, bind_pose_dic, shape_key_dic)
    # make vertex animation
    if use_vertex_animation:
        make_vertex_animation(context, hierarchy_dic, node_dic, exist_object_dic)
    # make custom property dic
    make_custom_property_dic(context, hierarchy_dic, node_dic, custom_property_dic)
    # make IK dic
    make_ik_dic(context, hierarchy_dic, node_dic, ik_dic)
    # set visibility
    for node in node_dic.values():
        if 'Object' in node:
            ob = node['Object']
            if 'Visibility' in node:
                hide_viewport = node['Visibility'][0][1] == 0
                if bpy.app.version < (2, 80):
                    if hasattr(ob, 'hide'):
                        ob.hide = hide_viewport
                else:
                    if hasattr(ob, 'hide_viewport'):
                        ob.hide_viewport = hide_viewport
    print("="*30)

    return {'FINISHED'}


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class BetterImportFbx(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "better_import.fbx"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Better Import FBX"
    bl_options = {'UNDO', 'PRESET'}

    @classmethod
    def poll(self, context):
        return context.mode == 'OBJECT'


    # ImportHelper mixin class uses this
    filename_ext = ".fbx"

    filter_glob: StringProperty(
            default="*.fbx;*.dae;*.obj;*.dxf;*.3ds",
            options={'HIDDEN'},
            maxlen=255,  # Max internal buffer length, longer would be clamped.
            )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    files: CollectionProperty(
            name="File Path",
            type=bpy.types.OperatorFileListElement,
            )

    use_auto_bone_orientation: BoolProperty(
            name="Automatic Bone Orientation",
            description="Automatically sort bones orientations, if you want to preserve the original armature, please disable the option",
            default=True,
            )

    my_calculate_roll: EnumProperty(
            name="Calculate Roll",
            description="Automatically fix alignment of imported bones’ axes when 'Automatic Bone Orientation' is enabled",
            items=(('POS_X', "POS_X", "POS_X"),
                   ('POS_Z', "POS_Z", "POS_Z"),
                   ('GLOBAL_POS_X', "GLOBAL_POS_X", "GLOBAL_POS_X"),
                   ('GLOBAL_POS_Y', "GLOBAL_POS_Y", "GLOBAL_POS_Y"),
                   ('GLOBAL_POS_Z', "GLOBAL_POS_Z", "GLOBAL_POS_Z"),
                   ('NEG_X', "NEG_X", "NEG_X"),
                   ('NEG_Z', "NEG_Z", "NEG_Z"),
                   ('GLOBAL_NEG_X', "GLOBAL_NEG_X", "GLOBAL_NEG_X"),
                   ('GLOBAL_NEG_Y', "GLOBAL_NEG_Y", "GLOBAL_NEG_Y"),
                   ('GLOBAL_NEG_Z', "GLOBAL_NEG_Z", "GLOBAL_NEG_Z"),
                   ('ACTIVE', "ACTIVE", "ACTIVE"),
                   ('VIEW', "VIEW", "VIEW"),
                   ('CURSOR', "CURSOR", "CURSOR"),
                   ('None', "None", "Does not fix alignment of imported bones’ axes")),
            default='None',
            )

    my_bone_length: FloatProperty(
        name = "Bone Length",
        description = "Bone length when 'Automatic Bone Orientation' is disabled",
        default = 10.0,
        min = 0.0001,
        max = 10000.0)

    my_leaf_bone: EnumProperty(
            name="Leaf Bone",
            description="The length of leaf bone",
            items=(('Long', "Long", "1/1 length of its parent"),
                   ('Short', "Short", "1/10 length of its parent")),
            default='Long',
            )

    use_fix_bone_poses: BoolProperty(
            name="Fix Bone Poses",
            description="Try fixing bone poses with default poses whenever bind poses are not equal to default poses",
            default=False,
            )

    use_fix_attributes: BoolProperty(
            name="Fix Attributes For Unity & C4D",
            description="Try fixing null attributes for Unity's FBX exporter & C4D's FBX exporter, but it may bring extra fake bones",
            default=False,
            )

    use_only_deform_bones: BoolProperty(
            name="Only Deform Bones",
            description="Import only deform bones",
            default=False,
            )

    use_vertex_animation: BoolProperty(
            name="Vertex Animation",
            description="Import vertex animation",
            default=True,
            )

    use_animation: BoolProperty(
            name="Animation",
            description="Import animation",
            default=True,
            )

    use_triangulate: BoolProperty(
            name="Triangulate",
            description="Triangulate meshes",
            default=False,
            )

    my_import_normal: EnumProperty(
            name="Normal",
            description="How to get normals",
            items=(('Calculate', "Calculate", "Let Blender generate normals"),
                   ('Import', "Import", "Use imported normals")),
            default='Import',
            )

    use_auto_smooth: BoolProperty(
            name="Auto Smooth",
            description="Auto smooth (based on smooth/sharp faces/edges and angle between faces)",
            default=True,
            )

    my_angle: FloatProperty(
        name = "Angle",
        description = "Maximum angle between face normals that will be considered as smooth",
        default = 60.0,
        min = 0.0,
        max = 180.0)

    my_shade_mode: EnumProperty(
            name="Shading",
            description="How to render and display faces",
            items=(('Smooth', "Smooth", "Render and display faces smooth, using interpolated vertex normals"),
                   ('Flat', "Flat", "Render and display faces uniform, using face normals")),
            default='Smooth',
            )

    my_scale: FloatProperty(
        name = "Scale",
        description = "Scale all data",
        default = 0.01,
        min = 0.0001,
        max = 10000.0)

    use_optimize_for_blender: BoolProperty(
            name="Optimize For Blender",
            description="Make Blender friendly rotation and scale. This is an experimental feature, which may has bugs, use at your own risk",
            default=False,
            )

    use_reset_mesh_origin: BoolProperty(
            name="Reset Mesh Origin",
            description="Reset mesh origin to zero",
            default=True,
            )

    use_edge_crease: BoolProperty(
            name="Edge Crease",
            description="Import edge crease",
            default=True,
            )

    my_edge_crease_scale: FloatProperty(
        name = "Edge Crease Scale",
        description = "Scale of the edge crease value",
        default = 1.0,
        min = 0.0001,
        max = 10000.0)

    my_edge_smoothing: EnumProperty(
            name="Smoothing Groups",
            description="How to generate smoothing groups",
            items=(('None', "None", "Does not generate smoothing groups"),
                   ('Import', "Import From File", "Import smoothing groups from file"),
                   ('FBXSDK', "Generate By FBX SDK", "Generate smoothing groups from normals by FBX SDK"),
                   ('Blender', "Generate By Blender", "Generate smoothing groups from normals by Blender")),
            default='FBXSDK',
            )

    use_import_materials: BoolProperty(
            name="Import Materials",
            description="Import materials for meshes, if you don't want to import any materials, you can turn off this option",
            default=True,
            )

    use_rename_by_filename: BoolProperty(
            name="Rename By Filename",
            description="If you want to import a lot of 3d models or armatures in batch, and there is only one mesh or one armature per file, you may turn on this option to rename the imported meshes or armatures by their filenames",
            default=False,
            )

    my_rotation_mode: EnumProperty(
            name="Rotation Mode",
            description="Rotation mode of all objects",
            items=(('QUATERNION', "Quaternion (WXYZ)", "Quaternion (WXYZ), No Gimbal Lock"),
                   ('XYZ', "XYZ Euler", "XYZ Rotation Order - prone to Gimbal Lock"),
                   ('XZY', "XZY Euler", "XZY Rotation Order - prone to Gimbal Lock"),
                   ('YXZ', "YXZ Euler", "YXZ Rotation Order - prone to Gimbal Lock"),
                   ('YZX', "YZX Euler", "YZX Rotation Order - prone to Gimbal Lock"),
                   ('ZXY', "ZXY Euler", "ZXY Rotation Order - prone to Gimbal Lock"),
                   ('ZYX', "ZYX Euler", "ZYX Rotation Order - prone to Gimbal Lock"),
                   ('AXIS_ANGLE', "Axis Angle", "Axis Angle (W+XYZ), defines a rotation around some axis defined by 3D-Vector")),
            default='QUATERNION',
            )

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Basic Options:")
        box.prop(self, 'my_rotation_mode')
        box.prop(self, 'my_import_normal')
        box.prop(self, 'use_auto_smooth')
        box.prop(self, 'my_angle')
        box.prop(self, 'my_shade_mode')
        box.prop(self, 'my_scale')

        box = layout.box()
        box.label(text="Blender Options: (Experimental)")
        box.prop(self, 'use_optimize_for_blender')
        box.prop(self, 'use_reset_mesh_origin')

        box = layout.box()
        box.label(text="Bone Options:")
        box.prop(self, 'use_auto_bone_orientation')
        box.prop(self, 'my_calculate_roll')
        box.prop(self, 'my_bone_length')
        box.prop(self, 'my_leaf_bone')
        box.prop(self, 'use_fix_bone_poses')
        box.prop(self, 'use_fix_attributes')
        box.prop(self, 'use_only_deform_bones')

        box = layout.box()
        box.label(text="Animation Options:")
        box.prop(self, 'use_animation')

        box = layout.box()
        box.label(text="Vertex Animation Options:")
        box.prop(self, 'use_vertex_animation')

        box = layout.box()
        box.label(text="Mesh Options:")
        box.prop(self, 'use_triangulate')
        box.prop(self, 'use_import_materials')
        box.prop(self, 'use_rename_by_filename')

        box = layout.box()
        box.label(text="Edge Options:")
        box.prop(self, 'my_edge_smoothing')
        box.prop(self, 'use_edge_crease')
        box.prop(self, 'my_edge_crease_scale')


    def execute(self, context):
        # do the job in background
        executable_path = None
        if platform.system() == 'Windows':
            if platform.machine().endswith('64'):
                executable_path = os.path.join(os.path.dirname(__file__), "bin", platform.system(), "x64", "fbx-utility")
            else:
                executable_path = os.path.join(os.path.dirname(__file__), "bin", platform.system(), "x86", "fbx-utility")
        else:
            if platform.system() == 'Linux':
                glibc_version = os.confstr('CS_GNU_LIBC_VERSION').split(" ")
                if glibc_version[0] == 'glibc' and glibc_version[1] >= '2.29':
                    executable_path = os.path.join(os.path.dirname(__file__), "bin", platform.system(), "fbx-utility")
                else:
                    executable_path = os.path.join(os.path.dirname(__file__), "bin", platform.system(), "fbx-utility2")
            elif platform.system() == 'Darwin':
                if platform.mac_ver()[0] >= '10.15':
                    executable_path = os.path.join(os.path.dirname(__file__), "bin", platform.system(), "fbx-utility")
                elif platform.mac_ver()[0] >= '10.13':
                    executable_path = os.path.join(os.path.dirname(__file__), "bin", platform.system(), "fbx-utility2")
                else:
                    executable_path = os.path.join(os.path.dirname(__file__), "bin", platform.system(), "fbx-utility3")
            # chmod
            if not os.access(executable_path, os.X_OK):
                os.chmod(executable_path, 0o755)

        # delete deprecated output path
        deprecated_output_path = os.path.join(os.path.dirname(__file__), "data", "untitled-fbx.txt")
        if os.path.exists(deprecated_output_path):
            os.remove(deprecated_output_path)

        # write to inner format
        output_path = os.path.join(os.path.dirname(__file__), "data", uuid.uuid4().hex + ".txt")

        if self.files:
            dirname = os.path.dirname(self.filepath)
            for file in self.files:
                path = os.path.join(dirname, file.name)
                result = subprocess.run([executable_path, path, output_path, str(self.my_scale), "None", "None", "None", "True" if self.use_only_deform_bones else "False", "True" if self.use_animation else "False", "None", "None", "True" if self.use_reset_mesh_origin else "False", "True" if self.use_fix_attributes else "False", "True" if self.use_triangulate else "False", "True" if self.use_optimize_for_blender else "False", self.my_edge_smoothing, "None", "None", "None"])
                if result.returncode != 0:
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    return {'CANCELLED'}
                result = read_some_data(context, output_path, self.my_leaf_bone, self.my_import_normal, self.my_shade_mode, self.use_auto_smooth, self.my_angle, self.use_auto_bone_orientation, self.my_bone_length, self.my_calculate_roll, self.use_vertex_animation, self.use_edge_crease, self.my_edge_crease_scale, self.my_edge_smoothing, self.use_import_materials, file.name[:file.name.rfind(".")] if self.use_rename_by_filename else None, self.my_rotation_mode, self.use_fix_bone_poses)
                if result != {'FINISHED'}:
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    return {'CANCELLED'}
            if os.path.exists(output_path):
                os.remove(output_path)
            return {'FINISHED'}
        else:
            result = subprocess.run([executable_path, self.filepath, output_path, str(self.my_scale), "None", "None", "None", "True" if self.use_only_deform_bones else "False", "True" if self.use_animation else "False", "None", "None", "True" if self.use_reset_mesh_origin else "False", "True" if self.use_fix_attributes else "False", "True" if self.use_triangulate else "False", "True" if self.use_optimize_for_blender else "False", self.my_edge_smoothing, "None", "None", "None"])
            if result.returncode != 0:
                if os.path.exists(output_path):
                    os.remove(output_path)
                return {'CANCELLED'}
            result = read_some_data(context, output_path, self.my_leaf_bone, self.my_import_normal, self.my_shade_mode, self.use_auto_smooth, self.my_angle, self.use_auto_bone_orientation, self.my_bone_length, self.my_calculate_roll, self.use_vertex_animation, self.use_edge_crease, self.my_edge_crease_scale, self.my_edge_smoothing, self.use_import_materials, None, self.my_rotation_mode, self.use_fix_bone_poses)
            if os.path.exists(output_path):
                os.remove(output_path)
            return result


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(BetterImportFbx.bl_idname, text="Better FBX Importer (.fbx/.dae/.obj/.dxf/.3ds)")


def register_importer():
    bpy.utils.register_class(BetterImportFbx)
    if bpy.app.version < (2, 80):
        bpy.types.INFO_MT_file_import.append(menu_func_import)
    else:
        bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister_importer():
    bpy.utils.unregister_class(BetterImportFbx)
    if bpy.app.version < (2, 80):
        bpy.types.INFO_MT_file_import.remove(menu_func_import)
    else:
        bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register_importer()

    # test call
    bpy.ops.better_import.fbx('INVOKE_DEFAULT')
