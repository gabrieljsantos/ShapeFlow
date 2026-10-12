import bpy
from mathutils import Vector

from ..mesh.transforms import (
    object_world_center, object_world_size, scale_factor_for_target_size, scale_matrix_about_pivot, scale_object,
)
from ..utils.geometry import typed_length_to_blender_units
from ..utils.picking import capture_hovered_workplane, pick_mesh_face, viewport_mouse
from ..utils.viewport import ViewportPreviewMixin, draw_polyline


BOX_EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)


class SHAPEFLOW_OT_transform_object(ViewportPreviewMixin, bpy.types.Operator):
    bl_idname = "shapeflow.transform_object"
    bl_label = "Scale Object"
    bl_options = {'REGISTER', 'BLOCKING'}

    mode: bpy.props.EnumProperty(items=(('SCALE', "Scale", "Scale by factor, percentage, or target size"),))

    @classmethod
    def description(cls, _context, properties):
        return "Scale by factor, percentage, or a requested final size"

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'VIEW_3D' and context.window_manager.shapeflow_mode

    def invoke(self, context, _event):
        context.window_manager.shapeflow_active_tool = self.mode
        self._object = None
        self._hovered = None
        self._dragging = False
        self._numeric = ""
        if context.scene.shapeflow.scale_input_mode == 'PERCENT':
            self._value = 100.0
        elif context.scene.shapeflow.scale_input_mode == 'DIMENSION':
            self._value = context.scene.shapeflow.scale_target_size
        else:
            self._value = 1.0
        self._start_mouse = None
        self._preview_corners = ()
        self.add_preview(context)
        context.window_manager.modal_handler_add(self)
        self._set_status(context)
        return {'RUNNING_MODAL'}

    def _set_status(self, context):
        if not self._dragging:
            context.workspace.status_text_set("ShapeFlow Scale: click an object and drag • W captures a face plane • Esc stops")
            return
        settings = context.scene.shapeflow
        suffix = {'FACTOR': 'x', 'PERCENT': '%', 'DIMENSION': f" {settings.length_unit.lower()}"}[settings.scale_input_mode]
        text = f"{self._numeric or f'{self._value:.4g}'}{suffix}"
        context.workspace.status_text_set(f"ShapeFlow Scale [{settings.scale_input_mode}, {settings.scale_axis}]: {text} • release or Enter confirms")

    def _update_hover(self, context, event):
        viewport = viewport_mouse(context, event)
        picked = pick_mesh_face(context, viewport[1]) if viewport else None
        self._hovered = picked[0] if picked else None

    def _begin(self, context, event):
        if self._hovered is None:
            return False
        self._object = self._hovered
        self._original_matrix = self._object.matrix_world.copy()
        self._pivot = object_world_center(self._object)
        self._corners = tuple(self._original_matrix @ Vector(corner) for corner in self._object.bound_box)
        self._start_mouse = viewport_mouse(context, event)[1]
        self._dragging = True
        self._update_preview(context)
        self._set_status(context)
        return True

    def _scale_factor(self, context):
        settings = context.scene.shapeflow
        numeric = float(self._numeric) if self._numeric else self._value
        if settings.scale_input_mode == 'PERCENT':
            return numeric / 100.0
        if settings.scale_input_mode == 'DIMENSION':
            target = typed_length_to_blender_units(
                numeric, settings.length_unit, context.scene.unit_settings.scale_length,
            )
            return scale_factor_for_target_size(self._object, target, settings.scale_axis)
        return numeric

    def _update_preview(self, context):
        if not self._object:
            self._preview_corners = ()
            return
        try:
            matrix = scale_matrix_about_pivot(self._scale_factor(context), self._pivot)
            self._preview_corners = tuple(matrix @ corner for corner in self._corners)
        except (ValueError, ZeroDivisionError):
            self._preview_corners = self._corners

    def _confirm(self, context):
        try:
            scale_object(self._object, self._scale_factor(context), self._pivot)
        except (ValueError, ZeroDivisionError) as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return False
        bpy.ops.ed.undo_push(message=f"ShapeFlow {self.mode.title()}")
        self._object = None; self._dragging = False; self._numeric = ""; self._preview_corners = ()
        self._set_status(context); context.area.tag_redraw()
        return True

    def modal(self, context, event):
        wm = context.window_manager
        if not wm.shapeflow_mode or wm.shapeflow_active_tool != self.mode:
            self._finish(context); return {'CANCELLED'}
        if event.type == 'ESC':
            wm.shapeflow_active_tool = 'NONE'; self._finish(context); return {'CANCELLED'}
        if event.type == 'RIGHTMOUSE':
            self._object = None; self._dragging = False; self._numeric = ""; self._preview_corners = ()
            self._set_status(context); context.area.tag_redraw(); return {'RUNNING_MODAL'}
        if event.type == 'W' and event.value == 'PRESS' and not self._dragging:
            if not capture_hovered_workplane(context, event):
                self.report({'WARNING'}, "ShapeFlow: hover a mesh face before pressing W")
            self._set_status(context); return {'RUNNING_MODAL'}
        viewport = viewport_mouse(context, event)
        if viewport and not (0 <= viewport[1][0] <= viewport[0].width and 0 <= viewport[1][1] <= viewport[0].height):
            return {'PASS_THROUGH'}
        if event.type == 'MOUSEMOVE' and not self._dragging:
            self._update_hover(context, event); context.area.tag_redraw()
        elif event.type == 'MOUSEMOVE' and not self._numeric:
            pixels = viewport[1][0] - self._start_mouse[0]
            settings = context.scene.shapeflow
            if settings.scale_input_mode == 'PERCENT':
                self._value = max(0.1, 100.0 + pixels)
            elif settings.scale_input_mode == 'DIMENSION':
                base_world = object_world_size(self._object, settings.scale_axis)
                factor = max(0.001, 1.0 + pixels * 0.01)
                world_size = base_world * factor
                unit_factor = typed_length_to_blender_units(
                    1.0, settings.length_unit, context.scene.unit_settings.scale_length,
                )
                self._value = world_size / unit_factor
            else:
                self._value = max(0.001, 1.0 + pixels * 0.01)
            self._update_preview(context); self._set_status(context); context.area.tag_redraw()
        if self._dragging and event.ascii and (event.ascii.isdigit() or event.ascii in '.,-'):
            self._numeric += '.' if event.ascii == ',' else event.ascii
            try:
                self._value = float(self._numeric)
                if self.mode == 'SCALE' and context.scene.shapeflow.scale_input_mode == 'DIMENSION':
                    context.scene.shapeflow.scale_target_size = max(0.0001, self._value)
                self._update_preview(context)
            except ValueError:
                pass
            self._set_status(context); context.area.tag_redraw(); return {'RUNNING_MODAL'}
        if self._dragging and event.type == 'BACK_SPACE' and event.value == 'PRESS':
            self._numeric = self._numeric[:-1]; self._update_preview(context); self._set_status(context); return {'RUNNING_MODAL'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS' and not self._dragging:
            self._begin(context, event); return {'RUNNING_MODAL'}
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self._dragging:
            self._confirm(context); return {'RUNNING_MODAL'}
        if event.type in {'RET', 'NUMPAD_ENTER'} and self._dragging:
            self._confirm(context); return {'RUNNING_MODAL'}
        return {'RUNNING_MODAL'}

    def draw_preview(self, _context):
        corners = self._preview_corners
        if corners:
            for first, second in BOX_EDGES:
                draw_polyline((corners[first], corners[second]), color=(1.0, 0.55, 0.1, 1.0), width=2.5)

    def _finish(self, context):
        self.remove_preview(context)
        context.workspace.status_text_set(None)
