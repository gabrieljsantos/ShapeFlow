"""Native object transform helpers shared by ShapeFlow tools."""
from mathutils import Matrix, Vector


EPSILON = 1.0e-8


def object_world_center(obj):
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return sum(corners, Vector()) / len(corners)


def object_world_size(obj, axis='MAX'):
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    dimensions = Vector(tuple(
        max(point[index] for point in corners) - min(point[index] for point in corners)
        for index in range(3)
    ))
    if axis == 'MAX':
        return max(dimensions)
    return dimensions['XYZ'.index(axis)]


def rotation_matrix_about_pivot(angle, axis, pivot):
    axis = Vector(axis).normalized()
    if axis.length_squared < EPSILON:
        raise ValueError("Rotation axis is invalid")
    pivot = Vector(pivot)
    return Matrix.Translation(pivot) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-pivot)


def scale_matrix_about_pivot(factor, pivot):
    if abs(factor) < EPSILON:
        raise ValueError("Scale factor is too small")
    pivot = Vector(pivot)
    scale = Matrix.Diagonal((factor, factor, factor, 1.0))
    return Matrix.Translation(pivot) @ scale @ Matrix.Translation(-pivot)


def rotate_object(obj, angle, axis, pivot=None):
    pivot = object_world_center(obj) if pivot is None else Vector(pivot)
    obj.matrix_world = rotation_matrix_about_pivot(angle, axis, pivot) @ obj.matrix_world
    return obj


def scale_object(obj, factor, pivot=None):
    pivot = object_world_center(obj) if pivot is None else Vector(pivot)
    obj.matrix_world = scale_matrix_about_pivot(factor, pivot) @ obj.matrix_world
    return obj


def scale_factor_for_target_size(obj, target_size, axis='MAX'):
    current = object_world_size(obj, axis)
    if current < EPSILON:
        raise ValueError("The selected object has no measurable size on this axis")
    if target_size <= EPSILON:
        raise ValueError("Target size must be greater than zero")
    return target_size / current
