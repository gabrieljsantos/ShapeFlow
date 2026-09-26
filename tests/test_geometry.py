"""Run with: blender --background --factory-startup --python tests/test_geometry.py"""
import os
import sys
import unittest

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shapeflow.mesh.creation import create_rectangle_object
from shapeflow.mesh.extrusion import extrude_face
from shapeflow.mesh.splitting import split_face_between_edges
from shapeflow.utils.geometry import parse_coordinate_pair, snap_scalar, typed_length_to_blender_units


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

    def test_grid_snap(self):
        self.assertAlmostEqual(snap_scalar(0.00137, 0.001), 0.001)
        self.assertAlmostEqual(snap_scalar(0.00162, 0.001), 0.002)

    def test_coordinate_pair(self):
        self.assertEqual(parse_coordinate_pair("10.37;12"), (10.37, 12.0))
        self.assertEqual(parse_coordinate_pair("10,37;12"), (10.37, 12.0))


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ShapeFlowGeometryTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
