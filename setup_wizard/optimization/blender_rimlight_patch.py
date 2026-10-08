import bpy

def is_blender_official():
    """
    Returns True if running in official Blender (e.g. 5.2 / 4.x)
    where custom Goo Engine shader nodes (ShaderNodeCurvature, ShaderNodeScreenspaceInfo) do not exist.
    """
    return not hasattr(bpy.types, 'ShaderNodeCurvature')


def patch_depth_based_rim_group(ng):
    """
    Patches 'Depth-based Rim' node group in memory for Blender 5.2 / standard Blender.
    Replaces undefined Curvature node with LayerWeight (Facing) working from the border inwards.
    When Scale == 0, rim light is strictly 0. As Scale increases, rim light begins
    at the silhouette border and expands inwards without deadzones.
    """
    if not ng:
        return False
        
    math_node = ng.nodes.get('Math')
    if not math_node:
        return False

    g_in = next((n for n in ng.nodes if n.type == 'GROUP_INPUT'), None)

    # 1. Layer Weight node for silhouette detection (Facing is 0 at center, ~0.76 at border)
    lw = ng.nodes.get('Blender_LayerWeight_Rim')
    if not lw:
        lw = ng.nodes.new('ShaderNodeLayerWeight')
        lw.name = 'Blender_LayerWeight_Rim'
        lw.label = 'Blender Native Rim (Layer Weight)'
        lw.location = (math_node.location.x - 600, math_node.location.y)
    lw.inputs['Blend'].default_value = 0.5

    # 2. Normalize Facing so border reaches ~1.0
    fnorm = ng.nodes.get('Blender_Rim_FacingNorm')
    if not fnorm:
        fnorm = ng.nodes.new('ShaderNodeMath')
        fnorm.name = 'Blender_Rim_FacingNorm'
        fnorm.operation = 'MULTIPLY'
        fnorm.inputs[1].default_value = 1.0
        fnorm.location = (math_node.location.x - 400, math_node.location.y + 100)
    else:
        fnorm.operation = 'MULTIPLY'
        fnorm.inputs[1].default_value = 1.0
    ng.links.new(lw.outputs['Facing'], fnorm.inputs[0])

    # 3. Handle Rim Scale input
    scale_out = None
    if g_in:
        for out in g_in.outputs:
            if 'scale' in out.name.lower():
                scale_out = out
                break

    scale_sock = None
    if scale_out:
        if scale_out.type == 'VECTOR':
            sep_xyz = ng.nodes.get('Blender_Rim_SepScale')
            if not sep_xyz:
                sep_xyz = ng.nodes.new('ShaderNodeSeparateXYZ')
                sep_xyz.name = 'Blender_Rim_SepScale'
                sep_xyz.location = (math_node.location.x - 700, math_node.location.y - 150)
            ng.links.new(scale_out, sep_xyz.inputs['Vector'])

            # Anisotropic Rim: Normal in camera space to separate horizontal (X) and vertical (Y)
            geom = ng.nodes.get('Blender_Rim_Geom')
            if not geom:
                geom = ng.nodes.new('ShaderNodeNewGeometry')
                geom.name = 'Blender_Rim_Geom'
                geom.location = (math_node.location.x - 900, math_node.location.y - 300)

            vtrans = ng.nodes.get('Blender_Rim_VTrans')
            if not vtrans:
                vtrans = ng.nodes.new('ShaderNodeVectorTransform')
                vtrans.name = 'Blender_Rim_VTrans'
                vtrans.vector_type = 'NORMAL'
                vtrans.convert_from = 'WORLD'
                vtrans.convert_to = 'CAMERA'
                vtrans.location = (math_node.location.x - 700, math_node.location.y - 300)
            ng.links.new(geom.outputs['Normal'], vtrans.inputs['Vector'])

            sep_norm = ng.nodes.get('Blender_Rim_SepNorm')
            if not sep_norm:
                sep_norm = ng.nodes.new('ShaderNodeSeparateXYZ')
                sep_norm.name = 'Blender_Rim_SepNorm'
                sep_norm.location = (math_node.location.x - 550, math_node.location.y - 300)
            ng.links.new(vtrans.outputs['Vector'], sep_norm.inputs['Vector'])

            # nx^2 and ny^2
            nx_sq = ng.nodes.get('Blender_Rim_NxSq')
            if not nx_sq:
                nx_sq = ng.nodes.new('ShaderNodeMath')
                nx_sq.name = 'Blender_Rim_NxSq'
                nx_sq.operation = 'MULTIPLY'
                nx_sq.location = (math_node.location.x - 400, math_node.location.y - 250)
            ng.links.new(sep_norm.outputs['X'], nx_sq.inputs[0])
            ng.links.new(sep_norm.outputs['X'], nx_sq.inputs[1])

            ny_sq = ng.nodes.get('Blender_Rim_NySq')
            if not ny_sq:
                ny_sq = ng.nodes.new('ShaderNodeMath')
                ny_sq.name = 'Blender_Rim_NySq'
                ny_sq.operation = 'MULTIPLY'
                ny_sq.location = (math_node.location.x - 400, math_node.location.y - 350)
            ng.links.new(sep_norm.outputs['Y'], ny_sq.inputs[0])
            ng.links.new(sep_norm.outputs['Y'], ny_sq.inputs[1])

            # scale_x * nx^2 and scale_y * ny^2
            x_eff = ng.nodes.get('Blender_Rim_XEff')
            if not x_eff:
                x_eff = ng.nodes.new('ShaderNodeMath')
                x_eff.name = 'Blender_Rim_XEff'
                x_eff.operation = 'MULTIPLY'
                x_eff.location = (math_node.location.x - 250, math_node.location.y - 200)
            ng.links.new(sep_xyz.outputs['X'], x_eff.inputs[0])
            ng.links.new(nx_sq.outputs['Value'], x_eff.inputs[1])

            y_eff = ng.nodes.get('Blender_Rim_YEff')
            if not y_eff:
                y_eff = ng.nodes.new('ShaderNodeMath')
                y_eff.name = 'Blender_Rim_YEff'
                y_eff.operation = 'MULTIPLY'
                y_eff.location = (math_node.location.x - 250, math_node.location.y - 300)
            ng.links.new(sep_xyz.outputs['Y'], y_eff.inputs[0])
            ng.links.new(ny_sq.outputs['Value'], y_eff.inputs[1])

            eff_scale = ng.nodes.get('Blender_Rim_EffScale')
            if not eff_scale:
                eff_scale = ng.nodes.new('ShaderNodeMath')
                eff_scale.name = 'Blender_Rim_EffScale'
                eff_scale.operation = 'ADD'
                eff_scale.location = (math_node.location.x - 100, math_node.location.y - 250)
            ng.links.new(x_eff.outputs['Value'], eff_scale.inputs[0])
            ng.links.new(y_eff.outputs['Value'], eff_scale.inputs[1])

            scale_sock = eff_scale.outputs['Value']
        else:
            scale_sock = scale_out

    # 4. smul = Scale * 0.055 (maps full slider travel 0..10 to exact max rim width of 0.55)
    smul = ng.nodes.get('Blender_Rim_ScaleMul')
    if not smul:
        smul = ng.nodes.new('ShaderNodeMath')
        smul.name = 'Blender_Rim_ScaleMul'
        smul.operation = 'MULTIPLY'
        smul.inputs[1].default_value = 0.055
        smul.location = (math_node.location.x - 400, math_node.location.y - 150)
    else:
        smul.operation = 'MULTIPLY'
        smul.inputs[1].default_value = 0.055
    if scale_sock:
        ng.links.new(scale_sock, smul.inputs[0])
    else:
        smul.inputs[0].default_value = 5.0

    # 5. Threshold = 1.0 - smul
    thresh = ng.nodes.get('Blender_Rim_Thresh')
    if not thresh:
        thresh = ng.nodes.new('ShaderNodeMath')
        thresh.name = 'Blender_Rim_Thresh'
        thresh.operation = 'SUBTRACT'
        thresh.inputs[0].default_value = 1.0
        thresh.location = (math_node.location.x - 200, math_node.location.y - 100)
    else:
        thresh.operation = 'SUBTRACT'
        thresh.inputs[0].default_value = 1.0
    ng.links.new(smul.outputs['Value'], thresh.inputs[1])

    # 6. Greater than: Facing_norm > Threshold (silhouette edge inwards)
    math_node.operation = 'GREATER_THAN'
    for l in list(math_node.inputs[0].links):
        ng.links.remove(l)
    for l in list(math_node.inputs[1].links):
        ng.links.remove(l)
    ng.links.new(fnorm.outputs['Value'], math_node.inputs[0])
    ng.links.new(thresh.outputs['Value'], math_node.inputs[1])

    # 7. Multiply rim intensity x2
    rim_boost = ng.nodes.get('Blender_Rim_Boost')
    if not rim_boost:
        rim_boost = ng.nodes.new('ShaderNodeMath')
        rim_boost.name = 'Blender_Rim_Boost'
        rim_boost.operation = 'MULTIPLY'
        rim_boost.location = (math_node.location.x + 150, math_node.location.y)
    rim_boost.inputs[1].default_value = 2.0
    ng.links.new(math_node.outputs['Value'], rim_boost.inputs[0])

    # 8. Feed rim_boost directly into Math.003 and Math.013
    for next_name in ['Math.003', 'Math.013']:
        next_n = ng.nodes.get(next_name)
        if next_n and len(next_n.inputs) > 0:
            for l in list(next_n.inputs[0].links):
                if l.from_node != rim_boost:
                    ng.links.remove(l)
            ng.links.new(rim_boost.outputs['Value'], next_n.inputs[0])

    # Clean up obsolete nodes if present
    for old_name in ['Blender_Rim_IsActive', 'Blender_Rim_ActiveMul', 'Blender_Rim_ThreshClamp', 'Blender_Rim_OneMinus', 'Blender_Rim_ScaleBoost']:
        old_n = ng.nodes.get(old_name)
        if old_n:
            ng.nodes.remove(old_n)

    # Unlink legacy undefined Curvature node if present
    curv = next((n for n in ng.nodes if 'curvature' in n.name.lower() or n.type in ('CURVATURE', 'CUSTOM')), None)
    if curv:
        for out in curv.outputs:
            for l in list(out.links):
                ng.links.remove(l)

    return True


def patch_genshin_rimlight_group(ng):
    """
    Patches 'Genshin Impact - Rimlight' node group in memory for Blender 5.2 / standard Blender.
    Replaces undefined Screenspace Info nodes.
    """
    if not ng:
        return False

    map_range = ng.nodes.get('Map Range')
    if not map_range:
        return False

    g_in = next((n for n in ng.nodes if n.type == 'GROUP_INPUT'), None)

    lw = ng.nodes.get('Blender_LayerWeight_Rim')
    if not lw:
        lw = ng.nodes.new('ShaderNodeLayerWeight')
        lw.name = 'Blender_LayerWeight_Rim'
        lw.location = (map_range.location.x - 600, map_range.location.y)
    lw.inputs['Blend'].default_value = 0.5

    fnorm = ng.nodes.get('Blender_Rim_FacingNorm')
    if not fnorm:
        fnorm = ng.nodes.new('ShaderNodeMath')
        fnorm.name = 'Blender_Rim_FacingNorm'
        fnorm.operation = 'MULTIPLY'
        fnorm.inputs[1].default_value = 1.0
        fnorm.location = (map_range.location.x - 400, map_range.location.y + 100)
    else:
        fnorm.operation = 'MULTIPLY'
        fnorm.inputs[1].default_value = 1.0
    ng.links.new(lw.outputs['Facing'], fnorm.inputs[0])

    scale_out = None
    if g_in:
        for out in g_in.outputs:
            if 'scale' in out.name.lower():
                scale_out = out
                break

    scale_sock = None
    if scale_out:
        if scale_out.type == 'VECTOR':
            sep_xyz = ng.nodes.get('Blender_Rim_SepScale')
            if not sep_xyz:
                sep_xyz = ng.nodes.new('ShaderNodeSeparateXYZ')
                sep_xyz.name = 'Blender_Rim_SepScale'
                sep_xyz.location = (map_range.location.x - 600, map_range.location.y - 150)
            ng.links.new(scale_out, sep_xyz.inputs['Vector'])
            scale_sock = sep_xyz.outputs['X']
        else:
            scale_sock = scale_out

    # 4. smul = Scale * 0.055 (maps slider position to max rim width of 0.55)
    smul = ng.nodes.get('Blender_Rim_ScaleMul')
    if not smul:
        smul = ng.nodes.new('ShaderNodeMath')
        smul.name = 'Blender_Rim_ScaleMul'
        smul.operation = 'MULTIPLY'
        smul.inputs[1].default_value = 0.055
        smul.location = (map_range.location.x - 400, map_range.location.y - 150)
    else:
        smul.operation = 'MULTIPLY'
        smul.inputs[1].default_value = 0.055
    if scale_sock:
        ng.links.new(scale_sock, smul.inputs[0])
    else:
        smul.inputs[0].default_value = 0.5

    # 5. Threshold = 1.0 - smul
    thresh = ng.nodes.get('Blender_Rim_Thresh')
    if not thresh:
        thresh = ng.nodes.new('ShaderNodeMath')
        thresh.name = 'Blender_Rim_Thresh'
        thresh.operation = 'SUBTRACT'
        thresh.inputs[0].default_value = 1.0
        thresh.location = (map_range.location.x - 200, map_range.location.y - 100)
    else:
        thresh.operation = 'SUBTRACT'
        thresh.inputs[0].default_value = 1.0
    ng.links.new(smul.outputs['Value'], thresh.inputs[1])

    # 6. Greater than: Facing_norm > Threshold (silhouette edge inwards)
    gt = ng.nodes.get('Blender_Rim_GT')
    if not gt:
        gt = ng.nodes.new('ShaderNodeMath')
        gt.name = 'Blender_Rim_GT'
        gt.operation = 'GREATER_THAN'
        gt.location = (map_range.location.x - 50, map_range.location.y)
    ng.links.new(fnorm.outputs['Value'], gt.inputs[0])
    ng.links.new(thresh.outputs['Value'], gt.inputs[1])

    # 7. Multiply rim intensity x2
    rim_boost = ng.nodes.get('Blender_Rim_Boost')
    if not rim_boost:
        rim_boost = ng.nodes.new('ShaderNodeMath')
        rim_boost.name = 'Blender_Rim_Boost'
        rim_boost.operation = 'MULTIPLY'
        rim_boost.location = (map_range.location.x - 20, map_range.location.y)
    rim_boost.inputs[1].default_value = 2.0
    ng.links.new(gt.outputs['Value'], rim_boost.inputs[0])

    # 8. Feed rim_boost directly into Map Range Value
    for l in list(map_range.inputs['Value'].links):
        ng.links.remove(l)
    ng.links.new(rim_boost.outputs['Value'], map_range.inputs['Value'])

    # Clean up obsolete cutoff nodes if present
    for old_name in ['Blender_Rim_IsActive', 'Blender_Rim_ActiveMul', 'Blender_Rim_ThreshClamp', 'Blender_Rim_OneMinus']:
        old_n = ng.nodes.get(old_name)
        if old_n:
            ng.nodes.remove(old_n)

    return True


def patch_lit_rimlight_custom_group(ng):
    """
    Patches groups like 'Lit rimlight Hutao' that have undefined Curvature and a Color Ramp.
    """
    if not ng:
        return False
    cr = ng.nodes.get('Color Ramp')
    if not cr:
        return False

    lw = ng.nodes.get('Blender_LayerWeight_Rim')
    if not lw:
        lw = ng.nodes.new('ShaderNodeLayerWeight')
        lw.name = 'Blender_LayerWeight_Rim'
        lw.location = (cr.location.x - 300, cr.location.y)
    lw.inputs['Blend'].default_value = 0.5

    # Map Facing (0.65 .. 0.95) to Color Ramp Fac (0.0 .. stop_max) so it only lights the ~2cm edge
    mr = ng.nodes.get('Blender_Rim_MapRange')
    if not mr:
        mr = ng.nodes.new('ShaderNodeMapRange')
        mr.name = 'Blender_Rim_MapRange'
        mr.location = (cr.location.x - 150, cr.location.y)
    mr.clamp = True
    mr.inputs['From Min'].default_value = 0.65
    mr.inputs['From Max'].default_value = 0.95
    mr.inputs['To Min'].default_value = 0.0
    stop_max = cr.color_ramp.elements[-1].position if (hasattr(cr, 'color_ramp') and len(cr.color_ramp.elements) > 1) else 0.118
    mr.inputs['To Max'].default_value = stop_max

    ng.links.new(lw.outputs['Facing'], mr.inputs['Value'])

    for l in list(cr.inputs['Fac'].links):
        ng.links.remove(l)
    ng.links.new(mr.outputs['Result'], cr.inputs['Fac'])

    curv = next((n for n in ng.nodes if n.type in ('CURVATURE', 'CUSTOM') and 'curvature' in n.name.lower()), None)
    if curv:
        for out in curv.outputs:
            for l in list(out.links):
                ng.links.remove(l)
    return True


def patch_all_rimlight_groups_for_blender():
    """
    Checks all node groups in bpy.data.node_groups and patches Rim Light groups
    if running under Blender 5.2 / official Blender.
    Does nothing on Goo Engine to preserve native engine shaders.
    """
    if not is_blender_official():
        return False

    patched_any = False
    for ng in list(bpy.data.node_groups):
        ng_low = ng.name.lower()
        if 'depth-based rim' in ng_low or ng.name == 'Depth-based Rim':
            if patch_depth_based_rim_group(ng):
                patched_any = True
        elif 'genshin impact - rimlight' in ng_low or (('rimlight' in ng_low or 'rim light' in ng_low) and 'depth' not in ng_low and 'lit rimlight' not in ng_low):
            if patch_genshin_rimlight_group(ng):
                patched_any = True
        elif 'lit rimlight' in ng_low:
            if patch_lit_rimlight_custom_group(ng):
                patched_any = True

    return patched_any

