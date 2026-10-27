import bpy
import bmesh
from typing import List, Tuple, Set

try:
    from ..utils.modifier_utils import set_modifier_property
except ImportError:
    try:
        from setup_wizard.utils.modifier_utils import set_modifier_property
    except ImportError:
        set_modifier_property = None


def _assign_to_genshin_other_material_option(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    if not obj or not getattr(obj, "modifiers", None) or not mat:
        return
    for mod in obj.modifiers:
        if getattr(mod, "type", None) != 'NODES':
            continue
        ng = getattr(mod, "node_group", None)
        if not ng:
            continue
        ng_name = (getattr(ng, "name", "") or "").lower()
        mod_name = (getattr(mod, "name", "") or "").lower()
        if "genshin impact" in ng_name or "genshin impact" in mod_name:
            if set_modifier_property:
                set_modifier_property(mod, 'Input_26', mat)
            try:
                if hasattr(mod, "properties") and hasattr(mod.properties, "inputs"):
                    if 'Input_26' in mod.properties.inputs:
                        mod.properties.inputs['Input_26']['value'] = mat
            except Exception:
                pass
            try:
                mod['Input_26'] = mat
            except Exception:
                pass


EYE_THROUGH_HAIR_S2RGB_LABEL = "Eye Through Hair Shader to RGB"
EYE_THROUGH_HAIR_AOV_COLOR_LABEL = "Eye Through Hair Color"
EYE_THROUGH_HAIR_AOV_MASK_LABEL = "Eye Through Hair Mask"
EYE_THROUGH_HAIR_SUFFIX = "_EyeThroughHair"
EYE_THROUGH_HAIR_MIN_VERSION = (5, 2, 0)


def supports_eye_through_hair():
    """Supported utility baseline; this is not the introduction version of AOVs."""
    return (bpy.app.version >= EYE_THROUGH_HAIR_MIN_VERSION
            and 'aovs' in bpy.types.ViewLayer.bl_rna.properties
            and hasattr(bpy.types, 'ShaderNodeOutputAOV')
            and hasattr(bpy.types, 'ShaderNodeShaderToRGB'))


def ensure_aov_passes(view_layer: bpy.types.ViewLayer) -> Tuple[bool, bool]:
    """Ensure that 'Eye color' and 'Eye mask' AOV passes exist in the view layer."""
    existing_aovs = {aov.name: aov for aov in view_layer.aovs}
    
    if "Eye color" not in existing_aovs:
        aov = view_layer.aovs.add()
        aov.name = "Eye color"
        if hasattr(aov, "type"):
            aov.type = 'COLOR'

    if "Eye mask" not in existing_aovs:
        aov = view_layer.aovs.add()
        aov.name = "Eye mask"
        if hasattr(aov, "type"):
            aov.type = 'COLOR'

    # Repair passes created manually or by older setups with the wrong type.
    for aov in view_layer.aovs:
        if aov.name in ('Eye color', 'Eye mask'):
            aov.type = 'COLOR'

    from .compositor_effects import order_aov_passes
    order_aov_passes(bpy.context.scene, view_layer)
    return True, True


def get_selected_faces_and_materials(obj: bpy.types.Object) -> Tuple[List[int], dict]:
    """
    Returns a list of selected face indices and a map of {material_index: [face_indices]}.
    Works both in EDIT mode and OBJECT mode.
    """
    selected_face_indices = []
    mat_index_to_faces = {}

    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        # Check faces directly selected
        faces = [f for f in bm.faces if f.select]
        if not faces:
            # Fallback: if user selected vertices or edges, find faces touching selected verts
            faces = [f for f in bm.faces if any(v.select for v in f.verts)]
        
        for f in faces:
            selected_face_indices.append(f.index)
            mat_index_to_faces.setdefault(f.material_index, []).append(f.index)
    else:
        for poly in obj.data.polygons:
            if poly.select:
                selected_face_indices.append(poly.index)
                mat_index_to_faces.setdefault(poly.material_index, []).append(poly.index)

    return selected_face_indices, mat_index_to_faces


def configure_material_eye_through_hair_nodes(mat: bpy.types.Material) -> bool:
    """
    Configures shader nodes in the duplicated material:
    - Finds Material Output Surface link.
    - Connects that surface shader into a DEDICATED Shader to RGB node.
      (Never reuses any internal Shader to RGB node already present in the material)
    - Connects that Shader to RGB Color into an AOV Output named 'Eye color'.
    - Adds an AOV Output named 'Eye mask' with pure white color (1.0, 1.0, 1.0, 1.0).
    """
    if hasattr(mat, "use_nodes"):
        try:
            mat.use_nodes = True
        except Exception:
            pass

    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = 'DITHERED'
    if hasattr(mat, "blend_method"):
        try:
            mat.blend_method = 'HASHED'
        except Exception:
            pass

    tree = getattr(mat, "node_tree", None)
    if not tree:
        return False

    nodes = tree.nodes
    links = tree.links

    # Find the active material output node
    output_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL' and getattr(n, "is_active_output", False)), None)
    if not output_node:
        output_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)

    if not output_node:
        return False

    surface_input = output_node.inputs.get("Surface")
    if not surface_input or not surface_input.is_linked:
        return False

    source_shader_socket = surface_input.links[0].from_socket

    # ONLY reuse a Shader to RGB node if it was specifically created by this eye-through-hair tool.
    # NEVER hijack internal Shader to RGB nodes that belong to the material.
    s2rgb_node = next(
        (n for n in nodes if (n.type == 'SHADER_TO_RGB' or n.bl_idname == 'ShaderNodeShaderToRGB')
         and getattr(n, "label", "") in (EYE_THROUGH_HAIR_S2RGB_LABEL, "See-Through Shader to RGB")),
        None
    )
    if not s2rgb_node:
        s2rgb_node = nodes.new(type='ShaderNodeShaderToRGB')
        s2rgb_node.name = "Shader to RGB (Eye Through Hair)"
        s2rgb_node.label = EYE_THROUGH_HAIR_S2RGB_LABEL
        s2rgb_node.location = (output_node.location.x - 220, output_node.location.y - 140)
    else:
        s2rgb_node.label = EYE_THROUGH_HAIR_S2RGB_LABEL

    # Connect surface shader output to our dedicated Shader to RGB
    links.new(source_shader_socket, s2rgb_node.inputs.get("Shader") or s2rgb_node.inputs[0])

    # AOV Output: Eye color
    aov_color = next(
        (n for n in nodes if getattr(n, "aov_name", "") == "Eye color"
         and getattr(n, "label", "") in (EYE_THROUGH_HAIR_AOV_COLOR_LABEL, "See-Through Eye Color")),
        None
    )
    if not aov_color:
        aov_color = next((n for n in nodes if getattr(n, "aov_name", "") == "Eye color"), None)

    if not aov_color:
        aov_color = nodes.new(type='ShaderNodeOutputAOV')
        aov_color.name = "AOV Output (Eye Color)"
        aov_color.label = EYE_THROUGH_HAIR_AOV_COLOR_LABEL
        aov_color.aov_name = "Eye color"
        aov_color.location = (s2rgb_node.location.x + 220, s2rgb_node.location.y)
    else:
        aov_color.label = EYE_THROUGH_HAIR_AOV_COLOR_LABEL

    # Ensure Eye color AOV is linked from OUR dedicated s2rgb node
    color_in = aov_color.inputs.get("Color") or aov_color.inputs[0]
    links.new(s2rgb_node.outputs.get("Color") or s2rgb_node.outputs[0], color_in)
    if "Value" in aov_color.inputs:
        aov_color.inputs["Value"].default_value = 0.0

    # AOV Output: Eye mask
    aov_mask = next(
        (n for n in nodes if getattr(n, "aov_name", "") == "Eye mask"
         and getattr(n, "label", "") in (EYE_THROUGH_HAIR_AOV_MASK_LABEL, "See-Through Eye Mask")),
        None
    )
    if not aov_mask:
        aov_mask = next((n for n in nodes if getattr(n, "aov_name", "") == "Eye mask"), None)

    if not aov_mask:
        aov_mask = nodes.new(type='ShaderNodeOutputAOV')
        aov_mask.name = "AOV Output (Eye Mask)"
        aov_mask.label = EYE_THROUGH_HAIR_AOV_MASK_LABEL
        aov_mask.aov_name = "Eye mask"
        aov_mask.location = (aov_color.location.x, aov_color.location.y - 120)
    else:
        aov_mask.label = EYE_THROUGH_HAIR_AOV_MASK_LABEL

    mask_color_input = aov_mask.inputs.get("Color") or aov_mask.inputs[0]
    for l in list(mask_color_input.links):
        links.remove(l)
    mask_color_input.default_value = (1.0, 1.0, 1.0, 1.0)
    if "Value" in aov_mask.inputs:
        aov_mask.inputs["Value"].default_value = 0.0

    return True


def isolate_and_assign_eye_through_hair_materials(obj: bpy.types.Object) -> List[bpy.types.Material]:
    """
    Duplicates materials for selected faces of an object and assigns the duplicates
    exclusively to those selected faces. Reuses existing EyeThroughHair slots without
    creating .001 duplicates.
    """
    selected_face_indices, mat_index_to_faces = get_selected_faces_and_materials(obj)
    if not selected_face_indices:
        return []

    is_edit_mode = (obj.mode == 'EDIT')
    bm = bmesh.from_edit_mesh(obj.data) if is_edit_mode else None

    created_materials = []

    for mat_idx, face_indices in mat_index_to_faces.items():
        if mat_idx >= len(obj.material_slots) or not obj.material_slots[mat_idx].material:
            continue

        orig_mat = obj.material_slots[mat_idx].material

        if "_EyeThroughHair" in orig_mat.name or "_SeeThrough" in orig_mat.name:
            new_mat = orig_mat
            new_slot_idx = mat_idx
        else:
            target_name = f"{orig_mat.name}{EYE_THROUGH_HAIR_SUFFIX}"
            # 1. Reuse existing slot on this object if already present
            existing_slot = next(
                (i for i, s in enumerate(obj.material_slots) if s.material and s.material.name == target_name),
                None
            )
            if existing_slot is not None:
                new_mat = obj.material_slots[existing_slot].material
                new_slot_idx = existing_slot
            else:
                # 2. Reuse existing material from scene if already created
                existing_mat = bpy.data.materials.get(target_name)
                if existing_mat:
                    new_mat = existing_mat
                    obj.data.materials.append(new_mat)
                    new_slot_idx = len(obj.material_slots) - 1
                else:
                    # 3. Create first duplicate cleanly
                    new_mat = orig_mat.copy()
                    new_mat.name = target_name
                    obj.data.materials.append(new_mat)
                    new_slot_idx = len(obj.material_slots) - 1

        configure_material_eye_through_hair_nodes(new_mat)
        if hasattr(new_mat, "surface_render_method"):
            new_mat.surface_render_method = 'DITHERED'
        if hasattr(new_mat, "blend_method"):
            try:
                new_mat.blend_method = 'HASHED'
            except Exception:
                pass
        created_materials.append(new_mat)
        _assign_to_genshin_other_material_option(obj, new_mat)

        # Reassign faces to new material slot
        target_indices_set = set(face_indices)
        if is_edit_mode and bm:
            bm.faces.ensure_lookup_table()
            for f in bm.faces:
                if f.index in target_indices_set:
                    f.material_index = new_slot_idx
        else:
            for poly in obj.data.polygons:
                if poly.index in target_indices_set:
                    poly.material_index = new_slot_idx

    if is_edit_mode and bm:
        bmesh.update_edit_mesh(obj.data)
    else:
        obj.data.update()

    return created_materials


def configure_hair_materials_blended(context: bpy.types.Context) -> int:
    """
    Finds hair objects and materials in the scene (including NTE 'mrim' material)
    and ensures they use 'BLENDED' (Eevee Next) / 'BLEND' (legacy Eevee) render method.
    Sets use_transparency_overlap to False ONLY on hair mesh materials, leaving
    outline materials untouched.
    Explicitly ignores eye-through-hair materials (_EyeThroughHair, _SeeThrough) so they
    remain DITHERED.
    """
    count = 0
    hair_keywords = ("hair", "pelo", "bangs", "mrim")
    outline_keywords = ("outline", "_ol", "mrim")
    processed_materials = set()

    def process_material(mat: bpy.types.Material, is_hair_mesh_obj: bool, is_outline_obj: bool):
        nonlocal count
        if not mat or mat.name in processed_materials:
            return
        if "_eyethroughhair" in mat.name.lower() or "_seethrough" in mat.name.lower():
            return
        processed_materials.add(mat.name)

        is_outline = is_outline_obj or any(k in mat.name.lower() for k in outline_keywords)
        modified = False

        if hasattr(mat, "surface_render_method") and mat.surface_render_method != 'BLENDED':
            mat.surface_render_method = 'BLENDED'
            modified = True
        if hasattr(mat, "blend_method") and mat.blend_method != 'BLEND':
            mat.blend_method = 'BLEND'
            modified = True

        # Only hair mesh materials get use_transparency_overlap = False; outlines are left untouched
        if not is_outline:
            if hasattr(mat, "use_transparency_overlap") and mat.use_transparency_overlap:
                mat.use_transparency_overlap = False
                modified = True

        if modified:
            count += 1

    # 1. Check all mesh objects with hair in their name
    for o in context.scene.objects:
        if o.type == 'MESH':
            is_hair_obj = any(k in o.name.lower() for k in hair_keywords)
            is_outline_obj = any(k in o.name.lower() for k in outline_keywords)
            for slot in o.material_slots:
                mat = slot.material
                if not mat:
                    continue
                if "_eyethroughhair" in mat.name.lower() or "_seethrough" in mat.name.lower():
                    continue
                is_hair_mat = any(k in mat.name.lower() for k in hair_keywords)
                if is_hair_obj or is_hair_mat:
                    process_material(mat, is_hair_mesh_obj=is_hair_obj and not is_outline_obj, is_outline_obj=is_outline_obj)

    # 2. Check all materials in bpy.data.materials as fallback
    for mat in bpy.data.materials:
        if "_eyethroughhair" in mat.name.lower() or "_seethrough" in mat.name.lower():
            continue
        if any(k in mat.name.lower() for k in hair_keywords):
            process_material(mat, is_hair_mesh_obj=True, is_outline_obj=False)

    return count


def get_or_create_compositor_tree(scene: bpy.types.Scene) -> bpy.types.NodeTree:
    """
    Retrieves or creates the compositor node tree across Blender 4.x / Goo Engine
    and Blender 5.x.
    """
    scene.render.use_compositing = True
    if hasattr(scene, "compositing_node_group"):
        if not scene.compositing_node_group:
            scene.compositing_node_group = bpy.data.node_groups.new("Compositing Nodetree", "CompositorNodeTree")
        return scene.compositing_node_group
    else:
        if hasattr(scene, "use_nodes"):
            scene.use_nodes = True
        return getattr(scene, "node_tree", None)


def setup_compositor_nodes(scene: bpy.types.Scene) -> bool:
    """Expose the effect as one Eye See Through group with an Opacity control."""
    from .compositor_effects import setup_eye_group
    tree = get_or_create_compositor_tree(scene)
    return bool(tree and setup_eye_group(scene, tree))


def set_viewport_compositor_always(context: bpy.types.Context) -> None:
    """Sets Viewport Compositor to 'ALWAYS' across all 3D View spaces."""
    screens: Set[bpy.types.Screen] = set()
    if hasattr(context, "screen") and context.screen:
        screens.add(context.screen)
    for scr in bpy.data.screens:
        screens.add(scr)
    for wm in bpy.data.window_managers:
        for win in wm.windows:
            if win.screen:
                screens.add(win.screen)

    for scr in screens:
        for area in scr.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D' and hasattr(space, "shading"):
                        if hasattr(space.shading, "use_compositor"):
                            try:
                                space.shading.use_compositor = 'ALWAYS'
                            except Exception:
                                pass


def get_target_mesh_objects(context: bpy.types.Context) -> List[bpy.types.Object]:
    """
    Returns all candidate mesh objects:
    - Objects currently in Edit mode (multi-object editing)
    - Selected mesh objects
    - Active mesh object
    """
    target_objs = []
    
    # 1. Objects in Edit mode (multi-object editing in Blender 2.8+)
    if hasattr(context, "objects_in_mode") and context.objects_in_mode:
        for o in context.objects_in_mode:
            if o.type == 'MESH' and o not in target_objs:
                target_objs.append(o)

    # 2. Selected objects
    for o in getattr(context, "selected_objects", []):
        if o.type == 'MESH' and o not in target_objs:
            target_objs.append(o)

    # 3. Active object fallback
    act = context.active_object or context.object
    if act and act.type == 'MESH' and act not in target_objs:
        target_objs.append(act)

    return target_objs


def execute_eye_through_hair(context: bpy.types.Context) -> Tuple[bool, str]:
    """
    Full pipeline execution:
    1. Ensures AOV passes in ViewLayer.
    2. Isolates materials for selected faces on ALL target mesh objects (multi-object support).
    3. Configures hair materials to blended render method.
    4. Sets up Compositor nodes.
    5. Sets viewport compositor to ALWAYS.
    """
    if not supports_eye_through_hair():
        return False, 'Eye Through Hair requires Blender 5.2 or newer with shader AOV support.'
    target_objs = get_target_mesh_objects(context)
    if not target_objs:
        return False, "No mesh objects found in selection or active context."

    # Step 1: Ensure AOVs
    view_layer = context.view_layer
    ensure_aov_passes(view_layer)

    # Step 2: Isolate materials & configure shader nodes across all target objects
    all_created_materials = []
    processed_objects = []

    for obj in target_objs:
        created = isolate_and_assign_eye_through_hair_materials(obj)
        if created:
            all_created_materials.extend(created)
            processed_objects.append(obj.name)

    if not all_created_materials:
        return False, "No faces were selected on any target mesh. Please select eye/eyebrow faces in Edit Mode."

    # Step 3: Hair materials to BLENDED
    hair_count = configure_hair_materials_blended(context)

    # Step 3b: Ensure all eye through hair materials are set to DITHERED
    for mat in all_created_materials:
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = 'DITHERED'
        if hasattr(mat, "blend_method"):
            try:
                mat.blend_method = 'HASHED'
            except Exception:
                pass
    for mat in bpy.data.materials:
        if "_eyethroughhair" in mat.name.lower() or "_seethrough" in mat.name.lower():
            if hasattr(mat, "surface_render_method"):
                mat.surface_render_method = 'DITHERED'
            if hasattr(mat, "blend_method"):
                try:
                    mat.blend_method = 'HASHED'
                except Exception:
                    pass

    # Step 4: Compositor setup
    comp_ok = setup_compositor_nodes(context.scene)
    if not comp_ok:
        return False, "Failed to configure Compositor node tree."

    # Step 5: Set viewport compositor to ALWAYS
    set_viewport_compositor_always(context)

    obj_names_str = ", ".join(processed_objects)
    return True, (
        f"Successfully applied Eye Through Hair on {len(processed_objects)} object(s) [{obj_names_str}] "
        f"({len(all_created_materials)} materials isolated as Dithered, {hair_count} hair materials set to Blended). "
        f"Viewport Compositor set to ALWAYS."
    )


class CSW_OT_EyeThroughHair(bpy.types.Operator):
    """Configure eye through hair effect for selected mesh faces with AOVs and Compositor"""
    bl_idname = "setup_wizard.eye_through_hair"
    bl_label = "Eye Through Hair"
    bl_description = "Duplicate materials for selected eye/eyebrow faces across objects, add AOVs, set hair to Blended, and set Compositor to Always"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not supports_eye_through_hair():
            cls.poll_message_set('Eye Through Hair requires Blender 5.2 or newer with shader AOV support.')
            return False
        if context.active_object and context.active_object.type == 'MESH':
            return True
        if any(o.type == 'MESH' for o in getattr(context, 'selected_objects', [])):
            return True
        if any(o.type == 'MESH' for o in getattr(context, 'objects_in_mode', [])):
            return True
        return False

    def execute(self, context):
        success, message = execute_eye_through_hair(context)
        if success:
            self.report({'INFO'}, message)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}
