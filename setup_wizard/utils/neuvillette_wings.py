"""Neuvillette's skill wings use cutout materials without an outline hull."""

def is_neuvillette_wing(obj):
    if obj is None or obj.type != 'MESH':
        return False
    materials = [slot.material for slot in obj.material_slots if slot.material]
    wing_part = ('wing' in obj.name.casefold() or 'wing' in obj.data.name.casefold()
                 or materials and all('wing' in (mat.get('_original_material_name', '') + ' ' + mat.name).casefold()
                                      for mat in materials))
    if not wing_part:
        return False
    from setup_wizard.replace_default_materials_setup.game_default_material_replacers import is_specific_character
    owner = obj.find_armature() or obj.parent
    character = str(owner.get('gacha_character', '')) if owner else ''
    if character and character.casefold() not in {'character', 'unknown'}:
        return is_specific_character('neuvillette', material=character, allow_context=False)
    return is_specific_character('neuvillette', mesh=obj, allow_context=False)


def configure_neuvillette_wings(objects=None):
    import bpy

    objects = list(bpy.context.scene.objects if objects is None else objects)
    wings = [obj for obj in objects if is_neuvillette_wing(obj)]
    copies = {}
    for obj in wings:
        for modifier in list(obj.modifiers):
            group = getattr(modifier, 'node_group', None)
            if (modifier.type in {'NODES', 'SOLIDIFY'} and
                    ('outline' in modifier.name.casefold() or group and 'outline' in group.name.casefold())):
                obj.modifiers.remove(modifier)
        for slot in obj.material_slots:
            material = slot.material
            if not material or not material.node_tree:
                continue
            original = material.get('_original_material_name', material.name).casefold()
            # The separate dissolve/effect material is not a Hair/Dress cutout.
            if 'eff' in original:
                continue
            if not any(node.type == 'GROUP' and ('Toggle Alpha' in node.inputs or 'Use Alpha' in node.inputs)
                       for node in material.node_tree.nodes):
                continue
            if any(other.type == 'MESH' and not is_neuvillette_wing(other)
                   and any(other_slot.material == material for other_slot in other.material_slots)
                   for other in bpy.data.objects):
                if material not in copies:
                    copies[material] = material.copy()
                    copies[material].name = material.name + ' [Neuvillette Wings]'
                material = copies[material]
                slot.material = material
            for node in material.node_tree.nodes:
                if node.type != 'GROUP':
                    continue
                for name, value in (
                    ('Use Alpha', 1.0), ('Toggle Alpha', True),
                    ('0 = Emission, 1 = Transparency', 1.0), ('Emit / Transparency', True),
                    ('Transparency Cutoff', 0.1), ('Transparency Clip Threshold', 0.1),
                ):
                    socket = node.inputs.get(name)
                    if socket is not None:
                        for link in list(socket.links):
                            material.node_tree.links.remove(link)
                        socket.default_value = value
            # Eevee Next implements the hard cutoff in the shader itself.
            if hasattr(material, 'surface_render_method'):
                material.surface_render_method = 'DITHERED'
            else:
                material.blend_method = 'CLIP'
            if hasattr(material, 'alpha_threshold'):
                material.alpha_threshold = 0.1
        # The second (Eff) slot uses the Hair cutout from the third slot too.
        # Keep slots and polygon indices intact; only replace the assignment.
        if len(obj.material_slots) >= 3:
            obj.material_slots[1].material = obj.material_slots[2].material
    return wings
