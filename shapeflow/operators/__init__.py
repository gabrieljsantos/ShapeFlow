from .draw_profile import SHAPEFLOW_OT_draw_rectangle
from .extrude_face import SHAPEFLOW_OT_extrude_face
from .workspace import SHAPEFLOW_OT_workspace
from .mode import SHAPEFLOW_OT_activate_tool, SHAPEFLOW_OT_toggle_mode, SHAPEFLOW_OT_tool_placeholder

CLASSES = (
    SHAPEFLOW_OT_draw_rectangle,
    SHAPEFLOW_OT_extrude_face,
    SHAPEFLOW_OT_workspace,
    SHAPEFLOW_OT_toggle_mode,
    SHAPEFLOW_OT_activate_tool,
    SHAPEFLOW_OT_tool_placeholder,
)
