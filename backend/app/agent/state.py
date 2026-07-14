from typing import TypedDict, Annotated, Optional, Dict, Any
import operator


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    current_form_state: Dict[str, Any]
    tool_calls: list
    updated_fields: Dict[str, Any]
    compliance_flag: Optional[str]
