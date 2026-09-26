"""Grid and existing-geometry snapping for drawing tools."""
from dataclasses import dataclass

from mathutils import Vector
from bpy_extras import view3d_utils

from .geometry import (
    nearest_point_on_segment,
    plane_axes,
    plane_coordinates,
    point_from_plane_coordinates,
    snap_scalar,
    typed_length_to_blender_units,
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
    candidates = [SnapCandidate(point.copy(), "VERTEX") for point in vertices]
    edges = []
    for edge in obj.data.edges:
        a = vertices[edge.vertices[0]].copy()
        b = vertices[edge.vertices[1]].copy()
        edges.append((a, b))
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


def nearest_screen_geometry(context, region, mouse, candidates, edges, threshold):
    """Find a point, or any position along an edge, near the screen cursor."""
    rv3d = context.space_data.region_3d
    mouse = Vector(mouse)
    best = None
    for candidate in candidates:
        screen = view3d_utils.location_3d_to_region_2d(region, rv3d, candidate.point)
        if screen is None:
            continue
        distance = (screen - mouse).length
        score = (SNAP_PRIORITY.get(candidate.kind, 99), distance)
        if distance <= threshold and (best is None or score < best[0]):
            best = (score, candidate)
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
        if distance <= threshold and (best is None or score < best[0]):
            best = (score, SnapCandidate(a.lerp(b, factor), "EDGE", (a.copy(), b.copy())))
    return best[1] if best else None


def _screen_distance(region, rv3d, a, b):
    a2 = view3d_utils.location_3d_to_region_2d(region, rv3d, a)
    b2 = view3d_utils.location_3d_to_region_2d(region, rv3d, b)
    if a2 is None or b2 is None:
        return float('inf')
    return (a2 - b2).length


def snap_draw_point(context, region, raw_point, plane, settings, candidates, edges, bypass=False):
    if bypass or not settings.snap_enabled:
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
        u, v = snap_scalar(u, unit_spacing), snap_scalar(v, unit_spacing)
        kind = "GRID"
    point = point_from_plane_coordinates(u, v, plane) + plane_offset

    if not settings.geometry_snap:
        return SnapResult(point, kind)

    rv3d = context.space_data.region_3d
    threshold = float(settings.snap_distance)
    # Strongest snap: a known point or any position along a coplanar edge.
    best = None
    for candidate in candidates:
        distance = _screen_distance(region, rv3d, raw_point, candidate.point)
        if distance <= threshold and (best is None or distance < best[0]):
            best = (distance, candidate.point, candidate.kind)
    for a, b in edges:
        nearest, _factor = nearest_point_on_segment(raw_point, a, b)
        distance = _screen_distance(region, rv3d, raw_point, nearest)
        if distance <= threshold and (best is None or distance < best[0]):
            best = (distance, nearest, "EDGE")
    if best is not None:
        return SnapResult(best[1].copy(), best[2], best[1].copy(), best[1].copy())

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
