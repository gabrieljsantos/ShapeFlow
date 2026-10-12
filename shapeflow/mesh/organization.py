"""Native Blender grouping and linked-component helpers."""
from mathutils import Vector


def combine_objects(context, objects, name="Combined"):
    """Combine selected mesh and curve objects into one mesh object.

    Curves are converted to mesh data in temporary duplicates so the source
    objects remain untouched. Disconnected mesh islands stay disconnected.
    """
    import bpy

    objects = tuple(obj for obj in objects if obj is not None)
    if len(objects) < 2:
        raise ValueError("Select at least two mesh or curve objects to combine")
    unsupported = [obj for obj in objects if obj.type not in {'MESH', 'CURVE'}]
    if unsupported:
        raise ValueError("Combine supports mesh and curve objects")

    depsgraph = context.evaluated_depsgraph_get()
    combined_mesh = bpy.data.meshes.new(name)
    combined = bpy.data.objects.new(name, combined_mesh)
    context.collection.objects.link(combined)

    # Join coordinates in world space, then keep the combined object's origin
    # at the centroid of source origins for a predictable transform pivot.
    center = sum((obj.matrix_world.translation for obj in objects), Vector()) / len(objects)
    combined.location = center
    vertices, edges, faces = [], [], []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        temp_mesh = evaluated.to_mesh()
        try:
            offset = len(vertices)
            matrix = combined.matrix_world.inverted() @ obj.matrix_world
            vertices.extend(matrix @ vertex.co for vertex in temp_mesh.vertices)
            edges.extend(tuple(index + offset for index in edge.vertices) for edge in temp_mesh.edges)
            faces.extend(tuple(index + offset for index in polygon.vertices) for polygon in temp_mesh.polygons)
        finally:
            evaluated.to_mesh_clear()
    combined_mesh.from_pydata(vertices, edges, faces)
    combined_mesh.update()

    for obj in objects:
        obj.select_set(False)
    combined.select_set(True)
    context.view_layer.objects.active = combined
    return combined


def separate_object(context, obj):
    """Split a combined mesh into objects by disconnected mesh islands."""
    import bpy
    import bmesh

    if obj is None or obj.type != 'MESH':
        raise ValueError("Select one combined mesh object to separate")
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        # Walk connected vertices so faces, edges, and loose vertices all split.
        unseen = set(bm.verts)
        groups = []
        while unseen:
            seed = unseen.pop()
            group = {seed}
            stack = [seed]
            while stack:
                vertex = stack.pop()
                for edge in vertex.link_edges:
                    other = edge.other_vert(vertex)
                    if other in unseen:
                        unseen.remove(other)
                        group.add(other)
                        stack.append(other)
            groups.append(group)
        if len(groups) < 2:
            raise ValueError("The selected mesh has no disconnected parts to separate")

        created = []
        base_name = obj.name
        bm.verts.ensure_lookup_table()
        component_indices = [{vert.index for vert in group} for group in groups]
        for index, indices in enumerate(component_indices):
            part = bmesh.new()
            part.from_mesh(obj.data)
            keep = [vertex for vertex in part.verts if vertex.index in indices]
            bmesh.ops.delete(part, geom=[vertex for vertex in part.verts if vertex not in keep], context='VERTS')
            if index == 0:
                part.to_mesh(obj.data)
                part.free()
                obj.data.update()
                obj.name = f"{base_name} Part 1"
                created.append(obj)
                continue
            mesh = bpy.data.meshes.new(f"{base_name} Part {index + 1}")
            part.to_mesh(mesh)
            part.free()
            new_obj = bpy.data.objects.new(f"{base_name} Part {index + 1}", mesh)
            (obj.users_collection[0] if obj.users_collection else context.collection).objects.link(new_obj)
            new_obj.matrix_world = obj.matrix_world.copy()
            created.append(new_obj)
        for selected in context.selected_objects:
            selected.select_set(False)
        obj.select_set(True)
        for part_obj in created:
            part_obj.select_set(True)
        context.view_layer.objects.active = obj
        return tuple(created)
    finally:
        bm.free()


def group_objects(context, objects, name="ShapeFlow Group"):
    objects = tuple(obj for obj in objects if obj is not None)
    if not objects:
        raise ValueError("Select at least one object to group")
    empty = __import__('bpy').data.objects.new(name, None)
    empty.empty_display_type = 'PLAIN_AXES'
    context.collection.objects.link(empty)
    center = sum((obj.matrix_world.translation for obj in objects), Vector()) / len(objects)
    empty.location = center
    for obj in objects:
        world = obj.matrix_world.copy()
        obj.parent = empty
        obj.matrix_world = world
        obj.select_set(False)
    empty.select_set(True)
    context.view_layer.objects.active = empty
    return empty


def create_linked_instance(context, source, location=None):
    if source is None or source.data is None:
        raise ValueError("Select an object with linkable data")
    instance = source.copy()
    instance.data = source.data
    collection = source.users_collection[0] if source.users_collection else context.collection
    collection.objects.link(instance)
    if location is not None:
        instance.location = Vector(location)
    for selected in context.selected_objects:
        selected.select_set(False)
    instance.select_set(True)
    context.view_layer.objects.active = instance
    return instance


def make_instance_unique(obj):
    if obj is None or obj.data is None:
        raise ValueError("Select an object with data to make unique")
    obj.data = obj.data.copy()
    return obj
