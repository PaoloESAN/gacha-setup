"""Inspect the baked HSR face modifier using Blender 4.5, its authored version."""
from pathlib import Path
import sys
import bpy

ROOT=Path(__file__).resolve().parents[1]
shader=ROOT/'setup_wizard/shaders/hsr/StellarToonV1.1.blend'
def signature(tree):
    def value(item):
        if isinstance(item,bpy.types.ID): return item.name
        if isinstance(item,(str,int,float,bool)) or item is None: return item
        return tuple(item)
    return ([(n.name,n.bl_idname,[(s.identifier,value(s.default_value)) for s in n.inputs if hasattr(s,'default_value')],
              [(p,getattr(n,p)) for p in ('operation','data_type','domain','mode','input_type','blend_type') if hasattr(n,p)])
             for n in tree.nodes],
            [(l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in tree.links])
original=None
if '--' in sys.argv:
    bpy.ops.wm.open_mainfile(filepath=str(Path(sys.argv[sys.argv.index('--')+1]).resolve()))
    original={g.name:signature(g) for g in bpy.data.node_groups}
bpy.ops.wm.open_mainfile(filepath=str(shader))
assert bpy.app.version[:2] == (4,5), bpy.app.version
assert bpy.data.version[:2] == (4,5), bpy.data.version
group=bpy.data.node_groups['StellarToon - Outlines FACE']
assert group.use_fake_user and group.get('gacha_hsr_face_outlines') == 1
preview=bpy.data.objects['Face Preview']
modifier=next(m for m in preview.modifiers if m.type=='NODES' and m.node_group==group)
assert modifier['Input_8'] == 0
assert modifier[group['dynamic_socket']] == 1
assert modifier[group['head_socket']] == bpy.data.objects['Head Origin']
assert modifier['Input_4'] == bpy.context.scene.camera
assert any(m.type=='NODES' and m.node_group.name=='StellarToon - Outlines GN'
           for m in bpy.data.objects['Sphere'].modifiers)
assert len(group.nodes) > len(bpy.data.node_groups['StellarToon - Outlines GN'].nodes)
if original:
    for name,snapshot in original.items():
        assert name in bpy.data.node_groups and signature(bpy.data.node_groups[name])==snapshot, name
print('HSR_SHADER_ASSET_PASS',bpy.app.version,bpy.data.version,len(group.nodes),flush=True)
