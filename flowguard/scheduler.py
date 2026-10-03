"""choose_slot：全局最优会议择时。

最优性说明：固定某日后，可行起点构成若干整数区间。对每位参与者，
把新会议 [s, s+d) 视为 meeting 重算专注容量，其损失 loss(s) 关于 s
分片线性，断点只出现在潜在专注段派生点 a+5400 与 c-5400-d 处
（a、c 为段端点），每片内斜率属于 {-1, 0, 1}。逐人损失的最大值是
凸分片线性函数，其在整数点上的最小值只可能出现在分片端点或两条
损失线交点的取整邻域；总损失在每片内线性，最值在端点。因此枚举
"区间端点 + 断点 + 交点取整邻域"即可覆盖全局最优解。
"""

from __future__ import annotations

from fractions import Fraction

from .capacity import FOCUS_THRESHOLD, focus_capacity
from .intervals import intersect, subtract
from .types import Interval, Participant, SlotChoice

MIN_DURATION = 15 * 60
MAX_DURATION = 120 * 60
DURATION_STEP = 15 * 60


def choose_slot(
    participants: list[Participant],
    blocked: list[Interval],
    duration: int,
) -> SlotChoice | None:
    """返回最优会议起止时间；无解返回 None。

    依次最小化：最大个人损失、全体损失之和、开始时间。
    """
    if not participants:
        raise ValueError("participants 不能为空")
    if not (MIN_DURATION <= duration <= MAX_DURATION):
        raise ValueError("会议时长必须在 15 至 120 分钟之间")
    if duration % DURATION_STEP != 0:
        raise ValueError("会议时长必须是 15 分钟的整数倍")

    best: tuple[int, int, int] | None = None  # (max_loss, total_loss, start)

    for day in range(5):
        common: list[Interval] | None = None
        day_data: list[tuple[Interval, list[Interval], int]] = []
        for person in participants:
            work = person.work_windows[day]
            capacity_blockers = person.meetings + person.personal
            focus_segments = subtract(work, capacity_blockers)
            before = focus_capacity(work, capacity_blockers)
            day_data.append((work, focus_segments, before))
            available = subtract(
                work, capacity_blockers + person.focus_blocks + blocked
            )
            common = available if common is None else intersect(common, available)
            if not common:
                break
        if not common:
            continue

        for candidate in _candidate_starts(common, day_data, duration):
            losses = [
                before - focus_capacity(work, _blockers_with(work, segs, before,
                                                              candidate, duration))
                for work, segs, before in day_data
            ]
            key = (max(losses), sum(losses), candidate)
            if best is None or key < best:
                best = key

    if best is None:
        return None
    max_loss, total_loss, start = best
    return SlotChoice(start=start, end=start + duration,
                      max_loss=max_loss, total_loss=total_loss)


def _blockers_with(work, focus_segments, before, start, duration):
    """由会前专注段反推 blockers 并附上新会议（避免重复合并开销）。"""
    meeting = Interval(start, start + duration)
    blockers: list[Interval] = []
    cursor = work.start
    for seg in focus_segments:
        if cursor < seg.start:
            blockers.append(Interval(cursor, seg.start))
        cursor = seg.end
    if cursor < work.end:
        blockers.append(Interval(cursor, work.end))
    blockers.append(meeting)
    return blockers


def _candidate_starts(
    common: list[Interval],
    day_data: list[tuple[Interval, list[Interval], int]],
    duration: int,
) -> list[int]:
    """生成覆盖全局最优解的候选起点集合。"""
    candidates: set[int] = set()
    for window in common:
        lo = window.start
        hi = window.end - duration
        if hi < lo:
            continue
        # 断点：专注段 [a, c) 派生 a+5400 与 c-5400-d
        points = {lo, hi}
        for _, segments, _ in day_data:
            for seg in segments:
                for point in (seg.start + FOCUS_THRESHOLD,
                              seg.end - FOCUS_THRESHOLD - duration):
                    if lo < point < hi:
                        points.add(point)
        ordered = sorted(points)
        candidates.update(ordered)
        # 每个分片内求两两损失线交点，加入取整邻域
        for left, right in zip(ordered, ordered[1:]):
            if left >= right:
                continue
            lines = [_loss_line(data, left, right, duration) for data in day_data]
            for i in range(len(lines)):
                for j in range(i + 1, len(lines)):
                    slope_i, intercept_i = lines[i]
                    slope_j, intercept_j = lines[j]
                    if slope_i == slope_j:
                        continue
                    cross = Fraction(intercept_j - intercept_i,
                                     slope_i - slope_j)
                    if cross <= left or cross >= right:
                        continue
                    base = cross.numerator // cross.denominator  # floor
                    for offset in (-1, 0, 1, 2):
                        point = base + offset
                        if left <= point <= right:
                            candidates.add(point)
    return sorted(candidates)


def _loss_line(
    data: tuple[Interval, list[Interval], int],
    left: int,
    right: int,
    duration: int,
) -> tuple[int, int]:
    """由两点损失值还原分片内的线性损失 (slope, intercept)。"""
    work, segments, before = data
    loss_left = _loss_at(work, segments, before, left, duration)
    loss_right = _loss_at(work, segments, before, right, duration)
    slope = (loss_right - loss_left) // (right - left)
    intercept = loss_left - slope * left
    return slope, intercept


def _loss_at(
    work: Interval,
    focus_segments: list[Interval],
    before: int,
    start: int,
    duration: int,
) -> int:
    blockers = _blockers_with(work, focus_segments, before, start, duration)
    return before - focus_capacity(work, blockers)
