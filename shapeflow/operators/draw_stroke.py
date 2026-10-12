import bpy
from mathutils import Vector

from .drawing_base import PlanarDrawingMixin
from ..mesh.creation import create_pen_curve_object, create_poly_curve_object
from ..utils.geometry import ellipse_points, plane_axes, recognize_stroke, smooth_stroke_points
from ..utils.picking import ray_plane, viewport_mouse
from ..utils.snapping import snap_draw_point
from ..utils.viewport import draw_polyline, draw_snap_circle


class SHAPEFLOW_OT_draw_stroke(PlanarDrawingMixin, bpy.types.Operator):
    bl_idname = "shapeflow.draw_stroke"
    bl_label = "Draw Stroke"
    bl_options = {'REGISTER', 'BLOCKING'}

    mode: bpy.props.EnumProperty(items=(
        ('FREEHAND', "Freehand", "Capture the pointer as a native Poly Curve"),
        ('LIVE_SKETCH', "Live Sketch", "Smooth the captured stroke into a native Bezier Curve"),
        ('SMART_DRAW', "Smart Drawing", "Recognize a line or circle, otherwise create a smooth Bezier Curve"),
    ))

    @classmethod
    def description(cls, _context, properties):
        descriptions = {
            'FREEHAND': "Click and drag a freehand native curve",
            'LIVE_SKETCH': "Click and drag a smoothed live Bezier sketch",
            'SMART_DRAW': "Click and drag; recognize a line or circle automatically",
        }
        return descriptions.get(properties.mode, "Draw a native stroke")

    def invoke(self, context, _event):
        return self._start_planar_modal(context, self.mode)

    def _reset(self, context):
        self._points = []
        self._drawing = False
        self._last_sample_mouse = None
        self._initialize_planar_cursor(context)
        if context.scene.shapeflow.drawing_plane == 'AUTO':
            self._auto_plane = 'XY'
            self._refresh_plane_geometry(context)

    def _set_status(self, context):
        label = {'FREEHAND': "Freehand", 'LIVE_SKETCH': "Live Sketch", 'SMART_DRAW': "Smart Drawing"}[self.mode]
        context.workspace.status_text_set(
            f"ShapeFlow {label}: click and drag • release to create • Esc exits • Alt temporarily free"
        )

    def _mouse_point(self, context, event):
        viewport = viewport_mouse(context, event)
        if not viewport:
            return None
        region, mouse = viewport
        settings = context.scene.shapeflow
        plane = self._effective_plane(settings) or 'XY'
        _u, _v, normal = plane_axes(plane)
        origin = self._points[0] if self._points else Vector(settings.drawing_origin)
        raw = ray_plane(context, mouse, origin, normal)
        if raw is None:
            return None
        snap = snap_draw_point(
            context, region, raw, plane, settings, self._candidates, self._edges,
            bypass=event.alt, magnetic_bypass=event.alt, origin=origin,
        )
        self._snap_result = snap
        return snap.point

    def _commit(self, context):
        if len(self._points) < 2:
            return
        if self.mode == 'SMART_DRAW':
            kind, data = recognize_stroke(self._points)
            if kind == 'LINE':
                create_poly_curve_object(context, data, "ShapeFlow Smart Line")
            elif kind == 'CIRCLE':
                center, radius = data
                plane = self._effective_plane(context.scene.shapeflow) or 'XY'
                axis_u, _axis_v, _normal = plane_axes(plane)
                points = ellipse_points(center, center + axis_u * radius, center, plane, proportional=True)
                create_poly_curve_object(context, points, "ShapeFlow Smart Circle", cyclic=True)
            else:
                create_pen_curve_object(
                    context, smooth_stroke_points(self._points, context.scene.shapeflow.live_smoothing),
                    "ShapeFlow Smart Curve",
                )
        elif self.mode == 'LIVE_SKETCH':
            points = smooth_stroke_points(
                self._points, context.scene.shapeflow.live_smoothing,
            )
            create_pen_curve_object(context, points, "ShapeFlow Live Sketch")
        else:
            create_poly_curve_object(context, self._points, "ShapeFlow Freehand")
        bpy.ops.ed.undo_push(message=f"ShapeFlow {self.mode.title()}")

    def modal(self, context, event):
        wm = context.window_manager
        if not wm.shapeflow_mode or wm.shapeflow_active_tool != self.mode:
            self._finish(context); return {'CANCELLED'}
        if event.type == 'ESC':
            wm.shapeflow_active_tool = 'NONE'; self._finish(context); return {'CANCELLED'}
        if self._pointer_outside_viewport(context, event):
            return {'PASS_THROUGH'}
        viewport = viewport_mouse(context, event)
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            point = self._mouse_point(context, event)
            if point is not None:
                self._points = [point.copy()]
                self._drawing = True
                self._last_sample_mouse = Vector(viewport[1]) if viewport else None
            return {'RUNNING_MODAL'}
        if event.type == 'MOUSEMOVE':
            point = self._mouse_point(context, event)
            if point is not None:
                self._current = point
                if self._drawing and viewport:
                    mouse = Vector(viewport[1])
                    if self._last_sample_mouse is None or (mouse - self._last_sample_mouse).length >= context.scene.shapeflow.stroke_spacing:
                        if not self._points or (point - self._points[-1]).length > 1.0e-6:
                            self._points.append(point.copy())
                            self._last_sample_mouse = mouse
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self._drawing:
            self._commit(context)
            self._reset(context)
            self._set_status(context)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        return {'RUNNING_MODAL'}

    def draw_preview(self, context):
        points = self._points + ([self._current] if self._drawing and self._current is not None else [])
        if len(points) >= 2:
            preview = smooth_stroke_points(points, 1) if self.mode in {'LIVE_SKETCH', 'SMART_DRAW'} else points
            draw_polyline(preview, color=(0.15, 0.85, 1.0, 1.0), width=2.5)
        if self._current is not None:
            draw_snap_circle(context, self._current, radius=4.0)
