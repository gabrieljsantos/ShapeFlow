from mathutils import Vector


UNIT_TO_METERS = {
    'MILLIMETERS': 0.001,
    'CENTIMETERS': 0.01,
    'METERS': 1.0,
}


def typed_length_to_blender_units(value, unit, scale_length=1.0):
    """Convert a value in the selected display unit to Blender units."""
    if scale_length <= 0.0:
        scale_length = 1.0
    return float(value) * UNIT_TO_METERS[unit] / scale_length


def unit_suffix(unit):
    return {'MILLIMETERS': 'mm', 'CENTIMETERS': 'cm', 'METERS': 'm'}[unit]


def plane_axes(plane):
    if plane == 'XZ':
        return Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))
    if plane == 'YZ':
        return Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))
    return Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def rectangle_corners(start, end, plane):
    axis_u, axis_v, _ = plane_axes(plane)
    delta = end - start
    du, dv = delta.dot(axis_u), delta.dot(axis_v)
    return [start, start + axis_u * du, start + axis_u * du + axis_v * dv, start + axis_v * dv]


def nearest_point_on_segment(point, a, b):
    segment = b - a
    length_squared = segment.length_squared
    factor = 0.0 if length_squared == 0.0 else (point - a).dot(segment) / length_squared
    factor = max(0.0, min(1.0, factor))
    return a.lerp(b, factor), factor
