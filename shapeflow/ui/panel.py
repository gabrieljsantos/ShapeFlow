import bpy


class SHAPEFLOW_PT_main(bpy.types.Panel):
    bl_label = "ShapeFlow"
    bl_idname = "SHAPEFLOW_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ShapeFlow"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.shapeflow
        layout.label(text="ShapeFlow 0.2.1")
        layout.operator("shapeflow.open_workspace", icon='WORKSPACE')
        box = layout.box()
        box.label(text="Drawing")
        box.prop(settings, "drawing_plane", expand=True)
        box.prop(settings, "snap_enabled")
        box.operator("shapeflow.draw_rectangle", text="Draw Rectangle", icon='MESH_PLANE')
        box = layout.box()
        box.label(text="Direct Modeling")
        box.prop(settings, "length_unit", text="Typed unit")
        box.operator("shapeflow.extrude_face", text="Extrude", icon='MOD_SOLIDIFY')
        box.operator("shapeflow.split_face", text="Split", icon='MOD_BOOLEAN')
        layout.separator()
        layout.label(text="Activate a tool, then choose a face", icon='INFO')
