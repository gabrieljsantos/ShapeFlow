"""Load the ShapeFlow symbol as a Blender custom preview icon."""

from pathlib import Path

import bpy.utils.previews


_preview_collection = None
_ICON_FILES = {
    "BRAND": "shapeflow-icon.png",
    "RECTANGLE": "tool-rectangle.png",
    "RECTANGLE_CORNER": "tool-rectangle-corner.png",
    "SQUARE_REGULAR": "tool-square-regular.png",
    "RECTANGLE_MIRROR": "tool-rectangle-center.png",
    "RECTANGLE_MIRROR_2P": "tool-rectangle-mirror-2p.png",
    "BOX_3P": "tool-box-3p.png",
    "EXTRUDE": "tool-extrude.png",
    "ARC": "tool-arc-3p.png",
    "BEZIER": "tool-bezier.png",
    "BSPLINE": "tool-bspline.png",
    "FREEHAND": "tool-freehand.png",
    "RECTANGLE_2P": "tool-rectangle-2p.png",
    "RECTANGLE_ROTATED": "tool-rectangle-rotated.png",
    "POLYGON": "tool-polygon.png",
    "LINE": "tool-line.png",
    "POLYLINE": "tool-polyline.png",
    "ELLIPSE": "tool-ellipse.png",
    "ELLIPSE_CENTER": "tool-ellipse-center.png",
    "ELLIPSE_FOCI": "tool-ellipse-foci.png",
    "ELLIPSE_AXIS": "tool-ellipse-axis.png",
    "CIRCLE": "tool-circle.png",
    "CIRCLE_CENTER": "tool-circle-center.png",
    "CIRCLE_DIAMETER": "tool-circle-diameter.png",
    "POLYGON_VERTEX": "tool-polygon-vertex.png",
    "POLYGON_EDGE": "tool-polygon-edge.png",
    "POLYGON_FREE": "tool-polygon-free-vertices.png",
    "ARC_2P": "tool-arc-2p.png",
    "ARC_CENTER": "tool-arc-center.png",
    "PIE": "tool-pie.png",
    "PEN": "tool-pen.png",
    "LIVE_SKETCH": "tool-live-sketch.png",
    "SMART_DRAW": "tool-smart-draw.png",
    "CRESCENT": "tool-crescent-2arc.png",
    "MOVE": "tool-move.png",
    "ROTATE": "tool-rotate.png",
    "SCALE": "tool-scale.png",
    "FOLLOW_ME": "tool-follow-me.png",
    "OFFSET": "tool-offset.png",
    "FILLET": "tool-fillet.png",
    "CHAMFER": "tool-chamfer.png",
    "TRIM": "tool-trim.png",
    "EXTEND": "tool-extend.png",
    "UNION": "tool-union.png",
    "SUBTRACT": "tool-subtract.png",
    "INTERSECT": "tool-intersect.png",
    "SOLID_TRIM": "tool-solid-trim.png",
    "SOLID_SPLIT": "tool-solid-split.png",
    "MEASURE": "tool-measure.png",
    "PROTRACTOR": "tool-protractor.png",
    "DIMENSIONS": "tool-dimensions.png",
    "GROUP": "tool-group.png",
    "COMPONENT": "tool-component.png",
    "ARRAY_COPY": "tool-array-copy.png",
    "MIRROR": "tool-mirror.png",
    "SOLID_CHECK": "tool-solid-check.png",
    "WORKPLANE": "tool-workplane.png",
    "CURSOR": "tool-cursor.png",
    "SNAP": "tool-snap.png",
    "NUMERIC": "tool-numeric.png",
}


def register_brand_icon():
    global _preview_collection
    if _preview_collection is not None:
        return
    _preview_collection = bpy.utils.previews.new()
    asset_dir = Path(__file__).resolve().parent.parent / "assets"
    for name, filename in _ICON_FILES.items():
        _preview_collection.load(name, str(asset_dir / filename), 'IMAGE')


def unregister_brand_icon():
    global _preview_collection
    if _preview_collection is not None:
        bpy.utils.previews.remove(_preview_collection)
        _preview_collection = None


def brand_icon_value():
    if _preview_collection is None:
        return 0
    return _preview_collection["BRAND"].icon_id


def tool_icon_value(name):
    if _preview_collection is None:
        return 0
    return _preview_collection[name].icon_id
