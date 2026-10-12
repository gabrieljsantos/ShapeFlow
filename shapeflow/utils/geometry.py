from mathutils import Vector
from math import acos, atan2, cos, pi, sin, sqrt


UNIT_TO_METERS = {
    'MILLIMETERS': 0.001,
    'CENTIMETERS': 0.01,
    'METERS': 1.0,
}


def angle_between_points(center, first, second):
    """Return the unsigned angle in radians between two rays from center."""
    center = Vector(center)
    first_ray = Vector(first) - center
    second_ray = Vector(second) - center
    if first_ray.length < 1.0e-6 or second_ray.length < 1.0e-6:
        raise ValueError("Angle directions must be different from the center")
    cosine = max(-1.0, min(1.0, first_ray.normalized().dot(second_ray.normalized())))
    return acos(cosine)


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
    if not isinstance(plane, str):
        axis_u, axis_v, normal = plane
        return Vector(axis_u).normalized(), Vector(axis_v).normalized(), Vector(normal).normalized()
    if plane == 'XZ':
        return Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))
    if plane == 'YZ':
        return Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))
    return Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def settings_plane(settings, auto_plane=None):
    """Resolve a configured world, automatic, or captured face workplane."""
    if settings.drawing_plane == 'AUTO':
        return auto_plane
    if settings.drawing_plane == 'FACE':
        return (
            Vector(settings.workplane_u),
            Vector(settings.workplane_v),
            Vector(settings.workplane_normal),
        )
    return settings.drawing_plane


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


def regular_polygon_edge_points(center, edge_midpoint, plane, sides):
    """Build a regular polygon when the drag endpoint is an edge midpoint."""
    if sides < 3:
        raise ValueError("A polygon needs at least three sides")
    axis_u, axis_v, _normal = plane_axes(plane)
    radial = Vector(edge_midpoint) - Vector(center)
    apothem = sqrt(radial.dot(axis_u) ** 2 + radial.dot(axis_v) ** 2)
    if apothem < 1.0e-6:
        raise ValueError("Polygon apothem is too small")
    circumradius = apothem / cos(pi / sides)
    edge_angle = atan2(radial.dot(axis_v), radial.dot(axis_u))
    first_angle = edge_angle - pi / sides
    return [
        Vector(center)
        + axis_u * (cos(first_angle + 2.0 * pi * index / sides) * circumradius)
        + axis_v * (sin(first_angle + 2.0 * pi * index / sides) * circumradius)
        for index in range(sides)
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


def center_arc_points(center, start, end, plane, segments=32):
    """Create a counter-clockwise arc from center, radius point, and angle point."""
    center = Vector(center)
    start = Vector(start)
    end = Vector(end)
    axis_u, axis_v, _normal = plane_axes(plane)
    start_vector = start - center
    radius = start_vector.length
    if radius < 1.0e-6:
        raise ValueError("Arc radius is too small")
    start_angle = atan2(start_vector.dot(axis_v), start_vector.dot(axis_u))
    end_vector = end - center
    if end_vector.length < 1.0e-6:
        raise ValueError("Arc angle point is too close to the center")
    end_angle = atan2(end_vector.dot(axis_v), end_vector.dot(axis_u))
    sweep = (end_angle - start_angle) % (2.0 * pi)
    if sweep < 1.0e-6:
        raise ValueError("Arc angle is too small")
    return [
        center
        + axis_u * (radius * cos(start_angle + sweep * index / segments))
        + axis_v * (radius * sin(start_angle + sweep * index / segments))
        for index in range(segments + 1)
    ]


def ellipse_points(center, radius_point, secondary_point, plane, proportional=False, segments=64):
    """Return a planar ellipse oriented by its first radius vector."""
    if segments < 8:
        raise ValueError("An ellipse needs at least eight segments")
    center = Vector(center)
    radius_vector = Vector(radius_point) - center
    axis_u, axis_v, _normal = plane_axes(plane)
    first_u = radius_vector.dot(axis_u)
    first_v = radius_vector.dot(axis_v)
    first_radius = (first_u * first_u + first_v * first_v) ** 0.5
    if first_radius < 1.0e-6:
        raise ValueError("Ellipse radius is too small")
    major = (axis_u * first_u + axis_v * first_v).normalized()
    minor = (-axis_u * first_v + axis_v * first_u).normalized()
    if proportional:
        second_radius = first_radius
    else:
        second_radius = abs((Vector(secondary_point) - center).dot(minor))
        if second_radius < 1.0e-6:
            raise ValueError("Ellipse secondary radius is too small")
    return [
        center
        + major * (first_radius * cos(2.0 * pi * index / segments))
        + minor * (second_radius * sin(2.0 * pi * index / segments))
        for index in range(segments)
    ]


def ellipse_from_foci_points(first_focus, second_focus, curve_point, plane, segments=64):
    """Create an ellipse through curve_point from two focal points."""
    first_focus, second_focus, curve_point = map(Vector, (first_focus, second_focus, curve_point))
    axis_u, axis_v, normal = plane_axes(plane)
    center = (first_focus + second_focus) * 0.5
    focal_vector = second_focus - first_focus
    focal_x, focal_y = focal_vector.dot(axis_u) * 0.5, focal_vector.dot(axis_v) * 0.5
    focal_distance = sqrt(focal_x * focal_x + focal_y * focal_y)
    if focal_distance < 1.0e-6:
        raise ValueError("Ellipse foci must be distinct")
    major = (axis_u * focal_x + axis_v * focal_y).normalized()
    minor = normal.cross(major).normalized()
    point_vector = curve_point - center
    point_x, point_y = point_vector.dot(major), point_vector.dot(minor)
    major_radius = ((curve_point - first_focus).length + (curve_point - second_focus).length) * 0.5
    if major_radius <= focal_distance + 1.0e-6:
        raise ValueError("The curve point must define a non-degenerate ellipse")
    minor_radius = sqrt(max(0.0, major_radius * major_radius - focal_distance * focal_distance))
    if minor_radius < 1.0e-6:
        raise ValueError("Ellipse height is too small")
    return [
        center + major * (major_radius * cos(2*pi*i/segments))
        + minor * (minor_radius * sin(2*pi*i/segments))
        for i in range(segments)
    ]


def ellipse_from_axis_height(start, end, height_point, plane, segments=64):
    """Create an ellipse from major-axis endpoints and a perpendicular height."""
    start, end, height_point = map(Vector, (start, end, height_point))
    _axis_u, _axis_v, normal = plane_axes(plane)
    axis = end - start
    major_radius = axis.length * 0.5
    if major_radius < 1.0e-6:
        raise ValueError("Ellipse axis is too small")
    major = axis.normalized()
    minor = normal.cross(major).normalized()
    center = (start + end) * 0.5
    minor_radius = abs((height_point - center).dot(minor))
    if minor_radius < 1.0e-6:
        raise ValueError("Ellipse height is too small")
    return [
        center + major * (major_radius*cos(2*pi*i/segments))
        + minor * (minor_radius*sin(2*pi*i/segments))
        for i in range(segments)
    ]


def circle_from_diameter_points(start, end, plane, segments=64):
    """Create a circle through two opposite diameter endpoints."""
    start, end = Vector(start), Vector(end)
    center = (start + end) * 0.5
    radius_point = end
    axis_u, axis_v, _normal = plane_axes(plane)
    delta = radius_point - center
    radius = sqrt(delta.dot(axis_u)**2 + delta.dot(axis_v)**2)
    if radius < 1.0e-6:
        raise ValueError("Circle diameter is too small")
    angle = atan2(delta.dot(axis_v), delta.dot(axis_u))
    return [center + axis_u*(radius*cos(angle+2*pi*i/segments)) + axis_v*(radius*sin(angle+2*pi*i/segments)) for i in range(segments)]


def crescent_two_arcs_points(first, second, bulge, plane, inner_factor=0.28):
    """Create a crescent from its chord and one curvature point."""
    first, second, bulge = map(Vector, (first, second, bulge))
    midpoint = (first + second) * 0.5
    inner_bulge = midpoint + (bulge - midpoint) * inner_factor
    first_arc = arc_points_three(first, bulge, second, plane)
    second_arc = arc_points_three(second, inner_bulge, first, plane)
    return first_arc + second_arc[1:-1]


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


def smooth_stroke_points(points, iterations=2):
    """Smooth an open stroke with endpoint-preserving Chaikin subdivision."""
    result = [Vector(point) for point in points]
    if len(result) < 3:
        return result
    for _index in range(max(0, iterations)):
        smoothed = [result[0]]
        for first, second in zip(result, result[1:]):
            smoothed.extend((first.lerp(second, 0.25), first.lerp(second, 0.75)))
        smoothed.append(result[-1])
        result = smoothed
    return result


def recognize_stroke(points):
    """Classify a sampled stroke as LINE, CIRCLE, or SMOOTH."""
    samples = [Vector(point) for point in points]
    if len(samples) < 2:
        raise ValueError("A smart stroke needs at least two points")
    start, end = samples[0], samples[-1]
    chord = end - start
    if chord.length > 1.0e-6:
        direction = chord.normalized()
        deviation = max(((point - start) - direction * (point - start).dot(direction)).length for point in samples)
        if deviation <= max(chord.length * 0.025, 1.0e-5):
            return 'LINE', (start, end)
    center = sum(samples, Vector()) / len(samples)
    radii = [(point - center).length for point in samples]
    radius = sum(radii) / len(radii)
    closed = radius > 1.0e-6 and (end - start).length <= radius * 0.35
    radial_error = max(abs(value - radius) for value in radii) / radius if radius > 1.0e-6 else 1.0
    if len(samples) >= 8 and closed and radial_error <= 0.18:
        return 'CIRCLE', (center, radius)
    return 'SMOOTH', tuple(samples)


def rotated_rectangle_points(origin, width_end, height_point, plane):
    """Build a rectangle from an arbitrary planar width direction and height point."""
    origin, width_end, height_point = Vector(origin), Vector(width_end), Vector(height_point)
    width = width_end - origin
    if width.length < 1.0e-6:
        raise ValueError("Rotated rectangle width is too small")
    _axis_u, _axis_v, normal = plane_axes(plane)
    side = normal.cross(width).normalized()
    height = (height_point - width_end).dot(side)
    if abs(height) < 1.0e-6:
        raise ValueError("Rotated rectangle height is too small")
    offset = side * height
    return [origin, width_end, width_end + offset, origin + offset]
