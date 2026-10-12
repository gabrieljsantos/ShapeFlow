import bpy

from ..mesh.sweep import apply_follow_me


class SHAPEFLOW_OT_follow_me(bpy.types.Operator):
    bl_idname = "shapeflow.follow_me"
    bl_label = "Follow Me"
    bl_description = "Sweep a selected Curve or mesh profile along the active native Curve path"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (
            context.window_manager.shapeflow_mode
            and context.active_object is not None
            and context.active_object.type == 'CURVE'
            and len(context.selected_objects) == 2
        )

    def execute(self, context):
        path = context.active_object
        profile = next(obj for obj in context.selected_objects if obj is not path)
        try:
            apply_follow_me(context, path, profile, context.scene.shapeflow.follow_me_caps)
        except ValueError as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return {'CANCELLED'}
        return {'FINISHED'}
