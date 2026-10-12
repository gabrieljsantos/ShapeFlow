"""Read-only native BMesh diagnostics for solid meshes."""
import bmesh


def inspect_solid(obj):
    if obj is None or obj.type != 'MESH':
        raise ValueError("Solid Inspector requires an active mesh object")
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.normal_update()
        boundary_edges = [edge.index for edge in bm.edges if len(edge.link_faces) == 1]
        non_manifold_edges = [edge.index for edge in bm.edges if len(edge.link_faces) != 2]
        loose_edges = [edge.index for edge in bm.edges if not edge.link_faces]
        loose_vertices = [vertex.index for vertex in bm.verts if not vertex.link_edges]
        degenerate_faces = [face.index for face in bm.faces if face.calc_area() <= 1.0e-12]
        signatures = {}
        duplicate_faces = []
        for face in bm.faces:
            signature = tuple(sorted(vertex.index for vertex in face.verts))
            if signature in signatures:
                duplicate_faces.append(face.index)
            else:
                signatures[signature] = face.index
        closed = bool(bm.faces) and not non_manifold_edges
        signed_volume = bm.calc_volume(signed=True) if closed else 0.0
        return {
            'vertices': len(bm.verts),
            'edges': len(bm.edges),
            'faces': len(bm.faces),
            'boundary_edges': boundary_edges,
            'non_manifold_edges': non_manifold_edges,
            'loose_edges': loose_edges,
            'loose_vertices': loose_vertices,
            'degenerate_faces': degenerate_faces,
            'duplicate_faces': duplicate_faces,
            'closed': closed,
            'signed_volume': signed_volume,
            'inverted': closed and signed_volume < 0.0,
            'valid': closed and signed_volume > 0.0 and not (
                loose_edges or loose_vertices or degenerate_faces or duplicate_faces
            ),
        }
    finally:
        bm.free()
