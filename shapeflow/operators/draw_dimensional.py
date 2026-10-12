import bpy
from mathutils import Vector

from .drawing_base import PlanarDrawingMixin
from ..mesh.creation import create_box_object, create_rectangle_object
from ..utils.geometry import accumulate_axis_intent, axis_name, plane_axes, settings_plane
from ..utils.picking import viewport_mouse
from ..utils.snapping import collect_scene_snap_geometry, travel_3d_cursor
from ..utils.viewport import (
    draw_nearby_snap_candidates, draw_polyline,
    draw_snap_circle,
)


AXES = {'X': Vector((1, 0, 0)), 'Y': Vector((0, 1, 0)), 'Z': Vector((0, 0, 1))}


class SHAPEFLOW_OT_draw_dimensional(PlanarDrawingMixin, bpy.types.Operator):
    """Create an orthogonal face or box one dimension at a time."""

    bl_idname = "shapeflow.draw_dimensional"
    bl_label = "Draw Dimensional Shape"
    bl_options = {'REGISTER', 'BLOCKING'}

    shape: bpy.props.EnumProperty(items=(
        ('RECTANGLE_2P', "2-Point Rectangle", "Origin, width, then height"),
        ('BOX_3P', "3-Point Box", "Origin, width, height, then depth"),
    ))

    @classmethod
    def description(cls, _context, properties):
        if properties.shape == 'BOX_3P':
            return "3-point box: draw width, height, and depth as consecutive orthogonal stages"
        return "2-point rectangle: draw a line first, then pull its orthogonal height"

    def invoke(self, context, _event):
        return self._start_planar_modal(context, self.shape)

    def _reset(self, context):
        settings = context.scene.shapeflow
        origin = Vector(settings.drawing_origin)
        basis = plane_axes(settings_plane(settings)) if settings.drawing_plane == 'FACE' else tuple(AXES.values())
        self._axes = dict(zip(('X', 'Y', 'Z'), basis))
        self._fixed = []
        self._current = origin.copy()
        self._raw = origin.copy()
        self._stage_origin = origin.copy()
        self._last_mouse = None
        self._axis_names = []
        self._locked_axis = None
        self._gesture_candidate = None
        self._gesture_pixels = 0.0
        self._snap_kind = "FREE"
        self._scene_candidates, self._scene_edges = collect_scene_snap_geometry(context)
        self._stage_candidates = self._scene_candidates
        self._stage_edges = self._scene_edges

    def _set_status(self, context):
        label = "2P Rectangle" if self.shape == 'RECTANGLE_2P' else "3P Box"
        stages = ("origin", "width", "height") if self.shape == 'RECTANGLE_2P' else (
            "origin", "width", "height", "depth"
        )
        stage = stages[min(len(self._fixed), len(stages) - 1)]
        axis = self._locked_axis or "choose axis"
        context.workspace.status_text_set(
            f"ShapeFlow {label}: {stage} [{axis}] • click to confirm stage • Alt temporarily free"
        )

    def _begin_stage(self, point, mouse):
        self._stage_origin = point.copy()
        self._current = point.copy()
        self._raw = point.copy()
        self._last_mouse = Vector(mouse)
        self._locked_axis = None
        self._gesture_candidate = None
        self._gesture_pixels = 0.0
        self._stage_candidates = []
        self._stage_edges = []

    def _lock_axis(self, context, name):
        self._locked_axis = name
        self._gesture_candidate = None
        self._gesture_pixels = 0.0
        axis = self._axes[name]
        displacement = self._current - self._stage_origin
        self._current = self._stage_origin + axis * displacement.dot(axis)
        self._raw = self._current.copy()
        tolerance = 1.0e-5
        self._stage_candidates = [
            candidate for candidate in self._scene_candidates
            if ((candidate.point - self._stage_origin)
                - axis * (candidate.point - self._stage_origin).dot(axis)).length <= tolerance
        ]
        self._stage_edges = []
        self._set_status(context)

    def _mouse_point(self, context, event):
        viewport = viewport_mouse(context, event)
        if not viewport:
            return None
        region, mouse = viewport
        settings = context.scene.shapeflow
        if self._last_mouse is None:
            self._last_mouse = Vector(mouse)
        previous_mouse = Vector(self._last_mouse)
        if not self._fixed:
            candidates, edges = self._scene_candidates, self._scene_edges
            allowed = None
        else:
            candidates, edges = self._stage_candidates, self._stage_edges
            allowed = {self._locked_axis} if self._locked_axis else set(AXES) - set(self._axis_names)
        point, kind, axis, raw = travel_3d_cursor(
            context, region, mouse, self._last_mouse, self._current, settings,
            candidates, edges, bypass=event.alt, magnetic_bypass=event.alt,
            raw_point=self._raw, snap_origin=self._stage_origin, allowed_axes=allowed,
        )
        self._last_mouse = Vector(mouse)
        self._raw = raw
        self._current = point
        self._snap_kind = kind
        if self._fixed and self._locked_axis is None:
            name = axis_name(axis)
            motion = (Vector(mouse) - previous_mouse).length
            self._gesture_candidate, self._gesture_pixels, accepted = accumulate_axis_intent(
                self._gesture_candidate, self._gesture_pixels, name, motion,
                settings.auto_axis_threshold,
            )
            if accepted and name not in self._axis_names:
                self._lock_axis(context, name)
        if not self._fixed:
            settings.drawing_origin = point
        return self._current

    @staticmethod
    def _base_corners(points):
        origin, width_end, height_end = points[:3]
        return [origin, width_end, height_end, origin + (height_end - width_end)]

    def _commit(self, context):
        base = self._base_corners(self._fixed)
        if self.shape == 'RECTANGLE_2P':
            create_rectangle_object(context, base, "ShapeFlow 2P Rectangle")
        else:
            create_box_object(context, base, self._fixed[3] - self._fixed[2], "ShapeFlow 3P Box")
        bpy.ops.ed.undo_push(message="ShapeFlow Dimensional Shape")
        self._reset(context)
        self._set_status(context)

    def modal(self, context, event):
        wm = context.window_manager
        if not wm.shapeflow_mode or wm.shapeflow_active_tool != self.shape:
            self._finish(context)
            return {'CANCELLED'}
        if event.type == 'ESC':
            wm.shapeflow_active_tool = 'NONE'
            self._finish(context)
            return {'CANCELLED'}
        if event.type == 'RIGHTMOUSE':
            self._reset(context)
            self._set_status(context)
            return {'RUNNING_MODAL'}
        handled = self._capture_workplane_event(context, event)
        if handled:
            return handled
        handled = self._recenter_increment_event(context, event)
        if handled:
            return handled
        if self._pointer_outside_viewport(context, event):
            return {'PASS_THROUGH'}
        viewport = viewport_mouse(context, event)
        if event.type == 'MOUSEMOVE':
            self._mouse_point(context, event)
            context.area.tag_redraw()
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            point = self._mouse_point(context, event)
            if point is None:
                return {'RUNNING_MODAL'}
            if self._fixed and self._locked_axis is None:
                self.report({'INFO'}, "ShapeFlow: move deliberately to choose this stage axis")
                return {'RUNNING_MODAL'}
            self._fixed.append(point.copy())
            if self._locked_axis:
                self._axis_names.append(self._locked_axis)
            required = 3 if self.shape == 'RECTANGLE_2P' else 4
            if len(self._fixed) == required:
                try:
                    self._commit(context)
                except ValueError as error:
                    self.report({'WARNING'}, f"ShapeFlow: {error}")
                    self._fixed.pop()
                return {'RUNNING_MODAL'}
            self._begin_stage(point, viewport[1])
            self._set_status(context)
        return {'RUNNING_MODAL'}

    def draw_preview(self, context):
        settings = context.scene.shapeflow
        candidates = self._scene_candidates if not self._fixed or self._locked_axis is None else self._stage_candidates
        if settings.geometry_snap:
            active = self._current if self._snap_kind in {
                'VERTEX', 'MIDPOINT', 'EDGE', 'FACE_CENTER', 'FACE_POINT'
            } else None
            draw_nearby_snap_candidates(
                context, self._current, candidates,
                screen_radius=max(48.0, settings.snap_distance * 2.5), active=active,
            )
        if self._fixed:
            draw_polyline([self._fixed[-1], self._current], color=(1.0, 0.8, 0.15, 1.0))
        if len(self._fixed) >= 2:
            preview_points = self._fixed + [self._current]
            if len(preview_points) >= 3:
                base = self._base_corners(preview_points)
                draw_polyline(base, color=(0.15, 0.85, 1.0, 1.0), closed=True)
                if self.shape == 'BOX_3P' and len(self._fixed) >= 3:
                    depth = self._current - self._fixed[2]
                    top = [point + depth for point in base]
                    draw_polyline(top, color=(0.2, 1.0, 0.45, 1.0), closed=True)
                    for source, target in zip(base, top):
                        draw_polyline([source, target], color=(0.2, 1.0, 0.45, 0.8))
        for point in self._fixed:
            draw_snap_circle(context, point, radius=5.0)
        if self._snap_kind in {'VERTEX', 'MIDPOINT', 'EDGE', 'FACE_CENTER', 'FACE_POINT'}:
            draw_snap_circle(
                context, self._current, radius=6.5,
                fill=(0.12, 0.9, 0.3, 0.72), outline=(0.2, 1.0, 0.42, 1.0), width=2.5,
            )
