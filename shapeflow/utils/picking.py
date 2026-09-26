from mathutils import Vector
from bpy_extras import view3d_utils

from .geometry import nearest_point_on_segment


def viewport_region(context):
    """Return the main WINDOW region, even when invoked from the N-panel."""
    if context.area is None or context.area.type != 'VIEW_3D':
        return None
    return next((region for region in context.area.regions if region.type == 'WINDOW'), None)


def viewport_mouse(context, event):
    region = viewport_region(context)
    if region is None:
        return None
    return region, (event.mouse_x - region.x, event.mouse_y - region.y)


def mouse_ray(context, mouse):
    region = viewport_region(context)
    rv3d = context.space_data.region_3d
    origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mouse)
    direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, mouse)
    return origin, direction.normalized()


def ray_plane(context, mouse, plane_point, plane_normal):
    origin, direction = mouse_ray(context, mouse)
    denominator = direction.dot(plane_normal)
    if abs(denominator) < 1.0e-8:
        return None
    distance = (plane_point - origin).dot(plane_normal) / denominator
    return origin + direction * distance


def pick_mesh_face(context, mouse):
    origin, direction = mouse_ray(context, mouse)
    hit, location, normal, face_index, obj, _matrix = context.scene.ray_cast(
        context.evaluated_depsgraph_get(), origin, direction
    )
    if not hit or obj is None or obj.type != 'MESH' or face_index < 0:
        return None
    return obj, face_index, location, normal


def nearest_face_boundary(obj, face_index, world_point):
    polygon = obj.data.polygons[face_index]
    inverse = obj.matrix_world.inverted()
    local_point = inverse @ world_point
    best = None
    for edge_key in polygon.edge_keys:
        edge = next(e for e in obj.data.edges if set(e.vertices) == set(edge_key))
        a = obj.data.vertices[edge.vertices[0]].co
        b = obj.data.vertices[edge.vertices[1]].co
        point, factor = nearest_point_on_segment(local_point, a, b)
        distance = (point - local_point).length
        if best is None or distance < best[0]:
            best = (distance, obj.matrix_world @ point, edge.index, factor)
    return best
