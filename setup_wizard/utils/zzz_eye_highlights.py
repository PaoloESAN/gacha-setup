"""Assign the bundled ZZZ eye-highlight material using skinning groups."""
import re


def assign_zzz_eye_highlights(mesh_object, material):
    if material is None or mesh_object.type != 'MESH':
        return 0
    groups = set()
    for group in mesh_object.vertex_groups:
        name = re.sub(r'[^a-z0-9]', '', group.name.lower())
        if any(token in name for token in ('eyehighlight', 'eyehighliht', 'eyelight')) or re.fullmatch(r'skn[lr]highlights?', name):
            groups.add(group.index)
    if not groups:
        return 0
    vertices = {v.index for v in mesh_object.data.vertices
                if any(g.group in groups and g.weight > 0.0001 for g in v.groups)}
    polygons = [p for p in mesh_object.data.polygons if all(i in vertices for i in p.vertices)]
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
