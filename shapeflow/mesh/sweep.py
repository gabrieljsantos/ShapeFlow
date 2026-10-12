"""Native Blender Curve sweep helpers for ShapeFlow Follow Me."""
import bpy


def mesh_profile_to_curve(context, obj):
    """Create a native cyclic Curve profile from a mesh polygon."""
    if obj.type != 'MESH' or not obj.data.polygons:
        raise ValueError("The profile must be a Curve or a mesh with a face")
    polygon = obj.data.polygons[0]
    coordinates = [obj.data.vertices[index].co.copy() for index in polygon.vertices]
    if len(coordinates) < 3:
        raise ValueError("The profile needs at least three points")
    curve = bpy.data.curves.new(f"{obj.name} Sweep Profile", type='CURVE')
    curve.dimensions = '2D'
    curve.resolution_u = 1
    spline = curve.splines.new(type='POLY')
    spline.points.add(len(coordinates) - 1)
    for point, coordinate in zip(spline.points, coordinates):
        point.co = (*coordinate, 1.0)
    spline.use_cyclic_u = True
    profile = bpy.data.objects.new(f"{obj.name} Sweep Profile", curve)
    collection = obj.users_collection[0] if obj.users_collection else context.collection
    collection.objects.link(profile)
    profile.matrix_world = obj.matrix_world.copy()
    profile.hide_render = True
    profile.hide_set(True)
    profile["shapeflow_sweep_profile"] = True
    return profile


def apply_follow_me(context, path, profile, fill_caps=True):
    """Use Blender's native Curve bevel-object sweep along a path."""
    if path.type != 'CURVE':
        raise ValueError("The active path must be a native Curve")
    if path is profile:
        raise ValueError("Select a separate profile object")
    bevel_profile = profile if profile.type == 'CURVE' else mesh_profile_to_curve(context, profile)
    if bevel_profile.type != 'CURVE':
        raise ValueError("The profile must be a Curve or mesh face")
    path.data.dimensions = '3D'
    path.data.bevel_mode = 'OBJECT'
    path.data.bevel_object = bevel_profile
    path.data.use_fill_caps = fill_caps
    path["shapeflow_follow_me"] = True
    path["shapeflow_profile"] = bevel_profile.name
    context.view_layer.objects.active = path
    path.select_set(True)
    return path
