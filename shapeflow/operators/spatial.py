import bpy
from mathutils import Vector
from bpy_extras import view3d_utils

from ..utils.geometry import snap_scalar, typed_length_to_blender_units
from ..utils.picking import pick_mesh_face, ray_plane, viewport_mouse
from ..utils.snapping import (
    collect_object_snap_geometry,
    collect_scene_snap_geometry,
    nearest_screen_geometry,
)
from ..utils.viewport import ViewportPreviewMixin, draw_polyline, draw_snap_circle


AXES = {'X': Vector((1, 0, 0)), 'Y': Vector((0, 1, 0)), 'Z': Vector((0, 0, 1))}

SOFT_POINT = (0.65, 0.88, 1.0, 0.62)
ACTIVE_POINT = (1.0, 0.82, 0.16, 1.0)
TARGET_POINT = (0.2, 1.0, 0.42, 1.0)
RELATED_EDGE = (0.18, 0.62, 1.0, 0.95)


def _draw_related_highlight(kind, highlight, color, offset=None):
    if not highlight:
        return
    if offset is None:
        offset = Vector()
    if kind == 'VERTEX':
        for edge in highlight:
            draw_polyline([point + offset for point in edge], color=color, width=3.0)
        return
    draw_polyline([point + offset for point in highlight], color=color,
                  closed=kind in {'FACE_CENTER', 'FACE_POINT'}, width=3.0)


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
    distance = pixels * max(context.space_data.region_3d.view_distance, 0.001) * 2.0 / max(region.height, 1)
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


class SHAPEFLOW_OT_move_object(_SpatialToolMixin, bpy.types.Operator):
    bl_idname = "shapeflow.move_object"
    bl_label = "Move Object"
    bl_description = "M: drag an object; hold Ctrl when grabbing to deform only a vertex, edge, or face"
    bl_options = {'REGISTER', 'BLOCKING'}

    def invoke(self, context, _event):
        context.window_manager.shapeflow_active_tool = 'MOVE'
        self._dragging = False; self._object = None; self._copied = False
        self._anchor = None; self._anchor_highlight = None
        self._snap_target = None; self._snap_kind = None; self._snap_highlight = None
        self._hover_object = None; self._hover_snap = None; self._hover_face = None
        self._hover_face_index = None
        self._hover_points = (); self._nearby_targets = ()
        self._partial = False; self._partial_vertices = (); self._partial_start = {}
        self._current_offset = Vector()
        self.add_preview(context); context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set("ShapeFlow Move: drag an object • Copy duplicates first • Esc stops")
        return {'RUNNING_MODAL'}

    def _update_hover(self, context, region, mouse):
        picked = pick_mesh_face(context, mouse)
        if not picked:
            self._hover_object = None; self._hover_snap = None; self._hover_face = None
            self._hover_face_index = None
            self._hover_points = ()
            context.area.tag_redraw()
            return
        obj, face_index, hit, _normal = picked
        candidates, edges = collect_object_snap_geometry(obj)
        self._hover_snap = nearest_screen_geometry(
            context, region, mouse, candidates, edges, context.scene.shapeflow.snap_distance
        )
        polygon = obj.data.polygons[face_index]
        self._hover_object = obj
        self._hover_face_index = face_index
        self._hover_hit = hit.copy()
        self._hover_face = tuple(obj.matrix_world @ obj.data.vertices[index].co for index in polygon.vertices)
        face_points = list(self._hover_face)
        for index, point in enumerate(self._hover_face):
            face_points.append((point + self._hover_face[(index + 1) % len(self._hover_face)]) * 0.5)
        self._hover_points = tuple(face_points)
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
            self._partial = bool(event.ctrl)
            if context.scene.shapeflow.copy_mode and not self._partial:
                duplicate = obj.copy(); duplicate.data = obj.data.copy(); context.collection.objects.link(duplicate); obj = duplicate
                self._copied = True
            else:
                self._copied = False
            self._object = obj
            self._start_location = obj.location.copy()
            self._anchor = source_snap.point.copy() if source_snap else hit.copy()
            self._anchor_kind = source_snap.kind if source_snap else "FACE_POINT"
            self._anchor_highlight = source_snap.highlight if source_snap else self._hover_face
            if self._partial:
                self._partial_vertices = self._resolve_partial_vertices(obj, self._anchor_kind, self._anchor)
                self._partial_start = {
                    index: obj.data.vertices[index].co.copy() for index in self._partial_vertices
                }
            else:
                self._partial_vertices = (); self._partial_start = {}
            self._current_offset = Vector()
            self._mouse_start = mouse
            self._candidates, self._edges = collect_scene_snap_geometry(context, exclude=obj)
            self._snap_target = None; self._snap_kind = None; self._snap_highlight = None; self._dragging = True
            self._nearby_targets = ()
            self._hover_object = None
            mode = "partial geometry" if self._partial else "object"
            context.workspace.status_text_set(
                f"ShapeFlow Move: grabbed {self._anchor_kind.lower()} ({mode}) • drag near target geometry"
            )
        elif event.type == 'MOUSEMOVE' and self._dragging:
            settings = context.scene.shapeflow
            target = nearest_screen_geometry(
                context, region, mouse, self._candidates, self._edges, settings.snap_distance
            )
            rv3d = context.space_data.region_3d
            nearby_radius = settings.snap_distance * 2.0
            self._nearby_targets = tuple(
                candidate.point for candidate in self._candidates
                if (screen := view3d_utils.location_3d_to_region_2d(region, rv3d, candidate.point)) is not None
                and (screen - Vector(mouse)).length <= nearby_radius
            )
            if target and settings.snap_enabled and settings.geometry_snap and not event.shift:
                offset = target.point - self._anchor
                changed_target = self._snap_target is None or (self._snap_target - target.point).length > 1.0e-7
                self._snap_target = target.point.copy(); self._snap_kind = target.kind
                self._snap_highlight = target.highlight
                if changed_target:
                    screen = view3d_utils.location_3d_to_region_2d(
                        region, context.space_data.region_3d, target.point
                    )
                    if screen is not None:
                        context.window.cursor_warp(int(region.x + screen.x), int(region.y + screen.y))
            else:
                self._snap_target = None; self._snap_kind = None; self._snap_highlight = None
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
            self._current_offset = offset.copy()
            if self._partial:
                local_offset = self._object.matrix_world.inverted().to_3x3() @ offset
                for index, coordinate in self._partial_start.items():
                    self._object.data.vertices[index].co = coordinate + local_offset
                self._object.data.update()
            else:
                self._object.location = self._start_location + offset
            context.view_layer.update()
            if self._snap_kind:
                context.workspace.status_text_set(
                    f"ShapeFlow Move: {self._anchor_kind.lower()} → {self._snap_kind.lower()} • release to confirm"
                )
        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self._dragging:
            self._dragging = False; self._snap_target = None; self._snap_highlight = None
            self._object = None; self._anchor = None; self._anchor_highlight = None
            self._partial = False; self._partial_vertices = (); self._partial_start = {}
            self._current_offset = Vector()
            self._nearby_targets = ()
            bpy.ops.ed.undo_push(message="ShapeFlow Move Object")
            context.workspace.status_text_set("ShapeFlow Move: drag another object • Esc stops")
        return {'RUNNING_MODAL'}

    def _cancel_drag(self):
        if self._dragging and self._object:
            if self._copied:
                bpy.data.objects.remove(self._object, do_unlink=True)
            elif self._partial:
                for index, coordinate in self._partial_start.items():
                    self._object.data.vertices[index].co = coordinate
                self._object.data.update()
            else:
                self._object.location = self._start_location
        self._dragging = False; self._object = None; self._anchor = None; self._anchor_highlight = None
        self._snap_target = None; self._snap_highlight = None
        self._nearby_targets = ()
        self._partial = False; self._partial_vertices = (); self._partial_start = {}
        self._current_offset = Vector()

    def _resolve_partial_vertices(self, obj, kind, anchor):
        """Choose the mesh component controlled by Ctrl at drag start."""
        inverse = obj.matrix_world.inverted()
        local_anchor = inverse @ anchor
        if kind == 'VERTEX':
            vertex = min(obj.data.vertices, key=lambda item: (item.co - local_anchor).length_squared)
            return (vertex.index,)
        if kind in {'EDGE', 'MIDPOINT'}:
            edge = min(
                obj.data.edges,
                key=lambda item: (
                    (obj.data.vertices[item.vertices[0]].co + obj.data.vertices[item.vertices[1]].co) * 0.5
                    - local_anchor
                ).length_squared,
            )
            return tuple(edge.vertices)
        if self._hover_face_index is not None:
            return tuple(obj.data.polygons[self._hover_face_index].vertices)
        return ()

    def draw_preview(self, context):
        if not self._dragging and self._hover_object is not None:
            cyan = (0.1, 0.85, 1.0, 1.0)
            snap = self._hover_snap
            for point in self._hover_points:
                draw_snap_circle(context, point, radius=3.5, fill=(0.1, 0.7, 1.0, 0.10), outline=SOFT_POINT)
            if snap and snap.highlight:
                _draw_related_highlight(snap.kind, snap.highlight, RELATED_EDGE)
            elif self._hover_face:
                draw_polyline(list(self._hover_face), color=cyan, closed=True)
            point = snap.point if snap else self._hover_hit
            draw_snap_circle(context, point, radius=6.0, fill=(1.0, 0.72, 0.08, 0.72),
                             outline=ACTIVE_POINT, width=2.5)
        if self._anchor is not None and self._object is not None:
            move_offset = self._current_offset if self._partial else self._object.location - self._start_location
            moved_anchor = self._anchor + move_offset
            _draw_related_highlight(self._anchor_kind, self._anchor_highlight,
                                    ACTIVE_POINT, move_offset)
            draw_snap_circle(context, moved_anchor, radius=6.0, fill=(1.0, 0.72, 0.08, 0.72),
                             outline=ACTIVE_POINT, width=2.5)
        for point in self._nearby_targets:
            if self._snap_target is None or (point - self._snap_target).length > 1.0e-7:
                draw_snap_circle(context, point, radius=3.5, fill=(0.1, 0.85, 1.0, 0.10), outline=SOFT_POINT)
        if self._snap_target is not None:
            _draw_related_highlight(self._snap_kind, self._snap_highlight, TARGET_POINT)
            draw_snap_circle(context, self._snap_target, radius=6.5, fill=(0.12, 0.9, 0.3, 0.72),
                             outline=TARGET_POINT, width=2.5)

    def _finish(self, context):
        self.remove_preview(context); context.workspace.status_text_set(None)
