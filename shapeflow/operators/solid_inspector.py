import bpy

from ..mesh.inspection import inspect_solid


class SHAPEFLOW_OT_solid_inspector(bpy.types.Operator):
    bl_idname = "shapeflow.solid_inspector"
    bl_label = "Solid Inspector"
    bl_description = "Inspect the active mesh for open, non-manifold, loose, duplicate, degenerate, or inverted geometry"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return (
            context.window_manager.shapeflow_mode
            and context.active_object is not None
            and context.active_object.type == 'MESH'
        )

    def execute(self, context):
        obj = context.active_object
        try:
            result = inspect_solid(obj)
        except ValueError as error:
            self.report({'WARNING'}, f"ShapeFlow: {error}")
            return {'CANCELLED'}
        obj["shapeflow_solid_valid"] = result['valid']
        obj["shapeflow_boundary_edges"] = len(result['boundary_edges'])
        obj["shapeflow_non_manifold_edges"] = len(result['non_manifold_edges'])
        obj["shapeflow_loose_elements"] = len(result['loose_edges']) + len(result['loose_vertices'])
        obj["shapeflow_degenerate_faces"] = len(result['degenerate_faces'])
        obj["shapeflow_duplicate_faces"] = len(result['duplicate_faces'])
        obj["shapeflow_inverted"] = result['inverted']
        settings = context.scene.shapeflow
        settings.inspection_summary = (
            "Valid closed solid" if result['valid'] else
            f"Open {len(result['boundary_edges'])} • Non-manifold {len(result['non_manifold_edges'])} • "
            f"Loose {len(result['loose_edges']) + len(result['loose_vertices'])} • "
            f"Degenerate {len(result['degenerate_faces'])} • Duplicate {len(result['duplicate_faces'])} • "
            f"Inverted {'yes' if result['inverted'] else 'no'}"
        )
        self.report({'INFO'} if result['valid'] else {'WARNING'}, f"ShapeFlow: {settings.inspection_summary}")
        return {'FINISHED'}
