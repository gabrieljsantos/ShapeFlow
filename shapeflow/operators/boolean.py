import bpy

from ..mesh.boolean import add_boolean_modifier


class SHAPEFLOW_OT_boolean(bpy.types.Operator):
    bl_idname = "shapeflow.boolean"
    bl_label = "ShapeFlow Boolean"
    bl_options = {'REGISTER', 'UNDO'}

    operation: bpy.props.EnumProperty(items=(
        ('UNION', "Union", "Combine the selected mesh solids"),
        ('DIFFERENCE', "Subtract", "Subtract the other selected mesh from the active mesh"),
        ('INTERSECT', "Intersect", "Keep only the shared volume"),
    ))

    @classmethod
    def description(cls, _context, properties):
        descriptions = {
            'UNION': "Add a native non-destructive Union Boolean modifier",
            'DIFFERENCE': "Add a native non-destructive Difference Boolean modifier",
            'INTERSECT': "Add a native non-destructive Intersect Boolean modifier",
        }
        return descriptions.get(properties.operation, "Add a native Boolean modifier")

    @classmethod
    def poll(cls, context):
        return (
            context.window_manager.shapeflow_mode
            and context.active_object is not None
            and context.active_object.type == 'MESH'
            and len([obj for obj in context.selected_objects if obj.type == 'MESH']) >= 2
        )

    def execute(self, context):
        target = context.active_object
        operand = next(
            (obj for obj in context.selected_objects if obj != target and obj.type == 'MESH'),
            None,
        )
        try:
            modifier = add_boolean_modifier(target, operand, self.operation)
        except ValueError as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"ShapeFlow: {modifier.name} modifier added; apply it when ready")
        return {'FINISHED'}
