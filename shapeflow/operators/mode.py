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


class SHAPEFLOW_OT_tool_placeholder(bpy.types.Operator):
    bl_idname = "shapeflow.tool_placeholder"
    bl_label = "Upcoming ShapeFlow Tool"

    tool_name: bpy.props.StringProperty(options={'SKIP_SAVE'})

    @classmethod
    def description(cls, _context, properties):
        return f"{properties.tool_name}: button reserved; interaction will be defined in a later version"

    def execute(self, _context):
        self.report({'INFO'}, f"ShapeFlow: {self.tool_name} is being designed")
        return {'FINISHED'}
