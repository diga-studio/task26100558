"""FlowGuard 团队会议择时库：数据类型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Interval:
    """左闭右开的整数秒区间 [start, end)。"""

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"区间终点早于起点: {self.start} > {self.end}")

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass
class Participant:
    """一位参与者：五个工作日各一个工作时段，以及已有事件。"""

    name: str
    work_windows: tuple[Interval, ...]
    meetings: list[Interval] = field(default_factory=list)
    personal: list[Interval] = field(default_factory=list)
    focus_blocks: list[Interval] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.work_windows) != 5:
            raise ValueError("work_windows 必须包含 5 个工作日时段")


@dataclass(frozen=True)
class SlotChoice:
    """choose_slot 的结果：最优会议区间及损失明细。"""

    start: int
    end: int
    max_loss: int
    total_loss: int
