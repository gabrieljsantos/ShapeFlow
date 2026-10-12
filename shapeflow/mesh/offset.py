"""Native Blender mesh offset operations."""
import bmesh


EPSILON = 1.0e-6


def inset_face(obj, face_index, thickness):
    """Inset one mesh face using Blender's native BMesh operation."""
    if obj is None or obj.type != 'MESH':
        raise ValueError("Offset requires a mesh object")
    if abs(thickness) < EPSILON:
        raise ValueError("Offset distance is too small")
    if not 0 <= face_index < len(obj.data.polygons):
        raise ValueError("The selected face no longer exists")

    scale = obj.matrix_world.to_scale()
    average_scale = sum(abs(value) for value in scale) / 3.0
    if average_scale < EPSILON:
        raise ValueError("Apply a valid object scale before offsetting")

    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        face = bm.faces[face_index]
        result = bmesh.ops.inset_individual(
            bm,
            faces=[face],
            thickness=abs(thickness) / average_scale,
            depth=0.0,
            use_even_offset=True,
            use_interpolate=True,
            use_relative_offset=False,
        )
        if not result.get('faces'):
            raise ValueError("Blender could not offset this face")
        bm.to_mesh(obj.data)
        obj.data.update()
    finally:
        bm.free()
    return obj
