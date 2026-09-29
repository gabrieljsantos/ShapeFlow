"""Grid and existing-geometry snapping for drawing tools."""
from dataclasses import dataclass

from mathutils import Vector
from bpy_extras import view3d_utils

from .geometry import (
    plane_axes,
    plane_coordinates,
    point_from_plane_coordinates,
    snap_scalar,
    typed_length_to_blender_units,
    settings_plane,
)


SNAP_PRIORITY = {
    "VERTEX": 0,
    "MIDPOINT": 1,
    "EDGE": 2,
    "FACE_CENTER": 3,
    "FACE_POINT": 4,
}


@dataclass
class SnapCandidate:
    point: Vector
    kind: str
    highlight: tuple | None = None


@dataclass
class SnapResult:
    point: Vector
    kind: str = "FREE"
    guide_u: Vector | None = None
    guide_v: Vector | None = None


def collect_plane_geometry(context, plane, plane_point=None, tolerance=1.0e-5):
    """Collect stable snap locations and coplanar edges from visible mesh objects."""
    _u, _v, normal = plane_axes(plane)
    plane_point = Vector((0.0, 0.0, 0.0)) if plane_point is None else Vector(plane_point)
    candidates = []
    edges = []
    for obj in context.visible_objects:
        if obj.type != 'MESH' or obj.hide_get():
            continue
        matrix = obj.matrix_world
        world_vertices = [matrix @ vertex.co for vertex in obj.data.vertices]
        for point in world_vertices:
            if abs((point - plane_point).dot(normal)) <= tolerance:
                candidates.append(SnapCandidate(point.copy(), "VERTEX"))
        for edge in obj.data.edges:
            a = world_vertices[edge.vertices[0]]
            b = world_vertices[edge.vertices[1]]
            if abs((a - plane_point).dot(normal)) <= tolerance and abs((b - plane_point).dot(normal)) <= tolerance:
                midpoint = (a + b) * 0.5
                candidates.append(SnapCandidate(midpoint, "MIDPOINT"))
                edges.append((a.copy(), b.copy()))
        for polygon in obj.data.polygons:
            center = matrix @ polygon.center
            if abs((center - plane_point).dot(normal)) <= tolerance:
                candidates.append(SnapCandidate(center, "FACE_CENTER"))
    return candidates, edges


def collect_scene_snap_points(context, exclude=None):
    """Collect vertices, edge midpoints, and face centers in full 3D space."""
    points = []
    for obj in context.visible_objects:
        if obj == exclude or obj.type != 'MESH' or obj.hide_get():
            continue
        matrix = obj.matrix_world
        vertices = [matrix @ vertex.co for vertex in obj.data.vertices]
        points.extend(SnapCandidate(point.copy(), "VERTEX") for point in vertices)
        for edge in obj.data.edges:
            points.append(SnapCandidate(
                (vertices[edge.vertices[0]] + vertices[edge.vertices[1]]) * 0.5, "MIDPOINT"
            ))
        points.extend(SnapCandidate(matrix @ polygon.center, "FACE_CENTER") for polygon in obj.data.polygons)
    return points


def collect_object_snap_geometry(obj):
    """Return full-3D snap points and edges for one mesh object."""
    if obj is None or obj.type != 'MESH':
        return [], []
    matrix = obj.matrix_world
    vertices = [matrix @ vertex.co for vertex in obj.data.vertices]
    vertex_edges = {index: [] for index in range(len(vertices))}
    edges = []
    for edge in obj.data.edges:
        a = vertices[edge.vertices[0]].copy()
        b = vertices[edge.vertices[1]].copy()
        edges.append((a, b))
        vertex_edges[edge.vertices[0]].append((a.copy(), b.copy()))
        vertex_edges[edge.vertices[1]].append((a.copy(), b.copy()))
    candidates = [
        SnapCandidate(point.copy(), "VERTEX", tuple(vertex_edges[index]))
        for index, point in enumerate(vertices)
    ]
    for a, b in edges:
        candidates.append(SnapCandidate((a + b) * 0.5, "MIDPOINT", (a.copy(), b.copy())))
    for polygon in obj.data.polygons:
        outline = tuple(vertices[index].copy() for index in polygon.vertices)
        candidates.append(SnapCandidate(matrix @ polygon.center, "FACE_CENTER", outline))
    return candidates, edges


def collect_scene_snap_geometry(context, exclude=None):
    candidates = []
    edges = []
    for obj in context.visible_objects:
        if obj == exclude or obj.type != 'MESH' or obj.hide_get():
            continue
        obj_candidates, obj_edges = collect_object_snap_geometry(obj)
        candidates.extend(obj_candidates)
        edges.extend(obj_edges)
    return candidates, edges


def nearest_screen_candidate(context, region, mouse, candidates, threshold):
    rv3d = context.space_data.region_3d
    best = None
    for candidate in candidates:
        screen = view3d_utils.location_3d_to_region_2d(region, rv3d, candidate.point)
        if screen is None:
            continue
        distance = (screen - Vector(mouse)).length
        if distance <= threshold and (best is None or distance < best[0]):
            best = (distance, candidate)
    return best[1] if best else None


def _screen_geometry_matches(context, region, mouse, candidates, edges, threshold):
    """Return all geometry under the cursor in Move priority order."""
    rv3d = context.space_data.region_3d
    mouse = Vector(mouse)
    matches = []
    for candidate in candidates:
        screen = view3d_utils.location_3d_to_region_2d(region, rv3d, candidate.point)
        if screen is None:
            continue
        distance = (screen - mouse).length
        score = (SNAP_PRIORITY.get(candidate.kind, 99), distance)
        if distance <= threshold:
            matches.append((score, candidate))
    for a, b in edges:
        screen_a = view3d_utils.location_3d_to_region_2d(region, rv3d, a)
        screen_b = view3d_utils.location_3d_to_region_2d(region, rv3d, b)
        if screen_a is None or screen_b is None:
            continue
        segment = screen_b - screen_a
        factor = 0.0 if segment.length_squared == 0.0 else (mouse - screen_a).dot(segment) / segment.length_squared
        factor = max(0.0, min(1.0, factor))
        screen_point = screen_a.lerp(screen_b, factor)
        distance = (screen_point - mouse).length
        score = (SNAP_PRIORITY["EDGE"], distance)
        if distance <= threshold:
            matches.append((score, SnapCandidate(a.lerp(b, factor), "EDGE", (a.copy(), b.copy()))))
    matches.sort(key=lambda item: item[0])
    return [candidate for _score, candidate in matches]


def nearest_screen_geometry(context, region, mouse, candidates, edges, threshold, skip=0):
    """Find geometry near the cursor, optionally skipping higher-priority hits."""
    matches = _screen_geometry_matches(context, region, mouse, candidates, edges, threshold)
    return matches[skip] if skip < len(matches) else None


def travel_3d_cursor(context, region, mouse, previous_mouse, point, settings, candidates, edges,
                     bypass=False, magnetic_bypass=False, skip=0, raw_point=None,
                     snap_origin=None, allowed_axes=None):
    """Position the construction cursor using geometry, an axis, or the drawing plane."""
    geometry = nearest_screen_geometry(
        context, region, mouse, candidates, edges, settings.snap_distance, skip=skip
    )
    if geometry and settings.geometry_snap and not bypass and not magnetic_bypass:
        snapped = geometry.point.copy()
        return snapped, geometry.kind, None, snapped.copy()

    if not settings.axis_cursor:
        rv3d = context.space_data.region_3d
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mouse)
        ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, mouse)
        active_plane = settings_plane(settings)
        _axis_u, _axis_v, normal = plane_axes(active_plane)
        denominator = ray_direction.dot(normal)
        if abs(denominator) < 1.0e-8:
            current = Vector(point)
            return current, "CURSOR", None, current.copy()
        distance = (Vector(point) - ray_origin).dot(normal) / denominator
        result = ray_origin + ray_direction * distance
        if settings.grid_snap and not bypass:
            spacing = typed_length_to_blender_units(
                settings.grid_spacing, settings.length_unit,
                context.scene.unit_settings.scale_length,
            )
            u, v = plane_coordinates(result, active_plane)
            plane_offset = normal * Vector(point).dot(normal)
            result = point_from_plane_coordinates(
                snap_scalar(u, spacing), snap_scalar(v, spacing), active_plane,
            ) + plane_offset
        return result, "PLANE", None, result.copy()

    if previous_mouse is None:
        current = Vector(point)
        return current, "CURSOR", None, current.copy()
    delta = Vector(mouse) - Vector(previous_mouse)
    if delta.length < 1.0e-6:
        current = Vector(point)
        raw = Vector(raw_point) if raw_point is not None else current.copy()
        return current, "CURSOR", None, raw
    rv3d = context.space_data.region_3d
    origin_screen = view3d_utils.location_3d_to_region_2d(region, rv3d, point)
    if origin_screen is None:
        current = Vector(point)
        raw = Vector(raw_point) if raw_point is not None else current.copy()
        return current, "CURSOR", None, raw
    options = []
    navigation_axes = (
        tuple(zip(('X', 'Y', 'Z'), plane_axes(settings_plane(settings))))
        if settings.drawing_plane == 'FACE'
        else (('X', Vector((1, 0, 0))), ('Y', Vector((0, 1, 0))), ('Z', Vector((0, 0, 1))))
    )
    for name, axis in navigation_axes:
        if allowed_axes is not None and name not in allowed_axes:
            continue
        axis_screen = view3d_utils.location_3d_to_region_2d(region, rv3d, Vector(point) + axis)
        if axis_screen is None or (axis_screen - origin_screen).length < 1.0e-5:
            continue
        direction = axis_screen - origin_screen
        pixels_per_unit = direction.length
        direction.normalize()
        options.append((
            abs(delta.normalized().dot(direction)), delta.dot(direction),
            pixels_per_unit, name, axis,
        ))
    if not options:
        current = Vector(point)
        raw = Vector(raw_point) if raw_point is not None else current.copy()
        return current, "CURSOR", None, raw
    _alignment, signed_pixels, pixels_per_unit, name, axis = max(
        options, key=lambda item: item[0]
    )
    distance = signed_pixels / pixels_per_unit
    raw = Vector(raw_point) if raw_point is not None else Vector(point)
    raw_result = raw + axis * distance
    result = raw_result.copy()
    if settings.grid_snap and not bypass:
        spacing = typed_length_to_blender_units(
            settings.grid_spacing, settings.length_unit, context.scene.unit_settings.scale_length
        )
        origin = Vector(snap_origin) if snap_origin is not None else Vector(point)
        displacement = raw_result - origin
        result = origin + Vector(tuple(snap_scalar(value, spacing) for value in displacement))
    return result, f"AXIS_{name}", axis, raw_result


def _screen_distance(region, rv3d, a, b):
    a2 = view3d_utils.location_3d_to_region_2d(region, rv3d, a)
    b2 = view3d_utils.location_3d_to_region_2d(region, rv3d, b)
    if a2 is None or b2 is None:
        return float('inf')
    return (a2 - b2).length


def snap_draw_point(context, region, raw_point, plane, settings, candidates, edges,
                    bypass=False, magnetic_bypass=False, skip=0, origin=None):
    if bypass:
        return SnapResult(raw_point.copy())

    unit_spacing = typed_length_to_blender_units(
        settings.grid_spacing, settings.length_unit, context.scene.unit_settings.scale_length
    )
    raw_u, raw_v = plane_coordinates(raw_point, plane)
    _axis_u, _axis_v, normal = plane_axes(plane)
    plane_offset = normal * raw_point.dot(normal)
    u, v = raw_u, raw_v
    kind = "FREE"
    if settings.grid_snap:
        if origin is None:
            origin_u = origin_v = 0.0
        else:
            origin_u, origin_v = plane_coordinates(origin, plane)
        u = origin_u + snap_scalar(u - origin_u, unit_spacing)
        v = origin_v + snap_scalar(v - origin_v, unit_spacing)
        kind = "GRID"
    point = point_from_plane_coordinates(u, v, plane) + plane_offset

    if not settings.geometry_snap or magnetic_bypass:
        return SnapResult(point, kind)

    rv3d = context.space_data.region_3d
    threshold = float(settings.snap_distance)
    # Reuse Move's screen-space priority, limited to the drawing tool's existing
    # coplanar candidate set. Tab advances through this ordered list.
    raw_screen = view3d_utils.location_3d_to_region_2d(region, rv3d, raw_point)
    matches = (
        _screen_geometry_matches(context, region, raw_screen, candidates, edges, threshold)
        if raw_screen is not None else []
    )
    if skip < len(matches):
        geometry = matches[skip]
        return SnapResult(
            geometry.point.copy(), geometry.kind, geometry.point.copy(), geometry.point.copy()
        )

    # After all direct hits, offer axis alignment once, then a free cursor.
    if skip > len(matches):
        return SnapResult(point, kind)

    if not settings.smart_guides:
        return SnapResult(point, kind)

    # Secondary snap: align either crosshair axis with known geometry.
    guide_u = guide_v = None
    best_u = best_v = None
    for candidate in candidates:
        candidate_u, candidate_v = plane_coordinates(candidate.point, plane)
        aligned_u = point_from_plane_coordinates(candidate_u, raw_v, plane) + plane_offset
        aligned_v = point_from_plane_coordinates(raw_u, candidate_v, plane) + plane_offset
        distance_u = _screen_distance(region, rv3d, raw_point, aligned_u)
        distance_v = _screen_distance(region, rv3d, raw_point, aligned_v)
        if distance_u <= threshold and (best_u is None or distance_u < best_u[0]):
            best_u = (distance_u, candidate_u, candidate.point)
        if distance_v <= threshold and (best_v is None or distance_v < best_v[0]):
            best_v = (distance_v, candidate_v, candidate.point)
    if best_u:
        u, guide_u, kind = best_u[1], best_u[2].copy(), "ALIGNMENT"
    if best_v:
        v, guide_v, kind = best_v[1], best_v[2].copy(), "ALIGNMENT"
    return SnapResult(point_from_plane_coordinates(u, v, plane) + plane_offset, kind, guide_u, guide_v)
