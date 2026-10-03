"""核心择时逻辑。

思路：
- 每天先求所有参与者工作时段的交集，再扣除全部事件与禁会区间，得到可行窗口。
- 关键观察：可行窗口必落在该人某条潜在专注段（工作时段扣除 meeting∪personal）
  之内，因此插入会议只会把该专注段 (fs, fe) 拆成 (fs, s) 与 (s+d, fe) 两段，
  个人损失可 O(1) 计算，逐秒枚举所有可行整数起点即为全局最优。
"""
from __future__ import annotations

from bisect import bisect_right

from .intervals import Interval, clip, normalize, subtract
from .types import DAYS, MIN_FOCUS_SEGMENT, Event, EventKind, Problem, Slot

_MIN_DURATION = 15 * 60
_MAX_DURATION = 120 * 60
_STEP = 15 * 60

_CUT_KINDS = (EventKind.MEETING, EventKind.PERSONAL)
_INF = 1 << 62


def _contrib(length: int) -> int:
    """潜在专注段的贡献：达到阈值贡献全部长度，否则为零。"""
    return length if length >= MIN_FOCUS_SEGMENT else 0


def _validate(problem: Problem) -> None:
    if not problem.participants:
        raise ValueError("participants 不能为空")
    if (
        problem.duration < _MIN_DURATION
        or problem.duration > _MAX_DURATION
        or problem.duration % _STEP != 0
    ):
        raise ValueError("duration 必须是 15~120 分钟的 15 分钟整数倍")
    for person in problem.participants:
        windows = problem.work_hours.get(person)
        if windows is None or len(windows) != DAYS:
            raise ValueError(f"{person!r} 必须提供 {DAYS} 天的工作时段")
        for window in windows:
            if window is not None and window[1] <= window[0]:
                raise ValueError(f"{person!r} 的工作时段必须非空且 end > start")
    for person, events in problem.events.items():
        for event in events:
            if event.end <= event.start:
                raise ValueError(f"{person!r} 存在空事件区间")
    for start, end in problem.blocked:
        if end <= start:
            raise ValueError("禁会区间必须非空且 end > start")


def _free_segments(
    window: tuple[int, int], events: list[Event]
) -> tuple[list[Interval], int]:
    """返回 (潜在专注段列表, 当日专注容量)。"""
    busy = [(e.start, e.end) for e in events if e.kind in _CUT_KINDS]
    segments = subtract(window, clip(busy, window[0], window[1]))
    capacity = sum(_contrib(e - s) for s, e in segments)
    return segments, capacity


def choose_slot(problem: Problem) -> Slot | None:
    """返回最优会议起止时间；无解返回 None。

    最优：依次最小化 最大个人损失、全体损失之和、开始时间。
    """
    _validate(problem)
    duration = problem.duration
    participants = problem.participants
    blocked = normalize(problem.blocked)

    best_key: tuple[int, int, int] | None = None

    for day in range(DAYS):
        # 共同工作时段：每人每天至多一个区间，直接求交。
        common: Interval | None = None
        for person in participants:
            window = problem.work_hours[person][day]
            if window is None:
                common = None
                break
            common = window if common is None else (
                max(common[0], window[0]),
                min(common[1], window[1]),
            )
            if common[1] <= common[0]:
                common = None
                break
        if common is None or common[1] - common[0] < duration:
            continue

        # 禁会并集：所有参与者的全部事件（含 focus_block）+ 团队禁会区间。
        forbidden = list(clip(blocked, common[0], common[1]))
        for person in participants:
            forbidden.extend(
                clip([(e.start, e.end) for e in problem.events.get(person, [])],
                     common[0], common[1])
            )
        feasible = subtract(common, forbidden)

        # 每人当天的潜在专注段（只被 meeting/personal 切断）。
        free_by_person: dict[str, list[Interval]] = {}
        for person in participants:
            window = problem.work_hours[person][day]
            assert window is not None
            segments, _ = _free_segments(window, problem.events.get(person, []))
            free_by_person[person] = segments

        for win_start, win_end in feasible:
            if win_end - win_start < duration:
                continue
            # 可行窗口必完整落在每人某条专注段内，定位一次即可。
            anchors: dict[str, Interval] = {}
            for person in participants:
                segments = free_by_person[person]
                idx = bisect_right(segments, (win_start, _INF)) - 1
                seg = segments[idx]
                assert seg[0] <= win_start and win_end <= seg[1]
                anchors[person] = seg
            last_start = win_end - duration
            for start in range(win_start, last_start + 1):
                max_loss = 0
                total_loss = 0
                for person in participants:
                    seg_start, seg_end = anchors[person]
                    loss = (
                        _contrib(seg_end - seg_start)
                        - _contrib(start - seg_start)
                        - _contrib(seg_end - start - duration)
                    )
                    if loss > max_loss:
                        max_loss = loss
                    total_loss += loss
                key = (max_loss, total_loss, start)
                if best_key is None or key < best_key:
                    best_key = key

    if best_key is None:
        return None
    return Slot(start=best_key[2], end=best_key[2] + duration)
