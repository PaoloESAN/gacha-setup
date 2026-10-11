"""Run with Blender --background --python tests/test_pupil_face_classification.py."""
import ast
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "setup_wizard/replace_default_materials_setup/game_default_material_replacers.py"
# Load the geometry functions without registering the add-on or loading shaders.
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
names = {"classify_pupil_faces", "setup_new_pupil_highlight_layer"}
namespace = {
    "bpy": bpy,
    "is_durin_character": lambda mesh: False,
    "remove_set_depth_nodes_from_highlight_material": lambda material: None,
}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[]), str(SOURCE), "exec"), namespace)
classify = namespace["classify_pupil_faces"]
setup = namespace["setup_new_pupil_highlight_layer"]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(ROOT / "chars/genshin/prune-witch-hunter-regalia/Avatar_Loli_Catalyst_Prune.fbx"))
pupil = bpy.data.objects["Pupil"]
outer, inner = classify(pupil)
# Prune's separate shine patches use the atlas region above the iris region.
uvs = pupil.data.uv_layers.active.data
expected_outer = {p.index for p in pupil.data.polygons if all(uvs[i].uv.y > 0.52 for i in p.loop_indices)}
assert len(expected_outer) == 32
assert outer == expected_outer, "Highlight classification includes iris faces"
assert len(inner) == 228
assert outer | inner == {p.index for p in pupil.data.polygons}
for side in (-1, 1):
    assert sum(1 for p in pupil.data.polygons if p.index in outer and sum(pupil.data.vertices[i].co.x for i in p.vertices) * side > 0) == 16
# The material replacer's >=100-face heuristic must not promote this legacy pupil.
assert len(outer) < 100

base_mat = bpy.data.materials.new("HoYoverse - Genshin New Pupil")
highlight_mat = bpy.data.materials.new("HoYoverse - Genshin Highlight")
setup(pupil)
assert pupil.data.materials[0] == base_mat
assert pupil.data.materials[1] == highlight_mat
assert {p.index for p in pupil.data.polygons if p.material_index == 1} == expected_outer
setup(pupil)
assert {p.index for p in pupil.data.polygons if p.material_index == 1} == expected_outer

# Preserve the existing full-texture UV contrast, including the original limits.
def make_eye(iris_span, shine_span):
    mesh = bpy.data.meshes.new("UV contrast test")
    mesh.from_pydata([(1,0,0),(2,0,0),(1,1,0),(1,0,-1),(2,0,-1),(1,1,-1)], [], [(0,1,2),(3,4,5)])
    mesh.update()
    obj = bpy.data.objects.new("UV contrast test", mesh)
    uv = mesh.uv_layers.new()
    for poly, span in zip(mesh.polygons, (iris_span, shine_span)):
        for i, coord in zip(poly.loop_indices, ((0,0),(span,0),(0,span))):
            uv.data[i].uv = coord
    return obj

for spans in ((1.0, 0.2), (0.71, 0.34), (0.1, 0.016)):
    obj = make_eye(*spans)
    assert classify(obj) == ({1}, {0}), spans
    bpy.data.objects.remove(obj)
print("PASS: Prune iris faces stay on the pupil material; both shine patches receive Highlight; full-texture UV classification is preserved.")
