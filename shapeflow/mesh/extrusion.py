import bmesh


EPSILON = 1.0e-6


def _is_movable_boundary_face(face):
    """A closed cap can be pushed inward by moving its existing boundary.

    Coplanar neighbours indicate that the face is only part of a larger surface;
    those faces keep extrusion semantics so a future recess can have side walls.
    """
    for edge in face.edges:
        if len(edge.link_faces) != 2:
            return False
        neighbour = edge.link_faces[0] if edge.link_faces[1] == face else edge.link_faces[1]
        if neighbour.normal.dot(face.normal) > 1.0 - EPSILON:
            return False
    return True


def extrude_face(obj, face_index, distance, copy=False):
    """Push/pull one face along its local normal.

    With Copy disabled, a face on an existing closed solid is pushed or pulled
    by moving its existing boundary. With Copy enabled, the source is preserved
    and an extruded copy plus side walls is created. A lone profile always keeps
    its source so it can become the base of a solid.
    """
    if obj.type != 'MESH':
        raise ValueError("Active object is not a mesh")
    if abs(distance) < EPSILON:
        raise ValueError("Extrusion distance is too small")
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        if not 0 <= face_index < len(bm.faces):
            raise ValueError("Face no longer exists")
        source = bm.faces[face_index]
        normal = source.normal.normalized().copy()
        if not copy and _is_movable_boundary_face(source):
            bmesh.ops.translate(bm, verts=list(source.verts), vec=normal * distance)
            for face in bm.faces:
                face.select = False
            source.select = True
            bm.normal_update()
            bm.to_mesh(obj.data)
            obj.data.update()
            for polygon in obj.data.polygons:
                polygon.select = polygon.index == face_index
            return face_index

        # A lone profile needs its original face as the solid's base. On an
        # existing solid, however, keeping the source would create an internal
        # duplicate face after an outward or recessed extrusion.
        keep_original = copy or any(len(edge.link_faces) == 1 for edge in source.edges)
        source_verts = set(source.verts)
        result = bmesh.ops.extrude_face_region(
            bm,
            geom=[source, *source.edges, *source.verts],
            use_keep_orig=keep_original,
            use_select_history=True,
        )
        new_verts = [item for item in result['geom'] if isinstance(item, bmesh.types.BMVert) and item not in source_verts]
        if not new_verts:
            raise ValueError("Blender could not create the extruded region")
        bmesh.ops.translate(bm, verts=new_verts, vec=normal * distance)
        new_vert_set = set(new_verts)
        new_faces = [
            item for item in result['geom']
            if isinstance(item, bmesh.types.BMFace) and set(item.verts).issubset(new_vert_set)
        ]
        if not new_faces:
            raise ValueError("Blender could not identify the new extrusion face")
        new_face = new_faces[0]
        for face in bm.faces:
            face.select = False
        new_face.select = True
        bm.normal_update()
        bm.faces.index_update()
        new_index = new_face.index
        bm.to_mesh(obj.data)
        obj.data.update()
        for polygon in obj.data.polygons:
            polygon.select = polygon.index == new_index
        return new_index
    finally:
        bm.free()
