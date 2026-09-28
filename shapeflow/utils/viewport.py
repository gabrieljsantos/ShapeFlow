import bpy
import blf
import gpu
from math import cos, pi, sin
from mathutils import Vector
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader


def draw_polyline(points, color=(0.15, 0.8, 1.0, 1.0), closed=False, width=2.0):
    if len(points) < 2:
        return
    coords = list(points)
    if closed:
        coords.append(coords[0])
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": coords})
    gpu.state.line_width_set(width)
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)
    gpu.state.line_width_set(1.0)


def draw_snap_circle(context, point, radius=5.0, fill=(0.1, 0.85, 1.0, 0.22),
                     outline=(0.75, 0.95, 1.0, 0.9), width=1.5):
    """Draw a viewport-facing circular snap marker with a pixel-stable size."""
    region = next((item for item in context.area.regions if item.type == 'WINDOW'), context.region)
    rv3d = context.space_data.region_3d
    center = view3d_utils.location_3d_to_region_2d(region, rv3d, point)
    if center is None:
        return

    ring = []
    for index in range(25):
        angle = 2.0 * pi * index / 24.0
        screen = center + Vector((cos(angle) * radius, sin(angle) * radius))
        ring.append(view3d_utils.region_2d_to_location_3d(region, rv3d, screen, point))

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    gpu.state.blend_set('ALPHA')
    if fill[3] > 0.0:
        triangles = []
        for index in range(24):
            triangles.extend((point, ring[index], ring[index + 1]))
        batch = batch_for_shader(shader, 'TRIS', {"pos": triangles})
        shader.bind()
        shader.uniform_float("color", fill)
        batch.draw(shader)

    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": ring})
    gpu.state.line_width_set(width)
    shader.bind()
    shader.uniform_float("color", outline)
    batch.draw(shader)
    gpu.state.line_width_set(1.0)
    gpu.state.blend_set('NONE')


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
