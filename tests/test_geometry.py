"""Run with: blender --background --factory-startup --python tests/test_geometry.py"""
import os
import sys
import unittest

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shapeflow.mesh.creation import create_polyline_object, create_profile_object, create_rectangle_object
from shapeflow.mesh.extrusion import extrude_face
from shapeflow.mesh.splitting import split_face_between_edges
from shapeflow.utils.geometry import (
    blender_units_to_typed_length,
    arc_points_three,
    bezier_points,
    crescent_points,
    parse_coordinate_pair,
    regular_polygon_points,
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

    def test_extrude_face(self):
        obj = self.rectangle()
        extrude_face(obj, 0, 1.0)
        self.assertEqual(len(obj.data.vertices), 8)
        self.assertEqual(len(obj.data.polygons), 6)

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

    def test_regular_polygon(self):
        points = regular_polygon_points(
            __import__('mathutils').Vector((0, 0, 0)),
            __import__('mathutils').Vector((1, 0, 0)),
            'XY', 5,
        )
        self.assertEqual(len(points), 5)
        self.assertTrue(all(abs(point.length - 1.0) < 1.0e-6 for point in points))

    def test_three_point_arc(self):
        from mathutils import Vector
        start, middle, end = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((-1, 0, 0))
        points = arc_points_three(start, middle, end, 'XY', segments=16)
        self.assertEqual(len(points), 17)
        self.assertLess((points[0] - start).length, 1.0e-6)
        self.assertLess((points[-1] - end).length, 1.0e-6)
        self.assertGreater(max(point.y for point in points), 0.99)

    def test_bezier_curve_and_polyline(self):
        from mathutils import Vector
        start, end = Vector((0, 0, 0)), Vector((1, 0, 0))
        points = bezier_points(start, Vector((0, 1, 0)), Vector((1, 1, 0)), end, segments=8)
        self.assertEqual(points[0], start)
        self.assertEqual(points[-1], end)
        obj = create_polyline_object(bpy.context, points)
        self.assertEqual(len(obj.data.edges), 8)

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

    def test_mode_starts_disabled(self):
        if not hasattr(bpy.types.WindowManager, 'shapeflow_mode'):
            import shapeflow
            shapeflow.register()
            self.addCleanup(shapeflow.unregister)
        self.assertFalse(bpy.context.window_manager.shapeflow_mode)
        self.assertEqual(bpy.context.window_manager.shapeflow_active_tool, 'NONE')


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ShapeFlowGeometryTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
