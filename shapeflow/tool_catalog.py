"""Single source of truth for ShapeFlow's currently available tools.

Keep UI labels and WindowManager identifiers here. Geometry and interaction
implementations stay in their respective operator modules.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolSpec:
    identifier: str
    label: str
    description: str
    section: str


TOOLS = (
    ToolSpec('RECTANGLE', "Rectangle", "Create rectangles continuously", 'DRAW'),
    ToolSpec('RECTANGLE_2P', "2-Point Rectangle", "Create a rectangle as width then height", 'DRAW'),
    ToolSpec('RECTANGLE_ROTATED', "Rotated Rectangle", "Create a rectangle from an arbitrary planar width direction", 'DRAW'),
    ToolSpec('POLYGON', "Polygon", "Create regular polygons continuously", 'DRAW'),
    ToolSpec('LINE', "2-Point Line", "Create straight two-point lines continuously", 'DRAW'),
    ToolSpec('POLYLINE', "Polyline", "Create one continuous native Curve path point by point", 'DRAW'),
    ToolSpec('ELLIPSE_CENTER', "Ellipse by Center", "Create an ellipse from its center, width and height radii", 'DRAW'),
    ToolSpec('ELLIPSE_FOCI', "Ellipse by Foci", "Create an ellipse from two foci and a point on its curve", 'DRAW'),
    ToolSpec('ELLIPSE_AXIS', "Ellipse by Axis and Height", "Create an ellipse from axis endpoints and its height", 'DRAW'),
    ToolSpec('CIRCLE_CENTER', "Circle by Center", "Create a circle from its center and radius", 'DRAW'),
    ToolSpec('CIRCLE_DIAMETER', "Circle by Diameter", "Create a circle from opposite diameter endpoints", 'DRAW'),
    ToolSpec('ARC_2P', "2-Point Arc", "Create an arc by endpoints and bulge", 'DRAW'),
    ToolSpec('ARC_CENTER', "Center Arc", "Create an arc by center, radius, and angle", 'DRAW'),
    ToolSpec('PIE', "Pie", "Create a closed circular sector face", 'DRAW'),
    ToolSpec('ARC', "3-Point Curve", "Create three-point circular arcs continuously", 'DRAW'),
    ToolSpec('BEZIER', "Bezier", "Create cubic Bezier curves continuously", 'DRAW'),
    ToolSpec('BSPLINE', "B-Spline", "Create an editable native NURBS spline from control points", 'DRAW'),
    ToolSpec('PEN', "Pen", "Create a multi-node native Bezier path with automatic handles", 'DRAW'),
    ToolSpec('FREEHAND', "Freehand", "Capture a dragged stroke as a native Poly Curve", 'DRAW'),
    ToolSpec('LIVE_SKETCH', "Live Sketch", "Smooth a dragged stroke into a native Bezier Curve", 'DRAW'),
    ToolSpec('SMART_DRAW', "Smart Drawing", "Recognize dragged lines and circles or create a smooth native curve", 'DRAW'),
    ToolSpec('CRESCENT', "Crescent", "Create crescent faces continuously", 'DRAW'),
    ToolSpec('BOX_3P', "3-Point Box", "Create a box as width, height, then depth", 'MODEL'),
    ToolSpec('EXTRUDE', "Push/Pull", "Push or pull faces continuously", 'MODEL'),
    ToolSpec('MOVE', "Move", "Move whole objects or selected mesh components", 'MODEL'),
    ToolSpec('OFFSET', "Offset", "Inset a face using Blender native mesh geometry", 'EDIT'),
    ToolSpec('FILLET', "Fillet", "Round an edge with native bevel geometry", 'EDIT'),
    ToolSpec('CHAMFER', "Chamfer", "Cut an edge with a one-segment native bevel", 'EDIT'),
    ToolSpec('TRIM', "Trim", "Trim an active native Poly Curve against a selected boundary", 'EDIT'),
    ToolSpec('EXTEND', "Extend", "Extend an active native Poly Curve to a selected boundary", 'EDIT'),
    ToolSpec('ROTATE', "Rotate", "Rotate using a world plane, captured workplane, or hovered face", 'MODEL'),
    ToolSpec('SCALE', "Scale", "Scale by factor, percentage, or a requested final dimension", 'MODEL'),
    ToolSpec('FOLLOW_ME', "Follow Me", "Sweep a native profile along an active Curve path", 'MODEL'),
    ToolSpec('UNION', "Union", "Combine solids with a native Boolean modifier", 'SOLID'),
    ToolSpec('SUBTRACT', "Subtract", "Subtract a solid with a native Boolean modifier", 'SOLID'),
    ToolSpec('INTERSECT', "Intersect", "Keep shared volume with a native Boolean modifier", 'SOLID'),
    ToolSpec('SOLID_TRIM', "Solid Trim", "Trim one solid non-destructively with another", 'SOLID'),
    ToolSpec('SOLID_SPLIT', "Solid Split", "Create complementary inside and outside solid results", 'SOLID'),
    ToolSpec('GROUP', "Group", "Parent selected objects to a native Blender Empty", 'ORGANIZE'),
    ToolSpec('COMPONENT', "Component", "Create linked duplicates using shared Blender data", 'ORGANIZE'),
    ToolSpec('MEASURE', "Tape Measure", "Measure between snapped points and optionally create a native guide", 'PRECISION'),
    ToolSpec('PROTRACTOR', "Protractor", "Measure angles and optionally create native angled guides", 'PRECISION'),
    ToolSpec('DIMENSIONS', "Dimensions", "Create editable native linear, angular, radius, and diameter dimensions", 'PRECISION'),
    ToolSpec('ARRAY_COPY', "Copy Series", "Create a native linear array or radial linked instances", 'ORGANIZE'),
    ToolSpec('MIRROR', "Mirror", "Mirror non-destructively with Blender's native modifier", 'ORGANIZE'),
    ToolSpec('SOLID_CHECK', "Solid Inspector", "Find open, non-manifold, loose, duplicate, degenerate, and inverted geometry", 'ORGANIZE'),
)

TOOLS_BY_ID = {tool.identifier: tool for tool in TOOLS}

def active_tool_items():
    """Return Blender EnumProperty items, including the inactive state."""
    return (
        ('NONE', "None", "No ShapeFlow tool is active"),
        *((tool.identifier, tool.label, tool.description) for tool in TOOLS),
    )


def tools_in_section(section):
    return tuple(tool for tool in TOOLS if tool.section == section)
