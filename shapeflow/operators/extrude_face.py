import bpy
from bpy_extras import view3d_utils

from ..mesh.extrusion import extrude_face
from ..utils.geometry import typed_length_to_blender_units, unit_suffix
from ..utils.picking import pick_mesh_face, viewport_mouse
from ..utils.viewport import ViewportPreviewMixin, draw_polyline


class SHAPEFLOW_OT_extrude_face(ViewportPreviewMixin, bpy.types.Operator):
    bl_idname = "shapeflow.extrude_face"
    bl_label = "Extrude Face"
    bl_description = "Click a face, move to set the distance, and click to confirm"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}

    _hovered = None
    _picked = None
    _dragging = False
    _distance = 0.0
    _start_mouse = None
    _numeric = ""

    @classmethod
    def poll(cls, context):
        return (
            context.area and context.area.type == 'VIEW_3D'
            and context.window_manager.shapeflow_mode
        )

    def invoke(self, context, event):
        self._hovered = None
        self._picked = None
        self._dragging = False
        self._distance = 0.0
        self._numeric = ""
        self.add_preview(context)
        context.window_manager.modal_handler_add(self)
        self._set_status(context)
        return {'RUNNING_MODAL'}

    def _set_status(self, context):
        suffix = unit_suffix(context.scene.shapeflow.length_unit)
        if self._dragging:
            value = self._numeric if self._numeric else f"{self._distance:.4g} BU"
            context.workspace.status_text_set(
                f"ShapeFlow Extrude: drag • type a value ({suffix}) [{value}] • release/Enter confirms • Esc cancels"
            )
        else:
            context.workspace.status_text_set("ShapeFlow Extrude: hover a face, then click and drag • Esc cancels")

    def _update_hover(self, context, event):
        viewport = viewport_mouse(context, event)
        picked = pick_mesh_face(context, viewport[1]) if viewport else None
        if picked is None:
            self._hovered = None
            return
        obj, face_index, _location, _normal = picked
        if face_index >= len(obj.data.polygons):
            self._hovered = None
            return
        polygon = obj.data.polygons[face_index]
        points = [obj.matrix_world @ obj.data.vertices[i].co for i in polygon.vertices]
        self._hovered = (obj, face_index, points)

    def _begin_drag(self, context, event):
        if self._hovered is None:
            return False
        obj, face_index, points = self._hovered
        context.view_layer.objects.active = obj
        for selected in context.selected_objects:
            selected.select_set(False)
        obj.select_set(True)
        polygon = obj.data.polygons[face_index]
        self._picked = (obj, face_index, points)
        self._normal = (obj.matrix_world.to_3x3() @ polygon.normal).normalized()
        self._center = obj.matrix_world @ polygon.center
        viewport = viewport_mouse(context, event)
        self._start_mouse = viewport[1]
        self._dragging = True
        self._set_status(context)
        return True

    def _confirm(self, context):
        obj, face_index, _points = self._picked
        try:
            extrude_face(obj, face_index, self._distance, copy=context.scene.shapeflow.copy_mode)
        except ValueError as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return False
        self._finish(context)
        return True

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            self._finish(context)
            return {'CANCELLED'}
        if event.type == 'MOUSEMOVE' and not self._dragging:
            self._update_hover(context, event)
            context.area.tag_redraw()
        elif event.type == 'MOUSEMOVE' and not self._numeric:
            viewport = viewport_mouse(context, event)
            region = viewport[0]
            mouse = viewport[1]
            rv3d = context.space_data.region_3d
            center_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, self._center)
            normal_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, self._center + self._normal)
            if center_2d is not None and normal_2d is not None:
                axis = normal_2d - center_2d
                if axis.length > 1.0e-5:
                    axis.normalize()
                    delta = (mouse[0] - self._start_mouse[0], mouse[1] - self._start_mouse[1])
                    self._distance = (delta[0] * axis.x + delta[1] * axis.y) * 0.01
            context.area.tag_redraw()
            self._set_status(context)
        if self._dragging and event.ascii and (event.ascii.isdigit() or event.ascii in '.,-'):
            character = '.' if event.ascii == ',' else event.ascii
            self._numeric += character
            try:
                self._distance = typed_length_to_blender_units(
                    float(self._numeric),
                    context.scene.shapeflow.length_unit,
                    context.scene.unit_settings.scale_length,
                )
            except ValueError:
                pass
            self._set_status(context)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        if self._dragging and event.type == 'BACK_SPACE' and event.value == 'PRESS':
            self._numeric = self._numeric[:-1]
            if self._numeric not in {'', '-'}:
                self._distance = typed_length_to_blender_units(
                    float(self._numeric), context.scene.shapeflow.length_unit,
                    context.scene.unit_settings.scale_length,
                )
            self._set_status(context)
            return {'RUNNING_MODAL'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS' and not self._dragging:
            if self._begin_drag(context, event):
                return {'RUNNING_MODAL'}
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self._dragging:
            return {'FINISHED'} if self._confirm(context) else {'RUNNING_MODAL'}
        if event.type in {'RET', 'NUMPAD_ENTER'} and self._dragging:
            return {'FINISHED'} if self._confirm(context) else {'RUNNING_MODAL'}
        return {'RUNNING_MODAL'}

    def draw_preview(self, _context):
        if self._picked:
            points = [point + self._normal * self._distance for point in self._picked[2]]
            draw_polyline(points, color=(1.0, 0.55, 0.1, 1.0), closed=True)
            for source, target in zip(self._picked[2], points):
                draw_polyline([source, target], color=(1.0, 0.55, 0.1, 0.8))
        elif self._hovered:
            draw_polyline(self._hovered[2], color=(0.2, 1.0, 0.35, 1.0), closed=True)

    def _finish(self, context):
        self.remove_preview(context)
        context.workspace.status_text_set(None)
