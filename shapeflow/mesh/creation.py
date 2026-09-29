import bpy
from mathutils import Vector


EPSILON = 1.0e-6


def create_profile_object(context, corners, name="ShapeFlow Profile"):
    """Create a normal Blender Mesh object containing one polygon face."""
    if len(corners) < 3:
        raise ValueError("A profile needs at least three corners")
    count = len(corners)
    if min((Vector(corners[(i + 1) % count]) - Vector(corners[i])).length for i in range(count)) < EPSILON:
        raise ValueError("Profile sides are too small")
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(corners, [], [tuple(range(count))])
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


def create_box_object(context, base_corners, depth, name="ShapeFlow Box"):
    """Create a closed native mesh box from four base corners and a depth vector."""
    if len(base_corners) != 4:
        raise ValueError("A box base needs exactly four corners")
    depth = Vector(depth)
    if depth.length < EPSILON:
        raise ValueError("Box depth is too small")
    base = [Vector(point) for point in base_corners]
    if min((base[(i + 1) % 4] - base[i]).length for i in range(4)) < EPSILON:
        raise ValueError("Box sides are too small")
    vertices = base + [point + depth for point in base]
    faces = (
        (0, 3, 2, 1), (4, 5, 6, 7),
        (0, 1, 5, 4), (1, 2, 6, 5),
        (2, 3, 7, 6), (3, 0, 4, 7),
    )
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    context.collection.objects.link(obj)
    for selected in context.selected_objects:
        selected.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj
    return obj


def create_polyline_object(context, points, name="ShapeFlow Curve"):
    if len(points) < 2:
        raise ValueError("A curve needs at least two points")
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [(index, index + 1) for index in range(len(points) - 1)], [])
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    context.collection.objects.link(obj)
    for selected in context.selected_objects:
        selected.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj
    return obj
