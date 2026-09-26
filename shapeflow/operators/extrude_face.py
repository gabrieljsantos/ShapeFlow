import bpy
from bpy_extras import view3d_utils

from ..mesh.extrusion import extrude_face
from ..utils.picking import pick_mesh_face
from ..utils.viewport import ViewportPreviewMixin, draw_polyline


class SHAPEFLOW_OT_extrude_face(ViewportPreviewMixin, bpy.types.Operator):
    bl_idname = "shapeflow.extrude_face"
    bl_label = "Extrude Face"
    bl_description = "Click a face, move to set the distance, and click to confirm"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}

    _picked = None
    _distance = 0.0
    _start_mouse = None
    _numeric = ""

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'VIEW_3D'

    def invoke(self, context, event):
        picked = pick_mesh_face(context, (event.mouse_region_x, event.mouse_region_y))
        if picked is None:
            self.report({'WARNING'}, "ShapeFlow: place the cursor over a mesh face before starting Extrude")
            return {'CANCELLED'}
        obj, face_index, _location, _normal = picked
        context.view_layer.objects.active = obj
        obj.select_set(True)
        polygon = obj.data.polygons[face_index]
        self._picked = (obj, face_index, [obj.matrix_world @ obj.data.vertices[i].co for i in polygon.vertices])
        self._normal = (obj.matrix_world.to_3x3() @ polygon.normal).normalized()
        self._center = obj.matrix_world @ polygon.center
        self._start_mouse = (event.mouse_region_x, event.mouse_region_y)
        self._distance = 0.0
        self._numeric = ""
        self.add_preview(context)
        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set("ShapeFlow Extrude: move and click • type a distance • Esc cancels")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            self._finish(context)
            return {'CANCELLED'}
        if event.type == 'MOUSEMOVE' and not self._numeric:
            center_2d = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, self._center)
            normal_2d = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, self._center + self._normal)
            if center_2d is not None and normal_2d is not None:
                axis = normal_2d - center_2d
                if axis.length > 1.0e-5:
                    axis.normalize()
                    delta = (event.mouse_region_x - self._start_mouse[0], event.mouse_region_y - self._start_mouse[1])
                    self._distance = (delta[0] * axis.x + delta[1] * axis.y) * 0.01
            context.area.tag_redraw()
        if event.ascii and (event.ascii.isdigit() or event.ascii in '.-'):
            self._numeric += event.ascii
            try:
                self._distance = float(self._numeric)
            except ValueError:
                pass
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        if event.type == 'BACK_SPACE' and event.value == 'PRESS':
            self._numeric = self._numeric[:-1]
            return {'RUNNING_MODAL'}
        if (event.type == 'LEFTMOUSE' and event.value == 'PRESS') or event.type in {'RET', 'NUMPAD_ENTER'}:
            obj, face_index, _points = self._picked
            try:
                extrude_face(obj, face_index, self._distance)
            except ValueError as error:
                self.report({'WARNING'}, f"ShapeFlow: {error}")
                return {'RUNNING_MODAL'}
            self._finish(context)
            return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def draw_preview(self, _context):
        if self._picked:
            points = [point + self._normal * self._distance for point in self._picked[2]]
            draw_polyline(points, color=(1.0, 0.55, 0.1, 1.0), closed=True)
            for source, target in zip(self._picked[2], points):
                draw_polyline([source, target], color=(1.0, 0.55, 0.1, 0.8))

    def _finish(self, context):
        self.remove_preview(context)
        context.workspace.status_text_set(None)

