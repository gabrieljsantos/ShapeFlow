from mathutils import Vector
from math import atan2, cos, pi, sin


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


def blender_units_to_typed_length(value, unit, scale_length=1.0):
    """Convert Blender units to the selected display unit."""
    if scale_length <= 0.0:
        scale_length = 1.0
    return float(value) * scale_length / UNIT_TO_METERS[unit]


def unit_suffix(unit):
    return {'MILLIMETERS': 'mm', 'CENTIMETERS': 'cm', 'METERS': 'm'}[unit]


def snap_scalar(value, spacing):
    if spacing <= 0.0:
        return value
    return round(value / spacing) * spacing


def plane_coordinates(point, plane):
    axis_u, axis_v, _normal = plane_axes(plane)
    return point.dot(axis_u), point.dot(axis_v)


def point_from_plane_coordinates(u, v, plane):
    axis_u, axis_v, _normal = plane_axes(plane)
    return axis_u * u + axis_v * v


def parse_coordinate_pair(text):
    """Parse two decimal values separated by a semicolon."""
    parts = [part.strip().replace(',', '.') for part in text.split(';')]
    if len(parts) != 2 or not all(parts):
        raise ValueError("Use two values separated by semicolon")
    return float(parts[0]), float(parts[1])


def plane_axes(plane):
    if plane == 'XZ':
        return Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))
    if plane == 'YZ':
        return Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))
    return Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def axis_name(axis):
    """Return the world-axis name represented by a unit direction vector."""
    if axis is None:
        return None
    components = (abs(axis.x), abs(axis.y), abs(axis.z))
    return ('X', 'Y', 'Z')[max(range(3), key=components.__getitem__)]


def plane_from_axes(first, second):
    """Return the drawing plane defined by two different world-axis names."""
    pair = frozenset((first, second))
    return {
        frozenset(('X', 'Y')): 'XY',
        frozenset(('X', 'Z')): 'XZ',
        frozenset(('Y', 'Z')): 'YZ',
    }.get(pair)


def accumulate_axis_intent(candidate, pixels, axis, motion_pixels, threshold):
    """Accumulate a continuous screen-space gesture before accepting an auto axis."""
    if axis is None:
        return candidate, pixels, False
    if axis != candidate:
        candidate = axis
        pixels = 0.0
    pixels += max(0.0, float(motion_pixels))
    return candidate, pixels, pixels >= float(threshold)


def rectangle_corners(start, end, plane, origin_mode='DIAMETER', proportional=False):
    axis_u, axis_v, _ = plane_axes(plane)
    delta = end - start
    du, dv = delta.dot(axis_u), delta.dot(axis_v)
    if proportional:
        size = max(abs(du), abs(dv))
        du = size if du >= 0.0 else -size
        dv = size if dv >= 0.0 else -size
    if origin_mode == 'CENTER':
        return [
            start - axis_u * du - axis_v * dv,
            start + axis_u * du - axis_v * dv,
            start + axis_u * du + axis_v * dv,
            start - axis_u * du + axis_v * dv,
        ]
    return [start, start + axis_u * du, start + axis_u * du + axis_v * dv, start + axis_v * dv]


def regular_polygon_points(start, end, plane, sides, origin_mode='CENTER'):
    """Build a regular polygon on a ShapeFlow drawing plane."""
    if sides < 3:
        raise ValueError("A polygon needs at least three sides")
    axis_u, axis_v, _normal = plane_axes(plane)
    if origin_mode == 'DIAMETER':
        center = (start + end) * 0.5
        radial = (end - start) * 0.5
    else:
        center = start
        radial = end - start
    radius = radial.length
    if radius < 1.0e-6:
        raise ValueError("Polygon radius is too small")
    angle = __import__('math').atan2(radial.dot(axis_v), radial.dot(axis_u))
    return [
        center + axis_u * (cos(angle + 2.0 * pi * i / sides) * radius)
        + axis_v * (sin(angle + 2.0 * pi * i / sides) * radius)
        for i in range(sides)
    ]


def _plane_point(u, v, offset, plane):
    axis_u, axis_v, normal = plane_axes(plane)
    return axis_u * u + axis_v * v + normal * offset


def arc_points_three(start, middle, end, plane, segments=32):
    """Sample the circular arc that passes through three coplanar points."""
    p1 = plane_coordinates(start, plane); p2 = plane_coordinates(middle, plane); p3 = plane_coordinates(end, plane)
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3
    determinant = 2.0 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(determinant) < 1.0e-10:
        raise ValueError("Arc points must not be collinear")
    ux = ((x1*x1+y1*y1)*(y2-y3) + (x2*x2+y2*y2)*(y3-y1) + (x3*x3+y3*y3)*(y1-y2)) / determinant
    uy = ((x1*x1+y1*y1)*(x3-x2) + (x2*x2+y2*y2)*(x1-x3) + (x3*x3+y3*y3)*(x2-x1)) / determinant
    a1, a2, a3 = atan2(y1-uy, x1-ux), atan2(y2-uy, x2-ux), atan2(y3-uy, x3-ux)
    tau = 2.0 * pi
    ccw_total = (a3 - a1) % tau
    ccw_middle = (a2 - a1) % tau
    sweep = ccw_total if ccw_middle <= ccw_total else ccw_total - tau
    radius = ((x1-ux)**2 + (y1-uy)**2) ** 0.5
    _u, _v, normal = plane_axes(plane)
    offset = start.dot(normal)
    return [_plane_point(ux + cos(a1+sweep*i/segments)*radius, uy + sin(a1+sweep*i/segments)*radius, offset, plane) for i in range(segments+1)]


def bezier_points(start, start_handle, end_handle, end, segments=32):
    points = []
    for index in range(segments + 1):
        t = index / segments; one = 1.0 - t
        points.append(start * (one**3) + start_handle * (3*one*one*t) + end_handle * (3*one*t*t) + end * (t**3))
    return points


def crescent_points(center, rim, curvature, plane, segments=32):
    """Create a closed crescent outline from center, radius and inner bulge."""
    axis_u, axis_v, normal = plane_axes(plane)
    radial = rim - center
    radius = radial.length
    if radius < 1.0e-6:
        raise ValueError("Crescent radius is too small")
    direction = radial.normalized()
    side = normal.cross(direction).normalized()
    first = center + side * radius
    last = center - side * radius
    outer = []
    for i in range(segments + 1):
        angle = pi * 0.5 - pi * i / segments
        outer.append(center + side * (sin(angle) * radius) + direction * (cos(angle) * radius))
    control = curvature
    inner = []
    # Omit the final `first` point: the polygon closing edge supplies it and
    # avoids a duplicate zero-length edge in Blender's mesh.
    for i in range(1, segments):
        t = i / segments; one = 1.0 - t
        inner.append(last * (one*one) + control * (2*one*t) + first * (t*t))
    return outer + inner


def nearest_point_on_segment(point, a, b):
    segment = b - a
    length_squared = segment.length_squared
    factor = 0.0 if length_squared == 0.0 else (point - a).dot(segment) / length_squared
    factor = max(0.0, min(1.0, factor))
    return a.lerp(b, factor), factor
