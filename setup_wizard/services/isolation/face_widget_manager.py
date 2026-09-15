import re
import bpy

_FACE_WIDGET_SUFFIX = re.compile(r"^(WGT-Face_.+?)\.(\d{3})$")


def face_widget_base_name(name):
    match = _FACE_WIDGET_SUFFIX.match(name or "")
    return match.group(1) if match else name


def capture_existing_face_widgets():
    """
    Captures canonical WGT-Face_* widgets present in current scene before
    appending character result, enabling clean reuse across characters.
    """
    result = {}
    for obj in bpy.data.objects:
        if not obj.name.startswith("WGT-Face_"):
            continue
        if _FACE_WIDGET_SUFFIX.match(obj.name):
            continue
        result[obj.name] = obj
    return result


def _custom_shape_is_used(target):
    for obj in bpy.data.objects:
        if obj.type != "ARMATURE" or not obj.pose:
            continue
        for bone in obj.pose.bones:
            if bone.custom_shape == target:
                return True
    return False


def _remove_orphan_object_data(data):
    if data is None or getattr(data, "users", 1) != 0:
        return
    for collection in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.grease_pencils,
    ):
        try:
            if data.name in collection:
                collection.remove(data)
                return
        except Exception:
            continue


def dedupe_shared_face_widgets(objects, canonical_widgets):
    """
    Remaps FaceRig custom bone shapes to existing canonical widgets in the main
    project, then safely removes unused duplicate widget objects.
    """
    if not canonical_widgets:
        return {"face_widget_bones_remapped": 0, "face_widget_objects_removed": 0}

    remapped = 0
    duplicates = set()

    for obj in objects:
        if obj.type != "ARMATURE" or not obj.pose:
            continue
        for bone in obj.pose.bones:
            shape = bone.custom_shape
            if shape is None or not shape.name.startswith("WGT-Face_"):
                continue

            base_name = face_widget_base_name(shape.name)
            canonical = canonical_widgets.get(base_name)
            if canonical is None or canonical == shape:
                continue

            bone.custom_shape = canonical
            duplicates.add(shape)
            remapped += 1

    if remapped:
        try:
            bpy.context.view_layer.update()
        except Exception:
            pass

    removed = 0
    for duplicate in duplicates:
        if _custom_shape_is_used(duplicate):
            continue
        try:
            references = bpy.data.user_map(subset={duplicate}).get(duplicate, set())
            if duplicate.use_fake_user or any(
                not isinstance(user, bpy.types.Collection) for user in references
            ):
                # Retain objects still referenced by constraints, parents or drivers
                continue
        except Exception:
            pass
        data = getattr(duplicate, "data", None)
        try:
            bpy.data.objects.remove(duplicate, do_unlink=True)
            removed += 1
        except Exception:
            continue
        _remove_orphan_object_data(data)

    return {
        "face_widget_bones_remapped": remapped,
        "face_widget_objects_removed": removed,
    }
