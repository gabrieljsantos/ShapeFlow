# ShapeFlow

ShapeFlow 0.9.0 is a Blender 5.2 add-on for direct modelling with persistent creation and transformation modes over native Blender meshes. Creation tools include a roaming 3D construction cursor; face orientation never fixes the cursor to a zero-coordinate plane.

Move snapping is screen-space driven: vertices, edge midpoints, arbitrary positions along edges, and face centers become magnetic when their projection is within the configured **Snap distance** in pixels. Their world-space distance does not prevent alignment when they are visually close in the current view.

Before a Move drag starts, available points on the hovered face appear as soft circular markers. The active point uses an emphasized yellow circle, its related edge changes to blue, and the snapped destination uses an emphasized green circle.

Overlapping screen-space candidates use a fixed priority: vertex, edge midpoint, edge, face center, then free face point. A corner therefore wins over a line even when the projected line is mathematically closer to the cursor.

## Install and activate

1. Download or build `shapeflow.zip`.
2. In Blender, open **Edit → Preferences → Add-ons → Install from Disk**.
3. Select `shapeflow.zip`, then enable **ShapeFlow**.
4. In the 3D Viewport, press **N** and open the **ShapeFlow** tab.
5. Optionally click **Open ShapeFlow Workspace**. This duplicates the current workspace once and names it ShapeFlow; the normal Blender workspaces remain available.
6. Click **Enter ShapeFlow Mode**. The add-on never captures viewport input merely because it is installed; the interaction mode starts disabled and is not saved in the `.blend` file.

## Quick Start

### Rectangle → Extrude → Split → Extrude

1. Click **Enter ShapeFlow Mode**, choose the **XY**, **XZ**, or **YZ** drawing plane, and start from a view where that plane is visible.
2. Click the **R** tool. Grid and Geometry alignment are enabled by default. Create as many rectangles as needed—the tool remains active until Escape or another tool is chosen. Hover each letter button to see its name and purpose.
   For polygons, click **P**, choose the side count in the temporary popup (five by default), and create by center/radius or across two opposite points. Click **P** again whenever you want the popup back; the last side count is preserved.
3. Choose the typed unit (millimeters by default), then click the **E** tool. Hovering highlights the available face in green. Press and drag that face; the distance follows ShapeFlow's **Step size**, independently of Blender's visible grid. Hold Shift while dragging for continuous movement, or type an exact value such as `1.5` and press Enter. The tool remains active for consecutive extrusions.
4. Put the pointer over the face to cut and click **Split**. Click a point on one boundary edge, then a point on a different boundary edge.
5. Put the pointer over either new face, click **Extrude**, move, and click.

Press **Esc** or right-click to cancel any active operation. Each completed operation participates separately in Blender Undo/Redo.

Use **Exit ShapeFlow Mode** to return full viewport control to Blender. Loading another file or leaving the workspace disables ShapeFlow Mode automatically.

## Tools

- **Draw Rectangle** creates a new object containing one quad on the selected world plane.
- **Arc**, **Bezier**, and **Crescent** create three-point circular arcs, cubic curves with explicit handles, and closed crescent profiles.
- **Move** drags the complete object by default. Hold **Ctrl when starting the drag** to move only the hovered vertex, edge, or face; geometric targets remain magnetic in screen space.
- **Extrude** enters a tool mode and highlights the face under the pointer. With **Copy** disabled, a face on a closed solid is pushed or pulled by moving its existing boundary, so no internal source face remains. With **Copy** enabled, ShapeFlow preserves the source and extrudes a duplicate with side walls. A lone profile still becomes a solid in either mode. Typed values use the unit selected in the panel.
- Split has been removed from the active palette while the future line-based workflow is designed.

## Current limitations

- Drawing is axis-aligned on an explicit world XY/XZ/YZ plane. Drawing directly into an existing mesh face is planned.
- Split requires two different boundary edges on the same face. It does not yet create enclosed internal cuts.
- Curves are created as native mesh polylines; editable Blender Curve objects and persistent Bézier-handle widgets are planned refinements.
- Drag distance is screen-derived. Typed values use the millimeter, centimeter, or meter unit selected in the ShapeFlow panel and are converted to Blender units using the scene scale.
- The Snap switch reserves the UI and data model for richer snapping; boundary snapping is always enforced by Split in this release.
- Picking uses the evaluated viewport mesh. Objects with topology-changing modifiers can produce face-index ambiguity; apply or temporarily disable those modifiers before editing with ShapeFlow.

## Native modifier compatibility

ShapeFlow never creates a proprietary geometry type. Select its mesh and add Blender's native **Bevel**, **Boolean**, **Subdivision Surface**, **Solidify**, **Mirror**, or Geometry Nodes modifiers normally. For a quick Bevel check, complete the Quick Start, open the Modifiers tab, add **Bevel**, and adjust Width and Segments.

## Development and tests

Run geometry tests with Blender itself:

```bash
blender --background --factory-startup --python tests/test_geometry.py
```

Build the installable archive from the repository root:

```bash
zip -r shapeflow.zip shapeflow -x "*/__pycache__/*" "*.pyc"
```

The ZIP root contains the `shapeflow/` package as required by Blender's add-on installer.

## Roadmap

- Draw rectangles and closed polygons directly on arbitrary mesh faces.
- Vertex/edge/grid snap controls and visible snap markers.
- Dimension HUD with scene-unit parsing for rectangle width/height and extrusion.
- More robust modifier-aware picking and multi-face extrusion.
- Inset, offset, cut, and native-modifier Boolean helpers.
