import bpy

from ..mesh.solid_tools import split_solid, trim_solid


class SHAPEFLOW_OT_solid_tool(bpy.types.Operator):
    bl_idname = "shapeflow.solid_tool"
    bl_label = "Solid Operation"
    bl_options = {'REGISTER', 'UNDO'}

    operation: bpy.props.EnumProperty(items=(
        ('DIFFERENCE_1_2', "Subtraction 1 in 2", "Subtract solid 1 from solid 2; object 2 is the result target"),
        ('DIFFERENCE_2_1', "Subtraction 2 in 1", "Subtract solid 2 from solid 1; object 1 is the result target"),
        ('SPLIT', "Split Solid", "Keep both the inside and outside parts as separate objects"),
    ))

    @classmethod
    def description(cls, _context, properties):
        return (
            "Subtract solid 1 from solid 2; active is 1 and the other selected object is 2"
            if properties.operation == 'DIFFERENCE_1_2'
            else "Subtract solid 2 from solid 1; active is 1 and the other selected object is 2"
            if properties.operation == 'DIFFERENCE_2_1'
            else "Split object 1 with object 2 and keep both inside and outside results"
        )

    @classmethod
    def poll(cls, context):
        return (
            context.window_manager.shapeflow_mode
            and context.active_object is not None
            and context.active_object.type == 'MESH'
            and len([obj for obj in context.selected_objects if obj.type == 'MESH']) == 2
        )

    def execute(self, context):
        active = context.active_object
        other = next(obj for obj in context.selected_objects if obj is not active and obj.type == 'MESH')
        first, second = active, other
        try:
            if self.operation == 'DIFFERENCE_1_2':
                target, cutter = second, first
                trim_solid(target, cutter)
                target["shapeflow_solid_operation"] = 'DIFFERENCE_1_IN_2'
            elif self.operation == 'DIFFERENCE_2_1':
                target, cutter = first, second
                trim_solid(target, cutter)
                target["shapeflow_solid_operation"] = 'DIFFERENCE_2_IN_1'
            else:
                split_solid(context, first, second)
        except ValueError as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return {'CANCELLED'}
        return {'FINISHED'}
