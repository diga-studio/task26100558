"""FlowGuard：在插入会议后尽量保住每个人的连续深度工作时间。"""

from .scheduler import choose_slot
from .types import Interval, Participant, SlotChoice

__all__ = ["Interval", "Participant", "SlotChoice", "choose_slot"]
