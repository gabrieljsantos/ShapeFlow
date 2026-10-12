"""Run with: blender --background --factory-startup --python tests/test_geometry.py"""
import os
import sys
import unittest

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shapeflow.mesh.creation import (
    create_bezier_curve_object, create_box_object, create_guide_curve, create_nurbs_curve_object,
    create_pen_curve_object, create_poly_curve_object, create_polyline_object, create_profile_object,
    create_rectangle_object,
)
from shapeflow.mesh.bevel import bevel_edge
from shapeflow.mesh.boolean import add_boolean_modifier
from shapeflow.mesh.dimensions import create_angular_dimension, create_linear_dimension
from shapeflow.mesh.curve_edit import extend_curve, trim_curve
from shapeflow.mesh.inspection import inspect_solid
from shapeflow.mesh.extrusion import extrude_face
from shapeflow.mesh.offset import inset_face
from shapeflow.mesh.organization import combine_objects, create_linked_instance, group_objects, make_instance_unique
from shapeflow.mesh.repetition import add_linear_array, add_mirror_modifier, create_radial_series
from shapeflow.mesh.sweep import apply_follow_me
from shapeflow.mesh.solid_tools import split_solid, trim_solid
from shapeflow.mesh.transforms import (
    object_world_size, rotate_object, scale_factor_for_target_size, scale_object,
)
from shapeflow.mesh.splitting import split_face_between_edges
from shapeflow.tool_catalog import TOOLS, TOOLS_BY_ID, active_tool_items
from shapeflow.utils.geometry import (
    accumulate_axis_intent, angle_between_points,
    blender_units_to_typed_length,
    center_arc_points,
    arc_points_three,
    bezier_points,
    crescent_points,
    crescent_two_arcs_points,
    circle_from_diameter_points,
    ellipse_from_axis_height,
    ellipse_from_foci_points,
    ellipse_points,
    parse_coordinate_pair,
    plane_from_axes,
    regular_polygon_points,
    regular_polygon_edge_points,
    recognize_stroke,
    rotated_rectangle_points,
    smooth_stroke_points,
    snap_scalar,
    typed_length_to_blender_units,
)


class ShapeFlowGeometryTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.object.mode_set(mode='OBJECT') if bpy.context.object and bpy.context.object.mode != 'OBJECT' else None
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)

    def rectangle(self):
        return create_rectangle_object(
            bpy.context,
            [(0, 0, 0), (2, 0, 0), (2, 1, 0), (0, 1, 0)],
        )

    def test_create_rectangle(self):
        obj = self.rectangle()
        self.assertEqual(len(obj.data.vertices), 4)
        self.assertEqual(len(obj.data.polygons), 1)

    def test_create_three_point_box_geometry(self):
        obj = create_box_object(
            bpy.context,
            [(0, 0, 0), (2, 0, 0), (2, 3, 0), (0, 3, 0)],
            (0, 0, 4),
        )
        self.assertEqual(len(obj.data.vertices), 8)
        self.assertEqual(len(obj.data.edges), 12)
        self.assertEqual(len(obj.data.polygons), 6)

    def test_extrude_face(self):
        obj = self.rectangle()
        extrude_face(obj, 0, 1.0)
        self.assertEqual(len(obj.data.vertices), 8)
        self.assertEqual(len(obj.data.polygons), 6)

    def test_inset_face_uses_native_mesh_geometry(self):
        obj = self.rectangle()
        inset_face(obj, 0, 0.2)
        self.assertEqual(obj.type, 'MESH')
        self.assertGreater(len(obj.data.vertices), 4)
        self.assertGreater(len(obj.data.polygons), 1)

    def test_native_edge_chamfer_and_fillet(self):
        bpy.ops.mesh.primitive_cube_add(size=2.0)
        chamfered = bpy.context.object
        bevel_edge(chamfered, 0, 0.1, segments=1)
        self.assertGreater(len(chamfered.data.polygons), 6)
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(4, 0, 0))
        filleted = bpy.context.object
        bevel_edge(filleted, 0, 0.1, segments=4)
        self.assertGreater(len(filleted.data.polygons), len(chamfered.data.polygons))

    def test_native_rotate_and_scale_with_target_size(self):
        from math import pi
        from mathutils import Vector
        obj = self.rectangle()
        original_center = sum((obj.matrix_world @ Vector(corner) for corner in obj.bound_box), Vector()) / 8
        rotate_object(obj, pi * 0.5, Vector((0, 0, 1)))
        rotated_center = sum((obj.matrix_world @ Vector(corner) for corner in obj.bound_box), Vector()) / 8
        self.assertLess((rotated_center - original_center).length, 1.0e-6)
        factor = scale_factor_for_target_size(obj, 4.0, 'MAX')
        scale_object(obj, factor)
        self.assertAlmostEqual(object_world_size(obj, 'MAX'), 4.0)

    def test_rotation_about_selected_geometry_pivot(self):
        from math import pi
        from mathutils import Vector
        obj = self.rectangle()
        pivot = Vector((0, 0, 0))
        rotate_object(obj, pi * 0.5, Vector((0, 0, 1)), pivot)
        transformed = obj.matrix_world @ obj.data.vertices[1].co
        self.assertLess((transformed - Vector((0, 2, 0))).length, 1.0e-6)

    def test_native_boolean_modifier_is_non_destructive(self):
        bpy.ops.mesh.primitive_cube_add(size=2.0)
        target = bpy.context.object
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(1, 0, 0))
        operand = bpy.context.object
        original_vertices = len(target.data.vertices)
        modifier = add_boolean_modifier(target, operand, 'DIFFERENCE')
        self.assertEqual(modifier.type, 'BOOLEAN')
        self.assertEqual(modifier.operation, 'DIFFERENCE')
        self.assertEqual(modifier.object, operand)
        self.assertEqual(len(target.data.vertices), original_vertices)

    def test_native_solid_trim_and_complementary_split(self):
        bpy.ops.mesh.primitive_cube_add(size=2.0)
        target = bpy.context.object
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(1, 0, 0))
        cutter = bpy.context.object
        trim = trim_solid(target, cutter)
        self.assertEqual(trim.operation, 'DIFFERENCE')
        target.modifiers.remove(trim)
        left, center, right = split_solid(bpy.context, target, cutter)
        self.assertIs(left.data, center.data)
        self.assertIs(right.data, cutter.data)
        self.assertEqual(left.modifiers[-1].operation, 'DIFFERENCE')
        self.assertEqual(center.modifiers[-1].operation, 'INTERSECT')
        self.assertEqual(right.modifiers[-1].operation, 'DIFFERENCE')
        self.assertEqual(left["shapeflow_solid_operation"], 'SPLIT_LEFT')
        self.assertEqual(center["shapeflow_solid_operation"], 'SPLIT_CENTER')
        self.assertEqual(right["shapeflow_solid_operation"], 'SPLIT_RIGHT')

    def test_solid_inspector_finds_closed_and_open_meshes(self):
        bpy.ops.mesh.primitive_cube_add(size=2.0)
        cube = bpy.context.object
        closed = inspect_solid(cube)
        self.assertTrue(closed['closed'])
        self.assertTrue(closed['valid'])
        self.assertEqual(closed['boundary_edges'], [])
        plane = self.rectangle()
        opened = inspect_solid(plane)
        self.assertFalse(opened['closed'])
        self.assertEqual(len(opened['boundary_edges']), 4)
        self.assertEqual(len(opened['non_manifold_edges']), 4)

    def test_native_groups_and_linked_components(self):
        first = self.rectangle()
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(3, 0, 0))
        second = bpy.context.object
        group = group_objects(bpy.context, (first, second))
        self.assertEqual(first.parent, group)
        self.assertEqual(second.parent, group)
        instance = create_linked_instance(bpy.context, first, (6, 0, 0))
        self.assertIs(instance.data, first.data)
        make_instance_unique(instance)
        self.assertIsNot(instance.data, first.data)

    def test_combine_meshes_and_curves_into_disconnected_mesh_object(self):
        first = self.rectangle()
        curve = create_poly_curve_object(bpy.context, [(3, 0, 0), (4, 0, 0)], "Combine curve")
        combined = combine_objects(bpy.context, (first, curve))
        self.assertEqual(combined.type, 'MESH')
        self.assertEqual(len(combined.data.vertices), 6)
        self.assertEqual(len(combined.data.polygons), 1)
        self.assertFalse(first.select_get())
        self.assertFalse(curve.select_get())
        self.assertTrue(combined.select_get())

    def test_native_linear_radial_series_and_mirror(self):
        from mathutils import Vector
        obj = self.rectangle()
        array = add_linear_array(obj, 4, 2.5, 'Y')
        self.assertEqual(array.type, 'ARRAY')
        self.assertEqual(array.count, 4)
        self.assertEqual(tuple(array.constant_offset_displace), (0.0, 2.5, 0.0))
        mirror = add_mirror_modifier(obj, 'X')
        self.assertEqual(mirror.type, 'MIRROR')
        self.assertEqual(tuple(mirror.use_axis), (True, False, False))
        instances = create_radial_series(bpy.context, obj, 4, 90.0, 'Z', Vector((0, 0, 0)))
        self.assertEqual(len(instances), 3)
        self.assertTrue(all(instance.data is obj.data for instance in instances))
        self.assertLess((instances[0].location - Vector((0, 0, 0))).length, 1.0e-6)

    def test_negative_push_moves_existing_cube_face(self):
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 0))
        obj = bpy.context.object
        top = max(obj.data.polygons, key=lambda polygon: polygon.normal.z)
        extrude_face(obj, top.index, -0.5)
        self.assertEqual(len(obj.data.vertices), 8)
        self.assertEqual(len(obj.data.polygons), 6)
        self.assertAlmostEqual(max(vertex.co.z for vertex in obj.data.vertices), 0.5)
        self.assertAlmostEqual(min(vertex.co.z for vertex in obj.data.vertices), -1.0)

    def test_positive_pull_moves_existing_cube_face_without_copy(self):
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 0))
        obj = bpy.context.object
        top = max(obj.data.polygons, key=lambda polygon: polygon.normal.z)
        extrude_face(obj, top.index, 0.5)
        self.assertEqual(len(obj.data.vertices), 8)
        self.assertEqual(len(obj.data.polygons), 6)
        self.assertAlmostEqual(max(vertex.co.z for vertex in obj.data.vertices), 1.5)

    def test_copy_extrusion_preserves_source_face(self):
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 0))
        obj = bpy.context.object
        top = max(obj.data.polygons, key=lambda polygon: polygon.normal.z)
        extrude_face(obj, top.index, 0.5, copy=True)
        self.assertEqual(len(obj.data.vertices), 12)
        self.assertEqual(len(obj.data.polygons), 11)
        self.assertAlmostEqual(max(vertex.co.z for vertex in obj.data.vertices), 1.5)

    def test_split_face(self):
        obj = self.rectangle()
        split_face_between_edges(obj, 0, 0, 0.5, 2, 0.5)
        self.assertEqual(len(obj.data.polygons), 2)

    def test_extrude_after_split(self):
        obj = self.rectangle()
        split_face_between_edges(obj, 0, 0, 0.5, 2, 0.5)
        extrude_face(obj, 0, 0.5)
        self.assertGreaterEqual(len(obj.data.polygons), 6)

    def test_millimeter_input_conversion(self):
        self.assertAlmostEqual(typed_length_to_blender_units(1.5, 'MILLIMETERS'), 0.0015)
        self.assertAlmostEqual(typed_length_to_blender_units(1.5, 'MILLIMETERS', 0.001), 1.5)
        self.assertAlmostEqual(blender_units_to_typed_length(0.0015, 'MILLIMETERS'), 1.5)

    def test_grid_snap(self):
        self.assertAlmostEqual(snap_scalar(0.00137, 0.001), 0.001)
        self.assertAlmostEqual(snap_scalar(0.00162, 0.001), 0.002)

    def test_cursor_increment_requires_axis_travel(self):
        from types import SimpleNamespace
        from shapeflow.utils.snapping import cursor_increment_enabled
        settings = SimpleNamespace(axis_cursor=True, grid_snap=True)
        self.assertTrue(cursor_increment_enabled(settings))
        settings.axis_cursor = False
        self.assertFalse(cursor_increment_enabled(settings))
        settings.axis_cursor = True
        self.assertFalse(cursor_increment_enabled(settings, bypass=True))

    def test_regular_polygon(self):
        points = regular_polygon_points(
            __import__('mathutils').Vector((0, 0, 0)),
            __import__('mathutils').Vector((1, 0, 0)),
            'XY', 5,
        )
        self.assertEqual(len(points), 5)
        self.assertTrue(all(abs(point.length - 1.0) < 1.0e-6 for point in points))

    def test_regular_polygon_edge_uses_apothem(self):
        from math import cos, pi
        from mathutils import Vector
        points = regular_polygon_edge_points(Vector((0, 0, 0)), Vector((2, 0, 0)), 'XY', 6)
        self.assertEqual(len(points), 6)
        self.assertAlmostEqual(((points[0] + points[1]) * 0.5).x, 2.0)
        self.assertAlmostEqual(max(point.length for point in points), 2.0 / cos(pi / 6))

    def test_ellipse_by_foci_axis_and_circle_diameter(self):
        from mathutils import Vector
        first, second, on_curve = Vector((-2, 0, 0)), Vector((2, 0, 0)), Vector((0, 3, 0))
        ellipse = ellipse_from_foci_points(first, second, on_curve, 'XY', segments=32)
        self.assertEqual(len(ellipse), 32)
        distances = [(point - first).length + (point - second).length for point in ellipse]
        self.assertTrue(all(abs(value - distances[0]) < 1.0e-5 for value in distances))
        axis = ellipse_from_axis_height(Vector((-3, 0, 0)), Vector((3, 0, 0)), Vector((0, 2, 0)), 'XY', segments=32)
        self.assertAlmostEqual(max(point.x for point in axis), 3.0)
        self.assertAlmostEqual(max(point.y for point in axis), 2.0)
        circle = circle_from_diameter_points(Vector((-2, 0, 0)), Vector((2, 0, 0)), 'XY', segments=32)
        self.assertTrue(all(abs(point.length - 2.0) < 1.0e-6 for point in circle))

    def test_crescent_uses_chord_and_midpoint_bulge_to_form_two_arcs(self):
        from mathutils import Vector
        profile = crescent_two_arcs_points(
            Vector((-2, 0, 0)), Vector((2, 0, 0)), Vector((0, 2, 0)), 'XY',
        )
        self.assertEqual(len(profile), 64)
        self.assertLess((profile[0] - Vector((-2, 0, 0))).length, 1.0e-6)
        self.assertLess((profile[32] - Vector((2, 0, 0))).length, 1.0e-5)
        self.assertGreater(max(point.y for point in profile), 1.0)
        self.assertLess(min(point.y for point in profile), 1.0)

    def test_oriented_ellipse_and_circle(self):
        from mathutils import Vector
        center = Vector((0, 0, 0))
        ellipse = ellipse_points(
            center, Vector((2, 0, 0)), Vector((0, 1, 0)), 'XY', segments=32,
        )
        self.assertEqual(len(ellipse), 32)
        self.assertAlmostEqual(max(point.x for point in ellipse), 2.0)
        self.assertAlmostEqual(max(point.y for point in ellipse), 1.0)
        circle = ellipse_points(
            center, Vector((2, 0, 0)), Vector((0, 0.5, 0)), 'XY',
            proportional=True, segments=32,
        )
        self.assertTrue(all(abs(point.length - 2.0) < 1.0e-6 for point in circle))

    def test_three_point_arc(self):
        from mathutils import Vector
        start, middle, end = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((-1, 0, 0))
        points = arc_points_three(start, middle, end, 'XY', segments=16)
        self.assertEqual(len(points), 17)
        self.assertLess((points[0] - start).length, 1.0e-6)
        self.assertLess((points[-1] - end).length, 1.0e-6)
        self.assertGreater(max(point.y for point in points), 0.99)

    def test_center_arc(self):
        from mathutils import Vector
        points = center_arc_points(
            Vector((0, 0, 0)), Vector((1, 0, 0)), Vector((0, 1, 0)),
            'XY', segments=16,
        )
        self.assertEqual(len(points), 17)
        self.assertLess((points[0] - Vector((1, 0, 0))).length, 1.0e-6)
        self.assertLess((points[-1] - Vector((0, 1, 0))).length, 1.0e-6)
        self.assertTrue(all(abs(point.length - 1.0) < 1.0e-6 for point in points))

    def test_protractor_angle_between_three_points(self):
        from math import pi
        from mathutils import Vector
        angle = angle_between_points(
            Vector((0, 0, 0)), Vector((1, 0, 0)), Vector((0, 1, 0)),
        )
        self.assertAlmostEqual(angle, pi * 0.5)
        with self.assertRaises(ValueError):
            angle_between_points(Vector(), Vector(), Vector((1, 0, 0)))

    def test_bezier_curve_and_polyline(self):
        from mathutils import Vector
        start, end = Vector((0, 0, 0)), Vector((1, 0, 0))
        points = bezier_points(start, Vector((0, 1, 0)), Vector((1, 1, 0)), end, segments=8)
        self.assertEqual(points[0], start)
        self.assertEqual(points[-1], end)
        obj = create_polyline_object(bpy.context, points)
        self.assertEqual(len(obj.data.edges), 8)

    def test_native_poly_curve(self):
        from mathutils import Vector
        obj = create_poly_curve_object(
            bpy.context,
            (Vector((0, 0, 0)), Vector((1, 0, 0)), Vector((1, 1, 0))),
        )
        self.assertEqual(obj.type, 'CURVE')
        self.assertEqual(len(obj.data.splines), 1)
        self.assertEqual(obj.data.splines[0].type, 'POLY')
        self.assertEqual(len(obj.data.splines[0].points), 3)

    def test_native_poly_curve_trim_and_extend(self):
        from mathutils import Vector
        subject = create_poly_curve_object(
            bpy.context, (Vector((-2, 0, 0)), Vector((2, 0, 0))), "Trim Subject",
        )
        cutter = create_poly_curve_object(
            bpy.context, (Vector((0, -1, 0)), Vector((0, 1, 0))), "Boundary",
        )
        trim_curve(subject, cutter, 'END')
        trimmed = [subject.matrix_world @ Vector(point.co[:3]) for point in subject.data.splines[0].points]
        self.assertLess((trimmed[-1] - Vector((0, 0, 0))).length, 1.0e-6)
        extension = create_poly_curve_object(
            bpy.context, (Vector((-2, 0, 0)), Vector((-1, 0, 0))), "Extend Subject",
        )
        extend_curve(extension, cutter, 'END')
        extended = [extension.matrix_world @ Vector(point.co[:3]) for point in extension.data.splines[0].points]
        self.assertLess((extended[-1] - Vector((0, 0, 0))).length, 1.0e-6)

    def test_native_nurbs_bspline(self):
        from mathutils import Vector
        obj = create_nurbs_curve_object(
            bpy.context,
            (Vector((0, 0, 0)), Vector((1, 1, 0)), Vector((2, -1, 0)), Vector((3, 0, 0))),
        )
        spline = obj.data.splines[0]
        self.assertEqual(obj.type, 'CURVE')
        self.assertEqual(spline.type, 'NURBS')
        self.assertEqual(len(spline.points), 4)
        self.assertEqual(spline.order_u, 4)
        self.assertTrue(spline.use_endpoint_u)

    def test_native_bezier_and_pen_curves(self):
        from mathutils import Vector
        bezier = create_bezier_curve_object(
            bpy.context, Vector((0, 0, 0)), Vector((0, 1, 0)),
            Vector((2, 0, 0)), Vector((2, 1, 0)),
        )
        spline = bezier.data.splines[0]
        self.assertEqual(spline.type, 'BEZIER')
        self.assertEqual(len(spline.bezier_points), 2)
        self.assertEqual(spline.bezier_points[0].handle_right, Vector((0, 1, 0)))
        pen = create_pen_curve_object(
            bpy.context,
            (Vector((0, 0, 0)), Vector((1, 1, 0)), Vector((2, 0, 0))),
        )
        pen_points = pen.data.splines[0].bezier_points
        self.assertEqual(len(pen_points), 3)
        self.assertTrue(all(point.handle_left_type == 'AUTO' for point in pen_points))

    def test_live_stroke_smoothing_preserves_endpoints(self):
        from mathutils import Vector
        source = (Vector((0, 0, 0)), Vector((1, 1, 0)), Vector((2, 0, 0)))
        smooth = smooth_stroke_points(source, iterations=2)
        self.assertEqual(smooth[0], source[0])
        self.assertEqual(smooth[-1], source[-1])
        self.assertGreater(len(smooth), len(source))

    def test_smart_stroke_recognizes_line_circle_and_curve(self):
        from math import cos, pi, sin
        from mathutils import Vector
        kind, _data = recognize_stroke((Vector((0, 0, 0)), Vector((1, 0.01, 0)), Vector((2, 0, 0))))
        self.assertEqual(kind, 'LINE')
        circle = [Vector((cos(2*pi*i/16), sin(2*pi*i/16), 0)) for i in range(17)]
        kind, data = recognize_stroke(circle)
        self.assertEqual(kind, 'CIRCLE')
        self.assertAlmostEqual(data[1], 1.0, places=2)
        kind, _data = recognize_stroke((Vector((0, 0, 0)), Vector((1, 2, 0)), Vector((2, 0, 0))))
        self.assertEqual(kind, 'SMOOTH')

    def test_rotated_rectangle_is_orthogonal(self):
        from mathutils import Vector
        points = rotated_rectangle_points(
            Vector((0, 0, 0)), Vector((1, 1, 0)), Vector((0, 2, 0)), 'XY',
        )
        self.assertEqual(len(points), 4)
        width = points[1] - points[0]
        height = points[2] - points[1]
        self.assertAlmostEqual(width.dot(height), 0.0, places=6)
        self.assertGreater(abs(height.length), 0.0)

    def test_native_non_rendering_guide_curve(self):
        from mathutils import Vector
        guide = create_guide_curve(
            bpy.context, Vector((0, 0, 0)), Vector((3, 4, 0)),
        )
        self.assertEqual(guide.type, 'CURVE')
        self.assertTrue(guide.hide_render)
        self.assertTrue(guide.show_in_front)
        self.assertTrue(guide["shapeflow_guide"])
        self.assertAlmostEqual(guide["shapeflow_length"], 5.0)

    def test_native_linear_and_angular_dimensions(self):
        from math import pi
        from mathutils import Vector
        linear = create_linear_dimension(
            bpy.context, Vector((0, 0, 0)), Vector((1, 0, 0)), 'METERS',
        )
        self.assertEqual(linear["shapeflow_dimension"], 'LINEAR')
        self.assertAlmostEqual(linear["shapeflow_value"], 1.0)
        self.assertEqual(len(linear.children), 2)
        angular = create_angular_dimension(
            bpy.context, Vector(), Vector((1, 0, 0)), Vector((0, 1, 0)), 'XY',
        )
        self.assertEqual(angular["shapeflow_dimension"], 'ANGULAR')
        self.assertAlmostEqual(angular["shapeflow_value"], pi * 0.5)

    def test_native_follow_me_curve_sweep(self):
        from mathutils import Vector
        path = create_poly_curve_object(
            bpy.context, (Vector((0, 0, 0)), Vector((0, 0, 2))), "Sweep Path",
        )
        profile = create_profile_object(
            bpy.context,
            (Vector((-0.5, -0.5, 0)), Vector((0.5, -0.5, 0)),
             Vector((0.5, 0.5, 0)), Vector((-0.5, 0.5, 0))),
            "Sweep Profile",
        )
        result = apply_follow_me(bpy.context, path, profile)
        self.assertIs(result, path)
        self.assertEqual(path.data.bevel_mode, 'OBJECT')
        self.assertEqual(path.data.bevel_object.type, 'CURVE')
        self.assertTrue(path.data.use_fill_caps)
        self.assertTrue(path["shapeflow_follow_me"])
        evaluated = path.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        try:
            self.assertGreater(len(mesh.vertices), 0)
            self.assertGreater(len(mesh.polygons), 0)
        finally:
            evaluated.to_mesh_clear()

    def test_crescent_profile_supports_more_than_four_vertices(self):
        from mathutils import Vector
        points = crescent_points(Vector((0, 0, 0)), Vector((1, 0, 0)), Vector((0.25, 0, 0)), 'XY', segments=12)
        obj = create_profile_object(bpy.context, points, "ShapeFlow Crescent Test")
        self.assertEqual(len(obj.data.vertices), len(points))
        self.assertEqual(len(obj.data.polygons), 1)

    def test_profile_can_be_created_on_offset_plane(self):
        from mathutils import Vector
        from shapeflow.utils.geometry import rectangle_corners
        points = rectangle_corners(Vector((0, 0, 0.007)), Vector((0.01, 0.02, 0.007)), 'XY')
        self.assertTrue(all(abs(point.z - 0.007) < 1.0e-9 for point in points))

    def test_cube_exposes_full_3d_move_snap_geometry(self):
        from shapeflow.utils.snapping import collect_object_snap_geometry
        bpy.ops.mesh.primitive_cube_add(size=2.0)
        candidates, edges = collect_object_snap_geometry(bpy.context.object)
        self.assertEqual(len(edges), 12)
        self.assertEqual(sum(candidate.kind == 'VERTEX' for candidate in candidates), 8)
        self.assertEqual(sum(candidate.kind == 'MIDPOINT' for candidate in candidates), 12)
        self.assertEqual(sum(candidate.kind == 'FACE_CENTER' for candidate in candidates), 6)

    def test_move_snap_priority(self):
        from shapeflow.utils.snapping import SNAP_PRIORITY
        self.assertLess(SNAP_PRIORITY['VERTEX'], SNAP_PRIORITY['MIDPOINT'])
        self.assertLess(SNAP_PRIORITY['MIDPOINT'], SNAP_PRIORITY['EDGE'])
        self.assertLess(SNAP_PRIORITY['EDGE'], SNAP_PRIORITY['FACE_CENTER'])

    def test_coordinate_pair(self):
        self.assertEqual(parse_coordinate_pair("10.37;12"), (10.37, 12.0))
        self.assertEqual(parse_coordinate_pair("10,37;12"), (10.37, 12.0))

    def test_automatic_plane_from_two_axes(self):
        self.assertEqual(plane_from_axes('X', 'Y'), 'XY')
        self.assertEqual(plane_from_axes('Z', 'X'), 'XZ')
        self.assertEqual(plane_from_axes('Y', 'Z'), 'YZ')
        self.assertIsNone(plane_from_axes('X', 'X'))

    def test_automatic_axis_requires_continuous_pixel_gesture(self):
        candidate, pixels, accepted = accumulate_axis_intent(None, 0, 'X', 7, 18)
        self.assertEqual((candidate, pixels, accepted), ('X', 7.0, False))
        candidate, pixels, accepted = accumulate_axis_intent(candidate, pixels, 'X', 11, 18)
        self.assertTrue(accepted)
        candidate, pixels, accepted = accumulate_axis_intent(candidate, pixels, 'Z', 2, 18)
        self.assertEqual((candidate, pixels, accepted), ('Z', 2.0, False))

    def test_mode_starts_disabled(self):
        if not hasattr(bpy.types.WindowManager, 'shapeflow_mode'):
            import shapeflow
            shapeflow.register()
            self.addCleanup(shapeflow.unregister)
        self.assertFalse(bpy.context.window_manager.shapeflow_mode)
        self.assertEqual(bpy.context.window_manager.shapeflow_active_tool, 'NONE')
        self.assertTrue(bpy.context.scene.shapeflow.axis_cursor)
        self.assertTrue(bpy.context.scene.shapeflow.grid_snap)
        self.assertTrue(bpy.context.scene.shapeflow.geometry_snap)
        self.assertTrue(bpy.context.scene.shapeflow.smart_guides)
        self.assertEqual(bpy.context.scene.shapeflow.scale_input_mode, 'FACTOR')
        self.assertEqual(bpy.context.scene.shapeflow.scale_axis, 'MAX')
        self.assertEqual(bpy.context.scene.shapeflow.scale_target_size, 1000.0)
        self.assertEqual(bpy.context.scene.shapeflow.auto_axis_threshold, 18)
        plane_items = bpy.context.scene.shapeflow.bl_rna.properties['drawing_plane'].enum_items
        self.assertIn('AUTO', {item.identifier for item in plane_items})

    def test_tool_catalog_has_unique_complete_identifiers(self):
        identifiers = [tool.identifier for tool in TOOLS]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(set(identifiers), set(TOOLS_BY_ID))
        self.assertEqual(
            {'NONE', *identifiers},
            {identifier for identifier, _label, _description in active_tool_items()},
        )

    def test_toolbar_groups_cover_every_interactive_toolbar_tool_once(self):
        from shapeflow.operators.workspace import TOOLBAR_TOOL_IDS
        from shapeflow.ui.workspace_tools import TOOL_GROUPS, TOOLBAR_ICONS, TOOLS
        grouped = tuple(
            identifier
            for _group_name, identifiers in TOOL_GROUPS
            for identifier in identifiers
        )
        self.assertEqual(set(grouped), set(TOOLBAR_TOOL_IDS))
        self.assertEqual(len(grouped), len(set(grouped)))
        self.assertEqual(set(TOOLBAR_ICONS), set(TOOLBAR_TOOL_IDS))
        self.assertEqual(len(TOOLS), len(TOOLBAR_TOOL_IDS))


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ShapeFlowGeometryTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
