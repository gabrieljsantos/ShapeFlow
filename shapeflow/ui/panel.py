import bpy

from ..tool_catalog import TOOLS_BY_ID
from .brand_icon import brand_icon_value, tool_icon_value
from .icons import tool_icon, ui_icon


def _tool_label(identifier):
    return TOOLS_BY_ID[identifier].label


def _tool_item(layout, icon_name, operator_id, label, *, depress=False):
    """Draw a larger preview above its clickable tool button."""
    item = layout.column(align=True)
    item.template_icon(icon_value=tool_icon_value(icon_name), scale=2.0)
    return item.operator(operator_id, text=label, icon='NONE', depress=depress)


def _tool_panel(layout, identifier, title, *, default_closed=True):
    """Create one compact, independently collapsible tool group."""
    header, body = layout.panel(identifier, default_closed=default_closed)
    header.label(text=title)
    return body


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

        brand = layout.row(align=True)
        brand.template_icon(icon_value=brand_icon_value(), scale=1.35)
        brand.label(text="ShapeFlow 0.9.0")
        if mode_enabled:
            row = layout.row()
            row.alert = True
            operator = row.operator("shapeflow.toggle_mode", text="Exit ShapeFlow Mode", icon=ui_icon('MODE_EXIT'))
            operator.enable = False
        else:
            operator = layout.operator("shapeflow.toggle_mode", text="Enter ShapeFlow Mode", icon=ui_icon('MODE_ENTER'))
            operator.enable = True

        tools = layout.column()
        tools.enabled = mode_enabled

        plane = tools.box()
        plane.label(text="Face orientation", icon_value=tool_icon_value('WORKPLANE'))
        row = plane.row(align=True)
        row.prop(settings, "drawing_plane", expand=True)
        if settings.drawing_plane == 'AUTO':
            plane.prop(settings, "auto_axis_threshold", text="Axis gesture")
        operator = plane.operator("shapeflow.pick_workplane", text="W  Capture hovered face", icon_value=tool_icon_value('WORKPLANE'))
        if settings.drawing_plane == 'FACE':
            plane.label(text="Local axes follow captured face", icon=ui_icon('FACE'))

        space = tools.box()
        space.label(text="3D construction cursor", icon_value=tool_icon_value('CURSOR'))
        space.prop(settings, "drawing_origin", text="Position")
        row = space.row(align=True)
        row.prop(settings, "show_native_grid", text="Grid", toggle=True, icon=ui_icon('GRID'))
        row.prop(settings, "axis_cursor", text="Axis travel", toggle=True)
        space.label(text="Mouse follows local U/V/N" if settings.drawing_plane == 'FACE' else "Mouse direction follows projected X/Y/Z")

        options = tools.box()
        options.label(text="Options")
        options.prop(settings, "creation_output", expand=True)
        if settings.creation_output == 'EMBEDDED':
            target = settings.workplane_object or "No receiver face"
            options.label(text=f"Receiver: {target}", icon=ui_icon('FACE'))
        row = options.row(align=True)
        row.prop(settings, "copy_mode", text="C  Copy", toggle=True, icon=ui_icon('COPY'))
        row = options.row(align=True)
        row.prop(settings, "creation_origin", expand=True)
        options.prop(settings, "proportional_creation", text="P  Proportional", toggle=True)

        drawing = _tool_panel(tools, "SHAPEFLOW_PT_drawing_tools", "Drawing", default_closed=False)
        if drawing:
            profiles = _tool_panel(drawing, "SHAPEFLOW_PT_profile_tools", "Profiles", default_closed=False)
            if profiles:
                grid = profiles.grid_flow(row_major=True, columns=4, even_columns=True, even_rows=True, align=True)
                grid.scale_x = 1.0
                grid.scale_y = 1.0
                for icon_name, variant in (('RECTANGLE_CORNER', 'CORNER'), ('SQUARE_REGULAR', 'SQUARE'), ('RECTANGLE_MIRROR', 'CENTER')):
                    label = {'CORNER': 'Rectangle', 'SQUARE': 'Square', 'CENTER': 'Center'}[variant]
                    operator = _tool_item(grid, icon_name, "shapeflow.activate_tool", label, depress=active == 'RECTANGLE')
                    operator.tool = 'RECTANGLE'
                    operator.rectangle_variant = variant
                operator = _tool_item(grid, 'RECTANGLE_2P', "shapeflow.draw_dimensional", '2-Point Rectangle', depress=active == 'RECTANGLE_2P')
                operator.shape = 'RECTANGLE_2P'
                operator = _tool_item(grid, 'RECTANGLE_ROTATED', "shapeflow.draw_advanced", 'Rotated Rectangle', depress=active == 'RECTANGLE_ROTATED')
                operator.tool = 'RECTANGLE_ROTATED'
                polygon = _tool_item(grid, 'POLYGON_VERTEX', "shapeflow.polygon_settings", 'Polygon: Vertex', depress=active == 'POLYGON' and getattr(window_manager, 'shapeflow_polygon_mode', 'VERTEX') == 'VERTEX')
                polygon.mode = 'VERTEX'
                for mode, icon_name in (('EDGE', 'POLYGON_EDGE'), ('FREE', 'POLYGON_FREE')):
                    label = 'Polygon: Edge' if mode == 'EDGE' else 'Polygon: Free'
                    polygon = _tool_item(grid, icon_name, "shapeflow.polygon_settings", label, depress=active == 'POLYGON' and settings.polygon_sides and getattr(window_manager, 'shapeflow_polygon_mode', 'VERTEX') == mode)
                    polygon.mode = mode
                operator = _tool_item(grid, 'LINE', "shapeflow.draw_advanced", 'Line', depress=active == 'LINE')
                operator.tool = 'LINE'
                operator = _tool_item(grid, 'POLYLINE', "shapeflow.draw_advanced", 'Polyline', depress=active == 'POLYLINE')
                operator.tool = 'POLYLINE'
                for identifier in ('ELLIPSE_CENTER', 'ELLIPSE_FOCI', 'ELLIPSE_AXIS', 'CIRCLE_CENTER', 'CIRCLE_DIAMETER'):
                    operator = _tool_item(grid, identifier, "shapeflow.draw_advanced", _tool_label(identifier), depress=active == identifier)
                    operator.tool = identifier
                for identifier in ('ARC_2P', 'ARC_CENTER', 'PIE'):
                    operator = _tool_item(grid, identifier, "shapeflow.draw_advanced", _tool_label(identifier), depress=active == identifier)
                    operator.tool = identifier
                operator = _tool_item(grid, 'ARC', "shapeflow.draw_advanced", '3-Point Curve', depress=active == 'ARC')
                operator.tool = 'ARC'

            curves = _tool_panel(drawing, "SHAPEFLOW_PT_curve_drawing_tools", "Curves and freehand", default_closed=True)
            if curves:
                curve_grid = curves.grid_flow(row_major=True, columns=4, even_columns=True, even_rows=True, align=True)
                for identifier in ('BEZIER', 'BSPLINE', 'PEN'):
                    operator = _tool_item(curve_grid, identifier, "shapeflow.draw_advanced", _tool_label(identifier), depress=active == identifier)
                    operator.tool = identifier
                for identifier in ('FREEHAND', 'LIVE_SKETCH', 'SMART_DRAW'):
                    operator = _tool_item(curve_grid, identifier, "shapeflow.draw_stroke", _tool_label(identifier), depress=active == identifier)
                    operator.mode = identifier
                operator = _tool_item(curve_grid, 'CRESCENT', "shapeflow.draw_advanced", 'Crescent', depress=active == 'CRESCENT')
                operator.tool = 'CRESCENT'
                curves.prop(settings, "stroke_spacing")
                curves.prop(settings, "live_smoothing")

        modeling = _tool_panel(tools, "SHAPEFLOW_PT_modeling_tools", "Modeling", default_closed=False)
        if modeling:
            grid = modeling.grid_flow(row_major=True, columns=4, even_columns=True, even_rows=True, align=True)
            grid.scale_x = 1.0
            grid.scale_y = 1.0
            operator = _tool_item(grid, 'BOX_3P', "shapeflow.draw_dimensional", '3-Point Box', depress=active == 'BOX_3P')
            operator.shape = 'BOX_3P'
            operator = _tool_item(grid, 'EXTRUDE', "shapeflow.activate_tool", 'Push/Pull', depress=active == 'EXTRUDE')
            operator.tool = 'EXTRUDE'
            operator = _tool_item(grid, 'MOVE', "shapeflow.activate_tool", 'Move', depress=active == 'MOVE')
            operator.tool = 'MOVE'
            _tool_item(grid, 'OFFSET', "shapeflow.offset_face", 'Offset', depress=active == 'OFFSET')
            for identifier in ('FILLET', 'CHAMFER'):
                operator = _tool_item(grid, identifier, "shapeflow.bevel_edge", _tool_label(identifier), depress=active == identifier)
                operator.mode = identifier
            _tool_item(grid, 'ROTATE', "shapeflow.rotate_precise", 'Rotate', depress=active == 'ROTATE')
            operator = _tool_item(grid, 'SCALE', "shapeflow.transform_object", 'Scale', depress=active == 'SCALE')
            operator.mode = 'SCALE'
            modeling.label(text="Rotation")
            modeling.prop(settings, "rotation_pivot_mode", expand=True)
            row = modeling.row(align=True)
            row.prop(settings, "rotation_increment_enabled", text="Angular increment", toggle=True)
            step = row.row(align=True)
            step.enabled = settings.rotation_increment_enabled
            step.prop(settings, "rotation_increment", text="Step")
            modeling.label(text="Scale")
            modeling.prop(settings, "scale_input_mode", expand=True)
            if settings.scale_input_mode == 'DIMENSION':
                modeling.prop(settings, "scale_axis", text="Measure")
                modeling.prop(settings, "scale_target_size", text="Target size")
                modeling.label(text=f"Value uses {settings.length_unit.lower()}")
            modeling.label(text="Push/Pull")
            modeling.prop(settings, "extrusion_mode", expand=True)
            constraints = _tool_panel(modeling, "SHAPEFLOW_PT_move_constraints", "Move constraints", default_closed=True)
            if constraints:
                row = constraints.row(align=True)
                for value in ('X', 'Y', 'Z'):
                    row.prop_enum(settings, "move_constraint", value=value)
                row = constraints.row(align=True)
                for value in ('XY', 'XZ', 'YZ', 'XYZ'):
                    row.prop_enum(settings, "move_constraint", value=value)

        curve_edit = _tool_panel(tools, "SHAPEFLOW_PT_curve_edit_tools", "Curve editing", default_closed=True)
        if curve_edit:
            curve_edit.label(text="Select both curves first, using Shift")
            row = curve_edit.row(align=True)
            for identifier in ('TRIM', 'EXTEND'):
                operator = row.operator("shapeflow.curve_edit", text=_tool_label(identifier), icon_value=tool_icon_value(identifier))
                operator.operation = identifier
            curve_edit.prop(settings, "curve_edit_side", expand=True)
            curve_edit.label(text="Active Poly Curve: subject • second Curve: boundary")
            curve_edit.label(text="Choose the endpoint to trim or extend")

        solid_tools = _tool_panel(tools, "SHAPEFLOW_PT_solid_tools", "Solid operations", default_closed=True)
        if solid_tools:
            grid = solid_tools.grid_flow(row_major=True, columns=4, even_columns=True, even_rows=True, align=True)
            for identifier, operation in (
                ('UNION', 'UNION'),
                ('INTERSECT', 'INTERSECT'),
            ):
                operator = grid.operator("shapeflow.boolean", text=_tool_label(identifier), icon=tool_icon(identifier))
                operator.operation = operation
            row = solid_tools.row(align=True)
            operator = row.operator("shapeflow.solid_tool", text="Subtração", icon_value=tool_icon_value('SOLID_TRIM'))
            operator.operation = 'DIFFERENCE_1_2'
            operator = row.operator("shapeflow.solid_tool", text="Subtração invertida", icon_value=tool_icon_value('SOLID_TRIM_REVERSE'))
            operator.operation = 'DIFFERENCE_2_1'
            operator = solid_tools.operator("shapeflow.solid_tool", text="Dividir sólido", icon=tool_icon('SOLID_SPLIT'))
            operator.operation = 'SPLIT'

        precision = _tool_panel(tools, "SHAPEFLOW_PT_precision_tools", "Precision", default_closed=False)
        if precision:
            operator = precision.operator("shapeflow.draw_advanced", text="Tape measure", icon_value=tool_icon_value('MEASURE'), depress=active == 'MEASURE')
            operator.tool = 'MEASURE'
            precision.prop(settings, "measure_create_guide")
            if settings.last_measure > 0.0:
                from ..utils.geometry import blender_units_to_typed_length
                measured = blender_units_to_typed_length(
                    settings.last_measure, settings.length_unit,
                    context.scene.unit_settings.scale_length,
                )
                precision.label(text=f"Last: {measured:.4f} {settings.length_unit.lower()}")
            operator = precision.operator("shapeflow.draw_advanced", text="Protractor", icon_value=tool_icon_value('PROTRACTOR'), depress=active == 'PROTRACTOR')
            operator.tool = 'PROTRACTOR'
            precision.prop(settings, "protractor_create_guide")
            if settings.last_angle > 0.0:
                from math import degrees
                precision.label(text=f"Last angle: {degrees(settings.last_angle):.2f}°")
            operator = precision.operator("shapeflow.draw_advanced", text="Dimensions", icon_value=tool_icon_value('DIMENSIONS'), depress=active == 'DIMENSIONS')
            operator.tool = 'DIMENSIONS'
            precision.prop(settings, "dimension_type", expand=True)

        organization = _tool_panel(tools, "SHAPEFLOW_PT_organization_tools", "Organization", default_closed=True)
        if organization:
            row = organization.row(align=True)
            row.operator("shapeflow.combine_objects", text="Combine", icon_value=tool_icon_value('COMBINE'))
            row.operator("shapeflow.separate_object", text="Separate", icon_value=tool_icon_value('SEPARATE'))
            row = organization.row(align=True)
            row.operator("shapeflow.group_objects", text="Group", icon_value=tool_icon_value('GROUP'))
            operator = row.operator("shapeflow.component", text="Linked copy", icon_value=tool_icon_value('COMPONENT'))
            operator.action = 'INSTANCE'
            operator = organization.operator("shapeflow.component", text="Make active instance unique", icon_value=tool_icon_value('COMPONENT'))
            operator.action = 'UNIQUE'
            row = organization.row(align=True)
            row.operator("shapeflow.copy_series", text="Copy series", icon_value=tool_icon_value('ARRAY_COPY'))
            row.operator("shapeflow.mirror", text="Mirror", icon_value=tool_icon_value('MIRROR'))
            organization.prop(settings, "array_mode", expand=True)
            row = organization.row(align=True)
            row.prop(settings, "array_axis", expand=True)
            row.prop(settings, "array_count")
            if settings.array_mode == 'LINEAR':
                organization.prop(settings, "array_spacing", text="Spacing")
                organization.label(text=f"Value uses {settings.length_unit.lower()}")
            else:
                organization.prop(settings, "array_angle", text="Step angle")
                organization.label(text="Pivot: ShapeFlow construction cursor")
            organization.prop(settings, "mirror_axis", expand=True)

        inspection = _tool_panel(tools, "SHAPEFLOW_PT_inspection_tools", "Inspection", default_closed=True)
        if inspection:
            inspection.operator("shapeflow.solid_inspector", text="Inspect active solid", icon_value=tool_icon_value('SOLID_CHECK'))
            inspection.label(text=settings.inspection_summary)

        header, body = tools.panel("SHAPEFLOW_PT_alignment_settings", default_closed=True)
        header.label(text="Alignment settings", icon_value=tool_icon_value('SNAP'))
        if body:
            body.prop(settings, "grid_snap", text="Incremental")
            step = body.column()
            step.enabled = settings.grid_snap
            step.prop(settings, "grid_spacing", text="Step size")
            body.prop(settings, "geometry_snap", text="Magnetic")
            magnetic = body.column()
            magnetic.enabled = settings.geometry_snap
            magnetic.prop(settings, "snap_distance", text="Magnetic distance")
            body.prop(settings, "smart_guides", text="Smart guides")
            body.label(text="Alt: temporarily free (no snap/increment)", icon='EVENT_ALT')
            body.label(text="Shift: accumulate Blender selection", icon='EVENT_SHIFT')
            body.label(text="Tab: next snap candidate", icon='EVENT_TAB')
            body.label(text="F: fix/release snapped edge guide", icon='EVENT_F')

        header, body = tools.panel("SHAPEFLOW_PT_numeric_settings", default_closed=True)
        header.label(text="Numeric input", icon_value=tool_icon_value('NUMERIC'))
        if body:
            body.prop(settings, "length_unit", text="Unit")

        tools.separator()
        if active == 'RECTANGLE':
            tools.label(text="Rectangle active — Esc to stop", icon='RADIOBUT_ON')
        elif active == 'RECTANGLE_2P':
            tools.label(text="2P Rectangle active — width, then height", icon='RADIOBUT_ON')
        elif active == 'RECTANGLE_ROTATED':
            tools.label(text="Rotated Rectangle active — width, then height", icon='RADIOBUT_ON')
        elif active == 'BOX_3P':
            tools.label(text="3P Box active — width, height, depth", icon='RADIOBUT_ON')
        elif active == 'POLYGON':
            tools.label(text=f"Polygon ({settings.polygon_sides}) active — Esc to stop", icon='RADIOBUT_ON')
        elif active == 'ARC':
            tools.label(text="Arc active — 3 points — Esc to stop", icon='RADIOBUT_ON')
        elif active == 'BEZIER':
            tools.label(text="Bezier active — points and handles", icon='RADIOBUT_ON')
        elif active == 'BSPLINE':
            tools.label(text="B-Spline active — Enter finishes", icon='RADIOBUT_ON')
        elif active == 'PEN':
            tools.label(text="Pen active — Enter finishes", icon='RADIOBUT_ON')
        elif active in {'FREEHAND', 'LIVE_SKETCH', 'SMART_DRAW'}:
            tools.label(text=f"{_tool_label(active)} active — click and drag", icon='RADIOBUT_ON')
        elif active == 'CRESCENT':
            tools.label(text="Crescent active — chord endpoints and arc point", icon='RADIOBUT_ON')
        elif active == 'EXTRUDE':
            tools.label(text="Extrude active — Esc to stop", icon='RADIOBUT_ON')
        elif active == 'MOVE':
            tools.label(text="Move active — Esc to stop", icon='RADIOBUT_ON')
        elif active == 'MEASURE':
            tools.label(text="Tape Measure active — choose two points", icon='RADIOBUT_ON')
        elif active == 'PROTRACTOR':
            tools.label(text="Protractor active — center and two directions", icon='RADIOBUT_ON')
        elif active == 'DIMENSIONS':
            tools.label(text=f"{settings.dimension_type.title()} dimension active", icon='RADIOBUT_ON')
        else:
            tools.label(text="Choose a tool", icon='INFO')
