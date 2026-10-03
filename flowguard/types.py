"""FlowGuard 团队会议择时库的类型定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

DAYS = 5
MIN_FOCUS_SEGMENT = 5400  # 潜在专注段贡献阈值（秒）


class EventKind(str, Enum):
    MEETING = "meeting"
    PERSONAL = "personal"
    FOCUS_BLOCK = "focus_block"


@dataclass(frozen=True)
class Event:
    """左闭右开的整数秒区间。"""

    start: int
    end: int
    kind: EventKind


@dataclass
class Problem:
    """一次择时请求的完整输入。

    work_hours: person -> 长度为 5 的列表，元素为 (start, end) 或 None。
    events: person -> 该人的事件列表（可重叠、重复、跨界）。
    blocked: 团队禁会区间列表。
    duration: 会议时长（秒），15~120 分钟的 15 分钟整数倍。
    """

    participants: list[str]
    work_hours: dict[str, list[tuple[int, int] | None]]
    events: dict[str, list[Event]] = field(default_factory=dict)
    blocked: list[tuple[int, int]] = field(default_factory=list)
    duration: int = 900


@dataclass(frozen=True)
class Slot:
    """choose_slot 的结果：最优起止时间。"""

    start: int
    end: int
