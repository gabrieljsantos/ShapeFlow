import bpy
from mathutils import Vector

from ..mesh.creation import create_profile_object
from ..utils.geometry import plane_axes, regular_polygon_points
from ..utils.picking import ray_plane, viewport_mouse
from ..utils.snapping import collect_plane_geometry, collect_scene_snap_geometry, snap_draw_point, travel_3d_cursor
from ..utils.viewport import ViewportPreviewMixin, draw_polyline


class SHAPEFLOW_OT_polygon_settings(bpy.types.Operator):
    bl_idname = "shapeflow.polygon_settings"
    bl_label = "Polygon"
    bl_description = "Polygon: choose the side count, then create consecutive polygons"

    sides: bpy.props.IntProperty(name="Sides", default=5, min=3, max=256)

    def invoke(self, context, _event):
        self.sides = context.scene.shapeflow.polygon_sides
        return context.window_manager.invoke_props_popup(self, _event)

    def execute(self, context):
        context.scene.shapeflow.polygon_sides = self.sides
        if context.window_manager.shapeflow_active_tool != 'POLYGON':
            context.window_manager.shapeflow_active_tool = 'POLYGON'
            bpy.ops.shapeflow.draw_polygon('INVOKE_DEFAULT')
        return {'FINISHED'}


class SHAPEFLOW_OT_draw_polygon(ViewportPreviewMixin, bpy.types.Operator):
    bl_idname = "shapeflow.draw_polygon"
    bl_label = "Draw Polygon"
    bl_description = "Create regular polygons continuously"
    bl_options = {'REGISTER', 'BLOCKING'}

    _start = None
    _current = None

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'VIEW_3D' and context.window_manager.shapeflow_mode

    def invoke(self, context, _event):
        context.window_manager.shapeflow_active_tool = 'POLYGON'
        self._reset(context)
        self.add_preview(context)
        context.window_manager.modal_handler_add(self)
        self._set_status(context)
        return {'RUNNING_MODAL'}

    def _reset(self, context):
        self._start = None
        self._current = Vector(context.scene.shapeflow.drawing_origin)
        self._snap_result = None
        self._last_mouse = None
        self._travel_axis = None
        self._scene_candidates, self._scene_edges = collect_scene_snap_geometry(context)
        self._candidates, self._edges = collect_plane_geometry(
            context, context.scene.shapeflow.drawing_plane, context.scene.shapeflow.drawing_origin
        )

    def _set_status(self, context):
        sides = context.scene.shapeflow.polygon_sides
        mode = "center/radius" if context.scene.shapeflow.creation_origin == 'CENTER' else "across"
        context.workspace.status_text_set(
            f"ShapeFlow Polygon: {sides} sides • {mode} • click two points • Esc stops"
        )

    def _mouse_point(self, context, event):
        viewport = viewport_mouse(context, event)
        if viewport is None:
            return None
        settings = context.scene.shapeflow
        if self._start is None:
            point, _kind, axis = travel_3d_cursor(
                context, viewport[0], viewport[1], self._last_mouse, self._current,
                settings, self._scene_candidates, self._scene_edges, bypass=event.shift,
            )
            self._last_mouse = viewport[1]
            self._current = point; self._travel_axis = axis; settings.drawing_origin = point
            return point
        _u, _v, normal = plane_axes(settings.drawing_plane)
        raw = ray_plane(context, viewport[1], self._start, normal)
        if raw is None:
            return None
        self._snap_result = snap_draw_point(
            context, viewport[0], raw, settings.drawing_plane, settings,
            self._candidates, self._edges, bypass=event.shift,
        )
        return self._snap_result.point

    def modal(self, context, event):
        window_manager = context.window_manager
        if not window_manager.shapeflow_mode or window_manager.shapeflow_active_tool != 'POLYGON':
            self._finish(context)
            return {'CANCELLED'}
        if event.type == 'ESC':
            window_manager.shapeflow_active_tool = 'NONE'
            self._finish(context)
            return {'CANCELLED'}
        if event.type == 'RIGHTMOUSE':
            self._reset(context)
            return {'RUNNING_MODAL'}
        viewport = viewport_mouse(context, event)
        if viewport and not (0 <= viewport[1][0] <= viewport[0].width and 0 <= viewport[1][1] <= viewport[0].height):
            return {'PASS_THROUGH'}
        if event.type == 'MOUSEMOVE':
            self._current = self._mouse_point(context, event)
            context.area.tag_redraw()
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            point = self._mouse_point(context, event)
            if point is None:
                return {'RUNNING_MODAL'}
            if self._start is None:
                self._start = self._current = point
                self._travel_axis = None
            else:
                settings = context.scene.shapeflow
                try:
                    points = regular_polygon_points(
                        self._start, point, settings.drawing_plane,
                        settings.polygon_sides, settings.creation_origin,
                    )
                    create_profile_object(context, points, f"ShapeFlow {settings.polygon_sides}-gon")
                except ValueError as error:
                    self.report({'WARNING'}, f"ShapeFlow: {error}")
                    return {'RUNNING_MODAL'}
                bpy.ops.ed.undo_push(message="ShapeFlow Polygon")
                self._reset(context)
                self._set_status(context)
        return {'RUNNING_MODAL'}

    def draw_preview(self, context):
        if self._current is None:
            return
        settings = context.scene.shapeflow
        axis_u, axis_v, normal = plane_axes(settings.drawing_plane)
        span = max(0.05, context.space_data.region_3d.view_distance * 0.15)
        colors = ((1, .15, .15, .8), (.15, 1, .15, .8), (.15, .4, 1, .8))
        for axis, color in zip((axis_u, axis_v, normal), colors):
            if self._travel_axis is not None and abs(self._travel_axis.dot(axis)) > 0.9:
                color = (1, .8, .15, 1)
            draw_polyline([self._current - axis * span, self._current + axis * span], color=color)
        if self._start is None:
            return
        try:
            points = regular_polygon_points(
                self._start, self._current, settings.drawing_plane,
                settings.polygon_sides, settings.creation_origin,
            )
        except ValueError:
            return
        draw_polyline(points, color=(0.2, 0.85, 1.0, 1.0), closed=True)

    def _finish(self, context):
        self.remove_preview(context)
        context.workspace.status_text_set(None)
