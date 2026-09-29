import bmesh
from mathutils import Vector


EPSILON = 1.0e-5


def _point_on_edge(edge, factor):
    factor = max(0.0, min(1.0, factor))
    if factor <= EPSILON:
        return edge.verts[0]
    if factor >= 1.0 - EPSILON:
        return edge.verts[1]
    # bmesh.utils.edge_split uses a factor measured from the supplied vertex.
    _, vertex = bmesh.utils.edge_split(edge, edge.verts[0], factor)
    return vertex


def split_face_between_edges(obj, face_index, edge_a_index, factor_a, edge_b_index, factor_b):
    """Split a face by connecting two locations on distinct boundary edges."""
    if edge_a_index == edge_b_index:
        raise ValueError("Choose two different edges of the face")
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        if not 0 <= face_index < len(bm.faces):
            raise ValueError("Face no longer exists")
        face = bm.faces[face_index]
        boundary = {edge.index for edge in face.edges}
        if edge_a_index not in boundary or edge_b_index not in boundary:
            raise ValueError("Both cut points must be on the selected face boundary")
        edge_a = bm.edges[edge_a_index]
        edge_b = bm.edges[edge_b_index]
        vertex_a = _point_on_edge(edge_a, factor_a)
        # Edge indices can change after a split, but the object reference is stable.
        vertex_b = _point_on_edge(edge_b, factor_b)
        if vertex_a == vertex_b or (vertex_a.co - vertex_b.co).length < EPSILON:
            raise ValueError("Cut points are too close together")
        result = bmesh.ops.connect_vert_pair(bm, verts=[vertex_a, vertex_b], faces_exclude=[])
        if not result.get('edges'):
            raise ValueError("The selected points cannot form a valid split")
        for item in bm.faces:
            item.select = False
        new_faces = [item for item in vertex_a.link_faces if vertex_b in item.verts]
        for item in new_faces:
            item.select = True
        bm.normal_update()
        bm.to_mesh(obj.data)
        obj.data.update()
        return len(new_faces)
    finally:
        bm.free()


def split_face_with_path(obj, face_index, points, edge_a_index, factor_a, edge_b_index, factor_b):
    """Split one polygon using an open polyline whose endpoints lie on its boundary."""
    if len(points) < 2:
        raise ValueError("An embedded path needs at least two points")
    if edge_a_index == edge_b_index:
        raise ValueError("Embedded path endpoints must touch two different face edges")
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
        if not 0 <= face_index < len(bm.faces):
            raise ValueError("Receiver face no longer exists")
        face = bm.faces[face_index]
        boundary = {edge.index for edge in face.edges}
        if edge_a_index not in boundary or edge_b_index not in boundary:
            raise ValueError("Both path endpoints must lie on the receiver boundary")
        edge_a, edge_b = bm.edges[edge_a_index], bm.edges[edge_b_index]
        vertex_a = _point_on_edge(edge_a, factor_a)
        vertex_b = _point_on_edge(edge_b, factor_b)
        loop = list(face.verts)
        ia, ib = loop.index(vertex_a), loop.index(vertex_b)

        def arc(start, end):
            result = [loop[start]]
            while start != end:
                start = (start + 1) % len(loop)
                result.append(loop[start])
            return result

        inverse = obj.matrix_world.inverted()
        interior = [bm.verts.new(inverse @ Vector(point)) for point in points[1:-1]]
        side_a = arc(ia, ib) + list(reversed(interior))
        side_b = arc(ib, ia) + interior
        bm.faces.remove(face)
        new_faces = [bm.faces.new(side_a), bm.faces.new(side_b)]
        for item in bm.faces:
            item.select = False
        for item in new_faces:
            item.select = True
        bm.normal_update(); bm.to_mesh(obj.data); obj.data.update()
        return len(new_faces)
    finally:
        bm.free()
