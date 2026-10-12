import bpy

from ..mesh.curve_edit import extend_curve, trim_curve


class SHAPEFLOW_OT_curve_edit(bpy.types.Operator):
    bl_idname = "shapeflow.curve_edit"
    bl_label = "Edit Curve to Boundary"
    bl_options = {'REGISTER', 'UNDO'}

    operation: bpy.props.EnumProperty(items=(
        ('TRIM', "Trim", "Remove the chosen end up to the cutter intersection"),
        ('EXTEND', "Extend", "Extend the chosen endpoint to the boundary"),
    ))

    @classmethod
    def description(cls, _context, properties):
        return "Trim the active Poly Curve against the second selected Curve" if properties.operation == 'TRIM' else "Extend the active Poly Curve to the second selected Curve"

    @classmethod
    def poll(cls, context):
        return (
            context.window_manager.shapeflow_mode
            and context.active_object is not None
            and context.active_object.type == 'CURVE'
            and len([obj for obj in context.selected_objects if obj.type == 'CURVE']) == 2
        )

    def execute(self, context):
        subject = context.active_object
        boundary = next(obj for obj in context.selected_objects if obj is not subject and obj.type == 'CURVE')
        side = context.scene.shapeflow.curve_edit_side
        try:
            if self.operation == 'TRIM':
                trim_curve(subject, boundary, side)
            else:
                extend_curve(subject, boundary, side)
        except ValueError as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return {'CANCELLED'}
        return {'FINISHED'}
