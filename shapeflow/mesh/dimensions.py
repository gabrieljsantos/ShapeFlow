"""Editable native Curve/Text dimensions for ShapeFlow."""
from math import degrees

import bpy
from mathutils import Vector

from ..utils.geometry import angle_between_points, blender_units_to_typed_length, center_arc_points


def _curve_object(context, splines, name):
    curve = bpy.data.curves.new(name, type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 1
    for points in splines:
        spline = curve.splines.new(type='POLY')
        spline.points.add(len(points) - 1)
        for control, point in zip(spline.points, points):
            control.co = (*Vector(point), 1.0)
    obj = bpy.data.objects.new(name, curve)
    context.collection.objects.link(obj)
    obj.show_in_front = True
    return obj


def _text_object(context, text, location, name):
    data = bpy.data.curves.new(name, type='FONT')
    data.body = text
    data.align_x = 'CENTER'
    data.align_y = 'CENTER'
    data.size = 0.12
    obj = bpy.data.objects.new(name, data)
    context.collection.objects.link(obj)
    obj.location = location
    obj.show_in_front = True
    return obj


def _dimension_group(context, geometry, label, label_position, kind, value):
    group = bpy.data.objects.new(f"ShapeFlow {kind.title()} Dimension", None)
    group.empty_display_type = 'PLAIN_AXES'
    group.location = label_position
    context.collection.objects.link(group)
    geometry.parent = group
    geometry.matrix_parent_inverse = group.matrix_world.inverted()
    text = _text_object(context, label, label_position, f"ShapeFlow {kind.title()} Label")
    text.parent = group
    text.matrix_parent_inverse = group.matrix_world.inverted()
    group["shapeflow_dimension"] = kind
    group["shapeflow_value"] = value
    for selected in context.selected_objects:
        selected.select_set(False)
    group.select_set(True)
    context.view_layer.objects.active = group
    return group


def create_linear_dimension(context, start, end, unit, scale_length=1.0, kind='LINEAR'):
    start, end = Vector(start), Vector(end)
    distance = (end - start).length
    if distance < 1.0e-6:
        raise ValueError("Dimension points must be different")
    multiplier = 2.0 if kind == 'DIAMETER' else 1.0
    value = blender_units_to_typed_length(distance * multiplier, unit, scale_length)
    prefix = 'R ' if kind == 'RADIUS' else 'Ø ' if kind == 'DIAMETER' else ''
    geometry = _curve_object(context, ((start, end),), f"ShapeFlow {kind.title()} Line")
    return _dimension_group(
        context, geometry, f"{prefix}{value:.4f} {unit.lower()}",
        start.lerp(end, 0.5), kind, value,
    )


def create_angular_dimension(context, center, first, second, plane):
    center, first, second = Vector(center), Vector(first), Vector(second)
    angle = angle_between_points(center, first, second)
    radius = min((first - center).length, (second - center).length) * 0.65
    if radius < 1.0e-6:
        raise ValueError("Angle directions must be different from the center")
    first_arc = center + (first - center).normalized() * radius
    second_arc = center + (second - center).normalized() * radius
    arc = center_arc_points(center, first_arc, second_arc, plane, segments=24)
    geometry = _curve_object(context, ((center, first), (center, second), arc), "ShapeFlow Angular Lines")
    label_position = arc[len(arc) // 2]
    return _dimension_group(
        context, geometry, f"{degrees(angle):.2f}°", label_position,
        'ANGULAR', angle,
    )
