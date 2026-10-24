"""Small compositor groups shared by the character utilities (Blender 5.2+)."""
import bpy


def order_aov_passes(scene, view_layer):
    """Work around Eevee 5.2's mixed AOV hash packing: colors precede values.

    Rebuilding the RNA collection can replace Render Layers sockets, so save
    and restore their consumers by pass name, including user compositor groups.
    """
    current = [(a.name, a.type) for a in view_layer.aovs]
    ordered = sorted(current, key=lambda a: a[1] != 'COLOR')
    if current == ordered:
        return
    names = {name for name, _ in current}
    trees = {g for g in bpy.data.node_groups if g.bl_idname == 'CompositorNodeTree'}
    for s in bpy.data.scenes:
        tree = getattr(s, 'node_tree', None)
        if tree:
            trees.add(tree)
    connections = []
    for tree in trees:
        for n in tree.nodes:
            if n.type == 'R_LAYERS' and n.layer == view_layer.name and (n.scene is None or n.scene == scene):
                connections.extend((tree, n, output.name, link.to_socket)
                                   for output in n.outputs if output.name in names for link in list(output.links))
    for aov in list(view_layer.aovs):
        view_layer.aovs.remove(aov)
    for name, kind in ordered:
        aov = view_layer.aovs.add()
        aov.name, aov.type = name, kind
    for tree, node, name, destination in connections:
        output = node.outputs.get(name)
        if output is not None:
            tree.links.new(output, destination)


def socket(tree, name, kind='NodeSocketFloat', default=None, output=False, minimum=None, maximum=None):
    s = tree.interface.new_socket(name=name, in_out='OUTPUT' if output else 'INPUT', socket_type=kind)
    if default is not None:
        s.default_value = default
    if minimum is not None:
        s.min_value = minimum
    if maximum is not None:
        s.max_value = maximum
    return s


def math_node(tree, operation, a, b=None, name=None):
    n = tree.nodes.new('ShaderNodeMath')
    n.operation = operation
    if name:
        n.name = n.label = name
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (float, int)):
            n.inputs[i].default_value = v
        else:
            tree.links.new(v, n.inputs[i])
    return n.outputs[0]


def mix_node(tree, factor, a, b, blend='MIX'):
    n = tree.nodes.new('ShaderNodeMix')
    n.data_type = 'RGBA'
    n.blend_type = blend
    tree.links.new(factor, n.inputs[0])
    tree.links.new(a, n.inputs[6])
    tree.links.new(b, n.inputs[7])
    return n.outputs[2]


def render_layer(tree, scene, view_layer=None):
    layer = view_layer or bpy.context.view_layer
    node = next((n for n in tree.nodes if n.type == 'R_LAYERS'
                 and (n.scene is None or n.scene == scene) and n.layer == layer.name), None)
    if node is None:
        node = tree.nodes.new('CompositorNodeRLayers')
        node.scene, node.layer = scene, layer.name
        node.location = (-600, 200)
    return node


def ensure_output(tree, scene):
    out = next((n for n in tree.nodes if n.type in ('COMPOSITE', 'GROUP_OUTPUT')
                and getattr(n, 'is_active_output', True)), None)
    if out is None:
        if hasattr(scene, 'compositing_node_group'):
            if not any(s.in_out == 'OUTPUT' and s.socket_type == 'NodeSocketColor'
                       for s in tree.interface.items_tree if s.item_type == 'SOCKET'):
                socket(tree, 'Image', 'NodeSocketColor', output=True)
            out = tree.nodes.new('NodeGroupOutput')
        else:
            out = tree.nodes.new('CompositorNodeComposite')
        out.location = (600, 200)
    # Group interface names belong to the file and can be translated or renamed.
    return out.inputs.get('Image') or next((s for s in out.inputs if s.type == 'RGBA'), None)


def insert_effect(tree, scene, rl, node, old_output=None, old_input=None):
    """Replace a legacy effect or insert before existing grading; never loop on rerun."""
    links = tree.links
    if old_output is not None:
        consumers = [l.to_socket for l in list(old_output.links)]
        source = old_input.links[0].from_socket if old_input is not None and old_input.is_linked else rl.outputs['Image']
        links.new(source, node.inputs['Image'])
        for dest in consumers:
            links.new(node.outputs['Image'], dest)
    elif not node.inputs['Image'].is_linked:
        consumers = [l.to_socket for l in list(rl.outputs['Image'].links) if l.to_node != node]
        links.new(rl.outputs['Image'], node.inputs['Image'])
        for dest in consumers:
            links.new(node.outputs['Image'], dest)
    output = ensure_output(tree, scene)
    if output is not None and not output.is_linked:
        links.new(node.outputs['Image'], output)
    # Lay out the utility chain without stacking the groups on top of each other.
    visited = set()

    def arrange(effect, x):
        if effect in visited:
            return
        visited.add(effect)
        effect.location = (x, rl.location.y)
        for link in effect.outputs['Image'].links:
            if link.to_node.get('csw_effect'):
                arrange(link.to_node, x + 260)

    for link in rl.outputs['Image'].links:
        if link.to_node.get('csw_effect'):
            arrange(link.to_node, rl.location.x + 260)
    # Linked image/pass sockets stay available but don't clutter the controls.
    for s in node.inputs:
        if s.is_linked:
            s.hide = True


def eye_group():
    name = 'Eye See Through'
    tree = bpy.data.node_groups.get(name)
    if tree and tree.get('csw_effect') == 'eye':
        return tree
    tree = bpy.data.node_groups.new(name, 'CompositorNodeTree')
    tree['csw_effect'] = 'eye'
    socket(tree, 'Image', 'NodeSocketColor')
    socket(tree, 'Eye Color', 'NodeSocketColor')
    socket(tree, 'Eye Mask', 'NodeSocketColor')
    socket(tree, 'Opacity', default=.5, minimum=0, maximum=1)
    socket(tree, 'Image', 'NodeSocketColor', output=True)
    inp, out = tree.nodes.new('NodeGroupInput'), tree.nodes.new('NodeGroupOutput')
    factor = math_node(tree, 'MULTIPLY', inp.outputs['Eye Mask'], inp.outputs['Opacity'])
    result = mix_node(tree, factor, inp.outputs['Image'], inp.outputs['Eye Color'])
    tree.links.new(result, out.inputs['Image'])
    inp.location, out.location = (-400, 0), (400, 0)
    return tree


def setup_eye_group(scene, tree, view_layer=None):
    rl = render_layer(tree, scene, view_layer)
    color, mask = rl.outputs.get('Eye color'), rl.outputs.get('Eye mask')
    if color is None or mask is None:
        return False
    node = next((n for n in tree.nodes if n.get('csw_effect') == 'eye'), None)
    legacy = next((n for n in tree.nodes if n.name == 'Mix (Eye Through Hair)'
                   or n.label in ('Eye Through Hair Mix', 'See-Through Mix')), None)
    multiply = tree.nodes.get('Math (Eye Through Hair Multiply)')
    if node is None:
        node = tree.nodes.new('CompositorNodeGroup')
        node.node_tree = eye_group()
        node.name = node.label = 'Eye See Through'
        node['csw_effect'] = 'eye'
        if multiply:
            node.inputs['Opacity'].default_value = multiply.inputs[1].default_value
    tree.links.new(color, node.inputs['Eye Color'])
    tree.links.new(mask, node.inputs['Eye Mask'])
    if legacy:
        old_input = next((s for s in legacy.inputs if s.identifier in ('A_Color', 'Image', 'Image1')), None)
        old_output = next((s for s in legacy.outputs if s.identifier in ('Result_Color', 'Image')), legacy.outputs[0])
        insert_effect(tree, scene, rl, node, old_output, old_input)
        tree.nodes.remove(legacy)
        if multiply and not any(s.is_linked for s in multiply.outputs):
            tree.nodes.remove(multiply)
    else:
        insert_effect(tree, scene, rl, node)
    return True
