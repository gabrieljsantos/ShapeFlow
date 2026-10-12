import bpy
from math import degrees
from mathutils import Vector

from .drawing_base import PlanarDrawingMixin
from ..mesh.creation import (
    create_bezier_curve_object, create_guide_curve, create_nurbs_curve_object,
    create_pen_curve_object, create_poly_curve_object, create_polyline_object, create_profile_object,
)
from ..mesh.dimensions import create_angular_dimension, create_linear_dimension
from ..mesh.splitting import split_face_with_path
from ..utils.geometry import (
    accumulate_axis_intent, angle_between_points, arc_points_three, axis_name, bezier_points,
    blender_units_to_typed_length, center_arc_points, ellipse_points, plane_axes, plane_from_axes,
    rotated_rectangle_points, ellipse_from_foci_points, ellipse_from_axis_height,
    circle_from_diameter_points, crescent_two_arcs_points,
)
from ..utils.picking import nearest_face_boundary, ray_plane, viewport_mouse
from ..utils.snapping import collect_plane_geometry, snap_draw_point, travel_3d_cursor
from ..utils.viewport import (
    draw_nearby_snap_candidates, draw_polyline, draw_snap_circle, draw_text,
)
from bpy_extras import view3d_utils


TOOL_DATA = {
    'LINE': ("Line", 2, "two points: start and end"),
    'POLYLINE': ("Polyline", None, "click consecutive points; Enter finishes; Backspace removes the last point"),
    'ELLIPSE': ("Ellipse / Circle", 3, "center, first radius and secondary radius"),
    'ELLIPSE_CENTER': ("Ellipse by center", 3, "center, width radius and height radius"),
    'ELLIPSE_FOCI': ("Ellipse by foci", 3, "first focus, second focus and a point on the ellipse"),
    'ELLIPSE_AXIS': ("Ellipse by axis and height", 3, "axis endpoints and perpendicular height"),
    'CIRCLE_CENTER': ("Circle by center", 2, "center and radius"),
    'CIRCLE_DIAMETER': ("Circle by diameter", 2, "opposite diameter endpoints"),
    'ARC_2P': ("2-Point Arc", 3, "start, end and bulge"),
    'ARC_CENTER': ("Center Arc", 3, "center, radius and angle"),
    'PIE': ("Pie", 3, "center, radius and angle"),
    'ARC': ("Arc", 3, "three points: start, point on arc, end"),
    'BEZIER': ("Bezier", 4, "four points: start, start handle, end, end handle"),
    'CRESCENT': ("Crescent", 3, "two chord endpoints and one point controlling the two arcs"),
    'MEASURE': ("Tape Measure", 2, "two points: start and end; optionally creates a native guide"),
    'PROTRACTOR': ("Protractor", 3, "three points: center, reference direction and final direction"),
    'DIMENSIONS': ("Dimensions", None, "place points for an editable native Curve/Text dimension"),
    'BSPLINE': ("B-Spline", None, "click control points; Enter finishes; Backspace removes the last point"),
    'PEN': ("Pen", None, "click Bezier nodes; Enter finishes; Backspace removes the last node"),
    'RECTANGLE_ROTATED': ("Rotated Rectangle", 3, "three points: origin, arbitrary width and orthogonal height"),
}


class SHAPEFLOW_OT_draw_advanced(PlanarDrawingMixin, bpy.types.Operator):
    bl_idname = "shapeflow.draw_advanced"
    bl_label = "Draw Advanced Shape"
    bl_options = {'REGISTER', 'BLOCKING'}

    tool: bpy.props.EnumProperty(items=tuple((key, value[0], value[2]) for key, value in TOOL_DATA.items()))

    @classmethod
    def description(cls, _context, properties):
        label, _count, help_text = TOOL_DATA.get(properties.tool, ("Shape", 0, ""))
        return f"{label}: {help_text}; remains active until Escape or another tool"

    def invoke(self, context, _event):
        return self._start_planar_modal(context, self.tool)

    def _reset(self, context):
        self._fixed = []
        self._initialize_planar_cursor(context)

    def _set_status(self, context):
        label, count, help_text = TOOL_DATA[self.tool]
        plane = self._effective_plane(context.scene.shapeflow)
        auto = f" • Auto {plane or 'waiting'}" if context.scene.shapeflow.drawing_plane == 'AUTO' else ""
        settings = context.scene.shapeflow
        output = "Embedded" if settings.creation_output == 'EMBEDDED' else "Separate"
        receiver = f" → {settings.workplane_object}" if settings.creation_output == 'EMBEDDED' and settings.workplane_object else ""
        if self.tool == 'DIMENSIONS':
            count = 3 if settings.dimension_type == 'ANGULAR' else 2
        progress = f"point {len(self._fixed)+1}" if count is None else f"point {len(self._fixed)+1}/{count}"
        context.workspace.status_text_set(
            f"ShapeFlow {label}: {help_text} • {output}{receiver} • {progress}{auto} • Alt temporarily free"
        )

    def _complete(self, context):
        try:
            self._commit(context)
        except ValueError as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return False
        bpy.ops.ed.undo_push(message=f"ShapeFlow {TOOL_DATA[self.tool][0]}")
        self._reset(context)
        self._set_status(context)
        return True

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
                bypass=event.alt, magnetic_bypass=event.alt, skip=self._snap_skip,
                raw_point=self._travel_raw, snap_origin=self._travel_origin,
                allowed_axes={'X', 'Y'} if settings.drawing_plane == 'FACE' else None,
            )
            self._last_mouse = Vector(mouse)
            self._travel_raw = raw
            self._travel_axis = axis
            self._set_travel_snap(point, kind)
            settings.drawing_origin = point
            return point
        plane = self._effective_plane(settings)
        if settings.drawing_plane == 'AUTO' and plane is None:
            previous_mouse = Vector(self._last_mouse)
            point, kind, axis, raw = travel_3d_cursor(
                context, region, mouse, self._last_mouse, self._current, settings,
                self._scene_candidates, self._scene_edges,
                bypass=event.alt, magnetic_bypass=event.alt, skip=self._snap_skip,
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
                    self._candidates, self._edges = collect_plane_geometry(
                        context, self._auto_plane, self._fixed[0]
                    )
                    self._set_status(context)
            self._set_travel_snap(point, kind)
            return point
        _u, _v, normal = plane_axes(plane)
        raw = ray_plane(context, mouse, self._fixed[0], normal)
        if raw is None:
            return None
        self._snap_result = snap_draw_point(
            context, region, raw, plane, settings,
            self._candidates, self._edges,
            bypass=event.alt, magnetic_bypass=event.alt, skip=self._snap_skip,
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
        if self.tool in {'POLYLINE', 'BSPLINE', 'PEN'} and event.type == 'BACK_SPACE' and event.value == 'PRESS':
            if self._fixed:
                self._fixed.pop()
                self._snap_skip = 0
                self._set_status(context)
                context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        if self.tool in {'POLYLINE', 'BSPLINE', 'PEN'} and event.type in {'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            minimum = 3 if self.tool == 'BSPLINE' else 2
            if len(self._fixed) < minimum:
                self.report({'WARNING'}, f"ShapeFlow: {TOOL_DATA[self.tool][0]} needs at least {minimum} points")
            else:
                self._complete(context)
            return {'RUNNING_MODAL'}
        handled = self._recenter_increment_event(context, event)
        if handled:
            return handled
        handled = self._cycle_snap_event(context, event)
        if handled:
            return handled
        handled = self._capture_workplane_event(context, event)
        if handled:
            return handled
        if self._pointer_outside_viewport(context, event):
            return {'PASS_THROUGH'}
        viewport = viewport_mouse(context, event)
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
                    self._candidates, self._edges = collect_plane_geometry(
                        context, plane, point
                    )
            self._snap_skip = 0
            required = 3 if self.tool == 'DIMENSIONS' and context.scene.shapeflow.dimension_type == 'ANGULAR' else TOOL_DATA[self.tool][1]
            if self.tool == 'DIMENSIONS' and required is None:
                required = 2
            if required is not None and len(self._fixed) == required:
                if not self._complete(context):
                    self._fixed.pop()
                    return {'RUNNING_MODAL'}
            self._set_status(context)
        return {'RUNNING_MODAL'}

    def _commit(self, context):
        plane = self._effective_plane(context.scene.shapeflow)
        if plane is None:
            raise ValueError("Move along two different axes to choose the automatic plane")
        if self.tool in {'LINE', 'POLYLINE'}:
            points = list(self._fixed)
            name = "ShapeFlow Polyline" if self.tool == 'POLYLINE' else "ShapeFlow Line"
        elif self.tool == 'BSPLINE':
            create_nurbs_curve_object(context, self._fixed)
            return
        elif self.tool == 'PEN':
            create_pen_curve_object(context, self._fixed)
            return
        elif self.tool == 'MEASURE':
            settings = context.scene.shapeflow
            start, end = self._fixed
            settings.last_measure = (end - start).length
            value = blender_units_to_typed_length(
                settings.last_measure, settings.length_unit,
                context.scene.unit_settings.scale_length,
            )
            if settings.measure_create_guide:
                create_guide_curve(context, start, end)
            self.report({'INFO'}, f"ShapeFlow: {value:.4f} {settings.length_unit.lower()}")
            return
        elif self.tool == 'PROTRACTOR':
            settings = context.scene.shapeflow
            center, first, second = self._fixed
            settings.last_angle = angle_between_points(center, first, second)
            if settings.protractor_create_guide:
                guide = create_poly_curve_object(
                    context, (first, center, second), "ShapeFlow Angle Guide",
                )
                guide.hide_render = True
                guide.show_in_front = True
                guide["shapeflow_guide"] = True
                guide["shapeflow_angle"] = settings.last_angle
            self.report({'INFO'}, f"ShapeFlow: {degrees(settings.last_angle):.2f}°")
            return
        elif self.tool == 'DIMENSIONS':
            settings = context.scene.shapeflow
            if settings.dimension_type == 'ANGULAR':
                create_angular_dimension(context, *self._fixed, plane)
            else:
                create_linear_dimension(
                    context, *self._fixed, settings.length_unit,
                    context.scene.unit_settings.scale_length,
                    settings.dimension_type,
                )
            return
        elif self.tool == 'ARC':
            points, name = arc_points_three(*self._fixed, plane), "ShapeFlow Arc"
        elif self.tool == 'ARC_2P':
            start, end, bulge = self._fixed
            points, name = arc_points_three(start, bulge, end, plane), "ShapeFlow 2-Point Arc"
        elif self.tool == 'ARC_CENTER':
            points, name = center_arc_points(*self._fixed, plane), "ShapeFlow Center Arc"
        elif self.tool == 'BEZIER':
            start, start_handle, end, end_handle = self._fixed
            if context.scene.shapeflow.creation_output == 'SEPARATE':
                create_bezier_curve_object(context, start, start_handle, end, end_handle)
                return
            points, name = bezier_points(start, start_handle, end_handle, end), "ShapeFlow Bezier"
        elif self.tool == 'CRESCENT':
            create_profile_object(context, crescent_two_arcs_points(*self._fixed, plane), "ShapeFlow Crescent")
            return
        elif self.tool == 'RECTANGLE_ROTATED':
            create_profile_object(
                context, rotated_rectangle_points(*self._fixed, plane),
                "ShapeFlow Rotated Rectangle",
            )
            return
        elif self.tool == 'PIE':
            arc = center_arc_points(*self._fixed, plane)
            create_profile_object(context, [self._fixed[0], *arc], "ShapeFlow Pie")
            return
        elif self.tool in {'ELLIPSE_FOCI', 'ELLIPSE_AXIS', 'ELLIPSE_CENTER', 'CIRCLE_CENTER', 'CIRCLE_DIAMETER'}:
            if self.tool == 'ELLIPSE_FOCI':
                points = ellipse_from_foci_points(*self._fixed, plane)
                name = "ShapeFlow Ellipse"
            elif self.tool == 'ELLIPSE_AXIS':
                points = ellipse_from_axis_height(*self._fixed, plane)
                name = "ShapeFlow Ellipse"
            elif self.tool == 'CIRCLE_DIAMETER':
                points = circle_from_diameter_points(*self._fixed, plane)
                name = "ShapeFlow Circle"
            elif self.tool == 'CIRCLE_CENTER':
                points = ellipse_points(self._fixed[0], self._fixed[1], self._fixed[1], plane, proportional=True)
                name = "ShapeFlow Circle"
            else:
                points = ellipse_points(*self._fixed, plane)
                name = "ShapeFlow Ellipse"
            create_profile_object(context, points, name)
            return
        else:
            settings = context.scene.shapeflow
            create_profile_object(
                context,
                ellipse_points(
                    *self._fixed, plane,
                    proportional=settings.proportional_creation,
                ),
                "ShapeFlow Circle" if settings.proportional_creation else "ShapeFlow Ellipse",
            )
            return
        settings = context.scene.shapeflow
        if settings.creation_output == 'SEPARATE':
            if self.tool in {'POLYLINE', 'ARC_2P', 'ARC_CENTER'}:
                create_poly_curve_object(context, points, name)
            else:
                create_polyline_object(context, points, name)
            return
        obj = bpy.data.objects.get(settings.workplane_object)
        face_index = settings.workplane_face_index
        if obj is None or obj.type != 'MESH' or not 0 <= face_index < len(obj.data.polygons):
            raise ValueError("Capture a receiver face with W before embedding")
        first = nearest_face_boundary(obj, face_index, points[0])
        last = nearest_face_boundary(obj, face_index, points[-1])
        polygon = obj.data.polygons[face_index]
        world = [obj.matrix_world @ obj.data.vertices[index].co for index in polygon.vertices]
        scale = max((point - world[0]).length for point in world)
        tolerance = max(1.0e-5, scale * 0.025)
        if first is None or last is None or first[0] > tolerance or last[0] > tolerance:
            raise ValueError("Embedded open paths must start and end on the receiver boundary")
        embedded = list(points)
        embedded[0], embedded[-1] = first[1], last[1]
        split_face_with_path(obj, face_index, embedded, first[2], first[3], last[2], last[3])
        context.view_layer.objects.active = obj
        obj.select_set(True)
        settings.workplane_face_index = -1

    def _preview_points(self, context):
        points = self._fixed + ([self._current] if self._current is not None else [])
        plane = self._effective_plane(context.scene.shapeflow)
        if plane is None:
            return points
        try:
            if self.tool == 'LINE' and len(points) >= 2:
                return points[:2]
            if self.tool in {'POLYLINE', 'BSPLINE', 'PEN'}:
                return points
            if self.tool == 'ARC' and len(points) >= 3:
                return arc_points_three(points[0], points[1], points[2], plane)
            if self.tool == 'ARC_2P' and len(points) >= 3:
                return arc_points_three(points[0], points[2], points[1], plane)
            if self.tool in {'ARC_CENTER', 'PIE'} and len(points) >= 3:
                arc = center_arc_points(points[0], points[1], points[2], plane)
                return [points[0], *arc] if self.tool == 'PIE' else arc
            if self.tool == 'BEZIER' and len(points) >= 4:
                return bezier_points(points[0], points[1], points[3], points[2])
            if self.tool == 'CRESCENT' and len(points) >= 3:
                try:
                    return crescent_two_arcs_points(points[0], points[1], points[2], plane)
                except ValueError:
                    return points
            if self.tool == 'ELLIPSE_FOCI' and len(points) >= 3:
                return ellipse_from_foci_points(*points[:3], plane)
            if self.tool == 'ELLIPSE_AXIS' and len(points) >= 3:
                return ellipse_from_axis_height(*points[:3], plane)
            if self.tool in {'ELLIPSE_CENTER', 'CIRCLE_CENTER'} and len(points) >= 2:
                if self.tool == 'CIRCLE_CENTER':
                    return ellipse_points(points[0], points[1], points[1], plane, proportional=True)
                if len(points) >= 3:
                    return ellipse_points(points[0], points[1], points[2], plane)
            if self.tool == 'CIRCLE_DIAMETER' and len(points) >= 2:
                return circle_from_diameter_points(points[0], points[1], plane)
            if self.tool == 'RECTANGLE_ROTATED' and len(points) >= 3:
                return rotated_rectangle_points(points[0], points[1], points[2], plane)
            if self.tool == 'ELLIPSE' and len(points) >= 3:
                return ellipse_points(
                    points[0], points[1], points[2], plane,
                    proportional=context.scene.shapeflow.proportional_creation,
                )
        except ValueError:
            pass
        return points

    def draw_preview(self, context):
        settings = context.scene.shapeflow
        if settings.creation_output == 'EMBEDDED':
            obj = bpy.data.objects.get(settings.workplane_object)
            face_index = settings.workplane_face_index
            if obj and obj.type == 'MESH' and 0 <= face_index < len(obj.data.polygons):
                polygon = obj.data.polygons[face_index]
                receiver = [obj.matrix_world @ obj.data.vertices[index].co for index in polygon.vertices]
                draw_polyline(receiver, color=(1.0, 0.34, 0.08, 1.0), closed=True, width=3.0)
        if settings.geometry_snap and self._current is not None:
            candidates = self._scene_candidates if not self._fixed else (
                self._candidates or self._scene_candidates
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
            closed = self.tool in {'CRESCENT', 'ELLIPSE', 'ELLIPSE_CENTER', 'ELLIPSE_FOCI', 'ELLIPSE_AXIS', 'CIRCLE_CENTER', 'CIRCLE_DIAMETER', 'PIE', 'RECTANGLE_ROTATED'} and len(self._fixed) >= 2
            draw_polyline(preview, color=(.15,.85,1,1), closed=closed)
        for point in self._fixed:
            draw_snap_circle(context, point, radius=5.0)
        if self._snap_result and self._snap_result.kind in {'VERTEX', 'MIDPOINT', 'EDGE', 'FACE_CENTER', 'FACE_POINT'}:
            draw_snap_circle(context, self._current, radius=6.0,
                             fill=(.2, 1, .42, .24), outline=(.2, 1, .42, 1))
        if self.tool == 'BEZIER' and len(self._fixed) >= 2:
            draw_polyline(self._fixed[:2], color=(1,.6,.15,.9))
        if self.tool == 'BEZIER' and len(self._fixed) >= 3:
            draw_polyline([self._fixed[2], self._current], color=(1,.6,.15,.9))

    def draw_hud(self, context):
        if self.tool not in {'MEASURE', 'PROTRACTOR'} or not self._fixed or self._current is None:
            return
        settings = context.scene.shapeflow
        if self.tool == 'MEASURE':
            distance = (self._current - self._fixed[0]).length
            value = blender_units_to_typed_length(
                distance, settings.length_unit, context.scene.unit_settings.scale_length,
            )
            label = f"{value:.4f} {settings.length_unit.lower()}"
        elif len(self._fixed) >= 2:
            try:
                label = f"{degrees(angle_between_points(self._fixed[0], self._fixed[1], self._current)):.2f}°"
            except ValueError:
                return
        else:
            return
        region = next((item for item in context.area.regions if item.type == 'WINDOW'), context.region)
        screen = view3d_utils.location_3d_to_region_2d(
            region, context.space_data.region_3d,
            (self._fixed[0] + self._current) * 0.5,
        )
        if screen is not None:
            draw_text(screen + Vector((12, 12)), label, size=15)
