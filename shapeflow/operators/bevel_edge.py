import bpy

from ..mesh.bevel import bevel_edge
from ..utils.geometry import (
    blender_units_to_typed_length, snap_scalar, typed_length_to_blender_units,
    unit_suffix,
)
from ..utils.picking import nearest_face_boundary, pick_mesh_face, viewport_mouse
from ..utils.viewport import ViewportPreviewMixin, draw_polyline


class SHAPEFLOW_OT_bevel_edge(ViewportPreviewMixin, bpy.types.Operator):
    bl_idname = "shapeflow.bevel_edge"
    bl_label = "Fillet / Chamfer Edge"
    bl_options = {'REGISTER', 'BLOCKING'}

    mode: bpy.props.EnumProperty(items=(
        ('FILLET', "Fillet", "Round an edge with multiple bevel segments"),
        ('CHAMFER', "Chamfer", "Cut an edge with one straight bevel segment"),
    ))

    @classmethod
    def description(cls, _context, properties):
        return "Round an edge with native Blender bevel geometry" if properties.mode == 'FILLET' else "Cut an edge with a native one-segment bevel"

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'VIEW_3D' and context.window_manager.shapeflow_mode

    def invoke(self, context, _event):
        context.window_manager.shapeflow_active_tool = self.mode
        self._reset()
        self.add_preview(context)
        context.window_manager.modal_handler_add(self)
        self._set_status(context)
        return {'RUNNING_MODAL'}

    def _reset(self):
        self._hovered = None
        self._picked = None
        self._dragging = False
        self._width = 0.0
        self._numeric = ""
        self._start_mouse = None

    def _set_status(self, context):
        label = "Fillet" if self.mode == 'FILLET' else "Chamfer"
        if not self._dragging:
            context.workspace.status_text_set(f"ShapeFlow {label}: hover an edge, then click and drag • Esc stops")
            return
        settings = context.scene.shapeflow
        value = self._numeric or f"{blender_units_to_typed_length(self._width, settings.length_unit, context.scene.unit_settings.scale_length):.4g} {unit_suffix(settings.length_unit)}"
        context.workspace.status_text_set(
            f"ShapeFlow {label}: {value} • Alt temporarily free • type exact value • release/Enter confirms"
        )

    def _update_hover(self, context, event):
        viewport = viewport_mouse(context, event)
        picked = pick_mesh_face(context, viewport[1]) if viewport else None
        if picked is None:
            self._hovered = None
            return
        obj, face_index, hit, _normal = picked
        boundary = nearest_face_boundary(obj, face_index, hit)
        if boundary is None:
            self._hovered = None
            return
        edge = obj.data.edges[boundary[2]]
        points = tuple(obj.matrix_world @ obj.data.vertices[index].co for index in edge.vertices)
        self._hovered = (obj, edge.index, points)

    def _begin_drag(self, context, event):
        if self._hovered is None:
            return False
        self._picked = self._hovered
        self._start_mouse = viewport_mouse(context, event)[1]
        self._dragging = True
        self._set_status(context)
        return True

    def _confirm(self, context):
        try:
            bevel_edge(
                self._picked[0], self._picked[1], self._width,
                segments=6 if self.mode == 'FILLET' else 1,
            )
        except ValueError as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return False
        bpy.ops.ed.undo_push(message=f"ShapeFlow {self.mode.title()}")
        self._reset(); self._set_status(context); context.area.tag_redraw()
        return True

    def modal(self, context, event):
        wm = context.window_manager
        if not wm.shapeflow_mode or wm.shapeflow_active_tool != self.mode:
            self._finish(context); return {'CANCELLED'}
        if event.type == 'ESC':
            wm.shapeflow_active_tool = 'NONE'; self._finish(context); return {'CANCELLED'}
        if event.type == 'RIGHTMOUSE':
            self._reset(); self._set_status(context); context.area.tag_redraw(); return {'RUNNING_MODAL'}
        viewport = viewport_mouse(context, event)
        if viewport and not (0 <= viewport[1][0] <= viewport[0].width and 0 <= viewport[1][1] <= viewport[0].height):
            return {'PASS_THROUGH'}
        if event.type == 'MOUSEMOVE' and not self._dragging:
            self._update_hover(context, event); context.area.tag_redraw()
        elif event.type == 'MOUSEMOVE' and not self._numeric:
            raw = abs(viewport[1][0] - self._start_mouse[0]) * 0.01
            settings = context.scene.shapeflow
            if settings.grid_snap and not event.alt:
                spacing = typed_length_to_blender_units(settings.grid_spacing, settings.length_unit, context.scene.unit_settings.scale_length)
                self._width = abs(snap_scalar(raw, spacing))
            else:
                self._width = raw
            self._set_status(context); context.area.tag_redraw()
        if self._dragging and event.ascii and (event.ascii.isdigit() or event.ascii in '.,'):
            self._numeric += '.' if event.ascii == ',' else event.ascii
            try:
                self._width = typed_length_to_blender_units(float(self._numeric), context.scene.shapeflow.length_unit, context.scene.unit_settings.scale_length)
            except ValueError:
                pass
            self._set_status(context); return {'RUNNING_MODAL'}
        if self._dragging and event.type == 'BACK_SPACE' and event.value == 'PRESS':
            self._numeric = self._numeric[:-1]; self._set_status(context); return {'RUNNING_MODAL'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS' and not self._dragging:
            self._begin_drag(context, event); return {'RUNNING_MODAL'}
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self._dragging:
            self._confirm(context); return {'RUNNING_MODAL'}
        if event.type in {'RET', 'NUMPAD_ENTER'} and self._dragging:
            self._confirm(context); return {'RUNNING_MODAL'}
        return {'RUNNING_MODAL'}

    def draw_preview(self, _context):
        target = self._picked or self._hovered
        if target:
            color = (1.0, 0.55, 0.1, 1.0) if self._picked else (0.2, 1.0, 0.35, 1.0)
            draw_polyline(target[2], color=color, width=4.0)

    def _finish(self, context):
        self.remove_preview(context)
        context.workspace.status_text_set(None)
