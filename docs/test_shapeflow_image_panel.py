"""Toggle a temporary image-and-description preview in the ShapeFlow N-panel.

Run this text in Blender's Text Editor. Run it again to remove the preview.
"""

from pathlib import Path
import textwrap

import bpy
import bpy.utils.previews
import shapeflow


_KEY = "shapeflow_temporary_tool_preview"
_saved = bpy.app.driver_namespace.get(_KEY)

if _saved:
    # Second run: remove the temporary panel and free its custom PNG preview.
    panel_type, preview_collection = _saved
    try:
        bpy.utils.unregister_class(panel_type)
    except RuntimeError:
        pass
    bpy.utils.previews.remove(preview_collection)
    del bpy.app.driver_namespace[_KEY]
    print("ShapeFlow image preview removed.")
else:
    _asset = Path(shapeflow.__file__).resolve().parent / "assets" / "tool-rectangle-2p.png"
    if not _asset.is_file():
        raise FileNotFoundError(f"ShapeFlow icon not found: {_asset}")

    _previews = bpy.utils.previews.new()
    _previews.load("RECTANGLE_2P_PREVIEW", str(_asset), 'IMAGE')
    _icon_id = _previews["RECTANGLE_2P_PREVIEW"].icon_id

    class VIEW3D_PT_shapeflow_temporary_tool_preview(bpy.types.Panel):
        bl_label = "Preview: Rectangle"
        bl_idname = "VIEW3D_PT_shapeflow_temporary_tool_preview"
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_category = "ShapeFlow"
        bl_order = 0

        def draw(self, context):
            layout = self.layout
            layout.template_icon(icon_value=_icon_id, scale=8.0)
            layout.label(text="2-Point Rectangle", icon='EVENT_R')
            for line in textwrap.wrap(
                "Create a rectangle as width then height", width=34
            ):
                layout.label(text=line)

    bpy.utils.register_class(VIEW3D_PT_shapeflow_temporary_tool_preview)
    bpy.app.driver_namespace[_KEY] = (
        VIEW3D_PT_shapeflow_temporary_tool_preview,
        _previews,
    )

    # Open the N sidebar in the current screen so the panel can be inspected.
    window = bpy.context.window
    if window:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.show_region_ui = True
                area.tag_redraw()

    print(f"ShapeFlow image preview enabled using: {_asset}")
