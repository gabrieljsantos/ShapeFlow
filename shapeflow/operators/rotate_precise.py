from math import atan2, degrees, radians

import bpy
from mathutils import Vector
from bpy_extras import view3d_utils

from .drawing_base import PlanarDrawingMixin
from ..mesh.transforms import object_world_center, rotate_object, rotation_matrix_about_pivot
from ..utils.geometry import plane_axes
from ..utils.picking import ray_plane, viewport_mouse
from ..utils.snapping import collect_plane_geometry, snap_draw_point
from ..utils.viewport import draw_polyline, draw_snap_circle, draw_text


BOX_EDGES = ((0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7))


class SHAPEFLOW_OT_rotate_precise(PlanarDrawingMixin, bpy.types.Operator):
    bl_idname = "shapeflow.rotate_precise"
    bl_label = "Rotate from Pivot"
    bl_description = "Choose a snapped pivot, reference direction, and final direction on the active plane"
    bl_options = {'REGISTER', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return super().poll(context) and context.active_object is not None

    def invoke(self, context, _event):
        self._object = context.active_object
        self._original_matrix = self._object.matrix_world.copy()
        self._corners = tuple(self._original_matrix @ Vector(corner) for corner in self._object.bound_box)
        return self._start_planar_modal(context, 'ROTATE')

    def _reset(self, context):
        settings = context.scene.shapeflow
        self._fixed = [object_world_center(self._object)] if settings.rotation_pivot_mode == 'CENTER' else []
        self._numeric = ""
        self._angle = 0.0
        self._preview_corners = self._corners
        self._initialize_planar_cursor(context)
        if context.scene.shapeflow.drawing_plane == 'AUTO':
            self._auto_plane = 'XY'
            self._refresh_plane_geometry(context)
        if settings.rotation_pivot_mode == 'CENTER':
            self._refresh_plane_geometry(context, self._fixed[0])

    def _set_status(self, context):
        settings = context.scene.shapeflow
        stages = (
            ("choose pivot", "choose reference direction", "choose final direction")
            if settings.rotation_pivot_mode == 'PICKED'
            else ("object center", "choose reference direction", "choose final direction")
        )
        snap = f"increment {settings.rotation_increment:g}°" if settings.rotation_increment_enabled else "free angle"
        context.workspace.status_text_set(
            f"ShapeFlow Rotate: {stages[min(len(self._fixed), 2)]} • {snap} • Alt temporarily free • W captures face"
        )

    def _mouse_point(self, context, event):
        viewport = viewport_mouse(context, event)
        if not viewport:
            return None
        region, mouse = viewport
        settings = context.scene.shapeflow
        plane = self._effective_plane(settings) or 'XY'
        normal = plane_axes(plane)[2]
        origin = self._fixed[0] if self._fixed else Vector(settings.drawing_origin)
        raw = ray_plane(context, mouse, origin, normal)
        if raw is None:
            return None
        self._snap_result = snap_draw_point(
            context, region, raw, plane, settings, self._candidates, self._edges,
            bypass=event.alt, magnetic_bypass=event.alt, skip=self._snap_skip, origin=origin,
        )
        return self._snap_result.point

    def _signed_angle(self, context, target):
        pivot, reference = self._fixed[:2]
        normal = plane_axes(self._effective_plane(context.scene.shapeflow) or 'XY')[2]
        first, second = reference - pivot, target - pivot
        if first.length < 1.0e-6 or second.length < 1.0e-6:
            return 0.0
        return atan2(normal.dot(first.cross(second)), first.dot(second))

    def _update_angle(self, context, target, bypass=False):
        angle = self._signed_angle(context, target)
        settings = context.scene.shapeflow
        if settings.rotation_increment_enabled and not bypass:
            step = radians(settings.rotation_increment)
            angle = round(angle / step) * step
        self._angle = angle
        matrix = rotation_matrix_about_pivot(
            angle, plane_axes(self._effective_plane(settings) or 'XY')[2], self._fixed[0],
        )
        self._preview_corners = tuple(matrix @ corner for corner in self._corners)

    def _confirm(self, context):
        if self._numeric:
            self._angle = radians(float(self._numeric))
        rotate_object(
            self._object, self._angle,
            plane_axes(self._effective_plane(context.scene.shapeflow) or 'XY')[2], self._fixed[0],
        )
        bpy.ops.ed.undo_push(message="ShapeFlow Rotate")
        self._original_matrix = self._object.matrix_world.copy()
        self._corners = tuple(self._original_matrix @ Vector(corner) for corner in self._object.bound_box)
        self._reset(context)
        self._set_status(context)

    def modal(self, context, event):
        wm = context.window_manager
        if not wm.shapeflow_mode or wm.shapeflow_active_tool != 'ROTATE':
            self._finish(context); return {'CANCELLED'}
        if event.type == 'ESC':
            wm.shapeflow_active_tool = 'NONE'; self._finish(context); return {'CANCELLED'}
        if event.type == 'RIGHTMOUSE':
            self._reset(context); self._set_status(context); return {'RUNNING_MODAL'}
        handled = self._capture_workplane_event(context, event)
        if handled: return handled
        handled = self._cycle_snap_event(context, event)
        if handled: return handled
        if self._pointer_outside_viewport(context, event): return {'PASS_THROUGH'}
        if len(self._fixed) >= 2 and event.ascii and (event.ascii.isdigit() or event.ascii in '.,-'):
            self._numeric += '.' if event.ascii == ',' else event.ascii
            try:
                self._angle = radians(float(self._numeric))
                matrix = rotation_matrix_about_pivot(
                    self._angle, plane_axes(self._effective_plane(context.scene.shapeflow) or 'XY')[2], self._fixed[0],
                )
                self._preview_corners = tuple(matrix @ corner for corner in self._corners)
            except ValueError: pass
            context.area.tag_redraw(); return {'RUNNING_MODAL'}
        if len(self._fixed) >= 2 and event.type in {'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            self._confirm(context); return {'RUNNING_MODAL'}
        if event.type == 'MOUSEMOVE':
            point = self._mouse_point(context, event)
            if point is not None:
                self._current = point
                if len(self._fixed) >= 2 and not self._numeric: self._update_angle(context, point, event.alt)
            context.area.tag_redraw()
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            point = self._mouse_point(context, event)
            if point is None: return {'RUNNING_MODAL'}
            self._fixed.append(point.copy())
            if len(self._fixed) == 1 and context.scene.shapeflow.rotation_pivot_mode == 'PICKED':
                self._candidates, self._edges = collect_plane_geometry(
                    context, self._effective_plane(context.scene.shapeflow) or 'XY', point,
                )
            elif len(self._fixed) == 3:
                self._update_angle(context, point, event.alt)
                self._confirm(context); return {'RUNNING_MODAL'}
            self._set_status(context)
        return {'RUNNING_MODAL'}

    def draw_preview(self, context):
        for first, second in BOX_EDGES:
            draw_polyline((self._preview_corners[first], self._preview_corners[second]), color=(1.0,.55,.1,1.0), width=2.5)
        points = self._fixed + ([self._current] if self._current is not None else [])
        if len(points) >= 2: draw_polyline((points[0], points[1]), color=(.2,.75,1,1), width=2)
        if len(points) >= 3: draw_polyline((points[0], points[-1]), color=(1,.75,.1,1), width=2)
        for point in self._fixed: draw_snap_circle(context, point, radius=5)

    def draw_hud(self, context):
        if len(self._fixed) < 2 or self._current is None: return
        region = next((item for item in context.area.regions if item.type == 'WINDOW'), context.region)
        screen = view3d_utils.location_3d_to_region_2d(region, context.space_data.region_3d, self._fixed[0])
        if screen is not None: draw_text(screen + Vector((14,14)), self._numeric or f"{degrees(self._angle):.2f}°", size=15)
