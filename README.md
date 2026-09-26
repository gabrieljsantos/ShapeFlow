# ShapeFlow

ShapeFlow is a Blender 5.2 add-on for direct modelling with native `bpy.types.Mesh` objects. It provides a deliberately small workflow: draw a rectangular face, extrude a face, split a face from boundary to boundary, and extrude again. The result remains editable with every normal Blender mesh tool and modifier.

## Install and activate

1. Download or build `shapeflow.zip`.
2. In Blender, open **Edit → Preferences → Add-ons → Install from Disk**.
3. Select `shapeflow.zip`, then enable **ShapeFlow**.
4. In the 3D Viewport, press **N** and open the **ShapeFlow** tab.
5. Optionally click **Open ShapeFlow Workspace**. This duplicates the current workspace once and names it ShapeFlow; the normal Blender workspaces remain available.

## Quick Start

### Rectangle → Extrude → Split → Extrude

1. Choose the **XY**, **XZ**, or **YZ** drawing plane. Start from a view where that plane is visible.
2. Click **Draw Rectangle**, click the first corner, move the pointer, then click the opposite corner.
3. Put the pointer over the face and click **Extrude**. Move along the orange preview and click to confirm. You may type a Blender-unit distance and press Enter instead.
4. Put the pointer over the face to cut and click **Split**. Click a point on one boundary edge, then a point on a different boundary edge.
5. Put the pointer over either new face, click **Extrude**, move, and click.

Press **Esc** or right-click to cancel any active operation. Each completed operation participates separately in Blender Undo/Redo.

## Tools

- **Draw Rectangle** creates a new object containing one quad on the selected world plane.
- **Extrude** picks the face under the pointer and performs a real BMesh face extrusion with side walls.
- **Split** snaps each click to the nearest boundary edge of the face under the pointer and creates a real topological edge.

## Current limitations

- Drawing is axis-aligned on an explicit world XY/XZ/YZ plane. Drawing directly into an existing mesh face is planned.
- Split requires two different boundary edges on the same face. It does not yet create enclosed internal cuts.
- The first version supports rectangles, not free polygons.
- Drag distance is screen-derived; typed values use the current Blender scene unit convention and are stored internally in Blender units.
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
