import bpy
from mathutils import Vector

from ..mesh.creation import create_rectangle_object
from ..utils.geometry import plane_axes, rectangle_corners
from ..utils.picking import ray_plane
from ..utils.viewport import ViewportPreviewMixin, draw_polyline


class SHAPEFLOW_OT_draw_rectangle(ViewportPreviewMixin, bpy.types.Operator):
    bl_idname = "shapeflow.draw_rectangle"
    bl_label = "Draw Rectangle"
    bl_description = "Draw a rectangular native mesh face"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}

    _start = None
    _current = None

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'VIEW_3D'

    def invoke(self, context, event):
        self._start = None
        self._current = None
        self.add_preview(context)
        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set("ShapeFlow Draw: click two corners • Esc cancels")
        return {'RUNNING_MODAL'}

    def _mouse_point(self, context, event):
        plane = context.scene.shapeflow.drawing_plane
        _, _, normal = plane_axes(plane)
        return ray_plane(context, (event.mouse_region_x, event.mouse_region_y), Vector((0, 0, 0)), normal)

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            self._finish(context)
            return {'CANCELLED'}
        if event.type == 'MOUSEMOVE':
            self._current = self._mouse_point(context, event)
            context.area.tag_redraw()
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            point = self._mouse_point(context, event)
            if point is None:
                self.report({'WARNING'}, "ShapeFlow: the view is parallel to the drawing plane")
                return {'RUNNING_MODAL'}
            if self._start is None:
                self._start = self._current = point
            else:
                try:
                    corners = rectangle_corners(self._start, point, context.scene.shapeflow.drawing_plane)
                    create_rectangle_object(context, corners)
                except ValueError as error:
                    self.report({'WARNING'}, f"ShapeFlow: {error}")
                    return {'RUNNING_MODAL'}
                self._finish(context)
                return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def draw_preview(self, _context):
        if self._start is not None and self._current is not None:
            plane = bpy.context.scene.shapeflow.drawing_plane
            draw_polyline(rectangle_corners(self._start, self._current, plane), closed=True)

    def _finish(self, context):
        self.remove_preview(context)
        context.workspace.status_text_set(None)

