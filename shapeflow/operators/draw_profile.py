import bpy
from bpy_extras import view3d_utils
from mathutils import Vector

from .drawing_base import PlanarDrawingMixin
from ..mesh.creation import create_rectangle_object
from ..utils.geometry import (
    accumulate_axis_intent,
    axis_name,
    parse_coordinate_pair,
    plane_axes,
    plane_from_axes,
    point_from_plane_coordinates,
    rectangle_corners,
    typed_length_to_blender_units,
    unit_suffix,
)
from ..utils.picking import ray_plane, viewport_mouse
from ..utils.snapping import (
    collect_plane_geometry,
    snap_draw_point,
    travel_3d_cursor,
)
from ..utils.viewport import (
    draw_nearby_snap_candidates, draw_polyline,
    draw_snap_circle, draw_text,
)


class SHAPEFLOW_OT_draw_rectangle(PlanarDrawingMixin, bpy.types.Operator):
    bl_idname = "shapeflow.draw_rectangle"
    bl_label = "Draw Rectangle"
    bl_description = "Draw a rectangular native mesh face"
    bl_options = {'REGISTER', 'BLOCKING'}

    _start = None
    _current = None
    _snap_result = None
    _numeric = ""

    def _corners(self, context, start, end):
        settings = context.scene.shapeflow
        plane = self._effective_plane(settings)
        if plane is None:
            raise ValueError("Move along two different axes to choose the automatic plane")
        return rectangle_corners(
            start, end, plane,
            settings.creation_origin, settings.proportional_creation,
        )

    def invoke(self, context, event):
        return self._start_planar_modal(context, 'RECTANGLE')

    def _reset(self, context):
        self._start = None
        self._numeric = ""
        self._initialize_planar_cursor(context)

    def _set_status(self, context):
        plane = context.scene.shapeflow.drawing_plane
        effective = self._effective_plane(context.scene.shapeflow)
        labels = {'XY': 'X;Y', 'XZ': 'X;Z', 'YZ': 'Y;Z'}.get(effective, 'local U;V' if plane == 'FACE' else 'two axes') if isinstance(effective, str) else 'local U;V'
        stage = "origin" if self._start is None else "size"
        auto = f" • Auto {effective or 'waiting'}" if plane == 'AUTO' else ""
        context.workspace.status_text_set(
            f"ShapeFlow Draw: click/type {labels} for {stage}{auto} • Alt temporarily free • Tab next target"
        )

    def _mouse_point(self, context, event):
        viewport = viewport_mouse(context, event)
        if viewport is None:
            return None
        settings = context.scene.shapeflow
        plane = self._effective_plane(settings)
        if self._start is None:
            if self._last_mouse is None:
                self._last_mouse = Vector(viewport[1])
            point, kind, axis, raw = travel_3d_cursor(
                context, viewport[0], viewport[1], self._last_mouse, self._current,
                settings, self._scene_candidates, self._scene_edges,
                bypass=event.alt, magnetic_bypass=event.alt, skip=self._snap_skip,
                raw_point=self._travel_raw, snap_origin=self._travel_origin,
                allowed_axes={'X', 'Y'} if settings.drawing_plane == 'FACE' else None,
            )
            self._last_mouse = Vector(viewport[1])
            self._travel_raw = raw
            self._current = point
            self._travel_axis = axis
            settings.drawing_origin = point
            self._set_travel_snap(point, kind)
            return point
        if settings.drawing_plane == 'AUTO':
            if self._last_mouse is None:
                self._last_mouse = Vector(viewport[1])
            previous_mouse = Vector(self._last_mouse)
            allowed = set(plane) if plane else None
            candidates = self._candidates if plane else self._scene_candidates
            edges = self._edges if plane else self._scene_edges
            point, kind, axis, raw = travel_3d_cursor(
                context, viewport[0], viewport[1], self._last_mouse, self._current,
                settings, candidates, edges,
                bypass=event.alt, magnetic_bypass=event.alt, skip=self._snap_skip,
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
                        context, self._auto_plane, self._start,
                    )
                    self._set_status(context)
            self._set_travel_snap(point, kind)
            return point
        _, _, normal = plane_axes(plane)
        raw = ray_plane(context, viewport[1], self._start, normal)
        if raw is None:
            return None
        self._snap_result = snap_draw_point(
            context, viewport[0], raw, plane, context.scene.shapeflow,
            self._candidates, self._edges, bypass=event.alt,
            magnetic_bypass=event.alt, skip=self._snap_skip, origin=self._start,
        )
        return self._snap_result.point

    def _numeric_point(self, context):
        first, second = parse_coordinate_pair(self._numeric)
        settings = context.scene.shapeflow
        plane = self._effective_plane(settings)
        if plane is None:
            raise ValueError("Automatic plane must be chosen with the mouse before numeric input")
        first = typed_length_to_blender_units(first, settings.length_unit, context.scene.unit_settings.scale_length)
        second = typed_length_to_blender_units(second, settings.length_unit, context.scene.unit_settings.scale_length)
        if self._start is None:
            if settings.drawing_plane == 'FACE':
                axis_u, axis_v, _normal = plane_axes(plane)
                return Vector(settings.drawing_origin) + axis_u * first + axis_v * second
            return point_from_plane_coordinates(first, second, plane)
        axis_u, axis_v, _normal = plane_axes(plane)
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
        handled = self._capture_workplane_event(context, event)
        if handled:
            return handled
        handled = self._recenter_increment_event(context, event)
        if handled:
            return handled
        handled = self._cycle_snap_event(context, event)
        if handled:
            return handled
        if self._pointer_outside_viewport(context, event):
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
                self._snap_skip = 0
                plane = self._effective_plane(context.scene.shapeflow)
                if plane:
                    self._candidates, self._edges = collect_plane_geometry(
                        context, plane, point,
                    )
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
                self._travel_origin = point.copy()
                self._travel_raw = point.copy()
                viewport = viewport_mouse(context, event)
                self._last_mouse = Vector(viewport[1]) if viewport else None
                self._travel_axis = None
                self._snap_skip = 0
                self._numeric = ""
                plane = self._effective_plane(context.scene.shapeflow)
                if plane:
                    self._candidates, self._edges = collect_plane_geometry(
                        context, plane, point,
                    )
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
        settings = context.scene.shapeflow
        if settings.geometry_snap and self._current is not None:
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
        if self._current is not None:
            plane = self._effective_plane(settings)
            display_axes = plane_axes(plane) if plane else (
                Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
            )
            axis_u, axis_v, normal = display_axes
            rv3d = context.space_data.region_3d
            span = max(0.05, rv3d.view_distance * (0.15 if self._start is None else 2.0))
            magnetic = self._snap_result and self._snap_result.kind in {'VERTEX', 'MIDPOINT', 'EDGE', 'FACE_CENTER', 'FACE_POINT'}
            base_alpha = 0.12 if magnetic else 0.55
            color_u = (1.0, 0.8, 0.15, 0.9) if self._snap_result and self._snap_result.guide_u and not magnetic else (0.8, 0.12, 0.12, base_alpha)
            color_v = (1.0, 0.8, 0.15, 0.9) if self._snap_result and self._snap_result.guide_v and not magnetic else (0.8, 0.12, 0.12, base_alpha)
            color_n = (1.0, 0.8, 0.15, 0.95) if self._travel_axis is not None and abs(self._travel_axis.dot(normal)) > 0.9 else (0.15, 0.4, 1.0, 0.12 if magnetic else 0.8)
            draw_polyline([self._current - axis_u * span, self._current + axis_u * span], color=color_u)
            draw_polyline([self._current - axis_v * span, self._current + axis_v * span], color=color_v)
            draw_polyline([self._current - normal * span, self._current + normal * span], color=color_n)
            if self._snap_result and self._snap_result.guide_u:
                draw_polyline([self._current, self._snap_result.guide_u], color=color_u)
            if self._snap_result and self._snap_result.guide_v:
                draw_polyline([self._current, self._snap_result.guide_v], color=color_v)
            if magnetic:
                draw_snap_circle(context, self._current, radius=6.0,
                                 fill=(0.2, 1.0, 0.42, 0.24), outline=(0.2, 1.0, 0.42, 1.0))
        if self._start is not None and self._current is not None:
            if self._effective_plane(context.scene.shapeflow):
                draw_polyline(self._corners(context, self._start, self._current), closed=True)
            else:
                draw_polyline([self._start, self._current], color=(1.0, 0.8, 0.15, 0.9))

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
        plane = self._effective_plane(settings)
        axes = {'XY': ('X', 'Y'), 'XZ': ('X', 'Z'), 'YZ': ('Y', 'Z')}.get(plane, ('X', 'Y'))
        values = {'XY': (self._current.x, self._current.y), 'XZ': (self._current.x, self._current.z), 'YZ': (self._current.y, self._current.z)}.get(plane, (self._current.x, self._current.y))
        suffix = unit_suffix(settings.length_unit)
        snap_kind = self._snap_result.kind.replace('_', ' ').title() if self._snap_result else 'Free'
        text = f"{axes[0]} {values[0] * factor:.4g}; {axes[1]} {values[1] * factor:.4g} {suffix}  [{snap_kind}]"
        if settings.drawing_plane == 'AUTO':
            text += f"  [Auto → {plane or 'waiting for 2 axes'}]"
        if self._numeric:
            text += f"  › {self._numeric}"
        draw_text((screen.x + 16, screen.y + 16), text, color=(1.0, 0.9, 0.75, 1.0))
