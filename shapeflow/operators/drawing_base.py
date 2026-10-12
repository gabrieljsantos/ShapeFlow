"""Shared interaction lifecycle for planar ShapeFlow drawing operators."""
from bpy_extras import view3d_utils
from mathutils import Vector

from ..utils.geometry import plane_axes, settings_plane, snap_scalar, typed_length_to_blender_units
from ..utils.picking import capture_hovered_workplane, viewport_mouse
from ..utils.picking import ray_plane
from ..utils.snapping import (
    SnapResult,
    collect_plane_geometry,
    collect_scene_snap_geometry,
    cursor_increment_enabled,
    snap_draw_point,
)
from ..utils.viewport import ViewportPreviewMixin


class PlanarDrawingMixin(ViewportPreviewMixin):
    """Reusable state and events shared by planar creation tools.

    Shape-specific operators still own their click stages, geometry preview,
    commit operation, and status text. This mixin owns only the common cursor,
    workplane, snap-cache, modal startup, and shutdown behavior.
    """

    @classmethod
    def poll(cls, context):
        return (
            context.area
            and context.area.type == 'VIEW_3D'
            and context.window_manager.shapeflow_mode
        )

    def _effective_plane(self, settings):
        return settings_plane(settings, self._auto_plane)

    def _start_planar_modal(self, context, active_tool):
        context.window_manager.shapeflow_active_tool = active_tool
        self._reset(context)
        self.add_preview(context)
        context.window_manager.modal_handler_add(self)
        self._set_status(context)
        return {'RUNNING_MODAL'}

    def _initialize_planar_cursor(self, context):
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
        self._refresh_plane_geometry(context)

    def _refresh_plane_geometry(self, context, origin=None):
        plane = self._effective_plane(context.scene.shapeflow)
        if plane:
            self._candidates, self._edges = collect_plane_geometry(
                context,
                plane,
                context.scene.shapeflow.drawing_origin if origin is None else origin,
            )
        else:
            self._candidates, self._edges = [], []

    def _set_travel_snap(self, point, kind):
        self._snap_result = SnapResult(Vector(point), kind)

    def _capture_workplane_event(self, context, event):
        if event.type != 'W' or event.value != 'PRESS':
            return None
        if capture_hovered_workplane(context, event):
            self._reset(context)
            self._set_status(context)
            context.area.tag_redraw()
        else:
            self.report({'WARNING'}, "ShapeFlow: hover a mesh face before pressing W")
        return {'RUNNING_MODAL'}

    def _cycle_snap_event(self, context, event):
        if event.type != 'TAB' or event.value != 'PRESS':
            return None
        self._snap_skip += 1
        point = self._mouse_point(context, event)
        if point is not None:
            self._current = point
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _recenter_increment_event(self, context, event):
        """Re-anchor the incremental cursor under the pointer with Space."""
        if event.type != 'SPACE' or event.value != 'PRESS':
            return None
        settings = context.scene.shapeflow
        if not cursor_increment_enabled(settings):
            return None
        viewport = viewport_mouse(context, event)
        if viewport is None:
            return {'RUNNING_MODAL'}

        region, mouse = viewport
        if not (0 <= mouse[0] <= region.width and 0 <= mouse[1] <= region.height):
            return None
        plane = self._effective_plane(settings)
        fixed = getattr(self, '_start', None)
        if fixed is None:
            fixed_points = getattr(self, '_fixed', None)
            if fixed_points:
                fixed = fixed_points[0]
        stage_origin = getattr(self, '_stage_origin', None)
        if stage_origin is not None and hasattr(self, '_locked_axis'):
            fixed = stage_origin
        anchor = Vector(fixed if fixed is not None else settings.drawing_origin)

        locked_axis = getattr(self, '_locked_axis', None)
        axes = getattr(self, '_axes', {})
        axis = axes.get(locked_axis) if locked_axis else None
        if axis is not None:
            # In dimensional tools, keep the cursor on the active construction axis.
            rv3d = context.space_data.region_3d
            screen_origin = view3d_utils.location_3d_to_region_2d(region, rv3d, anchor)
            screen_end = view3d_utils.location_3d_to_region_2d(region, rv3d, anchor + axis)
            if screen_origin is None or screen_end is None:
                return {'RUNNING_MODAL'}
            screen_axis = screen_end - screen_origin
            if screen_axis.length_squared < 1.0e-12:
                return {'RUNNING_MODAL'}
            distance = (Vector(mouse) - screen_origin).dot(screen_axis) / screen_axis.length_squared
            spacing = typed_length_to_blender_units(
                settings.grid_spacing, settings.length_unit,
                context.scene.unit_settings.scale_length,
            )
            point = anchor + axis * snap_scalar(distance, spacing)
            snap = SnapResult(point, 'GRID')
        else:
            if plane:
                normal = plane_axes(plane)[2]
            else:
                normal = context.space_data.region_3d.view_rotation @ Vector((0.0, 0.0, 1.0))
            raw = ray_plane(context, mouse, anchor, normal)
            if raw is None:
                return {'RUNNING_MODAL'}
            candidates = getattr(self, '_candidates', None) or getattr(self, '_scene_candidates', [])
            edges = getattr(self, '_edges', None) or getattr(self, '_scene_edges', [])
            if plane:
                snap = snap_draw_point(
                    context, region, raw, plane, settings, candidates, edges,
                    origin=anchor,
                )
            else:
                spacing = typed_length_to_blender_units(
                    settings.grid_spacing, settings.length_unit,
                    context.scene.unit_settings.scale_length,
                )
                point = anchor + Vector(tuple(
                    snap_scalar(value, spacing) for value in (raw - anchor)
                ))
                snap = SnapResult(point, 'GRID')

        self._current = snap.point.copy()
        self._travel_raw = snap.point.copy()
        if fixed is None:
            self._travel_origin = snap.point.copy()
            settings.drawing_origin = snap.point
        self._last_mouse = Vector(mouse)
        self._travel_axis = None
        self._snap_result = snap
        if hasattr(self, '_raw'):
            self._raw = snap.point.copy()
        if hasattr(self, '_snap_kind'):
            self._snap_kind = snap.kind
        if context.area:
            context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    @staticmethod
    def _pointer_outside_viewport(context, event):
        viewport = viewport_mouse(context, event)
        return bool(
            viewport
            and not (
                0 <= viewport[1][0] <= viewport[0].width
                and 0 <= viewport[1][1] <= viewport[0].height
            )
        )

    def _finish(self, context):
        self.remove_preview(context)
        context.workspace.status_text_set(None)
