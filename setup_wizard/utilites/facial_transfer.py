"""Shared, driver-preserving facial animation transfer for VMD and PMX."""
import ast
import bisect
import math
import operator
import re
from dataclasses import dataclass

import bpy


def resolve_node(owner, node):
    if isinstance(node, ast.Name) and node.id == 'owner':
        return owner
    if isinstance(node, ast.Attribute):
        return getattr(resolve_node(owner, node.value), node.attr)
    if isinstance(node, ast.Subscript):
        return resolve_node(owner, node.value)[ast.literal_eval(node.slice)]
    raise ValueError('Unsupported control path')


@dataclass(frozen=True)
class Control:
    owner: object
    path: str
    index: int = -1

    def read(self):
        value = self.owner.path_resolve(self.path)
        return float(value if self.index < 0 else value[self.index])

    def write(self, value):
        if self.index >= 0:
            self.owner.path_resolve(self.path)[self.index] = value
        else:
            # Parse only RNA attributes and literal subscripts, never execute a path.
            node = ast.parse('owner.' + self.path if not self.path.startswith('[')
                             else 'owner' + self.path, mode='eval').body
            parent = resolve_node(self.owner, node.value)
            if isinstance(node, ast.Attribute):
                setattr(parent, node.attr, value)
            elif isinstance(node, ast.Subscript):
                parent[ast.literal_eval(node.slice)] = value
            else:
                raise ValueError('Unsupported control path')
        self.owner.update_tag()

    def keyframe(self, frame):
        kwargs = dict(data_path=self.path, frame=frame, group='VMD Face')
        if self.index >= 0:
            kwargs['index'] = self.index
        if not self.owner.keyframe_insert(**kwargs):
            raise RuntimeError('Cannot keyframe facial control: ' + self.path)


def curve_points(frames):
    """Sorted VMD weights, with deterministic handling of duplicate frames."""
    points = {}
    for frame in frames:
        number, weight = int(frame.frame_number), float(frame.weight)
        if number < 0 or not math.isfinite(weight):
            raise ValueError('Invalid facial keyframe')
        points[number] = weight
    return sorted(points.items())


def sample(points, frame):
    # VMD holds the first/last weight outside the keyed interval.
    i = bisect.bisect_right(points, (frame, float('inf')))
    if i == 0:
        return points[0][1]
    if i == len(points):
        return points[-1][1]
    x0, y0 = points[i-1]
    x1, y1 = points[i]
    return y0 + (y1-y0) * (frame-x0) / (x1-x0)


def solve_x_for_value(samples, desired, reference=0.0):
    """Invert a sampled driver, selecting the nearest branch to its neutral."""
    candidates = []
    desired = max(min(y for _, y in samples), min(max(y for _, y in samples), desired))
    for (x0, y0), (x1, y1) in zip(samples, samples[1:]):
        if min(y0, y1)-1e-8 <= desired <= max(y0, y1)+1e-8:
            if abs(y1-y0) < 1e-8:
                candidates.append(max(min(x0, x1), min(max(x0, x1), reference)))
            else:
                candidates.append(x0+(desired-y0)*(x1-x0)/(y1-y0))
    return min(candidates, key=lambda x: abs(x-reference)) if candidates else min(
        samples, key=lambda p: (abs(p[1]-desired), abs(p[0]-reference)))[0]


def driver_controls(driver, allowed_owners):
    controls = []
    for variable in driver.variables:
        target = variable.targets[0]
        if target.id not in allowed_owners:
            continue
        if variable.type == 'TRANSFORMS':
            if target.transform_space != 'LOCAL_SPACE' or not target.bone_target:
                continue
            bone = target.id.pose.bones.get(target.bone_target)
            kind, axis = target.transform_type.rsplit('_', 1)
            prop = {'LOC': 'location', 'ROT': 'rotation_euler', 'SCALE': 'scale'}.get(kind)
            if not bone or not prop or axis not in 'XYZ':
                continue
            if kind == 'ROT' and bone.rotation_mode in {'QUATERNION', 'AXIS_ANGLE'}:
                continue
            control = Control(target.id, bone.path_from_id(prop), 'XYZ'.index(axis))
        elif variable.type == 'SINGLE_PROP' and target.data_path:
            match = re.fullmatch(r'(.+)\[(\d+)\]', target.data_path)
            control = (Control(target.id, match[1], int(match[2])) if match
                       else Control(target.id, target.data_path))
        else:
            continue
        try:
            if math.isfinite(control.read()) and control not in controls:
                controls.append(control)
        except (ValueError, TypeError, AttributeError, KeyError):
            continue
    return controls


def scalar_expression(expression, variable):
    """Compile a small arithmetic AST into functions, without executing Python."""
    binary = {ast.Add: operator.add, ast.Sub: operator.sub,
              ast.Mult: operator.mul, ast.Div: operator.truediv}
    functions = {'min': min, 'max': max, 'abs': abs}

    def build(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return lambda x: node.value
        if isinstance(node, ast.Name) and node.id == variable:
            return lambda x: x
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            child = build(node.operand)
            sign = -1 if isinstance(node.op, ast.USub) else 1
            return lambda x: sign*child(x)
        if isinstance(node, ast.BinOp) and type(node.op) in binary:
            if isinstance(node.op, ast.Div) and not (
                    isinstance(node.right, ast.Constant)
                    and type(node.right.value) in (int, float) and node.right.value != 0):
                raise ValueError('Variable denominator requires Blender evaluation')
            left, right, operation = build(node.left), build(node.right), binary[type(node.op)]
            return lambda x: operation(left(x), right(x))
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in functions and not node.keywords):
            children, function = [build(arg) for arg in node.args], functions[node.func.id]
            return lambda x: function(*(child(x) for child in children))
        raise ValueError('Expression requires Blender evaluation')

    return build(ast.parse(expression, mode='eval').body)


def arithmetic_sampler(fcurve, key):
    """Recognize simple drivers; constraints and custom driver logic use Blender."""
    driver = fcurve.driver
    # Blender adds an identity Generator to many driver curves by default.
    modifiers_change_value = any(not m.mute and not (
        m.type == 'GENERATOR' and m.mode == 'POLYNOMIAL' and not m.use_additive
        and tuple(m.coefficients) == (0.0, 1.0)) for m in fcurve.modifiers)
    if (driver.type != 'SCRIPTED' or driver.use_self or len(driver.variables) != 1
            or modifiers_change_value or fcurve.keyframe_points):
        return None
    variable = driver.variables[0]
    target = variable.targets[0]
    limits = []
    if variable.type == 'TRANSFORMS':
        bone = target.id.pose.bones.get(target.bone_target)
        if not bone or not target.transform_type.startswith(('LOC_', 'SCALE_')):
            return None
        for constraint in bone.constraints:
            if constraint.mute or constraint.influence == 0:
                continue
            if (constraint.type != 'LIMIT_LOCATION' or constraint.owner_space != 'LOCAL'
                    or constraint.influence != 1 or not target.transform_type.startswith('LOC_')):
                return None
            axis = target.transform_type[-1].lower()
            limits.append((getattr(constraint, 'min_'+axis) if getattr(constraint, 'use_min_'+axis) else -math.inf,
                           getattr(constraint, 'max_'+axis) if getattr(constraint, 'use_max_'+axis) else math.inf))
    elif variable.type != 'SINGLE_PROP':
        return None
    try:
        expression = scalar_expression(driver.expression, variable.name)
    except (ValueError, SyntaxError):
        return None

    def measure(x):
        for lower, upper in limits:
            x = max(lower, min(upper, x))
        value = float(expression(x))
        if not math.isfinite(value):
            raise ValueError('Non-finite driver weight')
        return max(key.slider_min, min(key.slider_max, value))

    return measure


def calibrate(context, keys, key, controls, fcurve=None):
    """Probe at the current pose and restore every touched channel, even on failure."""
    originals = {c: c.read() for c in controls}
    best = None
    try:
        for control in controls:
            neutral = originals[control]
            def evaluate(x):
                control.write(x)
                context.view_layer.update()
                value = float(keys.evaluated_get(context.evaluated_depsgraph_get()).key_blocks[key.name].value)
                if not math.isfinite(value):
                    raise ValueError('Driver returned a non-finite weight')
                return value

            measure = evaluate
            fast = arithmetic_sampler(fcurve, key) if fcurve else None
            if fast:
                # Verify the actual rig first. A driver can differ from its formula
                # through Blender's transform evaluation, limits or animation stack.
                try:
                    if all(abs(evaluate(x)-fast(x)) <= 1e-5
                           for x in (neutral, neutral-.173, neutral+.173)):
                        measure = fast
                except (ValueError, ArithmeticError, TypeError):
                    pass
            # Include small facial ranges as well as larger selector/scale controls.
            xs = sorted({neutral, 0.0, 1.0, *[neutral+s*v for s in (-1, 1)
                         for v in (.001, .005, .01, .025, .05, .1, .2, .5, 1, 2)]})
            samples = []
            for x in xs:
                value = measure(x)
                samples.append((x, value))
            # Resolve clamp boundaries and curved expressions instead of assuming
            # a coarse interval is linear (facial controls often move only .01).
            def refine(left, right, depth=0):
                x = (left[0]+right[0])*.5
                y = measure(x)
                mid = (x, y)
                if depth < 10 and abs(y-(left[1]+right[1])*.5) > 1e-5:
                    return refine(left, mid, depth+1) + refine(mid, right, depth+1)
                return [left, mid]
            samples = [p for left, right in zip(samples, samples[1:])
                       for p in refine(left, right)] + [samples[-1]]
            control.write(neutral)
            spread = max(y for _, y in samples)-min(y for _, y in samples)
            if spread > 1e-4 and (best is None or spread > best[0]):
                best = spread, control, samples, neutral
    finally:
        for control, value in originals.items():
            control.write(value)
        context.view_layer.update()
    return best[1:] if best else None


def action_curves(data):
    action = data.action
    if not action:
        return []
    if hasattr(action, 'layers'):
        slot = data.action_slot
        return [curve for layer in action.layers for strip in layer.strips
                for bag in strip.channelbags if slot and bag.slot_handle == slot.handle
                for curve in bag.fcurves]
    return list(action.fcurves)


def write_channel(control, coordinates):
    """Create the RNA channel once, then populate its points in a single batch."""
    frame, value = coordinates[0]
    control.write(value)
    control.keyframe(frame)
    curve = next(c for c in action_curves(control.owner.animation_data)
                 if c.data_path == control.path and c.array_index == max(0, control.index))
    points = curve.keyframe_points
    existing = [(p.co.x, p.co.y) for p in points]
    points.add(len(coordinates)-1)
    points.foreach_set('co', [v for pair in existing+coordinates[1:] for v in pair])
    for point in points:
        if coordinates[0][0] <= point.co.x <= coordinates[-1][0]:
            point.interpolation = 'LINEAR'
    curve.update()


def transfer_tracks(context, objects, motion, start, action_name, mapping=None, owners=None):
    """Bake linear facial tracks, keeping drivers and previous actions intact.

    Returns (imported source names, diagnostic messages). Shared channels are
    written once per frame; different axes on the same bone remain independent.
    """
    mapping = SHAPEKEY_MAP if mapping is None else mapping
    tracks = {name: curve_points(frames) for name, frames in motion.items() if frames}
    if not tracks:
        return set(), []
    objects = list(objects)
    allowed = set(owners or ())
    allowed.update(obj.data.shape_keys for obj in objects if obj.data.shape_keys)
    resolved, diagnostics, seen = [], [], set()
    original_frame, subframe = context.scene.frame_current, context.scene.frame_subframe
    actions, values, touched = {}, {}, {}
    imported = set()
    try:
        context.scene.frame_set(start)
        for obj in objects:
            keys = obj.data.shape_keys
            if not keys or keys in seen:
                continue
            seen.add(keys)
            matches = {}
            for name in tracks:
                # Exact PMX/custom names take precedence over aliases.
                targets = [name] if name in keys.key_blocks else mapping.get(name, ())
                targets = [targets] if isinstance(targets, str) else targets
                # The manual O is model-specific; fall back to standard mouth keys.
                if targets == ['Mouth_O_manual'] and 'Mouth_O_manual' not in keys.key_blocks:
                    targets = ['Mouth_Open01', 'Mouth_O01'] if name != 'え' else ['Mouth_Angry01']
                    targets = next(([t] for t in targets if t in keys.key_blocks), [])
                for target in targets:
                    if target in keys.key_blocks:
                        matches.setdefault(target, []).append(name)
            drivers = {d.data_path: d for d in keys.animation_data.drivers} if keys.animation_data else {}
            for target, sources in matches.items():
                key = keys.key_blocks[target]
                path = key.path_from_id('value')
                driver = drivers.get(path)
                if driver:
                    if driver.mute:
                        diagnostics.append(f'{obj.name}/{target}: muted driver; skipped')
                        continue
                    controls = driver_controls(driver.driver, allowed)
                    result = calibrate(context, keys, key, controls, driver) if controls else None
                    if not result:
                        diagnostics.append(f'{obj.name}/{target}: unsupported or unresponsive driver; skipped')
                        continue
                    control, samples, neutral = result
                else:
                    control, samples, neutral = Control(keys, path), None, key.value
                resolved.append((control, samples, neutral, sources, key.slider_min, key.slider_max))

        groups = {}
        for entry in resolved:
            groups.setdefault(entry[0], []).append(entry)
        if not groups:
            return imported, diagnostics
        # Copy actions once per owner. In particular, keep newly imported body keys.
        for control in groups:
            owner = control.owner
            values[control] = control.read()
            if owner not in actions:
                data = owner.animation_data_create()
                previous, slot = data.action, data.action_slot
                new = previous.copy() if previous else bpy.data.actions.new(action_name+' Face')
                actions[owner] = previous, slot, new
                data.action = new
                if slot:
                    data.action_slot = new.slots[slot.identifier]
            touched.setdefault(owner, set()).add((control.path, max(0, control.index)))
        end = max(tracks[name][-1][0] for entry in resolved for name in entry[3])
        # Old subframe keys inside the imported interval must not distort the
        # linear bake. Other channels and keys outside this interval survive.
        for owner, channels in touched.items():
            for curve in action_curves(owner.animation_data):
                if (curve.data_path, curve.array_index) in channels:
                    for point in reversed(list(curve.keyframe_points)):
                        if start <= point.co.x <= start+end:
                            curve.keyframe_points.remove(point, fast=True)
                    curve.update()
        weights = {name: [sample(tracks[name], frame) for frame in range(end+1)]
                   for name in {n for entry in resolved for n in entry[3]}}
        for control, entries in groups.items():
            coordinates, solved = [], {}
            for frame in range(end+1):
                winner = max(range(len(entries)),
                             key=lambda i: max(weights[n][frame] for n in entries[i][3]))
                entry = entries[winner]
                _, samples, neutral, sources, lower, upper = entry
                weight = max(weights[n][frame] for n in sources)
                weight = max(lower, min(upper, weight))
                cache_key = winner, weight
                if cache_key not in solved:
                    solved[cache_key] = solve_x_for_value(samples, weight, neutral) if samples else weight
                coordinates.append((start+frame, solved[cache_key]))
            write_channel(control, coordinates)
        for previous, _, _ in actions.values():
            if previous:
                previous.use_fake_user = True
        imported.update(n for entry in resolved for n in entry[3])
        return imported, diagnostics
    except Exception:
        for owner, (previous, slot, new) in actions.items():
            owner.animation_data.action = previous
            if slot:
                owner.animation_data.action_slot = slot
            if not new.users:
                bpy.data.actions.remove(new)
        raise
    finally:
        for control, value in values.items():
            control.write(value)
        context.scene.frame_set(original_frame, subframe=subframe)

SHAPEKEY_MAP = {
    "真面目": ["Brow_Trouble_L", "Brow_Trouble_R"],
    "困る": ["Brow_Trouble_L", "Brow_Trouble_R"],
    "困る左": "Brow_Trouble_L",
    "困る右": "Brow_Trouble_R",
    "にこり": ["Brow_Smily_L", "Brow_Smily_R"],
    "にこり左": "Brow_Smily_L",
    "にこり右": "Brow_Smily_R",
    "怒り": ["Brow_Angry_L", "Brow_Angry_R"],
    "怒り左": "Brow_Angry_L",
    "怒り右": "Brow_Angry_R",
    "恥ずかしい": ["Brow_Shy_L", "Brow_Shy_R"],
    "恥ずかしい左": "Brow_Shy_L",
    "恥ずかしい右": "Brow_Shy_R",
    "上": ["Brow_Up_L", "Brow_Up_R"],
    "上左": "Brow_Up_L",
    "上右": "Brow_Up_R",
    "下": ["Brow_Down_L", "Brow_Down_R"],
    "下左": "Brow_Down_L",
    "下右": "Brow_Down_R",
    "前": ["Brow_Squeeze_L", "Brow_Squeeze_R"],
    "前左": "Brow_Squeeze_L",
    "前右": "Brow_Squeeze_R",
    "まばたき": ["Eye_WinkB_L", "Eye_WinkB_R"],
    "笑い": ["Eye_WinkC_L", "Eye_WinkC_R"],
    "ウィンク": "Eye_WinkA_L",
    "ウィンク右": "Eye_WinkA_R",
    "ウィンク２": "Eye_WinkB_L",
    "ウィンク２右": "Eye_WinkB_R",
    "なごみ": ["Eye_WinkC_L", "Eye_WinkC_R"],
    "なごみ左": "Eye_WinkC_L",
    "なごみ右": "Eye_WinkC_R",
    "びっくり": "Eye_Ha",
    "じと目": "Eye_Jito",
    "悲しむ": "Eye_Wail",
    "怒り目": "Eye_Hostility",
    "ジト目": "Eye_Tired",
    "眼角上": "Eye_WUp",
    "眼角下": "Eye_WDown",
    "下眼上": "Eye_Lowereyelid",
    "じと目2": ["Eye_WinkB_L", "Eye_WinkB_R"],
    "はちゅ目": ["Eye_WinkB_L", "Eye_WinkB_R"],
    "あ": "Mouth_A01",
    "い": "Mouth_Line01",
    "う": "Mouth_Line02",
    # shape key esculpido a mano para la boca en O, no depende del hueso
    # compartido con Mouth_A01/Mouth_Line01.
    "え": "Mouth_O_manual",
    "お": "Mouth_O_manual",
    "お２": "Mouth_O_manual",
    "にやり": "Mouth_Smile01",
    "ワ": "Mouth_Smile02",
    "ん": "Mouth_Default",
    "い１": "Mouth_Angry02",
    "い２": "Mouth_Angry03",
    "あ２": "Mouth_Fury01",
    "にやり２": "Mouth_Doya01",
    "にやり３": "Mouth_Doya02",
    "ω": "Mouth_Neko01",
    "てへぺろ": "Mouth_Pero01",
    "ぺろっ": "Mouth_Pero02",
    "口角上げ": "Mouth_Smile01",
    "口角下げ": "Mouth_Default",
    "口横広げ": "Mouth_Line01",
    "口横狭め": "Mouth_Line02",
    "舌広げ": "Mouth_BigTongue01",
}


