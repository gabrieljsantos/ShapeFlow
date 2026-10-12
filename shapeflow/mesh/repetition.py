"""Native Blender repetition helpers used by ShapeFlow organization tools."""
from math import radians

from mathutils import Matrix, Vector


AXIS_INDEX = {'X': 0, 'Y': 1, 'Z': 2}


def add_linear_array(obj, count, spacing, axis='X'):
    """Add a non-destructive native Array modifier with constant spacing."""
    if obj.type != 'MESH':
        raise ValueError("Linear series requires an active mesh object")
    if count < 2:
        raise ValueError("Copy count must be at least 2")
    if axis not in AXIS_INDEX:
        raise ValueError("Array axis must be X, Y, or Z")
    modifier = obj.modifiers.new(name="ShapeFlow Copy Series", type='ARRAY')
    modifier.count = count
    modifier.use_relative_offset = False
    modifier.use_constant_offset = True
    offset = [0.0, 0.0, 0.0]
    offset[AXIS_INDEX[axis]] = spacing
    modifier.constant_offset_displace = offset
    return modifier


def create_radial_series(context, source, count, angle, axis='Z', pivot=None):
    """Create native linked object instances around a pivot."""
    if source.data is None:
        raise ValueError("Active object has no reusable data")
    if count < 2:
        raise ValueError("Copy count must be at least 2")
    if axis not in AXIS_INDEX:
        raise ValueError("Rotation axis must be X, Y, or Z")
    pivot = Vector(source.location if pivot is None else pivot)
    direction = Vector((axis == 'X', axis == 'Y', axis == 'Z'))
    collection = source.users_collection[0] if source.users_collection else context.collection
    instances = []
    for index in range(1, count):
        rotation = Matrix.Translation(pivot) @ Matrix.Rotation(
            radians(angle * index), 4, direction,
        ) @ Matrix.Translation(-pivot)
        instance = source.copy()
        instance.data = source.data
        collection.objects.link(instance)
        instance.matrix_world = rotation @ source.matrix_world
        instances.append(instance)
    return instances


def add_mirror_modifier(obj, axis='X'):
    """Add a non-destructive native Mirror modifier around the object origin."""
    if obj.type != 'MESH':
        raise ValueError("Mirror requires an active mesh object")
    if axis not in AXIS_INDEX:
        raise ValueError("Mirror axis must be X, Y, or Z")
    modifier = obj.modifiers.new(name="ShapeFlow Mirror", type='MIRROR')
    modifier.use_axis = tuple(index == AXIS_INDEX[axis] for index in range(3))
    modifier.use_clip = True
    modifier.use_mirror_merge = True
    return modifier
