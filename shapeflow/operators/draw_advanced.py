import bpy
from mathutils import Vector

from ..mesh.creation import create_polyline_object, create_profile_object
from ..utils.geometry import arc_points_three, bezier_points, crescent_points, plane_axes
from ..utils.picking import ray_plane, viewport_mouse
from ..utils.snapping import collect_plane_geometry, collect_scene_snap_geometry, snap_draw_point, travel_3d_cursor
from ..utils.viewport import ViewportPreviewMixin, draw_polyline, draw_snap_circle


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
        self._last_mouse = None
        self._travel_axis = None
        self._scene_candidates, self._scene_edges = collect_scene_snap_geometry(context)
        self._plane_candidates, self._plane_edges = collect_plane_geometry(
            context, context.scene.shapeflow.drawing_plane, context.scene.shapeflow.drawing_origin
        )

    def _set_status(self, context):
        label, count, help_text = TOOL_DATA[self.tool]
        context.workspace.status_text_set(
            f"ShapeFlow {label}: {help_text} • point {len(self._fixed)+1}/{count} • right-click resets • Esc stops"
        )

    def _mouse_point(self, context, event):
        viewport = viewport_mouse(context, event)
        if not viewport:
            return None
        region, mouse = viewport
        settings = context.scene.shapeflow
        if not self._fixed:
            point, _kind, axis = travel_3d_cursor(
                context, region, mouse, self._last_mouse, self._current, settings,
                self._scene_candidates, self._scene_edges, bypass=event.shift,
            )
            self._last_mouse = mouse
            self._travel_axis = axis
            settings.drawing_origin = point
            return point
        _u, _v, normal = plane_axes(settings.drawing_plane)
        raw = ray_plane(context, mouse, self._fixed[0], normal)
        if raw is None:
            return None
        return snap_draw_point(
            context, region, raw, settings.drawing_plane, settings,
            self._plane_candidates, self._plane_edges, bypass=event.shift,
        ).point

    def modal(self, context, event):
        wm = context.window_manager
        if not wm.shapeflow_mode or wm.shapeflow_active_tool != self.tool:
            self._finish(context); return {'CANCELLED'}
        if event.type == 'ESC':
            wm.shapeflow_active_tool = 'NONE'; self._finish(context); return {'CANCELLED'}
        if event.type == 'RIGHTMOUSE':
            self._reset(context); self._set_status(context); return {'RUNNING_MODAL'}
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
        plane = context.scene.shapeflow.drawing_plane
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
        plane = context.scene.shapeflow.drawing_plane
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
        if not self._fixed:
            axis_u, axis_v, normal = plane_axes(context.scene.shapeflow.drawing_plane)
            span = max(0.05, context.space_data.region_3d.view_distance * 0.15)
            for axis, color in ((axis_u, (1,.15,.15,.8)), (axis_v, (.15,1,.15,.8)), (normal, (.15,.4,1,.8))):
                if self._travel_axis is not None and abs(self._travel_axis.dot(axis)) > .9:
                    color = (1,.8,.15,1)
                draw_polyline([self._current-axis*span, self._current+axis*span], color=color)
            return
        preview = self._preview_points(context)
        if len(preview) >= 2:
            draw_polyline(preview, color=(.15,.85,1,1), closed=self.tool == 'CRESCENT' and len(self._fixed) >= 2)
        for point in self._fixed:
            draw_snap_circle(context, point, radius=5.0)
        if self.tool == 'BEZIER' and len(self._fixed) >= 2:
            draw_polyline(self._fixed[:2], color=(1,.6,.15,.9))
        if self.tool == 'BEZIER' and len(self._fixed) >= 3:
            draw_polyline([self._fixed[2], self._current], color=(1,.6,.15,.9))

    def _finish(self, context):
        self.remove_preview(context)
        context.workspace.status_text_set(None)
