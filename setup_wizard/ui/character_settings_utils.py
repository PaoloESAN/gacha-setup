# Central helper: per-armature game tag for Character Settings panels.
# Stores GameType.name on the rig object so Append keeps the info and
# each panel only shows for its own game + selected character.

GACHA_GAME_KEY = "gacha_game"
GACHA_CHAR_KEY = "gacha_character"


def stamp_rig_game(rig_obj, game_name, char_name=None):
    """Tags a rig armature or character object so its Character Settings panel can be resolved after Append / Setup."""
    if rig_obj is None:
        return
    invalidate_caches()
    try:
        rig_obj[GACHA_GAME_KEY] = str(game_name)
    except Exception:
        pass
    if char_name:
        try:
            rig_obj[GACHA_CHAR_KEY] = str(char_name)
        except Exception:
            pass
    # Also tag armature/mesh data (survives some Append/Link paths)
    try:
        data = getattr(rig_obj, "data", None)
        if data is not None:
            data[GACHA_GAME_KEY] = str(game_name)
            if char_name:
                data[GACHA_CHAR_KEY] = str(char_name)
    except Exception:
        pass

    if str(game_name).upper() in ("ZENLESS_ZONE_ZERO", "ZZZ"):
        st = getattr(bpy.context.scene, "zzz_shader_type", "LEGACY")
        try:
            if "zzz_shader_type" not in rig_obj:
                rig_obj["zzz_shader_type"] = st
            data = getattr(rig_obj, "data", None)
            if data is not None and "zzz_shader_type" not in data:
                data["zzz_shader_type"] = st
        except Exception:
            pass


def hide_eyestar_if_unrigged(context=None):
    """When setup runs without rigging for Genshin, ensure EyeStar has hide_viewport and hide_render set to True."""
    import bpy
    for obj in bpy.data.objects:
        if "eyestar" in obj.name.lower() or "eye_star" in obj.name.lower():
            try:
                obj.hide_set(True)
            except Exception:
                pass
            obj.hide_viewport = True
            obj.hide_render = True


# Backward-compatible alias
unhide_and_reset_eyestar = hide_eyestar_if_unrigged


_registered_rig_ids = set()


def patch_rig_ui_text_content(text_content):
    """Patches RigUI and RigLayers code in UI text scripts to support mesh selection and Object Mode."""
    if not text_content:
        return text_content

    # 1. Patch RigLayers.poll to resolve armature from selection (mesh or armature)
    old_layers_poll = """    @classmethod
    def poll(cls, context):
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False"""

    new_layers_poll = """    @classmethod
    def poll(cls, context):
        try:
            act = getattr(context, "active_object", None)
            if act and getattr(act, "type", None) == 'ARMATURE' and getattr(act, "data", None) and act.data.get("rig_id") == rig_id:
                return True
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(context)
            if arm and getattr(arm, "data", None) and arm.data.get("rig_id") == rig_id:
                return True
        except Exception:
            pass
        return False"""

    if old_layers_poll in text_content:
        text_content = text_content.replace(old_layers_poll, new_layers_poll)

    # 2. Patch RigUI.poll to resolve armature from selection (mesh or armature) only in POSE mode
    old_ui_poll = """    @classmethod
    def poll(cls, context):
        if context.mode != 'POSE':
            return False
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False"""

    prev_ui_poll = """    @classmethod
    def poll(cls, context):
        try:
            act = getattr(context, "active_object", None)
            if act and getattr(act, "type", None) == 'ARMATURE' and getattr(act, "data", None) and act.data.get("rig_id") == rig_id:
                return True
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(context)
            if arm and getattr(arm, "data", None) and arm.data.get("rig_id") == rig_id:
                return True
        except Exception:
            pass
        return False"""

    new_ui_poll = """    @classmethod
    def poll(cls, context):
        if context.mode != 'POSE':
            return False
        try:
            act = getattr(context, "active_object", None)
            if act and getattr(act, "type", None) == 'ARMATURE' and getattr(act, "data", None) and act.data.get("rig_id") == rig_id:
                return True
            from setup_wizard.ui.character_settings_utils import resolve_settings_armature
            arm = resolve_settings_armature(context)
            if arm and getattr(arm, "data", None) and arm.data.get("rig_id") == rig_id:
                return True
        except Exception:
            pass
        return False"""

    if old_ui_poll in text_content:
        text_content = text_content.replace(old_ui_poll, new_ui_poll)
    elif prev_ui_poll in text_content:
        text_content = text_content.replace(prev_ui_poll, new_ui_poll)

    # 3. Patch RigLayers arm_obj resolution in draw()
    old_arm_obj = "arm_obj = context.active_object if (context.active_object and context.active_object.type == 'ARMATURE') else (context.object if (context.object and context.object.type == 'ARMATURE') else None)"
    new_arm_obj = """arm_obj = context.active_object if (context.active_object and context.active_object.type == 'ARMATURE') else None
            if not arm_obj:
                try:
                    from setup_wizard.ui.character_settings_utils import resolve_settings_armature
                    arm_obj = resolve_settings_armature(context)
                except Exception:
                    pass"""

    if old_arm_obj in text_content:
        text_content = text_content.replace(old_arm_obj, new_arm_obj)

    # 4. Patch RigUI draw() to resolve arm from selection
    old_rig_ui_draw_start = """    def draw(self, context):
        layout = self.layout
        pose_bones = context.active_object.pose.bones"""

    prev_rig_ui_draw_start = """    def draw(self, context):
        layout = self.layout
        arm = context.active_object if (context.active_object and context.active_object.type == 'ARMATURE') else None
        if not arm:
            try:
                from setup_wizard.ui.character_settings_utils import resolve_settings_armature
                arm = resolve_settings_armature(context)
            except Exception:
                pass
        if not arm or not getattr(arm, "pose", None):
            return
        pose_bones = arm.pose.bones
        if context.mode != 'POSE':
            box = layout.box()
            row = box.row(align=True)
            row.label(text=f"Rig: {rig_name} (Object Mode)", icon='ARMATURE_DATA')
            op = row.operator("object.mode_set", text="Pose Mode", icon='POSE_HLT')
            op.mode = 'POSE'
            if "plate-settings" in pose_bones:
                for pk in ["Use Head Controller", "Use Neck Follow", "Use Eye Tracking"]:
                    if pk in pose_bones["plate-settings"]:
                        box.prop(pose_bones["plate-settings"], f'["{pk}"]', slider=True)
            return"""

    new_rig_ui_draw_start = """    def draw(self, context):
        layout = self.layout
        arm = context.active_object if (context.active_object and context.active_object.type == 'ARMATURE') else None
        if not arm:
            try:
                from setup_wizard.ui.character_settings_utils import resolve_settings_armature
                arm = resolve_settings_armature(context)
            except Exception:
                pass
        if not arm or not getattr(arm, "pose", None):
            return
        pose_bones = arm.pose.bones"""

    if prev_rig_ui_draw_start in text_content:
        text_content = text_content.replace(prev_rig_ui_draw_start, new_rig_ui_draw_start)
    elif old_rig_ui_draw_start in text_content:
        text_content = text_content.replace(old_rig_ui_draw_start, new_rig_ui_draw_start)

    return text_content


def _register_fallback_rig_panels(target_armature, r_id):
    """Creates standalone RigLayers and RigUI panels when text datablock was not appended."""
    import bpy
    char_name = resolve_character_name(target_armature, target_armature.name.replace("Rig", ""))

    class DynamicRigLayers(bpy.types.Panel):
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_label = f"Rig Layers: {char_name}"
        bl_order = 3
        bl_options = {'DEFAULT_CLOSED'}
        bl_idname = f"VIEW3D_PT_rig_layers_{r_id}"
        bl_category = 'Item'

        @classmethod
        def poll(cls, context):
            try:
                arm = resolve_settings_armature(context)
                return bool(arm and getattr(arm, "data", None) and arm.data.get("rig_id") == r_id)
            except Exception:
                return False

        def draw(self, context):
            arm = resolve_settings_armature(context)
            if not arm or not hasattr(arm, "data") or not hasattr(arm.data, "collections"):
                return
            layout = self.layout
            col = layout.column()
            colls = arm.data.collections
            for c in colls:
                if c.name in ["Other", "Others"]:
                    continue
                row = col.row(align=True)
                row.prop(c, "is_visible", toggle=True, text=c.name)
                row.prop(c, "is_solo", toggle=True, text="★")

    class DynamicRigUI(bpy.types.Panel):
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_label = f"Rig Properties: {char_name}"
        bl_order = 2
        bl_options = {'DEFAULT_CLOSED'}
        bl_idname = f"VIEW3D_PT_rig_ui_{r_id}"
        bl_category = 'Item'

        @classmethod
        def poll(cls, context):
            if context.mode != 'POSE':
                return False
            try:
                arm = resolve_settings_armature(context)
                return bool(arm and getattr(arm, "data", None) and arm.data.get("rig_id") == r_id)
            except Exception:
                return False

        def draw(self, context):
            arm = resolve_settings_armature(context)
            if not arm or not getattr(arm, "pose", None):
                return
            layout = self.layout
            box = layout.box()
            box.label(text=f"Rig: {char_name} (Pose Mode)", icon='ARMATURE_DATA')
            if "plate-settings" in arm.pose.bones:
                pb = arm.pose.bones["plate-settings"]
                for pk in ["Use Head Controller", "Use Neck Follow", "Use Eye Tracking"]:
                    if pk in pb:
                        box.prop(pb, f'["{pk}"]', slider=True)

    try:
        bpy.utils.register_class(DynamicRigLayers)
        bpy.utils.register_class(DynamicRigUI)
        _registered_rig_ids.add(r_id)
        print(f"[GACHA SETUP] Registered fallback Rig Layers & UI for '{char_name}' (rig_id: {r_id})")
    except Exception as e:
        print(f"[GACHA SETUP] Fallback Rig UI register notice: {e}")


def ensure_all_rig_uis_registered(target_armature=None):
    """Auto-registers Rig UI / Rig Layers panels for all rigs in the scene or .blend file."""
    import bpy
    if "RIG_LOG" in bpy.data.texts:
        try:
            bpy.data.texts.remove(bpy.data.texts["RIG_LOG"])
        except Exception:
            pass
    for t in list(bpy.data.texts):
        t_name = t.name.lower()
        if "_ui" in t_name or t_name == "rig_ui.py":
            try:
                content = t.as_string()
                if "rig_id = " not in content and "class RigLayers" not in content:
                    continue
                r_id = None
                if 'rig_id = "' in content:
                    r_id = content.split('rig_id = "')[1].split('"')[0]
                elif "rig_id = '" in content:
                    r_id = content.split("rig_id = '")[1].split("'")[0]

                if r_id and f"VIEW3D_PT_rig_layers_{r_id}" in dir(bpy.types):
                    _registered_rig_ids.add(r_id)
                    continue

                patched = patch_rig_ui_text_content(content)
                if patched != content:
                    t.from_string(patched)
                exec(compile(patched, t.name, 'exec'), {})
                if r_id:
                    _registered_rig_ids.add(r_id)
                print(f"[GACHA SETUP] Auto-registered Rig UI: '{t.name}' (rig_id: {r_id})")
            except Exception as e:
                print(f"[GACHA SETUP] Warning registering Rig UI from text '{t.name}': {e}")

    # Fallback for armatures whose UI text is missing in bpy.data.texts (e.g. appended collection)
    if target_armature and getattr(target_armature, "type", None) == 'ARMATURE':
        r_id = getattr(getattr(target_armature, "data", None), "get", lambda k: None)("rig_id")
        if r_id and f"VIEW3D_PT_rig_layers_{r_id}" not in dir(bpy.types):
            _register_fallback_rig_panels(target_armature, r_id)


def resolve_settings_armature(context):
    """Cached resolve: O(1) while active object / selection / object count are unchanged."""
    if context is None:
        return None
    try:
        act = getattr(context, "active_object", None) or getattr(context, "object", None)
        sel = getattr(context, "selected_objects", None) or ()
        key = (
            act.as_pointer() if act is not None else 0,
            tuple(o.as_pointer() for o in sel),
            _object_count(),
        )
    except Exception:
        return _resolve_settings_armature_uncached(context)
    if _ARM_CACHE["key"] == key:
        arm = _ARM_CACHE["arm"]
        if arm is None:
            return None
        try:
            arm.name  # raises ReferenceError if freed
            return arm
        except Exception:
            pass
    arm = _resolve_settings_armature_uncached(context)
    _ARM_CACHE["key"] = key
    _ARM_CACHE["arm"] = arm
    return arm


def _resolve_settings_armature_uncached(context):
    """Returns the armature targeted by selection (None if none). Falls back to active mesh or scene armature."""
    if context is None:
        return None
    try:
        obj = getattr(context, "active_object", None) or getattr(context, "object", None)
    except Exception:
        obj = None
    # An active scene light/camera must not borrow a character from selection
    # or from the scene-wide fallback (even when parented to a character rig).
    if obj is None or getattr(obj, 'type', None) in {'LIGHT', 'CAMERA'}:
        return None
    candidates = []
    if obj is not None:
        candidates.append(obj)
    try:
        candidates.extend(list(getattr(context, "selected_objects", []) or []))
    except Exception:
        pass
    target_arm = None
    for cand in candidates:
        if cand is None:
            continue
        if getattr(cand, "type", None) == 'ARMATURE':
            target_arm = cand
            break
        try:
            arm = cand.find_armature()
            if arm is not None:
                target_arm = arm
                break
        except Exception:
            pass
        for mod in getattr(cand, "modifiers", []) or []:
            try:
                if mod.type == 'ARMATURE' and getattr(mod, "object", None) is not None:
                    target_arm = mod.object
                    break
            except Exception:
                continue
        if target_arm is not None:
            break
        parent = getattr(cand, "parent", None)
        if parent is not None and getattr(parent, "type", None) == 'ARMATURE':
            target_arm = parent
            break

    # If no armature found directly from selection, check if selected object is a character mesh
    # and find any character armature in the scene / active collection
    if target_arm is None:
        import bpy
        for cand in candidates:
            if getattr(cand, "type", None) == 'MESH':
                scn_objs = getattr(getattr(context, "scene", None) or getattr(bpy.context, "scene", None), "objects", bpy.data.objects)
                for o in scn_objs:
                    if o.type == 'ARMATURE' and not any(ign in o.name.lower() for ign in ["eyerig", "facerig", "lighting", "metarig", "wgt"]):
                        target_arm = o
                        break
                if target_arm is None:
                    # Mesh-only model without armature: return the mesh object as the settings target
                    if cand.get(GACHA_GAME_KEY) or any(slot.material for slot in getattr(cand, "material_slots", [])):
                        target_arm = cand
                break
        if target_arm is None:
            scn_objs = getattr(getattr(context, "scene", None) or getattr(bpy.context, "scene", None), "objects", bpy.data.objects)
            for o in scn_objs:
                if o.type == 'ARMATURE' and not any(ign in o.name.lower() for ign in ["eyerig", "facerig", "lighting", "metarig", "wgt"]):
                    target_arm = o
                    break

    return target_arm


_MISSING = object()
_MESH_CACHE = {}
_GAME_CACHE = {}
_ARM_CACHE = {"key": None, "arm": None}


def _object_count():
    import bpy
    return len(bpy.data.objects)


def invalidate_caches():
    """Drops all cached lookups (call after structural changes: parenting, modifiers, tags)."""
    _MESH_CACHE.clear()
    _GAME_CACHE.clear()
    _ARM_CACHE["key"] = None
    _ARM_CACHE["arm"] = None


def _iter_rig_meshes(arm):
    """Cached list of meshes belonging to arm. Full scan only on cache miss."""
    if arm is None:
        return iter(())
    try:
        key = arm.as_pointer()
        count = _object_count()
    except Exception:
        return _iter_rig_meshes_uncached(arm)
    entry = _MESH_CACHE.get(key)
    if entry is not None and entry[0] == count:
        try:
            for m in entry[1]:
                m.name  # raises ReferenceError if freed
            return iter(entry[1])
        except Exception:
            pass
    meshes = list(_iter_rig_meshes_uncached(arm))
    _MESH_CACHE[key] = (count, meshes)
    return iter(meshes)


def _iter_rig_meshes_uncached(arm):
    seen = set()
    if arm is None:
        return
    if getattr(arm, "type", None) == 'MESH':
        if arm.name not in seen:
            seen.add(arm.name)
            yield arm
        return

    try:
        for child in getattr(arm, "children_recursive", []) or []:
            if getattr(child, "type", None) == 'MESH' and child.name not in seen:
                seen.add(child.name)
                yield child
    except Exception:
        pass

    import bpy
    for obj in bpy.data.objects:
        if getattr(obj, "type", None) != 'MESH' or obj.name in seen:
            continue
        p = getattr(obj, "parent", None)
        while p:
            if p == arm:
                seen.add(obj.name)
                yield obj
                break
            p = getattr(p, "parent", None)
        if obj.name in seen:
            continue
        try:
            for mod in getattr(obj, "modifiers", []) or []:
                if mod.type == 'ARMATURE' and getattr(mod, "object", None) == arm:
                    seen.add(obj.name)
                    yield obj
                    break
        except Exception:
            continue


def get_character_materials(context=None, arm=None):
    """Returns (arm, [materials]) scoped strictly to the selected character armature."""
    if arm is None:
        arm = resolve_settings_armature(context)
    if arm is None:
        return None, []
    import bpy
    from setup_wizard.utils.modifier_utils import get_modifier_property
    mats = []
    seen = set()
    visited_groups = set()

    def geometry_materials(tree):
        if tree in visited_groups:
            return
        visited_groups.add(tree)
        for node in tree.nodes:
            for socket in node.inputs:
                value = getattr(socket, 'default_value', None)
                if not socket.is_linked and isinstance(value, bpy.types.Material):
                    yield value
            if node.type == 'GROUP' and node.node_tree:
                yield from geometry_materials(node.node_tree)

    for mesh in _iter_rig_meshes(arm):
        mesh_materials = [slot.material for slot in mesh.material_slots if slot.material]
        for modifier in mesh.modifiers:
            if modifier.type != 'NODES' or not modifier.node_group:
                continue
            tree = modifier.node_group
            for item in tree.interface.items_tree:
                if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.socket_type == 'NodeSocketMaterial':
                    value = get_modifier_property(modifier, item.identifier)
                    if isinstance(value, bpy.types.Material):
                        mesh_materials.append(value)
            mesh_materials.extend(geometry_materials(tree))
        for mat in mesh_materials:
            if mat and mat.name not in seen:
                seen.add(mat.name)
                mats.append(mat)
            if mat and mat.name.endswith("_Low"):
                orig_name = mat.name[:-4]
                orig_mat = bpy.data.materials.get(orig_name)
                if orig_mat and orig_mat.name not in seen:
                    seen.add(orig_mat.name)
                    mats.append(orig_mat)
    return arm, mats


def detect_armature_game(arm):
    """Cached wrapper around the heuristic detection (invalidated by invalidate_caches())."""
    if arm is None:
        return None
    try:
        key = (arm.as_pointer(), _object_count())
    except Exception:
        return _detect_armature_game_uncached(arm)
    hit = _GAME_CACHE.get(key, _MISSING)
    if hit is not _MISSING:
        return hit
    result = _detect_armature_game_uncached(arm)
    _GAME_CACHE[key] = result
    return result


def _detect_armature_game_uncached(arm):
    """Detects GameType.name for an armature: stamped tag first, then per-rig heuristics."""
    if arm is None:
        return None
    # 1. Stamped tag (set at rig/setup time, survives Append)
    try:
        g = arm.get(GACHA_GAME_KEY)
        if g:
            return str(g)
    except Exception:
        pass
    try:
        g = getattr(arm, "data", {}).get(GACHA_GAME_KEY) if hasattr(getattr(arm, "data", None), "get") else None
        if g:
            return str(g)
    except Exception:
        pass
    # 2. Bone signatures (WuWa / AKE empties are parented, not bones, so check objects too)
    try:
        bones = getattr(getattr(arm, "data", None), "bones", []) or []
        bone_names = set(bones.keys()) if hasattr(bones, "keys") else {b.name for b in bones}
        if "EyeTracker" in bone_names or arm.get("ww_model_prefix") is not None:
            return "WUTHERING_WAVES"
    except Exception:
        pass
    # 3. Modifiers on meshes linked to this armature
    try:
        for mesh in _iter_rig_meshes(arm):
            for mod in getattr(mesh, "modifiers", []):
                if mod.type == 'NODES' and mod.node_group:
                    ng_name = mod.node_group.name.lower()
                    if "ww - outlines" in ng_name or "resonatorstar" in ng_name:
                        return "WUTHERING_WAVES"
                    if "zzz outlines" in ng_name or "extra fx" in ng_name:
                        return "ZENLESS_ZONE_ZERO"
                    if "impacttoon" in ng_name or "betterhi3rd" in ng_name:
                        return "HONKAI_IMPACT_3RD"
                    if "nexus" in ng_name or "anima" in ng_name:
                        return "HONKAI_NEXUS_ANIMA"
                    if "stellartoon" in ng_name or "nya222" in ng_name:
                        return "HONKAI_STAR_RAIL"
                    if "bonny festivity" in ng_name or "primotoon" in ng_name:
                        return "GENSHIN_IMPACT"
    except Exception:
        pass
    # 4. Per-rig materials (scoped to this rig, never global bpy.data.materials)
    try:
        mat_names = []
        for mesh in _iter_rig_meshes(arm):
            for slot in getattr(mesh, "material_slots", []) or []:
                mat = getattr(slot, "material", None)
                if mat is not None:
                    mat_names.append(mat.name.lower())
        blob = " ".join(mat_names)
        if blob:
            if any(k in blob for k in ["impacttoon", "hi3", "honkai 3rd", "honkai3rd", "betterhi3rd"]):
                return "HONKAI_IMPACT_3RD"
            if any(k in blob for k in ["nexus_anima", "nexus anima", "hna"]):
                return "HONKAI_NEXUS_ANIMA"
            if any(k in blob for k in ["stellartoon", "hsr", "star rail", "star_rail", "nya222"]):
                return "HONKAI_STAR_RAIL"
            if any(k in blob for k in ["kythera", "zzz ", " zzz", "zenless"]) or blob.strip() == "zzz":
                return "ZENLESS_ZONE_ZERO"
            if any(k in blob for k in ["pbrtoon", "endfield", "arknights", "ake"]):
                return "ARKNIGHTS_ENDFIELD"
            if any(k in blob for k in ["wuwa", "wuthering", "gustling"]):
                return "WUTHERING_WAVES"
            if any(k in blob for k in ["nte", "neverness"]):
                return "NEVERNESS_TO_EVERNESS"
            if any(k in blob for k in ["pgr", "punishing", "jarednyts"]):
                return "PUNISHING_GRAY_RAVEN"
            if any(k in blob for k in ["genshin", "festivity", "primotoon", "hoyoverse", "mihoyo"]):
                return "GENSHIN_IMPACT"
    except Exception:
        pass
    return None


def resolve_character_name(arm, fallback=None):
    """Single canonical character name for WGTS_<Char> (Append-safe).

    Prefers the stamped gacha_character tag, else the shared
    extract_clean_character_name() so rig scripts and face rigs always
    produce the SAME collection name (no WGTS_Skeleton + WGTS_SkeletonRig dupes).
    """
    if arm is not None:
        try:
            tag = arm.get(GACHA_CHAR_KEY)
            if tag:
                return str(tag)
        except Exception:
            pass
        try:
            from setup_wizard.character_rig_setup.rig_ui_utils import extract_clean_character_name
            clean = extract_clean_character_name(getattr(arm, "name", "") or "")
            if clean and clean.lower() not in ("character", "armature", "rig", "root"):
                return clean
        except Exception:
            pass
        try:
            return str(arm.name).replace("Rig", "")
        except Exception:
            pass
    return fallback


def is_game_armature(context, game_name):
    """True only if the selected armature belongs to game_name. False otherwise (incl. no selection)."""
    arm = resolve_settings_armature(context)
    if arm is None:
        return False
    detected = detect_armature_game(arm)
    if detected is not None:
        return detected == str(game_name)
    return False


_LAST_SETTINGS_ARM = None


def has_active_character_changed(context):
    """Returns True if the active character changed since last check, updating the cache."""
    global _LAST_SETTINGS_ARM
    current_arm = resolve_settings_armature(context)
    if current_arm is None:
        return False
    if current_arm != _LAST_SETTINGS_ARM:
        _LAST_SETTINGS_ARM = current_arm
        _MESH_CACHE.clear()
        _GAME_CACHE.clear()
        return True
    return False


def reset_last_settings_arm():
    """Forces the next check to report a change."""
    global _LAST_SETTINGS_ARM
    _LAST_SETTINGS_ARM = None
    invalidate_caches()


def ensure_character_node_trees_isolated(arm, mats, force=False):
    """Share one compatible properties tree per character, including outlines.

    Append and earlier isolation runs can leave .001/.002 copies in different
    materials. Consolidate those copies before isolating from other characters.
    Distinct shader families/interfaces keep their own independent controls.
    """
    if not arm or not mats or not getattr(arm, 'name', ''):
        return
    import bpy
    import re
    from collections import defaultdict, Counter

    families = defaultdict(list)
    for mat in set(mats):
        if not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            tree = getattr(node, 'node_tree', None)
            if node.type != 'GROUP' or tree is None:
                continue
            if not any(k in tree.name.lower() for k in ('global', 'properties')) and '_owner_armature' not in tree:
                continue
            family = re.sub(r'\.\d{3}$', '', tree.name).lower()
            interface = tuple((s.name, s.in_out, s.socket_type) for s in tree.interface.items_tree if s.item_type == 'SOCKET')
            families[(family, interface)].append((node, tree, mat))

    # A genuinely shared tree must stay independent in the other character.
    other_trees = None
    def external_trees():
        nonlocal other_trees
        if other_trees is None:
            other_trees = set()
            for other in bpy.data.objects:
                if other.type != 'ARMATURE' or other == arm:
                    continue
                _, materials = get_character_materials(arm=other)
                for mat in materials:
                    if mat.node_tree:
                        other_trees.update(n.node_tree for n in mat.node_tree.nodes if n.type == 'GROUP' and n.node_tree)
        return other_trees

    retired = set()
    canonical_trees = set()
    for references in families.values():
        trees = {tree for _, tree, _ in references}
        main_counts = Counter(tree for _, tree, mat in references if 'outline' not in mat.name.lower())
        counts = Counter(tree for _, tree, _ in references)
        canonical = max(trees, key=lambda t: (t.get('_owner_armature') == arm.name, main_counts[t], counts[t], -len(t.name)))
        real_users = canonical.users - int(canonical.use_fake_user)
        if ((real_users > counts[canonical] or canonical.get('_owner_armature') != arm.name or force)
                and canonical in external_trees()):
            canonical = canonical.copy()
        canonical['_owner_armature'] = arm.name
        canonical_trees.add(canonical)
        for node, tree, _ in references:
            if tree == canonical:
                continue
            # Match sockets by name, even when Append assigned different IDs.
            host = node.id_data
            incoming = [(s.name, l.from_socket) for s in node.inputs for l in list(s.links)]
            outgoing = [(s.name, l.to_socket) for s in node.outputs for l in list(s.links)]
            defaults = {s.name: tuple(s.default_value) if hasattr(s.default_value, '__len__') and not isinstance(s.default_value, str) else s.default_value
                        for s in node.inputs if hasattr(s, 'default_value')}
            node.node_tree = canonical
            for socket in [*node.inputs, *node.outputs]:
                for link in list(socket.links):
                    host.links.remove(link)
            for name, value in defaults.items():
                if name in node.inputs:
                    node.inputs[name].default_value = value
            for name, source in incoming:
                if name in node.inputs:
                    host.links.new(source, node.inputs[name])
            for name, destination in outgoing:
                if name in node.outputs:
                    host.links.new(node.outputs[name], destination)
            retired.add(tree)
    for tree in retired:
        if tree.users <= int(tree.use_fake_user):
            tree.use_fake_user = False
            if tree.users == 0:
                bpy.data.node_groups.remove(tree)
    for tree in canonical_trees:
        base = re.sub(r'\.\d{3}$', '', tree.name)
        if base not in bpy.data.node_groups:
            tree.name = base
