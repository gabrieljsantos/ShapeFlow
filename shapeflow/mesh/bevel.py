"""Native Blender mesh bevel operations used by Fillet and Chamfer."""
import bmesh


EPSILON = 1.0e-6


def bevel_edge(obj, edge_index, width, segments=1):
    if obj is None or obj.type != 'MESH':
        raise ValueError("Bevel requires a mesh object")
    if abs(width) < EPSILON:
        raise ValueError("Bevel width is too small")
    if not 0 <= edge_index < len(obj.data.edges):
        raise ValueError("The selected edge no longer exists")

    scale = obj.matrix_world.to_scale()
    average_scale = sum(abs(value) for value in scale) / 3.0
    if average_scale < EPSILON:
        raise ValueError("Apply a valid object scale before beveling")

    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        result = bmesh.ops.bevel(
            bm,
            geom=[bm.edges[edge_index]],
            offset=abs(width) / average_scale,
            segments=max(1, int(segments)),
            affect='EDGES',
            clamp_overlap=True,
        )
        if not result.get('faces'):
            raise ValueError("Blender could not bevel this edge")
        bm.to_mesh(obj.data)
        obj.data.update()
    finally:
        bm.free()
    return obj
