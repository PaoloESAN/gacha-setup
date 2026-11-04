"""Resolve surface shaders without confusing separator/custom-pass outputs."""


def surface_shader_output(node):
    if node is None:
        return None
    for name in ('BSDF', 'PrimoToon', 'Shader'):
        socket = node.outputs.get(name)
        if socket is not None and socket.type == 'SHADER':
            return socket
    return next((socket for socket in node.outputs if socket.type == 'SHADER'), None)
