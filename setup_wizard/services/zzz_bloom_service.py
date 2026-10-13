# Author: setup_wizard team
# Purpose: Sets up Bloom post-processing for Zenless Zone Zero (Blender 4.1 native EEVEE Bloom panel, and Blender 4.2+ Compositor Bloom)

import bpy


def setup_zzz_bloom(scene=None):
    """Configures Bloom post-processing for Zenless Zone Zero.
    
    - In Blender 4.1 and earlier (< 4.2):
      Configures the native EEVEE Bloom panel in Render Properties exactly as shown in the settings:
        * Bloom (use_bloom): True
        * Threshold: 0.800
        * Knee: 0.500
        * Radius: 6.500
        * Color: #FFE6DA (linear RGB: 1.0, 0.789, 0.697)
        * Intensity: 0.300
        * Clamp: 0.000
    
    - In Blender 4.2+ (and 5.x):
      Since EEVEE Next removed the native Bloom panel from Render Properties,
      bloom is configured via the Compositor Glare node (Bloom type) and Viewport Compositing
      (use_compositor = 'ALWAYS') so the bloom effect appears in the 3D viewport in real time.
    """
    if scene is None:
        scene = bpy.context.scene

    # 1. Blender < 4.2: Native EEVEE Bloom panel (Blender 4.1, 4.0, 3.x)
    is_legacy_eevee = hasattr(scene, "eevee") and hasattr(scene.eevee, "use_bloom")
    if is_legacy_eevee:
        try:
            if hasattr(scene.render, "engine"):
                scene.render.engine = 'BLENDER_EEVEE'
            scene.eevee.use_bloom = True
            scene.eevee.bloom_threshold = 0.8
            scene.eevee.bloom_knee = 0.5
            scene.eevee.bloom_radius = 6.5
            scene.eevee.bloom_color = (1.0, 0.789, 0.697)
            scene.eevee.bloom_intensity = 0.3
            scene.eevee.bloom_clamp = 0.0
            print("[ZZZ] Configured native Blender 4.1 EEVEE Bloom panel.")
            return
        except Exception as ex:
            print(f"[ZZZ] EEVEE native bloom setup notice: {ex}")

    # 2. Modern Blender (4.2+, 5.x) Compositor Bloom setup
    try:
        from setup_wizard.genshin_compositing_node_setup import (
            get_node_tree,
            get_output_node_name,
            get_output_node_type,
        )

        if hasattr(scene, "use_nodes"):
            scene.use_nodes = True

        tree = get_node_tree(scene)
        if not tree:
            return

        # Ensure Render Layers node
        rl_node = tree.nodes.get("Render Layers")
        if not rl_node:
            for n in tree.nodes:
                if n.type == 'R_LAYERS' or isinstance(n, bpy.types.CompositorNodeRLayers):
                    rl_node = n
                    break
        if not rl_node:
            rl_node = tree.nodes.new(type="CompositorNodeRLayers")
            rl_node.name = "Render Layers"
        rl_node.location = (-250, 400)

        # Ensure Composite / Output node
        out_name = get_output_node_name()
        out_type = get_output_node_type()
        comp_node = tree.nodes.get(out_name)
        if not comp_node:
            for n in tree.nodes:
                if n.type in {'COMPOSITE', 'GROUP_OUTPUT'}:
                    comp_node = n
                    break
        if not comp_node:
            comp_node = tree.nodes.new(type=out_type)
            comp_node.name = out_name
        comp_node.location = (500, 400)

        # Optional Viewer node for backdrop preview
        viewer_node = tree.nodes.get("Viewer")
        if not viewer_node:
            for n in tree.nodes:
                if n.type == 'VIEWER' or isinstance(n, bpy.types.CompositorNodeViewer):
                    viewer_node = n
                    break
        if not viewer_node:
            try:
                viewer_node = tree.nodes.new(type="CompositorNodeViewer")
                viewer_node.name = "Viewer"
            except Exception:
                viewer_node = None
        if viewer_node:
            viewer_node.location = (500, 150)

        # Glare / Bloom node
        bloom_node = tree.nodes.get("Bloom")
        if not bloom_node:
            for n in tree.nodes:
                if n.type == 'GLARE' or isinstance(n, bpy.types.CompositorNodeGlare):
                    bloom_node = n
                    break
        if not bloom_node:
            bloom_node = tree.nodes.new(type="CompositorNodeGlare")
            bloom_node.name = "Bloom"
            bloom_node.label = "Bloom"
        bloom_node.location = (120, 400)

        # Configure Bloom mode
        if "Type" in bloom_node.inputs:
            bloom_node.inputs["Type"].default_value = "Bloom"
        elif hasattr(bloom_node, "glare_type"):
            bloom_node.glare_type = "BLOOM"

        # Threshold: 0.200 (Compositor Glare threshold)
        if "Highlights Threshold" in bloom_node.inputs:
            bloom_node.inputs["Highlights Threshold"].default_value = 0.2
        elif "Threshold" in bloom_node.inputs:
            bloom_node.inputs["Threshold"].default_value = 0.2
        elif hasattr(bloom_node, "threshold"):
            bloom_node.threshold = 0.2

        # Knee / Smoothness: 0.500
        if "Highlights Smoothness" in bloom_node.inputs:
            bloom_node.inputs["Highlights Smoothness"].default_value = 0.5
        elif "Smoothness" in bloom_node.inputs:
            bloom_node.inputs["Smoothness"].default_value = 0.5

        # Intensity / Strength: 0.300
        if "Strength" in bloom_node.inputs:
            bloom_node.inputs["Strength"].default_value = 0.3

        # Radius / Size: 6.500 (normalized to 0.65 when max is 1.0)
        if "Size" in bloom_node.inputs:
            try:
                s_prop = bloom_node.inputs["Size"].bl_rna.properties["default_value"]
                bloom_node.inputs["Size"].default_value = 0.65 if s_prop.hard_max <= 1.0 else 6.5
            except Exception:
                bloom_node.inputs["Size"].default_value = 0.65
        elif hasattr(bloom_node, "size"):
            try:
                bloom_node.size = 6.5
            except Exception:
                pass

        # Color / Tint: peach (RGB 255, 230, 218 -> linear 1.0, 0.789, 0.697)
        if "Tint" in bloom_node.inputs:
            bloom_node.inputs["Tint"].default_value = (1.0, 0.789, 0.697, 1.0)

        # Quality: High
        if "Quality" in bloom_node.inputs:
            bloom_node.inputs["Quality"].default_value = "High"
        elif hasattr(bloom_node, "quality"):
            bloom_node.quality = "HIGH"

        # Clamp: 0.000 / False
        if "Clamp Highlights" in bloom_node.inputs:
            bloom_node.inputs["Clamp Highlights"].default_value = False

        # If a direct link existed between Render Layers and Composite, remove it so Bloom is inserted
        rl_out = rl_node.outputs.get("Image")
        comp_in = comp_node.inputs.get("Image")
        if rl_out and comp_in:
            for l in list(tree.links):
                if l.from_socket == rl_out and l.to_socket == comp_in:
                    tree.links.remove(l)

        # Connect Render Layers -> Bloom
        bloom_in = bloom_node.inputs.get("Image")
        if rl_out and bloom_in:
            if not any(l.from_socket == rl_out and l.to_socket == bloom_in for l in tree.links):
                tree.links.new(rl_out, bloom_in)

        # Connect Bloom -> Composite
        bloom_out = bloom_node.outputs.get("Image")
        if bloom_out and comp_in:
            if not any(l.from_socket == bloom_out and l.to_socket == comp_in for l in tree.links):
                tree.links.new(bloom_out, comp_in)

        # Connect Bloom -> Viewer
        if viewer_node and bloom_out:
            viewer_in = viewer_node.inputs.get("Image")
            if viewer_in and not any(l.from_socket == bloom_out and l.to_socket == viewer_in for l in tree.links):
                tree.links.new(bloom_out, viewer_in)

        # 3. Enable Viewport Compositing in all 3D viewports so bloom is visible immediately
        if hasattr(bpy, "context") and hasattr(bpy.context, "window_manager") and bpy.context.window_manager:
            for window in bpy.context.window_manager.windows:
                if window.screen:
                    for area in window.screen.areas:
                        if area.type == "VIEW_3D":
                            for space in area.spaces:
                                if space.type == "VIEW_3D" and hasattr(space, "shading") and hasattr(space.shading, "use_compositor"):
                                    space.shading.use_compositor = "ALWAYS"

        print("[ZZZ] Successfully configured Compositor Bloom post-processing.")
    except Exception as ex:
        print(f"[ZZZ] Compositor bloom setup warning: {ex}")
