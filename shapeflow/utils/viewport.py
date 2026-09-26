import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader


def draw_polyline(points, color=(0.15, 0.8, 1.0, 1.0), closed=False):
    if len(points) < 2:
        return
    coords = list(points)
    if closed:
        coords.append(coords[0])
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": coords})
    gpu.state.line_width_set(2.0)
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)
    gpu.state.line_width_set(1.0)


class ViewportPreviewMixin:
    _draw_handle = None
    _hud_handle = None

    def add_preview(self, context):
        self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_preview, (context,), 'WINDOW', 'POST_VIEW')
        if hasattr(self, "draw_hud"):
            self._hud_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_hud, (context,), 'WINDOW', 'POST_PIXEL')

    def remove_preview(self, context):
        if self._draw_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            self._draw_handle = None
        if self._hud_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._hud_handle, 'WINDOW')
            self._hud_handle = None
        if context.area:
            context.area.tag_redraw()


def draw_text(position, text, color=(1.0, 1.0, 1.0, 1.0), size=14):
    font_id = 0
    blf.position(font_id, position[0], position[1], 0)
    blf.size(font_id, size)
    blf.color(font_id, *color)
    blf.draw(font_id, text)
