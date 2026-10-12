"""Native Poly Curve trim and extend operations."""
from mathutils import Vector
from mathutils.geometry import intersect_line_line


EPSILON = 1.0e-5


def _poly_world_points(obj):
    if obj is None or obj.type != 'CURVE' or not obj.data.splines:
        raise ValueError("Select native Curve objects")
    spline = obj.data.splines[0]
    if spline.type != 'POLY' or len(spline.points) < 2:
        raise ValueError("Trim and Extend currently require a Poly Curve")
    return [obj.matrix_world @ Vector(point.co[:3]) for point in spline.points]


def _replace_poly_points(obj, world_points):
    local = obj.matrix_world.inverted()
    obj.data.splines.clear()
    spline = obj.data.splines.new(type='POLY')
    spline.points.add(len(world_points) - 1)
    for point, world in zip(spline.points, world_points):
        point.co = (*(local @ Vector(world)), 1.0)
    obj.data.update_tag()
    return obj


def _line_intersection(first_a, first_b, second_a, second_b):
    result = intersect_line_line(first_a, first_b, second_a, second_b)
    if result is None or (result[0] - result[1]).length > EPSILON:
        return None
    point = (result[0] + result[1]) * 0.5
    first = first_b - first_a
    second = second_b - second_a
    if first.length_squared < EPSILON or second.length_squared < EPSILON:
        return None
    t = (point - first_a).dot(first) / first.length_squared
    u = (point - second_a).dot(second) / second.length_squared
    return point, t, u


def trim_curve(subject, cutter, side='END'):
    points = _poly_world_points(subject)
    cutter_points = _poly_world_points(cutter)
    intersections = []
    for index, (start, end) in enumerate(zip(points, points[1:])):
        for cut_start, cut_end in zip(cutter_points, cutter_points[1:]):
            result = _line_intersection(start, end, cut_start, cut_end)
            if result and -EPSILON <= result[1] <= 1.0 + EPSILON and -EPSILON <= result[2] <= 1.0 + EPSILON:
                intersections.append((index + result[1], index, result[0]))
    if not intersections:
        raise ValueError("The selected curves do not intersect")
    position, index, point = (max(intersections) if side == 'END' else min(intersections))
    if side == 'END':
        result = [*points[:index + 1], point]
    else:
        result = [point, *points[index + 1:]]
    if len(result) < 2 or sum((b - a).length for a, b in zip(result, result[1:])) < EPSILON:
        raise ValueError("Trim would remove the entire curve")
    return _replace_poly_points(subject, result)


def extend_curve(subject, boundary, side='END'):
    points = _poly_world_points(subject)
    boundary_points = _poly_world_points(boundary)
    if side == 'END':
        endpoint, neighbor = points[-1], points[-2]
    else:
        endpoint, neighbor = points[0], points[1]
    direction = endpoint - neighbor
    candidates = []
    for start, end in zip(boundary_points, boundary_points[1:]):
        result = _line_intersection(endpoint, endpoint + direction, start, end)
        if result and result[1] > EPSILON and -EPSILON <= result[2] <= 1.0 + EPSILON:
            candidates.append(((result[0] - endpoint).length, result[0]))
    if not candidates:
        raise ValueError("No boundary intersects the selected endpoint direction")
    point = min(candidates, key=lambda item: item[0])[1]
    result = [*points, point] if side == 'END' else [point, *points]
    return _replace_poly_points(subject, result)
