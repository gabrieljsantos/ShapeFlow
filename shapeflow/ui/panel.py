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
        layout.label(text="ShapeFlow 0.4.0")
        layout.operator("shapeflow.open_workspace", icon='WORKSPACE')
        mode_enabled = context.window_manager.shapeflow_mode
        if mode_enabled:
            row = layout.row()
            row.alert = True
            operator = row.operator("shapeflow.toggle_mode", text="Exit ShapeFlow Mode", icon='PAUSE')
            operator.enable = False
            layout.label(text="Mode active", icon='RADIOBUT_ON')
        else:
            operator = layout.operator("shapeflow.toggle_mode", text="Enter ShapeFlow Mode", icon='PLAY')
            operator.enable = True
            layout.label(text="Blender controls are active", icon='RADIOBUT_OFF')

        tools = layout.column()
        tools.enabled = mode_enabled
        box = tools.box()
        box.label(text="Drawing")
        box.prop(settings, "drawing_plane", expand=True)
        box.separator()
        box.label(text="Automatic alignment")
        box.prop(settings, "snap_enabled", text="Enabled")
        snap_col = box.column()
        snap_col.enabled = settings.snap_enabled
        snap_col.prop(settings, "grid_snap")
        snap_col.prop(settings, "geometry_snap")
        snap_col.prop(settings, "grid_spacing")
        snap_col.prop(settings, "snap_distance")
        snap_col.label(text="Hold Shift for temporary bypass", icon='EVENT_SHIFT')
        box.operator("shapeflow.draw_rectangle", text="Draw Rectangle", icon='MESH_PLANE')
        box = tools.box()
        box.label(text="Direct Modeling")
        box.prop(settings, "length_unit", text="Typed unit")
        box.prop(settings, "copy_mode", toggle=True, icon='DUPLICATE')
        box.operator("shapeflow.extrude_face", text="Extrude", icon='MOD_SOLIDIFY')
        box.operator("shapeflow.split_face", text="Split", icon='MOD_BOOLEAN')
        tools.separator()
        tools.label(text="Activate a tool, then choose a face", icon='INFO')
