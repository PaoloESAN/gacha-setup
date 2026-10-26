"""Bind Kythera V2 face vectors to a real Sun and a head-relative basis."""
import bpy
from mathutils import Matrix


def _face_material(material):
    return bool(material and material.node_tree and any(
        node.type == 'GROUP' and node.node_tree
        and "kythera's zzz face shader v2" in node.node_tree.name.lower()
        for node in material.node_tree.nodes))


def setup_kythera_lighting(context, armature=None, final=False):
    """Create independent lights/vector groups per character; safe to rerun.

    Run again after rig generation so the head basis follows the final rig.
    Legacy shader users are left on their original lighting system.
    """
    from setup_wizard.utils.modifier_utils import set_modifier_property

    owners = [armature] if armature else [obj for obj in context.scene.objects if obj.type == 'ARMATURE']
    result = []
    for owner in owners:
        meshes = [obj for obj in context.scene.objects if obj.type == 'MESH'
                  and (obj.find_armature() == owner or obj.parent == owner)
                  and any(_face_material(slot.material) for slot in obj.material_slots)]
        if not meshes:
            continue
        modifiers = [mod for obj in meshes for mod in obj.modifiers
                     if mod.type == 'NODES' and mod.node_group
                     and mod.node_group.get('zzz_kythera_vectors')]
        tree = modifiers[0].node_group if modifiers else None
        # A copied character must get its own Sun and head basis.
        if tree and any(obj not in meshes and obj.type == 'MESH'
                        and any(mod.type == 'NODES' and mod.node_group == tree for mod in obj.modifiers)
                        for obj in context.scene.objects):
            tree = None
        sun = tree.nodes['Object Info'].inputs['Object'].default_value if tree else None
        basis = tree.nodes['Object Info.001'].inputs['Object'].default_value if tree else None
        if tree is None:
            template = next((group for group in bpy.data.node_groups
                             if group.get('zzz_kythera_vectors') and not group.get('zzz_kythera_owner')), None)
            if template is None:
                continue
            tree = template.copy()
            tree.use_fake_user = False
            tree.name = f'Kythera Face Vectors - {owner.name}'
            # Appending the vector template already imports its Sun dependency.
            # Use it for the first character instead of appending another Sun.
            template_sun = template.nodes['Object Info'].inputs['Object'].default_value
            if template_sun is None or template_sun.type != 'LIGHT' or template_sun.data.type != 'SUN':
                raise RuntimeError('Kythera V2 bundle is missing its Sun light.')
            if template_sun.get('zzz_kythera_owner'):
                sun = template_sun.copy()
                sun.data = template_sun.data.copy()
                if hasattr(sun, 'light_linking'):
                    sun.light_linking.receiver_collection = None
            else:
                sun = template_sun
            sun.name = f'Sun_{owner.name}'
            basis = bpy.data.objects.new(f'Kythera Head Basis_{owner.name}', None)
            basis.empty_display_type = 'PLAIN_AXES'
            basis.empty_display_size = 0.1
        sun['zzz_kythera_owner'] = owner
        tree['zzz_kythera_owner'] = owner
        destination = next((coll for coll in owner.users_collection
                            if not any(word in coll.name.lower() for word in ('wgt', 'widget'))), context.scene.collection)
        widgets = next((coll for coll in destination.children
                        if coll.name.startswith('WGTS') or coll.name.lower() == 'wgt'), None)
        if widgets is None and final:
            widgets = bpy.data.collections.new(f'WGTS_{destination.name}')
            destination.children.link(widgets)
            widgets.hide_viewport = True
            widgets.hide_render = True
            widgets.hide_select = True
        for obj, target in ((sun, destination), (basis, widgets or destination)):
            if obj.name not in target.objects:
                target.objects.link(obj)
            # The initial import can link helpers to the scene root. Keep a
            # single collection membership when the character is organized.
            for previous in list(obj.users_collection):
                if previous != target:
                    previous.objects.unlink(obj)
        sun.hide_viewport = False
        sun.hide_render = False
        sun.hide_set(False)
        basis.hide_render = True
        if hasattr(sun, 'light_linking'):
            # Collection organization at the end of setup moves objects out
            # of temporary receiver collections. Link the finished character's
            # actual collection so its Sun still illuminates the final meshes.
            if final:
                sun.light_linking.receiver_collection = destination
            receivers = sun.light_linking.receiver_collection
            if receivers is None:
                receivers = bpy.data.collections.new(f'Kythera Light Receivers_{owner.name}')
                sun.light_linking.receiver_collection = receivers
            for obj in context.scene.objects:
                if obj.type == 'MESH' and (obj.find_armature() == owner or obj.parent == owner):
                    if obj.name not in receivers.objects:
                        receivers.objects.link(obj)

        head = next((owner.pose.bones.get(name) for name in ('head', 'DEF-head', 'Skn_Head')
                     if owner.pose.bones.get(name)), None)
        if head is None:
            head = next((bone for bone in owner.pose.bones if 'head' in bone.name.lower()
                         and not any(word in bone.name.lower() for word in ('track', 'end', 'twist'))), None)
        if head:
            follow = basis.constraints.get('Kythera Head Follow')
            if follow is None:
                follow = basis.constraints.new('CHILD_OF')
                follow.name = 'Kythera Head Follow'
            if follow.target != owner or follow.subtarget != head.name:
                matrix = owner.matrix_world @ head.matrix
                basis.matrix_world = Matrix.Translation(matrix.translation)
                follow.target = owner
                follow.subtarget = head.name
                follow.inverse_matrix = matrix.inverted_safe()
        tree.nodes['Object Info'].inputs['Object'].default_value = sun
        tree.nodes['Object Info.001'].inputs['Object'].default_value = basis
        tree.nodes['Object Info.002'].inputs['Object'].default_value = basis
        # Rig generation can rebind the panel's original vector modifier.
        # Keep its RGB/sliders, but use Sun for its direction input as well.
        for obj in context.scene.objects:
            if obj.type != 'MESH' or not (obj.find_armature() == owner or obj.parent == owner):
                continue
            for mod in obj.modifiers:
                if mod.type != 'NODES' or not mod.node_group or not mod.name.startswith('Light Vectors'):
                    continue
                for socket in mod.node_group.interface.items_tree:
                    if (socket.item_type == 'SOCKET' and socket.in_out == 'INPUT'
                            and socket.name == 'Light Direction'):
                        set_modifier_property(mod, socket.identifier, sun)
        for obj in meshes:
            modifier = next((mod for mod in obj.modifiers if mod.type == 'NODES' and mod.node_group
                             and mod.node_group.get('zzz_kythera_vectors')), None)
            if modifier is None:
                modifier = obj.modifiers.new('Kythera Face Vectors', 'NODES')
            modifier.node_group = tree
            # Write the vectors on original geometry before outline generation.
            obj.modifiers.move(list(obj.modifiers).index(modifier), 0)
            obj.update_tag()
        result.append(sun)
    return result
