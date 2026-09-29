import bpy

from ..utils.picking import pick_mesh_face, set_workplane_from_face, viewport_mouse
from ..utils.viewport import ViewportPreviewMixin, draw_polyline


class SHAPEFLOW_OT_pick_workplane(ViewportPreviewMixin, bpy.types.Operator):
    bl_idname = "shapeflow.pick_workplane"
    bl_label = "Capture Face Workplane"
    bl_description = "Hover a mesh face and click to use it as ShapeFlow's local drawing plane"
    bl_options = {'REGISTER', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'VIEW_3D' and context.window_manager.shapeflow_mode

    def invoke(self, context, event):
        viewport = viewport_mouse(context, event)
        if viewport and 0 <= viewport[1][0] <= viewport[0].width and 0 <= viewport[1][1] <= viewport[0].height:
            picked = pick_mesh_face(context, viewport[1])
            if picked and set_workplane_from_face(context, picked[0], picked[1], picked[2]):
                self.report({'INFO'}, "ShapeFlow: face workplane captured")
                return {'FINISHED'}
        self._picked = None
        context.window_manager.shapeflow_active_tool = 'NONE'
        self.add_preview(context)
        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set("ShapeFlow Workplane: hover a face and click • Esc cancels")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            self._finish(context)
            return {'CANCELLED'}
        viewport = viewport_mouse(context, event)
        if viewport is None or not (0 <= viewport[1][0] <= viewport[0].width and 0 <= viewport[1][1] <= viewport[0].height):
            return {'PASS_THROUGH'}
        if event.type == 'MOUSEMOVE':
            self._picked = pick_mesh_face(context, viewport[1])
            context.area.tag_redraw()
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self._picked = pick_mesh_face(context, viewport[1])
            if self._picked and set_workplane_from_face(context, self._picked[0], self._picked[1], self._picked[2]):
                self.report({'INFO'}, "ShapeFlow: face workplane captured")
                self._finish(context)
                return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def draw_preview(self, _context):
        if not self._picked:
            return
        obj, face_index, _hit, _normal = self._picked
        polygon = obj.data.polygons[face_index]
        points = [obj.matrix_world @ obj.data.vertices[index].co for index in polygon.vertices]
        draw_polyline(points, color=(1.0, 0.45, 0.08, 1.0), closed=True, width=3.0)

    def _finish(self, context):
        self.remove_preview(context)
        context.workspace.status_text_set(None)
