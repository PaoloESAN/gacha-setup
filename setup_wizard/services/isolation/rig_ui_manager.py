import ast
import os
import re
import traceback
import bpy


def _rig_ui_string(node, rig_id):
    """Resolves generated class IDs without executing the script."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id == "rig_id":
        return rig_id
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _rig_ui_string(node.left, rig_id) + _rig_ui_string(node.right, rig_id)
    if isinstance(node, ast.IfExp) and isinstance(node.test, ast.Name) and node.test.id == "rig_id":
        return _rig_ui_string(node.body if rig_id else node.orelse, rig_id)
    raise ValueError("Unsupported rig UI class identifier")


def _rig_ui_manifest(source, rig_id):
    """Retrieves only classes explicitly registered by the rig's UI script."""
    tree = ast.parse(source)
    script_id = None
    classes = {}
    register = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "rig_id" for t in node.targets):
                script_id = ast.literal_eval(node.value)
        elif isinstance(node, ast.ClassDef):
            for statement in node.body:
                if isinstance(statement, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "bl_idname" for t in statement.targets
                ):
                    classes[node.name] = _rig_ui_string(statement.value, rig_id)
        elif isinstance(node, ast.FunctionDef) and node.name == "register":
            register = node

    if script_id != rig_id:
        raise ValueError(f"Rig UI Text ({script_id}) does not match rig_id ({rig_id})")
    if register is None:
        raise ValueError("Rig UI Text has no register() function")

    expected = []
    for node in ast.walk(register):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        owner = node.func.value
        if not (
            node.func.attr == "register_class"
            and isinstance(owner, ast.Attribute)
            and owner.attr == "utils"
            and isinstance(owner.value, ast.Name)
            and owner.value.id == "bpy"
        ):
            continue
        if not node.args or not isinstance(node.args[0], ast.Name):
            raise ValueError("Unsupported rig UI registration call")
        name = node.args[0].id
        if name not in classes:
            raise ValueError(f"Cannot verify rig UI class: {name}")
        class_id = classes[name]
        if not class_id.endswith("_" + rig_id):
            raise ValueError(f"Rig UI class does not belong to this rig: {class_id}")
        expected.append(class_id)

    return expected


def _registered_ui_class(class_id):
    if "." in class_id:
        module, name = class_id.split(".", 1)
        rna_name = module.upper() + "_OT_" + name
        return bpy.types.Operator.bl_rna_get_subclass_py(rna_name, None)
    return bpy.types.Panel.bl_rna_get_subclass_py(class_id, None)


def _find_rig_ui_text(rig, rig_id):
    text = rig.get("rig_ui")
    if isinstance(text, bpy.types.Text):
        return text
    marker = re.compile(
        r"^rig_id\s*=\s*(['\"])" + re.escape(rig_id) + r"\1\s*$", re.MULTILINE
    )
    for text in bpy.data.texts:
        try:
            if marker.search(text.as_string()):
                return text
        except Exception:
            continue
    return None


def initialize_rig_uis(objects):
    """
    Execute ONLY from an operator or timer context (with write permissions).
    Registers Rigify UI for imported armatures, preventing the polling loop
    and viewport freeze.
    """
    stats = {"rig_ui_ready": 0, "rig_ui_initialized": 0, "rig_ui_errors": []}
    seen = set()

    for rig in objects:
        if rig.type != "ARMATURE":
            continue
        rig_id = getattr(rig.data, "get", lambda k: None)("rig_id") or rig.get("rig_id")
        if not rig_id or rig_id in seen:
            continue
        seen.add(rig_id)

        try:
            text = _find_rig_ui_text(rig, rig_id)
            if not text:
                continue

            source = text.as_string()
            try:
                expected = _rig_ui_manifest(source, rig_id)
            except Exception:
                expected = []

            # If all expected classes are already registered, avoid re-executing
            if expected and all(_registered_ui_class(name) is not None for name in expected):
                stats["rig_ui_ready"] += 1
                continue

            code = compile(source, text.name, "exec")
            previous_classes = [(name, _registered_ui_class(name)) for name in expected]
            registration_started = True

            # Unregister partial/fallback registrations for this rig_id before re-running
            if expected:
                for name in reversed(expected):
                    cls = _registered_ui_class(name)
                    if cls is not None:
                        try:
                            bpy.utils.unregister_class(cls)
                        except Exception:
                            pass

            exec(code, {"__name__": "__main__"})
            missing = [name for name in expected if _registered_ui_class(name) is None]
            if missing:
                raise RuntimeError("Rig UI registration incomplete: " + ", ".join(missing))

            stats["rig_ui_ready"] += 1
            stats["rig_ui_initialized"] += 1
            print(f"[GACHA SETUP] Rig UI ready: {rig.name} (rig_id: {rig_id})")
        except Exception as exc:
            if registration_started:
                for name, previous in reversed(previous_classes):
                    current = _registered_ui_class(name)
                    if current is not None and current is not previous:
                        try:
                            bpy.utils.unregister_class(current)
                        except Exception:
                            pass
                    if previous is not None and _registered_ui_class(name) is None:
                        try:
                            bpy.utils.register_class(previous)
                        except Exception:
                            pass
            message = f"{rig.name}: {exc}"
            stats["rig_ui_errors"].append(message)
            print(f"[GACHA SETUP] Error initializing Rig UI: {message}")
            traceback.print_exc()

    return stats
