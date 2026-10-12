import bpy

from ..mesh.repetition import add_linear_array, add_mirror_modifier, create_radial_series
from ..utils.geometry import typed_length_to_blender_units


class SHAPEFLOW_OT_copy_series(bpy.types.Operator):
    bl_idname = "shapeflow.copy_series"
    bl_label = "Copy Series"
    bl_description = "Create a native linear Array modifier or radial linked instances"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.window_manager.shapeflow_mode and context.active_object is not None

    def execute(self, context):
        settings = context.scene.shapeflow
        source = context.active_object
        try:
            if settings.array_mode == 'LINEAR':
                spacing = typed_length_to_blender_units(
                    settings.array_spacing, settings.length_unit,
                    context.scene.unit_settings.scale_length,
                )
                add_linear_array(source, settings.array_count, spacing, settings.array_axis)
            else:
                create_radial_series(
                    context, source, settings.array_count, settings.array_angle,
                    settings.array_axis, settings.drawing_origin,
                )
        except ValueError as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return {'CANCELLED'}
        return {'FINISHED'}


class SHAPEFLOW_OT_mirror(bpy.types.Operator):
    bl_idname = "shapeflow.mirror"
    bl_label = "Mirror"
    bl_description = "Add a non-destructive native Mirror modifier around the object origin"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (
            context.window_manager.shapeflow_mode
            and context.active_object is not None
            and context.active_object.type == 'MESH'
        )

    def execute(self, context):
        try:
            add_mirror_modifier(context.active_object, context.scene.shapeflow.mirror_axis)
        except ValueError as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return {'CANCELLED'}
        return {'FINISHED'}
