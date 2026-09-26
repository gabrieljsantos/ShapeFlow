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
        if self.enable:
            self.report({'INFO'}, "ShapeFlow Mode enabled")
        else:
            context.workspace.status_text_set(None)
            self.report({'INFO'}, "ShapeFlow Mode disabled")
        if context.area:
            context.area.tag_redraw()
        return {'FINISHED'}
