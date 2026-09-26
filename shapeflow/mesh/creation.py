import bpy
from mathutils import Vector


EPSILON = 1.0e-6


def create_profile_object(context, corners, name="ShapeFlow Profile"):
    """Create a normal Blender Mesh object containing one polygon face."""
    if len(corners) < 3:
        raise ValueError("A profile needs at least three corners")
    if min((Vector(corners[(i + 1) % 4]) - Vector(corners[i])).length for i in range(4)) < EPSILON:
        raise ValueError("Rectangle sides are too small")
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(corners, [], [(0, 1, 2, 3)])
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    context.collection.objects.link(obj)
    for selected in context.selected_objects:
        selected.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj
    return obj


def create_rectangle_object(context, corners, name="ShapeFlow Rectangle"):
    if len(corners) != 4:
        raise ValueError("A rectangle needs exactly four corners")
    return create_profile_object(context, corners, name)
