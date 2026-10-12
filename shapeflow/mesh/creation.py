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


def create_poly_curve_object(context, points, name="ShapeFlow Polyline", cyclic=False):
    """Create an editable native Blender Curve with one POLY spline."""
    if len(points) < 2:
        raise ValueError("A polyline needs at least two points")
    coordinates = [Vector(point) for point in points]
    if any(
        (second - first).length < EPSILON
        for first, second in zip(coordinates, coordinates[1:])
    ):
        raise ValueError("Polyline segments are too small")
    curve = bpy.data.curves.new(name, type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 1
    spline = curve.splines.new(type='POLY')
    spline.points.add(len(coordinates) - 1)
    for control_point, coordinate in zip(spline.points, coordinates):
        control_point.co = (*coordinate, 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    context.collection.objects.link(obj)
    for selected in context.selected_objects:
        selected.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj
    return obj


def create_guide_curve(context, start, end, name="ShapeFlow Guide"):
    """Create a native non-rendering Curve that remains editable as a guide."""
    start, end = Vector(start), Vector(end)
    if (end - start).length < EPSILON:
        raise ValueError("A guide needs two different points")
    obj = create_poly_curve_object(context, (start, end), name)
    obj.hide_render = True
    obj.show_in_front = True
    obj.color = (0.15, 0.8, 1.0, 1.0)
    obj["shapeflow_guide"] = True
    obj["shapeflow_length"] = (end - start).length
    return obj


def create_nurbs_curve_object(context, points, name="ShapeFlow B-Spline", order=4):
    """Create an editable native Blender NURBS spline."""
    coordinates = [Vector(point) for point in points]
    if len(coordinates) < 3:
        raise ValueError("A B-Spline needs at least three points")
    curve = bpy.data.curves.new(name, type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 12
    spline = curve.splines.new(type='NURBS')
    spline.points.add(len(coordinates) - 1)
    for control, coordinate in zip(spline.points, coordinates):
        control.co = (*coordinate, 1.0)
    spline.order_u = min(max(2, order), len(coordinates))
    spline.use_endpoint_u = True
    obj = bpy.data.objects.new(name, curve)
    context.collection.objects.link(obj)
    for selected in context.selected_objects:
        selected.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj
    return obj


def create_bezier_curve_object(context, start, start_handle, end, end_handle,
                               name="ShapeFlow Bezier"):
    """Create one editable native cubic Bezier segment with explicit handles."""
    start, start_handle = Vector(start), Vector(start_handle)
    end, end_handle = Vector(end), Vector(end_handle)
    if (end - start).length < EPSILON:
        raise ValueError("Bezier endpoints must be different")
    curve = bpy.data.curves.new(name, type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 12
    spline = curve.splines.new(type='BEZIER')
    spline.bezier_points.add(1)
    first, last = spline.bezier_points
    first.co = start
    first.handle_left_type = first.handle_right_type = 'FREE'
    first.handle_right = start_handle
    first.handle_left = start * 2.0 - start_handle
    last.co = end
    last.handle_left_type = last.handle_right_type = 'FREE'
    last.handle_left = end_handle
    last.handle_right = end * 2.0 - end_handle
    obj = bpy.data.objects.new(name, curve)
    context.collection.objects.link(obj)
    for selected in context.selected_objects:
        selected.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj
    return obj


def create_pen_curve_object(context, points, name="ShapeFlow Pen"):
    """Create a multi-node native Bezier path with automatic handles."""
    coordinates = [Vector(point) for point in points]
    if len(coordinates) < 2:
        raise ValueError("A Pen path needs at least two points")
    curve = bpy.data.curves.new(name, type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 12
    spline = curve.splines.new(type='BEZIER')
    spline.bezier_points.add(len(coordinates) - 1)
    for point, coordinate in zip(spline.bezier_points, coordinates):
        point.co = coordinate
        point.handle_left_type = 'AUTO'
        point.handle_right_type = 'AUTO'
    obj = bpy.data.objects.new(name, curve)
    context.collection.objects.link(obj)
    for selected in context.selected_objects:
        selected.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj
    return obj
