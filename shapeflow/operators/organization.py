import bpy

from ..mesh.organization import combine_objects, create_linked_instance, group_objects, make_instance_unique, separate_object


class SHAPEFLOW_OT_combine_objects(bpy.types.Operator):
    bl_idname = "shapeflow.combine_objects"
    bl_label = "Combine"
    bl_description = "Combine selected meshes and curves into one mesh object; disconnected parts stay separate"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (
            context.window_manager.shapeflow_mode
            and len(context.selected_objects) >= 2
            and all(obj.type in {'MESH', 'CURVE'} for obj in context.selected_objects)
        )

    def execute(self, context):
        try:
            combine_objects(context, context.selected_objects)
        except ValueError as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return {'CANCELLED'}
        return {'FINISHED'}


class SHAPEFLOW_OT_separate_object(bpy.types.Operator):
    bl_idname = "shapeflow.separate_object"
    bl_label = "Separate"
    bl_description = "Split a combined mesh into objects by disconnected parts"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.window_manager.shapeflow_mode and context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        try:
            parts = separate_object(context, context.active_object)
        except ValueError as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"ShapeFlow: separated into {len(parts)} objects")
        return {'FINISHED'}


class SHAPEFLOW_OT_group_objects(bpy.types.Operator):
    bl_idname = "shapeflow.group_objects"
    bl_label = "Group Objects"
    bl_description = "Parent selected objects to a native Blender Empty"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.window_manager.shapeflow_mode and bool(context.selected_objects)

    def execute(self, context):
        try:
            group_objects(context, context.selected_objects)
        except ValueError as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return {'CANCELLED'}
        return {'FINISHED'}


class SHAPEFLOW_OT_component(bpy.types.Operator):
    bl_idname = "shapeflow.component"
    bl_label = "Linked Component"
    bl_options = {'REGISTER', 'UNDO'}

    action: bpy.props.EnumProperty(items=(
        ('INSTANCE', "Create Instance", "Create a linked duplicate at the ShapeFlow cursor"),
        ('UNIQUE', "Make Unique", "Copy the active object's data for independent editing"),
    ))

    @classmethod
    def description(cls, _context, properties):
        return "Create a native linked duplicate at the ShapeFlow cursor" if properties.action == 'INSTANCE' else "Make the active linked instance independently editable"

    @classmethod
    def poll(cls, context):
        return (
            context.window_manager.shapeflow_mode
            and context.active_object is not None
            and context.active_object.data is not None
        )

    def execute(self, context):
        try:
            if self.action == 'INSTANCE':
                create_linked_instance(
                    context, context.active_object,
                    context.scene.shapeflow.drawing_origin,
                )
            else:
                make_instance_unique(context.active_object)
        except ValueError as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return {'CANCELLED'}
        return {'FINISHED'}
