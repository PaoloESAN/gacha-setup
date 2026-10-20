"""Single-material pupil exception for Avatar_Boy_Gun_AetherShadow only."""

TAG = 'setup_wizard_aether_gun_pupil'


def is_aether_gun(mesh=None, material_name=''):
    if mesh is not None and mesh.get(TAG):
        return True
    from setup_wizard.replace_default_materials_setup.game_default_material_replacers import is_specific_character
    return is_specific_character('Avatar_Boy_Gun_AetherShadow', mesh=mesh,
                                 material=material_name, allow_context=False)


def disable_lightmap(material):
    if not material or not material.get(TAG) or not material.node_tree:
        return False
    tree = material.node_tree
    for node in tree.nodes:
        if node.type == 'TEX_IMAGE' and 'lightmap' in node.name.lower():
            node.image = None
            node.mute = True
        if node.type != 'GROUP':
            continue
        for socket in node.inputs:
            if socket.name in ('Toggle Lightmap AO', 'Use Lightmap AO', 'Use Lightmap'):
                for link in list(socket.links):
                    tree.links.remove(link)
                socket.default_value = False
            elif socket.name in ('Lightmap Color', 'Lightmap Alpha'):
                for link in list(socket.links):
                    tree.links.remove(link)
                # Preserve the shader's saved neutral, untextured defaults.
    return True


def setup_single_pupil(mesh, template):
    mesh[TAG] = True
    material = next((m for m in mesh.data.materials if m and m.get(TAG)), None)
    if material is None:
        material = template.copy()
        material.name = 'HoYoverse - Genshin New Pupil [AetherShadow Gun]'
        material[TAG] = True
        material['_original_material_name'] = 'Avatar_Boy_Gun_AetherShadow_Mat_Pupil'
        # Keep the pupil images isolated from other characters' materials.
        for node in material.node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree and 'pupilatodo' in node.node_tree.name.lower():
                node.node_tree = node.node_tree.copy()
    mesh.data.materials.clear()
    mesh.data.materials.append(material)
    for polygon in mesh.data.polygons:
        polygon.material_index = 0
    disable_lightmap(material)
    return material
