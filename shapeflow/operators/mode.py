import bpy


class SHAPEFLOW_OT_toggle_mode(bpy.types.Operator):
    bl_idname = "shapeflow.toggle_mode"
    bl_label = "Toggle ShapeFlow Mode"
    bl_description = "Enter or leave ShapeFlow's viewport interaction mode"

    enable: bpy.props.BoolProperty(default=True, options={'SKIP_SAVE'})

    def execute(self, context):
        window_manager = context.window_manager
        window_manager.shapeflow_mode = self.enable
        window_manager.shapeflow_workspace = context.workspace.name if self.enable else ""
        if not self.enable:
            window_manager.shapeflow_active_tool = 'NONE'
        if self.enable:
            self.report({'INFO'}, "ShapeFlow Mode enabled")
        else:
            context.workspace.status_text_set(None)
            self.report({'INFO'}, "ShapeFlow Mode disabled")
        if context.area:
            context.area.tag_redraw()
        return {'FINISHED'}

class SHAPEFLOW_OT_activate_tool(bpy.types.Operator):
    bl_idname = "shapeflow.activate_tool"
    bl_label = "Activate ShapeFlow Tool"

    tool: bpy.props.EnumProperty(
        items=(
            ('RECTANGLE', "Rectangle", "Create rectangles continuously"),
            ('EXTRUDE', "Extrude", "Push or pull faces continuously"),
            ('MOVE', "Move", "Move whole objects"),
        )
    )
    rectangle_variant: bpy.props.EnumProperty(items=(
        ('SETTINGS', "Current settings", "Use the current rectangle options"),
        ('CORNER', "Corner to corner", "Define opposite corners"),
        ('SQUARE', "Regular square", "Keep all sides equal"),
        ('CENTER', "Mirrored from center", "Expand symmetrically from the first point"),
    ), default='SETTINGS', options={'HIDDEN'})

    @classmethod
    def description(cls, _context, properties):
        descriptions = {
            'RECTANGLE': "Rectangle: create consecutive rectangular faces; remains active until Escape or another tool",
            'EXTRUDE': "Extrude: push or pull consecutive faces; remains active until Escape or another tool",
            'MOVE': "Move: drag whole objects with axis/plane constraints and geometry snapping",
        }
        return descriptions.get(properties.tool, "Activate a ShapeFlow tool")

    @classmethod
    def poll(cls, context):
        return context.window_manager.shapeflow_mode

    def execute(self, context):
        window_manager = context.window_manager
        if self.tool == 'RECTANGLE':
            settings = context.scene.shapeflow
            if self.rectangle_variant == 'CORNER':
                settings.creation_origin, settings.proportional_creation = 'DIAMETER', False
            elif self.rectangle_variant == 'SQUARE':
                settings.creation_origin, settings.proportional_creation = 'DIAMETER', True
            elif self.rectangle_variant == 'CENTER':
                settings.creation_origin, settings.proportional_creation = 'CENTER', False
        if window_manager.shapeflow_active_tool == self.tool:
            return {'FINISHED'}
        window_manager.shapeflow_active_tool = self.tool
        if self.tool == 'RECTANGLE':
            bpy.ops.shapeflow.draw_rectangle('INVOKE_DEFAULT')
        elif self.tool == 'EXTRUDE':
            bpy.ops.shapeflow.extrude_face('INVOKE_DEFAULT')
        elif self.tool == 'MOVE':
            bpy.ops.shapeflow.move_object('INVOKE_DEFAULT')
        return {'FINISHED'}
