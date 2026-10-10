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

    if target_arm is not None:
        try:
            r_id = getattr(getattr(target_arm, "data", None), "get", lambda k: None)("rig_id")
            if r_id and r_id not in _registered_rig_ids:
                _registered_rig_ids.add(r_id)
                ensure_all_rig_uis_registered(target_arm)
        except Exception:
            pass

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
    mats = []
    seen = set()
    for mesh in _iter_rig_meshes(arm):
        for slot in getattr(mesh, "material_slots", []) or []:
            mat = getattr(slot, "material", None)
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
    """
    Ensures that character-setting node groups (such as 'Global Material Properties')
    in mats are uniquely owned by this character.
    Fast path: skips immediately if all relevant groups are already owned by this character.
    """
    if not arm or not mats:
        return
    arm_name = getattr(arm, "name", "")
    if not arm_name:
        return

    # 1. Collect only relevant property node groups (e.g. "Global Material Properties")
    relevant_nodes = []
    needs_isolation = False

    for m in mats:
        if not getattr(m, "node_tree", None):
            continue
        for n in m.node_tree.nodes:
            if n.type == 'GROUP' and n.node_tree:
                t = n.node_tree
                t_name = t.name.lower()
                if "global" in t_name or "properties" in t_name or "_owner_armature" in t:
                    relevant_nodes.append((n, t))
                    if t.get("_owner_armature") != arm_name:
                        needs_isolation = True

    if not needs_isolation and not force:
        return

    import bpy

    # 2. Trees used by other armatures: computed lazily (only needed for un-owned trees)
    other_trees_cache = []

    def _get_other_trees():
        if other_trees_cache:
            return other_trees_cache[0]
        other_trees = set()
        for o_arm in bpy.data.objects:
            if o_arm.type != 'ARMATURE' or o_arm == arm:
                continue
            for mesh in _iter_rig_meshes(o_arm):
                for slot in getattr(mesh, "material_slots", []) or []:
                    m = getattr(slot, "material", None)
                    if m and getattr(m, "node_tree", None):
                        for n in m.node_tree.nodes:
                            if n.type == 'GROUP' and n.node_tree:
                                other_trees.add(n.node_tree)
        other_trees_cache.append(other_trees)
        return other_trees

    # 3. Remap trees ensuring all materials of this armature share the same isolated tree
    remapped_trees = {}

    for n, t in relevant_nodes:
        if t in remapped_trees:
            n.node_tree = remapped_trees[t]
            continue
        owner = t.get("_owner_armature")
        if owner == arm_name:
            remapped_trees[t] = t
            continue
        if owner is not None or t in _get_other_trees():
            target_tree = t.copy()
            target_tree["_owner_armature"] = arm_name
            remapped_trees[t] = target_tree
            n.node_tree = target_tree
        else:
            t["_owner_armature"] = arm_name
            remapped_trees[t] = t



