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
        window_manager = context.window_manager
        mode_enabled = window_manager.shapeflow_mode
        active = window_manager.shapeflow_active_tool

        layout.label(text="ShapeFlow 0.7.2")
        layout.operator("shapeflow.open_workspace", icon='WORKSPACE')
        if mode_enabled:
            row = layout.row()
            row.alert = True
            operator = row.operator("shapeflow.toggle_mode", text="Exit ShapeFlow Mode", icon='PAUSE')
            operator.enable = False
        else:
            operator = layout.operator("shapeflow.toggle_mode", text="Enter ShapeFlow Mode", icon='PLAY')
            operator.enable = True

        tools = layout.column()
        tools.enabled = mode_enabled

        plane = tools.box()
        plane.label(text="Face orientation")
        row = plane.row(align=True)
        row.prop(settings, "drawing_plane", expand=True)

        space = tools.box()
        space.label(text="3D creation origin")
        space.prop(settings, "drawing_origin", text="")
        row = space.row(align=True)
        operator = row.operator("shapeflow.activate_tool", text="G  Position", depress=active == 'ORIGIN')
        operator.tool = 'ORIGIN'
        row.prop(settings, "show_native_grid", text="Grid", toggle=True, icon='GRID')

        options = tools.box()
        options.label(text="Options")
        row = options.row(align=True)
        row.prop(settings, "copy_mode", text="C  Copy", toggle=True, icon='DUPLICATE')
        row.prop(settings, "snap_enabled", text="S  Snap", toggle=True, icon='SNAP_ON')
        row = options.row(align=True)
        row.prop(settings, "creation_origin", expand=True)
        options.prop(settings, "proportional_creation", text="P  Proportional", toggle=True)

        shapes = tools.box()
        shapes.label(text="Shapes")
        grid = shapes.grid_flow(row_major=True, columns=4, even_columns=True, even_rows=True, align=True)
        operator = grid.operator("shapeflow.activate_tool", text="R", depress=active == 'RECTANGLE')
        operator.tool = 'RECTANGLE'
        grid.operator("shapeflow.polygon_settings", text="P", depress=active == 'POLYGON')

        transform = tools.box()
        transform.label(text="Transform")
        grid = transform.grid_flow(row_major=True, columns=4, even_columns=True, even_rows=True, align=True)
        operator = grid.operator("shapeflow.activate_tool", text="E", depress=active == 'EXTRUDE')
        operator.tool = 'EXTRUDE'
        operator = grid.operator("shapeflow.activate_tool", text="M", depress=active == 'MOVE')
        operator.tool = 'MOVE'
        operator = grid.operator("shapeflow.tool_placeholder", text="O")
        operator.tool_name = "Rotate"

        constraints = tools.box()
        constraints.label(text="Move constraint")
        row = constraints.row(align=True)
        for value in ('X', 'Y', 'Z'):
            row.prop_enum(settings, "move_constraint", value=value)
        row = constraints.row(align=True)
        for value in ('XY', 'XZ', 'YZ', 'XYZ'):
            row.prop_enum(settings, "move_constraint", value=value)

        header, body = tools.panel("SHAPEFLOW_PT_alignment_settings", default_closed=True)
        header.label(text="Alignment settings")
        if body:
            body.enabled = settings.snap_enabled
            body.prop(settings, "grid_snap", text="Use step snapping")
            body.prop(settings, "geometry_snap")
            body.prop(settings, "grid_spacing", text="Step size")
            body.prop(settings, "snap_distance")
            body.label(text="Hold Shift for temporary bypass", icon='EVENT_SHIFT')

        header, body = tools.panel("SHAPEFLOW_PT_numeric_settings", default_closed=True)
        header.label(text="Numeric input")
        if body:
            body.prop(settings, "length_unit", text="Unit")

        tools.separator()
        if active == 'RECTANGLE':
            tools.label(text="Rectangle active — Esc to stop", icon='RADIOBUT_ON')
        elif active == 'POLYGON':
            tools.label(text=f"Polygon ({settings.polygon_sides}) active — Esc to stop", icon='RADIOBUT_ON')
        elif active == 'EXTRUDE':
            tools.label(text="Extrude active — Esc to stop", icon='RADIOBUT_ON')
        elif active == 'ORIGIN':
            tools.label(text="3D origin active — Esc to stop", icon='RADIOBUT_ON')
        elif active == 'MOVE':
            tools.label(text="Move active — Esc to stop", icon='RADIOBUT_ON')
        else:
            tools.label(text="Choose a tool", icon='INFO')
