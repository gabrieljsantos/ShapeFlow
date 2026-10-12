"""Non-destructive native Blender Boolean helpers."""


OPERATIONS = {'UNION', 'DIFFERENCE', 'INTERSECT'}


def add_boolean_modifier(target, operand, operation):
    if target is None or operand is None or target == operand:
        raise ValueError("Select a target and a different operand object")
    if target.type != 'MESH' or operand.type != 'MESH':
        raise ValueError("Boolean operations require two mesh objects")
    if operation not in OPERATIONS:
        raise ValueError("Unsupported Boolean operation")
    modifier = target.modifiers.new(
        name=f"ShapeFlow {operation.title()}", type='BOOLEAN',
    )
    modifier.operation = operation
    modifier.solver = 'EXACT'
    modifier.object = operand
    return modifier
