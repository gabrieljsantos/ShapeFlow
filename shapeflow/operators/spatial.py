import bpy
from mathutils import Vector
from bpy_extras import view3d_utils

from ..utils.geometry import snap_scalar, typed_length_to_blender_units
from ..utils.picking import pick_mesh_face, ray_plane, viewport_mouse
from ..utils.snapping import (
    collect_object_snap_geometry,
    collect_scene_snap_geometry,
    collect_scene_snap_points,
    nearest_screen_candidate,
    nearest_screen_geometry,
)
from ..utils.viewport import ViewportPreviewMixin, draw_polyline


AXES = {'X': Vector((1, 0, 0)), 'Y': Vector((0, 1, 0)), 'Z': Vector((0, 0, 1))}


def _step(context):
    settings = context.scene.shapeflow
    return typed_length_to_blender_units(
        settings.grid_spacing, settings.length_unit, context.scene.unit_settings.scale_length
    )


def _projected_axis(context, region, origin, axis):
    rv3d = context.space_data.region_3d
    a = view3d_utils.location_3d_to_region_2d(region, rv3d, origin)
    b = view3d_utils.location_3d_to_region_2d(region, rv3d, origin + axis)
    if a is None or b is None or (b - a).length < 1.0e-5:
        return None
    direction = b - a
    direction.normalize()
    return direction


def _axis_drag(context, region, origin, mouse_start, mouse_now, allowed='XYZ', bypass=False):
    delta = Vector(mouse_now) - Vector(mouse_start)
    candidates = []
    for name, axis in AXES.items():
        if name not in allowed:
            continue
        screen_axis = _projected_axis(context, region, origin, axis)
        if screen_axis is not None:
            candidates.append((abs(delta.dot(screen_axis)), delta.dot(screen_axis), axis))
    if not candidates:
        return Vector(), None
    _score, pixels, axis = max(candidates, key=lambda item: item[0])
    distance = pixels * 0.01
    settings = context.scene.shapeflow
    if settings.snap_enabled and settings.grid_snap and not bypass:
        distance = snap_scalar(distance, _step(context))
    return axis * distance, axis


class _SpatialToolMixin(ViewportPreviewMixin):
    def _outside_viewport(self, context, event):
        viewport = viewport_mouse(context, event)
        if not viewport:
            return True
        region, mouse = viewport
        return not (0 <= mouse[0] <= region.width and 0 <= mouse[1] <= region.height)


class SHAPEFLOW_OT_position_origin(_SpatialToolMixin, bpy.types.Operator):
    bl_idname = "shapeflow.position_origin"
    bl_label = "Position Creation Origin"
    bl_description = "G: drag the 3D ShapeFlow origin along a projected world axis; snap to existing geometry"
    bl_options = {'REGISTER', 'BLOCKING'}

    def invoke(self, context, _event):
        context.window_manager.shapeflow_active_tool = 'ORIGIN'
        self._dragging = False
        self._origin = Vector(context.scene.shapeflow.drawing_origin)
        self._current = self._origin.copy()
        self._axis = None
        self._candidates = collect_scene_snap_points(context)
        self.add_preview(context)
        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set("ShapeFlow Origin: drag in an axis direction • geometry snaps in 3D • Esc stops")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        wm = context.window_manager
        if not wm.shapeflow_mode or wm.shapeflow_active_tool != 'ORIGIN':
            self._finish(context); return {'CANCELLED'}
        if event.type == 'ESC':
            wm.shapeflow_active_tool = 'NONE'; self._finish(context); return {'CANCELLED'}
        if self._outside_viewport(context, event):
            return {'PASS_THROUGH'}
        region, mouse = viewport_mouse(context, event)
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self._dragging = True; self._mouse_start = mouse; self._origin = Vector(context.scene.shapeflow.drawing_origin)
        elif event.type == 'MOUSEMOVE' and self._dragging:
            settings = context.scene.shapeflow
            snap = nearest_screen_candidate(context, region, mouse, self._candidates, settings.snap_distance)
            if snap and settings.snap_enabled and settings.geometry_snap and not event.shift:
                self._current, self._axis = snap.point.copy(), None
            else:
                offset, self._axis = _axis_drag(context, region, self._origin, self._mouse_start, mouse, 'XYZ', event.shift)
                self._current = self._origin + offset
            settings.drawing_origin = self._current
            context.area.tag_redraw()
        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self._dragging:
            self._dragging = False
            bpy.ops.ed.undo_push(message="ShapeFlow Position Origin")
        return {'RUNNING_MODAL'}

    def draw_preview(self, context):
        span = max(0.1, context.space_data.region_3d.view_distance * 0.2)
        colors = {'X': (1, .15, .15, .9), 'Y': (.15, 1, .15, .9), 'Z': (.2, .45, 1, .9)}
        for name, axis in AXES.items():
            color = (1, .8, .15, 1) if self._axis == axis else colors[name]
            draw_polyline([self._current - axis * span, self._current + axis * span], color=color)

    def _finish(self, context):
        self.remove_preview(context); context.workspace.status_text_set(None)


class SHAPEFLOW_OT_move_object(_SpatialToolMixin, bpy.types.Operator):
    bl_idname = "shapeflow.move_object"
    bl_label = "Move Object"
    bl_description = "M: drag a whole object; use axis/plane constraints, steps, and geometry snapping"
    bl_options = {'REGISTER', 'BLOCKING'}

    def invoke(self, context, _event):
        context.window_manager.shapeflow_active_tool = 'MOVE'
        self._dragging = False; self._object = None; self._copied = False
        self._anchor = None; self._snap_target = None; self._snap_kind = None
        self._hover_object = None; self._hover_snap = None; self._hover_face = None
        self.add_preview(context); context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set("ShapeFlow Move: drag an object • Copy duplicates first • Esc stops")
        return {'RUNNING_MODAL'}

    def _update_hover(self, context, region, mouse):
        picked = pick_mesh_face(context, mouse)
        if not picked:
            self._hover_object = None; self._hover_snap = None; self._hover_face = None
            context.area.tag_redraw()
            return
        obj, face_index, hit, _normal = picked
        candidates, edges = collect_object_snap_geometry(obj)
        self._hover_snap = nearest_screen_geometry(
            context, region, mouse, candidates, edges, context.scene.shapeflow.snap_distance
        )
        polygon = obj.data.polygons[face_index]
        self._hover_object = obj
        self._hover_hit = hit.copy()
        self._hover_face = tuple(obj.matrix_world @ obj.data.vertices[index].co for index in polygon.vertices)
        kind = self._hover_snap.kind.lower() if self._hover_snap else "face point"
        context.workspace.status_text_set(f"ShapeFlow Move: {kind} ready • click and drag")
        context.area.tag_redraw()

    def modal(self, context, event):
        wm = context.window_manager
        if not wm.shapeflow_mode or wm.shapeflow_active_tool != 'MOVE':
            self._cancel_drag(); self._finish(context); return {'CANCELLED'}
        if event.type == 'ESC':
            self._cancel_drag(); wm.shapeflow_active_tool = 'NONE'; self._finish(context); return {'CANCELLED'}
        if event.type == 'RIGHTMOUSE':
            self._cancel_drag(); return {'RUNNING_MODAL'}
        if self._outside_viewport(context, event):
            return {'PASS_THROUGH'}
        region, mouse = viewport_mouse(context, event)
        if event.type == 'MOUSEMOVE' and not self._dragging:
            self._update_hover(context, region, mouse)
            return {'RUNNING_MODAL'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS' and not self._dragging:
            if self._hover_object is None:
                self._update_hover(context, region, mouse)
            if self._hover_object is None:
                return {'RUNNING_MODAL'}
            obj = self._hover_object
            hit = self._hover_hit
            source_snap = self._hover_snap
            if context.scene.shapeflow.copy_mode:
                duplicate = obj.copy(); duplicate.data = obj.data.copy(); context.collection.objects.link(duplicate); obj = duplicate
                self._copied = True
            else:
                self._copied = False
            self._object = obj
            self._start_location = obj.location.copy()
            self._anchor = source_snap.point.copy() if source_snap else hit.copy()
            self._anchor_kind = source_snap.kind if source_snap else "FACE_POINT"
            self._mouse_start = mouse
            self._candidates, self._edges = collect_scene_snap_geometry(context, exclude=obj)
            self._snap_target = None; self._snap_kind = None; self._dragging = True
            self._hover_object = None
            context.workspace.status_text_set(f"ShapeFlow Move: grabbed {self._anchor_kind.lower()} • drag near target geometry")
        elif event.type == 'MOUSEMOVE' and self._dragging:
            settings = context.scene.shapeflow
            target = nearest_screen_geometry(
                context, region, mouse, self._candidates, self._edges, settings.snap_distance
            )
            if target and settings.snap_enabled and settings.geometry_snap and not event.shift:
                offset = target.point - self._anchor
                changed_target = self._snap_target is None or (self._snap_target - target.point).length > 1.0e-7
                self._snap_target = target.point.copy(); self._snap_kind = target.kind
                if changed_target:
                    screen = view3d_utils.location_3d_to_region_2d(
                        region, context.space_data.region_3d, target.point
                    )
                    if screen is not None:
                        context.window.cursor_warp(int(region.x + screen.x), int(region.y + screen.y))
            else:
                self._snap_target = None; self._snap_kind = None
                constraint = settings.move_constraint
                if len(constraint) == 1:
                    offset, _axis = _axis_drag(context, region, self._anchor, self._mouse_start, mouse, constraint, event.shift)
                else:
                    normal = {'XY': AXES['Z'], 'XZ': AXES['Y'], 'YZ': AXES['X']}.get(constraint)
                    if normal is None:
                        normal = context.space_data.region_3d.view_rotation @ Vector((0, 0, 1))
                    start = ray_plane(context, self._mouse_start, self._anchor, normal)
                    now = ray_plane(context, mouse, self._anchor, normal)
                    offset = (now - start) if start is not None and now is not None else Vector()
                    if settings.snap_enabled and settings.grid_snap and not event.shift:
                        spacing = _step(context)
                        offset = Vector(tuple(snap_scalar(value, spacing) for value in offset))
            self._object.location = self._start_location + offset
            context.view_layer.update()
            if self._snap_kind:
                context.workspace.status_text_set(
                    f"ShapeFlow Move: {self._anchor_kind.lower()} → {self._snap_kind.lower()} • release to confirm"
                )
        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self._dragging:
            self._dragging = False; self._snap_target = None; self._object = None; self._anchor = None
            bpy.ops.ed.undo_push(message="ShapeFlow Move Object")
            context.workspace.status_text_set("ShapeFlow Move: drag another object • Esc stops")
        return {'RUNNING_MODAL'}

    def _cancel_drag(self):
        if self._dragging and self._object:
            if self._copied:
                bpy.data.objects.remove(self._object, do_unlink=True)
            else:
                self._object.location = self._start_location
        self._dragging = False; self._object = None; self._anchor = None; self._snap_target = None

    def draw_preview(self, context):
        span = max(0.003, context.space_data.region_3d.view_distance * 0.02)
        if not self._dragging and self._hover_object is not None:
            cyan = (0.1, 0.85, 1.0, 1.0)
            snap = self._hover_snap
            if snap and snap.highlight:
                draw_polyline(list(snap.highlight), color=cyan, closed=snap.kind == 'FACE_CENTER')
            elif self._hover_face:
                draw_polyline(list(self._hover_face), color=cyan, closed=True)
            point = snap.point if snap else self._hover_hit
            draw_polyline([point - AXES['X'] * span, point + AXES['X'] * span], color=cyan)
            draw_polyline([point - AXES['Y'] * span, point + AXES['Y'] * span], color=cyan)
            draw_polyline([point - AXES['Z'] * span, point + AXES['Z'] * span], color=cyan)
        if self._anchor is not None and self._object is not None:
            moved_anchor = self._anchor + (self._object.location - self._start_location)
            draw_polyline([moved_anchor - AXES['X'] * span, moved_anchor + AXES['X'] * span], color=(1, .8, .1, 1))
            draw_polyline([moved_anchor - AXES['Y'] * span, moved_anchor + AXES['Y'] * span], color=(1, .8, .1, 1))
            draw_polyline([moved_anchor - AXES['Z'] * span, moved_anchor + AXES['Z'] * span], color=(1, .8, .1, 1))
        if self._snap_target is not None:
            draw_polyline([self._snap_target - AXES['X'] * span, self._snap_target + AXES['X'] * span], color=(.1, 1, .35, 1))
            draw_polyline([self._snap_target - AXES['Y'] * span, self._snap_target + AXES['Y'] * span], color=(.1, 1, .35, 1))
            draw_polyline([self._snap_target - AXES['Z'] * span, self._snap_target + AXES['Z'] * span], color=(.1, 1, .35, 1))

    def _finish(self, context):
        self.remove_preview(context); context.workspace.status_text_set(None)
