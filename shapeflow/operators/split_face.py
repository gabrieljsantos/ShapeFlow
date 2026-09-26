import bpy

from ..mesh.splitting import split_face_between_edges
from ..utils.picking import nearest_face_boundary, pick_mesh_face
from ..utils.viewport import ViewportPreviewMixin, draw_polyline


class SHAPEFLOW_OT_split_face(ViewportPreviewMixin, bpy.types.Operator):
    bl_idname = "shapeflow.split_face"
    bl_label = "Split Face"
    bl_description = "Draw a cut between two boundary edges of one face"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}

    _target = None
    _start = None
    _hover = None

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'VIEW_3D'

    def invoke(self, context, event):
        picked = pick_mesh_face(context, (event.mouse_region_x, event.mouse_region_y))
        if picked is None:
            self.report({'WARNING'}, "ShapeFlow: place the cursor over the face to split")
            return {'CANCELLED'}
        obj, face_index, location, _normal = picked
        self._target = (obj, face_index)
        self._start = None
        self._hover = nearest_face_boundary(obj, face_index, location)
        context.view_layer.objects.active = obj
        obj.select_set(True)
        self.add_preview(context)
        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set("ShapeFlow Split: click two different boundary edges • Esc cancels")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            self._finish(context)
            return {'CANCELLED'}
        if event.type == 'MOUSEMOVE':
            picked = pick_mesh_face(context, (event.mouse_region_x, event.mouse_region_y))
            if picked and picked[0] == self._target[0] and picked[1] == self._target[1]:
                self._hover = nearest_face_boundary(picked[0], picked[1], picked[2])
                context.area.tag_redraw()
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS' and self._hover:
            if self._start is None:
                self._start = self._hover
            else:
                if self._start[2] == self._hover[2]:
                    self.report({'WARNING'}, "ShapeFlow: choose a different boundary edge")
                    return {'RUNNING_MODAL'}
                obj, face_index = self._target
                try:
                    split_face_between_edges(
                        obj, face_index,
                        self._start[2], self._start[3],
                        self._hover[2], self._hover[3],
                    )
                except ValueError as error:
                    self.report({'WARNING'}, f"ShapeFlow: {error}")
                    return {'RUNNING_MODAL'}
                self._finish(context)
                return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def draw_preview(self, _context):
        if self._hover:
            point = self._hover[1]
            if self._start:
                draw_polyline([self._start[1], point], color=(1.0, 0.15, 0.15, 1.0))

    def _finish(self, context):
        self.remove_preview(context)
        context.workspace.status_text_set(None)

