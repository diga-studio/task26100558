"""潜在专注段与专注容量计算。"""

from __future__ import annotations

from .intervals import subtract
from .types import Interval

FOCUS_THRESHOLD = 5400


def focus_capacity(work: Interval, blockers: list[Interval]) -> int:
    """从工作时段扣除 blockers 后，长度达到阈值的连续段贡献其全长。

    blockers 仅包含 meeting 与 personal；focus_block 与禁会区间不切断
    潜在专注段，因此不在此扣除。
    """
    segments = subtract(work, blockers)
    return sum(seg.length for seg in segments if seg.length >= FOCUS_THRESHOLD)
