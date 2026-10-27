"""Recover neutral references for HSR expressions baked with a posed head."""
import re
from mathutils import Vector


def rebase_baked_expressions(mesh):
    """Use the authored family default only when it contains a global offset.

    Bone-animation bakes can include a whole head pose as well as the facial
    expression. Relative shape keys must subtract that same posed neutral,
    rather than the FBX's unposed Basis. Keep all coordinates unchanged.
    """
    shapes = mesh.data.shape_keys
    if not shapes or not shapes.use_relative or not shapes.reference_key.data:
        return 0
    basis = shapes.reference_key
    points = [point.co for point in basis.data]
    extent = max(max(p[i] for p in points) - min(p[i] for p in points) for i in range(3))
    if extent < 1e-8:
        return 0
    offset_defaults = {}

    def has_baked_pose(neutral):
        if neutral.name not in offset_defaults:
            deltas = [point.co - rest.co for point, rest in zip(neutral.data, basis.data)]
            mean = sum(deltas, Vector()) / len(deltas)
            offset_defaults[neutral.name] = (mean.length > extent * .05
                and sum(delta.length > extent * .01 for delta in deltas) > len(deltas) * .8)
        return offset_defaults[neutral.name]

    changed = 0
    for key in shapes.key_blocks:
        if not key.name.startswith('Emo_') or 'default' in key.name.lower() or key.relative_key != basis:
            continue
        family = re.match(r'^(Emo_.+_(?:Brow|Eye|Mouth)_\d+)_', key.name)
        animation = re.match(r'^(Emo_.+)_Ani_', key.name)
        closed_eye = re.match(r'^(Emo_.+)_Close\d+_Eye$', key.name)
        neutral_name = (family.group(1) + '_Default' if family else
                        animation.group(1) + '_Ani_Default' if animation else
                        closed_eye.group(1) + '_Default_Eye' if closed_eye else None)
        neutral = shapes.key_blocks.get(neutral_name) if neutral_name else None
        if neutral and neutral != key and neutral.relative_key == basis and has_baked_pose(neutral):
            key.relative_key = neutral
            changed += 1
    if changed:
        mesh.update_tag()
    return changed
