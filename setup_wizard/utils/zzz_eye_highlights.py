"""Assign the bundled ZZZ eye-highlight material using skinning groups."""
import re


def assign_zzz_eye_highlights(mesh_object, material):
    if material is None or mesh_object.type != 'MESH':
        return 0
    groups = set()
    for group in mesh_object.vertex_groups:
        name = re.sub(r'[^a-z0-9]', '', re.sub(r'\.\d+$', '', group.name.lower()))
        if any(token in name for token in ('eyehighlight', 'eyehighliht', 'eyelight')) or re.fullmatch(r'(?:skn|bdy)[lr]highlights?(?:(?:new|better)[0-9]*)?', name):
            groups.add(group.index)
    vertices = {v.index for v in mesh_object.data.vertices
                if any(g.group in groups and g.weight > 0.0001 for g in v.groups)}
    polygons = [p for p in mesh_object.data.polygons if all(i in vertices for i in p.vertices)]
    # Original Belle has the same separate highlight geometry/UV patch as
    # her newer model, but skins it to Bdy_*_Eye instead of highlight bones.
    if not groups and 'belle' in mesh_object.name.casefold():
        uv = mesh_object.data.uv_layers.active
        eye_groups = {group.index for group in mesh_object.vertex_groups
                      if re.fullmatch(r'bdy[lr]eye', re.sub(r'[^a-z0-9]', '', group.name.lower()))}
        eye_vertices = {v.index for v in mesh_object.data.vertices
                        if any(g.group in eye_groups and g.weight > 0.1 for g in v.groups)}
        if uv and eye_vertices:
            polygons = [p for p in mesh_object.data.polygons
                        if all(i in eye_vertices for i in p.vertices)
                        and all(0.91 <= uv.data[i].uv.x <= 0.985
                                and 0.31 <= uv.data[i].uv.y <= 0.385 for i in p.loop_indices)]

    if not polygons:
        return 0
    materials = mesh_object.data.materials
    slot = next((i for i, mat in enumerate(materials) if mat == material), None)
    if slot is None:
        materials.append(material)
        slot = len(materials) - 1
    for polygon in polygons:
        polygon.material_index = slot
    return len(polygons)
