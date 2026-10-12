import bpy

from ..mesh.solid_tools import split_solid, trim_solid


class SHAPEFLOW_OT_solid_tool(bpy.types.Operator):
    bl_idname = "shapeflow.solid_tool"
    bl_label = "Solid Tool"
    bl_options = {'REGISTER', 'UNDO'}

    operation: bpy.props.EnumProperty(items=(
        ('TRIM', "Solid Trim", "Trim the active solid with the second selected solid"),
        ('SPLIT', "Solid Split", "Create complementary inside and outside results"),
    ))

    @classmethod
    def description(cls, _context, properties):
        return (
            "Trim the active solid non-destructively with an exact Boolean"
            if properties.operation == 'TRIM'
            else "Split the active solid into non-destructive inside and outside results"
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
        target = context.active_object
        cutter = next(obj for obj in context.selected_objects if obj is not target and obj.type == 'MESH')
        try:
            if self.operation == 'TRIM':
                trim_solid(target, cutter)
            else:
                split_solid(context, target, cutter)
        except ValueError as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return {'CANCELLED'}
        return {'FINISHED'}
