import bpy


class SHAPEFLOW_OT_workspace(bpy.types.Operator):
    bl_idname = "shapeflow.open_workspace"
    bl_label = "Open ShapeFlow Workspace"
    bl_description = "Create or switch to a workspace named ShapeFlow"

    def execute(self, context):
        workspace = bpy.data.workspaces.get("ShapeFlow")
        if workspace is None:
            bpy.ops.workspace.duplicate()
            context.workspace.name = "ShapeFlow"
        else:
            context.window.workspace = workspace
        return {'FINISHED'}

