import bmesh


EPSILON = 1.0e-6


def extrude_face(obj, face_index, distance):
    """Extrude one face along its local normal and return the new face index."""
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
        source_verts = set(source.verts)
        result = bmesh.ops.extrude_face_region(
            bm,
            geom=[source, *source.edges, *source.verts],
            use_keep_orig=True,
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
