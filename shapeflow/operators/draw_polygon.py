import bpy
from mathutils import Vector

from ..mesh.creation import create_profile_object
from ..utils.geometry import (
    accumulate_axis_intent, axis_name, plane_axes, plane_from_axes,
    regular_polygon_points,
)
from ..utils.picking import ray_plane, viewport_mouse
from ..utils.snapping import collect_plane_geometry, collect_scene_snap_geometry, snap_draw_point, travel_3d_cursor
from ..utils.viewport import (
    ViewportPreviewMixin, draw_nearby_snap_candidates, draw_polyline, draw_snap_circle,
)


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

    def _effective_plane(self, settings):
        return self._auto_plane if settings.drawing_plane == 'AUTO' else settings.drawing_plane

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
        self._travel_origin = self._current.copy()
        self._travel_raw = self._current.copy()
        self._snap_result = None
        self._last_mouse = None
        self._travel_axis = None
        self._snap_skip = 0
        self._auto_plane = None
        self._auto_axes = []
        self._auto_axis_candidate = None
        self._auto_axis_pixels = 0.0
        self._scene_candidates, self._scene_edges = collect_scene_snap_geometry(context)
        plane = self._effective_plane(context.scene.shapeflow)
        if plane:
            self._candidates, self._edges = collect_plane_geometry(
                context, plane, context.scene.shapeflow.drawing_origin
            )
        else:
            self._candidates, self._edges = [], []

    def _set_status(self, context):
        sides = context.scene.shapeflow.polygon_sides
        mode = "center/radius" if context.scene.shapeflow.creation_origin == 'CENTER' else "across"
        plane = self._effective_plane(context.scene.shapeflow)
        auto = f" • Auto {plane or 'waiting'}" if context.scene.shapeflow.drawing_plane == 'AUTO' else ""
        context.workspace.status_text_set(
            f"ShapeFlow Polygon: {sides} sides • {mode}{auto} • Alt bypasses magnetic • Shift free • Tab next target"
        )

    def _mouse_point(self, context, event):
        viewport = viewport_mouse(context, event)
        if viewport is None:
            return None
        settings = context.scene.shapeflow
        if self._start is None:
            if self._last_mouse is None:
                self._last_mouse = Vector(viewport[1])
            point, kind, axis, raw = travel_3d_cursor(
                context, viewport[0], viewport[1], self._last_mouse, self._current,
                settings, self._scene_candidates, self._scene_edges,
                bypass=event.shift, magnetic_bypass=event.alt, skip=self._snap_skip,
                raw_point=self._travel_raw, snap_origin=self._travel_origin,
            )
            self._last_mouse = Vector(viewport[1])
            self._travel_raw = raw
            self._current = point; self._travel_axis = axis; settings.drawing_origin = point
            self._snap_result = type('TravelSnap', (), {'kind': kind})()
            return point
        plane = self._effective_plane(settings)
        if settings.drawing_plane == 'AUTO':
            previous_mouse = Vector(self._last_mouse)
            allowed = set(plane) if plane else None
            candidates = self._candidates if plane else self._scene_candidates
            edges = self._edges if plane else self._scene_edges
            point, kind, axis, raw = travel_3d_cursor(
                context, viewport[0], viewport[1], self._last_mouse, self._current,
                settings, candidates, edges,
                bypass=event.shift, magnetic_bypass=event.alt, skip=self._snap_skip,
                raw_point=self._travel_raw, snap_origin=self._start,
                allowed_axes=allowed,
            )
            self._last_mouse = Vector(viewport[1])
            self._travel_raw = raw
            self._travel_axis = axis
            name = axis_name(axis)
            motion = (Vector(viewport[1]) - previous_mouse).length
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
                    self._candidates, self._edges = collect_plane_geometry(
                        context, self._auto_plane, self._start
                    )
                    self._set_status(context)
            self._snap_result = type('TravelSnap', (), {'kind': kind})()
            return point
        _u, _v, normal = plane_axes(plane)
        raw = ray_plane(context, viewport[1], self._start, normal)
        if raw is None:
            return None
        self._snap_result = snap_draw_point(
            context, viewport[0], raw, plane, settings,
            self._candidates, self._edges, bypass=event.shift,
            magnetic_bypass=event.alt, skip=self._snap_skip, origin=self._start,
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
        if event.type == 'TAB' and event.value == 'PRESS':
            self._snap_skip += 1
            self._current = self._mouse_point(context, event)
            context.area.tag_redraw()
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
                self._travel_origin = point.copy()
                self._travel_raw = point.copy()
                self._last_mouse = Vector(viewport[1]) if viewport else None
                self._travel_axis = None
                self._snap_skip = 0
                plane = self._effective_plane(context.scene.shapeflow)
                if plane:
                    self._candidates, self._edges = collect_plane_geometry(
                        context, plane, point
                    )
            else:
                settings = context.scene.shapeflow
                plane = self._effective_plane(settings)
                if plane is None:
                    self.report({'WARNING'}, "ShapeFlow: move along two different axes to choose the automatic plane")
                    return {'RUNNING_MODAL'}
                try:
                    points = regular_polygon_points(
                        self._start, point, plane,
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
        if settings.geometry_snap:
            candidates = self._scene_candidates if self._start is None else (
                self._candidates or self._scene_candidates
            )
            active = self._current if self._snap_result and self._snap_result.kind in {
                'VERTEX', 'MIDPOINT', 'EDGE', 'FACE_CENTER', 'FACE_POINT'
            } else None
            draw_nearby_snap_candidates(
                context, self._current, candidates,
                screen_radius=max(48.0, settings.snap_distance * 2.5), active=active,
            )
        plane = self._effective_plane(settings)
        axis_u, axis_v, normal = plane_axes(plane) if plane else (
            Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
        )
        span = max(0.05, context.space_data.region_3d.view_distance * 0.15)
        colors = ((1, .15, .15, .8), (.15, 1, .15, .8), (.15, .4, 1, .8))
        magnetic = self._snap_result and self._snap_result.kind in {
            'VERTEX', 'MIDPOINT', 'EDGE', 'FACE_CENTER', 'FACE_POINT'
        }
        for axis, color in zip((axis_u, axis_v, normal), colors):
            if self._travel_axis is not None and abs(self._travel_axis.dot(axis)) > 0.9:
                color = (1, .8, .15, 1)
            elif magnetic:
                color = (*color[:3], 0.12)
            draw_polyline([self._current - axis * span, self._current + axis * span], color=color)
        if magnetic:
            draw_snap_circle(context, self._current, radius=6.0,
                             fill=(0.2, 1.0, 0.42, 0.24), outline=(0.2, 1.0, 0.42, 1.0))
        if self._start is None:
            return
        if plane is None:
            draw_polyline([self._start, self._current], color=(1.0, 0.8, 0.15, 0.9))
            return
        try:
            points = regular_polygon_points(
                self._start, self._current, plane,
                settings.polygon_sides, settings.creation_origin,
            )
        except ValueError:
            return
        draw_polyline(points, color=(0.2, 0.85, 1.0, 1.0), closed=True)

    def _finish(self, context):
        self.remove_preview(context)
        context.workspace.status_text_set(None)
