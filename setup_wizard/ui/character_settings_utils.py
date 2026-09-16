# Central helper: per-armature game tag for Character Settings panels.
# Stores GameType.name on the rig object so Append keeps the info and
# each panel only shows for its own game + selected character.

GACHA_GAME_KEY = "gacha_game"
GACHA_CHAR_KEY = "gacha_character"


def stamp_rig_game(rig_obj, game_name, char_name=None):
    """Tags a rig armature so its Character Settings panel can be resolved after Append."""
    if rig_obj is None:
        return
    try:
        rig_obj[GACHA_GAME_KEY] = str(game_name)
    except Exception:
        pass
    if char_name:
        try:
            rig_obj[GACHA_CHAR_KEY] = str(char_name)
        except Exception:
            pass
    # Also tag armature data (survives some Append/Link paths)
    try:
        data = getattr(rig_obj, "data", None)
        if data is not None:
            data[GACHA_GAME_KEY] = str(game_name)
    except Exception:
        pass


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
    """Returns the armature targeted by selection (None if none). Never falls back to scene."""
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

    if target_arm is not None:
        try:
            r_id = getattr(getattr(target_arm, "data", None), "get", lambda k: None)("rig_id")
            if r_id and (r_id not in _registered_rig_ids or f"VIEW3D_PT_rig_layers_{r_id}" not in dir(bpy.types)):
                ensure_all_rig_uis_registered(target_arm)
        except Exception:
            pass

    return target_arm


# Meshes that never belong to a character (widgets, helpers, light rigs).
_HELPER_MESH_PREFIXES = (
    "WGT-", "Highlight", "Eye Highlight", "Eye_Highlight", "Sun",
    "Head Origin", "Head Forward", "Head Up", "Light Direction",
)


def _is_helper_mesh(obj):
    try:
        name = getattr(obj, "name", "") or ""
    except Exception:
        return True
    for prefix in _HELPER_MESH_PREFIXES:
        if name.startswith(prefix):
            return True
    try:
        for coll in getattr(obj, "users_collection", []) or []:
            cname = getattr(coll, "name", "") or ""
            if cname.startswith("WGTS") or cname.lower() == "wgt":
                return True
    except Exception:
        pass
    return False


def _iter_rig_meshes(arm):
    """Yields every MESH bound to `arm` (children, parent chain or Armature modifier).

    Meshes rigged with Rigify / imported from uemodel are usually NOT
    object-children of the rig: they just carry an Armature modifier (or sit
    next to it in the character collection). All three bindings are scanned
    so selecting the armature always resolves its character materials
    (multi-character / Append safe). Helper meshes (widgets, highlights,
    light rigs) are skipped.
    """
    if arm is None:
        return
    seen = set()

    def _emit(obj):
        if obj is None or id(obj) in seen:
            return None
        if getattr(obj, "type", None) != 'MESH':
            return None
        if _is_helper_mesh(obj):
            return None
        seen.add(id(obj))
        return obj

    # 1. Object children (recursive).
    try:
        for child in getattr(arm, "children_recursive", []) or []:
            mesh = _emit(child)
            if mesh is not None:
                yield mesh
    except Exception:
        pass

    # 2. Parent-chain walk + Armature-modifier scan over all objects.
    # (Runs always, not just on error: modifier-bound meshes are the norm.)
    try:
        import bpy
        all_objs = list(getattr(bpy.data, "objects", []) or [])
    except Exception:
        return
    for obj in all_objs:
        if obj is None or id(obj) in seen:
            continue
        if getattr(obj, "type", None) != 'MESH':
            continue
        bound = False
        try:
            p = getattr(obj, "parent", None)
            while p is not None:
                if p == arm:
                    bound = True
                    break
                p = getattr(p, "parent", None)
        except Exception:
            pass
        if not bound:
            try:
                for mod in getattr(obj, "modifiers", []) or []:
                    try:
                        if mod.type == 'ARMATURE' and getattr(mod, "object", None) == arm:
                            bound = True
                            break
                    except Exception:
                        continue
            except Exception:
                pass
        if bound:
            mesh = _emit(obj)
            if mesh is not None:
                yield mesh


def get_character_materials(context=None, arm=None):
    """Returns (arm, [materials]) scoped strictly to the selected character armature."""
    if arm is None:
        arm = resolve_settings_armature(context)
    if arm is None:
        return None, []
    mats = []
    seen = set()
    for mesh in _iter_rig_meshes(arm):
        for slot in getattr(mesh, "material_slots", []) or []:
            mat = getattr(slot, "material", None)
            if mat and mat.name not in seen:
                seen.add(mat.name)
                mats.append(mat)
    return arm, mats


def detect_armature_game(arm):
    """Detects GameType.name for an armature: stamped tag first, then per-rig heuristics."""
    if arm is None:
        return None
    # 1. Stamped tag (set at rig time, survives Append)
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
    # 3. Per-rig materials (scoped to this rig, never global bpy.data.materials)
    try:
        mat_names = []
        for mesh in _iter_rig_meshes(arm):
            for slot in getattr(mesh, "material_slots", []) or []:
                mat = getattr(slot, "material", None)
                if mat is not None:
                    mat_names.append(mat.name.lower())
        blob = " ".join(mat_names)
        if not blob:
            return None
        if "stellartoon" in blob or "hsr" in blob:
            return "HONKAI_STAR_RAIL"
        if "hoyoverse - genshin" in blob or "hoyoverse - gi" in blob or "genshin" in blob:
            return "GENSHIN_IMPACT"
        if "kythera" in blob or blob.strip().startswith("zzz ") or " zzz " in f" {blob} ":
            return "ZENLESS_ZONE_ZERO"
        if "pbrtoon" in blob or "endfield" in blob or "arknights" in blob:
            return "ARKNIGHTS_ENDFIELD"
        if "wuwa" in blob or "wuthering" in blob or "gustling" in blob \
                or "ww -" in blob or "ww_" in blob:
            # "WW - ..." are WuWa's own per-character materials
            # (e.g. "WW - MainV2 Camellya", "WW - Face", "WW - Outlines").
            return "WUTHERING_WAVES"
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
        return True
    return False


def reset_last_settings_arm():
    """Forces the next check to report a change."""
    global _LAST_SETTINGS_ARM
    _LAST_SETTINGS_ARM = None


def ensure_character_node_trees_isolated(arm, mats):
    """
    Ensures that shader node groups reachable from mats are uniquely owned
    by this character (Append / multi-character safe).

    Walks the whole GROUP-node chain (materials AND nested node groups):
    a tree owned by another armature is duplicated so per-character panel
    updates (e.g. the light selector) never leak into other characters.
    """
    if not arm or not mats:
        return
    arm_name = getattr(arm, "name", "")
    if not arm_name:
        return

    remapped = {}

    def _own(tree):
        owner = tree.get("_owner_armature")
        if owner is None:
            tree["_owner_armature"] = arm_name
            return tree
        if owner != arm_name:
            new_tree = tree.copy()
            new_tree["_owner_armature"] = arm_name
            return new_tree
        return tree

    def _isolate_container(container, seen):
        if container is None or id(container) in seen:
            return
        seen.add(id(container))
        try:
            nodes = list(getattr(container, "nodes", []) or [])
        except Exception:
            return
        for node in nodes:
            try:
                if getattr(node, "type", None) != 'GROUP':
                    continue
                tree = getattr(node, "node_tree", None)
                if tree is None:
                    continue
                if id(tree) in remapped:
                    tree = remapped[id(tree)]
                    try:
                        node.node_tree = tree
                    except Exception:
                        pass
                else:
                    new_tree = _own(tree)
                    if new_tree is not tree:
                        remapped[id(tree)] = new_tree
                        try:
                            node.node_tree = new_tree
                        except Exception:
                            pass
                        tree = new_tree
                _isolate_container(tree, seen)
            except Exception:
                continue

    seen = set()
    for m in mats:
        try:
            tree = getattr(m, "node_tree", None)
        except Exception:
            tree = None
        if tree is not None:
            _isolate_container(tree, seen)


# ---------------------------------------------------------------------------
# Shared shader-node helpers (per-character panel updates).
# Used by every game's Character Settings (WuWa, HSR, GI, ZZZ, ...) so the
# light selector and options resolve the SELECTED character's nodes even when
# they live nested inside group trees, and write tree-level defaults scoped
# to that character's isolated trees instead of the global definitions.
# ---------------------------------------------------------------------------

def _iter_character_group_nodes(mats, *keywords):
    """Yields GROUP nodes (from the given materials) whose tree name matches.

    Direct (material-level) nodes first, then nodes nested inside the
    materials' group trees (e.g. inside "WW - Main"). This keeps the
    Character Settings working per character after Append / with several
    characters in the same file, mirroring how the other games resolve
    their nodes.
    """
    wanted = [k.lower() for k in keywords]
    seen_containers = set()
    direct = []
    nested = []
    queue = []
    for mat in mats or []:
        try:
            tree = getattr(mat, "node_tree", None)
        except Exception:
            tree = None
        if tree is not None and id(tree) not in seen_containers:
            seen_containers.add(id(tree))
            queue.append((tree, 0))
    while queue:
        container, depth = queue.pop(0)
        try:
            nodes = list(getattr(container, "nodes", []) or [])
        except Exception:
            continue
        for node in nodes:
            try:
                if getattr(node, "type", None) != 'GROUP':
                    continue
                subtree = getattr(node, "node_tree", None)
                if subtree is None:
                    continue
                tname = getattr(subtree, "name", "").lower()
                if any(k in tname for k in wanted):
                    (direct if depth == 0 else nested).append(node)
                if id(subtree) not in seen_containers:
                    seen_containers.add(id(subtree))
                    queue.append((subtree, depth + 1))
            except Exception:
                continue
    for node in direct:
        yield node
    for node in nested:
        yield node


def _iter_character_palette_nodes(mats):
    """Yields 'Color Palette' GROUP nodes reachable from the given materials."""
    return _iter_character_group_nodes(mats, "color palette")


def _character_group_trees(mats, *keywords):
    """Unique node-group trees (deduped) reachable from mats matching keywords.

    Used to write tree-level defaults (Group Input / Group Output sockets
    and interface defaults) scoped to one character's isolated trees,
    instead of the single global tree definition.
    """
    wanted = [k.lower() for k in keywords]
    seen = set()
    found = []
    queue = []
    for mat in mats or []:
        try:
            tree = getattr(mat, "node_tree", None)
        except Exception:
            tree = None
        if tree is not None and id(tree) not in seen:
            seen.add(id(tree))
            queue.append(tree)
    while queue:
        container = queue.pop(0)
        try:
            nodes = list(getattr(container, "nodes", []) or [])
        except Exception:
            continue
        for node in nodes:
            try:
                if getattr(node, "type", None) != 'GROUP':
                    continue
                subtree = getattr(node, "node_tree", None)
                if subtree is None or id(subtree) in seen:
                    continue
                seen.add(id(subtree))
                queue.append(subtree)
                if any(k in getattr(subtree, "name", "").lower() for k in wanted):
                    found.append(subtree)
            except Exception:
                continue
    return found


def _set_group_input_defaults(tree, pairs):
    """Writes defaults on GROUP_INPUT node outputs inside a node-group tree."""
    try:
        nodes = getattr(tree, "nodes", None)
    except Exception:
        return
    if not nodes:
        return
    try:
        node_list = list(nodes)
    except Exception:
        return
    for node in node_list:
        try:
            if getattr(node, "type", None) != 'GROUP_INPUT':
                continue
            outputs = getattr(node, "outputs", {})
            for socket_name, val in pairs:
                try:
                    if socket_name in outputs:
                        outputs[socket_name].default_value = val
                except Exception:
                    pass
        except Exception:
            continue


def _set_group_output_defaults(tree, node_names, pairs):
    """Writes defaults on a Group Output node's inputs inside a tree."""
    try:
        nodes = getattr(tree, "nodes", None)
    except Exception:
        return
    if not nodes:
        return
    out_node = None
    try:
        get_node = getattr(nodes, "get", None)
        if callable(get_node):
            for cand in node_names:
                out_node = get_node(cand)
                if out_node is not None:
                    break
    except Exception:
        out_node = None
    if out_node is None:
        return
    try:
        inputs = getattr(out_node, "inputs", {})
    except Exception:
        return
    for socket_name, val in pairs:
        try:
            if socket_name in inputs:
                inputs[socket_name].default_value = val
        except Exception:
            pass


def _set_interface_defaults(tree, pairs):
    """Writes interface socket defaults of a node-group tree."""
    try:
        interface = getattr(tree, "interface", None)
        items = getattr(interface, "items_tree", None)
    except Exception:
        return
    if not items:
        return
    try:
        item_list = list(items)
    except Exception:
        return
    wanted = {name: val for name, val in pairs}
    for item in item_list:
        try:
            if getattr(item, "name", None) in wanted:
                item.default_value = wanted[item.name]
        except Exception:
            pass


def _read_tree_output_default(tree, node_names, socket_name):
    """Reads a Group Output node's input default inside a tree (or None)."""
    try:
        nodes = getattr(tree, "nodes", None)
        get_node = getattr(nodes, "get", None)
        if not callable(get_node):
            return None
        for cand in node_names:
            try:
                out_node = get_node(cand)
            except Exception:
                continue
            if out_node is None:
                continue
            try:
                inputs = getattr(out_node, "inputs", {})
                if socket_name in inputs:
                    return inputs[socket_name].default_value
            except Exception:
                continue
    except Exception:
        pass
    return None


def _read_tree_group_input_default(tree, socket_name):
    """Reads a GROUP_INPUT node output default inside a tree (or None)."""
    try:
        node_list = list(getattr(tree, "nodes", []) or [])
    except Exception:
        return None
    for node in node_list:
        try:
            if getattr(node, "type", None) != 'GROUP_INPUT':
                continue
            outputs = getattr(node, "outputs", {})
            if socket_name in outputs:
                return outputs[socket_name].default_value
        except Exception:
            continue
    return None


def _read_tree_socket_default(tree, socket_name, _seen=None):
    """Reads a socket default from anywhere inside a tree (or None).

    Scans every node's inputs (descending into nested group trees with
    cycle protection) first, then the tree interface. Used by panel pull
    functions as a fallback when the GROUP node instance in the material
    does not expose the socket (e.g. a "StellarToon" wrapper shadows the
    inner "GlobalProperties" node).
    """
    if _seen is None:
        _seen = set()
    if tree is None or id(tree) in _seen:
        return None
    _seen.add(id(tree))
    try:
        node_list = list(getattr(tree, "nodes", []) or [])
    except Exception:
        node_list = []
    nested = []
    for node in node_list:
        try:
            inputs = getattr(node, "inputs", {})
            if socket_name in inputs:
                return inputs[socket_name].default_value
        except Exception:
            pass
        try:
            if getattr(node, "type", None) == 'GROUP':
                subtree = getattr(node, "node_tree", None)
                if subtree is not None and id(subtree) not in _seen:
                    nested.append(subtree)
        except Exception:
            pass
    for subtree in nested:
        try:
            val = _read_tree_socket_default(subtree, socket_name, _seen)
        except Exception:
            val = None
        if val is not None:
            return val
    try:
        interface = getattr(tree, "interface", None)
        items = getattr(interface, "items_tree", None) or []
        for item in list(items):
            try:
                if getattr(item, "name", None) == socket_name:
                    return item.default_value
            except Exception:
                continue
    except Exception:
        pass
    return None

