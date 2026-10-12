"""Native non-destructive solid trimming and splitting."""
from .boolean import add_boolean_modifier


def trim_solid(target, cutter):
    """Trim target using a native exact Difference modifier."""
    modifier = add_boolean_modifier(target, cutter, 'DIFFERENCE')
    modifier.name = "ShapeFlow Subtraction"
    target["shapeflow_solid_operation"] = 'DIFFERENCE'
    return modifier


def split_solid(context, target, cutter):
    """Keep left-only, shared, and right-only volume regions separately."""
    if target is None or cutter is None or target == cutter:
        raise ValueError("Select an active target and a different cutter")
    if target.type != 'MESH' or cutter.type != 'MESH':
        raise ValueError("Solid Split requires two mesh objects")
    collection = target.users_collection[0] if target.users_collection else context.collection
    first_only = target
    first_only.name = f"{target.name} Split Left"
    shared = target.copy()
    shared.data = target.data
    collection.objects.link(shared)
    shared.name = f"{target.name} Split Center"
    second_only = cutter.copy()
    second_only.data = cutter.data
    collection.objects.link(second_only)
    second_only.name = f"{cutter.name} Split Right"
    difference = add_boolean_modifier(first_only, cutter, 'DIFFERENCE')
    difference.name = "ShapeFlow Split Left"
    intersection = add_boolean_modifier(shared, cutter, 'INTERSECT')
    intersection.name = "ShapeFlow Split Center"
    remainder = add_boolean_modifier(second_only, target, 'DIFFERENCE')
    remainder.name = "ShapeFlow Split Right"
    first_only["shapeflow_solid_operation"] = 'SPLIT_LEFT'
    shared["shapeflow_solid_operation"] = 'SPLIT_CENTER'
    second_only["shapeflow_solid_operation"] = 'SPLIT_RIGHT'
    for selected in context.selected_objects:
        selected.select_set(False)
    for result in (first_only, shared, second_only):
        result.select_set(True)
    context.view_layer.objects.active = first_only
    return first_only, shared, second_only
