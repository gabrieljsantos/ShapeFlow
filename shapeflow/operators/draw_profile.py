import bpy
from bpy_extras import view3d_utils
from mathutils import Vector

from ..mesh.creation import create_rectangle_object
from ..utils.geometry import (
    parse_coordinate_pair,
    plane_axes,
    point_from_plane_coordinates,
    rectangle_corners,
    typed_length_to_blender_units,
    unit_suffix,
)
from ..utils.picking import ray_plane, viewport_mouse
from ..utils.snapping import (
    collect_plane_geometry,
    collect_scene_snap_geometry,
    snap_draw_point,
    travel_3d_cursor,
)
from ..utils.viewport import ViewportPreviewMixin, draw_polyline, draw_text


class SHAPEFLOW_OT_draw_rectangle(ViewportPreviewMixin, bpy.types.Operator):
    bl_idname = "shapeflow.draw_rectangle"
    bl_label = "Draw Rectangle"
    bl_description = "Draw a rectangular native mesh face"
    bl_options = {'REGISTER', 'BLOCKING'}

    _start = None
    _current = None
    _snap_result = None
    _numeric = ""

    @staticmethod
    def _corners(context, start, end):
        settings = context.scene.shapeflow
        return rectangle_corners(
            start, end, settings.drawing_plane,
            settings.creation_origin, settings.proportional_creation,
        )

    @classmethod
    def poll(cls, context):
        return (
            context.area and context.area.type == 'VIEW_3D'
            and context.window_manager.shapeflow_mode
        )

    def invoke(self, context, event):
        context.window_manager.shapeflow_active_tool = 'RECTANGLE'
        self._reset(context)
        self.add_preview(context)
        context.window_manager.modal_handler_add(self)
        self._set_status(context)
        return {'RUNNING_MODAL'}

    def _reset(self, context):
        self._start = None
        self._current = None
        self._snap_result = None
        self._numeric = ""
        self._current = Vector(context.scene.shapeflow.drawing_origin)
        self._last_mouse = None
        self._travel_axis = None
        self._scene_candidates, self._scene_edges = collect_scene_snap_geometry(context)
        self._candidates, self._edges = collect_plane_geometry(
            context, context.scene.shapeflow.drawing_plane,
            context.scene.shapeflow.drawing_origin,
        )

    def _set_status(self, context):
        plane = context.scene.shapeflow.drawing_plane
        labels = {'XY': 'X;Y', 'XZ': 'X;Z', 'YZ': 'Y;Z'}[plane]
        stage = "origin" if self._start is None else "size"
        context.workspace.status_text_set(
            f"ShapeFlow Draw: click or type {labels} for {stage} • Shift bypasses snap • Esc cancels"
        )

    def _mouse_point(self, context, event):
        viewport = viewport_mouse(context, event)
        if viewport is None:
            return None
        plane = context.scene.shapeflow.drawing_plane
        if self._start is None:
            point, kind, axis = travel_3d_cursor(
                context, viewport[0], viewport[1], self._last_mouse, self._current,
                context.scene.shapeflow, self._scene_candidates, self._scene_edges,
                bypass=event.shift,
            )
            self._last_mouse = viewport[1]
            self._current = point
            self._travel_axis = axis
            context.scene.shapeflow.drawing_origin = point
            self._snap_result = type('TravelSnap', (), {'kind': kind, 'guide_u': None, 'guide_v': None})()
            return point
        _, _, normal = plane_axes(plane)
        raw = ray_plane(context, viewport[1], self._start, normal)
        if raw is None:
            return None
        self._snap_result = snap_draw_point(
            context, viewport[0], raw, plane, context.scene.shapeflow,
            self._candidates, self._edges, bypass=event.shift,
        )
        return self._snap_result.point

    def _numeric_point(self, context):
        first, second = parse_coordinate_pair(self._numeric)
        settings = context.scene.shapeflow
        first = typed_length_to_blender_units(first, settings.length_unit, context.scene.unit_settings.scale_length)
        second = typed_length_to_blender_units(second, settings.length_unit, context.scene.unit_settings.scale_length)
        if self._start is None:
            return point_from_plane_coordinates(first, second, settings.drawing_plane)
        axis_u, axis_v, _normal = plane_axes(settings.drawing_plane)
        if settings.creation_origin == 'CENTER':
            first *= 0.5
            second *= 0.5
        return self._start + axis_u * first + axis_v * second

    def modal(self, context, event):
        if not context.window_manager.shapeflow_mode or context.window_manager.shapeflow_active_tool != 'RECTANGLE':
            self._finish(context)
            return {'CANCELLED'}
        if event.type == 'ESC':
            context.window_manager.shapeflow_active_tool = 'NONE'
            self._finish(context)
            return {'CANCELLED'}
        if event.type == 'RIGHTMOUSE':
            self._reset(context)
            self._set_status(context)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        viewport = viewport_mouse(context, event)
        if viewport and not (0 <= viewport[1][0] <= viewport[0].width and 0 <= viewport[1][1] <= viewport[0].height):
            return {'PASS_THROUGH'}
        if event.type == 'MOUSEMOVE':
            self._current = self._mouse_point(context, event)
            context.area.tag_redraw()
        if event.ascii and (event.ascii.isdigit() or event.ascii in '.,;-'):
            self._numeric += event.ascii
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        if event.type == 'BACK_SPACE' and event.value == 'PRESS':
            self._numeric = self._numeric[:-1]
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        if event.type in {'RET', 'NUMPAD_ENTER'} and self._numeric:
            try:
                point = self._numeric_point(context)
            except ValueError as error:
                self.report({'WARNING'}, f"ShapeFlow: {error}")
                return {'RUNNING_MODAL'}
            self._numeric = ""
            if self._start is None:
                self._start = self._current = point
                self._set_status(context)
                return {'RUNNING_MODAL'}
            try:
                corners = self._corners(context, self._start, point)
                create_rectangle_object(context, corners)
            except ValueError as error:
                self.report({'WARNING'}, f"ShapeFlow: {error}")
                return {'RUNNING_MODAL'}
            bpy.ops.ed.undo_push(message="ShapeFlow Rectangle")
            self._reset(context)
            self._set_status(context)
            return {'RUNNING_MODAL'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            point = self._mouse_point(context, event)
            if point is None:
                self.report({'WARNING'}, "ShapeFlow: the view is parallel to the drawing plane")
                return {'RUNNING_MODAL'}
            if self._start is None:
                self._start = self._current = point
                self._travel_axis = None
                self._numeric = ""
                self._set_status(context)
            else:
                try:
                    corners = self._corners(context, self._start, point)
                    create_rectangle_object(context, corners)
                except ValueError as error:
                    self.report({'WARNING'}, f"ShapeFlow: {error}")
                    return {'RUNNING_MODAL'}
                bpy.ops.ed.undo_push(message="ShapeFlow Rectangle")
                self._reset(context)
                self._set_status(context)
                return {'RUNNING_MODAL'}
        return {'RUNNING_MODAL'}

    def draw_preview(self, context):
        if self._current is not None:
            axis_u, axis_v, normal = plane_axes(context.scene.shapeflow.drawing_plane)
            rv3d = context.space_data.region_3d
            span = max(0.05, rv3d.view_distance * (0.15 if self._start is None else 2.0))
            color_u = (1.0, 0.8, 0.15, 0.9) if self._snap_result and self._snap_result.guide_u else (0.8, 0.12, 0.12, 0.55)
            color_v = (1.0, 0.8, 0.15, 0.9) if self._snap_result and self._snap_result.guide_v else (0.8, 0.12, 0.12, 0.55)
            color_n = (1.0, 0.8, 0.15, 0.95) if self._travel_axis is not None and abs(self._travel_axis.dot(normal)) > 0.9 else (0.15, 0.4, 1.0, 0.8)
            draw_polyline([self._current - axis_u * span, self._current + axis_u * span], color=color_u)
            draw_polyline([self._current - axis_v * span, self._current + axis_v * span], color=color_v)
            draw_polyline([self._current - normal * span, self._current + normal * span], color=color_n)
            if self._snap_result and self._snap_result.guide_u:
                draw_polyline([self._current, self._snap_result.guide_u], color=color_u)
            if self._snap_result and self._snap_result.guide_v:
                draw_polyline([self._current, self._snap_result.guide_v], color=color_v)
        if self._start is not None and self._current is not None:
            draw_polyline(self._corners(context, self._start, self._current), closed=True)

    def draw_hud(self, context):
        if self._current is None:
            return
        region = next((item for item in context.area.regions if item.type == 'WINDOW'), None)
        screen = view3d_utils.location_3d_to_region_2d(region, context.space_data.region_3d, self._current)
        if screen is None:
            return
        settings = context.scene.shapeflow
        scale = context.scene.unit_settings.scale_length or 1.0
        factor = {'MILLIMETERS': 1000.0, 'CENTIMETERS': 100.0, 'METERS': 1.0}[settings.length_unit] * scale
        axes = {'XY': ('X', 'Y'), 'XZ': ('X', 'Z'), 'YZ': ('Y', 'Z')}[settings.drawing_plane]
        values = {'XY': (self._current.x, self._current.y), 'XZ': (self._current.x, self._current.z), 'YZ': (self._current.y, self._current.z)}[settings.drawing_plane]
        suffix = unit_suffix(settings.length_unit)
        snap_kind = self._snap_result.kind.replace('_', ' ').title() if self._snap_result else 'Free'
        text = f"{axes[0]} {values[0] * factor:.4g}; {axes[1]} {values[1] * factor:.4g} {suffix}  [{snap_kind}]"
        if self._numeric:
            text += f"  › {self._numeric}"
        draw_text((screen.x + 16, screen.y + 16), text, color=(1.0, 0.9, 0.75, 1.0))

    def _finish(self, context):
        self.remove_preview(context)
        context.workspace.status_text_set(None)
