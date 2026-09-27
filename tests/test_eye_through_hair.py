import sys
import bpy
import bmesh
from pathlib import Path

# Add workspace to sys.path
workspace = Path(__file__).resolve().parent.parent
if str(workspace) not in sys.path:
    sys.path.insert(0, str(workspace))

import addon_utils
addon_utils.enable("setup_wizard", default_set=True)

print("--- Testing Eye Through Hair Operator ---")

# 1. Verify operator is registered
assert hasattr(bpy.ops.setup_wizard, "eye_through_hair"), "Operator setup_wizard.eye_through_hair is NOT registered!"
print("✔ Operator setup_wizard.eye_through_hair is registered")

# 2. Setup clean test scene
bpy.ops.object.mode_set(mode='OBJECT') if bpy.context.object and bpy.context.object.mode != 'OBJECT' else None
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

# Create a test hair object
bpy.ops.mesh.primitive_cube_add(location=(5, 0, 0))
hair_obj = bpy.context.active_object
hair_obj.name = "Character_Hair"
hair_mat = bpy.data.materials.new(name="M_Hair")
hair_mat.use_nodes = True
hair_obj.data.materials.append(hair_mat)

# Create NTE mrim outline material with use_transparency_overlap = True
mrim_mat = bpy.data.materials.new(name="mrim")
mrim_mat.use_nodes = True
if hasattr(mrim_mat, "use_transparency_overlap"):
    mrim_mat.use_transparency_overlap = True

# Create HSR Hair Mesh material
hsr_hair_mat = bpy.data.materials.new(name="StellarToon - Hair")
hsr_hair_mat.use_nodes = True
if hasattr(hsr_hair_mat, "use_transparency_overlap"):
    hsr_hair_mat.use_transparency_overlap = True

# Create HSR Hair Outlines material
hsr_hair_ol_mat = bpy.data.materials.new(name="StellarToon - Hair Outlines")
hsr_hair_ol_mat.use_nodes = True
if hasattr(hsr_hair_ol_mat, "use_transparency_overlap"):
    hsr_hair_ol_mat.use_transparency_overlap = False

# Test HSR hair transparency configuration step
from setup_wizard.geometry_nodes_setup.geometry_nodes_setups import configure_hsr_hair_transparency
configure_hsr_hair_transparency()

# Verify HSR Hair Mesh: BLENDED and use_transparency_overlap = False
if hasattr(hsr_hair_mat, "surface_render_method"):
    assert hsr_hair_mat.surface_render_method == 'BLENDED'
if hasattr(hsr_hair_mat, "blend_method"):
    assert hsr_hair_mat.blend_method == 'BLEND'
if hasattr(hsr_hair_mat, "use_transparency_overlap"):
    assert hsr_hair_mat.use_transparency_overlap is False, f"HSR Hair mesh overlap was {hsr_hair_mat.use_transparency_overlap}"
print("✔ HSR Hair Mesh setup step verified (BLENDED and use_transparency_overlap = False)!")

# Verify HSR Hair Outlines: BLENDED and use_transparency_overlap = True
if hasattr(hsr_hair_ol_mat, "surface_render_method"):
    assert hsr_hair_ol_mat.surface_render_method == 'BLENDED'
if hasattr(hsr_hair_ol_mat, "blend_method"):
    assert hsr_hair_ol_mat.blend_method == 'BLEND'
if hasattr(hsr_hair_ol_mat, "use_transparency_overlap"):
    assert hsr_hair_ol_mat.use_transparency_overlap is True, f"HSR Hair outlines overlap was {hsr_hair_ol_mat.use_transparency_overlap}"
print("✔ HSR Hair Outlines setup step verified (BLENDED and use_transparency_overlap = True)!")

# Ensure hair_mat has use_transparency_overlap = True before operator to verify it gets set to False
if hasattr(hair_mat, "use_transparency_overlap"):
    hair_mat.use_transparency_overlap = True

# Create Face mesh with pupil material containing INTERNAL Shader to RGB
bpy.ops.mesh.primitive_grid_add(x_subdivisions=4, y_subdivisions=4, location=(0, 0, 0))
face_obj = bpy.context.active_object
face_obj.name = "Character_Face"

pupil_mat = bpy.data.materials.new(name="HoYoverse - Anastasya New Pupil")
pupil_mat.use_nodes = True
nodes = pupil_mat.node_tree.nodes
links = pupil_mat.node_tree.links

highlight = nodes.new('ShaderNodeEmission')
highlight.name = "Highlight"
internal_s2rgb = nodes.new('ShaderNodeShaderToRGB')
internal_s2rgb.name = "Pupil_Internal_S2RGB"
internal_s2rgb.label = "Shader to RGB" # Note default label
mix_shader = nodes.new('ShaderNodeMixShader')
mix_shader.name = "Mix Shader"
out_mat = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')

# Wire internal chain: Highlight -> internal_s2rgb -> Alpha -> Mix Shader Factor
links.new(highlight.outputs['Emission'], internal_s2rgb.inputs['Shader'])
fac_in = mix_shader.inputs.get('Factor') or mix_shader.inputs.get('Fac') or mix_shader.inputs[0]
links.new(internal_s2rgb.outputs['Alpha'], fac_in)
links.new(highlight.outputs['Emission'], mix_shader.inputs[1])
links.new(mix_shader.outputs['Shader'], out_mat.inputs['Surface'])

face_obj.data.materials.append(pupil_mat)

# Select faces in Edit Mode
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(face_obj.data)
bm.faces.ensure_lookup_table()
for f in bm.faces: f.select = False
bm.faces[0].select = True
bm.faces[1].select = True
bmesh.update_edit_mesh(face_obj.data)

print("✔ Test scene with complex pupil material created")

# 2. Run operator
res = bpy.ops.setup_wizard.eye_through_hair()
assert res == {'FINISHED'}, f"Operator failed with result {res}"
print("✔ Operator executed successfully")

# 3. Verify duplicated material
assert len(face_obj.material_slots) == 2
st_mat = face_obj.material_slots[1].material
assert st_mat.name == "HoYoverse - Anastasya New Pupil_EyeThroughHair"

st_nodes = st_mat.node_tree.nodes
st_links = st_mat.node_tree.links

# Verify internal_s2rgb is STILL properly connected to Highlight and Mix Shader
st_internal_s2rgb = next(n for n in st_nodes if n.name == "Pupil_Internal_S2RGB")
assert st_internal_s2rgb.inputs['Shader'].is_linked, "Internal s2rgb Shader input is not linked!"
assert st_internal_s2rgb.inputs['Shader'].links[0].from_node.name == "Highlight", "Internal s2rgb input was hijacked!"
assert st_internal_s2rgb.outputs['Alpha'].is_linked, "Internal s2rgb Alpha output not linked!"
assert st_internal_s2rgb.outputs['Alpha'].links[0].to_node.name == "Mix Shader", "Internal s2rgb Alpha no longer feeds Mix Shader!"

# Verify dedicated Eye Through Hair Shader to RGB was created
st_dedicated_s2rgb = next(n for n in st_nodes if getattr(n, "label", "") == "Eye Through Hair Shader to RGB")
assert st_dedicated_s2rgb is not None, "Dedicated Eye Through Hair Shader to RGB missing!"
assert st_dedicated_s2rgb.inputs['Shader'].is_linked
assert st_dedicated_s2rgb.inputs['Shader'].links[0].from_node.name == "Mix Shader"

# Verify AOV Output Eye color is linked from DEDICATED s2rgb
aov_col = next(n for n in st_nodes if getattr(n, "aov_name", "") == "Eye color")
assert aov_col.inputs['Color'].links[0].from_node == st_dedicated_s2rgb, "Eye color AOV should come from dedicated s2rgb!"

# Verify AOV Output Eye mask is pure white and NOT linked
aov_mask = next(n for n in st_nodes if getattr(n, "aov_name", "") == "Eye mask")
assert not aov_mask.inputs['Color'].is_linked, "Eye mask Color should not have links!"
assert tuple(aov_mask.inputs['Color'].default_value)[:3] == (1.0, 1.0, 1.0)

# Verify hair material settings
if hasattr(hair_mat, "surface_render_method"):
    assert hair_mat.surface_render_method == 'BLENDED', f"Hair render method was {hair_mat.surface_render_method}"
if hasattr(hair_mat, "blend_method"):
    assert hair_mat.blend_method == 'BLEND', f"Hair blend method was {hair_mat.blend_method}"
if hasattr(hair_mat, "use_transparency_overlap"):
    assert hair_mat.use_transparency_overlap is False, f"Hair use_transparency_overlap was {hair_mat.use_transparency_overlap}"
print("✔ Hair material settings verified (BLENDED and use_transparency_overlap = False)!")

# Verify NTE mrim material settings (BLENDED, but use_transparency_overlap left untouched as True)
if hasattr(mrim_mat, "surface_render_method"):
    assert mrim_mat.surface_render_method == 'BLENDED', f"mrim render method was {mrim_mat.surface_render_method}"
if hasattr(mrim_mat, "blend_method"):
    assert mrim_mat.blend_method == 'BLEND', f"mrim blend method was {mrim_mat.blend_method}"
if hasattr(mrim_mat, "use_transparency_overlap"):
    assert mrim_mat.use_transparency_overlap is True, f"mrim use_transparency_overlap should remain True, was {mrim_mat.use_transparency_overlap}"
print("✔ NTE mrim material settings verified (BLENDED and use_transparency_overlap untouched as True)!")

# Verify HSR Hair Outlines material settings (BLENDED, and use_transparency_overlap left untouched as True)
if hasattr(hsr_hair_ol_mat, "surface_render_method"):
    assert hsr_hair_ol_mat.surface_render_method == 'BLENDED', f"HSR Hair outlines render method was {hsr_hair_ol_mat.surface_render_method}"
if hasattr(hsr_hair_ol_mat, "blend_method"):
    assert hsr_hair_ol_mat.blend_method == 'BLEND', f"HSR Hair outlines blend method was {hsr_hair_ol_mat.blend_method}"
if hasattr(hsr_hair_ol_mat, "use_transparency_overlap"):
    assert hsr_hair_ol_mat.use_transparency_overlap is True, f"HSR Hair outlines use_transparency_overlap should remain True, was {hsr_hair_ol_mat.use_transparency_overlap}"
print("✔ HSR Hair Outlines settings verified (BLENDED and use_transparency_overlap untouched as True)!")

print("✔ Internal Shader to RGB fully intact and untouched!")
print("✔ Dedicated Eye Through Hair Shader to RGB created with zero cycles!")

# 4. Test re-running operator to test idempotency
res2 = bpy.ops.setup_wizard.eye_through_hair()
assert res2 == {'FINISHED'}, f"Re-running operator failed: {res2}"
print("✔ Re-running operator cleanly updates without issues")

# 5. Test selecting MORE faces of original material subsequently
bm = bmesh.from_edit_mesh(face_obj.data)
bm.faces.ensure_lookup_table()
for f in bm.faces: f.select = False
# Select face 2 (which still has original material slot 0)
assert bm.faces[2].material_index == 0
bm.faces[2].select = True
bmesh.update_edit_mesh(face_obj.data)

res3 = bpy.ops.setup_wizard.eye_through_hair()
assert res3 == {'FINISHED'}, f"Third run failed: {res3}"

slot_names = [s.material.name for s in face_obj.material_slots]
print("Slots after subsequent run:", slot_names)
assert len(face_obj.material_slots) == 2, f"Expected 2 slots, got {len(face_obj.material_slots)}: {slot_names}"
assert "HoYoverse - Anastasya New Pupil_EyeThroughHair.001" not in slot_names, "Created duplicate .001 material!"

bm = bmesh.from_edit_mesh(face_obj.data)
bm.faces.ensure_lookup_table()
assert bm.faces[2].material_index == 1, f"Face 2 should point to slot 1, got {bm.faces[2].material_index}"
print("✔ Verified: Subsequent selections reuse existing EyeThroughHair slot without creating .001 duplicates!")

print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! 🎉\n")
