"""Native Blender grouping and linked-component helpers."""
from mathutils import Vector


def group_objects(context, objects, name="ShapeFlow Group"):
    objects = tuple(obj for obj in objects if obj is not None)
    if not objects:
        raise ValueError("Select at least one object to group")
    empty = __import__('bpy').data.objects.new(name, None)
    empty.empty_display_type = 'PLAIN_AXES'
    context.collection.objects.link(empty)
    center = sum((obj.matrix_world.translation for obj in objects), Vector()) / len(objects)
    empty.location = center
    for obj in objects:
        world = obj.matrix_world.copy()
        obj.parent = empty
        obj.matrix_world = world
        obj.select_set(False)
    empty.select_set(True)
    context.view_layer.objects.active = empty
    return empty


def create_linked_instance(context, source, location=None):
    if source is None or source.data is None:
        raise ValueError("Select an object with linkable data")
    instance = source.copy()
    instance.data = source.data
    collection = source.users_collection[0] if source.users_collection else context.collection
    collection.objects.link(instance)
    if location is not None:
        instance.location = Vector(location)
    for selected in context.selected_objects:
        selected.select_set(False)
    instance.select_set(True)
    context.view_layer.objects.active = instance
    return instance


def make_instance_unique(obj):
    if obj is None or obj.data is None:
        raise ValueError("Select an object with data to make unique")
    obj.data = obj.data.copy()
    return obj
