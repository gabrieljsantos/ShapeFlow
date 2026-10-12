"""Native non-destructive solid trimming and splitting."""
from .boolean import add_boolean_modifier


def trim_solid(target, cutter):
    """Trim target using a native exact Difference modifier."""
    modifier = add_boolean_modifier(target, cutter, 'DIFFERENCE')
    modifier.name = "ShapeFlow Solid Trim"
    target["shapeflow_solid_operation"] = 'TRIM'
    return modifier


def split_solid(context, target, cutter):
    """Create complementary Difference and Intersect results non-destructively."""
    if target is None or cutter is None or target == cutter:
        raise ValueError("Select an active target and a different cutter")
    if target.type != 'MESH' or cutter.type != 'MESH':
        raise ValueError("Solid Split requires two mesh objects")
    inside = target.copy()
    inside.data = target.data
    collection = target.users_collection[0] if target.users_collection else context.collection
    collection.objects.link(inside)
    inside.name = f"{target.name} Split Inside"
    outside = target
    outside.name = f"{target.name} Split Outside"
    difference = add_boolean_modifier(outside, cutter, 'DIFFERENCE')
    difference.name = "ShapeFlow Split Outside"
    intersection = add_boolean_modifier(inside, cutter, 'INTERSECT')
    intersection.name = "ShapeFlow Split Inside"
    outside["shapeflow_solid_operation"] = 'SPLIT_OUTSIDE'
    inside["shapeflow_solid_operation"] = 'SPLIT_INSIDE'
    for selected in context.selected_objects:
        selected.select_set(False)
    outside.select_set(True)
    inside.select_set(True)
    context.view_layer.objects.active = outside
    return outside, inside
