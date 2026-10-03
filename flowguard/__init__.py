"""FlowGuard：团队会议择时，尽量保住连续深度工作时间。"""
from .types import DAYS, MIN_FOCUS_SEGMENT, Event, EventKind, Problem, Slot
from .scheduler import choose_slot

__all__ = [
    "DAYS",
    "MIN_FOCUS_SEGMENT",
    "Event",
    "EventKind",
    "Problem",
    "Slot",
    "choose_slot",
]
