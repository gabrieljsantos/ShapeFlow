# Incremental movement baseline

Validated manually on 2026-09-29 in Blender 5.2.2.

This document records the accepted ShapeFlow incremental-cursor behavior. Future
changes to snapping, drawing, units, viewport projection, or modal input must
preserve these invariants.

## Required behavior

- Incremental cursor movement works in a normal-scale default Blender scene.
- Incremental cursor movement works in a scene configured and modeled in millimeters.
- Slow mouse movement accumulates instead of repeatedly rounding each event to zero.
- The cursor does not jump to very large distances because of viewport zoom or perspective.
- Mouse direction is evaluated continuously, so navigation can change between X, Y,
  and Z during the same positioning operation.
- XY, XZ, and YZ select the orientation of the created face only. They must not
  prevent the construction cursor from moving along the remaining axis.
- The configured Step size quantizes the accumulated raw position relative to the
  beginning of the gesture.
- Magnetic geometry snapping may override the increment near a direct target.
- Holding Alt temporarily bypasses Magnetic, Smart Guides, and incremental motion.
- Shift remains reserved for accumulated Blender selection.

## Implementation contract

The construction cursor intentionally maintains separate state for:

1. the last mouse position, used to detect the current projected axis;
2. the raw accumulated 3D position, which preserves sub-step movement;
3. the displayed position, quantized from the raw position by Step size; and
4. the gesture origin, used as the stable increment reference.

Do not replace this with either per-event quantization or a single displacement
measured from the initial mouse position. Per-event quantization loses slow input;
initial-displacement direction selection makes the cursor stick to a dominant axis.

The pixel-to-world conversion must use the actual projected screen length of a
world-space axis at the cursor position. A viewport-distance heuristic produces
scale-dependent jumps.

## Manual regression check

For both a default scene and a millimeter-scale scene:

1. Enable Incremental and Axis travel.
2. Select each face orientation: XY, XZ, and YZ.
3. Move the mouse very slowly and confirm that sub-step motion accumulates.
4. Change direction during the same gesture and confirm movement along X, Y, and Z.
5. Confirm that the HUD changes by the configured Step size without large jumps.
6. Repeat with Magnetic enabled and Alt held; confirm Shift remains available for accumulated selection before tool activation.
