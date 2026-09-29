import bpy
from mathutils import Vector

from ..mesh.creation import create_polyline_object, create_profile_object
from ..utils.geometry import (
    accumulate_axis_intent, arc_points_three, axis_name, bezier_points, crescent_points,
    plane_axes, plane_from_axes,
)
from ..utils.picking import ray_plane, viewport_mouse
from ..utils.snapping import collect_plane_geometry, collect_scene_snap_geometry, snap_draw_point, travel_3d_cursor
from ..utils.viewport import (
    ViewportPreviewMixin, draw_nearby_snap_candidates, draw_polyline, draw_snap_circle,
)


TOOL_DATA = {
    'ARC': ("Arc", 3, "three points: start, point on arc, end"),
    'BEZIER': ("Bezier", 4, "four points: start, start handle, end, end handle"),
    'CRESCENT': ("Crescent", 3, "three points: center, radius, inner curvature"),
}


class SHAPEFLOW_OT_draw_advanced(ViewportPreviewMixin, bpy.types.Operator):
    bl_idname = "shapeflow.draw_advanced"
    bl_label = "Draw Advanced Shape"
    bl_options = {'REGISTER', 'BLOCKING'}

    tool: bpy.props.EnumProperty(items=tuple((key, value[0], value[2]) for key, value in TOOL_DATA.items()))

    def _effective_plane(self, settings):
        return self._auto_plane if settings.drawing_plane == 'AUTO' else settings.drawing_plane

    @classmethod
    def description(cls, _context, properties):
        label, _count, help_text = TOOL_DATA.get(properties.tool, ("Shape", 0, ""))
        return f"{label}: {help_text}; remains active until Escape or another tool"

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'VIEW_3D' and context.window_manager.shapeflow_mode

    def invoke(self, context, _event):
        context.window_manager.shapeflow_active_tool = self.tool
        self._reset(context)
        self.add_preview(context)
        context.window_manager.modal_handler_add(self)
        self._set_status(context)
        return {'RUNNING_MODAL'}

    def _reset(self, context):
        self._fixed = []
        self._current = Vector(context.scene.shapeflow.drawing_origin)
        self._travel_origin = self._current.copy()
        self._travel_raw = self._current.copy()
        self._last_mouse = None
        self._travel_axis = None
        self._snap_result = None
        self._snap_skip = 0
        self._auto_plane = None
        self._auto_axes = []
        self._auto_axis_candidate = None
        self._auto_axis_pixels = 0.0
        self._scene_candidates, self._scene_edges = collect_scene_snap_geometry(context)
        plane = self._effective_plane(context.scene.shapeflow)
        if plane:
            self._plane_candidates, self._plane_edges = collect_plane_geometry(
                context, plane, context.scene.shapeflow.drawing_origin
            )
        else:
            self._plane_candidates, self._plane_edges = [], []

    def _set_status(self, context):
        label, count, help_text = TOOL_DATA[self.tool]
        plane = self._effective_plane(context.scene.shapeflow)
        auto = f" • Auto {plane or 'waiting'}" if context.scene.shapeflow.drawing_plane == 'AUTO' else ""
        context.workspace.status_text_set(
            f"ShapeFlow {label}: {help_text} • point {len(self._fixed)+1}/{count}{auto} • Alt bypasses magnetic • Shift free • Tab next target"
        )

    def _mouse_point(self, context, event):
        viewport = viewport_mouse(context, event)
        if not viewport:
            return None
        region, mouse = viewport
        settings = context.scene.shapeflow
        if not self._fixed:
            if self._last_mouse is None:
                self._last_mouse = Vector(mouse)
            point, kind, axis, raw = travel_3d_cursor(
                context, region, mouse, self._last_mouse, self._current, settings,
                self._scene_candidates, self._scene_edges,
                bypass=event.shift, magnetic_bypass=event.alt, skip=self._snap_skip,
                raw_point=self._travel_raw, snap_origin=self._travel_origin,
            )
            self._last_mouse = Vector(mouse)
            self._travel_raw = raw
            self._travel_axis = axis
            self._snap_result = type('TravelSnap', (), {'kind': kind})()
            settings.drawing_origin = point
            return point
        plane = self._effective_plane(settings)
        if settings.drawing_plane == 'AUTO' and plane is None:
            previous_mouse = Vector(self._last_mouse)
            point, kind, axis, raw = travel_3d_cursor(
                context, region, mouse, self._last_mouse, self._current, settings,
                self._scene_candidates, self._scene_edges,
                bypass=event.shift, magnetic_bypass=event.alt, skip=self._snap_skip,
                raw_point=self._travel_raw, snap_origin=self._fixed[0],
            )
            self._last_mouse = Vector(mouse)
            self._travel_raw = raw
            self._travel_axis = axis
            name = axis_name(axis)
            motion = (Vector(mouse) - previous_mouse).length
            self._auto_axis_candidate, self._auto_axis_pixels, accepted = accumulate_axis_intent(
                self._auto_axis_candidate, self._auto_axis_pixels, name, motion,
                settings.auto_axis_threshold,
            )
            if accepted and name not in self._auto_axes:
                self._auto_axes.append(name)
                self._auto_axis_candidate = None
                self._auto_axis_pixels = 0.0
                if len(self._auto_axes) == 2:
                    self._auto_plane = plane_from_axes(*self._auto_axes)
                    self._plane_candidates, self._plane_edges = collect_plane_geometry(
                        context, self._auto_plane, self._fixed[0]
                    )
                    self._set_status(context)
            self._snap_result = type('TravelSnap', (), {'kind': kind})()
            return point
        _u, _v, normal = plane_axes(plane)
        raw = ray_plane(context, mouse, self._fixed[0], normal)
        if raw is None:
            return None
        self._snap_result = snap_draw_point(
            context, region, raw, plane, settings,
            self._plane_candidates, self._plane_edges,
            bypass=event.shift, magnetic_bypass=event.alt, skip=self._snap_skip,
            origin=self._fixed[0],
        )
        return self._snap_result.point

    def modal(self, context, event):
        wm = context.window_manager
        if not wm.shapeflow_mode or wm.shapeflow_active_tool != self.tool:
            self._finish(context); return {'CANCELLED'}
        if event.type == 'ESC':
            wm.shapeflow_active_tool = 'NONE'; self._finish(context); return {'CANCELLED'}
        if event.type == 'RIGHTMOUSE':
            self._reset(context); self._set_status(context); return {'RUNNING_MODAL'}
        if event.type == 'TAB' and event.value == 'PRESS':
            self._snap_skip += 1
            point = self._mouse_point(context, event)
            if point is not None:
                self._current = point
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        viewport = viewport_mouse(context, event)
        if viewport and not (0 <= viewport[1][0] <= viewport[0].width and 0 <= viewport[1][1] <= viewport[0].height):
            return {'PASS_THROUGH'}
        if event.type == 'MOUSEMOVE':
            point = self._mouse_point(context, event)
            if point is not None: self._current = point
            context.area.tag_redraw()
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            point = self._mouse_point(context, event)
            if point is None: return {'RUNNING_MODAL'}
            self._fixed.append(point.copy())
            if len(self._fixed) == 1:
                self._travel_origin = point.copy()
                self._travel_raw = point.copy()
                self._last_mouse = Vector(viewport[1]) if viewport else None
                self._travel_axis = None
                plane = self._effective_plane(context.scene.shapeflow)
                if plane:
                    self._plane_candidates, self._plane_edges = collect_plane_geometry(
                        context, plane, point
                    )
            self._snap_skip = 0
            required = TOOL_DATA[self.tool][1]
            if len(self._fixed) == required:
                try:
                    self._commit(context)
                except ValueError as error:
                    self.report({'WARNING'}, f"ShapeFlow: {error}")
                    self._fixed.pop()
                    return {'RUNNING_MODAL'}
                bpy.ops.ed.undo_push(message=f"ShapeFlow {TOOL_DATA[self.tool][0]}")
                self._reset(context)
            self._set_status(context)
        return {'RUNNING_MODAL'}

    def _commit(self, context):
        plane = self._effective_plane(context.scene.shapeflow)
        if plane is None:
            raise ValueError("Move along two different axes to choose the automatic plane")
        if self.tool == 'ARC':
            create_polyline_object(context, arc_points_three(*self._fixed, plane), "ShapeFlow Arc")
        elif self.tool == 'BEZIER':
            start, start_handle, end, end_handle = self._fixed
            create_polyline_object(
                context, bezier_points(start, start_handle, end_handle, end), "ShapeFlow Bezier"
            )
        else:
            create_profile_object(context, crescent_points(*self._fixed, plane), "ShapeFlow Crescent")

    def _preview_points(self, context):
        points = self._fixed + ([self._current] if self._current is not None else [])
        plane = self._effective_plane(context.scene.shapeflow)
        if plane is None:
            return points
        try:
            if self.tool == 'ARC' and len(points) >= 3:
                return arc_points_three(points[0], points[1], points[2], plane)
            if self.tool == 'BEZIER' and len(points) >= 4:
                return bezier_points(points[0], points[1], points[3], points[2])
            if self.tool == 'CRESCENT' and len(points) >= 3:
                return crescent_points(points[0], points[1], points[2], plane)
        except ValueError:
            pass
        return points

    def draw_preview(self, context):
        settings = context.scene.shapeflow
        if settings.geometry_snap and self._current is not None:
            candidates = self._scene_candidates if not self._fixed else (
                self._plane_candidates or self._scene_candidates
            )
            active = self._current if self._snap_result and self._snap_result.kind in {
                'VERTEX', 'MIDPOINT', 'EDGE', 'FACE_CENTER', 'FACE_POINT'
            } else None
            draw_nearby_snap_candidates(
                context, self._current, candidates,
                screen_radius=max(48.0, settings.snap_distance * 2.5), active=active,
            )
        if not self._fixed:
            plane = self._effective_plane(context.scene.shapeflow)
            axis_u, axis_v, normal = plane_axes(plane) if plane else (
                Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
            )
            span = max(0.05, context.space_data.region_3d.view_distance * 0.15)
            magnetic = self._snap_result and self._snap_result.kind in {
                'VERTEX', 'MIDPOINT', 'EDGE', 'FACE_CENTER', 'FACE_POINT'
            }
            for axis, color in ((axis_u, (1,.15,.15,.8)), (axis_v, (.15,1,.15,.8)), (normal, (.15,.4,1,.8))):
                if self._travel_axis is not None and abs(self._travel_axis.dot(axis)) > .9:
                    color = (1,.8,.15,1)
                elif magnetic:
                    color = (*color[:3], .12)
                draw_polyline([self._current-axis*span, self._current+axis*span], color=color)
            if magnetic:
                draw_snap_circle(context, self._current, radius=6.0,
                                 fill=(.2, 1, .42, .24), outline=(.2, 1, .42, 1))
            return
        if self._effective_plane(context.scene.shapeflow) is None:
            draw_polyline([self._fixed[0], self._current], color=(1.0, 0.8, 0.15, 0.9))
            for point in self._fixed:
                draw_snap_circle(context, point, radius=5.0)
            return
        preview = self._preview_points(context)
        if len(preview) >= 2:
            draw_polyline(preview, color=(.15,.85,1,1), closed=self.tool == 'CRESCENT' and len(self._fixed) >= 2)
        for point in self._fixed:
            draw_snap_circle(context, point, radius=5.0)
        if self._snap_result and self._snap_result.kind in {'VERTEX', 'MIDPOINT', 'EDGE', 'FACE_CENTER', 'FACE_POINT'}:
            draw_snap_circle(context, self._current, radius=6.0,
                             fill=(.2, 1, .42, .24), outline=(.2, 1, .42, 1))
        if self.tool == 'BEZIER' and len(self._fixed) >= 2:
            draw_polyline(self._fixed[:2], color=(1,.6,.15,.9))
        if self.tool == 'BEZIER' and len(self._fixed) >= 3:
            draw_polyline([self._fixed[2], self._current], color=(1,.6,.15,.9))

    def _finish(self, context):
        self.remove_preview(context)
        context.workspace.status_text_set(None)
